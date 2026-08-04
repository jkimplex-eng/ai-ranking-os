from sqlalchemy import select
from sqlalchemy.orm import Session

from recommendation.templates.models import RecommendationTemplate


class RecommendationTemplateNotFoundError(LookupError):
    """No template exists for the requested code."""


class RecommendationTemplateRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self) -> list[RecommendationTemplate]:
        return list(
            self.db.scalars(
                select(RecommendationTemplate).order_by(
                    RecommendationTemplate.template_code,
                    RecommendationTemplate.version.desc(),
                )
            )
        )

    def get_latest(self, code: str) -> RecommendationTemplate:
        template = self.db.scalar(
            select(RecommendationTemplate)
            .where(RecommendationTemplate.template_code == code)
            .order_by(
                RecommendationTemplate.created_at.desc(),
                RecommendationTemplate.id.desc(),
            )
        )
        if template is None:
            raise RecommendationTemplateNotFoundError(
                f"Recommendation template {code} not found"
            )
        return template

    def by_type(self, version: str) -> dict[str, RecommendationTemplate]:
        templates = self.db.scalars(
            select(RecommendationTemplate)
            .where(RecommendationTemplate.version == version)
            .order_by(RecommendationTemplate.id)
        )
        return {item.recommendation_type: item for item in templates}
