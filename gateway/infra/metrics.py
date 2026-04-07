from prometheus_client import Counter

radix_tree_unmatched_total = Counter(
    "radix_tree_unmatched_total",
    "Callback routes with no radix match",
)
