# First Production Deploy

Prerequisites: DNS `app.разуммаркета.рф` points to the VPS, Docker/Compose and host Nginx are
installed, ports 80/443 are open, and `/opt/ai-ranking-os` belongs to a dedicated deploy user.

```sh
cd /opt/ai-ranking-os/deployment/production
cp .env.example .env
chmod 600 .env
# Fill secrets and immutable image/build values.
./scripts/deploy.sh
curl -fsS http://127.0.0.1:8100/ready
```

Issue the Let's Encrypt certificate manually, install the separate host vhost, run `nginx -t` and
reload. Open `https://app.разуммаркета.рф`, log in using the bootstrap account, select Skinjestique
and `gpt-4o-mini`, review and run the research, then confirm the report. Finally run the automated
smoke test using the same public URL. Change the initial password after first access.
