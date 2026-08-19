from sqlalchemy import select
from sqlalchemy.orm import Session

from publication_learning.models import PublicationExperiment, PublicationInfluenceEstimate


class PublicationLearningRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def experiments_for_entity(self, entity_id: object) -> list[PublicationExperiment]:
        return list(
            self.db.scalars(
                select(PublicationExperiment)
                .where(PublicationExperiment.entity_id == entity_id)
                .order_by(
                    PublicationExperiment.evaluated_at.desc(), PublicationExperiment.id.desc()
                )
            )
        )

    def experiment(self, experiment_id: int) -> PublicationExperiment | None:
        return self.db.get(PublicationExperiment, experiment_id)

    def estimates(
        self, entity_dimensions: dict[str, str] | None = None
    ) -> list[PublicationInfluenceEstimate]:
        statement = select(PublicationInfluenceEstimate)
        if entity_dimensions:
            for key, value in entity_dimensions.items():
                if value:
                    statement = statement.where(getattr(PublicationInfluenceEstimate, key) == value)
        return list(
            self.db.scalars(
                statement.order_by(
                    PublicationInfluenceEstimate.confidence_score.desc(),
                    PublicationInfluenceEstimate.expected_delta.desc(),
                )
            )
        )
