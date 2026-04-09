from __future__ import annotations

import argparse
import functools
import html
import json
import math
import os
import re
import shutil
import socketserver
import struct
import subprocess
import textwrap
import threading
import wave
from datetime import datetime
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from typing import Dict, List, Tuple

import imageio_ffmpeg
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
HOME = Path.home()
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
WIDTH = 1920
HEIGHT = 1080
FPS = 24
BRAND = "磊哥哥科技拆解室"
LEAD_IN_SECONDS = 0.55
DEFAULT_SOUND_CONFIG = {
    "preset": "cyber-brush",
    "intensity": 1.0,
    "brightness": 1.0,
    "tail": 1.0,
    "chirp": 1.0,
    "stereo": 1.0,
}


def resolve_skill_dir(name: str) -> Path:
    candidates = [
        HOME / ".codex" / "skills" / name,
        HOME / ".agents" / "skills" / name,
        ROOT.parent / name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"未找到技能目录：{name}")


TTS_SKILL = resolve_skill_dir("lei-bloger-tts")
TTS_SYNTH_PROJECT = TTS_SKILL / "scripts" / "synthesize_project.py"
try:
    GEMINI_SKILL = resolve_skill_dir("gemini-image-gen")
except FileNotFoundError:
    GEMINI_SKILL = None
GEMINI_CONFIG = GEMINI_SKILL / "config.json" if GEMINI_SKILL else None
GEMINI_GENERATE = GEMINI_SKILL / "scripts" / "generate.py" if GEMINI_SKILL else None
OUTPUT_ROOT = Path("/Users/zhangleiandhim/Documents/index-tts2/outputs/lei_web_ppt_av")


def progress(label: str, index: int, total: int) -> None:
    filled = int(index / total * 24) if total else 24
    print(
        f"[lei-bloger-web-ppt-av] [{'#' * filled}{'-' * (24 - filled)}] {index}/{total} | {label}",
        flush=True,
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate Lei blogger audio + Swiss-style web PPT + synced video."
    )
    parser.add_argument("--text", default=None, help="Raw input text.")
    parser.add_argument("--input-file", default=None, help="Path to input txt/md file.")
    parser.add_argument("--output-dir", default=None, help="Optional output directory.")
    parser.add_argument("--slug", default=None, help="Optional output folder slug.")
    parser.add_argument(
        "--reuse-project-file",
        default=None,
        help="Reuse an existing Lei TTS project json instead of regenerating it.",
    )
    parser.add_argument(
        "--reuse-audio-file",
        default=None,
        help="Reuse an existing merged wav instead of running TTS again.",
    )
    parser.add_argument(
        "--min-scene-seconds",
        type=float,
        default=5.0,
        help="Minimum scene / slide duration.",
    )
    parser.add_argument(
        "--max-scene-seconds",
        type=float,
        default=8.5,
        help="Maximum scene / slide duration.",
    )
    parser.add_argument(
        "--target-scene-seconds",
        type=float,
        default=6.6,
        help="Target scene / slide duration.",
    )
    parser.add_argument(
        "--keep-tts-segments",
        action="store_true",
        help="Keep intermediate per-segment wav files.",
    )
    parser.add_argument(
        "--tts-max-chars",
        type=int,
        default=1800,
        help="Approximate max chars per Lei TTS project segment for long-form generation.",
    )
    parser.add_argument(
        "--skip-tts",
        action="store_true",
        help="Debug mode: skip Lei TTS and synthesize a silent placeholder wav.",
    )
    parser.add_argument(
        "--open-deck",
        action="store_true",
        help="Open the generated web PPT after the pipeline finishes.",
    )
    parser.add_argument(
        "--image-mode",
        choices=["auto", "svg", "gemini"],
        default="auto",
        help="Slide image mode. `auto` tries Gemini first and falls back to SVG.",
    )
    return parser.parse_args()


def ffmpeg() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()


def slugify(text: str) -> str:
    value = re.sub(r"\s+", "-", text.strip())
    value = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff_-]", "", value)
    value = value[:48].strip("-_")
    return value or "lei-bloger-web-ppt-av"


def load_raw_text(args) -> str:
    if args.text:
        return args.text.strip()
    if args.input_file:
        return Path(args.input_file).read_text(encoding="utf-8").strip()
    raise ValueError("请提供 --text 或 --input-file。")


def shorten_text(text: str, limit: int) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    if len(clean) <= limit:
        return clean
    return clean[: max(0, limit - 1)].rstrip("，。；：、 ") + "…"


def extract_title_metadata(raw_text: str) -> Dict[str, str]:
    title = ""
    subtitle = ""
    body_source = raw_text

    inline_title = re.search(
        r"(?:标题|题目|title)(?:为)?\s*[：:]\s*(.+?)(?=(?:\s*(?:副标题|subtitle)(?:为)?\s*[：:])|[。！？\n\r]|$)",
        raw_text,
        re.IGNORECASE,
    )
    inline_subtitle = re.search(
        r"(?:副标题|subtitle)(?:为)?\s*[：:]\s*(.+?)(?=[。！？\n\r]|$)",
        raw_text,
        re.IGNORECASE,
    )
    if inline_title:
        title = inline_title.group(1).strip("，。； ")
        body_source = body_source.replace(inline_title.group(0), "", 1)
    if inline_subtitle:
        subtitle = inline_subtitle.group(1).strip("，。； ")
        body_source = body_source.replace(inline_subtitle.group(0), "", 1)

    cleaned_lines: List[str] = []

    for raw_line in body_source.splitlines():
        line = raw_line.strip()
        if not line:
            cleaned_lines.append("")
            continue

        title_match = re.match(r"^(?:标题|题目|title)(?:为)?\s*[：:]\s*(.+)$", line, re.IGNORECASE)
        subtitle_match = re.match(r"^(?:副标题|subtitle)(?:为)?\s*[：:]\s*(.+)$", line, re.IGNORECASE)
        if title_match and not title:
            title = title_match.group(1).strip("，。； ")
            continue
        if subtitle_match and not subtitle:
            subtitle = subtitle_match.group(1).strip("，。； ")
            continue
        if line.startswith("# ") and not title:
            title = line[2:].strip()
            continue
        if line.startswith("## ") and not subtitle:
            subtitle = line[3:].strip()
            continue
        cleaned_lines.append(raw_line.rstrip())

    body = "\n".join(cleaned_lines).strip()
    if not title:
        first = re.split(r"[。！？\n]", body, maxsplit=1)[0].strip()
        title = shorten_text(first or "Lei 口播网页 PPT 视频", 26)
    return {"title": title, "subtitle": subtitle, "body": body or raw_text.strip()}


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
    return re.sub(r"\s+", " ", text).strip()


def oral_polish_sentence(sentence: str) -> str:
    sentence = sentence.strip()
    if not sentence:
        return ""
    replacements = [
        ("首先说说", "首先说说，"),
        ("再说说", "再说说，"),
        ("最后聊聊", "最后聊聊，"),
        ("最后做个总结", "最后做个总结，"),
        ("说白了就是", "说白了就是，"),
        ("比如 ", "比如说，"),
        ("比如，", "比如说，"),
    ]
    for old, new in replacements:
        sentence = sentence.replace(old, new)
    for starter in ["其实", "不过", "当然", "所以", "另外", "同时", "那"]:
        if sentence.startswith(starter) and not sentence.startswith(f"{starter}，"):
            sentence = sentence.replace(starter, f"{starter}，", 1)
    sentence = re.sub(r"\s+", " ", sentence).strip()
    if sentence and sentence[-1] not in "。！？":
        sentence += "。"
    return normalize_punctuation(sentence)


def split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[。！？])\s*", normalize_punctuation(text))
    return [oral_polish_sentence(part) for part in parts if part.strip()]


def build_polished_text(text: str) -> str:
    return "\n".join(split_sentences(text))


def summarize_title(text: str, index: int) -> str:
    rules = [
        ("OpenClaw", "OpenClaw 判断"),
        ("多 Agent", "多 Agent 集群"),
        ("AI 操作系统", "AI OS 方向"),
        ("操作系统", "AI OS 方向"),
        ("流量", "流量入口"),
        ("Workbuddy", "本土产品趋势"),
        ("总结", "总结判断"),
        ("安全", "安全与门槛"),
    ]
    for keyword, title in rules:
        if keyword.lower() in text.lower():
            return f"{index:02d}｜{title}"
    first = re.sub(r"[。！？].*", "", text).strip()
    return f"{index:02d}｜{shorten_text(first or f'第{index}段', 18)}"


def build_tts_sections(polished_text: str, max_chars: int = 1800) -> List[Dict]:
    sentences = [line.strip() for line in polished_text.splitlines() if line.strip()]
    sections: List[Dict] = []
    current: List[str] = []
    count = 0
    for sentence in sentences:
        if current and count + len(sentence) > max_chars:
            merged = " ".join(current).strip()
            sections.append({"title": summarize_title(merged, len(sections) + 1), "text": merged})
            current = [sentence]
            count = len(sentence)
        else:
            current.append(sentence)
            count += len(sentence)
    if current:
        merged = " ".join(current).strip()
        sections.append({"title": summarize_title(merged, len(sections) + 1), "text": merged})
    return sections


def infer_emotion(title: str, text: str) -> Dict:
    lower = f"{title} {text}".lower()
    if re.search(r"开场|大家好|判断|分类|引入", lower):
        return {"emotion_mode": "vector", "emo_alpha": 0.62, "emo_vector": [0.44, 0.0, 0.0, 0.0, 0.0, 0.0, 0.12, 0.12]}
    if re.search(r"吸引|活过来|养龙虾|成长|临场感|陪伴感", lower):
        return {"emotion_mode": "vector", "emo_alpha": 0.72, "emo_vector": [0.58, 0.0, 0.0, 0.0, 0.0, 0.0, 0.18, 0.08]}
    if re.search(r"问题|安全|门槛|复杂|隐私|封杀|风险|难", lower):
        return {"emotion_mode": "vector", "emo_alpha": 0.58, "emo_vector": [0.12, 0.08, 0.03, 0.02, 0.01, 0.03, 0.06, 0.14]}
    if re.search(r"趋势|机会|普及|优势|推广|未来|预测|大厂", lower):
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
            current = {
                "emotion_mode": "vector",
                "emo_alpha": round(previous["emo_alpha"] * 0.4 + current["emo_alpha"] * 0.6, 2),
                "emo_vector": [
                    round(prev_item * 0.4 + curr_item * 0.6, 4)
                    for prev_item, curr_item in zip(previous["emo_vector"], current["emo_vector"])
                ],
            }
        result.append({**segment, "emotion": current})
        previous = current
    return result


def save_segments_markdown(segments: List[Dict], path: Path) -> None:
    lines: List[str] = []
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


def estimate_audio_seconds(text: str) -> float:
    punctuation_bonus = sum(text.count(mark) for mark in "，。！？；：、") * 0.16
    return max(2.6, len(text) / 4.6 + punctuation_bonus)


def write_silent_wav(path: Path, seconds: float, sample_rate: int = 24000) -> None:
    total_frames = max(1, int(seconds * sample_rate))
    silence = struct.pack("<" + "h" * total_frames, *([0] * total_frames))
    with wave.open(str(path), "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(sample_rate)
        writer.writeframes(silence)


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wav_file:
        return wav_file.getnframes() / wav_file.getframerate()


def segment_audio_paths(audio_path: Path, count: int) -> List[Path]:
    root, ext = os.path.splitext(str(audio_path))
    suffix = ext or ".wav"
    return [Path(f"{root}.seg{index:02d}{suffix}") for index in range(1, count + 1)]


def proportional_segment_durations(segments: List[Dict], total_audio_seconds: float) -> List[float]:
    total_chars = sum(max(len(segment["text"]), 1) for segment in segments) or 1
    durations = [
        total_audio_seconds * max(len(segment["text"]), 1) / total_chars
        for segment in segments
    ]
    if durations:
        durations[-1] += total_audio_seconds - sum(durations)
    return [round(duration, 2) for duration in durations]


def split_visual_units(text: str) -> List[str]:
    clauses = [part.strip() for part in re.split(r"(?<=[。；！？])\s*", text) if part.strip()]
    return clauses or [text]


def chunk_text_by_length(text: str, parts: int) -> List[str]:
    chars_total = len(text)
    if chars_total == 0:
        return [text]
    chunk_size = max(24, math.ceil(chars_total / max(parts, 1)))
    chunks = [text[index:index + chunk_size].strip() for index in range(0, chars_total, chunk_size)]
    return [chunk for chunk in chunks if chunk]


def group_clauses_to_scenes(
    clauses: List[str],
    total_seconds: float,
    min_s: float,
    max_s: float,
    target_s: float,
    depth: int = 0,
) -> List[Dict]:
    if total_seconds <= max_s or total_seconds < min_s * 2:
        return [{"text": " ".join(clauses).strip(), "duration": round(total_seconds, 2)}]

    full_chars = sum(max(len(item), 1) for item in clauses)
    if full_chars == 0:
        return [{"text": " ", "duration": round(total_seconds, 2)}]

    cps = full_chars / max(total_seconds, 0.001)
    target_chars = max(40, int(cps * target_s))
    groups: List[List[str]] = []
    current: List[str] = []
    chars = 0

    for clause in clauses:
        clause_length = len(clause)
        if current and chars + clause_length > target_chars:
            groups.append(current)
            current = [clause]
            chars = clause_length
        else:
            current.append(clause)
            chars += clause_length
    if current:
        groups.append(current)

    scenes = []
    for group in groups:
        text = " ".join(group).strip()
        proportion = sum(len(item) for item in group) / full_chars
        scenes.append({"text": text, "duration": proportion * total_seconds})

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
            sub_chunks = chunk_text_by_length(scene["text"], parts)
            duration_chunks = proportional_segment_durations(
                [{"text": chunk} for chunk in sub_chunks],
                scene["duration"],
            )
            for chunk, duration in zip(sub_chunks, duration_chunks):
                final_scenes.append({"text": chunk, "duration": duration})
            continue

        sentence_clauses = split_visual_units(scene["text"])
        if len(sentence_clauses) == 1 or sentence_clauses == [scene["text"]]:
            chunks = chunk_text_by_length(scene["text"], max(2, int(math.ceil(scene["duration"] / target_s))))
        else:
            chunks = sentence_clauses
        final_scenes.extend(group_clauses_to_scenes(chunks, scene["duration"], min_s, max_s, target_s, depth + 1))

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
        durations = proportional_segment_durations([{"text": chunk} for chunk in chunks], scene["duration"])
        for chunk, duration in zip(chunks, durations):
            bounded.append({"text": chunk, "duration": duration})

    drift = round(total_seconds - sum(scene["duration"] for scene in bounded), 2)
    if bounded:
        bounded[-1]["duration"] = round(bounded[-1]["duration"] + drift, 2)
    return bounded


def extract_brands(text: str) -> List[str]:
    candidates = [
        "OpenClaw",
        "Codex",
        "Claude Code",
        "Claude Work",
        "Workbuddy",
        "豆包",
        "微信",
        "飞书",
        "QQ",
        "腾讯",
        "阿里",
        "智谱",
        "Kimi",
        "DeepSeek",
        "Windows",
        "Mac",
        "安卓",
        "鸿蒙",
    ]
    lower = text.lower()
    hits = []
    for item in candidates:
        if item.lower() in lower and item not in hits:
            hits.append(item)
    return hits[:4]


def infer_template(text: str) -> str:
    lower = text.lower()
    if re.search(r"第一类|第二类|第三类|分成三类|分类", lower):
        return "compare"
    if re.search(r"openclaw|codex|claude|workbuddy|微信|飞书|qq|kimi|deepseek|windows|mac|豆包", lower):
        return "brand"
    if re.search(r"问题|复杂|安全|隐私|风险|坑|阻力|难", lower):
        return "issue"
    if re.search(r"趋势|未来|流量|操作系统|集群|机会|普及|推广|爆发", lower):
        return "trend"
    return "statement"


def scene_title(text: str, index: int) -> str:
    sentence = re.sub(r"[。！？].*", "", text).strip()
    return shorten_text(sentence or f"场景 {index}", 26)


def sentence_parts(text: str) -> List[str]:
    return [
        part.strip("，。；：！？ ")
        for part in re.split(r"[，。；：！？]", text)
        if part.strip("，。；：！？ ")
    ]


def scene_bullets(text: str) -> List[str]:
    bullets = []
    for part in sentence_parts(text):
        value = shorten_text(part, 26)
        if value and value not in bullets:
            bullets.append(value)
    return bullets[:4]


def build_takeaway(text: str) -> str:
    parts = sentence_parts(text)
    if not parts:
        return shorten_text(text, 28)
    if len(parts) >= 2:
        return shorten_text(f"{parts[0]}，{parts[1]}", 30)
    return shorten_text(parts[0], 30)


def build_storyboard(
    segments: List[Dict],
    segment_wavs: List[Path] | None,
    audio_path: Path,
    output_path: Path,
    min_s: float,
    max_s: float,
    target_s: float,
) -> Dict:
    if segment_wavs:
        segment_durations = [wav_duration(path) for path in segment_wavs]
        total_audio_seconds = round(sum(segment_durations), 2)
    else:
        total_audio_seconds = round(wav_duration(audio_path), 2)
        segment_durations = proportional_segment_durations(segments, total_audio_seconds)

    scenes = []
    start = 0.0
    scene_index = 1

    for segment, duration in zip(segments, segment_durations):
        groups = group_clauses_to_scenes(
            split_visual_units(segment["text"]),
            duration,
            min_s,
            max_s,
            target_s,
        )
        consumed = 0.0
        for group in groups:
            text = group["text"].strip()
            scenes.append(
                {
                    "id": f"s{scene_index:03d}",
                    "segment_title": segment["title"],
                    "title": scene_title(text, scene_index),
                    "text": text,
                    "template": infer_template(text),
                    "bullets": scene_bullets(text),
                    "brands": extract_brands(text),
                    "duration": round(group["duration"], 2),
                    "audio_start": round(start + consumed, 2),
                    "audio_duration": round(group["duration"], 2),
                }
            )
            consumed += group["duration"]
            scene_index += 1
        start += duration

    durations = [scene["duration"] for scene in scenes]
    for index, duration in enumerate(durations):
        if duration >= min_s:
            continue
        need = round(min_s - duration, 2)
        for other in range(index + 1, len(durations)):
            slack = round(durations[other] - min_s, 2)
            if slack <= 0:
                continue
            give = min(slack, need)
            durations[other] = round(durations[other] - give, 2)
            durations[index] = round(durations[index] + give, 2)
            need = round(need - give, 2)
            if need <= 0:
                break
        if need > 0:
            for other in range(index - 1, -1, -1):
                slack = round(durations[other] - min_s, 2)
                if slack <= 0:
                    continue
                give = min(slack, need)
                durations[other] = round(durations[other] - give, 2)
                durations[index] = round(durations[index] + give, 2)
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
        "total_audio_seconds": round(total_audio_seconds, 2),
        "scenes": scenes,
        "style": {
            "brand": BRAND,
            "width": WIDTH,
            "height": HEIGHT,
            "fps": FPS,
            "min_scene_seconds": min_s,
            "max_scene_seconds": max_s,
            "target_scene_seconds": target_s,
        },
    }
    output_path.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")
    return storyboard


def srt_time(value: float) -> str:
    milliseconds = max(0, int(round(value * 1000)))
    hours, rest = divmod(milliseconds, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    seconds, millis = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def write_captions_srt(storyboard: Dict, path: Path) -> None:
    lines: List[str] = []
    for index, scene in enumerate(storyboard["scenes"], start=1):
        start = scene["audio_start"]
        end = scene["audio_start"] + scene["duration"]
        lines.extend(
            [
                str(index),
                f"{srt_time(start)} --> {srt_time(end)}",
                scene["text"],
                "",
            ]
        )
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


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


def strip_svg_wrapper(svg: str) -> str:
    svg = re.sub(r"^<svg[^>]*>", "", svg)
    return re.sub(r"</svg>\s*$", "", svg)


def build_scene_svg(scene: Dict) -> str:
    inner = strip_svg_wrapper(icon_svg(scene["template"]))
    dots = []
    for index in range(12):
        x = 120 + index * 120
        y = 110 + ((index * 37) % 7) * 74
        size = 8 + (index % 3) * 4
        dots.append(
            f"<rect x='{x}' y='{y}' width='{size}' height='{size}' fill='rgba(207,31,54,0.12)'/>"
        )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900">
  <defs>
    <linearGradient id="bg" x1="0" x2="1" y1="0" y2="1">
      <stop offset="0%" stop-color="#fffdfb"/>
      <stop offset="100%" stop-color="#fff4f6"/>
    </linearGradient>
  </defs>
  <rect width="1600" height="900" fill="url(#bg)"/>
  <g opacity="0.9">{''.join(dots)}</g>
  <rect x="140" y="108" width="1320" height="684" rx="48" fill="#ffffff" stroke="rgba(207,31,54,0.10)" stroke-width="6"/>
  <rect x="140" y="108" width="1320" height="18" fill="#cf1f36"/>
  <rect x="220" y="740" width="420" height="18" rx="9" fill="rgba(207,31,54,0.12)"/>
  <rect x="220" y="776" width="560" height="18" rx="9" fill="rgba(17,17,17,0.08)"/>
  <g transform="translate(420 165) scale(1.65)">{inner}</g>
</svg>"""


def gemini_api_key_available() -> bool:
    if not GEMINI_CONFIG or not GEMINI_CONFIG.exists():
        return False
    try:
        config = json.loads(GEMINI_CONFIG.read_text(encoding="utf-8"))
    except Exception:
        config = {}
    if config.get("api_key"):
        return True
    key_env = config.get("api_key_env", "GEMINI_API_KEY")
    return bool(os.getenv(key_env))


def build_scene_image_prompt(scene: Dict) -> str:
    keywords = "、".join(scene.get("brands", [])[:3]) or "AI 智能体、桌面端 Agent、网页 PPT"
    bullets = "；".join(scene.get("bullets", [])[:3]) or scene["text"]
    return (
        "瑞士风格、红白主色、浅色背景、像素科技感、几何编辑插画、统一系列感、16:9 构图、"
        "高质感科技评论配图、干净留白、不要文字、不要 logo、不要水印。"
        f"主题：{scene['title']}。"
        f"关键词：{keywords}。"
        f"画面需要表达：{bullets}。"
        "用于中文科技博客网页 PPT 单页主插图。"
    )


def maybe_generate_gemini_image(scene: Dict, output_path: Path) -> bool:
    if not GEMINI_GENERATE or not GEMINI_GENERATE.exists() or not GEMINI_CONFIG or not GEMINI_CONFIG.exists():
        return False
    if not gemini_api_key_available() or shutil.which("uv") is None:
        return False
    cmd = [
        "uv",
        "run",
        str(GEMINI_GENERATE),
        "--config",
        str(GEMINI_CONFIG),
        "--prompt",
        build_scene_image_prompt(scene),
        "--aspect-ratio",
        "16:9",
        "--output",
        str(output_path),
    ]
    result = subprocess.run(cmd, text=True, capture_output=True)
    return result.returncode == 0 and output_path.exists()


def create_scene_visual(scene: Dict, index: int, images_dir: Path, image_mode: str) -> Path:
    png_path = images_dir / f"slide-{index:02d}.png"
    svg_path = images_dir / f"slide-{index:02d}.svg"
    if image_mode in {"auto", "gemini"} and maybe_generate_gemini_image(scene, png_path):
        return png_path
    svg_path.write_text(build_scene_svg(scene), encoding="utf-8")
    return svg_path


def build_keywords(scene: Dict) -> List[str]:
    chips: List[str] = []
    for brand in scene.get("brands", []):
        value = shorten_text(brand, 10)
        if value not in chips:
            chips.append(value)
    for bullet in scene.get("bullets", []):
        part = shorten_text(bullet, 10)
        if part and part not in chips:
            chips.append(part)
    defaults = {
        "compare": ["三类形态", "差异判断", "使用门槛"],
        "brand": ["产品样本", "入口变化", "替代路径"],
        "issue": ["安装门槛", "配置复杂", "安全风险"],
        "trend": ["趋势判断", "商业机会", "后续变化"],
        "statement": ["核心观点", "关键结论", "展开说明"],
    }
    for fallback in defaults.get(scene["template"], defaults["statement"]):
        if fallback not in chips:
            chips.append(fallback)
    return chips[:3]


def build_metric_items(scene: Dict) -> List[Dict]:
    type_map = {
        "compare": ("分类", "结构"),
        "brand": ("对象", "品牌"),
        "issue": ("重点", "门槛"),
        "trend": ("方向", "趋势"),
        "statement": ("核心", "判断"),
    }
    action_map = {
        "compare": "拆解",
        "brand": "替代",
        "issue": "卡点",
        "trend": "演进",
        "statement": "结论",
    }
    first_label, first_value = type_map.get(scene["template"], type_map["statement"])
    subject = scene["brands"][0] if scene["brands"] else shorten_text(build_takeaway(scene["text"]), 8)
    return [
        {"value": first_value, "label": first_label},
        {"value": shorten_text(subject, 8), "label": "对象"},
        {"value": action_map.get(scene["template"], "判断"), "label": "动作"},
    ]


def build_scene_copy(scene: Dict) -> Dict:
    eyebrow_map = {
        "compare": "结构拆解",
        "brand": "产品样本",
        "issue": "问题拆解",
        "trend": "趋势判断",
        "statement": "核心观点",
    }
    panel_map = {
        "compare": "把分类和差异讲清楚",
        "brand": "把产品与入口对应起来",
        "issue": "把门槛和阻力拆开看",
        "trend": "把趋势和机会往后推演",
        "statement": "把这一页的重点展开说明",
    }
    media_tag_map = {
        "compare": "结构图示",
        "brand": "产品关系图",
        "issue": "阻力图示",
        "trend": "趋势图示",
        "statement": "核心配图",
    }
    note_map = {
        "compare": "这张图用来辅助理解不同形态之间的差异和位置。",
        "brand": "这张图对应这一页提到的产品、品牌或入口关系。",
        "issue": "这张图对应这一页提到的门槛、风险和现实阻力。",
        "trend": "这张图对应这一页关于趋势、阶段和演进路径的判断。",
        "statement": "这张图对应这一页的核心论点和重点判断。",
    }
    bullets = scene["bullets"][:3]
    while len(bullets) < 3:
        bullets.append("这一页继续补充相关背景和判断。")
    return {
        "eyebrow": eyebrow_map.get(scene["template"], "核心观点"),
        "title": shorten_text(scene["title"], 28),
        "lead": shorten_text(build_takeaway(scene["text"]), 38),
        "bullets": bullets[:3],
        "chips": build_keywords(scene),
        "quote": shorten_text(scene["text"], 56),
        "stamp": scene["segment_title"].split("｜")[-1].strip(),
        "panel_title": panel_map.get(scene["template"], panel_map["statement"]),
        "side_copy": shorten_text(scene["text"], 72),
        "metrics": build_metric_items(scene),
        "media_tag": media_tag_map.get(scene["template"], media_tag_map["statement"]),
        "media_note": note_map.get(scene["template"], note_map["statement"]),
    }


def build_slide_html(scene: Dict, index: int, total: int, image_rel_path: str) -> str:
    copy = build_scene_copy(scene)
    metrics_html = "\n".join(
        f"""              <div class="metric-box">
                <div class="metric-value">{esc(item['value'])}</div>
                <div class="metric-label">{esc(item['label'])}</div>
              </div>"""
        for item in copy["metrics"]
    )
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{index:02d} / {total:02d} - {esc(copy['title'])}</title>
    <link rel="stylesheet" href="../assets/deck.css" />
  </head>
  <body data-mode="slide">
    <canvas class="particle-canvas"></canvas>
    <div class="noise"></div>
    <div class="cursor-follower"></div>
    <div class="stage-root">
      <header class="slide-top">
        <div class="brand-chip">{esc(BRAND)}</div>
        <div class="page-chip">{index:02d} / {total:02d}</div>
      </header>

      <main class="deck hero-grid">
        <section class="panel panel-strong hero-copy hover-card tilt-card reveal" style="--delay: 0.08s">
          <div class="copy-stack">
            <p class="eyebrow">{esc(copy['eyebrow'])}</p>
            <h1 class="slide-title slide-title--compact">{esc(copy['title'])}</h1>
            <p class="lead">{esc(copy['lead'])}</p>
          </div>

          <div class="list-stack">
            <ul class="bullet-list">
              <li class="bullet-item"><span class="dot"></span><span>{esc(copy['bullets'][0])}</span></li>
              <li class="bullet-item"><span class="dot"></span><span>{esc(copy['bullets'][1])}</span></li>
              <li class="bullet-item"><span class="dot"></span><span>{esc(copy['bullets'][2])}</span></li>
            </ul>

            <div class="chip-row">
              <span class="text-chip">{esc(copy['chips'][0])}</span>
              <span class="text-chip">{esc(copy['chips'][1])}</span>
              <span class="text-chip">{esc(copy['chips'][2])}</span>
            </div>

            <div class="quote-box">
              <p class="quote-text">“{esc(copy['quote'])}”</p>
            </div>
          </div>
        </section>

        <section class="panel hover-card reveal" style="--delay: 0.18s">
          <div class="content-stack">
            <div class="stamp">{esc(copy['stamp'])}</div>
            <h2 class="panel-title">{esc(copy['panel_title'])}</h2>
            <p class="card-copy">{esc(copy['side_copy'])}</p>

            <div class="metric-strip">
{metrics_html}
            </div>

            <div class="media-stack">
              <figure class="media-frame compact contain tilt-card hover-card">
                <img src="{esc(image_rel_path)}" alt="{esc(copy['title'])} 配图" />
                <div class="image-tint"></div>
                <div class="scan"></div>
              </figure>

              <div class="media-caption">
                <span class="media-tag">{esc(copy['media_tag'])}</span>
                <span class="media-note">{esc(copy['media_note'])}</span>
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
    <script src="../assets/deck.js"></script>
  </body>
</html>
"""


def render_index_template(values: Dict[str, str]) -> str:
    template = (ROOT / "assets/templates/index.template.html").read_text(encoding="utf-8")
    for key, value in values.items():
        template = template.replace(f"{{{{{key}}}}}", value)
    return template


def copy_base_assets(deck_dir: Path) -> None:
    assets_dir = deck_dir / "assets"
    images_dir = assets_dir / "images"
    slides_dir = deck_dir / "slides"
    assets_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)
    slides_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "assets/base/deck.css", assets_dir / "deck.css")
    shutil.copy2(ROOT / "assets/base/deck.js", assets_dir / "deck.js")
    (assets_dir / "deck-config.js").write_text(
        f"window.DECK_SOUND_CONFIG = {json.dumps(DEFAULT_SOUND_CONFIG, ensure_ascii=False, indent=2)};\n",
        encoding="utf-8",
    )


def build_iframes(scene_count: int) -> str:
    return "\n".join(
        f'        <iframe class="deck-slide" src="slides/slide-{index:02d}.html" title="第 {index} 页"></iframe>'
        for index in range(1, scene_count + 1)
    )


def build_web_ppt(
    output_dir: Path,
    title: str,
    subtitle: str,
    storyboard: Dict,
    image_mode: str,
) -> Tuple[Path, Path, Path]:
    deck_dir = output_dir / "web_ppt"
    copy_base_assets(deck_dir)

    slides_dir = deck_dir / "slides"
    images_dir = deck_dir / "assets/images"
    scenes = storyboard["scenes"]
    total = len(scenes)

    for index, scene in enumerate(scenes, start=1):
        image_path = create_scene_visual(scene, index, images_dir, image_mode)
        image_name = image_path.name
        slide_path = slides_dir / f"slide-{index:02d}.html"
        slide_html = build_slide_html(scene, index, total, f"../assets/images/{image_name}")
        slide_path.write_text(slide_html, encoding="utf-8")
        scene["slide_file"] = str(slide_path)
        scene["slide_src"] = f"slides/slide-{index:02d}.html"
        scene["image_file"] = str(image_path)

    document_title = title if not subtitle else f"{title}｜{subtitle}"
    index_html = render_index_template(
        {
            "DOCUMENT_TITLE": esc(document_title),
            "COVER_TITLE": esc(title),
            "START_LABEL": esc("开始播放"),
            "SLIDE_IFRAMES": build_iframes(total),
            "TOTAL_SLIDES": f"{total:02d}",
        }
    )
    index_path = deck_dir / "index.html"
    index_path.write_text(index_html, encoding="utf-8")

    manifest_path = output_dir / "slides_manifest.json"
    manifest_path.write_text(json.dumps({"slides": scenes}, ensure_ascii=False, indent=2), encoding="utf-8")
    return deck_dir, index_path, manifest_path


class QuietStaticHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        return


def start_static_server(root_dir: Path) -> Tuple[socketserver.TCPServer, str]:
    handler = functools.partial(QuietStaticHandler, directory=str(root_dir))
    server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    return server, f"http://127.0.0.1:{port}"


def stop_static_server(server: socketserver.TCPServer) -> None:
    server.shutdown()
    server.server_close()


def launch_browser(playwright):
    kwargs = {"headless": True}
    if CHROME.exists():
        kwargs["executable_path"] = str(CHROME)
    return playwright.chromium.launch(**kwargs)


def record_deck_playback(deck_dir: Path, storyboard: Dict, raw_video_path: Path) -> Path:
    recordings_dir = raw_video_path.parent / "recordings"
    recordings_dir.mkdir(parents=True, exist_ok=True)
    server, base_url = start_static_server(deck_dir)
    video_obj = None
    recorded_path = None
    try:
        with sync_playwright() as playwright:
            browser = launch_browser(playwright)
            context = browser.new_context(
                viewport={"width": WIDTH, "height": HEIGHT},
                device_scale_factor=1,
                record_video_dir=str(recordings_dir),
                record_video_size={"width": WIDTH, "height": HEIGHT},
            )
            page = context.new_page()
            video_obj = page.video
            page.goto(f"{base_url}/index.html", wait_until="load")
            page.wait_for_timeout(180)
            page.locator("[data-start]").click()
            page.wait_for_function("document.body.classList.contains('is-playing')")
            page.wait_for_timeout(int(LEAD_IN_SECONDS * 1000))
            page.locator("body").focus()
            total = len(storyboard["scenes"])
            for index, scene in enumerate(storyboard["scenes"], start=1):
                progress(f"录制网页 PPT 第 {index} 页", index, total)
                page.wait_for_timeout(max(1, int(scene["duration"] * 1000)))
                if index < total:
                    page.keyboard.press("ArrowRight")
            page.wait_for_timeout(260)
            page.close()
            context.close()
            if video_obj is not None:
                recorded_path = Path(video_obj.path())
            browser.close()
        if video_obj is None:
            raise RuntimeError("Playwright 未返回录制视频对象。")
        if recorded_path is None:
            raise RuntimeError("Playwright 未返回录制文件路径。")
        shutil.copy2(recorded_path, raw_video_path)
        return raw_video_path
    finally:
        stop_static_server(server)


def render_slide_previews(deck_dir: Path, scenes: List[Dict], png_dir: Path) -> List[Path]:
    png_dir.mkdir(parents=True, exist_ok=True)
    server, base_url = start_static_server(deck_dir)
    outputs: List[Path] = []
    try:
        with sync_playwright() as playwright:
            browser = launch_browser(playwright)
            page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT}, device_scale_factor=1)
            total = len(scenes)
            for index, scene in enumerate(scenes, start=1):
                png_path = png_dir / f"slide-{index:02d}.png"
                page.goto(f"{base_url}/{scene['slide_src']}", wait_until="load")
                page.wait_for_timeout(220)
                page.screenshot(path=str(png_path))
                outputs.append(png_path)
                progress(f"截图回退页 {index}", index, total)
            browser.close()
    finally:
        stop_static_server(server)
    return outputs


def trim_video(source_video: Path, out_path: Path, start_seconds: float, duration: float) -> None:
    subprocess.run(
        [
            ffmpeg(),
            "-y",
            "-ss",
            str(start_seconds),
            "-i",
            str(source_video),
            "-t",
            str(duration),
            "-vf",
            f"fps={FPS},scale={WIDTH}:{HEIGHT}",
            "-pix_fmt",
            "yuv420p",
            "-an",
            str(out_path),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


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


def fallback_video_from_previews(deck_dir: Path, storyboard: Dict, out_path: Path, clips_dir: Path) -> Path:
    png_dir = out_path.parent / "previews"
    png_paths = render_slide_previews(deck_dir, storyboard["scenes"], png_dir)
    clips_dir.mkdir(parents=True, exist_ok=True)
    clip_paths: List[Path] = []
    for index, (scene, png_path) in enumerate(zip(storyboard["scenes"], png_paths), start=1):
        clip_path = clips_dir / f"fallback-{index:02d}.mp4"
        make_clip_from_png(png_path, scene["duration"], clip_path)
        clip_paths.append(clip_path)
    concat_video_clips(clip_paths, out_path)
    return out_path


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

    def pseudo_noise(index: int) -> float:
        value = math.sin(index * 12.9898) * 43758.5453
        return (value - math.floor(value)) * 2.0 - 1.0

    effect = []
    for index in range(effect_count):
        t = index / framerate
        sweep = math.sin(2 * math.pi * (560 + 2000 * (t / effect_duration)) * t)
        click = math.sin(2 * math.pi * 1300 * t)
        noise = pseudo_noise(index) * 0.25
        env = (1 - t / effect_duration) ** 2
        sample = (sweep * 0.52 + click * 0.16 + noise * 0.18) * env
        effect.append(int(sample * 32767 * gain))

    for boundary in boundaries:
        start_frame = int(max(0, boundary - 0.03) * framerate)
        for index, fx in enumerate(effect):
            pos = start_frame + index
            if pos >= total_frames:
                break
            for channel in range(channels):
                pointer = pos * channels + channel
                mixed = samples[pointer] + fx
                samples[pointer] = max(-32768, min(32767, mixed))

    write_wav_pcm(target_audio, channels, sampwidth, framerate, samples)


def mux_video_audio(video_path: Path, audio_path: Path, out_path: Path) -> None:
    subprocess.run(
        [
            ffmpeg(),
            "-y",
            "-i",
            str(video_path),
            "-i",
            str(audio_path),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-shortest",
            str(out_path),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def build_output_dir(args, title: str) -> Path:
    if args.output_dir:
        path = Path(args.output_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    slug = args.slug or slugify(title)
    folder = OUTPUT_ROOT / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{slug}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def maybe_open_deck(index_path: Path) -> None:
    if shutil.which("open"):
        subprocess.Popen(["open", str(index_path)])


def main():
    args = parse_args()
    metadata = extract_title_metadata(load_raw_text(args))
    title = metadata["title"]
    subtitle = metadata["subtitle"]
    source_body = metadata["body"]
    output_dir = build_output_dir(args, title)

    total_steps = 8
    source_path = output_dir / "source.txt"
    source_path.write_text(source_body, encoding="utf-8")

    polished = build_polished_text(source_body)
    polished_path = output_dir / "polished_script.txt"
    polished_path.write_text(polished, encoding="utf-8")
    progress("口播文案润色完成", 1, total_steps)

    reused_project = None
    if args.reuse_project_file:
        reused_project = json.loads(Path(args.reuse_project_file).read_text(encoding="utf-8"))
        tts_sections = reused_project["segments"]
    else:
        tts_sections = smooth_emotions(build_tts_sections(polished, max_chars=args.tts_max_chars))

    segments_md = output_dir / "polished_segments.md"
    save_segments_markdown(tts_sections, segments_md)
    progress("口播分段完成", 2, total_steps)

    audio_path = output_dir / "lei_audio.wav"
    tts_project_path = output_dir / "tts_project.json"
    if reused_project:
        reused_project["output_path"] = str(audio_path)
        reused_project["keep_segments"] = True
        tts_project_path.write_text(json.dumps(reused_project, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        build_tts_project(tts_sections, tts_project_path, audio_path)

    if args.reuse_audio_file:
        shutil.copy2(args.reuse_audio_file, audio_path)
        segment_wavs = None
    elif args.skip_tts:
        total_seconds = sum(estimate_audio_seconds(segment["text"]) for segment in tts_sections)
        write_silent_wav(audio_path, total_seconds)
        segment_wavs = None
    else:
        run_tts(tts_project_path, keep_segments=True)
        segment_wavs = segment_audio_paths(audio_path, len(tts_sections))
    progress("音频准备完成", 3, total_steps)

    storyboard_path = output_dir / "storyboard.json"
    storyboard = build_storyboard(
        tts_sections,
        segment_wavs,
        audio_path,
        storyboard_path,
        args.min_scene_seconds,
        args.max_scene_seconds,
        args.target_scene_seconds,
    )
    captions_path = output_dir / "captions.srt"
    write_captions_srt(storyboard, captions_path)
    progress("分镜与时间线完成", 4, total_steps)

    deck_dir, index_path, slides_manifest_path = build_web_ppt(
        output_dir,
        title,
        subtitle,
        storyboard,
        args.image_mode,
    )
    progress("网页 PPT 生成完成", 5, total_steps)

    raw_video = output_dir / "deck_recording.webm"
    silent_video = output_dir / "deck_playback.mp4"
    fallback_video = output_dir / "deck_playback_fallback.mp4"
    clips_dir = output_dir / "clips"
    video_mode = "recorded_deck"
    try:
        record_deck_playback(deck_dir, storyboard, raw_video)
        trim_video(raw_video, silent_video, LEAD_IN_SECONDS, storyboard["total_audio_seconds"])
    except Exception as error:
        print(f"[lei-bloger-web-ppt-av] deck recording fallback: {error}", flush=True)
        fallback_video_from_previews(deck_dir, storyboard, fallback_video, clips_dir)
        silent_video = fallback_video
        video_mode = "fallback_stills"
    progress("PPT 回放视频生成完成", 6, total_steps)

    boundaries = []
    elapsed = 0.0
    for scene in storyboard["scenes"][:-1]:
        elapsed += scene["duration"]
        boundaries.append(elapsed)

    audio_fx = output_dir / "lei_audio_with_sfx.wav"
    overlay_transition_sfx(audio_path, audio_fx, boundaries)
    progress("翻页音效叠加完成", 7, total_steps)

    final_video = output_dir / "final_video.mp4"
    mux_video_audio(silent_video, audio_fx, final_video)
    progress("最终视频完成", 8, total_steps)

    if segment_wavs and not args.keep_tts_segments:
        for wav_path in segment_wavs:
            if wav_path.exists():
                wav_path.unlink()

    if args.open_deck:
        maybe_open_deck(index_path)

    summary = {
        "output_dir": str(output_dir),
        "title": title,
        "subtitle": subtitle,
        "source_text": str(source_path),
        "polished_script": str(polished_path),
        "segments_markdown": str(segments_md),
        "tts_project": str(tts_project_path),
        "tts_max_chars": args.tts_max_chars,
        "audio": str(audio_path),
        "audio_with_sfx": str(audio_fx),
        "storyboard": str(storyboard_path),
        "captions_srt": str(captions_path),
        "deck_dir": str(deck_dir),
        "deck_index": str(index_path),
        "slides_manifest": str(slides_manifest_path),
        "image_mode": args.image_mode,
        "video_mode": video_mode,
        "silent_video": str(silent_video),
        "final_video": str(final_video),
        "scene_count": len(storyboard["scenes"]),
        "audio_seconds": storyboard["total_audio_seconds"],
    }
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
