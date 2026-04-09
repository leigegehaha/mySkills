from __future__ import annotations

import argparse
import base64
import json
import os
import re
from datetime import datetime
from pathlib import Path

import requests


SKILL_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = SKILL_DIR / "config.json"


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def slugify(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return text or "gemini-image"


def build_prompt(user_prompt: str, style_suffix: str) -> str:
    return f"{user_prompt.strip()}, {style_suffix}"


def generate_once(prompt: str, output_dir: Path) -> Path | None:
    config = load_config()["gemini"]
    api_key = os.getenv(config["api_key_env"], "").strip()
    if not api_key:
        return None
    url = f"{config['api_base_url']}/models/{config['model']}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
    }
    response = requests.post(url, json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()
    candidates = data.get("candidates", [])
    for candidate in candidates:
        parts = candidate.get("content", {}).get("parts", [])
        for part in parts:
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                mime_type = inline.get("mimeType") or inline.get("mime_type") or "image/png"
                suffix = ".png" if "png" in mime_type else ".jpg"
                output_dir.mkdir(parents=True, exist_ok=True)
                name = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{slugify(prompt)[:50]}{suffix}"
                path = output_dir / name
                path.write_bytes(base64.b64decode(inline["data"]))
                return path
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--count", type=int, default=1)
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    style_suffix = load_config()["gemini"]["default_style_suffix"]
    final_prompt = build_prompt(args.prompt, style_suffix)
    outputs = []
    for _ in range(max(1, args.count)):
        path = generate_once(final_prompt, output_dir)
        if path:
            outputs.append(str(path))
    print(json.dumps(outputs, indent=2))


if __name__ == "__main__":
    main()
