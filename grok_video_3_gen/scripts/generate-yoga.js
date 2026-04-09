const { exec } = require('child_process');
const path = require('path');

const prompt = "一位中国女性在练习瑜伽，做树式姿势，穿着运动服，在明亮的瑜伽馆里，阳光透过窗户照进来";

console.log('开始生成瑜伽视频...');
console.log('提示词:', prompt);

const cmd = `node "${path.join(__dirname, 'video-generator.js')}" text "${prompt}" 16:9 5`;

exec(cmd, { timeout: 600000 }, (error, stdout, stderr) => {
  if (error) {
    console.error('生成失败:', error.message);
    return;
  }
  console.log('生成完成!');
  console.log(stdout);
});

console.log('视频生成任务已在后台启动，请稍后查看 output 目录');
