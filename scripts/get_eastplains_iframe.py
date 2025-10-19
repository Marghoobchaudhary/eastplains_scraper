import re
import sys
import urllib.parse
import requests
from bs4 import BeautifulSoup

PAGE_URL = "https://www.eastplainscorporation.com/foreclosure-listings"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124 Safari/537.36"
)

HEADERS = {
    "User-Agent": UA,
    "Referer": "https://www.eastplainscorporation.com/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

def fetch(url: str) -> str:
    try:
        r = requests.get(url, headers=HEADERS, timeout=25, allow_redirects=True)
        r.raise_for_status()
        return r.text
    except Exception as e:
        sys.stderr.write(f"Fetch failed: {url}\n{e}\n")
        return ""

def resolve_iframe_from_html(html: str, base: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    # Try DOM first
    for iframe in soup.find_all("iframe"):
        src = iframe.get("src") or iframe.get("data-src") or ""
        if not src:
            continue
        abs_url = urllib.parse.urljoin(base, src)
        if re.search(r"filesusr\.com/.*/html/[^\"'\s]+\.html", abs_url, re.I):
            return abs_url

    # Fallback regex if iframe not parsed properly
    m = re.search(
        r"https?://[^\"'\s]*filesusr\.com/[^\"'\s]*/html/[^\"'\s]+\.html", html, re.I
    )
    if m:
        return m.group(0)

    return ""

def resolve_via_thunderbolt(html: str) -> str:
    m = re.search(
        r"https://siteassets\.parastorage\.com/pages/pages/thunderbolt\?[^\"'\s]+",
        html,
        re.I,
    )
    if not m:
        return ""
    thunder_url = urllib.parse.unquote(m.group(0))
    json_text = fetch(thunder_url)
    if not json_text:
        return ""

    # Absolute filesusr URL inside JSON?
    m2 = re.search(
        r"https?://[^\"'\s]*filesusr\.com/[^\"'\s]*/html/[^\"'\s]+\.html", json_text, re.I
    )
    if m2:
        return m2.group(0)

    # Relative with staticHTMLComponentUrl
    base = ""
    b = re.search(r"staticHTMLComponentUrl=([^&\s]+)", thunder_url, re.I)
    if b:
        base = urllib.parse.unquote(b.group(1))
        if not base.endswith("/"):
            base += "/"

    r2 = re.search(r"/html/[^\"'\s]+\.html", json_text, re.I)
    if base and r2:
        return urllib.parse.urljoin(base, r2.group(0))
    return ""

def get_eastplains_iframe_url() -> str:
    html = fetch(PAGE_URL)
    if not html:
        return ""
    src = resolve_iframe_from_html(html, PAGE_URL)
    if not src:
        src = resolve_via_thunderbolt(html)
    return src

if __name__ == "__main__":
    url = get_eastplains_iframe_url()
    if url:
        print(url)
    else:
        print("Iframe not found", file=sys.stderr)
        sys.exit(1)
