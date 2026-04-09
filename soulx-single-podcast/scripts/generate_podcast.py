#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def load_config(config_path: Path) -> dict:
    return json.loads(config_path.read_text(encoding="utf-8"))


def ensure_runtime(config_path: Path) -> None:
    config = load_config(config_path)
    target_python = str(Path(config["python_bin"]).resolve())
    if Path(sys.executable).resolve() == Path(target_python):
        return
    try:
        import numpy  # noqa: F401
        import soundfile  # noqa: F401
    except Exception:
        os.execv(target_python, [target_python, *sys.argv])


def resolve_path(base: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (base / path).resolve()


def choose_reference(config: dict, config_path: Path, reference_id: str | None) -> dict:
    references = config["reference_profiles"]
    if reference_id:
        for item in references:
            if item["id"] == reference_id:
                return item
        raise ValueError(f"Unknown reference id: {reference_id}")
    for item in references:
        if item.get("default"):
            return item
    return references[0]


def run_command(command: list[str], env: dict, dry_run: bool) -> None:
    print(" ".join(command))
    if dry_run:
        return
    subprocess.run(command, check=True, env=env)


def merge_wavs(segment_paths: list[Path], output_path: Path, silence_ms: int) -> tuple[int, float]:
    import numpy as np
    import soundfile as sf

    parts = []
    sr = None
    for idx, segment_path in enumerate(segment_paths):
        data, part_sr = sf.read(segment_path)
        if sr is None:
            sr = part_sr
        if data.ndim > 1:
            data = data.mean(axis=1)
        parts.append(data.astype(np.float32))
        if idx < len(segment_paths) - 1:
            parts.append(np.zeros(int(sr * silence_ms / 1000), dtype=np.float32))
    merged = np.concatenate(parts) if parts else np.array([], dtype=np.float32)
    sf.write(output_path, merged, sr or 24000)
    duration = round(len(merged) / (sr or 24000), 2)
    return sr or 24000, duration


def apply_speed_rate(audio_path: Path, speed_rate: float) -> tuple[int, float]:
    import librosa
    import numpy as np
    import soundfile as sf

    if abs(speed_rate - 1.0) < 1e-6:
        data, sr = sf.read(audio_path)
        return sr, round(len(data) / sr, 2)

    data, sr = sf.read(audio_path)
    if data.ndim > 1:
        channels = []
        for channel_index in range(data.shape[1]):
            channels.append(librosa.effects.time_stretch(data[:, channel_index].astype(float), rate=speed_rate))
        min_len = min(len(channel) for channel in channels)
        stretched = np.stack([channel[:min_len] for channel in channels], axis=1)
    else:
        stretched = librosa.effects.time_stretch(data.astype(float), rate=speed_rate)
    sf.write(audio_path, stretched, sr)
    return sr, round(len(stretched) / sr, 2)


def main() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    default_config = skill_dir / "config.json"
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(default_config))
    parser.add_argument("--text")
    parser.add_argument("--input-file")
    parser.add_argument("--language", choices=["zh", "en"])
    parser.add_argument("--oralization-degree", type=float)
    parser.add_argument("--reference-id")
    parser.add_argument("--output-dir")
    parser.add_argument("--output-name")
    parser.add_argument("--max-chars", type=int)
    parser.add_argument("--silence-ms", type=int)
    parser.add_argument("--speed-rate", type=float)
    parser.add_argument("--keep-segments", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    ensure_runtime(config_path)
    skill_dir = config_path.parent
    config = load_config(config_path)

    output_root = resolve_path(skill_dir, args.output_dir or config["output_dir"])
    output_root.mkdir(parents=True, exist_ok=True)
    job_name = args.output_name or datetime.now().strftime("podcast-%Y%m%d-%H%M%S")
    job_dir = output_root / job_name
    job_dir.mkdir(parents=True, exist_ok=True)

    prepare_script = skill_dir / "scripts" / "prepare_script.py"
    prepare_cmd = [
        "python3",
        str(prepare_script),
        "--config",
        str(config_path),
        "--output-dir",
        str(job_dir),
    ]
    if args.text:
        prepare_cmd.extend(["--text", args.text])
    if args.input_file:
        prepare_cmd.extend(["--input-file", args.input_file])
    if args.language:
        prepare_cmd.extend(["--language", args.language])
    if args.oralization_degree is not None:
        prepare_cmd.extend(["--oralization-degree", str(args.oralization_degree)])
    if args.max_chars is not None:
        prepare_cmd.extend(["--max-chars", str(args.max_chars)])
    run_command(prepare_cmd, env=os.environ.copy(), dry_run=args.dry_run)

    if args.dry_run:
        return

    prepare_manifest = json.loads((job_dir / "prepare_manifest.json").read_text(encoding="utf-8"))
    language = prepare_manifest["language"]
    degree = prepare_manifest["oralization_degree"]
    speed_rate = args.speed_rate if args.speed_rate is not None else config["default_speed_rate"]
    reference = choose_reference(config, config_path, args.reference_id)

    repo = Path(config["soulx_repo_path"]).resolve()
    python_bin = Path(config["python_bin"]).resolve()
    model_path = Path(config["model_path"]).resolve()
    reference_audio = resolve_path(skill_dir, reference["audio_path"])
    prompt_text = reference["prompt_text"]
    segments = json.loads((job_dir / "segments.json").read_text(encoding="utf-8"))

    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo)
    segment_paths: list[Path] = []
    for idx, segment in enumerate(segments, start=1):
        out_path = job_dir / f"segment_{idx:02d}.wav"
        command = [
            str(python_bin),
            str(repo / "cli" / "tts.py"),
            "--prompt_text",
            prompt_text,
            "--prompt_audio",
            str(reference_audio),
            "--text",
            segment,
            "--model_path",
            str(model_path),
            "--output_path",
            str(out_path),
            "--seed",
            "7",
        ]
        run_command(command, env=env, dry_run=False)
        segment_paths.append(out_path)

    final_path = job_dir / "final.wav"
    sample_rate, duration = merge_wavs(
        segment_paths,
        final_path,
        args.silence_ms if args.silence_ms is not None else config["default_silence_ms"],
    )
    sample_rate, duration = apply_speed_rate(final_path, speed_rate)

    manifest = {
        "job_dir": str(job_dir),
        "language": language,
        "oralization_degree": degree,
        "speed_rate": speed_rate,
        "reference_id": reference["id"],
        "segment_count": len(segment_paths),
        "sample_rate": sample_rate,
        "duration_sec": duration,
        "final_audio": str(final_path),
    }
    (job_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if not args.keep_segments:
        pass

    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
