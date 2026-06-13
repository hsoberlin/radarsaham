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
import plotly.graph_objects as go
import feedparser

st.set_page_config(
    page_title="Dashboard Screening Saham IHSG",
    layout="wide",
)

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
    "TLKM.JK": "Infrastruktur", "TOWR.JK": "Infrastruktur",
    "TBIG.JK": "Infrastruktur", "EXCL.JK": "Infrastruktur",
    "ISAT.JK": "Infrastruktur",
    "ASII.JK": "Industri", "UNVR.JK": "Konsumer Non-Primer",
    "ICBP.JK": "Konsumer Primer", "INDF.JK": "Konsumer Primer",
    "ANTM.JK": "Energi dan Mineral", "INCO.JK": "Energi dan Mineral",
    "MDKA.JK": "Energi dan Mineral", "ADRO.JK": "Energi dan Mineral",
    "PTBA.JK": "Energi dan Mineral", "ITMG.JK": "Energi dan Mineral",
    "PGAS.JK": "Energi dan Mineral", "PGEO.JK": "Energi dan Mineral",
    "AMMN.JK": "Energi dan Mineral", "MEDC.JK": "Energi dan Mineral",
    "BUMI.JK": "Energi dan Mineral",
    "SMGR.JK": "Industri", "INTP.JK": "Industri",
    "CPIN.JK": "Konsumer Primer", "JPFA.JK": "Konsumer Primer",
    "KLBF.JK": "Kesehatan", "SIDO.JK": "Kesehatan",
    "MIKA.JK": "Kesehatan", "HEAL.JK": "Kesehatan",
    "BRPT.JK": "Industri", "TPIA.JK": "Industri",
    "ACES.JK": "Konsumer Non-Primer", "AMRT.JK": "Konsumer Primer",
    "MAPI.JK": "Konsumer Non-Primer", "ERAA.JK": "Konsumer Non-Primer",
    "PWON.JK": "Properti", "CTRA.JK": "Properti",
    "BSDE.JK": "Properti", "SMRA.JK": "Properti",
}

DEFAULT_WEIGHTS = {
    "likuiditas": 0.20,
    "teknikal": 0.35,
    "momentum": 0.20,
    "fundamental": 0.15,
    "katalis": 0.10,
}

DEFAULT_SECTOR_BIAS = {
    "Keuangan": 70,
    "Properti": 35,
    "Energi dan Mineral": 55,
    "Infrastruktur": 55,
    "Industri": 55,
    "Konsumer Primer": 55,
    "Konsumer Non-Primer": 60,
    "Kesehatan": 50,
    "Lainnya": 50,
}


@st.cache_data(ttl=60 * 60 * 24 * 7, show_spinner=False)
def fetch_all_idx_tickers():
    url = "[id.wikipedia.org](https://id.wikipedia.org/wiki/Daftar_perusahaan_yang_tercatat_di_Bursa_Efek_Indonesia)"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8")
        text_only = re.sub(r"<[^>]+>", " ", html)
        matches = re.findall(r"BEI\s*:\s*([A-Z]{4})", text_only)
        if matches:
            tickers = sorted(list(set([f"{m}.JK" for m in matches])))
            if len(tickers) > 500:
                return tickers
    except Exception:
        pass
    return DEFAULT_UNIVERSE


@st.cache_data(ttl=60 * 60 * 24, show_spinner=False)
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
        "trailingPE": np.nan,
        "priceToBook": np.nan,
        "earningsQuarterlyGrowth": np.nan,
        "revenueGrowth": np.nan,
        "marketCap": np.nan,
        "shortName": ticker,
    }
    try:
        info = yf.Ticker(ticker).get_info()
        for k in out:
            if k in info and info[k] is not None:
                out[k] = info[k]
    except Exception:
        pass
    return out


@st.cache_data(ttl=60 * 60, show_spinner=False)
def fetch_news(query: str, max_items: int = 5):
    encoded_query = urllib.parse.quote(query)
    url = f"[news.google.com](https://news.google.com/rss/search?q={encoded_query}&hl=id&gl=ID&ceid=ID:id)"
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
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


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()
    df["MA150"] = df["Close"].rolling(150).mean()
    df["MA200"] = df["Close"].rolling(200).mean()
    df["VolMA20"] = df["Volume"].rolling(20).mean()
    df["VolMA50"] = df["Volume"].rolling(50).mean()
    df["High52w"] = df["Close"].rolling(252, min_periods=50).max()
    df["Low52w"] = df["Close"].rolling(252, min_periods=50).min()

    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["RSI14"] = 100 - (100 / (1 + rs))

    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACDSignal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["RangePct"] = (df["High"] - df["Low"]) / df["Close"].replace(0, np.nan)
    return df


def ma200_slope_positive(df: pd.DataFrame, lookback: int = 22) -> bool:
    s = df["MA200"].dropna()
    if len(s) < lookback + 1:
        return False
    return s.iloc[-1] > s.iloc[-lookback - 1]


def classify_stage(df: pd.DataFrame) -> str:
    if df.empty or len(df) < 210:
        return "Data Tidak Cukup"

    last = df.iloc[-1]
    price = last["Close"]
    ma50 = last["MA50"]
    ma150 = last["MA150"]
    ma200 = last["MA200"]

    if any(math.isnan(x) for x in [price, ma50, ma150, ma200]):
        return "Data Tidak Cukup"

    ma200_up = ma200_slope_positive(df)
    if price > ma50 > ma150 > ma200 and ma200_up:
        return "Stage 2"
    if price < ma200 and not ma200_up:
        return "Stage 4"
    if abs(price - ma200) / ma200 < 0.08:
        return "Stage 1"
    return "Stage 3"


def score_liquidity(df: pd.DataFrame, avg_value_threshold_idr: float = 5e9) -> float:
    if df.empty or len(df) < 20:
        return 0.0
    recent = df.tail(20)
    avg_value = (recent["Close"] * recent["Volume"]).mean()
    if avg_value <= 0 or math.isnan(avg_value):
        return 0.0
    ratio = avg_value / avg_value_threshold_idr
    score = 50 * math.log2(max(ratio, 0.05)) + 50
    return float(np.clip(score, 0, 100))


def score_trend_template(df: pd.DataFrame) -> tuple[float, dict]:
    if df.empty or len(df) < 210:
        return 0.0, {"catatan": "Data historis kurang dari 210 hari."}

    last = df.iloc[-1]
    checks = {
        "Harga di atas MA50": last["Close"] > last["MA50"],
        "Harga di atas MA150": last["Close"] > last["MA150"],
        "Harga di atas MA200": last["Close"] > last["MA200"],
        "MA50 di atas MA150": last["MA50"] > last["MA150"],
        "MA150 di atas MA200": last["MA150"] > last["MA200"],
        "MA200 menanjak": ma200_slope_positive(df),
        "Harga minimal 25 persen di atas low 52 minggu": (
            last["Close"] >= last["Low52w"] * 1.25 if not math.isnan(last["Low52w"]) else False
        ),
        "Harga dekat high 52 minggu": (
            last["Close"] >= last["High52w"] * 0.75 if not math.isnan(last["High52w"]) else False
        ),
    }
    score = 100 * sum(checks.values()) / len(checks)
    return float(score), checks


def score_momentum(df: pd.DataFrame, benchmark_df: pd.DataFrame) -> float:
    if df.empty or len(df) < 70:
        return 0.0

    lb = min(63, len(df) - 1)
    try:
        ret_stock = df["Close"].iloc[-1] / df["Close"].iloc[-lb - 1] - 1
        ret_bench = benchmark_df["Close"].iloc[-1] / benchmark_df["Close"].iloc[-lb - 1] - 1 if not benchmark_df.empty else 0
        rs = ret_stock - ret_bench
        rs_score = np.clip(50 + rs * 200, 0, 100)
    except Exception:
        rs_score = 50

    last = df.iloc[-1]
    if not math.isnan(last.get("VolMA20", np.nan)) and last["VolMA20"] > 0:
        vol_score = np.clip(((last["Volume"] / last["VolMA20"]) - 0.5) * 60, 0, 100)
    else:
        vol_score = 50

    rsi = last.get("RSI14", np.nan)
    if math.isnan(rsi):
        rsi_score = 50
    elif 50 <= rsi <= 75:
        rsi_score = 100
    elif 75 < rsi <= 85:
        rsi_score = 70
    elif rsi > 85:
        rsi_score = 30
    elif 35 <= rsi < 50:
        rsi_score = 60
    else:
        rsi_score = 30

    score = 0.5 * rs_score + 0.25 * vol_score + 0.25 * rsi_score
    return float(np.clip(score, 0, 100))


def score_fundamental(fund: dict) -> float:
    score = 50.0
    eg = fund.get("earningsQuarterlyGrowth", np.nan)
    rg = fund.get("revenueGrowth", np.nan)
    pe = fund.get("trailingPE", np.nan)
    pb = fund.get("priceToBook", np.nan)

    growth_scores = []
    if isinstance(eg, (int, float)) and not math.isnan(eg):
        growth_scores.append(np.clip(50 + eg * 100, 0, 100))
    if isinstance(rg, (int, float)) and not math.isnan(rg):
        growth_scores.append(np.clip(50 + rg * 150, 0, 100))

    if growth_scores:
        score = float(np.mean(growth_scores))

    penalty = 0
    if isinstance(pe, (int, float)) and not math.isnan(pe) and pe > 40:
        penalty += 10
    if isinstance(pb, (int, float)) and not math.isnan(pb) and pb > 8:
        penalty += 10

    return float(np.clip(score - penalty, 0, 100))


def composite_score(sub_scores: dict, weights: dict) -> float:
    return float(sum(sub_scores.get(k, 0) * w for k, w in weights.items()))


def confidence_score(df: pd.DataFrame, fund: dict) -> str:
    score = 0
    if not df.empty and len(df) >= 210:
        score += 1
    if not math.isnan(fund.get("trailingPE", np.nan)):
        score += 1
    if not math.isnan(fund.get("priceToBook", np.nan)):
        score += 1
    if not math.isnan(fund.get("earningsQuarterlyGrowth", np.nan)) or not math.isnan(fund.get("revenueGrowth", np.nan)):
        score += 1

    if score >= 4:
        return "Tinggi"
    if score >= 2:
        return "Sedang"
    return "Rendah"


def hard_filter_liquidity(df: pd.DataFrame, min_avg_value: float) -> bool:
    if df.empty or len(df) < 20:
        return False
    avg_value = (df.tail(20)["Close"] * df.tail(20)["Volume"]).mean()
    return bool(avg_value >= min_avg_value)


def hard_filter_trend(df: pd.DataFrame) -> bool:
    stage = classify_stage(df)
    return stage == "Stage 2"


def hard_filter_fundamental(fund: dict) -> bool:
    eg = fund.get("earningsQuarterlyGrowth", np.nan)
    rg = fund.get("revenueGrowth", np.nan)

    checks = []
    if isinstance(eg, (int, float)) and not math.isnan(eg):
        checks.append(eg > -0.15)
    if isinstance(rg, (int, float)) and not math.isnan(rg):
        checks.append(rg > -0.10)

    if not checks:
        return True
    return all(checks)


def nearest_supports(df: pd.DataFrame) -> dict:
    last = df.iloc[-1]
    price = float(last["Close"])
    ma20 = float(last["MA20"]) if not math.isnan(last["MA20"]) else price
    ma50 = float(last["MA50"]) if not math.isnan(last["MA50"]) else price * 0.95
    ma150 = float(last["MA150"]) if not math.isnan(last["MA150"]) else price * 0.85

    recent = df.tail(60)
    swing_low = float(recent["Low"].min()) if not recent.empty else ma50
    pivot = float(recent["High"].rolling(20).max().dropna().iloc[-5:].min()) if len(recent) >= 25 else price

    return {
        "price": round(price, 0),
        "pivot": round(pivot, 0),
        "ma20": round(ma20, 0),
        "ma50": round(ma50, 0),
        "swing_low": round(swing_low, 0),
        "invalidation": round(min(ma150 * 0.97, swing_low * 0.98), 0),
    }


def build_dca_plan(df: pd.DataFrame) -> pd.DataFrame:
    lv = nearest_supports(df)
    return pd.DataFrame([
        {"Tahap Entry": "Entry 1", "Alokasi": "30-40%", "Area Harga": lv["price"], "Basis": "Konfirmasi harga aktif atau breakout awal"},
        {"Tahap Entry": "Entry 2", "Alokasi": "30-35%", "Area Harga": min(lv["ma20"], lv["pivot"]), "Basis": "Pullback ringan ke area support terdekat"},
        {"Tahap Entry": "Entry 3", "Alokasi": "20-30%", "Area Harga": lv["ma50"], "Basis": "Retest support menengah"},
        {"Tahap Entry": "Batal Setup", "Alokasi": "-", "Area Harga": lv["invalidation"], "Basis": "Invalidation struktur trend"},
    ])


def summarize_setup(row: dict) -> str:
    reasons = []
    if row["Likuiditas"] >= 70:
        reasons.append("likuiditas kuat")
    if row["Teknikal"] >= 75:
        reasons.append("trend template valid")
    if row["Momentum"] >= 70:
        reasons.append("momentum relatif baik")
    if row["Fundamental"] >= 60:
        reasons.append("fundamental mendukung")
    if row["Katalis"] >= 60:
        reasons.append("sektor mendapat dukungan konteks makro")

    if not reasons:
        return "Tidak ada faktor dominan yang sangat kuat."
    return ", ".join(reasons).capitalize() + "."


def summarize_risk(row: dict) -> str:
    risks = []
    if row["Momentum"] < 55:
        risks.append("momentum belum kuat")
    if row["Fundamental"] < 50:
        risks.append("dukungan fundamental terbatas")
    if row["Katalis"] < 50:
        risks.append("konteks sektor kurang mendukung")
    if row["Confidence"] == "Rendah":
        risks.append("kualitas data belum lengkap")

    if not risks:
        return "Risiko utama tetap pada perubahan trend dan breakout gagal."
    return ", ".join(risks).capitalize() + "."


def analyze_ticker(ticker: str, benchmark_df: pd.DataFrame, weights: dict, sector_bias: dict, min_avg_value: float):
    raw_df = fetch_history(ticker, period="1y", interval="1d")
    if raw_df.empty or len(raw_df) < 60:
        return None

    df = add_indicators(raw_df)
    fund = fetch_fundamentals(ticker)
    sector = SECTOR_MAP.get(ticker, "Lainnya")
    stage = classify_stage(df)

    passed_liq = hard_filter_liquidity(df, min_avg_value)
    passed_trend = hard_filter_trend(df)
    passed_fund = hard_filter_fundamental(fund)

    s_liq = score_liquidity(df, min_avg_value)
    s_trend, t_checks = score_trend_template(df)
    s_mom = score_momentum(df, benchmark_df)
    s_fund = score_fundamental(fund)
    s_cat = float(sector_bias.get(sector, 50))
    conf = confidence_score(df, fund)

    total = composite_score(
        {
            "likuiditas": s_liq,
            "teknikal": s_trend,
            "momentum": s_mom,
            "fundamental": s_fund,
            "katalis": s_cat,
        },
        weights,
    )

    return {
        "Ticker": ticker.replace(".JK", ""),
        "Nama": fund.get("shortName", ticker.replace(".JK", "")),
        "Sektor": sector,
        "Harga": round(float(df.iloc[-1]["Close"]), 0),
        "Stage": stage,
        "Lolos Likuiditas": passed_liq,
        "Lolos Trend": passed_trend,
        "Lolos Fundamental": passed_fund,
        "Skor Total": round(total, 1),
        "Likuiditas": round(s_liq, 1),
        "Teknikal": round(s_trend, 1),
        "Momentum": round(s_mom, 1),
        "Fundamental": round(s_fund, 1),
        "Katalis": round(s_cat, 1),
        "Confidence": conf,
        "_df": df,
        "_fund": fund,
        "_trend_checks": t_checks,
    }


@st.cache_data(ttl=60 * 30, show_spinner=False)
def run_screening(tickers: tuple, weights: dict, sector_bias: dict, min_avg_value: float):
    benchmark_df = add_indicators(fetch_history("^JKSE", period="1y", interval="1d"))
    results = []

    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = [ex.submit(analyze_ticker, t, benchmark_df, weights, sector_bias, min_avg_value) for t in tickers]
        for fut in as_completed(futures):
            try:
                r = fut.result()
                if r is not None:
                    results.append(r)
            except Exception:
                continue

    return results, benchmark_df


st.title("Dashboard Screening Saham IHSG")
st.caption("Pendekatan multi-parameter untuk seleksi saham dan rencana entry bertahap.")

with st.sidebar:
    st.subheader("Konfigurasi")

    universe_mode = st.selectbox(
        "Mode Universe",
        ["Semua Saham Terdeteksi", "Universe Default"],
        index=1,
    )

    if universe_mode == "Semua Saham Terdeteksi":
        all_tickers = fetch_all_idx_tickers()
    else:
        all_tickers = DEFAULT_UNIVERSE

    universe_text = st.text_area(
        "Daftar Ticker",
        value=", ".join(all_tickers),
        height=150,
    )
    tickers = tuple(sorted(set(t.strip().upper() for t in universe_text.split(",") if t.strip())))

    st.subheader("Profil Strategi")
    strategy = st.selectbox(
        "Preset Bobot",
        ["Balanced", "Momentum Agresif", "Konservatif"],
        index=0,
    )

    if strategy == "Momentum Agresif":
        weights = {
            "likuiditas": 0.20,
            "teknikal": 0.40,
            "momentum": 0.25,
            "fundamental": 0.10,
            "katalis": 0.05,
        }
    elif strategy == "Konservatif":
        weights = {
            "likuiditas": 0.20,
            "teknikal": 0.30,
            "momentum": 0.15,
            "fundamental": 0.25,
            "katalis": 0.10,
        }
    else:
        weights = DEFAULT_WEIGHTS.copy()

    min_avg_value = st.number_input(
        "Minimal Rata-rata Transaksi Harian 20 Hari (Rp miliar)",
        min_value=0.5,
        value=5.0,
        step=0.5,
    ) * 1e9

    n_final = st.slider("Jumlah Kandidat Final", 3, 10, 5)

    st.subheader("Bias Sektor")
    sector_bias = {}
    for sec in sorted(set(SECTOR_MAP.values()) | {"Lainnya"}):
        sector_bias[sec] = st.slider(sec, 0, 100, DEFAULT_SECTOR_BIAS.get(sec, 50), key=f"sector_{sec}")

    run_btn = st.button("Jalankan Screening", use_container_width=True)

if not run_btn and "screening_results_v2" not in st.session_state:
    st.info("Atur parameter pada panel kiri lalu jalankan screening.")
    st.stop()

if run_btn:
    with st.spinner(f"Memproses {len(tickers)} saham..."):
        results, benchmark_df = run_screening(tickers, weights, sector_bias, min_avg_value)
        st.session_state["screening_results_v2"] = results
        st.session_state["benchmark_df_v2"] = benchmark_df
        st.session_state["last_run_v2"] = dt.datetime.now()

results = st.session_state.get("screening_results_v2", [])
benchmark_df = st.session_state.get("benchmark_df_v2", pd.DataFrame())
last_run = st.session_state.get("last_run_v2")

if not results:
    st.error("Tidak ada hasil screening yang valid.")
    st.stop()

if last_run:
    st.caption(f"Pembaruan terakhir: {last_run.strftime('%d %b %Y %H:%M:%S')}")

df_all = pd.DataFrame(results)

n_universe = len(df_all)
n_liq = int(df_all["Lolos Likuiditas"].sum())
df_stage = df_all[df_all["Lolos Likuiditas"]]
n_trend = int(df_stage["Lolos Trend"].sum()) if not df_stage.empty else 0
df_fund = df_all[(df_all["Lolos Likuiditas"]) & (df_all["Lolos Trend"])]
n_fund = int(df_fund["Lolos Fundamental"].sum()) if not df_fund.empty else 0

df_final = df_all[
    (df_all["Lolos Likuiditas"]) &
    (df_all["Lolos Trend"]) &
    (df_all["Lolos Fundamental"])
].copy()

df_final = df_final.sort_values("Skor Total", ascending=False)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Jumlah Saham Diproses", f"{n_universe}")
col2.metric("Lolos Likuiditas", f"{n_liq}")
col3.metric("Lolos Trend Template", f"{n_trend}")
col4.metric("Lolos Fundamental", f"{n_fund}")

st.markdown("---")

st.subheader("Hasil Seleksi Bertahap")
funnel_table = pd.DataFrame({
    "Tahap": [
        "Universe Awal",
        "Filter Likuiditas",
        "Filter Trend Template",
        "Filter Fundamental",
    ],
    "Jumlah Saham": [
        n_universe,
        n_liq,
        n_trend,
        n_fund,
    ]
})
st.dataframe(funnel_table, use_container_width=True, hide_index=True)

st.markdown("---")

st.subheader("Kandidat Teratas")
if df_final.empty:
    st.warning("Tidak ada saham yang lolos seluruh tahapan hard filter.")
    st.stop()

display_cols = [
    "Ticker", "Nama", "Sektor", "Harga", "Stage", "Skor Total",
    "Likuiditas", "Teknikal", "Momentum", "Fundamental", "Katalis", "Confidence"
]
st.dataframe(
    df_final[display_cols].head(50),
    use_container_width=True,
    hide_index=True,
)

st.markdown("---")

top_candidates = df_final.head(n_final)
results_map = {r["Ticker"]: r for r in results}

st.subheader("Detail Kandidat Final")

for _, row in top_candidates.iterrows():
    r = results_map[row["Ticker"]]

    st.markdown(f"### {row['Ticker']} - {row['Nama']}")
    info1, info2, info3, info4 = st.columns(4)
    info1.metric("Sektor", row["Sektor"])
    info2.metric("Harga Terakhir", f"Rp {row['Harga']:,.0f}")
    info3.metric("Stage", row["Stage"])
    info4.metric("Skor Total", f"{row['Skor Total']:.1f}")

    st.write(f"**Alasan utama:** {summarize_setup(r)}")
    st.write(f"**Risiko utama:** {summarize_risk(r)}")

    score_table = pd.DataFrame({
        "Kategori": ["Likuiditas", "Teknikal", "Momentum", "Fundamental", "Katalis", "Confidence"],
        "Nilai": [
            r["Likuiditas"], r["Teknikal"], r["Momentum"],
            r["Fundamental"], r["Katalis"], r["Confidence"]
        ]
    })
    st.dataframe(score_table, use_container_width=True, hide_index=True)

    df_plot = r["_df"].tail(180)
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df_plot.index,
        open=df_plot["Open"],
        high=df_plot["High"],
        low=df_plot["Low"],
        close=df_plot["Close"],
        name="Harga"
    ))
    for ma, color in [("MA20", "orange"), ("MA50", "blue"), ("MA150", "purple"), ("MA200", "red")]:
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot[ma], name=ma, line=dict(width=1, color=color)))
    fig.update_layout(
        height=360,
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis_rangeslider_visible=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.write("**Checklist Trend Template**")
    trend_checks = r["_trend_checks"]
    trend_rows = [{"Parameter": k, "Status": "Ya" if v else "Tidak"} for k, v in trend_checks.items()]
    st.dataframe(pd.DataFrame(trend_rows), use_container_width=True, hide_index=True)

    st.write("**Rencana Entry Bertahap**")
    st.dataframe(build_dca_plan(r["_df"]), use_container_width=True, hide_index=True)

    st.write("**Berita Terkait**")
    news_items = fetch_news(f"{row['Ticker']} saham", 3)
    if not news_items:
        st.write("Belum ada berita yang berhasil dimuat.")
    else:
        news_df = pd.DataFrame(news_items)
        news_df = news_df.rename(columns={
            "title": "Judul",
            "source": "Sumber",
            "published": "Waktu",
            "link": "Tautan",
        })
        st.dataframe(news_df[["Judul", "Sumber", "Waktu", "Tautan"]], use_container_width=True, hide_index=True)

    st.markdown("---")

st.subheader("Konteks Pasar")
if not benchmark_df.empty:
    p_df = benchmark_df.tail(180)
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=p_df.index, y=p_df["Close"], name="IHSG", line=dict(color="navy", width=2)))
    fig2.update_layout(
        height=320,
        margin=dict(l=10, r=10, t=20, b=10),
    )
    st.plotly_chart(fig2, use_container_width=True)

macro_news = fetch_news("IHSG BI Rate ekonomi Indonesia", 5)
st.write("**Berita Makro Terkini**")
if not macro_news:
    st.write("Belum ada berita makro yang berhasil dimuat.")
else:
    macro_df = pd.DataFrame(macro_news).rename(columns={
        "title": "Judul",
        "source": "Sumber",
        "published": "Waktu",
        "link": "Tautan",
    })
    st.dataframe(macro_df[["Judul", "Sumber", "Waktu", "Tautan"]], use_container_width=True, hide_index=True)
