"""Загрузка маршрутов callback_data из YAML-файла в CallbackRouterProtocol."""

import structlog
import yaml

from gateway.protocols.callback_router import CallbackRouterProtocol

log = structlog.stdlib.get_logger("gateway.infra.callback_routes_yaml")


def load_routes_from_yaml_file(path: str, router: CallbackRouterProtocol) -> None:
    with open(path, encoding="utf-8") as f:  # noqa: PTH123
        data: dict[str, dict[str, object]] = yaml.safe_load(f) or {}

    count = 0
    for path_pattern, route_cfg in data.items():
        handler_id = str(route_cfg.get("handler", ""))
        requires: dict[str, object] = dict(route_cfg.get("requires", {}))  # type: ignore[arg-type]
        if not handler_id:
            log.warning("маршрут без handler пропущен", path=path_pattern)
            continue
        router.insert(path_pattern, handler_id, requires)
        count += 1

    log.info("маршруты загружены", count=count, file=path)
