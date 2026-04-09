import argparse
import json
import os
import re
import subprocess
import wave
from datetime import datetime
from typing import List, Optional


REPO_DIR = "/Users/zhangleiandhim/Documents/index-tts2"
PYTHON_BIN = os.path.join(REPO_DIR, "venv", "bin", "python")
ENTRY_SCRIPT = os.path.join(REPO_DIR, "tools", "reference_tts.py")
REFERENCE_AUDIO = "/Users/zhangleiandhim/Documents/audio record from Xunfei/1773672171371/1773672171371.wav"
OUTPUT_DIR = os.path.join(REPO_DIR, "outputs", "lei")
DEFAULT_CONFIG_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "emotion_config.json")
)
EMOTION_VECTOR_LABELS = ["高兴", "愤怒", "悲伤", "害怕", "厌恶", "忧郁", "惊讶", "平静"]


def slugify_text(text: str) -> str:
    normalized = re.sub(r"\s+", "-", text.strip())
    normalized = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff_-]", "", normalized)
    normalized = normalized[:24].strip("-_")
    return normalized or "lei-tts"


def build_output_path(text: str, output: Optional[str]) -> str:
    if output:
        return output
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = slugify_text(text)
    return os.path.join(OUTPUT_DIR, f"{timestamp}_{stem}.wav")


def split_long_text(text: str, max_chars_per_chunk: int) -> List[str]:
    normalized = re.sub(r"\r\n?", "\n", text).strip()
    if not normalized:
        return []

    paragraphs = [part.strip() for part in re.split(r"\n{2,}", normalized) if part.strip()]
    if not paragraphs:
        paragraphs = [normalized]

    chunks: List[str] = []
    for paragraph in paragraphs:
        if len(paragraph) <= max_chars_per_chunk:
            chunks.append(paragraph)
            continue

        sentences = [
            piece.strip()
            for piece in re.split(r"(?<=[。！？!?；;：:\n])", paragraph)
            if piece.strip()
        ]
        if not sentences:
            sentences = [paragraph]

        current = ""
        for sentence in sentences:
            if not current:
                current = sentence
                continue
            if len(current) + len(sentence) <= max_chars_per_chunk:
                current += sentence
            else:
                chunks.append(current.strip())
                current = sentence
        if current:
            chunks.append(current.strip())

    final_chunks: List[str] = []
    for chunk in chunks:
        if len(chunk) <= max_chars_per_chunk:
            final_chunks.append(chunk)
            continue
        start = 0
        while start < len(chunk):
            final_chunks.append(chunk[start:start + max_chars_per_chunk].strip())
            start += max_chars_per_chunk
    return [chunk for chunk in final_chunks if chunk]


def concat_wavs(input_paths: List[str], output_path: str) -> None:
    if not input_paths:
        raise ValueError("没有可拼接的音频片段。")

    with wave.open(input_paths[0], "rb") as first_wav:
        params = first_wav.getparams()
        frames = [first_wav.readframes(first_wav.getnframes())]
    base_signature = (
        params.nchannels,
        params.sampwidth,
        params.framerate,
        params.comptype,
        params.compname,
    )

    for wav_path in input_paths[1:]:
        with wave.open(wav_path, "rb") as wav_file:
            signature = (
                wav_file.getnchannels(),
                wav_file.getsampwidth(),
                wav_file.getframerate(),
                wav_file.getcomptype(),
                wav_file.getcompname(),
            )
            if signature != base_signature:
                raise ValueError(f"WAV 参数不一致，无法拼接: {wav_path}")
            frames.append(wav_file.readframes(wav_file.getnframes()))

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with wave.open(output_path, "wb") as merged_wav:
        merged_wav.setparams(params)
        for frame in frames:
            merged_wav.writeframes(frame)


def build_base_command(text: str, output_path: str, emotion: dict, args) -> List[str]:
    cmd = [
        PYTHON_BIN,
        ENTRY_SCRIPT,
        "--reference",
        REFERENCE_AUDIO,
        "--text",
        text,
        "--output",
        output_path,
    ]
    if emotion["emo_reference"]:
        cmd.extend(["--emo-reference", emotion["emo_reference"]])
    cmd.extend(["--emo-alpha", str(emotion["emo_alpha"])])
    if emotion["emo_vector"] is not None:
        cmd.extend(["--emo-vector", ",".join(str(item) for item in emotion["emo_vector"])])
    if emotion["use_emo_text"]:
        cmd.append("--use-emo-text")
        if emotion["emo_text"]:
            cmd.extend(["--emo-text", emotion["emo_text"]])
    if emotion["use_random"]:
        cmd.append("--use-random")
    if args.fp16:
        cmd.append("--fp16")
    if args.verbose:
        cmd.append("--verbose")
    return cmd


def synthesize_single(text: str, output_path: str, emotion: dict, args, env: dict) -> None:
    cmd = build_base_command(text, output_path, emotion, args)
    subprocess.run(
        cmd,
        cwd=REPO_DIR,
        env=env,
        check=True,
        text=True,
    )


def load_skill_config(config_path: str) -> dict:
    if not os.path.isfile(config_path):
        return {}
    with open(config_path, "r", encoding="utf-8") as file:
        return json.load(file)


def parse_emo_vector(value):
    if value is None:
        return None
    if isinstance(value, list):
        vector = [float(item) for item in value]
    else:
        parts = [item.strip() for item in str(value).split(",") if item.strip()]
        vector = [float(item) for item in parts]
    if len(vector) != 8:
        raise ValueError(
            "情绪向量必须正好包含 8 个值，顺序为："
            + "、".join(EMOTION_VECTOR_LABELS)
        )
    return vector


def resolve_emotion_settings(args) -> dict:
    skill_config = load_skill_config(args.config_file)
    profiles = skill_config.get("profiles", {})
    profile_name = args.profile or skill_config.get("default_profile")
    profile = profiles.get(profile_name, {}) if profile_name else {}

    emotion_mode = args.emotion_mode or profile.get("emotion_mode") or "reference"
    emo_reference = args.emo_reference if args.emo_reference is not None else profile.get("emo_reference")
    emo_alpha = args.emo_alpha if args.emo_alpha is not None else profile.get("emo_alpha", 1.0)
    emo_text = args.emo_text if args.emo_text is not None else profile.get("emo_text")
    emo_vector_raw = args.emo_vector if args.emo_vector is not None else profile.get("emo_vector")
    emo_vector = parse_emo_vector(emo_vector_raw) if emo_vector_raw is not None else None
    use_random = args.use_random if args.use_random is not None else bool(profile.get("use_random", False))

    if emotion_mode == "reference":
        return {
            "profile_name": profile_name,
            "emotion_mode": emotion_mode,
            "emo_reference": emo_reference,
            "emo_alpha": float(emo_alpha),
            "emo_text": None,
            "emo_vector": None,
            "use_emo_text": False,
            "use_random": False,
        }

    if emotion_mode == "vector":
        if emo_vector is None:
            raise ValueError("当前情绪模式为 vector，但没有提供 `emo_vector`。")
        return {
            "profile_name": profile_name,
            "emotion_mode": emotion_mode,
            "emo_reference": None,
            "emo_alpha": float(emo_alpha),
            "emo_text": None,
            "emo_vector": emo_vector,
            "use_emo_text": False,
            "use_random": bool(use_random),
        }

    if emotion_mode == "text":
        return {
            "profile_name": profile_name,
            "emotion_mode": emotion_mode,
            "emo_reference": None,
            "emo_alpha": float(emo_alpha),
            "emo_text": emo_text,
            "emo_vector": None,
            "use_emo_text": True,
            "use_random": bool(use_random),
        }

    raise ValueError(f"不支持的 emotion_mode: {emotion_mode}")


def main():
    parser = argparse.ArgumentParser(description="Generate speech in Lei's voice.")
    parser.add_argument("--text", required=True, help="Text to synthesize.")
    parser.add_argument("--output", default=None, help="Optional output wav path.")
    parser.add_argument("--config-file", default=DEFAULT_CONFIG_PATH, help="Emotion config JSON path.")
    parser.add_argument("--profile", default=None, help="Emotion profile name from config file.")
    parser.add_argument("--emotion-mode", choices=["reference", "vector", "text"], default=None, help="Override emotion mode.")
    parser.add_argument("--emo-reference", default=None, help="Optional emotion reference wav.")
    parser.add_argument("--emo-alpha", type=float, default=None, help="Emotion blend weight.")
    parser.add_argument("--emo-text", default=None, help="Emotion description text for text mode.")
    parser.add_argument("--emo-vector", default=None, help="Comma-separated 8D emotion vector.")
    parser.add_argument("--use-random", action="store_true", default=None, help="Enable random emotion sampling in vector/text mode.")
    parser.add_argument("--max-chars-per-chunk", type=int, default=180, help="Long-text chunk size in characters.")
    parser.add_argument("--keep-segments", action="store_true", help="Keep intermediate chunk wav files.")
    parser.add_argument("--fp16", action="store_true", help="Enable fp16 when supported.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose inference logs.")
    args = parser.parse_args()

    if not os.path.isfile(PYTHON_BIN):
        raise FileNotFoundError(f"Python runtime not found: {PYTHON_BIN}")
    if not os.path.isfile(ENTRY_SCRIPT):
        raise FileNotFoundError(f"Entry script not found: {ENTRY_SCRIPT}")
    if not os.path.isfile(REFERENCE_AUDIO):
        raise FileNotFoundError(f"Lei reference audio not found: {REFERENCE_AUDIO}")

    output_path = build_output_path(args.text, args.output)
    emotion = resolve_emotion_settings(args)

    env = os.environ.copy()
    env["MPLCONFIGDIR"] = env.get("MPLCONFIGDIR", "/tmp/mpl")
    env["HF_HOME"] = os.path.join(REPO_DIR, "tmp_hf_home_by_modelscope")
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    env["PYTHONPATH"] = REPO_DIR
    env["PYTHONUNBUFFERED"] = "1"

    print(
        "[lei-reference-tts] emotion profile:",
        emotion["profile_name"] or "cli-only",
        "| mode:",
        emotion["emotion_mode"],
        "| alpha:",
        emotion["emo_alpha"],
        flush=True,
    )
    if emotion["emo_vector"] is not None:
        print("[lei-reference-tts] emotion vector:", emotion["emo_vector"], flush=True)
    if emotion["emo_text"]:
        print("[lei-reference-tts] emotion text:", emotion["emo_text"], flush=True)

    chunks = split_long_text(args.text, args.max_chars_per_chunk)
    if not chunks:
        raise ValueError("文本为空，无法生成音频。")

    print(f"[lei-reference-tts] text chunks: {len(chunks)}", flush=True)
    if len(chunks) == 1:
        synthesize_single(chunks[0], output_path, emotion, args, env)
        print(output_path)
        return 0

    output_root, output_ext = os.path.splitext(output_path)
    segment_paths = []
    for index, chunk_text in enumerate(chunks, start=1):
        segment_path = f"{output_root}.part{index:03d}{output_ext or '.wav'}"
        print(
            f"[lei-reference-tts] synthesize chunk {index}/{len(chunks)} -> {os.path.basename(segment_path)}",
            flush=True,
        )
        synthesize_single(chunk_text, segment_path, emotion, args, env)
        segment_paths.append(segment_path)

    concat_wavs(segment_paths, output_path)
    print(f"[lei-reference-tts] merged {len(segment_paths)} chunk wavs", flush=True)

    if not args.keep_segments:
        for segment_path in segment_paths:
            if os.path.exists(segment_path):
                os.remove(segment_path)

    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
