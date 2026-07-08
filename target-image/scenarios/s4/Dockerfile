FROM php:8.2-cli

RUN apt-get update && apt-get install -y \
    openssh-server \
    supervisor \
    unzip \
    git \
    patch \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# PHP extensions
RUN docker-php-ext-install pdo pdo_sqlite

# Composer
COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

# SSH setup
RUN rm -f /etc/ssh/ssh_host_* && \
    ssh-keygen -t rsa -b 2048 -f /etc/ssh/ssh_host_rsa_key -N "" && \
    useradd -m ctf && echo "ctf:ctf" | chpasswd && \
    mkdir -p /var/run/sshd && \
    sed -i 's/#PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config

WORKDIR /app
COPY . .

RUN composer install --no-dev --optimize-autoloader

RUN mkdir -p /app/data \
             /app/storage/framework/sessions \
             /app/storage/framework/views \
             /app/storage/framework/cache/data \
             /app/storage/app \
             /app/storage/logs \
             /app/bootstrap/cache && \
    chmod -R 777 /app/storage /app/bootstrap/cache && \
    chmod +x /app/artisan /app/start.sh && \
    php artisan key:generate --force

RUN rm -f /app/public/.env

COPY supervisord.conf /etc/supervisor/supervisord.conf

EXPOSE 3000 22

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]
