# GitHub Copilot Instructions

---

## CP2 ACTIVE — Read This First

The repository is currently executing the **CP2 ticket program.**

**CP2:** Calibration-Channel Poisoning of Federated Threshold Personalization in IoT Anomaly Detection: A Policy-Differentiated Vulnerability Analysis

**Root instructions:** `CLAUDE.md` (always read this first for CP2 work)

**CP2 is greenfield inside this repository.** Existing code is not automatically canonical. No backward compatibility unless a ticket explicitly says so.

### CP2 files (use these, not the DATP journal paths below)

| Purpose | File |
|---|---|
| CP2 protocol of record | `docs/DATP_CP_Roadmap.md` |
| Ticket index | `docs/tickets/TICKET_INDEX.md` |
| Phase layout + scientific locks | `docs/tickets/README.md` |
| Progress tracker | `docs/tickets/_ai_tracking/progress/CP2_PROGRESS.md` |
| Decision log | `docs/tickets/_ai_tracking/decisions/CP2_DECISION_LOG.md` |
| Paper notes | `docs/tickets/_ai_tracking/paper_notes/CP2_PAPER_NOTES_CONSOLIDATED.md` |
| Graphify status | `docs/tickets/_ai_tracking/graphify/CP2_GRAPHIFY_STATUS.md` |

### CP2 working rules

- Before editing code, read the active CP2 ticket and its listed dependencies.
- Inspect actual code, tests, outputs before trusting progress files.
- Do not use `docs/journal/*.md` as the CP2 planning layer.
- Do not use `docs/tickets/ticket_inventory.md` or `ticket_progress.md` for CP2 — use `TICKET_INDEX.md` and `CP2_PROGRESS.md`.
- Do not implement outside the current ticket scope.
- Do not run final experiments before CP2-T056.
- Do not run final analysis before CP2-T057.
- Do not write the final paper package before CP2-T058.
- Graphify is **AVAILABLE** (`graphify update .` — no API key needed).

### CP2 scientific locks (summary)

- Calibration-channel poisoning only. Training, model weights, aggregation, and test data are never poisoned.
- Injection: `REPLACE_FIXED_BUDGET` (replace positions with victim-local reservoir values resampled with replacement; never mutate clean arrays in place).
- Default policies: B1, B2, B4. B3 excluded. Edge-IIoTset forbidden.
- Seeds via `SeedSequence([training_seed, poisoning_seed, client_id, scope_id])` — no integer addition.
- `CV(FPR) = σ/µ` (no epsilon). Always report coverage. AUROC invariant.
- Two-layer statistics: per-victim paired deltas → 5 seed aggregates → bootstrap CI. Not 45 independent.
- `mu_flag_threshold` locked before any poisoned run.
- No privacy, deployment, or FL robustness overclaim.

---

This repository implements DATP: Device-Aware Threshold Personalization for federated IoT malware/anomaly detection.

Correctness in this repository means both:

1. Software correctness.
2. Scientific correctness.

Never optimize one by breaking the other.

These instructions apply to all Copilot work in this repository, not only to the autonomous launcher.

Use them for:

```text
normal coding
debugging
reviewing
testing
refactoring
documentation updates
ticket work
scientific audits
workflow audits
autonomous Start_My_Agent execution
```

Do not treat this file as only a launcher file.

---

## 0. Launcher Contract

When the user sends exactly:

```text
Start_My_Agent
```

treat it as the repository launcher command.

The legacy alias below is accepted only to avoid accidental non-triggering from older notes:

```text
StartMyAgent
```

If the user sends `StartMyAgent`, normalize it internally to:

```text
Start_My_Agent
```

Do not ask what it means.

Do not summarize these instructions.

Do not start random refactoring.

Do not wait for the user to create tickets.

Do not ask the user what to do next.

Do not pause for confirmation, approval, or clarification.

Do not stop after readiness if safe work remains.

Immediately start the DATP autonomous workflow from the repository root:

```bash
cd /home/naslouby/Projects/datp-calibration-poisoning
```

Then inspect, audit, create or update tickets only when justified by verified findings, assign work, refactor safely, update tests, re-audit, update ticket/progress evidence, and write a precise handoff before any stop.

The keyword `Start_My_Agent` means:

- resume from the last recorded ticket/progress evidence;
- audit recorded progress;
- audit the codebase;
- audit the tests;
- audit scientific rules;
- audit the conference-to-journal transition;
- audit existing tickets as evidence and dependencies;
- detect technical and scientific discrepancies;
- create or update tickets only after verified findings;
- use available agents and skills;
- use tools and models cost-consciously;
- refactor safely when the active scope authorizes fixing;
- update tests;
- track progress;
- re-audit after changes;
- continue until the active goal is complete or a hard blocker is reached;
- stop only with a precise handoff.

---

### 0.1 Required Copilot mode

`Start_My_Agent` is intended for VS Code Copilot **Agent Mode**.

Agent Mode must be able to:

```text
read files
edit files
run terminal commands
inspect command output
chain multiple actions
update repository progress records
```

If the current Copilot mode cannot do those things, record the limitation in the relevant ticket progress entry or in `docs/tickets/human_interventions.md`.

Then continue with any safe inspection or planning work available.

Do not pretend autonomous execution is possible if the current mode cannot execute it.

---

### 0.2 Resume-first rule

Every `Start_My_Agent` run may be a resumed session.

Before planning new work, read:

```text
docs/tickets/ticket_inventory.md
docs/tickets/ticket_progress.md
docs/tickets/human_interventions.md
```

Then determine:

```text
last active ticket
last active goal
last completed step
last failed step
last edited files
active file locks
stale assumptions
deferred checks
scientific checks still pending
quality checks still pending
next exact safe action
```

Do not restart from zero unless the progress records are missing, corrupt, or contradicted by repository reality.

If written state contradicts the repository, repository reality wins.

Record the contradiction in the relevant ticket progress entry or in `docs/tickets/human_interventions.md`.

Then continue.

---

### 0.3 No-human-interaction rule

During autonomous execution, never ask clarifying questions.

Never pause for:

```text
approval
confirmation
manual ticket creation
manual file ownership decisions
manual test selection
manual handoff writing
```

When information is missing:

1. inspect the repository;
2. inspect ticket and progress records;
3. inspect the active scientific anchors;
4. infer the safest bounded action;
5. continue with the smallest safe next step.

Only stop for a hard blocker.

Hard blockers include:

```text
risk of overwriting unexplained user edits
destructive deletion risk
missing scientific anchors
scientific ambiguity that cannot be resolved from anchors, code, artifacts, plans, or tickets
credentials, login, account, or payment requirements
external service requiring manual interaction
terminal/tool failure with no safe fallback
heavy training or experiments without explicit authorization
actions that would violate the DATP scientific contract
```

When blocked, write:

```text
exact blocker
command or action that failed
evidence
fallbacks attempted
remaining safe work
next command to resume
```

Update the relevant ticket progress entry or `docs/tickets/human_interventions.md` before stopping.

---

### 0.4 Tickets are not the default work target

`docs/tickets/**` is a ledger, dependency source, and evidence record.

It is not the default execution target.

During `Start_My_Agent`, the agent must read tickets for context, ordering, dependencies, blockers, and evidence, but must not begin by editing ticket files unless the active task explicitly targets ticket maintenance.

Default startup target order is:

1. active scientific anchors
2. active task scope
3. impacted code, tests, configs, artifacts, or documentation declared by the active task
4. `docs/tickets/**` only as a record/update layer after verified findings or completed work

Allowed reasons to edit `docs/tickets/**`:

1. the active task is ticket generation, ticket audit, ticket repair, or ticket cleanup;
2. the active task explicitly names `docs/tickets/**` as the target scope;
3. a verified code, test, artifact, workflow, or scientific finding must be recorded;
4. ticket progress must be updated after actual verified work;
5. a blocker or human intervention must be recorded;
6. a ticket status must be corrected because actual repository evidence contradicts it.

Forbidden behavior:

1. starting autonomous work by rewriting tickets;
2. treating tickets as the main implementation target by default;
3. creating tickets before inspecting actual code, tests, progress records, and active task scope;
4. marking tickets complete from prose;
5. spending the first autonomous run cleaning ticket prose instead of readiness, inventory, and active-task execution;
6. editing `docs/tickets/**` just because the files exist;
7. using ticket files as a substitute for inspecting source code, tests, configs, artifacts, and scientific anchors.

If no valid active task exists, inspect repository reality before editing:

```text
docs/tickets/**
```

When in doubt, inspect the active task and repository reality first.

Tickets are updated after evidence exists.

Tickets do not decide the first work scope by themselves.

---

## 1. Repository Context

Work inside:

```text
/home/naslouby/Projects/datp-calibration-poisoning
```

This project is transitioning from the conference DATP paper to the journal extension.

Conference anchors:

```text
Blueprint.md
paper/DATP.tex
paper/sections/
paper/DATP.pdf
```

Journal anchors:

```text
docs/journal/PRE_CODING_PLAN.md
docs/journal/CODING_PLAN.md
docs/journal/EXPERIMENT_PLAN.md
docs/journal/POST_EXPERIMENT_PLAN.md
```

Ticket ledger:

```text
docs/tickets/
docs/tickets/ticket_inventory.md
docs/tickets/ticket_progress.md
docs/tickets/human_interventions.md
```

Tickets are not the default work target.

They are read for dependency context and updated only after verified work or verified findings.

Archived journal-extension context:

```text
Journal/Journal_Extension_Master_Roadmap.md
```

The archived roadmap is context only.

If the archived roadmap conflicts with the active four-file journal package, the active four-file package wins.

Agent and skill anchors:

```text
.claude/agents/
.claude/skills/
.claude/settings.json
```

---

## 2. First Commands on `Start_My_Agent`

Run these first:

```bash
cd /home/naslouby/Projects/datp-calibration-poisoning
pwd
git status --short
python --version
python -m pytest --version
python -m ruff --version
python -m pyright --version || pyright --version
cs --version || true
codex --version || true
claude --version || true
agy --version || true
copilot --version || true
graphify --version || true
uv run vulture --version || vulture --version || true
uv run refurb --version || refurb --version || true
uv run semgrep --version || semgrep --version || true
```

Do not assume a tool exists.

Record tool availability in the relevant ticket progress entry or audit report.

Do not claim a tool exists unless the command proves it.

Do not claim a check passed unless it actually ran.

---

## 3. Required Reading Order

Read these before planning or editing:

1. `.github/copilot-instructions.md`
2. `Blueprint.md`
3. `CLAUDE.md`
4. `paper/DATP.tex`
5. `paper/sections/*.tex`
6. `Journal/Journal_Extension_Master_Roadmap.md`
7. `docs/journal/PRE_CODING_PLAN.md`
8. `docs/journal/CODING_PLAN.md`
9. `docs/journal/EXPERIMENT_PLAN.md`
10. `docs/journal/POST_EXPERIMENT_PLAN.md`
11. `docs/tickets/ticket_inventory.md`
12. `docs/tickets/ticket_progress.md`
13. `docs/tickets/human_interventions.md`
14. relevant `docs/tickets/T*.md` only when the active task or verified finding needs ticket context
15. relevant `docs/tickets/audits/*.md` only when auditing ticket evidence or scientific history
16. `.claude/agents/*.md`
17. `.claude/skills/*.md`

Important rule:

`Journal/Journal_Extension_Master_Roadmap.md` is journal-extension context, but if it conflicts with the active four-file package under `docs/journal/`, the active `docs/journal/` package wins.

Do not hallucinate missing files.

If a file does not exist, record that fact and continue with repository reality.

Do not treat the existence of many ticket files as a reason to make tickets the first work target.

---

## 4. Source-of-Truth Order

Use sources in this order:

1. Actual repository code, tests, configs, scripts, generated artifacts, and command output.
2. `docs/journal/PRE_CODING_PLAN.md`
3. `docs/journal/CODING_PLAN.md`
4. `docs/journal/EXPERIMENT_PLAN.md`
5. `docs/journal/POST_EXPERIMENT_PLAN.md`
6. `docs/tickets/ticket_progress.md`
7. `docs/tickets/ticket_inventory.md`
8. Individual tickets under `docs/tickets/`
9. Audit reports under `docs/tickets/audits/`
10. `.claude/agents/`
11. `.claude/skills/`
12. `Journal/Journal_Extension_Master_Roadmap.md`
13. `paper/DATP.tex`
14. `paper/sections/*.tex`
15. `Blueprint.md`
16. `CLAUDE.md`
17. `AGENTS.md`

Do not trust documentation that says something is done.

Verify actual implementation, tests, outputs, and artifacts.

Do not hallucinate files, commands, agents, tickets, results, datasets, or previous work.

If a referenced file does not exist, adapt to the actual repository.

Ticket prose is never stronger evidence than code, tests, artifacts, and command output.

---

## 5. Conference-to-Journal Transition Audit

The first major audit must check the transition from the conference paper to the journal extension.

Audit for discrepancies between:

```text
Blueprint.md
paper/DATP.tex
paper/sections/*.tex
Journal/Journal_Extension_Master_Roadmap.md
docs/journal/*.md
docs/tickets/*.md
src/datp/
tests/
outputs/
results/
```

Find:

```text
stale conference assumptions
stale journal assumptions
stale roadmap claims
journal tasks missing from code
code implementing rejected behavior
code missing required feasibility gates
docs claiming unsupported behavior
tests validating obsolete behavior
tickets with obsolete scope
duplicate tickets
contradictory tickets
missing tickets
unsupported paper claims
unsupported result claims
baseline semantic drift
regime semantic drift
hidden retraining
stage-boundary violations
dataset metadata fabrication
```

Create or update tickets only for real findings.

Do not create vague tickets.

Do not create duplicate tickets.

Do not mark any ticket `DONE` from prose alone.

Do not start by rewriting tickets.

Inspect active task scope first.

---

## 6. Agent and Skill Utilization

Use `.claude/agents` and `.claude/skills` as role contracts when supported.

Available agent roles include:

```text
orchestrator-agent
implementation-agent
refactor-agent
test-agent
reviewer-agent
scientific-contract-agent
drift-enforcer-agent
code-quality-gate-agent
ticket-planner-agent
ticket-completion-auditor-agent
results-audit-agent
experiment-runner-agent
paper-update-agent
```

Available skills include:

```text
artifact-audit-skill
datp-invariant-check-skill
experiment-gate-skill
human-intervention-gate-skill
latex-paper-skill
long-run-monitoring-skill
paper-claim-discipline-skill
refactor-clean-code-skill
results-statistics-skill
schema-enum-constant-skill
static-analysis-quality-gate-skill
test-coverage-skill
ticket-audit-skill
ticket-completion-audit-skill
ticket-generation-skill
ticket-progress-skill
```

If agents or skills are unavailable, continue manually.

Do not claim an agent or skill was used unless it was actually used.

Parallel work is allowed only when file scopes are disjoint.

Do not let two agents edit overlapping files.

---

## 7. Progress Records

Use written progress records to avoid redundant checks and enable continuation after stopped sessions.

Every flag must record:

```text
what was checked
command or inspection method
file paths covered
git commit or working-tree context
timestamp if available
result
invalidation rule
```

A flag is obsolete if:

```text
any referenced file changed
imports changed
package structure changed
tests changed
configs changed
tickets changed
scientific assumptions changed
Graphify graph was generated before major moves
Vulture/Refurb/Semgrep was run before major moves
later audit contradicts it
```

Never trust stale memory over current code.

Never rely on chat history for continuation.

---

## 8. Graphify Usage

Graphify should be used repeatedly during refactoring.

Check whether Graphify is available:

```bash
graphify --version || true
```

If missing, check installers:

```bash
uv --version || true
pipx --version || true
python -m pip --version
```

Preferred install:

```bash
uv tool install graphifyy
```

Alternative:

```bash
pipx install graphifyy
```

Fallback:

```bash
python -m pip install graphifyy
```

Register when useful:

```bash
graphify install
graphify install --platform copilot
graphify vscode install
```

Run from repo root:

```bash
graphify .
```

If slash commands are available:

```text
/graphify .
```

Refresh Graphify:

1. during initial repository mapping;
2. after major package moves;
3. after scoring, thresholding, metrics, eligibility, artifact, reporting, or test-structure changes;
4. after deleting wrappers or compatibility shells;
5. before final hostile architecture review;
6. whenever architecture assumptions are stale;
7. whenever check flags invalidate graph evidence.

Record useful Graphify findings in the relevant ticket progress entry or audit report.

Graphify is an accelerator, not proof.

Verify important findings with:

```text
rg
code inspection
ruff
pyright
pytest
CodeScene
Vulture
Refurb
Semgrep
scientific documents
actual artifacts
```

---

## 9. Model and Token Policy

Use normal tools first:

```text
git
rg
find
python
ruff
pyright
pytest
cs
graphify
vulture
refurb
semgrep
```

Default model/tool roles:

```text
VS Code Copilot + DeepSeek V4 Pro: main orchestrator and coding worker
WSL Copilot CLI: secondary lightweight helper
Codex CLI with o3: audit, diff review, test review, independent verification
Claude Code with Sonnet: scientific review, architecture review, hostile final review
Antigravity CLI through agy: optional extra implementation, audit, repair, or verification
```

Codex default:

```bash
codex -m o3 exec "prompt"
```

Claude default:

```bash
claude --model sonnet -p "prompt"
```

Antigravity command:

```bash
agy
```

Before relying on Antigravity interactively, check:

```text
/usage
/quota
/model
```

Do not use these unless explicitly approved for the exact task:

```text
Claude Opus
Codex gpt-5.5
Codex gpt-5.5 high
expensive Gemini Ultra/Pro-style models
```

If quota is hit:

```text
write a handoff
record active locks
record completed checks
record pending checks
update ticket progress
continue with cheaper tools or another approved agent
do not lose state
```

---

## 10. Ticket System Behavior

Tickets are ledgers, not the default implementation target.

Do not wait for the user to create tickets.

For every verified finding, choose exactly one:

```text
fix immediately inside active scope
attach to existing ticket
create new ticket
mark blocked with precise blocker
mark rejected because it violates scientific scope
```

Every created or updated ticket must include:

```text
objective
scope
files likely impacted
scientific risks
technical risks
required checks
acceptance criteria
assigned role/tool
status
re-audit trigger
```

Do not create duplicate tickets.

Do not create tickets that only say “clean code.”

Do not mark tickets complete from prose.

Verify actual code, tests, and artifacts.

Only edit `docs/tickets/**` when there is verified evidence or when the active task explicitly targets tickets.

Do not select `docs/tickets/**` as the first work scope merely because tickets exist.

---

## 11. Scientific Contract

Protect the DATP scientific identity.

For any fixed dataset, regime, seed, and alpha value:

```text
B1, B2, B3, and B4 must share the same trained federated autoencoder.
```

For B1–B4:

```text
AE architecture is fixed.
FedAvg training protocol is fixed.
local epochs are fixed.
data split is fixed.
random seed is fixed.
score artifacts are fixed.
only threshold calibration scope varies.
```

Reject any change that:

```text
trains a separate encoder per baseline
changes model architecture differently across B1-B4
changes training protocol differently across B1-B4
uses different seeds across B1-B4
recomputes scores inside threshold/result/report stages
adds baseline-specific score directories for B1-B4
adds baseline-specific checkpoints for B1-B4
turns supportive evidence into the main claim
fabricates unavailable dataset metadata
reports CV(FPR) without coverage
```

Main claim remains:

```text
Threshold calibration scope under a fixed encoder and fixed FedAvg setup.
```

Primary comparison:

```text
Regime A
B1 vs B2
CV(FPR)
bootstrap confidence interval
coverage ratio
```

---

## 12. Baseline and Comparator Meanings

Canonical baseline meanings:

| Label | Meaning | Scope |
|---|---|---|
| B0 | Centralized AE reference comparator | Reference only |
| B1 | Shared/global threshold | Core |
| B2 | Per-client threshold | Core primary comparator against B1 |
| B3 | Family/group threshold | Core variant where applicable |
| B4 | Fingerprint-cluster threshold | Core variant |
| B5 | Local-only bounding case | Supplementary or ablation only |
| B-FedStatsBenign | Benign-only federated-statistics comparator | Journal comparator |
| B-LaridiFaithful | Faithful Laridi-style comparator using anomaly-labeled summaries where permitted | Outside DATP benign-only assumption |
| FedProx | Aggregation stress test | Not main threshold ladder |
| Ditto | Personalization stress test only if faithfully implemented | Not main threshold ladder |
| FedRep-AE/FedPer-AE fallback | Fallback local-head/shared-representation comparator | Must not be called Ditto unless faithful |

Do not rename baselines casually.

Do not make B5 the headline.

Do not call `B-FedStatsBenign` faithful Laridi.

Do not call a FedRep/FedPer fallback Ditto.

Do not treat FedProx or personalization comparators as part of B1–B4 threshold-scope causal evidence.

---

## 13. Train Once, Derive Many

The mainline invariant is:

```text
for each fixed dataset/regime/seed/alpha:
    train shared FL encoder once
    save checkpoint once
    generate shared per-client score artifacts once
    derive B1-B4 thresholds from saved scores
    compute result metrics from saved scores and thresholds
```

Do not implement:

```text
for each baseline:
    train a new encoder
```

Do not hide baseline-specific retraining behind:

```text
runner convenience
CLI shortcuts
threshold functions
evaluation functions
analysis scripts
reporting scripts
audit scripts
```

---

## 14. Score Artifacts

Score artifacts are shared across B1–B4 for a fixed training cell.

Score paths must not be baseline-specific for B1–B4.

Score artifacts must include the expected score column:

```text
reconstruction_error
```

Score artifacts must separate:

```text
calibration scores
test benign scores
test attack scores
```

Thresholding consumes saved scores.

Evaluation consumes saved scores and thresholds.

Reporting consumes saved result artifacts.

Do not recompute reconstruction errors in downstream stages.

---

## 15. Artifact Layout

Artifact layout must remain canonical.

Expected shared training layout:

```text
outputs/checkpoints/<regime>/seed_<N>[/alpha_<alpha>]/
outputs/scores/<regime>/seed_<N>[/alpha_<alpha>]/
```

Expected baseline-specific result layout:

```text
outputs/results/<regime>/<baseline>/seed_<N>[/alpha_<alpha>]/
```

Expected logs layout:

```text
outputs/logs/<regime>/<baseline>/seed_<N>[/alpha_<alpha>]/
outputs/console_logs/
```

Expected files:

```text
model.pt
metrics.json
manifest.json
scaler.pkl
DONE.txt
IN_PROGRESS
ABORTED.txt
```

`metrics.json.tmp` is not a completed result.

A result exists only if `metrics.json` exists and is non-empty.

Do not treat `.tmp` placeholders as success.

---

## 16. Configuration Discipline

Scientific parameters must come from config.

Do not hide scientific values as module constants.

Config-driven values include:

```text
n_min
q
seeds
alpha values
rounds_initial
rounds_max
convergence_relative_threshold
batch size
feature count
dataset paths
threshold quantiles
cluster K when scientifically configured
```

Before a run, validate:

```text
cfg.model.input_dim == cfg.dataset.feature_count
dataset schema matches feature count
test_benign exists
test_attack exists
resource bounds are safe
resolved config is written
```

Do not silently fall back to values that change scientific behavior.

---

## 17. Determinism

At every experiment entrypoint, set seeds for:

```text
Python random
NumPy
PyTorch CPU
PyTorch CUDA when available
```

Do not introduce nondeterministic data splits.

Do not introduce nondeterministic clustering without controlled seeds.

Do not use random defaults without explicit configuration.

---

## 18. Dataset and Regime Discipline

Regime meanings:

| Regime | Meaning |
|---|---|
| Regime A | N-BaIoT natural physical-device split; confirmatory |
| Regime B-a | CICIoT2023 file-level pseudo-clients; boundary/external validation |
| Regime B-b | Conditional CICIoT2023 device-MAC or device-group repartition after feasibility gate |
| Regime C | N-BaIoT Dirichlet severity sweep; supportive/exploratory |
| Regime D | Conditional Edge-IIoTset external validation after feasibility gate |

Do not fabricate device identifiers.

Do not invent dataset metadata.

Do not treat pseudo-clients as physical devices.

Do not upgrade feasibility-gated regimes to confirmed regimes without evidence.

Do not use archived roadmap assumptions over active `docs/journal/` files.

---

## 19. Calibration-Pending Clients

Calibration-Pending handling is scientifically critical.

Clients with fewer than `n_min` benign calibration samples are Calibration-Pending.

Rules:

```text
Calibration-Pending clients receive the global fallback threshold.
Calibration-Pending clients are excluded from eligible-only aggregation.
Coverage ratio must be reported.
CV(FPR) must be interpreted with coverage.
```

Do not silently drop pending clients without reporting coverage.

Do not include pending clients in eligible-only calculations.

Do not change fallback behavior without a scientific ticket and audit.

---

## 20. Metrics and Reporting

Primary endpoint:

```text
CV(FPR)
```

Always report coverage ratio with CV(FPR).

Other metrics:

```text
CV(TPR)
Macro-F1
worst-client balanced accuracy
mean FPR
mean TPR
P10 Macro-F1 where required
IQR(FPR)
max-min FPR
```

Baseline comparisons require confidence intervals when used for claims.

Use seed-level deltas for bootstrap comparisons when required.

Do not overinterpret non-confirmatory regimes.

Do not write causal language for mechanism analyses unless the design supports causality.

---

## 21. Code Ownership and Structure

Maintain clear package ownership.

Audit these packages:

```text
src/datp/analyses
src/datp/artifacts
src/datp/audit
src/datp/baselines
src/datp/cli
src/datp/config
src/datp/core
src/datp/data
src/datp/evaluation
src/datp/models
src/datp/pipeline
src/datp/reporting
src/datp/statistics
src/datp/sweep
src/datp/training
tests
```

Find unclear ownership in:

```text
scoring
thresholding
metrics
eligibility
artifact paths
baseline enums
regime enums
score loading
metric serialization
result loading
config validation
dataset schema validation
test fixtures
synthetic builders
```

If structure is wrong:

```text
create or update the ownership map
update ownership documentation when relevant
create tickets only after verified findings
move code by responsibility
update imports
update tests
delete obsolete shells
refresh Graphify after major moves
rerun optional tools if cleanup claims depend on them
```

Do not leave wrappers or redirects.

No internal backwards compatibility.

---

## 22. Refactoring Rules

Fix:

```text
duplicated logic
scattered constants
scattered enums
hardcoded scientific values
hardcoded artifact names
hardcoded baseline strings
hardcoded regime strings
long functions
long classes
weak abstractions
unused objects
dead modules
obsolete wrappers
redirect files
compatibility shells
circular imports
fragile imports
repeated fixtures
skipped tests
xfailed tests
commented-out tests
unclear package ownership
scattered path construction
repeated score loading
repeated metric parsing
repeated eligibility logic
```

Do not refactor just to create churn.

If code is already clean, leave it unchanged and prove cleanliness through checks.

---

## 23. Clean Code Rules

Use the clean-code checklist below as the canonical clean-code rulebook.

Mandatory checks:

```text
closed concepts use enums
stable names use canonical constants
structured values use dataclasses or typed objects
utilities have domain ownership
no wrappers
no redirects
no compatibility aliases
no old package shells
no old-path tests
no duplicate typed shapes
no hidden scientific constants
tests move with production code
no skipped/xfailed/commented-out tests hiding failures
```

Do not create vague `utils`, `helpers`, `common`, `misc`, or `shared` modules unless ownership is explicit and unavoidable.

---

## 24. Duplication and Hardcoded Values

Search for duplication in:

```text
score loading
metric parsing
path construction
artifact naming
baseline strings
regime strings
threshold eligibility
calibration-pending handling
result serialization
dataset schemas
fixture builders
CUDA/device checks
config fallbacks
```

Do not fix repeated problems locally one by one.

Promote repeated problems to:

```text
docs/tickets/
```

Only promote to `docs/tickets/**` after the repeated pattern is verified.

---

## 25. Typing and Naming Rules

Prefer:

```text
enums
frozen dataclasses
typed config models
typed request objects
typed result objects
clear domain names
canonical path builders
explicit artifact descriptors
```

Avoid:

```text
untyped dictionaries
anonymous tuples
duplicate NamedTuple shapes
long primitive argument lists
internal str-or-enum unions
repeated parsing inside domain logic
isinstance-based enum normalization scattered across modules
```

Parse strings at boundaries.

Use typed domain values internally.

---

## 26. Complexity, Dead Code, and Wrappers

Reduce:

```text
deep nesting
long functions
long classes
high argument counts
wide branching
unused objects
dead imports
unreachable code
over-specified docstrings
comments that repeat code
```

Do not reduce complexity by:

```text
hiding scientific steps
collapsing meaningful stages
weakening names
using clever one-liners
using broad dynamic dispatch
adding magic defaults
adding side effects
```

Dead-code tools are only signals.

Vulture findings are suspects.

Verify before deletion.

---

## 27. Error Handling and Logging

Use explicit errors for:

```text
missing artifacts
empty metrics
invalid score schemas
invalid configs
missing datasets
wrong feature counts
unsafe stage transitions
scientific invariant violations
```

Do not swallow exceptions that indicate scientific or artifact corruption.

Do not log success before artifacts are actually complete.

Do not let logging imply unsupported claims.

---

## 28. Test Quality Rules

Do not:

```text
mark failing tests as skipped
mark failing tests as xfail
comment out failing tests
delete tests just because they fail
weaken assertions to pass
mock away the behavior being verified
replace meaningful tests with smoke tests
let tests pass silently on missing artifacts
hide tests behind environment flags unnecessarily
skip CUDA/GPU tests when CUDA is available
```

Fix:

```text
failing tests
errored tests
collection errors
import errors
fixture errors
skipped package-related tests
xfailed package-related tests
commented-out tests
nondeterministic tests
brittle implementation-detail assertions
tests that assert mocks instead of behavior
tests without meaningful assertions
tests that preserve old internal import paths
tests that validate obsolete package names
```

Do not run full E2E by default.

Run impacted E2E only when directly required.

---

## 29. Required Test Scenarios

Test coverage must protect:

```text
shared training invariant
score artifact reuse
no per-baseline retraining
threshold derivation from saved scores
Calibration-Pending fallback
coverage ratio reporting
CV(FPR) computation
baseline-specific result paths
shared checkpoint paths
shared score paths
config validation
dataset schema validation
determinism
metric serialization
reporting sidecars
no placeholder results
```

When refactoring, update impacted tests.

Do not keep old tests alive solely to preserve obsolete paths.

---

## 30. Static Analysis and Quality Gates

Default required checks after code/test changes:

```bash
git status --short
python -m ruff check src/datp tests
python -m pyright
python -m pytest <impacted-test-paths>
```

Use CodeScene when useful and available:

```bash
cs delta
cs review
make codescene-check
```

Use optional extra tools when useful and available:

```bash
uv run vulture src/datp tests --min-confidence 80
uv run refurb src/datp tests
uv run semgrep scan --config auto src/datp tests
```

Use Sonar only as optional final audit if healthy.

Do not claim Sonar passed unless it actually ran.

Do not claim CodeScene passed unless it actually ran.

Do not claim Vulture, Refurb, or Semgrep passed unless they actually ran.

---

## 31. Refactor Workflow

For every meaningful scope, perform:

```text
pre-change audit
implementation
targeted tests
static checks
optional extra-tool checks when useful
post-fix audit
integration re-audit
scientific-contract audit
hostile reviewer audit
ownership-map update when relevant
progress record update
handoff update
```

Do not stop after first green check.

Do not treat pre-existing failures as acceptable.

Do not make churn changes on second run.

When the active task authorizes fixing, do not stop at audit-only reporting.

Fix in the smallest safe batch, then re-audit.

---

## 32. Non-Negotiable Rejection Rules

Reject changes that:

```text
create wrappers
create redirects
create compatibility aliases
create old package shells
preserve old internal import paths
add old-path tests
weaken tests
skip failing tests
hide scientific constants
retrain per baseline
recompute scores downstream
change baseline semantics
change regime semantics
fabricate metadata
overclaim privacy
overclaim robustness
overclaim deployment
treat archived roadmap as active plan
overwrite unexplained user work
start autonomous work by editing docs/tickets as the default target
```

---

## 33. Paper and Documentation Rules

Documentation must match actual code and artifacts.

Do not update docs to hide unfinished work.

Do not mark tickets complete from docs alone.

When editing paper or docs:

```text
separate direct evidence from supportive evidence
avoid unsupported causal language
avoid deployment/privacy/robustness overclaims
report coverage with CV(FPR)
keep Regime A confirmatory
keep Regime B/C/D scope correct
keep stress tests outside the B1-B4 causal ladder
keep archived roadmap as archived context
```

Do not use result wording that is stronger than the evidence.

---

## 34. Definition of Done

Nothing is `DONE` until:

```text
code reality was inspected
documentation reality was inspected
scientific rules were inspected
conference-to-journal transition was inspected when relevant
tickets were updated only from verified evidence
progress records were updated
ownership maps were updated when relevant
move/test plans were updated when reality changed
Graphify status was refreshed or explicitly deferred with reason when architecture changed
Vulture/Refurb/Semgrep status was recorded if used
impacted code was refactored
impacted tests were updated
ruff passed or remaining issues were documented with reasons
pyright passed or remaining issues were documented with reasons
impacted tests passed
CodeScene was run when useful or explicitly deferred with reason
Sonar was not falsely claimed
skipped/xfailed/commented-out tests were removed or justified
no wrappers or redirects remain from internal moves
scientific invariants were preserved
later re-audit passed
handoff was written
```

If later re-audit has not happened, use:

```text
REAUDIT_REQUIRED
```

not:

```text
DONE
```

---

## 35. Final Report and Handoff

When stopping, write a handoff in the relevant ticket progress entry or audit report.

Also update `docs/tickets/human_interventions.md` if a blocker requires human action.

Include:

```text
current git status
active task
active ticket
active locks
completed work
files changed
commands run
checks passed
checks failed
Graphify status
Vulture/Refurb/Semgrep status
ownership-map status
scientific risks
unresolved issues
next exact action
whether memory/flags remain valid
```

When reporting to the user, include only evidence-backed claims.

Do not claim:

```text
a file was reviewed unless inspected
a test passed unless run
a tool passed unless run
SonarQube passed unless actually executed
CodeScene passed unless actually executed
Vulture passed unless actually executed
Refurb passed unless actually executed
Semgrep passed unless actually executed
Graphify findings are proof without verification
all issues are fixed unless checks support it
```

Any remaining issue must include:

```text
exact file
exact reason it remains
exact risk
exact next action
```

---

## 36. Default Principle

When uncertain, choose the action that is:

```text
scientifically safest
smallest correct change
most consistent with canonical code owners
easiest to test
least likely to introduce churn
most honest about evidence
```

Never sacrifice scientific validity for cleaner-looking code.

Never sacrifice code correctness for a stronger-looking research result.

Never treat ticket prose as a substitute for repository evidence.

---

## AGENTS.md

The repository may also include `AGENTS.md`.

If present, use it as an additional role map.

If `AGENTS.md` conflicts with this file or the active scientific contract, this file and the scientific contract win.

---

## Purpose

The agent system exists to support disciplined, auditable, scientifically safe work.

Agents are not allowed to bypass repository reality, test results, or scientific constraints.

Agents must update progress records and handoff notes.

Agents must never create the appearance of progress without evidence.

---

## Behavioral Guidelines

Agents must:

```text
inspect first
act in the smallest safe batch
record evidence
update tests
update maps
update tickets only from verified evidence
update handoff
re-audit
continue until done or blocked
```

Agents must not:

```text
hallucinate files
ignore existing state
overwrite user changes
skip scientific review
hide failed checks
create wrappers
keep old paths alive
mark tickets done from prose
ask the user what to do next during Start_My_Agent
start autonomous work in docs/tickets unless ticket maintenance is the active task
```

---

## Core Rule

The real repository is the source of truth.

Plans, tickets, maps, reports, and handoffs are valid only after they match real code, tests, artifacts, and command output.

---

## Agents

### Orchestrator Agent

Owns:

```text
startup
progress reading
ticket coordination
role routing
handoff quality
final status
```

Must update progress records and handoff notes.

Must not choose `docs/tickets/**` as the default first work target.

### Implementation Agent

Owns:

```text
small scoped code changes
direct import repair
test updates
no-wrapper enforcement
simple command verification
```

Must not make unsupported scientific changes.

### Refactor Agent

Owns:

```text
package ownership repair
duplication consolidation
constants/enums/dataclasses cleanup
module boundary cleanup
old-path deletion
```

Must not preserve backwards compatibility internally.

### Test Agent

Owns:

```text
targeted test updates
fixture cleanup
skipped/xfail audit
old-path test removal
behavior-focused assertions
```

Must not weaken tests to pass.

### Code Quality Gate Agent

Owns:

```text
Ruff
Pyright
targeted pytest
CodeScene when useful
Vulture when useful
Refurb when useful
Semgrep when useful
Sonar only if healthy and final-only
```

Must not claim tools passed unless they ran.

### Ticket Completion Auditor Agent

Owns:

```text
actual-code verification
actual-test verification
evidence-backed DONE status
dependency checks
re-audit status
```

Must not trust ticket prose.

### Drift Enforcer Agent

Owns:

```text
scientific drift detection
baseline semantics
regime semantics
claim discipline
stage boundaries
journal plan consistency
```

Must block unsafe scientific changes.

### Scientific Contract Agent

Owns:

```text
B1 versus B2 identity
shared-score invariant
fixed-encoder invariant
Calibration-Pending handling
CV(FPR) and coverage reporting
bootstrap comparison discipline
```

### Experiment Runner Agent

Owns:

```text
experiment readiness
run gates
resource checks
no accidental heavy jobs
artifact completion validation
```

Must not launch heavy experiments unless explicitly authorized.

### Results Audit Agent

Owns:

```text
metrics lineage
artifact validation
figure/table sidecars
result completeness
claim support
```

### Paper Update Agent

Owns:

```text
paper text updates
caption/table consistency
claim wording
IEEE/journal writing discipline
evidence qualification
```

Must not overclaim.

---

## Ticket Workflow

Tickets are execution records, dependencies, and evidence ledgers.

Tickets are not the default first work target.

Ticket status must reflect actual verified state.

Every ticket must include:

```text
objective
scope
evidence
scientific risk
technical risk
required implementation
required tests
required audit
acceptance criteria
status
```

---

## Status Rules

Allowed statuses:

```text
NOT_STARTED
READY
IN_PROGRESS
BLOCKED
NEEDS_REPAIR
NEEDS_REAUDIT
REAUDIT_REQUIRED
DONE
```

`DONE` requires:

```text
implementation evidence
test evidence
static-check evidence
scientific-contract evidence
ownership-map update when relevant
handoff update
post-fix audit
later re-audit
```

---

## Prohibited Completion

Do not mark complete when:

```text
tests were not run and no valid reason is recorded
Ruff/Pyright were skipped without reason
scientific invariant was not checked
files were not inspected
progress records were not updated
handoff was not written
old wrappers remain
old redirects remain
old compatibility aliases remain
old-path tests remain
skipped tests hide failures
duplicate string/enum/constant/schema ownership is scattered
hardcoded scientific values remain
DATP invariants are not checked
drift check is required but missing
progress files are stale
ticket files were edited without repository evidence
```
