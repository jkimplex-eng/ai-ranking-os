# TASK-1100 — Existing Website Technical Audit

Дата аудита: 2026-08-07  
VPS: `72.56.33.7`  
Режим: только чтение; файлы и конфигурация на VPS не изменялись, сервисы не перезапускались.

## Резюме

На VPS работает существующий продукт «РазумМаркет»: статический лендинг на основном домене и экспортированное Expo/React-приложение по пути `/agent/`. Его API — отдельный FastAPI-проект Ozon AI Agent, запущенный через Supervisor на порту `8000`. AI Ranking OS на сервере не обнаружен.

Рекомендуется **вариант В: развернуть AI Ranking OS на отдельном поддомене `app.разуммаркета.рф`**. Это сохраняет существующие URL и отделяет новый продукт от уже работающих лендинга, frontend и API.

## 1. Технологический стек

### Основной сайт

- Домен: `https://разуммаркета.рф/` (`xn--80aaatitma6afyf.xn--p1ai`).
- Тип: статический лендинг.
- Реализация: обычные HTML, CSS и JavaScript; серверная обработка отдельных PHP-файлов через PHP-FPM 8.3.
- Каталог: `/var/www/landing`.
- Основной файл: `/var/www/landing/index.html`.
- Признаков Next.js, Vue, Nuxt, Laravel, Django, WordPress, Bitrix, Astro или Svelte в активном сайте не найдено.

### Существующее приложение

- URL: `https://разуммаркета.рф/agent/`.
- Frontend: Expo Router, React 19.2.3, React Native 0.86 и React Native Web.
- На сервере опубликован статический Expo web export в `/var/www/landing/agent`.
- Исходный frontend найден в `/root/ozon-ai-agent-mobile-stage/mobile`.
- Nginx использует SPA fallback на `/agent/index.html` и отдельно обслуживает `/_expo/`.

### Существующий backend

- Проект: Ozon AI Agent, а не AI Ranking OS.
- Стек: Python 3.11+, FastAPI, Uvicorn, Pydantic v2, psycopg/psycopg_pool, PostgreSQL.
- Каталог: `/root/ozon-ai-agent`.
- Python-пакет: `/root/ozon-ai-agent/src/ozon_agent`.
- Запуск: `uvicorn ozon_agent.api.app:app --host 0.0.0.0 --port 8000`.
- OpenAPI: `Ozon AI Agent API`, версия `0.1.0`, 33 пути.
- Локальные проверки: `/health` — 200, `/docs` — 200, `/openapi.json` — 200, `/` — 404.
- AI Ranking OS и каталоги с именами `ai-ranking-os`/`ai_ranking_os` на VPS не найдены.

## 2. Расположение и управление

| Компонент | Расположение / способ запуска |
|---|---|
| Статический лендинг | `/var/www/landing` |
| Expo web frontend | `/var/www/landing/agent` |
| Исходный Expo frontend | `/root/ozon-ai-agent-mobile-stage/mobile` |
| Ozon AI Agent backend | `/root/ozon-ai-agent` |
| AI Ranking OS backend | На VPS не обнаружен |
| Активный Nginx vhost | `/etc/nginx/sites-enabled/landing` |
| TLS-сертификат | `/etc/letsencrypt/live/xn--80aaatitma6afyf.xn--p1ai/` |
| Supervisor | `ozon-api`, `ozon-sheets-watch`, `ozon-telegram-bot` |
| Docker Compose проекта Ozon | `/root/ozon-ai-agent/docker-compose.yml` |
| Активные Compose-проекты | Нет |
| Основной Git-репозиторий backend | `/root/ozon-ai-agent`, ветка `feature/telegram-business-ui` |
| Дополнительные Git-репозитории | `/root/ollama-bot`, `/root/betting-agent-ai` |
| GitHub Actions runner | `/home/ozon-agent/actions-runner` |

У Ozon-проекта также присутствуют Git worktree/stage-каталоги для mobile, crossdock и daily SKU. Они не являются развертыванием AI Ranking OS.

## 3. Инфраструктура и работающие сервисы

### Docker

- Docker Server `29.6.0` установлен и работает.
- Docker Compose `v5.1.4` установлен.
- `docker ps` пуст: запущенных контейнеров нет.
- `docker compose ls` возвращает пустой список.
- Compose-файлы присутствуют, но активный сайт и API сейчас запущены непосредственно на хосте.

### Nginx и reverse proxy

- Nginx `1.24.0` слушает публичные порты `80` и `443`.
- HTTP перенаправляется на HTTPS.
- `/` обслуживается статически из `/var/www/landing`.
- `/agent/` обслуживает статический Expo frontend.
- `/agent-api/` проксируется на `http://127.0.0.1:8000/`.
- `/mobile/v1/` проксируется на `http://127.0.0.1:8000` с сохранением пути.
- Публичного маршрута `/api/` для AI Ranking OS нет.

### SSL

- Сертификат: Let's Encrypt, CN основного punycode-домена.
- Действует с `2026-07-22 12:11:42 UTC` до `2026-10-20 12:11:41 UTC`.
- Для нового поддомена потребуется отдельное расширение/получение сертификата.

### Сервисы и порты

| Сервис | Состояние | Интерфейс |
|---|---|---|
| Nginx | Работает | `0.0.0.0:80`, `0.0.0.0:443` |
| Ozon FastAPI/Uvicorn | Работает под Supervisor | `0.0.0.0:8000` |
| PostgreSQL 16 | Работает | только `127.0.0.1/[::1]:5432` |
| Ollama | Работает | только `127.0.0.1:11434` |
| PHP 8.3 FPM | Работает | Unix socket |
| Supervisor | Работает | управляет тремя Ozon-процессами |
| Docker/containerd | Работают | активных контейнеров нет |
| Redis | Неактивен; порт `6379` не слушается | — |
| PM2 | systemd-служба присутствует | активных PID приложений не найдено |
| GitHub Actions runner | Работает | локальный runner репозитория Ozon |

Порт `8000` слушает на всех интерфейсах. Для текущего API это лишняя внешняя экспозиция: при последующем hardening его следует привязать к loopback или внутренней Docker-сети. Это рекомендация; в рамках аудита конфигурация не изменялась.

## 4. Текущее обслуживание домена

Основной домен уже является работающим публичным сайтом, а не пустой заглушкой:

- `/` — лендинг «РазумМаркет»;
- `/agent/` — существующее Expo/React web-приложение;
- `/agent-api/` и `/mobile/v1/` — маршруты существующего Ozon FastAPI;
- PHP включен для файлов `*.php`.

Следовательно, размещение нового большого приложения внутри текущих каталогов или маршрутов создаст тесную связь с несвязанным продуктом и риск конфликтов deployment, API paths, SPA fallback и cookies.

## 5. Единственная рекомендуемая схема интеграции

### Вариант В — `app.разуммаркета.рф`

Развернуть AI Ranking OS как самостоятельное приложение на поддомене:

```text
Internet
  ├── разуммаркета.рф
  │     ├── /              → текущий статический лендинг
  │     ├── /agent/        → текущий Expo web export
  │     └── /agent-api/    → текущий Ozon FastAPI :8000
  │
  └── app.разуммаркета.рф
        └── Nginx vhost
              ├── /        → AI Ranking OS frontend
              └── /api/    → AI Ranking OS FastAPI в изолированной сети
```

Почему выбран этот вариант:

1. Не изменяет публичные маршруты существующего сайта.
2. Не смешивает AI Ranking OS с несвязанным Ozon AI Agent.
3. Исключает конфликт с уже занятыми `/agent/`, `/agent-api/`, `/mobile/v1/` и портом `8000`.
4. Позволяет независимо выпускать, масштабировать, откатывать и мониторить AI Ranking OS.
5. Дает отдельную область безопасности для cookies, CORS, rate limiting и OAuth redirects.

Варианты интеграции внутрь текущего проекта и размещения по `/app` не рекомендуются.

## 6. Необходимые изменения для развертывания

Ниже перечислен план будущих изменений; в ходе данного аудита они не выполнялись.

1. Создать DNS-запись `A` для `app.разуммаркета.рф` на `72.56.33.7`; `AAAA` добавлять только при фактически настроенном IPv6.
2. Разместить Git checkout AI Ranking OS в отдельном каталоге, например `/opt/ai-ranking-os`; не использовать `/var/www/landing` и `/root/ozon-ai-agent`.
3. Запускать production Compose отдельным project name и отдельной сетью: `api`, `worker`, `postgres`, `redis` и frontend.
4. Не публиковать PostgreSQL и Redis наружу. API привязать к loopback либо оставить только во внутренней Docker-сети.
5. Не занимать порт `8000`; для локального upstream использовать отдельный порт, например `127.0.0.1:8100`, если API публикуется на хост.
6. Создать отдельный Nginx vhost для `app.разуммаркета.рф`, настроить proxy headers, WebSocket/streaming, ограничения размера запроса и timeouts согласно контрактам приложения.
7. Выпустить Let's Encrypt сертификат для нового поддомена и проверить автоматическое продление.
8. Использовать отдельные PostgreSQL database/role и отдельный Redis instance/namespace; не смешивать данные с базой Ozon Agent.
9. Хранить секреты вне Git, добавить backup/restore, healthchecks, readiness, централизованные логи и алерты.
10. Перед переключением DNS выполнить Alembic upgrade, smoke test `/health`, OpenAPI validation и полный end-to-end сценарий в изолированном окружении.

## 7. Рекомендуемая целевая архитектура

- **Edge:** один системный Nginx, отдельные server blocks для основного домена и `app`.
- **Deployment:** изолированный production Docker Compose AI Ranking OS с фиксированными image tags и healthchecks.
- **Application:** frontend и FastAPI API одного продукта; фоновые задачи выполняет отдельный worker.
- **Data:** отдельные PostgreSQL 16 и Redis 8, доступные только внутри compose network; persistent volumes и резервное копирование.
- **Operations:** отдельный deploy user вместо запуска приложения из `/root`, CI/CD с миграциями и rollback gate, Prometheus metrics и structured logs.
- **Security:** наружу открыты только `22`, `80`, `443`; application ports, PostgreSQL, Redis и Ollama закрыты firewall и Docker publishing rules.

## 8. Ограничения аудита

- Аудит выполнен без чтения секретов, содержимого пользовательских submissions и переменных окружения процессов.
- Конфигурация DNS-провайдера и внешняя система резервного копирования не были доступны из файловой системы VPS.
- Фактическое production-развертывание AI Ranking OS отсутствует, поэтому его runtime, миграции и интеграционные проверки на этом VPS оценить невозможно.

## Итог

Существующий домен и его маршруты уже используются отдельным продуктом. AI Ranking OS следует развернуть независимо на **`app.разуммаркета.рф`** с отдельным Nginx vhost и изолированным production Compose. Это минимально влияет на текущую систему и сохраняет четкие границы между продуктами.
