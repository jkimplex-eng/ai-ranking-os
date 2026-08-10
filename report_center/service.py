import hashlib
import json

from report_center.ports import ReportSource, ReportSourceItem
from report_center.repository import ReportCatalogRepository
from report_center.schemas import (
    ReportCatalogPage,
    ReportCatalogRead,
    ReportCatalogUpdate,
    ReportVersionComparison,
    ReportVersionRead,
)


class ReportNotFoundError(LookupError):
    pass


class ReportCenterService:
    def __init__(self, repository: ReportCatalogRepository, source: ReportSource) -> None:
        self.repository = repository
        self.source = source

    @staticmethod
    def _read(source: ReportSourceItem, tags: list[str], archived: bool) -> ReportCatalogRead:
        return ReportCatalogRead(
            **source.__dict__, tags=tags, archived=archived
        )

    def list(
        self,
        *,
        project_id: int | None,
        search: str | None,
        tag: str | None,
        archived: bool,
        offset: int,
        limit: int,
    ) -> ReportCatalogPage:
        sources = self.source.list_reports(project_id)
        metadata = self.repository.metadata([item.research_id for item in sources])
        rows = []
        for source in sources:
            item = metadata.get(source.research_id)
            tags = item.tags if item else []
            is_archived = item.archived if item else False
            if is_archived != archived:
                continue
            if search and search.casefold() not in source.title.casefold():
                continue
            if tag and tag not in tags:
                continue
            rows.append(self._read(source, tags, is_archived))
        return ReportCatalogPage(
            items=rows[offset : offset + limit],
            total=len(rows),
            offset=offset,
            limit=limit,
        )

    def update(self, research_id: int, payload: ReportCatalogUpdate) -> ReportCatalogRead:
        source = next(
            (item for item in self.source.list_reports() if item.research_id == research_id),
            None,
        )
        if source is None:
            raise ReportNotFoundError(f"Report for research {research_id} not found")
        item = self.repository.get_or_create(research_id, source.project_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, field, value)
        item = self.repository.save(item)
        return self._read(source, item.tags, item.archived)

    def export(self, research_id: int) -> dict:
        try:
            return self.source.export_payload(research_id)
        except LookupError as error:
            raise ReportNotFoundError(f"Report for research {research_id} not found") from error

    def snapshot(self, research_id: int) -> ReportVersionRead:
        source = next(
            (item for item in self.source.list_reports() if item.research_id == research_id),
            None,
        )
        if source is None:
            raise ReportNotFoundError(f"Report for research {research_id} not found")
        payload = self.source.export_payload(research_id)
        checksum = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        entry = self.repository.get_or_create(research_id, source.project_id)
        version = self.repository.add_version(entry, checksum, payload)
        return ReportVersionRead.model_validate(version, from_attributes=True)

    def versions(self, research_id: int) -> list[ReportVersionRead]:
        self.snapshot(research_id)
        return [
            ReportVersionRead.model_validate(item, from_attributes=True)
            for item in self.repository.versions(research_id)
        ]

    @staticmethod
    def _values(payload: dict, field: str, key: str) -> set[str]:
        return {str(item[key]) for item in payload.get(field, []) if item.get(key)}

    def compare_versions(
        self, research_id: int, left: int, right: int
    ) -> ReportVersionComparison:
        left_version = self.repository.version(research_id, left)
        right_version = self.repository.version(research_id, right)
        if left_version is None or right_version is None:
            raise ReportNotFoundError("One or both report versions were not found")
        left_score = left_version.payload.get("score") or {}
        right_score = right_version.payload.get("score") or {}
        score_fields = (
            "visibility_score",
            "mention_score",
            "recommendation_score",
            "citation_score",
            "coverage_score",
            "confidence_score",
        )
        deltas = {
            field: round(float(right_score[field]) - float(left_score[field]), 4)
            if field in left_score and field in right_score
            else None
            for field in score_fields
        }
        left_entities = self._values(left_version.payload, "entities", "canonical_name")
        right_entities = self._values(right_version.payload, "entities", "canonical_name")
        left_recommendations = self._values(
            left_version.payload, "recommendations", "content"
        )
        right_recommendations = self._values(
            right_version.payload, "recommendations", "content"
        )
        return ReportVersionComparison(
            research_id=research_id,
            left_version=left,
            right_version=right,
            score_deltas=deltas,
            added_entities=sorted(right_entities - left_entities),
            removed_entities=sorted(left_entities - right_entities),
            added_recommendations=sorted(right_recommendations - left_recommendations),
            removed_recommendations=sorted(left_recommendations - right_recommendations),
        )
from __future__ import annotations
