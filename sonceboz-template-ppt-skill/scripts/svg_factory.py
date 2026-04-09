from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


CANVAS_W = 1600
CANVAS_H = 900
RED = "#C00000"
RED_DARK = "#910000"
TEXT = "#333333"
MUTED = "#6A6A6A"
BG = "#FFFFFF"
LIGHT = "#F5F5F5"
BORDER = "#D9D9D9"


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def safe_name(text: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return name or "visual"


def wrap_text(text: str, limit: int = 38) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = []
    for word in words:
        candidate = " ".join(current + [word])
        if len(candidate) > limit and current:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines


def svg_header() -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_W}" height="{CANVAS_H}" viewBox="0 0 {CANVAS_W} {CANVAS_H}">',
        f'<rect width="{CANVAS_W}" height="{CANVAS_H}" fill="{BG}"/>',
    ]


def svg_footer() -> list[str]:
    return ["</svg>"]


def render_metric_grid(data: dict, out_dir: Path) -> tuple[Path, Path]:
    facts = data.get("numeric_facts", [])[:4]
    title = data.get("title") or "Key Metrics"
    svg = svg_header()
    svg.append(f'<text x="90" y="110" font-size="54" font-family="Arial" font-weight="700" fill="{RED}">{title}</text>')
    svg.append(f'<text x="90" y="165" font-size="24" font-family="Arial" fill="{MUTED}">Automatically generated summary visual</text>')
    boxes = [(90, 240), (810, 240), (90, 520), (810, 520)]
    for idx, fact in enumerate(facts):
        x, y = boxes[idx]
        svg.append(f'<rect x="{x}" y="{y}" rx="28" ry="28" width="620" height="220" fill="{LIGHT}" stroke="{BORDER}" stroke-width="2"/>')
        value = f'{fact["value"]} {fact.get("unit","").strip()}'.strip()
        svg.append(f'<text x="{x+40}" y="{y+92}" font-size="62" font-family="Arial" font-weight="700" fill="{RED_DARK}">{value}</text>')
        for line_idx, line in enumerate(wrap_text(fact["label"], 26)):
            svg.append(f'<text x="{x+40}" y="{y+145 + line_idx*32}" font-size="28" font-family="Arial" fill="{TEXT}">{line}</text>')
    svg.extend(svg_footer())
    svg_path = out_dir / f"{safe_name(title)}-metric-grid.svg"
    svg_path.write_text("\n".join(svg), encoding="utf-8")

    image = Image.new("RGB", (CANVAS_W, CANVAS_H), "white")
    draw = ImageDraw.Draw(image)
    title_font = load_font(34, True)
    subtitle_font = load_font(18, False)
    value_font = load_font(40, True)
    label_font = load_font(20, False)
    draw.text((90, 70), title, fill=(192, 0, 0), font=title_font)
    draw.text((90, 118), "Automatically generated summary visual", fill=(106, 106, 106), font=subtitle_font)
    for idx, fact in enumerate(facts):
        x, y = boxes[idx]
        draw.rounded_rectangle((x, y, x + 620, y + 220), radius=28, fill=(245, 245, 245), outline=(217, 217, 217), width=2)
        value = f'{fact["value"]} {fact.get("unit","").strip()}'.strip()
        draw.text((x + 32, y + 30), value, fill=(145, 0, 0), font=value_font)
        for line_idx, line in enumerate(wrap_text(fact["label"], 26)):
            draw.text((x + 32, y + 110 + line_idx * 28), line, fill=(51, 51, 51), font=label_font)
    png_path = out_dir / f"{safe_name(title)}-metric-grid.png"
    image.save(png_path)
    return svg_path, png_path


def render_timeline(data: dict, out_dir: Path) -> tuple[Path, Path]:
    title = data.get("title") or "Project Timeline"
    lines = data.get("lines", [])[:4]
    points = [(180, 320), (500, 420), (860, 320), (1220, 420)]
    svg = svg_header()
    svg.append(f'<text x="90" y="110" font-size="54" font-family="Arial" font-weight="700" fill="{RED}">{title}</text>')
    svg.append(f'<line x1="150" y1="380" x2="1340" y2="380" stroke="{RED}" stroke-width="10" stroke-linecap="round"/>')
    for idx, point in enumerate(points[: len(lines)]):
        x, y = point
        svg.append(f'<circle cx="{x}" cy="{y}" r="28" fill="{RED_DARK}"/>')
        svg.append(f'<rect x="{x-120}" y="{y-130 if idx % 2 == 0 else y+40}" rx="18" ry="18" width="250" height="120" fill="{LIGHT}" stroke="{BORDER}" stroke-width="2"/>')
        label_lines = wrap_text(lines[idx], 24)
        for line_idx, line in enumerate(label_lines[:3]):
            svg.append(f'<text x="{x-95}" y="{(y-88 if idx % 2 == 0 else y+78) + line_idx*28}" font-size="24" font-family="Arial" fill="{TEXT}">{line}</text>')
    svg.extend(svg_footer())
    svg_path = out_dir / f"{safe_name(title)}-timeline.svg"
    svg_path.write_text("\n".join(svg), encoding="utf-8")

    image = Image.new("RGB", (CANVAS_W, CANVAS_H), "white")
    draw = ImageDraw.Draw(image)
    title_font = load_font(34, True)
    text_font = load_font(18, False)
    draw.text((90, 70), title, fill=(192, 0, 0), font=title_font)
    draw.line((150, 380, 1340, 380), fill=(192, 0, 0), width=8)
    for idx, (x, y) in enumerate(points[: len(lines)]):
        draw.ellipse((x - 28, y - 28, x + 28, y + 28), fill=(145, 0, 0))
        box_top = y - 130 if idx % 2 == 0 else y + 40
        draw.rounded_rectangle((x - 120, box_top, x + 130, box_top + 120), radius=18, fill=(245, 245, 245), outline=(217, 217, 217), width=2)
        for line_idx, line in enumerate(wrap_text(lines[idx], 24)[:3]):
            draw.text((x - 95, (y - 88 if idx % 2 == 0 else y + 78) + line_idx * 24), line, fill=(51, 51, 51), font=text_font)
    png_path = out_dir / f"{safe_name(title)}-timeline.png"
    image.save(png_path)
    return svg_path, png_path


def render_comparison(data: dict, out_dir: Path) -> tuple[Path, Path]:
    title = data.get("title") or "Comparison"
    left_items = data.get("left", [])[:4]
    right_items = data.get("right", [])[:4]
    svg = svg_header()
    svg.append(f'<text x="90" y="110" font-size="54" font-family="Arial" font-weight="700" fill="{RED}">{title}</text>')
    svg.append(f'<rect x="90" y="190" rx="28" ry="28" width="640" height="600" fill="{LIGHT}" stroke="{BORDER}" stroke-width="2"/>')
    svg.append(f'<rect x="870" y="190" rx="28" ry="28" width="640" height="600" fill="{LIGHT}" stroke="{BORDER}" stroke-width="2"/>')
    svg.append(f'<text x="130" y="260" font-size="34" font-family="Arial" font-weight="700" fill="{RED_DARK}">Key Points</text>')
    svg.append(f'<text x="910" y="260" font-size="34" font-family="Arial" font-weight="700" fill="{RED_DARK}">Implications</text>')
    for idx, item in enumerate(left_items):
        y = 330 + idx * 110
        svg.append(f'<circle cx="132" cy="{y-8}" r="9" fill="{RED}"/>')
        for line_idx, line in enumerate(wrap_text(item, 30)[:3]):
            svg.append(f'<text x="160" y="{y + line_idx*28}" font-size="24" font-family="Arial" fill="{TEXT}">{line}</text>')
    for idx, item in enumerate(right_items):
        y = 330 + idx * 110
        svg.append(f'<circle cx="912" cy="{y-8}" r="9" fill="{RED}"/>')
        for line_idx, line in enumerate(wrap_text(item, 30)[:3]):
            svg.append(f'<text x="940" y="{y + line_idx*28}" font-size="24" font-family="Arial" fill="{TEXT}">{line}</text>')
    svg.extend(svg_footer())
    svg_path = out_dir / f"{safe_name(title)}-comparison.svg"
    svg_path.write_text("\n".join(svg), encoding="utf-8")

    image = Image.new("RGB", (CANVAS_W, CANVAS_H), "white")
    draw = ImageDraw.Draw(image)
    title_font = load_font(34, True)
    header_font = load_font(24, True)
    body_font = load_font(18, False)
    draw.text((90, 70), title, fill=(192, 0, 0), font=title_font)
    draw.rounded_rectangle((90, 190, 730, 790), radius=28, fill=(245, 245, 245), outline=(217, 217, 217), width=2)
    draw.rounded_rectangle((870, 190, 1510, 790), radius=28, fill=(245, 245, 245), outline=(217, 217, 217), width=2)
    draw.text((130, 226), "Key Points", fill=(145, 0, 0), font=header_font)
    draw.text((910, 226), "Implications", fill=(145, 0, 0), font=header_font)
    for idx, item in enumerate(left_items):
        y = 330 + idx * 110
        draw.ellipse((124, y - 22, 140, y - 6), fill=(192, 0, 0))
        for line_idx, line in enumerate(wrap_text(item, 30)[:3]):
            draw.text((160, y + line_idx * 24 - 22), line, fill=(51, 51, 51), font=body_font)
    for idx, item in enumerate(right_items):
        y = 330 + idx * 110
        draw.ellipse((904, y - 22, 920, y - 6), fill=(192, 0, 0))
        for line_idx, line in enumerate(wrap_text(item, 30)[:3]):
            draw.text((940, y + line_idx * 24 - 22), line, fill=(51, 51, 51), font=body_font)
    png_path = out_dir / f"{safe_name(title)}-comparison.png"
    image.save(png_path)
    return svg_path, png_path


def choose_visuals(source: dict, purpose: str) -> list[tuple[Path, Path]]:
    out_dir = Path(source["output_dir"]).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    visuals: list[tuple[Path, Path]] = []
    title = source.get("title") or source.get("metadata", {}).get("source", "Summary")
    facts = source.get("numeric_facts", [])
    lines = [line.strip() for line in source.get("text", "").splitlines() if line.strip()]
    cleaned = [line for line in lines if not line.lower().startswith(("purpose:", "title:"))]
    if facts:
        visuals.append(render_metric_grid({"title": title, "numeric_facts": facts}, out_dir))
    if purpose == "meeting-summary":
        visuals.append(render_timeline({"title": f"{title} Timeline", "lines": cleaned[:4]}, out_dir))
    elif purpose == "market-research":
        visuals.append(render_comparison({"title": f"{title} Comparison", "left": cleaned[:4], "right": cleaned[4:8]}, out_dir))
    else:
        visuals.append(render_timeline({"title": f"{title} Milestones", "lines": cleaned[:4]}, out_dir))
    return visuals


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, help="normalized source JSON")
    parser.add_argument("--purpose", choices=["test-report", "market-research", "meeting-summary"], required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    payload = json.loads(Path(args.source).read_text(encoding="utf-8"))
    payload["output_dir"] = str(Path(args.output_dir).resolve())
    if "title" not in payload:
        payload["title"] = "Generated Visual"
    visuals = choose_visuals(payload, args.purpose)
    print(json.dumps([{"svg": str(svg), "png": str(png)} for svg, png in visuals], indent=2))


if __name__ == "__main__":
    main()
