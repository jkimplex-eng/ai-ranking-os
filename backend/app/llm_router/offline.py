from threading import RLock

from sqlalchemy import create_engine, delete
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base
from backend.app.llm_router.models import BudgetReservation, RouterCostLog, RouterHistory
from backend.app.llm_router.schemas import RouteRequest, RouteResponse
from backend.app.llm_router.service import router_service
from provider_registry.models import ProviderRecord  # noqa: F401

_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(_engine)
_sessions = sessionmaker(bind=_engine, expire_on_commit=False)
_lock = RLock()


def route_offline(request: RouteRequest) -> RouteResponse:
    """Offline infrastructure adapter delegating to the single production Router."""

    with _lock, _sessions() as db:
        response = router_service.decide(db, request)
        db.execute(delete(RouterHistory))
        db.execute(delete(RouterCostLog))
        db.execute(delete(BudgetReservation))
        db.commit()
        return response
