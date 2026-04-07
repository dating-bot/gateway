# Gateway / bot-service — план работ

Единый деплой: **gateway = bot-service**. Разрешение `callback_data` и ACL — in-process (без gRPC «бот → gateway»). Детали и обоснования: [`../docs/gateway_bot_service_plan.md`](../docs/gateway_bot_service_plan.md).

## Текущее состояние

- Готово: hex-слой (`ResolvedCallback`, `CallbackRouterProtocol`, `ResolveCallbackRouteUsecase`, `RadixCallbackRouterAdapter`), загрузка YAML, тесты.
- Сейчас: **aiohttp** (GET `/health`, `/ready`, `/metrics`, POST webhook) + **aiogram 3** + **Dishka** и **gRPC** в одном процессе; маршруты из `routes.yaml` (см. `config.toml` → `callback_routing.routes_file`).
- Valkey: **Redis** URL в `valkey.url` — FSM + rate limit + lock; при пустом URL — `MemoryStorage`, middleware без Redis (no-op).
- Сделано: цепочка **RateLimit → Lock → radix+ACL (stub)** на `update`; счётчик `radix_tree_unmatched_total` + `/metrics`.
- Нет: реальная проверка ACL (profile/billing), readiness с Valkey, cluster Valkey.

---

## Часть A — ядро bot-service в `gateway/`

### Принятые решения (пока)

- **HTTP:** **aiohttp** (`web.Application`) + aiogram 3 — без Litestar/FastAPI в этом шаге.
- **Входящий gRPC:** **оставляем** (Ping + health) параллельно с HTTP до отдельного решения перенести health на HTTP.
- **Valkey:** **один инстанс** (compose / один endpoint); переход на cluster / шардирование — **позже**, конфиг и клиент заложить с запасом.
- **IP-лимит / Bloom / edge anti-DDoS:** **не закладываем** в текущий чеклист — вернёмся отдельно.

### 1. HTTP webhook + aiogram + DI

- [x] Зависимости: aiogram 3, **aiohttp**.
- [x] Роут POST для Telegram webhook (`SimpleRequestHandler`); проверка `secret_token` через `webhook_secret_token` (если задан в `setWebhook`).
- [x] Интеграция **dishka**: `AiogramProvider`, `setup_dishka(..., auto_inject=True)`, пример `FromDishka[ResolveCallbackRouteUsecase]` в [`gateway/app/telegram/handlers.py`](gateway/app/telegram/handlers.py).
- [x] Единый процесс: **aiohttp** (`AppRunner`/`TCPSite`) + существующий **gRPC** (см. [`gateway/app/server/server.py`](gateway/app/server/server.py)).

### 2. Конфиг и загрузка маршрутов

- [x] Поле в `GlobalConfig`: путь к `routes.yaml` (env `GATEWAY_*`, TOML).
- [x] При старте: `load_routes_from_yaml_file` → один экземпляр `RadixCallbackRouterAdapter` в DI (не `default_factory` с пустым деревом).

### 3. Valkey: FSM и middleware

- [x] Подключить Valkey как storage для FSM aiogram (**один инстанс** на первом этапе; cluster — позже).
- [x] `RateLimitMiddleware`: ~30 actions/min на uid (`INCR` + TTL).
- [x] `LockMiddleware`: `lock:user:{uid}` (`SET NX EX`); на одном реплике pod можно упростить или отложить.

### 4. Цепочка обработки update

- [x] Порядок: RateLimit → Lock → radix (`ResolveCallbackRouteUsecase`) → ACL → handler.
- [x] `AclMiddleware`: читает `requires` из `ResolvedCallback`, порт проверки прав (заглушка → Valkey/HTTP к profile/billing).

### 5. Наблюдаемость

- [x] Счётчик `radix_tree_unmatched_total` при отсутствии совпадения маршрута (одна точка инкремента).
- [x] HTTP `/health` и `/ready` (и при необходимости `/metrics` для Prometheus).

### 6. Входящий gRPC

- **Сейчас:** оставляем gRPC (health / Ping / будущие RPC) рядом с aiohttp.
- [ ] Позже (по [`../docs/gateway_bot_service_plan.md`](../docs/gateway_bot_service_plan.md)): при желании перенести readiness на HTTP и удалить grpclib — убрать сервер, proto из рантайма, обновить `docker-compose` / entrypoint.

### 7. Дубли кода

- [ ] При появлении черновика `dating_bot/bot` — свести radix/YAML к одному месту в `gateway/`.

---

## Часть B — Этап 2 продукта (вне только gateway)

Зависит от остальных сервисов ([`../docs/dating_bot_docs_v5.md`](../docs/dating_bot_docs_v5.md), «Этап 2 — bot-service + анкета»).

- [ ] **profile-service**: CRUD, MinIO, presigned URL, `profile.updated` → RabbitMQ.
- [ ] FSM анкеты (5 шагов) в боте + вызовы profile-service.
- [ ] Инфра: RabbitMQ, общие миграции/compose по монорепо.

---

## Порядок внедрения (рекомендуемый)

1. Минимальный HTTP webhook (aiohttp) + aiogram (200 OK) + HTTP `/health` / `/ready` при необходимости; gRPC уже есть.
2. Конфиг + загрузка `routes.yaml` + radix в DI.
3. Valkey (один инстанс): FSM + RateLimit + Lock.
4. Цепочка radix + ACL (заглушки).
5. Метрики и тесты.
6. По мере надобности — Valkey cluster, затем опционально упрощение/удаление gRPC (п. 6).
7. Параллельно/после — часть B (profile-service, анкета).
