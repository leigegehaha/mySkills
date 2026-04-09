#!/usr/bin/env node

/**
 * 自动轮询脚本 - 任务ID: video_ae262936-9bb6-498c-a106-4bd2f9a0079f
 * 生成时间: 3/17/2026, 2:44:04 PM
 */

const https = require('https');
const fs = require('fs');
const path = require('path');

const API_KEY = 'your-api-key-here';
const TASK_ID = 'video_ae262936-9bb6-498c-a106-4bd2f9a0079f';

console.log('🎬 视频生成任务轮询');
console.log('任务ID:', TASK_ID);
console.log('提示词: 图片中的美女对着镜头，抽了一口烟，然后用美式英语说：go to hell, my boy , see ya, 然后扣动扳机，慢动作，枪口喷火，子弹打出');
console.log('比例: 9:16');
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
  console.log('⏳ 开始轮询，等待视频生成...\n');
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
    
    process.stdout.write('\r[' + elapsed + 's] [' + bar + '] ' + progress + '% | ' + status + '  ');
    
    if (status === 'completed') {
      console.log('\n\n✅ 视频生成完成!');
      console.log('📹 视频链接:', result.video_url);
      
      // 下载视频
      const outputDir = path.join(__dirname, 'output');
      if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir, { recursive: true });
      
      const fileName = 'video-' + TASK_ID.split('_')[1].split('-')[0] + '.mp4';
      const outputPath = path.join(outputDir, fileName);
      
      console.log('\n📥 开始下载视频...');
      await downloadVideo(result.video_url, outputPath);
      
      console.log('\n🎉 全部完成!');
      console.log('📁 本地文件:', outputPath);
      return;
    }
    
    if (status === 'failed' || status === 'error') {
      console.error('\n❌ 生成失败:', result);
      process.exit(1);
    }
    
    await new Promise(r => setTimeout(r, 5000));
  }
  
  console.error('\n⏱️ 轮询超时');
  process.exit(1);
}

main().catch(console.error);
