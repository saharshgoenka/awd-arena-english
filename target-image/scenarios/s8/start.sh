#!/usr/bin/env bash
set -e
cd /app
mkdir -p /app/data

# Recompile from (possibly patched) source, then run. The module cache is
# already populated by the image build, so this works offline.
go build -o /app/server .

exec /app/server
