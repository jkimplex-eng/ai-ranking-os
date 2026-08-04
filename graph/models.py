from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


class GraphSnapshot(Base):
    __tablename__ = "graph_snapshots"
    __table_args__ = (Index("ix_graph_snapshots_created", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    structure_version: Mapped[str] = mapped_column(String(50), nullable=False)
    node_count: Mapped[int] = mapped_column(Integer, nullable=False)
    edge_count: Mapped[int] = mapped_column(Integer, nullable=False)
    build_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    nodes: Mapped[list["GraphNode"]] = relationship(
        back_populates="snapshot", cascade="all, delete-orphan"
    )
    edges: Mapped[list["GraphEdge"]] = relationship(
        back_populates="snapshot", cascade="all, delete-orphan"
    )


class GraphNode(Base):
    __tablename__ = "graph_nodes"
    __table_args__ = (
        Index("uq_graph_nodes_snapshot_external", "snapshot_id", "external_id", unique=True),
        Index("ix_graph_nodes_snapshot_type", "snapshot_id", "node_type"),
        Index("ix_graph_nodes_snapshot_name", "snapshot_id", "name"),
        Index("ix_graph_nodes_snapshot_canonical", "snapshot_id", "canonical_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("graph_snapshots.id", ondelete="CASCADE"), nullable=False
    )
    external_id: Mapped[str] = mapped_column(String(300), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(500), nullable=False)
    node_type: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False)
    aliases: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    properties: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    snapshot: Mapped[GraphSnapshot] = relationship(back_populates="nodes")
    outgoing_edges: Mapped[list["GraphEdge"]] = relationship(
        foreign_keys="GraphEdge.source_node_id", back_populates="source_node"
    )
    incoming_edges: Mapped[list["GraphEdge"]] = relationship(
        foreign_keys="GraphEdge.target_node_id", back_populates="target_node"
    )


class GraphEdge(Base):
    __tablename__ = "graph_edges"
    __table_args__ = (
        Index("ix_graph_edges_snapshot_type", "snapshot_id", "edge_type"),
        Index("ix_graph_edges_snapshot_target", "snapshot_id", "target_node_id"),
        Index(
            "uq_graph_edges_snapshot_nodes_type",
            "snapshot_id",
            "source_node_id",
            "target_node_id",
            "edge_type",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("graph_snapshots.id", ondelete="CASCADE"), nullable=False
    )
    source_node_id: Mapped[int] = mapped_column(
        ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False
    )
    target_node_id: Mapped[int] = mapped_column(
        ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False
    )
    edge_type: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False)
    properties: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    snapshot: Mapped[GraphSnapshot] = relationship(back_populates="edges")
    source_node: Mapped[GraphNode] = relationship(
        foreign_keys=[source_node_id], back_populates="outgoing_edges"
    )
    target_node: Mapped[GraphNode] = relationship(
        foreign_keys=[target_node_id], back_populates="incoming_edges"
    )
