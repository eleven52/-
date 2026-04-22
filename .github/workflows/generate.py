import requests, json, re
from datetime import datetime, timezone, timedelta

tz = timezone(timedelta(hours=8))
now = datetime.now(tz)
date = now.strftime('%Y%m%d')
date_cn = now.strftime('%Y年%-m月%-d日')
weekday = ['一','二','三','四','五','六','日'][now.weekday()]

# ── 1. 实时行情 ──────────────────────────────────────────────
def get_prices():
    try:
        r = requests.get(
            'https://api.coingecko.com/api/v3/simple/price'
            '?ids=bitcoin,ethereum,solana,ripple&vs_currencies=usd&include_24hr_change=true',
            timeout=10, headers={'User-Agent': 'Mozilla/5.0'}
        ).json()
        def fmt(k):
            v = r[k]['usd']
            c = r[k]['usd_24h_change']
            arrow = '▲' if c >= 0 else '▼'
            cls = 'up' if c >= 0 else 'down'
            price = f'${v:,.0f}' if v > 100 else f'${v:,.3f}'
            chg = f'<div class="coin-change {cls}">{arrow} {abs(c):.2f}% 24H</div>'
            return price, chg
        return {
            'btc': fmt('bitcoin'), 'eth': fmt('ethereum'),
            'sol': fmt('solana'),  'xrp': fmt('ripple')
        }
    except:
        dummy = ('--', '')
        return {'btc': dummy, 'eth': dummy, 'sol': dummy, 'xrp': dummy}

# ── 2. 恐慌贪婪指数 ──────────────────────────────────────────
def get_fng():
    try:
        d = requests.get('https://api.alternative.me/fng/?limit=1', timeout=10).json()
        v = d['data'][0]['value']
        label_map = {
            'Extreme Fear': '极度恐慌', 'Fear': '恐慌',
            'Neutral': '中性', 'Greed': '贪婪', 'Extreme Greed': '极度贪婪'
        }
        l = label_map.get(d['data'][0]['value_classification'], '--')
        color = '#FF4D4D' if int(v) < 40 else ('#BCFF2F' if int(v) > 60 else '#999')
        return v, l, color
    except:
        return '--', '--', '#999'

# ── 3. 抓取 Odaily 快讯 ──────────────────────────────────────
def get_odaily_news():
    items = []
    try:
        r = requests.get(
            'https://www.odaily.news/api/pp/api/app-feeds/newsflash'
            '?b_id=&per_page=30&show_all=1',
            timeout=15,
            headers={
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)',
                'Referer': 'https://www.odaily.news/'
            }
        )
        data = r.json()
        posts = data.get('data', {}).get('items', [])
        cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(hours=14)
        for p in posts[:30]:
            pub = p.get('published_at') or p.get('created_at', '')
            try:
                t = datetime.fromisoformat(pub.replace('Z', '+00:00')).astimezone(tz)
                if t < cutoff:
                    continue
            except:
                pass
            title = p.get('title', '').strip()
            summary = p.get('description', '') or p.get('summary', '')
            summary = re.sub(r'<[^>]+>', '', summary).strip()[:200]
            pid = p.get('entity_id') or p.get('id', '')
            url = f'https://www.odaily.news/zh-CN/newsflash/{pid}' if pid else 'https://www.odaily.news/zh-CN'
            if title:
                items.append({'title': title, 'summary': summary, 'url': url, 'source': 'Odaily'})
    except Exception as e:
        print(f'Odaily抓取失败: {e}')
    return items[:15]

# ── 4. 抓取 CoinDesk 头条 ────────────────────────────────────
def get_coindesk_news():
    items = []
    try:
        r = requests.get(
            'https://www.coindesk.com/arc/outboundfeeds/rss/',
            timeout=15,
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        titles = re.findall(r'<title><!\[CDATA\[(.*?)\]\]></title>', r.text)
        links  = re.findall(r'<link>(https://www\.coindesk\.com/[^<]+)</link>', r.text)
        descs  = re.findall(r'<description><!\[CDATA\[(.*?)\]\]></description>', r.text, re.DOTALL)
        for i, title in enumerate(titles[1:9], 0):
            title = title.strip()
            url   = links[i] if i < len(links) else 'https://www.coindesk.com'
            desc  = re.sub(r'<[^>]+>', '', descs[i]).strip()[:180] if i < len(descs) else ''
            if title:
                items.append({'title': title, 'summary': desc, 'url': url, 'source': 'CoinDesk'})
    except Exception as e:
        print(f'CoinDesk抓取失败: {e}')
    return items[:6]

# ── 5. 分类规则 ───────────────────────────────────────────────
CATS = [
    ('⚖️', '全球监管',  ['SEC', 'ETF', '监管', '合规', '法案', '执法', 'CFTC', 'FCA', 'regulation', 'approve']),
    ('🏛️', '货币政策',  ['降息', '加息', '美联储', 'FOMC', '鲍威尔', '利率', 'Fed', 'rate', 'QE', 'QT']),
    ('📊', '宏观数据',   ['CPI', '非农', 'GDP', '通胀', '就业', '美元', 'DXY', '黄金', '原油']),
    ('🏦', '传统金融',   ['银行', '股市', '纳指', '标普', '高盛', '摩根', '贝莱德', 'BlackRock', 'bank']),
    ('🌍', '全球事件',   ['战争', '制裁', '地缘', '伊朗', '俄罗斯', '关税', '停火', '海峡']),
    ('⛓️', '链上事件',   ['黑客', '被盗', '攻击', 'exploit', '漏洞', '巨鲸', '转移', '清算', 'hack']),
    ('🚀', '行业趋势',   ['RWA', 'AI', 'DePIN', 'Meme', '稳定币', 'stablecoin', 'Layer2', 'ZK', 'DeFi']),
    ('📈', '加密数据',   ['BTC', 'ETH', 'SOL', '比特币', '以太坊', '价格', '涨', '跌', '持仓', 'TVL']),
    ('🧠', '观点研报',   ['分析师', '预测', '报告', '研究', 'analyst', 'report', '观点', 'KOL']),
    ('🅾️', 'OKX动态',   ['OKX', 'okx', 'OK集团']),
]

def classify(title, summary):
    text = title + ' ' + summary
    for icon, name, kws in CATS:
        for kw in kws:
            if kw.lower() in text.lower():
                return icon, name
    return ('📋', '行业动态')

def priority(title, summary):
    text = title + ' ' + summary
    high_kws = ['SEC', '美联储', 'FOMC', '降息', '黑客', '被盗', 'ETF', '制裁', '战争', '停火', '海峡', '攻击', '巨鲸']
    low_kws  = ['预测', '分析', '观点', '提醒', '提示']
    for kw in high_kws:
        if kw in text:
            return 'high', '高价值'
    for kw in low_kws:
        if kw in text:
            return 'low', '情绪噪音'
    return 'mid', '中优级'

# ── 6. 组装新闻 ───────────────────────────────────────────────
prices = get_prices()
fng_v, fng_l, fng_color = get_fng()
news_all = get_odaily_news() + get_coindesk_news()

# 去重
seen = set()
news_dedup = []
for n in news_all:
    key = n['title'][:20]
    if key not in seen:
        seen.add(key)
        news_dedup.append(n)

# 分类
sections = {}
for n in news_dedup:
    icon, cat = classify(n['title'], n['summary'])
    prio_cls, prio_label = priority(n['title'], n['summary'])
    n['icon'] = icon
    n['cat']  = cat
    n['prio_cls']   = prio_cls
    n['prio_label'] = prio_label
    sections.setdefault(cat, {'icon': icon, 'items': []})['items'].append(n)

# ── 7. 生成 HTML ──────────────────────────────────────────────
def render_section(cat_name, cat_data):
    items_html = ''
    for n in cat_data['items']:
        items_html += f'''
        <div class="news-item">
          <div class="priority {n["prio_cls"]}">{n["prio_label"]}</div>
          <div class="news-title">{n["title"]}</div>
          {'<div class="news-detail">' + n["summary"] + '</div>' if n["summary"] else ''}
          <div class="news-source">来源：<a href="{n["url"]}" target="_blank">{n["source"]}</a></div>
        </div>'''
    return f'''
    <div class="section">
      <div class="section-header">
        <span class="section-icon">{cat_data["icon"]}</span>
        <span class="section-title">{cat_name}</span>
        <span class="section-count">{len(cat_data["items"])} 条</span>
      </div>
      {items_html}
    </div>'''

sections_html = ''.join(render_section(k, v) for k, v in sections.items() if v['items'])

btc_p, btc_c = prices['btc']
eth_p, eth_c = prices['eth']
sol_p, sol_c = prices['sol']
xrp_p, xrp_c = prices['xrp']

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>加密行业热点早报 · {date_cn}</title>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700;900&family=Noto+Serif+SC:wght@600;700&display=swap" rel="stylesheet">
  <style>
    :root{{--black:#000;--neo:#191919;--white:#fff;--neon:#BCFF2F;--neon-dim:rgba(188,255,47,.10);--neon-mid:rgba(188,255,47,.20);--g1:#111;--g2:#1a1a1a;--ts:#999;--td:#666;--th:#444;--brd:rgba(255,255,255,.06);--bhv:rgba(188,255,47,.18);--red:#FF4D4D;--green:#2ECC71;}}
    *{{margin:0;padding:0;box-sizing:border-box;}}
    body{{background:var(--black);color:#fff;font-family:'Noto Sans SC',sans-serif;font-size:14px;line-height:1.7;padding:20px 14px;}}
    .container{{max-width:780px;margin:0 auto;}}
    .header{{text-align:center;padding:36px 0 28px;border-bottom:1px solid var(--brd);margin-bottom:24px;}}
    .date-badge{{display:inline-flex;align-items:center;gap:8px;background:var(--neo);border:1px solid var(--brd);border-radius:20px;padding:4px 14px;font-size:11px;color:var(--ts);margin-bottom:14px;letter-spacing:.05em;}}
    .dot{{width:6px;height:6px;border-radius:50%;background:var(--neon);animation:pulse 2s infinite;}}
    @keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.4}}}}
    h1{{font-family:'Noto Serif SC',serif;font-size:30px;font-weight:700;margin-bottom:6px;letter-spacing:-.02em;}}
    .accent{{color:var(--neon);}}
    .sub{{font-size:11px;color:var(--td);margin-bottom:14px;letter-spacing:.1em;}}
    .source-bar{{display:flex;flex-wrap:wrap;gap:6px;justify-content:center;}}
    .source-tag{{background:var(--g1);border:1px solid var(--brd);border-radius:4px;padding:3px 10px;font-size:10px;color:var(--ts);}}
    .market{{background:var(--neo);border:1px solid var(--brd);border-radius:12px;margin-bottom:20px;overflow:hidden;}}
    .market-header{{display:flex;justify-content:space-between;align-items:center;padding:12px 16px;border-bottom:1px solid var(--brd);}}
    .market-title{{font-size:12px;font-weight:700;color:var(--ts);}}
    .market-time{{font-size:10px;color:var(--td);}}
    .grid{{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--brd);}}
    .ci{{background:var(--g1);padding:14px 16px;}}
    .cl{{display:flex;align-items:center;gap:8px;margin-bottom:6px;}}
    .ico{{width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;flex-shrink:0;}}
    .btc{{background:#F7931A;color:#fff;}}.eth{{background:#627EEA;color:#fff;}}.sol{{background:#9945FF;color:#fff;}}.xrp{{background:#346AA9;color:#fff;}}
    .cn{{font-size:11px;color:var(--ts);}}
    .cp{{font-size:20px;font-weight:700;}}
    .coin-change{{font-size:11px;font-weight:600;margin-top:2px;}}
    .up{{color:var(--green);}}.down{{color:var(--red);}}
    .fng-bar{{display:grid;grid-template-columns:repeat(3,1fr);background:var(--g2);border-top:1px solid var(--brd);}}
    .fi{{padding:10px;text-align:center;border-right:1px solid var(--brd);}}
    .fi:last-child{{border-right:none;}}
    .fl{{font-size:9px;color:var(--td);margin-bottom:4px;}}
    .fv{{font-size:12px;font-weight:700;}}
    .section{{background:var(--neo);border:1px solid var(--brd);border-radius:12px;margin-bottom:14px;overflow:hidden;}}
    .section-header{{display:flex;align-items:center;gap:10px;padding:13px 18px;background:var(--g2);border-bottom:1px solid var(--brd);}}
    .section-icon{{font-size:17px;}}
    .section-title{{font-size:13px;font-weight:700;flex:1;letter-spacing:.02em;}}
    .section-count{{background:var(--neon-dim);border:1px solid var(--bhv);color:var(--neon);font-size:10px;font-weight:700;padding:2px 9px;border-radius:10px;}}
    .news-item{{padding:14px 18px;border-bottom:1px solid var(--brd);}}
    .news-item:last-child{{border-bottom:none;}}
    .priority{{display:inline-block;font-size:10px;font-weight:700;padding:2px 7px;border-radius:3px;margin-bottom:7px;letter-spacing:.04em;}}
    .priority.high{{background:var(--neon);color:#000;}}
    .priority.mid{{background:rgba(255,255,255,.07);color:var(--ts);border:1px solid rgba(255,255,255,.1);}}
    .priority.low{{background:rgba(255,255,255,.03);color:var(--th);border:1px solid rgba(255,255,255,.05);}}
    .news-title{{font-size:13px;font-weight:700;margin-bottom:5px;line-height:1.5;}}
    .news-detail{{font-size:12px;color:var(--ts);line-height:1.7;margin-bottom:8px;}}
    .news-source{{font-size:11px;color:var(--th);}}
    .news-source a{{color:var(--neon);text-decoration:none;opacity:.8;}}
    .news-source a:hover{{opacity:1;}}
    .divider{{height:1px;background:var(--brd);margin:24px 0;}}
    .footer{{text-align:center;padding:20px 0 12px;}}
    .disclaimer{{font-size:10px;color:var(--th);line-height:1.7;max-width:520px;margin:0 auto 10px;}}
    .compiled{{font-size:10px;color:var(--th);letter-spacing:.15em;}}
    .empty{{text-align:center;padding:32px;color:var(--td);font-size:13px;}}
  </style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="date-badge"><span class="dot"></span> {date_cn} · 周{weekday}</div>
    <h1>加密行业热点<span class="accent">早报</span></h1>
    <div class="sub">多源去重 · 分类评级 · 自动生成</div>
    <div class="source-bar">
      <span class="source-tag">Odaily星球日报</span>
      <span class="source-tag">CoinDesk</span>
      <span class="source-tag">CoinGecko</span>
      <span class="source-tag">Alternative.me</span>
    </div>
  </div>

  <div class="market">
    <div class="market-header">
      <span class="market-title">📊 实时行情</span>
      <span class="market-time">{now.strftime('%H:%M')} UTC+8</span>
    </div>
    <div class="grid">
      <div class="ci"><div class="cl"><div class="ico btc">₿</div><span class="cn">Bitcoin</span></div><div class="cp">{btc_p}</div>{btc_c}</div>
      <div class="ci"><div class="cl"><div class="ico eth">Ξ</div><span class="cn">Ethereum</span></div><div class="cp">{eth_p}</div>{eth_c}</div>
      <div class="ci"><div class="cl"><div class="ico sol">◎</div><span class="cn">Solana</span></div><div class="cp">{sol_p}</div>{sol_c}</div>
      <div class="ci"><div class="cl"><div class="ico xrp">✕</div><span class="cn">XRP</span></div><div class="cp">{xrp_p}</div>{xrp_c}</div>
    </div>
    <div class="fng-bar">
      <div class="fi"><div class="fl">恐慌贪婪指数</div><div class="fv" style="color:{fng_color}">{fng_v} · {fng_l}</div></div>
      <div class="fi"><div class="fl">BTC主导率</div><div class="fv">~57%</div></div>
      <div class="fi"><div class="fl">更新时间</div><div class="fv" style="font-size:11px">{now.strftime('%H:%M')}</div></div>
    </div>
  </div>

  {sections_html if sections_html else '<div class="empty">⚠️ 今日资讯抓取中，请稍后刷新</div>'}

  <div class="divider"></div>
  <div class="footer">
    <div class="disclaimer">⚠️ 本早报由程序自动抓取公开信息整合生成，不构成任何投资建议。加密资产具有高度波动性，投资须谨慎。</div>
    <div class="compiled">AUTO GENERATED · {date} · POWERED BY GITHUB ACTIONS</div>
  </div>
</div>
</body>
</html>"""

with open(f'{date}.html', 'w', encoding='utf-8') as f:
    f.write(html)
print(f'✅ Done: {date}.html — {len(news_dedup)} 条资讯，{len(sections)} 个分类')
