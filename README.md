# Dashboard Screening Saham IHSG — Multi-Parameter Swing Trading

Dashboard Streamlit yang mengambil data harga & fundamental saham BEI secara
*real-time* dari Yahoo Finance (`yfinance`) dan berita terbaru dari Google
News RSS, lalu menghitung skor komposit berbobot berdasarkan 5 kategori
parameter (sesuai laporan metodologi):

| Kategori | Bobot default |
|---|---|
| Likuiditas & Struktur Pasar | 20% |
| Tren & Trend Template (Stage Analysis / Minervini) | 35% |
| Momentum, Volume & Relative Strength | 20% |
| Fundamental (pertumbuhan laba/revenue, valuasi) | 15% |
| Katalis / Bias Sektor terhadap Makro | 10% |

Hasil akhir: 3-5 saham dengan skor tertinggi, lengkap dengan chart candlestick,
breakdown skor per kategori, rencana entry bertahap (DCA/scaling-in), ringkasan
fundamental, dan berita terbaru per saham.

## Struktur Folder

```
.
├── app.py                  # aplikasi utama Streamlit
├── requirements.txt        # dependencies
├── .streamlit/
│   └── config.toml         # tema warna
└── README.md
```

## Jalankan Lokal

```bash
pip install -r requirements.txt
streamlit run app.py
```

Buka browser ke `http://localhost:8501`.

## Deploy ke Streamlit Community Cloud (via GitHub)

1. Buat repository baru di GitHub, push seluruh isi folder ini (termasuk
   `.streamlit/config.toml`).
2. Buka [share.streamlit.io](https://share.streamlit.io), login dengan akun
   GitHub.
3. Klik **New app** → pilih repo dan branch → set **Main file path** ke
   `app.py` → **Deploy**.
4. Tunggu proses build (instalasi `requirements.txt`) selesai. Aplikasi akan
   memiliki URL publik `https://<nama-app>.streamlit.app`.

## Cara Pakai

1. **Sidebar — Universe Saham**: edit daftar ticker (format `KODE.JK`,
   contoh `BBCA.JK`). Tambahkan/kurangi sesuai watchlist Anda.
2. **Sidebar — Bobot Parameter**: geser slider untuk menyesuaikan bobot
   5 kategori. Total otomatis dinormalisasi ke 100%.
3. **Sidebar — Bias Sektor**: atur skor 0-100 per sektor sesuai pandangan
   makro Anda saat ini (50 = netral, di atas 50 = sektor diuntungkan,
   di bawah 50 = sektor tertekan).
4. **Sidebar — Jumlah saham terbaik**: pilih 3-5.
5. Klik **Jalankan Screening**.
6. Lihat tabel skor lengkap, lalu kartu detail untuk masing-masing saham
   terbaik (chart, breakdown skor, rencana DCA, fundamental, berita).

## Catatan Teknis & Keterbatasan

- **Sumber data**: `yfinance` mengambil data dari Yahoo Finance — gratis,
  namun tidak dijamin SLA dan kadang rate-limited. Jika gagal, coba lagi
  beberapa saat atau kurangi jumlah ticker.
- **Cache**: data harga di-cache 30 menit, fundamental 6 jam, berita 1 jam,
  agar tidak membebani API dan mempercepat reload.
- **Berita**: menggunakan Google News RSS (tanpa API key). Jika ingin sumber
  berita lain (misal NewsAPI, atau RSS media finansial Indonesia spesifik),
  ganti fungsi `fetch_news()` dengan endpoint pilihan Anda.
- **Trend Template** membutuhkan minimal ~210 hari data historis (untuk
  MA200 + slope). Saham yang baru IPO atau data tidak lengkap akan diberi
  skor teknikal 0 dengan catatan.
- **Skor fundamental** bersifat *best-effort* — banyak field `yfinance`
  untuk emiten Indonesia bisa `None`/kosong. Jika data tidak tersedia,
  skor fundamental default 50 (netral).
- Skor "Katalis/Makro" murni berdasarkan **bias sektor manual** yang Anda
  set di sidebar — ini adalah input subjektif yang merepresentasikan
  pandangan Anda terhadap kondisi makro terkini (BI Rate, rotasi sektor,
  dll), bukan hasil analisis otomatis dari berita.

## Disclaimer

Dashboard ini dibuat untuk tujuan **edukasi dan riset mandiri**. Skor yang
dihasilkan bersifat heuristik dan dapat keliru atau tidak akurat akibat
keterbatasan data. Ini **bukan** rekomendasi atau nasihat investasi. Selalu
lakukan verifikasi mandiri (DYOR) dan pertimbangkan berkonsultasi dengan
penasihat keuangan/investasi berlisensi OJK sebelum mengambil keputusan
trading/investasi apa pun.
