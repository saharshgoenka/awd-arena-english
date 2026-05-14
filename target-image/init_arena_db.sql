-- OpenClaw AWD arena database bootstrap
-- Creates arena_secret for flag storage

-- Flag storage table
CREATE TABLE IF NOT EXISTS arena_secret (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    flag TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for lookups and time-based queries
CREATE INDEX IF NOT EXISTS idx_flag ON arena_secret(flag);
CREATE INDEX IF NOT EXISTS idx_created_at ON arena_secret(created_at);

-- Seed row (replaced when the match starts)
INSERT OR IGNORE INTO arena_secret (flag) VALUES ('FLAG{initial_placeholder_flag}');

-- Auto-update updated_at on row changes
CREATE TRIGGER IF NOT EXISTS update_arena_secret_timestamp
AFTER UPDATE ON arena_secret
BEGIN
    UPDATE arena_secret SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
