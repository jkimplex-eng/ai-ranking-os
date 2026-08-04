from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from graph.engine import GraphSnapshotNotFoundError
from influence.engine import EntityInfluenceNotFoundError, InfluenceEngine
from influence.graph_adapter import PublicGraphAdapter
from influence.schemas import EntityInfluenceRead, InfluenceSnapshotRead

router = APIRouter(prefix="/graph/influence", tags=["influence"])
DbSession = Annotated[Session, Depends(get_db)]


def _engine(db: Session) -> InfluenceEngine:
    return InfluenceEngine(db, PublicGraphAdapter(db))


@router.get("", response_model=InfluenceSnapshotRead)
def get_graph_influence(db: DbSession) -> InfluenceSnapshotRead:
    try:
        return _engine(db).calculate()
    except GraphSnapshotNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/{entity_id}", response_model=EntityInfluenceRead)
def get_entity_influence(entity_id: str, db: DbSession) -> EntityInfluenceRead:
    try:
        return _engine(db).get_entity(entity_id)
    except (GraphSnapshotNotFoundError, EntityInfluenceNotFoundError) as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
