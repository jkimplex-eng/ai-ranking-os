# Sprint 11 — Production Deployment Report

Дата: 2026-08-07  
Ветка: `feature/sprint-11-production-deployment`  
Целевой VPS: `72.56.33.7`

## Статус

Production-инсталляция AI Ranking OS развёрнута изолированно в `/opt/ai-ranking-os`. Все шесть
Compose-сервисов healthy, полный Skinjestique pipeline прошёл через Web UI и API. Host Nginx имеет
отдельный HTTP bootstrap vhost; существующий лендинг и Ozon Agent не изменялись.

Публичный выпуск по `https://app.разуммаркета.рф` ожидает внешнюю DNS A-запись и ручной выпуск
Let's Encrypt сертификата. Автоматическая выдача сертификата намеренно не выполнялась согласно
TASK-1104. До выполнения этих двух операций Sprint технически готов к переключению, но публичный
HTTPS acceptance gate остаётся заблокирован внешней конфигурацией.

## Реализованные задачи

- TASK-1101/1102: отдельный production deployment и Compose.
- TASK-1103/1104: внутренний edge Nginx, отдельные host bootstrap/HTTPS vhost templates и ACME
  инфраструктура.
- TASK-1105: development/staging/production examples; production secrets только в `.env` с mode
  `600`.
- TASK-1106: PostgreSQL 16, Alembic 0001→0042, downgrade/upgrade, backup и restore validation.
- TASK-1107: Redis 8 с authentication, persistence, memory policy и degraded readiness mode.
- TASK-1108: `/health`, `/live`, `/ready`, `/metrics`, resource status и component monitoring.
- TASK-1109: JSON request logging с request/user/research/execution/provider IDs и latency.
- TASK-1110: deploy, rollback, backup, restore и smoke scripts.
- TASK-1111/1112: API smoke и браузерный Skinjestique production E2E.
- TASK-1113/1114: эксплуатационная документация, Python/API и Playwright acceptance tests.

## Архитектура развёртывания

```text
Host Nginx :80/:443
  ├── разуммаркета.рф              → существующий landing/Ozon Agent (без изменений)
  └── app.разуммаркета.рф          → 127.0.0.1:8100
                                         │
                                  Compose Nginx
                                    ├── /       → frontend:8080
                                    └── /api/   → backend:8000
                                                       ├── PostgreSQL 16
                                                       └── Redis 8
                                  worker → PostgreSQL/Redis
```

Наружу из Compose опубликован только `127.0.0.1:8100`. PostgreSQL, Redis, backend и frontend не
публикуют host ports.

## Структура

```text
deployment/production/
  docker-compose.yml
  .env.example
  nginx/
    internal.conf
    host-bootstrap.conf.example
    host-vhost.conf.example
  scripts/
    deploy.sh
    rollback.sh
    backup.sh
    restore.sh
    smoke_test.py
  backups/
  monitoring/prometheus.yml
```

Frontend реализован в `frontend/` на React, TypeScript и Vite. Он оркестрирует только существующие
API: authentication, wizard review/run и final report.

## Compose-сервисы

| Сервис | Назначение | Health |
|---|---|---|
| `postgres` | PostgreSQL 16 | `pg_isready` |
| `redis` | Redis 8, AOF, authenticated | authenticated `PING` |
| `backend` | FastAPI production API | `/ready` |
| `worker` | background worker | process health + Redis heartbeat |
| `frontend` | immutable web build | `/healthz` |
| `nginx` | routing/security/cache edge | `/health` |

## Переменные окружения

Ключевые группы: build/version, PostgreSQL, Redis, JWT/authentication, initial admin, provider keys,
pool limits, worker/process settings, logging and backup retention. Полный безопасный шаблон находится
в `deployment/production/.env.example`; реальные значения не включены в Git.

Первичные credentials хранятся только на VPS в `/root/.ai-ranking-os-initial-admin` с mode `600`.

## Первый запуск, обновление и откат

- Первый запуск: заполнить `.env`, затем `./scripts/deploy.sh`.
- Обновление: backup → reviewed immutable commit/tag → `deploy.sh` → smoke/E2E.
- Откат: установить `ROLLBACK_IMAGE_TAG` и выполнить `rollback.sh`; schema rollback проводится
  отдельно после проверки совместимости.
- Подробности: `docs/FIRST_DEPLOY.md`, `docs/Deployment.md`, `docs/Operations.md`.

## Результаты проверок

| Проверка | Результат |
|---|---|
| Ruff | PASS |
| Pytest | 222 PASS |
| Python coverage | 94% (13,932 statements) |
| Compileall | PASS |
| ESLint | PASS |
| TypeScript | PASS |
| Vite production build | PASS |
| Playwright local | PASS |
| Playwright production Web UI | 2 PASS |
| Docker backend build | PASS |
| Docker frontend build | PASS |
| Production Compose validation | PASS |
| Six service healthchecks | PASS |
| PostgreSQL migration upgrade | PASS, head `0042` |
| PostgreSQL downgrade `0042→0041` | PASS |
| PostgreSQL re-upgrade `0041→0042` | PASS |
| Backup | PASS |
| Restore into isolated validation DB | PASS, revision `0042` |
| API production smoke | PASS, research `COMPLETED` |
| Skinjestique browser flow | PASS, report rendered |
| GitHub Actions | PASS on implementation commits |

## Новые API и тесты

Новые operational API: `GET /live`, `GET /ready`, `GET /system/resources`. Существующие API не
удалялись и не переименовывались.

Добавлены три Python production acceptance tests и два Playwright tests. Полный Python suite:
222 tests; полный browser suite: 2 tests.

## Миграции

Новых schema migration в Sprint 11 не потребовалось. Итоговая Alembic revision — `0042`; её upgrade
и downgrade проверены на production PostgreSQL.

## Известные ограничения

1. DNS `app.разуммаркета.рф` пока не возвращает A-запись. Необходимо направить его на
   `72.56.33.7`.
2. После распространения DNS необходимо вручную выпустить Let's Encrypt сертификат и заменить
   bootstrap vhost на HTTPS template. Только тогда публичный URL сможет пройти финальный HTTPS gate.
3. Production установлен с `PROVIDER_MOCK_MODE=true`, поскольку реальные provider secrets не были
   предоставлены. Весь pipeline воспроизводим, но ответы провайдеров mock.
4. Prometheus scrape configuration подготовлена, однако отдельный Prometheus container намеренно не
   добавлен к обязательному application stack.

## Следующее действие

После настройки DNS и ручного TLS выполнить smoke и Playwright по
`https://app.разуммаркета.рф`. Затем PR готов к архитектурному review. Sprint 12 не начат.
