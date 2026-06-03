FROM ruby:3.2-slim

RUN apt-get update && apt-get install -y \
    openssh-server supervisor sqlite3 libsqlite3-dev \
    build-essential git curl libyaml-dev && \
    rm -rf /var/lib/apt/lists/*

RUN rm -f /etc/ssh/ssh_host_* && \
    ssh-keygen -t rsa -b 2048 -f /etc/ssh/ssh_host_rsa_key -N "" && \
    useradd -m ctf && echo "ctf:ctf" | chpasswd && \
    mkdir -p /var/run/sshd

WORKDIR /app
COPY Gemfile ./
RUN bundle config set --local without 'development test' && bundle install

COPY . .
RUN mkdir -p /app/bin && \
    printf '#!/usr/bin/env ruby\nAPP_PATH = File.expand_path("../config/application", __dir__)\nrequire_relative "../config/boot"\nrequire "rails/commands"\n' > /app/bin/rails && \
    chmod +x /app/bin/rails /app/start.sh && \
    mkdir -p /app/data

COPY supervisord.conf /etc/supervisor/supervisord.conf

EXPOSE 3000 22

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]
