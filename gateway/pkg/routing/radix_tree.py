from dataclasses import dataclass, field

__all__ = ["MatchResult", "RadixNode", "RadixTree"]


@dataclass
class MatchResult:
    handler: str
    requires: dict[str, object]
    params: dict[str, str]


@dataclass(slots=True)
class RadixNode:
    children: dict[str, "RadixNode"] = field(default_factory=dict)
    value: str = ""
    handler: str | None = None
    requires: dict[str, object] = field(default_factory=dict)
    is_terminal: bool = False
    param_name: str | None = None


@dataclass(slots=True)
class RadixTree:
    root: RadixNode = field(default_factory=RadixNode)

    def insert(
        self,
        path: str,
        handler: str,
        requires: dict[str, object] | None = None,
    ) -> None:
        if not path:
            return

        req: dict[str, object] = dict(requires) if requires is not None else {}
        segments = path.split(":")
        current = self.root

        for i, raw_segment in enumerate(segments):
            is_last = i == len(segments) - 1

            param_name: str | None = None
            if raw_segment.startswith("{") and raw_segment.endswith("}"):
                param_name = raw_segment[1:-1]
                seg = "*"
            else:
                seg = raw_segment

            if seg not in current.children:
                new_node = RadixNode(value=seg)
                if seg == "*":
                    new_node.param_name = param_name
                current.children[seg] = new_node

            current = current.children[seg]

            if is_last:
                current.is_terminal = True
                current.handler = handler
                current.requires = req

    def match(self, path: str) -> MatchResult | None:
        if not path:
            return None

        segments = path.split(":")
        return self._match_recursive(self.root, segments, 0, {})

    def _match_recursive(
        self,
        node: RadixNode,
        segments: list[str],
        index: int,
        params: dict[str, str],
    ) -> MatchResult | None:
        if index == len(segments):
            if node.is_terminal and node.handler is not None:
                return MatchResult(
                    handler=node.handler,
                    requires=node.requires,
                    params=params,
                )
            return None

        segment = segments[index]

        if segment in node.children:
            result = self._match_recursive(
                node.children[segment],
                segments,
                index + 1,
                params,
            )
            if result:
                return result

        if "*" in node.children:
            param_node = node.children["*"]
            new_params = {**params, param_node.param_name: segment} if param_node.param_name else params
            return self._match_recursive(
                param_node,
                segments,
                index + 1,
                new_params,
            )

        return None
