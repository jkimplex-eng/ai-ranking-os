from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.llm_router.cost_optimizer import current_costs
from backend.app.llm_router.metrics import ROUTER_ERRORS
from backend.app.llm_router.models import (
    CircuitBreakerRecord,
    RegisteredModel,
    RouterHistory,
    RoutingPolicy,
)
from backend.app.llm_router.pipeline import RoutingError, route
from backend.app.llm_router.registry import (
    ModelRepository,
    PolicyRepository,
    RegistryConflictError,
    RegistryNotFoundError,
    ensure_seeded,
)
from backend.app.llm_router.schemas import (
    HistoryList,
    HistoryRead,
    ModelCreate,
    ModelList,
    ModelRead,
    ModelUpdate,
    PolicyRead,
    PolicyUpdate,
    RouteRequest,
    RouteResponse,
    RouterStatus,
)
from query_executor.schemas import ExecutionPlan

router = APIRouter(prefix="/router", tags=["llm-router"])
DbSession = Annotated[Session, Depends(get_db)]


def _registry_error(error: Exception) -> HTTPException:
    code = (
        status.HTTP_404_NOT_FOUND
        if isinstance(error, RegistryNotFoundError)
        else status.HTTP_409_CONFLICT
    )
    return HTTPException(status_code=code, detail=str(error))


@router.post("/route", response_model=RouteResponse, status_code=status.HTTP_201_CREATED)
def route_query(payload: RouteRequest, db: DbSession) -> RouteResponse:
    try:
        return route(db, payload)
    except (RegistryNotFoundError, RoutingError, ValueError) as error:
        ROUTER_ERRORS.labels(error_type=type(error).__name__).inc()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.post("/plan", response_model=ExecutionPlan, status_code=status.HTTP_201_CREATED)
def build_plan(payload: RouteRequest, db: DbSession) -> ExecutionPlan:
    try:
        return route(db, payload).plan
    except (RegistryNotFoundError, RoutingError, ValueError) as error:
        ROUTER_ERRORS.labels(error_type=type(error).__name__).inc()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.get("/models", response_model=ModelList)
def list_models(
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    provider: str | None = None,
    model_status: Annotated[str | None, Query(alias="status")] = None,
    capability: str | None = None,
    search: str | None = None,
) -> ModelList:
    ensure_seeded(db)
    items, total = ModelRepository(db).list(
        page=page,
        page_size=page_size,
        provider=provider,
        status=model_status,
        capability=capability,
        search=search,
    )
    return ModelList(items=items, total=total, page=page, page_size=page_size)


@router.get("/model/{model_id}", response_model=ModelRead)
def get_model(model_id: str, db: DbSession) -> ModelRead:
    ensure_seeded(db)
    try:
        return ModelRepository(db).get(model_id)
    except RegistryNotFoundError as error:
        raise _registry_error(error) from error


@router.post("/models", response_model=ModelRead, status_code=status.HTTP_201_CREATED)
def create_model(payload: ModelCreate, db: DbSession) -> ModelRead:
    ensure_seeded(db)
    try:
        return ModelRepository(db).create(payload)
    except RegistryConflictError as error:
        raise _registry_error(error) from error


@router.patch("/models/{model_id}", response_model=ModelRead)
def update_model(model_id: str, payload: ModelUpdate, db: DbSession) -> ModelRead:
    ensure_seeded(db)
    try:
        return ModelRepository(db).update(model_id, payload)
    except RegistryNotFoundError as error:
        raise _registry_error(error) from error


@router.delete("/models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_model(model_id: str, db: DbSession) -> Response:
    ensure_seeded(db)
    try:
        ModelRepository(db).delete(model_id)
    except RegistryNotFoundError as error:
        raise _registry_error(error) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/policies", response_model=list[PolicyRead])
def list_policies(db: DbSession) -> list[PolicyRead]:
    ensure_seeded(db)
    return PolicyRepository(db).list()


@router.patch("/policies/{policy_id}", response_model=PolicyRead)
def update_policy(
    policy_id: str,
    payload: PolicyUpdate,
    db: DbSession,
) -> PolicyRead:
    ensure_seeded(db)
    try:
        return PolicyRepository(db).update(policy_id, payload)
    except RegistryNotFoundError as error:
        raise _registry_error(error) from error


@router.get("/history", response_model=HistoryList)
def routing_history(
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    policy_id: str | None = None,
    intent: str | None = None,
) -> HistoryList:
    filters = []
    if policy_id:
        filters.append(RouterHistory.policy_id == policy_id)
    if intent:
        filters.append(RouterHistory.intent == intent)
    query = (
        select(RouterHistory)
        .where(*filters)
        .order_by(RouterHistory.created_at.desc(), RouterHistory.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    count_query = select(func.count()).select_from(RouterHistory).where(*filters)
    return HistoryList(
        items=[
            HistoryRead.model_validate(item)
            for item in db.scalars(query)
        ],
        total=int(db.scalar(count_query) or 0),
        page=page,
        page_size=page_size,
    )


@router.get("/status", response_model=RouterStatus)
def router_status(db: DbSession) -> RouterStatus:
    ensure_seeded(db)
    models = {
        state: int(
            db.scalar(
                select(func.count())
                .select_from(RegisteredModel)
                .where(RegisteredModel.status == state)
            )
            or 0
        )
        for state in ("ACTIVE", "DEGRADED", "DISABLED", "MAINTENANCE")
    }
    circuits = {
        state: int(
            db.scalar(
                select(func.count())
                .select_from(CircuitBreakerRecord)
                .where(CircuitBreakerRecord.state == state)
            )
            or 0
        )
        for state in ("CLOSED", "OPEN", "HALF_OPEN")
    }
    daily, monthly = current_costs(db)
    return RouterStatus(
        status="healthy" if models["ACTIVE"] else "unavailable",
        models=models,
        policies=int(db.scalar(select(func.count()).select_from(RoutingPolicy)) or 0),
        circuit_breakers=circuits,
        costs={"daily_usd": daily, "monthly_usd": monthly},
    )
