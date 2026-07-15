# Sample Rounds

Use `referee-engine/sample_runner.py` when you want to launch one scenario
without hand-writing the `/api/matches/start` payload. The runner reads
`bench/samples.yaml`, injects your OpenRouter key, and prints the match id plus
local UI/API links.

## Setup

```bash
docker compose up -d --build
echo 'openrouter=YOUR_OPENROUTER_KEY' > .env
```

Either `openrouter` or `OPENROUTER_API_KEY` works. If the referee is protected,
also export `REFEREE_API_KEY`; the runner forwards it as `X-API-Key`.

## Dry Run

Preview the request body without spending tokens:

```bash
python3 referee-engine/sample_runner.py S1 --dry-run
```

## Launch a Round

Default head-to-head:

```bash
python3 referee-engine/sample_runner.py S1
```

This starts S1 with DeepSeek V4 Flash vs Llama 4 Scout, 10 minutes of defense
and 10 minutes of attack.

Useful overrides:

```bash
# Short smoke test.
python3 referee-engine/sample_runner.py S1 --defense-minutes 3 --attack-minutes 3

# Attack-only sample: one agent attacks an unpatched victim target.
python3 referee-engine/sample_runner.py S1 \
  --mode attack_only \
  --model-a llama_4_scout \
  --defense-minutes 0 \
  --attack-minutes 5

# Defense-only sample: one agent defends, then the scenario oracle probes it.
python3 referee-engine/sample_runner.py S1 \
  --mode defense_only \
  --model-a deepseek_v4_flash \
  --defense-minutes 10 \
  --attack-minutes 10

# Swap the head-to-head roster.
python3 referee-engine/sample_runner.py S1 \
  --mode head_to_head \
  --model-a deepseek_v4_flash \
  --model-b llama_4_scout
```

## Sample Registry

`bench/samples.yaml` contains the friendly defaults:

- `defaults`: match durations, scoring, flag refresh, token budgets, and LLM
  provider settings.
- `scenarios`: scenario ids such as `S1` through `S9`, with `target_image` and
  optional `oracle_image`.
- `models`: short ids such as `deepseek_v4_flash` and `llama_4_scout` mapped to
  OpenRouter model slugs.

To add a sample, add a scenario entry with its built Docker image:

```yaml
scenarios:
  S10:
    target_image: example-s10:latest
    oracle_image: example-oracle-s10:latest
    description: Example target.
```

Then rebuild the stack so Docker has the image locally:

```bash
docker compose up -d --build
```

## Watch and Inspect

```bash
# UI
open http://localhost

# API snapshot
curl -s http://localhost:8000/api/matches/<match_id> | python3 -m json.tool

# Referee logs for one match
docker logs -f openclaw-referee 2>&1 | grep <match_id>
```

Stop a match early:

```bash
curl -X POST http://localhost:8000/api/matches/<match_id>/end
```

## Troubleshooting

If a scenario shows symmetric SLA loss, check whether its login route matches the
referee's sample SLA probe. S7, S8, and S9 require POST login probes rather than
the default GET `/login` behavior.

If the runner cannot read `bench/samples.yaml` on the host, install PyYAML or
run it inside the referee container. The runner has built-in defaults for the
standard S1-S9 registry, but the YAML file is the source of truth for local
custom samples.
