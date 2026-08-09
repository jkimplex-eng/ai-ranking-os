from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from model_benchmark.schemas import ModelBenchmarkRead, ModelBenchmarkRequest
from model_benchmark.service import ModelBenchmarkService

router = APIRouter(prefix="/providers/benchmarks", tags=["model-benchmarks"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=ModelBenchmarkRead, status_code=status.HTTP_201_CREATED)
def run_benchmark(payload: ModelBenchmarkRequest, db: DbSession) -> ModelBenchmarkRead:
    return ModelBenchmarkService(db).run(payload)


@router.get("/{run_id}", response_model=ModelBenchmarkRead)
def get_benchmark(run_id: int, db: DbSession) -> ModelBenchmarkRead:
    try:
        return ModelBenchmarkService(db).get(run_id)
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
