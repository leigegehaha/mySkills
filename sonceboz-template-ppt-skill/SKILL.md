---
name: sonceboz-template-ppt-skill
description: Create English PowerPoint decks strictly from the bundled Sonceboz template when the user wants a PPT for a test report, market research, or meeting summary, especially when the input is free text, a document, or a webpage URL and the deck should reuse the template, polish the wording, extract images/data, and produce a professional client-facing presentation.
---

# Sonceboz Template PPT Skill

Use this skill when the user wants a PPT generated from:
- plain text or notes
- a `.docx` file
- a webpage URL
- mixed material with text, images, and numeric results

The deck must:
- use `assets/template.pptx` as the base template
- preserve the template theme, master, and layouts
- produce polished English copy
- choose an appropriate structure for `test-report`, `market-research`, or `meeting-summary`
- reuse extracted source images where available
- create simple visuals with PowerPoint shapes when no suitable image exists
- leave explicit placeholders for missing video or image assets when required
- support an `illustration-richness` level from `0` to `5`

## Non-negotiable rules

1. Always generate from `assets/template.pptx`.
2. Never hardcode an external absolute template path.
3. If the user replaces `assets/template.pptx`, re-run `scripts/analyze_template.py` or let `scripts/generate_deck.py` re-read the template automatically.
4. Keep the output in English unless the user explicitly asks for another language.
5. Prefer source-extracted images first. If the source has no useful images, use PowerPoint-native diagrams/cards/placeholders. Only fetch web images when the task clearly benefits from them and the source material is thin.
6. Respect `illustration-richness`:
   - `0`: no extra illustrations beyond source images and SVG visuals
   - `1-3`: use progressively more real web images
   - `4-5`: use real web images first, then Gemini fallback if insufficient
7. When evidence is incomplete, say so in the deck with a professional placeholder or note rather than inventing facts.

## Workflow

### 1. Inspect the template

Run:

```bash
python skills/sonceboz-template-ppt-skill/scripts/analyze_template.py
```

This reports:
- available layouts
- slide size
- placeholder structure
- theme colors and fonts, when detectable

Use the detected layouts instead of assuming fixed coordinates whenever possible. The generator already uses the template directly, so this step is mainly for validation and debugging.

### 2. Extract source material

Run:

```bash
python skills/sonceboz-template-ppt-skill/scripts/extract_source.py \
  --input /path/to/source.docx \
  --output /tmp/source.json
```

or:

```bash
python skills/sonceboz-template-ppt-skill/scripts/extract_source.py \
  --input 'https://example.com/page' \
  --output /tmp/source.json
```

This creates a normalized JSON package with:
- extracted text
- candidate numeric facts
- extracted images
- source metadata

Supported inputs:
- plain text file
- markdown file
- `.docx`
- `.html`
- webpage URL

### 3. Generate the deck

Run:

```bash
python skills/sonceboz-template-ppt-skill/scripts/generate_deck.py \
  --source /tmp/source.json \
  --purpose test-report \
  --title "Linkerhand O6 Test Report" \
  --output /path/to/output.pptx
```

Purposes:
- `test-report`
- `market-research`
- `meeting-summary`

The generator will:
- load the template from `assets/template.pptx`
- remove template content slides
- build a new deck on top of the template masters/layouts
- polish and expand the language
- lay out each slide according to the selected purpose
- add charts, metric cards, comparison blocks, and placeholders where appropriate
- optionally call the sibling `web-image-research` skill for filtered real web images when better supporting visuals are needed
- optionally generate richer SVG-based diagrams and insert rendered PNG versions into the deck

## Web image enrichment

When source images are missing or weak, first try:

```bash
python skills/sonceboz-template-ppt-skill/scripts/extract_source.py \
  --input /path/to/source.docx \
  --output /tmp/source.json \
  --auto-web-images
```

This will:
- derive image queries from the source title and top content lines
- search the sibling `web-image-research` skill, which can use Bing, Wikipedia, Wikimedia Commons, Openverse, and Flickr
- download candidate images into the extracted asset folder
- append them to `image_paths`

Use Wikimedia images as support visuals, not as evidence for unsupported claims.

## Illustration richness

Use `--illustration-richness` to control how many extra support visuals appear:

```bash
python skills/sonceboz-template-ppt-skill/scripts/generate_deck.py \
  --source /tmp/source.json \
  --purpose test-report \
  --title "Example" \
  --output /tmp/example.pptx \
  --auto-visuals \
  --illustration-richness 4
```

- `0`: only original images + generated SVG visuals
- `1`: up to 1 real web image
- `2`: up to 2 real web images
- `3`: up to 3 real web images
- `4`: up to 4 real web images, then 1 Gemini realistic fallback image if needed
- `5`: up to 5 real web images, then up to 2 Gemini realistic fallback images if needed

The last page is always a template thank-you page containing only `Thank you`. Summary content goes on the page before it, using a normal body layout.

## SVG visual generation

Generate richer reusable visuals:

```bash
python skills/sonceboz-template-ppt-skill/scripts/svg_factory.py \
  --source /tmp/source.json \
  --purpose test-report \
  --output-dir /tmp/visuals
```

This creates:
- SVG source visuals for sharing and editing
- PNG renders for insertion into PPT

The deck generator can also call this automatically:

```bash
python skills/sonceboz-template-ppt-skill/scripts/generate_deck.py \
  --source /tmp/source.json \
  --purpose market-research \
  --title "Example" \
  --output /tmp/example.pptx \
  --auto-visuals \
  --illustration-richness 3
```

## Distribution zip

Package the whole skill for sharing:

```bash
python skills/sonceboz-template-ppt-skill/scripts/package_skill.py \
  --skill-dir skills/sonceboz-template-ppt-skill \
  --output /tmp/sonceboz-template-ppt-skill.zip
```

The zip excludes transient outputs and cache files.

## Purpose-specific guidance

### Test Report

Default structure:
- cover
- executive summary
- product / scope overview
- setup or method
- result slides grouped by topic
- conclusion / recommendation

What to emphasize:
- measured value vs. nominal value
- test method clarity
- evidence quality
- missing evidence placeholders for videos or thermal images

### Market Research

Default structure:
- cover
- executive summary
- market landscape
- customer / competitor snapshot
- key findings
- opportunities and risks
- recommendation / next step

What to emphasize:
- crisp market framing
- comparison tables
- shareable client-facing language

### Meeting Summary

Default structure:
- cover
- summary of meeting purpose
- discussion highlights
- decisions
- open issues
- action items and next steps

What to emphasize:
- short, explicit, executive wording
- owner / deadline structure when present
- no vague filler

## Editing expectations

When the source text is rough, rewrite it into concise professional English:
- convert raw notes into complete statements
- add context words that improve readability
- keep all quantitative claims faithful to the source
- avoid exaggeration when evidence is thin

Good:
- `The corrected maximum grasp force reached 67.8 N, which is close to the 70 N nominal specification.`

Bad:
- `The product delivered outstanding best-in-class performance.` unless the source actually supports that claim.

## Images and visuals

Preferred order:
1. extracted source images
2. filtered real web images from the sibling `web-image-research` skill
3. PowerPoint-native diagrams, SVG visuals, or metric cards
4. explicit placeholders for user-supplied media

Do not clutter the slide. A simple shape-based visual is better than an irrelevant stock image.

Placement is purpose-aware:
- test reports: overview slide prefers product imagery, method slide prefers setup/evidence imagery, results slide prefers generated metric or timeline visuals
- market research: first visual should establish market or product context, second visual should support implications or recommendation
- meeting summary: one supporting context image is enough; do not spread decorative imagery across every page

## Files in this skill

- `assets/template.pptx`: replaceable Sonceboz PPT template asset
- `scripts/analyze_template.py`: inspect layouts and placeholders
- `scripts/extract_source.py`: normalize text/images/data from input
- `scripts/generate_deck.py`: create the final PowerPoint
- `scripts/svg_factory.py`: generate reusable SVG and PNG visuals
- `scripts/package_skill.py`: build a clean distributable zip
- sibling skill `../web-image-research`: search real web images and Gemini fallback visuals
- `requirements.txt`: Python dependencies for this skill only

## Validation

Before handing off the result:

1. Open the output PPT with `python-pptx` and confirm the slide count is correct.
2. Inspect extracted slide text:

```bash
python skills/sonceboz-template-ppt-skill/scripts/generate_deck.py --inspect /path/to/output.pptx
```

3. Check for leftover placeholders like `Click to edit`.
4. If the user changed the template, regenerate and inspect again.
