from __future__ import annotations

import pytest

from scanners.dynamic.crawler import Crawler
from scanners.dynamic.payloads import test_xss_reflection, Page


def test_extract_links_same_origin_and_depth_limit() -> None:
    html_doc = """
    <html>
      <body>
        <a href="/a">A</a>
        <a href="/a/b">B</a>
        <a href="/a/b/c">Too Deep</a>
        <a href="https://example.com/a/b">Same Origin Absolute</a>
        <a href="https://other.com/x">Other Origin</a>
        <a href="javascript:alert(1)">JS</a>
        <a href="#frag">Fragment</a>
      </body>
    </html>
    """
    c = Crawler()
    base = "https://example.com/"
    links = c.extract_links(html_doc, base)
    # Should include depth 0-2 paths, same origin only
    assert "https://example.com/a" in links
    assert "https://example.com/a/b" in links
    assert "https://example.com/a/b/c" not in links
    assert "https://other.com/x" not in links
    # No javascript or fragment
    assert not any(l.startswith("javascript:") for l in links)
    assert not any("#" in l for l in links)


def test_xss_token_reflection_positive() -> None:
    page = Page(
        url="https://example.com/search?q=test",
        status=200,
        headers={"content-type": "text/html"},
        elapsed_ms=120,
        body_excerpt="... hello <dyn_xss_test> world ...",
    )
    findings = test_xss_reflection(page, "<dyn_xss_test>")
    assert len(findings) == 1
    assert findings[0].category == "xss.reflection"


def test_xss_token_reflection_negative() -> None:
    page = Page(
        url="https://example.com/",
        status=200,
        headers={"content-type": "text/html"},
        elapsed_ms=50,
        body_excerpt="no token here",
    )
    findings = test_xss_reflection(page, "<dyn_xss_test>")
    assert findings == []