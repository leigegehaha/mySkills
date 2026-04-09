const https = require('https');
const fs = require('fs');
const path = require('path');

const API_KEY = 'your-api-key-here';
const TASK_ID = 'video_b18f6c56-1324-4401-b312-af17f058cc40';

console.log('🎬 轮询柯基视频任务...');
console.log('任务ID:', TASK_ID);
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
          process.stdout.write('\r📥 下载进度: ' + percent + '%');
        }
      });
      
      response.pipe(file);
      file.on('finish', () => {
        file.close();
        console.log('\n✅ 视频已保存:', outputPath);
        resolve(outputPath);
      });
    }).on('error', reject);
  });
}

async function main() {
  console.log('⏳ 开始轮询...\n');
  const startTime = Date.now();
  
  while (true) {
    const result = await getTask();
    const status = result.status || 'unknown';
    const progress = result.progress ?? 0;
    const elapsed = Math.floor((Date.now() - startTime) / 1000);
    
    // 显示进度条
    const barLength = 30;
    const filled = Math.floor((progress / 100) * barLength);
    const empty = barLength - filled;
    const bar = '█'.repeat(filled) + '░'.repeat(empty);
    
    console.log(`[${elapsed}s] [${bar}] ${progress}% | ${status}`);
    
    if (status === 'completed') {
      console.log('\n✅ 视频生成完成!');
      console.log('📹 视频链接:', result.video_url);
      
      // 下载视频
      const outputDir = path.join(__dirname, 'output');
      if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir, { recursive: true });
      
      const outputPath = path.join(outputDir, 'corgi-video.mp4');
      
      console.log('\n📥 开始下载...');
      await downloadVideo(result.video_url, outputPath);
      
      console.log('\n🎉 全部完成!');
      
      // 打开视频
      const { exec } = require('child_process');
      exec('open "' + outputPath + '"');
      
      return;
    }
    
    if (status === 'failed' || status === 'error') {
      console.error('\n❌ 生成失败:', result);
      process.exit(1);
    }
    
    // 等待5秒
    await new Promise(r => setTimeout(r, 5000));
    
    // 清除上一行（除了第一次）
    process.stdout.write('\x1B[1A\x1B[K');
  }
}

main().catch(console.error);
