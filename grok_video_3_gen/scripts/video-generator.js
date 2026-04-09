#!/usr/bin/env node

const https = require('https');
const fs = require('fs');
const path = require('path');

const BASE_HOST = 'api.vectorengine.ai';
const DEFAULT_RATIO = '3:2';
const DEFAULT_SIZE = '720P';
const DEFAULT_DURATION = 6;
const POLL_INTERVAL_MS = 5000;
const MAX_POLL_MS = 10 * 60 * 1000;

function getModelByDuration(duration) {
  const normalized = Number(duration || DEFAULT_DURATION);
  if (normalized === 10) return 'grok-video-3-10s';
  if (normalized === 15) return 'grok-video-3-15s';
  return 'grok-video-3';
}

function normalizeDuration(duration) {
  const normalized = Number(duration || DEFAULT_DURATION);
  if ([6, 10, 15].includes(normalized)) return normalized;
  return DEFAULT_DURATION;
}

function loadApiKey() {
  const envPath = path.join(__dirname, '.env');
  if (!fs.existsSync(envPath)) {
    throw new Error('找不到 scripts/.env 文件');
  }
  const content = fs.readFileSync(envPath, 'utf-8');
  const match = content.match(/API_KEY=(.+)/);
  if (!match) {
    throw new Error('.env 文件中找不到 API_KEY');
  }
  return match[1].trim();
}

const API_KEY = loadApiKey();

function requestJson(method, apiPath, body) {
  return new Promise((resolve, reject) => {
    const payload = body ? JSON.stringify(body) : null;
    const options = {
      hostname: BASE_HOST,
      port: 443,
      path: apiPath,
      method,
      headers: {
        Authorization: `Bearer ${API_KEY}`,
        Accept: 'application/json',
      },
    };

    if (payload) {
      options.headers['Content-Type'] = 'application/json';
      options.headers['Content-Length'] = Buffer.byteLength(payload);
    }

    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => {
        data += chunk;
      });
      res.on('end', () => {
        let parsed = data;
        try {
          parsed = data ? JSON.parse(data) : {};
        } catch {}

        if (res.statusCode < 200 || res.statusCode >= 300) {
          const error = new Error(`请求失败: ${res.statusCode} ${apiPath}`);
          error.response = parsed;
          error.statusCode = res.statusCode;
          reject(error);
          return;
        }

        resolve(parsed);
      });
    });

    req.on('error', reject);
    if (payload) {
      req.write(payload);
    }
    req.end();
  });
}

function isRemoteUrl(value) {
  return /^https?:\/\//i.test(value);
}

function guessMimeType(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  if (ext === '.png') return 'image/png';
  if (ext === '.webp') return 'image/webp';
  if (ext === '.gif') return 'image/gif';
  return 'image/jpeg';
}

function imageToInlineDataUrl(filePath) {
  const mimeType = guessMimeType(filePath);
  const buffer = fs.readFileSync(filePath);
  return `data:${mimeType};base64,${buffer.toString('base64')}`;
}

function normalizePrompt(prompt) {
  const cleaned = (prompt || '').trim();
  if (!cleaned) return '--mode=custom';
  return cleaned.includes('--mode=custom') ? cleaned : `${cleaned} --mode=custom`;
}

function normalizeTaskId(response) {
  return response.task_id || response.id || response.data?.task_id || response.data?.id;
}

function extractVideoUrl(value) {
  if (!value) return null;
  if (typeof value === 'string' && /^https?:\/\//i.test(value) && /\.(mp4|mov|webm)(\?|$)/i.test(value)) {
    return value;
  }
  if (Array.isArray(value)) {
    for (const item of value) {
      const found = extractVideoUrl(item);
      if (found) return found;
    }
    return null;
  }
  if (typeof value === 'object') {
    const directKeys = ['video_url', 'url', 'download_url', 'file_url', 'result_url'];
    for (const key of directKeys) {
      const found = extractVideoUrl(value[key]);
      if (found) return found;
    }
    for (const nestedValue of Object.values(value)) {
      const found = extractVideoUrl(nestedValue);
      if (found) return found;
    }
  }
  return null;
}

function getStatus(result) {
  return (
    result.status ||
    result.state ||
    result.data?.status ||
    result.data?.state ||
    'unknown'
  );
}

function getProgress(result) {
  const progress =
    result.progress ??
    result.percentage ??
    result.data?.progress ??
    result.data?.percentage ??
    0;
  return Number.isFinite(Number(progress)) ? Number(progress) : 0;
}

async function createVideo(prompt, imageSource, aspectRatio, size, duration) {
  const images = [];
  const normalizedDuration = normalizeDuration(duration);
  const model = getModelByDuration(normalizedDuration);

  if (imageSource) {
    if (isRemoteUrl(imageSource)) {
      images.push(imageSource);
    } else {
      if (!fs.existsSync(imageSource)) {
        throw new Error(`图片不存在: ${imageSource}`);
      }
      images.push(imageToInlineDataUrl(imageSource));
    }
  }

  const payload = {
    model,
    prompt: normalizePrompt(prompt),
    aspect_ratio: aspectRatio || DEFAULT_RATIO,
    size: (size || DEFAULT_SIZE).toUpperCase(),
    images,
  };

  console.log('\n🎬 创建视频任务...');
  console.log(`模型: ${model}`);
  console.log(`提示词: ${payload.prompt}`);
  console.log(`比例: ${payload.aspect_ratio}`);
  console.log(`清晰度: ${payload.size}`);
  console.log(`时长: ${normalizedDuration} 秒`);
  if (images.length > 0) {
    console.log(`模式: 图生视频 (${isRemoteUrl(imageSource) ? '远程图片' : '本地图片'})`);
  } else {
    console.log('模式: 文生视频');
  }

  const response = await requestJson('POST', '/v1/video/create', payload);
  const taskId = normalizeTaskId(response);
  if (!taskId) {
    throw new Error(`创建任务失败，未返回任务 ID: ${JSON.stringify(response)}`);
  }

  console.log(`\n✅ 任务已提交: ${taskId}`);
  console.log(`状态: ${getStatus(response)}`);
  return { taskId, response };
}

async function getTask(taskId) {
  const candidates = [
    `/v1/video/${encodeURIComponent(taskId)}`,
    `/v1/video/status/${encodeURIComponent(taskId)}`,
    `/v1/video/status?task_id=${encodeURIComponent(taskId)}`,
    `/v1/videos/${encodeURIComponent(taskId)}`,
  ];

  let lastError = null;
  for (const apiPath of candidates) {
    try {
      const response = await requestJson('GET', apiPath);
      return { response, apiPath };
    } catch (error) {
      lastError = error;
    }
  }

  if (lastError) {
    throw new Error(`查询任务失败: ${lastError.message}`);
  }
  throw new Error('查询任务失败');
}

function createOutputPath(taskId) {
  const outputDir = path.join(__dirname, 'output');
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }
  const safeId = taskId.replace(/[^a-zA-Z0-9._-]/g, '_').slice(-40);
  return path.join(outputDir, `grok-video-${safeId}.mp4`);
}

function downloadVideo(url, outputPath) {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(outputPath);
    https
      .get(url, (response) => {
        if (response.statusCode !== 200) {
          reject(new Error(`下载失败: ${response.statusCode}`));
          return;
        }

        let downloaded = 0;
        const total = parseInt(response.headers['content-length'] || '0', 10);
        response.on('data', (chunk) => {
          downloaded += chunk.length;
          if (total > 0) {
            const percent = Math.floor((downloaded / total) * 100);
            process.stdout.write(`\r📥 下载进度: ${percent}%`);
          }
        });

        response.pipe(file);
        file.on('finish', () => {
          file.close();
          console.log(`\n✅ 视频已保存到: ${outputPath}`);
          resolve(outputPath);
        });
      })
      .on('error', (error) => {
        fs.unlink(outputPath, () => {});
        reject(error);
      });
  });
}

async function pollAndDownload(taskId) {
  console.log('\n⏳ 开始轮询，等待视频生成...\n');
  const startTime = Date.now();

  while (Date.now() - startTime < MAX_POLL_MS) {
    const { response, apiPath } = await getTask(taskId);
    const status = getStatus(response);
    const progress = getProgress(response);
    const elapsed = Math.floor((Date.now() - startTime) / 1000);
    const videoUrl = extractVideoUrl(response);

    const barLength = 30;
    const filled = Math.floor((progress / 100) * barLength);
    const empty = barLength - filled;
    const bar = '█'.repeat(Math.max(0, filled)) + '░'.repeat(Math.max(0, empty));

    process.stdout.write(`\r[${elapsed}s] [${bar}] ${progress}% | ${status} | ${apiPath}   `);

    if (['completed', 'success', 'succeeded', 'finished'].includes(String(status).toLowerCase()) || videoUrl) {
      console.log('\n\n✅ 视频生成完成!');
      if (!videoUrl) {
        console.log(JSON.stringify(response, null, 2));
        throw new Error('任务已完成，但未找到可下载的视频 URL');
      }
      console.log(`📹 视频链接: ${videoUrl}`);
      const outputPath = createOutputPath(taskId);
      console.log('\n📥 开始下载视频...');
      await downloadVideo(videoUrl, outputPath);
      console.log('\n🎉 全部完成!');
      console.log(`📁 本地文件: ${outputPath}`);
      return { taskId, videoUrl, localPath: outputPath };
    }

    if (['failed', 'error', 'cancelled', 'canceled'].includes(String(status).toLowerCase())) {
      throw new Error(`生成失败: ${JSON.stringify(response)}`);
    }

    await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
  }

  throw new Error('轮询超时（10分钟）');
}

function printHelp() {
  console.log(`
Grok Video 3 Generator

用法:
  node video-generator.js text "提示词" [比例] [清晰度] [时长]
  node video-generator.js image "图片URL或本地路径" "提示词" [比例] [清晰度] [时长]
  node video-generator.js query 任务ID

比例:
  16:9, 9:16, 1:1, 4:3, 3:4, 3:2, 2:3

清晰度:
  720P, 1080P

时长:
  6, 10, 15

示例:
  node video-generator.js text "小猫在吃鱼" 3:2 720P 6
  node video-generator.js image ./cat.png "让小猫看向镜头" 16:9 1080P 10
  node video-generator.js image "https://example.com/cat.png" "让小猫轻轻摆尾" 3:2 720P 15
  `);
}

async function main() {
  const args = process.argv.slice(2);
  const cmd = args[0];

  try {
    if (cmd === 'text') {
      const prompt = args[1];
      const ratio = args[2] || DEFAULT_RATIO;
      const size = args[3] || DEFAULT_SIZE;
      const duration = normalizeDuration(args[4] || DEFAULT_DURATION);
      if (!prompt) {
        printHelp();
        process.exit(1);
      }
      const { taskId } = await createVideo(prompt, null, ratio, size, duration);
      await pollAndDownload(taskId);
      return;
    }

    if (cmd === 'image') {
      const imageSource = args[1];
      const prompt = args[2] || '';
      const ratio = args[3] || DEFAULT_RATIO;
      const size = args[4] || DEFAULT_SIZE;
      const duration = normalizeDuration(args[5] || DEFAULT_DURATION);
      if (!imageSource) {
        printHelp();
        process.exit(1);
      }
      const { taskId } = await createVideo(prompt, imageSource, ratio, size, duration);
      await pollAndDownload(taskId);
      return;
    }

    if (cmd === 'query') {
      const taskId = args[1];
      if (!taskId) {
        printHelp();
        process.exit(1);
      }
      const result = await getTask(taskId);
      console.log(JSON.stringify(result.response, null, 2));
      return;
    }

    printHelp();
  } catch (error) {
    console.error(`\n❌ 错误: ${error.message}`);
    if (error.response) {
      console.error(JSON.stringify(error.response, null, 2));
    }
    process.exit(1);
  }
}

module.exports = {
  createVideo,
  getTask,
  pollAndDownload,
  normalizePrompt,
  extractVideoUrl,
  getStatus,
  getProgress,
  createOutputPath,
  DEFAULT_RATIO,
  DEFAULT_SIZE,
  DEFAULT_DURATION,
  normalizeDuration,
  getModelByDuration,
};

if (require.main === module) {
  main();
}
