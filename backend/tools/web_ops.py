from .registry import tool

_stealthy_available = None
_fetcher_available = None


def _init_fetchers():
    global _fetcher_available, _stealthy_available
    if _fetcher_available is not None:
        return
    try:
        from scrapling.fetchers import Fetcher, StealthyFetcher
        _fetcher_available = Fetcher
        StealthyFetcher.adaptive = True
        _stealthy_available = StealthyFetcher
    except ImportError:
        _fetcher_available = None
        _stealthy_available = None


@tool(category="web")
def web_search(query: str, max_results: int = 10) -> str:
    """Search the web using DuckDuckGo.
    Args:
        query: Search query text.
        max_results: Maximum number of results to return (max 20). Defaults to 10.
    Returns:
        Search results with titles, snippets, and URLs.
    """
    import urllib.parse
    _init_fetchers()
    try:
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(query)}"
        p = _fetcher_available.get(url, stealthy_headers=True, timeout=15)
        results = []
        for i, result in enumerate(p.css("div.result") or []):
            if len(results) >= min(max_results, 20):
                break
            title_el = result.css("h2 a.result__a::text, a.result__a::text").get()
            raw_href = (result.css("a.result__a::attr(href)").get() or "").lstrip("//")
            if raw_href.startswith("duckduckgo.com/l/?uddg="):
                from urllib.parse import parse_qs, urlparse
                raw_href = parse_qs(urlparse(raw_href).query).get("uddg", [raw_href])[0]
            body_el = result.css("a.result__snippet::text, .result__snippet::text").get()
            if title_el and raw_href:
                results.append(f"{i + 1}. {title_el}\n   {body_el or ''}\n   {raw_href}")
        return "\n\n".join(results) if results else "No results found"
    except ImportError:
        return "Web search requires scrapling package"
    except Exception as e:
        return f"Search error: {e}"


@tool(category="web")
def web_fetch(
    url: str,
    selector: str = "",
    max_chars: int = 10000,
    headless: bool = False,
) -> str:
    """Fetch and extract content from a web page with anti-bot bypass.
    Uses CloakBrowser stealth Chromium behind the scenes for sites with bot protection.
    Args:
        url: Full URL of the web page to fetch.
        selector: Optional CSS selector to extract specific content (e.g. 'article', '.repo-list li', 'h1'). If empty, returns all text.
        max_chars: Maximum characters to return. Defaults to 10000.
        headless: Whether to run browser in headless mode. Defaults to False (uses fast HTTP first).
    Returns:
        Extracted text content from the page.
    """
    _init_fetchers()
    if not _fetcher_available:
        return _fallback_fetch(url, max_chars)

    try:
        if headless or _stealthy_available is None:
            p = _fetcher_available.get(url, stealthy_headers=True, timeout=20)
        else:
            p = _stealthy_available.fetch(url, headless=True, network_idle=True, timeout=20)

        if selector:
            elements = p.css(selector)
            if not elements:
                return f"No elements matched selector '{selector}'"
            text = "\n\n".join(e.css("::text").getall() or [e.text for e in elements])
        else:
            text = p.text

        if not text or not text.strip():
            text = p.get_all_text() or ""

        text = text.strip()
        if len(text) > max_chars:
            text = text[:max_chars] + f"\n\n[... truncated, {len(text) - max_chars} more chars omitted]"
        return text or "Page returned no text content"

    except Exception as e:
        return _fallback_fetch(url, max_chars, error=str(e))


def _fallback_fetch(url: str, max_chars: int = 10000, error: str = "") -> str:
    try:
        import requests
        from bs4 import BeautifulSoup
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        text = "\n".join(lines)
        if len(text) > max_chars:
            text = text[:max_chars] + f"\n\n[... truncated, {len(text) - max_chars} more chars omitted]"
        prefix = f"[Scrapling unavailable, fell back to requests]\n" if error else ""
        return prefix + text
    except Exception as e2:
        return f"Fetch error: {error}; fallback also failed: {e2}"


@tool(category="web")
def web_scrape(
    url: str,
    selector: str,
    max_pages: int = 1,
    max_results: int = 50,
) -> str:
    """Crawl multiple pages of a site using CSS selector extraction.
    Follows pagination links (next, load more) automatically.
    Uses CloakBrowser stealth Chromium + Scrapling for anti-bot bypass.
    Args:
        url: Starting URL.
        selector: CSS selector for items to extract (e.g. '.repo', '.issue', '.result').
        max_pages: Maximum pages to crawl. Defaults to 1.
        max_results: Maximum total items to return. Defaults to 50.
    Returns:
        Extracted items across all crawled pages.
    """
    _init_fetchers()
    if not _fetcher_available:
        return "web_scrape requires scrapling package (pip install scrapling[fetchers])"

    try:
        if _stealthy_available:
            p = _stealthy_available.fetch(url, headless=True, network_idle=True)
        else:
            p = _fetcher_available.get(url, stealthy_headers=True)

        all_items = []
        seen = set()

        for page_num in range(max_pages):
            if page_num > 0:
                next_link = p.css("a[rel=next]::attr(href), .pagination .next a::attr(href), .load-more::attr(href)").get()
                if not next_link:
                    next_link = p.css("a:has-text('Next')::attr(href), a:has-text('next')::attr(href)").get()
                if not next_link:
                    break
                next_url = p.urljoin(next_link)
                if next_url in seen:
                    break
                seen.add(next_url)
                if _stealthy_available:
                    p = _stealthy_available.fetch(next_url, headless=True, network_idle=True)
                else:
                    p = _fetcher_available.get(next_url, stealthy_headers=True)

            items = p.css(selector)
            for item in items:
                text = item.text.strip() if item.text else ""
                if text and len(all_items) < max_results:
                    all_items.append(text)
                if len(all_items) >= max_results:
                    break

        if not all_items:
            return f"No items found for selector '{selector}'"

        result = f"Found {len(all_items)} items across {max_pages} page(s):\n\n"
        result += "\n---\n".join(all_items)
        if len(result) > 20000:
            result = result[:20000] + "\n\n[... truncated]"
        return result

    except Exception as e:
        return f"Crawl error: {e}"


@tool(category="web")
def extract_links(url: str, max_results: int = 100) -> str:
    """Extract all links from a web page.
    Args:
        url: Full URL of the web page.
        max_results: Maximum number of links to return. Defaults to 100.
    Returns:
        List of links with their text and href attributes.
    """
    _init_fetchers()
    try:
        p = _fetcher_available.get(url, stealthy_headers=True, timeout=15)
        links = []
        for a in p.css(f"a[href]") or []:
            href = a.attrib.get("href", "")
            if not href or href.startswith("#") or href.startswith("javascript:"):
                continue
            full_url = p.urljoin(href)
            text = (a.text or "").strip()[:80]
            links.append(f"{text}: {full_url}" if text else full_url)
            if len(links) >= max_results:
                break
        return "\n".join(links) if links else "No links found"
    except ImportError:
        return "Link extraction requires scrapling package"
    except Exception as e:
        return f"Extract error: {e}"


@tool(category="web")
def extract_json(url: str, headless: bool = False) -> str:
    """Fetch a URL and parse it as JSON.
    Useful for APIs and structured data endpoints.
    Args:
        url: URL returning JSON.
        headless: Use headless browser if True. Defaults to False (fast HTTP).
    Returns:
        JSON content as formatted text.
    """
    _init_fetchers()
    if not _fetcher_available:
        return "extract_json requires scrapling package"

    try:
        import json
        if headless and _stealthy_available:
            p = _stealthy_available.fetch(url, headless=True, network_idle=True, timeout=20)
        else:
            p = _fetcher_available.get(url, stealthy_headers=True, timeout=20)
        data = p.json()
        return json.dumps(data, indent=2, default=str)[:20000]
    except Exception as e:
        return f"JSON extract error: {e}"


def _run_async(coro):
    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    if loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()
    return asyncio.run(coro)


@tool(category="web")
def extract_markdown(
    url: str,
    selector: str = "",
    main_content_only: bool = True,
) -> str:
    """Fetch a page and convert it to Markdown using curl_cffi Chrome impersonation.
    Uses Scrapling's MCP server HTTP-level impersonation (no browser).
    Good for simple pages; for JS-heavy/anti-bot sites use web_fetch with headless=True.
    Args:
        url: Full URL to fetch.
        selector: Optional CSS selector to extract specific content.
        main_content_only: Extract only body content. Defaults to True.
    Returns:
        Page content in Markdown format.
    """
    try:
        from scrapling.core.ai import ScraplingMCPServer

        async def _get():
            resp = await ScraplingMCPServer.get(
                url,
                extraction_type="markdown",
                css_selector=selector or None,
                main_content_only=main_content_only,
            )
            return resp

        result = _run_async(_get())
        text = "\n".join(result.content) if isinstance(result.content, list) else str(result.content)
        return text[:20000] if text else "No content extracted"
    except ImportError:
        return "extract_markdown requires scrapling[all] package"
    except Exception as e:
        return f"Markdown extract error: {e}"


@tool(category="web")
def fetch_bulk(
    urls: list,
    extraction_type: str = "text",
    main_content_only: bool = False,
) -> str:
    """Fetch multiple URLs in parallel with curl_cffi Chrome impersonation.
    Args:
        urls: List of URLs to fetch (e.g. ["https://example.com", "https://example.org"]).
        extraction_type: Content format - "text", "markdown", or "html". Defaults to "text".
        main_content_only: Extract only body content. Defaults to False.
    Returns:
        Combined content from all URLs.
    """
    try:
        from scrapling.core.ai import ScraplingMCPServer

        async def _get():
            results = await ScraplingMCPServer.bulk_get(
                urls=list(urls),
                extraction_type=extraction_type,
                main_content_only=main_content_only,
            )
            return results

        results = _run_async(_get())
        parts = []
        for i, r in enumerate(results):
            text = "\n".join(r.content) if isinstance(r.content, list) else str(r.content)
            parts.append(f"--- URL {i + 1}: {r.url} ---\n{text[:5000]}")
        return "\n\n".join(parts)[:50000]
    except ImportError:
        return "fetch_bulk requires scrapling[all] package"
    except Exception as e:
        return f"Bulk fetch error: {e}"


@tool(category="web")
def web_capture(
    url: str,
    session_type: str = "dynamic",
    full_page: bool = False,
    network_idle: bool = True,
) -> str:
    """Capture a screenshot of a web page as a data URL.
    Opens a temporary browser session, captures the page, and returns the image as a data URL.
    Args:
        url: Full URL of the web page to capture.
        session_type: "dynamic" (Playwright) or "stealthy" (CloakBrowser). Defaults to "dynamic".
        full_page: Capture full scrollable page. Defaults to False (viewport only).
        network_idle: Wait for network idle. Defaults to True.
    Returns:
        Screenshot image as a data URL.
    """
    try:
        from scrapling.core.ai import ScraplingMCPServer

        async def _capture():
            import base64
            server = ScraplingMCPServer()
            session = await server.open_session(
                session_type=session_type,
                headless=True,
                network_idle=network_idle,
            )
            try:
                result = await server.screenshot(
                    url=url,
                    session_id=session.session_id,
                    full_page=full_page,
                    network_idle=network_idle,
                )
                for item in result:
                    if hasattr(item, "data") and hasattr(item, "mimeType"):
                        b64 = base64.b64encode(item.data).decode()
                        return f"data:{item.mimeType};base64,{b64}"
                return str(result)
            finally:
                await server.close_session(session.session_id)

        return _run_async(_capture())
    except ImportError:
        return "web_capture requires scrapling[all] package"
    except Exception as e:
        return f"Capture error: {e}"
