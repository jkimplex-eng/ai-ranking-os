# GEO Site Audit and Competitor Social Monitoring

## GEO site readiness

`POST /geo/site-audits` reads the public homepage, `robots.txt`, and sitemap. It calculates a
versioned 0–100 readiness score from 23 checks:

- crawlability — 20 points;
- entity clarity — 20 points;
- content — 25 points;
- evidence — 20 points;
- technical signals — 15 points.

Every check stores the observed evidence, awarded points, and a remediation when it fails.
Requests are restricted to public HTTP(S) hosts to prevent server-side request forgery. The result
is a readiness assessment, not proof of indexing or causality inside a closed AI platform.

## Competitor social sources

Each competitor can own multiple monitored social sources. Telegram public preview pages and
YouTube Atom feeds are credential-free. VK and Instagram use their official APIs and require an
access token; the token is encrypted at rest and never returned by the API.

The existing worker refreshes due sources once per day. Posts retain their public engagement
metrics when available. Publication significance is a reproducible observation score based on
available reach, engagement, and metric completeness. Missing metrics remain `null`; the system
does not invent values. Significance is correlation evidence and must not be described as a proven
cause of AI recommendations.

## Manual verification

1. Open **GEO-площадки**, enter a brand and its public website, then select
   **Провести GEO-аудит**. Confirm the score, category totals, actions, and detailed evidence.
2. Open **Конкуренты**, select or create a project and competitor, then expand
   **Соцсети и ежедневные публикации**.
3. Add a Telegram handle or YouTube Channel ID. Confirm the source status and collected posts.
4. For VK or Instagram, provide an official token. Confirm that the UI never displays the token.
5. Use the refresh action or wait for the daily worker run. If a provider rejects access, confirm
   that the source shows `ERROR` or `NOT_CONFIGURED` with the actual reason.
