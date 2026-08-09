from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from model_evaluation.schemas import CapabilityMatrixRead, EvaluationRequest, EvaluationScoreRead
from model_evaluation.service import ModelEvaluationService

router = APIRouter(prefix="/providers", tags=["model-evaluation"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/evaluations", response_model=list[EvaluationScoreRead], status_code=status.HTTP_201_CREATED
)
def evaluate_models(payload: EvaluationRequest, db: DbSession) -> list[EvaluationScoreRead]:
    try:
        return ModelEvaluationService(db).evaluate(payload)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@router.get("/capability-matrix", response_model=CapabilityMatrixRead)
def capability_matrix(db: DbSession) -> CapabilityMatrixRead:
    return ModelEvaluationService(db).matrix()
