from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from graph.engine import GraphSnapshotNotFoundError
from relationship_discovery.adapters import build_relationship_discovery_engine
from relationship_discovery.engine import (
    RelationshipCandidateNotFoundError,
    RelationshipDecisionConflictError,
)
from relationship_discovery.models import RelationshipStatus
from relationship_discovery.schemas import (
    DiscoveryRunRequest,
    DiscoveryRunResult,
    RelationshipCandidateRead,
    RelationshipDecisionRequest,
)

router = APIRouter(prefix="/relationship-discovery", tags=["relationship-discovery"])
DbSession = Annotated[Session, Depends(get_db)]
Offset = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=500)]
CandidateStatus = Annotated[RelationshipStatus | None, Query(alias="status")]


@router.post("/run", response_model=DiscoveryRunResult)
def run_discovery(payload: DiscoveryRunRequest, db: DbSession) -> DiscoveryRunResult:
    try:
        return build_relationship_discovery_engine(db).run(payload.snapshot_id)
    except GraphSnapshotNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/candidates", response_model=list[RelationshipCandidateRead])
def list_candidates(
    db: DbSession,
    candidate_status: CandidateStatus = None,
    offset: Offset = 0,
    limit: Limit = 100,
) -> list[RelationshipCandidateRead]:
    return build_relationship_discovery_engine(db).candidates(
        status=candidate_status, offset=offset, limit=limit
    )


@router.post("/{candidate_id}/approve", response_model=RelationshipCandidateRead)
def approve_candidate(
    candidate_id: int, payload: RelationshipDecisionRequest, db: DbSession
) -> RelationshipCandidateRead:
    try:
        return build_relationship_discovery_engine(db).approve(candidate_id, payload)
    except RelationshipCandidateNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except RelationshipDecisionConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.post("/{candidate_id}/reject", response_model=RelationshipCandidateRead)
def reject_candidate(
    candidate_id: int, payload: RelationshipDecisionRequest, db: DbSession
) -> RelationshipCandidateRead:
    try:
        return build_relationship_discovery_engine(db).reject(candidate_id, payload)
    except RelationshipCandidateNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except RelationshipDecisionConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
