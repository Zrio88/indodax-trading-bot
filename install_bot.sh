#!/bin/bash
# =====================================================
# Install Indodax Trading Bot — Ubuntu ProOT
# =====================================================
# Jalankan:
#   proot-distro login ubuntu
#   bash <(curl -s https://raw.githubusercontent.com/Zrio88/indodax-trading-bot/main/install_bot.sh)
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
print_info() { echo -e "  ${CYAN}→${NC} $1"; }

cd "$HOME"

# --- 1. Dependencies ---
print_step "Install system dependencies..."
apt update -qq && apt upgrade -y -qq
apt install -y -qq python3 python3-pip python3-venv git curl wget \
  libta-lib-dev build-essential sqlite3 screen tmux 2>&1 | tail -1
print_ok "System dependencies selesai"

# --- 2. Clone Repo ---
print_step "Clone repository..."
if [ -d "indodax-trading-bot" ]; then
  print_warn "Folder udah ada, pull ulang..."
  cd indodax-trading-bot && git pull
else
  git clone https://github.com/Zrio88/indodax-trading-bot.git
  cd indodax-trading-bot
fi
print_ok "Repository siap di $HOME/indodax-trading-bot"

# --- 3. Virtual Environment ---
print_step "Setup virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
print_ok "Virtual environment siap"

# --- 4. Install Python Dependencies ---
print_step "Install Python packages..."
pip install -r requirements.txt -q 2>&1 | tail -1 || {
  print_warn "Coba --no-binary TA-Lib..."
  pip install --no-binary :all: TA-Lib -q
  pip install -r requirements.txt -q
}
print_ok "Semua packages terinstall"

# --- 5. Setup .env ---
print_step "Konfigurasi .env..."
if [ ! -f ".env" ]; then
  cp .env.example .env
  print_info "File .env udah dibuat"
  print_info "Isi API key: nano $HOME/indodax-trading-bot/.env"
fi

# --- 6. Verify ---
print_step "Verifikasi packages..."
python3 -c "import talib; print(f'  TA-Lib: {talib.__version__}')" 2>&1 || print_warn "TA-Lib import gagal"
python3 -c "import ccxt; print(f'  CCXT: {ccxt.__version__}')" 2>&1

# --- 7. Tests ---
print_step "Jalankan tests..."
python3 -m pytest tests/ -q --tb=short 2>&1 | tail -3
if python3 -m pytest tests/ -q --tb=short 2>&1 | grep -q "failed"; then
  print_fail "Ada test gagal — cek: python3 -m pytest tests/ -v"
else
  print_ok "SEMUA TESTS LULUS ✅"
fi

# --- 8. Done ---
echo ""
echo -e "${BOLD}${GREEN}╔═══════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║     INSTALASI SELESAI! ✅              ║${NC}"
echo -e "${BOLD}${GREEN}╚═══════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}Cara pakai:${NC}"
echo "    cd ~/indodax-trading-bot && source venv/bin/activate"
echo ""
echo -e "  ${BOLD}Backtest:${NC}"
echo "    python main.py backtest --pairs SOL_IDR,DOGE_IDR \\"
echo "      --start 2026-06-01 --end 2026-07-03"
echo ""
echo -e "  ${BOLD}Paper Trading:${NC}"
echo "    screen -S bot"
echo "    python main.py paper --pairs SOL_IDR,DOGE_IDR --timeframe 15m"
echo ""
echo -e "  ${BOLD}Live:${NC}"
echo "    python main.py live --pairs SOL_IDR --timeframe 1h"
echo ""
