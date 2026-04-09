from __future__ import annotations

import argparse
import json
import re
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

try:
    from PIL import Image, UnidentifiedImageError
except Exception:  # pragma: no cover - optional validation
    Image = None
    UnidentifiedImageError = Exception


COMMONS_ENDPOINT = "https://commons.wikimedia.org/w/api.php"
OPENVERSE_ENDPOINT = "https://api.openverse.org/v1/images/"
WIKIPEDIA_ENDPOINT = "https://en.wikipedia.org/w/api.php"
FLICKR_PUBLIC_FEED = "https://www.flickr.com/services/feeds/photos_public.gne"
BING_IMAGE_SEARCH = "https://www.bing.com/images/search"
SKILL_DIR = Path(__file__).resolve().parents[1]
GEMINI_SCRIPT = SKILL_DIR / "scripts" / "gemini_real_image.py"
REQUEST_TIMEOUT = (4, 6)
DOWNLOAD_TIMEOUT = (4, 8)
HEADERS = {
    "User-Agent": "web-image-research-skill/1.0 (+presentation-image-search)",
}
GENERIC_LINE_PATTERNS = (
    "this document should",
    "please preserve",
    "please polish",
    "reserve placeholders",
    "key source facts",
)
STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "that",
    "this",
    "into",
    "after",
    "before",
    "report",
    "validation",
    "document",
    "customer",
    "facing",
    "concise",
    "english",
    "measured",
    "correction",
    "communication",
    "weight",
    "speed",
    "temperature",
    "rise",
    "endurance",
    "purpose",
    "title",
}
TOPIC_KEYWORDS_BY_PURPOSE = {
    "test-report": {
        "dof",
        "grasp force",
        "robot",
        "hand",
        "finger",
        "actuator",
        "industrial",
        "test",
        "bench",
        "measurement",
        "validation",
        "setup",
    },
    "market-research": {
        "ai",
        "agent",
        "agents",
        "agentic",
        "llm",
        "model",
        "models",
        "automation",
        "autonomous",
        "workflow",
        "enterprise",
        "platform",
        "orchestration",
        "memory",
        "reasoning",
        "retrieval",
        "tool",
        "tools",
        "software",
        "robotics",
        "industry",
        "market",
    },
    "meeting-summary": {
        "meeting",
        "workshop",
        "review",
        "roadmap",
        "discussion",
        "action",
        "decision",
        "team",
        "project",
    },
}
BLOCKED_DOMAIN_TOKENS = {
    "alamy",
    "shutterstock",
    "gettyimages",
    "istockphoto",
    "depositphotos",
    "dreamstime",
    "123rf",
    "vecteezy",
    "freepik",
    "colourbox",
    "canstockphoto",
    "turbosquid",
    "pngwing",
    "pngtree",
    "clipart",
}
BLOCKED_TEXT_TOKENS = {
    "stock photo",
    "stock image",
    "stock vector",
    "vector",
    "illustration",
    "clipart",
    "icon",
    "logo",
    "watermark",
    "rigged model",
    "3d model",
    "render",
    "rendering",
    "download scientific diagram",
    "scientific diagram",
    "diagram",
    "documentation",
    "docs",
    "template",
    "mockup",
}
THUMBNAIL_TOKENS = {
    "/thumbnail/",
    "/thumb/",
    "thumbnail/entry_id",
    "/fill/w_",
    "!detail.v1",
    "preview",
    "sprite",
}
PREFERRED_DOMAIN_TOKENS = {
    "nist",
    "shadowrobot",
    "abb",
    "festo",
    "schunk",
    "robotics",
    "research",
    "university",
    "edu",
    "gov",
    "industry",
}
PRODUCT_TOKENS = {
    "robotic hand",
    "dexterous hand",
    "gripper",
    "robot hand",
    "actuator",
    "end effector",
    "robotic arm",
    "product",
    "device",
    "system",
}
EVIDENCE_TOKENS = {
    "test",
    "test bench",
    "bench",
    "lab",
    "laboratory",
    "measurement",
    "validation",
    "inspection",
    "setup",
    "protocol",
    "performance",
    "evaluation",
    "experiment",
}
MEETING_TOKENS = {
    "meeting",
    "workshop",
    "conference",
    "team",
    "discussion",
    "office",
    "presentation",
}
MARKET_TOKENS = {
    "factory",
    "industrial",
    "automation",
    "market",
    "manufacturing",
    "plant",
    "production",
}


def slugify(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-") or "image"


def clean_topic_phrase(text: str) -> str:
    text = re.sub(r"[^A-Za-z0-9 ]+", " ", text)
    parts = []
    for token in text.split():
        lower = token.lower()
        if lower in STOPWORDS:
            continue
        if re.fullmatch(r"\d+(?:\.\d+)?", token):
            continue
        if len(token) <= 1:
            continue
        parts.append(token)
    return " ".join(parts[:6]).strip()


def extract_title(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("title:"):
            return stripped.split(":", 1)[1].strip()
    return ""


def extract_topic_candidates(text: str, purpose: str) -> list[str]:
    candidates: list[str] = []
    title = extract_title(text)
    if title:
        candidates.append(title)

    purpose_keywords = TOPIC_KEYWORDS_BY_PURPOSE[purpose]
    for raw_line in text.splitlines():
        line = raw_line.strip(" -•\t")
        lower = line.lower()
        if not line:
            continue
        if lower.startswith(("purpose:", "title:")):
            continue
        if any(pattern in lower for pattern in GENERIC_LINE_PATTERNS):
            continue
        if any(keyword in lower for keyword in purpose_keywords):
            candidates.append(line)

    normalized: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        phrase = clean_topic_phrase(candidate)
        if not phrase:
            continue
        key = phrase.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(phrase)
    return normalized


def derive_queries(text: str, purpose: str, limit: int = 5) -> list[str]:
    base_terms = {
        "test-report": ["industrial testing", "test bench", "laboratory measurement", "robotic hand"],
        "market-research": ["ai agents enterprise workflow", "agentic ai platform", "multi agent systems", "enterprise automation ai"],
        "meeting-summary": ["business meeting", "engineering workshop", "industrial discussion", "team collaboration"],
    }[purpose]
    queries = []

    topic_candidates = extract_topic_candidates(text, purpose)
    if purpose == "test-report":
        title = extract_title(text).lower()
        if "dexterous hand" in title:
            topic_candidates.insert(0, "dexterous robotic hand")
            topic_candidates.insert(1, "robotic hand test bench")
        elif "hand" in title:
            topic_candidates.insert(0, "robotic hand")
            topic_candidates.insert(1, "robotic hand testing")
    elif purpose == "market-research":
        title = extract_title(text).lower()
        if "ai agent" in title or "agent" in title:
            topic_candidates.insert(0, "ai agents enterprise automation")
            topic_candidates.insert(1, "agentic ai workflow")
            topic_candidates.insert(2, "multi agent systems")

    for topic in topic_candidates:
        if topic.lower() not in {x.lower() for x in queries}:
            queries.append(topic)
        if len(queries) >= limit:
            break
    for term in base_terms:
        if len(queries) >= limit:
            break
        if term.lower() not in {x.lower() for x in queries}:
            queries.append(term)
    return queries[:limit]


def extract_domain(value: str) -> str:
    if not value:
        return ""
    return urlparse(value).netloc.lower().removeprefix("www.")


def joined_candidate_text(item: dict) -> str:
    return " ".join(
        part
        for part in [
            item.get("title", ""),
            item.get("query", ""),
            item.get("page_url", ""),
            item.get("url", ""),
        ]
        if part
    ).lower()


def has_any_token(text: str, tokens: set[str]) -> bool:
    return any(token in text for token in tokens)


def infer_role(item: dict, purpose: str) -> str:
    text = joined_candidate_text(item)
    if purpose == "test-report":
        if has_any_token(text, EVIDENCE_TOKENS):
            return "evidence"
        if has_any_token(text, PRODUCT_TOKENS):
            return "product"
        return "context"
    if purpose == "market-research":
        if has_any_token(text, PRODUCT_TOKENS):
            return "product"
        if has_any_token(text, MARKET_TOKENS):
            return "context"
        return "context"
    if has_any_token(text, MEETING_TOKENS):
        return "meeting"
    return "context"


def should_reject_candidate(item: dict) -> tuple[bool, str]:
    text = joined_candidate_text(item)
    domain = extract_domain(item.get("page_url") or item.get("url", ""))
    image_domain = extract_domain(item.get("url", ""))
    if any(token in domain for token in BLOCKED_DOMAIN_TOKENS) or any(token in image_domain for token in BLOCKED_DOMAIN_TOKENS):
        return True, "blocked-domain"
    if has_any_token(text, BLOCKED_TEXT_TOKENS):
        return True, "blocked-text"
    if has_any_token((item.get("url", "") + " " + item.get("page_url", "")).lower(), THUMBNAIL_TOKENS):
        return True, "thumbnail-url"
    if "/video/" in text or "/videos/" in text or "youtube.com" in text or "youtu.be" in text:
        return True, "video-thumbnail"
    return False, ""


def commons_search(query: str, limit: int = 6) -> list[dict]:
    params = {
        "action": "query",
        "generator": "search",
        "gsrnamespace": 6,
        "gsrsearch": query,
        "gsrlimit": limit,
        "prop": "imageinfo",
        "iiprop": "url|size",
        "iiurlwidth": 1600,
        "format": "json",
    }
    response = requests.get(COMMONS_ENDPOINT, params=params, timeout=REQUEST_TIMEOUT, headers=HEADERS)
    response.raise_for_status()
    pages = response.json().get("query", {}).get("pages", {})
    results = []
    for page in pages.values():
        info = (page.get("imageinfo") or [{}])[0]
        url = info.get("thumburl") or info.get("url")
        if not url:
            continue
        results.append(
            {
                "source": "wikimedia",
                "title": page.get("title", ""),
                "url": url,
                "width": info.get("thumbwidth") or info.get("width") or 0,
                "height": info.get("thumbheight") or info.get("height") or 0,
                "query": query,
            }
        )
    return results


def openverse_search(query: str, limit: int = 6) -> list[dict]:
    response = requests.get(OPENVERSE_ENDPOINT, params={"q": query, "page_size": limit}, timeout=REQUEST_TIMEOUT, headers=HEADERS)
    response.raise_for_status()
    results = []
    for item in response.json().get("results", []):
        url = item.get("thumbnail") or item.get("url")
        if not url:
            continue
        results.append(
            {
                "source": "openverse",
                "title": item.get("title", ""),
                "url": url,
                "width": item.get("width") or 0,
                "height": item.get("height") or 0,
                "query": query,
            }
        )
    return results


def wikipedia_search(query: str, limit: int = 6) -> list[dict]:
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrlimit": limit,
        "prop": "pageimages|info",
        "piprop": "thumbnail|name|original",
        "pithumbsize": 1600,
        "inprop": "url",
        "format": "json",
    }
    response = requests.get(WIKIPEDIA_ENDPOINT, params=params, timeout=REQUEST_TIMEOUT, headers=HEADERS)
    response.raise_for_status()
    pages = response.json().get("query", {}).get("pages", {})
    results = []
    for page in pages.values():
        thumb = page.get("thumbnail") or {}
        original = page.get("original") or {}
        url = original.get("source") or thumb.get("source")
        if not url:
            continue
        results.append(
            {
                "source": "wikipedia",
                "title": page.get("title", ""),
                "url": url,
                "width": original.get("width") or thumb.get("width") or 0,
                "height": original.get("height") or thumb.get("height") or 0,
                "query": query,
                "page_url": page.get("fullurl", ""),
            }
        )
    return results


def flickr_search(query: str, limit: int = 6) -> list[dict]:
    tags = ",".join(query.lower().split()[:4])
    params = {
        "format": "json",
        "nojsoncallback": 1,
        "tags": tags,
        "tagmode": "all" if len(tags.split(",")) <= 2 else "any",
        "lang": "en-us",
    }
    response = requests.get(FLICKR_PUBLIC_FEED, params=params, timeout=REQUEST_TIMEOUT, headers=HEADERS)
    response.raise_for_status()
    items = response.json().get("items", [])[:limit]
    results = []
    for item in items:
        media_url = (item.get("media") or {}).get("m")
        if not media_url:
            continue
        results.append(
            {
                "source": "flickr",
                "title": unescape(item.get("title") or ""),
                "url": media_url.replace("_m.", "_b."),
                "width": 0,
                "height": 0,
                "query": query,
                "page_url": item.get("link", ""),
                "author": unescape(item.get("author", "")),
            }
        )
    return results


def bing_image_search(query: str, limit: int = 8) -> list[dict]:
    response = requests.get(BING_IMAGE_SEARCH, params={"q": query}, timeout=REQUEST_TIMEOUT, headers=HEADERS)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    results = []
    for anchor in soup.select("a.iusc"):
        raw_meta = anchor.get("m")
        if not raw_meta:
            continue
        try:
            meta = json.loads(raw_meta)
        except Exception:
            continue
        url = meta.get("murl") or meta.get("turl")
        if not url:
            continue
        results.append(
            {
                "source": "bing",
                "title": meta.get("t", "") or anchor.get("aria-label", ""),
                "url": url,
                "width": meta.get("w") or 0,
                "height": meta.get("h") or 0,
                "query": query,
                "page_url": meta.get("purl", "") or anchor.get("href", ""),
                "thumbnail_url": meta.get("turl", ""),
            }
        )
        if len(results) >= limit:
            break
    return results


def score_candidate(item: dict, purpose: str) -> float:
    width = item.get("width", 0) or 0
    height = item.get("height", 0) or 0
    title = (item.get("title") or "").lower()
    query = (item.get("query") or "").lower()
    domain = item.get("domain") or extract_domain(item.get("page_url") or item.get("url", ""))
    role = item.get("role") or infer_role(item, purpose)
    score = 0.0
    score += min(width, 1600) / 400
    if width > height:
        score += 1.5
    if width >= 1200:
        score += 1.0
    score += sum(0.5 for token in query.split() if token in title)
    purpose_tokens = {
        "test-report": ["test", "lab", "robot", "industrial", "measurement"],
        "market-research": ["market", "factory", "industry", "automation", "technology"],
        "meeting-summary": ["meeting", "team", "office", "workshop", "discussion"],
    }[purpose]
    score += sum(0.4 for token in purpose_tokens if token in title)
    source_bonus = {
        "bing": 1.6,
        "wikipedia": 1.8,
        "openverse": 1.2,
        "wikimedia": 1.0,
        "flickr": 0.8,
    }
    score += source_bonus.get(item.get("source", ""), 0.0)
    if any(token in domain for token in PREFERRED_DOMAIN_TOKENS):
        score += 1.0
    if role == "product":
        score += 1.1
    elif role == "evidence":
        score += 0.9
    elif role == "meeting":
        score += 0.7
    return score


def download_image(url: str, target: Path) -> dict | None:
    try:
        response = requests.get(url, timeout=DOWNLOAD_TIMEOUT, headers=HEADERS)
        response.raise_for_status()
    except Exception:
        return None
    content_type = response.headers.get("content-type", "").lower()
    if content_type and not content_type.startswith("image/"):
        return None
    content = response.content
    if len(content) < 15_000:
        return None
    target.write_bytes(content)
    width = 0
    height = 0
    if Image is not None:
        try:
            with Image.open(target) as image:
                width, height = image.size
        except (UnidentifiedImageError, OSError):
            target.unlink(missing_ok=True)
            return None
        if max(width, height) < 600 or min(width, height) < 260:
            target.unlink(missing_ok=True)
            return None
    return {"width": width, "height": height, "bytes": len(content)}


def ai_prompt_from_source(source: dict, purpose: str) -> str:
    lines = [line.strip() for line in source.get("text", "").splitlines() if line.strip()]
    lines = [line for line in lines if not line.lower().startswith(("purpose:", "title:"))]
    phrase = " ".join(lines[:3])[:220]
    purpose_hint = {
        "test-report": "industrial product testing setup or clean robotic/mechatronic product photo",
        "market-research": "clean realistic industrial market context or product scene",
        "meeting-summary": "clean realistic professional workshop or engineering meeting scene",
    }[purpose]
    return f"{purpose_hint}, {phrase}"


def maybe_generate_ai_images(source: dict, purpose: str, output_dir: Path, count: int) -> list[Path]:
    if count <= 0 or not GEMINI_SCRIPT.exists():
        return []
    namespace = {"__file__": str(GEMINI_SCRIPT)}
    exec(GEMINI_SCRIPT.read_text(encoding="utf-8"), namespace)
    generate_once = namespace.get("generate_once")
    load_config = namespace.get("load_config")
    build_prompt = namespace.get("build_prompt")
    if not (generate_once and load_config and build_prompt):
        return []
    style_suffix = load_config()["gemini"]["default_style_suffix"]
    prompt = build_prompt(ai_prompt_from_source(source, purpose), style_suffix)
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    for _ in range(count):
        path = generate_once(prompt, output_dir)
        if path:
            outputs.append(path)
    return outputs


def search_and_collect(source: dict, purpose: str, output_dir: Path, richness: int) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    if richness <= 0:
        return {"queries": [], "images": []}
    query_limit = 1 if richness <= 1 else 2 if richness <= 4 else 3
    queries = derive_queries(source.get("text", "") or source.get("title", ""), purpose, limit=query_limit)
    candidates = []
    rejections = []
    search_sources = [bing_image_search, wikipedia_search, openverse_search] if richness <= 1 else [bing_image_search, wikipedia_search, openverse_search, commons_search, flickr_search]
    for query in queries:
        for search_fn in search_sources:
            try:
                candidates.extend(search_fn(query))
            except Exception:
                continue
    enriched = []
    for item in candidates:
        item["domain"] = extract_domain(item.get("page_url") or item.get("url", ""))
        item["role"] = infer_role(item, purpose)
        rejected, reason = should_reject_candidate(item)
        if rejected:
            rejections.append({"title": item.get("title", ""), "url": item.get("url", ""), "reason": reason})
            continue
        item["score"] = score_candidate(item, purpose)
        enriched.append(item)
    candidates = sorted(enriched, key=lambda item: item["score"], reverse=True)

    target_real_count = min(5, richness)
    selected = []
    seen_urls = set()
    seen_domains = set()
    for item in candidates:
        if item["url"] in seen_urls:
            continue
        if item.get("domain") in seen_domains and len(selected) < target_real_count - 1:
            continue
        seen_urls.add(item["url"])
        suffix = Path(urlparse(item["url"]).path).suffix or ".jpg"
        local_path = output_dir / f"real_{len(selected)+1:02d}_{slugify(item['query'])[:30]}{suffix}"
        downloaded = download_image(item["url"], local_path)
        if downloaded:
            if downloaded.get("width"):
                item["width"] = downloaded["width"]
            if downloaded.get("height"):
                item["height"] = downloaded["height"]
            item["byte_size"] = downloaded["bytes"]
            item["local_path"] = str(local_path.resolve())
            item["kind"] = "real"
            selected.append(item)
            if item.get("domain"):
                seen_domains.add(item["domain"])
        if len([x for x in selected if x["kind"] == "real"]) >= target_real_count:
            break

    ai_needed = 0
    if richness == 4 and len(selected) < 2:
        ai_needed = 1
    elif richness >= 5 and len(selected) < 3:
        ai_needed = 2

    if ai_needed:
        ai_paths = maybe_generate_ai_images(source, purpose, output_dir / "ai", ai_needed)
        for path in ai_paths:
            selected.append(
                {
                    "source": "gemini",
                    "title": path.stem,
                    "url": "",
                    "width": 0,
                    "height": 0,
                    "query": "gemini-fallback",
                    "score": 999.0,
                    "local_path": str(path.resolve()),
                    "kind": "ai",
                }
            )

    manifest = {"queries": queries, "images": selected, "richness": richness, "purpose": purpose, "rejections": rejections[:30]}
    (output_dir / "images_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", help="normalized source json")
    parser.add_argument("--query", help="raw search query")
    parser.add_argument("--purpose", choices=["test-report", "market-research", "meeting-summary"], required=True)
    parser.add_argument("--richness", type=int, default=3)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    if not args.source and not args.query:
        raise SystemExit("Provide --source or --query")
    if args.source:
        source = json.loads(Path(args.source).read_text(encoding="utf-8"))
    else:
        source = {"text": args.query, "title": args.query, "metadata": {"type": "query", "source": args.query}}
    manifest = search_and_collect(source, args.purpose, Path(args.output_dir).resolve(), max(0, min(5, args.richness)))
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
