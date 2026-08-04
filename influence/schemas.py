from datetime import datetime

from pydantic import BaseModel, Field


class EntityInfluenceRead(BaseModel):
    entity_id: str
    name: str
    node_type: str
    degree: float = Field(ge=0, le=1)
    weighted_degree: float = Field(ge=0, le=1)
    pagerank: float = Field(ge=0, le=1)
    betweenness: float = Field(ge=0, le=1)
    closeness: float = Field(ge=0, le=1)
    influence_score: float = Field(ge=0, le=100)
    rank: int = Field(ge=1)


class InfluenceSnapshotRead(BaseModel):
    id: int
    graph_snapshot_id: int
    algorithm_version: str
    node_count: int = Field(ge=0)
    edge_count: int = Field(ge=0)
    calculated_at: datetime
    entities: list[EntityInfluenceRead]
