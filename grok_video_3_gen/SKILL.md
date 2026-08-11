---
name: grok_video_3_gen
description: 使用 lingkeai.ai 平台的 grok-video-3 / grok-imagine-video-1.5-preview (display: grok-video-3.5) 系列视频模型，支持文生视频和图生视频；默认使用 grok-video-3（6s/10s），仅当用户明确要求 15 秒长视频时才切换到 grok-imagine-video-1.5-preview（后者仅支持图生）。
---

# Grok Video 3 Generator (lingkeai.ai)

## 概述

本技能使用 **lingkeai.ai** 平台的 Grok 系列视频模型生成视频。

- **API base**: `https://api.lingkeai.ai`
- **提交任务**: `POST /v1/media/generate`
- **轮询结果**: `GET /v1/media/status?task_id=<task_id>`
- **查看模型**: `GET /v1/skills/models?type=video`
- **鉴权**: `Authorization: Bearer <API_KEY>`

支持文生视频（t2v）和图生视频（i2v），所有视频自带音频，1280×720 / 24fps / MP4。

## 默认模型策略

**默认使用 `grok-video-3`**（支持文生+图生，6s/10s，720P，¥0.6864/次）。

仅当用户**明确要求 15 秒长视频**时，才切换到 `grok-imagine-video-1.5-preview`（display: grok-video-3.5，仅图生，¥1.716/次，必须传首帧参考图）。

触发技能时的默认行为：
- 用户没指定时长 → 6 秒 + `grok-video-3`
- 用户指定 6s 或 10s → `grok-video-3`
- 用户指定 15s → `grok-imagine-video-1.5-preview`（必须传图，否则报错）

## 触发场景

当用户需要生成短视频时使用，例如：
- "帮我生成一段视频"
- "用这张图片生成视频"
- "文生视频：……"
- "图生视频：……"
- "用 Grok 生成视频"

## 模型策略

按时长自动选择模型：

| 时长 | model 字段 | display_name | 文生 | 图生 | 自带音频 |
|---|---|---|---|---|---|
| 6 秒 | `grok-video-3` | grok-video-3 | ✅ | ✅ | ✅ |
| 10 秒 | `grok-video-3` | grok-video-3 | ✅ | ✅ | ✅ |
| 15 秒 | `grok-imagine-video-1.5-preview` | **grok-video-3.5** | ❌ | ✅ | ✅ |

**重要**：
- 提交任务时 `model` 字段必须用真实 ID（如 `grok-imagine-video-1.5-preview`），display_name（`grok-video-3.5`）只是给用户看的中文名
- `grok-imagine-video-1.5-preview` **仅支持图生视频**，必须传 `images` 字段（至少 1 张）
- `grok-video-3` 文生+图生都支持

## 使用流程

### 第一步：确认 API Key

密钥在 `scripts/.env`（支持多个 key 逗号分隔自动轮询）：

```bash
API_KEY=sk-xxx,sk-yyy
```

如需更换，直接编辑该文件。

### 第二步：运行命令

```bash
cd scripts

# 文生视频
node video-generator.js text "提示词" [比例] [清晰度] [时长]

# 图生视频（远程 URL 或本地图片）
node video-generator.js image "图片URL或本地路径" "提示词" [比例] [清晰度] [时长]

# 查询任务
node video-generator.js query 任务ID

# 列出可用视频模型
node video-generator.js models
```

## 命令参数

| 参数 | 可选值 | 默认值 |
|---|---|---|
| 比例 | `16:9`, `9:16`, `1:1`, `4:3`, `3:4`, `3:2`, `2:3` | `3:2` |
| 清晰度 | `720P`, `1080P` | `720P` |
| 时长 | `6`, `10`, `15` 秒 | `6` |

## 示例

```bash
# 文生视频（6s, grok-video-3）
node video-generator.js text "小猫在阳光下吃鱼" 3:2 720P 6

# 图生视频 - 远程 URL（6s, grok-video-3）
node video-generator.js image "https://example.com/cat.png" "让小猫抬头并轻轻摆尾" 3:2 720P 6

# 图生视频 - 本地图片（10s, grok-video-3）
node video-generator.js image ./cat.png "让小猫自然地走向镜头" 16:9 720P 10

# 图生视频 - 本地图片（15s, grok-imagine-video-1.5-preview）
node video-generator.js image ./cat.png "小猫在草地上自由奔跑 15 秒" 3:2 720P 15

# 查询任务
node video-generator.js query 94758701

# 列出视频模型
node video-generator.js models
```

## 请求格式

```json
{
  "model": "grok-video-3",
  "prompt": "小猫在阳光下吃鱼",
  "aspect_ratio": "3:2",
  "size": "720P",
  "seconds": 6,
  "images": []
}
```

- 文生视频：`images` 留空 `[]`
- 图生视频：`images` 传 URL 数组（远程 `https://...` 或本地 `data:image/...;base64,...`）

## 响应格式

提交任务响应（code=200 表示业务成功）：

```json
{
  "code": 200,
  "data": {
    "task_id": 94758701,
    "task_ids": [94758701],
    "任务ids": [94758701],
    "对话组ID": "group_xxx_xxx_xxx",
    "成功数量": 1
  },
  "msg": "任务创建成功"
}
```

轮询响应：

```json
{
  "code": 200,
  "data": {
    "task_id": 94758701,
    "state": "success",       // pending | processing | success | failed
    "status": "已完成",
    "status_group": "已完成",
    "progress": "100",
    "result_url": "https://cos.lingkeai.vip/uploads/.../xxx.mp4",
    "cost": 0.6864,            // 本次消耗（元）
    "is_final": true,
    "error": ""
  }
}
```

`task_id` 是**纯数字**（如 `94758701`），不是 UUID。

## 输出

- 任务状态实时轮询显示（每 5s）
- 生成完成后自动下载到 `scripts/output/grok-video-<task_id>.mp4`
- 视频会从 `cos.lingkeai.vip` CDN 下载（**有时效**，尽快用）

## 平台特点

1. **响应快**：实测 6s 视频约 60-120s 出结果（比 vectorengine.ai 快很多）
2. **自带音频**：所有视频均含 AAC 音频轨（grok-video-3.5 采样率 48kHz，比 grok-video-3 的 44.1kHz 更高）
3. **任务 ID 是数字**：轮询时用 `?task_id=94758701`，不是 `/v1/video/<uuid>`
4. **结果 CDN**：`cos.lingkeai.vip`，**有时效**（建议生成后立即用）
5. **多 key 轮询**：`.env` 支持多个 key 逗号分隔，遇到 401/429/500/503 自动切换
6. **业务码与 HTTP 双判断**：必须 `HTTP 2xx` 且 `response.code == 200` 才算成功

## 平台可靠性 & 错误处理

lingkeai 整体可用性较好（2026-08-05 实测 100% 成功），但仍有以下注意事项：

| 错误 | 含义 | 处理 |
|---|---|---|
| `code != 200` + `msg` 包含"模型不可用" | 后端渠道问题 | 切换 key 重试或换模型 |
| `HTTP 429` | 限流 | 脚本自动切换 key，3s 后重试 |
| `HTTP 401` | 鉴权失败 | 脚本自动切换 key 重试 |
| `state=failed` + `error` 字段 | 内容审核拦截 | 换 prompt 或换图片 |

**重要原则**：如果某模型 5 分钟内一直 pending 不动，可能上游排队。超过 10 分钟还在 `state=pending/processing` 且 `progress=0` 时，建议放弃此任务（脚本默认 15 分钟超时）。

## 注意事项

- **本地图片 base64**：不要把 base64 作为命令行参数传递（`Argument list too long`）。脚本内部已用 `fs.readFileSync` 处理。
- **远程图片 URL**：必须能被 lingkeai 后端访问（公网可访问的图片），如 `picsum.photos`、自有 CDN、对象存储公开链接。
- **grok-imagine-video-1.5-preview 强制图生**：传空 `images` 会直接报错，必须提供至少 1 张首帧参考图。
- **结果 URL 有效期**：`cos.lingkeai.vip` 的下载链接有有效期，生成后请尽快下载。
- **轮询频率**：脚本默认 5s 一次，足够用，不必调高。
- **图片 base64 命令行限制**：3MB 图片的 base64 (~4MB 字符串) 会触发 `Argument list too long`。始终用脚本处理本地图片。
