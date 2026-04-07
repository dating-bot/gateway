from prometheus_client import Counter, Histogram

radix_tree_unmatched_total = Counter(
    "radix_tree_unmatched_total",
    "Callback data не совпало ни с одним маршрутом в radix tree",
)

rate_limit_exceeded_total = Counter(
    "rate_limit_exceeded_total",
    "Превышен rate limit для пользователя",
)

telegram_update_duration_seconds = Histogram(
    "telegram_update_duration_seconds",
    "Время обработки Telegram update (сек)",
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)
