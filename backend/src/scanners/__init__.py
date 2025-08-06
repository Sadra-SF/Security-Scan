"""
Scanners plugin package.

Importing this package will import and register built-in placeholder adapters.
"""

# Re-export key symbols for convenience
from .base import ScanContext, FindingRecord, ScannerAdapter  # noqa: F401
from .constants import ScannerType, Severity  # noqa: F401
from . import registry  # noqa: F401

# Import built-in adapters to trigger registration on module import.
# These imports are intentionally at bottom to avoid circulars during type import.
# Static
from .static import deps_adapter as _deps_adapter  # noqa: F401
from .static import config_adapter as _config_adapter  # noqa: F401
# Dynamic
from .dynamic import zap_adapter as _zap_adapter  # noqa: F401
# New dynamic crawler-based plugins
from .dynamic import crawler_headers as _crawler_headers  # noqa: F401
from .dynamic import crawler_xss as _crawler_xss  # noqa: F401
from .dynamic import crawler_sqli as _crawler_sqli  # noqa: F401
# Network
from .network import nmap_adapter as _nmap_adapter  # noqa: F401