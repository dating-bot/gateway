"""Radix Tree маршрутизатор callback_data.

Путь — строка с сегментами разделёнными «:», например:
  «like:{profile_id}», «menu:profile:edit», «admin:ban:{user_id}»

Сложность поиска: O(k), где k — число сегментов.
Wildcard {param} — именованный параметр; литерал имеет приоритет над wildcard.
"""

from __future__ import annotations

from dataclasses import dataclass, field

_WILDCARD_SENTINEL = "\x00"  # внутренний ключ для wildcard-узла


@dataclass
class _Node:
    children: dict[str, _Node] = field(default_factory=dict)
    # wildcard дочерний узел с именем параметра, или None
    wildcard_child: _WildcardNode | None = None
    # данные листа (если этот узел — конец маршрута)
    handler_id: str | None = None
    requires: dict[str, object] = field(default_factory=dict)


@dataclass
class _WildcardNode:
    """Узел-wildcard: захватывает один сегмент в param_name."""

    param_name: str
    node: _Node = field(default_factory=_Node)


@dataclass
class MatchResult:
    handler_id: str
    path_params: dict[str, str] = field(default_factory=dict)
    requires: dict[str, object] = field(default_factory=dict)


class RadixTree:
    """Prefix tree на сегментах пути callback_data.

    Инициализируется пустым; маршруты добавляются через insert().
    Потокобезопасен для одновременного чтения (writes только при старте).
    """

    def __init__(self) -> None:
        self._root = _Node()

    def insert(self, path: str, handler_id: str, requires: dict[str, object]) -> None:
        """Зарегистрировать маршрут.

        path: «like:{profile_id}» — сегменты через «:», {param} — wildcard.
        """
        segments = path.split(":")
        node = self._root
        for segment in segments:
            if segment.startswith("{") and segment.endswith("}"):
                param_name = segment[1:-1]
                if node.wildcard_child is None:
                    node.wildcard_child = _WildcardNode(param_name=param_name)
                node = node.wildcard_child.node
            else:
                if segment not in node.children:
                    node.children[segment] = _Node()
                node = node.children[segment]
        node.handler_id = handler_id
        node.requires = dict(requires)

    def match(self, path: str) -> MatchResult | None:
        """Найти маршрут по callback_data.

        Литеральный сегмент имеет приоритет над wildcard.
        Возвращает None если маршрут не найден.
        """
        segments = path.split(":")
        path_params: dict[str, str] = {}
        return self._match_node(self._root, segments, 0, path_params)

    def _match_node(
        self,
        node: _Node,
        segments: list[str],
        idx: int,
        path_params: dict[str, str],
    ) -> MatchResult | None:
        if idx == len(segments):
            if node.handler_id is not None:
                return MatchResult(
                    handler_id=node.handler_id,
                    path_params=dict(path_params),
                    requires=dict(node.requires),
                )
            return None

        segment = segments[idx]

        # Попробовать литеральный переход (приоритет над wildcard)
        if segment in node.children:
            result = self._match_node(node.children[segment], segments, idx + 1, path_params)
            if result is not None:
                return result

        # Попробовать wildcard
        if node.wildcard_child is not None:
            wc = node.wildcard_child
            path_params[wc.param_name] = segment
            result = self._match_node(wc.node, segments, idx + 1, path_params)
            if result is not None:
                return result
            # откатить
            del path_params[wc.param_name]

        return None
