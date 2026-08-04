from sqlalchemy import select
from sqlalchemy.orm import Session

from rate_limit.models import RateLimitPolicy


class RateLimitRepository:
    def __init__(self, db: Session):
        self.db = db

    def save(self, p):
        self.db.add(p)
        self.db.commit()
        self.db.refresh(p)
        return p

    def get(self, id):
        return self.db.get(RateLimitPolicy, id)

    def list(self):
        return list(self.db.scalars(select(RateLimitPolicy).order_by(RateLimitPolicy.id)))
