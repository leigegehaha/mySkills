#!/usr/bin/env node

/**
 * Grok Video 3 Generator — lingkeai.ai edition (2026-08-05)
 *
 * API base: https://api.lingkeai.ai
 *  - POST /v1/media/generate       提交任务（文生 / 图生）
 *  - GET  /v1/media/status         轮询结果（query 参数 task_id）
 *  - GET  /v1/skills/models?type=video  列出可用视频模型
 *
 * 模型策略（按时长自动选）：
 *   6  / 10 秒 → grok-video-3              （文生 + 图生，720P）
 *   15 秒     → grok-imagine-video-1.5-preview  （仅图生，720P，自带音频）
 *
 * 注意：grok-imagine-video-1.5-preview 的 display_name 是 "grok-video-3.5"，
 * 但提交时 model 字段必须用真实 ID "grok-imagine-video-1.5-preview"。
 *
 * 鉴权：Authorization: Bearer <API_KEY>
 */

const https = require('https');
const fs = require('fs');
const path = require('path');

const BASE_HOST = 'api.lingkeai.ai';
const DEFAULT_RATIO = '3:2';
const DEFAULT_SIZE = '720P';
const DEFAULT_DURATION = 6;
const POLL_INTERVAL_MS = 5000;
const MAX_POLL_MS = 15 * 60 * 1000; // 15 分钟（lingkeai 队列可能长）
// lingkeai 任务 ID 是纯数字
const TASK_ID_RE = /^\d+$/;

function getModelByDuration(duration) {
  const normalized = Number(duration || DEFAULT_DURATION);
  if (normalized === 15) return 'grok-imagine-video-1.5-preview';
  // 6s / 10s 都用 grok-video-3
  return 'grok-video-3';
}

function normalizeDuration(duration) {
  const normalized = Number(duration || DEFAULT_DURATION);
  if ([6, 10, 15].includes(normalized)) return normalized;
  return DEFAULT_DURATION;
}

function loadApiKeys() {
  const envPath = path.join(__dirname, '.env');
  if (!fs.existsSync(envPath)) {
    throw new Error('找不到 scripts/.env 文件');
  }
  const content = fs.readFileSync(envPath, 'utf-8');
  const match = content.match(/API_KEY=(.+)/);
  if (!match) {
    throw new Error('.env 文件中找不到 API_KEY');
  }
  return match[1].split(',').map((k) => k.trim()).filter((k) => k.length > 0);
}

const API_KEYS = loadApiKeys();
let currentKeyIndex = 0;

function getApiKey() {
  return API_KEYS[currentKeyIndex % API_KEYS.length];
}

function switchApiKey() {
  if (API_KEYS.length <= 1) return false;
  currentKeyIndex = (currentKeyIndex + 1) % API_KEYS.length;
  console.log(`\n🔄 切换 API Key: key${currentKeyIndex + 1}/${API_KEYS.length}`);
  return true;
}

function requestJson(method, apiPath, body) {
  return new Promise((resolve, reject) => {
    const payload = body ? JSON.stringify(body) : null;
    const options = {
      hostname: BASE_HOST,
      port: 443,
      path: apiPath,
      method,
      headers: {
        Authorization: `Bearer ${getApiKey()}`,
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
        } catch (e) {
          // 保持原始字符串
        }

        // lingkeai 业务层成功码是 code=200，HTTP 也必须是 2xx
        if (res.statusCode < 200 || res.statusCode >= 300) {
          const error = new Error(`请求失败: HTTP ${res.statusCode} ${apiPath}`);
          error.response = parsed;
          error.statusCode = res.statusCode;
          reject(error);
          return;
        }

        // 业务层失败（code != 200）
        if (typeof parsed === 'object' && parsed !== null && 'code' in parsed && parsed.code !== 200) {
          const error = new Error(parsed.msg || parsed.message || `业务失败: code=${parsed.code}`);
          error.response = parsed;
          reject(error);
          return;
        }

        resolve(parsed);
      });
    });

    req.on('error', reject);
    if (payload) req.write(payload);
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
  return cleaned || 'A short video';
}

function extractTaskId(response) {
  if (!response || typeof response !== 'object') return null;
  // lingkeai 响应：{code:200, data:{task_id: 数字, ...}, msg}
  if (response.data && response.data.task_id) return String(response.data.task_id);
  if (response.task_id) return String(response.task_id);
  if (response.id) return String(response.id);
  return null;
}

function getStatus(result) {
  return (
    result.state ||
    result.status ||
    result.data?.state ||
    result.data?.status ||
    'unknown'
  );
}

function getProgress(result) {
  const progress =
    result.progress ?? result.percentage ?? result.data?.progress ?? result.data?.percentage ?? 0;
  return Number.isFinite(Number(progress)) ? Number(progress) : 0;
}

function getStatusGroup(result) {
  return result.status_group || result.data?.status_group || '';
}

function getError(result) {
  return result.error || result.data?.error || '';
}

function getResultUrl(result) {
  return result.result_url || result.data?.result_url || null;
}

function getCost(result) {
  const cost = result.cost ?? result.data?.cost;
  return typeof cost === 'number' ? cost : 0;
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

  // grok-imagine-video-1.5-preview 强制要求图片
  if (model === 'grok-imagine-video-1.5-preview' && images.length === 0) {
    throw new Error('grok-imagine-video-1.5-preview (grok-video-3.5) 仅支持图生视频，必须提供首帧参考图');
  }

  const payload = {
    model,
    prompt: normalizePrompt(prompt),
    aspect_ratio: aspectRatio || DEFAULT_RATIO,
    size: (size || DEFAULT_SIZE).toUpperCase(),
    seconds: normalizedDuration,
    images,
  };

  console.log('\n🎬 创建视频任务...');
  console.log(`模型: ${model}${model === 'grok-imagine-video-1.5-preview' ? ' (display: grok-video-3.5)' : ''}`);
  console.log(`提示词: ${payload.prompt}`);
  console.log(`比例: ${payload.aspect_ratio}`);
  console.log(`清晰度: ${payload.size}`);
  console.log(`时长: ${normalizedDuration} 秒`);
  if (images.length > 0) {
    console.log(`模式: 图生视频 (${isRemoteUrl(imageSource) ? '远程图片' : '本地图片'})`);
  } else {
    console.log('模式: 文生视频');
  }

  let lastError = null;
  for (let attempt = 0; attempt < API_KEYS.length * 2; attempt++) {
    try {
      const response = await requestJson('POST', '/v1/media/generate', payload);
      const taskId = extractTaskId(response);
      if (!taskId) {
        throw new Error(`创建任务失败，未返回 task_id: ${JSON.stringify(response)}`);
      }
      console.log(`\n✅ 任务已提交: ${taskId} (key${currentKeyIndex + 1})`);
      console.log(`状态: ${getStatus(response)} | ${getStatusGroup(response)}`);
      return { taskId, response };
    } catch (error) {
      lastError = error;
      const msg = error.message || '';
      // 限流 / 服务器错误 / 鉴权失败时切换 key 重试
      if (msg.includes('频率') || msg.includes('500') || msg.includes('503') || msg.includes('429') || msg.includes('401') || msg.includes('请求失败')) {
        if (switchApiKey()) {
          console.log('  重试中...');
          await new Promise((r) => setTimeout(r, 3000));
          continue;
        }
      }
      throw error;
    }
  }
  throw lastError || new Error('所有 API Key 均已尝试，创建任务失败');
}

async function getTask(taskId) {
  if (!TASK_ID_RE.test(String(taskId))) {
    throw new Error(`无效的 task_id: ${taskId}（lingkeai 任务 ID 应为纯数字）`);
  }
  const apiPath = `/v1/media/status?task_id=${encodeURIComponent(taskId)}`;
  return { response: await requestJson('GET', apiPath), apiPath };
}

function createOutputPath(taskId) {
  const outputDir = path.join(__dirname, 'output');
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }
  return path.join(outputDir, `grok-video-${taskId}.mp4`);
}

function downloadVideo(url, outputPath) {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(outputPath);
    https
      .get(url, (response) => {
        if (response.statusCode !== 200) {
          reject(new Error(`下载失败: HTTP ${response.statusCode}`));
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
  let lastState = '';

  while (Date.now() - startTime < MAX_POLL_MS) {
    let result;
    try {
      const r = await getTask(taskId);
      result = r.response;
    } catch (error) {
      console.log(`\n⚠️ 轮询错误: ${error.message}，5s 后重试`);
      await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
      continue;
    }

    // lingkeai 返回结构：{code, data:{...}, msg} 或直接 {state,...}
    const data = result.data || result;
    const state = getStatus(data);
    const statusText = data.status || '';
    const statusGroup = getStatusGroup(data);
    const progress = getProgress(data);
    const resultUrl = getResultUrl(data);
    const error = getError(data);
    const elapsed = Math.floor((Date.now() - startTime) / 1000);

    if (state !== lastState) {
      console.log(`\n  [${elapsed}s] state=${state} | status_group=${statusGroup} | status=${statusText}`);
      lastState = state;
    }

    const barLength = 30;
    const filled = Math.floor((progress / 100) * barLength);
    const empty = barLength - filled;
    const bar = '█'.repeat(Math.max(0, filled)) + '░'.repeat(Math.max(0, empty));
    process.stdout.write(`\r[${elapsed}s] [${bar}] ${progress}% | ${state} | ${statusGroup || statusText}   `);

    // 成功：state=success 且有 result_url
    if (String(state).toLowerCase() === 'success' && resultUrl) {
      console.log('\n\n✅ 视频生成完成!');
      console.log(`📹 视频链接: ${resultUrl}`);
      const cost = getCost(data);
      if (cost > 0) console.log(`💰 本次消耗: ¥${cost}`);
      const outputPath = createOutputPath(taskId);
      console.log('\n📥 开始下载视频...');
      await downloadVideo(resultUrl, outputPath);
      console.log('\n🎉 全部完成!');
      console.log(`📁 本地文件: ${outputPath}`);
      return { taskId, videoUrl: resultUrl, localPath: outputPath, cost };
    }

    // 失败
    if (String(state).toLowerCase() === 'failed' || String(state).toLowerCase() === 'error') {
      console.log('');
      throw new Error(`生成失败: state=${state}, error=${error || JSON.stringify(data)}`);
    }

    await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
  }

  throw new Error('轮询超时（15 分钟）');
}

function printHelp() {
  console.log(`
Grok Video 3 Generator (lingkeai.ai)

用法:
  node video-generator.js text "提示词" [比例] [清晰度] [时长]
  node video-generator.js image "图片URL或本地路径" "提示词" [比例] [清晰度] [时长]
  node video-generator.js query 任务ID

模型选择 (按时长):
  6 / 10 秒 → grok-video-3                  (文生 + 图生, 720P)
  15 秒     → grok-imagine-video-1.5-preview  (仅图生, 720P, 自带音频)

比例: 16:9, 9:16, 1:1, 4:3, 3:4, 3:2, 2:3   (默认 3:2)
清晰度: 720P, 1080P                          (默认 720P)
时长: 6, 10, 15                              (默认 6)

示例:
  # 文生视频
  node video-generator.js text "小猫在吃鱼" 3:2 720P 6

  # 图生视频（远程 URL）
  node video-generator.js image "https://example.com/cat.png" "让小猫抬头并摆尾" 3:2 720P 6

  # 图生视频（本地图片）
  node video-generator.js image ./cat.png "让小猫看向镜头" 16:9 720P 6

  # 15 秒长视频（grok-imagine-video-1.5-preview，需要图片）
  node video-generator.js image ./cat.png "小猫在草地上自由奔跑 15 秒" 3:2 720P 15

  # 查询任务
  node video-generator.js query 94758701
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
      const { response } = await getTask(taskId);
      console.log(JSON.stringify(response, null, 2));
      return;
    }

    if (cmd === 'models') {
      const r = await requestJson('GET', '/v1/skills/models?type=video');
      console.log(JSON.stringify(r, null, 2));
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
  getModelByDuration,
  normalizeDuration,
  DEFAULT_RATIO,
  DEFAULT_SIZE,
  DEFAULT_DURATION,
  BASE_HOST,
};

if (require.main === module) {
  main();
}
