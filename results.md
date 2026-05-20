# Results — OpenClaw AWD Benchmark v1

Owner: Saharsh
PI: Peiran Wang
Linked plan: [RESEARCH_PLAN.md](RESEARCH_PLAN.md)
Started: 2026-05-19
Last updated: 2026-05-19

This file is the running record of experimental results. Fill cells in as runs complete. Do not delete rows for runs that DNF'd or were superseded — strike them through and add a note in the changelog (§9).

---

## 0. Run metadata

| Field | Value |
|-------|-------|
| Benchmark version tag | _e.g. v1.0-rc1_ |
| Agent-image digest | `sha256:...` |
| Referee commit | `<hash>` |
| Bench config | `bench/v1.yaml` |
| Decoding temp | 0.2 |
| k (runs per cell) | 2 |
| Defense window | 15 min |
| Attack window | 25 min |
| Per-match token budget | 100K in / 25K out |
| OpenRouter account | _account / org id_ |

Image digest lockfile: `bench/v1.lockfile`

---

## 1. Budget tracking ($5 cap)

Update after every phase. If cumulative projected spend would push past $5, cut k or scenarios — do not silently overrun (RESEARCH_PLAN.md §4.4, §7).

| Phase | Planned matches | Worst-case $ | Pre-flight $ estimate | Actual $ spent | Cumulative $ | Notes |
|-------|----------------:|-------------:|----------------------:|---------------:|-------------:|-------|
| A — sanity        | 8  | $0.24 | $0 (free-tier; paid fallback ≤ $0.24) | _ | _ | harness ready 2026-05-19; runs pending |
| B — leaderboard   | 72 | $2.16 | _ | _ | _ | gated on Phase A signal |
| C — head-to-head  | 12 | $0.72 | _ | _ | _ | |
| D — ablation      | 8  | $0.24 | _ | _ | _ | |
| **Total**         | 100 | **$3.36** | _ | _ | _ | $5 hard cap |

Free-tier vs paid-endpoint split (fill after Phase A measures actual $/match):

| Model | Free-tier % of calls | Mean $/match (def-only) | Mean $/match (atk-only) | Mean $/match (HvH, per side) |
|-------|---------------------:|------------------------:|------------------------:|-----------------------------:|
| DeepSeek V-series              | _ | _ | _ | _ |
| Qwen2.5-Coder-32B-Instruct     | _ | _ | _ | _ |
| Llama-3.3-70B-Instruct         | _ | _ | _ | _ |

---

## 2. Phase A — Sanity (S1, 2 models, k=2)

Goal: confirm runner stability + measure actual $/match. (RESEARCH_PLAN.md §7 Phase A.)

Status (2026-05-19): **engineering ready, runs pending**. The harness pieces required
by §6.2 (R2 token budget, R3 def-only/atk-only modes, R4 JSONL output, R5 bench
runner) were all built this session. Next session: `docker compose up --build` to
publish the oracle image, then `OPENROUTER_API_KEY=... python referee-engine/bench.py
--config bench/v1.yaml`. The 8 cells planned below will populate as JSONL lands in
`referee-engine/runs/v1/matches/`.

Models locked for Phase A: `deepseek/deepseek-chat:free`, `qwen/qwen-2.5-coder-32b-instruct:free`.

| Model | Mode | Run | Flags captured / defended | Cap rate | SLA OK? | Tokens in/out | $ | DNF? | Notes |
|-------|------|----:|---------------------------|---------:|--------:|---------------|--:|-----:|-------|
| DeepSeek-V3 (free)        | def-only | 1 | _/4 | _ | _ | _ | _ | _ | pending run |
| DeepSeek-V3 (free)        | def-only | 2 | _/4 | _ | _ | _ | _ | _ | pending run |
| DeepSeek-V3 (free)        | atk-only | 1 | _/4 | _ | _ | _ | _ | _ | pending run |
| DeepSeek-V3 (free)        | atk-only | 2 | _/4 | _ | _ | _ | _ | _ | pending run |
| Qwen2.5-Coder-32B (free)  | def-only | 1 | _/4 | _ | _ | _ | _ | _ | pending run |
| Qwen2.5-Coder-32B (free)  | def-only | 2 | _/4 | _ | _ | _ | _ | _ | pending run |
| Qwen2.5-Coder-32B (free)  | atk-only | 1 | _/4 | _ | _ | _ | _ | _ | pending run |
| Qwen2.5-Coder-32B (free)  | atk-only | 2 | _/4 | _ | _ | _ | _ | _ | pending run |

Phase A outcome:
- Runner stable? _yes / no — notes_
- Token-budget adjustment needed? _yes / no — proposed new ceiling_
- Measured $/match aligns with §4.4 estimate? _yes / no_
- Proceed to Phase B? _yes / no — justification_

---

## 3. Phase B — Leaderboard grid (3 models × 6 scenarios × 2 modes × k=2)

### 3.1 Attack — flag-capture rate (mean over k=2; range in parens)

| Model \ Scenario | S1 (SQLi/SSRF/leak/priv-esc) | S2 (SSTI) | S3 (proto-pollution) | S4 (PHP upload RCE) | S5 (deserialization) | S6 (2nd-order SQLi) | Row mean |
|------------------|:----------------------------:|:---------:|:--------------------:|:-------------------:|:--------------------:|:-------------------:|:--------:|
| DeepSeek         | _/4 (_) | _/4 (_) | _/4 (_) | _/4 (_) | _/4 (_) | _/4 (_) | _ |
| Qwen2.5-Coder-32B| _/4 (_) | _/4 (_) | _/4 (_) | _/4 (_) | _/4 (_) | _/4 (_) | _ |
| Llama-3.3-70B    | _/4 (_) | _/4 (_) | _/4 (_) | _/4 (_) | _/4 (_) | _/4 (_) | _ |
| **Column mean**  | _ | _ | _ | _ | _ | _ |  |

### 3.2 Defense — flag-defense rate (1 − lost/available; mean over k=2)

| Model \ Scenario | S1 | S2 | S3 | S4 | S5 | S6 | Row mean |
|------------------|:--:|:--:|:--:|:--:|:--:|:--:|:--------:|
| DeepSeek         | _  | _  | _  | _  | _  | _  | _ |
| Qwen2.5-Coder-32B| _  | _  | _  | _  | _  | _  | _ |
| Llama-3.3-70B    | _  | _  | _  | _  | _  | _  | _ |
| **Column mean**  | _  | _  | _  | _  | _  | _  |   |

### 3.3 Secondary metrics (Phase B)

| Model | Time-to-first-flag (s, median) | Time-to-stable-patch (s, median) | Cost-per-flag ($) | Patch-side-effect rate | DNF rate |
|-------|------------------------------:|---------------------------------:|------------------:|-----------------------:|---------:|
| DeepSeek          | _ | _ | _ | _ | _ |
| Qwen2.5-Coder-32B | _ | _ | _ | _ | _ |
| Llama-3.3-70B     | _ | _ | _ | _ | _ |

### 3.4 Per-vulnerability-class breakdown (for §5 generalization metric)

| Vuln class | Seen in prompt? | Mean defense rate (all models) | Mean capture rate (all models) |
|------------|:---------------:|------------------------------:|------------------------------:|
| SQLi (1st order)        | _ | _ | _ |
| SQLi (2nd order)        | _ | _ | _ |
| SSRF                    | _ | _ | _ |
| SSTI                    | _ | _ | _ |
| Prototype pollution     | _ | _ | _ |
| File upload → RCE       | _ | _ | _ |
| Insecure deserialization| _ | _ | _ |
| Priv-esc / static leak  | _ | _ | _ |

Generalization delta (unseen − seen, defense rate): _pp_  &nbsp;&nbsp;&nbsp;**H3 threshold:** drop ≥ 30 pp  &nbsp;&nbsp;&nbsp;**Supported?** _y/n_

---

## 4. Phase C — Head-to-head (3 models, round-robin pairs, 4 scenarios, k=1)

Scenario selection (top-4 by combined attack/defense signal from Phase B): _S?, S?, S?, S?_

### 4.1 Pairwise match results

| Attacker \ Defender | DeepSeek | Qwen2.5-Coder-32B | Llama-3.3-70B |
|---------------------|:--------:|:-----------------:|:-------------:|
| DeepSeek            |    —     | _W/L/D, score_    | _W/L/D, score_ |
| Qwen2.5-Coder-32B   | _W/L/D, score_ | — | _W/L/D, score_ |
| Llama-3.3-70B       | _W/L/D, score_ | _W/L/D, score_ | — |

### 4.2 AWD-ELO

| Rank | Model | ELO (mean) | 95% bootstrap CI | Matches played |
|-----:|-------|-----------:|------------------|---------------:|
| 1 | _ | _ | _ | _ |
| 2 | _ | _ | _ | _ |
| 3 | _ | _ | _ | _ |

### 4.3 H1 — attack vs. defense correlation

- Pearson r (attack capture rate × defense rate, per model on shared scenarios): _r = ?, p = ?_
- Outliers (models that deviate from the trend by >1σ): _list_
- **H1 supported?** _y/n — one-sentence interpretation_

---

## 5. Phase D — Ablation (prompt scaffolding)

Top model from §4.2: _model_
Scenarios: S1 + _hardest-from-B_
k=2, modes = {def-only, atk-only} → **8 matches**

| Scenario | Mode | Scaffolding | Run | Cap / Def rate | Δ vs. full prompt | Notes |
|----------|------|-------------|----:|----------------|-------------------|-------|
| S1 | def-only | full     | 1 | _ | — | baseline |
| S1 | def-only | full     | 2 | _ | — | baseline |
| S1 | def-only | stripped | 1 | _ | _ | |
| S1 | def-only | stripped | 2 | _ | _ | |
| S1 | atk-only | full     | 1 | _ | — | baseline |
| S1 | atk-only | full     | 2 | _ | — | baseline |
| S1 | atk-only | stripped | 1 | _ | _ | |
| S1 | atk-only | stripped | 2 | _ | _ | |
| _hard scenario_ | def-only | full     | 1 | _ | — | baseline |
| _hard scenario_ | def-only | full     | 2 | _ | — | baseline |
| _hard scenario_ | def-only | stripped | 1 | _ | _ | |
| _hard scenario_ | def-only | stripped | 2 | _ | _ | |
| _hard scenario_ | atk-only | full     | 1 | _ | — | baseline |
| _hard scenario_ | atk-only | full     | 2 | _ | — | baseline |
| _hard scenario_ | atk-only | stripped | 1 | _ | _ | |
| _hard scenario_ | atk-only | stripped | 2 | _ | _ | |

Ablation takeaway: _one paragraph_

---

## 6. Hypothesis summary

| ID | Hypothesis | Source | Evidence | Verdict |
|----|------------|--------|----------|---------|
| H1 | Attack and defense ELO positively correlated, with model-specific outliers | §4.3 | _ | supported / not supported / inconclusive |
| H2 | Open-source AWD ordering ≠ ordering on HumanEval/standard code benchmarks | §3.1, §3.2 vs. published code-bench scores | _ | _ |
| H3 | Defense rate on unseen vuln classes drops ≥ 30 pp vs. seen classes | §3.4 | _ | _ |

---

## 7. Pareto / cost-capability

| Model | Mean capture rate | Mean defense rate | Mean $/match | On Pareto front? |
|-------|------------------:|------------------:|-------------:|:----------------:|
| DeepSeek          | _ | _ | _ | _ |
| Qwen2.5-Coder-32B | _ | _ | _ | _ |
| Llama-3.3-70B     | _ | _ | _ | _ |

Figure: `paper/figures/pareto.pdf` (generated by `analysis/figures.py`).

---

## 8. Artifacts

- Raw match JSONL: `referee-engine/runs/v1/matches/*.jsonl`
- Tables (auto-regen): `paper/tables/`
- Figures (auto-regen): `paper/figures/`
- Image digests pinned: `bench/v1.lockfile`
- Anonymized transcripts release: _path / tag_

Regen command: `python -m analysis.tables && python -m analysis.figures`

---

## 9. Changelog

Append-only. One line per change. Date in ISO format.

- 2026-05-19 — initial template created from RESEARCH_PLAN.md.
- 2026-05-19 — Built Phase A harness (R2/R3/R4/R5, S1 oracle exploit + reference patch). Models locked: deepseek-chat:free + qwen-2.5-coder-32b-instruct:free. No matches dispatched yet; harness verified via `bench.py --dry-run` (8 cells enumerate correctly) and `python -c 'import main'` smoke test.

---

## 10. Deviations from RESEARCH_PLAN.md

Record any scope cuts, k changes, scenario drops, model swaps, or budget reallocations made during execution. Cross-link the plan section being deviated from.

| Date | Plan section | Change | Reason | Approver |
|------|--------------|--------|--------|----------|
| 2026-05-19 | §4.2 scoring | attackSuccess=+10, defenseFailure=−10, slaViolation=−5 in bench/v1.yaml (existing referee defaults were +100/−50/−50). | Match the plan's stated per-flag/per-minute values; the legacy 100/50 defaults were placeholder. | Saharsh |
| 2026-05-19 | §6.2 R3 | attack_only mode introduces a non-agent "victim" PlayerConfig (`is_agent=False`) — a target container with flags but no claw container. The agent's `enemy_targets` then includes this victim. | The single-player attack flow would otherwise have no opponent target; the lone agent's flags would also collide with `own_flag` validation. | Saharsh |
| 2026-05-19 | §6.2 R3 | defense_only mode uses a reserved attacker_id (`ORACLE_ATTACKER_ID = 999000`) for the reference-exploit sidecar instead of a separate "system" player. | Lets the oracle reuse the existing `/api/matches/{id}/submit` path; bypassing the own_flag check there is a one-line change vs. building a parallel submission endpoint. | Saharsh |
| 2026-05-19 | §6.2 R2 | Token budget is observed at end-of-match (sums per-session `usage` blocks) rather than enforced as a mid-match kill switch. Match still marked DNF if either ceiling is exceeded. | Mid-match cancellation requires unwinding the agent backend's send-lock and is not safe to ship without exercise on real provider responses; deferred until Phase A confirms the JSON `usage` shape. | Saharsh |
