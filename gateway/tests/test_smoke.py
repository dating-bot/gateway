import gateway.infra.config


def test_global_config_model_has_fields() -> None:
    fields = gateway.infra.config.GlobalConfig.model_fields
    assert "debug" in fields
    assert "grpc_server" in fields
