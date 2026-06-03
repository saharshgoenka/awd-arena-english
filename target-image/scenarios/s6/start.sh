#!/usr/bin/env bash
set -e
cd /app
export RAILS_ENV=production
export SECRET_KEY_BASE="${SECRET_KEY_BASE:-contenthub_static_secret_key_base_for_dev_only_not_secure}"

bin/rails db:migrate 2>&1
bin/rails db:seed  2>&1

exec bin/rails server -b 0.0.0.0 -p 3000 -e production
