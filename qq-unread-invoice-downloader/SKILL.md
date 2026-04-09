---
name: qq-unread-invoice-downloader
description: 扫描 QQ 邮箱未读邮件，识别发票相关邮件并下载发票 PDF 到本地文件夹，同时生成 Excel 汇总。适用于“下载未读邮件里的发票”“整理报销发票”“导出未读发票 PDF”等场景。识别规则需覆盖普通发票邮件，以及从 Zhang Lei 或 1296669775@qq.com 发给自己、通常带发票/PDF的邮件。Excel 必须标明哪些已下载、哪些需手动下载；需手动下载的行要标黄，并给出下载链接。
---

# QQ 未读发票下载

使用这个技能时：

1. 只扫描 `INBOX` 中的未读邮件
2. 识别发票相关邮件：
   - 常规关键词：`发票`、`电子发票`、`数电发票`、`invoice`、`报销单`、`receipt`
   - 特殊规则：发件人为 `Zhang Lei` 或地址为 `1296669775@qq.com` 且发给自己时，若主题/正文含 `.pdf` 或 `发票` 线索，也视为发票邮件
3. 只下载发票 `PDF`
4. 如果邮件没有可直接下载的 PDF，但正文有明显下载地址：
   - 不下载其它无关附件
   - 在 Excel 中标记为 `需手动下载`
   - 填入唯一合适的下载链接，不要把无关链接全塞进去
5. 生成 Excel 总结，至少包含：
   - `日期`
   - `发票号码`
   - `金额`
   - `购方名称`
   - `销方名称`
   - `主题`
   - `状态`
   - `已下载PDF`
   - `手动下载链接`
   - `UID`
   - `备注`
6. Excel 中 `需手动下载` 的整行标黄
7. 读取已下载的 PDF，提取：`金额`、`开票方`、`开票日期`
8. 其中 `发票金额` 需要优先按 AI 方式判断提取，规则匹配只作为兜底
9. 基于提取结果生成一段简短的 AI 总结，方便快速理解发票内容
10. 第一版不要改原来的汇总 sheet，新增一个 sheet：`PDF提取汇总`

## 运行方式

脚本目录：`scripts/`

推荐输出目录命名：
- `invoices_unread_pdf_only_YYYYMMDD`

执行步骤：

```bash
mkdir -p <输出目录>
QQ_EMAIL_ACCOUNT='...' QQ_EMAIL_AUTH_CODE='...' node scripts/export-unread-invoice-pdfs.js --out <输出目录>
python3 scripts/build_unread_pdf_invoice_excel.py <输出目录>
python3 scripts/enrich_invoice_pdf_sheet.py <输出目录>
```

## 输出要求

- 把下载下来的 PDF 放在输出目录根目录
- 把清单写成 `invoice_manifest_unread_pdf_only.json`
- 把 Excel 写成 `qq邮箱未读发票PDF汇总.xlsx`
- 最终向用户说明：
  - 输出文件夹位置
  - 下载了多少个 PDF
  - 有多少条需手动下载
  - Excel 路径

## 资源

- `scripts/export-unread-invoice-pdfs.js`：扫描未读邮件并下载 PDF / 提取手动下载链接
- `scripts/build_unread_pdf_invoice_excel.py`：根据 JSON 清单生成 Excel，并将需手动下载的行标黄
