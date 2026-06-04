#!/usr/bin/env bash
set -e
cd /app
mkdir -p /app/data

# Recompile from (possibly patched) source, then run. The crate caches are
# already populated by the image build, so this works offline.
export CARGO_NET_OFFLINE=true
cargo build --release

exec /app/target/release/vaultgate
