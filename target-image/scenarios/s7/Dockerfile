FROM golang:1.25-bookworm

# System deps: SSH (target access), supervisor (process mgmt),
# patch (in-container patch application), sqlite3 (debugging).
RUN apt-get update && apt-get install -y \
    openssh-server \
    supervisor \
    patch \
    sqlite3 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# SSH setup
RUN rm -f /etc/ssh/ssh_host_* && \
    ssh-keygen -t rsa -b 2048 -f /etc/ssh/ssh_host_rsa_key -N "" && \
    useradd -m ctf && echo "ctf:ctf" | chpasswd && \
    mkdir -p /var/run/sshd && \
    sed -i 's/#PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config

WORKDIR /app

# Copy source, resolve deps (incl. golang.org/x/crypto kept via tools.go for the
# patched build), populate the module cache, and compile once. start.sh rebuilds
# from (possibly patched) source on every restart, offline, using this cache.
ENV GOFLAGS=-mod=mod
COPY . .
RUN go get modernc.org/sqlite golang.org/x/crypto/bcrypt && \
    go mod tidy && \
    go build -o /app/server . && \
    mkdir -p /app/data && \
    chmod +x /app/start.sh

COPY supervisord.conf /etc/supervisor/supervisord.conf

EXPOSE 3000 22

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]
