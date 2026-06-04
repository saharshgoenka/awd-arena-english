FROM rust:1-bookworm

# System deps: SSH (target access), supervisor (process mgmt),
# patch (in-container patch application).
RUN apt-get update && apt-get install -y \
    openssh-server \
    supervisor \
    patch \
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

# Build once: this downloads/compiles all crates (incl. bcrypt for the patched
# build) and fills the registry + target caches. start.sh recompiles from
# (possibly patched) source on every restart, offline, using these caches.
COPY . .
RUN cargo build --release && \
    mkdir -p /app/data && \
    chmod +x /app/start.sh

COPY supervisord.conf /etc/supervisor/supervisord.conf

EXPOSE 3000 22

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]
