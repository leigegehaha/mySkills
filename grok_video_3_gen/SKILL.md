---
name: grok_video_3_gen
description: 使用 grok-video-3 系列模型生成视频，支持文生视频和图生视频；当用户提供图片时走图生视频，只有文字时走文生视频；可按 6 秒、10 秒、15 秒自动选择对应模型。
---

# Grok Video 3 Generator

## 概述

本技能使用 **grok-video-3** 系列模型通过 Vector Engine API 生成视频。

- 文生视频：根据文字提示生成视频
- 图生视频：根据图片 + 提示词生成视频
- 支持远程图片 URL，也尽量兼容本地图片文件

## 触发场景

当用户需要生成短视频时使用，例如：
- “帮我生成一段视频”
- “用这张图片生成视频”
- “文生视频：……”
- “图生视频：……”
- “用 Grok 生成视频”

## 使用流程

### 第一步：确认 API Key

默认密钥已写入 `scripts/.env`：

```bash
API_KEY=...
```

如需更换，直接编辑该文件即可。

### 第二步：运行命令

```bash
cd scripts

# 文生视频
node video-generator.js text "提示词" [比例] [清晰度] [时长]

# 图生视频（远程 URL 或本地图片路径）
node video-generator.js image "图片URL或本地路径" "提示词" [比例] [清晰度] [时长]

# 查询任务
node video-generator.js query 任务ID
```

## 命令参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| 比例 | `16:9`, `9:16`, `1:1`, `4:3`, `3:4`, `3:2`, `2:3` | `3:2` |
| 清晰度 | `720P`, `1080P` | `720P` |
| 时长 | `6`, `10`, `15` 秒 | `6` |

## 示例

```bash
# 文生视频
node video-generator.js text "小猫在吃鱼" 3:2 720P 6

# 图生视频（图片 URL）
node video-generator.js image "https://example.com/cat.png" "让小猫抬头并轻轻摆尾" 3:2 720P 10

# 图生视频（本地图片）
node video-generator.js image ./cat.png "让小猫看向镜头" 16:9 1080P 15
```

## 输出

- 任务状态会实时轮询显示
- 生成完成后自动下载到 `scripts/output/`

## 模型信息

- **模型**:
  - `grok-video-3`：6 秒
  - `grok-video-3-10s`：10 秒
  - `grok-video-3-15s`：15 秒
- **创建接口**: `https://api.vectorengine.ai/v1/video/create`
- **鉴权**: `Authorization: Bearer <token>`

## 请求格式

核心请求体如下：

```json
{
  "model": "grok-video-3-10s",
  "prompt": "小猫在吃鱼 --mode=custom",
  "aspect_ratio": "3:2",
  "size": "720P",
  "images": ["https://example.com/cat.png"]
}
```

当没有图片时，`images` 会留空并走文生视频；有图片时则走图生视频。技能会按时长自动选择对应模型：

- `6` 秒 → `grok-video-3`
- `10` 秒 → `grok-video-3-10s`
- `15` 秒 → `grok-video-3-15s`
