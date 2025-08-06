from __future__ import annotations

import logging
from typing import Any, Dict, Tuple

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def send_email(channel_config: Dict[str, Any], subject: str, body_text: str, body_html: str | None, extras: Dict[str, Any] | None = None) -> Tuple[bool, str]:
    """
    Send email using Django's email backend. Returns (success, info)
    channel_config expects:
      - recipients: list[str] or str
      - from_email: optional, overrides settings
    """
    recipients = channel_config.get("recipients") or channel_config.get("to") or []
    if isinstance(recipients, str):
        recipients = [recipients]
    if not recipients:
        return False, "missing_recipients"

    from_email = channel_config.get("from_email") or getattr(settings, "NOTIFICATIONS_DEFAULTS", {}).get("email_from") or getattr(
        settings, "DEFAULT_FROM_EMAIL", "no-reply@scanner.local"
    )

    try:
        if body_html:
            msg = EmailMultiAlternatives(subject=subject, body=body_text, from_email=from_email, to=recipients)
            msg.attach_alternative(body_html, "text/html")
            msg.send(fail_silently=False)
        else:
            send_mail(subject=subject, message=body_text, from_email=from_email, recipient_list=recipients, fail_silently=False)
        return True, "sent"
    except Exception as e:
        logger.exception("email send failed: %s", e)
        return False, f"exception:{type(e).__name__}:{e}"


def render_scan_summary(context: Dict[str, Any]) -> Tuple[str, str | None]:
    """
    Render text and html bodies for scan summary emails.
    """
    text = render_to_string("notifications/email/scan_summary.txt", context)
    html = None
    try:
        html = render_to_string("notifications/email/scan_summary.html", context)
    except Exception:
        html = None
    return text, html