#!/usr/bin/env node

/**
 * Veo Fast Video Generator
 * 使用 veo_3_1-fast-4K 模型生成视频
 * 自动生成轮询脚本，实时显示进度，完成后自动下载
 */

const https = require('https');
const fs = require('fs');
const path = require('path');

// 固定配置
const MODEL = 'veo_3_1-fast-4K';
const BASE_URL = 'https://api.vectorengine.ai';

// 加载 API Key
function loadApiKey() {
  const envPath = path.join(__dirname, '.env');
  if (!fs.existsSync(envPath)) {
    console.error('❌ 错误: 找不到 .env 文件');
    process.exit(1);
  }
  
  const content = fs.readFileSync(envPath, 'utf-8');
  const match = content.match(/API_KEY=(.+)/);
  if (!match) {
    console.error('❌ 错误: .env 文件中找不到 API_KEY');
    process.exit(1);
  }
  return match[1].trim();
}

const API_KEY = loadApiKey();

// 构建 multipart/form-data
function buildFormData(fields, boundary) {
  const parts = [];
  
  for (const [key, value] of Object.entries(fields)) {
    if (key === 'input_reference' && value) {
      const fileName = path.basename(value);
      const fileContent = fs.readFileSync(value);
      
      let header = `--${boundary}\r\n`;
      header += `Content-Disposition: form-data; name="${key}"; filename="${fileName}"\r\n`;
      header += `Content-Type: image/png\r\n\r\n`;
      
      parts.push(Buffer.from(header, 'utf-8'));
      parts.push(fileContent);
      parts.push(Buffer.from('\r\n', 'utf-8'));
    } else if (value !== undefined) {
      let part = `--${boundary}\r\n`;
      part += `Content-Disposition: form-data; name="${key}"\r\n\r\n`;
      part += value;
      part += '\r\n';
      parts.push(Buffer.from(part, 'utf-8'));
    }
  }
  
  parts.push(Buffer.from(`--${boundary}--\r\n`, 'utf-8'));
  return Buffer.concat(parts);
}

// POST 请求
function postForm(fields) {
  return new Promise((resolve, reject) => {
    const boundary = '----FormBoundary' + Date.now();
    const body = buildFormData(fields, boundary);
    
    const options = {
      hostname: 'api.vectorengine.ai',
      port: 443,
      path: '/v1/videos',
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'Content-Type': `multipart/form-data; boundary=${boundary}`,
        'Content-Length': body.length
      }
    };
    
    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          resolve(JSON.parse(data));
        } catch {
          resolve(data);
        }
      });
    });
    
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

// GET 请求查询状态
function getTask(taskId) {
  return new Promise((resolve, reject) => {
    const options = {
      hostname: 'api.vectorengine.ai',
      port: 443,
      path: `/v1/videos/${taskId}`,
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'Accept': 'application/json'
      }
    };
    
    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          resolve(JSON.parse(data));
        } catch {
          resolve(data);
        }
      });
    });
    
    req.on('error', reject);
    req.end();
  });
}

// 下载视频
function downloadVideo(url, outputPath) {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(outputPath);
    https.get(url, (response) => {
      if (response.statusCode !== 200) {
        reject(new Error(`下载失败: ${response.statusCode}`));
        return;
      }
      
      let downloaded = 0;
      const total = parseInt(response.headers['content-length'] || 0);
      
      response.on('data', (chunk) => {
        downloaded += chunk.length;
        if (total > 0) {
          const percent = Math.floor((downloaded / total) * 100);
          const downloadedMB = (downloaded/1024/1024).toFixed(1);
          const totalMB = (total/1024/1024).toFixed(1);
          process.stdout.write('\r📥 下载进度: ' + percent + '% (' + downloadedMB + 'MB / ' + totalMB + 'MB)');
        }
      });
      
      response.pipe(file);
      file.on('finish', () => {
        file.close();
        console.log('\n✅ 视频已保存到:', outputPath);
        resolve(outputPath);
      });
    }).on('error', (err) => {
      fs.unlink(outputPath, () => {});
      reject(err);
    });
  });
}

// 生成轮询脚本
function generatePollScript(taskId, prompt, size) {
  const scriptContent = `#!/usr/bin/env node

/**
 * 自动轮询脚本 - 任务ID: ${taskId}
 * 生成时间: ${new Date().toLocaleString()}
 */

const https = require('https');
const fs = require('fs');
const path = require('path');

const API_KEY = '${API_KEY}';
const TASK_ID = '${taskId}';

console.log('🎬 视频生成任务轮询');
console.log('任务ID:', TASK_ID);
console.log('提示词: ${prompt}');
console.log('比例: ${size}');
console.log('');

function getTask() {
  return new Promise((resolve, reject) => {
    const options = {
      hostname: 'api.vectorengine.ai',
      port: 443,
      path: '/v1/videos/' + TASK_ID,
      method: 'GET',
      headers: {
        'Authorization': 'Bearer ' + API_KEY,
        'Accept': 'application/json'
      }
    };
    
    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          resolve(JSON.parse(data));
        } catch {
          resolve(data);
        }
      });
    });
    
    req.on('error', reject);
    req.end();
  });
}

function downloadVideo(url, outputPath) {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(outputPath);
    https.get(url, (response) => {
      if (response.statusCode !== 200) {
        reject(new Error('下载失败: ' + response.statusCode));
        return;
      }
      
      let downloaded = 0;
      const total = parseInt(response.headers['content-length'] || 0);
      
      response.on('data', (chunk) => {
        downloaded += chunk.length;
        if (total > 0) {
          const percent = Math.floor((downloaded / total) * 100);
          process.stdout.write('\\r📥 下载进度: ' + percent + '%');
        }
      });
      
      response.pipe(file);
      file.on('finish', () => {
        file.close();
        console.log('\\n✅ 视频已保存:', outputPath);
        resolve(outputPath);
      });
    }).on('error', reject);
  });
}

async function main() {
  console.log('⏳ 开始轮询，等待视频生成...\\n');
  const startTime = Date.now();
  const maxTime = 600000; // 10分钟
  
  while (Date.now() - startTime < maxTime) {
    const result = await getTask();
    const status = result.status || 'unknown';
    const progress = result.progress ?? 0;
    const elapsed = Math.floor((Date.now() - startTime) / 1000);
    
    // 显示进度条
    const barLength = 30;
    const filled = Math.floor((progress / 100) * barLength);
    const empty = barLength - filled;
    const bar = '█'.repeat(filled) + '░'.repeat(empty);
    
    process.stdout.write('\\r[' + elapsed + 's] [' + bar + '] ' + progress + '% | ' + status + '  ');
    
    if (status === 'completed') {
      console.log('\\n\\n✅ 视频生成完成!');
      console.log('📹 视频链接:', result.video_url);
      
      // 下载视频
      const outputDir = path.join(__dirname, 'output');
      if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir, { recursive: true });
      
      const fileName = 'video-' + TASK_ID.split('_')[1].split('-')[0] + '.mp4';
      const outputPath = path.join(outputDir, fileName);
      
      console.log('\\n📥 开始下载视频...');
      await downloadVideo(result.video_url, outputPath);
      
      console.log('\\n🎉 全部完成!');
      console.log('📁 本地文件:', outputPath);
      return;
    }
    
    if (status === 'failed' || status === 'error') {
      console.error('\\n❌ 生成失败:', result);
      process.exit(1);
    }
    
    await new Promise(r => setTimeout(r, 5000));
  }
  
  console.error('\\n⏱️ 轮询超时');
  process.exit(1);
}

main().catch(console.error);
`;

  const scriptPath = path.join(__dirname, `poll-${taskId.split('_')[1].split('-')[0]}.js`);
  fs.writeFileSync(scriptPath, scriptContent);
  fs.chmodSync(scriptPath, 0o755);
  
  return scriptPath;
}

// 比例转换
function toSize(ratio) {
  const map = { '3:4': '3x4', '4:3': '4x3', '9:16': '9x16', '16:9': '16x9', '1:1': '1x1' };
  return map[ratio] || '16x9';
}

// 创建视频任务
async function createVideo(prompt, imagePath, ratio, seconds) {
  const size = toSize(ratio);
  
  const fields = {
    model: MODEL,
    prompt: prompt,
    seconds: String(seconds),
    size: size,
    watermark: 'false'
  };
  
  if (imagePath) fields.input_reference = imagePath;
  
  console.log(`\n🎬 创建视频任务...`);
  console.log(`模型: ${MODEL}`);
  console.log(`提示词: ${prompt}`);
  console.log(`时长: ${seconds}秒`);
  console.log(`比例: ${ratio} (${size})`);
  if (imagePath) console.log(`图片: ${imagePath}`);
  
  const res = await postForm(fields);
  
  if (res.id) {
    console.log(`\n✅ 任务已提交: ${res.id}`);
    console.log(`状态: ${res.status}`);
    
    // 生成轮询脚本
    const scriptPath = generatePollScript(res.id, prompt, ratio);
    console.log(`\n📄 轮询脚本已生成: ${path.basename(scriptPath)}`);
    console.log(`你可以运行: node ${path.basename(scriptPath)}`);
    
    return { taskId: res.id, scriptPath };
  }
  throw new Error(`创建失败: ${JSON.stringify(res)}`);
}

// 轮询任务直到完成
async function pollAndDownload(taskId, prompt, size) {
  console.log('\n⏳ 开始轮询，等待视频生成...\n');
  const startTime = Date.now();
  const maxTime = 600000; // 10分钟
  
  while (Date.now() - startTime < maxTime) {
    const result = await getTask(taskId);
    const status = result.status || 'unknown';
    const progress = result.progress ?? 0;
    const elapsed = Math.floor((Date.now() - startTime) / 1000);
    
    // 显示进度条
    const barLength = 30;
    const filled = Math.floor((progress / 100) * barLength);
    const empty = barLength - filled;
    const bar = '█'.repeat(filled) + '░'.repeat(empty);
    
    process.stdout.write(`\r[${elapsed}s] [${bar}] ${progress}% | ${status}  `);
    
    if (status === 'completed') {
      console.log('\n\n✅ 视频生成完成!');
      console.log('📹 视频链接:', result.video_url);
      
      // 下载视频
      const outputDir = path.join(__dirname, 'output');
      if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir, { recursive: true });
      
      const fileName = `video-${taskId.split('_')[1].split('-')[0]}.mp4`;
      const outputPath = path.join(outputDir, fileName);
      
      console.log('\n📥 开始下载视频...');
      await downloadVideo(result.video_url, outputPath);
      
      console.log('\n🎉 全部完成!');
      console.log('📁 本地文件:', outputPath);
      
      return {
        taskId,
        videoUrl: result.video_url,
        localPath: outputPath
      };
    }
    
    if (status === 'failed' || status === 'error') {
      throw new Error(`生成失败: ${JSON.stringify(result)}`);
    }
    
    await new Promise(r => setTimeout(r, 5000));
  }
  
  throw new Error('轮询超时（10分钟）');
}

// 主函数
async function main() {
  const args = process.argv.slice(2);
  const cmd = args[0];
  
  try {
    switch (cmd) {
      case 'text': {
        const prompt = args[1];
        const ratio = args[2] || '16:9';
        const seconds = parseInt(args[3]) || 5;
        
        if (!prompt) {
          console.log('用法: node video-generator.js text "提示词" [16:9] [5]');
          process.exit(1);
        }
        
        const { taskId } = await createVideo(prompt, null, ratio, seconds);
        await pollAndDownload(taskId, prompt, ratio);
        break;
      }
      
      case 'image': {
        const imagePath = args[1];
        const prompt = args[2] || '';
        const seconds = parseInt(args[3]) || 5;
        
        if (!imagePath || !fs.existsSync(imagePath)) {
          console.log('用法: node video-generator.js image "图片路径" "提示词" [5]');
          process.exit(1);
        }
        
        const { taskId } = await createVideo(prompt, imagePath, '16:9', seconds);
        await pollAndDownload(taskId, prompt, '16:9');
        break;
      }
      
      case 'query': {
        const taskId = args[1];
        if (!taskId) {
          console.log('用法: node video-generator.js query video_xxx');
          process.exit(1);
        }
        const res = await getTask(taskId);
        console.log(JSON.stringify(res, null, 2));
        break;
      }
      
      default:
        console.log(`
Veo Fast Video Generator

用法:
  node video-generator.js text "提示词" [比例] [秒数]   - 文生视频
  node video-generator.js image "图片路径" "提示词" [秒数] - 图生视频
  node video-generator.js query video_xxx               - 查询任务

比例: 16:9, 9:16, 1:1, 4:3, 3:4 (默认 16:9)
秒数: 5-10 (默认 5)

示例:
  node video-generator.js text "一只猫在跑" 16:9 5
  node video-generator.js image ./cat.png "让猫动起来" 5

功能:
  ✅ 自动生成轮询脚本
  ✅ 实时显示进度条
  ✅ 完成后自动下载视频
  ✅ 显示视频链接和本地路径
        `);
    }
  } catch (err) {
    console.error('\n❌ 错误:', err.message);
    process.exit(1);
  }
}

module.exports = {
  createVideo,
  getTask,
  pollAndDownload,
};

if (require.main === module) {
  main();
}
