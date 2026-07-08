#!/usr/bin/env bash
set -e

# Inject live flag values from the container environment into .env
for i in 1 2 3 4 5; do
    VAR="FLAG_${i}"
    VAL="${!VAR}"
    if [ -n "$VAL" ]; then
        sed -i "s|FLAG_${i}=.*|FLAG_${i}=${VAL}|" /app/.env
    fi
done

rm -f /app/public/.env

mkdir -p /app/data \
         /app/storage/framework/sessions \
         /app/storage/framework/views \
         /app/storage/framework/cache/data \
         /app/storage/app \
         /app/storage/logs \
         /app/bootstrap/cache
chmod -R 777 /app/storage /app/bootstrap/cache

php artisan migrate --force
php artisan db:seed --force

# Wait up to 10s for port 3000 to be free (avoids TIME_WAIT on restart)
for i in $(seq 1 10); do
    php -r '$s=@fsockopen("127.0.0.1",3000,$e,$m,0.2);if($s===false){exit(0);}fclose($s);exit(1);' && break || true
    sleep 1
done

exec php artisan serve --host=0.0.0.0 --port=3000
