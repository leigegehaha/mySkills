#!/usr/bin/env python3
from __future__ import annotations
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "google-genai>=1.0.0",
#     "pillow>=10.0.0",
#     "openai>=1.0.0",
# ]
# ///
"""
Gemini Image Generator - 支持 Gemini 原生 API 和 OpenAI 兼容格式。
支持 Text-to-Image (T2I) 和 Image-to-Image (I2I) 两种模式。

Usage:
    # T2I 文生图
    uv run generate.py --config config.json --prompt "描述" --aspect-ratio "16:9"
    # I2I 图生图
    uv run generate.py --config config.json --prompt "描述" --image input.png --aspect-ratio "16:9"
"""

import argparse
import base64
import json
import os
import re
import sys
from datetime import datetime
from io import BytesIO
from pathlib import Path

# 尺寸映射表：(宽高比, 清晰度) -> (width, height)
SIZE_MAP = {
    ("3:4", "2K"): (1536, 2048),
    ("9:16", "2K"): (1152, 2048),
    ("4:3", "2K"): (2048, 1536),
    ("16:9", "2K"): (2048, 1152),
    ("1:1", "2K"): (1536, 1536),
    ("3:4", "4K"): (3072, 4096),
    ("9:16", "4K"): (2304, 4096),
    ("4:3", "4K"): (4096, 3072),
    ("16:9", "4K"): (4096, 2304),
    ("1:1", "4K"): (3072, 3072),
}


def load_config(config_path: str) -> dict:
    """加载配置文件"""
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_api_key(config: dict, provided_key: str | None) -> str | None:
    """获取 API Key：命令行参数 > config.api_key > 环境变量"""
    if provided_key:
        return provided_key
    # 优先从 config.json 的 api_key 字段读取
    config_key = config.get("api_key")
    if config_key:
        return config_key
    env_name = config.get("api_key_env", "GEMINI_API_KEY")
    return os.environ.get(env_name)


def get_output_path(config: dict, provided_output: str | None, prompt: str) -> Path:
    """生成输出文件路径"""
    if provided_output:
        return Path(provided_output)
    output_dir = config.get("output_dir", ".")
    # 从 prompt 取前 20 个字符作为文件名描述
    safe_name = "".join(c for c in prompt[:20] if c.isalnum() or c in " _-").strip()
    safe_name = safe_name.replace(" ", "_") or "image"
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    filename = f"{timestamp}-{safe_name}.png"
    return Path(output_dir) / filename


def load_input_image(image_path: str) -> tuple[bytes, str]:
    """加载输入图片，返回 (bytes, mime_type)"""
    from PIL import Image as PILImage

    path = Path(image_path)
    if not path.exists():
        print(f"错误：输入图片不存在: {image_path}", file=sys.stderr)
        sys.exit(1)

    suffix = path.suffix.lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
    }
    mime_type = mime_map.get(suffix, "image/png")

    with open(path, "rb") as f:
        image_bytes = f.read()

    # 验证图片可以被打开
    try:
        PILImage.open(BytesIO(image_bytes)).verify()
    except Exception as e:
        print(f"错误：无法读取输入图片: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"输入图片: {path.name} ({mime_type}, {len(image_bytes) / 1024:.1f} KB)")
    return image_bytes, mime_type


def generate_gemini(config: dict, api_key: str, prompt: str,
                    aspect_ratio: str, resolution: str, output_path: Path,
                    input_image: str | None = None):
    """使用 Gemini 原生 API 生成图片"""
    from google import genai
    from google.genai import types
    from PIL import Image as PILImage

    base_url = config.get("api_base_url", "https://generativelanguage.googleapis.com")
    model = config.get("model", "gemini-2.0-flash-exp-image-generation")

    # 创建客户端
    client_kwargs = {"api_key": api_key}
    # 如果用户自定义了 base_url，通过 http_options 设置
    default_url = "https://generativelanguage.googleapis.com"
    if base_url and base_url.rstrip("/") != default_url:
        client_kwargs["http_options"] = {"base_url": base_url}

    client = genai.Client(**client_kwargs)

    # 构建 prompt，加入尺寸要求
    width, height = SIZE_MAP.get((aspect_ratio, resolution), (1536, 1536))

    mode = "I2I 图生图" if input_image else "T2I 文生图"
    print(f"使用 Gemini 原生格式 ({mode})")
    print(f"模型: {model}")
    print(f"尺寸: {width}x{height} ({aspect_ratio}, {resolution})")
    print(f"正在生成图片...")

    # 构建 contents
    if input_image:
        image_bytes, mime_type = load_input_image(input_image)
        contents = [
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            types.Part.from_text(text=prompt),
        ]
    else:
        contents = prompt

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"],
            image_config=types.ImageConfig(
                image_size=resolution
            )
        )
    )

    # 处理响应
    image_saved = False
    for part in response.parts:
        if part.text is not None:
            print(f"模型回复: {part.text}")
        elif part.inline_data is not None:
            image_data = part.inline_data.data
            if isinstance(image_data, str):
                image_data = base64.b64decode(image_data)

            image = PILImage.open(BytesIO(image_data))

            # 调整到目标尺寸
            if image.size != (width, height):
                image = image.resize((width, height), PILImage.LANCZOS)

            # 保存为 PNG
            if image.mode == "RGBA":
                rgb = PILImage.new("RGB", image.size, (255, 255, 255))
                rgb.paste(image, mask=image.split()[3])
                rgb.save(str(output_path), "PNG")
            elif image.mode == "RGB":
                image.save(str(output_path), "PNG")
            else:
                image.convert("RGB").save(str(output_path), "PNG")
            image_saved = True

    if not image_saved:
        print("错误：API 未返回图片数据", file=sys.stderr)
        sys.exit(1)


def generate_openai(config: dict, api_key: str, prompt: str,
                    aspect_ratio: str, resolution: str, output_path: Path,
                    input_image: str | None = None):
    """使用 OpenAI Chat Completion 兼容格式生成图片"""
    from openai import OpenAI
    from PIL import Image as PILImage

    base_url = config.get("api_base_url", "https://generativelanguage.googleapis.com")
    model = config.get("model", "gemini-2.0-flash-exp-image-generation")

    # OpenAI 兼容格式需要 /v1 结尾的 base_url
    if not base_url.rstrip("/").endswith("/v1"):
        base_url = base_url.rstrip("/") + "/v1"

    client = OpenAI(api_key=api_key, base_url=base_url, timeout=300.0)

    width, height = SIZE_MAP.get((aspect_ratio, resolution), (1536, 1536))

    mode = "I2I 图生图" if input_image else "T2I 文生图"
    print(f"使用 OpenAI 兼容格式 ({mode})")
    print(f"Base URL: {base_url}")
    print(f"模型: {model}")
    print(f"尺寸: {width}x{height} ({aspect_ratio}, {resolution})")
    print(f"正在生成图片...")

    # 在 prompt 中嵌入尺寸信息
    size_prompt = f"{prompt}\n\nPlease generate the image in {width}x{height} resolution, aspect ratio {aspect_ratio}."

    # 构建消息内容
    if input_image:
        image_bytes, mime_type = load_input_image(input_image)
        b64_str = base64.b64encode(image_bytes).decode("utf-8")
        data_uri = f"data:{mime_type};base64,{b64_str}"
        user_content = [
            {
                "type": "image_url",
                "image_url": {"url": data_uri}
            },
            {
                "type": "text",
                "text": size_prompt
            }
        ]
    else:
        user_content = size_prompt

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": user_content
            }
        ],
        # 一些 OpenAI 兼容端点支持这些额外参数
        extra_body={
            "response_modalities": ["TEXT", "IMAGE"],
            "image_config": {
                "image_size": resolution
            }
        }
    )

    # 解析响应 - 兼容多种返回格式
    image_saved = False
    choice = response.choices[0] if response.choices else None

    if choice and choice.message:
        msg = choice.message

        # 情况1：content 是字符串（可能包含 base64）
        if isinstance(msg.content, str):
            content = msg.content
            # 尝试解析 JSON 格式的 base64 图片
            try:
                data = json.loads(content)
                if isinstance(data, dict) and "image" in data:
                    image_data = base64.b64decode(data["image"])
                    image = PILImage.open(BytesIO(image_data))
                    if image.size != (width, height):
                        image = image.resize((width, height), PILImage.LANCZOS)
                    image.convert("RGB").save(str(output_path), "PNG")
                    image_saved = True
            except (json.JSONDecodeError, Exception):
                pass

            # 情况1b：Markdown 格式 ![...](data:image/...;base64,xxxxx)
            if not image_saved:
                md_match = re.search(r'!\[.*?\]\((data:image/[^;]+;base64,([A-Za-z0-9+/=\s]+))\)', content, re.DOTALL)
                if md_match:
                    b64_data = md_match.group(2).replace("\n", "").replace(" ", "")
                    image_data = base64.b64decode(b64_data)
                    image = PILImage.open(BytesIO(image_data))
                    if image.size != (width, height):
                        image = image.resize((width, height), PILImage.LANCZOS)
                    image.convert("RGB").save(str(output_path), "PNG")
                    image_saved = True

            # 情况1c：纯 data URI（无 markdown 包裹）
            if not image_saved and "data:image/" in content:
                uri_match = re.search(r'data:image/[^;]+;base64,([A-Za-z0-9+/=\s]+)', content, re.DOTALL)
                if uri_match:
                    b64_data = uri_match.group(1).replace("\n", "").replace(" ", "")
                    image_data = base64.b64decode(b64_data)
                    image = PILImage.open(BytesIO(image_data))
                    if image.size != (width, height):
                        image = image.resize((width, height), PILImage.LANCZOS)
                    image.convert("RGB").save(str(output_path), "PNG")
                    image_saved = True

        # 情况2：content 是列表（multimodal 响应）
        if not image_saved and isinstance(msg.content, list):
            for part in msg.content:
                if isinstance(part, dict):
                    # 文本部分
                    if part.get("type") == "text":
                        print(f"模型回复: {part.get('text', '')}")
                    # 图片部分
                    elif part.get("type") == "image_url":
                        img_url = part.get("image_url", {})
                        url = img_url.get("url", "") if isinstance(img_url, dict) else str(img_url)
                        if url.startswith("data:"):
                            # data URI: data:image/png;base64,xxxxx
                            b64_data = url.split(",", 1)[1] if "," in url else url
                            image_data = base64.b64decode(b64_data)
                            image = PILImage.open(BytesIO(image_data))
                            if image.size != (width, height):
                                image = image.resize((width, height), PILImage.LANCZOS)
                            image.convert("RGB").save(str(output_path), "PNG")
                            image_saved = True
                    elif part.get("type") == "image" and "data" in part:
                        image_data = base64.b64decode(part["data"])
                        image = PILImage.open(BytesIO(image_data))
                        if image.size != (width, height):
                            image = image.resize((width, height), PILImage.LANCZOS)
                        image.convert("RGB").save(str(output_path), "PNG")
                        image_saved = True

    if not image_saved:
        # 打印原始响应帮助调试
        print(f"警告：无法从响应中提取图片", file=sys.stderr)
        if choice and choice.message:
            print(f"响应内容: {choice.message.content[:500] if choice.message.content else 'None'}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Gemini 图片生成器")
    parser.add_argument("--config", "-c", required=True, help="config.json 路径")
    parser.add_argument("--prompt", "-p", required=True, help="图片描述 Prompt")
    parser.add_argument("--aspect-ratio", "-a", default="1:1", help="宽高比 (如 3:4, 16:9, 1:1)")
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--resolution", "-r", choices=["2K", "4K"], help="覆盖配置中的清晰度")
    parser.add_argument("--api-key", "-k", help="API Key（覆盖环境变量）")
    parser.add_argument("--image", "-i", help="输入图片路径（I2I 图生图模式）")

    args = parser.parse_args()

    # 加载配置
    config = load_config(args.config)

    # 获取 API Key
    api_key = get_api_key(config, args.api_key)
    if not api_key:
        env_name = config.get("api_key_env", "GEMINI_API_KEY")
        print(f"错误：未找到 API Key", file=sys.stderr)
        print(f"请设置环境变量 {env_name} 或使用 --api-key 参数", file=sys.stderr)
        sys.exit(1)

    # 确定参数
    resolution = args.resolution or config.get("resolution", "2K")
    aspect_ratio = args.aspect_ratio
    api_format = config.get("api_format", "gemini")

    # 验证宽高比
    valid_ratios = ["3:4", "9:16", "4:3", "16:9", "1:1"]
    if aspect_ratio not in valid_ratios:
        print(f"错误：不支持的宽高比 '{aspect_ratio}'", file=sys.stderr)
        print(f"支持的宽高比: {', '.join(valid_ratios)}", file=sys.stderr)
        sys.exit(1)

    # 确定输出路径
    output_path = get_output_path(config, args.output, args.prompt)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"=" * 50)
    print(f"Gemini 图片生成器")
    print(f"=" * 50)

    try:
        if api_format == "openai":
            generate_openai(config, api_key, args.prompt, aspect_ratio, resolution, output_path, args.image)
        else:
            generate_gemini(config, api_key, args.prompt, aspect_ratio, resolution, output_path, args.image)

        full_path = output_path.resolve()
        print(f"\n图片已保存: {full_path}")
        print(f"MEDIA: {full_path}")

    except Exception as e:
        print(f"生成图片时出错: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
