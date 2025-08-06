from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Protocol, Type

from .types import ScanContext, FindingRecord

logger = logging.getLogger(__name__)


class Plugin(Protocol):
    key: str
    name: str
    version: str
    type: str  # "static" | "dynamic"
    capabilities: List[str]

    def run(self, context: ScanContext) -> Iterable[FindingRecord]:
        ...


@dataclass
class PluginMeta:
    key: str
    name: str
    version: str
    type: str
    capabilities: List[str]


class _Registry:
    def __init__(self) -> None:
        self._plugins: Dict[str, Plugin] = {}

    def register(self, plugin: Plugin) -> None:
        key = getattr(plugin, "key", None)
        if not key:
            raise ValueError("Plugin must define a unique 'key'")
        if key in self._plugins:
            logger.warning("Plugin key '%s' already registered; overwriting.", key)
        self._plugins[key] = plugin
        logger.info("Registered scanner plugin: %s (%s)", key, getattr(plugin, "type", "unknown"))

    def get(self, key: str) -> Optional[Plugin]:
        return self._plugins.get(key)

    def all(self) -> List[Plugin]:
        return list(self._plugins.values())

    def by_type(self, typ: str) -> List[Plugin]:
        return [p for p in self._plugins.values() if getattr(p, "type", None) == typ]


registry = _Registry()


def scanner_plugin(*, key: str, type: str, name: Optional[str] = None, version: str = "0.1.0", capabilities: Optional[List[str]] = None):
    """
    Decorator to declare a scanner plugin and auto-register it.

    Usage:
        @scanner_plugin(key="static.headers", type="static", name="Security Headers")
        class HeadersPlugin:
            def run(self, context: ScanContext):
                yield FindingRecord(...)
    """
    def decorator(cls: Type[Any]) -> Type[Any]:
        # attach metadata
        setattr(cls, "key", key)
        setattr(cls, "type", type)
        setattr(cls, "name", name or key)
        setattr(cls, "version", version)
        setattr(cls, "capabilities", capabilities or [])
        # instantiate a singleton instance for registry
        instance = cls()  # type: ignore[call-arg]
        registry.register(instance)  # type: ignore[arg-type]
        return cls

    return decorator


# Convenience re-exports
register = registry.register
get_plugin = registry.get
list_plugins = registry.all
list_plugins_by_type = registry.by_type