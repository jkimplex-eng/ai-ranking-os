import os

from sqlalchemy.orm import Session

from backend.app.llm_router.ports import ModelEvaluationPort, ProviderReadinessPort, ProviderState
from backend.app.providers.credentials import credentials
from backend.app.providers.registry import registry


class RuntimeProviderReadiness(ProviderReadinessPort):
    """Provider infrastructure adapter kept outside Router decision logic."""

    def __init__(self, db: Session | None = None) -> None:
        self.db = db

    def state(self, provider_id: str) -> ProviderState:
        if self.db is not None:
            from provider_registry.models import ProviderRecord

            record = self.db.get(ProviderRecord, provider_id.casefold())
            if record is not None:
                aliases = {"AVAILABLE": "READY", "DEGRADED": "READY"}
                return ProviderState(aliases.get(record.availability, record.availability))
        try:
            definition = registry.get(provider_id)
        except KeyError:
            return ProviderState.UNAVAILABLE
        if not definition.enabled:
            return ProviderState.DISABLED
        configured_mock = os.getenv("PROVIDER_MOCK_MODE")
        mock_mode = (
            configured_mock.casefold() not in {"false", "0", "no"}
            if configured_mock is not None
            else definition.mock
        )
        if mock_mode:
            return ProviderState.READY
        if definition.name == "ollama":
            return ProviderState.READY
        if definition.credential and not credentials.get(definition.credential, required=False):
            return ProviderState.NOT_CONFIGURED
        if definition.project_credential and not credentials.get(
            definition.project_credential, required=False
        ):
            return ProviderState.NOT_CONFIGURED
        return ProviderState.READY


class SqlAlchemyModelEvaluation(ModelEvaluationPort):
    def __init__(self, db: Session) -> None:
        self.db = db

    def scores(self, task_type: str | None) -> dict[str, float]:
        from model_evaluation.service import empirical_model_scores

        return empirical_model_scores(self.db, task_type)
