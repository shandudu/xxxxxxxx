from backend.plugin.core import parse_plugin_config


def test_all_plugin_configurations_pass_runtime_validation() -> None:
    """Keep application startup from failing after the lightweight readiness check."""
    extend_plugins, app_plugins = parse_plugin_config()
    names = {plugin.name for plugin in extend_plugins}

    assert {'costing', 'finance'} <= names
    assert len(extend_plugins) == 24
    assert len(app_plugins) == 3
