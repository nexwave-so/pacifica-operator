# Pacifica Operator – Dominant Scalper Strategy

**Last updated:** 2026-01-30

Pacifica Operator is the **dominant scalper strategy**: short timeframes (5m), tight stops, volume confirmation, high frequency. Baddie Quant (Hyperliquid) is used for longer-term swing trading.

---

## Defaults (scalping)

| Parameter | Value | Purpose |
|-----------|--------|---------|
| **vwm_timeframe** | `5m` | 5-minute candles for fast signals |
| **vwm_momentum_threshold** | `0.001` | 0.1% entry trigger |
| **vwm_exit_threshold** | `0.0005` | 0.05% exit when momentum fades |
| **vwm_volume_multiplier** | `2.0` | 2× average volume confirmation |
| **vwm_lookback_period** | `12` | 12 candles (e.g. 1h on 5m) |
| **vwm_base_position_pct** | `1.0` | 1% base position size |
| **vwm_max_position_pct** | `5.0` | 5% max position |
| **vwm_stop_loss_atr_multiplier** | `1.5` | 1.5× ATR stop loss |
| **vwm_take_profit_atr_multiplier** | `2.5` | 2.5× ATR take profit |
| **trade_cooldown_seconds** | `300` | 5 min between trades |

---

## Where it’s implemented

- **Config:** `src/nexwave/common/config.py` – defaults and `STRATEGY_CONFIG_KEYS` (including `vwm_take_profit_atr_multiplier`).
- **Short-term strategy:** `src/nexwave/strategies/momentum/short_term_momentum.py` – reads timeframe, lookback, volume multiplier, SL/TP ATR multiples, and base position % from settings; uses 5m when `vwm_timeframe=5m`.
- **Env / Docker:** `env.example`, `docker-compose.yml` – scalping env defaults.
- **API:** All of the above are in `GET/PATCH /api/v1/strategy-config`; Nexbot can tweak via Telegram (e.g. `pacifica strategy set vwm_timeframe 5m`).

---

## Nexbot / API overrides

Strategy config is reloaded every 60s. Overrides can be set via:

- **Nexbot (Telegram):** e.g. “increase cooldown”, “tighten risk”.
- **CLI:** `pacifica strategy set <key> <value>` or `pacifica strategy apply` with JSON.
- **Env:** Set `VWM_*` and `TRADE_COOLDOWN_SECONDS` in `.env` or docker-compose.

See `~/.nexbot/docs/PACIFICA_OPERATOR_INTEGRATION.md` and `CLAUDE.md` for full variable lists.

---

## Comparison with Baddie Quant

| | Pacifica Operator | Baddie Quant |
|---|-------------------|---------------|
| **Role** | **Dominant scalper** | Swing / long-term |
| **Timeframe** | 5m (configurable) | 4h / daily |
| **Hold style** | Minutes to ~1h | Multi-day |
| **Frequency** | Higher (5 min cooldown) | Lower |
