from __future__ import annotations

import html
import logging
from typing import Iterable, List

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


@scanner_plugin(key="dynamic.crawler.headers", type="dynamic", name="Dynamic Crawler - Security Headers", version="0.1.0", capabilities=["crawl", "headers"])
class DynamicCrawlerHeaders:
    def run(self, context: ScanContext) -> Iterable[FindingRecord]:
        target = context.target
        start_url = getattr(target, "address", "") or ""
        if not start_url:
            return []

        crawler = Crawler(session=context.http_session, user_agent=context.user_agent, timeout_secs=context.timeout_secs)
        findings: List[FindingRecord] = []
        max_pages = 5
        for page in crawler.crawl(start_url, max_pages=max_pages, target_settings=getattr(target, "settings", {}) or {}):
            # skip error-only entries but attach minimal evidence for visibility
            if page.error:
                ev = EvidenceItem(kind="note", inline=page.error, content_type="text/plain", metadata={"url": page.url})
                findings.append(
                    FindingRecord(
                        plugin_key="dynamic.crawler.headers",
                        category="crawler.note",
                        title="Crawl note",
                        description=f"Page skipped or error: {page.error}",
                        severity="info",
                        location=page.url,
                        evidence=[ev],
                        metadata={"category": "crawler.note"},
                        compliance_tags=[],
                    )
                )
                continue

            p = _page_to_payload_page(page)
            findings.extend(payloads.test_headers(p))

        return findings