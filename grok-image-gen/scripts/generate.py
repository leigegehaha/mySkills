#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "httpx>=0.27.0",
#     "pillow>=10.0.0",
# ]
# ///

import argparse
import base64
import json
import os
import sys
from datetime import datetime
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image as PILImage

SIZE_MAP = {
    ("3:4", "2K"): (1536, 2048),
    ("9:16", "2K"): (1152, 2048),
    ("4:3", "2K"): (2048, 1536),
    ("16:9", "2K"): (2048, 1152),
    ("1:1", "2K"): (960, 960),
    ("3:4", "4K"): (3072, 4096),
    ("9:16", "4K"): (2304, 4096),
    ("4:3", "4K"): (4096, 3072),
    ("16:9", "4K"): (4096, 2304),
    ("1:1", "4K"): (2048, 2048),
}


def load_config(config_path: str) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_api_key(config: dict, provided_key: str | None) -> str | None:
    if provided_key:
        return provided_key
    if config.get("api_key"):
        return config["api_key"]
    return os.environ.get(config.get("api_key_env", "GROK_IMAGE_API_KEY"))


def get_output_path(config: dict, provided_output: str | None, prompt: str) -> Path:
    if provided_output:
        return Path(provided_output)
    output_dir = config.get("output_dir", ".")
    safe_name = "".join(c for c in prompt[:20] if c.isalnum() or c in " _-").strip().replace(" ", "_") or "image"
    filename = f"{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}-{safe_name}.png"
    return Path(output_dir) / filename


def save_image_from_response(data: dict, output_path: Path, width: int, height: int):
    image_b64 = None
    image_url = None
    if isinstance(data, dict):
        if isinstance(data.get("data"), list) and data["data"]:
            item = data["data"][0]
            image_b64 = item.get("b64_json") or item.get("image") or item.get("base64")
            image_url = item.get("url")
        image_b64 = image_b64 or data.get("b64_json")
        image_url = image_url or data.get("url")

    if image_b64:
        image_data = base64.b64decode(image_b64)
    elif image_url:
        with httpx.Client(timeout=300.0, follow_redirects=True) as client:
            response = client.get(image_url)
            response.raise_for_status()
            image_data = response.content
    else:
        print(f"错误：响应中未找到图片数据\n{json.dumps(data, ensure_ascii=False)[:1000]}", file=sys.stderr)
        sys.exit(1)

    image = PILImage.open(BytesIO(image_data))
    if image.size != (width, height):
        image = image.resize((width, height), PILImage.LANCZOS)
    image.convert("RGB").save(str(output_path), "PNG")


def generate_text_to_image(base_url: str, api_key: str, model: str, prompt: str, width: int, height: int, output_path: Path):
    url = f"{base_url}/v1/images/generations"
    payload = {
        "model": model,
        "prompt": prompt,
        "size": f"{width}x{height}"
    }

    print("=" * 50)
    print("Grok 图片生成器")
    print("=" * 50)
    print(f"接口: {url}")
    print(f"模型: {model}")
    print(f"尺寸: {width}x{height}")
    print("模式: T2I 文生图")
    print("正在生成图片...")

    with httpx.Client(timeout=300.0) as client:
        response = client.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    save_image_from_response(data, output_path, width, height)


def generate_image_edit(base_url: str, api_key: str, model: str, prompt: str, width: int, height: int, input_image: Path, output_path: Path):
    url = f"{base_url}/v1/images/edits"

    print("=" * 50)
    print("Grok 图片编辑器")
    print("=" * 50)
    print(f"接口: {url}")
    print(f"模型: {model}")
    print(f"尺寸: {width}x{height}")
    print(f"输入图片: {input_image}")
    print("模式: I2I 图生图 / 图片编辑")
    print("正在生成图片...")

    with httpx.Client(timeout=300.0) as client:
        with open(input_image, "rb") as f:
            files = {
                "image": (input_image.name, f, "application/octet-stream")
            }
            data = {
                "prompt": prompt,
                "model": model,
                "n": "1",
                "size": f"{width}x{height}"
            }
            response = client.post(
                url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Accept": "application/json",
                },
                data=data,
                files=files,
            )
            response.raise_for_status()
            body = response.json()

    save_image_from_response(body, output_path, width, height)


def main():
    parser = argparse.ArgumentParser(description="Grok 图片生成器 / 编辑器")
    parser.add_argument("--config", "-c", required=True, help="config.json 路径")
    parser.add_argument("--prompt", "-p", required=True, help="图片描述 Prompt")
    parser.add_argument("--aspect-ratio", "-a", default="1:1", help="宽高比 (如 3:4, 16:9, 1:1)")
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--resolution", "-r", choices=["2K", "4K"], help="覆盖配置中的清晰度")
    parser.add_argument("--api-key", "-k", help="API Key（覆盖配置或环境变量）")
    parser.add_argument("--image", "-i", help="输入图片路径；传入后启用图生图 / 图片编辑")
    args = parser.parse_args()

    config = load_config(args.config)
    api_key = get_api_key(config, args.api_key)
    if not api_key:
        print("错误：未找到 API Key", file=sys.stderr)
        sys.exit(1)

    resolution = args.resolution or config.get("resolution", "2K")
    aspect_ratio = args.aspect_ratio
    valid_ratios = ["3:4", "9:16", "4:3", "16:9", "1:1"]
    if aspect_ratio not in valid_ratios:
        print(f"错误：不支持的宽高比 '{aspect_ratio}'", file=sys.stderr)
        sys.exit(1)

    width, height = SIZE_MAP[(aspect_ratio, resolution)]
    base_url = config.get("api_base_url", "https://api.vectorengine.ai").rstrip("/")
    model = config.get("model", "grok-4.2-image")
    output_path = get_output_path(config, args.output, args.prompt)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        if args.image:
            input_image = Path(args.image)
            if not input_image.exists():
                print(f"错误：输入图片不存在: {input_image}", file=sys.stderr)
                sys.exit(1)
            generate_image_edit(base_url, api_key, model, args.prompt, width, height, input_image, output_path)
        else:
            generate_text_to_image(base_url, api_key, model, args.prompt, width, height, output_path)

        full_path = output_path.resolve()
        print(f"\n图片已保存: {full_path}")
        print(f"MEDIA: {full_path}")
    except Exception as e:
        print(f"生成图片时出错: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
