#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path


def load_config(config_path: Path) -> dict:
    return json.loads(config_path.read_text(encoding="utf-8"))


def read_input(text: str | None, input_file: str | None) -> str:
    if text:
        return text.strip()
    if not input_file:
        raise ValueError("Provide --text or --input-file")
    path = Path(input_file)
    if not path.exists():
        raise FileNotFoundError(path)
    if path.suffix.lower() not in {".txt", ".md"}:
        raise ValueError("Only .txt and .md are supported directly. Extract text first for .pdf/.docx.")
    return path.read_text(encoding="utf-8").strip()


def normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def zh_fillers(degree: float) -> list[str]:
    if degree < 0.35:
        return []
    if degree < 0.7:
        return ["其实", "你会发现", "嗯"]
    return ["其实", "你会发现", "嗯", "啊", "就是"]


def zh_paralinguistic_budget(degree: float) -> int:
    if degree < 0.78:
        return 0
    if degree < 0.9:
        return 1
    return 2


def en_fillers(degree: float) -> list[str]:
    if degree < 0.35:
        return []
    if degree < 0.7:
        return ["honestly", "basically", "the thing is"]
    return ["honestly", "basically", "the thing is", "you know", "to me"]


def smooth_mixed_language_zh(text: str) -> str:
    text = text.replace("IM + AI", "IM，和 AI")
    text = text.replace("AI + IM", "AI，和 IM")
    text = re.sub(r"([一-龥])\s*([A-Za-z][A-Za-z0-9+\-]{1,})", r"\1，\2", text)
    text = re.sub(r"([A-Za-z][A-Za-z0-9+\-]{1,})\s*([一-龥])", r"\1，\2", text)
    text = re.sub(r"([A-Za-z][A-Za-z0-9+\-]{1,})\s*([，、；。！？])", r"\1\2", text)
    text = re.sub(r"([，、；])\s*([A-Za-z][A-Za-z0-9+\-]{1,})", r"\1 \2", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def insert_zh_paralinguistic(sentence: str, degree: float, used_count: int) -> tuple[str, int]:
    budget = zh_paralinguistic_budget(degree)
    if used_count >= budget:
        return sentence, used_count
    if "<|" in sentence:
        return sentence, used_count

    if degree >= 0.9 and any(keyword in sentence for keyword in ["风险", "问题", "隐患", "门槛"]):
        return f"<|sigh|>{sentence}", used_count + 1
    if degree >= 0.85 and any(keyword in sentence for keyword in ["这其实也显示出", "你会发现", "说到这里", "还有一点"]):
        return f"<|breathing|>{sentence}", used_count + 1
    if degree >= 0.97 and any(keyword in sentence for keyword in ["好玩", "有意思", "挺有意思"]):
        return f"<|laughter|>{sentence}", used_count + 1
    if degree >= 0.995 and any(keyword in sentence for keyword in ["不好意思", "咳", "嗓子"]):
        return f"<|coughing|>{sentence}", used_count + 1
    return sentence, used_count


def polish_zh(text: str, degree: float) -> str:
    text = normalize_whitespace(text)
    text = smooth_mixed_language_zh(text)
    replacements = {
        "首先": "先说",
        "其次": "然后",
        "另外": "还有一点",
        "总的来说": "总的来说",
        "总体而言": "整体来看",
        "换句话说": "说白了",
        "我认为": "我觉得",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    paragraphs = [p.strip() for p in re.split(r"\n+", text) if p.strip()]
    fillers = zh_fillers(degree)
    polished = []
    for idx, paragraph in enumerate(paragraphs):
        if fillers and idx > 0:
            paragraph = f"{fillers[idx % len(fillers)]}，{paragraph}"
        if degree >= 0.7:
            paragraph = paragraph.replace("这显示出", "这其实也显示出", 1)
            paragraph = paragraph.replace("不仅", "不只是", 1)
            paragraph = paragraph.replace("更结合了", "而且还结合了", 1)
        if degree >= 0.8:
            paragraph = paragraph.replace("纷纷推出替代产品", "也都很快推出了自己的替代产品", 1)
            paragraph = paragraph.replace("试图利用", "其实就是想利用", 1)
            paragraph = paragraph.replace("抢占先机", "更早抢占先机", 1)
        sentences = [s.strip() for s in re.split(r"(?<=[。！？；])", paragraph) if s.strip()]
        if degree >= 0.75 and fillers:
            rebuilt = []
            for sentence_index, sentence in enumerate(sentences):
                if sentence_index == 0:
                    rebuilt.append(sentence)
                    continue
                if sentence.startswith(("其实", "你会发现", "嗯", "啊", "就是")):
                    rebuilt.append(sentence)
                    continue
                if sentence_index % 2 == 1:
                    prefix = fillers[(idx + sentence_index) % len(fillers)]
                    rebuilt.append(f"{prefix}，{sentence}")
                else:
                    rebuilt.append(sentence)
            paragraph = "".join(rebuilt)
        sentences = [s.strip() for s in re.split(r"(?<=[。！？；])", paragraph) if s.strip()]
        used_count = 0
        tagged = []
        for sentence in sentences:
            sentence, used_count = insert_zh_paralinguistic(sentence, degree, used_count)
            tagged.append(sentence)
        paragraph = "".join(tagged)
        paragraph = re.sub(r"([。！？；])", r"\1 ", paragraph)
        paragraph = re.sub(r"\s{2,}", " ", paragraph).strip()
        polished.append(paragraph)
    return "\n\n".join(polished)


def polish_en(text: str, degree: float) -> str:
    text = normalize_whitespace(text)
    replacements = {
        "In conclusion": "So, overall",
        "Firstly": "First",
        "Secondly": "Second",
        "Moreover": "And on top of that",
        "Therefore": "So",
        "In my opinion": "To me",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    paragraphs = [p.strip() for p in re.split(r"\n+", text) if p.strip()]
    fillers = en_fillers(degree)
    polished = []
    for idx, paragraph in enumerate(paragraphs):
        if fillers and idx > 0:
            paragraph = f"{fillers[idx % len(fillers)].capitalize()}, {paragraph}"
        paragraph = re.sub(r"([.!?;:])", r"\1 ", paragraph)
        paragraph = re.sub(r"\s{2,}", " ", paragraph).strip()
        polished.append(paragraph)
    return "\n\n".join(polished)


def split_sentences(text: str, language: str) -> list[str]:
    text = text.replace("\n", " ")
    if language == "zh":
        parts = re.split(r"(?<=[。！？；])", text)
    else:
        parts = re.split(r"(?<=[.!?;])\s+", text)
    return [part.strip() for part in parts if part.strip()]


def chunk_text(text: str, language: str, max_chars: int) -> list[str]:
    sentences = split_sentences(text, language)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        sep = "" if language == "zh" else " "
        candidate = f"{current}{sep}{sentence}".strip() if current else sentence
        if current and len(candidate) > max_chars:
            chunks.append(current.strip())
            current = sentence
        else:
            current = candidate
    if current.strip():
        chunks.append(current.strip())
    return chunks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(Path(__file__).resolve().parents[1] / "config.json"))
    parser.add_argument("--text")
    parser.add_argument("--input-file")
    parser.add_argument("--language", choices=["zh", "en"])
    parser.add_argument("--oralization-degree", type=float)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--max-chars", type=int)
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    config = load_config(config_path)
    language = args.language or config["default_language"]
    degree = args.oralization_degree if args.oralization_degree is not None else config["default_oralization_degree"]
    raw_text = read_input(args.text, args.input_file)
    if language == "zh":
        polished = polish_zh(raw_text, degree)
    else:
        polished = polish_en(raw_text, degree)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    max_chars = args.max_chars or config["max_chars_per_chunk"][language]
    segments = chunk_text(polished, language, max_chars)

    (output_dir / "raw.txt").write_text(raw_text, encoding="utf-8")
    (output_dir / "polished.txt").write_text(polished, encoding="utf-8")
    (output_dir / "segments.json").write_text(
        json.dumps(segments, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for idx, segment in enumerate(segments, start=1):
        (output_dir / f"segment_{idx:02d}.txt").write_text(segment, encoding="utf-8")

    manifest = {
        "language": language,
        "oralization_degree": degree,
        "segment_count": len(segments),
        "max_chars": max_chars,
    }
    (output_dir / "prepare_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(output_dir)


if __name__ == "__main__":
    main()
