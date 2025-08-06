from __future__ import annotations

# Ensure registry loads and plugins are registered on import
from scanners import registry  # noqa: F401
from scanners.registry import list_plugins, get_plugin  # noqa: F401

# Import plugin modules to trigger decorator-based registration (defensive)
import scanners.static.headers as _static_headers  # noqa: F401
import scanners.static.config as _static_config  # noqa: F401
import scanners.dynamic.headers as _dynamic_headers  # noqa: F401

# Newly added static scanners
import scanners.static.sqli as _static_sqli  # noqa: F401
import scanners.static.xss as _static_xss  # noqa: F401
import scanners.static.csrf as _static_csrf  # noqa: F401


def test_registry_imports_only() -> None:
    # Basic sanity: ensure our static and dynamic plugins are present
    keys = {p.key for p in list_plugins()}
    assert "static.headers" in keys
    assert "static.config" in keys
    assert "dynamic.headers" in keys
    # New static plugins
    assert "static.sqli" in keys
    assert "static.xss" in keys
    assert "static.csrf" in keys