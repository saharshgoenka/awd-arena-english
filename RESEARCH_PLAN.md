# Research Plan: Do Isolated Security-Agent Evaluations Predict AWD Outcomes?

**Project:** AWD Arena (implemented in the OpenClaw repository)
**Target venue:** AAAI-27 Main Technical Track
**Status (2026-07-15):** apparatus and exploratory grid complete; confirmatory
calibration and AWD-validation phases planned, not yet run.

This document distinguishes the already-observed exploratory evidence from the
pre-specified validation study. It is the single source of truth for the paper
claim, experimental protocol, and reporting boundaries.

---

## At a glance: paper, experiment, and deliverables

### The paper in one paragraph

This paper asks a narrow but useful evaluation question: **do isolated
attack-only and service-preserving defense-only evaluations predict how models
perform when they face each other's patched targets?** We use AWD Arena—a
controlled, symmetric, sequential patch-then-attack web-security testbed—to
estimate isolated profiles, freeze a simple prediction before any interactive
outcomes are visible, and test that prediction in a balanced round robin. The
paper does not claim to introduce the first attack/defense arena or to measure
real-world cyber capability.

### Contributions

1. **A controlled predictive-validity protocol.** Repeated isolated attack and
   defense measurements are converted into a frozen, pre-match prediction and
   tested against a balanced AWD tournament rather than assumed to transfer.
2. **Service-preserving defense measurement.** Defense is evaluated using flag
   protection *and* authenticated functional SLA checks, separating a genuine
   patch from a service-breaking apparent defense.
3. **A transparent AWD evaluation artifact.** Nine matched containerized web
   tasks, canonical and mutation oracle checks, run-level telemetry, explicit
   invalid-run rules, and a full outcome ledger make both transfer successes
   and failures inspectable.
4. **An empirical result with bounded interpretation.** The study will show
   whether isolated attack/defense profiles transfer within this controlled task
   family, whether raw versus SLA-clean defense changes the conclusion, and
   which observable failure modes explain disagreement.

### Experiment structure

| Stage | Purpose | Design | Output used by the paper |
| --- | --- | --- | --- |
| Exploratory grid — complete | Map the task space and select models | 8 models × 9 scenarios × attack-only/defense-only, k=1 | Descriptive landscape and frozen selection record; not confirmatory evidence |
| Fresh isolated calibration — planned | Estimate predictor inputs without reusing the selection run | 4 selected models × 9 scenarios × 2 modes × 2 fresh repeats = **144 runs** | Attack, clean-defense, reliability, and raw-to-clean-defense profiles |
| Predictor freeze | Prevent tuning to tournament results | Hash scenario-level attack-only, defense-only, and combined predictor tables for S1/S5/S7 | Predeclared AWD win/tie/loss predictions |
| Balanced AWD validation — planned | Test whether isolated profiles transfer | 4 models, all 6 pairs × S1/S5/S7 × 3 randomized rounds = **54 matches** | 18 cell means, within-cell variation, and 27 appearances/model |
| Analysis and release | Make the claim auditable | Predeclared baselines, validity ledger, figures, trace coding | Manuscript, result tables/figures, and reproducibility package |

The primary inferential unit is the **18 pairing × scenario cell means**; the
three matches per cell quantify match variability. Model-level tournament ranks
use 27 balanced appearances per model and are explicitly descriptive (n=4).

### Deliverables

At PI handoff, the project delivers:

- A rough AAAI manuscript that clearly separates exploratory and confirmatory
  evidence.
- A frozen run manifest, predictor table/hash, complete match/validity ledger,
  and cost/retry record.
- Core figures and tables: isolated profiles, raw-versus-clean defense,
  AWD round robin, predictor comparison, and failure taxonomy.
- A reproducibility package containing scenario/oracle/SLA contracts, prompts,
  scoring configuration, image digests, run metadata, and analysis inputs.
- A one-page result summary stating the supported claim, uncertainty, and
  limitations.

The detailed protocol, operational gates, analysis rules, and calendar appear
in Sections 5–12 below. No confirmatory or AWD run has been launched as of this
plan's status date.

---

## 1. Detailed thesis and claim boundaries

Security-agent evaluations are commonly decomposed into attack-only and
defense-only tasks. It is unknown whether those isolated measurements predict
relative performance when agents face another agent's model-patched target.

**Central question.** Given repeated isolated attack and clean-defense profiles,
can we predict the relative outcomes of balanced attack-with-defense (AWD)
matches?

AWD Arena is the controlled measurement apparatus, not the contribution by
itself. It provides matched vulnerable web applications, private oracle
validation, authenticated functional SLA probes, and run-level telemetry. The
contribution is a decomposition-and-validation protocol: estimate isolated
profiles, freeze the prediction rule, then test it in balanced AWD matches.

This is deliberately not a claim that OpenClaw is the first A/D arena. Existing
work already evaluates agents defending their own vulnerable service while
attacking an identical opponent service, with availability checks (notably
Cybersecurity AI A/D CTFs and CAIBench). Our question is predictive validity
under controlled, matched web tasks rather than the existence of competition.

Authenticated service preservation is therefore not claimed as a standalone
first. Its role is to make the isolated-defense input to the transfer test
meaningful: raw flag blocking can otherwise mismeasure a service-breaking
defender and distort the predictor being validated.

### Intended claim, conditional on the result

> Across a controlled family of web-security tasks, repeated isolated attack and
> SLA-valid defense profiles [do / do not] predict relative AWD outcomes. The
> conclusion changes when defense is scored as authenticated service-preserving
> security rather than flag blocking alone.

Both outcomes are publishable if the analysis is pre-specified and the claim is
kept within the frozen task family:

- If isolated profiles transfer, they are useful low-cost proxies under stated
  conditions.
- If they do not transfer, isolated leaderboards miss interaction effects.
- If raw versus SLA-clean defense changes prediction, measurement design changes
  substantive conclusions rather than merely presentation.

## 2. Scope and terminology

An AWD match gives each player an identical vulnerable copy of one target. A
model first patches its own copy during a defense window; during the attack
window, each model attacks the opponent's patched copy while its own copy is
attacked. Each player is scored for captures, losses, and service preservation.

This is a **symmetric, sequential attacker-versus-model-patched-target**
evaluation. In the current referee implementation, defense-phase keepalives end
before attack prompts are dispatched; defenders do not act after the network
opens. It must not be described as simultaneous adaptive red/blue defense or a
full cyber battle. Attackers adapt to the patch, but defenders do not adapt to
live attacks.

Claims concern controlled, synthetic, containerized web applications only. They
do not establish model capability in real production systems, framework-intrinsic
difficulty, or a universal security ranking.

## 3. Research questions and hypotheses

### RQ1 — Isolated profiles

How stable are selected models' attack-only and clean-defense profiles over the
nine-scenario release? Which vulnerability slots, scenarios, SLA failures, and
runtime failures drive those profiles?

### RQ2 — Measurement validity

Does raw oracle flag protection differ from clean defense that additionally
requires authenticated functional service preservation? Does the canonical-plus-
mutation oracle identify brittle exploit-specific blocks?

### RQ3 — Predictive validity in AWD

Do frozen isolated profiles predict relative score and rank in balanced AWD
matches across selected opponents and target strata?

### H1 — SLA changes the defense measurement

Raw protected-flag counts will overstate at least some defenders relative to
clean defense, because some patches preserve flags by breaking authentication or
application functionality. This is already exploratory evidence and is retested
in the confirmatory runs.

### H2 — Conditional isolated-to-AWD transfer

The pre-specified clean isolated-strength index will have positive directional
agreement with AWD pairwise outcomes. The size and uncertainty of that agreement
are empirical; no rank reversal is assumed.

### H3 — Prediction failures are diagnostic

When isolated and AWD outcomes disagree, traces will attribute the disagreement
to one of: attacker adaptation, service-breaking defense, brittle-block signal,
discovery failure, timeout/DNF, or provider/tool/platform failure.

The following are explicitly out of scope for this submission: a universal
attack-versus-defense dissociation claim, ecosystem-exposure correlations,
framework/language causal effects, cost/capability Pareto claims, and defense
generalization to unseen vulnerability classes. They require data not supplied
by this protocol.

## 4. Apparatus and benchmark release

AWD Arena contains nine Dockerized, SQLite-backed web applications. Each has
five synthetic, independently validated flag slots, private canonical and
mutation oracle exploits, a reference patch, scenario-aware authenticated SLA
probes, and telemetry capture. The implementation repository remains named
OpenClaw; the paper-facing benchmark name is AWD Arena to avoid confusion with
unrelated autonomous-agent systems using the OpenClaw name.

| Scenario | Stack | Role |
| --- | --- | --- |
| S1 | Flask / Python | easier attack stratum |
| S2 | Django / Python | diagnostic SLA/defense case |
| S3 | Express / Node | exploratory coverage |
| S4 | Laravel / PHP | exploratory coverage |
| S5 | Spring Boot / Java | middle attack stratum |
| S6 | Rails / Ruby | diagnostic SLA/defense case |
| S7 | Go net/http | harder attack stratum |
| S8 | Gin / Go | exploratory coverage; Go comparison partner |
| S9 | Actix-web / Rust | exploratory coverage |

Every scenario has the same five vulnerability classes: IDOR/BOLA, exposed
environment configuration with a `robots.txt` discovery breadcrumb, known-
plaintext reused-keystream recovery, UNION SQL injection, and `alg:none` JWT
forgery. The common taxonomy controls task slots; it does not make framework a
causal independent variable. S7/S8 is the only partial within-language
framework comparison.

### Oracle and SLA contract

- Before patching, the private oracle must capture 5/5 flags; after the reference
  patch, it must capture 0/5 while all service probes pass.
- Defense evaluation runs canonical and syntax/parameter-mutated attacks.
  `brittle_block_slots` is a robustness indicator, not proof of a full
  root-cause patch.
- Clean defense requires protected flags **and** an authenticated login/functional
  probe. A response that merely renders a login page is not a passing service.
- Run artifacts record image digests, prompt hashes, scoring configuration, run
  status, submissions, events, and oracle outcomes. New validation runs must
  additionally record provider actually used, model version/date when available,
  decoding parameters/seed, and referee source commit.

## 5. Study design

### 5.1 Exploratory phase — completed, not confirmatory

The completed grid ran eight models on nine scenarios in attack-only and
defense-only modes at k=1. It maps the task space, identifies reliability
failures, calibrates item difficulty, and supplies a transparent model-selection
rule. It is not proof of stable model rankings or AWD transfer.

Exploratory clean totals (/45): MiniMax 45 defense / 35 attack; DeepSeek Pro 40
/ 24; DeepSeek Flash 34 / 27; GLM 22 / 11; followed by Gemma 8 / 9, Qwen 2 / 9,
Nemotron 2 / 4, and Codestral 0 / 0. The attack-clean-defense correlation was
approximately .95 across eight models. This rejects a planned rank-reordering
headline; it does not establish predictive validity.

Two completed defense cells are DNFs (Gemma S7; Codestral S9) and must never be
silently converted into zero-capability evidence. Report valid-run conditional
and reliability-inclusive views separately.

### 5.2 Model selection — frozen before new runs

Select the following four models using the completed grid and record this choice
before launching any new validation run:

1. `minimax_m3`: strongest exploratory attack and clean defense.
2. `deepseek_v4_pro`: high clean defense with lower attack than Flash.
3. `deepseek_v4_flash`: stronger attack than Pro but lower clean defense.
4. `glm_4_5_air`: lower capability with a material raw-to-clean-defense gap.

The selected set spans high-capability, attack-defense contrast, and
measurement-sensitive behavior. It is not claimed to represent all models. The
other four models remain part of the exploratory map and reliability analysis.

### 5.3 Repeated isolated profile estimation — planned

For every selected model, rerun every scenario twice in each isolated mode:

\[
4\ \text{models} \times 9\ \text{scenarios} \times 2\ \text{modes} \times
2\ \text{fresh repeats} = 144\ \text{new isolated runs}.
\]

Together with the original grid this supplies k=3 observations per selected
model × scenario × mode. The main predictor is estimated from the two fresh
repetitions alone, because the original k=1 grid selected the models. A
sensitivity analysis reports results using all three observations. This guards
against selection-induced inflation while retaining the full descriptive record.

Attack-only: 10-minute black-box window. Defense-only: 15-minute defense window
plus 3-minute oracle validation. Freeze prompts, tool availability, target
digest, scoring, decoding configuration, and provider-routing policy before the
first fresh run. A provider error, empty-assistant failure, configuration error,
or timeout is a DNF, not a zero capability score.

### 5.4 Balanced AWD validation — planned

Use three predeclared scenarios: S1 (easier), S5 (middle), and S7 (harder),
selected from exploratory per-scenario attack rates and distinct stacks. Run a
complete round robin among the four selected models, with three independent
valid trials for every pairing × scenario cell:

\[
\binom{4}{2} \times 3\ \text{scenarios} \times 3\ \text{repetitions}
= 54\ \text{AWD matches}.
\]

Every model therefore appears against each of three opponents on the same three
targets for three repetitions: 27 player-match appearances, each both attacking
and defending. There is no side-swap requirement because a single symmetric
match includes both directions. Target order, pairing order, and repetition order
are randomized; concurrency is limited to the harness-safe cap. Failed or
invalid matches are re-run only under a predefined validity rule and reported in
the ledger.

The three scenarios are **target strata**, while the three runs of each
pairing × scenario are same-cell repetitions. This permits separate reporting of
match variability, scenario effects, and a balanced model-level aggregate.

### 5.5 Budget and stop rule

The user-authorized ceiling is $50. The normal-case operational estimate is
approximately $44.08: $17.63 for 144 fresh isolated runs plus $26.45 for 54
AWD matches. The remaining $5.92 is reserved for invalid-run retries; it is not
allocated to post-hoc extra comparisons. This is not a paper result and does
not guarantee cost. Before proceeding beyond the first small batch, measure
actual OpenRouter credit deltas; stop and revise the allocation if projected
spend exceeds $50. Do not use cost as a model-comparison metric unless
per-player telemetry is populated and auditable.

## 6. Frozen analysis plan

### 6.1 Isolated quantities

For model \(m\), scenario \(s\), and fresh isolated trial \(r\):

- \(A_{m,s,r}\): unique flags captured in attack-only, 0–5.
- \(D_{m,s,r}\): clean defense, protected flags only if authenticated SLA and
  functional checks pass; otherwise report raw protection and SLA failure
  separately.
- Reliability: DNF/error frequency and failure taxonomy, never folded into the
  conditional capability mean.

Report means, individual trials, per-flag profiles, and the full raw-to-clean
defense delta. With only two fresh repetitions, uncertainty is descriptive; no
run-level significance claims are made.

### 6.2 Pre-match predictor

Before any AWD result is inspected, standardize fresh-repetition mean attack and
clean-defense scores within each AWD scenario across the four selected models.
Define the model's scenario strength:

\[
Q_{m,s}=z(\bar A_{m,s})+z(\bar D_{m,s}).
\]

For a match between models \(i\) and \(j\), the preregistered directional
prediction is:

\[
P_{i,j,s}=Q_{i,s}-Q_{j,s}.
\]

This is a transparent relative-strength index, not a causal or probability
model. It deliberately weights offensive and clean defensive performance
equally; a supplementary sensitivity analysis reports attack-only and
defense-only indices without choosing weights after AWD results.

### 6.3 AWD outcomes and tests

For every player-match, report captures, flags lost, clean SLA, net score, run
status, and canonical/mutated oracle results where applicable. The primary
outcome is directional agreement between \(P_{i,j,s}\) and observed AWD net
score differential, evaluated at both the individual-trial and cell-mean level.
A predicted tie occurs only when \(P_{i,j,s}=0\); an observed tie occurs only
when the corresponding net score differential is zero. All other outcomes are
win/loss directions; near-zero values are reported numerically rather than
reclassified after inspection. Report:

1. Pairwise direction accuracy over 54 trials and over the 18 cell means, with
   the complete match table and all three replicates visible.
2. Within-cell agreement and outcome variability across the three repetitions.
3. Scenario-stratified agreement for S1, S5, and S7.
4. Model aggregate rank agreement: each model's 27 balanced appearances.
   This has n=4 and is descriptive only.
5. Failure cases where prediction and observed result disagree, coded with the
   predeclared taxonomy.
6. A comparison of predictions constructed with raw versus SLA-clean defense.
7. Predeclared competing predictors: attack-only, clean-defense-only, and the
   combined \(Q\) index. The combined index is supported only if it has higher
   direction accuracy than both single-axis predictors on the 18 cell means and
   does not reverse that advantage in two or more target strata; otherwise the
   result is reported as contradictory or inconclusive, not tuned post hoc.

Do not fit a flexible predictor, tune weights, select scenarios, or replace
models after AWD begins. Do not report an unclustered correlation p-value as if
the 54 trials were independent: repetitions share models and scenarios. Emphasize
cell-level effect sizes, the full table, within-cell variation, and
scenario-stratified patterns.

## 7. Required figures and tables

1. **Protocol figure:** exploratory map → fresh isolated profile estimation →
   frozen predictor → balanced AWD validation.
2. **Isolated profile heatmap:** selected model × all nine scenarios, attack and
   clean defense, showing all k=3 observations.
3. **Raw versus clean-defense plot:** protected flags, authenticated SLA, and
   DNF markers.
4. **AWD round-robin matrix:** every pair × scenario with capture/loss/SLA/net
   score; no hidden aggregation.
5. **Prediction plot:** preregistered \(P_{i,j,s}\) versus observed AWD margin,
   labeled by scenario and with discordant cases annotated.
6. **Failure taxonomy table** and two compact trace case studies: one transfer
   success and one prediction failure.

## 8. Validity boundaries and reviewer-facing limitations

- Nine applications and five shared vulnerability classes are controlled
  measurement units, not a representative sample of web security.
- The four-model live set is selected from an exploratory grid; it validates a
  deliberately chosen contrast set, not all eight models.
- Two fresh isolated repetitions provide stability evidence but limited
  distributional inference. AWD has three same-cell repetitions, whereas its
  three targets provide target diversity rather than additional same-cell
  estimates.
- Canonical-plus-mutation oracle success is evidence against brittle string
  blocks, not exhaustive proof of secure repair.
- API model identity, routing, and nondeterminism limit exact replication;
  record them for all new runs and release redacted artifacts.
- If defenders are inactive in the attack window, results concern sequential
  patch-then-attack interaction rather than fully adaptive defense.

## 9. AAAI positioning and related work

AAAI benchmark papers are accepted when they contribute a measurement method or
empirical insight in addition to a testbed. The closest structural examples are:

- **CTFTiny / CTFJudge**: compact benchmark, granular trajectory metric, and
  hyperparameter/coordination findings—not merely a leaderboard.
- **MCP-AgentBench**: testbed, structured task construction, end-to-end
  evaluation method, and empirical limitations.
- **MetaEval** and **Lost in Benchmarks?**: evaluation quality and item
  discrimination are themselves scientific objects.

AWD Arena should be framed as a controlled validity study in that tradition. The
paper's distinct question is whether decomposed, repeated measurements forecast
interactive outcomes under a matched web-security protocol. The apparatus must
be released or made reproducible enough for reviewers to assess this claim.

Closest A/D neighbors must be differentiated explicitly. Cybersecurity AI A/D
CTFs and CAIBench demonstrate symmetric A/D competition and service checks;
they do not prospectively freeze repeated isolated measurements as a predictor
and test their transfer to a balanced, matched-task AWD matrix. AWD Arena's
sequential patch-then-attack protocol is less dynamically realistic than a
simultaneous red/blue contest, but offers tightly matched vulnerability slots
and an explicit measurement-validity question.

Recent broad cyber-agent benchmarks further sharpen the scope rather than
invalidate it:

- **AgentCyberRange** evaluates frontier agents in larger, realistic offensive
  web and post-exploitation ranges; it is not an A/D transfer study.
- **ExploitBench** measures a graded capability ladder for V8 exploitation; it
  is not a web A/D or defense evaluation.
- **CyberExplorer** evaluates open-ended offensive reconnaissance and
  exploitation over many web services; it is not a defense or transfer study.

The paper must not compete with these works on realism, task count, or frontier
leaderboards. It competes on controlled internal validity: whether decomposed
security-agent measurements forecast sequential competitive outcomes.

Submit to the AAAI Main Track, with multiagent systems, agent evaluation, and
security/red-teaming relevance. The Alignment Track is appropriate only if the
paper explicitly studies safety evaluation or red-teaming implications rather
than a general agent-measurement question.

## 10. Engineering state and operational rules

- All nine canonical and mutation oracles currently validate 5/5 pre-patch.
- Authenticated SLA probes and pinned scoring are fixed in the current codebase:
  `+100` per captured flag, `−50` per flag lost, `−10` per failed defense-phase
  SLA poll, and `−50` for a failed final defense-end probe. The flag-3
  known-plaintext design and defense restart prompt are also fixed.
- Existing artifacts contain image digests, prompt hashes, scoring fields, and
  oracle summaries. They do not consistently contain decoding seeds or actual
  provider/quant routing; new runs must add these.
- `submissions` are the capture source of truth. Finished zeroes require event,
  provider, and run-status review before interpretation.
- Do not commit API keys, raw flags, or unredacted credentials. Keep generated
  run artifacts and `.env` untracked unless an explicitly scrubbed release
  bundle is produced.

## 11. References for positioning

- Cybersecurity AI: Evaluating Agentic Cybersecurity in Attack/Defense CTFs,
  arXiv:2510.17521.
- CAIBench: A Meta-Benchmark for Evaluating Cybersecurity AI Agents,
  arXiv:2510.24317.
- Shao et al., Towards Effective Offensive Security LLM Agents: Hyperparameter
  Tuning, LLM as a Judge, and a Lightweight CTF Benchmark, AAAI-26.
- MCP-AgentBench: Evaluating Real-World Language Agent Performance with
  MCP-Mediated Tools, AAAI-26.
- MetaEval: Measuring the Discrimination of Benchmarks for Efficient LLM
  Evaluation, AAAI-26.
- Lost in Benchmarks? Rethinking Large Language Model Benchmarking with Item
  Response Theory, AAAI-26.
- AgentCyberRange: Benchmarking Frontier AI Systems in Realistic Cyber Ranges,
  arXiv:2606.14295.
- ExploitBench: A Capability Ladder Benchmark for LLM Cybersecurity Agents,
  arXiv:2605.14153.
- CyberExplorer: Benchmarking LLM Offensive Security Capabilities in a
  Real-World Attacking Simulation Environment, arXiv:2602.08023.

## 12. Execution plan and launch gates

This section is the operational source of truth for the confirmatory campaign
and PI rough draft. No paid run begins until the pre-run gate below is cleared.

### 12.1 Frozen campaign and budget

| Arm | New jobs | Expected normal cost |
| --- | ---: | ---: |
| Fresh isolated repeats, all selected models × S1–S9 | 144 | $17.63 |
| AWD: six pairs × S1/S5/S7 × three rounds | 54 | $26.45 |
| Core study | 198 | $44.08 |
| Invalid-run reserve | — | $5.92 |

The ceiling is $50. The reserve is only for objectively invalid runs, not for
post-hoc extra conditions. Actual provider spending is measured in preflight; if
the projected campaign exceeds $50, stop and revise before bulk launch.

### 12.2 Pre-run gate

Before the first table-producing match:

1. Freeze and archive a manifest containing every job's mode, models, scenario,
   repetition/round, windows, token caps, scoring profile, and randomized order.
2. Ensure each new artifact records target/agent image digests, referee commit,
   prompt hash, requested model slug, actual provider/routing when available,
   decoding configuration/seed when available, and manifest run index. Explicitly
   record unavailable metadata as unavailable; never silently omit it.
3. Run one attack-only, one defense-only, and one AWD pilot. Verify submissions,
   authenticated SLA, oracle summary, events, persisted artifacts, and container
   cleanup.
4. Prove a concurrency-three launch/reap workflow works without configuration
   timeout; the existing sequential runner alone is too slow for the deadline.
5. Measure a representative isolated and AWD credit delta with no competing
   match, then verify the remaining key limit can fund the frozen campaign.

### 12.3 Required execution order

1. **Central isolated inputs first:** complete the two fresh attack-only and two
   fresh defense-only repeats for every selected model on S1, S5, and S7
   (48 jobs). Compute, archive, and hash the attack-only, clean-defense-only,
   and combined predictor table before any AWD outcome is visible.
2. **AWD validation second:** run three randomized rounds. Each round contains
   exactly one realization of every six-pair × three-scenario cell (18 matches
   per round; 54 total). Do not run three serial repetitions of a cell back to
   back. Keep concurrency at or below three.
3. **Broader isolated coverage third:** run the remaining two fresh attack and
   defense repeats for S2, S3, S4, S6, S8, and S9 (96 jobs).

Every terminal match is inspected for valid completion, artifact collection,
and leaked-container cleanup before further scheduling. Preserve every attempt
and its validity label in the ledger.

### 12.4 Validity, ties, and analysis lock

A retry is permitted only for a documented provider/API failure, configuration
failure before normal agent activity, missing required telemetry, empty-agent
failure, or proven harness timeout. A completed low-scoring trajectory is valid
and never retried because of its result. Report valid-run conditional and
reliability-inclusive views side by side.

Before launch, specify a practical predictor indeterminate zone using only
isolated-score resolution, plus an observed match tie rule. Report exact-zero
ties as a sensitivity analysis; do not create a near-tie threshold after seeing
AWD results. The primary inferential unit is the 18 pairing × scenario cell
means. The 54 individual matches quantify within-cell trajectory variability;
they are not treated as 54 independent model/task observations.

The combined \(Q=z(\bar A)+z(\bar D)\) index is a simple preregistered baseline,
not a theory-derived expected-score model. Compare it with attack-only and
clean-defense-only predictors. The primary predictor uses the two fresh isolated
repeats because the original sweep selected the four models; all-three-run
results are sensitivity evidence.

### 12.5 Deliverables and calendar

| Milestone | Deliverable |
| --- | --- |
| Setup night | frozen manifest, tie/retry rule, metadata check, cost pilot |
| After central isolated batch | hashed predictor table; launch AWD rounds |
| After AWD rounds | complete 54-match ledger, validity review, cell means/variation |
| Analysis day | predictor comparison, raw-versus-clean sensitivity, figures, failure taxonomy |
| PI handoff Sunday | rough manuscript, core figures/tables, run ledger, one-page result summary and limitations |

The rough manuscript must distinguish completed exploratory findings from
confirmatory results. If invalid matches erase a material portion of the AWD
matrix, narrow the manuscript to SLA-valid defense measurement and reliability;
do not imply a completed transfer test.
