---
name: stock-analysis
description: |
  根据用户输入的 A 股股票代码或股票名称，生成 90 天股票投资分析报告。
  输出交互式 HTML 报告，覆盖行情摘要、技术指标、K 线/BOLL/成交量图、新闻动态、
  机构评级、资金流向和综合分析。适用于“分析 603050”“帮我看下比亚迪股票”
  这类请求。
---

# 股票投资分析报告技能

## 功能描述

根据用户输入的股票代码或股票名称，自动生成一份完整的 90 天股票投资分析报告，包含：

- 行情摘要（当前价格、涨跌幅、最高/最低价）
- 技术指标分析（MA5/MA10/MA20、BOLL 布林带）
- 交互式 K 线图
- 交互式 BOLL 图
- 股价与成交量图
- 最新新闻动态
- 机构评级与盈利预测
- 资金流向分析
- 综合投资建议

## 触发方式

用户输入以下格式即可触发：

- `分析 603050`
- `分析 科博达`
- `帮我看下 比亚迪 股票`
- `生成 科博达 的投资报告`

## 使用方法

默认优先使用专业版脚本：

```bash
python3 {baseDir}/scripts/analyze_v2.py "603050"
```

如果只需要基础版，也可使用：

```bash
python3 {baseDir}/scripts/analyze.py "603050"
```

## 输出

- 生成一个交互式 HTML 报告文件
- 报告默认保存到 `~/Documents/Stock_analysis/`

## 技术依赖

- Python 3
- `akshare`
- `plotly`
- `pandas`
- 专业版额外可选：`PyMuPDF`

## 注意事项

- 当前主要面向 A 股
- 股票代码格式通常为 6 位数字
- 如果输入股票名称，脚本会尝试自动匹配股票代码
- 数据依赖 AkShare 公开接口，联网异常时可能失败

## 文件结构

```text
~/.agents/skills/stock-analysis/
├── SKILL.md
└── scripts/
    ├── analyze.py
    └── analyze_v2.py
```
