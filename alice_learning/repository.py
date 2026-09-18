from sqlalchemy import select
from sqlalchemy.orm import Session

from alice_learning.models import AliceModelSnapshot, AliceObservation, AlicePrediction


class AliceLearningRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def observation(self, response_id: int, feature_version: str) -> AliceObservation | None:
        return self.db.scalar(
            select(AliceObservation).where(
                AliceObservation.response_id == response_id,
                AliceObservation.feature_version == feature_version,
            )
        )

    def observations(
        self,
        organization_id: int,
        *,
        category: str | None = None,
        language: str | None = None,
        region: str | None = None,
    ) -> list[AliceObservation]:
        statement = select(AliceObservation).where(
            AliceObservation.organization_id == organization_id
        )
        if category and category != "UNIVERSAL":
            statement = statement.where(AliceObservation.category == category)
        if language:
            statement = statement.where(AliceObservation.language == language)
        if region:
            statement = statement.where(AliceObservation.region == region)
        return list(
            self.db.scalars(statement.order_by(AliceObservation.observed_at, AliceObservation.id))
        )

    def latest_model(
        self, organization_id: int, category: str, language: str, region: str
    ) -> AliceModelSnapshot | None:
        statement = select(AliceModelSnapshot).where(
            AliceModelSnapshot.organization_id == organization_id,
            AliceModelSnapshot.language == language,
            AliceModelSnapshot.region == region,
        )
        if category != "UNIVERSAL":
            statement = statement.where(AliceModelSnapshot.category == category)
        else:
            statement = statement.where(AliceModelSnapshot.category == "UNIVERSAL")
        return self.db.scalar(
            statement.order_by(AliceModelSnapshot.trained_at.desc(), AliceModelSnapshot.id.desc())
        )

    def predictions(self, organization_id: int, limit: int = 10) -> list[AlicePrediction]:
        return list(
            self.db.scalars(
                select(AlicePrediction)
                .where(AlicePrediction.organization_id == organization_id)
                .order_by(AlicePrediction.created_at.desc(), AlicePrediction.id.desc())
                .limit(limit)
            )
        )
