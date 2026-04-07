import gateway.infra.config
from gateway.adapters.telegram.callback_router import RadixCallbackRouterAdapter
from gateway.pkg.routing.radix_tree import RadixTree


def test_global_config_model_has_fields() -> None:
    fields = gateway.infra.config.GlobalConfig.model_fields
    assert "debug" in fields
    assert "grpc_server" in fields
    assert "http_server" in fields
    assert "telegram" in fields
    assert "valkey" in fields
    assert "profile_service" in fields
    assert "callback_routing" in fields


def test_radix_tree_literal_match() -> None:
    tree = RadixTree()
    tree.insert("menu:profile:view", "handle_profile_view", {})
    result = tree.match("menu:profile:view")
    assert result is not None
    assert result.handler_id == "handle_profile_view"
    assert result.path_params == {}


def test_radix_tree_wildcard_match() -> None:
    tree = RadixTree()
    tree.insert("like:{profile_id}", "handle_like", {"active": True})
    result = tree.match("like:42")
    assert result is not None
    assert result.handler_id == "handle_like"
    assert result.path_params == {"profile_id": "42"}
    assert result.requires == {"active": True}


def test_radix_tree_literal_priority_over_wildcard() -> None:
    tree = RadixTree()
    tree.insert("undo:last", "handle_undo", {})
    tree.insert("undo:{action}", "handle_undo_generic", {})
    result = tree.match("undo:last")
    assert result is not None
    assert result.handler_id == "handle_undo"


def test_radix_tree_no_match() -> None:
    tree = RadixTree()
    tree.insert("like:{profile_id}", "handle_like", {})
    result = tree.match("unknown:stuff")
    assert result is None


def test_radix_callback_router_adapter() -> None:
    adapter = RadixCallbackRouterAdapter()
    adapter.insert("super_like:{profile_id}", "handle_super_like", {"subscription": "PREMIUM"})
    result = adapter.match("super_like:999")
    assert result is not None
    assert result.handler_id == "handle_super_like"
    assert result.path_params == {"profile_id": "999"}
    assert result.requires == {"subscription": "PREMIUM"}
