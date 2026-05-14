#!/bin/bash
set -e

echo "[AWD Target] Starting initialization..."

# 1. Configure SSH password from environment
if [ -n "$SSH_PASSWORD" ]; then
    echo "juice:$SSH_PASSWORD" | chpasswd
    echo "[AWD Target] SSH password configured for user 'juice'"
else
    echo "[AWD Target] WARNING: SSH_PASSWORD not set, using default password"
fi

# 2. Initialize arena database
ARENA_DB="/app/arena/arena.db"

if [ ! -f "$ARENA_DB" ]; then
    echo "[AWD Target] Initializing arena database..."
    sqlite3 "$ARENA_DB" < /app/arena/init_arena_db.sql
    chown juice:juice "$ARENA_DB"
    chmod 644 "$ARENA_DB"
    echo "[AWD Target] Arena database initialized at $ARENA_DB"
else
    echo "[AWD Target] Arena database already exists"
fi

# 3. Start SSH
echo "[AWD Target] Starting SSH service..."
service ssh start

# 4. Banner
echo "=========================================="
echo "OpenClaw AWD Target Configuration"
echo "=========================================="
echo "Juice Shop Port:  3000"
echo "SSH Port:         22"
echo "SSH User:         juice"
echo "Arena Database:   $ARENA_DB"
echo "=========================================="

# 5. Start Juice Shop (upstream entrypoint)
echo "[AWD Target] Starting Juice Shop..."
exec npm start
