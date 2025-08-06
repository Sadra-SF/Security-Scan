from __future__ import annotations

# Import tasks to ensure Celery task registration/importability
# and services for planning helpers
from scans.tasks import start_scan, run_static_scan, run_dynamic_scan, aggregate_results  # noqa: F401
from scans import services  # noqa: F401


def test_imports_only() -> None:
    # This is a placeholder to allow pytest to collect the module successfully.
    assert callable  # trivial assertion to keep test frameworks happy