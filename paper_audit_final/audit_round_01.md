# Audit Round 01: Scientific Contract and Claim Discipline

## Scope
Audited title, abstract, keywords, introduction, related work, threat model, method, results, discussion, limitations, conclusion, figure captions, and table captions against `docs/DATP_CP_Roadmap.md` and prior paper governance.

## Findings

1. MUST_FIX: Threat-model injection budget used `floor(f * n_v)` while the locked protocol and implementation use `max(1, round(f * n))` for positive fractions.
   - Location: `paper/sections/threat_model.tex`, Attack mechanics, Raise bullet.
   - Risk: scientific correctness and protocol mismatch.
   - Fix: replaced floor formula with the locked fixed-budget formula.

2. MUST_FIX: After the budget formula edit, the Lower bullet needed to retain a clear reference to the same `m` budget.
   - Location: `paper/sections/threat_model.tex`, Attack mechanics, Lower bullet.
   - Risk: reader confusion if `m` is not defined.
   - Fix: kept compact `m` reference after defining `m` in the Raise bullet.

3. REJECTED: Add raw-traffic realizability claims or deployment interpretation.
   - Reason: forbidden by roadmap; paper already states score-level proxy and traffic-level future work.

4. REJECTED: Add privacy, robust-FL, model-poisoning, training-poisoning, aggregation-poisoning, backdoor, or evasion claims.
   - Reason: forbidden by roadmap; current paper uses these only as related-work contrasts or explicit negations.

## Result
PASS after fixes. Claims remain bounded to single-client, score-level calibration-channel poisoning on N-BaIoT with fixed model weights and fixed test scores/labels.
