---
name: grok-image-gen
description: |
  通过 VectorEngine 的图片生成接口调用 Grok 模型生成图片，根据用户 Prompt 生成高质量图片。
  使用模型 `grok-4.2-image`，支持文生图（T2I）以及图生图 / 图片编辑（I2I / Edits）。
  可配置 API 地址、模型名称、API Key、清晰度(2K/4K)、输出目录。
  当用户想要使用 Grok 生成图片、Grok 生图、AI 画图、生成图片、文生图时使用此技能。
  触发词：grok 生图、grok 图片、grok image、generate image with grok、AI 画图、生成图片、文生图。
---

# Grok 图片生成

通过 VectorEngine 图片接口使用 `grok-4.2-image` 模型生成图片。

## 配置

配置文件位于 skill 目录下的 `config.json`。

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `api_base_url` | API 基础地址 | `https://api.vectorengine.ai` |
| `api_key_env` | API Key 环境变量名 | `GROK_IMAGE_API_KEY` |
| `model` | 模型名称 | `grok-4.2-image` |
| `api_format` | API 请求格式 | `images` |
| `resolution` | 清晰度：`2K` 或 `4K` | `2K` |
| `output_dir` | 图片输出目录 | `.` |

## 工作流程

### T2I 文生图

1. 读取 `config.json`
2. 确认用户 Prompt
3. 如果用户没有指定图片尺寸比例，让用户选择：
   - `3:4`
   - `9:16`
   - `4:3`
   - `16:9`
   - `1:1`
4. 生成带时间戳的输出文件名
5. 调用脚本生成图片
6. 生成完成后，使用 Read 工具读取图片文件并展示给用户

## 使用方法

### T2I 文生图

```bash
uv run {baseDir}/scripts/generate.py \
  --config {baseDir}/config.json \
  --prompt "用户的图片描述" \
  --aspect-ratio "1:1" \
  --output "/输出目录/2026-03-16-16-36-00-image.png"
```

### I2I 图生图 / 图片编辑

```bash
uv run {baseDir}/scripts/generate.py \
  --config {baseDir}/config.json \
  --prompt "加一只小鸭" \
  --image "/path/to/input.png" \
  --aspect-ratio "3:4" \
  --output "/输出目录/2026-03-16-16-36-00-edit.png"
```

## Web 测试页

已提供一个前端测试页：`assets/web-demo/index.html`

功能：
- 编辑 Prompt
- 填写 API Key
- 选择比例与模型
- 直接向 `POST /v1/images/generations` 发送请求
- 生成完成后自动把图片加载到页面
- 使用 `localStorage` 保存历史记录
- 以流式卡片瀑布流方式展示历史图片

## 注意事项

- 当前技能按 `images/generations` 接口生成图片
- 请求体核心字段为：`model`、`prompt`、`size`
- 生成完成后脚本会输出 `MEDIA: /path/to/image.png`
- 这是独立的 Grok 生图技能，不影响原 `gemini-image-gen`
