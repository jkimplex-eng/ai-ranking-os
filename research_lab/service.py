from collections import defaultdict
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from graph.models import GraphSnapshot
from product.service import FinalReportService, ProductNotFoundError
from research.models import Research
from research_lab.repository import PublicationRepository


class ResearchLaboratoryService:
    """Compose persisted research evidence without provider calls or writes."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, research_id: int) -> dict[str, Any]:
        research = self._research(research_id)
        report = FinalReportService(self.db).get(research_id)
        evidence = report["explainability"]
        responses = report["responses"]
        entity_rows = report["detected_entities"]
        source_rows = report["sources"]
        response_map = {item["id"]: item for item in responses}
        entities_by_response = self._group(entity_rows, "response_id")
        sources_by_response = self._group(source_rows, "response_id")
        recommendations_by_response = self._group(evidence["responses"], "response_id")
        target = self._target(research)
        total = len(responses)
        models = []
        for response in sorted(
            responses, key=lambda item: (item["provider"], item["model"], item["id"])
        ):
            extracted_entities = entities_by_response[response["id"]]
            extracted_sources = sources_by_response[response["id"]]
            response_evidence = recommendations_by_response[response["id"]][0]
            mentioned = target in response["content"].casefold() or any(
                target
                in {
                    item["name"].casefold(),
                    item["canonical_name"].casefold(),
                    *(alias.casefold() for alias in item["aliases"]),
                }
                for item in extracted_entities
            )
            recommendation_count = len(response_evidence["recommendation_ids"])
            models.append(
                {
                    **response_evidence,
                    "content": response["content"],
                    "processing_status": response["processing_status"],
                    "language": research.metadata_payload.get(
                        "languages", research.metadata_payload.get("language")
                    ),
                    "region": research.metadata_payload.get(
                        "regions", research.metadata_payload.get("region")
                    ),
                    "signals": {
                        "mentioned": mentioned,
                        "recommended": recommendation_count > 0,
                        "citation_count": len(extracted_sources),
                        "mention_numerator_contribution": 1 if mentioned else 0,
                        "recommendation_numerator_contribution": 1 if recommendation_count else 0,
                        "citation_numerator_contribution": len(extracted_sources),
                        "aggregate_denominator_responses": total,
                        "visibility_score": None,
                        "visibility_status": "NOT_CALCULATED_PER_MODEL_IN_SCORING_V1",
                    },
                    "entities": extracted_entities,
                    "citations": extracted_sources,
                }
            )
        sources = self._sources(source_rows, response_map, total)
        entities = self._entities(entity_rows, response_map, source_rows)
        evidence["metric_explanations"] = self._metric_explanations(models, sources)
        graph = self._graph(research)
        timeline = self._timeline(research, responses, report, graph)
        publications = (
            PublicationRepository(self.db).list_for_entity(research.entity_id)
            if research.entity_id
            else []
        )
        for publication in publications:
            timeline.append(
                self._event(
                    "PUBLICATION", publication.published_at, publication.id, publication.title
                )
            )
            for observation in publication.observations:
                timeline.append(
                    self._event(
                        "FIRST_OBSERVED",
                        observation.first_observed_at,
                        observation.id,
                        f"{observation.provider}/{observation.model}",
                    )
                )
        timeline.sort(key=lambda item: (item["at"], item["type"], item["id"]))
        return {
            "research": report["research"],
            "score": report["score"],
            "provenance": evidence,
            "models": models,
            "sources": sources,
            "entities": entities,
            "graph": graph,
            "recommendations": self._recommendations(report, models, sources),
            "timeline": timeline,
            "publications": publications,
        }

    def diff(self, left_id: int, right_id: int) -> dict[str, Any]:
        left = self.get(left_id)
        right = self.get(right_id)
        metrics = (
            "visibility_score",
            "mention_score",
            "recommendation_score",
            "citation_score",
            "coverage_score",
            "confidence_score",
        )
        metric_deltas = {
            metric: self._delta(left["score"], right["score"], metric) for metric in metrics
        }
        left_models = {(item["provider"], item["model"]): item for item in left["models"]}
        right_models = {(item["provider"], item["model"]): item for item in right["models"]}
        response_changes: list[dict[str, Any]] = []
        signal_changes: list[dict[str, Any]] = []
        for key in sorted(set(left_models) | set(right_models)):
            before, after = left_models.get(key), right_models.get(key)
            state = "ADDED" if before is None else "REMOVED" if after is None else "UNCHANGED"
            if before and after and before["content"] != after["content"]:
                state = "CONTENT_CHANGED"
            response_changes.append({"provider": key[0], "model": key[1], "state": state})
            before_signals = before["signals"] if before else None
            after_signals = after["signals"] if after else None
            if before_signals != after_signals:
                signal_changes.append(
                    {
                        "provider": key[0],
                        "model": key[1],
                        "before": before_signals,
                        "after": after_signals,
                    }
                )
        return {
            "left_research_id": left_id,
            "right_research_id": right_id,
            "metric_deltas": metric_deltas,
            "response_changes": response_changes,
            "entity_changes": self._set_changes(
                left["entities"], right["entities"], "canonical_name"
            ),
            "source_changes": self._set_changes(left["sources"], right["sources"], "identity"),
            "provider_signal_changes": signal_changes,
            "interpretation": (
                "Observed differences between persisted research artifacts. They show correlation, "
                "not causal impact of any publication or intervention."
            ),
        }

    def _research(self, research_id: int) -> Research:
        item = self.db.scalar(
            select(Research).options(selectinload(Research.tasks)).where(Research.id == research_id)
        )
        if item is None:
            raise ProductNotFoundError(f"Research {research_id} not found")
        return item

    def _graph(self, research: Research) -> dict[str, Any]:
        graph_artifact = (
            research.metadata_payload.get("product_artifacts", {}).get("knowledge_graph") or {}
        )
        snapshot_id = graph_artifact.get("snapshot_id") or graph_artifact.get("id")
        snapshot = None
        if snapshot_id:
            snapshot = self.db.scalar(
                select(GraphSnapshot)
                .options(selectinload(GraphSnapshot.nodes), selectinload(GraphSnapshot.edges))
                .where(GraphSnapshot.id == snapshot_id)
            )
        if snapshot is None:
            return {
                "status": "NOT_LINKED",
                "reason": "No graph snapshot is linked to this research.",
                "nodes": [],
                "edges": [],
            }
        node_names = {node.id: node.name for node in snapshot.nodes}
        return {
            "status": "AVAILABLE",
            "snapshot_id": snapshot.id,
            "version": snapshot.structure_version,
            "nodes": [
                {
                    "id": node.id,
                    "name": node.name,
                    "canonical_name": node.canonical_name,
                    "type": node.node_type,
                    "confidence": node.confidence,
                    "aliases": node.aliases,
                    "properties": node.properties,
                }
                for node in sorted(snapshot.nodes, key=lambda item: item.id)
            ],
            "edges": [
                {
                    "id": edge.id,
                    "source_id": edge.source_node_id,
                    "source": node_names.get(edge.source_node_id),
                    "target_id": edge.target_node_id,
                    "target": node_names.get(edge.target_node_id),
                    "type": edge.edge_type,
                    "confidence": edge.confidence,
                    "properties": edge.properties,
                    "evidence_status": "RECORDED"
                    if edge.properties.get("evidence") or edge.properties.get("response_id")
                    else "NOT_RECORDED",
                }
                for edge in sorted(snapshot.edges, key=lambda item: item.id)
            ],
            "created_at": snapshot.created_at,
        }

    @staticmethod
    def _target(research: Research) -> str:
        for key in ("target_entity", "entity", "brand"):
            value = research.metadata_payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip().casefold()
        return research.title.strip().casefold()

    @staticmethod
    def _group(items: list[dict[str, Any]], key: str) -> defaultdict[Any, list[dict[str, Any]]]:
        grouped: defaultdict[Any, list[dict[str, Any]]] = defaultdict(list)
        for item in items:
            grouped[item[key]].append(item)
        return grouped

    @staticmethod
    def _sources(
        rows: list[dict[str, Any]], responses: dict[int, dict[str, Any]], total: int
    ) -> list[dict[str, Any]]:
        grouped: dict[str, dict[str, Any]] = {}
        denominator = total * 3
        for row in rows:
            identity = row.get("url") or row.get("source") or f"citation:{row['id']}"
            item = grouped.setdefault(
                identity,
                {
                    "identity": identity,
                    "url": row.get("url"),
                    "domain": urlparse(row["url"]).hostname if row.get("url") else None,
                    "title": row.get("title"),
                    "source": row.get("source"),
                    "citation_ids": [],
                    "providers": set(),
                    "models": set(),
                    "authority": None,
                    "authority_status": "NOT_CALCULATED_IN_SCORING_V1",
                },
            )
            item["citation_ids"].append(row["id"])
            response = responses[row["response_id"]]
            item["providers"].add(response["provider"])
            item["models"].add(response["model"])
        result = []
        for item in grouped.values():
            count = len(item["citation_ids"])
            item["citation_count"] = count
            item["citation_score_points_before_cap"] = (
                round(count / denominator * 100, 4) if denominator else 0.0
            )
            item["providers"] = sorted(item["providers"])
            item["models"] = sorted(item["models"])
            result.append(item)
        return sorted(result, key=lambda item: (-item["citation_count"], item["identity"]))

    @staticmethod
    def _entities(
        rows: list[dict[str, Any]],
        responses: dict[int, dict[str, Any]],
        citations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        citations_by_response = ResearchLaboratoryService._group(citations, "response_id")
        grouped: dict[str, dict[str, Any]] = {}
        for row in rows:
            key = row["canonical_name"].strip().casefold()
            item = grouped.setdefault(
                key,
                {
                    "canonical_name": row["canonical_name"],
                    "type": row["entity_type"],
                    "aliases": set(),
                    "occurrences": [],
                    "source_ids": set(),
                    "knowledge_graph_ids": set(),
                },
            )
            item["aliases"].update(row["aliases"])
            response = responses[row["response_id"]]
            item["occurrences"].append(
                {
                    "entity_id": row["id"],
                    "response_id": row["response_id"],
                    "provider": response["provider"],
                    "model": response["model"],
                    "confidence": row["confidence"],
                }
            )
            item["source_ids"].update(
                citation["id"] for citation in citations_by_response[row["response_id"]]
            )
            if row.get("knowledge_graph_id"):
                item["knowledge_graph_ids"].add(row["knowledge_graph_id"])
        for item in grouped.values():
            item["aliases"] = sorted(item["aliases"])
            item["source_ids"] = sorted(item["source_ids"])
            item["knowledge_graph_ids"] = sorted(item["knowledge_graph_ids"])
            item["occurrences"].sort(
                key=lambda occurrence: (
                    occurrence["provider"],
                    occurrence["model"],
                    occurrence["response_id"],
                )
            )
        return sorted(
            grouped.values(), key=lambda item: (item["type"], item["canonical_name"].casefold())
        )

    @staticmethod
    def _recommendations(
        report: dict[str, Any], models: list[dict[str, Any]], sources: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        affected = sorted(
            {
                f"{item['provider']}/{item['model']}"
                for item in models
                if not item["signals"]["recommended"] or not item["signals"]["citation_count"]
            }
        )
        missing_sources = not sources
        result = []
        for item in report["recommendations"]:
            payload = dict(item)
            payload["affected_models"] = affected
            payload["missing_sources"] = missing_sources
            payload["evidence_status"] = "OBSERVED_TRIGGER"
            result.append(payload)
        return result

    @staticmethod
    def _metric_explanations(
        models: list[dict[str, Any]], sources: list[dict[str, Any]]
    ) -> dict[str, Any]:
        total = len(models)
        mentioned = [item for item in models if item["signals"]["mentioned"]]
        recommended = [item for item in models if item["signals"]["recommended"]]
        cited = [item for item in models if item["signals"]["citation_count"]]

        def names(items: list[dict[str, Any]]) -> list[str]:
            return sorted(f"{item['provider']}/{item['model']}" for item in items)

        return {
            "mention_score": {
                "observed": f"Бренд упомянут в {len(mentioned)} из {total} ответов.",
                "positive_models": names(mentioned),
                "deficit_models": names([item for item in models if item not in mentioned]),
                "cause_status": "OBSERVED_RESPONSE_SIGNAL",
            },
            "recommendation_score": {
                "observed": f"Рекомендация обнаружена в {len(recommended)} из {total} ответов.",
                "positive_models": names(recommended),
                "deficit_models": names([item for item in models if item not in recommended]),
                "cause_status": "OBSERVED_RESPONSE_SIGNAL",
                "unknown_causes": (
                    "Причины отсутствия рекомендации нельзя утверждать без прямого "
                    "обоснования в ответе модели."
                ),
            },
            "citation_score": {
                "observed": (
                    f"Найдено {sum(item['signals']['citation_count'] for item in models)} "
                    f"цитат в {len(cited)} из {total} ответов."
                ),
                "positive_models": names(cited),
                "deficit_models": names([item for item in models if item not in cited]),
                "source_count": len(sources),
                "cause_status": "OBSERVED_RESPONSE_SIGNAL",
            },
            "coverage_score": {
                "observed": f"Получены сохранённые ответы от {total} моделей/запусков.",
                "positive_models": names(models),
                "deficit_models": [],
                "cause_status": "OBSERVED_EXECUTION_SIGNAL",
            },
        }

    @staticmethod
    def _timeline(
        research: Research,
        responses: list[dict[str, Any]],
        report: dict[str, Any],
        graph: dict[str, Any],
    ) -> list[dict[str, Any]]:
        items = [
            ResearchLaboratoryService._event(
                "RESEARCH_CREATED", research.created_at, research.id, research.title
            )
        ]
        for task in research.tasks:
            items.append(
                ResearchLaboratoryService._event(
                    "TASK_CREATED",
                    task.created_at,
                    task.id,
                    f"{task.provider or 'unassigned'}/{task.model or 'unassigned'}",
                )
            )
        for response in responses:
            items.append(
                ResearchLaboratoryService._event(
                    "RESPONSE_FINISHED",
                    response["finished_at"],
                    response["id"],
                    f"{response['provider']}/{response['model']}",
                )
            )
        if report["score"]:
            items.append(
                ResearchLaboratoryService._event(
                    "SCORE_CALCULATED",
                    report["score"]["calculated_at"],
                    report["score"]["id"],
                    report["score"]["version"],
                )
            )
        if graph.get("created_at"):
            items.append(
                ResearchLaboratoryService._event(
                    "GRAPH_BUILT", graph["created_at"], graph["snapshot_id"], graph["version"]
                )
            )
        items.sort(key=lambda item: (item["at"], item["type"], item["id"]))
        return items

    @staticmethod
    def _event(kind: str, at: datetime | str, item_id: int, label: str) -> dict[str, Any]:
        timestamp = at.isoformat() if isinstance(at, datetime) else at
        return {"type": kind, "at": timestamp, "id": item_id, "label": label}

    @staticmethod
    def _delta(
        left: dict[str, Any] | None, right: dict[str, Any] | None, metric: str
    ) -> float | None:
        if not left or not right:
            return None
        return round(float(right[metric]) - float(left[metric]), 4)

    @staticmethod
    def _set_changes(
        left: list[dict[str, Any]], right: list[dict[str, Any]], key: str
    ) -> dict[str, list[str]]:
        before = {str(item[key]) for item in left}
        after = {str(item[key]) for item in right}
        return {"added": sorted(after - before), "removed": sorted(before - after)}
