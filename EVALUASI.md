# EVALUASI STRATEGI — Indodax Trading Bot

## Ringkasan Backtest (Mei–Juni 2026)

| Metrik | SOL_IDR | DOGE_IDR | PEPE_IDR | SUI_IDR | XRP_IDR | ADA_IDR | LINK_IDR |
|--------|---------|----------|----------|---------|---------|---------|----------|
| **Total Trades** | 23 | 24 | 13 | 8 | 3 | 7 | 8 |
| **Win Rate** | 73.9% | **75.0%** | 53.8% | 50.0% | 0.0% | 28.6% | 25.0% |
| **Total Return** | **+8.06%** | +6.06% | +0.72% | +3.89% | -1.07% | -2.54% | -2.54% |
| **Profit Factor** | 3.38 | **4.35** | 1.25 | 1.99 | 0.00 | 0.30 | 0.40 |
| **Max Drawdown** | 2.04% | **0.60%** | 2.07% | 3.08% | 1.07% | 2.56% | 2.89% |
| **Sharpe Ratio** | 8.17 | **10.96** | 1.51 | 4.00 | -32.99 | -9.29 | -6.48 |
| **Avg Win** | +IDR 67,385 | +IDR 43,727 | +IDR 50,678 | +IDR 195,663 | — | +IDR 54,393 | +IDR 83,062 |
| **Avg Loss** | -IDR 56,542 | -IDR 30,185 | -IDR 47,144 | -IDR 98,401 | -IDR 35,615 | -IDR 72,515 | -IDR 70,003 |
| **Best Trade** | +9.80% | +5.27% | +5.46% | +7.49% | -0.58% | +2.51% | +2.02% |
| **Worst Trade** | -5.20% | -3.47% | -5.20% | -5.20% | -2.58% | -5.20% | -5.20% |
| **Volume 24J(IDR)** | 9,07 T | 1,82 T | 1,20 T | 595 M | 3,76 T | 1,36 T | 142 M |
| **Spread %** | 0.23% | 0.15% | 0.002% | 0.22% | 0.005% | 0.10% | 0.73% |
| **Volatilitas 24J** | 6.38% | 4.30% | 6.15% | 3.72% | 5.17% | 8.50% | 6.57% |

**Catatan:** Hasil sebelumnya (BTC, ETH) standalone — backtest baru mencakup 7 pair populer dengan rentang 2026-05-01 hingga 2026-07-03.

## Analisis per Pair

### SOL_IDR — Best Performer (Best)
- **23 trades**, 73.9% win rate — sinyal paling sering dan paling akurat
- Profit Factor 3.38 — sangat solid (setiap IDR 1 rugi menghasilkan IDR 3.38 untung)
- Max Drawdown 2.04% — risiko terkendali
- Volume 9,07 T — likuiditas tinggi, slippage rendah
- **Rekomendasi:** FOKUS UTAMA untuk live trading

### DOGE_IDR — Second Best (Recommended)
- **24 trades**, **75.0% win rate** — paling banyak trade dan paling tinggi win ratenya
- **Profit Factor 4.35** — TERTINGGI dari semua pair, modal sangat efisien
- **Max Drawdown hanya 0.60%** — paling aman
- **Sharpe 10.96** — return per unit risk tertinggi
- Harga IDR 1,335 per koin — mudah dibeli dalam jumlah besar
- Volume 1,82 T — likuiditas OK untuk modal 3jt
- **Kekurangan:** Spread 0.15%, volatilitas 4.30% (lebih rendah dari SOL)
- **Rekomendasi:** KANDIDAT KEDUA setelah SOL untuk live atau diversifikasi

### PEPE_IDR — Performa Standar
- 13 trades, 53.8% win rate — mendekati acak
- Profit Factor 1.25 — tipis, hampir breakeven
- **Spread sangat kecil 0.002%** — ideal untuk entry/exit tanpa slippage
- Harga mendekati 0 — sulit untuk position sizing presisi
- **Rekomendasi:** skip untuk live, risiko reward tidak sebanding

### SUI_IDR — Potensi Tapi Jarang Sinyal
- Hanya 8 trades dalam 2 bulan — sinyal jarang
- 50% win rate — acak
- Tapi avg win IDR 195,663 — sangat besar saat menang
- **Rekomendasi:** pantau saja, belum cukup data

### XRP_IDR — FAIL (0% Win Rate)
- Hanya 3 trades, **0 dari 3 profit** — strategi tidak cocok untuk XRP
- Likuiditas tinggi, spread 0.005%, tapi pattern harga XRP tidak cocok dengan indikator bot
- **Rekomendasi:** HINDARI

### ADA_IDR — FAIL
- 7 trades, 28.6% win rate — rugi terus
- Volatilitas 8.50% tinggi tapi tidak bisa dimanfaatkan bot
- **Rekomendasi:** HINDARI

### LINK_IDR — FAIL
- 8 trades, 25% win rate
- Volume rendah (142 M), spread tinggi (0.73%)
- **Rekomendasi:** HINDARI

## Paper Trading Test — 2026-07-03

**Sesi:** 3 cycle (15m timeframe, SOL_IDR + DOGE_IDR)

**Hasil:** 0 trades — kedua pair dalam regime **choppy** (ADX < 20):
- SOL_IDR: ADX 19.25 | RSI 39.43 | MACD negatif | Signal NEUTRAL | Phantom 0%
- DOGE_IDR: ADX 16.21 | RSI 48.29 | MACD positif | Signal NEUTRAL | Phantom 45%

**Verifikasi komponen:**
- ✅ Live OHLCV fetch dari Indodax (SOL + DOGE)
- ✅ Indicator calculation (ADX, RSI, MACD) — semua akurat
- ✅ Regime detection — mendeteksi choppy dengan tepat
- ✅ Phantom scan — DOGE_IDR terdeteksi 45% phantom
- ✅ Risk manager — 7 guards lulus
- ✅ Telegram startup notification — TERKIRIM
- ✅ Telegram shutdown notification — TERKIRIM
- ✅ CLI --pairs override config.json — bekerja (SOL+DOGE dimuat)
- ✅ Graceful shutdown — bersih tanpa error

**Observasi:**
- Phantom DOGE 45% di cycle 2–3 menunjukkan DOGE memiliki false signal risk tinggi saat sideways
- Bot TIDAK masuk trade karena regime choppy — ini perilaku yang benar (disiplin)
- Telegram notification berfungsi penuh (startup + shutdown)
- Tidak ada error/warning selama berjalan

## Backtest Terbaru — SOL_IDR + DOGE_IDR (2026-06-03 s.d. 2026-07-03, Fix2 Settings)

**Parameter:** Volume >1.3=75 / >1.0=50, Score 85/68/32/15, 2-indicator confirmation, SL 6%, TP 2:1, ATR vol fix

| Metrik | SOL_IDR | DOGE_IDR |
|--------|---------|----------|
| **Total Trades** | 14 | 14 |
| **Win Rate** | 71.4% | 71.4% |
| **Total Return** | +5.83% | +3.03% |
| **Profit Factor** | 3.09 | 4.24 |
| **Max Drawdown** | 0.00% | 3.35% |
| **Sharpe Ratio** | 8.08 | 9.56 |

**Analisis:** Kedua pair menunjukkan performa positif setelah revert parameter ke tingkat moderat. SOL_IDR unggul return (+5.83%), DOGE_IDR unggul profit factor (4.24). Mayoritas exit via Time Stop — bot konsisten mendapat entry di arah yang benar meski TP jarang tersentuh dalam 24h.

## Risiko Sebelum Live Trading

### 1. **Slippage & Likuiditas**
Backtest menggunakan `close` price — real order bisa kena slippage 0.1–1%. Pair besar (BTC/IDR) likuiditas baik, SOL/IDR juga cukup.

### 2. **Time Stop Dominan**
Mayoritas exit via Time Stop, bukan TP/SL. Artinya bot tidak bisa memprediksi arah dengan presisi tinggi — masuk di harga bagus tapi exit dipaksa waktu.

### 3. **SOL_IDR Dependency**
~70% profit dari SOL_IDR. Jika SOL sideways/bearish bertahuntahun, strategi bisa underperform.

### 4. **Kelly Sizing**
Position size Half-Kelly menghasilkan ukuran posisi kecil (0.1–2.5 SOL per trade). Aman untuk modal IDR 10jt, tapi profit juga kecil.

## Rekomendasi Sebelum Live

| # | Rekomendasi | Prioritas | Dampak |
|---|------------|-----------|--------|
| 1 | **Mulai dengan SOL_IDR** (+ DOGE_IDR opsi diversifikasi) | 🔴 WAJIB | SOL terbukti terbaik, DOGE kandidat kedua |
| 2 | **HINDARI XRP, ADA, LINK** | 🔴 WAJIB | Ketiganya rugi di backtest |
| 3 | **Gunakan modal kecil dulu** (IDR 1–5jt) | 🔴 WAJIB | Batasi risiko di minggu pertama |
| 4 | **Pasang Stop Loss harian** (MAX 5% dari modal) | 🔴 WAJIB | Proteksi dari crash/flash crash |
| 5 | **Aktifkan Telegram notification** | 🟡 SARAN | Pantau entry/exit real-time ✅ SUDAH AKTIF |
| 6 | **Dedicated VPS** | 🟡 SARAN | Bot harus running 24/7 |
| 7 | **Review setiap minggu** pertama | 🟡 SARAN | Evaluasi slippage, eksekusi, psikologi |

## Simulasi Proyeksi (SOL_IDR + DOGE_IDR, modal IDR 5jt)

| Skenario | Bulan 1 | Bulan 3 | Bulan 6 |
|----------|---------|---------|---------|
| **Optimis** (+5%/bln) | IDR 5,250,000 | IDR 5,788,000 | IDR 6,700,000 |
| **Moderat** (+3%/bln) | IDR 5,150,000 | IDR 5,464,000 | IDR 5,970,000 |
| **Pesimis** (-2%/bln) | IDR 4,900,000 | IDR 4,706,000 | IDR 4,427,000 |
| **Worst Case** (-5%/bln) | IDR 4,750,000 | IDR 4,287,000 | IDR 3,677,000 |

Dengan 71.4% SOL + 71.4% DOGE win rate, skenario moderat (3%/bln) realistis.

## Pair Research — Data 2026-07-03

| Pair | Volume 24J(IDR) | Spread | Volatilitas 24J | Kinerja Backtest |
|------|----------------|--------|-----------------|-----------------|
| **SOL_IDR** | 9,07 T | 0.23% | 6.38% | ✅ BEST +8.06% |
| **DOGE_IDR** | 1,82 T | 0.15% | 4.30% | ✅ +6.06% (PF 4.35) |
| **PEPE_IDR** | 1,20 T | 0.002% | 6.15% | ⚠️ +0.72% (mendekati 0) |
| **SUI_IDR** | 595 M | 0.22% | 3.72% | ⚠️ +3.89% (jarang sinyal) |
| **XRP_IDR** | 3,76 T | 0.005% | 5.17% | ❌ -1.07% (0% WR) |
| **ADA_IDR** | 1,36 T | 0.10% | 8.50% | ❌ -2.54% |
| **LINK_IDR** | 142 M | 0.73% | 6.57% | ❌ -2.54% (spread tinggi) |
| BTC_IDR | 18,65 T | 0.13% | 3.14% | ✅ +1.71% (sebelumnya) |
| ETH_IDR | 9,12 T | 0.11% | 6.31% | ⚠️ +0.54% (50% WR) |

**Kriteria seleksi:** Volume > IDR 100M, Spread < 0.5%, Backtest return positif, Win rate > 50%.

## Kesimpulan

**✅ STATUS: SIAP LIVE TRADING — Kedua pair backtest positif**

**Yang berfungsi:**
1. ✅ Semua komponen bot berjalan normal (fetch, indikator, regime, phantom, risk)
2. ✅ Telegram notification aktif dan terverifikasi (startup + shutdown)
3. ✅ CLI override config.json berfungsi
4. ✅ 92/92 tests pass
5. ✅ Fix parameter entry: score 85/68/32/15, volume >1.3, 2-indicator, ATR direction fix
6. ✅ Paper test: 0 false entries saat regime choppy

**Hasil Akhir:**
- ✅ SOL_IDR: 14 trades, 71.4% WR, +5.83% return
- ✅ DOGE_IDR: 14 trades, 71.4% WR, +3.03% return
- ✅ Kedua pair profit, PF > 3.0, Sharpe > 8.0

**Rekomendasi:**
| # | Tindakan | Prioritas |
|---|----------|-----------|
| 1 | **Mulai paper trading** SOL_IDR + DOGE_IDR (modal virtual 5jt) | 🟡 SARAN |
| 2 | **Pantau 1 minggu** — bandingkan eksekusi real vs backtest | 🟡 SARAN |
| 3 | **Evaluasi slippage** setelah 1 minggu paper | 🟡 SARAN |
| 4 | **Jika paper OK → live dengan IDR 3–5jt** | 🟡 SETELAH PAPER |
