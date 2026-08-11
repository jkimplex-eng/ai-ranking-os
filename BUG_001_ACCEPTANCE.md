# BUG-001 — Production Stabilization Acceptance

Дата проверки: 11 августа 2026. Ветка: `bugfix/bug-001-production-stabilization`. Production: `https://app.разуммаркета.рф`.

## Итог

Навигация SPA восстановлена, экраны подключены к реальным API, статические dashboard/report/provider значения удалены, production mock mode отключён, а полный Skinjestique-сценарий подтверждён через Web UI и PostgreSQL. PR: https://github.com/jkimplex-eng/ai-ranking-os/pull/7.

## Исправленные дефекты

| Дефект и причина | Решение | Основные файлы |
|---|---|---|
| F5/deep link возвращали 404; экран хранился только в React state | URL стал источником состояния, nginx получил SPA fallback, восстановление сессии выполняется до рендера | `frontend/src/main.tsx`, `frontend/nginx.conf` |
| Часть sidebar-разделов была заглушками или статическими блоками | Все 16 разделов получают данные через `ApiClient`; добавлены loading/error/empty states | `frontend/src/api.ts`, `frontend/src/main.tsx`, `frontend/src/styles.css` |
| Dashboard и Report показывали заранее заданные тренды, benchmark, insights и действия | Карточки, дельты, рекомендации, provider statistics и граф берутся только из research/report/analytics API | `frontend/src/main.tsx` |
| Provider Center показывал READY без runtime-проверки | Объединены registry, `/system/providers`, router history и реальная статистика последнего отчёта; отсутствующий ключ показывает `NOT_CONFIGURED` | `frontend/src/api.ts`, `frontend/src/main.tsx`, `backend/app/monitoring/service.py` |
| Admin/Product Analytics были видимы всем ролям | `/auth/me` возвращает реальные роли; меню и direct links защищены; RBAC API требует admin dependency | `authentication/router.py`, `authentication/schemas.py`, `rbac/router.py`, `frontend/src/main.tsx` |
| Прерванный worker навсегда занимал единственного агента | Старые активные execution переводятся в FAILED, задача — в BLOCKED, owner освобождается, событие журналируется | `execution_engine/service.py` |
| FAILED research продолжал строить score/graph/recommendations и выглядел успешным | Downstream запускается только для COMPLETED; wizard возвращает HTTP 409 и не показывает отчёт | `product/service.py`, `product/router.py`, `frontend/src/main.tsx` |
| Router обрывал Ollama через жёсткие 30 секунд, игнорируя provider timeout | Execution Plan использует metadata/provider/environment timeout; production Ollama — 180 секунд | `backend/app/llm_router/execution_plan.py` |
| Production Compose по умолчанию разрешал mocks | Production default и example изменены на `false`; CI override изолирован только внутри GitHub runner | `deployment/production/docker-compose.yml`, `deployment/production/.env.example`, `.github/workflows/ci.yml` |
| В production оставалась seed-организация | После backup удалена только `Demo Organization`; root demo seed scripts исключены из production image | `.dockerignore`; операция БД от 2026-08-11 |

## Browser Verification

Для каждого маршрута проверены открытие, F5, Back, Forward, deep link, отсутствие console/page errors, HTTP 4xx/5xx, `Coming Soon` и белого экрана.

| Раздел | URL | Основной API | Фактический результат |
|---|---|---|---|
| Dashboard | `/` | `GET /research`, `GET /research/{id}/final-report`, `GET /system/health` | PASS, реальные latest report/metrics |
| Research | `/research` | `GET /research` | PASS |
| Wizard | `/research/new` | `POST /research/wizard/review`, `POST /research/wizard/run` | PASS |
| Reports | `/reports` | `GET /reports` | PASS |
| Recommendations | `/recommendations` | `GET /research/{id}/recommendations` | PASS |
| Knowledge Graph | `/knowledge-graph` | `GET /graph` | PASS; корректный empty state при пустом snapshot |
| Competitors | `/competitors` | `GET /workspace/projects`, `GET /workspace/projects/{id}/competitors` | PASS |
| History | `/history` | `GET /research` | PASS, сортировка new → old |
| Notifications | `/notifications` | `GET /notifications`, `GET /notifications/summary` | PASS |
| Organizations | `/organizations` | `GET/POST /organizations`, members/activity/invitations | PASS; после удаления seed показан actionable empty state |
| Product Analytics | `/product-analytics` | `GET /product-analytics/dashboard` | PASS |
| Settings | `/settings` | `GET/PATCH /workspace`, `GET /api-keys`, `GET /providers` | PASS |
| Providers | `/providers` | `GET /providers`, `/system/providers`, `/router/history` | PASS |
| Feedback | `/feedback` | `GET /feedback` | PASS |
| Admin | `/admin` | admin users/reports/jobs/feedback/audit/health API | PASS для System Admin; direct access запрещён не-admin ролям |
| Profile | `/profile` | `GET /auth/me` | PASS |

Результаты браузеров:

- Chrome: route matrix PASS; реальный Skinjestique/Ollama smoke PASS.
- Edge: route matrix PASS.
- Firefox 153 (официальный Playwright Linux container): route matrix PASS. Локальный Windows headless Firefox не использован из-за ошибки SWGL test-host, не связанной с приложением.

Ручная проверка любого раздела: войти → открыть пункт sidebar → обновить страницу → Back → Forward → вставить URL в новую вкладку → убедиться, что заголовок/данные либо объяснённый Empty State отображаются, а DevTools Console/Network не содержит ошибок.

## Backend и production verification

Все frontend loaders используют HTTP API. FastAPI routes используют существующие Service/Repository/DI слои; production подключён к PostgreSQL и Redis. Static JSON/localStorage/fake repository не используются как источник экранных данных. В `sessionStorage` хранятся только access/refresh tokens.

Production runtime:

- `PROVIDER_MOCK_MODE=false`, `OLLAMA_MOCK_MODE=false`.
- Ollama: `READY`, runtime model `qwen2.5:3b`.
- Провайдеры без credentials: `NOT_CONFIGURED`, не `READY`.
- Demo organizations: 0; demo users: 0; перед очисткой создан backup `ai-ranking-20260811T113522Z.dump`.
- Test/demo utilities остаются только в исходниках для development/CI и исключены из production backend image.

Подтверждённый research `#28`:

- Research `COMPLETED`, 1/1 tasks, 0 failures, progress 100%.
- Execution `#36` `COMPLETED`, 1 attempt, 19,196 ms.
- Provider/model: `ollama` / `qwen2.5:3b`.
- Response `PROCESSED`, raw и normalized payload сохранены, error отсутствует.
- Usage: 59 input + 168 output = 227 tokens; cost 0.
- Score v1.0 сохранён; recommendations и immutable graph snapshot созданы.
- Entity/citation extraction для этого конкретного ответа вернул 0; UI честно показывает Empty State, sample graph не создаётся.

## RBAC

Проверены роли System Admin, Organization Admin, Analyst и Viewer на уровне permission/inheritance API tests. System/Organization Admin видят административные разделы; Analyst/Viewer не видят Admin/Product Analytics и получают экран запрета при direct link. Backend RBAC endpoints дополнительно защищены admin dependency. Production browser smoke выполнен под System Admin; искусственные production accounts не создавались.

## Автоматические проверки

| Проверка | Результат |
|---|---|
| Ruff | PASS |
| Pytest | PASS, 287 tests |
| Compileall | PASS |
| TypeScript | PASS |
| ESLint | PASS |
| Frontend Build | PASS |
| Playwright local | PASS |
| Production Playwright Chrome/Edge/Firefox | PASS |
| GitHub Actions | PASS, все 10 PR checks |
| Docker Build | PASS (CI и VPS) |
| Docker Runtime/health/readiness | PASS |
| Alembic upgrade/downgrade PostgreSQL 16 | PASS (CI); production upgrade PASS |
| OpenAPI contracts | PASS через API/contract tests |

## Smoke Test

Через Web UI выполнено: Login → Dashboard → Wizard → Private profile/Ollama → Run → Report → Recommendations → Knowledge Graph → Product Analytics → Notifications → Logout. Прямые API-вызовы для выполнения пользовательского сценария не использовались. После UI-теста данные сверены read-only SQL-запросами.

## Ограничения

- В исследовании `#28` локальная модель не вернула извлекаемые entity/citation элементы; это реальный результат модели, не дефект сохранения. Graph snapshot поэтому пуст.
- Исторические FAILED QA-запуски сохранены как execution history и не удалялись: это реальные ошибки, необходимые для аудита, а не demo-метрики.
- Внешние провайдеры без API keys намеренно остаются `NOT_CONFIGURED`; их live-вызовы не имитируются.
- Alembic downgrade проверяется только в изолированной PostgreSQL 16 среде CI, не на production базе.

BUG-001 ограничен стабилизацией. Новые функции и BUG-002 не начинались.
