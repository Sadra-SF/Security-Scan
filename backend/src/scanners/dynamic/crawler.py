from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Union
from urllib.parse import urljoin, urlparse, urlunparse, parse_qsl

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _get_defaults() -> Dict[str, Any]:
    d = getattr(settings, "SCANNER_DEFAULTS", {}) or {}
    return {
        "http_timeout_seconds": int(d.get("HTTP_TIMEOUT_SECS", 5)),
        "dynamic_max_pages": int(d.get("dynamic_max_pages", 10)),
        "rate_limit_rps": int(d.get("rate_limit_rps", 2)),
        "user_agent": str(d.get("user_agent", "SecurityScannerBot/1.0")),
    }


def _same_origin(url1: str, url2: str) -> bool:
    try:
        p1 = urlparse(url1)
        p2 = urlparse(url2)
        return (p1.scheme, p1.hostname, p1.port or _default_port(p1.scheme)) == (
            p2.scheme,
            p2.hostname,
            p2.port or _default_port(p2.scheme),
        )
    except Exception:
        return False


def _default_port(scheme: Optional[str]) -> Optional[int]:
    if scheme == "http":
        return 80
    if scheme == "https":
        return 443
    return None


def _normalize_url(u: str) -> str:
    try:
        p = urlparse(u)
        # drop fragment
        p = p._replace(fragment="")
        # remove default ports in netloc
        host = p.hostname or ""
        port = p.port
        if port and ((p.scheme == "http" and port == 80) or (p.scheme == "https" and port == 443)):
            netloc = host
        else:
            netloc = p.netloc
        p = p._replace(netloc=netloc)
        return urlunparse(p)
    except Exception:
        return u


def _path_depth(path: str) -> int:
    if not path:
        return 0
    # ignore leading/trailing slashes
    parts = [seg for seg in path.strip("/").split("/") if seg]
    return len(parts)


class _LinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        if tag.lower() == "a":
            href = None
            for k, v in attrs:
                if k.lower() == "href":
                    href = v
                    break
            if href:
                self.links.append(href)


@dataclass
class PageResult:
    url: str
    status: Optional[int] = None
    headers: Dict[str, str] = field(default_factory=dict)
    elapsed_ms: Optional[int] = None
    body_excerpt: Optional[str] = None
    error: Optional[str] = None
    method: str = "GET"
    http_evidence: Optional[Any] = None  # EvidenceItem for HTTP details


class TokenBucket:
    """
    Simple in-memory token bucket limiter (per-process).
    """

    def __init__(self, rate_per_sec: int, capacity: Optional[int] = None) -> None:
        self.rate = max(1, int(rate_per_sec or 1))
        self.capacity = int(capacity or self.rate)
        self.tokens = self.capacity
        self.timestamp = time.monotonic()

    def acquire(self) -> None:
        now = time.monotonic()
        # add tokens
        delta = now - self.timestamp
        self.timestamp = now
        self.tokens = min(self.capacity, self.tokens + delta * self.rate)
        if self.tokens < 1:
            # sleep until we have at least 1 token
            needed = 1 - self.tokens
            sleep_for = max(0.0, needed / self.rate)
            time.sleep(sleep_for)
            self.tokens = 0
        else:
            self.tokens -= 1


class Crawler:
    """
    Conservative HTTP crawler with robots.txt respect and strict timeouts.
    """

    def __init__(self, session: Optional[requests.Session] = None, user_agent: Optional[str] = None, timeout_secs: Optional[int] = None, rate_limit_rps: Optional[int] = None):
        defaults = _get_defaults()
        self.session = session or requests.Session()
        self.user_agent = user_agent or defaults["user_agent"]
        self.timeout = int(timeout_secs or defaults["http_timeout_seconds"])
        self.rate_limiter = TokenBucket(rate_limit_rps or defaults["rate_limit_rps"])
        # Ensure UA
        self.session.headers.update({"User-Agent": self.user_agent})
        # Prepared robots cache
        self._robots_cache: Dict[str, "Robots"] = {}

    def _get_robots(self, base_url: str, allow_bypass: bool) -> "Robots":
        origin = self._origin(base_url)
        if origin in self._robots_cache:
            return self._robots_cache[origin]
        robots = Robots(self.session, origin, self.user_agent, timeout=self.timeout, bypass=allow_bypass)
        self._robots_cache[origin] = robots
        return robots

    def _origin(self, url: str) -> str:
        p = urlparse(url)
        netloc = p.hostname or ""
        port = p.port
        if port and ((p.scheme == "http" and port != 80) or (p.scheme == "https" and port != 443)):
            netloc = f"{netloc}:{port}"
        return f"{p.scheme}://{netloc}"

    def fetch(
        self,
        url: str,
        method: str = "GET",
        params: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        allow_redirects: bool = True,
        max_redirects: int = 2,
        verify: bool = True,
        capture_http_details: bool = False,
    ) -> PageResult:
        result = PageResult(url=_normalize_url(url), method=method.upper())
        # Rate limit
        self.rate_limiter.acquire()
        # Safety knobs
        t = int(timeout or self.timeout)
        redirects_left = max(0, int(max_redirects))
        current_url = url
        h = {"User-Agent": self.user_agent}
        if headers:
            h.update(headers)
        # Initialize HTTP logger if detailed capture is requested
        http_logger = None
        if capture_http_details:
            try:
                from evidence.http_logger import HTTPLogger
                http_logger = HTTPLogger(self.session)
            except ImportError:
                logger.warning("HTTP logging not available, falling back to basic capture")

        try:
            while True:
                start = time.monotonic()
                start_datetime = datetime.now(timezone.utc)

                resp = self.session.request(method.upper(), current_url, params=params, data=data, headers=h, timeout=t, allow_redirects=False, verify=verify)
                elapsed_ms = int((time.monotonic() - start) * 1000)
                end_datetime = datetime.now(timezone.utc)

                status = resp.status_code
                hdrs = {k.lower(): v for k, v in (resp.headers or {}).items()}
                body_excerpt = ""
                if resp.content is not None:
                    try:
                        body_excerpt = (resp.text or "")[:500]
                    except Exception:
                        body_excerpt = ""

                result = PageResult(
                    url=_normalize_url(current_url),
                    status=status,
                    headers=hdrs,
                    elapsed_ms=elapsed_ms,
                    body_excerpt=body_excerpt,
                    method=method.upper(),
                )

                # Store HTTP details if logger is available
                if http_logger:
                    try:
                        # Convert data to appropriate format for logging
                        request_body = None
                        if data:
                            if isinstance(data, dict):
                                request_body = json.dumps(data)
                            else:
                                request_body = data

                        http_evidence = http_logger.log_request_response(
                            method=method.upper(),
                            url=current_url,
                            request_headers=h,
                            request_body=request_body,
                            response=resp,
                            start_time=start_datetime,
                            end_time=end_datetime,
                            metadata={
                                "redirect_count": 2 - redirects_left,
                                "is_redirect": status in (301, 302, 303, 307, 308)
                            }
                        )
                        # Store evidence in result for later use
                        result.http_evidence = http_evidence
                    except Exception as e:
                        logger.warning(f"Failed to log HTTP details: {e}")

                # Handle up to 2 redirects manually to keep control
                if status in (301, 302, 303, 307, 308) and redirects_left > 0:
                    location = hdrs.get("location") or hdrs.get("content-location")
                    if location:
                        next_url = urljoin(current_url, location)
                        if _same_origin(current_url, next_url):
                            redirects_left -= 1
                            current_url = next_url
                            continue
                break
        except Exception as e:
            result.error = f"{type(e).__name__}: {e}"
            logger.debug("crawler.fetch error url=%s err=%s", url, e)
        return result

    def extract_links(self, html: str, base_url: str) -> Set[str]:
        links: Set[str] = set()
        try:
            parser = _LinkExtractor()
            parser.feed(html or "")
            for href in parser.links:
                # Skip javascript/mailto/etc.
                if not href or href.startswith("#") or re.match(r"^(javascript|data|mailto):", href, re.IGNORECASE):
                    continue
                u = urljoin(base_url, href)
                u = _normalize_url(u)
                if not _same_origin(base_url, u):
                    continue
                p = urlparse(u)
                if _path_depth(p.path) > 2:
                    continue
                links.add(u)
        except Exception as e:
            logger.debug("extract_links failed base=%s err=%s", base_url, e)
        return links

    def crawl(self, start_url: str, max_pages: Optional[int] = None, target_settings: Optional[Dict[str, Any]] = None) -> Iterable[PageResult]:
        defaults = _get_defaults()
        limit = int(max_pages or defaults["dynamic_max_pages"])
        start_url = _normalize_url(start_url)
        visited: Set[str] = set()
        queue: List[str] = [start_url]
        allow_bypass = bool((target_settings or {}).get("allow_robots_bypass"))
        robots = self._get_robots(start_url, allow_bypass)

        while queue and len(visited) < limit:
            url = queue.pop(0)
            if url in visited:
                continue
            # robots check
            if not robots.allowed(url):
                logger.info("robots.txt disallow url=%s", url)
                visited.add(url)
                # still yield an entry to show it was skipped
                yield PageResult(url=url, error="robots_disallow")
                continue

            page = self.fetch(url, method="GET", timeout=self.timeout, verify=True)
            visited.add(url)
            yield page

            # only enqueue links for 2xx small pages
            if page.status and 200 <= page.status < 300 and page.body_excerpt:
                for link in self.extract_links(page.body_excerpt, url):
                    if link not in visited and link not in queue and _same_origin(start_url, link):
                        queue.append(link)


class Robots:
    """
    Extremely small robots.txt parser with user-agent matching.
    """

    def __init__(self, session: requests.Session, origin: str, user_agent: str, timeout: int, bypass: bool = False) -> None:
        self.origin = origin
        self.session = session
        self.user_agent = user_agent
        self.timeout = int(timeout)
        self.bypass = bool(bypass)
        self.rules: List[Tuple[str, str]] = []  # (ua, path) disallow paths
        if not bypass:
            self._load()

    def _load(self) -> None:
        url = f"{self.origin}/robots.txt"
        try:
            resp = self.session.get(url, timeout=self.timeout, allow_redirects=True)
            if resp.status_code >= 400 or not resp.text:
                return
            ua: Optional[str] = None
            for raw in resp.text.splitlines():
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(":", 1)
                if len(parts) != 2:
                    continue
                key, val = parts[0].strip().lower(), parts[1].strip()
                if key == "user-agent":
                    ua = val
                elif key == "disallow":
                    path = val or "/"
                    self.rules.append((ua or "*", path))
        except Exception as e:
            logger.debug("robots.txt load failed origin=%s err=%s", self.origin, e)

    def allowed(self, url: str) -> bool:
        if self.bypass:
            return True
        try:
            p = urlparse(url)
            path = p.path or "/"
            # Match exact UA first then *
            blocked: List[str] = []
            for ua, dis in self.rules:
                if ua not in (self.user_agent, "*"):
                    continue
                if dis == "":
                    # allow all
                    continue
                if dis == "/":
                    blocked.append(dis)
                elif path.startswith(dis):
                    blocked.append(dis)
            return len(blocked) == 0
        except Exception:
            return True