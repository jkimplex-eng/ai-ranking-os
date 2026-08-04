from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


class InfluenceSnapshot(Base):
    __tablename__ = "influence_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "graph_snapshot_id", "algorithm_version", name="uq_influence_snapshot_graph_version"
        ),
        Index("ix_influence_snapshots_calculated", "calculated_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    graph_snapshot_id: Mapped[int] = mapped_column(Integer, nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(50), nullable=False)
    node_count: Mapped[int] = mapped_column(Integer, nullable=False)
    edge_count: Mapped[int] = mapped_column(Integer, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    entities: Mapped[list["EntityInfluence"]] = relationship(
        back_populates="snapshot", cascade="all, delete-orphan"
    )


class EntityInfluence(Base):
    __tablename__ = "entity_influence"
    __table_args__ = (
        UniqueConstraint("snapshot_id", "entity_id", name="uq_entity_influence_snapshot_entity"),
        Index("ix_entity_influence_snapshot_rank", "snapshot_id", "rank"),
        Index("ix_entity_influence_entity", "entity_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("influence_snapshots.id", ondelete="CASCADE"), nullable=False
    )
    entity_id: Mapped[str] = mapped_column(String(300), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    node_type: Mapped[str] = mapped_column(String(100), nullable=False)
    degree: Mapped[float] = mapped_column(nullable=False)
    weighted_degree: Mapped[float] = mapped_column(nullable=False)
    pagerank: Mapped[float] = mapped_column(nullable=False)
    betweenness: Mapped[float] = mapped_column(nullable=False)
    closeness: Mapped[float] = mapped_column(nullable=False)
    influence_score: Mapped[float] = mapped_column(nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[InfluenceSnapshot] = relationship(back_populates="entities")
