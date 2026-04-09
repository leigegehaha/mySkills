#!/usr/bin/env node

const http = require('http');
const fs = require('fs');
const path = require('path');
const { URL } = require('url');
const { spawn } = require('child_process');
const {
  createVideo,
  getTask,
  extractVideoUrl,
  getStatus,
  getProgress,
  normalizeDuration,
  getModelByDuration,
} = require('../../grok_video_3_gen/scripts/video-generator');

const HOST = '127.0.0.1';
const PORT = Number(process.env.PORT || 3786);
const ROOT_DIR = path.join(__dirname, 'public');
const DATA_DIR = path.join(__dirname, 'data');
const HISTORY_FILE = path.join(DATA_DIR, 'history.json');
const UPLOAD_ROOT = path.join(DATA_DIR, 'uploads');
const IMAGE_OUTPUT_ROOT = path.join(DATA_DIR, 'generated-images');
const VIDEO_OUTPUT_ROOT = path.join(DATA_DIR, 'generated-videos');
const MAX_BODY_SIZE = 25 * 1024 * 1024;
const POLL_INTERVAL_MS = 4000;
const GEMINI_SKILL_DIR = path.resolve(__dirname, '..', '..', 'gemini-image-gen');

fs.mkdirSync(DATA_DIR, { recursive: true });
fs.mkdirSync(UPLOAD_ROOT, { recursive: true });
fs.mkdirSync(IMAGE_OUTPUT_ROOT, { recursive: true });
fs.mkdirSync(VIDEO_OUTPUT_ROOT, { recursive: true });
if (!fs.existsSync(HISTORY_FILE)) fs.writeFileSync(HISTORY_FILE, '[]\n');

const clients = new Set();
const activeJobs = new Map();

function nowIso() {
  return new Date().toISOString();
}

function calcElapsed(startedAt, endedAt = nowIso()) {
  const startMs = new Date(startedAt).getTime();
  const endMs = new Date(endedAt).getTime();
  if (!Number.isFinite(startMs) || !Number.isFinite(endMs) || endMs < startMs) return null;
  return Math.round((endMs - startMs) / 1000);
}

function readHistory() {
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

function updateHistoryItem(jobId, patch) {
  const history = readHistory();
  const index = history.findIndex((item) => item.jobId === jobId);
  if (index === -1) return null;
  const merged = { ...history[index], ...patch, updatedAt: nowIso() };
  if (merged.status === 'completed' && !merged.completedAt) merged.completedAt = merged.updatedAt;
  if (merged.status === 'completed' && !Number.isFinite(Number(merged.totalElapsedSeconds))) {
    merged.totalElapsedSeconds = calcElapsed(merged.createdAt, merged.completedAt);
  }
  history[index] = merged;
  writeHistory(history);
  sendEvent({ type: 'history:update', item: merged });
  return merged;
}

function addHistoryItem(item) {
  const history = readHistory();
  history.unshift(item);
  writeHistory(history);
  sendEvent({ type: 'history:create', item });
}

function removeFileIfExists(filePath) {
  try {
    if (filePath && fs.existsSync(filePath) && fs.statSync(filePath).isFile()) fs.unlinkSync(filePath);
  } catch {}
}

function deleteHistoryItem(jobId) {
  const history = readHistory();
  const index = history.findIndex((item) => item.jobId === jobId);
  if (index === -1) return null;
  const [item] = history.splice(index, 1);
  activeJobs.delete(jobId);
  removeFileIfExists(item.sourceImagePath);
  removeFileIfExists(item.generatedImageLocalPath);
  removeFileIfExists(item.generatedVideoLocalPath);
  writeHistory(history);
  sendEvent({ type: 'history:delete', jobId });
  return item;
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
        reject(new Error('请求体过大'));
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

function saveDataUrlImage(dataUrl, originalName) {
  const match = String(dataUrl || '').match(/^data:(image\/[a-zA-Z0-9.+-]+);base64,(.+)$/);
  if (!match) throw new Error('无效图片数据');
  const mimeType = match[1];
  const base64 = match[2];
  const extMap = { 'image/png': '.png', 'image/jpeg': '.jpg', 'image/webp': '.webp', 'image/gif': '.gif' };
  const ext = extMap[mimeType] || path.extname(originalName || '') || '.png';
  const fileName = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}${ext}`;
  const filePath = path.join(UPLOAD_ROOT, fileName);
  fs.writeFileSync(filePath, Buffer.from(base64, 'base64'));
  return filePath;
}

function sanitizePath(inputPath) {
  return String(inputPath || '').trim();
}

function makeJobId() {
  return `job_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function shellEscape(value) {
  return `'${String(value).replace(/'/g, `'\\''`)}'`;
}

function buildImagePrompt({ scene, dialogue, shotStyle }) {
  const base = `Use the provided face as the identity reference. Create a realistic vertical 9:16 scene based on this description: ${scene}. Keep strong identity consistency with the reference face, photorealistic, high detail, natural body proportions, clean composition, no subtitles, no text.`;
  if (shotStyle === 'selfie') {
    return `这是一张iPhone前置摄像头拍摄的自拍照片儿。 ${base} The person is personally holding the phone. This must look like a true iPhone front-camera selfie photo with close arm-length framing, slight front-camera wide-angle feel, and part of the hand, wrist, or forearm subtly visible at the frame edge. It must not look like a third-person shot.`;
  }
  if (shotStyle === 'rear-fixed') {
    return `${base} The scene is filmed by a fixed smartphone rear camera on a tripod or stand, not a selfie frame.`;
  }
  if (shotStyle === 'rear-handheld') {
    return `${base} The scene is filmed by a smartphone rear camera with natural handheld motion, not a selfie frame.`;
  }
  return `${base} The shot should feel cinematic and natural.`;
}

function buildVideoPrompt({ scene, dialogue, shotStyle, aspectRatio }) {
  const spokenLine = dialogue ? ` The person says in Chinese: '${dialogue}'.` : '';
  if (shotStyle === 'selfie') {
    return `Vertical ${aspectRatio} iPhone front-camera selfie video. The same person keeps the same face and appearance as the reference image and is holding the phone personally for the entire clip. Keep true selfie perspective from start to end, never switch to third-person view, and keep part of the hand, wrist, or forearm subtly visible near the edge of frame throughout so the phone-held selfie angle stays consistent. Close arm-length framing, slight iPhone wide-angle look, gentle handheld selfie shake. Scene: ${scene}.${spokenLine} Natural lip movement, no subtitles, maintain identity consistency.`;
  }
  if (shotStyle === 'rear-fixed') {
    return `Vertical ${aspectRatio} fixed smartphone rear-camera video. The same person keeps the same face and appearance as the reference image. The camera is fixed on a stand or tripod, not a selfie perspective. Scene: ${scene}.${spokenLine} Natural lip movement, no subtitles, maintain identity consistency.`;
  }
  if (shotStyle === 'rear-handheld') {
    return `Vertical ${aspectRatio} handheld smartphone rear-camera video. The same person keeps the same face and appearance as the reference image. The camera stays in rear-camera perspective with smooth natural handheld motion, not a selfie perspective. Scene: ${scene}.${spokenLine} Natural lip movement, no subtitles, maintain identity consistency.`;
  }
  return `Vertical ${aspectRatio} cinematic video. The same person keeps the same face and appearance as the reference image. Scene: ${scene}.${spokenLine} Natural motion, natural lip movement, no subtitles, maintain identity consistency.`;
}

function parseMediaPath(output) {
  const match = String(output || '').match(/MEDIA:\s*(.+)\s*$/m);
  return match ? match[1].trim() : null;
}

function runCommand(command) {
  return new Promise((resolve, reject) => {
    const child = spawn('/bin/zsh', ['-lc', `source ~/.zshrc >/dev/null 2>&1; ${command}`], {
      cwd: path.resolve(__dirname, '..'),
      env: process.env,
    });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (chunk) => { stdout += String(chunk); });
    child.stderr.on('data', (chunk) => { stderr += String(chunk); });
    child.on('error', reject);
    child.on('close', (code) => {
      if (code === 0) {
        resolve({ stdout, stderr });
      } else {
        reject(new Error((stderr || stdout || `命令失败，退出码 ${code}`).trim()));
      }
    });
  });
}

function outputVideoPath(taskId) {
  return path.join(VIDEO_OUTPUT_ROOT, `photo-scene-${taskId.replace(/[:/\\%]/g, '_')}.mp4`);
}

function downloadToFile(url, outputPath) {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(outputPath);
    const request = require('https').get(url, (response) => {
      if (response.statusCode !== 200) {
        reject(new Error(`下载失败: ${response.statusCode}`));
        return;
      }
      response.pipe(file);
      file.on('finish', () => file.close(() => resolve(outputPath)));
    });
    request.on('error', (error) => {
      fs.unlink(outputPath, () => {});
      reject(error);
    });
  });
}

async function generateImage(job) {
  const imagePrompt = buildImagePrompt(job);
  const outputName = `${Date.now()}-${job.jobId}.png`;
  const outputPath = path.join(IMAGE_OUTPUT_ROOT, outputName);
  const command = [
    'uv run',
    shellEscape(path.join(GEMINI_SKILL_DIR, 'scripts', 'generate.py')),
    '--config',
    shellEscape(path.join(GEMINI_SKILL_DIR, 'config.json')),
    '--prompt',
    shellEscape(imagePrompt),
    '--image',
    shellEscape(job.sourceImagePath),
    '--aspect-ratio',
    shellEscape(job.aspectRatio),
    '--output',
    shellEscape(outputPath),
  ].join(' ');

  const { stdout } = await runCommand(command);
  const mediaPath = parseMediaPath(stdout) || outputPath;
  return { imagePrompt, imagePath: mediaPath };
}

async function pollVideo(jobId, taskId, createdAt) {
  while (activeJobs.has(jobId)) {
    try {
      const { response } = await getTask(taskId);
      const status = String(getStatus(response)).toLowerCase();
      const progress = getProgress(response);
      const videoUrl = extractVideoUrl(response);

      updateHistoryItem(jobId, {
        stage: 'video',
        status,
        progress,
        remoteVideoUrl: videoUrl || null,
        taskId,
        rawStatus: response,
      });

      if (['completed', 'success', 'succeeded', 'finished'].includes(status) || videoUrl) {
        const localPath = outputVideoPath(taskId);
        if (videoUrl) await downloadToFile(videoUrl, localPath);
        updateHistoryItem(jobId, {
          stage: 'completed',
          status: 'completed',
          progress: 100,
          generatedVideoLocalPath: localPath,
          generatedVideoPath: `/video/${path.basename(localPath)}`,
          completedAt: nowIso(),
          totalElapsedSeconds: calcElapsed(createdAt),
        });
        activeJobs.delete(jobId);
        return;
      }

      if (['failed', 'error', 'cancelled', 'canceled'].includes(status)) {
        updateHistoryItem(jobId, {
          status: 'failed',
          error: response.error || '视频生成失败',
        });
        activeJobs.delete(jobId);
        return;
      }
    } catch (error) {
      updateHistoryItem(jobId, { status: 'failed', error: error.message });
      activeJobs.delete(jobId);
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
  }
}

async function runPipeline(job) {
  activeJobs.set(job.jobId, true);
  try {
    updateHistoryItem(job.jobId, { stage: 'image', status: 'processing', progress: 5 });
    const { imagePrompt, imagePath } = await generateImage(job);
    updateHistoryItem(job.jobId, {
      stage: 'image_completed',
      progress: 30,
      imagePrompt,
      generatedImageLocalPath: imagePath,
      generatedImagePath: `/image/${path.basename(imagePath)}`,
    });

    const videoPrompt = buildVideoPrompt(job);
    updateHistoryItem(job.jobId, { stage: 'video_submitting', progress: 35, videoPrompt });
    const { taskId } = await createVideo(videoPrompt, imagePath, job.aspectRatio, job.size, job.duration);
    updateHistoryItem(job.jobId, {
      taskId,
      model: getModelByDuration(job.duration),
      status: 'processing',
      stage: 'video',
      progress: 40,
    });
    await pollVideo(job.jobId, taskId, job.createdAt);
  } catch (error) {
    updateHistoryItem(job.jobId, { status: 'failed', error: error.message });
    activeJobs.delete(job.jobId);
  }
}

async function handleGenerate(req, res) {
  try {
    const body = await readBody(req);
    const scene = String(body.scene || '').trim();
    const dialogue = String(body.dialogue || '').trim();
    const shotStyle = String(body.shotStyle || 'selfie').trim();
    const aspectRatio = String(body.aspectRatio || '9:16').trim();
    const size = String(body.size || '720P').toUpperCase();
    const duration = normalizeDuration(body.duration || 6);
    const imagePath = sanitizePath(body.imagePath);
    const imageDataUrl = String(body.imageDataUrl || '');
    const imageFileName = String(body.imageFileName || 'upload.png');
    const sourceImagePath = imageDataUrl ? saveDataUrlImage(imageDataUrl, imageFileName) : imagePath;

    if (!scene) {
      sendJson(res, 400, { error: '场景描述不能为空' });
      return;
    }
    if (!sourceImagePath || !fs.existsSync(sourceImagePath)) {
      sendJson(res, 400, { error: '请提供本地参考照片' });
      return;
    }

    const createdAt = nowIso();
    const jobId = makeJobId();
    const item = {
      jobId,
      taskId: null,
      scene,
      dialogue,
      shotStyle,
      aspectRatio,
      size,
      duration,
      model: getModelByDuration(duration),
      sourceImagePath,
      generatedImageLocalPath: null,
      generatedImagePath: null,
      generatedVideoLocalPath: null,
      generatedVideoPath: null,
      imagePrompt: null,
      videoPrompt: null,
      status: 'queued',
      stage: 'queued',
      progress: 0,
      createdAt,
      updatedAt: createdAt,
      completedAt: null,
      totalElapsedSeconds: null,
      error: null,
    };

    addHistoryItem(item);
    runPipeline(item).catch(() => {});
    sendJson(res, 200, { ok: true, jobId });
  } catch (error) {
    sendJson(res, 500, { error: error.message });
  }
}

async function handleDelete(req, res) {
  try {
    const body = await readBody(req);
    const jobId = String(body.jobId || '').trim();
    if (!jobId) return sendJson(res, 400, { error: '缺少 jobId' });
    const deleted = deleteHistoryItem(jobId);
    if (!deleted) return sendJson(res, 404, { error: '记录不存在' });
    sendJson(res, 200, { ok: true });
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

  if (req.method === 'GET' && url.pathname === '/api/history') {
    return sendJson(res, 200, { items: readHistory() });
  }
  if (req.method === 'POST' && url.pathname === '/api/generate') {
    return handleGenerate(req, res);
  }
  if (req.method === 'POST' && url.pathname === '/api/history/delete') {
    return handleDelete(req, res);
  }
  if (req.method === 'GET' && url.pathname === '/api/events') {
    return handleEvents(req, res);
  }
  if (req.method === 'GET' && url.pathname === '/api/preview') {
    const requested = url.searchParams.get('path');
    if (!requested || !isSafeLocalFile(requested)) {
      res.writeHead(404);
      res.end('Not found');
      return;
    }
    return serveFile(res, path.resolve(requested));
  }
  if (req.method === 'GET' && url.pathname.startsWith('/image/')) {
    return serveFile(res, path.join(IMAGE_OUTPUT_ROOT, path.basename(url.pathname)));
  }
  if (req.method === 'GET' && url.pathname.startsWith('/video/')) {
    return serveFile(res, path.join(VIDEO_OUTPUT_ROOT, path.basename(url.pathname)));
  }
  if (req.method === 'GET' && url.pathname.startsWith('/source/')) {
    return serveFile(res, path.join(UPLOAD_ROOT, path.basename(url.pathname)));
  }

  const filePath = url.pathname === '/'
    ? path.join(ROOT_DIR, 'index.html')
    : path.join(ROOT_DIR, url.pathname.replace(/^\/+/, ''));

  serveFile(res, filePath);
});

server.listen(PORT, HOST, () => {
  console.log(`Photo Scene Video Tester running at http://${HOST}:${PORT}`);
});
