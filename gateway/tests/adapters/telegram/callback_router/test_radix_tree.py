from pathlib import Path

from gateway.adapters.telegram.callback_router.radix_router_adapter import RadixCallbackRouterAdapter
from gateway.infra.callback_routes_yaml import load_routes_from_yaml_file
from gateway.pkg.routing.radix_tree import RadixTree


def test_insert_single_route():
    tree = RadixTree()
    tree.insert("like", "handle_like", {"active": True})

    assert "like" in tree.root.children
    node = tree.root.children["like"]
    assert node.is_terminal is True
    assert node.handler == "handle_like"
    assert node.requires == {"active": True}


def test_insert_nested_routes():
    tree = RadixTree()
    tree.insert("menu:profile:view", "handle_profile_view", {"active": True})
    tree.insert("menu:profile:edit", "handle_profile_edit", {"active": True})
    tree.insert("menu:settings", "handle_settings", {"active": True})

    assert "menu" in tree.root.children
    menu = tree.root.children["menu"]
    assert "profile" in menu.children
    profile = menu.children["profile"]
    assert "view" in profile.children
    assert "edit" in profile.children
    assert "settings" in menu.children


def test_match_exact():
    tree = RadixTree()
    tree.insert("like", "handle_like", {"active": True})

    result = tree.match("like")
    assert result is not None
    assert result.handler == "handle_like"
    assert result.requires == {"active": True}
    assert result.params == {}


def test_match_nested():
    tree = RadixTree()
    tree.insert("menu:profile:view", "handle_profile_view", {"active": True})

    result = tree.match("menu:profile:view")
    assert result is not None
    assert result.handler == "handle_profile_view"
    assert result.requires == {"active": True}


def test_match_with_params():
    tree = RadixTree()
    tree.insert(
        "super_like:{profile_id}",
        "handle_super_like",
        {"active": True, "subscription": "PREMIUM"},
    )

    result = tree.match("super_like:12345")
    assert result is not None
    assert result.handler == "handle_super_like"
    assert result.requires == {"active": True, "subscription": "PREMIUM"}
    assert result.params == {"profile_id": "12345"}


def test_match_multiple_params():
    tree = RadixTree()
    tree.insert("admin:ban:{user_id}", "handle_ban", {"role": "admin"})

    result = tree.match("admin:ban:987")
    assert result is not None
    assert result.handler == "handle_ban"
    assert result.requires == {"role": "admin"}
    assert result.params == {"user_id": "987"}


def test_match_no_route():
    tree = RadixTree()
    tree.insert("like", "handle_like", {"active": True})

    result = tree.match("dislike")
    assert result is None


def test_match_partial_path():
    tree = RadixTree()
    tree.insert("menu:profile:view", "handle_profile_view", {"active": True})

    result = tree.match("menu:profile")
    assert result is None


def test_requires_extracted():
    tree = RadixTree()
    tree.insert(
        "super_like:{profile_id}",
        "handle_super_like",
        {"active": True, "subscription": "PREMIUM"},
    )

    result = tree.match("super_like:123")
    assert result is not None
    assert result.requires["active"] is True
    assert result.requires["subscription"] == "PREMIUM"


def test_empty_tree():
    tree = RadixTree()
    result = tree.match("anything")
    assert result is None


def test_insert_same_path_twice():
    tree = RadixTree()
    tree.insert("like", "handle_like_v1", {"active": True})
    tree.insert("like", "handle_like_v2", {"active": False})

    result = tree.match("like")
    assert result is not None
    assert result.handler == "handle_like_v2"
    assert result.requires == {"active": False}


def test_complex_route():
    tree = RadixTree()
    tree.insert("billing:subscribe", "handle_subscribe")
    tree.insert("billing:boost", "handle_boost", {"active": True})
    tree.insert("billing:cancel", "handle_cancel", {"active": True})

    result1 = tree.match("billing:subscribe")
    assert result1 is not None
    assert result1.handler == "handle_subscribe"
    assert result1.requires == {}

    result2 = tree.match("billing:boost")
    assert result2 is not None
    assert result2.handler == "handle_boost"
    assert result2.requires == {"active": True}


def test_undo_last():
    tree = RadixTree()
    tree.insert("undo:last", "handle_undo", {"active": True})

    result = tree.match("undo:last")
    assert result is not None
    assert result.handler == "handle_undo"
    assert result.requires == {"active": True}


def test_load_routes_yaml_fixture():
    router = RadixCallbackRouterAdapter()
    fixture = Path(__file__).resolve().parent.parent.parent.parent / "fixtures" / "routes.yaml"
    load_routes_from_yaml_file(router, fixture)

    r = router.match("menu:profile:view")
    assert r is not None
    assert r.handler_id == "handle_profile_view"

    r2 = router.match("super_like:12345")
    assert r2 is not None
    assert r2.path_params == {"profile_id": "12345"}
