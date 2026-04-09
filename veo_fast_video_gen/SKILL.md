---
name: veo_fast_video_gen
description: 使用 veo_3_1-fast-4K 模型快速生成视频，支持文生视频和图生视频。
---

# Veo Fast Video Generator

## 概述

本技能使用 **veo_3_1-fast-4K** 模型通过 Vector Engine API 快速生成视频。

- 文生视频：根据文字描述生成视频
- 图生视频：根据图片生成动态视频

## 触发场景

当用户需要生成短视频时使用，例如：
- "帮我生成一段视频"
- "用这张图片生成视频"
- "文生视频：..."

## 使用流程

### 第一步：配置 API Key

在 `scripts/.env` 文件中配置：
```
API_KEY=your-api-key-here
```

### 第二步：运行命令

```bash
cd scripts

# 文生视频
node video-generator.js text "提示词" [比例] [秒数]

# 图生视频
node video-generator.js image "图片路径" "提示词" [秒数]

# 查询任务
node video-generator.js query video_xxx
```

## 命令参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| 比例 | 16:9, 9:16, 1:1, 4:3, 3:4 | 16:9 |
| 秒数 | 视频时长 | 5 |

## 示例

```bash
# 文生视频 - 5秒 16:9
node video-generator.js text "一只可爱的猫在草地上奔跑"

# 文生视频 - 8秒 9:16
node video-generator.js text "日落海滩" 9:16 8

# 图生视频
node video-generator.js image ./photo.png "让图片动起来" 5
```

## 输出

生成的视频保存在 `scripts/output/` 目录。

## 模型信息

- **模型**: veo_3_1-fast-4K
- **API**: https://api.vectorengine.ai/v1/videos
