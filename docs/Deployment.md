# Deployment

For local or RC verification:

```bash
cp .env.example .env
docker compose up --build
curl http://localhost:8000/system/health
curl http://localhost:8000/metrics
```

The API container runs Alembic before Uvicorn; PostgreSQL and Redis health
checks gate startup. For production, pin the image digest, inject secrets,
restrict database and Redis networking, terminate TLS at the ingress, run
multiple API replicas, and use a managed PostgreSQL service with point-in-time
recovery.

Deploy migrations before shifting traffic. Verify health, build SHA, Router
status, provider status, a canary route, and the validation report. Roll back
the application image when application checks fail; database downgrade requires
an explicit reviewed procedure.
