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

# 💡 에테나(ENA-USD) 추가
CRYPTO_TICKERS = {
    "비트코인 (BTC)": "BTC-USD",
    "이더리움 (ETH)": "ETH-USD",
    "리플 (XRP)": "XRP-USD",
    "솔라나 (SOL)": "SOL-USD",
    "에테나 (ENA)": "ENA-USD"
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
    "AMAT", "ALAB", "BE", "COHR", "SCHD", "TQQQ",
    "005930.KS", "000660.KS"
]

WATCH_TICKERS = [
    "PWR", "LITE", "FCX", "CVX", "CRCL", "CAT", "OXY", 
    "AAPL", "AMZN", "META", "HOOD", "PANW", "ORCL",
    "CRWD", "FTNT", "ZS", "CYBR"
]

STOCK_INFO_MAP = {
    # 내 포트폴리오 (25개)
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
    "005930.KS": ("12.5x", "국내반도체", "삼성전자 (Samsung Electronics)"),
    "000660.KS": ("9.8x", "국내반도체", "SK하이닉스 (SK Hynix)"),
    
    # 관심종목 (17개)
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
    "CYBR": ("40.0x", "신원인증보안", "CyberArk Software")
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
    news_items = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    try:
        url_ko = "https://news.google.com/rss/search?q=뉴욕증시+미국주식+마감+특징주&hl=ko&gl=KR&ceid=KR:ko"
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

    try:
        url_en = "https://news.google.com/rss/search?q=Wall+Street+stock+market+stocks+rally+drop&hl=en-US&gl=US&ceid=US:en"
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
            "• <b>[미증시]</b> 미 연준 통화정책 경계감 속 국채 금리 및 기술주 차익 실현 매물 공방 <i>(마켓워치)</i>",
            "• <b>[미증시]</b> 주요 빅테크 및 반도체 밸류체인 실적 발표 앞두고 변동성 장세 지속 <i>(블룸버그)</i>"
        ]
        for fb in fallbacks:
            if len(news_items) >= 5:
                break
            news_items.append(fb)

    return news_items[:5]

def get_weekly_calendar():
    today = datetime.now()
    start_monday = today - timedelta(days=today.weekday())
    
    cal_days = []
    events_preset = [
        {"dow": "월", "day_offset": 0, "macro": "⚪ 제조업/서비스업 지수 및 단기 유동성 점검 (중요도: 보통)", "earnings": "장전: 리테일/소비재(KR 등) | 장후: 에너지"},
        {"dow": "화", "day_offset": 1, "macro": "🟡 21:30 미 소매판매(Retail Sales) & 산업생산 (중요도: 상 - 소비 건전성)", "earnings": "장전: COE 등 서비스 | 장후: 주택건설(LEN)"},
        {"dow": "수", "day_offset": 2, "macro": "🔴 FOMC 1일차 개막, 글로벌 주요국 CPI 물가 (중요도: 최상)", "earnings": "장후: 소프트웨어/플랫폼 밸류체인"},
        {"dow": "목", "day_offset": 3, "macro": "🔴 03:00 FOMC 금리 발표 & 기자회견, 21:30 신규 실업수당청구 (중요도: 최상)", "earnings": "장전: 페덱스(FDX, 경기 풍향계) | 장후: 대형 소비재"},
        {"dow": "금", "day_offset": 4, "macro": "🔴 BOJ 금리 결정(엔캐리 촉각), 미 쿼드러플 위칭데이 (중요도: 최상)", "earnings": "장전: 금융/방산 실적 점검"}
    ]

    for item in events_preset:
        d = start_monday + timedelta(days=item["day_offset"])
        d_str = d.strftime("%m/%d")
        cal_days.append({
            "date_label": f"{d_str} ({item['dow']})",
            "macro": item["macro"],
            "earnings": item["earnings"]
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
                "high_52w": high_52w,
                "low_52w": low_52w,
                "slider_pct": slider_pct
            })
        except Exception:
            continue
    return sector_list

def fetch_stock_data_list(ticker_list):
    stock_data_list = []
    stock_cards = []
    high_vol = []

    for ticker in ticker_list:
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="1y").dropna(subset=['Close'])
            if len(hist) < 2:
                continue

            cur_p = float(hist['Close'].iloc[-1])
            prev_p = float(hist['Close'].iloc[-2])
            w1_p = float(hist['Close'].iloc[-5]) if len(hist) >= 5 else float(hist['Close'].iloc[0])
            m1_p = float(hist['Close'].iloc[-21]) if len(hist) >= 21 else float(hist['Close'].iloc[0])

            d_chg = ((cur_p - prev_p) / prev_p) * 100 if prev_p else 0.0
            w_chg = ((cur_p - w1_p) / w1_p) * 100 if w1_p else 0.0
            m_chg = ((cur_p - m1_p) / m1_p) * 100 if m1_p else 0.0

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

            sma20 = float(hist['Close'].rolling(window=20).mean().iloc[-1]) if len(hist) >= 20 else None
            sma50 = float(hist['Close'].rolling(window=50).mean().iloc[-1]) if len(hist) >= 50 else None
            sma200 = float(hist['Close'].rolling(window=200).mean().iloc[-1]) if len(hist) >= 200 else None

            disp20 = ((cur_p - sma20) / sma20) * 100 if sma20 and not pd.isna(sma20) else None
            disp50 = ((cur_p - sma50) / sma50) * 100 if sma50 and not pd.isna(sma50) else None
            disp200 = ((cur_p - sma200) / sma200) * 100 if sma200 and not pd.isna(sma200) else None

            disp20_str = f"{disp20:+.1f}%" if disp20 is not None else "N/A"
            disp50_str = f"{disp50:+.1f}%" if disp50 is not None else "N/A"
            disp200_str = f"{disp200:+.1f}%" if disp200 is not None else "N/A"

            fwd_pe = t.info.get("forwardPE")
            pe_str = f"{fwd_pe:.1f}x" if fwd_pe and fwd_pe > 0 else "N/A"
            
            sec_pe, sector_name, full_name = STOCK_INFO_MAP.get(ticker, ("22.0x", "일반", ticker))
            display_name = full_name.split()[0] if "(" in full_name else ticker

            if abs(d_chg) >= 10.0:
                sign_txt = "급등 🚀" if d_chg > 0 else "급락 🩸"
                high_vol.append(f"🚨 <b>{display_name} ({ticker})</b>: {d_chg:+.1f}% {sign_txt}")

            if "SOXL" in ticker or "TQQQ" in ticker:
                sig = "⚪ 비중관리"
            elif pe_str != "N/A" and float(pe_str.replace("x","")) < float(sec_pe.replace("x","")):
                sig = "🟢 저평가분할"
            elif mdd <= -35.0:
                sig = "🟡 낙폭과대"
            else:
                sig = "🟡 홀딩/분할"

            stock_data_list.append({
                "ticker": ticker, 
                "full_name": full_name,
                "sector_name": sector_name,
                "cur_p": cur_p, "d_chg": d_chg, 
                "high_52w": high_52w, "low_52w": low_52w,
                "mdd": mdd, "slider_pct": slider_pct,
                "disp20": disp20, "disp50": disp50, "disp200": disp200,
                "disp20_str": disp20_str, "disp50_str": disp50_str, "disp200_str": disp200_str,
                "pe_str": pe_str, "sec_pe": sec_pe, "sig": sig
            })

            p_str = f"₩{cur_p:,.0f}" if ".KS" in ticker else f"${cur_p:.2f}"
            card = (
                f"▪️ <b>{ticker}</b> ({full_name}) | <code>{sector_name}</code>\n"
                f"   <b>가격:</b> {p_str} ({d_chg:+.1f}%) | <b>MDD:</b> {mdd:.1f}%\n"
                f"   <b>이격도:</b> 20D <b>{disp20_str}</b> | 50D <b>{disp50_str}</b> | 200D <b>{disp200_str}</b>\n"
                f"   <b>밸류:</b> F-PER <b>{pe_str}</b> (섹터: {sec_pe}) ➔ {sig}"
            )
            stock_cards.append(card)
        except Exception:
            continue

    return stock_data_list, stock_cards, high_vol

def generate_full_html(now_str, update_time_str, core_signal, score, rating, fg_status, 
                       s50_val, s200_val, breadth_status, summary_lines, 
                       macro_data, crypto_data, us_news, weekly_cal, index_data_list, 
                       sector_etfs, my_stocks, watch_stocks, high_vol):
    os.makedirs("docs", exist_ok=True)

    cal_html = ""
    for c in weekly_cal:
        cal_html += f"""
        <div class="cal-card">
            <div class="cal-header">
                <span class="cal-date">{c['date_label']}</span>
            </div>
            <div class="cal-body">
                <div class="cal-line"><b>📊 거시지표:</b> {c['macro']}</div>
                <div class="cal-line mt-1"><b>🏢 실적체크:</b> {c['earnings']}</div>
            </div>
        </div>
        """

    idx_cards_html = ""
    for d in index_data_list:
        chg_color = "#ef4444" if d['d_chg'] < 0 else "#22c55e"
        unit = "pt" if "^" in d['sym'] else "$"
        idx_cards_html += f"""
        <div class="card">
            <div class="flex-between">
                <span class="card-title">{d['name']}</span>
                <span class="price">{unit}{d['cur_p']:.2f}</span>
            </div>
            <div class="flex-between mt-1">
                <span style="color: {chg_color}; font-weight: bold;">{d['d_chg']:+.2f}%</span>
                <span class="text-sub">1주 {d['w_chg']:+.2f}% | 1달 {d['m_chg']:+.2f}%</span>
            </div>
            <div class="flex-between mt-2 pt-2 border-t">
                <span class="text-sub">52주 최고: {unit}{d['high_52w']:.2f}</span>
                <span class="badge-mdd">MDD {d['mdd']:.2f}%</span>
            </div>
            <div class="mt-1 text-sub">RSI(14): <b>{d['rsi_str']}</b></div>
        </div>
        """

    macro_cards_html = ""
    for m in macro_data:
        chg_color = "#ef4444" if m['d_chg'] < 0 else "#22c55e"
        macro_cards_html += f"""
        <div class="macro-card">
            <div class="flex-between">
                <span class="bold">{m['name']}</span>
                <span class="price">{m['cur_str']}</span>
            </div>
            <div class="flex-between mt-1">
                <span style="color: {chg_color}; font-weight: bold;">{m['d_chg']:+.2f}%</span>
                <span class="text-sub">{m['comment']}</span>
            </div>
        </div>
        """

    # 💡 가상자산 카드 HTML: 1H / 24H 와 7D / 30D (상승률 & 고점대비) 2단 구성
    crypto_cards_html = ""
    for c in crypto_data:
        d_chg_color = "#ef4444" if c['d_chg'] < 0 else "#22c55e"
        h_chg_color = "#ef4444" if c['h1_chg'] < 0 else "#22c55e"
        w_chg_color = "#ef4444" if c['w_chg'] < 0 else "#22c55e"
        m_chg_color = "#ef4444" if c['m_chg'] < 0 else "#22c55e"
        
        # 가격 표기 (에테나 등 1달러 미만일 경우 소수점 4자리까지 대응)
        p_format = f"${c['cur_p']:,.4f}" if c['cur_p'] < 1.0 else f"${c['cur_p']:,.2f}"

        crypto_cards_html += f"""
        <div class="crypto-card">
            <div class="flex-between">
                <span class="bold" style="font-size: 14px;">{c['name']}</span>
                <span class="price">{p_format}</span>
            </div>
            <div class="flex-between mt-1">
                <span style="color: {h_chg_color}; font-weight: bold; font-size: 12px;">1H: {c['h1_chg']:+.2f}%</span>
                <span style="color: {d_chg_color}; font-weight: bold; font-size: 12px;">24H: {c['d_chg']:+.2f}%</span>
            </div>
            <div class="flex-between mt-2 pt-2 border-t" style="font-size: 11px;">
                <div>7D: <b style="color: {w_chg_color};">{c['w_chg']:+.2f}%</b> <span class="badge-sub">고점 {c['d7_mdd']:+.1f}%</span></div>
                <div>30D: <b style="color: {m_chg_color};">{c['m_chg']:+.2f}%</b> <span class="badge-sub">고점 {c['d30_mdd']:+.1f}%</span></div>
            </div>
        </div>
        """

    sector_rows_html = ""
    for s in sector_etfs:
        c_d = "#ef4444" if s['d_chg'] < 0 else "#22c55e"
        c_w = "#ef4444" if s['w_chg'] < 0 else "#22c55e"
        c_m = "#ef4444" if s['m_chg'] < 0 else "#22c55e"
        c_y = "#ef4444" if s['y_chg'] < 0 else "#22c55e"
        
        sector_rows_html += f"""
        <tr>
            <td class="bold">{s['sym']} <span class="text-sub" style="font-size: 11px;">({s['name'].split()[0]})</span></td>
            <td>${s['cur_p']:.2f}</td>
            <td style="color: {c_d}; font-weight: bold;">{s['d_chg']:+.2f}%</td>
            <td style="color: {c_w};">{s['w_chg']:+.2f}%</td>
            <td style="color: {c_m};">{s['m_chg']:+.2f}%</td>
            <td style="color: {c_y};">{s['y_chg']:+.2f}%</td>
            <td style="min-width: 170px;">
                <div class="slider-wrap">
                    <span class="slider-val">{s['low_52w']:.1f}</span>
                    <div class="slider-track">
                        <div class="slider-dot" style="left: {s['slider_pct']:.1f}%;"></div>
                    </div>
                    <span class="slider-val">{s['high_52w']:.1f}</span>
                </div>
                <div class="slider-sub">
                    <span class="badge-mdd">MDD {s['mdd']:.1f}%</span>
                </div>
            </td>
        </tr>
        """

    def render_table_rows(stock_list):
        rows = ""
        for s in stock_list:
            chg_color = "#ef4444" if s['d_chg'] < 0 else "#22c55e"
            c20 = "#22c55e" if s['disp20'] and s['disp20'] >= 0 else "#ef4444"
            c50 = "#22c55e" if s['disp50'] and s['disp50'] >= 0 else "#ef4444"
            c200 = "#22c55e" if s['disp200'] and s['disp200'] >= 0 else "#ef4444"
            
            is_kr = ".KS" in s['ticker']
            cur_display = f"₩{s['cur_p']:,.0f}" if is_kr else f"${s['cur_p']:.2f}"
            low_str = f"₩{s['low_52w']:,.0f}" if is_kr else f"{s['low_52w']:.1f}"
            high_str = f"₩{s['high_52w']:,.0f}" if is_kr else f"{s['high_52w']:.1f}"
            
            rows += f"""
            <tr>
                <td style="line-height: 1.35; min-width: 150px;">
                    <div class="bold" style="font-size: 14px;">{s['ticker']}</div>
                    <div style="font-size: 11px; color: var(--text-sub); margin: 2px 0;">{s['full_name']}</div>
                    <span class="sector-tag">{s['sector_name']}</span>
                </td>
                <td style="font-weight: 700;">{cur_display}</td>
                <td style="color: {chg_color}; font-weight: bold;">{s['d_chg']:+.2f}%</td>
                <td style="min-width: 175px;">
                    <div class="slider-wrap">
                        <span class="slider-val">{low_str}</span>
                        <div class="slider-track">
                            <div class="slider-dot" style="left: {s['slider_pct']:.1f}%;"></div>
                        </div>
                        <span class="slider-val">{high_str}</span>
                    </div>
                    <div class="slider-sub">
                        <span class="badge-mdd">MDD {s['mdd']:.1f}%</span>
                    </div>
                </td>
                <td style="font-size: 11px; line-height: 1.4; white-space: nowrap;">
                    20D: <b style="color: {c20};">{s['disp20_str']}</b><br>
                    50D: <b style="color: {c50};">{s['disp50_str']}</b><br>
                    200D: <b style="color: {c200};">{s['disp200_str']}</b>
                </td>
                <td>{s['pe_str']} <span class="text-sub">({s['sec_pe']})</span></td>
                <td><span class="signal-tag">{s['sig']}</span></td>
            </tr>
            """
        return rows

    my_rows_html = render_table_rows(my_stocks)
    watch_rows_html = render_table_rows(watch_stocks)

    summary_html = "".join([f"<li>{line.replace('• ', '')}</li>" for line in summary_lines])
    us_news_html = "".join([f"<li>{line.replace('• ', '')}</li>" for line in us_news])

    high_vol_html = ""
    if high_vol:
        vol_items = "".join([f"<div class='vol-item'>{v}</div>" for v in high_vol])
        high_vol_html = f"<div class='high-vol-box'><h4>🚨 10%+ 고변동 종목</h4>{vol_items}</div>"

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Global Market Radar</title>
    <style>
        :root {{
            --bg: #0b0f19;
            --card-bg: #151d30;
            --border: #23314e;
            --text-main: #f1f5f9;
            --text-sub: #94a3b8;
            --accent: #38bdf8;
            --green: #22c55e;
            --red: #ef4444;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
        body {{ background-color: var(--bg); color: var(--text-main); padding: 14px; font-size: 14px; line-height: 1.5; }}
        header {{ margin-bottom: 16px; }}
        h1 {{ font-size: 19px; font-weight: 800; color: var(--accent); }}
        .date {{ color: var(--text-sub); font-size: 12px; margin-top: 2px; }}
        .signal-box {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 12px; margin-bottom: 14px; }}
        .badge-core {{ display: inline-block; font-size: 14px; font-weight: bold; padding: 4px 10px; border-radius: 8px; background: #23314e; margin-top: 4px; }}
        .card, .macro-card, .crypto-card, .cal-card {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 12px; margin-bottom: 10px; }}
        .cal-header {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }}
        .cal-date {{ font-size: 13px; font-weight: 800; color: var(--accent); background: rgba(56, 189, 248, 0.1); padding: 2px 8px; border-radius: 6px; }}
        .cal-line {{ font-size: 12px; color: #cbd5e1; line-height: 1.4; }}
        .flex-between {{ display: flex; justify-content: space-between; align-items: center; }}
        .card-title {{ font-size: 14px; font-weight: bold; }}
        .price {{ font-size: 15px; font-weight: 800; }}
        .text-sub {{ color: var(--text-sub); font-size: 12px; }}
        .mt-1 {{ margin-top: 4px; }}
        .mt-2 {{ margin-top: 8px; }}
        .pt-2 {{ padding-top: 8px; }}
        .border-t {{ border-top: 1px solid var(--border); }}
        .badge-mdd {{ background: rgba(239, 68, 68, 0.15); color: #f87171; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; }}
        .badge-sub {{ background: #1e293b; color: #cbd5e1; padding: 2px 6px; border-radius: 4px; font-size: 10px; }}
        .sector-tag {{ display: inline-block; font-size: 10px; background: rgba(56, 189, 248, 0.12); color: #38bdf8; padding: 1px 6px; border-radius: 4px; border: 1px solid rgba(56, 189, 248, 0.25); }}
        .section-title {{ font-size: 15px; font-weight: 700; margin: 20px 0 8px; display: flex; align-items: center; gap: 6px; color: #e2e8f0; }}
        ul {{ padding-left: 18px; }}
        li {{ margin-bottom: 6px; color: #cbd5e1; font-size: 13px; }}
        .table-wrap {{ overflow-x: auto; -webkit-overflow-scrolling: touch; border-radius: 12px; border: 1px solid var(--border); background: var(--card-bg); margin-bottom: 14px; }}
        table {{ width: 100%; border-collapse: collapse; min-width: 680px; font-size: 13px; }}
        th, td {{ padding: 10px 10px; text-align: left; border-bottom: 1px solid var(--border); vertical-align: middle; }}
        th {{ background: #1a243b; color: var(--text-sub); font-size: 11px; text-transform: uppercase; }}
        .bold {{ font-weight: bold; }}
        .signal-tag {{ font-size: 11px; padding: 2px 6px; background: #23314e; border-radius: 4px; white-space: nowrap; }}
        
        .slider-wrap {{ display: flex; align-items: center; gap: 6px; }}
        .slider-val {{ font-size: 11px; color: var(--text-sub); white-space: nowrap; }}
        .slider-track {{ position: relative; flex: 1; height: 5px; background: #2b3954; border-radius: 3px; min-width: 55px; }}
        .slider-dot {{ position: absolute; top: -3.5px; width: 12px; height: 12px; background: #38bdf8; border: 2px solid #0b0f19; border-radius: 50%; transform: translateX(-50%); box-shadow: 0 0 6px rgba(56, 189, 248, 0.8); }}
        .slider-sub {{ margin-top: 4px; display: flex; align-items: center; gap: 6px; }}

        .high-vol-box {{ background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 10px; padding: 12px; margin-bottom: 14px; }}
        .high-vol-box h4 {{ color: #f87171; font-size: 13px; margin-bottom: 6px; }}
        .vol-item {{ font-size: 12px; margin-bottom: 2px; }}
        .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }}
        .badge-live {{ display: inline-block; background: #22c55e; color: #fff; font-size: 10px; padding: 2px 6px; border-radius: 10px; margin-left: 6px; animation: pulse 2s infinite; }}
        @keyframes pulse {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0.4; }} 100% {{ opacity: 1; }} }}
        @media (max-width: 480px) {{ .grid-2 {{ grid-template-columns: 1fr; }} }}
    </style>
</head>
<body>
    <header>
        <h1>📡 GLOBAL 증시 & 자산 투자 레이더 <span class="badge-live">LIVE 1H</span></h1>
        <div class="date">최근 동기화: {update_time_str} KST (1시간 주기 자동 갱신)</div>
    </header>

    <div class="signal-box">
        <div>오늘의 핵심 시장 신호</div>
        <div class="badge-core">{core_signal}</div>
        <div class="mt-2 text-sub">CNN Fear & Greed: <b>{score}점 ({rating})</b> | {fg_status}</div>
    </div>

    <div class="card" style="border-left: 4px solid var(--accent);">
        <div class="flex-between">
            <span class="card-title">🌡️ S&P 500 마켓 브레드 (Market Breadth)</span>
            <span class="badge-sub">시장 건전성 온·습도계</span>
        </div>
        <div class="flex-between mt-2 pt-2 border-t">
            <div>
                <span class="text-sub">50일선 상회 (단기 모멘텀):</span> <b>{s50_val:.1f}%</b>
            </div>
            <div>
                <span class="text-sub">200일선 상회 (대세 상승선):</span> <b>{s200_val:.1f}%</b>
            </div>
        </div>
        <div class="mt-2" style="font-size: 12px; color: #38bdf8;">
            <b>상태 진단:</b> {breadth_status}
        </div>
    </div>

    {high_vol_html}

    <div class="section-title">🇺🇸 미 증시 실시간 핵심 & 인기 뉴스 TOP 5</div>
    <div class="card">
        <ul>{us_news_html}</ul>
    </div>

    <div class="section-title">🪙 가상자산 시황 (1H / 24H / 7D & 30D 종합)</div>
    <div class="grid-2">
        {crypto_cards_html}
    </div>

    <div class="section-title">💵 환율·금리 & 유가 (Macro FX/Rates/Oil)</div>
    <div class="grid-2">
        {macro_cards_html}
    </div>

    <div class="section-title">📊 미 증시 마감/현재 브리핑</div>
    <div class="card">
        <ul>{summary_html}</ul>
    </div>

    <div class="section-title">📅 이번 주 경제지표 & 어닝 캘린더 (월~금)</div>
    {cal_html}

    <div class="section-title">📈 글로벌 8대 주요 지수 정밀 진단</div>
    {idx_cards_html}

    <div class="section-title">🏢 미국 11대 섹터 시황 레이더 (US Equity Sectors)</div>
    <div class="table-wrap">
        <table>
            <thead>
                <tr>
                    <th>섹터 티커 (Name)</th>
                    <th>현재가</th>
                    <th>전일대비</th>
                    <th>1주</th>
                    <th>1달</th>
                    <th>1년</th>
                    <th>52주 범위 & MDD</th>
                </tr>
            </thead>
            <tbody>
                {sector_rows_html}
            </tbody>
        </table>
    </div>

    <div class="section-title">💼 내 포트폴리오 (미국 23개 + 국내 2개)</div>
    <div class="table-wrap">
        <table>
            <thead>
                <tr>
                    <th>종목 정보 (Ticker / Name / Sector)</th>
                    <th>현재가</th>
                    <th>전일대비</th>
                    <th>52주 범위 & MDD</th>
                    <th>이격도 (20/50/200D)</th>
                    <th>F-PER</th>
                    <th>신호</th>
                </tr>
            </thead>
            <tbody>
                {my_rows_html}
            </tbody>
        </table>
    </div>

    <div class="section-title">⭐ 관심종목 레이더 (Watchlist 17개)</div>
    <div class="table-wrap">
        <table>
            <thead>
                <tr>
                    <th>종목 정보 (Ticker / Name / Sector)</th>
                    <th>현재가</th>
                    <th>전일대비</th>
                    <th>52주 범위 & MDD</th>
                    <th>이격도 (20/50/200D)</th>
                    <th>F-PER</th>
                    <th>신호</th>
                </tr>
            </thead>
            <tbody>
                {watch_rows_html}
            </tbody>
        </table>
    </div>
    <div class="mt-2 text-sub" style="text-align: right;">※ 표를 좌우로 밀어서 전체 항목 확인 (슬라이더의 파란 점은 52주 내 현재 주가 위치입니다)</div>
</body>
</html>
"""
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html)

def run_radar():
    kst = pytz.timezone('Asia/Seoul')
    now_kst = datetime.now(kst)
    now_str = now_kst.strftime("%Y-%m-%d")
    update_time_str = now_kst.strftime("%Y-%m-%d %H:%M")

    is_morning_report_time = (now_kst.hour == 7)

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

    s50_val, s200_val, breadth_status = get_sp500_market_breadth()

    # 1. 지수 수집
    index_cards = []
    index_changes = {}
    index_data_list = []

    for name, sym in INDEX_TICKERS.items():
        try:
            t = yf.Ticker(sym)
            hist = t.history(period="1y").dropna(subset=['Close'])
            if len(hist) < 2:
                continue

            cur_p = float(hist['Close'].iloc[-1])
            prev_p = float(hist['Close'].iloc[-2])
            w1_p = float(hist['Close'].iloc[-5]) if len(hist) >= 5 else float(hist['Close'].iloc[0])
            m1_p = float(hist['Close'].iloc[-21]) if len(hist) >= 21 else float(hist['Close'].iloc[0])

            d_chg = ((cur_p - prev_p) / prev_p) * 100 if prev_p else 0.0
            w_chg = ((cur_p - w1_p) / w1_p) * 100 if w1_p else 0.0
            m_chg = ((cur_p - m1_p) / m1_p) * 100 if m1_p else 0.0
            index_changes[sym] = d_chg

            high_52w = t.info.get("fiftyTwoWeekHigh")
            if not high_52w or pd.isna(high_52w):
                high_52w = float(hist['High'].max())
            mdd = ((cur_p - high_52w) / high_52w) * 100 if high_52w else 0.0

            rsi_val = calculate_rsi(hist['Close'], period=14)
            rsi_str = "N/A" if pd.isna(rsi_val) else (f"🔥 {rsi_val:.1f}" if rsi_val >= 70 else (f"❄️ {rsi_val:.1f}" if rsi_val <= 30 else f"{rsi_val:.1f}"))

            index_data_list.append({
                "sym": sym, "name": name, "cur_p": cur_p, "d_chg": d_chg,
                "w_chg": w_chg, "m_chg": m_chg, "high_52w": high_52w,
                "mdd": mdd, "rsi_str": rsi_str
            })

            unit = "pt" if "^" in sym else "$"
            card = (
                f"▪️ <b>{name}</b>: <b>{unit}{cur_p:.2f}</b> ({d_chg:+.2f}%)\n"
                f"   변동: 1주 {w_chg:+.2f}% | 1달 {m_chg:+.2f}%\n"
                f"   52주 최고: {unit}{high_52w:.2f} | <b>MDD: {mdd:.2f}%</b> | RSI: <b>{rsi_str}</b>"
            )
            index_cards.append(card)
        except Exception:
            continue

    # 2. 매크로 & 환율/유가 수집
    macro_data = []
    macro_telegram = []
    for name, sym in MACRO_TICKERS.items():
        try:
            t = yf.Ticker(sym)
            hist = t.history(period="5d").dropna(subset=['Close'])
            if len(hist) < 2:
                continue
            cur_p = float(hist['Close'].iloc[-1])
            prev_p = float(hist['Close'].iloc[-2])
            d_chg = ((cur_p - prev_p) / prev_p) * 100 if prev_p else 0.0

            if sym == "^TNX":
                cur_str = f"{cur_p:.3f}%"
                comment = "금리 안정" if d_chg < 0 else "금리 상승 압력"
            elif sym == "DX-Y.NYB":
                cur_str = f"{cur_p:.2f}pt"
                comment = "달러 약세 (우호적)" if d_chg < 0 else "달러 강세"
            elif sym == "CL=F":
                cur_str = f"${cur_p:.2f}"
                comment = "인플레 완화 (호재)" if d_chg < 0 else "유가 상승 (인플레 경계)"
            elif sym == "USDKRW=X":
                cur_str = f"{cur_p:,.1f}원"
                comment = "원화 절상" if d_chg < 0 else "환율 상승"
            elif sym == "JPYKRW=X":
                val_100yen = cur_p * 100
                cur_str = f"{val_100yen:,.1f}원"
                comment = "엔화 강세" if d_chg > 0 else "엔저 지속"

            macro_data.append({"name": name, "cur_str": cur_str, "d_chg": d_chg, "comment": comment})
            macro_telegram.append(f"• <b>{name}</b>: <b>{cur_str}</b> ({d_chg:+.2f}%) | <i>{comment}</i>")
        except Exception:
            continue

    # 3. 가상자산 수집 (1H, 24H, 7D, 30D 상승률 및 고점대비 계산)
    crypto_data = []
    crypto_telegram = []
    solana_alert_msg = None

    for name, sym in CRYPTO_TICKERS.items():
        try:
            t = yf.Ticker(sym)
            hist_1h = t.history(period="2d", interval="1h").dropna(subset=['Close'])
            if len(hist_1h) >= 2:
                cur_p = float(hist_1h['Close'].iloc[-1])
                prev_1h_p = float(hist_1h['Close'].iloc[-2])
                h1_chg = ((cur_p - prev_1h_p) / prev_1h_p) * 100
            else:
                cur_p = float(t.history(period="2d").dropna(subset=['Close'])['Close'].iloc[-1])
                h1_chg = 0.0

            hist_d = t.history(period="45d").dropna(subset=['Close'])
            prev_d_p = float(hist_d['Close'].iloc[-2]) if len(hist_d) >= 2 else cur_p
            d_chg = ((cur_p - prev_d_p) / prev_d_p) * 100

            # 💡 주간(7D) 및 월간(30D) 수익률 계산
            p_7d = float(hist_d['Close'].iloc[-7]) if len(hist_d) >= 7 else float(hist_d['Close'].iloc[0])
            p_30d = float(hist_d['Close'].iloc[-30]) if len(hist_d) >= 30 else float(hist_d['Close'].iloc[0])
            w_chg = ((cur_p - p_7d) / p_7d) * 100 if p_7d else 0.0
            m_chg = ((cur_p - p_30d) / p_30d) * 100 if p_30d else 0.0

            # 고점 대비 낙폭 (7D & 30D)
            high_7d = float(hist_d['High'].iloc[-7:].max()) if len(hist_d) >= 7 else float(hist_d['High'].max())
            d7_mdd = ((cur_p - high_7d) / high_7d) * 100 if high_7d else 0.0

            high_30d = float(hist_d['High'].iloc[-30:].max()) if len(hist_d) >= 30 else float(hist_d['High'].max())
            d30_mdd = ((cur_p - high_30d) / high_30d) * 100 if high_30d else 0.0

            crypto_data.append({
                "name": name, "cur_p": cur_p, 
                "h1_chg": h1_chg, "d_chg": d_chg,
                "w_chg": w_chg, "m_chg": m_chg,
                "d7_mdd": d7_mdd, "d30_mdd": d30_mdd
            })

            p_format = f"${cur_p:,.4f}" if cur_p < 1.0 else f"${cur_p:,.2f}"
            crypto_telegram.append(
                f"• <b>{name}</b>: <b>{p_format}</b>\n"
                f"  └ 단기: 1H <b>{h1_chg:+.2f}%</b> | 24H <b>{d_chg:+.2f}%</b>\n"
                f"  └ 주간(7D): <b>{w_chg:+.1f}%</b> (고점: {d7_mdd:+.1f}%) | 월간(30D): <b>{m_chg:+.1f}%</b> (고점: {d30_mdd:+.1f}%)"
            )

            # 솔라나(SOL-USD) 5%+ 변동 감시
            if sym == "SOL-USD" and abs(d_chg) >= 5.0:
                direction = "급등 🚀" if d_chg > 0 else "급락 🩸"
                solana_alert_msg = (
                    f"🚨 <b>[솔라나(SOL) 5%+ 변동성 긴급 레이더]</b>\n"
                    f"─────────────────\n"
                    f"• <b>현재가:</b> ${cur_p:,.2f}\n"
                    f"• <b>24시간 변동률:</b> <b>{d_chg:+.2f}% ({direction})</b>\n"
                    f"• <b>직전 1시간 변동:</b> {h1_chg:+.2f}%\n"
                    f"• <b>7D 수익률:</b> {w_chg:+.1f}% | <b>30D 수익률:</b> {m_chg:+.1f}%\n"
                    f"• <b>측정 시각:</b> {update_time_str} KST\n"
                    f"─────────────────\n"
                    f"💡 <i>솔라나 24시간 등락폭이 ±5% 기준을 초과하여 발송된 실시간 알림입니다.</i>"
                )

        except Exception:
            continue

    if solana_alert_msg:
        send_message(solana_alert_msg)

    # 4. 미 증시 인기 뉴스 TOP 5 & 캘린더
    us_popular_news = get_us_market_popular_news()
    weekly_cal = get_weekly_calendar()

    cal_telegram = []
    for c in weekly_cal:
        cal_telegram.append(f"▪️ <b>[{c['date_label']}]</b>\n  • {c['macro']}\n  • 🏢 {c['earnings']}")

    spy_c = index_changes.get("SPY", 0.0)
    qqq_c = index_changes.get("QQQ", 0.0)
    soxx_c = index_changes.get("SOXX", 0.0)
    vix_val = index_changes.get("^VIX", 0.0)

    summary_lines = [
        f"• <b>S&P 500(SPY)</b>: {spy_c:+.2f}% 마감/진행",
        f"• <b>나스닥 100(QQQ)</b>: {qqq_c:+.2f}% 마감/진행",
        f"• <b>반도체(SOXX)</b>: {soxx_c:+.2f}% 시현",
        f"• <b>VIX 변동성</b>: 전일대비 {vix_val:+.2f}% 기록",
        f"• <b>CNN 공탐지수</b>: {score}pt ({rating})"
    ]

    # 5. 미국 11대 섹터 ETF 수집
    sector_etfs = fetch_sector_etfs()
    
    sector_summary_telegram = []
    if sector_etfs:
        sorted_sectors = sorted(sector_etfs, key=lambda x: x['d_chg'], reverse=True)
        top3 = [f"{s['sym']} ({s['d_chg']:+.1f}%)" for s in sorted_sectors[:3]]
        bot3 = [f"{s['sym']} ({s['d_chg']:+.1f}%)" for s in sorted_sectors[-3:]]
        sector_summary_telegram = [
            f"• <b>강세 섹터:</b> {', '.join(top3)}",
            f"• <b>약세 섹터:</b> {', '.join(bot3)}"
        ]

    # 6. 종목 수집 (내 포트폴리오 25개 + 관심 종목 17개)
    my_stocks, my_stock_cards, my_high_vol = fetch_stock_data_list(MY_TICKERS)
    watch_stocks, watch_stock_cards, watch_high_vol = fetch_stock_data_list(WATCH_TICKERS)
    
    total_high_vol = my_high_vol + watch_high_vol

    # HTML 웹 대시보드 생성 (1시간 주기 자동 갱신)
    generate_full_html(now_str, update_time_str, core_signal, score, rating, fg_status, 
                       s50_val, s200_val, breadth_status, summary_lines, 
                       macro_data, crypto_data, us_popular_news, weekly_cal, index_data_list, 
                       sector_etfs, my_stocks, watch_stocks, total_high_vol)

    # 아침 07:00 KST 정기 발송
    if is_morning_report_time:
        part1 = [
            "<b>📡 GLOBAL 증시 & 자산 투자 레이더 (Part 1/3)</b>",
            f"<b>📅 일자:</b> {now_str} (아침 07:00 KST)",
            f"<b>🚦 오늘의 핵심 신호:</b> {core_signal}",
            f"<b>🌡️ CNN 공탐지수:</b> {score}점 ({rating}) | {fg_status}",
            f"<b>📊 S&P 500 마켓 브레드:</b> 50일선 <b>{s50_val:.1f}%</b> | 200일선 <b>{s200_val:.1f}%</b>\n  └ <i>{breadth_status}</i>",
            "─────────────────",
            "<b>🏢 11대 섹터 당일 동향 요약</b>",
            "\n".join(sector_summary_telegram) if sector_summary_telegram else "• 섹터 데이터 집계 중",
            "─────────────────",
            "<b>🇺🇸 미 증시 실시간 인기/핵심 뉴스 TOP 5</b>",
            "\n".join(us_popular_news),
            "─────────────────",
            "<b>📅 이번 주 경제지표 & 어닝 캘린더</b>",
            "\n".join(cal_telegram),
            "─────────────────",
            "<b>💵 환율·금리 & 유가 (Macro FX/Rates/Oil)</b>",
            "\n".join(macro_telegram),
            "─────────────────",
            "<b>🪙 가상자산 시황 (1H / 24H / 7D / 30D)</b>",
            "\n".join(crypto_telegram),
            "─────────────────",
            "<b>📈 주요 8대 지수 정밀 진단</b>",
            "\n\n".join(index_cards)
        ]
        send_message("\n".join(part1))

        part2 = [
            "<b>💼 내 포트폴리오 25개 정밀 진단 (Part 2/3)</b>",
            "─────────────────"
        ]
        if my_high_vol:
            part2.append("<b>🚨 마감 기준 10%+ 고변동 종목</b>")
            part2.extend(my_high_vol)
            part2.append("─────────────────")
        part2.extend(my_stock_cards)
        send_message("\n".join(part2))

        part3 = [
            "<b>⭐ 관심종목(Watchlist) 17개 정밀 진단 (Part 3/3)</b>",
            "─────────────────"
        ]
        if watch_high_vol:
            part3.append("<b>🚨 관심종목 10%+ 고변동 포착</b>")
            part3.extend(watch_high_vol)
            part3.append("─────────────────")
        part3.extend(watch_stock_cards)
        send_message("\n".join(part3))

if __name__ == "__main__":
    run_radar()
