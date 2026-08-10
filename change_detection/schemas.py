from datetime import datetime

from pydantic import BaseModel


class ResearchChangeRead(BaseModel):
    id: int
    research_id: int
    previous_research_id: int | None
    metric_deltas: dict[str, float | None]
    new_recommendations: list[str]
    removed_recommendations: list[str]
    new_sources: list[str]
    removed_sources: list[str]
    graph_changes: dict[str, list[str] | int]
    algorithm_version: str
    created_at: datetime
