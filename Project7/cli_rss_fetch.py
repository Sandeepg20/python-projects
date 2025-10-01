"""
Project 7 — Load RSS, fetch links in parallel, write content to output.txt

Usage (PowerShell):
  python cli_rss_fetch.py --rss "D:\feeds\news.xml" --out "output.txt" --workers 8
  # or directly from a URL:
  python cli_rss_fetch.py --rss "https://example.com/feed.xml" --out "output.txt"

What it does
- Reads an RSS XML (local file OR URL)
- Extracts unique <link> values
- Downloads each page in parallel threads
- Extracts readable text (title + paragraphs) with BeautifulSoup
- Writes combined results to output.txt (UTF-8)

Exit codes
  0 = success (≥1 link processed)
  2 = RSS file missing / URL fetch failed
  3 = RSS XML empty or has no <link> items
  4 = Other runtime error
"""
from __future__ import annotations

import argparse
import sys
import time
from typing import List, Tuple
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from xml.etree import ElementTree as ET

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)

def is_url(s: str) -> bool:
    try:
        p = urlparse(s)
        return p.scheme in ("http", "https")
    except Exception:
        return False

def read_rss_source(rss: str, timeout: float = 15.0) -> str:
    """Return RSS XML as text. Supports local path or URL."""
    if is_url(rss):
        try:
            resp = requests.get(rss, timeout=timeout, headers={"User-Agent": DEFAULT_UA})
            resp.raise_for_status()
            return resp.text
        except Exception as exc:
            print(f"ERROR: Failed to download RSS URL '{rss}': {exc}", file=sys.stderr)
            raise FileNotFoundError from exc
    # local file
    try:
        with open(rss, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as exc:
        print(f"ERROR: RSS file not found or unreadable: '{rss}': {exc}", file=sys.stderr)
        raise FileNotFoundError from exc

def parse_rss_links(xml_text: str) -> List[str]:
    """Parse RSS XML and return a list of unique <link> values (preserve order)."""
    if not xml_text.strip():
        # empty xml
        return []

    try:
        root = ET.fromstring(xml_text)
    except Exception as exc:
        print(f"ERROR: Invalid XML: {exc}", file=sys.stderr)
        return []

    # Typical structure: <rss><channel><item><link>...</link></item></channel></rss>
    links: List[str] = []
    seen = set()
    for el in root.findall(".//item/link"):
        if el.text:
            url = el.text.strip()
            if url and url not in seen:
                seen.add(url)
                links.append(url)

    # Some feeds put link at channel level for the site; keep only item links
    return links

def fetch_and_extract(url: str, timeout: float = 15.0) -> Tuple[str, str]:
    """
    Fetch a URL and return (title, text). On failure, returns (title, error text).
    Text extraction:
      - <article> text if present
      - else all <p> paragraphs combined
    """
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent": DEFAULT_UA})
        r.raise_for_status()
        html = r.text
    except Exception as exc:
        return (url, f"[ERROR fetching: {exc}]")

    try:
        soup = BeautifulSoup(html, "lxml")
        title = (soup.title.string or "").strip() if soup.title else url

        # Prefer article tag
        article = soup.find("article")
        if article:
            paras = [p.get_text(" ", strip=True) for p in article.find_all("p")]
        else:
            paras = [p.get_text(" ", strip=True) for p in soup.find_all("p")]

        # Filter empties and duplicates
        body_lines = []
        seen = set()
        for p in paras:
            if p and p not in seen:
                seen.add(p)
                body_lines.append(p)
        body = "\n".join(body_lines).strip() or "[No readable text found]"

        return (title, body)
    except Exception as exc:
        return (title if "title" in locals() else url, f"[ERROR parsing HTML: {exc}]")

def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch RSS links in parallel and write text to output.txt.")
    ap.add_argument("--rss", required=True, help="Path to RSS XML file OR RSS URL.")
    ap.add_argument("--out", default="output.txt", help="Output file path (default: output.txt)")
    ap.add_argument("--workers", type=int, default=8, help="Number of parallel threads (default: 8)")
    ap.add_argument("--timeout", type=float, default=15.0, help="Per-request timeout seconds (default: 15)")
    args = ap.parse_args()

    # 1) Load RSS (error if file missing / URL fetch fails)
    try:
        xml_text = read_rss_source(args.rss, timeout=args.timeout)
    except FileNotFoundError:
        return 2

    # 2) Parse links (error if empty xml or no links)
    links = parse_rss_links(xml_text)
    if not links:
        print("ERROR: RSS XML is empty or contains no <item><link> entries.", file=sys.stderr)
        return 3

    print(f"Found {len(links)} link(s). Fetching with {args.workers} threads...")

    # 3) Parallel fetch
    results: List[Tuple[str, str, str]] = []  # (url, title, text)
    start = time.time()
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futures = {ex.submit(fetch_and_extract, url, args.timeout): url for url in links}
        for fut in as_completed(futures):
            url = futures[fut]
            title, text = fut.result()
            results.append((url, title, text))
            # Optional: progress line
            print(f"✓ {title[:80] or url}")

    elapsed = time.time() - start
    print(f"Done in {elapsed:.1f}s. Writing to '{args.out}' ...")

    # 4) Write output (UTF-8)
    try:
        with open(args.out, "w", encoding="utf-8") as f:
            for url, title, text in results:
                f.write(f"===== {title}\n")
                f.write(f"URL: {url}\n\n")
                f.write(text)
                f.write("\n\n\n")
    except Exception as exc:
        print(f"ERROR: Failed to write output file '{args.out}': {exc}", file=sys.stderr)
        return 4

    print(f"OK: Wrote {len(results)} article(s) to '{args.out}'.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
