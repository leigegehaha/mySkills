---
name: lei-bloger-av
description: End-to-end Lei blogger audio-video generation skill. Trigger this when the user wants one input稿件或文件直接输出：1) 润色后的口播文案，2) Lei 音色长语音，3) 基于口播内容自动生成的 PPT/HTML 风格讲解视频，4) 最终音视频合成结果。 Also use when the user mentions 长口播视频、配音加配图、blogger 视频生成、Lei 口播视频、语音和视频一起生成、根据文案自动出视频。
---

Use this skill when the user wants a single workflow that turns a text draft or file into:

- polished spoken script
- segmented Lei TTS audio
- PPT/HTML style visual video
- one final merged mp4

## Fixed setup

- TTS repo: `/Users/zhangleiandhim/Documents/index-tts2`
- Reuse Lei TTS scripts from: `/Users/zhangleiandhim/.codex/skills/lei-bloger-tts/scripts/`
- Default output root: `/Users/zhangleiandhim/Documents/index-tts2/outputs/lei_av`
- Main entry: `scripts/run.py`

## Workflow

1. Accept either `--text` or `--input-file`
2. Normalize and lightly oral-polish the draft
3. Split into long-form TTS segments with smooth emotions
4. Generate merged Lei wav
5. Split visuals into slower scenes (default target `5-8s`)
6. First generate an HTML page outline file for all pages
7. Build Swiss-style HTML/PPT pages from that outline with a 3-zone layout:
   - yellow zone: 一句话总结
   - red zone: 页面副标题
   - green zone: 丰富展开内容 + SVG / 品牌卡 / 说明卡
8. Render scene images, stitch video, add transition SFX, mux final mp4
9. Return:
   - polished script path
   - TTS project path
   - merged wav path
   - storyboard path
   - final mp4 path

## Command

```bash
python3 /Users/zhangleiandhim/.codex/skills/lei-bloger-av/scripts/run.py \
  --text "大家好，今天想和大家聊聊……"
```

Or:

```bash
python3 /Users/zhangleiandhim/.codex/skills/lei-bloger-av/scripts/run.py \
  --input-file /abs/path/draft.txt
```

If a matching long-form audio/project already exists and you want to skip re-synthesizing audio:

```bash
python3 /Users/zhangleiandhim/.codex/skills/lei-bloger-av/scripts/run.py \
  --input-file /abs/path/draft.txt \
  --reuse-project-file /abs/path/project.json \
  --reuse-audio-file /abs/path/full.wav
```

## Notes

- Visuals default to:
  - 真实风格
  - 红白搭配
  - 瑞士风格
  - 纯白背景
- Corner tag is fixed to `磊哥哥科技拆解室`
- Default visual scene duration strategy is slower: aim `7-10` seconds per scene
- Brand/product visuals prefer logo/wordmark cards and SVG explainer graphics, not GitHub screenshots
- The script prints progress for both audio generation and video rendering
