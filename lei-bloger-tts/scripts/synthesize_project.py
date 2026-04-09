import argparse
import importlib.util
import json
import os
import subprocess
import sys
from typing import Dict, List


SCRIPT_DIR = os.path.dirname(__file__)
SYNTHESIZE_SCRIPT = os.path.join(SCRIPT_DIR, "synthesize.py")


def load_synthesize_module():
    spec = importlib.util.spec_from_file_location("lei_synthesize", SYNTHESIZE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def render_progress(current: int, total: int, width: int = 24) -> str:
    filled = int(width * current / total) if total else width
    return "[" + "#" * filled + "-" * (width - filled) + "]"


def build_segment_command(segment: Dict, output_path: str, project: Dict) -> List[str]:
    cmd = [
        sys.executable,
        SYNTHESIZE_SCRIPT,
        "--text",
        segment["text"],
        "--output",
        output_path,
    ]

    if project.get("config_file"):
        cmd.extend(["--config-file", project["config_file"]])
    if project.get("profile"):
        cmd.extend(["--profile", project["profile"]])
    if project.get("fp16"):
        cmd.append("--fp16")
    if project.get("verbose"):
        cmd.append("--verbose")

    emotion = segment.get("emotion", {})
    if emotion.get("emotion_mode"):
        cmd.extend(["--emotion-mode", emotion["emotion_mode"]])
    if emotion.get("emo_alpha") is not None:
        cmd.extend(["--emo-alpha", str(emotion["emo_alpha"])])
    if emotion.get("emo_reference"):
        cmd.extend(["--emo-reference", emotion["emo_reference"]])
    if emotion.get("emo_text"):
        cmd.extend(["--emo-text", emotion["emo_text"]])
    if emotion.get("emo_vector") is not None:
        cmd.extend(["--emo-vector", ",".join(str(item) for item in emotion["emo_vector"])])
    if emotion.get("use_random"):
        cmd.append("--use-random")
    return cmd


def main():
    parser = argparse.ArgumentParser(description="Generate a multi-segment Lei TTS project.")
    parser.add_argument("--project-file", required=True, help="Path to project json.")
    parser.add_argument("--output", default=None, help="Optional final output wav path.")
    parser.add_argument("--keep-segments", action="store_true", help="Keep per-segment wav files.")
    args = parser.parse_args()

    with open(args.project_file, "r", encoding="utf-8") as file:
        project = json.load(file)

    segments = project.get("segments", [])
    if not segments:
        raise ValueError("项目里没有 segments。")

    synth = load_synthesize_module()
    output_path = args.output or project.get("output_path")
    if not output_path:
        raise ValueError("缺少输出路径，请在 project 里提供 output_path 或命令行传 --output。")

    output_root, output_ext = os.path.splitext(output_path)
    output_ext = output_ext or ".wav"
    segment_paths = []

    total = len(segments)
    print(f"[lei-reference-tts-project] total segments: {total}", flush=True)
    for index, segment in enumerate(segments, start=1):
        segment_path = f"{output_root}.seg{index:02d}{output_ext}"
        bar = render_progress(index - 1, total)
        title = segment.get("title", f"segment-{index}")
        print(
            f"[lei-reference-tts-project] {bar} {index - 1}/{total} | start {title}",
            flush=True,
        )
        cmd = build_segment_command(segment, segment_path, project)
        subprocess.run(cmd, check=True, text=True)
        segment_paths.append(segment_path)
        bar = render_progress(index, total)
        print(
            f"[lei-reference-tts-project] {bar} {index}/{total} | done {title}",
            flush=True,
        )

    print("[lei-reference-tts-project] merging segments...", flush=True)
    synth.concat_wavs(segment_paths, output_path)
    print(f"[lei-reference-tts-project] merged output: {output_path}", flush=True)

    if not args.keep_segments and not project.get("keep_segments", False):
        for segment_path in segment_paths:
            if os.path.exists(segment_path):
                os.remove(segment_path)

    print(output_path)


if __name__ == "__main__":
    raise SystemExit(main())
