from report_center.ports import ReportSource, ReportSourceItem
from report_center.repository import ReportCatalogRepository
from report_center.schemas import (
    ReportCatalogPage,
    ReportCatalogRead,
    ReportCatalogUpdate,
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
