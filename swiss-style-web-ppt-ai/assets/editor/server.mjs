import http from "node:http";
import path from "node:path";
import vm from "node:vm";
import { promises as fs } from "node:fs";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, "..");
const port = Number(process.env.PORT || 4321);

const DEFAULT_SOUND_CONFIG = Object.freeze({
  preset: "cyber-brush",
  intensity: 1,
  brightness: 1,
  tail: 1,
  chirp: 1,
  stereo: 1,
});

const MIME_TYPES = {
  ".css": "text/css; charset=utf-8",
  ".gif": "image/gif",
  ".html": "text/html; charset=utf-8",
  ".ico": "image/x-icon",
  ".jpeg": "image/jpeg",
  ".jpg": "image/jpeg",
  ".js": "application/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".md": "text/markdown; charset=utf-8",
  ".mjs": "application/javascript; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".txt": "text/plain; charset=utf-8",
  ".webp": "image/webp",
  ".woff2": "font/woff2",
};

const safeJson = (value) => JSON.stringify(value, null, 2);

const clampNumber = (value, min, max, fallback) => {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return fallback;
  return Math.min(max, Math.max(min, numeric));
};

const normalizeRequestPath = (value = "") => {
  const cleaned = decodeURIComponent(String(value)).split("?")[0].replace(/^\/+/, "");
  return cleaned.replace(/\\/g, "/");
};

const resolveWithinRoot = (relativePath) => {
  const normalized = normalizeRequestPath(relativePath);
  const absolute = path.resolve(rootDir, normalized);
  if (absolute !== rootDir && !absolute.startsWith(`${rootDir}${path.sep}`)) {
    throw new Error("Path is outside the project root");
  }
  return absolute;
};

const sendJson = (res, statusCode, payload) => {
  res.writeHead(statusCode, {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store",
  });
  res.end(JSON.stringify(payload));
};

const sendApiError = (res, error, fallback = "Invalid request") => {
  const message = error instanceof Error ? error.message : fallback;
  sendJson(res, 400, { error: message });
};

const sendText = (res, statusCode, text, contentType = "text/plain; charset=utf-8") => {
  res.writeHead(statusCode, {
    "Content-Type": contentType,
    "Cache-Control": "no-store",
  });
  res.end(text);
};

const redirect = (res, location) => {
  res.writeHead(302, { Location: location });
  res.end();
};

const parseJsonBody = async (req) => {
  const chunks = [];
  let total = 0;
  for await (const chunk of req) {
    total += chunk.length;
    if (total > 30 * 1024 * 1024) {
      throw new Error("Request body too large");
    }
    chunks.push(chunk);
  }
  const text = Buffer.concat(chunks).toString("utf8");
  if (!text) return {};
  return JSON.parse(text);
};

const matchTagContent = (html, tagName) => {
  const pattern = new RegExp(`<${tagName}[^>]*>([\\s\\S]*?)<\\/${tagName}>`, "i");
  const match = html.match(pattern);
  return match ? match[1].replace(/<[^>]+>/g, "").trim() : "";
};

const matchHeading = (html) => {
  const match = html.match(/<(h1|h2)[^>]*>([\s\S]*?)<\/\1>/i);
  return match ? match[2].replace(/<[^>]+>/g, "").trim() : "";
};

const toRelativePath = (absolutePath) => path.relative(rootDir, absolutePath).split(path.sep).join("/");

const normalizeSoundConfig = (config = {}) => ({
  preset: typeof config?.preset === "string" && config.preset ? config.preset : DEFAULT_SOUND_CONFIG.preset,
  intensity: clampNumber(config?.intensity, 0.35, 2, DEFAULT_SOUND_CONFIG.intensity),
  brightness: clampNumber(config?.brightness, 0.35, 2, DEFAULT_SOUND_CONFIG.brightness),
  tail: clampNumber(config?.tail, 0.35, 2, DEFAULT_SOUND_CONFIG.tail),
  chirp: clampNumber(config?.chirp, 0, 2.5, DEFAULT_SOUND_CONFIG.chirp),
  stereo: clampNumber(config?.stereo, 0, 2, DEFAULT_SOUND_CONFIG.stereo),
});

const readSoundConfig = async () => {
  const configPath = path.join(rootDir, "assets", "deck-config.js");
  try {
    const source = await fs.readFile(configPath, "utf8");
    const sandbox = { window: {} };
    vm.runInNewContext(source, sandbox, { timeout: 200 });
    return normalizeSoundConfig(sandbox.window.DECK_SOUND_CONFIG);
  } catch (error) {
    return { ...DEFAULT_SOUND_CONFIG };
  }
};

const writeSoundConfig = async (config) => {
  const normalized = normalizeSoundConfig(config);
  const configPath = path.join(rootDir, "assets", "deck-config.js");
  const source = `window.DECK_SOUND_CONFIG = ${safeJson(normalized)};\n`;
  await fs.mkdir(path.dirname(configPath), { recursive: true });
  await fs.writeFile(configPath, source, "utf8");
  return normalized;
};

const scanDecks = async () => {
  const entries = await fs.readdir(rootDir, { withFileTypes: true });
  const deckFiles = entries
    .filter((entry) => entry.isFile() && /^index.*\.html$/i.test(entry.name))
    .map((entry) => entry.name)
    .sort((left, right) => left.localeCompare(right, "zh-Hans-CN"));

  const decks = [];

  for (const indexFile of deckFiles) {
    const absoluteIndexPath = path.join(rootDir, indexFile);
    const html = await fs.readFile(absoluteIndexPath, "utf8");
    const title = matchTagContent(html, "title") || indexFile;
    const slides = [];
    const iframeMatches = html.matchAll(/<iframe[^>]+src="([^"]+)"/gi);

    for (const match of iframeMatches) {
      const slidePath = normalizeRequestPath(match[1]);
      const absoluteSlidePath = resolveWithinRoot(slidePath);
      let slideHtml = "";
      try {
        slideHtml = await fs.readFile(absoluteSlidePath, "utf8");
      } catch (error) {
        slideHtml = "";
      }
      slides.push({
        path: slidePath,
        title: matchHeading(slideHtml) || matchTagContent(slideHtml, "title") || path.basename(slidePath),
        label: matchTagContent(slideHtml, "title") || path.basename(slidePath),
      });
    }

    decks.push({
      indexFile,
      title,
      slides,
    });
  }

  return decks;
};

const extractIframePaths = (html) => {
  const pattern = /<iframe[^>]+src="([^"]+)"[^>]*>/gi;
  const paths = [];
  let match;
  while ((match = pattern.exec(html))) {
    paths.push(normalizeRequestPath(match[1]));
  }
  return paths;
};

const buildIframeMarkup = (paths) => {
  return paths
    .map(
      (src, index) =>
        `        <iframe class="deck-slide" src="${src}" title="第 ${index + 1} 页"></iframe>`
    )
    .join("\n");
};

const rewriteIndexIframes = (html, paths) => {
  const pattern =
    /(<div class="viewport-shell">[\s\S]*?<div class="shell-shutter"[^>]*><\/div>)([\s\S]*?)(<div class="shell-counter"[^>]*>[\s\S]*?<\/div>[\s\S]*?<\/div>)/m;
  const match = html.match(pattern);
  if (!match) {
    throw new Error("Cannot locate iframe block inside index");
  }
  const [_, head, oldList, tail] = match;
  const newList = buildIframeMarkup(paths);
  const prefix = head.endsWith("\n") ? head : `${head}\n`;
  return `${prefix}${newList}\n${tail}`;
};

const updateDeckIframes = async (deck, paths) => {
  const absolute = resolveWithinRoot(deck);
  const html = await fs.readFile(absolute, "utf8");
  const newHtml = rewriteIndexIframes(html, paths);
  await fs.writeFile(absolute, newHtml, "utf8");
  return paths;
};

const buildBlankSlide = ({ pageNumber, totalSlides, title, lead, brand }) => {
  const safeTitle = title || "新幻灯页";
  const safeLead = lead || "在右侧面板替换这一句话来描述本页核心观点。";
  const chipText = brand || "磊哥哥科技拆解室";
  const pageLabel = `${String(pageNumber).padStart(2, "0")} / ${String(totalSlides).padStart(2, "0")}`;
  return `<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>${pageLabel} - ${safeTitle}</title>
    <link rel="stylesheet" href="../assets/deck.css" />
  </head>
  <body data-mode="slide">
    <canvas class="particle-canvas"></canvas>
    <div class="noise"></div>
    <div class="cursor-follower"></div>
    <div class="stage-root">
      <header class="slide-top">
        <div class="brand-chip">${chipText}</div>
        <div class="page-chip">${pageLabel}</div>
      </header>
      <main class="deck hero-grid">
        <section class="panel panel-strong hero-copy hover-card tilt-card reveal">
          <div class="copy-stack">
            <p class="eyebrow">新页面</p>
            <h1 class="slide-title">${safeTitle}</h1>
            <p class="lead">${safeLead}</p>
          </div>
          <div class="chip-row">
            <span class="text-chip">新内容</span>
            <span class="text-chip">统一风格</span>
            <span class="text-chip">可调</span>
          </div>
        </section>
        <section class="panel hover-card reveal">
          <div class="content-stack">
            <div class="stamp">内容配图区</div>
            <h2 class="panel-title">在这里放本页关键配图</h2>
            <p class="card-copy">通过「上传图片」把这里替换为和本页观点直接相关的图片、图表或结构示意。</p>
            <div class="media-stack">
              <figure class="media-frame compact tilt-card hover-card">
                <div class="image-tint"></div>
                <div class="scan"></div>
              </figure>
              <div class="media-caption">
                <span class="media-tag">内容配图</span>
                <span class="media-note">右侧面板可调整图像地址、填充模式及透明度。</span>
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
    <script src="../assets/deck.js"></script>
  </body>
</html>`;
};

const ensureSlideDirectory = (deck, existingPaths) => {
  if (existingPaths.length) {
    return path.posix.dirname(existingPaths[0]);
  }
  if (deck.includes("ai")) {
    return "slides-ai";
  }
  return "slides";
};

const insertPathAfter = (paths, target, newPath) => {
  const idx = paths.findIndex((value) => value === target);
  if (idx === -1) {
    paths.push(newPath);
  } else {
    paths.splice(idx + 1, 0, newPath);
  }
  return paths;
};

const escapeHtml = (value = "") =>
  String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

const isDeckIndexFile = (value) => /^index.*\.html$/i.test(path.basename(value));

const ensureDeckIndexPath = (value) => {
  const normalized = normalizeRequestPath(value);
  if (!normalized || !isDeckIndexFile(normalized)) {
    throw new Error("Deck path must point to an index.*.html file");
  }
  return normalized;
};

const loadDeckMetadata = async (deck) => {
  const normalizedDeck = ensureDeckIndexPath(deck);
  const absoluteDeck = resolveWithinRoot(normalizedDeck);
  const html = await fs.readFile(absoluteDeck, "utf8");
  const paths = extractIframePaths(html);
  return { normalizedDeck, absoluteDeck, paths };
};

const determineSlideFolder = (deck, paths) => {
  const folder = normalizeRequestPath(ensureSlideDirectory(deck, paths));
  if (!folder || folder === ".") {
    return "slides";
  }
  return folder;
};

const getHighestSlideNumber = async (folder) => {
  const absolute = resolveWithinRoot(folder);
  try {
    const entries = await fs.readdir(absolute, { withFileTypes: true });
    return entries.reduce((max, entry) => {
      if (!entry.isFile()) return max;
      const match = entry.name.match(/^slide-(\d+)\.html$/i);
      if (!match) return max;
      return Math.max(max, Number(match[1]));
    }, 0);
  } catch (error) {
    if (error.code === "ENOENT") {
      return 0;
    }
    throw error;
  }
};

const allocateSlideFilename = async (folder) => {
  const highest = await getHighestSlideNumber(folder);
  const nextNumber = highest + 1;
  const label = String(nextNumber).padStart(2, "0");
  return `slide-${label}.html`;
};

const sanitizeSlidePaths = (values, folder) => {
  if (!Array.isArray(values)) {
    throw new Error("paths must be an array");
  }
  const prefix = `${folder}/`;
  return values
    .map((value) => normalizeRequestPath(value))
    .filter(Boolean)
    .map((value) => {
      if (!value.startsWith(prefix)) {
        throw new Error(`Slide path ${value} is outside of ${folder}`);
      }
      return value;
    });
};

const writeSlideFile = async (relativePath, content) => {
  const absolute = resolveWithinRoot(relativePath);
  await fs.mkdir(path.dirname(absolute), { recursive: true });
  await fs.writeFile(absolute, content, "utf8");
};

const createSlideEntry = async ({ deck, after, title, lead, brand }) => {
  const metadata = await loadDeckMetadata(deck);
  const folder = determineSlideFolder(deck, metadata.paths);
  const filename = await allocateSlideFilename(folder);
  const newSlidePath = `${folder}/${filename}`;
  const normalizedAfter = typeof after === "string" ? normalizeRequestPath(after) : undefined;
  const insertTarget =
    normalizedAfter && metadata.paths.includes(normalizedAfter)
      ? normalizedAfter
      : metadata.paths[metadata.paths.length - 1];
  const updatedPaths = insertPathAfter([...metadata.paths], insertTarget, newSlidePath);
  const pageIndex = updatedPaths.indexOf(newSlidePath);
  const content = buildBlankSlide({
    pageNumber: pageIndex + 1,
    totalSlides: updatedPaths.length,
    title: escapeHtml(title),
    lead: escapeHtml(lead),
    brand: escapeHtml(brand),
  });
  await writeSlideFile(newSlidePath, content);
  await updateDeckIframes(metadata.normalizedDeck, updatedPaths);
  return { path: newSlidePath, paths: updatedPaths };
};

const duplicateSlideEntry = async ({ deck, source, after }) => {
  if (!source) {
    throw new Error("Missing source slide for duplication");
  }
  const metadata = await loadDeckMetadata(deck);
  const folder = determineSlideFolder(deck, metadata.paths);
  const normalizedSource = sanitizeSlidePaths([source], folder)[0];
  if (!metadata.paths.includes(normalizedSource)) {
    throw new Error("Source slide is not part of the deck");
  }
  const filename = await allocateSlideFilename(folder);
  const newSlidePath = `${folder}/${filename}`;
  const absoluteSource = resolveWithinRoot(normalizedSource);
  const absoluteTarget = resolveWithinRoot(newSlidePath);
  await fs.copyFile(absoluteSource, absoluteTarget);
  const normalizedAfter = typeof after === "string" ? normalizeRequestPath(after) : normalizedSource;
  const insertTarget =
    normalizedAfter && metadata.paths.includes(normalizedAfter) ? normalizedAfter : normalizedSource;
  const updatedPaths = insertPathAfter([...metadata.paths], insertTarget, newSlidePath);
  await updateDeckIframes(metadata.normalizedDeck, updatedPaths);
  return { path: newSlidePath, paths: updatedPaths };
};

const deleteSlideEntry = async ({ deck, target }) => {
  if (!target) {
    throw new Error("Missing target slide for deletion");
  }
  const metadata = await loadDeckMetadata(deck);
  if (!metadata.paths.length) {
    throw new Error("Deck contains no slides");
  }
  if (metadata.paths.length === 1) {
    throw new Error("Deck must retain at least one slide");
  }
  const folder = determineSlideFolder(deck, metadata.paths);
  const normalizedTarget = sanitizeSlidePaths([target], folder)[0];
  if (!metadata.paths.includes(normalizedTarget)) {
    throw new Error("Target slide is not part of the deck");
  }
  const absoluteTarget = resolveWithinRoot(normalizedTarget);
  await fs.unlink(absoluteTarget);
  const updatedPaths = metadata.paths.filter((value) => value !== normalizedTarget);
  await updateDeckIframes(metadata.normalizedDeck, updatedPaths);
  return { path: normalizedTarget, paths: updatedPaths };
};

const updateDeckIframeOrder = async ({ deck, paths }) => {
  const metadata = await loadDeckMetadata(deck);
  const folder = determineSlideFolder(deck, metadata.paths);
  const normalizedPaths = sanitizeSlidePaths(paths, folder);
  if (!normalizedPaths.length) {
    throw new Error("Deck must include at least one slide");
  }
  if (new Set(normalizedPaths).size !== normalizedPaths.length) {
    throw new Error("Slide paths must be unique");
  }
  if (normalizedPaths.length !== metadata.paths.length) {
    throw new Error("Slide count mismatch");
  }
  const missing = metadata.paths.filter((value) => !normalizedPaths.includes(value));
  if (missing.length) {
    throw new Error("Provided paths must include every slide");
  }
  await updateDeckIframes(metadata.normalizedDeck, normalizedPaths);
  return { paths: normalizedPaths };
};

const handlePageCreate = async (body = {}) => {
  const result = await createSlideEntry({
    deck: body.deck || body.deckPath,
    after: body.after || body.afterPath,
    title: body.title,
    lead: body.lead,
    brand: body.brand,
  });
  const decks = await scanDecks();
  return { ok: true, decks, ...result };
};

const handlePageDuplicate = async (body = {}) => {
  const result = await duplicateSlideEntry({
    deck: body.deck || body.deckPath,
    source: body.path || body.sourcePath,
    after: body.after || body.afterPath,
  });
  const decks = await scanDecks();
  return { ok: true, decks, ...result };
};

const handlePageDelete = async (body = {}) => {
  const result = await deleteSlideEntry({
    deck: body.deck || body.deckPath,
    target: body.path || body.targetPath,
  });
  const decks = await scanDecks();
  return { ok: true, decks, ...result };
};

const handleDeckIframes = async (body = {}) => {
  const result = await updateDeckIframeOrder({
    deck: body.deck || body.deckPath,
    paths: body.paths,
  });
  const decks = await scanDecks();
  return { ok: true, decks, ...result };
};

const safeFilename = (value) => {
  const name = String(value || "image")
    .toLowerCase()
    .replace(/\.[^.]+$/, "")
    .replace(/[^a-z0-9-_]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
  return name || "image";
};

const extensionFromMime = (mimeType) => {
  const lookup = {
    "image/gif": ".gif",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/svg+xml": ".svg",
    "image/webp": ".webp",
  };
  return lookup[mimeType] || "";
};

const handleUploadImage = async (body) => {
  const dataUrl = String(body?.dataUrl || "");
  const filename = String(body?.filename || "image");
  const folder = normalizeRequestPath(body?.folder || "assets/images/editor");
  if (!folder.startsWith("assets/images")) {
    throw new Error("Images must be saved inside assets/images");
  }
  const dataMatch = dataUrl.match(/^data:([^;]+);base64,(.+)$/);
  if (!dataMatch) {
    throw new Error("Invalid image payload");
  }
  const mimeType = dataMatch[1];
  const base64 = dataMatch[2];
  const extension = path.extname(filename) || extensionFromMime(mimeType) || ".png";
  const absoluteFolder = resolveWithinRoot(folder);
  const targetName = `${Date.now()}-${safeFilename(filename)}${extension}`;
  const absoluteTarget = path.join(absoluteFolder, targetName);

  await fs.mkdir(absoluteFolder, { recursive: true });
  await fs.writeFile(absoluteTarget, Buffer.from(base64, "base64"));

  return {
    path: toRelativePath(absoluteTarget),
  };
};

const serveStaticFile = async (res, requestPath) => {
  try {
    const normalized = normalizeRequestPath(requestPath);
    const absolute = resolveWithinRoot(normalized || "editor/index.html");
    let stat = await fs.stat(absolute);
    let filePath = absolute;

    if (stat.isDirectory()) {
      filePath = path.join(absolute, "index.html");
      stat = await fs.stat(filePath);
    }

    const extension = path.extname(filePath).toLowerCase();
    const mimeType = MIME_TYPES[extension] || "application/octet-stream";
    const content = await fs.readFile(filePath);

    res.writeHead(200, {
      "Content-Type": mimeType,
      "Cache-Control": extension === ".html" ? "no-store" : "public, max-age=0",
      "Content-Length": stat.size,
    });
    res.end(content);
  } catch (error) {
    sendText(res, 404, "Not Found");
  }
};

const handleApi = async (req, res, pathname) => {
  if (req.method === "GET" && pathname === "/api/decks") {
    const decks = await scanDecks();
    sendJson(res, 200, {
      cwd: rootDir,
      decks,
    });
    return;
  }

  if (req.method === "GET" && pathname === "/api/sound-config") {
    const config = await readSoundConfig();
    sendJson(res, 200, { config });
    return;
  }

  if (req.method === "POST" && pathname === "/api/save-file") {
    const body = await parseJsonBody(req);
    const relativePath = normalizeRequestPath(body?.path);
    const content = String(body?.content ?? "");
    if (!relativePath) {
      sendJson(res, 400, { error: "Missing file path" });
      return;
    }
    const absolutePath = resolveWithinRoot(relativePath);
    await fs.mkdir(path.dirname(absolutePath), { recursive: true });
    await fs.writeFile(absolutePath, content, "utf8");
    sendJson(res, 200, {
      ok: true,
      path: relativePath,
    });
    return;
  }

  if (req.method === "POST" && pathname === "/api/upload-image") {
    const body = await parseJsonBody(req);
    const result = await handleUploadImage(body);
    sendJson(res, 200, result);
    return;
  }

  if (req.method === "POST" && pathname === "/api/sound-config") {
    const body = await parseJsonBody(req);
    const config = await writeSoundConfig(body?.config || {});
    sendJson(res, 200, { ok: true, config });
    return;
  }

  if (req.method === "POST" && pathname === "/api/page-create") {
    const body = await parseJsonBody(req);
    try {
      const result = await handlePageCreate(body);
      sendJson(res, 200, result);
    } catch (error) {
      sendApiError(res, error);
    }
    return;
  }

  if (req.method === "POST" && pathname === "/api/page-duplicate") {
    const body = await parseJsonBody(req);
    try {
      const result = await handlePageDuplicate(body);
      sendJson(res, 200, result);
    } catch (error) {
      sendApiError(res, error);
    }
    return;
  }

  if (req.method === "POST" && pathname === "/api/page-delete") {
    const body = await parseJsonBody(req);
    try {
      const result = await handlePageDelete(body);
      sendJson(res, 200, result);
    } catch (error) {
      sendApiError(res, error);
    }
    return;
  }

  if (req.method === "POST" && pathname === "/api/deck/iframes") {
    const body = await parseJsonBody(req);
    try {
      const result = await handleDeckIframes(body);
      sendJson(res, 200, result);
    } catch (error) {
      sendApiError(res, error);
    }
    return;
  }

  sendJson(res, 404, { error: "Unknown API route" });
};

const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url, `http://${req.headers.host || `127.0.0.1:${port}`}`);
    const pathname = url.pathname;

    if (pathname === "/") {
      redirect(res, "/editor/");
      return;
    }

    if (pathname === "/editor") {
      redirect(res, "/editor/");
      return;
    }

    if (pathname.startsWith("/api/")) {
      await handleApi(req, res, pathname);
      return;
    }

    await serveStaticFile(res, pathname);
  } catch (error) {
    sendJson(res, 500, {
      error: error instanceof Error ? error.message : "Unexpected server error",
    });
  }
});

server.listen(port, () => {
  console.log(`Swiss deck editor available at http://127.0.0.1:${port}/editor/`);
});
