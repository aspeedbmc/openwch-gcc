# Phase 3f completion audit addendum

## Status and relationship to the sealed package

This is a **post-seal, unsealed addendum**. It was written after the
reviewer-v3 freeze and the final live seal, and is intentionally not an input
to either. It does not rewrite the historical evidence package.

The execution has reached the terminal state **`INVALID`**. This means the
request to execute `tmp/prompts/phase-3f.md` can be returned as a completed
invalid run. It does **not** mean that the Phase 3f closure mission, the frozen
byte gate, the current-series matrix, or the toolchain project is complete.

The three result layers remain:

1. formal Phase 3f: `INVALID`;
2. frozen GCC 3 + binutils 6: `COUNTERFACTUAL-FAIL`;
3. current GCC 9 + binutils 6: `UNTESTED`.

The reviewer-v3 package remains a coherent historical snapshot within its
declared proof scope. Its manifest SHA-256 is
`f69a3ff1f98e484cd6f099fa09d8f3c7293c3430ed15636842012459e75d1990`.
The final live-seal JSON SHA-256 is
`8a127ba3d16f3d1298e3c4c1f7de6c4f9820997706e1546209b3410db0cc9ec5`.
Neither hash covers this addendum.

## Completion-audit findings

### T0 through T2

The frozen experiment itself was executed. The evidence contains the V2
pristine provenance and immutable 3,177-file installation, exact control
rehashes, the four-side driver/backend/GAS/L4 matrices, same-physical-path
identity controls, all 57 formerly unavailable mandatory probes, and the
exhaustive XW, custom32, and halfword denominators. The 35-feature table has
18 byte-exact, 11 behavior-exact, one upstream-identical, and five GAP rows.

Two historical boundary violations prevent a valid run:

- `P3F-BOUNDARY-0001` proves that the protected GCC series changed after the
  V2 freeze. The authoritative evidence is
  `tmp/phase3f-evidence/poststate/current/boundary-violation-events.tsv` and
  `tmp/phase3f-evidence/poststate/current/capture.json`.
- The first closure registration had 637 rows and SHA-256
  `5e6061bc58dbf05008de1e6bf09951e6a1c09f5ec1719a889f3c1ac09d89033d`.
  It was later overwritten at the same paths by a 636-row registration with
  SHA-256
  `7445cecbc2925435e748dc9ab1c083c7d9ba4e975dff111bbc546905341f7110`.
  The before/after wrapper records survive under
  `tmp/phase3f-evidence/commands/T0-BUILD-CLOSURE-OBLIGATIONS/` and
  `tmp/phase3f-evidence/commands/T0-REBUILD-CLOSURE-OBLIGATIONS-636/`, but the
  637-row content was not preserved. This violates the task book's
  append-only/no-deletion rule even though the final 636-row denominator is
  mechanically reproducible.

The sealed ledger's 636/636 latest-event coverage is therefore an accounting
property of the surviving registration, not proof that the run-wide boundary
or registration history was valid.

### T3 slim-LTO

The six-object denominator and logical-stream localization were executed, but
three producer causes remain `STILL-UNRESOLVED`:

- `DECL-MAIN-NODE-FIELD-OR-ORDER`;
- `ICF-HASH-INPUT-CAUSE`;
- `DEBUG-STATEMENT-FRONTIER-ORIGIN`.

The evidence proves six `.decls` main-stream differences, four serialized
`sem_item::get_hash()` field differences, and a bounded debug-statement
frontier difference. It does not finish the requested cause attribution or a
per-section functional-versus-metadata classification. Exact final ELF/BIN
consumers and 12 exact direct controls do not waive the six `.o` failures.

### T4 backend, tuning, and errata

The bounded tuning and errata work is complete at its stated strength:
1,056 selector rows, 276/276 WCH-versus-V2 comparisons, the static tune/cost/
pipeline denominators, and all 44 errata findings are accounted for. The
compiler-side fast-interrupt/vector behavior remains an in-gate GAP.

On-device HPE-generation, nested-vector, and calling-ABI safety remains
`RULED-OUT-OF-GATE` residual risk. The rejected alternative is a per-device-
generation hardware campaign with nested-interrupt, vector-state, and ABI
instrumentation. Its cost is a hardware/firmware test matrix, and it cannot
replace compiler artifact-byte comparison. No hardware-safety claim follows
from the compile-only evidence.

### T5 host Mach-O

The sealed package mechanically proves 47 four-side different paths, 188
complete file-side tilings, 8,166 intervals, and reproducibility of its
declared ASCII-string/symbol census. That is useful bounded evidence, but the
strong `FUNCTIONAL-LAYER-CLOSED` wording is not established at the full
strength required by the task book:

- whole `__TEXT,__text` sections are assigned a generalized owner from their
  implementation component rather than attributed function-by-function to a
  concrete canonical feature;
- 388 host-ABI and 204 generic host-data rows are reclassified when no
  declared ASCII/symbol target marker is present, which does not exclude an
  unnamed numeric cost, opcode, or dispatch table;
- the negative-space audit scans ASCII strings and `nm` symbols. Its zero
  unmapped count means zero under that declared lexical policy, not proof that
  unknown target-facing code or binary data-table differences do not exist.

Consequently the 172 semantic supersessions and 349 historical region
rule-outs are preserved as the sealed package's historical judgments, but
this completion audit does not use them to claim the stronger T5 semantic
premise. A valid rerun must either perform feature-specific function/data-table
attribution or retain the unproved rows as unresolved.

### T6 reviewer qualification and scope

Reviewer-v3 independently recomputed the frozen package and correctly kept
formal `INVALID`, frozen `COUNTERFACTUAL-FAIL`, and current `UNTESTED`
separate. The repository records the reviewer identity
`/root/independent_reviewer_v3_fresh`, but does not preserve model/effort or
participation-history metadata sufficient to prove the task book's
Opus-level/fresh-reviewer qualification from repository artifacts alone.
That is an additional qualification limitation, not a reason to upgrade or
downgrade any measured byte comparison.

The Linux four-pass T6 material in reviewer-v3 is separate Phase 3d evidence
with proof scope `SEALED-FINALIZER-ATTESTATION`. It does not enter the
darwin-arm64 Phase 3f matrix or test current GCC 9 + binutils 6.

## Accurate terminal accounting

The sealed 636-row projection has the following latest dispositions:

| Disposition | Rows |
| --- | ---: |
| `RULED-OUT-OF-GATE` | 353 |
| `SUPERSEDED-BY-V2` | 181 |
| `RESOLVED-EXACT` | 55 |
| `RECLASSIFIED-GAP` | 24 |
| `RECLASSIFIED-COVERED` | 13 |
| `RESOLVED-EXPLAINED` | 7 |
| `STILL-UNRESOLVED` | 3 |
| **Total** | **636** |

This is 636/636 disposition coverage, not 636/636 substantive closure. The
frozen snapshot has ten de-duplicated GAP/mismatch classes and cannot pass its
byte gate. The aggregate validator's `status=PASS` means only that the sealed
package's declared consistency checks passed; it is not a Phase 3f verdict.

## What a valid rerun requires

A later valid Phase 3f adjudication requires a new run, not a relabel or
reseal of this history:

1. select and freeze one quiescent patch/configure series before T0;
2. preserve the first obligation registration and every later change as
   append-only events;
3. record reviewer capability/effort and non-participation metadata;
4. finish the three slim-LTO producer causes and functional/metadata verdicts;
5. strengthen T5 to feature-specific code and binary-data attribution, or
   retain the remaining rows as unresolved;
6. keep the hardware HPE/vector campaign explicitly outside the compiler byte
   gate while carrying it as residual risk.

Until such a run exists, no Phase 3f PASS, darwin-arm64 byte-gate completion,
current-series coverage, or toolchain completion may be claimed.
