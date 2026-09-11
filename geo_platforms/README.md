# GEO Platform Registry

Independent registry of publication resources used by the GEO methodology. The module stores
canonical domains, normalized authority/content signals, costs, and the evidence/source behind
each value. It accepts manual records, normalized Ahrefs/Semrush exports, and provider-neutral
discovery input; it does not fabricate missing metrics or require paid integrations.

API:

- `POST /geo/platforms`
- `GET /geo/platforms`
- `GET /geo/platforms/{platform_id}`
- `PATCH /geo/platforms/{platform_id}`
- `DELETE /geo/platforms/{platform_id}`
- `POST /geo/platforms/imports`
- `POST /geo/platforms/discover`

