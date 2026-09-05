import os
import requests
import yfinance as yf
from datetime import datetime, timedelta

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

MY_TICKERS = [
    "DELL", "SOXL", "GEV", "HWM", "INTC", "IONQ", "MRVL", "MU", "NVDA", 
    "PLTR", "RKLB", "SNDK", "TSM", "ABCL", "CRDO", "NBIS", "AMD", 
    "AMAT", "ALAB", "BE", "COHR"
]

def get_fear_and_greed():
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=5).json()
        score = round(r["fear_and_greed"]["score"])
        rating = r["fear_and_greed"]["rating"].upper()
        return score, rating
    except:
        return 50, "NEUTRAL"

def generate_report():
    score, rating = get_fear_and_greed()
    
    # 공포탐욕 지수 알림 배지
    fg_badge = "🟡"
    if score <= 25:
        fg_badge = "🚨 [매수 레이더 발동!]"
    elif score <= 40:
        fg_badge = "👀 [관심 알림]"
    elif score >= 65:
        fg_badge = "⚠️ [탐욕 경계]"

    now_str = datetime.now().strftime("%Y-%m-%d")
    
    lines = [
        "<b>📡 DAILY 미국 증시 투자 레이더</b>",
        f"<b>🚦 시장 센티먼트:</b> {score}점 ({rating}) {fg_badge}",
        f"<b>📅 기준일자:</b> {now_str}",
        "─────────────────"
    ]
    
    high_vol = []
    stock_rows = []

    for ticker in MY_TICKERS:
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="1mo")
            if len(hist) < 2:
                continue
            
            cur_p = hist['Close'].iloc[-1]
            prev_p = hist['Close'].iloc[-2]
            w1_p = hist['Close'].iloc[-5] if len(hist) >= 5 else hist['Close'].iloc[0]
            m1_p = hist['Close'].iloc[0]
            
            d_chg = ((cur_p - prev_p) / prev_p) * 100
            w_chg = ((cur_p - w1_p) / w1_p) * 100
            m_chg = ((cur_p - m1_p) / m1_p) * 100
            
            # Forward PER 추출
            fwd_pe = t.info.get("forwardPE")
            pe_str = f"{fwd_pe:.1f}x" if fwd_pe else "N/A"

            # 10% 이상 고변동 알림 체크
            if abs(d_chg) >= 10.0:
                high_vol.append(f"• <b>{ticker}</b>: {d_chg:+.1f}% (현재가 ${cur_p:.2f})")

            sign = "🔺" if d_chg > 0 else "🔹"
            stock_rows.append(
                f"<b>{ticker}</b>: ${cur_p:.2f} ({sign}{d_chg:+.1f}% | 1주 {w_chg:+.1f}% | 1달 {m_chg:+.1f}%) [F-PE {pe_str}]"
            )
        except Exception as e:
            continue

    if high_vol:
        lines.append("<b>🚨 전일 10%+ 고변동 종목</b>")
        lines.extend(high_vol)
        lines.append("─────────────────")

    lines.append("<b>💼 보유 종목 가격 & PER 점검</b>")
    lines.extend(stock_rows)
    
    return "\n".join(lines)

def send_telegram():
    msg = generate_report()
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    requests.post(url, json=payload)

if __name__ == "__main__":
    send_telegram()
