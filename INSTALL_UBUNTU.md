# Panduan Install Bot di Ubuntu (Termux ProOT)

## Install Cepat (1 Perintah)

### Via Termux Native (Tanpa ProOT)
```bash
pkg install -y curl
bash <(curl -s https://raw.githubusercontent.com/Zrio88/indodax-trading-bot/main/install_termux.sh)
```

### Via ProOT Ubuntu
```bash
proot-distro login ubuntu
bash <(curl -s https://raw.githubusercontent.com/Zrio88/indodax-trading-bot/main/install_bot.sh)
```

---

## Install Manual

## 1. Setup ProOT Ubuntu

```bash
# Install Termux dari F-Droid (bukan Play Store)
# https://f-droid.org/packages/com.termux/

# Buka Termux, install proot-distro
pkg update && pkg upgrade -y
pkg install proot-distro -y

# Install Ubuntu 22.04/24.04
proot-distro install ubuntu

# Masuk ke Ubuntu
proot-distro login ubuntu
```

## 2. Update & Install Dependencies

```bash
# Update package list
apt update && apt upgrade -y

# Install Python dan tools dasar
apt install -y python3 python3-pip python3-venv git curl wget

# Install TA-Lib (required — wajib!)
apt install -y libta-lib-dev build-essential autoconf automake libtool

# Install sqlite3 (untuk database)
apt install -y sqlite3
```

## 3. Clone Repository

```bash
git clone https://github.com/Zrio88/indodax-trading-bot.git
cd indodax-trading-bot
```

## 4. Setup Virtual Environment

```bash
# Buat virtual environment
python3 -m venv venv

# Aktifkan
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install Python dependencies
pip install -r requirements.txt
```

> **Catatan:** Jika `pip install TA-Lib` gagal, instal manual:
> ```bash
> pip install --no-binary :all: TA-Lib
> ```

## 5. Konfigurasi

### 5a. Environment Variables

```bash
cp .env.example .env
nano .env
```

Isi minimal:
```
INDODAX_API_KEY=api_key_dari_indodax
INDODAX_SECRET_KEY=secret_key_dari_indodax
TELEGRAM_BOT_TOKEN=token_dari_botfather  # opsional
TELEGRAM_CHAT_ID=chat_id_telegram        # opsional
```

### 5b. Encrypt API Keys (Rekomendasi)

```bash
python utils/encrypt_keys.py
# Ikuti petunjuk untuk encrypt key
# Setelah selesai, hapus plaintext key dari .env
```

### 5c. Edit config.json (Opsional)

```bash
nano config.json
```

Sesuaikan pair, parameter risk, dll. Default sudah aman untuk paper trading.

## 6. Verifikasi

```bash
# Cek Python dan dependencies
python --version
pip list | grep -E "ccxt|TA-Lib|pandas|numpy"

# Jalankan tests
python -m pytest tests/ -v --tb=short
```

## 7. Running

```bash
# Aktifkan venv dulu
source venv/bin/activate

# Backtest (gratis, tanpa API key)
python main.py backtest --pairs SOL_IDR,DOGE_IDR --start 2026-06-01 --end 2026-07-03

# Paper trading
python main.py paper --pairs SOL_IDR,DOGE_IDR --timeframe 15m
```

## 8. Auto-Restart (Screen / Tmux)

Agar bot tetap jalan walau Termux di-minimize:

```bash
# Install screen
apt install -y screen

# Buat session
screen -S bot

# Di dalam screen:
cd indodax-trading-bot
source venv/bin/activate

# Paper trading
python main.py paper --pairs SOL_IDR,DOGE_IDR --timeframe 15m

# Detach: Ctrl+A, lalu D
# Re-attach: screen -r bot
```

Alternatif pakai tmux:
```bash
apt install -y tmux
tmux new -s bot
# Ctrl+B, lalu D untuk detach
# tmux attach -t bot untuk re-attach
```

## Troubleshooting

| Masalah | Solusi |
|---------|--------|
| `ModuleNotFoundError: No module named 'TA-Lib'` | `pip install TA-Lib` atau `apt install libta-lib-dev` |
| `ccxt.base.errors.ExchangeError: indodax does not have market symbol` | Pastikan pakai format `BTC_IDR` (dengan underscore) |
| `from is less than 2000-01-01` | Rate limit Indodax — tunggu 10 detik, coba lagi |
| `ENCRYPTION_KEY not found` | Jalankan `python utils/encrypt_keys.py` dulu |
| `Error: database is locked` | Hapus `storage/trades.db` atau tunggu bot berhenti |
| Bot berhenti setelah Termux di-minimize | Install Termux:Boot atau pakai **screen/tmux** |
| Termux di-kill Android | Aktifkan **wakelock** atau **battery optimization off** |

## Catatan Penting

- **Jangan gunakan API key dengan akses withdraw** — buat API key khusus trading
- **Mulai dengan paper trading** minimal 1 minggu sebelum live
- **Gunakan screen/tmux** agar bot tetap berjalan
- **Pastikan baterai Android tidak di-optimasi** untuk Termux
- **BACKUP .env dan trades.db** secara berkala
