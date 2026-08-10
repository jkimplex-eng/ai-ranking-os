from change_detection.models import ResearchChange
from change_detection.ports import ChangeSnapshotSource
from change_detection.repository import ChangeRepository
from change_detection.schemas import ResearchChangeRead
from notification_center.ports import NotificationPort


class ChangeNotFoundError(LookupError):
    pass


class ChangeDetectionService:
    METRICS = (
        "visibility_score",
        "recommendation_score",
        "citation_score",
        "coverage_score",
    )

    def __init__(
        self,
        repository: ChangeRepository,
        source: ChangeSnapshotSource,
        notifications: NotificationPort | None = None,
    ) -> None:
        self.repository = repository
        self.source = source
        self.notifications = notifications

    def detect(self, research_id: int) -> ResearchChangeRead:
        previous, current = self.source.pair(research_id)
        deltas = {
            metric: round(current.metrics[metric] - previous.metrics[metric], 4)
            if previous and metric in current.metrics and metric in previous.metrics
            else None
            for metric in self.METRICS
        }
        prior_recommendations = previous.recommendations if previous else frozenset()
        prior_sources = previous.sources if previous else frozenset()
        prior_nodes = previous.graph_nodes if previous else frozenset()
        prior_edges = previous.graph_edges if previous else frozenset()
        change = self.repository.get(research_id) or ResearchChange(research_id=research_id)
        change.previous_research_id = previous.research_id if previous else None
        change.metric_deltas = deltas
        change.new_recommendations = sorted(current.recommendations - prior_recommendations)
        change.removed_recommendations = sorted(prior_recommendations - current.recommendations)
        change.new_sources = sorted(current.sources - prior_sources)
        change.removed_sources = sorted(prior_sources - current.sources)
        change.graph_changes = {
            "added_nodes": sorted(current.graph_nodes - prior_nodes),
            "removed_nodes": sorted(prior_nodes - current.graph_nodes),
            "added_edges": sorted(current.graph_edges - prior_edges),
            "removed_edges": sorted(prior_edges - current.graph_edges),
        }
        result = ResearchChangeRead.model_validate(
            self.repository.save(change), from_attributes=True
        )
        significant = {
            metric: delta
            for metric, delta in deltas.items()
            if delta is not None and abs(delta) >= 5
        }
        if significant and self.notifications is not None:
            self.notifications.emit(
                "SIGNIFICANT_CHANGE",
                "Обнаружено значительное изменение",
                f"Метрики исследования {research_id} существенно изменились",
                resource_type="research",
                resource_id=str(research_id),
                metadata={"metric_deltas": significant},
            )
        return result

    def get(self, research_id: int) -> ResearchChangeRead:
        change = self.repository.get(research_id)
        if change is None:
            raise ChangeNotFoundError(f"Changes for research {research_id} not found")
        return ResearchChangeRead.model_validate(change, from_attributes=True)
