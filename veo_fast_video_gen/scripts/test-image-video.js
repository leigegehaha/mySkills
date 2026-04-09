const https = require('https');
const fs = require('fs');
const path = require('path');

const API_KEY = 'your-api-key-here';
const MODEL = 'veo_3_1-fast-4K';

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
    
    console.log('发送图生视频请求...');
    console.log('图片:', fields.input_reference);
    console.log('提示词:', fields.prompt);
    
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

// 主函数
async function main() {
  try {
    const imagePath = 'test-image.png';
    
    if (!fs.existsSync(imagePath)) {
      console.error('错误: 测试图片不存在');
      return;
    }
    
    const fields = {
      model: MODEL,
      prompt: '让红色背景流动起来，有光效变化',
      seconds: '5',
      size: '16x9',
      watermark: 'false',
      input_reference: imagePath
    };
    
    const result = await postVideo(fields);
    
    if (result.id) {
      console.log('\n✅ 任务已提交!');
      console.log('任务ID:', result.id);
      console.log('状态:', result.status);
      console.log('\n可以用以下命令查询进度:');
      console.log(`node video-generator.js query ${result.id}`);
    } else {
      console.error('创建失败:', result);
    }
  } catch (err) {
    console.error('错误:', err.message);
  }
}

main();
