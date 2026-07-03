#!/data/data/com.termux/files/usr/bin/bash
# =====================================================
# Menu Bot — Indodax Trading Bot
# =====================================================
# Jalanin dari mana aja:
#   cd ~/indodax-trading-bot && bash menu.sh
# =====================================================

BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
CYAN="\033[0;36m"
NC="\033[0m"
BOT_DIR="$HOME/indodax-trading-bot"

clear
echo -e "${BOLD}${GREEN}"
echo "  ╔═══════════════════════════════════════════╗"
echo "  ║      INDODAX TRADING BOT — MENU           ║"
echo "  ╚═══════════════════════════════════════════╝${NC}"
echo ""

# Cek directory
if [ ! -d "$BOT_DIR" ]; then
  echo -e "  ${RED}Folder bot ga ditemukan di $BOT_DIR${NC}"
  echo -e "  ${YELLOW}Jalankan dulu: bash <(curl -s ...install_termux.sh)${NC}"
  exit 1
fi

cd "$BOT_DIR"

# Aktifkan venv
if [ -f "venv/bin/activate" ]; then
  source venv/bin/activate
else
  echo -e "  ${RED}venv ga ada — jalankan install script dulu${NC}"
  exit 1
fi

# Cek .env
env_ok=0
if grep -q "INDODAX_API_KEY=" .env 2>/dev/null && ! grep -q 'INDODAX_API_KEY=""' .env 2>/dev/null; then
  env_ok=1
fi

menu() {
  echo -e "  ${BOLD}Pilih mode:${NC}"
  echo ""
  echo -e "  ${CYAN}[1]${NC}  Backtest       — uji strategi pake data historis"
  echo -e "  ${CYAN}[2]${NC}  Paper Trading  — simulasi (ga pake uang sungguhan)"
  echo -e "  ${CYAN}[3]${NC}  Live Trading   — UANG ASLI!"
  echo -e "  ${CYAN}[4]${NC}  Test           — jalanin 92 test cases"
  echo -e "  ${CYAN}[5]${NC}  Edit .env      — isi/ganti API key"
  echo -e "  ${CYAN}[6]${NC}  Encrypt Keys   — enkripsi API key"
  echo -e "  ${CYAN}[7]${NC}  Logs           — liat file log"
  echo -e "  ${CYAN}[8]${NC}  Keluar"
  echo ""
}

pilih_pairs() {
  echo ""
  echo -e "  ${BOLD}Pilih pair:${NC}"
  echo -e "  ${CYAN}[1]${NC}  SOL_IDR"
  echo -e "  ${CYAN}[2]${NC}  DOGE_IDR"
  echo -e "  ${CYAN}[3]${NC}  SOL_IDR + DOGE_IDR"
  echo -e "  ${CYAN}[4]${NC}  Ketik manual"
  echo ""
  read -p "  Pilihan [3]: " pair_choice
  case "${pair_choice:-3}" in
    1) echo "SOL_IDR" ;;
    2) echo "DOGE_IDR" ;;
    3) echo "SOL_IDR,DOGE_IDR" ;;
    4) read -p "  Masukin pair (contoh: BTC_IDR,ETH_IDR): " custom; echo "$custom" ;;
    *) echo "SOL_IDR,DOGE_IDR" ;;
  esac
}

pilih_timeframe() {
  echo ""
  echo -e "  ${BOLD}Pilih timeframe:${NC}"
  echo -e "  ${CYAN}[1]${NC}  15m  — buat scalping /高频"
  echo -e "  ${CYAN}[2]${NC}  1h   — standar (recommended)"
  echo -e "  ${CYAN}[3]${NC}  4h   — swing trading"
  echo ""
  read -p "  Pilihan [2]: " tf_choice
  case "${tf_choice:-2}" in
    1) echo "15m" ;;
    2) echo "1h" ;;
    3) echo "4h" ;;
    *) echo "1h" ;;
  esac
}

while true; do
  menu
  read -p "  Masukin nomor [1-8]: " choice

  case "$choice" in
    1)
      echo ""
      echo -e "${BOLD}═══ BACKTEST ═══${NC}"
      pairs=$(pilih_pairs)
      tf=$(pilih_timeframe)
      echo ""
      read -p "  Start date [2026-06-01]: " start
      read -p "  End date [2026-07-03]: " end
      start="${start:-2026-06-01}"
      end="${end:-2026-07-03}"
      echo ""
      python main.py backtest --pairs "$pairs" --timeframe "$tf" \
        --start "$start" --end "$end" --stop-loss 0.06 --take-profit 2.0
      echo ""
      read -p "  Tekan Enter buat balik ke menu..."
      ;;

    2)
      echo ""
      echo -e "${BOLD}═══ PAPER TRADING ═══${NC}"
      if [ "$env_ok" -eq 0 ]; then
        echo -e "  ${YELLOW}⚠ .env belum diisi — paper tetap jalan tapi pake fake balance${NC}"
      fi
      pairs=$(pilih_pairs)
      tf=$(pilih_timeframe)
      echo ""
      read -p "  Interval (menit) [5]: " interval
      interval="${interval:-5}"
      echo ""
      echo -e "  ${GREEN}Jalanin paper trading...${NC}"
      echo -e "  ${YELLOW}Ctrl+C buat stop${NC}"
      echo ""
      python main.py paper --pairs "$pairs" --timeframe "$tf" \
        --interval "$interval"
      echo ""
      read -p "  Tekan Enter buat balik ke menu..."
      ;;

    3)
      echo ""
      echo -e "${BOLD}${RED}═══ LIVE TRADING — UANG ASLI! ═══${NC}"
      if [ "$env_ok" -eq 0 ]; then
        echo -e "  ${RED}✗ .env belum diisi — isi API key dulu (menu [5])${NC}"
        read -p "  Tekan Enter..."
        continue
      fi
      echo -e "  ${RED}⚠ Pastikan API key TIDAK punya akses withdraw!${NC}"
      echo ""
      read -p "  Kamu yakin? (ketik 'yes'): " confirm
      if [ "$confirm" != "yes" ]; then
        continue
      fi
      pairs=$(pilih_pairs)
      tf=$(pilih_timeframe)
      echo ""
      echo -e "  ${RED}LIVE TRADING BERJALAN...${NC}"
      echo -e "  ${YELLOW}Ctrl+C buat stop${NC}"
      echo ""
      python main.py live --pairs "$pairs" --timeframe "$tf"
      echo ""
      read -p "  Tekan Enter buat balik ke menu..."
      ;;

    4)
      echo ""
      echo -e "${BOLD}═══ TEST ═══${NC}"
      echo -e "  ${CYAN}[1]${NC}  Semua test (92 tests)"
      echo -e "  ${CYAN}[2]${NC}  Test per komponen"
      echo -e "  ${CYAN}[3]${NC}  Test dengan coverage"
      echo ""
      read -p "  Pilihan [1]: " test_choice
      echo ""
      case "${test_choice:-1}" in
        1) python -m pytest tests/ -v --tb=short ;;
        2)
          echo -e "  ${CYAN}[1]${NC}  risk_manager"
          echo -e "  ${CYAN}[2]${NC}  exit_manager"
          echo -e "  ${CYAN}[3]${NC}  phantom_detector"
          echo -e "  ${CYAN}[4]${NC}  adaptive_engine"
          echo -e "  ${CYAN}[5]${NC}  sentiment"
          echo -e "  ${CYAN}[6]${NC}  indicators"
          read -p "  Pilihan: " comp
          case "$comp" in
            1) python -m pytest tests/test_risk_manager.py -v --tb=short ;;
            2) python -m pytest tests/test_exit_manager.py -v --tb=short ;;
            3) python -m pytest tests/test_phantom_detector.py -v --tb=short ;;
            4) python -m pytest tests/test_adaptive_engine.py -v --tb=short ;;
            5) python -m pytest tests/test_sentiment.py -v --tb=short ;;
            6) python -m pytest tests/test_indicators.py -v --tb=short ;;
            *) python -m pytest tests/ -v --tb=short ;;
          esac
          ;;
        3) python -m pytest --cov=. --cov-report=term-missing tests/ ;;
        *) python -m pytest tests/ -v --tb=short ;;
      esac
      echo ""
      read -p "  Tekan Enter buat balik ke menu..."
      ;;

    5)
      nano .env
      # Re-check env status
      if grep -q "INDODAX_API_KEY=" .env 2>/dev/null && ! grep -q 'INDODAX_API_KEY=""' .env 2>/dev/null; then
        env_ok=1
        echo -e "  ${GREEN}✓ .env terisi${NC}"
      fi
      read -p "  Tekan Enter..."
      ;;

    6)
      echo ""
      python utils/encrypt_keys.py
      echo ""
      read -p "  Tekan Enter..."
      ;;

    7)
      echo ""
      if [ -f "logs/bot.log" ]; then
        tail -50 logs/bot.log
      else
        echo -e "  ${YELLOW}Belum ada log${NC}"
      fi
      echo ""
      read -p "  Tekan Enter..."
      ;;

    8)
      echo ""
      echo -e "  ${GREEN}Dadah! 👋${NC}"
      echo ""
      exit 0
      ;;

    *)
      echo -e "  ${RED}Pilihan ga valid${NC}"
      sleep 1
      ;;
  esac
done
