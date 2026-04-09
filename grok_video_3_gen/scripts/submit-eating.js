const https = require('https');
const fs = require('fs');

const API_KEY = 'your-api-key-here';

const prompt = "一位年轻女性在餐厅享用美食，优雅地用筷子夹菜，面前摆着精致的菜肴，温馨的用餐环境，自然光线";

console.log('🎬 提交竖屏用餐视频任务...');
console.log('提示词:', prompt);
console.log('比例: 9:16 (竖屏)');

const boundary = '----FormBoundary' + Date.now();
let body = '';
const fields = {
  model: 'veo_3_1-fast-4K',
  prompt: prompt,
  seconds: '5',
  size: '9x16',
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
      fs.writeFileSync('eating-task-id.txt', result.id);
      console.log('任务ID已保存到 eating-task-id.txt');
      console.log('\n查询命令:');
      console.log('node video-generator.js query', result.id);
    } else {
      console.error('提交失败:', result);
    }
  });
});

req.write(bodyBuf);
req.end();
