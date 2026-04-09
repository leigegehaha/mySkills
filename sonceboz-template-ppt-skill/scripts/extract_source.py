from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse
from zipfile import ZipFile

import requests
from bs4 import BeautifulSoup
from docx import Document


NUMERIC_PATTERN = re.compile(
    r"(?P<label>[A-Za-z\u4e00-\u9fff][A-Za-z0-9_/\-\u4e00-\u9fff %°():+]{2,80}?)"
    r"\s*[:：-]?\s*"
    r"(?P<value>-?\d+(?:\.\d+)?)"
    r"\s*(?P<unit>°/s|deg/s|°C|ppm|kg|mm|cm|min|N|C|g|m|%|V|A|W|h|s)?\b"
)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def extract_numeric_facts(lines: Iterable[str]) -> list[dict[str, str]]:
    facts: list[dict[str, str]] = []
    for line in lines:
        for match in NUMERIC_PATTERN.finditer(line):
            label = re.sub(r"\s+", " ", match.group("label")).strip(" :-")
            value = match.group("value")
            unit = match.group("unit") or ""
            if not label:
                continue
            facts.append({"label": label, "value": value, "unit": unit, "source_text": line.strip()})
    return facts


def parse_text_file(input_path: Path) -> tuple[str, list[Path], dict[str, str]]:
    text = input_path.read_text(encoding="utf-8", errors="ignore")
    return text, [], {"type": "text-file", "source": str(input_path)}


def parse_docx(input_path: Path, image_dir: Path) -> tuple[str, list[Path], dict[str, str]]:
    document = Document(str(input_path))
    paragraphs = [p.text.strip() for p in document.paragraphs if p.text.strip()]
    with ZipFile(input_path) as archive:
        for name in archive.namelist():
            if not name.startswith("word/media/") or name.endswith("/"):
                continue
            target = image_dir / Path(name).name
            target.write_bytes(archive.read(name))
    images = sorted(image_dir.glob("*"))
    return "\n".join(paragraphs), images, {"type": "docx", "source": str(input_path)}


def parse_html_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text("\n")
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def download_url_images(soup: BeautifulSoup, base_url: str, image_dir: Path) -> list[Path]:
    images: list[Path] = []
    seen: set[str] = set()
    for index, tag in enumerate(soup.find_all("img"), start=1):
        source = tag.get("src")
        if not source:
            continue
        full_url = urljoin(base_url, source)
        if full_url in seen:
            continue
        seen.add(full_url)
        try:
            response = requests.get(full_url, timeout=20)
            response.raise_for_status()
        except Exception:
            continue
        suffix = Path(urlparse(full_url).path).suffix or ".img"
        target = image_dir / f"web_image_{index:02d}{suffix}"
        target.write_bytes(response.content)
        images.append(target)
    return images


def parse_url(url: str, image_dir: Path) -> tuple[str, list[Path], dict[str, str]]:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    html = response.text
    soup = BeautifulSoup(html, "html.parser")
    images = download_url_images(soup, url, image_dir)
    text = parse_html_text(html)
    return text, images, {"type": "url", "source": url}


def try_fetch_web_images(output_path: Path, image_dir: Path, max_images: int) -> list[Path]:
    script_path = Path(__file__).resolve().parent / "fetch_web_images.py"
    if not script_path.exists():
        return []
    namespace = {}
    exec(script_path.read_text(encoding="utf-8"), namespace)
    downloader = namespace.get("download_images")
    if not downloader:
        return []
    return downloader(output_path, image_dir / "web_search", max_images=max_images)


def parse_html_file(input_path: Path, image_dir: Path) -> tuple[str, list[Path], dict[str, str]]:
    html = input_path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "html.parser")
    images: list[Path] = []
    for index, tag in enumerate(soup.find_all("img"), start=1):
        src = tag.get("src")
        if not src:
            continue
        candidate = (input_path.parent / src).resolve()
        if candidate.exists():
            target = image_dir / f"html_image_{index:02d}{candidate.suffix}"
            target.write_bytes(candidate.read_bytes())
            images.append(target)
    text = parse_html_text(html)
    return text, images, {"type": "html-file", "source": str(input_path)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="text file, docx file, html file, or webpage URL")
    parser.add_argument("--output", required=True, help="output JSON path")
    parser.add_argument("--auto-web-images", action="store_true", help="search Wikimedia Commons for supporting images")
    parser.add_argument("--max-web-images", type=int, default=4)
    args = parser.parse_args()

    source_input = args.input
    output_path = Path(args.output).resolve()
    work_dir = output_path.parent / f"{output_path.stem}_assets"
    image_dir = work_dir / "images"
    ensure_dir(image_dir)

    if source_input.startswith(("http://", "https://")):
        text, images, metadata = parse_url(source_input, image_dir)
    else:
        input_path = Path(source_input).expanduser().resolve()
        suffix = input_path.suffix.lower()
        if suffix == ".docx":
            text, images, metadata = parse_docx(input_path, image_dir)
        elif suffix in {".html", ".htm"}:
            text, images, metadata = parse_html_file(input_path, image_dir)
        else:
            text, images, metadata = parse_text_file(input_path)

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    payload = {
        "metadata": metadata,
        "text": text,
        "line_count": len(lines),
        "image_paths": [str(path.resolve()) for path in images],
        "numeric_facts": extract_numeric_facts(lines),
    }
    ensure_dir(output_path.parent)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    if args.auto_web_images:
        web_images = try_fetch_web_images(output_path, image_dir, max_images=args.max_web_images)
        payload["image_paths"].extend(str(path.resolve()) for path in web_images)
        payload["web_image_paths"] = [str(path.resolve()) for path in web_images]
        output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(output_path)


if __name__ == "__main__":
    main()
