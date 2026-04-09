import nodemailer from 'nodemailer';
import fs from 'fs';
import path from 'path';

const account = process.env.QQ_EMAIL_ACCOUNT;
const authCode = process.env.QQ_EMAIL_AUTH_CODE;

if (!account || !authCode) {
  console.error('请设置环境变量 QQ_EMAIL_ACCOUNT 和 QQ_EMAIL_AUTH_CODE');
  process.exit(1);
}

const transporter = nodemailer.createTransport({
  host: 'smtp.qq.com',
  port: 465,
  secure: true,
  auth: {
    user: account,
    pass: authCode,
  },
});

async function readStdin() {
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  return Buffer.concat(chunks).toString('utf8').trim();
}

async function main() {
  const args = process.argv.slice(2);
  const useStdin = args.includes('--stdin');
  const htmlIndex = args.indexOf('--html-file');
  const attachIndex = args.indexOf('--attach');
  const inlineIndex = args.indexOf('--inline-image');
  const htmlFile = htmlIndex >= 0 ? args[htmlIndex + 1] : null;
  const attachmentPath = attachIndex >= 0 ? args[attachIndex + 1] : null;
  const inlineImagePath = inlineIndex >= 0 ? args[inlineIndex + 1] : null;
  const filtered = args.filter((a, index) => {
    if (a === '--stdin' || a === '--html-file' || a === '--attach' || a === '--inline-image') return false;
    if (
      (htmlIndex >= 0 && index === htmlIndex + 1) ||
      (attachIndex >= 0 && index === attachIndex + 1) ||
      (inlineIndex >= 0 && index === inlineIndex + 1)
    ) return false;
    return true;
  });

  let to, subject, body;
  if (useStdin) {
    if (filtered.length < 2) {
      console.error('用法: node scripts/send.js <收件人> <主题> --stdin');
      process.exit(1);
    }
    [to, subject] = filtered;
    body = await readStdin();
  } else {
    if (filtered.length < 3) {
      console.error('用法: node scripts/send.js <收件人> <主题> <正文>');
      process.exit(1);
    }
    [to, subject, body] = filtered;
  }

  const attachments = [];
  if (attachmentPath) {
    attachments.push({
      filename: path.basename(attachmentPath),
      path: attachmentPath,
    });
  }
  if (inlineImagePath) {
    attachments.push({
      filename: path.basename(inlineImagePath),
      path: inlineImagePath,
      cid: 'confession-card',
    });
  }

  try {
    const info = await transporter.sendMail({
      from: account,
      to,
      subject,
      text: body,
      html: htmlFile ? fs.readFileSync(htmlFile, 'utf8') : undefined,
      attachments: attachments.length > 0 ? attachments : undefined,
    });
    console.log('已发送:', info.messageId);
  } catch (err) {
    console.error('发信失败:', err.message);
    process.exit(1);
  }
}

main();
