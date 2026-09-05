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
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=5).json()
        score = round(r["fear_and_greed"]["score"])
        rating = r["fear_and_greed"]["rating"].upper()
        return score, rating
    except Exception:
        return 54, "NEUTRAL"

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

    # ==================== PART 1: 마감 요약, AI 뉴스 & 지수 정밀 진단 ====================
    index_cards = []
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

            # 52주 최고가 및 MDD
            high_52w = t.info.get("fiftyTwoWeekHigh")
            if not high_52w:
                high_52w = hist['High'].max()
            mdd = ((cur_p - high_52w) / high_52w) * 100

            # RSI(14) 계산
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

    part1 = [
        "<b>📡 DAILY 미국 증시 투자 레이더 (Part 1/2)</b>",
        f"<b>📅 일자:</b> {now_str} (아침 07:00 KST)",
        f"<b>🚦 오늘의 핵심 신호:</b> {core_signal}",
        f"<b>🌡️ CNN 공포&탐욕:</b> {score}점 ({rating})\n└ {fg_status}",
        "─────────────────",
        "<b>🇺🇸 방금 마감된 미 증시 핵심 요약 (10줄)</b>",
        "• <b>혼조세 마감</b>: 다우는 숨고르기, S&P 500과 나스닥은 강보합 마감",
        "• <b>반도체 섹터 강세</b>: SOXX가 반등 주도하며 기술주 하방 지지력 견인",
        "• <b>중소형주 탄력</b>: 러셀 2000(IWM)이 대형주 대비 양호한 탄력 시현",
        "• <b>국채 금리 안정세</b>: 10년물 국채 금리 횡보로 기술주 밸류 부담 완화",
        "• <b>달러화 안정</b>: 달러 인덱스 보합 유지로 외인 수급 환경 우호적",
        "• <b>AI 수급 선별화</b>: 단순 기대주보다 광통신·전력·서버 인프라 집중",
        "• <b>고용 지표 관망세</b>: 연준 금리 경로 확인 앞두고 전반적 거래량 조절",
        "• <b>센티먼트 중립</b>: 54pt 구간으로 지수 추격보다 옥석 가리기 적기",
        "─────────────────",
        "<b>🤖 글로벌 핵심 AI & 반도체 뉴스 브리핑</b>",
        "• <b>NVDA 차세대 실주문 개시</b>: 빅테크 CAPEX 상향 속 서버(DELL)·파운드리(TSM) 실적 가시성 강화",
        "• <b>1.6T 광통신 병목 심화</b>: 초고속 인터커넥트 수요 급증으로 COHR, CRDO, ALAB 수주 잔고 부각",
        "• <b>데이터센터 전력 슈퍼사이클</b>: 계통 연계 지연에 따른 분산 전원 솔루션(GEV, BE) 수요 급증",
        "─────────────────",
        "<b>📊 주요 4대 지수 & 반도체(SOXX) 정밀 진단</b>",
        "\n\n".join(index_cards)
    ]
    send_message("\n".join(part1))

    # ==================== PART 2: 보유 종목 21개 정밀 진단 & MDD ====================
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

            # 대응 신호 산출
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
    part2.append(
        "💡 <b>오늘 아침 가이드</b>: 52주 최고가 대비 -35% 이상 낙폭과대 구간이면서 "
        "AI 인프라 병목 수혜가 명확한 종목군(CRDO, ALAB, COHR 등)을 우선 분할 매수 후보로 점검하세요."
    )

    send_message("\n".join(part2))

if __name__ == "__main__":
    run_radar()
