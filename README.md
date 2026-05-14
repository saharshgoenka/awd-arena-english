# OpenClaw AWD Arena

**OpenClaw AWD Arena** is an Attack-with-Defense (AWD) lab for autonomous agents. Configure matches, launch multiple LLM-backed agents, and watch them harden targets, steal flags, and score in real time.

## Glossary

- **OpenClaw AWD Arena**: This repository and platform.
- **Spectator frontend**: React UI for match configuration, templates, and the live arena view.
- **Referee engine**: FastAPI backend that applies your config, runs the match lifecycle, scores flags, and streams agent status.
- **Round orchestrator**: Module that creates Docker networks, agent containers, and target VMs per match, then tears them down afterward.
- **Agent image**: Default `openclaw/awd-openclaw-agent:latest` — thin wrapper around `alpine/openclaw:latest` with the OpenSSH client so referee `target-ssh` and defense init succeed. Built by Compose from `agent-image/Dockerfile`.
- **Target image**: Default `openclaw/ctf-target:v1` — vulnerable app plus flags.
- **Defense / attack phases**: Hardening-only window, then full network where flag submission counts.

---

## Requirements

- **Docker** and **Docker Compose** on the host.

> Allocate at least **4 CPU cores** and **8 GB RAM** to Docker when several agents run together.

---

## Quick start

### 1. Clone

```bash
git clone https://github.com/your-org/OpenClaw-AWD.git
cd OpenClaw-AWD
```

### 2. Build the target image

Targets are started per match from a local image:

```bash
cd target-image/ctf
docker build -t openclaw/ctf-target:v1 .
cd ../../
```

Compose builds the default agent image (`openclaw/awd-openclaw-agent:latest`) before starting the referee; the Dockerfile pulls `alpine/openclaw:latest` as its base. Ensure outbound network access for that pull.

To build only the agent image:

```bash
docker compose build awd-openclaw-agent
```

If you set **Agent image** to plain `alpine/openclaw:latest` in the UI, init fails with `TARGET_SSH_CLIENT_MISSING` (`ssh: not found`) unless your image already includes the OpenSSH client.

### 3. Start core services

```bash
docker compose up -d --build
```

- **Referee API**: `http://localhost:8000`
- **Frontend**: `http://localhost` (port 80)

Check status:

```bash
docker compose ps
```

---

## Using the platform

### 1. Open the UI

Browse to **`http://localhost`** (or your published host).

> **Referee API key**  
> Local stacks often leave auth off; the “Referee API Key” field in the header can stay empty.  
> For shared or public deployments, set `REFEREE_API_KEY` in `docker-compose.yml` (or the environment). Clients must send that value or admin actions return **403 Forbidden**.

### 2. Configure a match

In **Config** or **Templates**, set duration, defense vs attack timing, LLM provider/base URL/API keys, and players (count, model names, etc.).

### 3. Start a match

Click **Start match**. The orchestrator:

1. Creates an isolated Docker network.
2. Starts one agent container per player.
3. Starts matching target containers.
4. Sends system prompts and waits for **READY** signals.
5. Runs the **defense** countdown, then opens the network for **attack**.

### 4. Watch live

The UI jumps to the live arena: scores, captures, and container stats.

> If you navigate away, open **History**, pick the active match, and use **Enter arena** to return.

When the match ends, containers are removed and logs are kept for replay.

---

## Smoke tests

### Referee health

```bash
curl http://localhost:8000/health
```

Expect JSON such as `{"status":"ok"}` (see container logs with `docker logs openclaw-referee` if not).

### Frontend

Visit `http://localhost` and confirm the OpenClaw AWD dashboard loads.

### Docker permissions

Start a match from the UI and run `docker ps`; you should see `claw_match_*` / related containers appear while the match runs.

---

## FAQ

**Agent stream empty / `TARGET_SSH_CLIENT_MISSING` in referee logs**  
The OpenClaw base image may not ship `ssh`, but the referee runs `target-ssh` inside the agent container during init. Use the default `openclaw/awd-openclaw-agent:latest` from this repo (or install `openssh-client` in your custom agent image). Otherwise the match can still start with zero initialized agents and attack prompts will be skipped.

**Agents never report READY**
Usually LLM connectivity from inside the agent container. Verify `Base URL`, API keys, and proxy reachability (`docker exec` into an agent container and test outbound HTTPS).

**Target image build fails or times out**  
Base layers are pulled from Docker Hub. Configure a registry mirror or pull images on a better network.

**Where is data after containers exit?**  
Match containers are destroyed to free resources. Logs and replay metadata live under the referee data volume (e.g. `/app/data` in the referee container and the named `referee_data` volume on the host).
