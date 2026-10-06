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

WATCH_TICKERS = [
    "PWR", "LITE", "FCX", "CVX", "CRCL", "CAT", "OXY", 
    "AAPL", "AMZN", "META", "HOOD", "PANW", "ORCL",
    "CRWD", "FTNT", "ZS", "CYBR", "LLY", "MSTR"
]

STOCK_INFO_MAP = {
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
        url = f"
