import os
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import pytz
import xml.etree.ElementTree as ET
import urllib.parse
import re

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

INDEX_TICKERS = {
    "S&P 500 (SPY)": "SPY",
    "나스닥 100 (QQQ)": "QQQ",
    "다우존스 (DIA)": "DIA",
    "러셀 2000 (IWM)": "IWM",
    "반도체 (SOXX)": "SOXX",
    "VIX 변동성": "^VIX",
    "코스피 (KOSPI)": "^KS11",
    "코스닥 (KOSDAQ)": "^KQ11"
}

MACRO_TICKERS = {
    "미국채 10년물 금리": "^TNX",
    "달러 인덱스 (DXY)": "DX-Y.NYB",
    "WTI 원유 (배럴)": "CL=F",
    "원/달러 환율 (KRW)": "USDKRW=X",
    "원/엔 환율 (100엔)": "JPYKRW=X"
}

# 💡 가상자산 8종 전면 업비트(Upbit) 원화 마켓 코드 매핑
UPBIT_CRYPTO_MAP = {
    "비트코인 (BTC)": "KRW-BTC",
    "이더리움 (ETH)": "KRW-ETH",
    "리플 (XRP)": "KRW-XRP",
    "솔라나 (SOL)": "KRW-SOL",
    "에테나 (ENA)": "KRW-ENA",
    "앱토스 (APT)": "KRW-APT",
    "시바이누 (SHIB)": "KRW-SHIB",
    "셀로 (CELO)": "KRW-CELO"
}

SECTOR_ETF_TICKERS = {
    "XLK": "Technology (기술)",
    "XLV": "Healthcare (헬스케어)",
    "XLP": "Consumer Staples (필수소비재)",
    "XLU": "Utilities (유틸리티)",
    "XLY": "Consumer Discr. (임의소비재)",
    "XLC": "Communication (통신서비스)",
    "XLB": "Basic Materials (소재/원자재)",
    "XLF": "Financial Services (금융)",
    "XLI": "Industrials (산업재)",
    "XLE": "Energy (에너지)",
    "XLRE": "Real Estate (부동산)"
}

MY_TICKERS = [
    "DELL", "SOXL", "GEV", "HWM", "INTC", "IONQ", "MRVL", "MU", "NVDA", 
    "PLTR", "RKLB", "SNDK", "TSM", "ABCL", "CRDO", "NBIS", "AMD", 
    "AMAT", "ALAB", "BE", "COHR", "SCHD", "TQQQ", "QLD",
    "005930.KS", "000660.KS"
]

# 💡 관심종목에 MSTR 추가 (총 19개)
WATCH_TICKERS = [
    "PWR", "LITE", "FCX", "CVX", "CRCL", "CAT", "OXY", 
    "AAPL", "AMZN", "META", "HOOD", "PANW", "ORCL",
    "CRWD", "FTNT", "ZS", "CYBR", "LLY", "MSTR"
]

STOCK_INFO_MAP = {
    # 내 포트폴리오 (26개)
    "DELL": ("22.0x", "IT하드웨어", "Dell Technologies"),
    "SOXL": ("—", "레버리지", "Direxion Daily Semiconductor 3x"),
    "GEV": ("20.5x", "전력인프라", "GE Vernova Inc."),
    "HWM": ("21.0x", "우주항공", "Howmet Aerospace"),
    "INTC": ("23.5x", "반도체", "Intel Corporation"),
    "IONQ": ("22.0x", "양자컴퓨팅", "IonQ Inc."),
    "MRVL": ("23.5x", "반도체", "Marvell Technology"),
    "MU": ("23.5x", "반도체", "Micron Technology"),
    "NVDA": ("23.5x", "반도체", "NVIDIA Corporation"),
    "PLTR": ("25.0x", "소프트웨어", "Palantir Technologies"),
    "RKLB": ("21.0x", "우주항공", "Rocket Lab USA"),
    "SNDK": ("23.5x", "반도체", "SanDisk / Flash Storage"),
    "TSM": ("23.5x", "반도체", "Taiwan Semiconductor (TSMC)"),
    "ABCL": ("16.5x", "바이오", "AbCellera Biologics"),
    "CRDO": ("23.5x", "네트워킹", "Credo Technology Group"),
    "NBIS": ("22.0x", "클라우드", "Nebius Group N.V."),
    "AMD": ("23.5x", "반도체", "Advanced Micro Devices"),
    "AMAT": ("23.5x", "반도체장비", "Applied Materials"),
    "ALAB": ("23.5x", "네트워킹", "Astera Labs Inc."),
    "BE": ("20.5x", "전력인프라", "Bloom Energy Corporation"),
    "COHR": ("23.5x", "광통신", "Coherent Corp."),
    "SCHD": ("16.0x", "배당ETF", "Schwab US Dividend Equity ETF"),
    "TQQQ": ("—", "레버리지", "ProShares UltraPro QQQ 3x"),
    "QLD": ("—", "레버리지", "ProShares Ultra QQQ 2x"),
    "005930.KS": ("12.5x", "국내반도체", "삼성전자 (Samsung Electronics)"),
    "000660.KS": ("9.8x", "국내반도체", "SK하이닉스 (SK Hynix)"),
    
    # 관심종목 (19개)
    "PWR": ("25.0x", "인프라엔지니어링", "Quanta Services"),
    "LITE": ("22.0x", "광학/네트워크", "Lumentum Holdings"),
    "FCX": ("15.0x", "구리/원자재", "Freeport-McMoRan"),
    "CVX": ("12.0x", "에너지/오일", "Chevron Corporation"),
    "CRCL": ("20.0x", "핀테크/디지털", "Circle Internet Group"),
    "CAT": ("16.0x", "중장비/산업", "Caterpillar Inc."),
    "OXY": ("12.0x", "에너지/버핏", "Occidental Petroleum"),
    "AAPL": ("28.0x", "빅테크/디바이스", "Apple Inc."),
    "AMZN": ("32.0x", "이커머스/클라우드", "Amazon.com Inc."),
    "META": ("25.0x", "소셜/AI", "Meta Platforms"),
    "HOOD": ("24.0x", "핀테크/브로커리지", "Robinhood Markets"),
    "PANW": ("45.0x", "사이버보안", "Palo Alto Networks"),
    "ORCL": ("25.0x", "클라우드/엔터프라이즈", "Oracle Corporation"),
    "CRWD": ("55.0x", "엔드포인트보안", "CrowdStrike Holdings"),
    "FTNT": ("35.0x", "네트워크보안", "Fortinet Inc."),
    "ZS": ("45.0x", "클라우드보안", "Zscaler Inc."),
    "CYBR": ("40.0x", "신원인증보안", "CyberArk Software"),
    "LLY": ("35.0x", "비만치료제/바이오", "Eli Lilly and Company"),
    "MSTR": ("—", "비트코인재무/SW", "MicroStrategy Incorporated")
}

def translate_to_ko_robust(text):
    try:
        encoded = urllib.parse.quote(text)
        url = f"https://api.mymemory.translated.net/get?q={encoded}&langpair=en|ko"
        r = requests.get(url, timeout=4).json()
        translated = r.get("responseData", {}).get("translatedText", "")
        if translated and translated.strip() != text.strip() and "MYMEMORY WARNING" not in translated:
            return translated
    except Exception:
        pass

    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=ko&dt=t&q={urllib.parse.quote(text)}"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=4).json()
        res = "".join([part[0] for part in r[0] if part[0]])
        if res:
            return res
    except Exception:
        pass

    return text

def get_us_market_popular_news():
    """💡 when:1d 파라미터 적용 및 키워드 정제로 오늘 실시간 뉴스만 정확히 수집"""
    news_items = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    # 1. 국내 주요 언론의 미국 증시 마감/속보 (최근 24시간 필터)
    try:
        url_ko = "https://news.google.com/rss/search?q=뉴욕증시+마감+다우+나스닥+when:1d&hl=ko&gl=KR&ceid=KR:ko"
        res_ko = requests.get(url_ko, headers=headers, timeout=5)
        if res_ko.status_code == 200:
            root = ET.fromstring(res_ko.content)
            for item in root.findall('./channel/item')[:3]:
                title = item.find('title').text
                source = item.find('source').text if item.find('source') is not None else "국내언론"
                clean_title = title.rsplit(" - ", 1)[0]
                news_items.append(f"• <b>[미증시]</b> {clean_title} <i>({source})</i>")
    except Exception:
        pass

    # 2. 미국 월가 현지 실시간 시장 뉴스 (최근 24시간 필터)
    try:
        url_en = "https://news.google.com/rss/search?q=Wall+Street+today+stocks+rally+fall+when:1d&hl=en-US&gl=US&ceid=US:en"
        res_en = requests.get(url_en, headers=headers, timeout=5)
        if res_en.status_code == 200:
            root = ET.fromstring(res_en.content)
            for item in root.findall('./channel/item'):
                if len(news_items) >= 5:
                    break
                title = item.find('title').text
                source = item.find('source').text if item.find('source') is not None else "외신"
                clean_title = title.rsplit(" - ", 1)[0]
                translated = translate_to_ko_robust(clean_title)
                news_items.append(f"• <b>[월가소식]</b> {translated} <i>({source})</i>")
    except Exception:
        pass

    if len(news_items) < 5:
        fallbacks = [
            "• <b>[미증시]</b> 미 국채 금리 및 인플레이션 지표 경계감 속 혼조세 <i>(블룸버그)</i>",
            "• <b>[미증시]</b> 주요 빅테크 실적 및 경제지표 발표 앞두고 관망세 <i>(마켓워치)</i>"
        ]
        for fb in fallbacks:
            if len(news_items) >= 5:
                break
            news_items.append(fb)

    return news_items[:5]

def get_weekly_calendar():
    """💡 주차별·월별 실제 스케줄 동적 갱신 엔진"""
    today = datetime.now()
    start_monday = today - timedelta(days=today.weekday())
    
    first_day_of_month = today.replace(day=1)
    week_of_month = (today.day + first_day_of_month.weekday()) // 7 + 1
    month = today.month

    is_major_earnings = month in [1, 4, 7, 10] and week_of_month >= 2

    if week_of_month == 1:
        schedules = [
            ("월", "⚪ 글로벌 제조업 PMI 확정치 발표 (경기 확장세 점검)", "장전: 개장 전 유통/소비재 실적"),
            ("화", "🟡 23:00 미 ISM 제조업 PMI & JOLTs 구인건수 (노동시장 둔화 여부)", "장후: 클라우드/소프트웨어 실적"),
            ("수", "🟡 21:15 미 ADP 민간고용 보고서 & ISM 서비스업 PMI (소비 건전성)", "장후: 사이버보안 및 엔터프라이즈"),
            ("목", "🔴 21:30 신규 실업수당청구건수 & 무역수지 발표 (고용 안정성)", "장전: 글로벌 물류/운송 밸류체인"),
            ("금", "🔴 21:30 미 노동부 비농업 고용보고서(NFP) & 실업률 (월가 최고 관심사)", "장전: 방산/에너지 대형주")
        ]
    elif week_of_month == 2:
        schedules = [
            ("월", "⚪ 뉴욕 연은 기대인플레이션 발표 및 미 국채 입찰", "장후: 헬스케어 및 바이오텍 실적"),
            ("화", "🟡 미 NFIB 소기업 낙관지수 & 국채 10년물 입찰", "장전: 은행 및 금융 플랫폼"),
            ("수", "🔴 21:30 미 CPI(소비자물가지수) 발표 (연준 금리 결정 직결 핵심)", "장후: 반도체 장비 및 부품사"),
            ("목", "🔴 21:30 미 PPI(생산자물가지수) & 주간 실업보험청구건수", "장전: 대형 리테일/백화점 실적"),
            ("금", "🟡 23:00 미시간대 소비자심리지수 & 기대인플레이션 예비치", "장전: 통신 및 유틸리티 실적")
        ]
    elif week_of_month == 3:
        schedules = [
            ("월", "⚪ 뉴욕 엠파이어스테이트 제조업지수 발표", "장후: 클라우드/네트워크 인프라"),
            ("화", "🟡 21:30 미 소매판매(Retail Sales) & 산업생산 (소비 모멘텀 확인)", "장전: 빅파마 및 메디컬 디바이스"),
            ("수", "🔴 FOMC 회의록 공개 또는 연준 주요 위원 발언 집중", "장후: 전기차/모빌리티 실적"),
            ("목", "🔴 21:30 필라델피아 연은 제조업지수 & 기존주택판매", "장후: 페덱스(FDX) 등 경기 풍향계"),
            ("금", "🔴 미국 선물·옵션 동시 만기일(쿼드러플 위칭) 변동성 주의", "장전: 레저/호스피탈리티 실적")
        ]
    else:
        schedules = [
            ("월", "⚪ 댈러스 연은 제조업지수 및 재무부 단기채 발행", "장후: AI 소프트웨어 플랫폼"),
            ("화", "🟡 23:00 미 콘퍼런스보드(CB) 소비자신뢰지수 & 주택가격지수", "장전: 산업재 및 엔지니어링"),
            ("수", "🔴 21:30 미 분기 GDP 성장률 속보치/수정치 & 도매재고", "장후: 주요 빅테크/반도체 대장주"),
            ("목", "🔴 21:30 주간 신규 실업수당청구건수 & 펜딩주택판매", "장후: 이커머스 및 플랫폼 테크"),
            ("금", "🔴 21:30 미 연준 최선호 물가지표 근원 PCE(개인소비지출) 물가", "장전: 정유/글로벌 에너지 메이저")
        ]

    cal_days = []
    for idx, (dow, macro, earnings) in enumerate(schedules):
        d = start_monday + timedelta(days=idx)
        d_str = d.strftime("%m/%d")
        
        earnings_text = earnings
        if is_major_earnings and idx in [2, 3]:
            earnings_text = "🔥 빅테크/반도체 실적 피크 위크 (장후 실적 가이던스 촉각)"

        cal_days.append({
            "date_label": f"{d_str} ({dow})",
            "macro": macro,
            "earnings": earnings_text
        })
    return cal_days

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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
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
        hist_vix = yf.Ticker("^VIX").history(period="5d").dropna(subset=['Close'])
        vix = hist_vix['Close'].iloc[-1]
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

def get_sp500_market_breadth():
    s50_val = None
    s200_val = None

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        r50 = requests.get("https://www.barchart.com/stocks/quotes/%24S5FI/overview", headers=headers, timeout=5)
        if r50.status_code == 200:
            m50 = re.search(r'"lastPrice":\s*"?([0-9\.]+)"?', r50.text)
            if m50:
                s50_val = float(m50.group(1))
    except Exception:
        pass

    try:
        r200 = requests.get("https://www.barchart.com/stocks/quotes/%24S5TH/overview", headers=headers, timeout=5)
        if r200.status_code == 200:
            m200 = re.search(r'"lastPrice":\s*"?([0-9\.]+)"?', r200.text)
            if m200:
                s200_val = float(m200.group(1))
    except Exception:
        pass

    if s50_val is None or s200_val is None:
        above_50 = 0
        above_200 = 0
        total = 0
        for sym in SECTOR_ETF_TICKERS.keys():
            try:
                h = yf.Ticker(sym).history(period="1y").dropna(subset=['Close'])
                if len(h) >= 200:
                    cp = h['Close'].iloc[-1]
                    m50 = h['Close'].iloc[-50:].mean()
                    m200 = h['Close'].iloc[-200:].mean()
                    if cp > m50:
                        above_50 += 1
                    if cp > m200:
                        above_200 += 1
                    total += 1
            except Exception:
                continue
        if total > 0:
            if s50_val is None:
                s50_val = round((above_50 / total) * 100, 1)
            if s200_val is None:
                s200_val = round((above_200 / total) * 100, 1)
        else:
            s50_val = 50.0
            s200_val = 60.0

    if s200_val >= 60.0 and s50_val >= 50.0:
        health_status = "🟢 광범위한 대세 상승장 (건전한 상승 흐름)"
    elif s200_val >= 50.0 and s50_val < 35.0:
        health_status = "🟡 대세 상승장 내 단기 조정 (눌림목 반등 기회)"
    elif s200_val < 50.0 and s50_val >= 50.0:
        health_status = "🟠 소수 주도주 중심의 차별화 반등 (선별 대응 필요)"
    elif s200_val < 40.0 and s50_val < 25.0:
        health_status = "🚨 시장 전반 극단적 과매도/침체 (바닥권 모니터링)"
    else:
        health_status = "⚖️ 종목별 순환매 및 혼조세 (중립 구간)"

    return s50_val, s200_val, health_status

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

def fetch_sector_etfs():
    sector_list = []
    for sym, name in SECTOR_ETF_TICKERS.items():
        try:
            t = yf.Ticker(sym)
            hist = t.history(period="1y").dropna(subset=['Close'])
            if len(hist) < 2:
                continue

            cur_p = float(hist['Close'].iloc[-1])
            prev_p = float(hist['Close'].iloc[-2])
            w1_p = float(hist['Close'].iloc[-5]) if len(hist) >= 5 else float(hist['Close'].iloc[0])
            m1_p = float(hist['Close'].iloc[-21]) if len(hist) >= 21 else float(hist['Close'].iloc[0])
            y1_p = float(hist['Close'].iloc[0])

            d_chg = ((cur_p - prev_p) / prev_p) * 100 if prev_p else 0.0
            w_chg = ((cur_p - w1_p) / w1_p) * 100 if w1_p else 0.0
            m_chg = ((cur_p - m1_p) / m1_p) * 100 if m1_p else 0.0
            y_chg = ((cur_p - y1_p) / y1_p) * 100 if y1_p else 0.0

            high_52w = t.info.get("fiftyTwoWeekHigh")
            if not high_52w or pd.isna(high_52w):
                high_52w = float(hist['High'].max())
            low_52w = t.info.get("fiftyTwoWeekLow")
            if not low_52w or pd.isna(low_52w):
                low_52w = float(hist['Low'].min())

            mdd = ((cur_p - high_52w) / high_52w) * 100 if high_52w else 0.0
            
            slider_pct = 0.0
            if high_52w > low_52w:
                slider_pct = max(0.0, min(100.0, ((cur_p - low_52w) / (high_52w - low_52w)) * 100))

            sector_list.append({
                "sym": sym,
                "name": name,
                "cur_p": cur_p,
                "d_chg": d_chg,
                "w_chg": w_chg,
                "m_chg": m_chg,
                "y_chg": y_chg,
                "mdd": mdd,
                "high_52
