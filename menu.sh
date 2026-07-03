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
  echo -e "  ${CYAN}[7]${NC}  Logs & System  — log aktivitas, resource, status"
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
  read -p "  Masukin nomor [1-7]: " choice

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
      echo ""
      if command -v nano &>/dev/null; then
        EDITOR="nano"
      elif command -v vim &>/dev/null; then
        EDITOR="vim"
      elif command -v vi &>/dev/null; then
        EDITOR="vi"
      else
        echo -e "  ${YELLOW}Ga ada editor teks, install nano dulu...${NC}"
        if command -v pkg &>/dev/null; then
          pkg install -y nano 2>/dev/null | tail -1
        elif command -v apt &>/dev/null; then
          apt install -y -qq nano 2>/dev/null
        fi
        EDITOR="nano"
      fi
      $EDITOR .env
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
      while true; do
        echo ""
        echo -e "${BOLD}═══ LOGS & SYSTEM ═══${NC}"
        echo ""
        echo -e "  ${CYAN}[1]${NC}  Bot Activity   — 50 baris terakhir log bot"
        echo -e "  ${CYAN}[2]${NC}  System Resource — CPU, RAM, disk, uptime"
        echo -e "  ${CYAN}[3]${NC}  Bot Status     — cek screen/tmux session"
        echo -e "  ${CYAN}[4]${NC}  Network Check  — ping ke Indodax & GitHub"
        echo -e "  ${CYAN}[5]${NC}  All in One     — tampilin semua sekaligus"
        echo -e "  ${CYAN}[0]${NC}  Kembali ke menu utama"
        echo ""
        read -p "  Pilihan [0]: " log_choice
        echo ""
        case "${log_choice:-0}" in
          1)
            if [ -f "logs/bot.log" ]; then
              tail -50 logs/bot.log
            else
              echo -e "  ${YELLOW}Belum ada log bot${NC}"
            fi
            ;;
          2)
            echo -e "  ${BOLD}CPU & RAM:${NC}"
            echo -e "    $(ps -eo pid,comm,%cpu,%mem,rss --sort=-%cpu | head -8)"
            echo ""
            echo -e "  ${BOLD}Disk:${NC}"
            df -h "$HOME" | awk 'NR==1 || /dev/'
            echo ""
            echo -e "  ${BOLD}Uptime:${NC}"
            uptime
            echo ""
            echo -e "  ${BOLD}Termux Wake Lock:${NC}"
            if command -v termux-wake-lock &>/dev/null; then
              termux-wake-lock 2>/dev/null && echo -e "    ${GREEN}Aktif${NC}" || echo -e "    ${YELLOW}Tidak aktif${NC}"
            else
              echo -e "    ${YELLOW}termux-api ga terinstall${NC}"
            fi
            ;;
          3)
            echo -e "  ${BOLD}Screen sessions:${NC}"
            screen -ls 2>/dev/null || echo "    (ga ada screen session)"
            echo ""
            echo -e "  ${BOLD}Tmux sessions:${NC}"
            tmux list-sessions 2>/dev/null || echo "    (ga ada tmux session)"
            echo ""
            echo -e "  ${BOLD}Bot PID (kalo jalan langsung):${NC}"
            pid=$(pgrep -f "python.*main.py" 2>/dev/null || true)
            if [ -n "$pid" ]; then
              echo -e "    ${GREEN}PID: $pid${NC}"
              ps -p "$pid" -o etime= 2>/dev/null | xargs echo "    Udah jalan:"
            else
              echo -e "    ${YELLOW}Bot ga jalan${NC}"
            fi
            ;;
          4)
            echo -e "  ${BOLD}Indodax:${NC}"
            if ping -c 1 -W 3 indodax.com &>/dev/null; then
              echo -e "    ${GREEN}✓${NC} indodax.com reachable"
            else
              echo -e "    ${RED}✗${NC} indodax.com ga nyampe!"
            fi
            echo -e "  ${BOLD}GitHub:${NC}"
            if ping -c 1 -W 3 github.com &>/dev/null; then
              echo -e "    ${GREEN}✓${NC} github.com reachable"
            else
              echo -e "    ${RED}✗${NC} github.com ga nyampe!"
            fi
            echo -e "  ${BOLD}IP Public:${NC}"
            ip=$(curl -s --max-time 5 ifconfig.me 2>/dev/null || echo "timeout")
            echo -e "    $ip"
            ;;
          5)
            echo -e "${BOLD}--- Bot Activity ---${NC}"
            if [ -f "logs/bot.log" ]; then
              tail -20 logs/bot.log
            else
              echo "  (belum ada log)"
            fi
            echo ""
            echo -e "${BOLD}--- CPU & RAM (top 5) ---${NC}"
            ps -eo pid,comm,%cpu,%mem,rss --sort=-%cpu | head -6
            echo ""
            echo -e "${BOLD}--- Disk ---${NC}"
            df -h "$HOME" | awk 'NR==1 || /dev/'
            echo ""
            echo -e "${BOLD}--- Bot Process ---${NC}"
            pid=$(pgrep -f "python.*main.py" 2>/dev/null || true)
            if [ -n "$pid" ]; then
              echo -e "  ${GREEN}Running (PID: $pid)${NC}"
            else
              echo -e "  ${YELLOW}Not running${NC}"
            fi
            echo ""
            echo -e "${BOLD}--- Network ---${NC}"
            ping -c 1 -W 2 indodax.com &>/dev/null && echo -e "  ${GREEN}✓ indodax.com${NC}" || echo -e "  ${RED}✗ indodax.com${NC}"
            ping -c 1 -W 2 github.com &>/dev/null && echo -e "  ${GREEN}✓ github.com${NC}" || echo -e "  ${RED}✗ github.com${NC}"
            ;;
          0) break ;;
          *) echo -e "  ${RED}Pilihan ga valid${NC}" ;;
        esac
        echo ""
        read -p "  Tekan Enter..."
      done
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
