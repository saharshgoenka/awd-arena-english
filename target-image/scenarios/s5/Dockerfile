FROM eclipse-temurin:21-jdk

# System deps: Maven (for in-container recompile after patch), SSH, supervisor
RUN apt-get update && apt-get install -y \
    maven \
    openssh-server \
    supervisor \
    patch \
    && rm -rf /var/lib/apt/lists/*

# SSH setup
RUN rm -f /etc/ssh/ssh_host_* && \
    ssh-keygen -t rsa -b 2048 -f /etc/ssh/ssh_host_rsa_key -N "" && \
    useradd -m ctf && echo "ctf:ctf" | chpasswd && \
    mkdir -p /var/run/sshd && \
    sed -i 's/#PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config

WORKDIR /app

# Download dependencies before copying source (layer cache)
COPY pom.xml .
RUN mvn dependency:resolve -q

# Copy source and compile
COPY src ./src
RUN mvn package -DskipTests -q

# Copy all remaining files
COPY start.sh flags.yaml hint.md oracle_exploit.py oracle_patch.diff ./
COPY tests/ tests/

RUN mkdir -p /app/data && chmod +x /app/start.sh

COPY supervisord.conf /etc/supervisor/supervisord.conf

EXPOSE 3000 22

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]
