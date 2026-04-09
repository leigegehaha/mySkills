from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import requests


COMMONS_ENDPOINT = "https://commons.wikimedia.org/w/api.php"


def derive_queries(text: str, max_queries: int = 3) -> list[str]:
    lines = [line.strip(" -") for line in text.splitlines() if line.strip()]
    cleaned = []
    for line in lines:
        lower = line.lower()
        if lower.startswith(("purpose:", "title:")):
            continue
        if len(line) < 8:
            continue
        cleaned.append(line)
    queries = []
    for line in cleaned[:8]:
        query = re.sub(r"[^A-Za-z0-9 ]+", " ", line)
        query = " ".join(query.split()[:6]).strip()
        if query and query.lower() not in {q.lower() for q in queries}:
            queries.append(query)
        if len(queries) >= max_queries:
            break
    return queries or ["industrial technology", "mechatronics", "robotic hand"]


def search_commons(query: str, limit: int = 3) -> list[dict]:
    params = {
        "action": "query",
        "generator": "search",
        "gsrnamespace": 6,
        "gsrsearch": query,
        "gsrlimit": limit,
        "prop": "imageinfo",
        "iiprop": "url",
        "iiurlwidth": 1600,
        "format": "json",
    }
    response = requests.get(COMMONS_ENDPOINT, params=params, timeout=30)
    response.raise_for_status()
    pages = response.json().get("query", {}).get("pages", {})
    results = []
    for page in pages.values():
        info = (page.get("imageinfo") or [{}])[0]
        url = info.get("thumburl") or info.get("url")
        if not url:
            continue
        results.append({"title": page.get("title", ""), "url": url, "query": query})
    return results


def download_images(source_json: Path, output_dir: Path, max_images: int = 4) -> list[Path]:
    payload = json.loads(source_json.read_text(encoding="utf-8"))
    text = payload.get("text", "")
    output_dir.mkdir(parents=True, exist_ok=True)
    downloaded: list[Path] = []
    seen_urls: set[str] = set()
    for query in derive_queries(text):
        for result in search_commons(query, limit=4):
            if result["url"] in seen_urls:
                continue
            seen_urls.add(result["url"])
            suffix = Path(result["url"]).suffix or ".jpg"
            target = output_dir / f"commons_{len(downloaded)+1:02d}{suffix}"
            try:
                response = requests.get(result["url"], timeout=30)
                response.raise_for_status()
            except Exception:
                continue
            target.write_bytes(response.content)
            downloaded.append(target)
            if len(downloaded) >= max_images:
                return downloaded
    return downloaded


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, help="normalized source json")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--max-images", type=int, default=4)
    args = parser.parse_args()

    paths = download_images(Path(args.source).resolve(), Path(args.output_dir).resolve(), max_images=args.max_images)
    print(json.dumps([str(path) for path in paths], indent=2))


if __name__ == "__main__":
    main()
