# Fix Log

## Fix 1
- File changed: `paper/sections/threat_model.tex`
- Section/location: Threat Model, Attack mechanics, Raise bullet.
- Issue category: scientific correctness; numerical/protocol consistency.
- Reason: manuscript stated `floor(f * n_v)`, but locked protocol and implementation use `max(1, round(f * n))` for positive fractions.
- Summary: replaced floor-based budget with `m=max(1, round(fn_v))` for `f>0`.
- Compile rerun: YES.
- Visual audit rerun: YES.
- Page count changed: NO, final remains 14 pages.
- Further action needed: NO.

## Fix 2
- File changed: `paper/sections/threat_model.tex`
- Section/location: Threat Model, Attack mechanics, Lower bullet.
- Issue category: reviewer clarity.
- Reason: Lower bullet references `m`; after fixing the Raise bullet, `m` needed to remain explicitly defined in the preceding bullet.
- Summary: retained compact `replace $m$ positions` wording after defining `m` in Raise.
- Compile rerun: YES.
- Visual audit rerun: YES.
- Page count changed: NO, final remains 14 pages.
- Further action needed: NO.

## Rejected/Deferred Items
- Figure regeneration: rejected, current figures are readable and no source values are contradicted.
- New raw-traffic experiment: rejected, outside score-level paper identity.
- New defenses or robust aggregation evaluation: rejected, wrong threat surface.
- New datasets or collusion experiments: rejected/deferred, outside main N-BaIoT single-client scope.
- Abstract compression: rejected, would risk removing necessary caveats; not a hard LNCS blocker.
- Cosmetic overfull fixes: rejected where visual audit shows no readability defect and page-budget risk is high.
- Unused `table_config.tex` cleanup: rejected as repository cleanup outside compiled paper.
