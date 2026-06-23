"""
Dashboard Screening Saham IHSG Multi-Parameter
================================================================
Kombinasi Strategi: Swing (Stoch 10,5,5) + Momentum Breakout 
Filter Mutlak: Likuiditas, Market Cap > 600B, Price > 60
"""

import time
import math
import datetime as dt
import urllib.request
import urllib.parse
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf
import feedparser

# ----------------------------------------------------------------------
# KONFIGURASI HALAMAN
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="Screener Saham IHSG Terintegrasi",
    layout="wide",
)

# ----------------------------------------------------------------------
# UNIVERSE SAHAM DEFAULT (Fallback)
# ----------------------------------------------------------------------
DEFAULT_UNIVERSE = [
    "BBCA.JK", "BBRI.JK", "BMRI.JK", "BBNI.JK", "BRIS.JK",
    "TLKM.JK", "ASII.JK", "UNVR.JK", "ICBP.JK", "INDF.JK",
    "ANTM.JK", "INCO.JK", "MDKA.JK", "ADRO.JK", "PTBA.JK",
    "ITMG.JK", "PGAS.JK", "PGEO.JK", "SMGR.JK", "INTP.JK", 
    "CPIN.JK", "JPFA.JK", "TOWR.JK", "TBIG.JK", "EXCL.JK", 
    "ISAT.JK", "KLBF.JK", "SIDO.JK", "MIKA.JK", "HEAL.JK",
    "BRPT.JK", "TPIA.JK", "AMMN.JK", "MEDC.JK", "ACES.JK", 
    "AMRT.JK", "MAPI.JK", "ERAA.JK", "BUMI.JK", "PWON.JK", 
    "CTRA.JK", "BSDE.JK", "SMRA.JK",
]

SECTOR_MAP = {
    "BBCA.JK": "Keuangan", "BBRI.JK": "Keuangan", "BMRI.JK": "Keuangan",
    "BBNI.JK": "Keuangan", "BRIS.JK": "Keuangan",
    "TLKM.JK": "Infrastruktur/Telko", "TOWR.JK": "Infrastruktur/Telko",
    "TBIG.JK": "Infrastruktur/Telko", "EXCL.JK": "Infrastruktur/Telko",
    "ISAT.JK": "Infrastruktur/Telko",
    "ASII.JK": "Industri", "UNVR.JK": "Consumer Non-Primer",
    "ICBP.JK": "Consumer Primer", "INDF.JK": "Consumer Primer",
    "ANTM.JK": "Energi/Mineral", "INCO.JK": "Energi/Mineral",
    "MDKA.JK": "Energi/Mineral", "ADRO.JK": "Energi/Mineral",
    "PTBA.JK": "Energi/Mineral", "ITMG.JK": "Energi/Mineral",
    "PGAS.JK": "Energi/Mineral", "PGEO.JK": "Energi/Mineral",
    "AMMN.JK": "Energi/Mineral", "MEDC.JK": "Energi/Mineral",
    "BUMI.JK": "Energi/Mineral",
    "SMGR.JK": "Industri", "INTP.JK": "Industri",
    "CPIN.JK": "Consumer Primer", "JPFA.JK": "Consumer Primer",
    "KLBF.JK": "Kesehatan", "SIDO.JK": "Kesehatan",
    "MIKA.JK": "Kesehatan", "HEAL.JK": "Kesehatan",
    "BRPT.JK": "Industri", "TPIA.JK": "Industri",
    "ACES.JK": "Consumer Non-Primer", "AMRT.JK": "Consumer Primer",
    "MAPI.JK": "Consumer Non-Primer", "ERAA.JK": "Consumer Non-Primer",
    "PWON.JK": "Properti", "CTRA.JK": "Properti",
    "BSDE.JK": "Properti", "SMRA.JK": "Properti",
}

DEFAULT_WEIGHTS = {
    "likuiditas": 0.15,
    "teknikal": 0.20,
    "momentum": 0.30,
    "smart_money": 0.25,
    "fundamental": 0.05,
    "katalis": 0.05,
}

# ----------------------------------------------------------------------
# DATA FETCHING
# ----------------------------------------------------------------------
@st.cache_data(ttl=60 * 60 * 24 * 7, show_spinner=False)
def fetch_all_idx_tickers():
    url = "https://id.wikipedia.org/wiki/Daftar_perusahaan_yang_tercatat_di_Bursa_Efek_Indonesia"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        html = urllib.request.urlopen(req).read().decode('utf-8')
        text_only = re.sub(r'<[^>]+>', ' ', html)
        matches = re.findall(r'BEI\s*:\s*([A-Z]{4})', text_only)
        if matches:
            tickers = sorted(list(set([f"{m}.JK" for m in matches])))
            if len(tickers) > 500:
                return tickers
    except Exception:
        pass
    return DEFAULT_UNIVERSE

@st.cache_data(ttl=60 * 30, show_spinner=False)
def fetch_history(ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    try:
        df = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=True)
        if df is None or df.empty:
            return pd.DataFrame()
        return df.dropna()
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def fetch_fundamentals(ticker: str) -> dict:
    out = {
        "trailingPE": np.nan, "priceToBook": np.nan,
        "earningsQuarterlyGrowth": np.nan, "revenueGrowth": np.nan,
        "marketCap": np.nan,
    }
    try:
        info = yf.Ticker(ticker).get_info()
        for k in out.keys():
            if k in info and info[k] is not None:
                out[k] = info[k]
    except Exception:
        pass
    return out

@st.cache_data(ttl=60 * 60, show_spinner=False)
def fetch_news(query: str, max_items: int = 6):
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=id&gl=ID&ceid=ID:id"
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    try:
        feed = feedparser.parse(url, agent=user_agent)
        items = []
        for entry in feed.entries[:max_items]:
            items.append({
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "source": entry.get("source", {}).get("title", "") if entry.get("source") else "",
            })
        return items
    except Exception:
        return []

# ----------------------------------------------------------------------
# INDIKATOR TEKNIKAL & SMART MONEY PROXY
# ----------------------------------------------------------------------
def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["MA5"] = df["Close"].rolling(5).mean()
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()
    df["MA150"] = df["Close"].rolling(150).mean()
    df["MA200"] = df["Close"].rolling(200).mean()
    df["VolMA20"] = df["Volume"].rolling(20).mean()
    
    # Kebutuhan Breakout
    df["Prev_Volume"] = df["Volume"].shift(1)
    df["Prev_Close"] = df["Close"].shift(1)
    df["Price_Change"] = (df["Close"] - df["Prev_Close"]) / df["Prev_Close"].replace(0, np.nan)

    # RSI
    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    rs = gain.rolling(14).mean() / loss.rolling(14).mean().replace(0, np.nan)
    df["RSI14"] = 100 - (100 / (1 + rs))
    
    # Stochastic (10, 5, 5)
    low_10 = df["Low"].rolling(window=10).min()
    high_10 = df["High"].rolling(window=10).max()
    fast_k = 100 * ((df["Close"] - low_10) / (high_10 - low_10).replace(0, np.nan))
    df["Stoch_K"] = fast_k.rolling(window=5).mean()
    df["Stoch_D"] = df["Stoch_K"].rolling(window=5).mean()

    # OBV & CMF
    df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
    df['OBV_MA20'] = df['OBV'].rolling(20).mean()
    mfm = ((df['Close'] - df['Low']) - (df['High'] - df['Close'])) / (df['High'] - df['Low']).replace(0, 0.0001)
    mfv = mfm * df['Volume']
    df['CMF'] = mfv.rolling(20).sum() / df['Volume'].rolling(20).sum()

    df["High52w"] = df["Close"].rolling(252, min_periods=50).max()
    df["Low52w"] = df["Close"].rolling(252, min_periods=50).min()
    return df

def ma200_slope_positive(df: pd.DataFrame, lookback: int = 22) -> bool:
    s = df["MA200"].dropna()
    if len(s) < lookback + 1: return False
    return s.iloc[-1] > s.iloc[-lookback - 1]

# ----------------------------------------------------------------------
# SCORING ENGINE
# ----------------------------------------------------------------------
def score_liquidity(df: pd.DataFrame, avg_value_threshold_idr: float = 5e9) -> float:
    recent = df.tail(20)
    avg_value = (recent["Close"] * recent["Volume"]).mean()
    ratio = avg_value / avg_value_threshold_idr
    return float(np.clip(50 * math.log2(max(ratio, 0.05)) + 50, 0, 100))

def score_trend_template(df: pd.DataFrame) -> tuple[float, dict]:
    if df.empty or len(df) < 210:
        return 0.0, {"note": "Data historis tidak memadai untuk evaluasi Trend Template."}
    last = df.iloc[-1]
    checks = {
        "Harga di atas MA50": last["Close"] > last["MA50"],
        "Harga di atas MA150": last["Close"] > last["MA150"],
        "Harga di atas MA200": last["Close"] > last["MA200"],
        "MA50 di atas MA150": last["MA50"] > last["MA150"],
        "MA150 di atas MA200": last["MA150"] > last["MA200"],
        "MA200 terkonfirmasi menanjak": ma200_slope_positive(df),
        "Harga 25% di atas Low 52-Minggu": ((last["Close"] >= last["Low52w"] * 1.25) if not math.isnan(last["Low52w"]) else False),
        "Harga dekat area High 52-Minggu": ((last["Close"] >= last["High52w"] * 0.75) if not math.isnan(last["High52w"]) else False),
    }
    return float(100 * sum(checks.values()) / len(checks)), checks

def score_momentum(df: pd.DataFrame, benchmark_df: pd.DataFrame) -> tuple[float, dict]:
    if df.empty or len(df) < 60: return 0.0, {}
    last = df.iloc[-1]
    
    # 1. Stochastic (10, 5, 5) Logic
    stoch_k = last.get("Stoch_K", np.nan)
    stoch_d = last.get("Stoch_D", np.nan)
    stoch_status = "Tidak Valid"
    stoch_score = 50.0
    
    if not math.isnan(stoch_k) and not math.isnan(stoch_d):
        if stoch_k < 50 and stoch_d < 50:
            if stoch_k >= stoch_d and (stoch_k - stoch_d) <= 8:
                stoch_score = 100.0
                stoch_status = f"Golden Cross di bawah 50 (K:{stoch_k:.1f}, D:{stoch_d:.1f})"
            elif stoch_k < stoch_d and (stoch_d - stoch_k) <= 5:
                stoch_score = 80.0
                stoch_status = f"Menuju Golden Cross (K:{stoch_k:.1f}, D:{stoch_d:.1f})"
            else:
                stoch_score = 60.0
                stoch_status = f"Oversold, belum crossing (K:{stoch_k:.1f}, D:{stoch_d:.1f})"
        elif stoch_k >= 50 and stoch_k > stoch_d:
            stoch_score = 50.0
            stoch_status = f"Uptrend di atas 50 (K:{stoch_k:.1f}, D:{stoch_d:.1f})"
        else:
            stoch_score = 30.0
            stoch_status = f"Overbought / Death Cross (K:{stoch_k:.1f}, D:{stoch_d:.1f})"

    # 2. Breakout Parameter (dari gambar referensi)
    breakout_score = 0
    b_checks = []
    vol = last.get("Volume", 0)
    prev_vol = last.get("Prev_Volume", 0)
    vol_ma20 = last.get("VolMA20", 0)
    price = last.get("Close", 0)
    ma5 = last.get("MA5", 0)
    p_change = last.get("Price_Change", 0)

    if prev_vol > 0 and vol >= 1.5 * prev_vol:
        breakout_score += 25
        b_checks.append("Vol > 1.5x Kemarin")
    if vol_ma20 > 0 and vol >= 1.2 * vol_ma20:
        breakout_score += 25
        b_checks.append("Vol > 1.2x MA20")
    if price >= ma5:
        breakout_score += 25
        b_checks.append("Harga > MA5")
    if p_change >= 0.02:
        breakout_score += 25
        b_checks.append("Kenaikan > 2%")

    if breakout_score == 100:
        stoch_status += " [Terdeteksi Breakout Valid]"

    # Komposit Momentum (Stoch 50%, Breakout 50%)
    sub = (0.50 * stoch_score) + (0.50 * breakout_score)
    
    return float(np.clip(sub, 0, 100)), {
        "stoch_status": stoch_status,
        "breakout_checks": ", ".join(b_checks) if b_checks else "Belum Breakout"
    }

def score_smart_money_proxy(df: pd.DataFrame) -> float:
    if df.empty or len(df) < 20: return 50.0
    last = df.iloc[-1]
    recent = df.tail(20)
    score = 50.0
    
    cmf_val = last.get('CMF', 0)
    if not math.isnan(cmf_val):
        score += (np.clip((cmf_val + 0.2) * 250, 0, 100) - 50) * 0.40
        
    obv_val, obv_ma = last.get('OBV', 0), last.get('OBV_MA20', 0)
    if not math.isnan(obv_val) and not math.isnan(obv_ma) and obv_ma != 0:
        obv_ratio = obv_val / obv_ma
        if obv_ratio > 1.05: score += 15
        elif obv_ratio > 1.0: score += 5
        elif obv_ratio < 0.95: score -= 15
        elif obv_ratio < 1.0: score -= 5

    acc_days, dist_days = 0, 0
    for i in range(1, len(recent)):
        if recent['Close'].iloc[i] > recent['Close'].iloc[i-1] and recent['Volume'].iloc[i] > recent['Volume'].iloc[i-1]:
            acc_days += 1
        elif recent['Close'].iloc[i] < recent['Close'].iloc[i-1] and recent['Volume'].iloc[i] > recent['Volume'].iloc[i-1]:
            dist_days += 1
            
    if acc_days > dist_days: score += 15
    elif dist_days > acc_days: score -= 15
        
    return float(np.clip(score, 0, 100))

def score_fundamental(fund: dict) -> float:
    score = 50.0
    eg, rg = fund.get("earningsQuarterlyGrowth", np.nan), fund.get("revenueGrowth", np.nan)
    g_scores = []
    if isinstance(eg, (int, float)) and not math.isnan(eg): g_scores.append(np.clip(50 + eg * 100, 0, 100))
    if isinstance(rg, (int, float)) and not math.isnan(rg): g_scores.append(np.clip(50 + rg * 150, 0, 100))
    if g_scores: score = np.mean(g_scores)
    return float(np.clip(score, 0, 100))

def composite_score(sub_scores: dict, weights: dict) -> float:
    return float(sum(sub_scores.get(k, 0) * w for k, w in weights.items()))

# ----------------------------------------------------------------------
# PIPELINE UTAMA
# ----------------------------------------------------------------------
def analyze_ticker(ticker: str, benchmark_df: pd.DataFrame, weights: dict, sector_bias: dict, min_avg_value: float):
    df = fetch_history(ticker, period="1y", interval="1d")
    if df.empty or len(df) < 60: return None

    # --- HARD FILTER 1: LIKUIDITAS VALUE TRANSAKSI ---
    recent_20 = df.tail(20)
    avg_tx_value = (recent_20["Close"] * recent_20["Volume"]).mean()
    if avg_tx_value < min_avg_value:
        return None

    # --- HARD FILTER 2: HARGA SAHAM > 60 ---
    last_price = df["Close"].iloc[-1]
    if last_price <= 60:
        return None

    fund = fetch_fundamentals(ticker)
    
    # --- HARD FILTER 3: MARKET CAP > 600 Miliar ---
    mc = fund.get("marketCap")
    if mc and not math.isnan(mc) and mc > 0:
        if mc <= 600e9: 
            return None

    df = add_indicators(df)
    sector = SECTOR_MAP.get(ticker, "Lainnya")

    s_liq = score_liquidity(df, min_avg_value)
    s_trend, t_checks = score_trend_template(df)
    
    s_mom_result = score_momentum(df, benchmark_df)
    s_mom = s_mom_result[0]
    stoch_status = s_mom_result[1]["stoch_status"]
    breakout_status = s_mom_result[1]["breakout_checks"]
    
    s_smart_money = score_smart_money_proxy(df)
    s_fund = score_fundamental(fund)
    s_cat = float(sector_bias.get(sector, 50))

    scores_dict = {"likuiditas": s_liq, "teknikal": s_trend, "momentum": s_mom, "smart_money": s_smart_money, "fundamental": s_fund, "katalis": s_cat}
    total = composite_score(scores_dict, weights)
    
    return {
        "Ticker": ticker.replace(".JK", ""), "Sektor": sector,
        "Harga": round(float(last_price), 0), "Skor Total": round(total, 1),
        "Likuiditas": round(s_liq, 1), "Teknikal": round(s_trend, 1),
        "Momentum": round(s_mom, 1), "Smart Money": round(s_smart_money, 1),
        "Fundamental": round(s_fund, 1), "Katalis/Makro": round(s_cat, 1),
        "Info Tambahan": f"{stoch_status} | {breakout_status}",
        "_df": df, "_trend_checks": t_checks,
    }

@st.cache_data(ttl=60 * 30, show_spinner=False)
def run_screening(tickers: tuple, weights: dict, sector_bias: dict, min_avg_value: float):
    raw_benchmark = fetch_history("^JKSE", period="1y", interval="1d")
    benchmark_df = add_indicators(raw_benchmark) if not raw_benchmark.empty else pd.DataFrame()
    
    results = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = [ex.submit(analyze_ticker, t, benchmark_df, weights, sector_bias, min_avg_value) for t in tickers]
        for fut in as_completed(futures):
            if (r := fut.result()) is not None: results.append(r)
    return results, benchmark_df

# ----------------------------------------------------------------------
# UI — SIDEBAR
# ----------------------------------------------------------------------
st.sidebar.title("Konfigurasi Parameter")

ALL_TICKERS = fetch_all_idx_tickers()
st.sidebar.markdown("**Daftar Universe Saham**")
universe_input = st.sidebar.text_area(
    "Format: KODE.JK",
    value=", ".join(ALL_TICKERS),
    height=150,
)
tickers = tuple(sorted(set(t.strip().upper() for t in universe_input.split(",") if t.strip())))

st.sidebar.markdown("---")
st.sidebar.markdown("**Bobot Analisis Khusus**")
w_liq = st.sidebar.slider("Likuiditas & Struktur Pasar", 0, 100, int(DEFAULT_WEIGHTS["likuiditas"] * 100))
w_tren = st.sidebar.slider("Struktur Tren Harga", 0, 100, int(DEFAULT_WEIGHTS["teknikal"] * 100))
w_mom = st.sidebar.slider("Momentum Breakout & Stoch", 0, 100, int(DEFAULT_WEIGHTS["momentum"] * 100))
w_sm = st.sidebar.slider("Jejak Smart Money (VPA/CMF/OBV)", 0, 100, int(DEFAULT_WEIGHTS["smart_money"] * 100))
w_fund = st.sidebar.slider("Pertumbuhan Fundamental", 0, 100, int(DEFAULT_WEIGHTS["fundamental"] * 100))
w_kat = st.sidebar.slider("Sentimen Makro Sektoral", 0, 100, int(DEFAULT_WEIGHTS["katalis"] * 100))

w_sum = max(w_liq + w_tren + w_mom + w_sm + w_fund + w_kat, 1)
weights = {"likuiditas": w_liq/w_sum, "teknikal": w_tren/w_sum, "momentum": w_mom/w_sum, "smart_money": w_sm/w_sum, "fundamental": w_fund/w_sum, "katalis": w_kat/w_sum}

st.sidebar.markdown("---")
n_final = st.sidebar.slider("Batas Tampilan Saham Tersaring", 3, 10, 5)

# Diubah nilai awalnya agar lebih dekat ke kriteria gambar Anda (100 Miliar default, dapat disesuaikan)
min_avg_value = st.sidebar.number_input("Batas Rata-Rata Transaksi (Miliar Rp)", min_value=0.5, value=10.0, step=0.5) * 1e9

run_btn = st.sidebar.button("Mulai Proses Kalkulasi", type="primary", use_container_width=True)

# ----------------------------------------------------------------------
# UI — HEADER
# ----------------------------------------------------------------------
st.title("Sistem Skoring Saham Terintegrasi")
st.caption("Fokus: Swing to Breakout (Stoch 10,5,5 + Kriteria Volume Reversal)")

if not run_btn and "screening_results" not in st.session_state:
    st.info("Pilih konfigurasi dan jalankan proses untuk menampilkan data.")
    st.stop()

# ----------------------------------------------------------------------
# EKSEKUSI
# ----------------------------------------------------------------------
if run_btn:
    with st.spinner(f"Melakukan komputasi terhadap {len(tickers)} data emiten..."):
        # Penyesuaian bias sektor statis untuk meminimalkan input manual
        sector_bias = {k: 50 for k in SECTOR_MAP.values()}
        results, benchmark_df = run_screening(tickers, weights, sector_bias, min_avg_value)
        st.session_state["screening_results"], st.session_state["benchmark_df"], st.session_state["last_run"] = results, benchmark_df, dt.datetime.now()

results, benchmark_df, last_run = st.session_state.get("screening_results", []), st.session_state.get("benchmark_df", pd.DataFrame()), st.session_state.get("last_run")

if not results:
    st.warning("Tidak ada saham yang lolos Hard Filter (Market Cap > 600B, Price > 60, dan Likuiditas minimum). Coba turunkan Batas Rata-Rata Transaksi.")
    st.stop()

if last_run: st.caption(f"Waktu Proses Terakhir: {last_run.strftime('%d %b %Y, %H:%M:%S')}")

# ----------------------------------------------------------------------
# OUTPUT
# ----------------------------------------------------------------------
# errors='ignore' dimasukkan agar terhindar dari KeyError jika cache menyimpang
df_results = pd.DataFrame(results).drop(columns=["_df", "_trend_checks", "Info Tambahan"], errors='ignore').sort_values("Skor Total", ascending=False)

st.subheader(f"Tinjauan Global: {len(df_results)} Emiten Terkualifikasi")
st.dataframe(df_results.style.background_gradient(subset=["Skor Total"], cmap="Greens"), use_container_width=True, hide_index=True)

st.markdown("---")
st.header(f"Fokus Utama: {n_final} Peringkat Tertinggi")
results_map = {r["Ticker"]: r for r in results}

import plotly.graph_objects as go

for _, row in df_results.head(n_final).iterrows():
    r = results_map[row["Ticker"]]
    with st.container(border=True):
        c1, c2 = st.columns([1, 2])
        with c1:
            st.subheader(f"{row['Ticker']} — {row['Sektor']}")
            st.metric("Skor Keseluruhan", f"{row['Skor Total']:.1f} / 100")
            st.metric("Level Harga", f"Rp {row['Harga']:,.0f}")
            st.markdown(f"**Status:** {r.get('Info Tambahan', 'Analisis Selesai')}")
            
            with st.expander("Indikator Trend Template"):
                for k, v in r.get("_trend_checks", {}).items():
                    if k != "note":
                        status = "[Valid]" if v else "[Gagal]"
                        st.write(f"{status} {k}")
                    else:
                        st.write(v)
        with c2:
            fig = go.Figure()
            p_df = r["_df"].tail(120) # Diperpendek menjadi 120 agar grafik lebih jelas terlihat polanya
            fig.add_trace(go.Candlestick(x=p_df.index, open=p_df["Open"], high=p_df["High"], low=p_df["Low"], close=p_df["Close"], name="Harga"))
            for ma, col in [("MA20", "orange"), ("MA50", "blue"), ("MA150", "purple"), ("MA200", "red")]:
                if ma in p_df.columns: fig.add_trace(go.Scatter(x=p_df.index, y=p_df[ma], name=ma, line=dict(width=1, color=col)))
            fig.update_layout(height=350, margin=dict(l=10, r=10, t=30, b=10), xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
