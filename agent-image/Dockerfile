# OpenClaw upstream image + OpenSSH client for referee `target-ssh` probes and defense prompts.
# Without `ssh`, init fails with TARGET_SSH_CLIENT_MISSING and the arena shows no agent stream.
#
# Pinned to alpine/openclaw:2026.5.20 (released 2026-05-21). Previously we tracked
# :latest, which silently floated: matches in a single 2026-05-22 session ran
# against v2026.5.7 *and* v2026.5.20 with subtly different config-handling
# behavior, producing $0-spend def-only matches when the version flipped
# mid-session. Pin prevents that drift; bump deliberately.
FROM alpine/openclaw:2026.5.20
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends openssh-client \
    && rm -rf /var/lib/apt/lists/*
# alpine/openclaw 2026.5.20+ refuses to bind the gateway without an auth token
# ("Refusing to bind gateway to auto without auth"); earlier versions
# auto-generated one. Also crash-loops without `gateway.mode` at all ("Missing
# config. Run `openclaw setup` ..."). The referee patches in the full
# provider/model config via `openclaw config patch --stdin` shortly after the
# container starts (see agent_client.configure_container — which triggers a hot
# reload through OpenClaw's writeConfigFile listener; external `docker cp` is
# invisible to the running gateway). The seed `auth.token` placeholder is a
# bootstrap value the referee overwrites; the gateway is on an isolated
# per-match Docker network so it's never reachable externally.
RUN mkdir -p /home/node/.openclaw \
    && printf '{\n  "gateway": {\n    "mode": "local",\n    "auth": { "mode": "token", "token": "bootstrap-placeholder-replaced-by-referee" }\n  }\n}\n' > /home/node/.openclaw/openclaw.json \
    && chown -R node:node /home/node/.openclaw
USER node
