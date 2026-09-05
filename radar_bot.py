import os
import requests
import yfinance as yf
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

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

def get_fear_and_greed():
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=5).json()
        score = round(r["fear_and_greed"]["score"])
        rating = r["fear_and_greed"]["rating"].upper()
        return score, rating
    except:
        return 54, "NEUTRAL"

def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    requests.post(url, json=payload)

def run_radar():
    score, rating = get_fear_and_greed()
    
    # Fear & Greed 배지
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

    # QQQ & SOXX 데이터 조회
    etf_summary = []
    for etf in ["QQQ", "SOXX"]:
        try:
            h = yf.Ticker(etf).history(period="5d")
            p = h['Close'].iloc[-1]
            prev = h['Close'].iloc[-2]
            chg = ((p - prev) / prev) * 100
            sign = "+" if chg >= 0 else ""
            etf_summary.append(f"• <b>{etf}</b>: ${p:.2f} ({sign}{chg:.2f}%)")
        except:
            pass

    # 리포트 헤더 조립
    report = [
        "<b>📡 DAILY 미국 증시 투자 레이더</b>",
        f"<b>📅 일자:</b> {now_str}",
        f"<b>🚦 오늘의 핵심 신호:</b> {core_signal}",
        f"<b>🌡️ CNN 공포&탐욕:</b> {score}점 ({rating})\n└ {fg_status}",
        "",
        "<b>📊 주요 ETF 현황</b>",
        "\n".join(etf_summary),
        "",
        "<b>📅 주요 체크 이벤트</b>",
        "• 노동시장 지표 및 연준 금리 인하 경로 점검",
        "• AI 데이터센터 CAPEX 및 실주문 잔고 확인",
        "• 국채 10년물 금리 변동성에 따른 밸류에이션 추이",
        "─────────────────"
    ]

    # 내 보유 종목 21개 데이터 처리
    high_vol = []
    stock_cards = []

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

            # Forward PER
            fwd_pe = t.info.get("forwardPE")
            if fwd_pe and fwd_pe > 0:
                pe_str = f"{fwd_pe:.1f}x"
            else:
                pe_str = "N/A"

            sec_pe, _ = SECTOR_PER_MAP.get(ticker, ("22.0x", "섹터"))

            # 10% 이상 변동성 체크
            if abs(d_chg) >= 10.0:
                sign_txt = "급등" if d_chg > 0 else "급락"
                high_vol.append(f"🚨 <b>{ticker}</b>: {d_chg:+.1f}% {sign_txt} (현재가 ${cur_p:.2f})")

            # 대응 신호
            if ticker == "SOXL":
                sig = "⚪ 비중조절/WAIT"
            elif pe_str != "N/A" and float(pe_str.replace("x","")) < float(sec_pe.replace("x","")):
                sig = "🟢 적극매수/홀딩"
            elif d_chg < -3.0:
                sig = "🟡 눌림목 분할"
            else:
                sig = "🟡 홀딩/분할"

            card = (
                f"▪️ <b>{ticker}</b>: <b>${cur_p:.2f}</b> ({d_chg:+.1f}%)\n"
                f"   1주: {w_chg:+.1f}% | 1달: {m_chg:+.1f}%\n"
                f"   F-PER: <b>{pe_str}</b> (섹터 {sec_pe}) | 신호: {sig}"
            )
            stock_cards.append(card)

        except Exception:
            continue

    if high_vol:
        report.append("<b>🚨 전일 10%+ 고변동 종목</b>")
        report.extend(high_vol)
        report.append("─────────────────")

    report.append("<b>💼 내 보유 종목 21개 진단</b>")
    report.extend(stock_cards)
    report.append("─────────────────")
    report.append("💡 <i>PER 저평가 및 펀더멘털 견고 종목 우선 분할 대응</i>")

    send_message("\n".join(report))

if __name__ == "__main__":
    run_radar()
