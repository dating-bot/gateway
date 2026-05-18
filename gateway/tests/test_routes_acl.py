from pathlib import Path

import yaml


def test_profile_edit_routes_are_not_gated_by_active_acl() -> None:
    routes_path = Path(__file__).parent / "fixtures" / "routes.yaml"
    routes = yaml.safe_load(routes_path.read_text(encoding="utf-8"))

    assert routes["menu:profile:edit"]["requires"] == {}
    assert routes["profile:photos:menu"]["requires"] == {}
    assert routes["photos:add"]["requires"] == {}
    assert routes["photos:del:{photo_id}"]["requires"] == {}
    assert routes["edit:{field}"]["requires"] == {}
