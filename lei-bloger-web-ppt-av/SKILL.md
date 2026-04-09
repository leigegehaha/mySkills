---
name: lei-bloger-web-ppt-av
description: Turn user-provided text or files into a polished Lei blogger narration, an iframe-based interactive web PPT, and a synchronized PPT playback video where slide content matches the narration and page-switch timing follows the audio. Use when users ask for 文案转博客音频、网页 PPT、音频配 PPT 视频、根据讲稿自动出讲解视频、网页幻灯片自动配音、让 PPT 按语音内容自动翻页。
---

# Lei Blogger Web PPT AV

Use this skill when the user wants one end-to-end flow that outputs:

- Lei 风格长口播音频
- iframe 拼接的网页 PPT
- 基于真实网页 PPT 回放录制的讲解视频
- 按音频时间线自动切换上下页的最终 `mp4`

## Fixed setup

- Main entry: `scripts/run.py`
- Reuses Lei TTS skill: `/Users/zhangleiandhim/.codex/skills/lei-bloger-tts`
- Reuses Swiss deck assets and player shell from this skill bundle
- Default output root: `/Users/zhangleiandhim/Documents/index-tts2/outputs/lei_web_ppt_av`

## Workflow

1. Accept `--text` or `--input-file`
2. Extract title / subtitle if the draft contains lines like `标题为：...`、`副标题为：...`
3. Lightly oral-polish the draft into a spoken Lei blogger script
4. Split the script into long-form TTS segments with smoothed emotions
5. Generate or reuse the merged Lei narration wav
6. Build a storyboard whose scene durations follow the narration timing
7. Generate a real web PPT deck:
   - `web_ppt/index.html`
   - `web_ppt/slides/slide-XX.html`
   - `web_ppt/assets/deck.css`
   - `web_ppt/assets/deck.js`
   - `web_ppt/assets/images/slide-XX.(png|svg)`
8. Record the actual deck playback with Playwright, and switch slides by keyboard according to the audio timeline
9. Add page-turn sound FX and mux the recorded PPT playback with the narration
10. Return the full artifact set plus a summary json

## Output contract

The pipeline writes:

- `source.txt`
- `polished_script.txt`
- `polished_segments.md`
- `tts_project.json`
- `lei_audio.wav`
- `lei_audio_with_sfx.wav`
- `storyboard.json`
- `captions.srt`
- `web_ppt/`
- `slides_manifest.json`
- `final_video.mp4`
- `summary.json`

## Command

```bash
python3 /Users/zhangleiandhim/.codex/skills/lei-bloger-web-ppt-av/scripts/run.py \
  --text "大家好，今天想和大家聊聊……"
```

```bash
python3 /Users/zhangleiandhim/.codex/skills/lei-bloger-web-ppt-av/scripts/run.py \
  --input-file /abs/path/draft.md
```

If you already have a project file or merged audio:

```bash
python3 /Users/zhangleiandhim/.codex/skills/lei-bloger-web-ppt-av/scripts/run.py \
  --input-file /abs/path/draft.md \
  --reuse-project-file /abs/path/project.json \
  --reuse-audio-file /abs/path/full.wav
```

For quick smoke tests:

```bash
python3 /Users/zhangleiandhim/.codex/skills/lei-bloger-web-ppt-av/scripts/run.py \
  --text "这是一段简短测试文案。" \
  --skip-tts
```

## Visual rules

- Cover page only shows title + start button
- Each slide stays inside strict `16:9`
- Each slide keeps the top-left channel chip `磊哥哥科技拆解室`
- Visible copy must stay tied to the source script; do not expose production-process labels such as `AI 插图` or `placeholder`
- Default image mode is `auto`: try Gemini image generation first when available, otherwise fall back to unified SVG illustrations
- Use left/right keyboard navigation in the player; no visible prev/next buttons

## Timing contract

- Slide timing is derived from the narration audio
- If per-segment wav files exist, use their actual durations first
- Scene splitting happens inside each segment, so the visual page switches stay aligned with the spoken content
- The final video is recorded from the real deck playback, not from a separate mock scene renderer

## Editing follow-up

If the user wants to fine-edit the generated web PPT like editing a normal PPT, enable the editor from `$swiss-style-web-ppt-ai`:

```bash
python3 /Users/zhangleiandhim/.codex/skills/swiss-style-web-ppt-ai/scripts/enable_web_ppt_editor.py \
  --project /abs/path/to/web_ppt \
  --launch \
  --open
```

## Notes

- If deck recording fails, the script falls back to slide preview stills and still outputs a video
- `summary.json` is the best handoff artifact because it contains every generated path
