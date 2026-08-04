from sqlalchemy.orm import Session

from observability.models import TraceSpan


class TraceRepository:
    def __init__(self, db: Session):
        self.db = db

    def append(self, span: TraceSpan):
        self.db.add(span)
        self.db.commit()
        return span
