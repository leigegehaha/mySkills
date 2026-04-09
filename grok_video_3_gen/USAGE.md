# Grok Video 3 Gen Usage Guide / 使用说明

## 1. Overview / 概述

**English**

`grok_video_3_gen` is a local skill for generating videos with the `grok-video-3` family through Vector Engine.

- Text to video
- Image to video
- Automatic model selection by duration
  - `6s` → `grok-video-3`
  - `10s` → `grok-video-3-10s`
  - `15s` → `grok-video-3-15s`
- Local test web app with live history

**中文**

`grok_video_3_gen` 是一个本地视频生成技能，基于 Vector Engine 的 `grok-video-3` 系列模型。

- 支持文生视频
- 支持图生视频
- 可按时长自动选择模型
  - `6秒` → `grok-video-3`
  - `10秒` → `grok-video-3-10s`
  - `15秒` → `grok-video-3-15s`
- 提供本地测试网页与实时历史记录

## 2. Skill Path / 技能路径

- Skill root / 技能根目录：`.`
- CLI script / 命令行脚本：`scripts/video-generator.js`
- Web app server / 网页服务：`webapp/server.js`

## 3. API Key Setup / API Key 配置

**English**

The API key is stored in:

- `scripts/.env`

Format:

```bash
API_KEY=your-api-key
```

**中文**

API Key 配置文件在：

- `/Users/zhangleiandhim/.agents/skills/grok_video_3_gen/scripts/.env`

格式如下：

```bash
API_KEY=your-api-key
```

## 4. CLI Usage / 命令行使用

### 4.1 Text to Video / 文生视频

```bash
node scripts/video-generator.js text "提示词" [比例] [清晰度] [时长]
```

Example / 示例：

```bash
node scripts/video-generator.js text "小猫在吃鱼" 3:2 720P 10
```

### 4.2 Image to Video / 图生视频

```bash
node scripts/video-generator.js image "图片路径或图片URL" "提示词" [比例] [清晰度] [时长]
```

Example / 示例：

```bash
node scripts/video-generator.js image "./example.png" "让人物自然转身看向镜头" 3:2 720P 6
```

### 4.3 Query Task / 查询任务

```bash
node scripts/video-generator.js query 任务ID
```

## 5. CLI Parameters / 参数说明

**English**

- Aspect ratio: `16:9`, `9:16`, `1:1`, `4:3`, `3:4`, `3:2`, `2:3`
- Size: `720P`, `1080P`
- Duration: `6`, `10`, `15`

**中文**

- 比例：`16:9`、`9:16`、`1:1`、`4:3`、`3:4`、`3:2`、`2:3`
- 清晰度：`720P`、`1080P`
- 时长：`6`、`10`、`15`

## 6. Output Files / 输出文件

**English**

Generated videos are downloaded to:

- `scripts/output/`

**中文**

生成完成后，视频会下载到：

- `/Users/zhangleiandhim/.agents/skills/grok_video_3_gen/scripts/output`

## 7. Web App Usage / 测试网页使用

### 7.1 Start the Web App / 启动测试网页

```bash
node webapp/server.js
```

Open in browser / 浏览器打开：

- `http://127.0.0.1:3784`

### 7.2 What the Web App Supports / 网页支持功能

**English**

- Text to video
- Image to video
- Local image picker
- Remote image URL
- Duration selector
- Live progress updates
- Waterfall history layout
- Reuse prompt from history
- Delete history and local output file together

**中文**

- 文生视频
- 图生视频
- 选择本地图片
- 填写远程图片 URL
- 选择视频时长
- 实时进度更新
- 瀑布流历史记录
- 从历史中一键复用提示词
- 删除历史时同步删除本地视频文件

### 7.3 Web App Data Files / 网页数据文件

- History / 历史记录：`webapp/data/history.json`
- Uploaded images / 上传图片缓存：`webapp/data/uploads/`

## 8. Notes / 注意事项

**English**

- If the model rejects a prompt, the request may fail even though the tool is working correctly.
- Large local images are uploaded through the web app and saved temporarily.
- Some prompts may be blocked by the model provider.

**中文**

- 如果提示词被模型审核拦截，即使工具本身正常，任务也可能失败。
- 网页中选择的大图会先上传并临时保存。
- 某些提示词可能会被模型提供方拦截。
