# AWD Arena AAAI-27 Action Plan

**Goal:** Submit a reproducible AAAI-27 Main Track paper on whether repeated
isolated security-agent profiles predict sequential AWD outcomes.

**Submission deadlines:** abstract registration July 21, 2026; full paper July
28; supplementary code/data July 31 (all Anywhere on Earth).

**Locked paper-facing name:** **AWD Arena**. The implementation repository may
remain named OpenClaw, but the manuscript must not present “OpenClaw” as the
benchmark name.

## 1. Frozen study

### Models and targets

- Models: `minimax_m3`, `deepseek_v4_pro`, `deepseek_v4_flash`,
  `glm_4_5_air`.
- Isolated targets: S1–S9.
- AWD targets: S1, S5, S7.
- AWD format: sequential patch-then-attack. Do not call it simultaneous
  adaptive defense.

### Run budget

| Arm | New jobs | Expected normal cost |
| --- | ---: | ---: |
| Fresh isolated attack and defense repeats | 144 | $17.63 |
| AWD round robin, 6 pairs × 3 targets × k=3 | 54 | $26.45 |
| Core study | 198 | $44.08 |
| Invalid-run reserve | — | $5.92 |

No additional model, target, pairing, or post-hoc replication is authorized
from the reserve. The reserve is only for runs that fail the frozen validity
criteria below.

### Frozen validity and retry rule

A run is invalid and may consume one retry only when it has a provider error,
empty-assistant failure, configuration/init failure, missing required telemetry,
or timeout/DNF caused by the harness rather than a completed agent trajectory.
Completed low-score trajectories are valid results. Record every invalid attempt
and reason; do not silently replace it.

## 2. Pre-run engineering gate — July 15–16

1. Record target image digest, agent image digest, referee Git commit, prompt
   hash, scoring profile, requested model slug, actual provider/model routing,
   decoding settings/seed if supported, and run-order index for every new run.
2. Dry-run one isolated attack, one isolated defense, and one AWD match. Confirm
   that submissions, oracle summary, authenticated SLA, target digests, events,
   and cleanup artifacts are persisted.
3. Measure OpenRouter credit delta for the first representative isolated and AWD
   runs. Recalculate the projected total before launching the bulk schedule.
4. Freeze the target digests, prompts, model roster, windows, scoring, and the
   random order manifest. Commit the manifest and metadata schema before the
   first table-producing run.

**Go/no-go:** stop the campaign if the revised normal-case projection exceeds
$50 or required routing/telemetry cannot be captured. Do not collect a paper
table that cannot identify the experimental condition.

## 3. Run campaign — July 16–19

### Isolated profile runs

Launch two fresh attack-only and two fresh defense-only trials for each selected
model × S1–S9 cell. Keep concurrency at or below three active matches. On every
terminal run, collect artifacts and remove leaked containers before launching
the next queued job.

### AWD runs

For every unordered model pair, run S1, S5, and S7 three times:

```text
MiniMax–Pro, MiniMax–Flash, MiniMax–GLM,
Pro–Flash, Pro–GLM, Flash–GLM
× S1, S5, S7 × repetition 1, 2, 3.
```

Randomize job order subject to the concurrency cap. A single AWD match supplies
both attack directions; do not add redundant side-swap matches.

### Continuous checks

- Reconcile submission counts with final score after each batch.
- Mark provider/runtime failures immediately; do not treat zeroes as model
  failures until logs establish a completed trajectory.
- Track actual spend against the $50 ceiling after each batch.
- Preserve all attempts, including invalid ones, in the run ledger.

## 4. Frozen analysis — July 19–21

1. Build fresh-run isolated means \(\bar A_{m,s}\) and \(\bar D_{m,s}\) from the
two new repeats; use the original exploratory run only for sensitivity analysis.
2. For each AWD target, compute the preregistered strength index
   \(Q_{m,s}=z(\bar A_{m,s})+z(\bar D_{m,s})\) and pairwise prediction
   \(P_{i,j,s}=Q_{i,s}-Q_{j,s}\).
3. Compute three frozen competing predictors: attack-only, clean-defense-only,
   and combined \(Q\). Do not select weights after observing AWD results.
4. Report all 54 AWD trials and 18 pairing × target cell means. Report
   within-cell variation, cell-level direction accuracy, scenario-stratified
   outcomes, raw-versus-clean-defense sensitivity, and descriptive four-model
   aggregate ranks.
5. Treat a predicted tie as exactly \(P=0\), and an observed tie as exactly zero
   net-score differential. Do not create a near-tie threshold after inspection.
6. Classify prediction failures with the frozen taxonomy: attacker adaptation,
   service-breaking defense, brittle-block signal, discovery failure, timeout/
   DNF, provider/tool/platform failure, or unresolved.

**Interpretation rule:** the combined predictor supports H2 only if it has higher
direction accuracy than both single-axis predictors on the 18 cell means and
does not reverse that advantage in two or more target strata. Otherwise label
the result contradictory or inconclusive; do not retrofit the claim.

## 5. Manuscript and release — July 16–28, in parallel

### Paper narrative

Lead with: “Do isolated security-agent evaluations predict sequential AWD
outcomes?” Present authenticated SLA as what prevents a malformed defense
measurement from contaminating that test.

Do not lead with any of these:

- first A/D arena;
- simultaneous adaptive defense;
- framework/language causal effects;
- universal cybersecurity capability ranking;
- cost leaderboard;
- proof of root-cause repair.

### Required 7-page contents

1. Motivation and contribution: isolated-to-AWD measurement validity.
2. Apparatus and sequential threat model.
3. Frozen design, selection boundary, validity rule, and predictor baselines.
4. Isolated profile and raw-versus-clean-defense results.
5. AWD k=3 results, prediction comparison, and failure cases.
6. Related work and limits.

Put exhaustive run tables, trajectories, prompt text, full artifacts, and
implementation details in the supplement, but retain all results critical to
the conclusion in the seven-page main paper.

### Related-work positioning

- Position Cybersecurity AI A/D CTFs and CAIBench as A/D and service-check
  predecessors.
- Position CTFTiny/CTFJudge, MCP-AgentBench, MetaEval, and Lost in Benchmarks?
  as AAAI-style measurement/benchmark precedents.
- Position AgentCyberRange, ExploitBench, and CyberExplorer as recent offensive
  benchmarks that outscale AWD Arena in realism or task volume but do not ask
  the isolated-to-AWD transfer question.

### Submission checklist

- Register a non-placeholder abstract by July 21.
- Complete a reproducibility checklist and prepare redacted code/data archive.
- Include image digests, prompts, model/provider metadata, run manifest,
  scoring, validity labels, and scripts needed to recreate tables.
- Redact API keys, flags, and real credentials.
- Submit the paper by July 28 and supplementary material by July 31.

## 6. Decision gates

### July 16: instrumentation gate

Proceed only if pilot runs capture required metadata and projected spend is at
most $50.

### July 20: evidence gate

Proceed with the predictive-validity headline only if enough valid AWD cells
remain to report all pairings × targets × repetitions transparently. If provider
or harness failures erase a material portion of the matrix, narrow the paper to
measurement validity and reliability rather than imply a complete tournament.

### July 25: submission gate

Submit only if the main paper contains the complete experimental condition,
validity handling, core tables/figures, and limitations without requiring a
reviewer to inspect the supplement. Otherwise preserve the experiment and
target a later archival cycle rather than rush unsupported claims.
