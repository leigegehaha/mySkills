---
name: photo_scene_video_gen
description: 根据用户提供的人像照片和场景描述，先生成高一致性人物图片，再生成对应短视频；适合“给你一张脸图 + 一个场景/台词/镜头要求，你帮我把人物做出来并动起来”的场景，支持普通镜头、手机自拍视频、固定机位、后置机位等风格。
---

# Photo Scene Video Generator

这个技能用于把“用户提供的人像照片 + 场景描述”转换成：

1. 一张高人物一致性的关键帧图片
2. 一段基于关键帧生成的短视频

优先复用已有技能：

- 图片阶段：`gemini-image-gen`
- 视频阶段：`grok_video_3_gen`

其中：

- 当前技能目录可记为 `{baseDir}`
- `gemini-image-gen` 技能目录可记为 `{geminiSkillDir}`
- `grok_video_3_gen` 技能目录可记为 `{grokVideoSkillDir}`

## 何时使用

当用户的需求类似下面这些情况时使用：

- “我给你一张人脸，帮我生成某个场景里的图和视频”
- “让这个人出现在某个场景中，并说一段台词”
- “先出图，再让图动起来”
- “做成自拍视角 / 手机后置拍摄 / 固定机位”

## 输入要素

尽量从用户那里确认这些信息：

- 人像图片路径
- 场景描述
- 人物动作
- 台词
- 视频比例，默认 `9:16`
- 视频时长，默认 `6` 秒
- 镜头风格：自拍 / 后置拍摄 / 固定机位 / 电影感

如果用户没有说清楚，按下面默认值执行：

- 比例：`9:16`
- 时长：`6` 秒
- 清晰度：`720P`
- 先生成关键帧，再做图生视频

## 工作流程

### 第一步：整理图片提示词

先根据用户的人像和场景，生成一个适合 `gemini-image-gen` 的图片提示词。

要求：

- 明确“使用提供的人脸作为身份参考”
- 明确场景、服装、动作、构图、光线
- 强调人物外观一致性
- 不要字幕，不要文字水印

如果用户要求手机自拍视频：

- 在图片提示词最前面加上：
  - `这是一张iPhone前置摄像头拍摄的自拍照片儿。`
- 同时强调：
  - 前置自拍视角
  - 手持自拍
  - 近距离构图
  - 轻微广角前置镜头感
  - 画面边缘可隐约看到手 / 手腕 / 前臂
  - 不能像第三人称拍摄

如果用户要求固定机位或后置机位，则明确写出：

- fixed smartphone rear camera
- tripod / stand
- not a selfie frame

### 第二步：用 `gemini-image-gen` 生成关键帧

参考命令：

```bash
uv run {geminiSkillDir}/scripts/generate.py \
  --config {geminiSkillDir}/config.json \
  --prompt "图片提示词" \
  --image "/path/to/face.png" \
  --aspect-ratio "9:16" \
  --output "<output-image-path>"
```

执行完成后，记录输出图片路径，并在对话中展示图片。

### 第三步：整理视频提示词

基于关键帧，再生成适合 `grok_video_3_gen` 的视频提示词。

要求：

- 明确人物要保持和参考图一致
- 明确动作、镜头、环境变化
- 如果有台词，直接写明 spoken line
- 强调自然口型、无字幕
- 如果是自拍，要求全程保持自拍视角不切机位

自拍视频建议加入这些硬约束：

- `The same woman is holding the phone herself for the entire clip.`
- `Keep true selfie perspective from start to end.`
- `Never switch to third-person view.`
- `Keep part of her hand, wrist, or forearm subtly visible near the edge of frame throughout.`

### 第四步：用 `grok_video_3_gen` 生成视频

参考命令：

```bash
cd {grokVideoSkillDir}/scripts
node video-generator.js image "/path/to/keyframe.png" "视频提示词" 9:16 720P 6
```

说明：

- `6` 秒 → `grok-video-3`
- `10` 秒 → `grok-video-3-10s`
- `15` 秒 → `grok-video-3-15s`

视频完成后会自动下载到 `grok_video_3_gen` 技能的 `scripts/output/` 目录。

## 输出要求

最终至少返回给用户：

- 关键帧图片路径
- 最终视频路径
- 使用的核心图片提示词
- 使用的核心视频提示词

如果用户明确要求统计时间，则记录：

- 开始执行时间
- 结束时间
- 总耗时（秒）

## 提示词策略

- 先保人物一致性，再保场景细节
- 自拍类需求优先强化“机位一致性”
- 如果自拍视频容易漂移成第三人称，优先减少花哨描述，保留最核心自拍约束
- 如果上游报错或拥塞，可缩短视频提示词后重试一次

## 参考模板

需要不同镜头风格时，读取：

- `references/prompt_templates.md`
