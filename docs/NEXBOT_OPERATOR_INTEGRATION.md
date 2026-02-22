# OpenClaw Agent Integration (Example: Nexbot)

The Pacifica Operator is designed to be monitored and tuned by an **OpenClaw agent** (such as our instance, **Nexbot**). This document summarizes how an OpenClaw agent interacts with this repository and operator preferences.

> **Note**: "Nexbot" is a specific instance of an [OpenClaw](https://github.com/openclaw/openclaw) agent. When setting up your own operator, replace "Nexbot" with the name of your agent throughout your configuration.

## Role of This Repo

- **Pacifica Operator** = dominant scalper strategy (5m, tight SL/TP, volume confirmation) for Nexwave perps on Pacifica DEX.
- **OpenClaw Agent** (e.g., Nexbot) monitors strategy, reads positions/performance via CLI and API, and can **tweak strategy in plain English** (e.g. "be less aggressive", "increase cooldown"). Overrides reload every 60s.

## Monitoring & Alerts

Your agent is typically instructed to:

1. **Ping the operator when Pacifica starts trading** — New position or trade after inactivity: symbol, side, size, entry, open positions count.
2. **Ping on closed trades** — Realized PnL, symbol, side, entry/exit, size; plus 24h summary (total PnL, win rate, trade count).

Details: agent's memory `~/.agent-name/memory/strategies/PACIFICA_ALERTS.md` and capabilities in `~/.agent-name/identity/CAPABILITIES.md`.

## API Used by Agent

- `GET /health` — Liveness
- `GET /api/v1/positions` — Open positions
- `GET /api/v1/performance?period=24h&strategy_id=vwm_momentum_1` — PnL, win rate, trade count
- `GET /api/v1/strategy-config` — Current strategy params
- `PATCH /api/v1/strategy-config` — Apply overrides (Agent plain-English → params)

Default base URL: `http://localhost:8000` or from `~/.agent-name/config/pacifica_operator.json`.

## Operator Yield Preference (Out of Scope for This Repo)

Our instance prefers **Kamino Finance** and **JitoSOL–SOL pools on Meteora** for yield automation. That work lives in the agent's yield stack, not in Pacifica Operator. Reference: `~/.agent-name/memory/strategies/KAMINO_JITOSOL_METEORA.md`.

## Related Docs

- **Pacifica Operator:** This repo; scalping strategy in `docs/SCALPING_STRATEGY.md`.
- **Data pipeline and "Not enough candle data":** `docs/DATA_PIPELINE_AND_CANDLE_WARNINGS.md` — pipeline is ticks → DB → continuous aggregates → candles; no backfill endpoint; let it run.
- **Agent integration (server):** `~/.agent-name/docs/PACIFICA_OPERATOR_INTEGRATION.md`.
- **OpenClaw Agent Skill:** `~/.agent-name/skills/pacifica-operator/`.

---

*Last updated: 2026-01-30*
