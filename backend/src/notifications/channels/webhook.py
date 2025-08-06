from __future__ import annotations

import hmac
import json
import logging
from hashlib import sha256
from typing import Any, Dict, Tuple

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def send(channel_config: Dict[str, Any], subject: str, body: str, extras: Dict[str, Any] | None = None) -> Tuple[bool, str]:
    """
    Generic JSON webhook sender.
    channel_config expects:
      - webhook_url: str
      - secret: optional, used to sign the body with HMAC SHA-256, header X-Signature
    The payload is provided via `extras["payload"]` if present, otherwise build a minimal envelope.
    """
    cfg = channel_config or {}
    url = cfg.get("webhook_url")
    if not url:
        return False, "missing_webhook_url"

    timeout = int(getattr(settings, "SCANNER_DEFAULTS", {}).get("HTTP_TIMEOUT_SECS", 5))
    payload: Dict[str, Any]
    if extras and isinstance(extras.get("payload"), dict):
        payload = extras["payload"]
    else:
        payload = {"subject": subject, "message": body}

    body_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    headers = {"Content-Type": "application/json"}
    secret = cfg.get("secret")
    if secret:
        signature = hmac.new(str(secret).encode("utf-8"), body_json.encode("utf-8"), sha256).hexdigest()
        headers["X-Signature"] = signature

    try:
        resp = requests.post(url, data=body_json, headers=headers, timeout=timeout)
        if 200 <= resp.status_code < 300:
            return True, f"{resp.status_code}"
        return False, f"non_2xx:{resp.status_code}"
    except Exception as e:
        logger.exception("generic webhook send failed: %s", e)
        return False, f"exception:{type(e).__name__}:{e}"