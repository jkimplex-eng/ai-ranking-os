from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.segmentation_source import PlatformSegmentationDataSource
from segmentation.repository import (
    SegmentCodeConflictError,
    SegmentNotFoundError,
    SqlAlchemySegmentRepository,
)
from segmentation.schemas import (
    SegmentCreate,
    SegmentEvaluationRead,
    SegmentPage,
    SegmentRead,
    SegmentTypeRead,
    SegmentUpdate,
)
from segmentation.service import InactiveSegmentError, SegmentService

router = APIRouter(prefix="/segments", tags=["segmentation"])
DbSession = Annotated[Session, Depends(get_db)]


def get_segment_service(db: DbSession) -> SegmentService:
    return SegmentService(PlatformSegmentationDataSource(db), SqlAlchemySegmentRepository(db))


Service = Annotated[SegmentService, Depends(get_segment_service)]


@router.get("/types", response_model=list[SegmentTypeRead])
def segment_types() -> list[SegmentTypeRead]:
    return SegmentService.types()


@router.post("", response_model=SegmentRead, status_code=status.HTTP_201_CREATED)
def create_segment(payload: SegmentCreate, service: Service) -> SegmentRead:
    try:
        return service.create(payload)
    except SegmentCodeConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.get("", response_model=SegmentPage)
def list_segments(
    service: Service,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> SegmentPage:
    return service.list(page, page_size)


@router.get("/{id}", response_model=SegmentRead)
def get_segment(
    segment_id: Annotated[int, Path(alias="id", ge=1)], service: Service
) -> SegmentRead:
    try:
        return service.get(segment_id)
    except SegmentNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.patch("/{id}", response_model=SegmentRead)
def update_segment(
    segment_id: Annotated[int, Path(alias="id", ge=1)],
    payload: SegmentUpdate,
    service: Service,
) -> SegmentRead:
    try:
        return service.update(segment_id, payload)
    except SegmentNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_segment(
    segment_id: Annotated[int, Path(alias="id", ge=1)], service: Service
) -> Response:
    try:
        service.delete(segment_id)
    except SegmentNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{id}/evaluate", response_model=SegmentEvaluationRead)
def evaluate_segment(
    segment_id: Annotated[int, Path(alias="id", ge=1)], service: Service
) -> SegmentEvaluationRead:
    try:
        return service.evaluate(segment_id)
    except SegmentNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except InactiveSegmentError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.get("/{id}/memberships", response_model=SegmentEvaluationRead)
def get_segment_memberships(
    segment_id: Annotated[int, Path(alias="id", ge=1)], service: Service
) -> SegmentEvaluationRead:
    try:
        return service.latest_memberships(segment_id)
    except (SegmentNotFoundError, LookupError) as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
