from sqlalchemy.orm import Session

from recommendation.research_adapter import SqlAlchemyResearchScoreAdapter
from recommendation.simulation.simulator import ImpactSimulator


def build_impact_simulator(db: Session) -> ImpactSimulator:
    """Composition root keeping Research integration outside simulator core."""

    return ImpactSimulator(db, SqlAlchemyResearchScoreAdapter(db))
