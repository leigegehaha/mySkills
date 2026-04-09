# Swiss Style Web PPT AI Playbook

## Non-negotiables

- Use `index.html` as the player and `slides/slide-XX.html` as the actual pages.
- Stitch slides together with `iframe`.
- Keep every page inside a strict 16:9 composition and safe margins.
- Show `磊哥哥科技拆解室` at the top-left of each slide unless the user explicitly overrides it.
- Keep the home page minimal: visible title + start button only.
- Never show a slide overview wall, thumbnail matrix, or page directory on the cover.
- Enter fullscreen on start whenever the browser allows it.
- Navigate with keyboard left/right only.
- Do not show visible previous/next buttons.
- Images may be AI-generated, but visible slide copy must not expose process labels like `AI illustration`, `AI generated`, or `placeholder` unless the source itself discusses them.

## Visual Defaults

- Style: Swiss editorial grid + red/white palette + light warm background + pixel-tech accents.
- Tone: clean, sharp, modern, rational, slightly playful.
- Typography: bold sans titles, readable sans body, mono or pixel labels for chips and counters.
- Keep red outline stamp labels horizontal and aligned to the grid; avoid diagonal sticker-style rotation.
- Layout: modular grid, large margins, strong alignment, obvious hierarchy.
- Avoid: dark cyberpunk overload, glossy gradients everywhere, heavy skeuomorphism, crowded dashboards.

## Density Guardrails

- One core claim per slide.
- One hero title, one short lead, one primary visual anchor.
- Prefer 3–5 bullets or 3 cards; split slides if the copy gets dense.
- Keep captions short and supportive.
- If a paragraph looks long in HTML, shorten it or move it to a new slide.

## Motion System

- Use subtle staggered reveals with short delays like `0.08s` to `0.24s`.
- Keep hover and tilt motion light; presentation readability is more important than spectacle.
- Keep particles sparse and ambient.
- Keep page-turn sound low, brush-like, and bass-leaning rather than bright or clicky.
- Make page transitions crisp and directional.
- Tune page-turn sound centrally in shared JS instead of per slide.

## AI Illustration Rules

- Generate the whole set as one series, not one unrelated image at a time.
- Keep the same perspective language, light source, texture treatment, and compositional density across slides.
- Prefer editorial / concept illustration instead of photoreal faces.
- Use images to clarify the core metaphor of the slide, not to decorate empty space.
- When an image would become too busy, switch to a custom SVG diagram instead.
- In visible captions, describe the business point or argument the image supports, not how the image was produced.

## Prompt Formula

Use this structure:

`[slide topic], Swiss editorial poster composition, red and white palette, light warm background, pixel-tech accents, modular grid feeling, crisp edges, subtle halftone texture, clean concept illustration, cohesive series, 16:9 horizontal layout, minimal clutter, no text, no watermark`

Recommended negative prompt:

`photoreal portrait, dark neon cyberpunk, crowded interface, tiny objects, readable text, logo, watermark, low contrast, muddy colors`

## Example Prompt

`Desktop AI agent replacing a fragile experimental claw workflow, Swiss editorial poster composition, red and white palette, light warm background, pixel-tech accents, modular grid feeling, crisp edges, subtle halftone texture, clean concept illustration, cohesive series, 16:9 horizontal layout, minimal clutter, no text, no watermark`

## File Conventions

- Save images as `assets/images/slide-01.png`, `assets/images/slide-02.png`, and so on.
- Keep deck-wide assets shared in `assets/deck.css` and `assets/deck.js`.
- Use relative paths from slide files, for example `../assets/images/slide-03.png`.

## QA Checklist

- Does the cover show only the title and the start button?
- Does the cover avoid any thumbnail wall or slide overview?
- Does every slide fit without overflow?
- Does every slide preserve the same red/white/light/pixel design system?
- Are the AI images stylistically consistent?
- Do visible labels stay tied to the script instead of exposing production-process notes?
- Do left/right keys switch pages and avoid visible nav buttons?
- Does the fullscreen start still work?
- Does the shared sound feel short, clean, and techy rather than musical?
