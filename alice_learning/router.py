from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from alice_learning.adapters import PublicationInfluenceSource, ResearchAliceEvidenceSource
from alice_learning.automation_adapters import build_alice_automation_service
from alice_learning.automation_schemas import (
    AutomationDashboard,
    AutomationPlanCreate,
    AutomationPlanRead,
    AutomationPlanUpdate,
    AutomationRunRead,
    RunNowRequest,
)
from alice_learning.automation_service import AliceAutomationError
from alice_learning.integration import rebuild_alice_learning
from alice_learning.repository import AliceLearningRepository
from alice_learning.schemas import (
    DashboardRead,
    ModelRead,
    ObservationRead,
    PredictionRead,
    PredictRequest,
    TrainRequest,
)
from alice_learning.service import AliceLearningError, AliceLearningService
from backend.app.database import get_db
from organization_workspace.repository import OrganizationRepository
from provider_connections.dependencies import default_organization

router = APIRouter(prefix="/alice-learning", tags=["alice-learning"])
DbSession = Annotated[Session, Depends(get_db)]


def _organization(db: Session, request: Request) -> int:
    principal = getattr(request.state, "principal", None)
    user_id = int(getattr(principal, "user_id", getattr(principal, "id", 1)))
    organization_id = default_organization(db, user_id)
    if OrganizationRepository(db).member(organization_id, user_id) is None:
        raise HTTPException(403, "Нет доступа к организации")
    return organization_id


def _user(request: Request) -> int:
    principal = getattr(request.state, "principal", None)
    return int(getattr(principal, "user_id", getattr(principal, "id", 1)))


def _service(db: Session) -> AliceLearningService:
    return AliceLearningService(
        db,
        ResearchAliceEvidenceSource(db),
        PublicationInfluenceSource(db),
        AliceLearningRepository(db),
    )


@router.post("/observations/{research_id}", response_model=list[ObservationRead])
def ingest(research_id: int, request: Request, db: DbSession):
    organization_id = _organization(db, request)
    try:
        return _service(db).ingest(organization_id, research_id)
    except LookupError as error:
        raise HTTPException(404, str(error)) from error
    except PermissionError as error:
        raise HTTPException(403, str(error)) from error


@router.post("/train", response_model=ModelRead)
def train(payload: TrainRequest, request: Request, db: DbSession):
    return _service(db).train(_organization(db, request), payload)


@router.post("/predict", response_model=PredictionRead)
def predict(payload: PredictRequest, request: Request, db: DbSession):
    try:
        return _service(db).predict(_organization(db, request), payload)
    except AliceLearningError as error:
        raise HTTPException(422, str(error)) from error


@router.get("/dashboard", response_model=DashboardRead)
def dashboard(request: Request, db: DbSession):
    return _service(db).dashboard(_organization(db, request))


@router.post("/rebuild", response_model=DashboardRead)
def rebuild(request: Request, db: DbSession):
    organization_id = _organization(db, request)
    rebuild_alice_learning(db, organization_id)
    return _service(db).dashboard(organization_id)


@router.get("/models/latest", response_model=ModelRead)
def latest_model(request: Request, db: DbSession):
    organization_id = _organization(db, request)
    item = AliceLearningRepository(db).latest_model(organization_id, "UNIVERSAL", "ru", "RU")
    if item is None:
        raise HTTPException(404, "Модель Алисы ещё не обучена")
    return item


@router.post("/automation/plans", response_model=AutomationPlanRead, status_code=201)
def create_automation_plan(payload: AutomationPlanCreate, request: Request, db: DbSession):
    try:
        return build_alice_automation_service(db).create(
            _organization(db, request), _user(request), payload
        )
    except (ValueError, LookupError) as error:
        raise HTTPException(422, str(error)) from error
    except PermissionError as error:
        raise HTTPException(403, str(error)) from error


@router.get("/automation/plans", response_model=list[AutomationPlanRead])
def list_automation_plans(request: Request, db: DbSession):
    return build_alice_automation_service(db).list(_organization(db, request))


@router.patch("/automation/plans/{plan_id}", response_model=AutomationPlanRead)
def update_automation_plan(
    plan_id: int, payload: AutomationPlanUpdate, request: Request, db: DbSession
):
    try:
        return build_alice_automation_service(db).update(
            _organization(db, request), plan_id, payload
        )
    except AliceAutomationError as error:
        raise HTTPException(404 if "не найден" in str(error) else 422, str(error)) from error
    except PermissionError as error:
        raise HTTPException(403, str(error)) from error


@router.post("/automation/plans/{plan_id}/run", response_model=AutomationRunRead)
def run_automation_plan(plan_id: int, payload: RunNowRequest, request: Request, db: DbSession):
    try:
        return build_alice_automation_service(db).run(
            _organization(db, request), plan_id, payload.kind
        )
    except AliceAutomationError as error:
        raise HTTPException(409, str(error)) from error
    except PermissionError as error:
        raise HTTPException(403, str(error)) from error


@router.get("/automation/dashboard", response_model=AutomationDashboard)
def automation_dashboard(request: Request, db: DbSession):
    return build_alice_automation_service(db).dashboard(_organization(db, request))
