# Production Deployment

AI Ranking OS is deployed independently from the existing `разуммаркета.рф` landing and Ozon
Agent. The checkout lives in `/opt/ai-ranking-os`; its Compose project publishes only the internal
edge on `127.0.0.1:8100`. Host Nginx terminates TLS for `app.разуммаркета.рф`.

## Deploy

1. Clone the repository and check out the reviewed immutable release commit.
2. Copy `deployment/production/.env.example` to `.env` and supply secrets.
3. Run `deployment/production/scripts/deploy.sh`.
4. Install `nginx/host-vhost.conf.example` as a separate host vhost after certificate issuance.
5. Run `SMOKE_BASE_URL=https://app.разуммаркета.рф SMOKE_EMAIL=... SMOKE_PASSWORD=... python deployment/production/scripts/smoke_test.py`.

The deployment script validates Compose, builds images, starts data services, runs Alembic once,
then starts application services. It never modifies the legacy website.

## Update

Back up the database, fetch the reviewed commit, set an immutable `IMAGE_TAG`, run `deploy.sh`, and
gate traffic on `/ready` plus the production smoke test. Never deploy mutable `latest` tags.

## Rollback

Set `ROLLBACK_IMAGE_TAG` to the previous immutable image tag and run `rollback.sh`. Database schema
rollback is a separate reviewed operation; restore a pre-deploy backup if the release is not
backward compatible.
