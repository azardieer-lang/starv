#
import re
import sys
import json
from urllib.parse import quote_plus, urlparse

import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()

#Config
REQUEST_TIMEOUT = 15
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]

SOCIAL_PLATFORMS = {
    "LinkedIn":    "https://www.linkedin.com/search/results/people/?keywords={query}",
    "Twitter / X": "https://x.com/search?q={query}&src=typed_query&f=user",
    "GitHub":      "https://github.com/search?q={query}&type=users",
    "Instagram":   "https://www.instagram.com/web/search/topsearch/?query={query}",
    "Facebook":    "https://www.facebook.com/search/people/?q={query}",
    "Reddit":      "https://www.reddit.com/search/?q={query}&type=user",
}

SEARCH_ENGINES = {
    "DuckDuckGo": "https://html.duckduckgo.com/html/?q={query}",
    "Bing":       "https://www.bing.com/search?q={query}",
}

session = requests.Session()


#Helpers
def get_headers() -> dict:
    import random
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }


def safe_request(url: str, *, params: dict | None = None) -> requests.Response | None:
    try:
        resp = session.get(
            url, headers=get_headers(), params=params,
            timeout=REQUEST_TIMEOUT, allow_redirects=True,
        )
        resp.raise_for_status()
        return resp
    except requests.exceptions.RequestException as e:
        console.print(f"  [dim]⚠  {urlparse(url).netloc}: {e}[/dim]")
        return None


def extract_links_from_html(html: str, domain_filter: str | None = None) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("//"):
            href = "https:" + href
        if href.startswith("/"):
            continue
        parsed = urlparse(href)
        if parsed.scheme not in ("http", "https"):
            continue
        if domain_filter and domain_filter not in parsed.netloc:
            continue
        links.append(href)
    return links


#S.Engines
def search_duckduckgo(query: str) -> list[dict]:
    """Search DuckDuckGo (HTML frontend — no API key needed)."""
    results = []
    resp = safe_request(SEARCH_ENGINES["DuckDuckGo"].format(query=quote_plus(query)))
    if not resp:
        return results
    soup = BeautifulSoup(resp.text, "html.parser")
    for item in soup.select(".result"):
        link_el = item.select_one("a.result__a")
        snippet_el = item.select_one(".result__snippet")
        if link_el:
            href = link_el.get("href", "")
            if href.startswith("//"):
                href = "https:" + href
            results.append({
                "title": link_el.get_text(strip=True),
                "url": href,
                "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
            })
    return results


def search_bing(query: str) -> list[dict]:
    results = []
    resp = safe_request(SEARCH_ENGINES["Bing"].format(query=quote_plus(query)))
    if not resp:
        return results
    soup = BeautifulSoup(resp.text, "html.parser")
    for item in soup.select("li.b_algo"):
        link_el = item.select_one("h2 a")
        snippet_el = item.select_one(".b_caption p")
        if link_el:
            results.append({
                "title": link_el.get_text(strip=True),
                "url": link_el.get("href", ""),
                "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
            })
    return results


# ─── Social Media ────────────────────────────────────────────────
def check_social_profiles(query: str) -> list[dict]:
    """Hit each social platform's search URL and report status."""
    found = []
    for platform, url_template in SOCIAL_PLATFORMS.items():
        url = url_template.format(query=quote_plus(query))
        resp = safe_request(url)
        if resp is None:
            found.append({"platform": platform, "status": "Blocked / Error", "url": url})
        elif resp.status_code == 200:
            found.append({"platform": platform, "status": "Accessible", "url": url})
        else:
            found.append({"platform": platform, "status": f"HTTP {resp.status_code}", "url": url})
    return found


#Display
def show_engine_results(engine_name: str, results: list[dict]):
    if not results:
        console.print(f"\n[bold yellow]── {engine_name} ──[/bold yellow]  [dim]No results[/dim]")
        return
    table = Table(title=f"{engine_name} Results", box=box.ROUNDED, title_justify="left")
    table.add_column("#", style="dim", width=3)
    table.add_column("Title", style="cyan", no_wrap=False)
    table.add_column("URL", style="blue", no_wrap=False)
    table.add_column("Snippet", style="white", no_wrap=False)
    for i, r in enumerate(results, 1):
        snippet = r.get("snippet", "")[:120] + "…" if len(r.get("snippet", "")) > 120 else r.get("snippet", "")
        table.add_row(str(i), r["title"], r["url"], snippet)
    console.print(table)


def show_social_results(results: list[dict]):
    table = Table(title="Social Media Presence", box=box.ROUNDED, title_justify="left")
    table.add_column("Platform", style="cyan", width=18)
    table.add_column("Status", style="green", width=20)
    table.add_column("Search URL", style="blue", no_wrap=False)
    for r in results:
        status_color = "green" if r["status"] == "Accessible" else "red"
        table.add_row(r["platform"], f"[{status_color}]{r['status']}[/{status_color}]", r["url"])
    console.print(table)


#Main
def main():
    console.print(Panel.fit(
        "[bold cyan]OSINT Recon Tool[/bold cyan]\n"
        "[dim]Open-source intelligence gathering from the terminal[/dim]",
        border_style="cyan",
    ))

    full_name = input("\nEnter full name: ").strip()
    if not full_name:
        console.print("[red]No name provided. Exiting.[/red]")
        sys.exit(1)

    #0
    quoted = quote_plus(full_name)

    console.print(f"\n[bold]Target:[/bold] {full_name}")
    console.print("=" * 50)

    # ── Step 1: S.Engines ──
    console.print("\n[bold underline]Phase 1 — Web Search[/bold underline]\n")

    console.print("[dim]Searching DuckDuckGo…[/dim]")
    ddg_results = search_duckduckgo(full_name)
    show_engine_results("DuckDuckGo", ddg_results)

    console.print("\n[dim]Searching Bing…[/dim]")
    bing_results = search_bing(full_name)
    show_engine_results("Bing", bing_results)

    # ── Step 2: S.Media ──
    console.print("\n[bold underline]Phase 2 — Social Media Scan[/bold underline]\n")
    social_results = check_social_profiles(full_name)
    show_social_results(social_results)

    # ── Step 3: Summary ──
    console.print("\n[bold underline]Summary[/bold underline]")
    total_web = len(ddg_results) + len(bing_results)
    accessible_social = sum(1 for r in social_results if r["status"] == "Accessible")
    console.print(f"  Web links found : {total_web}")
    console.print(f"  Social platforms: {accessible_social}/{len(social_results)} accessible")
    console.print(f"  Target name     : {full_name}")
    console.print("\n[dim]Results are printed above. Copy any URL to open in your browser.[/dim]\n")


if __name__ == "__main__":
    main()
