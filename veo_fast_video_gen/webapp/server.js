#!/usr/bin/env node

const http = require('http');
const fs = require('fs');
const path = require('path');
const { URL } = require('url');
const { createVideo, getTask } = require('../scripts/video-generator');

const HOST = '127.0.0.1';
const PORT = Number(process.env.PORT || 3785);
const ROOT_DIR = path.join(__dirname, 'public');
const DATA_DIR = path.join(__dirname, 'data');
const HISTORY_FILE = path.join(DATA_DIR, 'history.json');
const OUTPUT_ROOT = path.join(__dirname, '..', 'scripts', 'output');
const UPLOAD_ROOT = path.join(DATA_DIR, 'uploads');
const POLL_INTERVAL_MS = 4000;
const MAX_BODY_SIZE = 25 * 1024 * 1024;

fs.mkdirSync(DATA_DIR, { recursive: true });
fs.mkdirSync(OUTPUT_ROOT, { recursive: true });
fs.mkdirSync(UPLOAD_ROOT, { recursive: true });

const clients = new Set();
const activeJobs = new Map();

function nowIso() {
  return new Date().toISOString();
}

function calculateElapsedSeconds(startedAt, endedAt = nowIso()) {
  const startMs = new Date(startedAt).getTime();
  const endMs = new Date(endedAt).getTime();
  if (!Number.isFinite(startMs) || !Number.isFinite(endMs) || endMs < startMs) return null;
  return Math.round((endMs - startMs) / 1000);
}

function ensureHistoryFile() {
  if (!fs.existsSync(HISTORY_FILE)) fs.writeFileSync(HISTORY_FILE, '[]\n');
}

function readHistory() {
  ensureHistoryFile();
  try {
    return JSON.parse(fs.readFileSync(HISTORY_FILE, 'utf8'));
  } catch {
    return [];
  }
}

function writeHistory(items) {
  fs.writeFileSync(HISTORY_FILE, JSON.stringify(items, null, 2));
}

function sendJson(res, statusCode, data) {
  res.writeHead(statusCode, {
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store',
  });
  res.end(JSON.stringify(data));
}

function sendEvent(payload) {
  const message = `data: ${JSON.stringify(payload)}\n\n`;
  for (const client of clients) client.write(message);
}

function addHistoryItem(item) {
  const history = readHistory();
  history.unshift(item);
  writeHistory(history);
  sendEvent({ type: 'history:create', item });
}

function updateHistoryItem(jobId, patch) {
  const history = readHistory();
  const index = history.findIndex((item) => item.jobId === jobId);
  if (index === -1) return null;
  const merged = { ...history[index], ...patch, updatedAt: nowIso() };
  if (merged.status === 'completed' && !merged.completedAt) merged.completedAt = merged.updatedAt;
  if (merged.status === 'completed' && (merged.totalElapsedSeconds == null || merged.totalElapsedSeconds < 0)) {
    merged.totalElapsedSeconds = calculateElapsedSeconds(merged.createdAt, merged.completedAt);
  }
  history[index] = merged;
  writeHistory(history);
  sendEvent({ type: 'history:update', item: history[index] });
  return history[index];
}

function removeFileIfExists(filePath) {
  if (!filePath) return;
  try {
    if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) fs.unlinkSync(filePath);
  } catch {}
}

function deleteHistoryItem(jobId) {
  const history = readHistory();
  const index = history.findIndex((item) => item.jobId === jobId);
  if (index === -1) return null;
  const [item] = history.splice(index, 1);
  activeJobs.delete(jobId);
  removeFileIfExists(item.localPath);
  if (item.imagePath && String(item.imagePath).startsWith(UPLOAD_ROOT)) removeFileIfExists(item.imagePath);
  writeHistory(history);
  sendEvent({ type: 'history:delete', jobId });
  return item;
}

function sanitizePath(value) {
  return value ? String(value).trim() : '';
}

function saveDataUrlImage(dataUrl, originalName) {
  const match = String(dataUrl || '').match(/^data:(image\/[a-zA-Z0-9.+-]+);base64,(.+)$/);
  if (!match) throw new Error('无效的图片数据');
  const extMap = { 'image/png': '.png', 'image/jpeg': '.jpg', 'image/webp': '.webp', 'image/gif': '.gif' };
  const ext = extMap[match[1]] || path.extname(originalName || '') || '.png';
  const fileName = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}${ext}`;
  const filePath = path.join(UPLOAD_ROOT, fileName);
  fs.writeFileSync(filePath, Buffer.from(match[2], 'base64'));
  return filePath;
}

function makeJobId() {
  return `job_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function mimeType(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  if (ext === '.html') return 'text/html; charset=utf-8';
  if (ext === '.css') return 'text/css; charset=utf-8';
  if (ext === '.js') return 'application/javascript; charset=utf-8';
  if (ext === '.json') return 'application/json; charset=utf-8';
  if (ext === '.mp4') return 'video/mp4';
  if (ext === '.png') return 'image/png';
  if (ext === '.jpg' || ext === '.jpeg') return 'image/jpeg';
  if (ext === '.webp') return 'image/webp';
  return 'application/octet-stream';
}

function serveFile(res, filePath) {
  if (!fs.existsSync(filePath)) {
    res.writeHead(404);
    res.end('Not found');
    return;
  }
  res.writeHead(200, { 'Content-Type': mimeType(filePath) });
  fs.createReadStream(filePath).pipe(res);
}

function isSafeLocalFile(filePath) {
  try {
    const resolved = path.resolve(filePath);
    return fs.existsSync(resolved) && fs.statSync(resolved).isFile();
  } catch {
    return false;
  }
}

async function readBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    let tooLarge = false;
    req.on('data', (chunk) => {
      if (tooLarge) return;
      body += chunk;
      if (body.length > MAX_BODY_SIZE) {
        tooLarge = true;
        reject(new Error('请求体过大：图片请尽量控制在 15MB 内'));
      }
    });
    req.on('end', () => {
      if (tooLarge) return;
      try {
        resolve(body ? JSON.parse(body) : {});
      } catch {
        reject(new Error('无效 JSON'));
      }
    });
    req.on('error', reject);
  });
}

function detectVideoUrl(response) {
  return response.video_url || response.url || null;
}

function detectProgress(response) {
  return Number(response.progress ?? 0);
}

function detectStatus(response) {
  return String(response.status || 'unknown').toLowerCase();
}

function localOutputPath(taskId) {
  const safe = String(taskId).replace(/[^a-zA-Z0-9._-]/g, '_').slice(-40);
  return path.join(OUTPUT_ROOT, `veo-video-${safe}.mp4`);
}

function downloadToFile(url, outputPath) {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(outputPath);
    require('https').get(url, (response) => {
      if (response.statusCode !== 200) {
        reject(new Error(`下载失败: ${response.statusCode}`));
        return;
      }
      response.pipe(file);
      file.on('finish', () => file.close(() => resolve(outputPath)));
    }).on('error', (error) => {
      fs.unlink(outputPath, () => {});
      reject(error);
    });
  });
}

async function watchJob(job) {
  activeJobs.set(job.jobId, job);
  while (activeJobs.has(job.jobId)) {
    try {
      const response = await getTask(job.taskId);
      const status = detectStatus(response);
      const progress = detectProgress(response);
      const videoUrl = detectVideoUrl(response);

      updateHistoryItem(job.jobId, { status, progress, remoteUrl: videoUrl, rawStatus: response });

      if (status === 'completed' && videoUrl) {
        const completedAt = nowIso();
        const localPath = localOutputPath(job.taskId);
        await downloadToFile(videoUrl, localPath);
        updateHistoryItem(job.jobId, {
          status: 'completed',
          progress: 100,
          localPath,
          videoPath: `/output/${path.basename(localPath)}`,
          remoteUrl: videoUrl,
          completedAt,
          totalElapsedSeconds: calculateElapsedSeconds(job.createdAt, completedAt),
        });
        activeJobs.delete(job.jobId);
        return;
      }

      if (status === 'failed' || status === 'error') {
        updateHistoryItem(job.jobId, { status: 'failed', error: response.error || '生成失败', rawStatus: response });
        activeJobs.delete(job.jobId);
        return;
      }
    } catch (error) {
      updateHistoryItem(job.jobId, { status: 'failed', error: error.message });
      activeJobs.delete(job.jobId);
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
  }
}

async function handleGenerate(req, res) {
  try {
    const body = await readBody(req);
    const mode = body.mode === 'image' ? 'image' : 'text';
    const prompt = String(body.prompt || '').trim();
    const aspectRatio = String(body.aspectRatio || '16:9');
    const seconds = Number(body.seconds || 5);
    const imagePath = sanitizePath(body.imagePath);
    const imageDataUrl = String(body.imageDataUrl || '');
    const imageFileName = String(body.imageFileName || 'upload.png');
    const imageSource = imageDataUrl ? saveDataUrlImage(imageDataUrl, imageFileName) : imagePath;

    if (!prompt) return sendJson(res, 400, { error: '提示词不能为空' });
    if (mode === 'image' && !imageSource) return sendJson(res, 400, { error: '图生视频需要本地图片或远程 URL' });

    const jobId = makeJobId();
    const createdAt = nowIso();
    addHistoryItem({
      jobId,
      taskId: null,
      mode,
      prompt,
      imagePath: mode === 'image' ? imageSource : null,
      aspectRatio,
      seconds,
      model: 'veo_3_1-fast-4K',
      status: 'submitting',
      progress: 0,
      createdAt,
      updatedAt: createdAt,
      completedAt: null,
      totalElapsedSeconds: null,
      localPath: null,
      videoPath: null,
      remoteUrl: null,
      error: null,
    });

    const { taskId } = await createVideo(prompt, mode === 'image' ? imageSource : null, aspectRatio, seconds);
    updateHistoryItem(jobId, { taskId, status: 'processing', progress: 0 });
    watchJob({ jobId, taskId, createdAt }).catch((error) => updateHistoryItem(jobId, { status: 'failed', error: error.message }));
    sendJson(res, 200, { ok: true, jobId, taskId });
  } catch (error) {
    sendJson(res, 500, { error: error.message });
  }
}

async function handleDeleteHistory(req, res) {
  try {
    const body = await readBody(req);
    const jobId = String(body.jobId || '').trim();
    if (!jobId) return sendJson(res, 400, { error: '缺少 jobId' });
    const deleted = deleteHistoryItem(jobId);
    if (!deleted) return sendJson(res, 404, { error: '历史记录不存在' });
    sendJson(res, 200, { ok: true, jobId });
  } catch (error) {
    sendJson(res, 500, { error: error.message });
  }
}

function handleEvents(req, res) {
  res.writeHead(200, {
    'Content-Type': 'text/event-stream; charset=utf-8',
    'Cache-Control': 'no-cache, no-transform',
    Connection: 'keep-alive',
  });
  res.write('\n');
  clients.add(res);
  req.on('close', () => clients.delete(res));
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);

  if (req.method === 'GET' && url.pathname === '/api/history') return sendJson(res, 200, { items: readHistory() });
  if (req.method === 'POST' && url.pathname === '/api/generate') return handleGenerate(req, res);
  if (req.method === 'POST' && url.pathname === '/api/history/delete') return handleDeleteHistory(req, res);
  if (req.method === 'GET' && url.pathname === '/api/events') return handleEvents(req, res);
  if (req.method === 'GET' && url.pathname === '/api/preview') {
    const requested = url.searchParams.get('path');
    if (!requested || !isSafeLocalFile(requested)) {
      res.writeHead(404);
      res.end('Not found');
      return;
    }
    return serveFile(res, path.resolve(requested));
  }
  if (req.method === 'GET' && url.pathname.startsWith('/output/')) {
    return serveFile(res, path.join(OUTPUT_ROOT, path.basename(url.pathname)));
  }

  const filePath = url.pathname === '/' ? path.join(ROOT_DIR, 'index.html') : path.join(ROOT_DIR, url.pathname.replace(/^\/+/, ''));
  serveFile(res, filePath);
});

server.listen(PORT, HOST, () => {
  console.log(`Veo Tester running at http://${HOST}:${PORT}`);
});
