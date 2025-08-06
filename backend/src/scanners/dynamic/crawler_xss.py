from __future__ import annotations

import html
import logging
from typing import Iterable, List
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

from scanners.registry import scanner_plugin
from scanners.types import ScanContext, FindingRecord, EvidenceItem
from .crawler import Crawler, PageResult
from . import payloads

logger = logging.getLogger(__name__)


def _page_to_payload_page(p: PageResult) -> payloads.Page:
    return payloads.Page(
        url=p.url,
        status=p.status,
        headers=p.headers or {},
        elapsed_ms=p.elapsed_ms,
        body_excerpt=p.body_excerpt or "",
    )


def _inject_token(url: str, token: str) -> str:
    """
    For any existing query params, add token as a param named 'token' (no overwrite).
    If there are none, create ?token=...
    """
    parsed = urlparse(url)
    qs = parse_qsl(parsed.query, keep_blank_values=True)
    # avoid overwriting existing 'token'
    qs.append(("token", token))
    new_query = urlencode(qs, doseq=True)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))


@scanner_plugin(key="dynamic.crawler.xss", type="dynamic", name="Dynamic Crawler - XSS Reflection", version="0.1.0", capabilities=["crawl", "xss"])
class DynamicCrawlerXSS:
    def run(self, context: ScanContext) -> Iterable[FindingRecord]:
        target = context.target
        start_url = getattr(target, "address", "") or ""
        if not start_url:
            return []

        crawler = Crawler(session=context.http_session, user_agent=context.user_agent, timeout_secs=context.timeout_secs)
        findings: List[FindingRecord] = []
        max_pages = 5
        token = "<dyn_xss_test>"  # escaped string literal in source; actual value should be <dyn_xss_test>
        actual_token = "<dyn_xss_test>"

        for page in crawler.crawl(start_url, max_pages=max_pages, target_settings=getattr(target, "settings", {}) or {}):
            if page.error:
                # yield note for visibility
                findings.append(
                    FindingRecord(
                        plugin_key="dynamic.crawler.xss",
                        category="crawler.note",
                        title="Crawl note",
                        description=f"Page skipped or error: {page.error}",
                        severity="info",
                        location=page.url,
                        evidence=[EvidenceItem(kind="note", inline=page.error, content_type="text/plain", metadata={"url": page.url})],
                        metadata={"category": "crawler.note"},
                        compliance_tags=[],
                    )
                )
                continue

            # Only probe pages that already have a query string to keep impact low
            parsed = urlparse(page.url or "")
            if not parsed.query:
                continue

            probe_url = _inject_token(page.url, actual_token)
            probed = crawler.fetch(probe_url, method="GET", timeout=context.timeout_secs, verify=True)
            pp = _page_to_payload_page(probed)
            # Test for reflection of the token in response body
            findings.extend(payloads.test_xss_reflection(pp, actual_token))

        return findings