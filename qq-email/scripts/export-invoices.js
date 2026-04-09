import Imap from 'imap';
import { simpleParser } from 'mailparser';
import fs from 'fs';
import path from 'path';

const account = process.env.QQ_EMAIL_ACCOUNT;
const authCode = process.env.QQ_EMAIL_AUTH_CODE;

if (!account || !authCode) {
  console.error('请设置环境变量 QQ_EMAIL_ACCOUNT 和 QQ_EMAIL_AUTH_CODE');
  process.exit(1);
}

const imapConfig = {
  user: account,
  password: authCode,
  host: 'imap.qq.com',
  port: 993,
  tls: true,
  tlsOptions: { rejectUnauthorized: false },
};

function parseArgs() {
  const args = process.argv.slice(2);
  let days = 120;
  let outDir = process.cwd();
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--days' && args[i + 1]) {
      days = Math.max(1, parseInt(args[i + 1], 10) || 120);
      i++;
    } else if (args[i] === '--out' && args[i + 1]) {
      outDir = args[i + 1];
      i++;
    }
  }
  return { days, outDir };
}

function openInbox(imap) {
  return new Promise((resolve, reject) => {
    imap.openBox('INBOX', false, (err, box) => {
      if (err) reject(err);
      else resolve(box);
    });
  });
}

function sanitizeName(name) {
  return name.replace(/[\\/:*?"<>|]/g, '_');
}

function extractLinks(text) {
  if (!text) return [];
  const matches = text.match(/https?:\/\/[^\s<>"]+/g) || [];
  return [...new Set(matches)];
}

function isInvoiceMail(parsed) {
  const subject = parsed.subject || '';
  const from = parsed.from?.text || '';
  const body = `${parsed.text || ''}\n${parsed.html || ''}`;
  const keywords = ['发票', '电子发票', '数电发票', 'invoice', '报销单', 'receipt'];
  return keywords.some((k) => subject.includes(k) || from.includes(k) || body.includes(k));
}

async function fetchEmails(sinceDate) {
  const imap = new Imap(imapConfig);
  return new Promise((resolve, reject) => {
    const emails = [];
    imap.once('ready', () => {
      openInbox(imap)
        .then(() => {
          const searchCriteria = sinceDate ? [['SINCE', sinceDate]] : ['ALL'];
          imap.search(searchCriteria, (err, uids) => {
            if (err) {
              imap.end();
              return reject(err);
            }
            if (uids.length === 0) {
              imap.end();
              return resolve(emails);
            }
            const fetch = imap.fetch(uids, { bodies: '' });
            const parsePromises = [];
            fetch.on('message', (msg) => {
              let resolveP;
              parsePromises.push(new Promise((r) => {
                resolveP = r;
              }));
              const state = { parsed: null, uid: undefined, pushed: false };
              function maybePush() {
                if (state.parsed != null && state.uid !== undefined && !state.pushed) {
                  state.pushed = true;
                  emails.push({ parsed: state.parsed, uid: state.uid });
                  resolveP();
                }
              }
              msg.once('attributes', (attrs) => {
                state.uid = attrs && attrs.uid;
                maybePush();
              });
              msg.on('body', (stream) => {
                simpleParser(stream, (parseErr, parsed) => {
                  if (!parseErr) state.parsed = parsed;
                  maybePush();
                });
              });
              msg.once('end', () => {
                if (!state.pushed && state.parsed != null) {
                  state.pushed = true;
                  emails.push({ parsed: state.parsed, uid: state.uid });
                  resolveP();
                }
              });
            });
            fetch.once('error', (e) => {
              imap.end();
              reject(e);
            });
            fetch.once('end', () => {
              Promise.all(parsePromises).then(() => imap.end());
            });
          });
        })
        .catch((e) => {
          imap.end();
          reject(e);
        });
    });
    imap.once('error', reject);
    imap.once('end', () => resolve(emails));
    imap.connect();
  });
}

async function main() {
  const { days, outDir } = parseArgs();
  fs.mkdirSync(outDir, { recursive: true });
  const sinceDate = new Date();
  sinceDate.setDate(sinceDate.getDate() - days);

  const emails = await fetchEmails(sinceDate);
  const invoiceRows = [];

  for (const item of emails) {
    const parsed = item.parsed;
    if (!isInvoiceMail(parsed)) continue;

    const subject = parsed.subject || '';
    const from = parsed.from?.text || '';
    const date = parsed.date ? new Date(parsed.date).toISOString() : '';
    const text = parsed.text || '';
    const html = typeof parsed.html === 'string' ? parsed.html : '';
    const content = `${text}\n${html}`;
    const links = extractLinks(content).filter((link) => !link.includes('aka.ms'));

    const savedFiles = [];
    for (const att of parsed.attachments || []) {
      if (!att.filename) continue;
      const filename = `${item.uid}_${sanitizeName(att.filename)}`;
      const outputPath = path.join(outDir, filename);
      fs.writeFileSync(outputPath, att.content);
      savedFiles.push(outputPath);
    }

    invoiceRows.push({
      uid: item.uid,
      date,
      from,
      subject,
      attachment_count: (parsed.attachments || []).length,
      saved_files: savedFiles.join(' | '),
      download_links: links.join(' | '),
      body_preview: text.replace(/\s+/g, ' ').trim().slice(0, 500),
    });
  }

  const manifestPath = path.join(outDir, 'invoice_manifest.json');
  fs.writeFileSync(manifestPath, JSON.stringify(invoiceRows, null, 2));
  console.log(manifestPath);
}

main().catch((err) => {
  console.error(err.message);
  process.exit(1);
});
