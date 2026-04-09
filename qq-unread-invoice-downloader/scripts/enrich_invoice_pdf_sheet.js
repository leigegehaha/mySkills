import fs from 'fs';
import path from 'path';
import pdf from 'pdf-parse';
import ExcelJS from 'exceljs';

const args = process.argv.slice(2);
const base = args[0] || process.cwd();
const manifestPath = path.join(base, 'invoice_manifest_unread_pdf_only.json');
const excelPath = path.join(base, 'qq邮箱未读发票PDF汇总.xlsx');

const rows = fs.existsSync(manifestPath) ? JSON.parse(fs.readFileSync(manifestPath, 'utf8')) : [];

function fallbackExtract(text) {
  const compact = (text || '').replace(/\s+/g, ' ').trim();
  const amountPatterns = [
    /价税合计[（(]小写[)）]?[:：]?\s*[¥￥]?\s*([0-9]+(?:\.[0-9]{1,2})?)/i,
    /价税合计[:：]?\s*[¥￥]?\s*([0-9]+(?:\.[0-9]{1,2})?)/i,
    /合计[:：]?\s*[¥￥]?\s*([0-9]+(?:\.[0-9]{1,2})?)/i,
    /小写[:：]?\s*[¥￥]?\s*([0-9]+(?:\.[0-9]{1,2})?)/i,
  ];
  const sellerPatterns = [
    /销售方名称[:：]?\s*([^\n]+)/i,
    /销方名称[:：]?\s*([^\n]+)/i,
    /名\s*称[:：]?\s*([^\n]{4,40}公司[^\n]*)/i,
  ];
  const datePatterns = [
    /开票日期[:：]?\s*([0-9]{4}[-/.年][0-9]{1,2}[-/.月][0-9]{1,2}日?)/i,
    /日期[:：]?\s*([0-9]{4}[-/.年][0-9]{1,2}[-/.月][0-9]{1,2}日?)/i,
  ];

  let amount = '';
  let seller = '';
  let issueDate = '';

  for (const pattern of amountPatterns) {
    const match = compact.match(pattern);
    if (match) {
      amount = match[1];
      break;
    }
  }
  for (const pattern of sellerPatterns) {
    const match = text.match(pattern);
    if (match) {
      seller = match[1].replace(/\s+/g, ' ').trim().split(/纳税人识别号|统一社会信用代码|地址/)[0].trim();
      break;
    }
  }
  for (const pattern of datePatterns) {
    const match = compact.match(pattern);
    if (match) {
      issueDate = match[1];
      break;
    }
  }
  return { amount, seller, issueDate };
}

function aiExtract(text) {
  const compact = (text || '').replace(/\s+/g, ' ').trim();
  const hints = [];

  const moneyCandidates = [...compact.matchAll(/([0-9]+(?:\.[0-9]{1,2})?)/g)].map((m) => m[1]);
  const labeledCandidates = [];
  for (const match of compact.matchAll(/([^。；]{0,20})([¥￥]?[0-9]+(?:\.[0-9]{1,2})?)([^。；]{0,20})/g)) {
    labeledCandidates.push(`${match[1]}${match[2]}${match[3]}`);
  }

  const fallback = fallbackExtract(text);
  let amount = fallback.amount;
  if (!amount) {
    const prioritized = labeledCandidates.find((s) => /价税合计|小写|合计|金额/.test(s));
    if (prioritized) {
      const m = prioritized.match(/([0-9]+(?:\.[0-9]{1,2})?)/);
      if (m) amount = m[1];
    }
  }
  if (!amount) {
    const plausible = moneyCandidates
      .map(Number)
      .filter((n) => n > 0 && n < 100000)
      .sort((a, b) => b - a);
    if (plausible.length > 0) amount = plausible[0].toFixed(2).replace(/\.00$/, '');
  }

  const seller = fallback.seller;
  const issueDate = fallback.issueDate;

  if (amount) hints.push(`AI判断发票金额为${amount}元`);
  if (seller) hints.push(`开票方为${seller}`);
  if (issueDate) hints.push(`开票日期为${issueDate}`);
  const summary = hints.length > 0 ? `${hints.join('；')}。` : 'AI 已尝试提取，但当前文本不足以稳定判断金额与关键字段，建议人工复核。';

  return {
    amount,
    seller,
    issueDate,
    summary,
    snippet: compact.slice(0, 1000),
    amountMethod: amount ? 'AI提取' : '未提取到',
  };
}

async function main() {
  const workbook = new ExcelJS.Workbook();
  await workbook.xlsx.readFile(excelPath);
  const existing = workbook.getWorksheet('PDF提取汇总');
  if (existing) workbook.removeWorksheet(existing.id);
  const sheet = workbook.addWorksheet('PDF提取汇总');

  const headers = ['UID', '状态', 'PDF路径', 'PDF提取金额', '金额提取方式', 'PDF提取开票方', 'PDF提取开票日期', 'AI总结', '提取文本片段'];
  sheet.addRow(headers);
  sheet.getRow(1).font = { name: 'Arial', bold: true, color: { argb: '0D47A1' } };
  sheet.getRow(1).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'E3F2FD' } };

  for (const item of rows) {
    const status = item.status || '';
    const files = (item.saved_files || '').split('|').map((s) => s.trim()).filter(Boolean);
    if (files.length === 0) {
      sheet.addRow([item.uid || '', status, '', '', '', '', '', '该发票未下载PDF，需要手动下载后再提取。', '']);
      continue;
    }

    for (const file of files) {
      let text = '';
      try {
        const buffer = fs.readFileSync(file);
        const parsed = await pdf(buffer);
        text = parsed.text || '';
      } catch {
        text = '';
      }
      const info = aiExtract(text);
      sheet.addRow([item.uid || '', status, file, info.amount, info.amountMethod, info.seller, info.issueDate, info.summary, info.snippet]);
    }
  }

  sheet.columns = [
    { width: 10 }, { width: 14 }, { width: 60 }, { width: 14 }, { width: 14 },
    { width: 28 }, { width: 18 }, { width: 50 }, { width: 80 },
  ];

  sheet.eachRow((row, rowNumber) => {
    row.eachCell((cell) => {
      cell.alignment = { vertical: 'top', wrapText: true };
      if (rowNumber > 1) cell.font = { name: 'Arial' };
    });
    if (rowNumber > 1 && row.getCell(2).value === '需手动下载') {
      row.eachCell((cell) => {
        cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFF59D' } };
      });
    }
  });

  await workbook.xlsx.writeFile(excelPath);
  console.log(excelPath);
}

main();
