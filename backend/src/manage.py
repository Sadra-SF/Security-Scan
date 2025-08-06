#!/usr/bin/env python
import os
import sys
from pathlib import Path

if __name__ == "__main__":
    # Ensure project root in path
    ROOT = Path(__file__).resolve().parent.parent.parent
    sys.path.append(str(ROOT))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "api_server.settings")
    try:
        from django.core.management import execute_from_command_line  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable?"
        ) from exc
    execute_from_command_line(sys.argv)