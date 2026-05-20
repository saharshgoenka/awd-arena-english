# OpenClaw upstream image + OpenSSH client for referee `target-ssh` probes and defense prompts.
# Without `ssh`, init fails with TARGET_SSH_CLIENT_MISSING and the arena shows no agent stream.
FROM alpine/openclaw:latest
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends openssh-client \
    && rm -rf /var/lib/apt/lists/*
# Newer alpine/openclaw revisions refuse to start without an explicit config and
# crash-loop with "Missing config. Run `openclaw setup` or set gateway.mode=local
# (or pass --allow-unconfigured)." The referee pushes the full provider/model
# config via `docker cp` shortly after the container starts (see
# agent_client.configure_container), but that needs the daemon alive in the
# meantime. Seed a minimal `{ gateway: { mode: "local" } }` so the daemon boots;
# the referee then overwrites this file in-place with the real config.
RUN mkdir -p /home/node/.openclaw \
    && printf '{\n  "gateway": { "mode": "local" }\n}\n' > /home/node/.openclaw/openclaw.json \
    && chown -R node:node /home/node/.openclaw
USER node
