import logging

from sqlalchemy.orm import Session

from alice_learning.adapters import (
    PublicationInfluenceSource,
    ResearchAliceEvidenceSource,
    ResearchOrganizationSource,
)
from alice_learning.repository import AliceLearningRepository
from alice_learning.schemas import TrainRequest
from alice_learning.service import AliceLearningService

logger = logging.getLogger(__name__)


def learn_from_completed_research(db: Session, research_id: int) -> int:
    """Ingest Yandex observations after the normal research pipeline completes.

    The integration deliberately returns zero when tenant ownership or Yandex evidence is absent;
    a learning failure must not change the completed state of the source research.
    """

    organization_id = ResearchOrganizationSource(db).organization_id(research_id)
    if organization_id is None:
        logger.info("Alice learning skipped: organization unresolved research_id=%s", research_id)
        return 0
    service = AliceLearningService(
        db,
        ResearchAliceEvidenceSource(db),
        PublicationInfluenceSource(db),
        AliceLearningRepository(db),
    )
    observations = service.ingest(organization_id, research_id)
    if not observations:
        return 0
    service.train(organization_id, TrainRequest())
    dimensions = {
        (item.category, item.language, item.region)
        for item in observations
        if item.category != "UNIVERSAL"
    }
    for category, language, region in dimensions:
        service.train(
            organization_id,
            TrainRequest(category=category, language=language, region=region),
        )
    return len(observations)


def rebuild_alice_learning(db: Session, organization_id: int) -> int:
    learned = 0
    source = ResearchOrganizationSource(db)
    for research_id in source.research_ids(organization_id):
        learned += learn_from_completed_research(db, research_id)
    return learned
