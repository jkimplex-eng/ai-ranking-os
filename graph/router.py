from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from graph.engine import GraphSnapshotNotFoundError
from graph.extraction_adapter import build_graph_engine
from graph.ports import GraphBuildContext
from graph.schemas import GraphBuildRequest, GraphSnapshotRead

router = APIRouter(prefix="/graph", tags=["graph"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("/build", response_model=GraphSnapshotRead, status_code=status.HTTP_201_CREATED)
def build_graph(payload: GraphBuildRequest, db: DbSession) -> GraphSnapshotRead:
    return build_graph_engine(db).build(
        GraphBuildContext(source_ids=tuple(payload.source_ids), metadata=payload.metadata)
    )


@router.get("", response_model=GraphSnapshotRead)
def get_latest_graph(db: DbSession) -> GraphSnapshotRead:
    try:
        return build_graph_engine(db).latest()
    except GraphSnapshotNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/{snapshot_id}", response_model=GraphSnapshotRead)
def get_graph_snapshot(snapshot_id: int, db: DbSession) -> GraphSnapshotRead:
    try:
        return build_graph_engine(db).get(snapshot_id)
    except GraphSnapshotNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

