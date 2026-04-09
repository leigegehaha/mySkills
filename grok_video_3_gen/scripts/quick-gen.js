#!/usr/bin/env node

const https = require('https');
const fs = require('fs');
const path = require('path');

const API_KEY = 'your-api-key-here';
const MODEL = 'veo_3_1-fast-4K';

// 快速生成视频
async function generateVideo() {
  const prompt = "一位中国女性在练习瑜伽，做树式姿势，穿着运动服，在明亮的瑜伽馆里，阳光透过窗户照进来";
  
  console.log('🎬 生成瑜伽视频...');
  console.log('提示词:', prompt);
  
  // 构建 multipart/form-data
  const boundary = '----FormBoundary' + Date.now();
  const fields = {
    model: MODEL,
    prompt: prompt,
    seconds: '5',
    size: '16x9',
    watermark: 'false'
  };
  
  let body = '';
  for (const [key, value] of Object.entries(fields)) {
    body += `--${boundary}\r\n`;
    body += `Content-Disposition: form-data; name="${key}"\r\n\r\n`;
    body += value;
    body += '\r\n';
  }
  body += `--${boundary}--\r\n`;
  
  const bodyBuffer = Buffer.from(body, 'utf-8');
  
  // 发送请求
  const result = await new Promise((resolve, reject) => {
    const options = {
      hostname: 'api.vectorengine.ai',
      port: 443,
      path: '/v1/videos',
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'Content-Type': `multipart/form-data; boundary=${boundary}`,
        'Content-Length': bodyBuffer.length
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
    req.write(bodyBuffer);
    req.end();
  });
  
  if (result.id) {
    console.log('\n✅ 任务已提交!');
    console.log('任务ID:', result.id);
    console.log('\n正在轮询等待完成...');
    
    // 轮询等待完成
    const startTime = Date.now();
    const maxTime = 300000; // 5分钟
    
    while (Date.now() - startTime < maxTime) {
      const statusRes = await new Promise((resolve, reject) => {
        const options = {
          hostname: 'api.vectorengine.ai',
          port: 443,
          path: `/v1/videos/${result.id}`,
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
      
      const status = statusRes.status || 'unknown';
      const progress = statusRes.progress ?? '?';
      
      process.stdout.write(`\r[${new Date().toLocaleTimeString()}] ${status} | 进度: ${progress}%`);
      
      if (status === 'completed') {
        console.log('\n\n✅ 视频生成完成!');
        console.log('视频URL:', statusRes.video_url);
        
        // 保存任务信息
        const taskInfo = {
          taskId: result.id,
          videoUrl: statusRes.video_url,
          prompt: prompt,
          createdAt: new Date().toISOString()
        };
        fs.writeFileSync('yoga-video-task.json', JSON.stringify(taskInfo, null, 2));
        console.log('任务信息已保存到: yoga-video-task.json');
        
        return statusRes.video_url;
      }
      
      if (status === 'failed' || status === 'error') {
        throw new Error(`生成失败: ${JSON.stringify(statusRes)}`);
      }
      
      await new Promise(r => setTimeout(r, 5000));
    }
    
    throw new Error('生成超时');
  } else {
    throw new Error(`创建失败: ${JSON.stringify(result)}`);
  }
}

generateVideo().catch(err => {
  console.error('\n❌ 错误:', err.message);
  process.exit(1);
});
