#!/usr/bin/env python3
"""
股票投资分析报告生成脚本 - 增强版
生成90天的交互式股票分析报告，包含新闻链接、最新机构评级、综合分析
"""

import json
import sys
import os
import time
from datetime import datetime, timedelta

try:
    import akshare as ak
    import pandas as pd
except ImportError as exc:
    missing_pkg = exc.name or str(exc)
    print(f"缺少依赖: {missing_pkg}")
    print("请先安装: pip3 install akshare pandas")
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

def get_stock_code(query):
    """根据输入获取股票代码"""
    query = query.strip()
    
    # 如果是纯数字，直接认为是股票代码
    if query.isdigit() and len(query) == 6:
        return query
    
    # 搜索股票名称
    try:
        stocks = call_akshare(ak.stock_zh_a_spot_em)
        # 精确匹配
        exact_match = stocks[stocks['名称'] == query]
        if len(exact_match) > 0:
            return exact_match.iloc[0]['代码']
        # 模糊匹配
        matches = stocks[stocks['名称'].str.contains(query, na=False)]
        if len(matches) > 0:
            return matches.iloc[0]['代码']
    except:
        pass
    
    return None

def analyze_technical(data):
    """技术分析"""
    analysis = []
    
    # 均线分析
    if data['ma5_val'] > data['ma10_val'] > data['ma20_val']:
        analysis.append("✅ 均线多头排列，短期趋势向好")
    elif data['ma5_val'] < data['ma10_val'] < data['ma20_val']:
        analysis.append("⚠️ 均线空头排列，短期趋势走弱")
    else:
        analysis.append("➡️ 均线交织，趋势不明朗")
    
    # BOLL分析
    if data['latest_price'] > data['boll_upper_val'] * 0.98:
        analysis.append("⚠️ 股价接近BOLL上轨，存在回调压力")
    elif data['latest_price'] < data['boll_lower_val'] * 1.02:
        analysis.append("✅ 股价接近BOLL下轨，可能存在反弹机会")
    else:
        analysis.append("➡️ 股价在BOLL中轨附近运行")
    
    # 涨跌幅分析
    change_90 = (data['latest_price'] - data['low_90']) / data['low_90'] * 100
    if change_90 > 50:
        analysis.append(f"⚠️ 90日涨幅达{change_90:.1f}%，累计获利盘较多")
    elif change_90 > 20:
        analysis.append(f"✅ 90日涨幅{change_90:.1f}%，表现良好")
    elif change_90 < -20:
        analysis.append(f"⚠️ 90日跌幅{abs(change_90):.1f}%，走势较弱")
    
    return analysis

def analyze_news(news_list):
    """新闻分析"""
    if not news_list:
        return ["暂无相关新闻"], "中性"
    
    analysis = []
    sentiment = "中性"
    
    # 统计新闻时间分布
    recent_news = [n for n in news_list if '2026-03' in n[0] or '2026-02' in n[0]]
    if len(recent_news) >= 3:
        analysis.append(f"✅ 近期新闻活跃，近2个月有{len(recent_news)}条相关新闻")
    
    # 关键词分析
    positive_keywords = ['涨', '增持', '利好', '突破', '创新高', '净流入', '上涨']
    negative_keywords = ['跌', '减持', '利空', '跌破', '创新低', '净流出', '下跌', '召回', '处罚']
    
    positive_count = sum(1 for n in news_list for kw in positive_keywords if kw in n[1])
    negative_count = sum(1 for n in news_list for kw in negative_keywords if kw in n[1])
    
    if positive_count > negative_count:
        sentiment = "偏多"
        analysis.append(f"✅ 新闻情绪偏多，发现{positive_count}条积极信号")
    elif negative_count > positive_count:
        sentiment = "偏空"
        analysis.append(f"⚠️ 新闻情绪偏空，发现{negative_count}条消极信号")
    else:
        analysis.append("➡️ 新闻情绪中性，多空因素交织")
    
    return analysis, sentiment

def analyze_institution(reports):
    """机构评级分析"""
    if not reports:
        return ["暂无机构评级数据"], "未知", None
    
    analysis = []
    
    # 按日期排序获取最新评级
    sorted_reports = sorted(reports, key=lambda x: x[0], reverse=True)
    latest_report = sorted_reports[0]
    
    rating = latest_report[2] if len(latest_report) > 2 and latest_report[2] else "无评级"
    report_date = latest_report[0]
    
    analysis.append(f"📊 最新机构评级: {rating} ({report_date})")
    
    # 评级解读
    if rating in ['买入', '强烈推荐', '增持']:
        sentiment = "看多"
        analysis.append("✅ 机构整体看多，建议关注")
    elif rating in ['中性', '持有', '观望']:
        sentiment = "中性"
        analysis.append("➡️ 机构态度中性，谨慎观望")
    elif rating in ['卖出', '减持']:
        sentiment = "看空"
        analysis.append("⚠️ 机构看空，需注意风险")
    else:
        sentiment = "未知"
    
    # 盈利预测
    if len(latest_report) > 3 and latest_report[3] and latest_report[3] != 'nan':
        analysis.append(f"📈 2025年预测EPS: {latest_report[3]}元")
    if len(latest_report) > 4 and latest_report[4] and latest_report[4] != 'nan':
        analysis.append(f"📊 2025年预测PE: {latest_report[4]}倍")
    
    return analysis, sentiment, latest_report

def generate_investment_advice(tech_analysis, news_analysis, inst_analysis, data):
    """生成投资建议"""
    
    # 综合评分
    score = 0
    
    # 技术指标评分
    if '多头排列' in str(tech_analysis):
        score += 2
    if '回调压力' in str(tech_analysis):
        score -= 1
    if '反弹机会' in str(tech_analysis):
        score += 1
    
    # 新闻评分
    if '偏多' in str(news_analysis):
        score += 1
    elif '偏空' in str(news_analysis):
        score -= 1
    
    # 机构评分
    if '看多' in str(inst_analysis):
        score += 2
    elif '看空' in str(inst_analysis):
        score -= 2
    
    # 确定评级
    if score >= 3:
        rating = "★★★★☆ 推荐"
        risk = "中等"
    elif score >= 1:
        rating = "★★★☆☆ 谨慎推荐"
        risk = "中等"
    elif score >= -1:
        rating = "★★☆☆☆ 中性"
        risk = "中等偏高"
    else:
        rating = "★☆☆☆☆ 回避"
        risk = "高"
    
    # 生成操作建议
    current_price = data['latest_price']
    ma20 = data['ma20_val']
    
    short_stop = round(current_price * 0.95, 2)
    short_target = round(current_price * 1.08, 2)
    
    advice = {
        'rating': rating,
        'risk': risk,
        'short': f"建议在{round(ma20*0.98,1)}-{ma20}元区间逢低吸纳，止损位{short_stop}元，目标位{short_target}元",
        'medium': f"持有为主，有效跌破20日均线({ma20}元)需考虑减仓，突破前高可看高一线",
        'long': "关注公司基本面变化和行业政策，适合定投策略"
    }
    
    return advice

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
    
    # 获取新闻（带链接）
    try:
        news = ak.stock_news_em(symbol=stock_code)
        news_list = []
        for idx, row in news.head(10).iterrows():
            title = row.get('新闻标题', '')
            date = str(row.get('发布时间', ''))[:10]
            # 生成搜索链接
            search_url = f"https://www.baidu.com/s?wd={stock_name}+{title[:30]}"
            news_list.append([date, title, search_url])
    except:
        news_list = []
    
    # 获取研报（带链接）
    try:
        reports = ak.stock_research_report_em(symbol=stock_code)
        report_list = []
        for idx, row in reports.iterrows():
            date = str(row.get('日期', ''))
            title = row.get('报告名称', '')
            rating = row.get('东财评级', '')
            eps = str(row.get('2025-盈利预测-收益', ''))
            pe = str(row.get('2025-盈利预测-市盈率', ''))
            pdf_link = row.get('报告PDF链接', '')
            report_list.append([date, title, rating, eps, pe, pdf_link])
        # 按日期排序
        report_list.sort(key=lambda x: x[0], reverse=True)
    except:
        report_list = []
    
    # 获取资金流向
    try:
        market = "sh" if stock_code.startswith('6') else "sz"
        money = ak.stock_individual_fund_flow(stock=stock_code, market=market)
        money_list = [[str(row.get('日期', '')), row.get('收盘价', 0), 
                      row.get('涨跌幅', 0), row.get('主力净流入-净额', 0) or 0] 
                     for idx, row in money.tail(10).iterrows()]
    except:
        money_list = []
    
    # 准备数据
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
        'latest_price': round(latest['Close'], 2),
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
    
    # 进行分析
    tech_analysis = analyze_technical(data)
    news_analysis, news_sentiment = analyze_news(news_list)
    inst_analysis, inst_sentiment, latest_report = analyze_institution(report_list)
    advice = generate_investment_advice(tech_analysis, news_analysis, inst_analysis, data)
    
    data['tech_analysis'] = tech_analysis
    data['news_analysis'] = news_analysis
    data['news_sentiment'] = news_sentiment
    data['inst_analysis'] = inst_analysis
    data['inst_sentiment'] = inst_sentiment
    data['advice'] = advice
    data['latest_report'] = latest_report
    
    # 生成HTML报告
    html = generate_html(data)
    
    output_file = os.path.join(output_dir, f"{stock_name}_{stock_code}_投资分析报告.html")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✓ 报告已生成: {output_file}")
    return output_file

def generate_html(data):
    """生成美化后的HTML报告"""
    import json
    
    # 研报HTML生成
    reports_html = ""
    for r in data['reports'][:5]:
        date = r[0]
        title = r[1]
        rating = r[2] if r[2] else "无评级"
        eps = r[3] if r[3] and r[3] != 'nan' else "-"
        pe = r[4] if r[4] and r[4] != 'nan' else "-"
        pdf_link = r[5] if len(r) > 5 and r[5] else ""
        
        rating_color = "#27ae60" if rating in ['买入', '强烈推荐', '增持'] else "#e74c3c" if rating in ['卖出', '减持'] else "#f39c12"
        pdf_btn = f'<a href="{pdf_link}" target="_blank" style="color:#3498db;text-decoration:none;font-size:12px;">📄 查看研报</a>' if pdf_link else ''
        
        reports_html += f'''
        <div style="background:#fff;border-radius:8px;padding:15px;margin:10px 0;box-shadow:0 2px 4px rgba(0,0,0,0.1);border-left:4px solid {rating_color};">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <span style="color:#666;font-size:12px;">{date}</span>
                <span style="background:{rating_color};color:white;padding:2px 8px;border-radius:4px;font-size:12px;">{rating}</span>
            </div>
            <div style="margin:8px 0;font-weight:500;">{title}</div>
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <span style="color:#666;font-size:12px;">预测EPS: {eps} | PE: {pe}</span>
                {pdf_btn}
            </div>
        </div>
        '''
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{data['stock_name']}({data['stock_code']}) 投资分析报告</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary: #1e3c72;
            --secondary: #2a5298;
            --accent: #667eea;
            --success: #27ae60;
            --danger: #e74c3c;
            --warning: #f39c12;
            --bg: #f5f7fa;
            --card: #ffffff;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: 'Noto Sans SC', -apple-system, BlinkMacSystemFont, sans-serif;
            line-height: 1.6; 
            color: #333; 
            background: var(--bg);
            padding: 20px;
        }}
        .container {{ 
            max-width: 1200px; 
            margin: 0 auto; 
            background: var(--card); 
            border-radius: 16px; 
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            overflow: hidden;
        }}
        .header {{ 
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%); 
            color: white; 
            padding: 40px; 
            text-align: center;
            position: relative;
        }}
        .header::before {{
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.05'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
            opacity: 0.1;
        }}
        .header h1 {{ font-size: 32px; margin-bottom: 10px; font-weight: 700; position: relative; }}
        .header .subtitle {{ opacity: 0.9; font-size: 14px; position: relative; }}
        
        .section {{ padding: 30px 40px; border-bottom: 1px solid #eee; }}
        .section:last-child {{ border-bottom: none; }}
        .section-title {{ 
            font-size: 20px; 
            font-weight: 600; 
            color: var(--primary); 
            margin-bottom: 20px; 
            padding-left: 16px; 
            border-left: 4px solid var(--accent);
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .price-box {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); 
            gap: 20px; 
        }}
        .price-item {{ 
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); 
            padding: 20px; 
            border-radius: 12px; 
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            transition: transform 0.2s;
        }}
        .price-item:hover {{ transform: translateY(-2px); }}
        .price-item .label {{ font-size: 13px; color: #666; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px; }}
        .price-item .value {{ font-size: 24px; font-weight: 700; }}
        .positive {{ color: var(--success); }}
        .negative {{ color: var(--danger); }}
        .neutral {{ color: var(--warning); }}
        
        .tech-grid {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
            gap: 20px; 
        }}
        .tech-item {{ 
            background: linear-gradient(135deg, #f8f9fa 0%, #fff 100%); 
            padding: 20px; 
            border-radius: 12px; 
            border-left: 4px solid #ddd;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }}
        .tech-item.positive {{ border-left-color: var(--success); }}
        .tech-item.negative {{ border-left-color: var(--danger); }}
        .tech-item .label {{ font-size: 12px; color: #666; text-transform: uppercase; letter-spacing: 0.5px; }}
        .tech-item .value {{ font-size: 20px; font-weight: 700; margin-top: 8px; }}
        
        .chart-container {{ margin: 20px 0; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }}
        
        .news-list {{ list-style: none; }}
        .news-list li {{ 
            padding: 16px; 
            margin: 10px 0;
            background: #f8f9fa; 
            border-radius: 10px;
            display: flex;
            align-items: flex-start;
            gap: 12px;
            transition: all 0.2s;
        }}
        .news-list li:hover {{ background: #e9ecef; }}
        .news-list .date {{ 
            font-size: 12px; 
            color: #666; 
            background: #dee2e6;
            padding: 4px 8px;
            border-radius: 4px;
            white-space: nowrap;
        }}
        .news-list .content {{ flex: 1; }}
        .news-list .title {{ color: #333; font-weight: 500; }}
        .news-list a {{ 
            color: var(--accent); 
            text-decoration: none; 
            font-size: 12px;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            margin-top: 4px;
        }}
        .news-list a:hover {{ text-decoration: underline; }}
        
        .analysis-box {{
            background: linear-gradient(135deg, #f8f9fa 0%, #fff 100%);
            border-radius: 12px;
            padding: 20px;
            margin: 15px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }}
        .analysis-box h4 {{
            color: var(--primary);
            font-size: 16px;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .analysis-box ul {{
            list-style: none;
            padding-left: 0;
        }}
        .analysis-box li {{
            padding: 8px 0;
            padding-left: 24px;
            position: relative;
        }}
        .analysis-box li::before {{
            content: '•';
            position: absolute;
            left: 8px;
            color: var(--accent);
            font-weight: bold;
        }}
        
        .money-table {{ 
            width: 100%; 
            border-collapse: separate;
            border-spacing: 0;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }}
        .money-table th {{ 
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%); 
            color: white; 
            padding: 14px; 
            font-size: 13px;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .money-table td {{ 
            padding: 14px; 
            text-align: center; 
            border-bottom: 1px solid #e9ecef;
            background: #fff;
        }}
        .money-table tr:hover td {{ background: #f8f9fa; }}
        .money-table tr:last-child td {{ border-bottom: none; }}
        
        .advice-box {{ 
            background: linear-gradient(135deg, var(--accent) 0%, #764ba2 100%); 
            color: white; 
            padding: 30px; 
            border-radius: 16px;
            box-shadow: 0 4px 20px rgba(102,126,234,0.3);
        }}
        .advice-box .rating {{ 
            font-size: 24px; 
            font-weight: 700; 
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .advice-box .stars {{ color: #ffd700; font-size: 28px; }}
        .advice-box .risk-badge {{
            background: rgba(255,255,255,0.2);
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 14px;
            margin-left: auto;
        }}
        .advice-box h4 {{ 
            margin: 20px 0 12px 0; 
            font-size: 16px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .advice-box ul {{ margin-left: 0; list-style: none; }}
        .advice-box li {{ 
            padding: 10px 0; 
            padding-left: 28px;
            position: relative;
            opacity: 0.95;
        }}
        .advice-box li::before {{
            content: '';
            position: absolute;
            left: 8px;
            top: 50%;
            transform: translateY(-50%);
            width: 8px;
            height: 8px;
            background: rgba(255,255,255,0.6);
            border-radius: 50%;
        }}
        .advice-box .highlight {{
            background: rgba(255,255,255,0.15);
            padding: 16px;
            border-radius: 10px;
            margin: 12px 0;
        }}
        .advice-box .highlight strong {{
            display: block;
            margin-bottom: 8px;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            opacity: 0.9;
        }}
        
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .summary-card {{
            background: #fff;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.08);
            border-top: 4px solid var(--accent);
        }}
        .summary-card h5 {{
            color: var(--primary);
            font-size: 14px;
            margin-bottom: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .summary-card .sentiment {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            margin-bottom: 12px;
        }}
        .sentiment-bullish {{ background: #d4edda; color: #155724; }}
        .sentiment-bearish {{ background: #f8d7da; color: #721c24; }}
        .sentiment-neutral {{ background: #fff3cd; color: #856404; }}
        
        .footer {{ 
            text-align: center; 
            padding: 30px; 
            color: #666; 
            font-size: 13px; 
            background: #f8f9fa;
            border-top: 1px solid #e9ecef;
        }}
        
        @media (max-width: 768px) {{
            .section {{ padding: 20px; }}
            .header {{ padding: 30px 20px; }}
            .header h1 {{ font-size: 24px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 {data['stock_name']}({data['stock_code']}) 投资分析报告</h1>
            <div class="subtitle">报告日期: {datetime.now().strftime('%Y-%m-%d')} | 分析周期: 最近90个交易日</div>
        </div>
        
        <div class="section">
            <div class="section-title">📈 行情摘要</div>
            <div class="price-box">
                <div class="price-item">
                    <div class="label">当前价格</div>
                    <div class="value">¥{data['latest_price']}</div>
                </div>
                <div class="price-item">
                    <div class="label">涨跌幅</div>
                    <div class="value {'positive' if data['change_pct'] > 0 else 'negative'}">{data['change_pct']}%</div>
                </div>
                <div class="price-item">
                    <div class="label">90日最高</div>
                    <div class="value negative">¥{data['high_90']}</div>
                </div>
                <div class="price-item">
                    <div class="label">90日最低</div>
                    <div class="value positive">¥{data['low_90']}</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">🔧 技术指标</div>
            <div class="tech-grid">
                <div class="tech-item {'positive' if data['ma5_val'] > data['ma10_val'] else 'negative'}"><div class="label">MA5</div><div class="value">¥{data['ma5_val']}</div></div>
                <div class="tech-item {'positive' if data['ma10_val'] > data['ma20_val'] else 'negative'}"><div class="label">MA10</div><div class="value">¥{data['ma10_val']}</div></div>
                <div class="tech-item {'positive' if data['ma20_val'] > data['ma20_val'] * 0.95 else 'negative'}"><div class="label">MA20</div><div class="value">¥{data['ma20_val']}</div></div>
                <div class="tech-item {'negative' if data['latest_price'] > data['boll_upper_val'] * 0.98 else 'positive' if data['latest_price'] < data['boll_lower_val'] * 1.02 else ''}"><div class="label">BOLL上轨</div><div class="value">¥{data['boll_upper_val']}</div></div>
                <div class="tech-item"><div class="label">BOLL中轨</div><div class="value">¥{data['boll_mid_val']}</div></div>
                <div class="tech-item"><div class="label">BOLL下轨</div><div class="value">¥{data['boll_lower_val']}</div></div>
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">📊 K线图 + 均线</div>
            <div class="chart-container" id="kline-chart"></div>
        </div>
        
        <div class="section">
            <div class="section-title">📊 BOLL布林带</div>
            <div class="chart-container" id="boll-chart"></div>
        </div>
        
        <div class="section">
            <div class="section-title">📊 股价与成交量</div>
            <div class="chart-container" id="volume-chart"></div>
        </div>
        
        <div class="section">
            <div class="section-title">📰 最新新闻</div>
            <ul class="news-list">
                {''.join([f'<li><span class="date">{n[0]}</span><div class="content"><div class="title">{n[1]}</div><a href="{n[2]}" target="_blank">🔍 搜索详情 →</a></div></li>' for n in data['news']])}
            </ul>
        </div>
        
        <div class="section">
            <div class="section-title">🏛️ 机构评级与盈利预测</div>
            {reports_html}
        </div>
        
        <div class="section">
            <div class="section-title">💰 资金流向 (近10日)</div>
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
                    {''.join([f'<tr><td>{m[0]}</td><td>¥{m[1]}</td><td class="{"positive" if m[2] > 0 else "negative"}">{m[2]:.2f}%</td><td class="{"positive" if m[3] > 0 else "negative"}">{"+" if m[3] > 0 else ""}{int(m[3]):,}</td></tr>' for m in data['money']])}
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <div class="section-title">📊 多维度分析</div>
            <div class="summary-grid">
                <div class="summary-card">
                    <h5>📈 技术面分析</h5>
                    <span class="sentiment sentiment-{data['news_sentiment'].lower() if data['news_sentiment'] in ['偏多', '偏空'] else 'neutral'}">{data['news_sentiment']}</span>
                    <ul style="list-style:none;padding:0;">
                        {''.join([f'<li style="padding:4px 0;">{item}</li>' for item in data['tech_analysis']])}
                    </ul>
                </div>
                <div class="summary-card">
                    <h5>📰 消息面分析</h5>
                    <span class="sentiment sentiment-{data['news_sentiment'].lower() if data['news_sentiment'] in ['偏多', '偏空'] else 'neutral'}">{data['news_sentiment']}</span>
                    <ul style="list-style:none;padding:0;">
                        {''.join([f'<li style="padding:4px 0;">{item}</li>' for item in data['news_analysis']])}
                    </ul>
                </div>
                <div class="summary-card">
                    <h5>🏛️ 机构面分析</h5>
                    <span class="sentiment sentiment-{data['inst_sentiment'].lower() if data['inst_sentiment'] in ['看多', '看空'] else 'neutral'}">{data['inst_sentiment']}</span>
                    <ul style="list-style:none;padding:0;">
                        {''.join([f'<li style="padding:4px 0;">{item}</li>' for item in data['inst_analysis']])}
                    </ul>
                </div>
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">💡 综合投资建议</div>
            <div class="advice-box">
                <div class="rating">
                    <span class="stars">{data['advice']['rating'].split()[0]}</span>
                    {data['advice']['rating'].split(' ', 1)[1]}
                    <span class="risk-badge">风险等级: {data['advice']['risk']}</span>
                </div>
                
                <div class="highlight">
                    <strong>📋 操作建议</strong>
                    <ul>
                        <li><strong>短线(1-2周):</strong> {data['advice']['short']}</li>
                        <li><strong>中线(1-3个月):</strong> {data['advice']['medium']}</li>
                        <li><strong>长线(6个月以上):</strong> {data['advice']['long']}</li>
                    </ul>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>本报告仅供参考，不构成投资建议。投资有风险，入市需谨慎。</p>
            <p>数据来源: AkShare | 报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        </div>
    </div>
    
    <script>
        const data = {json.dumps({k: v for k, v in data.items() if k not in ['tech_analysis', 'news_analysis', 'inst_analysis', 'advice', 'latest_report']})};
        
        const x = data.dates.map((d, i) => i);
        
        // K线图
        const klineTrace = {{
            type: 'candlestick',
            x: x,
            open: data.open,
            high: data.high,
            low: data.low,
            close: data.close,
            name: 'K线',
            increasing: {{line: {{color: '#e74c3c'}}}},
            decreasing: {{line: {{color: '#27ae60'}}}}
        }};
        
        const ma5Trace = {{ x: x, y: data.ma5, type: 'scatter', mode: 'lines', name: 'MA5', line: {{color: '#f39c12', width: 1.5}}}};
        const ma10Trace = {{ x: x, y: data.ma10, type: 'scatter', mode: 'lines', name: 'MA10', line: {{color: '#3498db', width: 1.5}}}};
        const ma20Trace = {{ x: x, y: data.ma20, type: 'scatter', mode: 'lines', name: 'MA20', line: {{color: '#9b59b6', width: 1.5}}}};
        
        Plotly.newPlot('kline-chart', [klineTrace, ma5Trace, ma10Trace, ma20Trace], {{
            title: {{text: 'K线图 + 均线', font: {{size: 16}}}},
            xaxis: {{ tickmode: 'array', tickvals: x.filter((_, i) => i % 5 === 0), ticktext: data.dates.filter((_, i) => i % 5 === 0), tickangle: 45 }},
            yaxis: {{ title: '价格(元)' }},
            template: 'plotly_white',
            height: 500,
            hovermode: 'x unified'
        }});
        
        // BOLL图
        const bollUpper = {{ x: x, y: data.boll_upper, type: 'scatter', mode: 'lines', name: '上轨', line: {{color: '#e74c3c', dash: 'dash'}}}};
        const bollMid = {{ x: x, y: data.boll_mid, type: 'scatter', mode: 'lines', name: '中轨', line: {{color: '#3498db', width: 2}}}};
        const bollLower = {{ x: x, y: data.boll_lower, type: 'scatter', mode: 'lines', name: '下轨', line: {{color: '#27ae60', dash: 'dash'}}}};
        
        Plotly.newPlot('boll-chart', [klineTrace, bollUpper, bollMid, bollLower], {{
            title: {{text: 'BOLL布林带', font: {{size: 16}}}},
            xaxis: {{ tickmode: 'array', tickvals: x.filter((_, i) => i % 5 === 0), ticktext: data.dates.filter((_, i) => i % 5 === 0), tickangle: 45 }},
            yaxis: {{ title: '价格(元)' }},
            template: 'plotly_white',
            height: 500,
            hovermode: 'x unified'
        }});
        
        // 成交量图
        const volumeBar = {{
            type: 'bar',
            x: x,
            y: data.volume,
            name: '成交量',
            marker: {{ color: data.close.map((c, i) => c >= data.open[i] ? '#e74c3c' : '#27ae60') }},
            yaxis: 'y2'
        }};
        
        Plotly.newPlot('volume-chart', [klineTrace, volumeBar], {{
            title: {{text: '股价与成交量', font: {{size: 16}}}},
            xaxis: {{ tickmode: 'array', tickvals: x.filter((_, i) => i % 5 === 0), ticktext: data.dates.filter((_, i) => i % 5 === 0), tickangle: 45 }},
            yaxis: {{ title: '价格(元)', domain: [0.3, 1] }},
            yaxis2: {{ title: '成交量', domain: [0, 0.25], showgrid: false }},
            template: 'plotly_white',
            height: 600,
            hovermode: 'x unified'
        }});
    </script>
</body>
</html>'''
    
    return html

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python analyze.py <股票代码或名称>")
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
