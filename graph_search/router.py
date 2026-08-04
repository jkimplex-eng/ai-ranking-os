from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from graph.engine import GraphSnapshotNotFoundError
from graph_search.engine import GraphNodeNotFoundError, GraphSearchEngine
from graph_search.graph_adapter import PublicGraphSearchAdapter
from graph_search.schemas import (
    GraphNeighborsResult,
    GraphSearchNodeRead,
    GraphSearchResult,
    TraversalDirection,
)

router = APIRouter(prefix="/graph", tags=["graph-search"])
DbSession = Annotated[Session, Depends(get_db)]


def _engine(db: Session) -> GraphSearchEngine:
    return GraphSearchEngine(PublicGraphSearchAdapter(db))


@router.get("/search", response_model=GraphSearchResult)
def search_graph(
    db: DbSession,
    q: Annotated[str | None, Query(min_length=1, max_length=500)] = None,
    node_type: Annotated[list[str] | None, Query()] = None,
    relationship_type: Annotated[list[str] | None, Query()] = None,
    min_confidence: Annotated[float, Query(ge=0, le=1)] = 0,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> GraphSearchResult:
    try:
        return _engine(db).search(
            query=q,
            node_types=set(node_type or []),
            relationship_types=set(relationship_type or []),
            min_confidence=min_confidence,
            page=page,
            page_size=page_size,
        )
    except GraphSnapshotNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/node/{id}", response_model=GraphSearchNodeRead)
def get_graph_node(
    node_id: Annotated[str, Path(alias="id", min_length=1, max_length=300)], db: DbSession
) -> GraphSearchNodeRead:
    try:
        return _engine(db).get_node(node_id)
    except (GraphSnapshotNotFoundError, GraphNodeNotFoundError) as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/neighbors/{id}", response_model=GraphNeighborsResult)
def get_graph_neighbors(
    node_id: Annotated[str, Path(alias="id", min_length=1, max_length=300)],
    db: DbSession,
    depth: Annotated[int, Query(ge=1, le=5)] = 1,
    direction: TraversalDirection = TraversalDirection.BOTH,
    node_type: Annotated[list[str] | None, Query()] = None,
    relationship_type: Annotated[list[str] | None, Query()] = None,
    min_confidence: Annotated[float, Query(ge=0, le=1)] = 0,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> GraphNeighborsResult:
    try:
        return _engine(db).neighbors(
            node_id,
            depth=depth,
            direction=direction,
            node_types=set(node_type or []),
            relationship_types=set(relationship_type or []),
            min_confidence=min_confidence,
            page=page,
            page_size=page_size,
        )
    except (GraphSnapshotNotFoundError, GraphNodeNotFoundError) as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
