from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResolvedCallback:
    handler_id: str
    path_params: dict[str, str]
    requires: dict[str, object]
