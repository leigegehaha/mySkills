# Veo Fast Video Gen Usage Guide / 使用说明

## 1. Overview / 概述

**English**

`veo_fast_video_gen` is a local skill for testing the `veo_3_1-fast-4K` model through Vector Engine.

- Text to video
- Image to video
- Local CLI workflow
- Local browser-based test app
- Live history stream with reusable prompts

**中文**

`veo_fast_video_gen` 是一个本地视频生成技能，用来测试 Vector Engine 的 `veo_3_1-fast-4K` 模型。

- 支持文生视频
- 支持图生视频
- 支持命令行方式测试
- 支持本地网页方式测试
- 支持实时历史记录与提示词复用

## 2. Skill Path / 技能路径

- Skill root / 技能根目录：`.`
- CLI script / 命令行脚本：`scripts/video-generator.js`
- Web app server / 网页服务：`webapp/server.js`

## 3. API Key Setup / API Key 配置

**English**

Set your API key in:

- `scripts/.env`

Format:

```bash
API_KEY=your-api-key
```

**中文**

请在下面的文件中配置 API Key：

- `/Users/zhangleiandhim/.agents/skills/veo_fast_video_gen/scripts/.env`

格式：

```bash
API_KEY=your-api-key
```

## 4. CLI Usage / 命令行使用

### 4.1 Text to Video / 文生视频

```bash
node scripts/video-generator.js text "提示词" [比例] [秒数]
```

Example / 示例：

```bash
node scripts/video-generator.js text "日落海滩" 9:16 8
```

### 4.2 Image to Video / 图生视频

```bash
node scripts/video-generator.js image "图片路径" "提示词" [秒数]
```

Example / 示例：

```bash
node scripts/video-generator.js image "./example.png" "让人物缓慢转身看向镜头" 5
```

### 4.3 Query Task / 查询任务

```bash
node scripts/video-generator.js query 任务ID
```

## 5. CLI Parameters / 参数说明

**English**

- Aspect ratio: `16:9`, `9:16`, `1:1`, `4:3`, `3:4`
- Duration in seconds: usually `5` to `10`

**中文**

- 比例：`16:9`、`9:16`、`1:1`、`4:3`、`3:4`
- 秒数：通常 `5` 到 `10`

## 6. Output Files / 输出文件

**English**

Generated files are saved to:

- `scripts/output/`

**中文**

生成完成后，视频会保存到：

- `/Users/zhangleiandhim/.agents/skills/veo_fast_video_gen/scripts/output`

## 7. Web App Usage / 测试网页使用

### 7.1 Start the Web App / 启动测试网页

```bash
node webapp/server.js
```

Open in browser / 浏览器打开：

- `http://127.0.0.1:3785`

### 7.2 What the Web App Supports / 网页支持功能

**English**

- Text to video
- Image to video
- Local image picker
- Remote image URL
- Aspect ratio selection
- Duration selection
- Live progress stream
- Waterfall history layout
- Reuse prompt from history
- Delete history and local output together

**中文**

- 文生视频
- 图生视频
- 选择本地图片
- 填写远程图片 URL
- 选择比例
- 选择时长
- 实时进度更新
- 瀑布流历史记录
- 从历史中一键复用提示词
- 删除历史时同步删除本地视频文件

### 7.3 Web App Data Files / 网页数据文件

- History / 历史记录：`webapp/data/history.json`
- Uploaded images / 上传图片缓存：`webapp/data/uploads/`

## 8. Notes / 注意事项

**English**

- The web app is only a local tester; it still depends on the external Veo API.
- If the API rejects a request, the UI may show a failed status.
- Uploaded local images are stored temporarily.

**中文**

- 这个网页只是本地测试面板，底层仍然依赖外部 Veo API。
- 如果 API 拒绝请求，网页里会显示失败状态。
- 网页上传的本地图片会被临时保存。
