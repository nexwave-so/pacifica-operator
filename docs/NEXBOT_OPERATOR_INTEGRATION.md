# Nexbot Operator Integration

Pacifica Operator is monitored and tuned by **Nexbot** (DeFi agent layer). This doc summarizes how Nexbot interacts with this repo and operator preferences.

## Role of This Repo

- **Pacifica Operator** = dominant scalper strategy (5m, tight SL/TP, volume confirmation) for Nexwave perps on Pacifica DEX.
- **Nexbot** monitors strategy, reads positions/performance via `pacifica` CLI and API, and can **tweak strategy in plain English** (e.g. "be less aggressive", "increase cooldown"). Overrides reload every 60s.

## Monitoring & Alerts

Nexbot is instructed to:

1. **Ping the operator when Pacifica starts trading** — New position or trade after inactivity: symbol, side, size, entry, open positions count.
2. **Ping on closed trades** — Realized PnL, symbol, side, entry/exit, size; plus 24h summary (total PnL, win rate, trade count).

Details: operator’s Nexbot memory `~/.nexbot/memory/strategies/PACIFICA_ALERTS.md` and capabilities in `~/.nexbot/identity/CAPABILITIES.md`.

## API Used by Nexbot

- `GET /health` — Liveness
- `GET /api/v1/positions` — Open positions
- `GET /api/v1/performance?period=24h&strategy_id=vwm_momentum_1` — PnL, win rate, trade count
- `GET /api/v1/strategy-config` — Current strategy params
- `PATCH /api/v1/strategy-config` — Apply overrides (Nexbot plain-English → params)

Default base URL: `http://localhost:8000` or from `~/.nexbot/config/pacifica_operator.json`.

## Operator Yield Preference (Out of Scope for This Repo)

Operator prefers **Kamino Finance** and **JitoSOL–SOL pools on Meteora** for yield automation. That work lives in the Nexwave/Nexbot yield stack (e.g. JitoSOL in swap targets, Kamino/Meteora integration), not in Pacifica Operator. Reference: `~/.nexbot/memory/strategies/KAMINO_JITOSOL_METEORA.md`.

## Related Docs

- **Pacifica Operator:** This repo; scalping strategy in `docs/SCALPING_STRATEGY.md`.
- **Data pipeline and "Not enough candle data":** `docs/DATA_PIPELINE_AND_CANDLE_WARNINGS.md` — pipeline is ticks → DB → continuous aggregates → candles; no backfill endpoint; let it run.
- **Nexbot integration (server):** `~/.nexbot/docs/PACIFICA_OPERATOR_INTEGRATION.md`.
- **MoltBot skill:** `~/.moltbot/skills/pacifica-operator/`.

---

*Last updated: 2026-01-30*
