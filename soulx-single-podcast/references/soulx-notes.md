# SoulX Notes

- Local project: `/Users/zhangleiandhim/Documents/lmd_data_root/apps/soulx-podcast`
- Single-speaker synthesis uses `cli/tts.py`
- Base model supports Mandarin and English
- Single-speaker input does not need `[S1]`; `cli/tts.py` wraps it internally
- Long text should be split into chunks and merged
- Local SoulX repo currently does not expose a native `speed_rate`/`speech_rate` CLI parameter
- Supported paralinguistic tags confirmed in local usage notes:
  - `<|laughter|>`
  - `<|sigh|>`
  - `<|breathing|>`
  - `<|coughing|>`

Recommended default:

- Prefer ordinary spoken fillers first
- Keep tags sparse
- Use punctuation for pauses
- For “faster” delivery, shorten sentences instead of only reducing punctuation
