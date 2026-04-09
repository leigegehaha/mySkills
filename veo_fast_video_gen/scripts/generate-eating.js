const https = require('https');
const fs = require('fs');
const path = require('path');

const API_KEY = 'your-api-key-here';
const MODEL = 'veo_3_1-fast-4K';

// 提示词
const prompt = "一位年轻女性在餐厅享用美食，优雅地用筷子夹菜，面前摆着精致的菜肴，温馨的用餐环境，自然光线";
const size = "9x16"; // 竖屏
const seconds = "5";

console.log('🎬 生成竖屏用餐视频...');
console.log('提示词:', prompt);
console.log('比例: 9:16 (竖屏)');
console.log('时长:', seconds, '秒');

// 构建 multipart/form-data
function buildFormData(fields, boundary) {
  let body = '';
  for (const [key, value] of Object.entries(fields)) {
    body += `--${boundary}\r\n`;
    body += `Content-Disposition: form-data; name="${key}"\r\n\r\n`;
    body += value;
    body += '\r\n';
  }
  body += `--${boundary}--\r\n`;
  return Buffer.from(body, 'utf-8');
}

// POST 请求
function postVideo(fields) {
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
      response.pipe(file);
      file.on('finish', () => {
        file.close();
        resolve(outputPath);
      });
    }).on('error', (err) => {
      fs.unlink(outputPath, () => {});
      reject(err);
    });
  });
}

// 主函数
async function main() {
  try {
    // 提交任务
    const fields = {
      model: MODEL,
      prompt: prompt,
      seconds: seconds,
      size: size,
      watermark: 'false'
    };
    
    console.log('\n📤 提交任务...');
    const result = await postVideo(fields);
    
    if (!result.id) {
      throw new Error(`提交失败: ${JSON.stringify(result)}`);
    }
    
    console.log('✅ 任务已提交:', result.id);
    
    // 轮询等待完成
    console.log('\n⏳ 开始轮询，等待视频生成...\n');
    const startTime = Date.now();
    const maxTime = 600000; // 10分钟超时
    
    while (Date.now() - startTime < maxTime) {
      const statusRes = await getTask(result.id);
      const status = statusRes.status || 'unknown';
      const progress = statusRes.progress ?? 0;
      
      const elapsed = Math.floor((Date.now() - startTime) / 1000);
      process.stdout.write(`\r[${elapsed}s] 状态: ${status} | 进度: ${progress}%   `);
      
      if (status === 'completed') {
        console.log('\n\n✅ 视频生成完成!');
        console.log('视频URL:', statusRes.video_url);
        
        // 下载视频
        const outputDir = path.join(__dirname, 'output');
        if (!fs.existsSync(outputDir)) {
          fs.mkdirSync(outputDir, { recursive: true });
        }
        
        const outputPath = path.join(outputDir, `eating-9x16-${Date.now()}.mp4`);
        console.log('\n📥 下载视频中...');
        await downloadVideo(statusRes.video_url, outputPath);
        console.log('✅ 视频已保存:', outputPath);
        
        return {
          taskId: result.id,
          videoUrl: statusRes.video_url,
          localPath: outputPath
        };
      }
      
      if (status === 'failed' || status === 'error') {
        throw new Error(`生成失败: ${JSON.stringify(statusRes)}`);
      }
      
      // 等待5秒后继续轮询
      await new Promise(r => setTimeout(r, 5000));
    }
    
    throw new Error('轮询超时（10分钟）');
    
  } catch (err) {
    console.error('\n❌ 错误:', err.message);
    process.exit(1);
  }
}

main().then((result) => {
  console.log('\n🎉 全部完成!');
  console.log('任务ID:', result.taskId);
  console.log('本地视频:', result.localPath);
}).catch(console.error);
