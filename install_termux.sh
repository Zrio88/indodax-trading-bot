#!/data/data/com.termux/files/usr/bin/bash
# =====================================================
# Install Indodax Trading Bot — Termux Native
# =====================================================
# Jalankan:
#   pkg install -y curl
#   bash <(curl -s https://raw.githubusercontent.com/Zrio88/indodax-trading-bot/main/install_termux.sh)
# =====================================================

set -e

BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
CYAN="\033[0;36m"
NC="\033[0m"

print_step() { echo -e "\n${BOLD}${GREEN}[+]${NC} ${BOLD}$1${NC}"; }
print_warn() { echo -e "  ${YELLOW}⚠ $1${NC}"; }
print_ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
print_fail() { echo -e "  ${RED}✗${NC} $1"; }
print_info() { echo -e "  ${CYAN}→${NC} $1"; }

clear
echo -e "${BOLD}${GREEN}"
echo "  ╔═══════════════════════════════════════════╗"
echo "  ║     INstal Indodax Trading Bot — Termux   ║"
echo "  ╚═══════════════════════════════════════════╝"
echo -e "${NC}"

# --- Cek Termux ---
if [ ! -d "/data/data/com.termux" ] && [ ! -d "/data/data/com.termux.dev" ]; then
  print_fail "Ini bukan Termux!"
  print_warn "Jalankan script ini di dalam Termux, bukan proot Ubuntu."
  exit 1
fi

# --- 1. Update packages ---
print_step "Update package list..."
pkg update -y -qq 2>/dev/null || pkg update -y
print_ok "Packages updated"

# --- 2. Install dependencies ---
print_step "Install dependencies..."
PKGS="python python-pip git curl wget binutils pkg-config"
for pkg in $PKGS; do
  pkg install -y $pkg 2>/dev/null | tail -1
done
print_ok "Dependencies installed"

# --- 3. Request storage access ---
print_step "Storage access..."
if [ ! -d "$HOME/storage" ]; then
  print_warn "Termux perlu akses storage untuk nyimpan file."
  echo ""
  termux-setup-storage 2>/dev/null || true
  print_info "Kalo muncul dialog, kasih izin, lalu Enter."
  read -p "  Udah dikasih izin? Tekan Enter..."
else
  print_ok "Storage sudah siap"
fi

# --- 4. TA-Lib Installation ---
print_step "Install TA-Lib (library teknis analisis)..."

install_talib_source() {
  cd "$HOME"
  print_info "Download source TA-Lib..."
  curl -sL https://github.com/ta-lib/ta-lib/releases/download/v0.6.4/ta-lib-0.6.4-src.tar.gz -o /tmp/ta-lib.tar.gz
  tar xzf /tmp/ta-lib.tar.gz -C /tmp
  cd /tmp/ta-lib-0.6.4
  print_info "Compile TA-Lib... (butuh ~2 menit)"
  ./configure --prefix="$PREFIX" 2>&1 | tail -1
  make -j$(nproc) 2>&1 | tail -1
  make install 2>&1 | tail -1
  cd "$HOME"
  rm -rf /tmp/ta-lib*
}

# Coba pkg install dulu
if pkg install -y libta-lib 2>/dev/null; then
  print_ok "TA-Lib dari repository"
elif pkg install -y libta-lib-dev 2>/dev/null; then
  print_ok "TA-Lib (dev) dari repository"
else
  print_warn "TA-Lib ga ada di repo, compile dari source..."
  pkg install -y autoconf automake libtool make -qq 2>/dev/null
  install_talib_source
  print_ok "TA-Lib tercompile dari source"
fi

# Verify TA-Lib C library
if [ -f "$PREFIX/lib/libta_lib.so" ] || [ -f "$PREFIX/lib/libta_lib.a" ]; then
  print_ok "TA-Lib C library siap"
else
  print_fail "TA-Lib gagal diinstall, coba manual: https://github.com/ta-lib/ta-lib"
  exit 1
fi

# --- 5. Clone Repo ---
print_step "Clone repository..."
cd "$HOME"
if [ -d "indodax-trading-bot" ]; then
  print_warn "Folder udah ada, update..."
  cd indodax-trading-bot
  git pull
  cd "$HOME"
else
  git clone https://github.com/Zrio88/indodax-trading-bot.git
fi
cd indodax-trading-bot
print_ok "Repository siap"

# --- 6. Virtual Environment ---
print_step "Setup virtual environment..."
python -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
print_ok "Virtual environment siap"

# --- 7. Install Python packages ---
print_step "Install Python packages..."
print_info "Install TA-Lib Python binding..."
pip install TA-Lib -q 2>&1 | tail -1 || {
  print_warn "Coba binary package..."
  pip install --only-binary :all: TA-Lib 2>/dev/null || pip install TA-Lib --no-build-isolation 2>&1 | tail -1
}
pip install -r requirements.txt -q 2>&1 | tail -1
print_ok "Semua Python packages terinstall"

# --- 8. Verify TA-Lib ---
print_step "Verifikasi..."
python -c "import talib; print(f'  TA-Lib version: {talib.__version__}')" 2>&1
python -c "import ccxt; print(f'  CCXT version: {ccxt.__version__}')" 2>&1
print_ok "Import packages OK"

# --- 9. Setup config ---
print_step "Konfigurasi..."
if [ ! -f ".env" ]; then
  cp .env.example .env
  print_info "FILE .env UDAH DIBUAT — isi API key kamu:"
  print_info "  nano ~/indodax-trading-bot/.env"
else
  print_ok ".env udah ada"
fi

# --- 10. Tests ---
print_step "Jalankan tests (92 tests)..."
python -m pytest tests/ -q --tb=short 2>&1 | tail -5
if python -m pytest tests/ -q --tb=short 2>&1 | grep -q "failed"; then
  print_fail "Ada test gagal"
  print_info "Cek: python -m pytest tests/ -v --tb=long"
else
  print_ok "SEMUA TESTS LULUS ✅"
fi

# --- 11. Wake lock (biar ga dimatiin Android) ---
print_step "Setup wake lock..."
pkg install -y termux-services termux-api 2>/dev/null | tail -1 || true
termux-wake-lock 2>/dev/null && print_ok "Wake lock aktif" || print_warn "Gagal wake lock (manual: termux-wake-lock)"

# --- 12. Done ---
echo ""
echo -e "${BOLD}${GREEN}╔═══════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║     INSTALASI SELESAI! ✅                  ║${NC}"
echo -e "${BOLD}${GREEN}╚═══════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}${CYAN}Langkah selanjutnya:${NC}"
echo ""
echo -e "  ${BOLD}1. ISI API KEY${NC}"
echo "     nano ~/indodax-trading-bot/.env"
echo ""
echo -e "  ${BOLD}2. JALANKAN${NC}"
echo "     cd ~/indodax-trading-bot"
echo "     source venv/bin/activate"
echo ""
echo -e "  ${BOLD}   Backtest:${NC}"
echo "     python main.py backtest --pairs SOL_IDR,DOGE_IDR \\"
echo "       --start 2026-06-01 --end 2026-07-03"
echo ""
echo -e "  ${BOLD}   Paper Trading:${NC}"
echo "     python main.py paper --pairs SOL_IDR,DOGE_IDR \\"
echo "       --timeframe 15m"
echo ""
echo -e "  ${BOLD}   Biar bot jalan terus (walaupun HP di-lock):${NC}"
echo "     termux-wake-lock"
echo "     cd ~/indodax-trading-bot && source venv/bin/activate"
echo "     python main.py paper --pairs SOL_IDR,DOGE_IDR --timeframe 15m"
echo ""
echo -e "  ${BOLD}3. GANTI KE LIVE (kalo udah siap):${NC}"
echo "     python main.py live --pairs SOL_IDR --timeframe 1h"
echo ""
echo -e "  ${YELLOW}⚠ Pastikan API key TIDAK punya akses withdraw!${NC}"
echo ""
