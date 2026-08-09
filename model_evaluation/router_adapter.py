from sqlalchemy.orm import Session

from backend.app.llm_router.ports import ModelEvaluationPort


class SqlAlchemyModelEvaluation(ModelEvaluationPort):
    """Model-evaluation implementation of the Router evaluation port."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def scores(self, task_type: str | None) -> dict[str, float]:
        from model_evaluation.service import empirical_model_scores

        return empirical_model_scores(self.db, task_type)
