from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from alert.models import Alert, AlertEvent, AlertRule, AlertSeverity, AlertType
from alert.ports import AlertDataSource, AlertDataUnavailableError, AlertObservation
from alert.schemas import AlertEventRead, AlertRead


@dataclass(frozen=True, slots=True)
class AlertCandidate:
    alert_type: AlertType
    title: str
    message: str
    previous_value: float | None = None
    current_value: float | None = None
    context: dict[str, object] = field(default_factory=dict)


RULES_V1 = (
    ("visibility-drop", AlertType.VISIBILITY_DROP, 10.0, AlertSeverity.CRITICAL),
    ("trend-reversal", AlertType.TREND_REVERSAL, None, AlertSeverity.WARNING),
    (
        "brand-recommendation-disappeared",
        AlertType.BRAND_RECOMMENDATION_DISAPPEARED,
        None,
        AlertSeverity.WARNING,
    ),
    (
        "authoritative-citation-disappeared",
        AlertType.AUTHORITATIVE_CITATION_DISAPPEARED,
        None,
        AlertSeverity.CRITICAL,
    ),
    (
        "critical-recommendation-appeared",
        AlertType.CRITICAL_RECOMMENDATION_APPEARED,
        None,
        AlertSeverity.CRITICAL,
    ),
    ("confidence-shock", AlertType.CONFIDENCE_SHOCK, 15.0, AlertSeverity.WARNING),
)


class AlertEngine:
    RULE_VERSION = "1.0"

    def __init__(self, db: Session, source: AlertDataSource) -> None:
        self.db = db
        self.source = source

    def evaluate(self, entity_id: UUID) -> list[AlertRead]:
        observations = self.source.history(entity_id)
        if len(observations) < 2:
            raise AlertDataUnavailableError(
                f"Entity {entity_id} requires at least two scored observations"
            )
        rules = self._rules()
        candidates = self._candidates(observations, rules)
        alerts = []
        for candidate in candidates:
            rule = rules[candidate.alert_type]
            alert = Alert(
                entity_id=entity_id,
                rule_id=rule.id,
                alert_type=candidate.alert_type,
                severity=rule.severity,
                title=candidate.title,
                message=candidate.message,
                previous_value=candidate.previous_value,
                current_value=candidate.current_value,
                context=candidate.context,
            )
            alert.events.append(
                AlertEvent(
                    event_type="DETECTED",
                    payload={"rule_code": rule.code, "rule_version": rule.version},
                )
            )
            self.db.add(alert)
            alerts.append(alert)
        self.db.commit()
        for alert in alerts:
            self.db.refresh(alert)
        return [self._read(alert) for alert in alerts]

    def history(self, entity_id: UUID) -> list[AlertRead]:
        alerts = self.db.scalars(
            select(Alert)
            .options(selectinload(Alert.events), selectinload(Alert.rule))
            .where(Alert.entity_id == entity_id)
            .order_by(Alert.detected_at.desc(), Alert.id.desc())
        ).all()
        return [self._read(alert) for alert in alerts]

    def _rules(self) -> dict[AlertType, AlertRule]:
        existing = self.db.scalars(
            select(AlertRule).where(AlertRule.version == self.RULE_VERSION)
        ).all()
        by_type = {rule.alert_type: rule for rule in existing if rule.is_active}
        known = {(rule.code, rule.version) for rule in existing}
        for code, kind, threshold, severity in RULES_V1:
            if (code, self.RULE_VERSION) not in known:
                rule = AlertRule(
                    code=code,
                    alert_type=kind,
                    threshold=threshold,
                    severity=severity,
                    version=self.RULE_VERSION,
                    is_active=True,
                )
                self.db.add(rule)
                by_type[kind] = rule
        self.db.flush()
        return by_type

    def _candidates(
        self,
        observations: list[AlertObservation],
        rules: dict[AlertType, AlertRule],
    ) -> list[AlertCandidate]:
        previous, current = observations[-2:]
        candidates: list[AlertCandidate] = []
        drop = previous.visibility - current.visibility
        visibility_rule = rules.get(AlertType.VISIBILITY_DROP)
        if visibility_rule and drop > (visibility_rule.threshold or 0):
            candidates.append(
                AlertCandidate(
                    AlertType.VISIBILITY_DROP,
                    "AI Visibility significantly decreased",
                    f"Visibility fell by {drop:.2f} points.",
                    previous.visibility,
                    current.visibility,
                )
            )
        if AlertType.TREND_REVERSAL in rules and len(observations) >= 3:
            before = self._direction(observations[-3].visibility, previous.visibility)
            after = self._direction(previous.visibility, current.visibility)
            if {before, after} == {"UP", "DOWN"}:
                candidates.append(
                    AlertCandidate(
                        AlertType.TREND_REVERSAL,
                        "Visibility trend reversed",
                        f"Trend changed from {before} to {after}.",
                        context={"previous_direction": before, "current_direction": after},
                    )
                )
        candidates.extend(
            self._set_changes(
                rules,
                AlertType.BRAND_RECOMMENDATION_DISAPPEARED,
                previous.brand_recommendations - current.brand_recommendations,
                "Brand recommendation disappeared",
                "recommendation",
            )
        )
        candidates.extend(
            self._set_changes(
                rules,
                AlertType.AUTHORITATIVE_CITATION_DISAPPEARED,
                previous.authoritative_citations - current.authoritative_citations,
                "Authoritative citation disappeared",
                "citation",
            )
        )
        candidates.extend(
            self._set_changes(
                rules,
                AlertType.CRITICAL_RECOMMENDATION_APPEARED,
                current.critical_recommendations - previous.critical_recommendations,
                "New critical recommendation",
                "recommendation",
            )
        )
        confidence_rule = rules.get(AlertType.CONFIDENCE_SHOCK)
        confidence_delta = current.confidence - previous.confidence
        if confidence_rule and abs(confidence_delta) >= (confidence_rule.threshold or 0):
            candidates.append(
                AlertCandidate(
                    AlertType.CONFIDENCE_SHOCK,
                    "Confidence score changed sharply",
                    f"Confidence changed by {confidence_delta:.2f} points.",
                    previous.confidence,
                    current.confidence,
                )
            )
        return candidates

    @staticmethod
    def _set_changes(
        rules: dict[AlertType, AlertRule],
        kind: AlertType,
        values: frozenset[str],
        title: str,
        context_key: str,
    ) -> list[AlertCandidate]:
        if kind not in rules:
            return []
        return [
            AlertCandidate(kind, title, f"{title}: {value}", context={context_key: value})
            for value in sorted(values, key=str.casefold)
        ]

    @staticmethod
    def _direction(previous: float, current: float) -> str:
        if abs(current - previous) <= 1:
            return "STABLE"
        return "UP" if current > previous else "DOWN"

    @staticmethod
    def _read(alert: Alert) -> AlertRead:
        return AlertRead(
            id=alert.id,
            entity_id=alert.entity_id,
            rule_code=alert.rule.code,
            rule_version=alert.rule.version,
            alert_type=alert.alert_type,
            severity=alert.severity,
            title=alert.title,
            message=alert.message,
            previous_value=alert.previous_value,
            current_value=alert.current_value,
            context=alert.context,
            detected_at=alert.detected_at,
            events=[
                AlertEventRead(
                    id=event.id,
                    event_type=event.event_type,
                    payload=event.payload,
                    created_at=event.created_at,
                )
                for event in sorted(alert.events, key=lambda item: item.id)
            ],
        )

