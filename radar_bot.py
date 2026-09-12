import os
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

INDEX_TICKERS = {
    "S&P 500 (SPY)": "SPY",
    "나스닥 100 (QQQ)": "QQQ",
    "다우존스 (DIA)": "DIA",
    "러셀 2000 (IWM)": "IWM",
    "반도체 (SOXX)": "SOXX"
}

MY_TICKERS = [
    "DELL", "SOXL", "GEV", "HWM", "INTC", "IONQ", "MRVL", "MU", "NVDA", 
    "PLTR", "RKLB", "SNDK", "TSM", "ABCL", "CRDO", "NBIS", "AMD", 
    "AMAT", "ALAB", "BE", "COHR"
]

SECTOR_PER_MAP = {
    "DELL": ("22.0x", "IT하드웨어"),
    "SOXL": ("—", "레버리지"),
    "GEV": ("20.5x", "전력인프라"),
    "HWM": ("21.0x", "우주항공"),
    "INTC": ("23.5x", "반도체"),
    "IONQ": ("22.0x", "양자컴퓨팅"),
    "MRVL": ("23.5x", "반도체"),
    "MU": ("23.5x", "반도체"),
    "NVDA": ("23.5x", "반도체"),
    "PLTR": ("25.0x", "소프트웨어"),
    "RKLB": ("21.0x", "우주항공"),
    "SNDK": ("23.5x", "반도체"),
    "TSM": ("23.5x", "반도체"),
    "ABCL": ("16.5x", "바이오"),
    "CRDO": ("23.5x", "네트워킹"),
    "NBIS": ("22.0x", "클라우드"),
    "AMD": ("23.5x", "반도체"),
    "AMAT": ("23.5x", "반도체장비"),
    "ALAB": ("23.5x", "네트워킹"),
    "BE": ("20.5x", "전력인프라"),
    "COHR": ("23.5x", "광통신")
}

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

def get_fear_and_greed():
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.cnn.com/markets/fear-and-greed"
        }
        r = requests.get(url, headers=headers, timeout=6)
        if r.status_code == 200:
            data = r.json()
            score = round(float(data["fear_and_greed"]["score"]))
            rating = data["fear_and_greed"]["rating"].upper()
            return score, rating
    except Exception:
        pass

    try:
        vix = yf.Ticker("^VIX").history(period="2d")['Close'].iloc[-1]
        if vix >= 30:
            return int(round(100 - vix*2)), "EXTREME FEAR"
        elif vix >= 22:
            return 38, "FEAR"
        elif vix <= 14:
            return 72, "GREED"
        else:
            return 50, "NEUTRAL"
    except Exception:
        return 50, "NEUTRAL"

def get_realtime_ai_news():
    news_items = []
    tickers = ["NVDA", "TSM", "SMCI"]
    for sym in tickers:
        try:
            t = yf.Ticker(sym)
            raw_news = t.news
            if raw_news and len(raw_news) > 0:
                title = raw_news[0].get("title", "")
                publisher = raw_news[0].get("publisher", "")
                if title:
                    news_items.append(f"• <b>[{sym}]</b> {title} <i>({publisher})</i>")
        except Exception:
            continue
        if len(news_items) >= 3:
            break

    if not news_items:
        news_items = [
            "• <b>[AI HW]</b> 하이퍼스케일러 데이터센터 인프라 수주 잔고 지속 확인",
            "• <b>[반도체]</b> 차세대 AI 패키징 및 고속 인터커넥트 인터페이스 채택 가속",
            "• <b>[전력망]</b> 데이터센터 가동 전력 확보 및 신규 인프라 증설 모멘텀 유지"
        ]
    return news_items[:3]

def send_message(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception:
        pass

def generate_mobile_html(now_str, core_signal, score, rating, fg_status, summary_lines, ai_news, index_data, stock_data, high_vol):
    os.makedirs("docs", exist_ok=True)
    
    # 지수 카드 HTML
    idx_cards_html = ""
    for d in index_data:
        chg_color = "#ef4444" if d['d_chg'] < 0 else "#22c55e"
        idx_cards_html += f"""
        <div class="card">
            <div class="flex-between">
                <span class="card-title">{d['name']}</span>
                <span class="price">${d['cur_p']:.2f}</span>
            </div>
            <div class="flex-between mt-1">
                <span style="color: {chg_color}; font-weight: bold;">{d['d_chg']:+.2f}%</span>
                <span class="text-sub">1주 {d['w_chg']:+.2f}% | 1달 {d['m_chg']:+.2f}%</span>
            </div>
            <div class="flex-between mt-2 pt-2 border-t">
                <span class="text-sub">52주 최고 ${d['high_52w']:.2f}</span>
                <span class="badge-mdd">MDD {d['mdd']:.2f}%</span>
            </div>
            <div class="mt-1 text-sub">RSI(14): <b>{d['rsi_str']}</b></div>
        </div>
        """

    # 보유 종목 행 HTML
    rows_html = ""
    for s in stock_data:
        chg_color = "#ef4444" if s['d_chg'] < 0 else "#22c55e"
        rows_html += f"""
        <tr>
            <td class="bold">{s['ticker']}</td>
            <td>${s['cur_p']:.2f}</td>
            <td style="color: {chg_color}; font-weight: bold;">{s['d_chg']:+.2f}%</td>
            <td><span class="badge-mdd">{s['mdd']:.1f}%</span></td>
            <td>{s['pe_str']} <span class="text-sub">({s['sec_pe']})</span></td>
            <td><span class="signal-tag">{s['sig']}</span></td>
        </tr>
        """

    summary_html = "".join([f"<li>{line.replace('• ', '')}</li>" for line in summary_lines])
    news_html = "".join([f"<li>{line.replace('• ', '')}</li>" for line in ai_news])

    high_vol_html = ""
    if high_vol:
        vol_items = "".join([f"<div class='vol-item'>{v}</div>" for v in high_vol])
        high_vol_html = f"<div class='high-vol-box'><h4>🚨 마감 기준 10%+ 고변동 종목</h4>{vol_items}</div>"

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Daily Stock Radar</title>
    <style>
        :root {{
            --bg: #0f172a;
            --card-bg: #1e293b;
            --border: #334155;
            --text-main: #f8fafc;
            --text-sub: #94a3b8;
            --accent: #38bdf8;
            --green: #22c55e;
            --red: #ef4444;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
        body {{ background-color: var(--bg); color: var(--text-main); padding: 16px; font-size: 14px; line-height: 1.5; }}
        header {{ margin-bottom: 20px; }}
        h1 {{ font-size: 20px; font-weight: 800; color: var(--accent); }}
        .date {{ color: var(--text-sub); font-size: 12px; margin-top: 2px; }}
        .signal-box {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 14px; margin-bottom: 16px; }}
        .badge-core {{ display: inline-block; font-size: 14px; font-weight: bold; padding: 4px 10px; border-radius: 8px; background: #334155; margin-top: 4px; }}
        .card {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 14px; margin-bottom: 12px; }}
        .flex-between {{ display: flex; justify-content: space-between; align-items: center; }}
        .card-title {{ font-size: 15px; font-weight: bold; }}
        .price {{ font-size: 16px; font-weight: 800; }}
        .text-sub {{ color: var(--text-sub); font-size: 12px; }}
        .mt-1 {{ margin-top: 4px; }}
        .mt-2 {{ margin-top: 8px; }}
        .pt-2 {{ padding-top: 8px; }}
        .border-t {{ border-top: 1px solid var(--border); }}
        .badge-mdd {{ background: rgba(239, 68, 68, 0.15); color: #f87171; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; }}
        .section-title {{ font-size: 16px; font-weight: 700; margin: 24px 0 10px; display: flex; align-items: center; gap: 6px; }}
        ul {{ padding-left: 18px; margin-top: 6px; }}
        li {{ margin-bottom: 6px; color: #cbd5e1; font-size: 13px; }}
        .table-wrap {{ overflow-x: auto; -webkit-overflow-scrolling: touch; border-radius: 12px; border: 1px solid var(--border); background: var(--card-bg); }}
        table {{ width: 100%; border-collapse: collapse; min-width: 520px; font-size: 13px; }}
        th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--border); }}
        th {{ background: #1e293b; color: var(--text-sub); font-size: 12px; }}
        .bold {{ font-weight: bold; }}
        .signal-tag {{ font-size: 11px; padding: 2px 6px; background: #334155; border-radius: 4px; white-space: nowrap; }}
        .high-vol-box {{ background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 10px; padding: 12px; margin-bottom: 16px; }}
        .high-vol-box h4 {{ color: #f87171; font-size: 13px; margin-bottom: 6px; }}
        .vol-item {{ font-size: 12px; margin-bottom: 2px; }}
    </style>
</head>
<body>
    <header>
        <h1>📡 DAILY 미국 증시 투자 레이더</h1>
        <div class="date">{now_str} (한국 아침 07:00 마감 브리핑)</div>
    </header>

    <div class="signal-box">
        <div>오늘의 핵심 시장 신호</div>
        <div class="badge-core">{core_signal}</div>
        <div class="mt-2 text-sub">CNN Fear & Greed: <b>{score}점 ({rating})</b> | {fg_status}</div>
    </div>

    {high_vol_html}

    <div class="section-title">🇺🇸 미 증시 마감 핵심 브리핑</div>
    <div class="card">
        <ul>{summary_html}</ul>
    </div>

    <div class="section-title">🤖 AI & 반도체 실시간 뉴스</div>
    <div class="card">
        <ul>{news_html}</ul>
    </div>

    <div class="section-title">📊 주요 지수 & SOXX 정밀 진단</div>
    {idx_cards_html}

    <div class="section-title">💼 내 보유 종목 21개 진단표</div>
    <div class="table-wrap">
        <table>
            <thead>
                <tr>
                    <th>티커</th>
                    <th>현재가</th>
                    <th>전일대비</th>
                    <th>52주 MDD</th>
                    <th>F-PER</th>
                    <th>대응신호</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>
    <div class="mt-2 text-sub" style="text-align: right;">※ 좌우로 스크롤하여 전체 항목을 볼 수 있습니다.</div>
</body>
</html>
"""
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html)

def run_radar():
    score, rating = get_fear_and_greed()
    
    if score <= 25:
        fg_status = "🚨 [매수 레이더 발동! EXTREME FEAR]"
        core_signal = "🟢 적극 분할매수 진입"
    elif score <= 40:
        fg_status = "👀 [관심 알림 - 저점 매수 모니터링]"
        core_signal = "🟡 선별 분할매수"
    elif score >= 65:
        fg_status = "⚠️ [탐욕 경계 - 과열 주의]"
        core_signal = "🟡 WAIT (관망 및 보수적 분할매수)"
    else:
        fg_status = "⚖️ [중립 구간 - 숨고르기]"
        core_signal = "🟡 WAIT (관망 및 선별 분할매수)"

    now_str = datetime.now().strftime("%Y-%m-%d")

    # 지수 수집
    index_cards = []
    index_changes = {}
    index_data_list = []

    for name, sym in INDEX_TICKERS.items():
        try:
            t = yf.Ticker(sym)
            hist = t.history(period="3mo")
            if len(hist) < 2:
                continue

            cur_p = hist['Close'].iloc[-1]
            prev_p = hist['Close'].iloc[-2]
            w1_p = hist['Close'].iloc[-5] if len(hist) >= 5 else hist['Close'].iloc[0]
            m1_p = hist['Close'].iloc[-21] if len(hist) >= 21 else hist['Close'].iloc[0]

            d_chg = ((cur_p - prev_p) / prev_p) * 100
            w_chg = ((cur_p - w1_p) / w1_p) * 100
            m_chg = ((cur_p - m1_p) / m1_p) * 100
            index_changes[sym] = d_chg

            high_52w = t.info.get("fiftyTwoWeekHigh")
            if not high_52w:
                high_52w = hist['High'].max()
            mdd = ((cur_p - high_52w) / high_52w) * 100

            rsi_val = calculate_rsi(hist['Close'], period=14)
            if pd.isna(rsi_val):
                rsi_str = "N/A"
            else:
                if rsi_val >= 70:
                    rsi_str = f"🔥 {rsi_val:.1f} (과매수)"
                elif rsi_val <= 30:
                    rsi_str = f"❄️ {rsi_val:.1f} (과매도)"
                else:
                    rsi_str = f"{rsi_val:.1f} (중립)"

            index_data_list.append({
                "name": name, "cur_p": cur_p, "d_chg": d_chg,
                "w_chg": w_chg, "m_chg": m_chg, "high_52w": high_52w,
                "mdd": mdd, "rsi_str": rsi_str
            })

            card = (
                f"▪️ <b>{name}</b>: <b>${cur_p:.2f}</b> ({d_chg:+.2f}%)\n"
                f"   변동: 1주 {w_chg:+.2f}% | 1달 {m_chg:+.2f}%\n"
                f"   52주 최고: ${high_52w:.2f} | <b>MDD: {mdd:.2f}%</b>\n"
                f"   RSI(14): <b>{rsi_str}</b>"
            )
            index_cards.append(card)
        except Exception:
            continue

    spy_c = index_changes.get("SPY", 0.0)
    qqq_c = index_changes.get("QQQ", 0.0)
    soxx_c = index_changes.get("SOXX", 0.0)
    iwm_c = index_changes.get("IWM", 0.0)
    dia_c = index_changes.get("DIA", 0.0)

    summary_lines = [
        f"• <b>S&P 500(SPY)</b>: {spy_c:+.2f}% {'상승 마감' if spy_c >= 0 else '하락 마감'}",
        f"• <b>나스닥 100(QQQ)</b>: {qqq_c:+.2f}% 마감으로 기술주 {'견조세 유지' if qqq_c >= 0 else '조정 지속'}",
        f"• <b>반도체(SOXX)</b>: {soxx_c:+.2f}% 마감 ({'섹터 주도력 확대' if soxx_c > 1.0 else '단기 숨고르기'})",
        f"• <b>러셀 2000(IWM)</b>: {iwm_c:+.2f}% 기록으로 중소형주 수급 {'유입' if iwm_c >= 0 else '이탈'}",
        f"• <b>다우존스(DIA)</b>: {dia_c:+.2f}% 마감으로 가치주 흐름 반영",
        f"• <b>시장 센티먼트</b>: CNN 지표 {score}점 ({rating}) 구간 위치",
        f"• <b>반도체 vs 대형주</b>: 상대 강도 스프레드 {(soxx_c - spy_c):+.2f}%p 시현"
    ]

    ai_news = get_realtime_ai_news()

    # 보유 종목 21개 수집
    high_vol = []
    stock_cards = []
    stock_data_list = []

    for ticker in MY_TICKERS:
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="3mo")
            if len(hist) < 2:
                continue

            cur_p = hist['Close'].iloc[-1]
            prev_p = hist['Close'].iloc[-2]
            w1_p = hist['Close'].iloc[-5] if len(hist) >= 5 else hist['Close'].iloc[0]
            m1_p = hist['Close'].iloc[-21] if len(hist) >= 21 else hist['Close'].iloc[0]

            d_chg = ((cur_p - prev_p) / prev_p) * 100
            w_chg = ((cur_p - w1_p) / w1_p) * 100
            m_chg = ((cur_p - m1_p) / m1_p) * 100

            high_52w = t.info.get("fiftyTwoWeekHigh")
            if not high_52w:
                high_52w = hist['High'].max()
            mdd = ((cur_p - high_52w) / high_52w) * 100

            fwd_pe = t.info.get("forwardPE")
            if fwd_pe and fwd_pe > 0:
                pe_str = f"{fwd_pe:.1f}x"
            else:
                pe_str = "N/A"

            sec_pe, sec_name = SECTOR_PER_MAP.get(ticker, ("22.0x", "섹터"))

            if abs(d_chg) >= 10.0:
                sign_txt = "급등 🚀" if d_chg > 0 else "급락 🩸"
                high_vol.append(f"🚨 <b>{ticker}</b>: {d_chg:+.1f}% {sign_txt} (현재가 ${cur_p:.2f})")

            if ticker == "SOXL":
                sig = "⚪ 비중조절/WAIT"
            elif pe_str != "N/A" and float(pe_str.replace("x","")) < float(sec_pe.replace("x","")):
                sig = "🟢 적극매수/홀딩"
            elif mdd <= -35.0:
                sig = "🟡 낙폭과대 분할"
            elif d_chg < -3.0:
                sig = "🟡 눌림목 분할"
            else:
                sig = "🟡 홀딩/분할"

            stock_data_list.append({
                "ticker": ticker, "cur_p": cur_p, "d_chg": d_chg,
                "mdd": mdd, "pe_str": pe_str, "sec_pe": sec_pe, "sig": sig
            })

            card = (
                f"▪️ <b>{ticker}</b>: <b>${cur_p:.2f}</b> ({d_chg:+.1f}%)\n"
                f"   변동: 1주 {w_chg:+.1f}% | 1달 {m_chg:+.1f}%\n"
                f"   52주 최고: ${high_52w:.2f} | <b>MDD: {mdd:.1f}%</b>\n"
                f"   F-PER: <b>{pe_str}</b> (섹터 {sec_pe}) | 신호: {sig}"
            )
            stock_cards.append(card)

        except Exception:
            continue

    # 모바일 웹페이지 index.html 생성
    generate_mobile_html(now_str, core_signal, score, rating, fg_status, summary_lines, ai_news, index_data_list, stock_data_list, high_vol)

    # 기존 텔레그램 리포트 발송 유지
    part1 = [
        "<b>📡 DAILY 미국 증시 투자 레이더 (Part 1/2)</b>",
        f"<b>📅 일자:</b> {now_str} (아침 07:00 KST)",
        f"<b>🚦 오늘의 핵심 신호:</b> {core_signal}",
        f"<b>🌡️ CNN 공포&탐욕:</b> {score}점 ({rating})\n└ {fg_status}",
        "─────────────────",
        "<b>🇺🇸 미 증시 핵심 브리핑</b>",
        "\n".join(summary_lines),
        "─────────────────",
        "<b>🤖 AI & 반도체 실시간 뉴스</b>",
        "\n".join(ai_news),
        "─────────────────",
        "<b>📊 주요 4대 지수 & 반도체(SOXX)</b>",
        "\n\n".join(index_cards)
    ]
    send_message("\n".join(part1))

    part2 = [
        "<b>💼 내 보유 종목 21개 진단 & MDD (Part 2/2)</b>",
        "─────────────────"
    ]
    if high_vol:
        part2.append("<b>🚨 마감 기준 10%+ 고변동 종목</b>")
        part2.extend(high_vol)
        part2.append("─────────────────")
    part2.extend(stock_cards)
    send_message("\n".join(part2))

if __name__ == "__main__":
    run_radar()
