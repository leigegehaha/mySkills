---
name: gemini-image-gen
description: |
  通过 API 调用 Gemini 图片生成模型，根据用户 Prompt 生成高质量图片。
  支持 Gemini 原生 API 格式和 OpenAI Chat Completion 兼容格式。
  支持 Text-to-Image (T2I) 文生图和 Image-to-Image (I2I) 图生图两种模式。
  可配置 API 地址、模型名称、API Key、清晰度(2K/4K)、输出目录。
  当用户想要使用 Gemini 生成图片、AI 绘图、文生图、图生图时使用此技能。
  触发词：gemini 生图、gemini 图片、AI 画图、生成图片、文生图、图生图、以图生图、图片编辑、gemini image、generate image with gemini、image to image。
---

# Gemini 图片生成

通过 Gemini API 生成高质量图片，支持 T2I 文生图和 I2I 图生图两种模式。

## 配置

配置文件位于 skill 目录下的 `config.json`，包含以下字段：

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `api_base_url` | API 基础地址 | `https://generativelanguage.googleapis.com` |
| `api_key_env` | API Key 环境变量名 | `GEMINI_API_KEY` |
| `model` | 模型名称 | `gemini-2.0-flash-exp-image-generation` |
| `api_format` | API 格式：`gemini` 或 `openai` | `gemini` |
| `resolution` | 清晰度：`2K` 或 `4K` | `2K` |
| `output_dir` | 图片输出目录 | `.`（当前工作目录） |

用户首次使用前需要设置 API Key 环境变量：

```bash
export GEMINI_API_KEY="your-api-key-here"
```

如需修改配置，直接编辑 config.json 即可。

## 工作流程

### T2I 文生图

当用户请求生成图片时，按以下步骤执行：

1. 读取 config.json 获取配置
2. 确认用户的 Prompt 内容
3. 如果用户没有指定图片尺寸比例，使用 AskUserQuestion 让用户选择：
   - 3:4（竖版，适合人像/海报）
   - 9:16（竖版，适合手机壁纸/短视频封面）
   - 4:3（横版，适合风景/展示）
   - 16:9（横版，适合桌面壁纸/Banner）
   - 1:1（方形，适合头像/社交媒体）
4. 生成带时间戳的文件名，格式：`yyyy-mm-dd-HH-MM-SS-描述.png`
5. 调用脚本生成图片
6. 生成完成后，使用 Read 工具读取图片文件，在对话中直接展示给用户

### I2I 图生图

当用户提供了一张图片（附件、粘贴、或指定路径）并要求基于该图片生成新图片时：

1. 读取 config.json 获取配置
2. 确认用户提供的输入图片路径（用户可能通过附件上传、粘贴、或直接给出文件路径）
3. 确认用户的 Prompt 内容（描述希望对图片做什么修改/变换）
4. 如果用户没有指定图片尺寸比例，使用 AskUserQuestion 让用户选择（同 T2I）
5. 生成带时间戳的文件名
6. 调用脚本，传入 `--image` 参数指定输入图片路径
7. 生成完成后，使用 Read 工具读取图片文件，在对话中直接展示给用户

## 使用方法

### T2I 文生图

读取配置后，运行脚本：

```bash
uv run {baseDir}/scripts/generate.py \
  --config {baseDir}/config.json \
  --prompt "用户的图片描述" \
  --aspect-ratio "16:9" \
  --output "/输出目录/2026-03-08-19-51-18-描述.png"
```

### I2I 图生图

传入 `--image` 参数指定输入图片：

```bash
uv run {baseDir}/scripts/generate.py \
  --config {baseDir}/config.json \
  --prompt "将这张照片转换为水彩画风格" \
  --image "/path/to/input-image.png" \
  --aspect-ratio "16:9" \
  --output "/输出目录/2026-03-08-19-51-18-描述.png"
```

### 参数说明

| 参数 | 必需 | 说明 |
|------|------|------|
| `--config` | 是 | config.json 路径 |
| `--prompt` | 是 | 图片描述 Prompt |
| `--image` | 否 | 输入图片路径（传入则为 I2I 模式，支持 png/jpg/jpeg/webp/gif/bmp） |
| `--aspect-ratio` | 否 | 宽高比，如 `3:4`、`16:9`、`1:1` 等 |
| `--output` | 否 | 输出文件路径（默认使用 config 中的 output_dir） |
| `--resolution` | 否 | 覆盖 config 中的清晰度设置 |
| `--api-key` | 否 | 直接传入 API Key（覆盖环境变量） |

### 尺寸比例对应的像素

2K 清晰度：
- 3:4 → 1536x2048
- 9:16 → 1152x2048
- 4:3 → 2048x1536
- 16:9 → 2048x1152
- 1:1 → 1536x1536

4K 清晰度：
- 3:4 → 3072x4096
- 9:16 → 2304x4096
- 4:3 → 4096x3072
- 16:9 → 4096x2304
- 1:1 → 3072x3072

## 注意事项

- 脚本使用 `uv run` 执行，自动管理 Python 依赖，无需手动安装
- 生成完成后脚本会输出 `MEDIA: /path/to/image.png`，表示图片已保存
- 生成图片后，使用 Read 工具读取该图片文件路径，这样图片会直接显示在对话中
- 如果 API 调用失败，检查 API Key 是否正确、网络是否可达
- OpenAI 格式需要确保 base_url 指向支持图片生成的兼容端点
- I2I 模式支持 png、jpg、jpeg、webp、gif、bmp 格式的输入图片
- I2I 模式下，用户提供的图片可能来自附件上传、粘贴到对话、或直接指定文件路径，需要正确获取图片的本地路径
