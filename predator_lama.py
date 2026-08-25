"""
PREDATOR QUANTUM PRO — SETUP BOARD EDITION
==========================================
Gabungan tampilan terminal Predator Quantum Pro dengan mesin seleksi Setup Board
yang parameternya sudah diuji walk-forward.

Jalankan:  streamlit run predator_setup_board.py
Kebutuhan: pip install streamlit yfinance pandas numpy plotly feedparser streamlit-autorefresh requests
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import warnings, re, json, os, time
import urllib.parse
from datetime import datetime, timedelta, timezone
from collections import Counter, defaultdict

import plotly.graph_objects as go
from plotly.subplots import make_subplots

try:
    import feedparser
    ADA_FEED = True
except Exception:
    ADA_FEED = False
try:
    import requests
    ADA_REQ = True
except Exception:
    ADA_REQ = False
try:
    from streamlit_autorefresh import st_autorefresh
    ADA_AUTOREFRESH = True
except Exception:
    ADA_AUTOREFRESH = False

warnings.filterwarnings("ignore")
st.set_page_config(page_title="PREDATOR QUANTUM PRO", layout="wide")

WIB = timezone(timedelta(hours=7))
JURNAL_FILE = "jurnal.csv"

# =====================================================================
# TAMPILAN
# =====================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=JetBrains+Mono:wght@500;800&family=Inter:wght@400;600;900&display=swap');
.stApp { background-color:#020406; color:#fff; }
.header-container{padding:14px;background:rgba(0,255,204,.02);border-radius:10px;
  border:1px solid rgba(0,255,204,.1);text-align:center;margin-bottom:14px}
.header-title{font-family:'Orbitron',sans-serif!important;font-weight:900;font-size:34px!important;
  background:linear-gradient(90deg,#00ffcc,#ff0055);-webkit-background-clip:text;
  -webkit-text-fill-color:transparent;letter-spacing:5px}
.header-sub{font-family:'JetBrains Mono';font-size:10px;color:#7c8a94;letter-spacing:2px;margin-top:4px}
.macro-strip{display:flex;justify-content:space-around;background:#0a0e14;padding:9px;
  border-radius:5px;border:1px solid #333;margin-bottom:14px;flex-wrap:wrap;gap:6px}
.macro-item{font-family:'JetBrains Mono';font-size:12px;text-align:center}
.macro-label{font-size:9px;color:#888;display:block;margin-bottom:2px;letter-spacing:1px}
.macro-val-up{color:#00ffcc;font-weight:bold}
.macro-val-down{color:#ff0055;font-weight:bold}
.pixel-container{display:flex;gap:4px;margin-bottom:4px;background:#0a0e14;padding:5px;
  border-radius:5px;border:1px solid #333}
.pixel-metric{flex:1;text-align:center;font-family:'JetBrains Mono'}
.pixel-title{font-size:8px;color:#888;display:block;margin-bottom:2px;letter-spacing:1px}
.pixel-value-up{color:#00ffcc;font-weight:900;font-size:11px;text-shadow:0 0 5px rgba(0,255,204,.5)}
.pixel-value-down{color:#ff0055;font-weight:900;font-size:11px;text-shadow:0 0 5px rgba(255,0,85,.5)}
.pixel-value-neutral{color:#ffd166;font-weight:900;font-size:11px}
.thesis-box{background:rgba(2,20,20,.6);border-left:2px solid #00ffcc;border-right:1px solid #333;
  border-top:1px solid #333;border-bottom:1px solid #333;padding:11px;border-radius:4px;
  margin-top:8px;font-family:'Inter',sans-serif;font-size:12px;line-height:1.55;color:#ccc}
.thesis-header{font-family:'Orbitron';font-size:10px;color:#00ffcc;margin-bottom:5px;letter-spacing:1px}
.news-scroll-box{max-height:520px;overflow-y:auto}
.news-box{background:#0a0e14;border-left:3px solid #ff4d4d;padding:6px;margin-bottom:6px;border-radius:4px}
.news-box:hover{border-left:3px solid #00ffcc;background:#111a21}
.news-topic-header{font-family:'Orbitron';font-size:9px;color:#00ffcc;font-weight:bold}
.news-text{font-family:'Inter',sans-serif;font-size:10px;color:#e0e0e0}
.news-text a{text-decoration:none;color:inherit}
.blink{animation:blinker 1s linear infinite;font-family:'Orbitron';font-size:13px;color:#ff0055;
  text-align:center;letter-spacing:2px;margin:16px 0}
@keyframes blinker{50%{opacity:.35;color:#00ffcc}}
.warnbox{background:rgba(255,0,85,.06);border-left:3px solid #ff0055;padding:9px 12px;
  border-radius:4px;font-family:'Inter';font-size:11.5px;color:#c9d3d8;margin-bottom:12px}
.warnbox b{color:#fff}
[data-testid="stDataFrame"]{border:1px solid #333!important}
[data-testid="stDataFrame"] div[role="columnheader"]{background:#0a0e14!important;color:#00ffcc!important;
  font-family:'Orbitron'!important;font-weight:800!important;border-bottom:1px solid #444!important}
[data-testid="stDataFrame"] div[role="gridcell"]{background:#020406!important;color:#e0e0e0!important;
  font-family:'JetBrains Mono'!important;border-bottom:1px solid #222!important}
[data-testid="stDataFrame"] div[role="row"]:hover div[role="gridcell"]{background:rgba(0,255,204,.1)!important}
section[data-testid="stSidebar"]{background:#060a0f;border-right:1px solid #222}
</style>
""", unsafe_allow_html=True)

# =====================================================================
# PETA GRUP, SEKTOR, TEMA
# =====================================================================
MASTER_AFILIASI = {
    "BREN":"PRAJOGO PANGESTU","TPIA":"PRAJOGO PANGESTU","CUAN":"PRAJOGO PANGESTU","BRPT":"PRAJOGO PANGESTU",
    "PTRO":"PRAJOGO PANGESTU","CGAS":"PRAJOGO PANGESTU","CDIA":"PRAJOGO PANGESTU","GZCO":"PRAJOGO PANGESTU",
    "BUMI":"BAKRIE","BRMS":"BAKRIE","ENRG":"BAKRIE","DEWA":"BAKRIE","BNBR":"BAKRIE","UNSP":"BAKRIE",
    "VIVA":"BAKRIE","MDIA":"BAKRIE","JGLE":"BAKRIE","ALII":"BAKRIE","ELTY":"BAKRIE","BTEL":"BAKRIE","VKTR":"BAKRIE",
    "AMMN":"SALIM","INDF":"SALIM","ICBP":"SALIM","LSIP":"SALIM","SIMP":"SALIM","META":"SALIM",
    "ROTI":"SALIM","IMAS":"SALIM","DNET":"SALIM","MEDC":"SALIM",
    "DSSA":"SINAR MAS","BSDE":"SINAR MAS","INKP":"SINAR MAS","TKIM":"SINAR MAS","SMMA":"SINAR MAS",
    "DUTI":"SINAR MAS","SMAR":"SINAR MAS","FREN":"SINAR MAS","DMAS":"SINAR MAS",
    "PANI":"AGUAN","MKPI":"AGUAN","ASRI":"AGUAN","CBDK":"AGUAN",
    "ADRO":"BOY THOHIR","ADMR":"BOY THOHIR","ESSA":"BOY THOHIR","MBMA":"BOY THOHIR","MDKA":"BOY THOHIR",
    "DRMA":"TP RACHMAT","TAPG":"TP RACHMAT","DSNG":"TP RACHMAT","ASSA":"TP RACHMAT","ASLC":"TP RACHMAT",
    "RAJA":"HAPPY HAPSORO","CBRE":"HAPPY HAPSORO","PSAB":"HAPPY HAPSORO","MINA":"HAPPY HAPSORO","OASA":"HAPPY HAPSORO",
    "JIHD":"TOMY WINATA","SCBD":"TOMY WINATA","TINY":"TOMY WINATA",
    "KPIG":"MNC","BHIT":"MNC","MNCN":"MNC","IPTV":"MNC","BABP":"MNC","BCAP":"MNC",
    "LPKR":"LIPPO","LPPF":"LIPPO","MLPL":"LIPPO","MPPA":"LIPPO","SILO":"LIPPO","LPCK":"LIPPO","MLPT":"LIPPO",
    "GOTO":"TECH","EMTK":"EMTEK","SCMA":"EMTEK","BUKA":"TECH","ARTO":"TECH",
    "BBRI":"BUMN","BMRI":"BUMN","BBNI":"BUMN","BBTN":"BUMN","BRIS":"BUMN","TLKM":"BUMN","ANTM":"BUMN",
    "PTBA":"BUMN","TINS":"BUMN","PGAS":"BUMN","SMGR":"BUMN","JSMR":"BUMN","PGEO":"BUMN","MTEL":"BUMN",
    "WIKA":"BUMN KARYA","PTPP":"BUMN KARYA","ADHI":"BUMN KARYA","WTON":"BUMN KARYA","WEGE":"BUMN KARYA","PPRE":"BUMN KARYA",
    "ASII":"ASTRA","UNTR":"ASTRA","AALI":"ASTRA","ASGR":"ASTRA","AUTO":"ASTRA",
    "BBCA":"DJARUM","TOWR":"DJARUM","SUPR":"DJARUM",
    "PNBN":"PANIN","PNIN":"PANIN","PNLF":"PANIN","CFIN":"PANIN",
    "AMRT":"ALFAMART","MIDI":"ALFAMART","BUDI":"SUNGAI BUDI","TBLA":"SUNGAI BUDI",
    "MEGA":"CT CORP","BBHI":"CT CORP","SRTG":"SARATOGA","TBIG":"SARATOGA","MPMX":"SARATOGA",
}

SECTOR_MAP = {
    "BBCA":"FINANCE","BBRI":"FINANCE","BMRI":"FINANCE","BBNI":"FINANCE","BBTN":"FINANCE","BRIS":"FINANCE",
    "ARTO":"FINANCE","BJBR":"FINANCE","BJTM":"FINANCE","TUGU":"FINANCE","PNBN":"FINANCE","BDMN":"FINANCE",
    "BBHI":"FINANCE","SRTG":"FINANCE","ADMF":"FINANCE","BNGA":"FINANCE","BNII":"FINANCE","NISP":"FINANCE",
    "ADRO":"ENERGY","PTBA":"ENERGY","ITMG":"ENERGY","BYAN":"ENERGY","HRUM":"ENERGY","INDY":"ENERGY",
    "MEDC":"ENERGY","ELSA":"ENERGY","PGAS":"ENERGY","AKRA":"ENERGY","DOID":"ENERGY","BUMI":"ENERGY",
    "ENRG":"ENERGY","RAJA":"ENERGY","ADMR":"ENERGY","GEMS":"ENERGY","BSSR":"ENERGY","PGEO":"ENERGY","TOBA":"ENERGY",
    "ANTM":"BASIC-MAT","MDKA":"BASIC-MAT","INCO":"BASIC-MAT","TINS":"BASIC-MAT","MBMA":"BASIC-MAT",
    "NCKL":"BASIC-MAT","BRMS":"BASIC-MAT","PSAB":"BASIC-MAT","INKP":"BASIC-MAT","TKIM":"BASIC-MAT",
    "SMGR":"BASIC-MAT","INTP":"BASIC-MAT","TPIA":"BASIC-MAT","BRPT":"BASIC-MAT","ESSA":"BASIC-MAT",
    "LTLS":"BASIC-MAT","AMMN":"BASIC-MAT","ARCI":"BASIC-MAT","HRTA":"BASIC-MAT",
    "TLKM":"INFRA","ISAT":"INFRA","EXCL":"INFRA","FREN":"INFRA","JSMR":"INFRA","TBIG":"INFRA",
    "TOWR":"INFRA","MTEL":"INFRA","META":"INFRA","PPRE":"INFRA","ADHI":"INFRA","WIKA":"INFRA","PTPP":"INFRA",
    "ICBP":"CONSUMER","INDF":"CONSUMER","UNVR":"CONSUMER","MYOR":"CONSUMER","AMRT":"CONSUMER","MIDI":"CONSUMER",
    "ACES":"CONSUMER","MAPI":"CONSUMER","MAPA":"CONSUMER","CPIN":"CONSUMER","JPFA":"CONSUMER","GGRM":"CONSUMER",
    "HMSP":"CONSUMER","KLBF":"CONSUMER","SIDO":"CONSUMER","AUTO":"CONSUMER","ASII":"CONSUMER","ERAA":"CONSUMER",
    "BSDE":"PROPERTY","CTRA":"PROPERTY","SMRA":"PROPERTY","PWON":"PROPERTY","ASRI":"PROPERTY","DILD":"PROPERTY",
    "PANI":"PROPERTY","APLN":"PROPERTY","LPCK":"PROPERTY","LPKR":"PROPERTY","BEST":"PROPERTY","DMAS":"PROPERTY",
    "GOTO":"TECH","BUKA":"TECH","EMTK":"TECH","SCMA":"TECH","WIRG":"TECH","DCII":"TECH","MTDL":"TECH",
    "ASSA":"TRANS","BIRD":"TRANS","SMDR":"TRANS","TMAS":"TRANS","GIAA":"TRANS","IATA":"TRANS",
    "AALI":"PLANTATION","LSIP":"PLANTATION","SIMP":"PLANTATION","SMAR":"PLANTATION","DSNG":"PLANTATION",
    "TAPG":"PLANTATION","SGRO":"PLANTATION","UNTR":"HEAVY-EQP","PTRO":"HEAVY-EQP",
}

THEMES = {
    "batubara": ["ADRO","ADMR","PTBA","ITMG","HRUM","BUMI","GEMS","BSSR","MBAP","DOID","TOBA","BYAN"],
    "emas":     ["ANTM","MDKA","BRMS","PSAB","ARCI","HRTA"],
    "tembaga":  ["MDKA","BRMS","AMMN"],
    "nikel":    ["INCO","ANTM","NICL","MBMA","NCKL"],
    "minyak":   ["MEDC","ELSA","ENRG","PGAS","RAJA"],
    "cpo":      ["AALI","LSIP","SIMP","SMAR","DSNG","TAPG","SGRO","PALM","ANJT","BWPT"],
    "kertas":   ["INKP","TKIM","FASW"],
    "timah":    ["TINS"],
}
# Hanya tema dengan acuan harga gratis. Sisanya sengaja dibiarkan netral —
# tidak ada proxy batubara/nikel/CPO yang bisa diandalkan tanpa berlangganan.
COMMODITY_PROXY = {"emas": "GC=F", "tembaga": "HG=F", "minyak": "CL=F"}

RSS_LINKS = [
    "https://www.google.co.id/alerts/feeds/16876890487441803706/701647301640953919",
    "https://www.google.co.id/alerts/feeds/16876890487441803706/701647301640956058",
    "https://www.google.co.id/alerts/feeds/16876890487441803706/17720372188069162265",
    "https://www.google.co.id/alerts/feeds/16876890487441803706/4715023400486420700",
    "https://www.google.co.id/alerts/feeds/16876890487441803706/6157427371671042291",
    "https://www.google.co.id/alerts/feeds/16876890487441803706/8676695815866551512",
]

# =====================================================================
# PARAMETER SELEKSI  (sesuai SPESIFIKASI-PARAMETER.md)
# =====================================================================
STOCH_SCORE = {
    "GOLDEN CROSS DI JENUH JUAL": 100,
    "OVERSOLD & MULAI NAIK":       92,
    "CROSS UP DARI BAWAH":         82,
    "JENUH JUAL, BELUM BERBALIK":  70,
    "NAIK DARI ZONA BAWAH":        60,
    "NAIK DI ZONA TENGAH":         36,
    "MELEMAH":                      0,
    "JENUH BELI":                   0,
    "JENUH BELI, MULAI TURUN":      0,
    "N/A":                         30,
}
STOCH_BURUK = {"MELEMAH", "JENUH BELI", "JENUH BELI, MULAI TURUN"}

PRESETS = {
    "SEIMBANG":         {"stoch":30,"vol":30,"akum":18,"peer":12,"struktur":15,"tema":5},
    "JENUH JUAL":       {"stoch":45,"vol":25,"akum":10,"peer":6, "struktur":10,"tema":0},
    "AKUMULASI SENYAP": {"stoch":18,"vol":35,"akum":40,"peer":10,"struktur":15,"tema":5},
    "KEJAR LAGGARD":    {"stoch":15,"vol":25,"akum":15,"peer":45,"struktur":10,"tema":5},
    "VOLUME BICARA":    {"stoch":20,"vol":50,"akum":25,"peer":6, "struktur":15,"tema":0},
}

FALLBACK_UNIVERSE = sorted(set(list(MASTER_AFILIASI) + list(SECTOR_MAP) +
    [t for v in THEMES.values() for t in v]))

# =====================================================================
# PENGAMBILAN DATA
# =====================================================================
@st.cache_data(ttl=86400, show_spinner=False)
def ambil_universe():
    """Daftar emiten IDX dari screener TradingView. Gagal -> daftar bawaan."""
    if not ADA_REQ:
        return FALLBACK_UNIVERSE, "bawaan"
    try:
        body = {"filter":[{"left":"type","operation":"equal","right":"stock"}],
                "columns":["name","sector"],"range":[0,1200],
                "sort":{"sortBy":"name","sortOrder":"asc"}}
        r = requests.post("https://scanner.tradingview.com/indonesia/scan", json=body, timeout=25,
                          headers={"User-Agent":"Mozilla/5.0"})
        rows = r.json().get("data", [])
        tics, sect = [], {}
        for d in rows:
            kode = d["d"][0]
            if kode and kode.isalpha() and 3 <= len(kode) <= 5:
                tics.append(kode)
                if d["d"][1]:
                    sect.setdefault(kode, d["d"][1])
        if len(tics) > 200:
            for k, v in sect.items():
                SECTOR_MAP.setdefault(k, v)
            return sorted(set(tics)), "TradingView"
    except Exception:
        pass
    return FALLBACK_UNIVERSE, "bawaan"


@st.cache_data(ttl=900, show_spinner=False)
def ambil_harga(tickers, periode="1y", batch=80):
    """Unduh bar harian secara batch. Jauh lebih cepat daripada per emiten."""
    keluar = {}
    for i in range(0, len(tickers), batch):
        chunk = [f"{t}.JK" for t in tickers[i:i+batch]]
        try:
            df = yf.download(chunk, period=periode, interval="1d", progress=False,
                             auto_adjust=False, group_by="ticker", threads=True)
        except Exception:
            continue
        for sym in chunk:
            kode = sym[:-3]
            try:
                sub = df[sym] if isinstance(df.columns, pd.MultiIndex) else df
                sub = sub[["Open","High","Low","Close","Volume"]].dropna()
                if len(sub) >= 90:
                    keluar[kode] = sub
            except Exception:
                continue
    return keluar


@st.cache_data(ttl=900, show_spinner=False)
def ambil_makro():
    out = {}
    peta = {"^JKSE":"IHSG","IDR=X":"USDIDR","CL=F":"OIL","GC=F":"GOLD","HG=F":"COPPER","^IXIC":"NASDAQ"}
    try:
        df = yf.download(list(peta), period="1mo", interval="1d", progress=False,
                         auto_adjust=False, group_by="ticker", threads=True)
        for sym, nama in peta.items():
            try:
                s = (df[sym]["Close"] if isinstance(df.columns, pd.MultiIndex) else df["Close"]).dropna()
                if len(s) >= 2:
                    out[nama] = {"val": float(s.iloc[-1]),
                                 "chg": float(s.iloc[-1]/s.iloc[-2]-1)*100,
                                 "chg1m": float(s.iloc[-1]/s.iloc[0]-1)*100,
                                 "chg1w": float(s.iloc[-1]/s.iloc[-min(6,len(s))]-1)*100}
            except Exception:
                continue
    except Exception:
        pass
    return out


@st.cache_data(ttl=1800, show_spinner=False)
def ambil_berita():
    peta_topik = {"AKUISISI":"AKUISISI","RIGHTS ISSUE":"RIGHTS ISSUE","DANANTARA":"DANANTARA",
                  "MERGER":"MERGER","EKSPANSI":"EKSPANSI","INVESTASI":"INVESTASI","LABA":"EARNINGS",
                  "RUGI":"EARNINGS","DIVIDEN":"DIVIDEN","KONTRAK":"KONTRAK"}
    peta, daftar = {}, []
    if not ADA_FEED:
        return peta, daftar
    for url in RSS_LINKS:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries:
                judul = re.sub(r"</?b>", "", e.title).strip()
                topik = "STRATEGIS"
                for k, v in peta_topik.items():
                    if k in judul.upper():
                        topik = v; break
                for t in set(re.findall(r"\b[A-Z]{4}\b", judul.upper())):
                    if t not in {"IHSG","IDX","LQ45","BEII"}:
                        peta[t] = {"judul": judul, "topik": topik}
                daftar.append({"TOPIC": topik, "NEWS": judul})
        except Exception:
            continue
    return peta, daftar

# =====================================================================
# MESIN METRIK
# =====================================================================
def hitung_stoch(df, n=10, sk=5, sd=5):
    """Stochastic penuh 10,5,5 — %K periode 10 dihaluskan 5, %D = SMA(%K,5)."""
    ll = df["Low"].rolling(n).min()
    hh = df["High"].rolling(n).max()
    raw = 100 * (df["Close"] - ll) / (hh - ll)
    raw = raw.replace([np.inf, -np.inf], np.nan).fillna(50)
    K = raw.rolling(sk).mean().fillna(50)
    D = K.rolling(sd).mean().fillna(50)
    return K, D


def klasifikasi_stoch(k, d, kp, dp):
    naik = k > kp
    cross = (kp <= dp) and (k > d)
    if k < 20 and cross:  return "GOLDEN CROSS DI JENUH JUAL"
    if k < 20 and naik:   return "OVERSOLD & MULAI NAIK"
    if k < 35 and cross:  return "CROSS UP DARI BAWAH"
    if k < 20:            return "JENUH JUAL, BELUM BERBALIK"
    if k < 45 and naik:   return "NAIK DARI ZONA BAWAH"
    if k > 80 and k < kp: return "JENUH BELI, MULAI TURUN"
    if k > 80:            return "JENUH BELI"
    if naik:              return "NAIK DI ZONA TENGAH"
    return "MELEMAH"


def profil_volume(C, V, H, L):
    """Verifikasi volume PER FASE. Rasio agregat 20 hari tidak bisa membedakan
    apakah volume besar muncul saat naik atau saat turun — ini yang membedakan."""
    n = len(C)
    av20 = float(np.mean(V[-20:])) or 1.0

    naik_i = [i for i in range(n-20, n) if C[i] > C[i-1]]
    turun_i = [i for i in range(n-20, n) if C[i] < C[i-1]]
    upVolQ = float(np.mean([V[i] for i in naik_i]))/av20 if naik_i else 0.0
    dnVolQ = float(np.mean([V[i] for i in turun_i]))/av20 if turun_i else 0.0

    # --- fase naik ---
    ret5 = C[-1]/C[-6] - 1
    push5 = float(np.mean(V[-5:]))/av20
    if ret5 > 0.01:
        if push5 >= 1.20:  naik_vonis, naik_skor = "NAIK DIDUKUNG VOLUME", 100
        elif push5 >= 0.95: naik_vonis, naik_skor = "NAIK, VOLUME SECUKUPNYA", 62
        else:               naik_vonis, naik_skor = "NAIK TANPA VOLUME", 0
    elif ret5 < -0.01:      naik_vonis, naik_skor = "SEDANG TURUN", 45
    else:                   naik_vonis, naik_skor = "MENDATAR", 50

    # --- fase turun: cari puncak ayunan, jendela melebar sampai ketemu koreksi >=2% ---
    dryUp, dryBasis, dec, adv, hari = None, None, 0.0, 0.0, 0
    for win in (40, 60, 90, 130):
        look = min(win, n-1)
        seg = C[-look:]
        p = n - look + int(np.argmax(seg))
        if p >= n-2 or (C[-1]/C[p] - 1) > -0.02:
            continue
        lo = max(1, p-win)
        pre = C[lo:p+1]
        q = lo + int(np.argmin(pre)) if len(pre) else lo
        va = float(np.mean(V[q+1:p+1])) if p > q else 0.0
        vd = float(np.mean(V[p+1:n])) if n-1 > p else 0.0
        if va > 0 and vd > 0:
            dryUp, dryBasis = vd/va, "leg"
            dec, adv, hari = C[-1]/C[p]-1, C[p]/C[q]-1, n-1-p
            break
    if dryUp is None and upVolQ > 0 and dnVolQ > 0:
        dryUp, dryBasis = dnVolQ/upVolQ, "harian"

    if dryUp is None:      turun_vonis, turun_skor = "TIDAK TERBACA", 50
    elif dryUp <= 0.70:    turun_vonis, turun_skor = "VOLUME JUAL MENGERING", 100
    elif dryUp <= 1.00:    turun_vonis, turun_skor = "VOLUME JUAL MENURUN", 75
    elif dryUp <= 1.25:    turun_vonis, turun_skor = "VOLUME JUAL SETARA", 30
    else:                  turun_vonis, turun_skor = "VOLUME JUAL LEBIH BESAR", 0

    return dict(upVolQ=upVolQ, dnVolQ=dnVolQ, dryUp=dryUp, dryBasis=dryBasis,
                declineRet=dec, advanceRet=adv, declineDays=hari, ret5=ret5, push5=push5,
                naikVonis=naik_vonis, naikSkor=naik_skor,
                turunVonis=turun_vonis, turunSkor=turun_skor,
                gateNaik=0 if naik_skor == 0 else 1,
                gateTurun=0 if turun_skor <= 30 else 1)


def profil_akumulasi(C, V, H, L):
    n = len(C)
    obv = np.zeros(n)
    for i in range(1, n):
        obv[i] = obv[i-1] + (V[i] if C[i] > C[i-1] else (-V[i] if C[i] < C[i-1] else 0))
    obvSlope = (obv[-1]-obv[-21]) / (float(np.mean(V[-21:]))*20 or 1)
    up = sum(V[i] for i in range(n-20, n) if C[i] > C[i-1])
    dn = sum(V[i] for i in range(n-20, n) if C[i] < C[i-1])
    ud = min(up/dn, 5.0) if dn > 0 else 3.0
    rng = np.where(H[-10:] > L[-10:], (C[-10:]-L[-10:])/np.maximum(H[-10:]-L[-10:], 1e-9), 0.5)
    closePos = float(np.mean(rng))
    rng_now = float(np.mean((H[-10:]-L[-10:])/C[-10:]))
    rng_ref = float(np.mean((H[-60:-10]-L[-60:-10])/C[-60:-10])) or rng_now
    compress = rng_ref/rng_now if rng_now > 0 else 1.0
    volRatio = float(np.mean(V[-10:]))/(float(np.mean(V[-60:])) or 1)
    drift = C[-1]/C[-21]-1
    stealth = max(0.0, volRatio-1) * max(0.0, compress-0.9) * (1 if -0.02 < drift < 0.14 else 0.3)
    return dict(obvSlope=obvSlope, upDown=ud, closePos=closePos, compress=compress,
                volRatio=volRatio, stealth=stealth, obvHist=(obv[-40:]/(float(np.mean(V[-21:]))*20 or 1)))


def metrik(kode, df):
    if len(df) < 90:
        return None
    C = df["Close"].values.astype(float); V = df["Volume"].values.astype(float)
    H = df["High"].values.astype(float);  L = df["Low"].values.astype(float)
    n = len(C)
    back = lambda k: C[max(0, n-1-k)]

    K, D = hitung_stoch(df)
    k, d, kp, dp = float(K.iloc[-1]), float(D.iloc[-1]), float(K.iloc[-2]), float(D.iloc[-2])
    sinyal = klasifikasi_stoch(k, d, kp, dp)

    tv = C*V
    tv20, tv60 = tv[-20:], tv[-60:]
    ma20, ma50 = float(np.mean(C[-20:])), float(np.mean(C[-50:]))
    ma20p = float(np.mean(C[-25:-5]))
    rets = C[-60:]/C[-61:-1]-1

    vol = profil_volume(C, V, H, L)
    akm = profil_akumulasi(C, V, H, L)

    return dict(
        SYMBOL=kode, PRICE=float(C[-1]), TANGGAL=df.index[-1].strftime("%Y-%m-%d"),
        CHG=float(C[-1]/C[-2]-1), RET1W=float(C[-1]/back(5)-1),
        RET1M=float(C[-1]/back(21)-1), RET3M=float(C[-1]/back(63)-1),
        MA20=ma20, MA50=ma50, VS_MA20=float(C[-1]/ma20-1), VS_MA50=float(C[-1]/ma50-1),
        MA_RISING=int(ma20 > ma20p), MA_CROSS=int(ma20 >= ma50),
        VOLATILITY=float(np.std(rets, ddof=1)*np.sqrt(252)),
        TURN_AVG=float(np.mean(tv20)), TURN_MED=float(np.median(tv20)),
        TURN_MIN20=float(np.min(tv20)), TURN_MIN60=float(np.min(tv60)),
        HARI_5M=int(np.sum(tv20 >= 5e9)),
        VOL_POWER=float(V[-1]/(np.mean(V[-20:]) or 1)),
        FLOW_VELOCITY=float(np.mean(V[-5:])/(np.mean(V[-50:]) or 1)),
        STOCH_K=k, STOCH_D=d, STOCH_SIGNAL=sinyal, STOCH_SCORE=STOCH_SCORE.get(sinyal, 30),
        SECTOR=SECTOR_MAP.get(kode, "OTHERS"), GROUP=MASTER_AFILIASI.get(kode, "EXTERNAL"),
        THEMES=[t for t, m in THEMES.items() if kode in m],
        **{f"V_{a}": b for a, b in vol.items()},
        **{f"A_{a}": b for a, b in akm.items() if a != "obvHist"},
        A_obvHist=akm["obvHist"], RAW=df,
    )

# =====================================================================
# KETINGGALAN SEKELOMPOK: GRUP -> TEMA -> SEKTOR
# =====================================================================
def hitung_peer_gap(rows):
    r1w = {r["SYMBOL"]: r["RET1W"] for r in rows}
    likuid = {r["SYMBOL"] for r in rows if r["TURN_MIN20"] >= 1e9}

    def pemimpin(anggota):
        ada = [t for t in anggota if t in r1w and t in likuid]
        return (max(ada, key=lambda t: r1w[t]), len(ada)) if len(ada) >= 2 else (None, 0)

    grup_lead, tema_lead, sekt_lead = {}, {}, {}
    for g in set(MASTER_AFILIASI.values()):
        L, n = pemimpin([t for t, v in MASTER_AFILIASI.items() if v == g])
        if L: grup_lead[g] = (L, r1w[L], n)
    for th, mem in THEMES.items():
        L, n = pemimpin(mem)
        if L: tema_lead[th] = (L, r1w[L], n)
    per_sekt = defaultdict(list)
    for r in rows:
        if r["SYMBOL"] in likuid:
            per_sekt[r["SECTOR"]].append(r["SYMBOL"])
    for s, mem in per_sekt.items():
        if len(mem) >= 4:
            L = max(mem, key=lambda t: r1w[t])
            sekt_lead[s] = (L, r1w[L], len(mem))

    for r in rows:
        t = r["SYMBOL"]; gap, basis, label, lead = 0.0, None, None, None
        g = r["GROUP"]
        if g in grup_lead and grup_lead[g][1] > 0.03:
            gap, basis, label, lead = grup_lead[g][1]-r1w[t], "GRUP", g, grup_lead[g][0]
        if gap <= 0.005:
            for th in r["THEMES"]:
                if th in tema_lead and tema_lead[th][1] > 0.03:
                    v = tema_lead[th][1]-r1w[t]
                    if v > gap: gap, basis, label, lead = v, "KOMODITAS", th, tema_lead[th][0]
        if gap <= 0.005:
            s = r["SECTOR"]
            if s in sekt_lead and sekt_lead[s][1] > 0.03:
                gap, basis, label, lead = sekt_lead[s][1]-r1w[t], "SEKTOR", s, sekt_lead[s][0]
        r["PEER_GAP"] = max(0.0, gap); r["PEER_BASIS"] = basis or "-"
        r["PEER_LABEL"] = label or "-"; r["PEER_LEADER"] = lead or "-"
    return rows, grup_lead, sekt_lead

# =====================================================================
# SKOR
# =====================================================================
def komponen_mentah(r, makro):
    vol = r["V_naikSkor"]*0.45 + r["V_turunSkor"]*0.45 + \
          float(np.clip((r["V_upVolQ"]-r["V_dnVolQ"])*20, -20, 20))
    akum = r["A_obvSlope"]*30 + (r["A_upDown"]-1)*18 + (r["A_closePos"]-0.5)*55 + r["A_stealth"]*35
    struk = (22 if r["MA_RISING"] else 0) + (22 if r["MA_CROSS"] else 0) + \
            float(np.clip(r["VS_MA50"]*100, -30, 30)) + float(np.clip(r["VS_MA20"]*100, -18, 18))
    tema = 0.0
    for th in r["THEMES"]:
        sym = COMMODITY_PROXY.get(th)
        if sym:
            nm = {"GC=F":"GOLD","HG=F":"COPPER","CL=F":"OIL"}[sym]
            m = makro.get(nm)
            if m: tema = max(tema, m["chg1m"]*1.6 + m["chg1w"])
    return {"stoch": r["STOCH_SCORE"], "vol": vol, "akum": akum,
            "peer": r["PEER_GAP"]*100, "struktur": struk, "tema": tema}


def beri_skor(rows, bobot, makro):
    """Z-score lintas-saham, lalu dijumlahkan menurut bobot.

    Skor bersifat RELATIF terhadap kandidat yang lolos saringan hari itu —
    bukan nilai mutlak. Skor 70 saat 15 kandidat berbeda arti dengan skor 70
    saat 150 kandidat.
    """
    if not rows:
        return rows
    total = sum(bobot.values()) or 1
    if len(rows) < 5:
        # sampel terlalu kecil untuk z-score yang berarti; pakai skala mentah
        for r in rows:
            m = komponen_mentah(r, makro)
            r["KONTRIB"] = {k: 0.0 for k in bobot}
            r["CONF"] = float(np.clip(m["stoch"]*0.5 + m["vol"]*0.5, 0, 100))
    else:
        mentah = [komponen_mentah(r, makro) for r in rows]
        Z = {}
        for k in bobot:
            v = np.array([m[k] for m in mentah], dtype=float)
            s = v.std(ddof=1) or 1.0
            Z[k] = np.clip((v - v.mean())/s, -3, 3)
        for i, r in enumerate(rows):
            kontrib = {k: float(Z[k][i]*bobot[k]/total) for k in bobot}
            r["KONTRIB"] = kontrib
            r["CONF"] = float(np.clip(50 + sum(kontrib.values())*16.7, 0, 100))
    rows.sort(key=lambda r: -r["CONF"])
    for i, r in enumerate(rows):
        r["RANK"] = i+1
        r["PORTO"] = "15-20% (Aggressive)" if r["CONF"] >= 70 else \
                     ("10% (Medium)" if r["CONF"] >= 58 else "2-5% (Speculative)")
    return rows

def peringkat_semua_preset(rows, makro):
    """Urutan LENGKAP tiap preset pada kumpulan kandidat yang sama.

    Tidak mengubah CONF/RANK milik preset aktif — skor tiap preset dihitung
    terpisah lalu hanya diambil urutannya.
    """
    if len(rows) < 5:
        return {p: [r["SYMBOL"] for r in rows] for p in PRESETS}
    mentah = [komponen_mentah(r, makro) for r in rows]
    kunci = list(PRESETS["SEIMBANG"].keys())
    Z = {}
    for k in kunci:
        v = np.array([m[k] for m in mentah], dtype=float)
        s = v.std(ddof=1) or 1.0
        Z[k] = np.clip((v - v.mean())/s, -3, 3)
    hasil = {}
    for nama, bbt in PRESETS.items():
        tot = sum(bbt.values()) or 1
        skor = [sum(Z[k][i]*bbt.get(k, 0)/tot for k in kunci) for i in range(len(rows))]
        urut = sorted(range(len(rows)), key=lambda i: -skor[i])
        hasil[nama] = [rows[i]["SYMBOL"] for i in urut]
    return hasil


def alokasi_papan(peringkat, mode, top_n=3):
    """Susun papan dari urutan tiap preset.

    KONSENSUS — tiap preset ambil top_n miliknya apa adanya. Saham yang sama
    boleh muncul di beberapa preset; itu hasil apa adanya dari parameter.

    EKSKLUSIF — draft bergiliran: tiap preset bergantian mengambil saham
    peringkat tertinggi yang belum diambil preset lain. Hasilnya nama-nama
    berbeda yang mewakili selera KHAS tiap preset. Konsekuensinya sebagian
    pick jadi lebih lemah secara absolut — potensi untung ditukar dengan
    kemampuan membuktikan preset mana yang benar.
    """
    nama_preset = list(peringkat.keys())
    if mode == "KONSENSUS":
        return {p: peringkat[p][:top_n] for p in nama_preset}
    papan = {p: [] for p in nama_preset}
    terpakai = set()
    for putaran in range(top_n):
        for p in nama_preset:
            pilih = next((t for t in peringkat[p] if t not in terpakai), None)
            if pilih:
                papan[p].append(pilih); terpakai.add(pilih)
    return papan


# =====================================================================
# NARASI
# =====================================================================
def bangun_tesis(r, makro, berita, tp_pct, sl_pct):
    p = []
    warna = "#00ffcc" if r["STOCH_SCORE"] >= 70 else ("#ffd166" if r["STOCH_SCORE"] >= 36 else "#ff0055")
    p.append(f"🔵 <b>STOCHASTIC (10,5,5):</b> %K={r['STOCH_K']:.1f} | %D={r['STOCH_D']:.1f} → "
             f"<span style='color:{warna}'><b>{r['STOCH_SIGNAL']}</b></span>")

    v = r
    dry = "–" if v["V_dryUp"] is None else f"{v['V_dryUp']:.2f}x"
    warna_v = "#00ffcc" if v["V_turunSkor"] >= 75 else ("#ffd166" if v["V_turunSkor"] >= 50 else "#ff0055")
    p.append(f"🌊 <b>VOLUME:</b> fase naik <b>{v['V_naikVonis']}</b> (volume 5h {v['V_push5']:.2f}x) · "
             f"fase turun <span style='color:{warna_v}'><b>{v['V_turunVonis']}</b></span> (turun/naik {dry})")

    if v["V_dryUp"] is not None and v["V_declineDays"]:
        p.append(f"📐 <b>LEG:</b> naik {v['V_advanceRet']*100:+.1f}% lalu koreksi {v['V_declineRet']*100:+.1f}% "
                 f"selama {v['V_declineDays']} hari.")

    p.append(f"🏗️ <b>STRUKTUR:</b> {'MA20 di atas MA50' if r['MA_CROSS'] else 'MA20 di bawah MA50'}, "
             f"{'MA20 menanjak' if r['MA_RISING'] else 'MA20 melandai'} · "
             f"vs MA20 {r['VS_MA20']*100:+.1f}% · vs MA50 {r['VS_MA50']*100:+.1f}%")

    p.append(f"💧 <b>LIKUIDITAS:</b> minimum harian Rp {r['TURN_MIN20']/1e9:.2f} M · "
             f"{r['HARI_5M']}/20 hari tembus Rp 5 M · median Rp {r['TURN_MED']/1e9:.1f} M")

    if r["PEER_GAP"] > 0.005:
        p.append(f"🔗 <b>KETINGGALAN {r['PEER_BASIS']}:</b> tertinggal {r['PEER_GAP']*100:.1f}pp dari "
                 f"<b>{r['PEER_LEADER']}</b> di {r['PEER_LABEL']}.")

    for th in r["THEMES"]:
        nm = {"emas":"GOLD","tembaga":"COPPER","minyak":"OIL"}.get(th)
        if nm and nm in makro:
            p.append(f"⛏️ <b>KOMODITAS:</b> tema {th} — acuan {nm} {makro[nm]['chg1m']:+.1f}% sebulan.")
        elif not nm:
            p.append(f"⛏️ <b>KOMODITAS:</b> tema {th} — tidak ada acuan harga gratis, komponen dinetralkan.")

    n = berita.get(r["SYMBOL"])
    if n:
        p.append(f"📰 <b>{n['topik']}:</b> {n['judul'][:90]}…")

    entry = int(r["PRICE"])
    tp = int(round(entry*(1+tp_pct/100)))
    sl = int(round(entry*(1-sl_pct/100)))
    p.append(f"<div style='margin-top:8px;padding-top:6px;border-top:1px dashed #333;"
             f"font-family:JetBrains Mono;font-size:11px'>🛡️ <b>EKSEKUSI:</b> BUY {entry:,} | "
             f"<span style='color:#ff4d4d'>STOP {sl:,} (-{sl_pct}%)</span> | "
             f"<span style='color:#00ffcc'>TARGET {tp:,} (+{tp_pct}%)</span></div>".replace(",", "."))
    return "<br>".join(p)

# =====================================================================
# GRAFIK
# =====================================================================
def grafik(r):
    df = r["RAW"].tail(60).copy()
    K, D = hitung_stoch(r["RAW"])
    K, D = K.tail(60), D.tail(60)
    av20 = r["RAW"]["Volume"].rolling(20).mean().tail(60)

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03,
                        row_heights=[0.52, 0.20, 0.28])

    fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"],
                  close=df["Close"], increasing_line_color="#00ffcc", decreasing_line_color="#ff0055",
                  name=r["SYMBOL"]), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["Close"].rolling(20).mean(),
                  line=dict(color="#ffd166", width=1), name="MA20"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=r["RAW"]["Close"].rolling(50).mean().tail(60),
                  line=dict(color="#7c8a94", width=1, dash="dot"), name="MA50"), row=1, col=1)

    warna_vol = ["#00ffcc" if c >= o else "#ff0055" for c, o in zip(df["Close"], df["Open"])]
    fig.add_trace(go.Bar(x=df.index, y=df["Volume"], marker_color=warna_vol, name="Volume"), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=av20, line=dict(color="#fff", width=1, dash="dot"),
                  name="VMA20"), row=2, col=1)

    fig.add_hrect(y0=80, y1=100, fillcolor="rgba(255,0,85,.10)", line_width=0, row=3, col=1)
    fig.add_hrect(y0=0, y1=20, fillcolor="rgba(0,255,204,.10)", line_width=0, row=3, col=1)
    for y in (20, 50, 80):
        fig.add_hline(y=y, line_dash="dot", line_color="#555", line_width=1, row=3, col=1)
    fig.add_trace(go.Scatter(x=K.index, y=K, line=dict(color="#0088ff", width=2), name="%K"), row=3, col=1)
    fig.add_trace(go.Scatter(x=D.index, y=D, line=dict(color="#ff9900", width=2), name="%D"), row=3, col=1)

    cu = (K > D) & (K.shift(1) <= D.shift(1))
    if cu.any():
        fig.add_trace(go.Scatter(x=K.index[cu], y=K[cu], mode="markers",
                      marker=dict(symbol="star", size=10, color="#ffff00"), name="Cross"), row=3, col=1)

    judul = (f"<b style='color:#fff;font-size:17px'>{r['SYMBOL']}</b>"
             f"<span style='color:#888;font-size:11px'> | {r['GROUP']} · {r['SECTOR']} · "
             f"skor {r['CONF']:.1f}</span>")
    fig.update_layout(template="plotly_dark", height=420, paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", showlegend=False, xaxis_rangeslider_visible=False,
                      margin=dict(l=8, r=8, t=46, b=8), title=dict(text=judul, x=0.02, y=0.96))
    fig.update_xaxes(showticklabels=False, row=1, col=1)
    fig.update_xaxes(showticklabels=False, row=2, col=1)
    fig.update_yaxes(showticklabels=False, row=2, col=1)
    fig.update_yaxes(range=[-5, 105], row=3, col=1)
    return fig

# =====================================================================
# JURNAL
# =====================================================================
KOLOM_JURNAL = ["id","tanggal_beli","kode","preset","harga_beli","lot","modal","tp_persen","sl_persen",
                "jatuh_tempo","status","tanggal_jual","harga_jual","sebab","skor","stoch_k","stoch_d",
                "rasio_turun_naik","fase_naik","fase_turun","peer_gap","sektor","grup"]

def muat_jurnal():
    if "jurnal" not in st.session_state:
        if os.path.exists(JURNAL_FILE):
            try:
                st.session_state.jurnal = pd.read_csv(JURNAL_FILE).to_dict("records")
            except Exception:
                st.session_state.jurnal = []
        else:
            st.session_state.jurnal = []
    return st.session_state.jurnal

def simpan_jurnal():
    try:
        pd.DataFrame(st.session_state.jurnal, columns=KOLOM_JURNAL).to_csv(JURNAL_FILE, index=False)
    except Exception as e:
        st.warning(f"Gagal menulis {JURNAL_FILE}: {e}")

def bursa_plus(n):
    d = datetime.now(WIB)
    c = 0
    while c < n:
        d += timedelta(days=1)
        if d.weekday() < 5: c += 1
    return d.strftime("%Y-%m-%d")

def tambah_jurnal(r, preset, modal, tp, sl, hold):
    J = muat_jurnal()
    ada = next((x for x in J if x["kode"] == r["SYMBOL"] and x["status"] == "open"), None)
    if ada:                                    # satu saham = satu posisi
        pres = str(ada["preset"]).split("|")
        if preset not in pres:
            ada["preset"] = "|".join(pres + [preset])
            simpan_jurnal()
            return "gabung"
        return "duplikat"
    lot = max(1, int(modal // (r["PRICE"]*100)))
    J.append({
        "id": f"{int(time.time()*1000)}-{r['SYMBOL']}", "tanggal_beli": datetime.now(WIB).strftime("%Y-%m-%d"),
        "kode": r["SYMBOL"], "preset": preset, "harga_beli": round(r["PRICE"], 2), "lot": lot,
        "modal": round(r["PRICE"]*lot*100), "tp_persen": tp, "sl_persen": sl,
        "jatuh_tempo": bursa_plus(hold), "status": "open", "tanggal_jual": "", "harga_jual": "",
        "sebab": "", "skor": round(r["CONF"], 1), "stoch_k": round(r["STOCH_K"], 1),
        "stoch_d": round(r["STOCH_D"], 1),
        "rasio_turun_naik": "" if r["V_dryUp"] is None else round(r["V_dryUp"], 3),
        "fase_naik": r["V_naikVonis"], "fase_turun": r["V_turunVonis"],
        "peer_gap": round(r["PEER_GAP"], 4), "sektor": r["SECTOR"], "grup": r["GROUP"],
    })
    simpan_jurnal()
    return "baru"

def hitung_pnl(t, harga, fee_b, fee_s):
    lembar = int(t["lot"])*100
    modal = float(t["harga_beli"])*lembar*(1+fee_b)
    hasil = float(harga)*lembar*(1-fee_s)
    return hasil-modal, (hasil-modal)/modal

# =====================================================================
# SIDEBAR
# =====================================================================
st.sidebar.markdown("### ⚙️ PARAMETER")

mode_universe = st.sidebar.radio("Universe", ["Semua IDX", "Grup terpantau saja"], index=1,
    help="Semua IDX menarik 800+ emiten — putaran pertama 2-4 menit, lalu di-cache 15 menit.")

preset_nama = st.sidebar.selectbox("Preset", list(PRESETS), index=0)
bobot = dict(PRESETS[preset_nama])
with st.sidebar.expander("Setel bobot manual"):
    for k in bobot:
        bobot[k] = st.slider(k, 0, 50, bobot[k], 1, key=f"b_{k}")

st.sidebar.markdown("---")
amb_likuid = st.sidebar.selectbox("Transaksi harian minimal", [0, 1e9, 2e9, 5e9, 1e10, 2e10],
    index=3, format_func=lambda v: "Tanpa batas" if v == 0 else f"Rp {v/1e9:.0f} miliar")
dasar_likuid = st.sidebar.selectbox("Dasar hitung", ["TURN_MIN20","TURN_MIN60","TURN_MED","TURN_AVG"],
    index=0, format_func=lambda k: {"TURN_MIN20":"Minimum 20 hari","TURN_MIN60":"Minimum 60 hari",
    "TURN_MED":"Median 20 hari","TURN_AVG":"Rata-rata 20 hari (longgar)"}[k])
harga_min = st.sidebar.number_input("Harga minimal", 0, 100000, 50, 50)
k_maks = st.sidebar.slider("Stochastic %K maksimal", 0, 100, 100, 5)

st.sidebar.markdown("**Gerbang keras**")
buang_stoch = st.sidebar.checkbox("Buang JENUH BELI & MELEMAH", True)
gate_naik = st.sidebar.checkbox("Buang NAIK TANPA VOLUME", True)
gate_turun = st.sidebar.checkbox("Buang volume jual besar", True)
wajib_ma = st.sidebar.checkbox("Wajib MA20 > MA50", False)
wajib_obv = st.sidebar.checkbox("Wajib OBV 20 hari naik", False)
dry_maks = st.sidebar.number_input("Rasio turun/naik maksimal", 0.1, 5.0, 2.0, 0.05)

st.sidebar.markdown("---")
st.sidebar.markdown("**Jurnal**")
modal_total = st.sidebar.number_input("Modal total", 0, 10_000_000_000, 30_000_000, 1_000_000)
jml_posisi = st.sidebar.number_input("Jumlah posisi", 1, 50, 15, 1)
tp_pct = st.sidebar.number_input("Take profit %", 0.5, 50.0, 8.0, 0.5)
sl_pct = st.sidebar.number_input("Stop loss %", 0.5, 50.0, 5.0, 0.5)
hold_hari = st.sidebar.number_input("Tahan (hari bursa)", 1, 30, 5, 1)
fee_beli = st.sidebar.number_input("Fee beli %", 0.0, 2.0, 0.15, 0.01)/100
fee_jual = st.sidebar.number_input("Fee jual %", 0.0, 2.0, 0.25, 0.01)/100

if ADA_AUTOREFRESH and st.sidebar.checkbox("Auto refresh 5 menit", False):
    st_autorefresh(interval=300000, key="quantum_sync")

# =====================================================================
# HALAMAN
# =====================================================================
st.markdown('<div class="header-container"><div class="header-title">PREDATOR QUANTUM PRO</div>'
            '<div class="header-sub">SETUP BOARD ENGINE · STOCHASTIC 10,5,5 · VERIFIKASI VOLUME PER FASE</div></div>',
            unsafe_allow_html=True)

brk = (fee_beli+fee_jual)*100
impas = 100*(sl_pct+brk)/((tp_pct-brk)+(sl_pct+brk)) if (tp_pct-brk) > 0 else 100
st.markdown(f"""<div class="warnbox">
<b>Bid/offer, broker summary, dan net foreign tidak ada di sini</b> — ketiganya berlisensi bursa.
Papan ini menyempitkan daftar; konfirmasi akhir di layar sekuritas.<br>
Fee pulang-pergi <b>{brk:.2f}%</b> · TP bersih <b>+{tp_pct-brk:.2f}%</b> ·
SL bersih <b>−{sl_pct+brk:.2f}%</b> · titik impas <b>{impas:.0f}%</b> kemenangan.
</div>""", unsafe_allow_html=True)

makro = ambil_makro()
if makro:
    html = "<div class='macro-strip'>"
    for k, v in makro.items():
        cls = "macro-val-up" if v["chg"] >= 0 else "macro-val-down"
        panah = "▲" if v["chg"] >= 0 else "▼"
        html += (f"<div class='macro-item'><span class='macro-label'>{k}</span>"
                 f"<span class='{cls}'>{v['val']:,.2f} ({panah} {v['chg']:.2f}%)</span></div>")
    st.markdown(html + "</div>", unsafe_allow_html=True)

ph = st.empty()
ph.markdown('<div class="blink">MENARIK DATA & MENGHITUNG METRIK…</div>', unsafe_allow_html=True)

universe, sumber_universe = ambil_universe()
if mode_universe == "Grup terpantau saja":
    universe = sorted(set(FALLBACK_UNIVERSE) & set(universe)) or FALLBACK_UNIVERSE

harga = ambil_harga(tuple(universe))
berita_map, berita_list = ambil_berita()

rows = []
for kode, df in harga.items():
    try:
        m = metrik(kode, df)
        if m: rows.append(m)
    except Exception:
        continue
rows, grup_lead, sekt_lead = hitung_peer_gap(rows)
ph.empty()

lolos = [r for r in rows if
         r[dasar_likuid] >= amb_likuid and
         r["PRICE"] >= harga_min and
         r["STOCH_K"] <= k_maks and
         (not buang_stoch or r["STOCH_SIGNAL"] not in STOCH_BURUK) and
         (not gate_naik or r["V_gateNaik"]) and
         (not gate_turun or r["V_gateTurun"]) and
         (r["V_dryUp"] is None or r["V_dryUp"] <= dry_maks) and
         (not wajib_ma or r["MA_CROSS"]) and
         (not wajib_obv or r["A_obvSlope"] > 0)]
lolos = beri_skor(lolos, bobot, makro)

pulse = "MIXED MARKET"
if grup_lead:
    teratas = sorted(grup_lead.items(), key=lambda x: -x[1][1])[:1]
    if teratas and teratas[0][1][1] > 0.03:
        pulse = f"ROTASI: {teratas[0][0]} (pemimpin {teratas[0][1][0]} {teratas[0][1][1]*100:+.1f}%)"

st.markdown(f"<div style='text-align:center;margin-bottom:10px;color:#00ffcc;font-family:Orbitron;"
            f"letter-spacing:2px;font-size:11px'>📡 {pulse} &nbsp;·&nbsp; {len(rows)} emiten dihitung "
            f"({sumber_universe}) &nbsp;·&nbsp; {len(lolos)} lolos saringan &nbsp;·&nbsp; "
            f"{datetime.now(WIB).strftime('%d %b %Y %H:%M WIB')}</div>", unsafe_allow_html=True)

if not lolos:
    st.error("Tidak ada saham yang lolos. Longgarkan saringan — biasanya ambang likuiditas atau gerbang volume.")
    st.stop()

df_tampil = pd.DataFrame([{
    "SYMBOL": r["SYMBOL"], "CONF": r["CONF"], "PRICE": int(r["PRICE"]), "CHG%": round(r["CHG"]*100, 2),
    "STOCH": f"{r['STOCH_K']:.0f}/{r['STOCH_D']:.0f}", "STOCH_SIGNAL": r["STOCH_SIGNAL"],
    "FASE_NAIK": r["V_naikVonis"], "FASE_TURUN": r["V_turunVonis"],
    "T/N": None if r["V_dryUp"] is None else round(r["V_dryUp"], 2),
    "GAP": round(r["PEER_GAP"]*100, 1), "BASIS": r["PEER_BASIS"],
    "MIN/HARI": round(r["TURN_MIN20"]/1e9, 2), "HARI≥5M": r["HARI_5M"], "PORTO": r["PORTO"],
} for r in lolos])

col_main, col_news = st.columns([3, 1])

with col_main:
    st.markdown("<h3 style='font-family:Orbitron;color:#ff0055;font-size:17px'>📡 KANDIDAT TERSARING</h3>",
                unsafe_allow_html=True)
    st.dataframe(df_tampil, use_container_width=True, hide_index=True, height=380, column_config={
        "CONF": st.column_config.ProgressColumn("SKOR", min_value=0, max_value=100, format="%.1f"),
        "T/N": st.column_config.NumberColumn("TURUN/NAIK", format="%.2fx",
               help="Volume saat turun dibagi volume saat naik. Di bawah 0,70 = barang tidak dilepas."),
        "GAP": st.column_config.NumberColumn("KETINGGALAN", format="%.1fpp"),
        "MIN/HARI": st.column_config.NumberColumn("MIN Rp M", format="%.2f",
               help="Transaksi harian TERKECIL dalam 20 hari, bukan rata-rata."),
        "STOCH_SIGNAL": st.column_config.TextColumn("KONDISI D1"),
    })

    st.markdown("<h3 style='font-family:Orbitron;color:#00ffcc;font-size:17px;margin-top:14px'>"
                "📊 MONITORING 4 TERATAS</h3>", unsafe_allow_html=True)
    for i in range(0, min(4, len(lolos)), 2):
        cols = st.columns(2)
        for j, r in enumerate(lolos[i:i+2]):
            with cols[j]:
                css_st = ("pixel-value-up" if r["STOCH_SCORE"] >= 70 else
                          "pixel-value-neutral" if r["STOCH_SCORE"] >= 36 else "pixel-value-down")
                css_v = "pixel-value-up" if r["V_turunSkor"] >= 75 else "pixel-value-down"
                dry_s = "–" if r["V_dryUp"] is None else f"{r['V_dryUp']:.2f}x"
                st.markdown(f"""<div class="pixel-container">
                  <div class="pixel-metric"><span class="pixel-title">TREND</span>
                    <span class="{'pixel-value-up' if r['MA_CROSS'] else 'pixel-value-down'}">
                    {'BULLISH' if r['MA_CROSS'] else 'BEARISH'}</span></div>
                  <div class="pixel-metric"><span class="pixel-title">STOCH K/D</span>
                    <span class="{css_st}">{r['STOCH_K']:.0f}/{r['STOCH_D']:.0f}</span></div>
                  <div class="pixel-metric"><span class="pixel-title">TURUN/NAIK</span>
                    <span class="{css_v}">{dry_s}</span></div>
                  <div class="pixel-metric"><span class="pixel-title">MIN/HARI</span>
                    <span class="pixel-value-neutral">{r['TURN_MIN20']/1e9:.1f}M</span></div>
                </div>""", unsafe_allow_html=True)
                st.plotly_chart(grafik(r), use_container_width=True)

    st.markdown("<h3 style='font-family:Orbitron;color:#ff0055;font-size:17px;margin-top:20px'>"
                "📝 TESIS</h3>", unsafe_allow_html=True)
    for r in lolos[:5]:
        st.markdown(f"""<div class="thesis-box">
          <div style="display:flex;justify-content:space-between;margin-bottom:5px">
            <span style="color:#ff0055;font-weight:bold;font-size:14px">
              #{r['RANK']} {r['SYMBOL']} <span style="color:#7c8a94;font-size:11px">{r['GROUP']}</span></span>
            <span style="color:#00ffcc;font-family:JetBrains Mono;font-size:10px">
              SKOR {r['CONF']:.1f} · {r['PORTO']}</span></div>
          <div class="thesis-header">ANALISIS:</div>
          <div style="color:#e0e0e0">{bangun_tesis(r, makro, berita_map, tp_pct, sl_pct)}</div>
        </div>""", unsafe_allow_html=True)

with col_news:
    st.markdown("<h3 style='font-family:Orbitron;color:#fff;font-size:17px'>💡 INTEL</h3>",
                unsafe_allow_html=True)
    if berita_list:
        st.markdown('<div class="news-scroll-box">', unsafe_allow_html=True)
        for it in berita_list[:20]:
            q = urllib.parse.quote(it["NEWS"])
            st.markdown(f'<div class="news-box"><div class="news-topic-header">{it["TOPIC"]}</div>'
                        f'<div class="news-text"><a href="https://www.google.com/search?q={q}" '
                        f'target="_blank">{it["NEWS"]}</a></div></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.caption("Feed berita tidak tersedia (feedparser belum terpasang atau RSS gagal dibaca).")

# =====================================================================
# PANEL JURNAL
# =====================================================================
st.markdown("---")
st.markdown("<h3 style='font-family:Orbitron;color:#00ffcc;font-size:18px'>📒 JURNAL</h3>",
            unsafe_allow_html=True)

J = muat_jurnal()
terbuka = [t for t in J if t["status"] == "open"]
ditutup = [t for t in J if t["status"] == "closed"]
modal_per = int(modal_total/max(1, jml_posisi))

m1, m2 = st.columns([1, 3])
mode_papan = m1.radio("Mode papan", ["KONSENSUS", "EKSKLUSIF"], index=0, horizontal=True,
    help="KONSENSUS: tiap preset ambil 3 teratasnya apa adanya, boleh sama. "
         "EKSKLUSIF: draft bergiliran sehingga tiap preset dapat nama berbeda.")
pick_n = m2.slider("Pick per preset", 1, 6, 3, 1)

urutan = peringkat_semua_preset(lolos, makro)
papan = alokasi_papan(urutan, mode_papan, pick_n)
semua_slot = [t for v in papan.values() for t in v]
unik = list(dict.fromkeys(semua_slot))
hitung_dup = Counter(semua_slot)
modal_per_unik = int(modal_total/max(1, len(unik)))

if mode_papan == "KONSENSUS":
    st.markdown("**Mode konsensus** — tiap preset mengambil pick teratasnya apa adanya. "
                "Saham yang dipilih beberapa preset dibeli **sekali**; hasilnya tetap dihitung "
                "untuk setiap preset yang memilihnya.")
else:
    st.markdown("**Mode eksklusif** — draft bergiliran, tiap preset mendapat nama berbeda yang "
                "mewakili selera khasnya. Sebagian pick jadi lebih lemah secara absolut: "
                "kamu menukar potensi untung dengan kemampuan membuktikan preset mana yang benar.")

baris_papan = []
for nama, tics in papan.items():
    b = {"PRESET": nama}
    for i in range(pick_n):
        t = tics[i] if i < len(tics) else None
        b[f"PICK {i+1}"] = ("–" if not t else
                            (f"{t} ×{hitung_dup[t]}" if hitung_dup[t] > 1 else t))
    baris_papan.append(b)
st.dataframe(pd.DataFrame(baris_papan), use_container_width=True, hide_index=True)

pesan = f"{len(semua_slot)} slot → **{len(unik)} saham unik** → Rp {modal_per_unik:,} per posisi".replace(",", ".")
if mode_papan == "EKSKLUSIF" and len(unik) < len(PRESETS)*pick_n:
    pesan += (f" · kolam kandidat hanya {len(lolos)} saham, tidak cukup untuk "
              f"{len(PRESETS)*pick_n} slot berbeda — longgarkan saringan bila ingin penuh")
st.caption(pesan)

c1, c2, c3 = st.columns([3, 2, 3])
with c1:
    tambahan = st.multiselect(
        "Tambah manual (semua kandidat lolos saringan)",
        [r["SYMBOL"] for r in lolos], default=[],
        help="Daftar ini mengikuti saringan di sidebar, bukan preset. "
             "Untuk saham di luar saringan, pakai kolom di bawah.")
    luar = st.multiselect("Tambah di luar saringan (seluruh emiten terhitung)",
                          sorted(r["SYMBOL"] for r in rows), default=[])
with c2:
    st.metric("Modal per posisi", f"Rp {modal_per_unik:,}".replace(",", "."))
    st.caption(f"{len(terbuka)} terbuka · {len(ditutup)} tertutup")
with c3:
    b1, b2 = st.columns(2)
    if b1.button(f"➕ Masukkan papan ({len(unik)} posisi)", use_container_width=True):
        n_baru = n_gab = 0
        for nama, tics in papan.items():
            for t in tics:
                r = next((x for x in lolos if x["SYMBOL"] == t), None)
                if r:
                    hasil = tambah_jurnal(r, nama, modal_per_unik, tp_pct, sl_pct, hold_hari)
                    n_baru += (hasil == "baru"); n_gab += (hasil == "gabung")
        st.success(f"{len(semua_slot)} slot disaring jadi {n_baru} posisi baru "
                   f"({n_gab} preset digabung ke posisi yang sudah ada).")
        st.rerun()
    if b2.button("➕ Masukkan manual", use_container_width=True):
        n = 0
        for t in tambahan + luar:
            r = next((x for x in lolos if x["SYMBOL"] == t), None) or \
                next((x for x in rows if x["SYMBOL"] == t), None)
            if r:
                r.setdefault("CONF", 50.0); r.setdefault("PEER_GAP", 0.0)
                n += (tambah_jurnal(r, preset_nama, int(modal_total/max(1, jml_posisi)),
                                    tp_pct, sl_pct, hold_hari) == "baru")
        st.success(f"{n} posisi ditambahkan atas nama preset {preset_nama}.")
        st.rerun()

d1, d2 = st.columns(2)
if d1.button("🔄 Bagi rata modal ke posisi terbuka", use_container_width=True):
    if terbuka:
        per = int(modal_total/len(terbuka))
        for t in terbuka:
            t["lot"] = max(1, int(per // (float(t["harga_beli"])*100)))
            t["modal"] = round(float(t["harga_beli"])*t["lot"]*100)
        simpan_jurnal(); st.rerun()
if d2.button("🗑️ Kosongkan seluruh jurnal", use_container_width=True):
    if st.session_state.get("konfirm_hapus"):
        st.session_state.jurnal = []; simpan_jurnal()
        st.session_state.konfirm_hapus = False; st.rerun()
    else:
        st.session_state.konfirm_hapus = True
        st.warning("Klik sekali lagi untuk menghapus SELURUH jurnal.")

if terbuka:
    harga_kini = {r["SYMBOL"]: r["PRICE"] for r in rows}
    baris = []
    for t in terbuka:
        px = harga_kini.get(t["kode"], float(t["harga_beli"]))
        net, pct = hitung_pnl(t, px, fee_beli, fee_jual)
        baris.append({"kode": t["kode"], "preset": t["preset"], "beli": float(t["harga_beli"]),
                      "lot": int(t["lot"]), "modal": int(t["modal"]),
                      "TP": int(round(float(t["harga_beli"])*(1+float(t["tp_persen"])/100))),
                      "SL": int(round(float(t["harga_beli"])*(1-float(t["sl_persen"])/100))),
                      "jatuh_tempo": t["jatuh_tempo"], "terakhir": int(px),
                      "P/L": int(net), "P/L%": round(pct*100, 2)})
    st.dataframe(pd.DataFrame(baris), use_container_width=True, hide_index=True)

    with st.expander("Tutup posisi"):
        k1, k2, k3, k4 = st.columns([2, 2, 2, 1])
        pilih = k1.selectbox("Posisi", [t["kode"] for t in terbuka])
        px_jual = k2.number_input("Harga jual", 0.0, 1e9,
                                  float(harga_kini.get(pilih, 0)) or 0.0, 1.0)
        sebab = k3.selectbox("Sebab", ["TP", "SL", "Waktu"])
        if k4.button("Tutup"):
            t = next(x for x in terbuka if x["kode"] == pilih)
            t.update(status="closed", harga_jual=px_jual, sebab=sebab,
                     tanggal_jual=datetime.now(WIB).strftime("%Y-%m-%d"))
            simpan_jurnal(); st.rerun()

if ditutup:
    st.markdown("**Rekap per preset** — satu transaksi dihitung untuk setiap preset yang memilihnya")
    per_preset = defaultdict(list)
    for t in ditutup:
        net, pct = hitung_pnl(t, float(t["harga_jual"]), fee_beli, fee_jual)
        for nm in str(t["preset"]).split("|"):
            per_preset[nm].append((net, pct))
    rekap = []
    for nm, arr in per_preset.items():
        pcts = [p for _, p in arr]
        rekap.append({"preset": nm, "n": len(arr),
                      "menang%": round(100*sum(1 for p in pcts if p > 0)/len(pcts), 0),
                      "rata2%": round(float(np.mean(pcts))*100, 2),
                      "terbaik%": round(max(pcts)*100, 1), "terburuk%": round(min(pcts)*100, 1),
                      "P/L": int(sum(n for n, _ in arr)),
                      "keyakinan": "terlalu dini" if len(arr) < 10 else
                                   "masih tipis" if len(arr) < 20 else
                                   "mulai terbaca" if len(arr) < 30 else "cukup dinilai"})
    st.dataframe(pd.DataFrame(rekap).sort_values("rata2%", ascending=False),
                 use_container_width=True, hide_index=True)
    st.caption(f"Titik impas pada TP {tp_pct}% / SL {sl_pct}% dengan fee {brk:.2f}% adalah "
               f"{impas:.0f}% kemenangan. Preset dengan menang% di bawah itu sedang merugi.")

if J:
    st.download_button("⬇️ Unduh jurnal CSV",
        pd.DataFrame(J, columns=KOLOM_JURNAL).to_csv(index=False).encode(),
        f"jurnal-{datetime.now(WIB).strftime('%Y%m%d')}.csv", "text/csv")

st.caption(f"Data Yahoo Finance, tertunda ±10-15 menit · jurnal tersimpan di {JURNAL_FILE} · "
           "bukan rekomendasi investasi")
