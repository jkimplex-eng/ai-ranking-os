from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from entity_linking.models import (
    CanonicalEntity,
    EntityAlias,
    LinkCandidate,
    LinkDecision,
    LinkDecisionType,
    LinkStatus,
)
from entity_linking.ports import CanonicalRecord, EntityResolver, GraphProvider, LinkableEntity
from entity_linking.resolver import normalize_name
from entity_linking.schemas import (
    CandidateDecisionRequest,
    LinkCandidateRead,
    LinkDecisionRead,
    LinkingRunResult,
)


class LinkCandidateNotFoundError(LookupError):
    """Requested link candidate does not exist."""


class CanonicalEntityNotFoundError(LookupError):
    """Requested canonical entity does not exist."""


class LinkDecisionConflictError(ValueError):
    """Candidate has already received a final manual decision."""


class EntityLinkingEngine:
    ALGORITHM_VERSION = "1.0"
    AUTO_APPROVE_CONFIDENCE = 0.95

    def __init__(
        self, db: Session, graph_provider: GraphProvider, resolver: EntityResolver
    ) -> None:
        self.db = db
        self.graph_provider = graph_provider
        self.resolver = resolver

    def run(self, snapshot_id: int | None = None) -> LinkingRunResult:
        graph = self.graph_provider.graph(snapshot_id)
        candidates = []
        for entity in graph.entities:
            canonicals = self._canonical_records()
            resolution = self.resolver.resolve(entity, canonicals)
            canonical = (
                self.db.get(CanonicalEntity, resolution.canonical_entity_id)
                if resolution.canonical_entity_id
                else self._create_canonical(entity)
            )
            automatic = resolution.match_method != "FUZZY_NAME"
            status = LinkStatus.APPROVED if automatic else LinkStatus.PENDING
            candidate = LinkCandidate(
                graph_snapshot_id=graph.snapshot_id,
                graph_node_id=entity.graph_node_id,
                external_id=entity.external_id,
                entity_name=entity.name,
                normalized_name=normalize_name(entity.canonical_name or entity.name),
                entity_type=entity.entity_type,
                canonical_entity_id=canonical.id,
                confidence=resolution.confidence,
                match_method=resolution.match_method,
                status=status,
                algorithm_version=self.ALGORITHM_VERSION,
                resolved_at=datetime.now(UTC) if automatic else None,
            )
            self.db.add(candidate)
            self.db.flush()
            if automatic:
                decision_type = (
                    LinkDecisionType.AUTO_CREATE
                    if resolution.match_method == "NEW_ENTITY"
                    else LinkDecisionType.AUTO_MATCH
                )
                self._decision(candidate, decision_type, canonical.id, "system", None)
                self._add_aliases(canonical, entity, "automatic")
            candidates.append(candidate)
        self.db.commit()
        reads = [self._read(self._load(candidate.id)) for candidate in candidates]
        return LinkingRunResult(
            graph_snapshot_id=graph.snapshot_id,
            algorithm_version=self.ALGORITHM_VERSION,
            total=len(reads),
            approved=sum(item.status == LinkStatus.APPROVED for item in reads),
            pending=sum(item.status == LinkStatus.PENDING for item in reads),
            candidates=reads,
        )

    def candidates(
        self, *, status: LinkStatus | None, offset: int, limit: int
    ) -> list[LinkCandidateRead]:
        statement = (
            select(LinkCandidate)
            .options(
                selectinload(LinkCandidate.decisions),
                selectinload(LinkCandidate.canonical_entity),
            )
            .order_by(LinkCandidate.created_at.desc(), LinkCandidate.id.desc())
            .offset(offset)
            .limit(limit)
        )
        if status is not None:
            statement = statement.where(LinkCandidate.status == status)
        return [self._read(item) for item in self.db.scalars(statement).all()]

    def approve(self, candidate_id: int, payload: CandidateDecisionRequest) -> LinkCandidateRead:
        candidate = self._load(candidate_id)
        self._ensure_pending(candidate)
        canonical_id = payload.canonical_entity_id or candidate.canonical_entity_id
        canonical = self.db.get(CanonicalEntity, canonical_id) if canonical_id else None
        if canonical is None:
            raise CanonicalEntityNotFoundError(f"Canonical entity {canonical_id} not found")
        candidate.canonical_entity_id = canonical.id
        candidate.canonical_entity = canonical
        candidate.status = LinkStatus.APPROVED
        candidate.resolved_at = datetime.now(UTC)
        self._decision(
            candidate,
            LinkDecisionType.MANUAL_APPROVE,
            canonical.id,
            payload.actor,
            payload.reason,
        )
        self._add_alias(
            canonical,
            candidate.entity_name,
            candidate.entity_type,
            "manual",
        )
        self.db.commit()
        return self._read(self._load(candidate.id))

    def reject(self, candidate_id: int, payload: CandidateDecisionRequest) -> LinkCandidateRead:
        candidate = self._load(candidate_id)
        self._ensure_pending(candidate)
        candidate.status = LinkStatus.REJECTED
        candidate.resolved_at = datetime.now(UTC)
        self._decision(
            candidate,
            LinkDecisionType.MANUAL_REJECT,
            candidate.canonical_entity_id,
            payload.actor,
            payload.reason,
        )
        self.db.commit()
        return self._read(self._load(candidate.id))

    def _canonical_records(self) -> list[CanonicalRecord]:
        canonicals = self.db.scalars(
            select(CanonicalEntity).options(selectinload(CanonicalEntity.aliases))
        ).all()
        return [
            CanonicalRecord(
                id=item.id,
                canonical_name=item.canonical_name,
                normalized_name=item.normalized_name,
                entity_type=item.entity_type,
                aliases=tuple(alias.normalized_alias for alias in item.aliases),
            )
            for item in canonicals
        ]

    def _create_canonical(self, entity: LinkableEntity) -> CanonicalEntity:
        canonical = CanonicalEntity(
            canonical_name=entity.canonical_name or entity.name,
            normalized_name=normalize_name(entity.canonical_name or entity.name),
            entity_type=entity.entity_type,
            algorithm_version=self.ALGORITHM_VERSION,
        )
        self.db.add(canonical)
        self.db.flush()
        return canonical

    def _add_aliases(self, canonical: CanonicalEntity, entity: LinkableEntity, source: str) -> None:
        for alias in (entity.name, *entity.aliases):
            self._add_alias(canonical, alias, entity.entity_type, source)

    def _add_alias(
        self, canonical: CanonicalEntity, alias: str, entity_type: str, source: str
    ) -> None:
        normalized = normalize_name(alias)
        if not normalized or normalized == canonical.normalized_name:
            return
        exists = self.db.scalar(
            select(EntityAlias.id).where(
                EntityAlias.entity_type == entity_type,
                EntityAlias.normalized_alias == normalized,
            )
        )
        if exists is None:
            self.db.add(
                EntityAlias(
                    canonical_entity_id=canonical.id,
                    alias=alias,
                    normalized_alias=normalized,
                    entity_type=entity_type,
                    source=source,
                )
            )

    def _load(self, candidate_id: int) -> LinkCandidate:
        candidate = self.db.scalar(
            select(LinkCandidate)
            .options(
                selectinload(LinkCandidate.decisions),
                selectinload(LinkCandidate.canonical_entity),
            )
            .where(LinkCandidate.id == candidate_id)
        )
        if candidate is None:
            raise LinkCandidateNotFoundError(f"Link candidate {candidate_id} not found")
        return candidate

    @staticmethod
    def _ensure_pending(candidate: LinkCandidate) -> None:
        if candidate.status != LinkStatus.PENDING:
            raise LinkDecisionConflictError(
                f"Link candidate {candidate.id} is already {candidate.status}"
            )

    def _decision(
        self,
        candidate: LinkCandidate,
        decision: LinkDecisionType,
        canonical_entity_id: int | None,
        actor: str,
        reason: str | None,
    ) -> None:
        candidate.decisions.append(
            LinkDecision(
                decision=decision,
                canonical_entity_id=canonical_entity_id,
                actor=actor,
                reason=reason,
                algorithm_version=self.ALGORITHM_VERSION,
            )
        )

    @staticmethod
    def _read(candidate: LinkCandidate) -> LinkCandidateRead:
        return LinkCandidateRead(
            id=candidate.id,
            graph_snapshot_id=candidate.graph_snapshot_id,
            graph_node_id=candidate.graph_node_id,
            external_id=candidate.external_id,
            entity_name=candidate.entity_name,
            normalized_name=candidate.normalized_name,
            entity_type=candidate.entity_type,
            canonical_entity_id=candidate.canonical_entity_id,
            canonical_name=(
                candidate.canonical_entity.canonical_name if candidate.canonical_entity else None
            ),
            confidence=candidate.confidence,
            match_method=candidate.match_method,
            status=candidate.status,
            algorithm_version=candidate.algorithm_version,
            created_at=candidate.created_at,
            resolved_at=candidate.resolved_at,
            decisions=[
                LinkDecisionRead(
                    id=item.id,
                    decision=item.decision,
                    canonical_entity_id=item.canonical_entity_id,
                    actor=item.actor,
                    reason=item.reason,
                    algorithm_version=item.algorithm_version,
                    created_at=item.created_at,
                )
                for item in sorted(candidate.decisions, key=lambda value: value.id)
            ],
        )
