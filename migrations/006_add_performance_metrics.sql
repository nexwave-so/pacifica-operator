-- Migration: Add performance metrics table
-- Purpose: Store periodic snapshots of trading performance for historical analysis

CREATE TABLE IF NOT EXISTS performance_metrics (
    id SERIAL PRIMARY KEY,
    strategy_id VARCHAR(100) NOT NULL,

    -- Time period
    start_date TIMESTAMPTZ NOT NULL,
    end_date TIMESTAMPTZ NOT NULL,
    period_hours FLOAT NOT NULL,

    -- Trading activity
    total_trades INTEGER NOT NULL DEFAULT 0,
    winning_trades INTEGER NOT NULL DEFAULT 0,
    losing_trades INTEGER NOT NULL DEFAULT 0,
    breakeven_trades INTEGER NOT NULL DEFAULT 0,

    -- Performance
    win_rate FLOAT NOT NULL DEFAULT 0.0,
    total_pnl FLOAT NOT NULL DEFAULT 0.0,
    avg_win FLOAT NOT NULL DEFAULT 0.0,
    avg_loss FLOAT NOT NULL DEFAULT 0.0,
    largest_win FLOAT NOT NULL DEFAULT 0.0,
    largest_loss FLOAT NOT NULL DEFAULT 0.0,
    profit_factor FLOAT NOT NULL DEFAULT 0.0,

    -- Risk metrics
    sharpe_ratio FLOAT,
    max_drawdown FLOAT NOT NULL DEFAULT 0.0,
    max_drawdown_pct FLOAT NOT NULL DEFAULT 0.0,

    -- Efficiency
    avg_hold_time_hours FLOAT NOT NULL DEFAULT 0.0,
    avg_profit_per_hour FLOAT NOT NULL DEFAULT 0.0,

    -- Portfolio state at snapshot time
    open_positions INTEGER NOT NULL DEFAULT 0,
    total_capital FLOAT NOT NULL DEFAULT 0.0,
    capital_deployed FLOAT NOT NULL DEFAULT 0.0,
    capital_utilization_pct FLOAT NOT NULL DEFAULT 0.0,

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for fast lookups by strategy and time
CREATE INDEX IF NOT EXISTS idx_performance_metrics_strategy_time
    ON performance_metrics(strategy_id, end_date DESC);

-- Index for time-series queries
CREATE INDEX IF NOT EXISTS idx_performance_metrics_end_date
    ON performance_metrics(end_date DESC);

-- Comment
COMMENT ON TABLE performance_metrics IS 'Periodic snapshots of trading strategy performance metrics';
COMMENT ON COLUMN performance_metrics.sharpe_ratio IS 'Annualized risk-adjusted return (can be NULL if insufficient data)';
COMMENT ON COLUMN performance_metrics.profit_factor IS 'Ratio of total wins to total losses';
COMMENT ON COLUMN performance_metrics.max_drawdown IS 'Largest peak-to-trough decline in USD';
