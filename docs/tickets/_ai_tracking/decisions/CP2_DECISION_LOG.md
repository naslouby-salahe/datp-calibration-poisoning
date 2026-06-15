# CP2 Decision Log

Record every binding decision, blocker, and fallback activation here. Each entry
is a standalone, evidence-backed record. Do not delete entries; supersede them.

> Decisions must cite repository evidence (file paths, commands, outputs). A
> decision without evidence is a hypothesis, not a decision.

---

## Entry template

```
### DEC-NNNN — <short title>
- Date:
- Ticket(s):
- Type: decision | blocker | fallback-activation | scope-clarification
- Context:
- Evidence (paths / commands / outputs):
- Decision:
- Consequence / follow-up tickets:
- Status: open | resolved | superseded-by DEC-MMMM
```

---

## Fallback register (conditional — do NOT activate without trigger evidence)

| Fallback | Trigger (summary) | Ticket |
|---|---|---|
| CP2-FB1 | Clean score artifacts fail provenance/E=1 audit | `phase_a_audit/CP2-FB1.md` |
| CP2-FB2 | Victim 10% tail reservoir degenerate (<2 distinct values) | `phase_c_core_implementation/CP2-FB2.md` |
| CP2-FB3 | B4 procedure not reproducible from artifacts | `phase_a_audit/CP2-FB3.md` |
| CP2-FB4 | CICIoT2023 client semantics unsafe / B4 K shifts | `phase_f_full_optional/CP2-FB4.md` |

---

## Entries

_None yet._
