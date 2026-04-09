from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple


DEFAULT_CONFIG_FILE = "/Users/zhangleiandhim/.codex/skills/lei-reference-tts/emotion_config.json"
DEFAULT_OUTPUT_DIR = "/Users/zhangleiandhim/Documents/index-tts2/outputs/lei"


def parse_args():
    parser = argparse.ArgumentParser(description="Scaffold a long-form Lei TTS project JSON from polished segments text.")
    parser.add_argument("--input", required=True, help="Path to polished segments txt or md.")
    parser.add_argument("--output", default=None, help="Path to output project json.")
    parser.add_argument("--final-audio", default=None, help="Path to final merged wav.")
    parser.add_argument("--config-file", default=DEFAULT_CONFIG_FILE, help="Emotion config file path.")
    parser.add_argument("--profile", default="lively_excited", help="Default emotion profile.")
    return parser.parse_args()


def normalize_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    chunks: List[str] = []
    for line in lines:
        if not line:
            continue
        chunks.append(line)
    merged = " ".join(chunks)
    merged = re.sub(r"\s+", " ", merged).strip()
    return merged


def parse_sections(content: str) -> List[Tuple[str, str]]:
    lines = content.splitlines()
    sections: List[Tuple[str, List[str]]] = []
    current_title = None
    current_lines: List[str] = []

    def flush():
        nonlocal current_title, current_lines
        if current_title and current_lines:
            sections.append((current_title, current_lines[:]))
        current_title = None
        current_lines = []

    for raw in lines:
        line = raw.strip()
        if not line:
            if current_title:
                current_lines.append("")
            continue

        heading = re.match(r"^(?:##\s+)?(?:\d{1,2}\s*[｜|.-]\s*)?(.+)$", line)
        is_heading = False
        if raw.lstrip().startswith("## "):
            is_heading = True
        elif re.match(r"^\d{1,2}\s*[｜|.-]\s*.+$", line):
            is_heading = True

        if is_heading and heading:
            flush()
            current_title = heading.group(1).strip()
            continue

        if current_title is None:
            current_title = f"segment-{len(sections) + 1}"
        current_lines.append(line)

    flush()
    return [(title, normalize_text("\n".join(body))) for title, body in sections if normalize_text("\n".join(body))]


def clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def smooth(prev: Dict, current: Dict) -> Dict:
    if not prev:
        return current
    alpha = round(prev["emo_alpha"] * 0.35 + current["emo_alpha"] * 0.65, 2)
    vector = []
    for prev_item, curr_item in zip(prev["emo_vector"], current["emo_vector"]):
        vector.append(round(prev_item * 0.35 + curr_item * 0.65, 4))
    return {
        "emotion_mode": "vector",
        "emo_alpha": alpha,
        "emo_vector": vector,
    }


def infer_emotion(title: str, text: str) -> Dict:
    lower = f"{title} {text}"

    if re.search(r"开场|分类|总判断|引入", lower):
        return {
            "emotion_mode": "vector",
            "emo_alpha": 0.58,
            "emo_vector": [0.40, 0.0, 0.0, 0.0, 0.0, 0.0, 0.08, 0.16],
        }
    if re.search(r"吸引|龙虾|生命力|上头|成长", lower):
        return {
            "emotion_mode": "vector",
            "emo_alpha": 0.66,
            "emo_vector": [0.50, 0.0, 0.0, 0.0, 0.0, 0.0, 0.12, 0.12],
        }
    if re.search(r"问题|风险|门槛|安全|隐私|没流行|困难|复杂|报错", lower):
        return {
            "emotion_mode": "vector",
            "emo_alpha": 0.55,
            "emo_vector": [0.10, 0.08, 0.06, 0.02, 0.02, 0.04, 0.04, 0.16],
        }
    if re.search(r"机会|优势|流量|普及|预测|收束|总结|判断|本土|云端", lower):
        return {
            "emotion_mode": "vector",
            "emo_alpha": 0.60,
            "emo_vector": [0.42, 0.0, 0.0, 0.0, 0.0, 0.0, 0.10, 0.15],
        }
    if re.search(r"联网|想象|未来|操作系统|集群", lower):
        return {
            "emotion_mode": "vector",
            "emo_alpha": 0.58,
            "emo_vector": [0.30, 0.0, 0.02, 0.02, 0.0, 0.02, 0.15, 0.11],
        }
    return {
        "emotion_mode": "vector",
        "emo_alpha": 0.57,
        "emo_vector": [0.36, 0.0, 0.0, 0.0, 0.0, 0.0, 0.08, 0.18],
    }


def enforce_continuity(previous: Dict, current: Dict) -> Dict:
    smoothed = smooth(previous, current)
    if previous:
        delta = smoothed["emo_alpha"] - previous["emo_alpha"]
        smoothed["emo_alpha"] = round(previous["emo_alpha"] + clip(delta, -0.10, 0.10), 2)
    return smoothed


def build_project(sections: List[Tuple[str, str]], args) -> Dict:
    segments = []
    previous_emotion = None
    for title, text in sections:
        emotion = enforce_continuity(previous_emotion, infer_emotion(title, text))
        segments.append(
            {
                "title": title,
                "text": text,
                "emotion": emotion,
            }
        )
        previous_emotion = emotion

    input_path = Path(args.input)
    stem = input_path.stem
    final_audio = args.final_audio or os.path.join(DEFAULT_OUTPUT_DIR, f"{stem}_full.wav")
    return {
        "title": f"{stem} oral project",
        "config_file": args.config_file,
        "profile": args.profile,
        "output_path": final_audio,
        "keep_segments": False,
        "segments": segments,
    }


def main():
    args = parse_args()
    content = Path(args.input).read_text(encoding="utf-8")
    sections = parse_sections(content)
    if not sections:
        raise ValueError("没有解析出分段，请使用 `## 标题` 或 `01｜标题` 形式。")

    output = args.output or os.path.join(DEFAULT_OUTPUT_DIR, f"{Path(args.input).stem}_project.json")
    project = build_project(sections, args)
    Path(output).write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
