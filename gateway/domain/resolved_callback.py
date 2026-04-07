from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ResolvedCallback:
    """Результат разбора callback_data через radix tree."""

    handler_id: str
    path_params: dict[str, str] = field(default_factory=dict)
    requires: dict[str, object] = field(default_factory=dict)
