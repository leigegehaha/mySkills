---
name: lei-bloger-tts
description: Default skill for Lei long-form blogger TTS. Trigger this when the user mentions `lei-bloger-tts`, wants Lei voice / Lei 配音 / 用 lei 的声音生成语音, asks for a long spoken-style narration, wants a draft polished into口播文案, needs pauses/断句/语气词 added, wants emotion-arc segmentation with smooth per-segment emotion parameters, or wants all segments merged into one final long-form wav. Outputs should be saved under the repository path `outputs/lei/`.
---

Use this skill when the user wants TTS generated in Lei's voice.

如果用户要做“长文稿口播”，按下面的长流程执行；不要直接把原始书面文案硬丢给 TTS。

## Fixed setup

- Repository: `/Users/zhangleiandhim/Documents/index-tts2`
- Reference audio: `/Users/zhangleiandhim/Documents/audio record from Xunfei/1773672171371/1773672171371.wav`
- Output directory: `/Users/zhangleiandhim/Documents/index-tts2/outputs/lei`
- Main entry: `scripts/synthesize.py`
- Project entry: `scripts/synthesize_project.py`
- Project scaffold: `scripts/scaffold_long_form_project.py`
- Emotion config: `emotion_config.json`
- Long-form workflow reference: `references/long-form-oral-workflow.md`

## Workflow

1. Confirm the target text to synthesize.
2. Run the bundled script:

```bash
python3 /Users/zhangleiandhim/.codex/skills/lei-bloger-tts/scripts/synthesize.py --text "你好，这是一段 lei 音色测试。"
```

3. Return the generated file path to the user.

## Long Form Oral Workflow

适用于用户要：

- 把长文稿改成口播文案
- 增加断句、停顿、语气词
- 按情绪起伏分段
- 给每段设置不同情绪
- 最后拼接成完整长音频

先读：`references/long-form-oral-workflow.md`

推荐流程：

1. 先把原始文案润色成口语版
2. 用 `## 标题` 或 `01｜标题` 形式整理成分段稿
3. 保存为 `*_segments.txt`
4. 运行 `scripts/scaffold_long_form_project.py` 生成第一版 `*_project.json`
5. 视内容微调每段 `emotion`
6. 运行 `scripts/synthesize_project.py`
7. 返回：
   - 润色文案路径
   - project 路径
   - 最终 `wav` 路径

示例：

```bash
python3 /Users/zhangleiandhim/.codex/skills/lei-bloger-tts/scripts/scaffold_long_form_project.py \
  --input /Users/zhangleiandhim/Documents/index-tts2/outputs/lei/openclaw_polished_segments_v2.txt \
  --output /Users/zhangleiandhim/Documents/index-tts2/outputs/lei/openclaw_polished_segments_v2_project.json
```

```bash
python3 /Users/zhangleiandhim/.codex/skills/lei-bloger-tts/scripts/synthesize_project.py \
  --project-file /Users/zhangleiandhim/Documents/index-tts2/outputs/lei/openclaw_polished_segments_v2_project.json
```

## Long Text

- 现在支持长文稿自动分段、逐段生成、最后自动拼接成一个完整 `wav`
- 默认每段按 `180` 个字符左右切分，可用 `--max-chars-per-chunk` 调整
- 如需保留中间分段文件，可加 `--keep-segments`

示例：

```bash
python3 /Users/zhangleiandhim/.codex/skills/lei-bloger-tts/scripts/synthesize.py \
  --text "这里放一大段长文稿……" \
  --output /Users/zhangleiandhim/Documents/index-tts2/outputs/lei/long_form.wav \
  --max-chars-per-chunk 180
```

## Emotion Project

- 如果需要“先润色，再按情绪分段，再给每段单独设情绪，最后统一合并”，请使用 `scripts/synthesize_project.py`
- 项目文件里可以为每一段单独配置 `text` 和 `emotion`
- 如果已经整理好了分段稿，可先用 `scripts/scaffold_long_form_project.py` 自动生成第一版 project

示例：

```bash
python3 /Users/zhangleiandhim/.codex/skills/lei-bloger-tts/scripts/synthesize_project.py \
  --project-file /Users/zhangleiandhim/Documents/index-tts2/outputs/lei/openclaw_polished_project.json
```

## Emotion control

- 默认 profile 已调整为更活泼、更激动：`lively_excited`
- 可直接编辑配置文件：`/Users/zhangleiandhim/.codex/skills/lei-bloger-tts/emotion_config.json`
- 支持三种模式：
  - `reference`：情绪参考音频
  - `vector`：8 维情绪向量，顺序为 `[高兴, 愤怒, 悲伤, 害怕, 厌恶, 忧郁, 惊讶, 平静]`
  - `text`：用情绪描述文本控制
- 长口播默认优先用 `vector`，因为更稳定、更容易保持段落之间连续
- 如果用户要“起伏更大”，优先小幅提高：
  - `emo_alpha`
  - `高兴`
  - `惊讶`
- 如果用户觉得“不连贯”，优先先改文案断句，再改情绪，不要只靠调向量硬救

示例：

```bash
python3 /Users/zhangleiandhim/.codex/skills/lei-bloger-tts/scripts/synthesize.py \
  --text "大家好，这是一段更活泼的测试。" \
  --profile lively_excited
```

```bash
python3 /Users/zhangleiandhim/.codex/skills/lei-bloger-tts/scripts/synthesize.py \
  --text "大家好，这是一段手动情绪向量测试。" \
  --emotion-mode vector \
  --emo-alpha 0.95 \
  --emo-vector "0.75,0,0,0,0,0,0.38,0.06"
```

```bash
python3 /Users/zhangleiandhim/.codex/skills/lei-bloger-tts/scripts/synthesize.py \
  --text "大家好，这是一段文本情绪控制测试。" \
  --emotion-mode text \
  --emo-text "语气热情、兴奋、带一点惊喜感"
```

## Notes

- The script uses the repository's `venv/bin/python`.
- It enables offline Hugging Face cache settings so synthesis works without network access when local cache is present.
- It shows terminal progress for model loading, text segmentation, synthesis, and final file saving.
- `scripts/synthesize_project.py` 会输出总进度条，适合长口播任务。
- Default filenames are timestamped and saved to `outputs/lei/`.
- 如果用户给了额外的情绪参考音频，可用 `--emo-reference /abs/path/file.wav`。
- 命令行参数优先级高于 `emotion_config.json` 中的配置。
