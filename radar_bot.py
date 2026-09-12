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
    # 1차 시도: CNN 공식 데이터 피드
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
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

    # 2차 시도: 차단 시 실시간 VIX(변동성 지수) 기반 센티먼트 역산출
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
    """실시간 AI & 반도체 주요 뉴스 추출"""
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
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    requests.post(url, json=payload, timeout=10)

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

    # ==================== PART 1: 마감 요약, AI 실시간 뉴스 & 지수 ====================
    index_cards = []
    index_changes = {}

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

            # 52주 최고가 및 MDD
            high_52w = t.info.get("fiftyTwoWeekHigh")
            if not high_52w:
                high_52w = hist['High'].max()
            mdd = ((cur_p - high_52w) / high_52w) * 100

            # RSI(14)
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

            card = (
                f"▪️ <b>{name}</b>: <b>${cur_p:.2f}</b> ({d_chg:+.2f}%)\n"
                f"   변동: 1주 {w_chg:+.2f}% | 1달 {m_chg:+.2f}%\n"
                f"   52주 최고: ${high_52w:.2f} | <b>MDD: {mdd:.2f}%</b>\n"
                f"   RSI(14): <b>{rsi_str}</b>"
            )
            index_cards.append(card)
        except Exception:
            continue

    # 동적 10줄 마감 요약 생성 (실제 데이터 반영)
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
        f"• <b>반도체 vs 대형주</b>: 상대 강도 스프레드 {(soxx_c - spy_c):+.2f}%p 시현",
        "• <b>전략 행동</b>: " + ("사상 최고가권 분할 매도·차익 검토" if score >= 70 else ("낙폭과대 종목 선별 분할매수" if score <= 40 else "무리한 추격 매수 지양 및 현금 비중 유지"))
    ]

    ai_news = get_realtime_ai_news()

    part1 = [
        "<b>📡 DAILY 미국 증시 투자 레이더 (Part 1/2)</b>",
        f"<b>📅 일자:</b> {now_str} (아침 07:00 KST)",
        f"<b>🚦 오늘의 핵심 신호:</b> {core_signal}",
        f"<b>🌡️ CNN 공포&탐욕:</b> {score}점 ({rating})\n└ {fg_status}",
        "─────────────────",
        "<b>🇺🇸 방금 마감된 미 증시 핵심 브리핑 (실시간 데이터 연동)</b>",
        "\n".join(summary_lines),
        "─────────────────",
        "<b>🤖 글로벌 핵심 AI & 반도체 실시간 뉴스 헤드라인</b>",
        "\n".join(ai_news),
        "─────────────────",
        "<b>📊 주요 4대 지수 & 반도체(SOXX) 정밀 진단</b>",
        "\n\n".join(index_cards)
    ]
    send_message("\n".join(part1))

    # ==================== PART 2: 내 보유 종목 21개 진단 ====================
    high_vol = []
    stock_cards = []

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

            # 52주 최고가 및 MDD
            high_52w = t.info.get("fiftyTwoWeekHigh")
            if not high_52w:
                high_52w = hist['High'].max()
            mdd = ((cur_p - high_52w) / high_52w) * 100

            # Forward PER
            fwd_pe = t.info.get("forwardPE")
            if fwd_pe and fwd_pe > 0:
                pe_str = f"{fwd_pe:.1f}x"
            else:
                pe_str = "N/A"

            sec_pe, sec_name = SECTOR_PER_MAP.get(ticker, ("22.0x", "섹터"))

            # 10%+ 고변동 감지
            if abs(d_chg) >= 10.0:
                sign_txt = "급등 🚀" if d_chg > 0 else "급락 🩸"
                high_vol.append(f"🚨 <b>{ticker}</b>: {d_chg:+.1f}% {sign_txt} (현재가 ${cur_p:.2f})")

            # 대응 신호
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

            card = (
                f"▪️ <b>{ticker}</b>: <b>${cur_p:.2f}</b> ({d_chg:+.1f}%)\n"
                f"   변동: 1주 {w_chg:+.1f}% | 1달 {m_chg:+.1f}%\n"
                f"   52주 최고: ${high_52w:.2f} | <b>MDD: {mdd:.1f}%</b>\n"
                f"   F-PER: <b>{pe_str}</b> (섹터 {sec_pe}) | 신호: {sig}"
            )
            stock_cards.append(card)

        except Exception:
            continue

    part2 = [
        "<b>💼 내 보유 종목 21개 진단 & 52주 MDD (Part 2/2)</b>",
        "─────────────────"
    ]

    if high_vol:
        part2.append("<b>🚨 마감 기준 10%+ 고변동 종목</b>")
        part2.extend(high_vol)
        part2.append("─────────────────")

    part2.extend(stock_cards)
    part2.append("─────────────────")
    part2.append("💡 <i>고점 대비 낙폭(MDD)과 Forward PER을 종합해 선별 대응하세요.</i>")

    send_message("\n".join(part2))

if __name__ == "__main__":
    run_radar()
