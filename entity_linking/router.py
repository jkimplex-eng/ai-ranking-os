from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from entity_linking.engine import (
    CanonicalEntityNotFoundError,
    LinkCandidateNotFoundError,
    LinkDecisionConflictError,
)
from entity_linking.graph_adapter import build_entity_linking_engine
from entity_linking.models import LinkStatus
from entity_linking.schemas import (
    CandidateDecisionRequest,
    LinkCandidateRead,
    LinkingRunRequest,
    LinkingRunResult,
)
from graph.engine import GraphSnapshotNotFoundError

router = APIRouter(prefix="/entity-linking", tags=["entity-linking"])
DbSession = Annotated[Session, Depends(get_db)]
Offset = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=500)]
CandidateStatus = Annotated[LinkStatus | None, Query(alias="status")]


@router.post("/run", response_model=LinkingRunResult)
def run_entity_linking(payload: LinkingRunRequest, db: DbSession) -> LinkingRunResult:
    try:
        return build_entity_linking_engine(db).run(payload.snapshot_id)
    except GraphSnapshotNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/candidates", response_model=list[LinkCandidateRead])
def list_link_candidates(
    db: DbSession,
    candidate_status: CandidateStatus = None,
    offset: Offset = 0,
    limit: Limit = 100,
) -> list[LinkCandidateRead]:
    return build_entity_linking_engine(db).candidates(
        status=candidate_status, offset=offset, limit=limit
    )


@router.post("/{candidate_id}/approve", response_model=LinkCandidateRead)
def approve_link_candidate(
    candidate_id: int, payload: CandidateDecisionRequest, db: DbSession
) -> LinkCandidateRead:
    try:
        return build_entity_linking_engine(db).approve(candidate_id, payload)
    except (LinkCandidateNotFoundError, CanonicalEntityNotFoundError) as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except LinkDecisionConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.post("/{candidate_id}/reject", response_model=LinkCandidateRead)
def reject_link_candidate(
    candidate_id: int, payload: CandidateDecisionRequest, db: DbSession
) -> LinkCandidateRead:
    try:
        return build_entity_linking_engine(db).reject(candidate_id, payload)
    except LinkCandidateNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except LinkDecisionConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
