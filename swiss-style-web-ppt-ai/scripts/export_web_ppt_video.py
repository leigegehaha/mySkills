from __future__ import annotations

import argparse
import difflib
import functools
import html
import json
import math
import re
import shutil
import socketserver
import subprocess
import threading
import wave
from collections import Counter
from http.server import SimpleHTTPRequestHandler
from pathlib import Path

import numpy as np
from playwright.sync_api import sync_playwright


WIDTH = 1920
HEIGHT = 1080
SAMPLE_RATE = 48_000
DEFAULT_LEAD_IN = 0.55
ASCII_PHRASE_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9+./-]*(?: [A-Za-z0-9][A-Za-z0-9+./-]*)*")
OPEN_PUNCT = set("（【《「『“‘")
CLOSE_PUNCT = set("，。！？；：、,.!?;:）】》」』”’")
HTML_BREAK_TAGS = ("</h1>", "</h2>", "</h3>", "</h4>", "</p>", "</li>", "</div>", "</section>", "</article>", "<br", "</tr>")


class QuietStaticHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        return


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export an iframe-based web PPT to a synchronized video with subtitles.")
    parser.add_argument("--project", required=True, help="Web PPT project directory containing index.html and slide HTML files.")
    parser.add_argument("--audio", required=True, help="Narration audio file path.")
    parser.add_argument("--index-file", help="Optional index HTML path. Defaults to project/index.html when present.")
    parser.add_argument("--output-dir", help="Output directory. Defaults to <project>/video-export.")
    parser.add_argument("--language", default="zh", help="Whisper language code. Default: zh.")
    parser.add_argument("--model", default="large-v3-turbo", help="Whisper model. Default: large-v3-turbo.")
    parser.add_argument("--transcript-json", help="Reuse an existing transcript JSON instead of re-transcribing.")
    parser.add_argument("--script-file", help="Optional original narration script used to improve terminology correction.")
    parser.add_argument("--outline-file", help="Optional slide outline file. If omitted, the script auto-detects outline.md / outline*.md in the project.")
    parser.add_argument("--lead-in", type=float, default=DEFAULT_LEAD_IN, help="Seconds to wait after clicking start before timing begins.")
    parser.add_argument("--subtitle-mode", choices=["soft", "hard", "both", "none"], default="soft", help="Subtitle export mode. soft=plain video + soft subtitle track, hard=burned captions only, both=plain+soft+hardsub, none=plain video only.")
    parser.add_argument("--skip-record", action="store_true", help="Only generate transcript, captions, and slide timeline.")
    parser.add_argument("--disable-sfx", action="store_true", help="Disable synthetic page-turn SFX mixed into the audio.")
    parser.add_argument("--keep-raw", action="store_true", help="Keep previous raw recording files instead of overwriting them.")
    return parser.parse_args()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def probe_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nokey=1:noprint_wrappers=1",
            str(path),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return float(result.stdout.strip())


def run_ffmpeg(command: list[str], cwd: Path | None = None) -> None:
    subprocess.run(
        command,
        check=True,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def detect_index_file(project_dir: Path, explicit: str | None) -> Path:
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"Index file not found: {path}")
        return path

    preferred = [project_dir / "index.html", project_dir / "index-ai.html"]
    for candidate in preferred:
        if candidate.exists():
            return candidate

    matches = sorted(project_dir.glob("index*.html"))
    if matches:
        return matches[0]
    raise FileNotFoundError(f"No index HTML found under {project_dir}")


def extract_slide_paths_from_index(index_file: Path) -> list[Path]:
    raw = read_text(index_file)
    matches = re.findall(r'<iframe[^>]+src="([^"]*slide-[^"]+\.html)"', raw, flags=re.IGNORECASE)
    slides: list[Path] = []
    for item in matches:
        resolved = (index_file.parent / item).resolve()
        if resolved.exists():
            slides.append(resolved)
    return slides


def detect_slide_paths(project_dir: Path, index_file: Path) -> list[Path]:
    indexed = extract_slide_paths_from_index(index_file)
    if indexed:
        return indexed

    for dirname in ("slides", "slides-ai"):
        folder = project_dir / dirname
        candidates = sorted(folder.glob("slide-*.html"))
        if candidates:
            return candidates

    fallback = sorted(project_dir.glob("**/slide-*.html"))
    if fallback:
        return fallback
    raise FileNotFoundError(f"No slide HTML files found under {project_dir}")


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def strip_html_to_lines(raw_html: str) -> list[str]:
    content = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", raw_html)
    content = content.replace("\r", "\n")
    for tag in HTML_BREAK_TAGS:
        content = content.replace(tag, f"{tag}\n")
    content = re.sub(r"(?i)<br\s*/?>", "\n", content)
    content = re.sub(r"(?s)<[^>]+>", " ", content)
    content = html.unescape(content)
    lines = []
    for line in content.splitlines():
        line = normalize_whitespace(line)
        if line:
            lines.append(line)
    return lines


def is_noise_line(text: str) -> bool:
    compact = text.strip()
    if not compact:
        return True
    if compact in {"磊哥哥科技拆解室", "开始播放", "开始", "START"}:
        return True
    if re.fullmatch(r"\d+\s*/\s*\d+", compact):
        return True
    return False


def clean_slide_line(text: str) -> str:
    cleaned = normalize_whitespace(text)
    cleaned = re.sub(r"^\d+\s*/\s*\d+\s*[-—–:：]?\s*", "", cleaned)
    cleaned = cleaned.replace("WorkBuddy", "Workbuddy")
    cleaned = cleaned.replace("autoclaw", "AutoClaw")
    return cleaned


def detect_outline_entries(project_dir: Path, slide_count: int, explicit: str | None) -> list[str]:
    candidates: list[Path] = []
    if explicit:
        outline_path = Path(explicit).expanduser().resolve()
        if outline_path.exists():
            candidates.append(outline_path)
    else:
        candidates.extend(sorted(project_dir.glob("outline*.md")))

    for candidate in candidates:
        lines = []
        for raw_line in read_text(candidate).splitlines():
            stripped = raw_line.strip()
            if not stripped:
                continue
            match = re.match(r"^(?:[-*]\s+|\d+\s*[.)、｜|]\s+)(.+)$", stripped)
            if match:
                lines.append(normalize_whitespace(match.group(1)))
        if len(lines) == slide_count:
            return lines
    return []


def tokenize_match_text(text: str) -> Counter[str]:
    ascii_tokens = [token.lower() for token in ASCII_PHRASE_RE.findall(text)]
    ascii_tokens += [piece.lower() for phrase in ascii_tokens for piece in phrase.split() if piece]

    chinese_runs = re.findall(r"[\u4e00-\u9fff]{2,}", text)
    grams: list[str] = []
    for run in chinese_runs:
        grams.extend(run[index : index + 2] for index in range(len(run) - 1))
        if len(run) <= 8:
            grams.append(run)
    return Counter(ascii_tokens + grams)


def counter_cosine(left: Counter[str], right: Counter[str]) -> float:
    if not left or not right:
        return 0.0
    overlap = sum(value * right.get(key, 0) for key, value in left.items())
    if overlap <= 0:
        return 0.0
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return overlap / (left_norm * right_norm)


def build_slide_profiles(slide_paths: list[Path], outline_entries: list[str] | None = None) -> list[dict]:
    profiles: list[dict] = []
    for index, slide_path in enumerate(slide_paths, start=1):
        lines = [clean_slide_line(line) for line in strip_html_to_lines(read_text(slide_path)) if not is_noise_line(line)]
        deduped: list[str] = []
        seen: set[str] = set()
        for line in lines:
            if line in seen:
                continue
            seen.add(line)
            deduped.append(line)
        title_lines = deduped[:3] if deduped else [f"Slide {index}"]
        body_lines = deduped[:10]
        outline_text = clean_slide_line(outline_entries[index - 1]) if outline_entries and index - 1 < len(outline_entries) else ""
        title_text = normalize_whitespace(" ".join([outline_text, " ".join(title_lines)]).strip())
        body_text = normalize_whitespace(" ".join(body_lines))
        title_counter = tokenize_match_text(title_text)
        body_counter = tokenize_match_text(body_text)
        weight = max(60, int(len(title_text) * 1.6 + len(body_text) * 0.8))
        profiles.append(
            {
                "slide": index,
                "path": slide_path,
                "outline_text": outline_text,
                "title_lines": title_lines,
                "body_lines": body_lines,
                "title_text": title_text,
                "body_text": body_text,
                "title_counter": title_counter,
                "body_counter": body_counter,
                "weight": weight,
            }
        )
    return profiles


def collect_correction_phrases(slide_profiles: list[dict], extra_texts: list[str]) -> list[str]:
    phrases: set[str] = set()
    for profile in slide_profiles:
        source = f"{profile['title_text']} {profile['body_text']}"
        phrases.update(ASCII_PHRASE_RE.findall(source))
    for text in extra_texts:
        phrases.update(ASCII_PHRASE_RE.findall(text))

    prioritized = sorted(
        {phrase.strip() for phrase in phrases if len(phrase.strip()) >= 2},
        key=lambda item: (-len(item), item.lower()),
    )
    return prioritized


def correct_ascii_phrases(text: str, lexicon: list[str], cache: dict[str, str]) -> str:
    if not lexicon:
        return text

    lower_map = {item.lower(): item for item in lexicon}

    def replace(match: re.Match[str]) -> str:
        token = match.group(0)
        lookup = token.lower()
        if lookup in cache:
            return cache[lookup]
        if lookup in lower_map:
            cache[lookup] = lower_map[lookup]
            return cache[lookup]

        candidates = difflib.get_close_matches(token, lexicon, n=1, cutoff=0.74)
        if not candidates:
            candidates = difflib.get_close_matches(token.lower(), [item.lower() for item in lexicon], n=1, cutoff=0.74)
            if candidates:
                matched = lower_map[candidates[0]]
                cache[lookup] = matched
                return matched
            cache[lookup] = token
            return token

        cache[lookup] = candidates[0]
        return cache[lookup]

    return ASCII_PHRASE_RE.sub(replace, text)


def clean_transcript_text(text: str, lexicon: list[str], cache: dict[str, str]) -> str:
    value = normalize_whitespace(text)
    value = correct_ascii_phrases(value, lexicon, cache)
    replacements = {
        "雷哥哥": "磊哥哥",
        "李哥哥": "磊哥哥",
        "Open Core": "OpenClaw",
        "OpenCloud": "OpenClaw",
        "Open Cloud": "OpenClaw",
        "Open Claw": "OpenClaw",
        "Cloud Code": "Claude Code",
        "Cloud Work": "Claude Work",
        "WorkBuddy": "Workbuddy",
        "workbuddy": "Workbuddy",
        "M C P": "MCP",
        "V L M": "VLM",
        "A G I": "AGI",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    value = value.replace(",", "，")
    value = re.sub(r"\s*([，。！？；：、])\s*", r"\1", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def resolve_whisper_script() -> Path:
    current_skill = Path(__file__).resolve().parents[1]
    candidates = [
        current_skill.parent / "whisper-stt" / "scripts" / "transcribe.py",
        Path.home() / ".codex" / "skills" / "whisper-stt" / "scripts" / "transcribe.py",
        Path.home() / ".agents" / "skills" / "whisper-stt" / "scripts" / "transcribe.py",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Could not locate whisper-stt/scripts/transcribe.py")


def ensure_transcript(audio_path: Path, output_path: Path, language: str, model: str, explicit_json: str | None) -> Path:
    if explicit_json:
        transcript_path = Path(explicit_json).expanduser().resolve()
        if not transcript_path.exists():
            raise FileNotFoundError(f"Transcript JSON not found: {transcript_path}")
        return transcript_path

    if output_path.exists() and output_path.stat().st_size > 0:
        return output_path

    whisper_script = resolve_whisper_script()
    with output_path.open("w", encoding="utf-8") as handle:
        subprocess.run(
            [
                "python3",
                str(whisper_script),
                str(audio_path),
                "--language",
                language,
                "--model",
                model,
                "--output",
                "json",
            ],
            check=True,
            stdout=handle,
            stderr=subprocess.PIPE,
            text=True,
        )
    return output_path


def prepare_segments(transcript_data: dict, lexicon: list[str]) -> list[dict]:
    cache: dict[str, str] = {}
    segments: list[dict] = []
    for segment in transcript_data.get("segments", []):
        start = float(segment.get("start", 0.0))
        end = float(segment.get("end", start))
        if end <= start:
            continue
        text = clean_transcript_text(str(segment.get("text", "")).strip(), lexicon, cache)
        if not text:
            continue
        segments.append(
            {
                "start": start,
                "end": end,
                "text": text,
                "counter": tokenize_match_text(text),
            }
        )
    return segments


def build_expected_starts(slide_profiles: list[dict], total_duration: float) -> list[float]:
    total_weight = sum(profile["weight"] for profile in slide_profiles) or 1
    starts = [0.0]
    cumulative = 0.0
    for profile in slide_profiles[:-1]:
        cumulative += profile["weight"]
        starts.append(total_duration * cumulative / total_weight)
    return starts


def collect_window_counter(segments: list[dict], start_index: int, max_duration: float = 15.0, max_segments: int = 8) -> Counter[str]:
    counter: Counter[str] = Counter()
    if start_index >= len(segments):
        return counter
    limit = segments[start_index]["start"] + max_duration
    taken = 0
    for segment in segments[start_index:]:
        counter.update(segment["counter"])
        taken += 1
        if taken >= max_segments or segment["end"] >= limit:
            break
    return counter


def infer_timeline(slide_profiles: list[dict], segments: list[dict], total_duration: float) -> list[dict]:
    if not slide_profiles:
        return []
    average = total_duration / max(1, len(slide_profiles))
    min_gap = max(3.5, min(10.0, average * 0.35))
    expected = build_expected_starts(slide_profiles, total_duration)

    timeline = [
        {
            "slide": slide_profiles[0]["slide"],
            "start": 0.0,
            "method": "cover",
            "confidence": 1.0,
            "reason": slide_profiles[0]["title_text"] or "first slide",
        }
    ]

    used_segment_index = 0
    for slide_index in range(1, len(slide_profiles)):
        profile = slide_profiles[slide_index]
        previous_profile = slide_profiles[slide_index - 1]
        previous_start = timeline[-1]["start"]
        remaining = len(slide_profiles) - slide_index - 1
        latest = max(previous_start + min_gap, total_duration - remaining * min_gap - 0.8)
        expected_start = expected[slide_index]

        best_time = min(max(expected_start, previous_start + min_gap), latest)
        best_score = -1.0
        best_index = None
        scored_candidates: list[tuple[int, float, float]] = []

        for index in range(used_segment_index, len(segments)):
            segment = segments[index]
            start = float(segment["start"])
            if start < previous_start + min_gap:
                continue
            if start > latest:
                break
            window_counter = collect_window_counter(segments, index)
            score = counter_cosine(window_counter, profile["body_counter"])
            score += 1.12 * counter_cosine(window_counter, profile["title_counter"])
            score -= 0.34 * counter_cosine(window_counter, previous_profile["body_counter"])
            score -= 0.18 * counter_cosine(window_counter, previous_profile["title_counter"])
            score -= 0.015 * (abs(start - expected_start) / max(average, 1.0))
            scored_candidates.append((index, start, score))
            if score > best_score:
                best_score = score
                best_time = start
                best_index = index

        chosen_index = best_index
        chosen_time = best_time
        method = "estimated"
        confidence = 0.0
        if scored_candidates and best_index is not None and best_score >= 0.045:
            threshold = max(0.045, best_score * 0.72)
            for candidate_index, candidate_start, candidate_score in scored_candidates:
                if candidate_score >= threshold:
                    chosen_index = candidate_index
                    chosen_time = candidate_start
                    confidence = round(candidate_score, 4)
                    method = "matched"
                    break

        timeline.append(
            {
                "slide": profile["slide"],
                "start": round(chosen_time, 3),
                "method": method,
                "confidence": confidence,
                "reason": profile["title_text"] or f"slide {profile['slide']}",
            }
        )

        if chosen_index is not None:
            used_segment_index = chosen_index

    timeline[0]["start"] = 0.0
    for index, item in enumerate(timeline):
        next_start = timeline[index + 1]["start"] if index + 1 < len(timeline) else total_duration
        if next_start <= item["start"]:
            next_start = min(total_duration, item["start"] + min_gap)
            if index + 1 < len(timeline):
                timeline[index + 1]["start"] = next_start
        item["end"] = round(next_start, 3)
        item["duration"] = round(next_start - item["start"], 3)
        item["src"] = str(slide_profiles[index]["path"])

    timeline[-1]["end"] = round(total_duration, 3)
    timeline[-1]["duration"] = round(total_duration - timeline[-1]["start"], 3)
    return timeline


def visual_len(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def tokenize_caption_text(text: str) -> list[str]:
    pattern = r"[A-Za-z0-9][A-Za-z0-9+./-]*(?: [A-Za-z0-9][A-Za-z0-9+./-]*)*|[\u4e00-\u9fff]|[，。！？；：、,.!?;:（）【】《》「」『』“”‘’…—]|[^\s]"
    return re.findall(pattern, text)


def token_visual_width(token: str) -> int:
    return len(token) if ASCII_PHRASE_RE.fullmatch(token) else 1


def needs_space_between(prev: str, current: str) -> bool:
    if not prev:
        return False
    if prev in OPEN_PUNCT or current in CLOSE_PUNCT:
        return False
    if current in OPEN_PUNCT or prev in CLOSE_PUNCT:
        return False
    return ASCII_PHRASE_RE.fullmatch(prev) is not None or ASCII_PHRASE_RE.fullmatch(current) is not None


def join_caption_tokens(tokens: list[str]) -> str:
    output: list[str] = []
    previous = ""
    for token in tokens:
        if output and needs_space_between(previous, token):
            output.append(" ")
        output.append(token)
        previous = token
    return "".join(output)


def wrap_caption_text(text: str, width: int = 20) -> str:
    tokens = tokenize_caption_text(text)
    if not tokens:
        return text

    lines: list[str] = []
    current_tokens: list[str] = []
    current_width = 0

    for token in tokens:
        gap_width = 1 if current_tokens and needs_space_between(current_tokens[-1], token) else 0
        token_width = token_visual_width(token)
        if token in CLOSE_PUNCT and current_tokens and current_width + gap_width + token_width > width:
            current_tokens.append(token)
            current_width += gap_width + token_width
            continue
        if current_tokens and current_width + gap_width + token_width > width:
            lines.append(join_caption_tokens(current_tokens))
            current_tokens = [token]
            current_width = token_width
        else:
            current_width += gap_width + token_width
            current_tokens.append(token)
    if current_tokens:
        lines.append(join_caption_tokens(current_tokens))

    if len(lines) <= 2:
        return "\n".join(lines)
    return "\n".join([lines[0], "".join(lines[1:])])


def srt_time(value: float) -> str:
    milliseconds = max(0, int(round(value * 1000)))
    hours, rest = divmod(milliseconds, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    seconds, millis = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def build_captions(segments: list[dict]) -> list[dict]:
    captions: list[dict] = []
    current_parts: list[dict] = []
    current_text = ""
    current_start = 0.0

    def flush() -> None:
        nonlocal current_parts, current_text, current_start
        if not current_parts:
            return
        merged_text = normalize_whitespace("".join(part["text"] for part in current_parts))
        captions.append(
            {
                "index": len(captions) + 1,
                "start": round(current_start, 3),
                "end": round(float(current_parts[-1]["end"]), 3),
                "raw_text": merged_text,
                "text": wrap_caption_text(merged_text),
            }
        )
        current_parts = []
        current_text = ""
        current_start = 0.0

    for segment in segments:
        segment_text = segment["text"]
        if not current_parts:
            current_parts = [segment]
            current_text = segment_text
            current_start = float(segment["start"])
            continue

        candidate_text = current_text + segment_text
        candidate_duration = float(segment["end"]) - current_start
        should_flush = False
        if visual_len(current_text) >= 26:
            should_flush = True
        if candidate_duration >= 4.2:
            should_flush = True
        if visual_len(candidate_text) >= 34:
            should_flush = True
        if re.search(r"[。！？；]$", current_text) and candidate_duration >= 1.2:
            should_flush = True

        if should_flush:
            flush()
            current_parts = [segment]
            current_text = segment_text
            current_start = float(segment["start"])
        else:
            current_parts.append(segment)
            current_text = candidate_text

    flush()
    return captions


def write_captions(captions: list[dict], srt_path: Path, json_path: Path) -> None:
    lines: list[str] = []
    for item in captions:
        lines.extend(
            [
                str(item["index"]),
                f"{srt_time(float(item['start']))} --> {srt_time(float(item['end']))}",
                item["text"],
                "",
            ]
        )
    srt_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    json_path.write_text(json.dumps({"captions": captions}, ensure_ascii=False, indent=2), encoding="utf-8")


def build_page_turn_effect(sample_rate: int = SAMPLE_RATE, duration: float = 0.26) -> np.ndarray:
    rng = np.random.default_rng(20260324)
    frame_count = int(sample_rate * duration)
    time_axis = np.arange(frame_count, dtype=np.float32) / sample_rate
    sweep_hz = 180.0 - 95.0 * (time_axis / duration)
    phase = 2.0 * math.pi * np.cumsum(sweep_hz) / sample_rate
    tone = np.sin(phase).astype(np.float32)
    noise = rng.normal(0.0, 1.0, frame_count).astype(np.float32)
    kernel = np.hanning(121).astype(np.float32)
    kernel /= float(kernel.sum())
    filtered_noise = np.convolve(noise, kernel, mode="same")
    envelope = np.sin(np.pi * np.clip(time_axis / duration, 0.0, 1.0)).astype(np.float32)
    envelope *= np.exp(-3.8 * time_axis / duration).astype(np.float32)
    effect = (0.085 * filtered_noise + 0.16 * tone) * envelope
    effect /= max(1e-6, float(np.max(np.abs(effect))))
    return (effect * 0.28).astype(np.float32)


def write_wave(path: Path, samples: np.ndarray, sample_rate: int = SAMPLE_RATE) -> None:
    clipped = np.clip(samples, -1.0, 1.0)
    int16 = (clipped * 32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(int16.tobytes())


def build_page_sfx_track(total_duration: float, timeline: list[dict], output_path: Path) -> None:
    total_frames = int(math.ceil((total_duration + 1.0) * SAMPLE_RATE))
    track = np.zeros(total_frames, dtype=np.float32)
    effect = build_page_turn_effect()
    for item in timeline[1:]:
        begin = int(round(float(item["start"]) * SAMPLE_RATE))
        end = min(total_frames, begin + len(effect))
        track[begin:end] += effect[: end - begin]
    peak = float(np.max(np.abs(track)))
    if peak > 0.92:
        track /= peak / 0.92
    write_wave(output_path, track)


def mix_audio_with_sfx(audio_path: Path, sfx_path: Path, output_path: Path) -> None:
    run_ffmpeg(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(audio_path),
            "-i",
            str(sfx_path),
            "-filter_complex",
            "[0:a]volume=1.0[a0];[1:a]volume=0.32[a1];[a0][a1]amix=inputs=2:normalize=0[a]",
            "-map",
            "[a]",
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ]
    )


def start_static_server(root_dir: Path) -> tuple[socketserver.TCPServer, str]:
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


def inject_caption_overlay(page, captions: list[dict]) -> None:
    page.evaluate(
        """
        (payload) => {
          document.documentElement.requestFullscreen = async () => {};
          document.exitFullscreen = async () => {};

          if (!document.getElementById('record-caption-style')) {
            const style = document.createElement('style');
            style.id = 'record-caption-style';
            style.textContent = `
              #record-caption-layer {
                position: fixed;
                left: 0;
                right: 0;
                bottom: 34px;
                display: flex;
                justify-content: center;
                pointer-events: none;
                z-index: 2147483647;
              }
              #record-caption-box {
                max-width: min(1480px, calc(100vw - 120px));
                padding: 16px 30px 18px;
                border-radius: 24px;
                background: rgba(8, 11, 17, 0.72);
                border: 1px solid rgba(255, 255, 255, 0.12);
                color: #ffffff;
                font-family: "Hiragino Sans GB", "PingFang SC", "Microsoft YaHei", "Heiti SC", sans-serif;
                font-size: 46px;
                line-height: 1.34;
                font-weight: 700;
                letter-spacing: 0.02em;
                text-align: center;
                white-space: pre-line;
                box-shadow: 0 14px 36px rgba(0, 0, 0, 0.36);
                backdrop-filter: blur(12px);
                text-shadow: 0 2px 16px rgba(0, 0, 0, 0.42);
                opacity: 0;
                transform: translateY(10px);
                transition: opacity 160ms ease, transform 160ms ease;
              }
              body.is-playing #record-caption-box.is-visible {
                opacity: 1;
                transform: translateY(0);
              }
            `;
            document.head.appendChild(style);
          }

          let layer = document.getElementById('record-caption-layer');
          let box = document.getElementById('record-caption-box');
          if (!layer) {
            layer = document.createElement('div');
            layer.id = 'record-caption-layer';
            box = document.createElement('div');
            box.id = 'record-caption-box';
            layer.appendChild(box);
            document.body.appendChild(layer);
          }

          window.__RECORD_CAPTIONS__ = payload;
          window.__CAPTION_CLOCK_STARTED__ = false;

          window.__startRecordCaptions = (leadSeconds) => {
            if (window.__CAPTION_CLOCK_STARTED__) return;
            window.__CAPTION_CLOCK_STARTED__ = true;
            const captions = window.__RECORD_CAPTIONS__ || [];
            const leadMs = (leadSeconds || 0) * 1000;
            const startAt = performance.now() + leadMs;
            let pointer = 0;

            const tick = () => {
              const current = (performance.now() - startAt) / 1000;
              while (pointer < captions.length - 1 && current > captions[pointer].end) {
                pointer += 1;
              }
              const active = captions.find((item, index) => {
                if (index + 1 < pointer) return false;
                return current >= item.start && current < item.end;
              });
              if (active) {
                box.textContent = active.text;
                box.classList.add('is-visible');
              } else {
                box.textContent = '';
                box.classList.remove('is-visible');
              }
              requestAnimationFrame(tick);
            };
            requestAnimationFrame(tick);
          };
        }
        """,
        captions,
    )


def disable_fullscreen_request(page) -> None:
    page.evaluate(
        """() => {
          document.documentElement.requestFullscreen = async () => {};
          document.exitFullscreen = async () => {};
        }"""
    )


def click_start(page) -> None:
    selectors = [
        "[data-start]",
        "button.start-button",
        "button",
    ]
    for selector in selectors:
        locator = page.locator(selector)
        if locator.count():
            locator.first.click()
            return
    raise RuntimeError("Could not locate a start button in the web PPT player.")


def record_deck(
    project_dir: Path,
    index_file: Path,
    output_video: Path,
    timeline: list[dict],
    captions: list[dict],
    lead_in_seconds: float,
    keep_raw: bool,
    show_captions: bool,
) -> None:
    recordings_dir = output_video.parent / "recordings"
    recordings_dir.mkdir(parents=True, exist_ok=True)
    if output_video.exists() and not keep_raw:
        output_video.unlink()

    server, base_url = start_static_server(project_dir)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": WIDTH, "height": HEIGHT},
                device_scale_factor=1,
                record_video_dir=str(recordings_dir),
                record_video_size={"width": WIDTH, "height": HEIGHT},
            )
            page = context.new_page()
            page.goto(f"{base_url}/{index_file.relative_to(project_dir).as_posix()}", wait_until="load")
            disable_fullscreen_request(page)
            if show_captions:
                inject_caption_overlay(page, captions)
            page.wait_for_timeout(250)
            click_start(page)
            try:
                page.wait_for_function("document.body.classList.contains('is-playing')", timeout=2500)
            except Exception:
                pass
            if show_captions:
                page.evaluate("(leadSeconds) => window.__startRecordCaptions?.(leadSeconds)", lead_in_seconds)
            page.wait_for_timeout(int(lead_in_seconds * 1000))

            current_time = 0.0
            for item in timeline[1:]:
                wait_ms = max(0, int(round((float(item['start']) - current_time) * 1000)))
                if wait_ms:
                    page.wait_for_timeout(wait_ms)
                page.keyboard.press("ArrowRight")
                current_time = float(item["start"])

            tail_ms = max(0, int(round((float(timeline[-1]["end"]) - current_time + 0.35) * 1000)))
            if tail_ms:
                page.wait_for_timeout(tail_ms)
            page.wait_for_timeout(300)

            video = page.video
            page.close()
            context.close()
            browser.close()

            if video is None:
                raise RuntimeError("Playwright did not return a recording handle.")
            shutil.copy2(Path(video.path()), output_video)
    finally:
        stop_static_server(server)


def mux_plain_video(raw_webm: Path, audio_path: Path, lead_in: float, duration: float, output_video: Path) -> None:
    run_ffmpeg(
        [
            "ffmpeg",
            "-y",
            "-ss",
            str(lead_in),
            "-i",
            str(raw_webm),
            "-i",
            str(audio_path),
            "-t",
            f"{duration:.3f}",
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            "-shortest",
            str(output_video),
        ]
    )


def add_soft_subtitle_track(source_video: Path, captions_srt: Path, softsub_video: Path) -> None:
    run_ffmpeg(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(source_video),
            "-i",
            str(captions_srt),
            "-c:v",
            "copy",
            "-c:a",
            "copy",
            "-c:s",
            "mov_text",
            "-metadata:s:s:0",
            "language=zho",
            str(softsub_video),
        ]
    )


def extract_validation_frames(video_path: Path, output_dir: Path) -> list[str]:
    frames = [
        (2, output_dir / "frame_check_0002.png"),
        (min(60, int(probe_duration(video_path) // 2)), output_dir / "frame_check_mid.png"),
    ]
    generated: list[str] = []
    for second, path in frames:
        run_ffmpeg(
            [
                "ffmpeg",
                "-y",
                "-ss",
                str(second),
                "-i",
                str(video_path),
                "-vframes",
                "1",
                str(path),
            ]
        )
        generated.append(str(path))
    return generated


def main() -> None:
    args = parse_args()
    project_dir = Path(args.project).expanduser().resolve()
    if not project_dir.exists():
        raise FileNotFoundError(f"Project directory not found: {project_dir}")

    audio_path = Path(args.audio).expanduser().resolve()
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    index_file = detect_index_file(project_dir, args.index_file)
    slide_paths = detect_slide_paths(project_dir, index_file)
    outline_entries = detect_outline_entries(project_dir, len(slide_paths), args.outline_file)
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else (project_dir / "video-export")
    output_dir.mkdir(parents=True, exist_ok=True)

    transcript_output = output_dir / "transcript.json"
    captions_srt = output_dir / "captions.srt"
    captions_json = output_dir / "captions.json"
    timeline_json = output_dir / "slide_timeline.json"
    raw_recording = output_dir / "deck_recording.webm"
    raw_recording_hardsub = output_dir / "deck_recording_hardsub.webm"
    page_sfx_track = output_dir / "page_turn_sfx_track.wav"
    audio_with_sfx = output_dir / "audio_with_sfx.wav"
    final_video = output_dir / "final_video.mp4"
    final_video_softsub = output_dir / "final_video_softsub.mp4"
    final_video_hardsub = output_dir / "final_video_hardsub.mp4"
    summary_json = output_dir / "summary.json"

    extra_texts: list[str] = []
    if args.script_file:
        script_file = Path(args.script_file).expanduser().resolve()
        if script_file.exists():
            extra_texts.append(read_text(script_file))

    slide_profiles = build_slide_profiles(slide_paths, outline_entries=outline_entries)
    correction_phrases = collect_correction_phrases(slide_profiles, extra_texts)

    transcript_path = ensure_transcript(audio_path, transcript_output, args.language, args.model, args.transcript_json)
    transcript_data = json.loads(read_text(transcript_path))
    segments = prepare_segments(transcript_data, correction_phrases)
    if not segments:
        raise RuntimeError("No usable transcript segments were generated.")

    total_duration = probe_duration(audio_path)
    captions = build_captions(segments)
    write_captions(captions, captions_srt, captions_json)

    timeline = infer_timeline(slide_profiles, segments, total_duration)
    timeline_json.write_text(json.dumps({"timeline": timeline}, ensure_ascii=False, indent=2), encoding="utf-8")

    audio_for_video = audio_path
    if not args.disable_sfx:
        build_page_sfx_track(total_duration, timeline, page_sfx_track)
        mix_audio_with_sfx(audio_path, page_sfx_track, audio_with_sfx)
        audio_for_video = audio_with_sfx

    validation_frames: list[str] = []
    if not args.skip_record:
        soft_requested = args.subtitle_mode in {"soft", "both"}
        hard_requested = args.subtitle_mode in {"hard", "both"}
        plain_requested = args.subtitle_mode in {"soft", "both", "none"}

        if plain_requested:
            record_deck(project_dir, index_file, raw_recording, timeline, captions, args.lead_in, args.keep_raw, show_captions=False)
            mux_plain_video(raw_recording, audio_for_video, args.lead_in, total_duration, final_video)
            if soft_requested:
                add_soft_subtitle_track(final_video, captions_srt, final_video_softsub)

        if hard_requested:
            record_deck(project_dir, index_file, raw_recording_hardsub, timeline, captions, args.lead_in, args.keep_raw, show_captions=True)
            mux_plain_video(raw_recording_hardsub, audio_for_video, args.lead_in, total_duration, final_video_hardsub)
            if args.subtitle_mode == "hard":
                shutil.copy2(final_video_hardsub, final_video)

        frame_source = final_video if final_video.exists() else final_video_hardsub
        if frame_source.exists():
            validation_frames = extract_validation_frames(frame_source, output_dir)

    summary = {
        "project_dir": str(project_dir),
        "deck_index": str(index_file),
        "audio_source": str(audio_path),
        "audio_for_video": str(audio_for_video),
        "transcript_json": str(transcript_path),
        "captions_srt": str(captions_srt),
        "captions_json": str(captions_json),
        "slide_timeline_json": str(timeline_json),
        "slides": len(slide_profiles),
        "captions": len(captions),
        "duration_seconds": round(total_duration, 3),
        "subtitle_mode": args.subtitle_mode,
        "hard_subtitles_burned_in": args.subtitle_mode in {"hard", "both"} and not args.skip_record,
        "raw_recording": str(raw_recording) if raw_recording.exists() else None,
        "raw_recording_hardsub": str(raw_recording_hardsub) if raw_recording_hardsub.exists() else None,
        "final_video": str(final_video) if final_video.exists() else None,
        "final_video_softsub": str(final_video_softsub) if final_video_softsub.exists() else None,
        "final_video_hardsub": str(final_video_hardsub) if final_video_hardsub.exists() else None,
        "validation_frames": validation_frames,
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
