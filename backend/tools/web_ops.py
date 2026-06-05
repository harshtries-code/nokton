from .registry import tool


@tool(category="web")
def web_search(query: str, max_results: int = 5) -> str:
    """Search the web using DuckDuckGo (free, no API key).
    Args:
        query: Search query text.
        max_results: Maximum number of results to return. Defaults to 5.
    Returns:
        Search results with titles, snippets, and URLs.
    """
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for i, r in enumerate(ddgs.text(query, max_results=max_results)):
                results.append(f"{i + 1}. {r['title']}\n   {r['body'][:200]}\n   {r['href']}")
        return "\n\n".join(results) if results else "No results found"
    except ImportError:
        return "Web search requires duckduckgo_search package"
    except Exception as e:
        return f"Search error: {e}"


@tool(category="web")
def web_fetch(url: str) -> str:
    """Fetch and extract text content from a web page.
    Args:
        url: Full URL of the web page to fetch.
    Returns:
        Extracted text content from the page.
    """
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
        return "\n".join(lines[:200])  # Limit to 200 lines
    except ImportError:
        return "Web fetch requires requests and beautifulsoup4 packages"
    except Exception as e:
        return f"Fetch error: {e}"


@tool(category="web")
def extract_links(url: str) -> str:
    """Extract all links from a web page.
    Args:
        url: Full URL of the web page.
    Returns:
        List of links with their text and href attributes.
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        links = []
        for a in soup.find_all("a", href=True):
            href = urljoin(url, a["href"])
            text = a.get_text(strip=True)[:80]
            links.append(f"{text}: {href}" if text else href)
        return "\n".join(links[:100])
    except ImportError:
        return "Link extraction requires requests and beautifulsoup4 packages"
    except Exception as e:
        return f"Extract error: {e}"
