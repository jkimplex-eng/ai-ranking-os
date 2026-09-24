from dataclasses import dataclass
from decimal import Decimal

from eis.models import EISScore
from eis.repository import EISRepository
from eis.schemas import EISBatchRequest, EISCalculateRequest, QueryEvidence
from frozen_prompts.repository import FrozenPromptRepository
from geo_platforms.models import GeoPlatform
from geo_platforms.repository import PlatformRepository
from geo_platforms.service import PlatformNotFoundError

METHODOLOGY_VERSION = "heuristic_v1.0"
WEIGHT_SET_VERSION = "eis_relative_2026-08"


@dataclass(frozen=True)
class ComponentResult:
    value: float | None
    numerator: float
    denominator: float
    inputs: dict[str, float | bool | None]
    weights: dict[str, float]
    exclusions: list[str]

    def as_dict(self) -> dict:
        return {
            "value": self.value,
            "numerator": self.numerator,
            "denominator": self.denominator,
            "inputs": self.inputs,
            "weights": self.weights,
            "exclusions": self.exclusions,
        }


class EISService:
    COMPONENT_WEIGHTS = {"authority": 0.10, "entity": 0.15, "content": 0.12, "match": 0.10}
    ENGINE_BIASES = {
        "chatgpt": 2.0,
        "openai": 2.0,
        "perplexity": 1.0,
        "gemini": 3.0,
        "claude": -1.0,
        "anthropic": -1.0,
        "yandexgpt": 4.0,
        "yandex": 4.0,
        "gigachat": 1.0,
    }

    def __init__(
        self,
        repository: EISRepository,
        platforms: PlatformRepository,
        prompts: FrozenPromptRepository,
    ) -> None:
        self.repository = repository
        self.platforms = platforms
        self.prompts = prompts

    def calculate(self, payload: EISCalculateRequest) -> EISScore:
        platform = self.platforms.get(payload.platform_id)
        if platform is None:
            raise PlatformNotFoundError(f"Platform {payload.platform_id} not found")
        if payload.query_id is not None and self.prompts.get_instance(payload.query_id) is None:
            raise LookupError(f"Query {payload.query_id} not found")
        return self.repository.save(self._score(platform, payload))

    def prioritize(self, payload: EISBatchRequest) -> list[tuple[EISScore, float | None]]:
        unique_ids = list(dict.fromkeys(payload.platform_ids))
        results: list[tuple[EISScore, float | None]] = []
        for platform_id in unique_ids:
            request = EISCalculateRequest(
                platform_id=platform_id,
                query_id=payload.query_id,
                ai_engine=payload.ai_engine,
                model_type=payload.model_type,
                query_evidence=payload.query_evidence,
            )
            score = self.calculate(request)
            platform = self.platforms.get(platform_id)
            efficiency = self._cost_efficiency(score.eis_value, platform.cost_per_placement)
            results.append((score, efficiency))
        priority_rank = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, None: 4}
        return sorted(
            results,
            key=lambda row: (priority_rank[row[0].priority], -(row[0].eis_value or -1)),
        )

    def _score(self, platform: GeoPlatform, payload: EISCalculateRequest) -> EISScore:
        components = {
            "authority": self._authority(platform),
            "entity": self._entity(platform),
            "content": self._content(platform),
            "match": self._match(payload.query_evidence),
        }
        measured = {name: item for name, item in components.items() if item.value is not None}
        all_inputs = sum(len(item.inputs) for item in components.values())
        measured_inputs = sum(
            sum(value is not None for value in item.inputs.values()) for item in components.values()
        )
        if not measured:
            status = "NOT_MEASURED"
            score_value = None
            priority = None
            numerator = 0.0
            denominator = 0.0
            bias = 0.0
        else:
            numerator = sum(
                self.COMPONENT_WEIGHTS[name] * float(item.value) for name, item in measured.items()
            )
            denominator = sum(self.COMPONENT_WEIGHTS[name] for name in measured)
            base = numerator / denominator
            bias = self.ENGINE_BIASES.get(payload.ai_engine.casefold(), 0.0)
            score_value = round(min(100.0, max(0.0, base + bias)), 2)
            priority = self._priority(score_value)
            if len(measured) == 4 and measured_inputs == all_inputs:
                status = "MEASURED"
            elif measured_inputs < 4:
                status = "INSUFFICIENT_SAMPLE"
            else:
                status = "PARTIAL"
        component_payload = {name: result.as_dict() for name, result in components.items()}
        warnings = []
        if status != "MEASURED":
            warnings.append(
                "Some eligible evidence is missing; the estimate is not a complete measurement."
            )
        if score_value == 100:
            warnings.append(
                "100 is saturation inside this declared sample, not universal AI visibility."
            )
        explanation = {
            "formula": "weighted_component_sum / available_weight_sum + engine_bias",
            "numerator": round(numerator, 6),
            "denominator": round(denominator, 6),
            "normalization": "relative weights normalized by their available sum; clamp [0,100]",
            "cap": {"min": 0, "max": 100},
            "engine_bias": bias,
            "engine_bias_status": "UNVALIDATED_PRIOR",
            "component_weights": self.COMPONENT_WEIGHTS,
            "weighted_contributions": {
                name: round(self.COMPONENT_WEIGHTS[name] * float(item.value), 6)
                for name, item in measured.items()
            },
            "value_before_rounding": None
            if not measured
            else min(100.0, max(0.0, numerator / denominator + bias)),
            "value_after_rounding": score_value,
            "measured_inputs": measured_inputs,
            "eligible_inputs": all_inputs,
            "warnings": warnings,
            "limitation": "Correlation-based estimate; AI retrieval and ranking are black boxes.",
        }
        evidence = {
            "platform_evidence": platform.evidence,
            "evidence_ids": payload.query_evidence.evidence_ids,
            "failed_evidence_ids": payload.query_evidence.failed_evidence_ids,
            "excluded_inputs": {
                name: result.exclusions for name, result in components.items() if result.exclusions
            },
        }
        return EISScore(
            platform_id=platform.id,
            query_id=payload.query_id,
            ai_engine=payload.ai_engine,
            model_type=payload.model_type,
            eis_value=score_value,
            priority=priority,
            components=component_payload,
            signal_probabilities={
                "mention": None,
                "citation": None,
                "linked": None,
                "recommendation": None,
            },
            evidence=evidence,
            explanation=explanation,
            evidence_status=status,
            methodology_version=METHODOLOGY_VERSION,
            weight_set_version=WEIGHT_SET_VERSION,
        )

    def _authority(self, p: GeoPlatform) -> ComponentResult:
        return self._component(
            {
                "domain_trust": p.domain_trust,
                "topical_authority": p.topical_authority_score,
                "ai_citation_history": self._scale(p.ai_citation_history, 100),
                "allows_crawlers": self._boolean(p.allows_ai_crawlers),
            },
            {
                "domain_trust": 0.30,
                "topical_authority": 0.25,
                "ai_citation_history": 0.25,
                "allows_crawlers": 0.20,
            },
        )

    def _entity(self, p: GeoPlatform) -> ComponentResult:
        return self._component(
            {
                "branded_mentions_90d": self._scale(p.branded_mentions_90d, 1000),
                "youtube_mentions": self._scale(p.youtube_mentions, 100),
                "branded_anchors": self._scale(p.branded_anchors, 500),
                "in_knowledge_graph": self._boolean(p.in_knowledge_graph),
                "branded_search_volume": self._scale(p.branded_search_volume, 10000),
            },
            {
                "branded_mentions_90d": 0.35,
                "youtube_mentions": 0.30,
                "branded_anchors": 0.20,
                "in_knowledge_graph": 0.10,
                "branded_search_volume": 0.05,
            },
        )

    def _content(self, p: GeoPlatform) -> ComponentResult:
        schema_weights = {
            "FAQPage": 25,
            "HowTo": 25,
            "Article": 20,
            "Product": 15,
            "Organization": 15,
        }
        schema_score = (
            None
            if p.schema_markup_types is None
            else min(100.0, sum(schema_weights.get(item, 0) for item in p.schema_markup_types))
        )
        freshness = (
            None
            if p.content_freshness_days is None
            else 100 - min(90, p.content_freshness_days) * 0.5
        )
        return self._component(
            {
                "schema_score": schema_score,
                "direct_answer": self._boolean(p.has_direct_answer),
                "freshness_score": freshness,
                "structured_lists": self._boolean(p.has_structured_lists),
                "self_contained_paragraphs": p.self_contained_paragraph_score,
            },
            {
                "schema_score": 0.30,
                "direct_answer": 0.25,
                "freshness_score": 0.20,
                "structured_lists": 0.15,
                "self_contained_paragraphs": 0.10,
            },
        )

    def _match(self, q: QueryEvidence) -> ComponentResult:
        serp = None
        if q.serp_position is not None:
            serp = (
                0.0
                if q.serp_position == 0
                else 100.0
                if q.serp_position <= 3
                else 70.0
                if q.serp_position <= 10
                else 30.0
            )
        return self._component(
            {
                "cep_coverage": q.cep_coverage,
                "semantic_similarity": q.semantic_similarity,
                "serp_position_score": serp,
            },
            {"cep_coverage": 0.40, "semantic_similarity": 0.35, "serp_position_score": 0.25},
        )

    @staticmethod
    def _component(
        inputs: dict[str, float | bool | None], weights: dict[str, float]
    ) -> ComponentResult:
        available = {key: float(value) for key, value in inputs.items() if value is not None}
        numerator = sum(weights[key] * value for key, value in available.items())
        denominator = sum(weights[key] for key in available)
        value = None if denominator == 0 else round(numerator / denominator, 4)
        return ComponentResult(
            value,
            round(numerator, 6),
            round(denominator, 6),
            inputs,
            weights,
            [key for key, value in inputs.items() if value is None],
        )

    @staticmethod
    def _scale(value: int | float | None, cap: float) -> float | None:
        return None if value is None else min(100.0, max(0.0, float(value) / cap * 100))

    @staticmethod
    def _boolean(value: bool | None) -> float | None:
        return None if value is None else (100.0 if value else 0.0)

    @staticmethod
    def _priority(value: float) -> str:
        return "P0" if value >= 85 else "P1" if value >= 75 else "P2" if value >= 60 else "P3"

    @staticmethod
    def _cost_efficiency(score: float | None, cost: Decimal | None) -> float | None:
        if score is None or cost is None:
            return None
        return round(score / max(float(cost), 1.0), 6)
