from sqlalchemy.orm import Session

from baseline.engine import BaselineEngine
from trend.research_adapter import SqlAlchemyTrendDataSource


def build_baseline_engine(db: Session) -> BaselineEngine:
    return BaselineEngine(db, SqlAlchemyTrendDataSource(db))

