from sqlalchemy import select
from sqlalchemy.orm import Session

from hardening.models import DeadLetterMessage, IdempotencyRecord


class HardeningRepository:
    def __init__(self, db: Session):
        self.db = db

    def idempotency(self, scope, key):
        return self.db.scalar(
            select(IdempotencyRecord).where(
                IdempotencyRecord.scope == scope, IdempotencyRecord.key == key
            )
        )

    def save(self, value):
        self.db.add(value)
        self.db.commit()
        self.db.refresh(value)
        return value

    def dlq(self, status=None):
        q = select(DeadLetterMessage).order_by(DeadLetterMessage.id.desc())
        if status:
            q = q.where(DeadLetterMessage.status == status)
        return list(self.db.scalars(q))
