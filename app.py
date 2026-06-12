"""
Dashboard Screening Saham IHSG — Multi-Parameter Swing Trading
================================================================
Mengambil data harga via yfinance (Yahoo Finance) dan berita via RSS,
menghitung skor komposit berbobot (Stage Analysis / Trend Template /
Momentum / Fundamental / Katalis Makro), lalu menampilkan 3-5 saham
terbaik beserta rencana entry bertahap (DCA / scaling-in).

Cara jalan lokal:
    pip install -r requirements.txt
    streamlit run app.py

Deploy ke Streamlit Community Cloud:
    1. Push folder ini ke repo GitHub (app.py, requirements.txt, .streamlit/config.toml)
    2. Buka share.streamlit.io -> New app -> pilih repo -> main file: app.py
"""

import time
import math
import datetime as dt
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import feedparser

# ----------------------------------------------------------------------
# KONFIGURASI HALAMAN
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="Screener Saham IHSG — Multi-Parameter",
    page_icon="📈",
    layout="wide",
)

# ----------------------------------------------------------------------
# UNIVERSE SAHAM (bisa ditambah/dikurangi sesuai kebutuhan)
# Kode ticker yfinance untuk BEI = KODE.JK
# ----------------------------------------------------------------------
DEFAULT_UNIVERSE = [
    "BBCA.JK", "BBRI.JK", "BMRI.JK", "BBNI.JK", "BRIS.JK",
    "TLKM.JK", "ASII.JK", "UNVR.JK", "ICBP.JK", "INDF.JK",
    "ANTM.JK", "INCO.JK", "MDKA.JK", "ADRO.JK", "PTBA.JK",
    "ITMG.JK", "PGAS.JK", "PGEO.JK",
    "SMGR.JK", "INTP.JK", "CPIN.JK", "JPFA.JK",
    "TOWR.JK", "TBIG.JK", "EXCL.JK", "ISAT.JK",
    "KLBF.JK", "SIDO.JK", "MIKA.JK", "HEAL.JK",
    "BRPT.JK", "TPIA.JK", "AMMN.JK", "MEDC.JK",
    "ACES.JK", "AMRT.JK", "MAPI.JK", "ERAA.JK",
    "BUMI.JK", "PWON.JK", "CTRA.JK", "BSDE.JK", "SMRA.JK",
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

# ----------------------------------------------------------------------
# BOBOT PARAMETER (sesuai laporan: total 100%)
# ----------------------------------------------------------------------
DEFAULT_WEIGHTS = {
    "likuiditas": 0.20,
    "teknikal": 0.35,
    "momentum": 0.20,
    "fundamental": 0.15,
    "katalis": 0.10,
}

# ----------------------------------------------------------------------
# DATA FETCHING (cached)
# ----------------------------------------------------------------------
@st.cache_data(ttl=60 * 30, show_spinner=False)
def fetch_history(ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    try:
        df = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=True)
        if df is None or df.empty:
            return pd.DataFrame()
        df = df.dropna()
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def fetch_fundamentals(ticker: str) -> dict:
    """Ambil info fundamental dasar via yfinance (best-effort, banyak field bisa None)."""
    out = {
        "trailingPE": np.nan,
        "priceToBook": np.nan,
        "earningsQuarterlyGrowth": np.nan,
        "revenueGrowth": np.nan,
        "marketCap": np.nan,
        "shortName": ticker,
        "floatShares": np.nan,
        "sharesOutstanding": np.nan,
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
    """Ambil berita terbaru via Google News RSS (gratis, tanpa API key)."""
    url = f"https://news.google.com/rss/search?q={query}&hl=id&gl=ID&ceid=ID:id"
    try:
        feed = feedparser.parse(url)
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
# INDIKATOR TEKNIKAL
# ----------------------------------------------------------------------
def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()
    df["MA150"] = df["Close"].rolling(150).mean()
    df["MA200"] = df["Close"].rolling(200).mean()
    df["VolMA20"] = df["Volume"].rolling(20).mean()
    df["VolMA50"] = df["Volume"].rolling(50).mean()

    # RSI 14
    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["RSI14"] = 100 - (100 / (1 + rs))

    # MACD
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_hist"] = df["MACD"] - df["MACD_signal"]

    # 52-week high/low
    df["High52w"] = df["Close"].rolling(252, min_periods=50).max()
    df["Low52w"] = df["Close"].rolling(252, min_periods=50).min()

    return df


def ma200_slope_positive(df: pd.DataFrame, lookback: int = 22) -> bool:
    s = df["MA200"].dropna()
    if len(s) < lookback + 1:
        return False
    return s.iloc[-1] > s.iloc[-lookback - 1]


# ----------------------------------------------------------------------
# SCORING ENGINE
# ----------------------------------------------------------------------
def score_liquidity(df: pd.DataFrame, avg_value_threshold_idr: float = 5e9) -> float:
    """Skor 0-100 berdasarkan rata-rata nilai transaksi 20 hari terakhir."""
    if df.empty or len(df) < 20:
        return 0.0
    recent = df.tail(20)
    avg_value = (recent["Close"] * recent["Volume"]).mean()
    if avg_value <= 0 or math.isnan(avg_value):
        return 0.0
    # skala log terhadap threshold -> 100 jika >= 4x threshold
    ratio = avg_value / avg_value_threshold_idr
    score = 50 * math.log2(max(ratio, 0.05)) + 50
    return float(np.clip(score, 0, 100))


def score_trend_template(df: pd.DataFrame) -> tuple[float, dict]:
    """Skor 0-100 berdasarkan kriteria Trend Template (Minervini/Weinstein)."""
    if df.empty or len(df) < 210:
        return 0.0, {"note": "Data historis < 210 hari, Trend Template tidak dapat dihitung penuh"}

    last = df.iloc[-1]
    checks = {
        "Harga > MA50": last["Close"] > last["MA50"],
        "Harga > MA150": last["Close"] > last["MA150"],
        "Harga > MA200": last["Close"] > last["MA200"],
        "MA50 > MA150": last["MA50"] > last["MA150"],
        "MA150 > MA200": last["MA150"] > last["MA200"],
        "MA200 menanjak (>1 bulan)": ma200_slope_positive(df),
        "Harga >= 25% di atas Low 52w": (
            (last["Close"] >= last["Low52w"] * 1.25) if not math.isnan(last["Low52w"]) else False
        ),
        "Harga dalam jarak wajar dari High 52w (<=25%)": (
            (last["Close"] >= last["High52w"] * 0.75) if not math.isnan(last["High52w"]) else False
        ),
    }
    score = 100 * sum(checks.values()) / len(checks)
    return float(score), checks


def score_momentum(df: pd.DataFrame, benchmark_df: pd.DataFrame) -> float:
    """Skor 0-100: Relative Strength vs IHSG, volume breakout, RSI/MACD."""
    if df.empty or len(df) < 60:
        return 0.0

    sub = 0.0

    # Relative strength 3 bulan (~63 hari trading) vs benchmark
    lb = min(63, len(df) - 1)
    try:
        ret_stock = df["Close"].iloc[-1] / df["Close"].iloc[-lb - 1] - 1
        if not benchmark_df.empty and len(benchmark_df) > lb:
            ret_bench = benchmark_df["Close"].iloc[-1] / benchmark_df["Close"].iloc[-lb - 1] - 1
        else:
            ret_bench = 0
        rs = ret_stock - ret_bench
        rs_score = np.clip(50 + rs * 200, 0, 100)  # tiap 1% outperform ~+2 poin
    except Exception:
        rs_score = 50
    sub += 0.5 * rs_score

    # Volume vs rata-rata 20 hari (hari terakhir)
    last = df.iloc[-1]
    if not math.isnan(last.get("VolMA20", np.nan)) and last["VolMA20"] > 0:
        vol_ratio = last["Volume"] / last["VolMA20"]
        vol_score = np.clip((vol_ratio - 0.5) * 60, 0, 100)
    else:
        vol_score = 50
    sub += 0.25 * vol_score

    # RSI: ideal 50-75, penalti jika >85 (overbought ekstrem) atau <30
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
    sub += 0.25 * rsi_score

    return float(np.clip(sub, 0, 100))


def score_fundamental(fund: dict) -> float:
    """Skor 0-100 berdasarkan pertumbuhan laba/revenue & valuasi (best-effort)."""
    score = 50.0  # netral default jika data tidak tersedia

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
        score = np.mean(growth_scores)

    # penalti valuasi ekstrem (sangat kasar, hanya indikatif)
    penalty = 0
    if isinstance(pe, (int, float)) and not math.isnan(pe) and pe > 40:
        penalty += 10
    if isinstance(pb, (int, float)) and not math.isnan(pb) and pb > 8:
        penalty += 10

    return float(np.clip(score - penalty, 0, 100))


def score_catalyst_macro(sector: str, sector_bias: dict) -> float:
    """Skor 0-100 berdasarkan preferensi sektor sesuai konteks makro yang diinput user."""
    return float(sector_bias.get(sector, 50))


def composite_score(sub_scores: dict, weights: dict) -> float:
    total = 0.0
    for k, w in weights.items():
        total += sub_scores.get(k, 0) * w
    return float(total)


# ----------------------------------------------------------------------
# RENCANA ENTRY BERTAHAP (DCA / SCALING-IN)
# ----------------------------------------------------------------------
def build_dca_plan(df: pd.DataFrame) -> pd.DataFrame:
    last = df.iloc[-1]
    price = float(last["Close"])
    ma20 = float(last["MA20"]) if not math.isnan(last["MA20"]) else price
    ma50 = float(last["MA50"]) if not math.isnan(last["MA50"]) else price * 0.95
    ma150 = float(last["MA150"]) if not math.isnan(last["MA150"]) else price * 0.85

    # invalidation point: di bawah MA150 (dengan margin kecil)
    invalidation = ma150 * 0.97

    plan = pd.DataFrame([
        {
            "Tahap": "Entry 1 (awal)",
            "Alokasi": "30-40%",
            "Area Harga (acuan)": round(price, 0),
            "Basis": "Harga saat ini / konfirmasi breakout dengan volume",
        },
        {
            "Tahap": "Entry 2 (penambahan)",
            "Alokasi": "30-35%",
            "Area Harga (acuan)": round(ma20, 0),
            "Basis": "Pullback ke MA20",
        },
        {
            "Tahap": "Entry 3 (cadangan)",
            "Alokasi": "20-30%",
            "Area Harga (acuan)": round(ma50, 0),
            "Basis": "Pullback ke MA50",
        },
        {
            "Tahap": "Invalidation (batal rencana)",
            "Alokasi": "-",
            "Area Harga (acuan)": round(invalidation, 0),
            "Basis": "Di bawah MA150 — struktur Stage 2 dianggap rusak",
        },
    ])
    return plan


# ----------------------------------------------------------------------
# PIPELINE UTAMA: HITUNG SKOR UNTUK SELURUH UNIVERSE
# ----------------------------------------------------------------------
def analyze_ticker(ticker: str, benchmark_df: pd.DataFrame, weights: dict,
                    sector_bias: dict, min_avg_value: float) -> dict | None:
    df = fetch_history(ticker, period="1y", interval="1d")
    if df.empty or len(df) < 60:
        return None

    df = add_indicators(df)
    fund = fetch_fundamentals(ticker)

    s_liq = score_liquidity(df, avg_value_threshold_idr=min_avg_value)
    s_trend, trend_checks = score_trend_template(df)
    s_mom = score_momentum(df, benchmark_df)
    s_fund = score_fundamental(fund)
    sector = SECTOR_MAP.get(ticker, "Lainnya")
    s_cat = score_catalyst_macro(sector, sector_bias)

    sub_scores = {
        "likuiditas": s_liq,
        "teknikal": s_trend,
        "momentum": s_mom,
        "fundamental": s_fund,
        "katalis": s_cat,
    }
    total = composite_score(sub_scores, weights)

    last = df.iloc[-1]
    return {
        "Ticker": ticker.replace(".JK", ""),
        "Sektor": sector,
        "Harga": round(float(last["Close"]), 0),
        "Skor Total": round(total, 1),
        "Likuiditas": round(s_liq, 1),
        "Teknikal": round(s_trend, 1),
        "Momentum": round(s_mom, 1),
        "Fundamental": round(s_fund, 1),
        "Katalis/Makro": round(s_cat, 1),
        "_df": df,
        "_fund": fund,
        "_trend_checks": trend_checks,
    }


@st.cache_data(ttl=60 * 30, show_spinner=False)
def run_screening(tickers: tuple, weights: dict, sector_bias: dict, min_avg_value: float):
    benchmark_df = fetch_history("^JKSE", period="1y", interval="1d")
    benchmark_df = add_indicators(benchmark_df) if not benchmark_df.empty else benchmark_df

    results = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {
            ex.submit(analyze_ticker, t, benchmark_df, weights, sector_bias, min_avg_value): t
            for t in tickers
        }
        for fut in as_completed(futures):
            r = fut.result()
            if r is not None:
                results.append(r)
    return results, benchmark_df


# ----------------------------------------------------------------------
# UI — SIDEBAR
# ----------------------------------------------------------------------
st.sidebar.title("⚙️ Konfigurasi Screener")

st.sidebar.markdown("**Universe Saham**")
universe_input = st.sidebar.text_area(
    "Daftar ticker (pisahkan dengan koma, format BEI: KODE.JK)",
    value=", ".join(DEFAULT_UNIVERSE),
    height=120,
)
tickers = tuple(sorted(set(t.strip().upper() for t in universe_input.split(",") if t.strip())))

st.sidebar.markdown("---")
st.sidebar.markdown("**Bobot Parameter (%)**")
w_liq = st.sidebar.slider("Likuiditas & Struktur Pasar", 0, 100, int(DEFAULT_WEIGHTS["likuiditas"] * 100))
w_tren = st.sidebar.slider("Tren & Trend Template", 0, 100, int(DEFAULT_WEIGHTS["teknikal"] * 100))
w_mom = st.sidebar.slider("Momentum & Volume", 0, 100, int(DEFAULT_WEIGHTS["momentum"] * 100))
w_fund = st.sidebar.slider("Fundamental", 0, 100, int(DEFAULT_WEIGHTS["fundamental"] * 100))
w_kat = st.sidebar.slider("Katalis / Makro Sektor", 0, 100, int(DEFAULT_WEIGHTS["katalis"] * 100))

w_sum = w_liq + w_tren + w_mom + w_fund + w_kat
if w_sum == 0:
    w_sum = 1
weights = {
    "likuiditas": w_liq / w_sum,
    "teknikal": w_tren / w_sum,
    "momentum": w_mom / w_sum,
    "fundamental": w_fund / w_sum,
    "katalis": w_kat / w_sum,
}
st.sidebar.caption(f"Total input: {w_sum}% → dinormalisasi otomatis menjadi 100%.")

st.sidebar.markdown("---")
st.sidebar.markdown("**Bias Sektor (Konteks Makro)**")
st.sidebar.caption("Atur sektor mana yang sedang diuntungkan/dirugikan kondisi makro saat ini. 50 = netral.")

all_sectors = sorted(set(SECTOR_MAP.values()) | {"Lainnya"})
sector_bias = {}
default_bias = {
    "Keuangan": 70, "Properti": 35, "Energi/Mineral": 55,
    "Infrastruktur/Telko": 55, "Industri": 55, "Consumer Primer": 55,
    "Consumer Non-Primer": 60, "Kesehatan": 50, "Lainnya": 50,
}
with st.sidebar.expander("Atur bias per sektor"):
    for sec in all_sectors:
        sector_bias[sec] = st.slider(sec, 0, 100, default_bias.get(sec, 50), key=f"bias_{sec}")

st.sidebar.markdown("---")
n_final = st.sidebar.slider("Jumlah saham terbaik ditampilkan", 3, 5, 5)
min_avg_value_b = st.sidebar.number_input(
    "Ambang minimum rata-rata nilai transaksi 20 hari (miliar Rp)",
    min_value=0.5, max_value=100.0, value=5.0, step=0.5,
)
min_avg_value = min_avg_value_b * 1e9

st.sidebar.markdown("---")
run_btn = st.sidebar.button("🔄 Jalankan Screening", type="primary", use_container_width=True)


# ----------------------------------------------------------------------
# UI — HEADER
# ----------------------------------------------------------------------
st.title("📈 Dashboard Screening Saham IHSG — Multi-Parameter Swing Trading")
st.caption(
    "Data harga & fundamental: Yahoo Finance (yfinance). Berita: Google News RSS. "
    "Skor dihitung berdasarkan kerangka Trend Template / Stage Analysis / Momentum / "
    "Fundamental / Katalis Makro sesuai bobot yang dapat diatur di sidebar."
)

st.warning(
    "⚠️ **Disclaimer**: Dashboard ini untuk tujuan edukasi, bukan rekomendasi investasi. "
    "Skor bersifat heuristik dan dapat keliru. Selalu lakukan verifikasi mandiri (DYOR) "
    "dan pertimbangkan konsultasi dengan penasihat berlisensi OJK.",
    icon="⚠️",
)

if not run_btn and "screening_results" not in st.session_state:
    st.info("Atur konfigurasi di sidebar, lalu klik **Jalankan Screening** untuk memulai.")
    st.stop()

# ----------------------------------------------------------------------
# JALANKAN SCREENING
# ----------------------------------------------------------------------
if run_btn:
    with st.spinner("Mengambil data dan menghitung skor untuk seluruh universe saham..."):
        results, benchmark_df = run_screening(tickers, weights, sector_bias, min_avg_value)
        st.session_state["screening_results"] = results
        st.session_state["benchmark_df"] = benchmark_df
        st.session_state["last_run"] = dt.datetime.now()

results = st.session_state.get("screening_results", [])
benchmark_df = st.session_state.get("benchmark_df", pd.DataFrame())
last_run = st.session_state.get("last_run")

if last_run:
    st.caption(f"Terakhir diperbarui: {last_run.strftime('%d %b %Y, %H:%M:%S')} (cache 30 menit)")

if not results:
    st.error("Tidak ada data yang berhasil diambil. Periksa koneksi atau daftar ticker.")
    st.stop()

# ----------------------------------------------------------------------
# TABEL SKOR LENGKAP
# ----------------------------------------------------------------------
df_results = pd.DataFrame(results).drop(columns=["_df", "_fund", "_trend_checks"])
df_results = df_results.sort_values("Skor Total", ascending=False).reset_index(drop=True)

st.subheader("📊 Hasil Screening — Semua Kandidat")
st.dataframe(
    df_results.style.background_gradient(subset=["Skor Total"], cmap="Greens"),
    use_container_width=True,
    hide_index=True,
)

# ----------------------------------------------------------------------
# TOP N SAHAM TERBAIK
# ----------------------------------------------------------------------
st.markdown("---")
st.header(f"🏆 {n_final} Saham Terbaik Hasil Skoring")

top_n = df_results.head(n_final)

# Diversifikasi sektor sebagai catatan (tidak otomatis difilter, hanya info)
sector_counts = top_n["Sektor"].value_counts()
if sector_counts.max() > math.ceil(n_final / 2):
    st.info(
        f"ℹ️ Catatan diversifikasi: {sector_counts.idxmax()} mendominasi "
        f"{sector_counts.max()} dari {n_final} kandidat teratas. "
        "Pertimbangkan penyesuaian bias sektor di sidebar jika ingin sebaran lebih merata."
    )

results_map = {r["Ticker"]: r for r in results}

for _, row in top_n.iterrows():
    ticker_short = row["Ticker"]
    full_ticker = ticker_short + ".JK"
    r = results_map[ticker_short]
    df = r["_df"]
    fund = r["_fund"]
    trend_checks = r["_trend_checks"]

    with st.container(border=True):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.subheader(f"{ticker_short} — {row['Sektor']}")
            st.metric("Skor Total", f"{row['Skor Total']:.1f} / 100")
            st.metric("Harga Terakhir", f"Rp {row['Harga']:,.0f}")

            sub_df = pd.DataFrame({
                "Kategori": ["Likuiditas (20%)", "Teknikal (35%)", "Momentum (20%)",
                              "Fundamental (15%)", "Katalis/Makro (10%)"],
                "Skor": [row["Likuiditas"], row["Teknikal"], row["Momentum"],
                         row["Fundamental"], row["Katalis/Makro"]],
            })
            st.dataframe(sub_df, hide_index=True, use_container_width=True)

            with st.expander("Detail Trend Template"):
                for k, v in trend_checks.items():
                    if k == "note":
                        st.caption(v)
                        continue
                    icon = "✅" if v else "❌"
                    st.write(f"{icon} {k}")

        with col2:
            # Chart candlestick + MA
            fig = go.Figure()
            plot_df = df.tail(180)
            fig.add_trace(go.Candlestick(
                x=plot_df.index, open=plot_df["Open"], high=plot_df["High"],
                low=plot_df["Low"], close=plot_df["Close"], name="Harga",
            ))
            for ma, color in [("MA20", "orange"), ("MA50", "blue"), ("MA150", "purple"), ("MA200", "red")]:
                if ma in plot_df.columns:
                    fig.add_trace(go.Scatter(
                        x=plot_df.index, y=plot_df[ma], name=ma,
                        line=dict(width=1, color=color),
                    ))
            fig.update_layout(
                height=380, margin=dict(l=10, r=10, t=30, b=10),
                xaxis_rangeslider_visible=False,
                title=f"{ticker_short} — Harga 6 Bulan Terakhir",
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig, use_container_width=True)

        # Rencana DCA
        st.markdown("**📐 Rencana Entry Bertahap (DCA / Scaling-In)**")
        dca_plan = build_dca_plan(df)
        st.dataframe(dca_plan, hide_index=True, use_container_width=True)

        # Fundamental ringkas
        st.markdown("**📋 Ringkasan Fundamental (best-effort dari Yahoo Finance)**")
        f1, f2, f3, f4 = st.columns(4)
        f1.metric("PER (Trailing)", f"{fund.get('trailingPE', float('nan')):.1f}" if not math.isnan(fund.get("trailingPE", float('nan'))) else "N/A")
        f2.metric("PBV", f"{fund.get('priceToBook', float('nan')):.1f}" if not math.isnan(fund.get("priceToBook", float('nan'))) else "N/A")
        eg = fund.get("earningsQuarterlyGrowth", float("nan"))
        f3.metric("Pertumbuhan EPS QoQ", f"{eg*100:.1f}%" if not math.isnan(eg) else "N/A")
        rg = fund.get("revenueGrowth", float("nan"))
        f4.metric("Pertumbuhan Revenue", f"{rg*100:.1f}%" if not math.isnan(rg) else "N/A")

        # Berita terbaru
        st.markdown("**📰 Berita Terbaru**")
        news_items = fetch_news(f"{ticker_short} saham", max_items=5)
        if news_items:
            for item in news_items:
                st.markdown(f"- [{item['title']}]({item['link']})  \n  <sub>{item['source']} — {item['published']}</sub>", unsafe_allow_html=True)
        else:
            st.caption("Tidak ada berita ditemukan / RSS tidak dapat diakses.")

# ----------------------------------------------------------------------
# KONTEKS MAKRO / IHSG
# ----------------------------------------------------------------------
st.markdown("---")
st.header("🌐 Konteks Makro — IHSG")

if not benchmark_df.empty:
    col1, col2 = st.columns([2, 1])
    with col1:
        fig = go.Figure()
        plot_df = benchmark_df.tail(180)
        fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df["Close"], name="IHSG", line=dict(color="navy")))
        for ma, color in [("MA50", "blue"), ("MA200", "red")]:
            if ma in plot_df.columns:
                fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df[ma], name=ma, line=dict(width=1, dash="dot", color=color)))
        fig.update_layout(height=320, margin=dict(l=10, r=10, t=30, b=10), title="IHSG — 6 Bulan Terakhir")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        last = benchmark_df.iloc[-1]
        st.metric("IHSG Terkini", f"{last['Close']:,.0f}")
        if not math.isnan(last.get("MA200", np.nan)):
            position = "Di atas MA200 (bullish jangka panjang)" if last["Close"] > last["MA200"] else "Di bawah MA200 (waspada)"
            st.caption(position)

st.markdown("**📰 Berita Makro / IHSG Terbaru**")
macro_news = fetch_news("IHSG BI Rate ekonomi Indonesia", max_items=6)
if macro_news:
    for item in macro_news:
        st.markdown(f"- [{item['title']}]({item['link']})  \n  <sub>{item['source']} — {item['published']}</sub>", unsafe_allow_html=True)
else:
    st.caption("Tidak ada berita ditemukan / RSS tidak dapat diakses.")

st.markdown("---")
st.caption(
    "Dibangun dengan Streamlit + yfinance + Plotly. Bobot & parameter dapat disesuaikan di sidebar. "
    "Bukan nasihat investasi — gunakan untuk pembelajaran dan riset mandiri."
)
