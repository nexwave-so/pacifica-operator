-- Migration: Add pairs table and populate with all 30 Pacifica pairs
-- This ensures we have a centralized configuration for all trading pairs

-- Create pairs table
CREATE TABLE IF NOT EXISTS pairs (
    symbol VARCHAR(20) PRIMARY KEY,
    quote_currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    max_leverage INTEGER NOT NULL,
    min_order_size DECIMAL(20, 8) NOT NULL,
    tick_size DECIMAL(20, 10) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    category VARCHAR(20) NOT NULL CHECK (category IN ('major', 'mid-cap', 'emerging', 'small-cap')),
    whale_threshold_usd DECIMAL(20, 2),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create index on category for filtering
CREATE INDEX idx_pairs_category ON pairs(category);
CREATE INDEX idx_pairs_active ON pairs(is_active);

-- Insert all 30 Pacifica trading pairs

-- Major Pairs
INSERT INTO pairs (symbol, quote_currency, max_leverage, min_order_size, tick_size, display_name, category, whale_threshold_usd) VALUES
('BTC', 'USD', 50, 0.001, 0.1, 'Bitcoin', 'major', 25000),
('ETH', 'USD', 50, 0.01, 0.01, 'Ethereum', 'major', 25000),
('SOL', 'USD', 20, 0.1, 0.001, 'Solana', 'major', 25000);

-- Mid-Cap Pairs
INSERT INTO pairs (symbol, quote_currency, max_leverage, min_order_size, tick_size, display_name, category, whale_threshold_usd) VALUES
('HYPE', 'USD', 20, 1.0, 0.0001, 'Hyperliquid', 'mid-cap', 10000),
('ZEC', 'USD', 10, 0.01, 0.01, 'Zcash', 'mid-cap', 10000),
('BNB', 'USD', 10, 0.01, 0.01, 'BNB', 'mid-cap', 10000),
('XRP', 'USD', 20, 10.0, 0.0001, 'Ripple', 'mid-cap', 10000),
('PUMP', 'USD', 5, 100.0, 0.00001, 'Pump', 'mid-cap', 10000),
('AAVE', 'USD', 10, 0.1, 0.01, 'Aave', 'mid-cap', 10000),
('ENA', 'USD', 10, 10.0, 0.0001, 'Ethena', 'mid-cap', 10000);

-- Emerging Pairs
INSERT INTO pairs (symbol, quote_currency, max_leverage, min_order_size, tick_size, display_name, category, whale_threshold_usd) VALUES
('ASTER', 'USD', 5, 1.0, 0.0001, 'Aster', 'emerging', 5000),
('kBONK', 'USD', 10, 100.0, 0.000001, 'Bonk (1000x)', 'emerging', 5000),
('kPEPE', 'USD', 10, 100.0, 0.000001, 'Pepe (1000x)', 'emerging', 5000),
('LTC', 'USD', 10, 0.1, 0.01, 'Litecoin', 'emerging', 5000),
('PAXG', 'USD', 10, 0.01, 0.1, 'Paxos Gold', 'emerging', 5000),
('VIRTUAL', 'USD', 5, 1.0, 0.0001, 'Virtual', 'emerging', 5000),
('SUI', 'USD', 10, 1.0, 0.0001, 'Sui', 'emerging', 5000),
('FARTCOIN', 'USD', 10, 1.0, 0.00001, 'Fartcoin', 'emerging', 5000),
('TAO', 'USD', 10, 0.1, 0.01, 'Bittensor', 'emerging', 5000),
('DOGE', 'USD', 15, 10.0, 0.00001, 'Dogecoin', 'emerging', 5000),
('XPL', 'USD', 10, 1.0, 0.0001, 'XPL', 'emerging', 5000),
('AVAX', 'USD', 10, 1.0, 0.01, 'Avalanche', 'emerging', 5000),
('LINK', 'USD', 10, 1.0, 0.001, 'Chainlink', 'emerging', 5000),
('UNI', 'USD', 10, 1.0, 0.001, 'Uniswap', 'emerging', 5000);

-- Small-Cap Pairs
INSERT INTO pairs (symbol, quote_currency, max_leverage, min_order_size, tick_size, display_name, category, whale_threshold_usd) VALUES
('WLFI', 'USD', 5, 1.0, 0.0001, 'WLFI', 'small-cap', 2500),
('PENGU', 'USD', 5, 100.0, 0.000001, 'Pengu', 'small-cap', 2500),
('2Z', 'USD', 3, 1.0, 0.0001, '2Z', 'small-cap', 2500),
('MON', 'USD', 3, 10.0, 0.00001, 'MON', 'small-cap', 2500),
('LDO', 'USD', 10, 1.0, 0.001, 'Lido DAO', 'small-cap', 2500),
('CRV', 'USD', 10, 1.0, 0.0001, 'Curve', 'small-cap', 2500);

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_pairs_updated_at BEFORE UPDATE ON pairs
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add foreign key constraint to existing tables (if they exist)
-- This ensures data integrity between pairs and other tables
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'ticks') THEN
        ALTER TABLE ticks ADD CONSTRAINT fk_ticks_symbol FOREIGN KEY (symbol) REFERENCES pairs(symbol) ON DELETE CASCADE;
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'whale_activities') THEN
        ALTER TABLE whale_activities ADD CONSTRAINT fk_whale_symbol FOREIGN KEY (symbol) REFERENCES pairs(symbol) ON DELETE CASCADE;
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'orders') THEN
        ALTER TABLE orders ADD CONSTRAINT fk_orders_symbol FOREIGN KEY (symbol) REFERENCES pairs(symbol) ON DELETE CASCADE;
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'positions') THEN
        ALTER TABLE positions ADD CONSTRAINT fk_positions_symbol FOREIGN KEY (symbol) REFERENCES pairs(symbol) ON DELETE CASCADE;
    END IF;
END$$;

-- Verify insertion
SELECT
    category,
    COUNT(*) as count,
    STRING_AGG(symbol, ', ' ORDER BY symbol) as symbols
FROM pairs
WHERE is_active = true
GROUP BY category
ORDER BY
    CASE category
        WHEN 'major' THEN 1
        WHEN 'mid-cap' THEN 2
        WHEN 'emerging' THEN 3
        WHEN 'small-cap' THEN 4
    END;
