---
name: soulx-single-podcast
description: Polish user-provided text or extracted document content into a natural single-speaker SoulX podcast script, then synthesize long-form audio with a reference voice. Use when the user wants 单人口播、AI 播客、长文口播、文案润色后配音, or asks to generate Chinese or English podcast audio from a draft, note, txt, or markdown file.
---

Use this skill when the user wants a **single-host podcast** generated with the local `SoulX-Podcast` project.

This skill is for:

- raw text → 口语化润色 → 单人口播音频
- `.txt` / `.md` content → 口播稿 → 音频
- 中文或英文单人口播
- 长文自动分段合成并合并成一条 `wav`

This skill is **not** for:

- 多人播客
- 方言播客
- API service work

If the source file is `.pdf` or `.docx`, first use [$pdf](/Users/zhangleiandhim/.codex/skills/pdf/SKILL.md) or [$docx](/Users/zhangleiandhim/.codex/skills/docx/SKILL.md) to extract plain text, then continue with this skill.

## Fixed setup

- SoulX repo: `/Users/zhangleiandhim/Documents/lmd_data_root/apps/soulx-podcast`
- Main script: `scripts/generate_podcast.py`
- Prep script: `scripts/prepare_script.py`
- Config: `config.json`
- Output root: `outputs/soulx-podcast/`
- Reference voices live in `assets/`

## Workflow

1. Determine the source:
   - direct text from the user
   - or text extracted from a local document
2. Decide:
   - `language`: `zh` or `en`
   - `oralization_degree`: `0.0` to `1.0`
   - `speed_rate`: speech speed factor, default `1.0`
   - long text chunk size: use default config or pass `--max-chars`
3. Run `scripts/generate_podcast.py`
4. Return:
   - polished script path
   - segments manifest path
   - final merged `wav` path

## Oralization guidance

`oralization_degree` controls how “spoken” the script becomes:

- `0.2` to `0.4`: light polish, fewer fillers, fewer pauses
- `0.5` to `0.7`: balanced podcast tone
- `0.8` to `1.0`: stronger conversational style, more fillers, more pauses, and more paralinguistic tags

In practice, a higher `oralization_degree` makes the script:

- more conversational and less written
- more likely to add fillers
- more likely to add pause punctuation and stronger sentence breaks
- more likely to insert sparse paralinguistic tags in suitable contexts

## Speed control

SoulX local CLI does not expose a native speech-rate parameter in the current repo.

This skill adds a **post-processing speed control**:

- `speed_rate = 1.0`: unchanged
- `speed_rate > 1.0`: faster
- `speed_rate < 1.0`: slower

Recommended range:

- `0.9` to `1.15`

Use larger changes cautiously because strong time-stretching can reduce naturalness.

Default behavior:

- add spoken transitions
- shorten overly written phrasing
- insert moderate pauses with punctuation
- add filler words conservatively at low settings
- at higher `oralization_degree`, increase:
  - ordinary spoken fillers
  - pause punctuation
  - paralinguistic tags

Supported paralinguistic tags from the local SoulX usage notes:

- `<|laughter|>`
- `<|sigh|>`
- `<|breathing|>`
- `<|coughing|>`

Do **not** overuse these tags. Prefer ordinary spoken fillers first:

- Chinese: `嗯`, `啊`, `就是`, `其实`, `你会发现`
- English: `well`, `honestly`, `basically`, `you know`, `the thing is`

For Chinese scripts containing English brand or product names, this skill also adds more suitable pause punctuation so mixed-language reading sounds smoother and more natural. This is especially useful for names such as `OpenClaw`, `Workbuddy`, `Agent`, `MCP`, `Windows`, `Mac`, `Linux`, `VLM`, and similar mixed-language terms.

## Long-form segmentation

This skill supports long-form podcast generation by:

- polishing the full draft first
- splitting the polished script into multiple speaking segments
- synthesizing each segment separately
- merging all segment wavs into one `final.wav`

Tested guidance from the local SoulX workflow:

- short Chinese drafts: default chunking is fine
- long Chinese drafts: prefer a larger chunk size to avoid over-segmentation
- a practical range is `320` to `420` chars per segment
- `--max-chars 420` works better for long Chinese commentary-style podcasts

If the script is too fragmented, synthesis becomes much slower because each segment runs a separate `cli/tts.py` inference.

## Commands

Simple example:

```bash
python3 /Users/zhangleiandhim/.codex/skills/soulx-single-podcast/scripts/generate_podcast.py \
  --text "大家好，今天想聊聊 AI 智能体。" \
  --language zh \
  --oralization-degree 0.7 \
  --speed-rate 1.08
```

Long Chinese example with stronger oralization and larger chunks:

```bash
python3 /Users/zhangleiandhim/.codex/skills/soulx-single-podcast/scripts/generate_podcast.py \
  --text "大家好，今天想聊聊 OpenClaw 和 AI 智能体的发展。" \
  --language zh \
  --oralization-degree 0.9 \
  --speed-rate 1.1 \
  --max-chars 420 \
  --reference-id zhanglei-xunfei
```

Markdown input:

```bash
python3 /Users/zhangleiandhim/.codex/skills/soulx-single-podcast/scripts/generate_podcast.py \
  --input-file /abs/path/draft.md \
  --language en \
  --reference-id zhanglei-xunfei
```

Dry run:

```bash
python3 /Users/zhangleiandhim/.codex/skills/soulx-single-podcast/scripts/generate_podcast.py \
  --text "Test draft" \
  --dry-run
```

## Output contract

Each run creates one timestamped job folder under:

- `/Users/zhangleiandhim/.codex/skills/soulx-single-podcast/outputs/soulx-podcast`

Typical outputs:

- `polished.txt`
- `segments.json`
- `segment_01.txt`
- `segment_01.wav`
- `final.wav`
- `manifest.json`

## References

Read when needed:

- `references/soulx-notes.md` for SoulX-specific behavior
