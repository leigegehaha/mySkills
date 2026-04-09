from __future__ import annotations

import argparse
import html
import importlib.util
import json
import math
import os
import re
import shutil
import struct
import subprocess
import textwrap
import wave
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import imageio_ffmpeg
from playwright.sync_api import sync_playwright

ROOT = Path("/Users/zhangleiandhim/.codex/skills/lei-bloger-av")
TTS_SKILL = Path("/Users/zhangleiandhim/.codex/skills/lei-bloger-tts")
TTS_SYNTH_PROJECT = TTS_SKILL / "scripts" / "synthesize_project.py"
OUTPUT_ROOT = Path("/Users/zhangleiandhim/Documents/index-tts2/outputs/lei_av")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
WIDTH = 1920
HEIGHT = 1080
FPS = 12
BRAND = "磊哥哥科技拆解室"


def progress(label: str, index: int, total: int) -> None:
    filled = int(index / total * 24) if total else 24
    print(f"[lei-bloger-av] [{'#' * filled}{'-' * (24 - filled)}] {index}/{total} | {label}", flush=True)


def load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


TTS_SYNTH = load_module(TTS_SKILL / "scripts" / "synthesize.py", "lei_bloger_tts_synth")
TTS_SCAFFOLD = load_module(TTS_SKILL / "scripts" / "scaffold_long_form_project.py", "lei_bloger_tts_scaffold")


def parse_args():
    parser = argparse.ArgumentParser(description="Generate Lei long-form audio + PPT-style video from text or file.")
    parser.add_argument("--text", default=None, help="Raw input text.")
    parser.add_argument("--input-file", default=None, help="Path to input txt/md file.")
    parser.add_argument("--output-dir", default=None, help="Optional output directory.")
    parser.add_argument("--slug", default=None, help="Optional folder slug.")
    parser.add_argument("--reuse-project-file", default=None, help="Reuse an existing TTS project json instead of regenerating audio.")
    parser.add_argument("--reuse-audio-file", default=None, help="Reuse an existing merged wav instead of regenerating audio.")
    parser.add_argument("--min-scene-seconds", type=float, default=7.0, help="Minimum scene duration.")
    parser.add_argument("--max-scene-seconds", type=float, default=10.0, help="Maximum scene duration.")
    parser.add_argument("--target-scene-seconds", type=float, default=8.4, help="Target scene duration.")
    parser.add_argument("--keep-tts-segments", action="store_true", help="Keep intermediate segment wav files.")
    return parser.parse_args()


def slugify(text: str) -> str:
    value = re.sub(r"\s+", "-", text.strip())
    value = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff_-]", "", value)
    value = value[:36].strip("-_")
    return value or "lei-bloger-av"


def load_text(args) -> str:
    if args.text:
        return args.text.strip()
    if args.input_file:
        return Path(args.input_file).read_text(encoding="utf-8").strip()
    raise ValueError("请提供 --text 或 --input-file。")


def normalize_punctuation(text: str) -> str:
    replacements = {
        ",": "，",
        ";": "；",
        ":": "：",
        "?": "？",
        "!": "！",
        "（ ": "（",
        " ）": "）",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s*([，。！？；：、])\s*", r"\1 ", text)
    text = re.sub(r"\s*——\s*", " —— ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def oral_polish_sentence(sentence: str) -> str:
    sentence = sentence.strip()
    if not sentence:
        return ""
    sentence = sentence.replace("比如 ", "比如说，")
    sentence = sentence.replace("比如，", "比如说，")
    sentence = sentence.replace("首先说说", "首先说说，")
    sentence = sentence.replace("再说说", "再说说，")
    sentence = sentence.replace("最后聊聊", "最后聊聊，")
    sentence = sentence.replace("最后做个总结", "最后做个总结，")
    sentence = sentence.replace("说白了就是", "说白了就是，")
    sentence = sentence.replace("其实", "其实，", 1) if sentence.startswith("其实") else sentence
    sentence = sentence.replace("不过", "不过，", 1) if sentence.startswith("不过") else sentence
    sentence = sentence.replace("当然", "当然，", 1) if sentence.startswith("当然") else sentence
    sentence = sentence.replace("所以", "所以，", 1) if sentence.startswith("所以") else sentence
    sentence = re.sub(r"\s+", " ", sentence).strip()
    if sentence and sentence[-1] not in "。！？":
        sentence += "。"
    return normalize_punctuation(sentence)


def split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[。！？])\s*", normalize_punctuation(text))
    return [oral_polish_sentence(part) for part in parts if part.strip()]


def build_polished_text(text: str) -> str:
    sentences = split_sentences(text)
    return "\n".join(sentences)


def summarize_title(text: str, index: int) -> str:
    title_keywords = [
        ("OpenClaw", "OpenClaw 判断"),
        ("多 Agent", "多 Agent 集群"),
        ("操作系统", "AI 操作系统"),
        ("流量", "流量入口"),
        ("总结", "总结判断"),
        ("安全", "风险与安全"),
        ("Workbuddy", "本土产品趋势"),
    ]
    for keyword, title in title_keywords:
        if keyword.lower() in text.lower():
            return f"{index:02d}｜{title}"
    short = re.sub(r"[。！？].*", "", text).strip()
    short = short[:18] if len(short) > 18 else short
    return f"{index:02d}｜{short or f'第{index}段'}"


def build_tts_sections(polished_text: str, max_chars: int = 210) -> List[Dict]:
    sentences = [line.strip() for line in polished_text.splitlines() if line.strip()]
    sections: List[Dict] = []
    current: List[str] = []
    count = 0
    for sentence in sentences:
        if current and count + len(sentence) > max_chars:
            joined = " ".join(current).strip()
            sections.append({"title": summarize_title(joined, len(sections) + 1), "text": joined})
            current = [sentence]
            count = len(sentence)
        else:
            current.append(sentence)
            count += len(sentence)
    if current:
        joined = " ".join(current).strip()
        sections.append({"title": summarize_title(joined, len(sections) + 1), "text": joined})
    return sections


def infer_emotion(title: str, text: str) -> Dict:
    lower = f"{title} {text}".lower()
    if re.search(r"开场|大家好|判断|分类", lower):
        return {"emotion_mode": "vector", "emo_alpha": 0.62, "emo_vector": [0.44, 0.0, 0.0, 0.0, 0.0, 0.0, 0.12, 0.12]}
    if re.search(r"吸引|活过来|养龙虾|成长|生命力", lower):
        return {"emotion_mode": "vector", "emo_alpha": 0.72, "emo_vector": [0.58, 0.0, 0.0, 0.0, 0.0, 0.0, 0.18, 0.08]}
    if re.search(r"问题|安全|门槛|复杂|坑|隐私|封杀|风险", lower):
        return {"emotion_mode": "vector", "emo_alpha": 0.58, "emo_vector": [0.12, 0.08, 0.03, 0.02, 0.01, 0.03, 0.06, 0.14]}
    if re.search(r"趋势|机会|普及|优势|推广|未来|火|预测", lower):
        return {"emotion_mode": "vector", "emo_alpha": 0.66, "emo_vector": [0.48, 0.0, 0.0, 0.0, 0.0, 0.0, 0.16, 0.10]}
    if re.search(r"总结|最后", lower):
        return {"emotion_mode": "vector", "emo_alpha": 0.64, "emo_vector": [0.40, 0.0, 0.0, 0.0, 0.0, 0.0, 0.12, 0.16]}
    return {"emotion_mode": "vector", "emo_alpha": 0.63, "emo_vector": [0.38, 0.0, 0.0, 0.0, 0.0, 0.0, 0.12, 0.16]}


def smooth_emotions(segments: List[Dict]) -> List[Dict]:
    previous = None
    result = []
    for segment in segments:
        current = infer_emotion(segment["title"], segment["text"])
        if previous:
            alpha = round(previous["emo_alpha"] * 0.4 + current["emo_alpha"] * 0.6, 2)
            vector = [round(p * 0.4 + c * 0.6, 4) for p, c in zip(previous["emo_vector"], current["emo_vector"])]
            current = {"emotion_mode": "vector", "emo_alpha": alpha, "emo_vector": vector}
        result.append({**segment, "emotion": current})
        previous = current
    return result


def save_segments_markdown(segments: List[Dict], path: Path) -> None:
    lines = []
    for segment in segments:
        lines.append(f"## {segment['title']}")
        lines.append(segment["text"])
        lines.append("")
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def build_tts_project(segments: List[Dict], project_path: Path, audio_path: Path) -> Dict:
    project = {
        "title": f"{project_path.stem} oral project",
        "config_file": str(TTS_SKILL / "emotion_config.json"),
        "profile": "lively_excited",
        "output_path": str(audio_path),
        "keep_segments": True,
        "segments": segments,
    }
    project_path.write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")
    return project


def run_tts(project_path: Path, keep_segments: bool) -> None:
    cmd = ["python3", str(TTS_SYNTH_PROJECT), "--project-file", str(project_path)]
    if keep_segments:
        cmd.append("--keep-segments")
    subprocess.run(cmd, check=True, text=True)


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wav_file:
        return wav_file.getnframes() / wav_file.getframerate()


def segment_audio_paths(audio_path: Path, count: int) -> List[Path]:
    root, ext = os.path.splitext(str(audio_path))
    return [Path(f"{root}.seg{index:02d}{ext or '.wav'}") for index in range(1, count + 1)]


def proportional_segment_durations(segments: List[Dict], total_audio_seconds: float) -> List[float]:
    total_chars = sum(max(len(segment["text"]), 1) for segment in segments) or 1
    durations = []
    for segment in segments:
        durations.append(total_audio_seconds * max(len(segment["text"]), 1) / total_chars)
    if durations:
        drift = total_audio_seconds - sum(durations)
        durations[-1] += drift
    return [round(duration, 2) for duration in durations]


def split_visual_units(text: str) -> List[str]:
    clauses = [part.strip() for part in re.split(r"(?<=[。；！？])\s*", text) if part.strip()]
    return clauses or [text]


def chunk_text_by_length(text: str, parts: int) -> List[str]:
    chars_total = len(text)
    if chars_total == 0:
        return [text]
    chunk_size = max(24, math.ceil(chars_total / max(parts, 1)))
    chunks = [text[i:i + chunk_size].strip() for i in range(0, chars_total, chunk_size)]
    return [chunk for chunk in chunks if chunk]


def group_clauses_to_scenes(clauses: List[str], total_seconds: float, min_s: float, max_s: float, target_s: float, depth: int = 0) -> List[Dict]:
    if total_seconds <= max_s or total_seconds < min_s * 2:
        return [{"text": " ".join(clauses).strip(), "duration": round(total_seconds, 2)}]
    full_chars = sum(max(len(c), 1) for c in clauses)
    if full_chars == 0:
        return [{"text": " ", "duration": total_seconds}]
    cps = full_chars / max(total_seconds, 0.001)
    target_chars = max(40, int(cps * target_s))
    groups: List[List[str]] = []
    current: List[str] = []
    chars = 0
    for clause in clauses:
        c_len = len(clause)
        if current and chars + c_len > target_chars:
            groups.append(current)
            current = [clause]
            chars = c_len
        else:
            current.append(clause)
            chars += c_len
    if current:
        groups.append(current)

    scenes = []
    for group in groups:
        text = " ".join(group).strip()
        proportion = sum(len(item) for item in group) / full_chars
        duration = proportion * total_seconds
        scenes.append({"text": text, "duration": duration})

    merged: List[Dict] = []
    for scene in scenes:
        if merged and scene["duration"] < min_s:
            merged[-1]["text"] += " " + scene["text"]
            merged[-1]["duration"] += scene["duration"]
        else:
            merged.append(scene)

    final_scenes: List[Dict] = []
    for scene in merged:
        if scene["duration"] <= max_s:
            final_scenes.append(scene)
            continue
        if depth >= 6:
            parts = max(2, int(math.ceil(scene["duration"] / target_s)))
            sub = [{"text": chunk, "duration": scene["duration"] / parts} for chunk in chunk_text_by_length(scene["text"], parts)]
            final_scenes.extend(sub)
            continue
        sentence_clauses = split_visual_units(scene["text"])
        if len(sentence_clauses) == 1 or sentence_clauses == [scene["text"]]:
            parts = max(2, int(math.ceil(scene["duration"] / target_s)))
            chunks = chunk_text_by_length(scene["text"], parts)
        else:
            chunks = sentence_clauses
        sub = group_clauses_to_scenes(chunks, scene["duration"], min_s, max_s, target_s, depth + 1)
        final_scenes.extend(sub)

    total = sum(scene["duration"] for scene in final_scenes) or 1
    ratio = total_seconds / total
    for scene in final_scenes:
        scene["duration"] = round(scene["duration"] * ratio, 2)
    normalized: List[Dict] = []
    for scene in final_scenes:
        if normalized and scene["duration"] < min_s:
            normalized[-1]["text"] += " " + scene["text"]
            normalized[-1]["duration"] = round(normalized[-1]["duration"] + scene["duration"], 2)
        else:
            normalized.append(scene)
    if len(normalized) >= 2 and normalized[0]["duration"] < min_s:
        normalized[1]["text"] = normalized[0]["text"] + " " + normalized[1]["text"]
        normalized[1]["duration"] = round(normalized[0]["duration"] + normalized[1]["duration"], 2)
        normalized = normalized[1:]
    bounded: List[Dict] = []
    for scene in normalized:
        if scene["duration"] <= max_s:
            bounded.append(scene)
            continue
        parts = max(2, int(math.ceil(scene["duration"] / max_s)))
        chunks = chunk_text_by_length(scene["text"], parts)
        chunk_durations = proportional_segment_durations(
            [{"text": chunk} for chunk in chunks],
            scene["duration"],
        )
        for chunk, duration in zip(chunks, chunk_durations):
            bounded.append({"text": chunk, "duration": duration})
    drift = round(total_seconds - sum(scene["duration"] for scene in bounded), 2)
    if bounded:
        bounded[-1]["duration"] = round(bounded[-1]["duration"] + drift, 2)
    return bounded


def extract_brands(text: str) -> List[str]:
    brand_patterns = [
        "OpenClaw", "codex", "claude code", "Claude Work", "Workbuddy", "豆包", "微信", "飞书", "QQ",
        "腾讯", "阿里", "智谱", "Kimi", "Deepseek", "Windows", "Mac", "安卓", "鸿蒙",
    ]
    hits = []
    lower = text.lower()
    for brand in brand_patterns:
        if brand.lower() in lower and brand not in hits:
            hits.append(brand)
    return hits[:4]


def infer_template(text: str) -> str:
    lower = text.lower()
    if re.search(r"第一类|第二类|第三类|分成三类|总结|预测", lower):
        return "compare"
    if re.search(r"比如|openclaw|codex|claude|workbuddy|微信|飞书|qq|kimi|deepseek|windows|mac|豆包", lower):
        return "brand"
    if re.search(r"问题|复杂|安全|隐私|风险|坑", lower):
        return "issue"
    if re.search(r"趋势|未来|流量|操作系统|集群|机会|普及|推广", lower):
        return "trend"
    return "statement"


def scene_title(text: str, index: int) -> str:
    sentence = re.sub(r"[。！？].*", "", text).strip()
    if len(sentence) > 22:
        sentence = sentence[:22]
    return sentence or f"场景 {index}"


def scene_bullets(text: str) -> List[str]:
    parts = [part.strip("，。；： ") for part in re.split(r"[，；。]", text) if part.strip()]
    bullets = []
    for part in parts:
        if len(part) > 28:
            bullets.append(part[:28] + "…")
        else:
            bullets.append(part)
    return bullets[:4]


def shorten_text(text: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip("，。；： ") + "…"


def sentence_parts(text: str) -> List[str]:
    parts = [part.strip("，。；： ") for part in re.split(r"[，。；：！？]", text) if part.strip("，。；： ")]
    return parts


def build_takeaway(text: str) -> str:
    parts = sentence_parts(text)
    if not parts:
        return shorten_text(text, 26)
    if len(parts) >= 2:
        candidate = f"{parts[0]}，{parts[1]}"
    else:
        candidate = parts[0]
    return shorten_text(candidate, 30)


def build_subtitle(scene: Dict) -> str:
    template_map = {
        "compare": "这一页重点，是把结构和分类讲清楚。",
        "brand": "这一页重点，是把产品、品牌和入口对应起来。",
        "issue": "这一页重点，是把问题、风险和门槛拆开说明。",
        "trend": "这一页重点，是把趋势、机会和后续变化讲透。",
        "statement": "这一页重点，是把这段话的核心意思讲明白。",
    }
    base = template_map.get(scene["template"], template_map["statement"])
    return shorten_text(base, 34)


def build_detail_points(scene: Dict) -> List[str]:
    points = []
    for part in sentence_parts(scene["text"]):
        points.append(shorten_text(part, 26))
    for bullet in scene.get("bullets", []):
        clean = shorten_text(bullet, 26)
        if clean not in points:
            points.append(clean)
    if scene.get("brands"):
        for brand in scene["brands"][:3]:
            note = f"{brand} 是这一页涉及到的关键对象。"
            points.append(shorten_text(note, 26))
    deduped = []
    for point in points:
        if point and point not in deduped:
            deduped.append(point)
    while len(deduped) < 3:
        deduped.append("这一页继续补充相关背景和实际意义。")
    return deduped[:4]


def build_support_cards(scene: Dict) -> List[Dict]:
    cards: List[Dict] = []
    if scene["template"] == "compare":
        cards.append({"title": "结构", "body": "先讲分类，再讲差异，再讲为什么重要。"})
        cards.append({"title": "理解", "body": "把抽象概念翻译成更容易理解的使用场景。"})
    elif scene["template"] == "brand":
        cards.append({"title": "品牌", "body": "这一页聚焦具体产品、品牌或软件入口。"})
        cards.append({"title": "作用", "body": "通过品牌案例把抽象观点落到真实产品上。"})
    elif scene["template"] == "issue":
        cards.append({"title": "问题", "body": "把复杂问题拆成安装、配置、安全等更具体的小点。"})
        cards.append({"title": "结论", "body": "不是简单否定，而是解释为什么推广门槛高。"})
    elif scene["template"] == "trend":
        cards.append({"title": "趋势", "body": "从产品变化、商业模式和用户入口三个角度看。"})
        cards.append({"title": "判断", "body": "用更口语化的方式，把趋势判断说得更顺。"})
    else:
        cards.append({"title": "核心", "body": "这页先用一句话定住结论，再往下展开。"})
        cards.append({"title": "展开", "body": "让观众先抓住重点，再理解细节。"})
    return cards


def build_page_outline(scene: Dict) -> Dict:
    detail_points = build_detail_points(scene)
    return {
        "page_id": scene["id"],
        "yellow_summary": build_takeaway(scene["text"]),
        "red_subtitle": build_subtitle(scene),
        "green_left_title": shorten_text(scene["title"], 20),
        "green_left_quote": shorten_text(scene["text"], 56),
        "green_left_visual": scene["template"],
        "green_right_top_title": "展开讲解",
        "green_right_top_points": detail_points[:3],
        "green_right_bottom_title": "补充信息",
        "green_right_bottom_cards": build_support_cards(scene),
        "brands": scene.get("brands", []),
    }


def write_outline_files(storyboard: Dict, output_dir: Path) -> tuple[Path, Path]:
    outline_json = output_dir / "html_outline.json"
    outline_md = output_dir / "html_outline.md"
    pages = []
    md_lines = ["# HTML 页面大纲", ""]
    for scene in storyboard["scenes"]:
        outline = build_page_outline(scene)
        page = {
            "page_id": scene["id"],
            "segment_title": scene["segment_title"],
            "duration": scene["duration"],
            "audio_start": scene["audio_start"],
            "template": scene["template"],
            "source_text": scene["text"],
            "zones": outline,
        }
        pages.append(page)
        md_lines.extend(
            [
                f"## {scene['id']}｜{scene['segment_title']}",
                f"- 黄色区域：{outline['yellow_summary']}",
                f"- 红色区域：{outline['red_subtitle']}",
                f"- 绿色左区：{outline['green_left_title']} / {outline['green_left_quote']}",
                f"- 绿色右上：{'；'.join(outline['green_right_top_points'])}",
                f"- 绿色右下：{'；'.join(card['title'] + '：' + card['body'] for card in outline['green_right_bottom_cards'])}",
                "",
            ]
        )
    outline_json.write_text(json.dumps({"pages": pages}, ensure_ascii=False, indent=2), encoding="utf-8")
    outline_md.write_text("\n".join(md_lines), encoding="utf-8")
    return outline_json, outline_md


def build_storyboard(segments: List[Dict], segment_wavs: List[Path] | None, audio_path: Path, output_path: Path, min_s: float, max_s: float, target_s: float) -> Dict:
    scenes = []
    start = 0.0
    scene_index = 1
    if segment_wavs:
        segment_durations = [wav_duration(path) for path in segment_wavs]
        total_audio_seconds = round(sum(segment_durations), 2)
    else:
        total_audio_seconds = round(wav_duration(audio_path), 2)
        segment_durations = proportional_segment_durations(segments, total_audio_seconds)
    for segment, duration in zip(segments, segment_durations):
        clause_groups = group_clauses_to_scenes(split_visual_units(segment["text"]), duration, min_s, max_s, target_s)
        consumed = 0.0
        for group in clause_groups:
            title = scene_title(group["text"], scene_index)
            scenes.append(
                {
                    "id": f"s{scene_index:03d}",
                    "segment_title": segment["title"],
                    "title": title,
                    "text": group["text"],
                    "template": infer_template(group["text"]),
                    "bullets": scene_bullets(group["text"]),
                    "brands": extract_brands(group["text"]),
                    "duration": group["duration"],
                    "audio_start": round(start + consumed, 2),
                    "audio_duration": group["duration"],
                }
            )
            consumed += group["duration"]
            scene_index += 1
        start += duration
    durations = [scene["duration"] for scene in scenes]
    for i, duration in enumerate(durations):
        if duration >= min_s:
            continue
        need = round(min_s - duration, 2)
        for j in range(i + 1, len(durations)):
            slack = round(durations[j] - min_s, 2)
            if slack <= 0:
                continue
            give = min(slack, need)
            durations[j] = round(durations[j] - give, 2)
            durations[i] = round(durations[i] + give, 2)
            need = round(need - give, 2)
            if need <= 0:
                break
        if need > 0:
            for j in range(i - 1, -1, -1):
                slack = round(durations[j] - min_s, 2)
                if slack <= 0:
                    continue
                give = min(slack, need)
                durations[j] = round(durations[j] - give, 2)
                durations[i] = round(durations[i] + give, 2)
                need = round(need - give, 2)
                if need <= 0:
                    break
    for scene, duration in zip(scenes, durations):
        scene["duration"] = duration
    drift = round(total_audio_seconds - sum(scene["duration"] for scene in scenes), 2)
    if scenes:
        scenes[-1]["duration"] = round(scenes[-1]["duration"] + drift, 2)

    storyboard = {
        "audio_path": str(audio_path),
        "total_audio_seconds": total_audio_seconds,
        "scenes": scenes,
        "style": {
            "brand": BRAND,
            "width": WIDTH,
            "height": HEIGHT,
            "fps": FPS,
            "min_scene_seconds": min_s,
            "max_scene_seconds": max_s,
        },
    }
    output_path.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")
    return storyboard


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def wrap_lines(text: str, width: int = 18) -> str:
    lines = textwrap.wrap(text, width=width, break_long_words=False, break_on_hyphens=False) or [text]
    return "<br>".join(esc(line) for line in lines[:3])


def icon_svg(kind: str) -> str:
    if kind == "compare":
        return "<svg viewBox='0 0 560 440'><rect x='58' y='84' width='132' height='252' rx='24' fill='#fff' stroke='#f1ccd2'/><rect x='214' y='84' width='132' height='252' rx='24' fill='#fff5f6' stroke='#f1ccd2'/><rect x='370' y='84' width='132' height='252' rx='24' fill='#fff' stroke='#f1ccd2'/><circle cx='124' cy='142' r='26' fill='#111'/><circle cx='280' cy='142' r='26' fill='#c8102e'/><circle cx='436' cy='142' r='26' fill='#111'/><rect x='88' y='204' width='72' height='16' rx='8' fill='#c8102e'/><rect x='244' y='204' width='72' height='16' rx='8' fill='#c8102e'/><rect x='400' y='204' width='72' height='16' rx='8' fill='#c8102e'/></svg>"
    if kind == "brand":
        return "<svg viewBox='0 0 560 440'><circle cx='122' cy='120' r='54' fill='#c8102e'/><circle cx='280' cy='120' r='54' fill='#111'/><circle cx='438' cy='120' r='54' fill='#f06a7d'/><rect x='164' y='228' width='232' height='120' rx='28' fill='#fff' stroke='#f1ccd2'/><path d='M122 176L196 228M280 176L280 228M438 176L364 228' stroke='#c8102e' stroke-width='4' fill='none' stroke-linecap='round'/><rect x='212' y='260' width='136' height='18' rx='9' fill='#c8102e'/><rect x='196' y='296' width='168' height='18' rx='9' fill='#ffd8de'/></svg>"
    if kind == "issue":
        return "<svg viewBox='0 0 560 440'><rect x='78' y='78' width='404' height='252' rx='28' fill='#fff7f8' stroke='#f1ccd2'/><circle cx='180' cy='204' r='62' fill='#fff' stroke='#c8102e' stroke-width='4'/><path d='M180 166v52M180 248v4' stroke='#c8102e' stroke-width='4' fill='none' stroke-linecap='round'/><rect x='274' y='138' width='132' height='24' rx='12' fill='#c8102e'/><rect x='274' y='186' width='168' height='24' rx='12' fill='#ffd8de'/><rect x='274' y='234' width='146' height='24' rx='12' fill='#ffecef'/></svg>"
    if kind == "trend":
        return "<svg viewBox='0 0 560 440'><rect x='60' y='82' width='440' height='280' rx='28' fill='#fff' stroke='#f1ccd2'/><path d='M110 308H448M110 308V126' stroke='#c8102e' stroke-width='4' fill='none' stroke-linecap='round'/><path d='M134 286L208 248L278 222L352 164L430 132' stroke='#c8102e' stroke-width='8' fill='none'/><circle cx='134' cy='286' r='10' fill='#c8102e'/><circle cx='208' cy='248' r='10' fill='#c8102e'/><circle cx='278' cy='222' r='10' fill='#c8102e'/><circle cx='352' cy='164' r='10' fill='#c8102e'/><circle cx='430' cy='132' r='10' fill='#c8102e'/></svg>"
    return "<svg viewBox='0 0 560 440'><rect x='64' y='72' width='432' height='296' rx='28' fill='#fff' stroke='#f1ccd2'/><rect x='104' y='118' width='196' height='20' rx='10' fill='#c8102e'/><rect x='104' y='156' width='268' height='18' rx='9' fill='#ffd8de'/><rect x='104' y='194' width='238' height='18' rx='9' fill='#ffecef'/><rect x='104' y='248' width='350' height='76' rx='20' fill='#fff5f6'/></svg>"


CSS = """
:root{--bg:#fffdfb;--red:#cf1f36;--ink:#121212;--muted:#686868;--line:rgba(207,31,54,.14);--soft:#fff;--warm:#f8c63d;--shadow:0 18px 60px rgba(20,14,14,.08)}
*{box-sizing:border-box} html,body{margin:0;width:100%;height:100%;overflow:hidden;background:#fff}
body{font-family:"Avenir Next","PingFang SC","Helvetica Neue",sans-serif;color:var(--ink)}
.frame{position:relative;width:1920px;height:1080px;background:radial-gradient(circle at 12% 10%, rgba(207,31,54,.06), transparent 20%),linear-gradient(180deg, rgba(207,31,54,.02), transparent 32%),#fffdfb}
.grid{position:absolute;inset:0;background-image:linear-gradient(rgba(207,31,54,.042) 1px,transparent 1px),linear-gradient(90deg,rgba(207,31,54,.042) 1px,transparent 1px);background-size:84px 84px;opacity:.8}
.rail{position:absolute;left:72px;top:68px;bottom:72px;width:14px;border-radius:14px;background:linear-gradient(180deg,var(--red),rgba(207,31,54,.26))}
.rail:after{content:"";position:absolute;left:0;bottom:0;width:14px;height:118px;border-radius:14px;background:var(--ink)}
.tag{position:absolute;right:56px;top:44px;padding:12px 18px;border:1px solid var(--line);border-radius:999px;background:rgba(255,255,255,.94);font-size:22px;font-weight:900;color:var(--red)}
.kicker{position:absolute;left:108px;top:76px;font-size:22px;letter-spacing:.16em;color:var(--red);font-weight:900;text-transform:uppercase}
.zone-summary{position:absolute;left:96px;right:96px;top:104px;height:190px;padding:24px 26px 18px 26px;border-radius:30px;background:rgba(255,255,255,.92);box-shadow:var(--shadow);border:1px solid rgba(0,0,0,.04)}
.zone-summary:before{content:"";position:absolute;left:0;top:0;height:10px;width:100%;border-radius:30px 30px 0 0;background:var(--warm)}
.summary-label{font-size:18px;letter-spacing:.18em;color:#9a6a00;font-weight:900;text-transform:uppercase}
.summary-text{margin-top:12px;font-size:84px;line-height:.96;font-weight:900;letter-spacing:-.05em}
.zone-subtitle{position:absolute;left:96px;right:96px;top:320px;height:170px;padding:28px 34px;border-radius:28px;background:rgba(255,255,255,.96);box-shadow:var(--shadow);border:1px solid rgba(0,0,0,.04)}
.zone-subtitle:before{content:"";position:absolute;left:0;top:0;height:10px;width:100%;border-radius:28px 28px 0 0;background:var(--red)}
.subtitle-chip{display:inline-block;padding:10px 16px;border-radius:999px;background:#fff4f5;color:var(--red);font-size:18px;font-weight:900;letter-spacing:.16em;text-transform:uppercase;animation:pop .5s cubic-bezier(.2,.8,.2,1)}
.subtitle-text{margin-top:18px;font-size:46px;line-height:1.25;color:var(--muted);font-weight:780;animation:fadeup .55s ease-out}
.zone-content{position:absolute;left:96px;right:96px;top:518px;bottom:76px;display:grid;grid-template-columns:1.25fr .85fr;gap:24px}
.panel{position:relative;border-radius:30px;background:rgba(255,255,255,.97);box-shadow:var(--shadow);border:1px solid rgba(0,0,0,.04);overflow:hidden}
.panel-accent:before{content:"";position:absolute;left:0;top:0;height:8px;width:100%;background:linear-gradient(90deg,#f3d37a,#f8c63d)}
.left-panel{padding:30px 34px 24px 34px}
.left-title{font-size:26px;color:var(--red);font-weight:900;letter-spacing:.14em;text-transform:uppercase}
.left-quote{margin-top:18px;font-size:64px;line-height:1.06;font-weight:900;letter-spacing:-.04em}
.left-note{margin-top:18px;font-size:28px;line-height:1.35;color:var(--muted);font-weight:760}
.left-svg{position:absolute;left:32px;right:32px;bottom:26px;height:220px}
.left-svg svg{width:100%;height:100%}
.right-stack{display:grid;grid-template-rows:1fr 1fr;gap:24px}
.right-card{padding:26px 28px}
.right-card h3{margin:0;font-size:24px;color:var(--red);letter-spacing:.14em;text-transform:uppercase}
.point-list{display:flex;flex-direction:column;gap:14px;margin-top:18px}
.point{padding:16px 18px;border-radius:20px;background:#fff6f7;border:1px solid rgba(207,31,54,.1);font-size:26px;line-height:1.34;font-weight:770}
.info-grid{display:grid;grid-template-columns:1fr;gap:14px;margin-top:18px}
.info-card{padding:18px;border-radius:20px;background:#fff;border:1px solid rgba(0,0,0,.06)}
.info-top{font-size:17px;color:var(--red);font-weight:900;letter-spacing:.14em;text-transform:uppercase}
.info-body{margin-top:10px;font-size:25px;line-height:1.34;font-weight:780}
.brand-strip{display:flex;gap:12px;flex-wrap:wrap;margin-top:14px}
.brand-pill{padding:10px 14px;border-radius:999px;background:#fff4f5;color:var(--red);font-size:20px;font-weight:850}
.footer{position:absolute;left:110px;right:96px;bottom:36px;padding-top:8px;color:#7a7a7a;font-size:18px;font-weight:700}
@keyframes pop{from{opacity:0;transform:scale(.92) translateY(8px)}to{opacity:1;transform:scale(1) translateY(0)}}
@keyframes fadeup{from{opacity:0;transform:translateY(18px)}to{opacity:1;transform:translateY(0)}}
"""


def build_html_from_page(page: Dict) -> str:
    outline = page["zones"]
    point_html = "".join(f"<div class='point'>{esc(item)}</div>" for item in outline["green_right_top_points"])
    card_html = "".join(
        f"<div class='info-card'><div class='info-top'>{esc(card['title'])}</div><div class='info-body'>{esc(card['body'])}</div></div>"
        for card in outline["green_right_bottom_cards"]
    )
    brand_html = ""
    if outline["brands"]:
        brand_html = "<div class='brand-strip'>" + "".join(
            f"<div class='brand-pill'>{esc(brand)}</div>" for brand in outline["brands"]
        ) + "</div>"
    return f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=1920,height=1080,initial-scale=1'><style>{CSS}</style></head><body>
<div class='frame'><div class='grid'></div><div class='rail'></div><div class='tag'>{BRAND}</div><div class='kicker'>{esc(page['segment_title'])}</div>
<section class='zone-summary'>
  <div class='summary-label'>一句话总结</div>
  <div class='summary-text'>{wrap_lines(outline['yellow_summary'], 12)}</div>
</section>
<section class='zone-subtitle'>
  <div class='subtitle-chip'>页面主题</div>
  <div class='subtitle-text'>{esc(outline['red_subtitle'])}</div>
</section>
<section class='zone-content'>
  <div class='panel panel-accent left-panel'>
    <div class='left-title'>{esc(outline['green_left_title'])}</div>
    <div class='left-quote'>“{wrap_lines(outline['green_left_quote'], 16)}”</div>
    <div class='left-note'>{esc(page['source_text'])}</div>
    <div class='left-svg'>{icon_svg(outline['green_left_visual'])}</div>
  </div>
  <div class='right-stack'>
    <div class='panel right-card'>
      <h3>{esc(outline['green_right_top_title'])}</h3>
      <div class='point-list'>{point_html}</div>
    </div>
    <div class='panel right-card'>
      <h3>{esc(outline['green_right_bottom_title'])}</h3>
      {brand_html}
      <div class='info-grid'>{card_html}</div>
    </div>
  </div>
</section>
<div class='footer'>page {esc(page['page_id'])} · {page['duration']}s · 音频起点 {page['audio_start']}s</div>
</div></body></html>"""


def render_pages_from_outline(outline_json_path: Path, html_dir: Path, png_dir: Path) -> List[Dict]:
    html_dir.mkdir(parents=True, exist_ok=True)
    png_dir.mkdir(parents=True, exist_ok=True)
    pages = json.loads(outline_json_path.read_text(encoding="utf-8"))["pages"]
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=CHROME)
        page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT}, device_scale_factor=1)
        total = len(pages)
        for index, item in enumerate(pages, start=1):
            html_path = html_dir / f"{item['page_id']}.html"
            png_path = png_dir / f"{item['page_id']}.png"
            item["html_path"] = str(html_path)
            item["png_path"] = str(png_path)
            html_path.write_text(build_html_from_page(item), encoding="utf-8")
            page.goto(html_path.as_uri(), wait_until="load")
            page.wait_for_timeout(250)
            page.screenshot(path=str(png_path))
            progress(f"渲染画面 {item['page_id']}", index, total)
        browser.close()
    return pages


def ffmpeg() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()


def make_clip_from_png(png_path: Path, duration: float, out_path: Path) -> None:
    subprocess.run(
        [
            ffmpeg(),
            "-y",
            "-loop",
            "1",
            "-i",
            str(png_path),
            "-t",
            str(duration),
            "-vf",
            f"scale={WIDTH}:{HEIGHT},fps={FPS}",
            "-pix_fmt",
            "yuv420p",
            "-c:v",
            "libx264",
            str(out_path),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def concat_video_clips(clips: List[Path], out_path: Path) -> None:
    concat_file = out_path.with_suffix(".txt")
    concat_file.write_text("".join(f"file '{clip.as_posix()}'\n" for clip in clips), encoding="utf-8")
    subprocess.run(
        [ffmpeg(), "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(out_path)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def read_wav_pcm(path: Path):
    with wave.open(str(path), "rb") as reader:
        channels = reader.getnchannels()
        sampwidth = reader.getsampwidth()
        framerate = reader.getframerate()
        raw = reader.readframes(reader.getnframes())
    if sampwidth != 2:
        raise ValueError("Only 16-bit wav supported.")
    samples = list(struct.unpack("<" + "h" * (len(raw) // 2), raw))
    return channels, sampwidth, framerate, samples


def write_wav_pcm(path: Path, channels: int, sampwidth: int, framerate: int, samples: List[int]) -> None:
    raw = struct.pack("<" + "h" * len(samples), *samples)
    with wave.open(str(path), "wb") as writer:
        writer.setnchannels(channels)
        writer.setsampwidth(sampwidth)
        writer.setframerate(framerate)
        writer.writeframes(raw)


def overlay_transition_sfx(source_audio: Path, target_audio: Path, boundaries: List[float], gain: float = 0.17) -> None:
    channels, sampwidth, framerate, samples = read_wav_pcm(source_audio)
    total_frames = len(samples) // channels
    effect_duration = 0.22
    effect_count = int(effect_duration * framerate)

    def pseudo_noise(i: int) -> float:
        value = math.sin(i * 12.9898) * 43758.5453
        return (value - math.floor(value)) * 2.0 - 1.0

    effect = []
    for i in range(effect_count):
        t = i / framerate
        sweep = math.sin(2 * math.pi * (560 + 2000 * (t / effect_duration)) * t)
        click = math.sin(2 * math.pi * 1300 * t)
        noise = pseudo_noise(i) * 0.25
        env = (1 - t / effect_duration) ** 2
        sample = (sweep * 0.52 + click * 0.16 + noise * 0.18) * env
        effect.append(int(sample * 32767 * gain))

    for boundary in boundaries:
        start_frame = int(max(0, boundary - 0.03) * framerate)
        for i, fx in enumerate(effect):
            pos = start_frame + i
            if pos >= total_frames:
                break
            for channel in range(channels):
                idx = pos * channels + channel
                mixed = samples[idx] + fx
                samples[idx] = max(-32768, min(32767, mixed))
    write_wav_pcm(target_audio, channels, sampwidth, framerate, samples)


def mux_video_audio(video_path: Path, audio_path: Path, out_path: Path) -> None:
    subprocess.run(
        [ffmpeg(), "-y", "-i", str(video_path), "-i", str(audio_path), "-c:v", "copy", "-c:a", "aac", "-shortest", str(out_path)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def build_output_dir(args, text: str) -> Path:
    if args.output_dir:
        path = Path(args.output_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    slug = args.slug or slugify(text[:40])
    folder = OUTPUT_ROOT / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{slug}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def main():
    args = parse_args()
    raw_text = load_text(args)
    output_dir = build_output_dir(args, raw_text)
    html_dir = output_dir / "html"
    png_dir = output_dir / "png"
    clips_dir = output_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    total_steps = 7
    raw_path = output_dir / "source.txt"
    raw_path.write_text(raw_text, encoding="utf-8")

    polished = build_polished_text(raw_text)
    polished_path = output_dir / "polished_script.txt"
    polished_path.write_text(polished, encoding="utf-8")
    progress("口播文案润色完成", 1, total_steps)

    if args.reuse_project_file and args.reuse_audio_file:
        reused_project = json.loads(Path(args.reuse_project_file).read_text(encoding="utf-8"))
        tts_sections = reused_project["segments"]
    else:
        tts_sections = smooth_emotions(build_tts_sections(polished))
    segments_md = output_dir / "polished_segments.md"
    save_segments_markdown(tts_sections, segments_md)

    audio_path = output_dir / "lei_audio.wav"
    tts_project_path = output_dir / "tts_project.json"
    if args.reuse_project_file and args.reuse_audio_file:
        shutil.copy2(args.reuse_project_file, tts_project_path)
    else:
        build_tts_project(tts_sections, tts_project_path, audio_path)
    progress("TTS 项目生成完成", 2, total_steps)

    if args.reuse_project_file and args.reuse_audio_file:
        shutil.copy2(args.reuse_audio_file, audio_path)
        segment_wavs = None
    else:
        run_tts(tts_project_path, keep_segments=True)
        segment_wavs = segment_audio_paths(audio_path, len(tts_sections))
    progress("长语音合成完成", 3, total_steps)

    storyboard_path = output_dir / "storyboard.json"
    storyboard = build_storyboard(tts_sections, segment_wavs, audio_path, storyboard_path, args.min_scene_seconds, args.max_scene_seconds, args.target_scene_seconds)
    outline_json_path, outline_md_path = write_outline_files(storyboard, output_dir)
    storyboard_path.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")
    progress("视频分镜生成完成", 4, total_steps)

    pages = render_pages_from_outline(outline_json_path, html_dir, png_dir)
    pages_manifest_path = output_dir / "pages_manifest.json"
    pages_manifest_path.write_text(json.dumps({"pages": pages}, ensure_ascii=False, indent=2), encoding="utf-8")
    progress("HTML/PPT 画面渲染完成", 5, total_steps)

    clip_paths = []
    for page in pages:
        clip_path = clips_dir / f"{page['page_id']}.mp4"
        make_clip_from_png(Path(page["png_path"]), page["duration"], clip_path)
        clip_paths.append(clip_path)

    silent_video = output_dir / "video_silent.mp4"
    concat_video_clips(clip_paths, silent_video)

    audio_fx = output_dir / "lei_audio_with_sfx.wav"
    boundaries = []
    elapsed = 0.0
    for scene in storyboard["scenes"][:-1]:
        elapsed += scene["duration"]
        boundaries.append(elapsed)
    overlay_transition_sfx(audio_path, audio_fx, boundaries)
    progress("视频拼接与转场音效完成", 6, total_steps)

    final_video = output_dir / "final_video.mp4"
    mux_video_audio(silent_video, audio_fx, final_video)
    progress("最终视频完成", 7, total_steps)

    if segment_wavs and not args.keep_tts_segments:
        for wav_path in segment_wavs:
            if wav_path.exists():
                wav_path.unlink()

    summary = {
        "output_dir": str(output_dir),
        "raw_text": str(raw_path),
        "polished_script": str(polished_path),
        "segments_markdown": str(segments_md),
        "tts_project": str(tts_project_path),
        "audio": str(audio_path),
        "audio_with_sfx": str(audio_fx),
        "storyboard": str(storyboard_path),
        "html_outline_json": str(outline_json_path),
        "html_outline_md": str(outline_md_path),
        "pages_manifest": str(pages_manifest_path),
        "final_video": str(final_video),
        "scene_count": len(storyboard["scenes"]),
        "audio_seconds": storyboard["total_audio_seconds"],
    }
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
