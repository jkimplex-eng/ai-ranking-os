#!/bin/sh
set -eu

cd "$(dirname "$0")/.."
set -a
. ./.env
set +a

old_redis=$REDIS_PASSWORD
new_postgres=$(openssl rand -hex 32)
new_redis=$(openssl rand -hex 32)
new_jwt=$(openssl rand -hex 32)
new_admin=$(openssl rand -hex 20)

docker compose --env-file .env exec -T postgres \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 \
  -c "ALTER ROLE $POSTGRES_USER WITH PASSWORD '$new_postgres';" >/dev/null
docker compose --env-file .env exec -T redis \
  redis-cli -a "$old_redis" CONFIG SET requirepass "$new_redis" >/dev/null

python3 - "$new_postgres" "$new_redis" "$new_jwt" "$new_admin" <<'PY'
from pathlib import Path
import sys

path = Path(".env")
values = {
    "POSTGRES_PASSWORD": sys.argv[1],
    "REDIS_PASSWORD": sys.argv[2],
    "AUTH_JWT_SECRET": sys.argv[3],
    "ADMIN_PASSWORD": sys.argv[4],
}
values["DATABASE_URL"] = (
    f"postgresql+psycopg://ai_ranking:{sys.argv[1]}@postgres:5432/ai_ranking"
)
values["REDIS_URL"] = f"redis://:{sys.argv[2]}@redis:6379/0"
lines = path.read_text().splitlines()
updated = []
for line in lines:
    key = line.split("=", 1)[0] if "=" in line else ""
    updated.append(f"{key}={values[key]}" if key in values else line)
path.write_text("\n".join(updated) + "\n")
PY
chmod 600 .env
set -a
. ./.env
set +a

docker compose --env-file .env up -d --force-recreate \
  postgres redis backend worker nginx frontend >/dev/null
attempt=0
until curl -fsS http://127.0.0.1:${EDGE_PORT:-8100}/ready >/dev/null 2>&1; do
  attempt=$((attempt + 1))
  [ "$attempt" -lt 60 ] || { echo "Readiness timeout" >&2; exit 1; }
  sleep 2
done

docker compose --env-file .env exec -T backend python - <<'PY'
from authentication.models import AuthSession
from authentication.repository import SqlAlchemyAuthenticationRepository
from authentication.security import Argon2PasswordHasher
from backend.app.config import get_settings
from backend.app.database import SessionLocal

settings = get_settings()
with SessionLocal() as db:
    repository = SqlAlchemyAuthenticationRepository(db)
    user = repository.get_user_by_email(settings.admin_email)
    if user is None:
        raise SystemExit("Admin user is missing")
    user.password_hash = Argon2PasswordHasher().hash(settings.admin_password)
    user.token_version += 1
    db.query(AuthSession).filter(AuthSession.user_id == user.id).delete()
    db.commit()
PY

printf 'ADMIN_EMAIL=%s\nADMIN_PASSWORD=%s\n' \
  "$ADMIN_EMAIL" "$new_admin" > /root/.ai-ranking-os-initial-admin
chmod 600 /root/.ai-ranking-os-initial-admin
echo "secret_rotation=PASS"
