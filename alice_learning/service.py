from __future__ import annotations

import math
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from alice_learning.models import AliceModelSnapshot, AliceObservation, AlicePrediction
from alice_learning.ports import AliceEvidencePort, ConfirmedInfluencePort
from alice_learning.repository import AliceLearningRepository
from alice_learning.schemas import (
    FEATURE_NAMES,
    DashboardRead,
    ModelRead,
    PredictionRead,
    PredictRequest,
    TrainRequest,
)

ALGORITHM_VERSION = "1.0"
FEATURE_VERSION = "1.0"
MIN_SAMPLES = 12
MIN_CLASS_SAMPLES = 3

FEATURE_ACTIONS = {
    "search_visibility": "Улучшить позиции целевой страницы по этому и смежным запросам.",
    "landing_page_match": "Создать отдельную посадочную страницу под пользовательскую задачу.",
    "independent_source_support": (
        "Получить проверяемые независимые публикации с характеристиками бренда."
    ),
    "content_completeness": (
        "Раскрыть характеристики, сценарии, ограничения и сравнения без общих фраз."
    ),
    "expertise_evidence": "Добавить автора, квалификацию, методику и первичные доказательства.",
    "freshness": "Обновить факты, дату, цену, наличие и сведения о продукте.",
    "availability_clarity": "Явно указать цену, наличие, регион и условия покупки.",
    "technical_health": "Устранить проблемы индексирования и подтвердить состояние в Вебмастере.",
}


class AliceLearningError(ValueError):
    pass


class AliceLearningService:
    def __init__(
        self,
        db: Session,
        evidence: AliceEvidencePort,
        confirmed_influence: ConfirmedInfluencePort,
        repository: AliceLearningRepository | None = None,
    ) -> None:
        self.db = db
        self.evidence = evidence
        self.confirmed_influence = confirmed_influence
        self.repository = repository or AliceLearningRepository(db)

    def ingest(self, organization_id: int, research_id: int) -> list[AliceObservation]:
        saved = []
        for record in self.evidence.records(organization_id, research_id):
            item = self.repository.observation(record.response_id, FEATURE_VERSION)
            if item is None:
                item = AliceObservation(
                    organization_id=organization_id,
                    feature_version=FEATURE_VERSION,
                    **record.__dict__,
                )
                self.db.add(item)
            else:
                for key, value in record.__dict__.items():
                    setattr(item, key, value)
            saved.append(item)
        self.db.commit()
        for item in saved:
            self.db.refresh(item)
        return saved

    def train(self, organization_id: int, request: TrainRequest) -> AliceModelSnapshot:
        rows = self.repository.observations(
            organization_id,
            category=request.category,
            language=request.language,
            region=request.region,
        )
        positives = sum(item.recommended for item in rows)
        negatives = len(rows) - positives
        enough = (
            len(rows) >= MIN_SAMPLES
            and positives >= MIN_CLASS_SAMPLES
            and negatives >= MIN_CLASS_SAMPLES
        )
        prior = (positives + 1) / (len(rows) + 2)
        intercept = self._logit(prior)
        coefficients = {name: 0.0 for name in FEATURE_NAMES}
        if enough:
            intercept, coefficients = self._fit(rows, intercept)
        probabilities = [self._probability(intercept, coefficients, item.features) for item in rows]
        brier = (
            sum(
                (probability - float(item.recommended)) ** 2
                for probability, item in zip(probabilities, rows, strict=True)
            )
            / len(rows)
            if rows
            else None
        )
        measured_counts = {
            feature: sum(
                item.feature_evidence.get(feature, {}).get("status") == "MEASURED" for item in rows
            )
            for feature in FEATURE_NAMES
        }
        limitations = [
            (
                "Модель воспроизводит наблюдаемое поведение, но не раскрывает "
                "внутренний алгоритм Алисы."
            ),
            (
                "Коэффициенты являются ассоциациями; причинный эффект "
                "подтверждается отдельно экспериментами."
            ),
            "Проверка качества рассчитана на обучающей выборке до накопления достаточного holdout.",
        ]
        if not enough:
            limitations.insert(
                0,
                f"Недостаточно данных: нужно минимум {MIN_SAMPLES} наблюдений, включая "
                f"не менее {MIN_CLASS_SAMPLES} рекомендаций и {MIN_CLASS_SAMPLES} отказов.",
            )
        model = AliceModelSnapshot(
            organization_id=organization_id,
            category=request.category,
            language=request.language,
            region=request.region,
            status="READY" if enough else "INSUFFICIENT_SAMPLE",
            model_type="REGULARIZED_LOGISTIC_SURROGATE_V1",
            intercept=round(intercept, 8),
            coefficients={key: round(value, 8) for key, value in coefficients.items()},
            feature_statistics={
                "measured_counts": measured_counts,
                "neutral_imputation": 0.5,
                "feature_version": FEATURE_VERSION,
            },
            sample_size=len(rows),
            positive_samples=positives,
            negative_samples=negatives,
            validation={
                "method": "IN_SAMPLE_DIAGNOSTIC",
                "brier_score": round(brier, 6) if brier is not None else None,
                "smoothed_baseline_probability": round(prior, 6),
            },
            limitations=limitations,
            algorithm_version=ALGORITHM_VERSION,
            trained_at=datetime.now(UTC),
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return model

    def predict(self, organization_id: int, request: PredictRequest) -> AlicePrediction:
        model = self.repository.latest_model(
            organization_id, request.category, request.language, request.region
        )
        if model is None:
            raise AliceLearningError("Сначала загрузите наблюдения и обучите модель Алисы")
        probability = self._probability(model.intercept, model.coefficients, request.features)
        balance = (
            min(model.positive_samples, model.negative_samples)
            / max(model.positive_samples, model.negative_samples)
            if model.positive_samples and model.negative_samples
            else 0.0
        )
        confidence = min(0.95, model.sample_size / 60) * balance
        if model.status != "READY":
            confidence = min(confidence, 0.15)
        counterfactuals = []
        if model.status == "READY":
            for feature in FEATURE_NAMES:
                current = float(request.features[feature])
                if current >= 0.999 or model.coefficients.get(feature, 0) <= 0:
                    continue
                changed = dict(request.features)
                changed[feature] = 1.0
                predicted = self._probability(model.intercept, model.coefficients, changed)
                counterfactuals.append(
                    {
                        "feature": feature,
                        "current_value": current,
                        "target_value": 1.0,
                        "current_probability": round(probability, 6),
                        "predicted_probability": round(predicted, 6),
                        "predicted_delta": round(predicted - probability, 6),
                        "action": FEATURE_ACTIONS[feature],
                        "evidence_level": "MODEL_ASSOCIATION",
                    }
                )
        counterfactuals.sort(key=lambda item: item["predicted_delta"], reverse=True)
        confirmed = self.confirmed_influence.factors(
            category=request.category, language=request.language, region=request.region
        )
        prediction = AlicePrediction(
            organization_id=organization_id,
            model_id=model.id,
            brand=request.brand,
            query=request.query,
            features=request.features,
            probability=round(probability, 6),
            confidence=round(confidence, 6),
            counterfactuals=counterfactuals,
            explanation={
                "meaning": "Вероятность рекомендации внутри измеренной выборки Алисы/YandexGPT.",
                "formula": "sigmoid(intercept + Σ coefficient × feature)",
                "coefficients": model.coefficients,
                "sample": {
                    "total": model.sample_size,
                    "recommended": model.positive_samples,
                    "not_recommended": model.negative_samples,
                },
                "confirmed_publication_factors": confirmed[:10],
                "limitations": model.limitations,
            },
            evidence_status="MODELLED" if model.status == "READY" else "INSUFFICIENT_SAMPLE",
            algorithm_version=ALGORITHM_VERSION,
        )
        self.db.add(prediction)
        self.db.commit()
        self.db.refresh(prediction)
        return prediction

    def dashboard(self, organization_id: int, brand: str | None = None) -> DashboardRead:
        rows = self.repository.observations(organization_id)
        selected_brand = brand or (rows[-1].brand if rows else None)
        brand_rows = (
            [item for item in rows if item.brand.casefold() == selected_brand.casefold()]
            if selected_brand
            else []
        )
        model = self.repository.latest_model(organization_id, "UNIVERSAL", "ru", "RU")
        factors = []
        if model is not None:
            factors = [
                {
                    "feature": feature,
                    "coefficient": coefficient,
                    "direction": "POSITIVE"
                    if coefficient > 0
                    else "NEGATIVE"
                    if coefficient < 0
                    else "UNKNOWN",
                    "evidence_level": "MODEL_ASSOCIATION",
                }
                for feature, coefficient in sorted(
                    model.coefficients.items(), key=lambda item: abs(item[1]), reverse=True
                )
            ]
        confirmed = self.confirmed_influence.factors(
            category="UNIVERSAL", language="ru", region="RU"
        )
        baseline_probability = None
        actions = []
        if model is not None and model.status == "READY" and brand_rows:
            average_features = {
                feature: sum(float(item.features.get(feature, 0.5)) for item in brand_rows)
                / len(brand_rows)
                for feature in FEATURE_NAMES
            }
            baseline_probability = self._probability(
                model.intercept, model.coefficients, average_features
            )
            for feature in FEATURE_NAMES:
                current = average_features[feature]
                if current >= 0.999 or model.coefficients.get(feature, 0) <= 0:
                    continue
                changed = dict(average_features)
                changed[feature] = 1.0
                predicted = self._probability(model.intercept, model.coefficients, changed)
                actions.append(
                    {
                        "feature": feature,
                        "current_value": round(current, 6),
                        "target_value": 1.0,
                        "current_probability": round(baseline_probability, 6),
                        "predicted_probability": round(predicted, 6),
                        "predicted_delta": round(predicted - baseline_probability, 6),
                        "action": FEATURE_ACTIONS[feature],
                        "evidence_level": "MODEL_ASSOCIATION",
                    }
                )
            actions.sort(key=lambda item: item["predicted_delta"], reverse=True)
        return DashboardRead(
            status=model.status if model else "NOT_TRAINED",
            brand=selected_brand,
            observation_count=len(brand_rows),
            recommendation_count=sum(item.recommended for item in brand_rows),
            baseline_probability=(
                round(baseline_probability, 6) if baseline_probability is not None else None
            ),
            model=ModelRead.model_validate(model) if model else None,
            top_factors=factors
            + [
                {**item, "evidence_level": item.get("evidence_level", "EXPERIMENT")}
                for item in confirmed[:10]
            ],
            recommended_actions=actions,
            recent_predictions=[
                PredictionRead.model_validate(item)
                for item in self.repository.predictions(organization_id)
            ],
            limitations=[
                (
                    "Точный внутренний алгоритм Алисы закрыт; система обучает "
                    "проверяемую локальную модель."
                ),
                "Прогноз не является гарантией рекомендации.",
                (
                    "Причинными считаются только отдельно зарегистрированные "
                    "контролируемые эксперименты."
                ),
            ],
        )

    @staticmethod
    def _fit(rows: list[AliceObservation], intercept: float) -> tuple[float, dict[str, float]]:
        coefficients = {name: 0.0 for name in FEATURE_NAMES}
        learning_rate = 0.15
        regularization = 0.2
        size = len(rows)
        for _ in range(800):
            intercept_gradient = 0.0
            gradients = {name: 0.0 for name in FEATURE_NAMES}
            for row in rows:
                probability = AliceLearningService._probability(
                    intercept, coefficients, row.features
                )
                error = probability - float(row.recommended)
                intercept_gradient += error
                for feature in FEATURE_NAMES:
                    gradients[feature] += error * float(row.features.get(feature, 0.5))
            intercept -= learning_rate * intercept_gradient / size
            for feature in FEATURE_NAMES:
                gradient = gradients[feature] / size + regularization * coefficients[feature] / size
                coefficients[feature] -= learning_rate * gradient
        return intercept, coefficients

    @staticmethod
    def _probability(intercept: float, coefficients: dict, features: dict) -> float:
        score = intercept + sum(
            float(coefficients.get(name, 0)) * float(features.get(name, 0.5))
            for name in FEATURE_NAMES
        )
        score = max(-30.0, min(30.0, score))
        return 1 / (1 + math.exp(-score))

    @staticmethod
    def _logit(probability: float) -> float:
        probability = max(1e-6, min(1 - 1e-6, probability))
        return math.log(probability / (1 - probability))
