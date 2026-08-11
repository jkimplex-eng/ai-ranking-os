# BUG-002 — Data Credibility, Research Wizard & UX Stabilization

Дата проверки: 11 августа 2026. Ветка: `bugfix/bug-002-data-credibility`.

## Исправленные дефекты

| Причина | Решение | Файлы |
|---|---|---|
| Wizard показывал `Authentication required`, когда access token истекал | Добавлены single-flight refresh rotation и однократный повтор исходного запроса; при невозможности refresh показывается честное сообщение об истёкшей сессии | `frontend/src/api.ts`, `frontend/tests/app.spec.ts` |
| Состояние мастера терялось при F5 и browser history | Шаг, бренд, регион, язык и routing profile сохраняются в `sessionStorage` до отмены либо успешного запуска | `frontend/src/main.tsx` |
| Review не объяснял фактический план | Показаны возвращённые backend модели, estimated time и cost; отсутствующая оценка явно обозначается | `frontend/src/main.tsx`, `frontend/src/api.ts` |
| Dashboard содержал синтетические даты, рост и объяснения | Выводятся research ID/date, score timestamp/version, response provider/model/tokens/latency; explainability использует сохранённые ответы, сущности и источники | `frontend/src/main.tsx`, `frontend/src/ui.tsx` |
| Trend терял даты и связь с исследованиями | Точки содержат дату и research ID, tooltip показывает provenance, клик открывает соответствующий отчёт; диапазоны обозначают число точек, не вымышленные месяцы | `frontend/src/charts.tsx`, `frontend/src/main.tsx` |
| Benchmark сравнивал объект сам с собой | Benchmark скрыт до появления минимум двух объектов | `frontend/src/main.tsx` |
| Pipeline всегда изображался успешно завершённым | Timeline собирается из сохранённых ResearchTask, Response, GraphSnapshot и ResearchScore; показывает статусы, timestamps, provider/model, tokens, latency и cost | `frontend/src/api.ts`, `frontend/src/main.tsx` |
| Knowledge Graph был списком без связей | Экран строит направленный SVG по реальным GraphNode/GraphEdge, поддерживает поиск, type filter и details; для отсутствующих edges показан честный Empty State | `frontend/src/main.tsx`, `frontend/src/styles.css` |

## Browser verification

| Экран | URL | Реальный API | Результат и ручная проверка |
|---|---|---|---|
| Dashboard | `/` | `/research`, `/research/{id}/final-report`, `/research-tasks` | PASS: открыть, сверить ID/дату/provider с Report, нажать точку Trend |
| Wizard | `/research/new` | `/research/wizard/review`, `/research/wizard/run`, `/auth/refresh` | PASS: пройти до шага 4, F5, Back/Forward, выполнить review после истечения access token |
| Report | `/reports/latest` | `/research/{id}/final-report` | PASS: метрики, sources, entities, usage и cost только из report payload |
| Recommendations | `/recommendations` | `/research/{id}/recommendations` | PASS: metric, текущая величина и expected effect из repository |
| Knowledge Graph | `/knowledge-graph` | `/graph` | PASS: фильтр, поиск, node details и реальные directed edges |
| Providers | `/providers` | `/providers`, `/system/providers`, `/router/history` | PASS: отсутствующая конфигурация не обозначается как connected |

Автоматизированный Chromium smoke проверяет Login, deep links, F5, Back/Forward и прозрачный refresh токена. Ручная проверка: открыть URL, обновить страницу, выполнить Back/Forward, проверить Console и Network, затем сопоставить показанные значения с ответом указанного API.

## Проверки

- Ruff: PASS.
- Pytest: 287 PASS.
- Python compileall: PASS.
- TypeScript: PASS.
- ESLint: PASS.
- Frontend production build: PASS.
- Playwright Chromium: 3 PASS.
- OpenAPI: PASS в полном Pytest suite.
- Docker/Alembic/PostgreSQL runtime: локально не повторялись — Docker CLI отсутствует на рабочей станции; миграции и production runtime должны быть подтверждены CI/VPS до deployment sign-off.

## Ограничения

- Исторические исследования, созданные до сохранения отдельных stage timestamps, не могут показать несуществующие времена Normalization/Extraction; UI сообщает об отсутствии записи.
- Estimated time/cost показываются только если backend review их рассчитал; нулевое/отсутствующее значение не заменяется прогнозом frontend.
- Benchmark намеренно не показывается для выборки из одного объекта.
- Этот документ не заявляет production browser smoke до развёртывания ветки. Production verification фиксируется после успешных CI, migration и VPS runtime checks.
