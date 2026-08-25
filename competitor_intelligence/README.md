# Competitor Intelligence

The module aggregates competitor visibility and publication evidence from completed project
researches. It owns daily snapshots and source observations, while competitor CRUD remains in the
public Workspace API and recurring execution remains in Scheduler/Project Monitoring.

`observed_visibility_score` is a module-specific observation index, not the primary AI Visibility
score. Publication significance measures recurrence, provider coverage and recommendation
co-occurrence. It must never be presented as proof of causality or knowledge of provider ranking
algorithms.

API:

- `GET /competitor-intelligence/projects/{project_id}`
- `POST /competitor-intelligence/projects/{project_id}/refresh`
- `PUT /competitor-intelligence/projects/{project_id}/daily-monitoring`
- `POST /competitor-intelligence/projects/{project_id}/competitors/{competitor_id}/social/discover`
- `GET /competitor-intelligence/telegram/connection`
- `POST /competitor-intelligence/telegram/connection/send-code`
- `POST /competitor-intelligence/telegram/connection/verify`
- `DELETE /competitor-intelligence/telegram/connection`
- `PUT /competitor-intelligence/telegram/connection/proxy`
- `DELETE /competitor-intelligence/telegram/connection/proxy`
- `POST /competitor-intelligence/projects/{project_id}/competitors/{competitor_id}/telegram/search`

Social monitoring uses the same module and the existing worker queue. Telegram public previews
and YouTube feeds work without credentials. VK and Instagram use official APIs and require an
encrypted token. Unavailable sources remain visible with an explicit status; no synthetic posts
or metrics are generated.

Auto-discovery reads only competitor-owned public websites, extracts explicit social profile links,
deduplicates them, and starts the existing collectors. It blocks private and loopback addresses to
prevent SSRF. Global brand search is intentionally not simulated for YouTube, VK, or Instagram;
their official credentials and quota are required. Telegram uses the official MTProto global post
index after a service account is authorized.

## Telegram MTProto

The connection wizard stores `api_hash`, phone, optional SOCKS5 configuration, code challenge and
the resulting Telethon string session encrypted with the platform provider secret. Verification
codes and 2FA passwords are never persisted. Once connected, the service searches message content
for the competitor name and aliases across all indexed public channels (including channels the
account has not joined), saves evidence under the existing social source/post model, and repeats
searches daily through the existing worker. Private channels and chats remain inaccessible. Some
Telegram accounts may require Premium for global post search. Telegram content is evidence for
deterministic analytics and is not used to train or fine-tune an ML/LLM model.

An already-authorized account can add or replace its SOCKS5 route without reconnecting Telegram.
The service validates authentication through the proposed proxy before encrypting and persisting
its host, port and optional credentials. A failed proxy never replaces the active route.

For networks which block Telegram DCs, the same connection endpoint also accepts native
`MTPROXY` transport with `host`, `port` and `secret` from a `tg://proxy` or `t.me/proxy` link.
Telethon validates the MTProxy against the existing authorized session before it is saved. The
secret is encrypted together with the rest of the proxy configuration and is never returned by
the API. HTTP Webshare connections retain automatic SOCKS5 fallback for compatible endpoints.
