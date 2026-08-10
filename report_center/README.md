# Report Center

Searchable report catalog for completed and in-progress project research. The module owns
only report lifecycle metadata (tags and archive state) and reads report facts through the
public `ReportSource` port. It does not recalculate scores or duplicate Research reporting.

Endpoints:

- `GET /reports` — search, filter by project/tag/archive and paginate.
- `PATCH /reports/{research_id}` — update tags or archive state.
