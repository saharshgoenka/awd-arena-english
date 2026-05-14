# OpenClaw upstream image + OpenSSH client for referee `target-ssh` probes and defense prompts.
# Without `ssh`, init fails with TARGET_SSH_CLIENT_MISSING and the arena shows no agent stream.
FROM alpine/openclaw:latest
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends openssh-client \
    && rm -rf /var/lib/apt/lists/*
USER node
