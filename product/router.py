from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from change_detection.dependencies import build_change_detection
from notification_center.dependencies import build_notification_service
from product.brand_intelligence import BrandDiscoveryError, brand_intelligence_engine
from product.repository import (
    ProductConflictError,
    ProductNotFoundError,
    PromptRepository,
    ResearchTemplateRepository,
)
from product.schemas import (
    BrandProfileRead,
    BrandProfileRequest,
    PromptCreate,
    PromptRead,
    PromptUpdate,
    ResearchTemplateCreate,
    ResearchTemplateRead,
    ResearchTemplateUpdate,
    WizardRequest,
    WizardReview,
    WizardRunResult,
)
from product.service import FinalReportService, ProductPipeline, WizardValidationError
from research.models import ResearchStatus
from research.schemas import ResearchRead

router = APIRouter(tags=["product"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("/research/wizard/brand-profile", response_model=BrandProfileRead)
def build_brand_profile(payload: BrandProfileRequest) -> BrandProfileRead:
    try:
        return BrandProfileRead.model_validate(
            brand_intelligence_engine.analyze(brand=payload.brand, website_url=payload.website_url)
        )
    except BrandDiscoveryError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@router.get("/prompts", response_model=list[PromptRead])
def list_prompts(
    db: DbSession,
    category: str | None = Query(default=None),
    language: str | None = Query(default=None),
) -> list[PromptRead]:
    return PromptRepository(db).list(category=category, language=language)


@router.post("/prompts", response_model=PromptRead, status_code=status.HTTP_201_CREATED)
def create_prompt(payload: PromptCreate, db: DbSession) -> PromptRead:
    try:
        return PromptRepository(db).create(payload)
    except ProductConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.get("/prompts/{prompt_id}", response_model=PromptRead)
def get_prompt(prompt_id: int, db: DbSession) -> PromptRead:
    try:
        return PromptRepository(db).get(prompt_id)
    except ProductNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.patch("/prompts/{prompt_id}", response_model=PromptRead)
def update_prompt(prompt_id: int, payload: PromptUpdate, db: DbSession) -> PromptRead:
    try:
        return PromptRepository(db).update(prompt_id, payload)
    except ProductNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post(
    "/prompts/{prompt_id}/clone", response_model=PromptRead, status_code=status.HTTP_201_CREATED
)
def clone_prompt(prompt_id: int, db: DbSession) -> PromptRead:
    try:
        return PromptRepository(db).clone(prompt_id)
    except ProductNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/prompts/{prompt_id}/activate", response_model=PromptRead)
def activate_prompt(prompt_id: int, db: DbSession) -> PromptRead:
    try:
        return PromptRepository(db).activate(prompt_id)
    except ProductNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/prompts/{prompt_id}/deprecate", response_model=PromptRead)
def deprecate_prompt(prompt_id: int, db: DbSession) -> PromptRead:
    try:
        return PromptRepository(db).deprecate(prompt_id)
    except ProductNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/research/templates", response_model=list[ResearchTemplateRead])
def list_research_templates(db: DbSession) -> list[ResearchTemplateRead]:
    return ResearchTemplateRepository(db).list()


@router.get("/research/templates/{code}", response_model=ResearchTemplateRead)
def get_research_template(code: str, db: DbSession) -> ResearchTemplateRead:
    try:
        return ResearchTemplateRepository(db).get(code)
    except ProductNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post(
    "/research/templates",
    response_model=ResearchTemplateRead,
    status_code=status.HTTP_201_CREATED,
)
def create_research_template(
    payload: ResearchTemplateCreate, db: DbSession
) -> ResearchTemplateRead:
    try:
        return ResearchTemplateRepository(db).create(payload)
    except ProductConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.patch("/research/templates/{code}", response_model=ResearchTemplateRead)
def update_research_template(
    code: str, payload: ResearchTemplateUpdate, db: DbSession
) -> ResearchTemplateRead:
    try:
        return ResearchTemplateRepository(db).update(code, payload)
    except ProductNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post(
    "/research/templates/{code}/clone",
    response_model=ResearchTemplateRead,
    status_code=status.HTTP_201_CREATED,
)
def clone_research_template(code: str, db: DbSession) -> ResearchTemplateRead:
    try:
        return ResearchTemplateRepository(db).clone(code)
    except ProductNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/research/wizard/review", response_model=WizardReview)
def review_wizard(payload: WizardRequest, db: DbSession) -> WizardReview:
    try:
        return ProductPipeline(db).review(payload)
    except (ProductNotFoundError, WizardValidationError) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@router.post(
    "/research/wizard/run", response_model=WizardRunResult, status_code=status.HTTP_201_CREATED
)
def run_wizard(payload: WizardRequest, db: DbSession) -> WizardRunResult:
    try:
        notifications = build_notification_service(db)
        research = ProductPipeline(
            db,
            build_change_detection(db, notifications),
            notifications,
        ).run(payload)
        if research.status != ResearchStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Research {research.id} failed; no report was generated",
            )
        report = FinalReportService(db).get(research.id)
        return WizardRunResult(
            research=ResearchRead.model_validate(research),
            report_url=f"/research/{research.id}/final-report",
            report=report,
        )
    except (ProductNotFoundError, WizardValidationError) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@router.get("/research/{research_id}/final-report", response_model=dict)
def final_report(research_id: int, db: DbSession) -> dict:
    try:
        return FinalReportService(db).get(research_id)
    except (ProductNotFoundError, LookupError) as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
