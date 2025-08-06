from __future__ import annotations

import hmac
import json
import logging
from hashlib import sha256
from typing import Any, Dict, List, Tuple

import requests
from celery import shared_task
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.template.loader import render_to_string

from notifications.models import NotificationChannel, NotificationRule
from scans.models import Scan

logger = logging.getLogger(__name__)


# ---------------------------
# Helpers
# ---------------------------

SEVERITY_ORDER = ["info", "low", "medium", "high", "critical"]
EVENT_MAP = {
    "scan.completed": "scan_completed",
    "scan.failed": "scan_completed",  # reuse same rule event for completion/failure at minimal scope
    "severity.threshold": "scan_completed",  # threshold based on scan summary
}


def _severity_at_or_above(summary: Dict[str, Any], min_sev: str) -> bool:
    by_sev = (summary or {}).get("by_severity", {}) or {}
    try:
        idx = SEVERITY_ORDER.index(min_sev.lower())
    except ValueError:
        idx = SEVERITY_ORDER.index("high")
    for s in SEVERITY_ORDER[idx:]:
        if int(by_sev.get(s, 0) or 0) > 0:
            return True
    return False


def _safe_requests_post(url: str, json_payload: Dict[str, Any], headers: Dict[str, str] | None = None) -> Tuple[bool, str]:
    try:
        timeout = int(getattr(settings, "SCANNER_DEFAULTS", {}).get("HTTP_TIMEOUT_SECS", 5))
        resp = requests.post(url, json=json_payload, headers=headers or {}, timeout=timeout)
        if 200 <= resp.status_code < 300:
            return True, f"{resp.status_code}"
        return False, f"non_2xx:{resp.status_code}"
    except Exception as e:
        return False, f"exception:{type(e).__name__}:{e}"


def _render_email(scan: Scan, context: Dict[str, Any]) -> Tuple[str, str]:
    txt = render_to_string("notifications/email/scan_summary.txt", context)
    try:
        html = render_to_string("notifications/email/scan_summary.html", context)
    except Exception:
        html = ""
    return txt, html


def _redact_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    redact_keys = {"token", "secret", "password", "api_key", "webhook_url"}
    out: Dict[str, Any] = {}
    for k, v in (cfg or {}).items():
        if k.lower() in redact_keys:
            out[k] = "***redacted***"
        else:
            out[k] = v
    return out


def _build_context(scan: Scan) -> Dict[str, Any]:
    project = scan.target.project
    org = project.organization
    stats = scan.stats or {}
    summary = {
        "total": int(stats.get("total", 0) or 0),
        "by_severity": stats.get("by_severity", {}) or {},
        "by_category": stats.get("by_category", {}) or {},
    }
    ctx = {
        "scan": scan,
        "scan_id": str(scan.id),
        "project": project,
        "project_id": str(project.id),
        "project_name": project.name,
        "organization_id": str(org.id),
        "organization_name": org.name,
        "target_id": str(scan.target.id),
        "target_name": str(scan.target),
        "summary": summary,
        "api_scan_url": f"/api/v1/scans/{scan.id}",
    }
    return ctx


def _match_rules(scan: Scan, event_type: str) -> List[NotificationRule]:
    rule_event = EVENT_MAP.get(event_type, "")
    if not rule_event:
        return []
    rules = (
        NotificationRule.objects.select_related("project", "channel")
        .filter(project=scan.target.project, enabled=True, event=rule_event, channel__enabled=True)
        .all()
    )
    return list(rules)


def _dispatch_email(channel: NotificationChannel, event_type: str, context: Dict[str, Any]) -> Tuple[bool, str]:
    from django.core.mail import EmailMultiAlternatives, send_mail  # lazy import

    cfg = channel.config or {}
    recipients = cfg.get("recipients") or cfg.get("to") or []
    if isinstance(recipients, str):
        recipients = [recipients]
    if not recipients:
        return False, "missing_recipients"

    subject_prefix = (cfg.get("subject_prefix") or "[Scanner]").strip()
    subject = f"{subject_prefix} {event_type} for {context.get('project_name')}"

    txt, html = _render_email(context["scan"], context)

    from_addr = getattr(settings, "NOTIFICATIONS_DEFAULTS", {}).get("email_from") or getattr(
        settings, "DEFAULT_FROM_EMAIL", "no-reply@scanner.local"
    )
    try:
        if html:
            msg = EmailMultiAlternatives(subject=subject, body=txt, from_email=from_addr, to=recipients)
            msg.attach_alternative(html, "text/html")
            msg.send(fail_silently=False)
        else:
            send_mail(subject=subject, message=txt, from_email=from_addr, recipient_list=recipients, fail_silently=False)
        return True, "sent"
    except Exception as e:
        return False, f"exception:{type(e).__name__}:{e}"


def _dispatch_slack(channel: NotificationChannel, event_type: str, context: Dict[str, Any]) -> Tuple[bool, str]:
    cfg = channel.config or {}
    url = cfg.get("webhook_url")
    if not url:
        return False, "missing_webhook_url"
    text = f"{event_type}: project={context.get('project_name')} target={context.get('target_name')} scan_id={context.get('scan_id')} total={context.get('summary', {}).get('total', 0)}"
    payload = {"text": text}
    return _safe_requests_post(url, payload, headers={"Content-Type": "application/json"})


def _dispatch_teams(channel: NotificationChannel, event_type: str, context: Dict[str, Any]) -> Tuple[bool, str]:
    cfg = channel.config or {}
    url = cfg.get("webhook_url")
    if not url:
        return False, "missing_webhook_url"
    text = f"{event_type}: project={context.get('project_name')} target={context.get('target_name')} scan={context.get('scan_id')} total={context.get('summary', {}).get('total', 0)}"
    payload = {"text": text}
    return _safe_requests_post(url, payload, headers={"Content-Type": "application/json"})


def _dispatch_webhook(channel: NotificationChannel, event_type: str, context: Dict[str, Any]) -> Tuple[bool, str]:
    cfg = channel.config or {}
    url = cfg.get("webhook_url")
    if not url:
        return False, "missing_webhook_url"
    body: Dict[str, Any] = {
        "event": event_type,
        "project": {
            "id": context.get("project_id"),
            "name": context.get("project_name"),
            "organization_id": context.get("organization_id"),
            "organization_name": context.get("organization_name"),
        },
        "target": {"id": context.get("target_id"), "name": context.get("target_name")},
        "scan_id": context.get("scan_id"),
        "summary": context.get("summary"),
        "links": {"scan": context.get("api_scan_url")},
    }
    body_json = json.dumps(body, separators=(",", ":"), sort_keys=True)
    headers = {"Content-Type": "application/json"}
    secret = cfg.get("secret")
    if secret:
        sig = hmac.new(str(secret).encode("utf-8"), body_json.encode("utf-8"), sha256).hexdigest()
        headers["X-Signature"] = sig
    return _safe_requests_post(url, json.loads(body_json), headers=headers)


def _dispatch_channel(channel: NotificationChannel, event_type: str, context: Dict[str, Any]) -> Tuple[bool, str]:
    t = (channel.type or "").lower()
    if t == NotificationChannel.ChannelType.EMAIL:
        return _dispatch_email(channel, event_type, context)
    if t == NotificationChannel.ChannelType.SLACK:
        return _dispatch_slack(channel, event_type, context)
    if t == NotificationChannel.ChannelType.MS_TEAMS:
        return _dispatch_teams(channel, event_type, context)
    if t == NotificationChannel.ChannelType.WEBHOOK:
        return _dispatch_webhook(channel, event_type, context)
    return False, f"unsupported_channel:{t}"


def _should_fire_for_rule(rule: NotificationRule, event_type: str, context: Dict[str, Any]) -> bool:
    if event_type == "severity.threshold":
        min_sev = (rule.severity_min or "high").lower()
        return _severity_at_or_above(context.get("summary") or {}, min_sev)
    if rule.severity_min:
        return _severity_at_or_above(context.get("summary") or {}, (rule.severity_min or "high").lower())
    return True


# ---------------------------
# Celery Task
# ---------------------------

@shared_task(name="notifications.tasks.dispatch_event", max_retries=5, retry_backoff=True, autoretry_for=())
def dispatch_event(event_type: str, payload_id: str) -> Dict[str, Any]:
    """
    event_type in {"scan.completed","scan.failed","severity.threshold"}
    payload_id is Scan.id in this scope.
    """
    try:
        scan = Scan.objects.select_related("target", "target__project", "target__project__organization").get(pk=payload_id)
    except ObjectDoesNotExist:
        logger.error("notifications dispatch payload not found event_type=%s payload_id=%s", event_type, payload_id)
        return {"dispatched": 0, "errors": ["payload_not_found"]}

    context = _build_context(scan)
    matched = _match_rules(scan, event_type)

    results: List[Dict[str, Any]] = []
    success_count = 0

    for rule in matched:
        channel = rule.channel
        try:
            if not _should_fire_for_rule(rule, event_type, context):
                logger.info(
                    "notify skip event=%s project_id=%s channel_id=%s rule_id=%s reason=threshold",
                    event_type,
                    context.get("project_id"),
                    str(channel.id),
                    str(rule.id),
                )
                continue

            ok, info = _dispatch_channel(channel, event_type, context)
            results.append(
                {
                    "rule_id": str(rule.id),
                    "channel_id": str(channel.id),
                    "ok": ok,
                    "info": info,
                }
            )
            if ok:
                success_count += 1
                logger.info(
                    "notify sent event=%s project_id=%s channel_id=%s rule_id=%s",
                    event_type,
                    context.get("project_id"),
                    str(channel.id),
                    str(rule.id),
                )
            else:
                logger.warning(
                    "notify failure event=%s project_id=%s channel_id=%s rule_id=%s info=%s channel_cfg=%s",
                    event_type,
                    context.get("project_id"),
                    str(channel.id),
                    str(rule.id),
                    info,
                    _redact_config(channel.config or {}),
                )
                raise RuntimeError(f"dispatch_failed:{info}")
        except Exception as e:
            try:
                dispatch_event.retry(exc=e)
            except Exception:
                logger.exception(
                    "notify retry scheduling failed event=%s project_id=%s channel_id=%s rule_id=%s err=%s",
                    event_type,
                    context.get("project_id"),
                    str(getattr(rule, "channel_id", "")),
                    str(getattr(rule, "id", "")),
                    e,
                )
                results.append(
                    {
                        "rule_id": str(getattr(rule, "id", "")),
                        "channel_id": str(getattr(rule, "channel_id", "")),
                        "ok": False,
                        "info": f"exception:{type(e).__name__}:{e}",
                    }
                )

    return {"dispatched": success_count, "results": results}