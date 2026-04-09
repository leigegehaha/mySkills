#!/usr/bin/env python3
"""
股票投资分析报告生成脚本 - 专业版
包含新闻分析、研报PDF解析、预测价格计算
"""

import json
import sys
import os
import re
import time
from datetime import datetime, timedelta
from urllib.parse import quote

try:
    import akshare as ak
    import pandas as pd
    import requests
except ImportError as exc:
    missing_pkg = exc.name or str(exc)
    print(f"缺少依赖: {missing_pkg}")
    print("请先安装: pip3 install akshare pandas requests PyMuPDF")
    sys.exit(1)


def call_akshare(func, *args, retries=3, delay=1, **kwargs):
    """为不稳定的 AkShare 接口增加轻量重试。"""
    last_error = None
    for attempt in range(retries):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(delay)
    raise RuntimeError(f"AkShare 接口调用失败: {func.__name__}: {last_error}") from last_error

# 导入PDF解析库
try:
    import fitz  # PyMuPDF
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("警告: 未安装PyMuPDF，PDF解析功能将不可用")

def get_stock_code(query):
    """根据输入获取股票代码"""
    query = query.strip()
    
    if query.isdigit() and len(query) == 6:
        return query
    
    try:
        stocks = call_akshare(ak.stock_zh_a_spot_em)
        exact_match = stocks[stocks['名称'] == query]
        if len(exact_match) > 0:
            return exact_match.iloc[0]['代码']
        matches = stocks[stocks['名称'].str.contains(query, na=False)]
        if len(matches) > 0:
            return matches.iloc[0]['代码']
    except:
        pass
    
    return None

def analyze_news_content(title, stock_name):
    """分析新闻内容，提取关键信息和情感"""
    # 关键词分析
    positive_keywords = ['涨', '增持', '利好', '突破', '创新高', '净流入', '上涨', '增长', '盈利', '订单', '合作', '中标']
    negative_keywords = ['跌', '减持', '利空', '跌破', '创新低', '净流出', '下跌', '亏损', '召回', '处罚', '诉讼', '违规']
    
    sentiment_score = 0
    keywords_found = []
    
    for kw in positive_keywords:
        if kw in title:
            sentiment_score += 1
            keywords_found.append(kw)
    
    for kw in negative_keywords:
        if kw in title:
            sentiment_score -= 1
            keywords_found.append(kw)
    
    # 生成摘要
    if sentiment_score > 0:
        sentiment = "positive"
        summary = f"积极信号: 涉及{', '.join(keywords_found[:3])}"
    elif sentiment_score < 0:
        sentiment = "negative"
        summary = f"需关注: 涉及{', '.join(keywords_found[:3])}"
    else:
        sentiment = "neutral"
        summary = "中性新闻"
    
    return {
        'sentiment': sentiment,
        'summary': summary,
        'keywords': keywords_found
    }

def extract_pdf_content(pdf_url):
    """下载并解析PDF研报"""
    if not PDF_SUPPORT or not pdf_url:
        return None
    
    try:
        # 下载PDF
        response = requests.get(pdf_url, timeout=30)
        if response.status_code != 200:
            return None

        # 直接从内存解析，避免临时文件权限或并发问题
        doc = fitz.open(stream=response.content, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        
        # 提取关键信息
        info = {
            'target_price': None,
            'rating': None,
            'summary': text[:2000] if len(text) > 2000 else text
        }
        
        # 尝试提取目标价
        price_patterns = [
            r'目标价[：:]\s*(\d+\.?\d*)',
            r'目标价格[：:]\s*(\d+\.?\d*)',
            r'目标价位[：:]\s*(\d+\.?\d*)',
            r'目标[：:]\s*(\d+\.?\d*)元',
            r'目标价.*?([\d\.]+)\s*元',
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, text)
            if match:
                info['target_price'] = float(match.group(1))
                break
        
        # 尝试提取评级
        rating_patterns = [
            r'评级[：:]\s*(买入|增持|中性|减持|卖出|强烈推荐)',
            r'投资评级[：:]\s*(买入|增持|中性|减持|卖出|强烈推荐)',
        ]
        
        for pattern in rating_patterns:
            match = re.search(pattern, text)
            if match:
                info['rating'] = match.group(1)
                break

        return info
        
    except Exception as e:
        print(f"PDF解析错误: {e}")
        return None

def calculate_predicted_price(reports, current_price, tech_data):
    """基于研报和技术指标计算预测价格"""
    predictions = []
    
    # 从研报提取目标价
    for report in reports:
        target_price = report.get('target_price')
        if target_price:
            predictions.append({
                'source': f"研报:{report.get('date', '')}",
                'price': target_price,
                'type': '机构目标价'
            })
    
    # 基于技术指标计算
    boll_upper = tech_data.get('boll_upper_val', 0)
    high_90 = tech_data.get('high_90', 0)
    
    if boll_upper > current_price * 1.05:
        predictions.append({
            'source': '技术面:BOLL上轨',
            'price': round(boll_upper, 2),
            'type': '技术阻力'
        })
    
    if high_90 > current_price * 1.03:
        predictions.append({
            'source': '技术面:90日高点',
            'price': round(high_90 * 1.05, 2),
            'type': '突破目标'
        })
    
    # 计算加权平均预测价
    if predictions:
        avg_price = sum(p['price'] for p in predictions) / len(predictions)
        return {
            'average': round(avg_price, 2),
            'upside': round((avg_price - current_price) / current_price * 100, 1),
            'details': predictions
        }
    
    return None

def generate_report(stock_code, output_dir=None):
    """生成股票分析报告"""
    
    if output_dir is None:
        output_dir = os.path.expanduser("~/Documents/Stock_analysis")
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取股票基本信息
    try:
        stock_info = call_akshare(ak.stock_individual_info_em, symbol=stock_code)
        stock_name = stock_info[stock_info['item'] == '股票简称']['value'].values[0]
    except:
        stock_name = stock_code
    
    print(f"正在分析 {stock_name}({stock_code})...")
    
    # 获取K线数据
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=120)).strftime('%Y%m%d')
    
    ohlc = call_akshare(
        ak.stock_zh_a_hist,
        symbol=stock_code,
        period="daily",
        start_date=start_date,
        end_date=end_date,
        adjust="qfq",
    )
    ohlc['Date'] = pd.to_datetime(ohlc['日期'])
    ohlc = ohlc.rename(columns={'收盘': 'Close', '开盘': 'Open', '最高': 'High', 
                                '最低': 'Low', '成交量': 'Volume'})
    ohlc = ohlc.sort_values('Date').reset_index(drop=True)
    
    # 计算技术指标
    ohlc['MA5'] = ohlc['Close'].rolling(window=5).mean()
    ohlc['MA10'] = ohlc['Close'].rolling(window=10).mean()
    ohlc['MA20'] = ohlc['Close'].rolling(window=20).mean()
    ohlc['BOLL_MID'] = ohlc['Close'].rolling(window=20).mean()
    ohlc['BOLL_STD'] = ohlc['Close'].rolling(window=20).std()
    ohlc['BOLL_UPPER'] = ohlc['BOLL_MID'] + 2 * ohlc['BOLL_STD']
    ohlc['BOLL_LOWER'] = ohlc['BOLL_MID'] - 2 * ohlc['BOLL_STD']
    
    df = ohlc.tail(90).copy().reset_index(drop=True)
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    # 获取新闻（带真实链接）
    try:
        news = call_akshare(ak.stock_news_em, symbol=stock_code)
        news_list = []
        for idx, row in news.head(10).iterrows():
            title = row.get('新闻标题', '')
            date = str(row.get('发布时间', ''))[:10]
            
            # 分析新闻内容
            analysis = analyze_news_content(title, stock_name)
            
            # 生成真实新闻链接（基于东方财富）
            news_url = f"https://so.eastmoney.com/news/s?keyword={quote(stock_name + ' ' + title[:20])}"
            
            news_list.append({
                'date': date,
                'title': title,
                'url': news_url,
                'sentiment': analysis['sentiment'],
                'summary': analysis['summary'],
                'keywords': analysis['keywords']
            })
    except:
        news_list = []
    
    # 获取研报（带PDF链接）
    try:
        reports = call_akshare(ak.stock_research_report_em, symbol=stock_code)
        report_list = []
        for idx, row in reports.iterrows():
            date = str(row.get('日期', ''))
            title = row.get('报告名称', '')
            rating = row.get('东财评级', '')
            eps = str(row.get('2025-盈利预测-收益', ''))
            pe = str(row.get('2025-盈利预测-市盈率', ''))
            pdf_link = row.get('报告PDF链接', '')
            
            # 解析PDF获取目标价
            target_price = None
            if pdf_link:
                pdf_info = extract_pdf_content(pdf_link)
                if pdf_info:
                    target_price = pdf_info.get('target_price')
                    if pdf_info.get('rating'):
                        rating = pdf_info['rating']
            
            report_list.append({
                'date': date,
                'title': title,
                'rating': rating,
                'eps': eps if eps != 'nan' else '-',
                'pe': pe if pe != 'nan' else '-',
                'pdf_link': pdf_link,
                'target_price': target_price
            })
        
        # 按日期排序
        report_list.sort(key=lambda x: x['date'], reverse=True)
    except:
        report_list = []
    
    # 获取资金流向
    try:
        market = "sh" if stock_code.startswith('6') else "sz"
        money = call_akshare(ak.stock_individual_fund_flow, stock=stock_code, market=market)
        money_list = []
        for idx, row in money.tail(10).iterrows():
            money_list.append({
                'date': str(row.get('日期', '')),
                'price': row.get('收盘价', 0),
                'change': row.get('涨跌幅', 0),
                'main_in': row.get('主力净流入-净额', 0) or 0
            })
    except:
        money_list = []
    
    # 准备数据
    current_price = round(latest['Close'], 2)
    
    data = {
        'dates': df['Date'].dt.strftime('%Y-%m-%d').tolist(),
        'open': [round(x, 2) for x in df['Open'].tolist()],
        'high': [round(x, 2) for x in df['High'].tolist()],
        'low': [round(x, 2) for x in df['Low'].tolist()],
        'close': [round(x, 2) for x in df['Close'].tolist()],
        'volume': [int(x) for x in df['Volume'].tolist()],
        'ma5': [round(x, 2) if pd.notna(x) else None for x in df['MA5'].tolist()],
        'ma10': [round(x, 2) if pd.notna(x) else None for x in df['MA10'].tolist()],
        'ma20': [round(x, 2) if pd.notna(x) else None for x in df['MA20'].tolist()],
        'boll_upper': [round(x, 2) if pd.notna(x) else None for x in df['BOLL_UPPER'].tolist()],
        'boll_mid': [round(x, 2) if pd.notna(x) else None for x in df['BOLL_MID'].tolist()],
        'boll_lower': [round(x, 2) if pd.notna(x) else None for x in df['BOLL_LOWER'].tolist()],
        'latest_price': current_price,
        'change_pct': round(((latest['Close'] - prev['Close']) / prev['Close'] * 100), 2),
        'ma5_val': round(latest['MA5'], 2),
        'ma10_val': round(latest['MA10'], 2),
        'ma20_val': round(latest['MA20'], 2),
        'boll_upper_val': round(latest['BOLL_UPPER'], 2),
        'boll_mid_val': round(latest['BOLL_MID'], 2),
        'boll_lower_val': round(latest['BOLL_LOWER'], 2),
        'high_90': round(max(df['Close']), 2),
        'low_90': round(min(df['Close']), 2),
        'news': news_list,
        'reports': report_list,
        'money': money_list,
        'stock_code': stock_code,
        'stock_name': stock_name
    }
    
    # 计算预测价格
    tech_data = {
        'boll_upper_val': data['boll_upper_val'],
        'high_90': data['high_90']
    }
    predicted_price = calculate_predicted_price(report_list, current_price, tech_data)
    data['predicted_price'] = predicted_price
    
    # 生成HTML报告
    html = generate_html(data)
    
    output_file = os.path.join(output_dir, f"{stock_name}_{stock_code}_投资分析报告.html")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✓ 报告已生成: {output_file}")
    return output_file

def generate_html(data):
    """生成专业美化的HTML报告"""
    import json
    
    # 资金流向HTML生成
    money_rows_html = ""
    for m in data['money']:
        change_class = "positive" if m['change'] > 0 else "negative"
        main_class = "positive" if m['main_in'] > 0 else "negative"
        main_sign = "+" if m['main_in'] > 0 else ""
        money_rows_html += f"<tr><td>{m['date']}</td><td>¥{m['price']}</td><td class='{change_class}'>{m['change']:.2f}%</td><td class='{main_class}'>{main_sign}{int(m['main_in']):,}</td></tr>"
    
    # 新闻HTML生成
    news_items_html = ""
    for n in data['news']:
        news_items_html += f"""
                <div class="news-item {n['sentiment']}">
                    <div class="news-header">
                        <span class="news-date">{n['date']}</span>
                        <span class="news-sentiment {n['sentiment']}">{n['sentiment']}</span>
                    </div>
                    <div class="news-title">{n['title']}</div>
                    <div class="news-summary">{n['summary']}</div>
                    <a href="{n['url']}" target="_blank" class="news-link">查看详情 →</a>
                </div>
        """
    
    # 研报HTML生成
    reports_html = ""
    for r in data['reports'][:5]:
        rating = r['rating'] if r['rating'] else "无评级"
        rating_color = "#27ae60" if rating in ['买入', '强烈推荐', '增持'] else "#e74c3c" if rating in ['卖出', '减持'] else "#f39c12"
        
        target_price_html = f"<span style='color:#27ae60;font-weight:600;'>目标价: ¥{r['target_price']}</span>" if r['target_price'] else ""
        pdf_btn = f"<a href='{r['pdf_link']}' target='_blank' style='color:#3498db;text-decoration:none;font-size:12px;'>📄 下载PDF</a>" if r['pdf_link'] else ""
        
        reports_html += f"""
        <div style="background:linear-gradient(135deg,#fff 0%,#f8f9fa 100%);border-radius:12px;padding:16px;margin:12px 0;box-shadow:0 2px 8px rgba(0,0,0,0.08);border-left:4px solid {rating_color};">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <span style="color:#666;font-size:13px;font-weight:500;">{r['date']}</span>
                <span style="background:{rating_color};color:white;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600;">{rating}</span>
            </div>
            <div style="font-weight:600;color:#2c3e50;margin-bottom:8px;line-height:1.4;">{r['title']}</div>
            <div style="display:flex;justify-content:space-between;align-items:center;font-size:13px;color:#666;">
                <span>预测EPS: {r['eps']} | PE: {r['pe']}</span>
                {target_price_html}
            </div>
            {f'<div style="margin-top:8px;">{pdf_btn}</div>' if pdf_btn else ''}
        </div>
        """
    
    # 预测价格HTML
    predicted_html = ""
    if data.get('predicted_price'):
        pred = data['predicted_price']
        upside_color = "#27ae60" if pred['upside'] > 0 else "#e74c3c"
        
        details_html = ""
        for d in pred['details']:
            details_html += f"<li style='padding:4px 0;color:#666;'><strong>{d['source']}</strong>: ¥{d['price']} ({d['type']})</li>"
        
        predicted_html = f"""
        <div style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;padding:24px;border-radius:16px;margin:20px 0;box-shadow:0 4px 16px rgba(102,126,234,0.3);">
            <div style="font-size:14px;opacity:0.9;margin-bottom:8px;">AI综合预测目标价</div>
            <div style="font-size:36px;font-weight:700;margin-bottom:8px;">¥{pred['average']}</div>
            <div style="font-size:16px;color:{upside_color};background:rgba(255,255,255,0.2);display:inline-block;padding:4px 12px;border-radius:20px;">
                预期涨幅: {'+' if pred['upside'] > 0 else ''}{pred['upside']}%
            </div>
            <div style="margin-top:16px;padding-top:16px;border-top:1px solid rgba(255,255,255,0.2);">
                <div style="font-size:13px;opacity:0.8;margin-bottom:8px;">预测依据:</div>
                <ul style="list-style:none;padding:0;font-size:13px;">
                    {details_html}
                </ul>
            </div>
        </div>
        """
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{data['stock_name']}({data['stock_code']}) 投资分析报告</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary: #0f172a;
            --secondary: #1e293b;
            --accent: #3b82f6;
            --accent-light: #60a5fa;
            --success: #10b981;
            --danger: #ef4444;
            --warning: #f59e0b;
            --bg: #f1f5f9;
            --card: #ffffff;
            --text: #334155;
            --text-light: #64748b;
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{ 
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            line-height: 1.6; 
            color: var(--text); 
            background: var(--bg);
            padding: 0;
        }}
        
        .container {{ 
            max-width: 1400px; 
            margin: 0 auto; 
            background: var(--card); 
            min-height: 100vh;
        }}
        
        /* Header */
        .header {{ 
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%); 
            color: white; 
            padding: 60px 40px;
            position: relative;
            overflow: hidden;
        }}
        
        .header::before {{
            content: '';
            position: absolute;
            top: -50%;
            right: -20%;
            width: 600px;
            height: 600px;
            background: radial-gradient(circle, rgba(59,130,246,0.15) 0%, transparent 70%);
            border-radius: 50%;
        }}
        
        .header-content {{
            position: relative;
            z-index: 1;
        }}
        
        .stock-ticker {{
            font-family: 'Playfair Display', serif;
            font-size: 14px;
            letter-spacing: 3px;
            opacity: 0.7;
            margin-bottom: 12px;
            text-transform: uppercase;
        }}
        
        .header h1 {{ 
            font-family: 'Playfair Display', serif;
            font-size: 48px; 
            font-weight: 700;
            margin-bottom: 16px;
            letter-spacing: -0.5px;
        }}
        
        .header-subtitle {{
            font-size: 15px;
            opacity: 0.8;
            font-weight: 300;
        }}
        
        /* Section */
        .section {{ 
            padding: 48px 40px; 
            border-bottom: 1px solid #e2e8f0;
        }}
        
        .section:last-child {{ border-bottom: none; }}
        
        .section-title {{ 
            font-family: 'Playfair Display', serif;
            font-size: 24px; 
            font-weight: 600; 
            color: var(--primary);
            margin-bottom: 28px;
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        
        .section-title::before {{
            content: '';
            width: 4px;
            height: 28px;
            background: var(--accent);
            border-radius: 2px;
        }}
        
        /* Price Cards */
        .price-grid {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
            gap: 24px; 
        }}
        
        .price-card {{ 
            background: linear-gradient(135deg, #fff 0%, #f8fafc 100%);
            padding: 28px;
            border-radius: 16px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05), 0 4px 12px rgba(0,0,0,0.05);
            border: 1px solid #e2e8f0;
            transition: all 0.3s ease;
        }}
        
        .price-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        
        .price-card .label {{ 
            font-size: 12px; 
            color: var(--text-light);
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-weight: 500;
        }}
        
        .price-card .value {{ 
            font-family: 'Playfair Display', serif;
            font-size: 32px; 
            font-weight: 700;
            color: var(--primary);
        }}
        
        .price-card .change {{
            font-size: 14px;
            margin-top: 8px;
            font-weight: 500;
        }}
        
        .positive {{ color: var(--success); }}
        .negative {{ color: var(--danger); }}
        
        /* Tech Grid */
        .tech-grid {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); 
            gap: 20px; 
        }}
        
        .tech-item {{ 
            background: #fff;
            padding: 24px;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        
        .tech-item.bullish {{ border-left: 4px solid var(--success); }}
        .tech-item.bearish {{ border-left: 4px solid var(--danger); }}
        .tech-item.neutral {{ border-left: 4px solid var(--warning); }}
        
        .tech-item .label {{ 
            font-size: 11px; 
            color: var(--text-light);
            text-transform: uppercase;
            letter-spacing: 1px;
            font-weight: 600;
            margin-bottom: 8px;
        }}
        
        .tech-item .value {{ 
            font-family: 'Playfair Display', serif;
            font-size: 24px; 
            font-weight: 700;
            color: var(--primary);
        }}
        
        /* Charts */
        .chart-container {{ 
            margin: 24px 0; 
            border-radius: 16px; 
            overflow: hidden;
            box-shadow: 0 4px 16px rgba(0,0,0,0.08);
            border: 1px solid #e2e8f0;
        }}
        
        /* News */
        .news-list {{ list-style: none; }}
        
        .news-item {{ 
            padding: 20px;
            margin: 12px 0;
            background: #fff;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            transition: all 0.2s ease;
        }}
        
        .news-item:hover {{
            border-color: var(--accent-light);
            box-shadow: 0 4px 12px rgba(59,130,246,0.1);
        }}
        
        .news-item.positive {{ border-left: 4px solid var(--success); }}
        .news-item.negative {{ border-left: 4px solid var(--danger); }}
        .news-item.neutral {{ border-left: 4px solid var(--warning); }}
        
        .news-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }}
        
        .news-date {{ 
            font-size: 12px; 
            color: var(--text-light);
            font-weight: 500;
        }}
        
        .news-sentiment {{
            font-size: 11px;
            padding: 4px 10px;
            border-radius: 20px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .news-sentiment.positive {{ background: #d1fae5; color: #065f46; }}
        .news-sentiment.negative {{ background: #fee2e2; color: #991b1b; }}
        .news-sentiment.neutral {{ background: #fef3c7; color: #92400e; }}
        
        .news-title {{ 
            font-weight: 600; 
            color: var(--primary);
            margin-bottom: 8px;
            line-height: 1.5;
        }}
        
        .news-summary {{
            font-size: 13px;
            color: var(--text-light);
            margin-bottom: 12px;
        }}
        
        .news-link {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            color: var(--accent);
            text-decoration: none;
            font-size: 13px;
            font-weight: 500;
        }}
        
        .news-link:hover {{
            text-decoration: underline;
        }}
        
        /* Analysis Grid */
        .analysis-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 24px;
        }}
        
        .analysis-card {{
            background: #fff;
            border-radius: 16px;
            padding: 28px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        
        .analysis-card h4 {{
            font-family: 'Playfair Display', serif;
            font-size: 18px;
            color: var(--primary);
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .analysis-card ul {{
            list-style: none;
            padding: 0;
        }}
        
        .analysis-card li {{
            padding: 10px 0;
            padding-left: 20px;
            position: relative;
            font-size: 14px;
            color: var(--text);
            border-bottom: 1px solid #f1f5f9;
        }}
        
        .analysis-card li:last-child {{
            border-bottom: none;
        }}
        
        .analysis-card li::before {{
            content: '';
            position: absolute;
            left: 0;
            top: 50%;
            transform: translateY(-50%);
            width: 6px;
            height: 6px;
            background: var(--accent);
            border-radius: 50%;
        }}
        
        /* Money Table */
        .money-table {{ 
            width: 100%; 
            border-collapse: separate;
            border-spacing: 0;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        
        .money-table th {{ 
            background: var(--primary);
            color: white; 
            padding: 16px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .money-table td {{ 
            padding: 16px; 
            text-align: center; 
            border-bottom: 1px solid #e2e8f0;
            background: #fff;
            font-size: 14px;
        }}
        
        .money-table tr:hover td {{ background: #f8fafc; }}
        .money-table tr:last-child td {{ border-bottom: none; }}
        
        /* Advice Section */
        .advice-section {{
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            color: white;
            padding: 48px;
            border-radius: 24px;
            margin: 24px 0;
        }}
        
        .advice-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 32px;
            padding-bottom: 24px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        
        .advice-rating {{
            font-family: 'Playfair Display', serif;
            font-size: 32px;
            font-weight: 700;
        }}
        
        .advice-risk {{
            background: rgba(255,255,255,0.15);
            padding: 8px 20px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 500;
        }}
        
        .advice-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 24px;
        }}
        
        .advice-card {{
            background: rgba(255,255,255,0.08);
            padding: 24px;
            border-radius: 16px;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        
        .advice-card h5 {{
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            opacity: 0.7;
            margin-bottom: 12px;
            font-weight: 600;
        }}
        
        .advice-card p {{
            font-size: 15px;
            line-height: 1.7;
            opacity: 0.95;
        }}
        
        /* Footer */
        .footer {{ 
            text-align: center; 
            padding: 40px; 
            color: var(--text-light); 
            font-size: 13px; 
            background: #fff;
            border-top: 1px solid #e2e8f0;
        }}
        
        @media (max-width: 768px) {{
            .section {{ padding: 32px 24px; }}
            .header {{ padding: 40px 24px; }}
            .header h1 {{ font-size: 32px; }}
            .price-grid {{ grid-template-columns: repeat(2, 1fr); }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-content">
                <div class="stock-ticker">{data['stock_code']}</div>
                <h1>{data['stock_name']}</h1>
                <div class="header-subtitle">投资分析报告 | {datetime.now().strftime('%Y年%m月%d日')} | 90日分析周期</div>
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">行情摘要</div>
            <div class="price-grid">
                <div class="price-card">
                    <div class="label">当前价格</div>
                    <div class="value">¥{data['latest_price']}</div>
                </div>
                <div class="price-card">
                    <div class="label">涨跌幅</div>
                    <div class="value {'positive' if data['change_pct'] > 0 else 'negative'}">{data['change_pct']}%</div>
                    <div class="change {'positive' if data['change_pct'] > 0 else 'negative'}">{'+' if data['change_pct'] > 0 else ''}{data['change_pct']}%</div>
                </div>
                <div class="price-card">
                    <div class="label">90日最高</div>
                    <div class="value">¥{data['high_90']}</div>
                </div>
                <div class="price-card">
                    <div class="label">90日最低</div>
                    <div class="value">¥{data['low_90']}</div>
                </div>
            </div>
            {predicted_html}
        </div>
        
        <div class="section">
            <div class="section-title">技术指标</div>
            <div class="tech-grid">
                <div class="tech-item {'bullish' if data['ma5_val'] > data['ma10_val'] else 'bearish'}">
                    <div class="label">MA5</div>
                    <div class="value">¥{data['ma5_val']}</div>
                </div>
                <div class="tech-item {'bullish' if data['ma10_val'] > data['ma20_val'] else 'bearish'}">
                    <div class="label">MA10</div>
                    <div class="value">¥{data['ma10_val']}</div>
                </div>
                <div class="tech-item bullish">
                    <div class="label">MA20</div>
                    <div class="value">¥{data['ma20_val']}</div>
                </div>
                <div class="tech-item {'bearish' if data['latest_price'] > data['boll_upper_val'] * 0.98 else 'neutral'}">
                    <div class="label">BOLL上轨</div>
                    <div class="value">¥{data['boll_upper_val']}</div>
                </div>
                <div class="tech-item neutral">
                    <div class="label">BOLL中轨</div>
                    <div class="value">¥{data['boll_mid_val']}</div>
                </div>
                <div class="tech-item {'bullish' if data['latest_price'] < data['boll_lower_val'] * 1.02 else 'neutral'}">
                    <div class="label">BOLL下轨</div>
                    <div class="value">¥{data['boll_lower_val']}</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">K线图 + 均线</div>
            <div class="chart-container" id="kline-chart"></div>
        </div>
        
        <div class="section">
            <div class="section-title">BOLL布林带</div>
            <div class="chart-container" id="boll-chart"></div>
        </div>
        
        <div class="section">
            <div class="section-title">股价与成交量</div>
            <div class="chart-container" id="volume-chart"></div>
        </div>
        
        <div class="section">
            <div class="section-title">最新新闻</div>
            <div class="news-list">
                {news_items_html}
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">机构研报</div>
            {reports_html}
        </div>
        
        <div class="section">
            <div class="section-title">资金流向</div>
            <table class="money-table">
                <thead>
                    <tr>
                        <th>日期</th>
                        <th>收盘价</th>
                        <th>涨跌幅</th>
                        <th>主力净流入</th>
                    </tr>
                </thead>
                <tbody>
                    {money_rows_html}
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <div class="section-title">多维度分析</div>
            <div class="analysis-grid">
                <div class="analysis-card">
                    <h4>📈 技术面分析</h4>
                    <ul>
                        <li>{'均线多头排列，短期趋势向好' if data['ma5_val'] > data['ma10_val'] > data['ma20_val'] else '均线空头排列，短期趋势走弱' if data['ma5_val'] < data['ma10_val'] < data['ma20_val'] else '均线交织，趋势不明朗'}</li>
                        <li>{'股价接近BOLL上轨，注意回调压力' if data['latest_price'] > data['boll_upper_val'] * 0.98 else '股价接近BOLL下轨，关注反弹机会' if data['latest_price'] < data['boll_lower_val'] * 1.02 else '股价在BOLL中轨附近运行'}</li>
                        <li>90日波动区间: ¥{data['low_90']} - ¥{data['high_90']}</li>
                    </ul>
                </div>
                <div class="analysis-card">
                    <h4>📰 消息面分析</h4>
                    <ul>
                        <li>近10条新闻中，{sum(1 for n in data['news'] if n['sentiment'] == 'positive')}条积极，{sum(1 for n in data['news'] if n['sentiment'] == 'negative')}条消极</li>
                        <li>主要关键词: {', '.join(list(set([kw for n in data['news'] for kw in n['keywords']]))[:5])}</li>
                        <li>整体情绪: {sum(1 for n in data['news'] if n['sentiment'] == 'positive') > sum(1 for n in data['news'] if n['sentiment'] == 'negative') and '偏多' or sum(1 for n in data['news'] if n['sentiment'] == 'negative') > sum(1 for n in data['news'] if n['sentiment'] == 'positive') and '偏空' or '中性'}</li>
                    </ul>
                </div>
                <div class="analysis-card">
                    <h4>🏛️ 机构面分析</h4>
                    <ul>
                        <li>最新评级: {data['reports'][0]['rating'] if data['reports'] else '无评级'} ({data['reports'][0]['date'] if data['reports'] else 'N/A'})</li>
                        <li>目标价: ¥{data['reports'][0]['target_price'] if data['reports'] and data['reports'][0]['target_price'] else '未公布'}</li>
                        <li>预测EPS: {data['reports'][0]['eps'] if data['reports'] else 'N/A'}</li>
                    </ul>
                </div>
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">投资建议</div>
            <div class="advice-section">
                <div class="advice-header">
                    <div class="advice-rating">★★★☆☆ 谨慎推荐</div>
                    <div class="advice-risk">风险等级: 中等</div>
                </div>
                <div class="advice-grid">
                    <div class="advice-card">
                        <h5>短线策略 (1-2周)</h5>
                        <p>建议在¥{round(data['ma20_val']*0.98,1)}-{data['ma20_val']}区间逢低吸纳，止损位¥{round(data['latest_price']*0.95,2)}，目标位¥{round(data['latest_price']*1.08,2)}。</p>
                    </div>
                    <div class="advice-card">
                        <h5>中线策略 (1-3个月)</h5>
                        <p>持有为主，有效跌破20日均线(¥{data['ma20_val']})需考虑减仓，突破前高可看高一线。</p>
                    </div>
                    <div class="advice-card">
                        <h5>长线策略 (6个月以上)</h5>
                        <p>关注公司基本面变化和行业政策，适合定投策略，长期看好行业发展前景。</p>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>本报告仅供参考，不构成投资建议。投资有风险，入市需谨慎。</p>
            <p>数据来源: AkShare | 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        </div>
    </div>
    
    <script>
        const data = {json.dumps({k: v for k, v in data.items() if k not in ['news', 'reports', 'money']})};
        const x = data.dates.map((d, i) => i);
        
        const klineTrace = {{
            type: 'candlestick',
            x: x, open: data.open, high: data.high, low: data.low, close: data.close,
            name: 'K线', increasing: {{line: {{color: '#ef4444'}}}}, decreasing: {{line: {{color: '#10b981'}}}}
        }};
        
        const ma5Trace = {{ x: x, y: data.ma5, type: 'scatter', mode: 'lines', name: 'MA5', line: {{color: '#f59e0b', width: 1.5}}}};
        const ma10Trace = {{ x: x, y: data.ma10, type: 'scatter', mode: 'lines', name: 'MA10', line: {{color: '#3b82f6', width: 1.5}}}};
        const ma20Trace = {{ x: x, y: data.ma20, type: 'scatter', mode: 'lines', name: 'MA20', line: {{color: '#8b5cf6', width: 1.5}}}};
        
        Plotly.newPlot('kline-chart', [klineTrace, ma5Trace, ma10Trace, ma20Trace], {{
            title: {{text: 'K线图 + 均线', font: {{size: 16, color: '#0f172a'}}}},
            xaxis: {{ tickmode: 'array', tickvals: x.filter((_, i) => i % 5 === 0), ticktext: data.dates.filter((_, i) => i % 5 === 0), tickangle: 45 }},
            yaxis: {{ title: '价格(元)' }},
            template: 'plotly_white',
            height: 500,
            hovermode: 'x unified'
        }});
        
        const bollUpper = {{ x: x, y: data.boll_upper, type: 'scatter', mode: 'lines', name: '上轨', line: {{color: '#ef4444', dash: 'dash'}}}};
        const bollMid = {{ x: x, y: data.boll_mid, type: 'scatter', mode: 'lines', name: '中轨', line: {{color: '#3b82f6', width: 2}}}};
        const bollLower = {{ x: x, y: data.boll_lower, type: 'scatter', mode: 'lines', name: '下轨', line: {{color: '#10b981', dash: 'dash'}}}};
        
        Plotly.newPlot('boll-chart', [klineTrace, bollUpper, bollMid, bollLower], {{
            title: {{text: 'BOLL布林带', font: {{size: 16, color: '#0f172a'}}}},
            xaxis: {{ tickmode: 'array', tickvals: x.filter((_, i) => i % 5 === 0), ticktext: data.dates.filter((_, i) => i % 5 === 0), tickangle: 45 }},
            yaxis: {{ title: '价格(元)' }},
            template: 'plotly_white',
            height: 500,
            hovermode: 'x unified'
        }});
        
        const volumeBar = {{
            type: 'bar', x: x, y: data.volume, name: '成交量',
            marker: {{ color: data.close.map((c, i) => c >= data.open[i] ? '#ef4444' : '#10b981') }},
            yaxis: 'y2'
        }};
        
        Plotly.newPlot('volume-chart', [klineTrace, volumeBar], {{
            title: {{text: '股价与成交量', font: {{size: 16, color: '#0f172a'}}}},
            xaxis: {{ tickmode: 'array', tickvals: x.filter((_, i) => i % 5 === 0), ticktext: data.dates.filter((_, i) => i % 5 === 0), tickangle: 45 }},
            yaxis: {{ title: '价格(元)', domain: [0.3, 1] }},
            yaxis2: {{ title: '成交量', domain: [0, 0.25], showgrid: false }},
            template: 'plotly_white',
            height: 600,
            hovermode: 'x unified'
        }});
    </script>
</body>
</html>"""
    
    return html

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python analyze_v2.py <股票代码或名称>")
        sys.exit(1)
    
    query = sys.argv[1]
    stock_code = get_stock_code(query)
    
    if stock_code is None:
        print(f"未找到股票: {query}")
        sys.exit(1)

    try:
        output_file = generate_report(stock_code)
        print(f"\n报告已保存到: {output_file}")
    except Exception as exc:
        print(f"生成报告失败: {exc}")
        sys.exit(1)
