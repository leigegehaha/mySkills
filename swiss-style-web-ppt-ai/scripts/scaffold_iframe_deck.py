#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import shutil
import sys
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
BASE_ASSETS_DIR = SKILL_DIR / "assets" / "base"
TEMPLATES_DIR = SKILL_DIR / "assets" / "templates"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scaffold an iframe-based interactive HTML PPT deck."
    )
    parser.add_argument("--output", required=True, help="Output deck directory")
    parser.add_argument("--title", required=True, help="Deck title")
    parser.add_argument("--subtitle", default="", help="Deck subtitle for notes/outline")
    parser.add_argument("--slides", type=int, default=10, help="Number of content slides")
    parser.add_argument(
        "--brand",
        default="磊哥哥科技拆解室",
        help="Brand text shown on the top-left of each slide",
    )
    parser.add_argument(
        "--start-label", default="开始播放", help="Label for the cover start button"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing output directory",
    )
    return parser.parse_args()


def ensure_clean_dir(path: Path, force: bool) -> None:
    if path.exists():
        if not force:
            raise FileExistsError(f"Output directory already exists: {path}")
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    path.mkdir(parents=True, exist_ok=True)


def render(template_name: str, values: dict[str, str]) -> str:
    content = (TEMPLATES_DIR / template_name).read_text(encoding="utf-8")
    for key, value in values.items():
        content = content.replace(f"{{{{{key}}}}}", value)
    return content


def escape(value: str) -> str:
    return html.escape(value, quote=True)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def copy_shared_assets(output_dir: Path) -> None:
    assets_dir = output_dir / "assets"
    images_dir = assets_dir / "images"
    assets_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(BASE_ASSETS_DIR / "deck.css", assets_dir / "deck.css")
    shutil.copy2(BASE_ASSETS_DIR / "deck.js", assets_dir / "deck.js")


def build_iframes(slides: int) -> str:
    return "\n".join(
        [
            f'        <iframe class="deck-slide" src="slides/slide-{index:02d}.html" title="第 {index} 页"></iframe>'
            for index in range(1, slides + 1)
        ]
    )


def build_outline(title: str, subtitle: str, slides: int, brand: str) -> str:
    subtitle_block = f"- 副标题：{subtitle}\n" if subtitle else ""
    slide_lines = "\n".join(
        [
            (
                f"## Slide {index:02d}\n"
                f"- 核心标题：\n"
                f"- 一句话主张：\n"
                f"- 3 个支持点：\n"
                f"- 配图主题：\n"
            )
            for index in range(1, slides + 1)
        ]
    )
    return (
        f"# {title}\n\n"
        f"{subtitle_block}"
        f"- 结构：封面在 `index.html`，内容页在 `slides/`\n"
        f"- 默认品牌：{brand}\n"
        f"- 默认风格：瑞士风 + 红白浅色 + 像素科技感 + 统一内容配图\n\n"
        f"{slide_lines}"
    )


def scaffold_index(output_dir: Path, title: str, start_label: str, slides: int, subtitle: str) -> None:
    document_title = title if not subtitle else f"{title}｜{subtitle}"
    content = render(
        "index.template.html",
        {
            "DOCUMENT_TITLE": escape(document_title),
            "COVER_TITLE": escape(title),
            "START_LABEL": escape(start_label),
            "SLIDE_IFRAMES": build_iframes(slides),
            "TOTAL_SLIDES": f"{slides:02d}",
        },
    )
    write_text(output_dir / "index.html", content)


def scaffold_slides(output_dir: Path, brand: str, slides: int) -> None:
    for index in range(1, slides + 1):
        slide_num = f"{index:02d}"
        content = render(
            "slide.template.html",
            {
                "PAGE_NUM": slide_num,
                "TOTAL_SLIDES": f"{slides:02d}",
                "PAGE_TITLE": escape(f"第 {index} 页标题"),
                "BRAND": escape(brand),
                "EYEBROW": "核心观点",
                "SLIDE_TITLE": escape(f"在这里填写第 {index} 页标题"),
                "LEAD": escape("在这里填写一句话核心观点，保持短句、强节奏、可演示。"),
                "BULLET_1": escape("先写第一个关键论点，尽量控制在一行到一行半。"),
                "BULLET_2": escape("再写第二个支持点，优先保留信息密度和节奏感。"),
                "BULLET_3": escape("最后写第三个补充点；如果内容太多，直接拆成下一页。"),
                "CHIP_1": escape("核心判断"),
                "CHIP_2": escape("交互演示"),
                "CHIP_3": escape("关键图解"),
                "QUOTE": escape("“一页只讲透一个观点，视觉和节奏一起服务结论。”"),
                "STAMP": escape("内容模块"),
                "PANEL_TITLE": escape("右侧关键信息区"),
                "SIDE_COPY": escape("右侧放与本页结论直接相关的配图、图表、时间线或对比结构。"),
                "METRIC_1_VALUE": escape("01"),
                "METRIC_1_LABEL": escape("主结论"),
                "METRIC_2_VALUE": escape("3x"),
                "METRIC_2_LABEL": escape("支持点"),
                "METRIC_3_VALUE": escape("16:9"),
                "METRIC_3_LABEL": escape("严格适配"),
                "PLACEHOLDER_TITLE": escape("在这里替换为本页核心配图"),
                "PLACEHOLDER_COPY": escape("建议放入能直接支持本页论点的图片、图表或结构示意。"),
                "MEDIA_TAG": escape("核心图示"),
                "MEDIA_NOTE": escape("用一句短说明交代图像如何支持本页结论。"),
            },
        )
        write_text(output_dir / "slides" / f"slide-{slide_num}.html", content)


def main() -> int:
    args = parse_args()

    if args.slides < 1:
        print("--slides must be at least 1", file=sys.stderr)
        return 1

    output_dir = Path(args.output).expanduser().resolve()

    try:
        ensure_clean_dir(output_dir, args.force)
    except FileExistsError as error:
        print(str(error), file=sys.stderr)
        return 1

    copy_shared_assets(output_dir)
    scaffold_index(output_dir, args.title, args.start_label, args.slides, args.subtitle)
    scaffold_slides(output_dir, args.brand, args.slides)
    write_text(
        output_dir / "outline.md",
        build_outline(args.title, args.subtitle, args.slides, args.brand),
    )

    print(f"[OK] Deck scaffolded at {output_dir}")
    print(f"[OK] Slides: {args.slides}")
    print(f"[OK] Brand: {args.brand}")
    print(
        "[NEXT] Enable the bundled visual editor with:\n"
        f"       python3 {SKILL_DIR / 'scripts' / 'enable_web_ppt_editor.py'} --project {output_dir} --launch --open"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
