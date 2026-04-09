const https = require('https');
const fs = require('fs');

const API_KEY = 'your-api-key-here';

const prompt = "一位中国女性在练习瑜伽，做树式姿势，穿着运动服，在明亮的瑜伽馆里，阳光透过窗户照进来";

console.log('🎬 生成瑜伽视频...');
console.log('提示词:', prompt);

// 提交任务
const boundary = '----FormBoundary' + Date.now();
let body = '';
const fields = {
  model: 'veo_3_1-fast-4K',
  prompt: prompt,
  seconds: '5',
  size: '16x9',
  watermark: 'false'
};

for (const [key, value] of Object.entries(fields)) {
  body += `--${boundary}\r\nContent-Disposition: form-data; name="${key}"\r\n\r\n${value}\r\n`;
}
body += `--${boundary}--\r\n`;

const bodyBuf = Buffer.from(body, 'utf-8');

const req = https.request({
  hostname: 'api.vectorengine.ai',
  port: 443,
  path: '/v1/videos',
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${API_KEY}`,
    'Content-Type': `multipart/form-data; boundary=${boundary}`,
    'Content-Length': bodyBuf.length
  }
}, (res) => {
  let data = '';
  res.on('data', chunk => data += chunk);
  res.on('end', () => {
    const result = JSON.parse(data);
    if (result.id) {
      console.log('\n✅ 任务已提交:', result.id);
      fs.writeFileSync('yoga-task-id.txt', result.id);
      console.log('任务ID已保存到 yoga-task-id.txt');
      console.log('请稍后查询任务状态');
    } else {
      console.error('提交失败:', result);
    }
  });
});

req.write(bodyBuf);
req.end();
