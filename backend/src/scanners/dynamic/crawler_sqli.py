from __future__ import annotations

import logging
from typing import Iterable, List, Tuple
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


def _with_param(url: str, name: str, value: str) -> str:
    parsed = urlparse(url)
    qs = parse_qsl(parsed.query, keep_blank_values=True)
    # replace the single param
    new_qs: List[Tuple[str, str]] = []
    for k, v in qs:
        if k == name:
            new_qs.append((k, value))
        else:
            new_qs.append((k, v))
    new_query = urlencode(new_qs, doseq=True)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))


@scanner_plugin(key="dynamic.crawler.sqli", type="dynamic", name="Dynamic Crawler - SQLi Heuristic", version="0.1.0", capabilities=["crawl", "sqli"])
class DynamicCrawlerSQLI:
    def run(self, context: ScanContext) -> Iterable[FindingRecord]:
        target = context.target
        start_url = getattr(target, "address", "") or ""
        if not start_url:
            return []

        crawler = Crawler(session=context.http_session, user_agent=context.user_agent, timeout_secs=context.timeout_secs)
        findings: List[FindingRecord] = []
        max_pages = 5

        for page in crawler.crawl(start_url, max_pages=max_pages, target_settings=getattr(target, "settings", {}) or {}):
            if page.error:
                findings.append(
                    FindingRecord(
                        plugin_key="dynamic.crawler.sqli",
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

            # small body constraint to be conservative
            if not page.body_excerpt or len(page.body_excerpt) > 5000:
                continue

            parsed = urlparse(page.url or "")
            params = parse_qsl(parsed.query, keep_blank_values=True)
            if len(params) != 1:
                continue

            name, baseline_val = params[0]
            # Establish baseline by re-fetching current URL (ensures comparable path)
            baseline = crawler.fetch(page.url, method="GET", timeout=context.timeout_secs, verify=True)
            baseline_len = len(baseline.body_excerpt or "")

            # Probe value toggles
            probe_values = ["1", "' OR '1'='1"]
            consistent_signal = False
            evidence_items: List[EvidenceItem] = []
            for pv in probe_values:
                probe_url = _with_param(page.url, name, pv)
                probed = crawler.fetch(probe_url, method="GET", timeout=context.timeout_secs, verify=True)
                pp = _page_to_payload_page(probed)
                ev = payloads._evidence_from_page(pp, {"probe": {"param": name, "value": pv}})
                evidence_items.append(ev)
                # Use payloads heuristic for length-based signal against baseline
                sqli_findings = payloads.test_sqli_echo(pp, baseline_len)
                if sqli_findings:
                    consistent_signal = True

            if consistent_signal:
                # Emit a single consolidated finding with collected probe evidence
                findings.append(
                    FindingRecord(
                        plugin_key="dynamic.crawler.sqli",
                        category="injection.sqli.length",
                        title="Possible SQL injection (length/time heuristic)",
                        description=f"Heuristic signals suggest potential SQLi on parameter '{name}' at {page.url}",
                        severity="medium",
                        location=page.url,
                        metadata={"param": name, "category": "injection.sqli.length"},
                        compliance_tags=["A03:2021-Injection"],
                        evidence=evidence_items,
                    )
                )

        return findings