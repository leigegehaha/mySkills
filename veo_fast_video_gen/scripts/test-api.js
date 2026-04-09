const https = require('https');

const API_KEY = 'your-api-key-here';

const options = {
  hostname: 'api.vectorengine.ai',
  port: 443,
  path: '/v1/models',
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
      const json = JSON.parse(data);
      console.log('API 连接成功!');
      console.log('可用模型数:', json.data ? json.data.length : 0);
      const veoModels = json.data.filter(m => m.id.includes('veo_3_1-fast-4K'));
      console.log('veo_3_1-fast-4K 可用:', veoModels.length > 0 ? '是' : '否');
    } catch(e) {
      console.log('响应:', data.substring(0, 200));
    }
  });
});

req.on('error', (e) => console.error('错误:', e.message));
req.end();
