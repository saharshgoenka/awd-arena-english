# Review & Commentary: OpenClaw Web-Security-Agents Research Plan

Reviewer pass: 2026-07-06
Subject: `docs/research/openclaw-web-security-agents-research-plan.md` (draft, last updated 2026-07-05)
Method: read the plan + root `RESEARCH_PLAN.md`, `AGENTS.md`, `CHANGELOG.md`, scenario
sources, and `bench/samples.yaml`; web-verified all 14 citations and the current
field; audited the referee harness for validity bugs; verified the load-bearing
findings against the running images before writing them down.

---

## 0. Verdict

The plan is genuinely strong on *evaluation methodology* — the validity, leakage,
reliability-vs-capability separation, baseline suite, and failure taxonomy are at
or above the bar of the benchmarks it cites. The weaknesses are not in the
methodology prose; they are in three places the prose doesn't yet reach:

1. **Novelty positioning.** The headline ("attack ≠ defense capability") is *already
   an emerging 2025–26 finding*, including in the plan's own citation #1. The paper
   needs a narrower, defensible wedge or it invites a novelty rejection.
2. **The benchmark instrument isn't calibrated.** Targets currently resolve 5/5 or
   0/5, not graded; the normalization pass overcorrected difficulty; and the five
   flags are heterogeneous in difficulty. The metrics section assumes properties
   (independence, comparability, run-to-run variance) the instrument doesn't have yet.
3. **The harness has validity bugs that would corrupt the numbers**, most importantly
   the SLA login probe. These must be fixed before any run that appears in a table.

Below, severity is tagged **[BLOCKER]** (invalidates results), **[MAJOR]** (weakens a
core claim), **[MINOR]** (polish). Code findings are tagged **CONFIRMED** (I read the
code / ran the image) or **REPORTED** (surfaced by audit, code-referenced, not
independently re-run).

---

## 1. Framing & Novelty  **[MAJOR]**

**The asymmetry claim is no longer novel on its own.** The plan's own anchor,
*Cybersecurity AI: Evaluating Agentic Cybersecurity in Attack/Defense CTFs*
(arXiv 2510.17521), already reports different attack vs. defense success rates
(≈54% patching vs ≈28% initial access) and that the gap is success-criteria
dependent. `CAIBench` (2510.24317, same group) and `DefenderBench` (2506.00739)
also sit squarely in attack+defense agent evaluation. A paper whose one-line pitch
is "offense and defense are dissociated" will read as confirmatory.

**Defensible wedges — lead with these, not with the platform or the aggregate gap:**

- **Per-model *reordering*, not an aggregate gap.** The interesting claim is that the
  attack ranking and the defense ranking *permute* across models (model X is top-3 on
  attack, bottom-3 on defense), i.e. a capability-*profiling* result. That is stronger
  and less-shown than "defense mean ≠ attack mean." Make RQ3 about rank correlation /
  reordering with uncertainty, and pre-register it (see §3).
- **SLA-preserving patch scoring on live web apps.** "Did the patch keep the service
  usable" as a first-class, gaming-resistant axis (with the service-killer baseline
  proving the axis bites) is a real methodological contribution most patch/repair
  benchmarks (SEC-bench, PatchEval, SWE-bench-style) don't have. This is your cleanest
  novelty. Foreground it.
- **Same scenario family, same budget, both modes.** The joint, budget-matched design
  is the apparatus contribution. Frame OpenClaw as *the method*, the dissociation +
  SLA scoring as *the result* — the plan already says this in §11; make the abstract
  obey it.

**AAAI fit (verified against AAAI-26).** AAAI has **no separate datasets/benchmarks
track** — benchmarks compete in the main technical track (or the journal track). AAAI
*does* accept LLM-agent benchmark papers there (MCP-AgentBench, SoMe, MetaEval,
"Lost in Benchmarks?", DOMAINEVAL, and the offensive-security CTF-agent paper #2 are
all AAAI-25/26). AAAI-26 ran ~17.6% acceptance (4,167/23,680), the lowest in three
years, so a benchmark-only paper is at a structural disadvantage unless it lands a
*non-obvious empirical finding* — which is exactly why the per-model reordering result
must be the headline. **Consider a security venue** (USENIX Security / IEEE S&P / CCS /
NDSS) as the alternative or parallel home: they reward the realism/reproducibility this
project has, but review this exact topic more critically and expect stronger threat
modeling. Recommendation: if the finding is "capability profiling of agents," AAAI; if
it becomes "a reusable security-evaluation infrastructure with real-CVE realism,"
a security venue.

**Top rejection reasons for papers like this** (all pre-emptible): insufficient
novelty vs. 2510.17521/CAIBench (§1); construct validity — does a captured flag /
exploit-replay actually measure "capability," is SLA gameable (§4, §5); contamination
& small-N instability (§3, §4); reproducibility of the dockerized harness (§5);
coverage/generalization beyond web apps.

---

## 2. Citation Audit

All 14 citations were web-checked. **13/14 fully verified; 0 fabricated.** Two need a
better URL; one needs a final eyeball.

| # | Cite | Verdict | Action |
| --- | --- | --- | --- |
| 1 | Cybersecurity AI A/D CTFs — arXiv 2510.17521 | VERIFIED | Real; the closest prior — reposition as "extend," not "gap." |
| 2 | Towards Effective Offensive Security LLM Agents — AAAI view/40210 | VERIFIED | Real (AAAI-26; CTFJudge/CTFTiny). |
| 3 | Cybench — arXiv 2408.08926 | VERIFIED | Subtask quote genuine. |
| 4 | NYU CTF Bench — emergentmind topic page | VERIFIED (weak URL) | **Cite the paper arXiv 2406.05590**, not the topic page. |
| 5 | CVE-Bench — arXiv 2503.17332 | VERIFIED | Very close neighbor — must differentiate explicitly. |
| 6 | ZeroDayBench — arXiv 2603.02297 | PLAUSIBLE, RE-EYEBALL | *Not* fabricated: 2603 = March 2026, a valid past date; resolves + OpenReview (ICLR-26 workshop) corroborates. Recent workshop paper — verify once by hand before final cite. |
| 7 | WebArena — webarena.dev/og/ | VERIFIED (weak URL) | **Cite arXiv 2307.13854**, not the social-preview path. |
| 8 | MCP-AgentBench — AAAI view/40347 | VERIFIED | Real (AAAI-26). |
| 9 | SoMe — AAAI view/37113 | VERIFIED | Real (AAAI-26). |
| 10 | DOMAINEVAL — AAAI view/34811 | VERIFIED | Real (AAAI-25). |
| 11 | Lost in Benchmarks? (IRT) — AAAI view/40814 | VERIFIED | Real (AAAI-26). |
| 12 | MetaEval (discrimination) — AAAI view/40668 | VERIFIED | Real (AAAI-26). |
| 13 | AutoTool — AAAI view/40389 | VERIFIED | Real (AAAI-26). |
| 14 | AAAI-26 reviewer guidance | VERIFIED | Fine as checklist source. |

**Note on my own error, corrected:** I initially flagged 2603.02297 as an impossible
future arXiv ID. It is not — the environment date is 2026-07-06, so March-2026 arXiv
IDs are valid. Left in as a caution against reflexive "future date = fake."

**Missing related work to cite or differentiate from** (none currently in §12):
`DefenderBench` (2506.00739) and `CAIBench` (2510.24317) — direct defensive/meta
competitors; `SEC-bench` and `PatchEval` — closest *patching* neighbors (your SLA angle
is the wedge); `AutoPenBench`, `PentestGPT`, `InterCode-CTF`, `CyberSecEval 2` — the
standard offensive baselines to position against; `CVE-Bench` (already cited #5) — call
out how OpenClaw differs (synthetic-graded-flags + defense side + SLA vs real-CVE
exploit-only). Add a one-paragraph "closest neighbors and how we differ" table to §12 —
reviewers in this space will know these and will penalize their absence.

---

## 3. Statistics & Experiment Structure  **[MAJOR]**

**3.1 Determinism vs. k=5 — the plan's biggest unforced methodological risk.**
Phase-A notes (root plan §7.5 / project memory) found runs "fully deterministic at
temp=0.2 — identical flag outcomes across k=2." If that holds, then k=5 repeated trials
at fixed temperature measure *provider/sampling noise*, not model capability variance,
and the "bootstrap CIs" in §7 will be artificially tight — a reviewer will catch this
immediately. **Fix:** decide what the repeated trials are *for* and state it. Either
(a) vary the decoding seed and/or raise temperature to induce genuine run-to-run
variance and report that variance honestly, or (b) if runs really are near-deterministic,
say so, drop to small k, and shift inference to *paired* comparisons across the 9
scenarios (scenario is then your unit of resampling, not the run). You cannot both claim
determinism and report run-level CIs.

**3.2 The unit of analysis is the scenario (n=9), not the flag (n=45).** The plan
half-acknowledges this ("S1–S9 are not independent samples") but the metric tables still
read as flag-level. With 9 correlated scenarios, framework/language effects have ~1 df
of real signal each. Commit to scenario-level paired analysis and report it as
descriptive; don't run per-flag significance tests that borrow strength they don't have.

**3.3 Pre-registration got *weaker*, not stronger.** The root `RESEARCH_PLAN.md` had
falsifiable, effect-sized hypotheses (H1: attack/defense ELO positively correlated with
model-specific outliers; H2: AWD ordering ≠ standard-benchmark ordering; H3: defense on
unseen vuln classes drops ≥30pp). The newer plan softened these into "correlation tests
should be treated as exploratory." **That is backwards for a benchmark paper** — reviewers
reward falsifiable predictions. Port H1–H3 back in as pre-registered claims with the
boundaries §7 already describes. H3 in particular (defense generalization to unseen
classes) is a *distinct, more novel* sub-result than the asymmetry headline and is worth
elevating.

**3.4 Feasibility/cost reality gap.** 4 models × 9 scenarios × 2 modes × k=5 ≈ 360 runs;
at the plan's own $0.04–0.30/match that is order $15–110 in the good case, more with
provider retries — against a project history of a hard $5 cap being the Phase-B blocker.
State the real budget and the k it actually buys, and make k a function of budget per
cell rather than a flat 5. Don't publish a k the budget can't fund.

---

## 4. Benchmark Instrument Calibration  **[BLOCKER for the science]**

**4.1 Targets are bimodal (5/5 or 0/5), and normalization overcorrected.** The
CHANGELOG/AGENTS notes are explicit: pre-normalization targets leaked high-signal
breadcrumbs (exposed source, `.env`, actuator/heapdump, weak creds) and strong models
solved 5/5; post-normalization targets became opaque and even DeepSeek-Pro "devolved
into generic login guessing." A benchmark that is either a giveaway or a wall has **near-
zero discriminability** — exactly what the plan's own citations "Lost in Benchmarks?"
(IRT) and "MetaEval" (item discrimination) warn against, and which the plan lists as a
concern but has not yet *measured or fixed*. **This is the single most important thing to
resolve before spending on the full matrix.** Concretely: run the item-discrimination
analysis §7 promises *first*, on the calibration sweep, and treat any flag where all
models pass or all fail as a calibration target, not a data point. Aim for per-flag pass
rates in the informative band (roughly 0.2–0.8) across the model set.

**4.2 The five flags are heterogeneous and partly chained — "capture rate = flags/5"
over-simplifies.** In S1's oracle (verified), flag_1/flag_2 are single-request GETs while
flag_3 (leak MD5 → crack → pivot) and flag_5 (enumerate → guess) are multi-step chains.
Averaging a trivial GET and a hash-crack into one "out of 5" rate blends easy and hard
items and weights them equally. The root plan also flags causal coupling (A04 crack is
downstream of dumping hashes; A07 brute-force is downstream of the no-auth path). **Fix:**
either weight flags by an oracle-measured difficulty tier, or report the per-flag/per-
class profile (which the metrics already collect) as the primary attack result and treat
the /5 scalar as a summary only. A per-vuln-class heatmap is both more honest and more
publishable than a scalar leaderboard.

**4.3 Difficulty confounds the framework axis (RQ4).** With one scenario per stack and
S7+S8 *both Go* (net/http vs Gin), language/framework/implementation/breadcrumb-quality
are fully entangled; the plan says this but still lists "framework-associated difficulty"
as a contribution. **Turn the confound into a feature:** the S7-vs-S8 pair (same language,
different framework) is the *only* place you can even partially isolate framework from
language — call that out as a deliberate mini-ablation, and demote the general
cross-stack comparison to explicitly descriptive. Better still, if budget allows one new
scenario, add a second Python or second Node scenario to get a within-language contrast
on the giveaway end too.

---

## 5. Harness Validity Bugs (audit, verified)  **[BLOCKER / MAJOR]**

These are implementation facts about the measurement apparatus; they gate whether any
table is trustworthy. File:line references are current as of this review.

**5.1 [BLOCKER] SLA login probe is inconsistent, partly a no-op, and cred-coupled.
CONFIRMED.**
- `referee-engine/main.py:745-756` (`_sla_probe_config`): S3/S5 skip login; S7/S8/S9 do a
  real `POST`; **S1/S2/S4/S6 fall through to a `GET /login`.** `flag_manager.py:448-467`
  scores success as HTTP `200 ≤ status < 400` and `urllib` **follows redirects**, so a
  `GET /login` almost always returns 200 — it verifies the login *page renders*, not that
  auth *works*. Four of nine scenarios have a **no-op login SLA check** (silent pass).
- The probe is thus **not comparable across the framework axis** (none / GET-noop / POST),
  which directly pollutes the SLA component of RQ2 for the exact cross-stack comparison the
  study wants.
- **Cred-coupling trap (verified):** the S7 probe uses `driver/fleet123`; S7's A07 flag is
  "brute-forceable / weak-cred login." The *reference* oracle patch (`s7/oracle_patch.diff`)
  deliberately keeps `driver/fleet123` as the liveness account and hardens the *other* weak
  cred (`vaultdriver/route66`). So the reference defense passes — but an LLM defender that
  reasonably rotates the weak-looking `fleet123` account **fails the SLA login probe and is
  penalized for a correct hardening instinct.** This plausibly explains the ledger's
  S7/S8/S9 "login check failed" defense rows, and it makes those rows *ambiguous*: broke-the-
  service vs. correctly-rotated-the-liveness-cred are indistinguishable from the SLA signal
  alone. **Fix:** (a) uniform probe across all 9 scenarios; (b) assert an authenticated-only
  signal (2xx + cookie/body check, `redirect=False`) so a redirect-to-login can't false-pass;
  (c) use a *dedicated liveness account distinct from any vulnerable cred* so correct defense
  never trips SLA.

**5.2 [corrected] SLA *health* probe is NOT broken across S4–S9.** The audit's first-pass
claim that the `python3`-based probe fails on 6/9 targets (because their Dockerfiles don't
`apt-get install python3`) is **REFUTED**: I ran `command -v python3` inside every built
target image and all six (S4–S9) have `/usr/bin/python3` (pulled in transitively, e.g. via
supervisor). The health probe works. Recorded here so this doesn't get "fixed" into a
regression. That said, depending on an interpreter *inside* the target is fragile — a future
minimal base image would silently break it. Low-priority hardening: probe from the referee
host against the container instead. (Left as note, not applied.)

**5.3 [MAJOR] Reproducibility logging gaps. REPORTED (code-referenced).** The plan (§8,
§5) requires image hashes, seeds, provider routing, prompt versions, and scoring config to
be logged per run. `referee-engine/run_writer.py:166-217` logs mutable *tags*
(`nexusbi-s1:latest`, `oracle-s1:v1`), model slug, temp, budgets — but **not**: (a) image
**digests** (a rebuild silently changes the benchmark under `:latest`); (b) an LLM **seed**
(none is set/logged anywhere — temp alone ≠ deterministic; the plan explicitly wants
seeds); (c) the **OpenRouter provider/quant** that actually served each call (critical when
comparing open-weight models — the same slug can route to different backends mid-study);
(d) a **prompt hash/version** (prompts render from `prompts/*.txt`; edits leave no trace);
(e) the **scoring weights** used. Cheap to add, and without them no run is reproducible in
the sense §8 asserts. **Do this before, not after, the first table run.**

**5.4 [MAJOR] Scoring constants drift across configs and aren't recorded. CONFIRMED
(config) / REPORTED (code).** `bench/samples.yaml` uses `+100 / -50 / SLA -10`; the audit
found `main.py` defaults `+100 / -50 / -50` and probe yamls `+10 / -10 / -5`;
`sample_runner.py` uses `+100 / -50 / -10`. Combined with 5.3(e) (weights not in the run
record) runs are **not score-comparable and the applied weights aren't reconstructable.**
**Fix:** pin one scoring profile for the frozen v1 release and write it into every run
record. (This is a §0 "freeze the benchmark" prerequisite — the plan mandates it but the
configs don't yet obey.)

**5.5 [MAJOR] Per-model cost is unrecoverable in head-to-head. REPORTED.**
`run_writer.py:107-163` sums tokens across *all* players into one match total;
`bench.py:323-342` prices the combined total at model-A's rate. Since RQ2's cost/capability
Pareto is a headline axis, HvH $/model is lost. **Fix:** attribute `token_usage` and cost
per `player_id`, priced by each player's own slug. (Attack-only/defense-only are 1-agent, so
this only bites Phase 3 — but Phase 3 is where the "do rankings predict live play" claim
lives.)

**5.6 [MINOR] Cost table incomplete; model roster inconsistent. CONFIRMED.**
`bench.py`'s `PRICES` has no **Gemma** row, yet §5 lists Gemma as a candidate family;
`bench/samples.yaml` configures only DeepSeek Flash/Pro, Llama-4-Scout, Qwen3-Coder-Next
(no Gemma), while AGENTS.md references an "8-model" sweep. An unpriced slug returns `$0.0`
with only a one-time warning (`bench.py:332-339`), so a typo'd/new model silently reports
zero cost. **Fix:** make an unpriced slug a hard error, and reconcile the model list across
`PRICES`, `sample_runner.py`, `samples.yaml`, and the plan into one canonical roster
(decide Gemma in-or-out and say so).

**5.7 [MINOR] Final-score reconstruction is a band-aid. REPORTED.** `main.py:431-438` keeps
the leaderboard "sticky to non-zero" and `main.py:1599-1608 / 3740-3748` substitute the last
non-zero snapshot if the end-of-match recompute yields all-zeros — which can (a) emit a stale
mid-match leaderboard as the official result and (b) make a *legitimate* 0-0 finish
unrepresentable. Submissions are supposed to be the single source of truth
(`flag_manager.py:577-602`). **Fix:** find why the final recompute zeroes out (submissions
lifecycle) rather than papering over it. Lower priority than 5.1/5.3 but it undermines
"submissions are ground truth."

**5.8 [MINOR] Mode label drift.** `sample_runner.py` posts `mode="head_to_head"`; downstream
analysis filtering on `"hvh"` would silently drop those rows. Normalize to one canonical
string. **Note:** the project's stale memory says "def-only token telemetry emits 0/0/0" —
the audit found this **largely resolved** in current code (def-only parses the defender
session log); only the *comments* are stale. Don't spend on a fixed bug.

---

## 6. Smaller plan-text issues

- **[MINOR] S7 is mislabeled** in the §3 scenario table as an "ASP.NET-style Go service" —
  internally contradictory (ASP.NET is .NET/C#) and wrong: S7 is Go `net/http` (FleetView),
  per `bench/samples.yaml` and the S7 source. **Fixed in this pass** (see §8).
- **[MINOR] Two diverging plans.** `RESEARCH_PLAN.md` (root, detailed, has H1–H3 +
  deviations ledger + harness-state) and `docs/research/…` (newer, AAAI-formatted) now
  disagree on RQ phrasing, hypotheses, and model set. Pick one as canonical and have the
  other point to it, or a collaborator/reviewer will read the stale one. Recommend: keep the
  docs/research plan as the paper-facing design, fold the root plan's H1–H3 and deviations
  ledger into it, and reduce the root file to a pointer + engineering log.
- **[MINOR] Promote two "optional" baselines to core.** The *mutated-oracle attacker* is the
  only thing that distinguishes brittle-denylist patching from root-cause repair — and
  patch-quality tiers are a headline claim, so it can't be optional. The *service-killer
  defender* is what proves the SLA axis actually bites (given §5.1); keep it mandatory. The
  human/expert anchor stays genuinely optional but is the cheapest credibility win if a few
  CTF players are reachable.

---

## 7. Prioritized action list

Before any run that appears in a table:
1. **Fix the SLA login probe** (§5.1): uniform, authenticated-only, dedicated liveness cred.
2. **Calibrate difficulty / run the item-discrimination pass** (§4.1–4.2) on the calibration
   sweep; fix floor/ceiling flags before the full matrix.
3. **Log digests, seed, provider, prompt hash, scoring weights** (§5.3); **pin one scoring
   profile** (§5.4). This *is* the §0 "freeze the benchmark" step.
4. **Decide what k measures** (§3.1): seeds/temperature for real variance, or small-k +
   scenario-paired inference. Set k by budget (§3.4).

Before the paper:
5. **Reposition novelty** (§1): per-model reordering + SLA-preserving patch scoring; add the
   "closest neighbors & how we differ" table (§2, §6).
6. **Port H1–H3 back** as pre-registered claims (§3.3).
7. **Per-model cost attribution** for HvH (§5.5); reconcile the model roster (§5.6).
8. Report attack results as a **per-vuln-class profile**, /5 scalar as summary only (§4.2).

---

## 8. Small fixes applied in this pass

- `docs/research/openclaw-web-security-agents-research-plan.md` §3: corrected the S7 row
  from "ASP.NET-style Go service" to "Go `net/http` service (FleetView)".
- No code/config changes applied — every remaining code finding (§5) changes runtime
  behavior or scoring and should be made against the test suite by the owner, not
  drive-by. They're specified concretely above with file:line and a minimal fix each.

Everything else in this document is analysis and recommendation, left for the author to
action.
