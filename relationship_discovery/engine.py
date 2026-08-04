from datetime import UTC, datetime
from math import prod

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from relationship_discovery.models import (
    RelationshipCandidate,
    RelationshipDecision,
    RelationshipDecisionType,
    RelationshipEvidence,
    RelationshipStatus,
    RelationshipType,
)
from relationship_discovery.ports import EvidenceItem, EvidenceProvider, GraphProvider
from relationship_discovery.schemas import (
    DiscoveryRunResult,
    RelationshipCandidateRead,
    RelationshipDecisionRead,
    RelationshipDecisionRequest,
    RelationshipEvidenceRead,
)


class RelationshipCandidateNotFoundError(LookupError):
    """Requested relationship candidate does not exist."""


class RelationshipDecisionConflictError(ValueError):
    """Candidate already has a final decision."""


class RelationshipDiscoveryEngine:
    ALGORITHM_VERSION = "1.0"

    def __init__(
        self,
        db: Session,
        graph_provider: GraphProvider,
        evidence_provider: EvidenceProvider,
    ) -> None:
        self.db = db
        self.graph_provider = graph_provider
        self.evidence_provider = evidence_provider

    def run(self, snapshot_id: int | None = None) -> DiscoveryRunResult:
        graph = self.graph_provider.graph(snapshot_id)
        entity_ids = {entity.external_id for entity in graph.entities}
        existing = {
            (item.source_external_id, item.target_external_id, item.relationship_type)
            for item in graph.relationships
        }
        grouped: dict[tuple[str, str, RelationshipType], list[EvidenceItem]] = {}
        for item in self.evidence_provider.evidence(graph):
            if not 0 <= item.confidence <= 1:
                continue
            try:
                relationship_type = RelationshipType(item.relationship_type)
            except ValueError:
                continue
            if (
                item.source_external_id not in entity_ids
                or item.target_external_id not in entity_ids
                or item.source_external_id == item.target_external_id
            ):
                continue
            key = (item.source_external_id, item.target_external_id, relationship_type)
            if key in existing:
                continue
            grouped.setdefault(key, []).append(item)
        candidates = []
        for key, evidence_items in grouped.items():
            candidate = self.db.scalar(
                select(RelationshipCandidate)
                .options(selectinload(RelationshipCandidate.evidence))
                .where(
                    RelationshipCandidate.graph_snapshot_id == graph.snapshot_id,
                    RelationshipCandidate.source_external_id == key[0],
                    RelationshipCandidate.target_external_id == key[1],
                    RelationshipCandidate.relationship_type == key[2],
                )
            )
            if candidate is None:
                candidate = RelationshipCandidate(
                    graph_snapshot_id=graph.snapshot_id,
                    source_external_id=key[0],
                    target_external_id=key[1],
                    relationship_type=key[2],
                    confidence=0,
                    status=RelationshipStatus.PENDING,
                    algorithm_version=self.ALGORITHM_VERSION,
                )
                self.db.add(candidate)
                self.db.flush()
            known = {(item.source_type, item.source_reference) for item in candidate.evidence}
            for item in evidence_items:
                identity = (item.source_type, item.source_reference)
                if identity in known:
                    continue
                known.add(identity)
                candidate.evidence.append(
                    RelationshipEvidence(
                        source_type=item.source_type,
                        source_reference=item.source_reference,
                        confidence=item.confidence,
                        payload=item.payload,
                    )
                )
            self.db.flush()
            candidate.confidence = self._confidence(candidate.evidence)
            candidates.append(candidate)
        self.db.commit()
        reads = [self._read(self._load(item.id)) for item in candidates]
        return DiscoveryRunResult(
            graph_snapshot_id=graph.snapshot_id,
            algorithm_version=self.ALGORITHM_VERSION,
            candidate_count=len(reads),
            candidates=reads,
        )

    def candidates(
        self, *, status: RelationshipStatus | None, offset: int, limit: int
    ) -> list[RelationshipCandidateRead]:
        statement = (
            select(RelationshipCandidate)
            .options(
                selectinload(RelationshipCandidate.evidence),
                selectinload(RelationshipCandidate.decisions),
            )
            .order_by(RelationshipCandidate.created_at.desc(), RelationshipCandidate.id.desc())
            .offset(offset)
            .limit(limit)
        )
        if status is not None:
            statement = statement.where(RelationshipCandidate.status == status)
        return [self._read(item) for item in self.db.scalars(statement).all()]

    def approve(
        self, candidate_id: int, payload: RelationshipDecisionRequest
    ) -> RelationshipCandidateRead:
        candidate = self._load(candidate_id)
        self._ensure_pending(candidate)
        evidence = EvidenceItem(
            source_external_id=candidate.source_external_id,
            target_external_id=candidate.target_external_id,
            relationship_type=candidate.relationship_type,
            confidence=candidate.confidence,
            source_type="relationship_discovery",
            source_reference=str(candidate.id),
            payload={"candidate_id": candidate.id},
        )
        candidate.integrated_snapshot_id = self.graph_provider.integrate(
            candidate.graph_snapshot_id, evidence
        )
        candidate.status = RelationshipStatus.APPROVED
        candidate.resolved_at = datetime.now(UTC)
        self._decision(candidate, RelationshipDecisionType.APPROVE, payload)
        self.db.commit()
        return self._read(self._load(candidate.id))

    def reject(
        self, candidate_id: int, payload: RelationshipDecisionRequest
    ) -> RelationshipCandidateRead:
        candidate = self._load(candidate_id)
        self._ensure_pending(candidate)
        candidate.status = RelationshipStatus.REJECTED
        candidate.resolved_at = datetime.now(UTC)
        self._decision(candidate, RelationshipDecisionType.REJECT, payload)
        self.db.commit()
        return self._read(self._load(candidate.id))

    def _load(self, candidate_id: int) -> RelationshipCandidate:
        candidate = self.db.scalar(
            select(RelationshipCandidate)
            .options(
                selectinload(RelationshipCandidate.evidence),
                selectinload(RelationshipCandidate.decisions),
            )
            .where(RelationshipCandidate.id == candidate_id)
        )
        if candidate is None:
            raise RelationshipCandidateNotFoundError(
                f"Relationship candidate {candidate_id} not found"
            )
        return candidate

    @staticmethod
    def _ensure_pending(candidate: RelationshipCandidate) -> None:
        if candidate.status != RelationshipStatus.PENDING:
            raise RelationshipDecisionConflictError(
                f"Relationship candidate {candidate.id} is already {candidate.status}"
            )

    def _decision(
        self,
        candidate: RelationshipCandidate,
        decision: RelationshipDecisionType,
        payload: RelationshipDecisionRequest,
    ) -> None:
        candidate.decisions.append(
            RelationshipDecision(
                decision=decision,
                actor=payload.actor,
                reason=payload.reason,
                algorithm_version=self.ALGORITHM_VERSION,
            )
        )

    @staticmethod
    def _confidence(evidence: list[RelationshipEvidence]) -> float:
        return round(1 - prod(1 - item.confidence for item in evidence), 4)

    @staticmethod
    def _read(candidate: RelationshipCandidate) -> RelationshipCandidateRead:
        return RelationshipCandidateRead(
            id=candidate.id,
            graph_snapshot_id=candidate.graph_snapshot_id,
            source_external_id=candidate.source_external_id,
            target_external_id=candidate.target_external_id,
            relationship_type=candidate.relationship_type,
            confidence=candidate.confidence,
            status=candidate.status,
            algorithm_version=candidate.algorithm_version,
            integrated_snapshot_id=candidate.integrated_snapshot_id,
            created_at=candidate.created_at,
            resolved_at=candidate.resolved_at,
            evidence=[
                RelationshipEvidenceRead(
                    id=item.id,
                    source_type=item.source_type,
                    source_reference=item.source_reference,
                    confidence=item.confidence,
                    payload=item.payload,
                    created_at=item.created_at,
                )
                for item in sorted(candidate.evidence, key=lambda value: value.id)
            ],
            decisions=[
                RelationshipDecisionRead(
                    id=item.id,
                    decision=item.decision,
                    actor=item.actor,
                    reason=item.reason,
                    algorithm_version=item.algorithm_version,
                    created_at=item.created_at,
                )
                for item in sorted(candidate.decisions, key=lambda value: value.id)
            ],
        )
