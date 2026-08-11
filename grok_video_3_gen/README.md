# Grok Video 3 Generator (lingkeai.ai)

使用 lingkeai.ai 平台的 grok-video-3 / grok-imagine-video-1.5-preview 系列视频模型，支持文生视频和图生视频。

## 快速开始

1. 复制 `.env.example` 为 `.env`，填入你的 lingkeai.ai API Key
2. 运行 `node scripts/video-generator.js text "提示词"` 生成视频

## 配置

编辑 `scripts/.env`：

```
API_KEY=sk-your-key-1,sk-your-key-2
```

支持多 key 逗号分隔，遇到 401/429/500/503 自动切换。

## 用法

```bash
cd scripts

# 文生视频
node video-generator.js text "提示词" [比例] [清晰度] [时长]

# 图生视频
node video-generator.js image "图片URL或本地路径" "提示词" [比例] [清晰度] [时长]

# 查询任务
node video-generator.js query 任务ID

# 列出可用视频模型
node video-generator.js models
```

## 参数

| 参数 | 可选值 | 默认值 |
|---|---|---|
| 比例 | 16:9, 9:16, 1:1, 4:3, 3:4, 3:2, 2:3 | 3:2 |
| 清晰度 | 720P, 1080P | 720P |
| 时长 | 6, 10, 15 秒 | 6 |

## 模型策略

| 时长 | model | 文生 | 图生 | 自带音频 |
|---|---|---|---|---|
| 6 秒 | grok-video-3 | Yes | Yes | Yes |
| 10 秒 | grok-video-3 | Yes | Yes | Yes |
| 15 秒 | grok-imagine-video-1.5-preview | No | Yes | Yes |

## Web UI

```bash
cd webapp
node server.js
# 打开 http://127.0.0.1:3784
```

## API 参考

- API base: `https://api.lingkeai.ai`
- 提交任务: `POST /v1/media/generate`
- 轮询结果: `GET /v1/media/status?task_id=<task_id>`
- 查看模型: `GET /v1/skills/models?type=video`
- 鉴权: `Authorization: Bearer <API_KEY>`
