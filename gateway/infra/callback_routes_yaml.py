from pathlib import Path
from typing import TYPE_CHECKING, cast

import yaml

if TYPE_CHECKING:
    from gateway.adapters.telegram.callback_router.radix_router_adapter import RadixCallbackRouterAdapter


def _mapping_str_object(obj: object) -> dict[str, object]:
    if not isinstance(obj, dict):
        return {}
    raw = cast("dict[object, object]", obj)
    return {k: v for k, v in raw.items() if isinstance(k, str)}


def load_routes(config_path: str | Path) -> dict[str, dict[str, object]]:
    path = Path(config_path)
    if not path.is_file():
        msg = f"Config file not found: {config_path}"
        raise FileNotFoundError(msg)

    with path.open(encoding="utf-8") as f:
        loaded = cast("object", yaml.safe_load(f))

    if not isinstance(loaded, dict):
        raise TypeError("Invalid config: root must be a mapping")

    root_map = cast("dict[object, object]", loaded)
    routes_obj = root_map.get("routes")
    if not isinstance(routes_obj, dict):
        raise TypeError("Invalid config: 'routes' key not found or not a mapping")

    routes_dict = cast("dict[object, object]", routes_obj)
    out: dict[str, dict[str, object]] = {}
    for key_obj, val in routes_dict.items():
        route_key = key_obj if isinstance(key_obj, str) else str(key_obj)
        if isinstance(val, dict):
            out[route_key] = _mapping_str_object(cast("object", val))
        else:
            out[route_key] = {}

    return out


def load_routes_from_yaml_file(
    router: "RadixCallbackRouterAdapter",
    config_path: str | Path,
) -> None:
    routes = load_routes(config_path)

    for route_key, route_data in routes.items():
        path_val = route_data.get("path", route_key)
        path = path_val if isinstance(path_val, str) else route_key
        handler_val = route_data.get("handler")
        if not isinstance(handler_val, str) or not handler_val:
            continue

        requires_raw = route_data.get("requires", {})
        requires = _mapping_str_object(requires_raw)

        router.register_route(path, handler_val, requires)
