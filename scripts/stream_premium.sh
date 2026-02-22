#!/bin/bash
# Nexwave PREMIUM Visual Livestream
# Enhanced for live trading agent visibility - NO SECRETS DISPLAYED

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# Security: Filter out sensitive information
filter_secrets() {
    sed -E 's/(api[_-]?key|private[_-]?key|secret|password|token|wallet[_-]?priv|privkey)=[^[:space:]]+/[REDACTED]/gi' | \
    sed -E 's/[A-Za-z0-9]{32,}/[REDACTED]/g' | \
    sed -E 's/0x[0-9a-fA-F]{40,}/[REDACTED]/g'
}

clear

# Animated intro
echo -e "${CYAN}${BOLD}"
for i in {1..3}; do
    echo "▓"
    sleep 0.1
done

clear
cat << 'LOGO'

   ███╗   ██╗███████╗██╗  ██╗██╗    ██╗ █████╗ ██╗   ██╗███████╗
   ████╗  ██║██╔════╝╚██╗██╔╝██║    ██║██╔══██╗██║   ██║██╔════╝
   ██╔██╗ ██║█████╗   ╚███╔╝ ██║ █╗ ██║███████║██║   ██║█████╗
   ██║╚██╗██║██╔══╝   ██╔██╗ ██║███╗██║██╔══██║╚██╗ ██╔╝██╔══╝
   ██║ ╚████║███████╗██╔╝ ██╗╚███╔███╔╝██║  ██║ ╚████╔╝ ███████╗
   ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝ ╚═╝  ╚═╝  ╚═══╝  ╚══════╝

        🚀 A U T O N O M O U S   T R A D I N G   A G E N T 🚀

LOGO

echo -e "${WHITE}${BOLD}"
cat << 'INFO'

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ⚡ STRATEGY        Volume-Weighted Momentum (VWM)
  💰 CAPITAL         $159 → $795-$1,590 (5x leverage)
  📊 MARKETS         30 Perpetual Pairs (Pacifica DEX)
  🎯 SIGNALS         0.1% momentum + 1.2x volume
  🛡️  RISK MGMT      Stop Loss (2.5x ATR) | Take Profit (5x ATR)
  🤖 STATUS          LIVE & SCANNING FOR OPPORTUNITIES

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

INFO

echo -e "${YELLOW}${BOLD}"
echo ""
echo "  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "                  📡 LIVE SIGNAL FEED - HACKATHON DEMO 📡"
echo "  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${NC}"
echo ""

# Counters
total_signals=0
buy_signals=0
sell_signals=0
orders_placed=0
stop_losses=0
take_profits=0
scan_count=0

# Stream with improved output handling
docker logs nexwave-trading-engine -f --tail 0 2>&1 | stdbuf -oL sed 's/\x1b\[[0-9;]*m//g' | while IFS= read -r line; do
    timestamp=$(date '+%H:%M:%S')

    # Signal Check - Show interesting signals only
    if echo "$line" | grep -q "Signal Check:"; then
        symbol=$(echo "$line" | grep -oP '[A-Z0-9]+(?= Signal Check:)')
        vwm=$(echo "$line" | grep -oP 'VWM=\K[-0-9.]+' | head -1)
        volume=$(echo "$line" | grep -oP 'Volume=\K[0-9.]+' | head -1)

        # Only show if close to threshold or high volume
        if [ -n "$vwm" ] && [ -n "$volume" ]; then
            vwm_abs=$(echo "$vwm" | sed 's/-//')
            if (( $(echo "$vwm_abs > 0.0008" | bc -l 2>/dev/null || echo 0) )) || (( $(echo "$volume >= 1.0" | bc -l 2>/dev/null || echo 0) )); then
                vwm_pct=$(echo "scale=3; $vwm * 100" | bc 2>/dev/null || echo "$vwm")

                if (( $(echo "$vwm > 0" | bc -l 2>/dev/null || echo 0) )); then
                    echo -e "${DIM}[$timestamp]${NC} ${GREEN}📈${NC} ${CYAN}${symbol}${NC} ${GREEN}${vwm_pct}%${NC} | Vol:${volume}x"
                else
                    echo -e "${DIM}[$timestamp]${NC} ${RED}📉${NC} ${CYAN}${symbol}${NC} ${RED}${vwm_pct}%${NC} | Vol:${volume}x"
                fi
            fi
        fi

    # BUY Signal
    elif echo "$line" | grep -qi "BUY signal"; then
        ((total_signals++))
        ((buy_signals++))
        symbol=$(echo "$line" | grep -oP 'for \K[A-Z0-9]+' | head -1)

        echo ""
        echo -e "${GREEN}${BOLD}  ╔═══════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}${BOLD}  ║${NC}  🚀 ${WHITE}${BOLD}LONG SIGNAL${NC} ${GREEN}▲${NC}  ${CYAN}${symbol}${NC}  ${DIM}@ $timestamp${NC}"
        echo -e "${GREEN}${BOLD}  ╚═══════════════════════════════════════════════════════════════╝${NC}"
        echo ""

    # SELL Signal
    elif echo "$line" | grep -qi "SELL signal"; then
        ((total_signals++))
        ((sell_signals++))
        symbol=$(echo "$line" | grep -oP 'for \K[A-Z0-9]+' | head -1)

        echo ""
        echo -e "${RED}${BOLD}  ╔═══════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${RED}${BOLD}  ║${NC}  📉 ${WHITE}${BOLD}SHORT SIGNAL${NC} ${RED}▼${NC}  ${CYAN}${symbol}${NC}  ${DIM}@ $timestamp${NC}"
        echo -e "${RED}${BOLD}  ╚═══════════════════════════════════════════════════════════════╝${NC}"
        echo ""

    # Order Placed
    elif echo "$line" | grep -q -E "(Order placed|Order request sent|Order created successfully)"; then
        ((orders_placed++))
        symbol=$(echo "$line" | grep -oP 'for \K[A-Z0-9]+' | head -1 || echo "")
        echo -e "  ${CYAN}→${NC} ✅ ${WHITE}Order executed${NC} ${CYAN}${symbol}${NC}"

    # TP/SL Set
    elif echo "$line" | grep -q "TP/SL set"; then
        echo -e "  ${CYAN}→${NC} 🛡️  ${YELLOW}Protection set${NC}"

    # STOP LOSS
    elif echo "$line" | grep -qi "STOP LOSS"; then
        ((stop_losses++))
        symbol=$(echo "$line" | grep -oP 'for \K[A-Z0-9]+' | head -1 || echo "")

        echo ""
        echo -e "${RED}${BOLD}  ╔═══════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${RED}${BOLD}  ║${NC}  🛑 ${WHITE}${BOLD}STOP LOSS HIT${NC}  ${CYAN}${symbol}${NC}  ${DIM}@ $timestamp${NC}"
        echo -e "${RED}${BOLD}  ╚═══════════════════════════════════════════════════════════════╝${NC}"
        echo ""

    # TAKE PROFIT
    elif echo "$line" | grep -qi "TAKE PROFIT"; then
        ((take_profits++))
        symbol=$(echo "$line" | grep -oP 'for \K[A-Z0-9]+' | head -1 || echo "")

        echo ""
        echo -e "${GREEN}${BOLD}  ╔═══════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}${BOLD}  ║${NC}  💰 ${WHITE}${BOLD}TAKE PROFIT HIT${NC}  ${CYAN}${symbol}${NC}  ${DIM}@ $timestamp${NC}"
        echo -e "${GREEN}${BOLD}  ╚═══════════════════════════════════════════════════════════════╝${NC}"
        echo ""

    # Scan cycle complete
    elif echo "$line" | grep -q "Signal processing complete"; then
        ((scan_count++))
        echo -e "${DIM}[$timestamp] ✓ Scan #${scan_count} complete | Signals: ${total_signals} | Next: 60s${NC}"
        echo ""

        # Show summary every 10 scans
        if [ $((scan_count % 10)) -eq 0 ]; then
            echo -e "${MAGENTA}${BOLD}  ────────────────────────────────────────────────────────────────${NC}"
            echo -e "${MAGENTA}  📊 SESSION SUMMARY (${scan_count} scans)${NC}"
            echo -e "${MAGENTA}  ────────────────────────────────────────────────────────────────${NC}"
            echo -e "     Signals: ${GREEN}${buy_signals} LONG${NC} | ${RED}${sell_signals} SHORT${NC} | Total: ${total_signals}"
            echo -e "     Orders: ✅ ${orders_placed} | Stop Loss: 🛑 ${stop_losses} | Take Profit: 💰 ${take_profits}"
            echo -e "${MAGENTA}${BOLD}  ────────────────────────────────────────────────────────────────${NC}"
            echo ""
        fi
    fi
done
