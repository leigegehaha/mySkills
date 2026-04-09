---
name: web-image-research
description: Search and download real web images for presentations, reports, and research decks from text, documents, or normalized source JSON, then optionally fall back to Gemini image generation in a concise realistic style when not enough suitable real images are found.
---

# Web Image Research

Use this skill when a deck, report, or client-facing artifact needs:
- real web images
- topic-aware image search from text or documents
- automatic image download and scoring
- optional Gemini fallback when real images are insufficient

## Inputs

Preferred input is normalized JSON from another workflow, but raw query mode also works.

### Normalized source JSON

```bash
python skills/web-image-research/scripts/search_images.py \
  --source /tmp/source.json \
  --purpose test-report \
  --richness 3 \
  --output-dir /tmp/image-pack
```

### Raw query mode

```bash
python skills/web-image-research/scripts/search_images.py \
  --query "industrial robotic hand thermal test bench" \
  --purpose test-report \
  --richness 4 \
  --output-dir /tmp/image-pack
```

## Sources

The skill searches public real-image sources:
- Bing Images result-page extraction
- Wikipedia page images
- Wikimedia Commons
- Openverse
- Flickr public feed

If the result set is too weak and richness is high enough, it can call the bundled Gemini fallback script.

## Richness setting

`richness` is an integer from `0` to `5`:

- `0`: no extra web or AI images
- `1`: minimal extra illustration, up to 1 real image
- `2`: light illustration, up to 2 real images
- `3`: medium illustration, up to 3 real images
- `4`: rich illustration, up to 4 real images, then 1 Gemini fallback image if needed
- `5`: richest mode, up to 5 real images, then up to 2 Gemini fallback images if needed

## Real-image selection

The search script:
- derives multiple search queries from title and content
- scores images by size, orientation, and query relevance
- rejects many low-value Bing hits such as stock-image domains, vector/diagram pages, documentation screenshots, and obvious thumbnail URLs
- validates downloaded image size before keeping the file
- prefers domain diversity so the same site does not dominate the image set
- prefers landscape, clean, presentation-friendly imagery
- downloads results into the requested output folder
- writes a JSON manifest with metadata and rankings

## Gemini fallback

When enabled by richness and when `GEMINI_API_KEY` is present:
- generated images must use a concise realistic style
- prompts avoid fantasy or stylized illustration language
- generated images are treated as support visuals, not factual evidence

Run directly:

```bash
python skills/web-image-research/scripts/gemini_real_image.py \
  --prompt "clean realistic industrial robotic hand on white background, product photography, minimal studio lighting" \
  --output-dir /tmp/ai-images \
  --count 1
```

## Outputs

The skill writes:
- downloaded or generated image files
- `images_manifest.json`

Manifest contains:
- selected queries
- image origin
- inferred role such as `product`, `evidence`, or `context`
- local path
- score
- whether image is `real` or `ai`
- rejected candidates with simple reasons when filtering removes them

## Bundled files

- `scripts/search_images.py`
- `scripts/gemini_real_image.py`
- `config.json`
