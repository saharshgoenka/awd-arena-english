# Official benchmark run — 2026-07-10

Attack-only sweep of **DeepSeek V4 Pro** and **DeepSeek V4 Flash** across all 9 scenarios
(S1–S9). This folder is the self-contained research artifact for the run.

## What this is

- **Mode:** `attack_only` (target unpatched; agent attacks from black-box start).
- **Window:** 10 min attack / 0 min defense, ≤3 concurrent matches.
- **Models:** `deepseek/deepseek-v4-pro`, `deepseek/deepseek-v4-flash` (via OpenRouter).
- **Scenarios:** S1 NexusBI (Flask) … S9 VaultGate (Actix), each carrying the 5 standardized
  OWASP flag slots (see `docs/research/openclaw-web-security-agents-research-plan.md` §4.2).

## Layout

```
provenance.txt        git commit, host, harness versions, target+oracle image digests, key fingerprint (redacted)
deepseek_v4_pro.tsv   manifest: scenario -> match_id  (pro)
deepseek_v4_flash.tsv manifest: scenario -> match_id  (flash)
sweep_pro.out         full stdout of the pro sweep (launch + collection)
sweep_flash.out       full stdout of the flash sweep
driver.log            top-level driver log (both sweeps + key-scrub pass)
summary.md            per-model, per-scenario, per-flag capture summary
results.json          aggregate results (from collect_results.py), if produced
matches/              one folder per match — the primary artifact (see below)
```

### Per-match folder (`matches/<model>__<Sx>__match_<id>/`)

Everything needed to audit or reproduce a single match:

- `match.json` — referee match record (config, scenario, timing)
- `submissions.json` — every flag submission with success/failure
- `scoring.jsonl` — scoring events
- `events.jsonl` — full referee event stream (untruncated)
- `agent_trajectory.jsonl` — the agent's full reasoning + tool-call trajectory (from the bundle)
- `referee.log` — referee-side log lines for the match
- `bundle.zip` — full player_code_export bundle (target code snapshot, agent session, summaries)
- `summary.md` — human-readable per-match summary

## Provenance & integrity

- Target/oracle image **digests** are pinned in `provenance.txt` (the benchmark version this run
  measured). Rebuilding under `:latest` changes the benchmark — compare digests before comparing runs.
- The OpenRouter API key is **never stored** here; only a 6-char fingerprint is recorded. The driver
  runs a key-scrub pass over all files and warns if any key value survives inside a bundle.

## Caveats (read before citing)

- These are **calibration-grade** results, not the frozen table run. The harness-validity gates in
  `RESEARCH_PLAN.md` §5 (uniform SLA login probe, per-run seed/provider/prompt/scoring logging, pinned
  scoring profile, item-discrimination pass) are **not yet cleared**. Treat per-flag captures as
  calibration evidence.
- Attack windows are not yet frozen (Phase 0.5 pilot pending); 10 min was used as the working default.
- k=1 per (model × scenario). No repeated trials in this run.
