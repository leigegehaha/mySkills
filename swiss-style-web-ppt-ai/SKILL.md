---
name: swiss-style-web-ppt-ai
description: Create or edit an interactive HTML PPT / webpage slide deck with one slide per HTML file and a master HTML that stitches slides together with iframes. Also use this skill when the user already has a web PPT and wants to provide a narration audio file so the skill can infer slide-switch timing automatically, record the real deck playback, and generate MP4 video plus standalone subtitles. Triggers include 网页PPT、HTML 幻灯片、交互式演示、像 PPT 一样翻页的网页、每页一个 html、总 html 用 iframe 拼接、16:9 严格排版、全屏播放、左右键切页、粒子效果、鼠标跟随、统一动画节奏、网页 PPT 转视频、根据语音自动翻页、讲解视频、配音加字幕、现有 HTML deck 导出视频。
---

# Swiss Style Web PPT AI

Use this skill to build, edit, or export an iframe-based web deck that feels like a polished presentation player instead of a static page.

## Three Modes

### 1. Create a new deck

- Distill the source into a slide outline before writing HTML.
- Scaffold the deck with `scripts/scaffold_iframe_deck.py`.
- Generate the AI illustration set early so the whole deck shares one art direction.
- Fill each slide HTML while preserving the shared visual system and interaction rules.
- Verify density, motion rhythm, and navigation behavior in the master deck.
- 图片可以用 AI 生成，但可见页面里不要出现 `AI 插图`、`AI 生成`、`placeholder` 这类制作过程提示，除非原文案本身就在讲这个主题。

### 2. Edit an existing web PPT visually

- Enable the bundled editor with:
  - `python3 /Users/zhangleiandhim/.codex/skills/swiss-style-web-ppt-ai/scripts/enable_web_ppt_editor.py --project <deck-dir> --launch --open`
- This syncs `assets/editor/` into `<deck-dir>/editor/`, starts `node editor/server.mjs`, and opens `http://127.0.0.1:4321/editor/`.
- Use this mode when the user wants to edit text, typography, layout, images, page count, or page-turn sound like a PPT editor instead of rewriting HTML by hand.
- The editor supports undo/redo, multi-select, guide lines, snapping, drag-and-resize on canvas, duplicate/new/delete page, and sound tuning.
- The preview frame stays fixed at `16:9`; the editor page itself can scroll.

### 3. Export an existing web PPT to video from narration audio

- Use this mode when the user already has a generated web PPT and now wants `mp4 + 字幕`.
- The user must provide the web PPT project directory and the narration audio file.
- Default subtitle behavior should be `soft`: the exported soft-sub video must not contain burned-in subtitles.
- The skill should:
  - transcribe the narration locally,
  - auto-read `outline.md` / `outline*.md` when the deck project contains one,
  - extract slide text from the existing HTML slides,
  - infer slide-switch timing from `audio transcript + slide content`,
  - auto-switch pages while recording the real web PPT player,
  - burn visible subtitles into the video,
  - also output an independent `captions.srt`.
- Run:
  - `python3 /Users/zhangleiandhim/.codex/skills/swiss-style-web-ppt-ai/scripts/export_web_ppt_video.py --project <deck-dir> --audio <narration.wav> --subtitle-mode soft`
- If the user already has a transcript json, reuse it:
  - `python3 /Users/zhangleiandhim/.codex/skills/swiss-style-web-ppt-ai/scripts/export_web_ppt_video.py --project <deck-dir> --audio <narration.wav> --transcript-json <transcript.json>`
- If the user also provides the original script, pass it to improve terminology correction:
  - `python3 /Users/zhangleiandhim/.codex/skills/swiss-style-web-ppt-ai/scripts/export_web_ppt_video.py --project <deck-dir> --audio <narration.wav> --script-file <script.txt>`
- If the deck has a separate outline file you want to force, pass it explicitly:
  - `python3 /Users/zhangleiandhim/.codex/skills/swiss-style-web-ppt-ai/scripts/export_web_ppt_video.py --project <deck-dir> --audio <narration.wav> --outline-file <outline.md>`
- If the user can provide the original long-form script or polished narration text, strongly prefer passing it together with the audio because it improves both subtitle terminology and page-switch inference quality.
- Subtitle mode choices:
  - `soft`: plain video + soft subtitle track + standalone `captions.srt`
  - `hard`: burned captions video only
  - `both`: plain video + soft subtitle video + hard subtitle video
  - `none`: plain video only, but still output `captions.srt`

## Default Output

- Deliver `index.html` as the master player and `slides/slide-XX.html` as the individual slides.
- Keep shared behavior in `assets/deck.js` and shared styling in `assets/deck.css`.
- Save AI illustrations as `assets/images/slide-XX.png` unless a different naming scheme is required.
- Keep every slide inside a strict 16:9 safe area; split content into more slides instead of shrinking type until it becomes weak.
- The home page must show only the title and the start button; never render a slide overview wall, thumbnail grid, or directory page on the cover.
- In video-export mode, default outputs should live under `<deck-dir>/video-export/`.

## Build Sequence

### 1. Shape the deck

- Reduce the source into 8–16 slides unless the user explicitly wants a different length.
- Put the cover only in `index.html`; do not duplicate the cover as a content slide unless the story really needs it.
- Give each slide one core claim, one visual anchor, and one clear takeaway.
- If a slide starts to feel crowded, split it. Do not rely on tiny type.

### 2. Scaffold the project

- Run:
  - `python3 /Users/zhangleiandhim/.codex/skills/swiss-style-web-ppt-ai/scripts/scaffold_iframe_deck.py --output <deck-dir> --title "<标题>" --subtitle "<副标题>" --slides <n>`
- Reuse the shared assets from `assets/base/`.
- Start from the generated templates in `assets/templates/` instead of writing the shell and each slide from scratch.

### 3. Generate images first

- Prefer pure AI illustration decks by default.
- Prefer `$gemini-image-gen`; if unavailable, fall back to `$ai-image-generation`.
- Generate the whole image set with one consistent prompt formula before fine-tuning single slides.
- Keep the series consistent in palette, framing, lens feel, perspective, lighting, and texture.
- Avoid mixing real web photos unless the user explicitly asks for mixed media.

### 4. Preserve the interaction model

- Keep the cover page minimal: visible title and start button only.
- Do not place slide thumbnails, page matrices, or overview cards on the home page.
- Let the start button enter fullscreen and reveal the deck shell.
- Use left/right keyboard navigation only.
- Do not show visible previous/next buttons.
- Keep particles, cursor follower, reveal animation, hover motion, and page-turn sound in shared JS/CSS instead of re-implementing them per slide.

### 5. Populate slides carefully

- Keep the channel chip `磊哥哥科技拆解室` at top-left on every slide unless the user overrides it.
- Use the shared `reveal`, `hover-card`, and `tilt-card` hooks for motion.
- Prefer one strong image or diagram over several weak visuals.
- If the slide is data-heavy, consider a clean SVG or info-card composition instead of adding more paragraphs.
- Keep red outline stamp labels horizontal and square to the grid; do not rotate them diagonally.
- Keep visible labels tied to the script itself; do not expose production-process copy like `AI ILLUSTRATION` unless the source explicitly talks about image generation.

### 6. Tune motion and sound centrally

- Adjust the page transition sound in `assets/deck.js` once for the whole deck.
- Prefer a low-frequency brush-like swipe sound for page changes; avoid bright clicky beeps.
- Keep transitions short, crisp, and directional; do not make them feel slow or cinematic.
- Use staggered reveals sparingly so the deck still reads like a presentation, not a landing page.

### 7. Export video carefully

- Prefer using the existing web PPT itself as the recording surface; do not rebuild slides in a separate video scene system unless the player cannot be recorded.
- Override fullscreen during automated recording so the frame stays correctly filled in `16:9`.
- Infer slide timing from the slide HTML text plus the narration transcript; do not ask the user to hand-mark every page switch unless the automatic result is clearly unusable.
- Keep the spoken content and current slide semantically aligned; when timing confidence is low, bias toward slightly later page turns instead of jumping early.
- Always output:
  - standalone subtitle file,
  - slide timeline json,
  - summary json with every generated path.
- In `soft` mode, output:
  - plain main video with no burned captions,
  - soft-sub video variant,
  - standalone subtitle file,
  - slide timeline json,
  - summary json with every generated path.
- Treat `slide_timeline.json` as the review surface when timing confidence is mixed: generate it every time, so later edits can tweak only the page-switch points without rebuilding the whole deck.
- If possible, also export a soft-sub video variant for players that support subtitle tracks.

## Resources

- `references/design-playbook.md`: history-aligned defaults, density guardrails, image-generation guidance, and QA checklist.
- `scripts/scaffold_iframe_deck.py`: create a reusable starter deck with `index.html`, `slides/`, `assets/`, and `outline.md`.
- `scripts/enable_web_ppt_editor.py`: one-step sync, launch, and open flow for the bundled visual editor.
- `scripts/export_web_ppt_video.py`: reuse an existing web PPT plus a narration audio file to infer page timing automatically and export `mp4 + srt + slide_timeline.json`.
- `assets/base/deck.css`: shared Swiss-style red/white light-theme presentation system.
- `assets/base/deck.js`: fullscreen start, iframe routing, particles, reveal replay, cursor follower, and synthesized page-turn sound.
- `assets/editor/`: bundled web PPT editor app for direct visual editing of generated decks.
- `assets/templates/index.template.html`: master player template.
- `assets/templates/slide.template.html`: single-slide template with safe layout and content-image placeholder.

## Final Checks

- Check that no slide content overflows the 16:9 viewport.
- Check that every slide still matches the master deck style.
- Check that AI illustrations read as one coherent set.
- Check that `index.html` is keyboard-driven and fullscreen start still works.
- Check that the cover remains minimal and no visible next/previous buttons were introduced.
- If editing through the bundled editor, check that the saved deck still renders correctly in both the editor preview and the standalone player.
- If exporting video, check that:
  - the recorded frame fully fills `16:9`,
  - subtitles are visible and not clipped,
  - the slide-switch timing stays aligned with the spoken content,
  - `captions.srt` and `slide_timeline.json` were both written.
