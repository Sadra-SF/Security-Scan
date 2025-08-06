from __future__ import annotations

import logging
from typing import Any, Dict, Tuple

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def send(channel_config: Dict[str, Any], subject: str, body: str, extras: Dict[str, Any] | None = None) -> Tuple[bool, str]:
    """
    Send a Slack message via Incoming Webhook.
    channel_config expects:
      - webhook_url: str
    """
    url = (channel_config or {}).get("webhook_url")
    if not url:
        return False, "missing_webhook_url"

    timeout = int(getattr(settings, "SCANNER_DEFAULTS", {}).get("HTTP_TIMEOUT_SECS", 5))
    payload: Dict[str, Any] = {
        "text": f"{subject}\n{body}".strip(),
    }
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
        if 200 <= resp.status_code < 300:
            return True, f"{resp.status_code}"
        return False, f"non_2xx:{resp.status_code}"
    except Exception as e:
        logger.exception("slack webhook send failed: %s", e)
        return False, f"exception:{type(e).__name__}:{e}"