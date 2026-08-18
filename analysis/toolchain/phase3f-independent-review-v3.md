# Phase 3f independent final review v3

## Signed conclusions

The final 6,634-input reviewer package is internally consistent and receives
**`PASS-WITH-DISCLOSED-LIMITATIONS`**. This is a review-package conclusion,
not a Phase 3f or toolchain completion claim.

The substantive verdict layers remain:

1. Formal Phase 3f: **`INVALID`**.
2. Frozen GCC 3 + binutils 6 snapshot: **`COUNTERFACTUAL-FAIL`**.
3. Captured current GCC 9 + binutils 6 series: **`UNTESTED`** by the Phase 3f
   matrix.

The frozen snapshot has 10 terminal mismatch classes and three slim-LTO
cause-level `STILL-UNRESOLVED` questions. This review does not establish a
Phase 3f `PASS` or overall multi-version, dual-platform toolchain completion;
the separate Linux T6 result below remains scoped evidence.

Reviewer: `/root/independent_reviewer_v3_fresh`  
Review date: 2026-08-15  
Final logical-input manifest SHA-256:
`f69a3ff1f98e484cd6f099fa09d8f3c7293c3430ed15636842012459e75d1990`

## Frozen-input verification and pre-signing correction

`validate-reviewer-freeze.py --version v3 --check-only` independently passed
6,634/6,634 regular files with zero mode, size, or SHA-256 differences. The
manifest has 6,634 unique paths and excludes all reviewer-v3 outputs, so it is
not self-referential.

During review, the earlier 1,313-row intermediate freeze was rejected before
signing because it contained only an old Phase 3d RC01 summary and a diagnostic
root snapshot for the requested Linux T6 four-pass claim. It did not contain
the final T6 originals. The final freeze adds the complete 5,225-file sealed
T6 evidence tree, invocation and publication records, support roots, and a
semantic validator. Finding `P3F-IR-V3-001` is therefore
`CORRECTED-BEFORE-FINAL-SIGNING`; no conclusion below relies on the rejected
intermediate freeze.

The machine recomputations are in
`tmp/phase3f-evidence/reviewer-v3/recomputations.tsv`, findings and proof
limits are in `findings.tsv`, and the signed machine summary is
`validation.json`.

## Closure accounting

The immutable registration has 636 unique rows, all initially `PENDING`. Its
source-kind denominator is 21 unresolved-ledger rows, 11 unresolved features,
57 unavailable mandatory probes, 18 mandatory mismatches, one unresolved
erratum, six reviewer limitations, one invalid-verdict obligation, 172 host
semantic obligations, and 349 host-region obligations.

The append-only event ledger has 2,117 sequential, unique events. Projecting
the greatest numeric `event_sequence` for every registered identifier gives:

| Latest disposition | Rows |
| --- | ---: |
| `RULED-OUT-OF-GATE` | 353 |
| `SUPERSEDED-BY-V2` | 181 |
| `RESOLVED-EXACT` | 55 |
| `RECLASSIFIED-GAP` | 24 |
| `RECLASSIFIED-COVERED` | 13 |
| `RESOLVED-EXPLAINED` | 7 |
| `STILL-UNRESOLVED` | 3 |
| **Total** | **636** |

The registration, latest-event projection, and published table have identical
identifier sets. The six immutable registration fields and three published
terminal fields have zero differences. The three unresolved closure rows are
the historical LTO-object obligations `L1-UNRES-LTO-OBJECT`,
`L2-UNR-LTO-SLIM`, and `L4-UNRES-LTO-OBJECT`; they point to the three
producer-cause questions below.

## Features and terminal repair surfaces

The fixed feature denominator is 35 unique terminal rows:

| Feature status | Rows |
| --- | ---: |
| `COVERED-BYTE-EXACT` | 18 |
| `COVERED-BEHAVIOR-EXACT` | 11 |
| `UPSTREAM-IDENTICAL` | 1 |
| `GAP` | 5 |

Five append-only candidate GAPs combine with the five fixed-feature GAPs into
10 de-duplicated terminal classes. Raw observations across driver, backend,
GAS, L4, errata, and Phase 3b clusters are non-additive.

| Terminal class | Repair surface |
| --- | --- |
| `P3F-MM-ZSTD` | GCC/binutils configure capability plus loader-relative zstd dependency packaging; no ISA patch. |
| `P3F-MM-FASTIRQ-VECTOR-DEFAULT` | GCC RISC-V WCH-fast default vector-save and frame policy. |
| `P3F-MM-SLIM-LTO` | Declaration SCC/tree-record production and inputs, `sem_item::get_hash()` inputs, and debug-frontier creation versus serialization; no narrower patch is justified yet. |
| `P3F-MM-NORVC-DIAGNOSTIC` | GAS `riscv_ip` disabled-candidate diagnostic precedence. |
| `P3F-MM-ELFEDIT-MMAP` | Binutils host `HAVE_MMAP` configure capability for elfedit. |
| `P3F-MM-HIGHCODE-PARAM` | GCC parameter registration/diagnostics/help and exact `.highcode` declaration section-name selection. |
| `P3F-MM-CCV-ABI-PARAM` | GCC parameter registration plus WCH-fast selective vector callee-save policy. |
| `P3F-MM-IMPLICIT-FUNCTION-DIAGNOSTICS` | C frontend default severity, WCH diagnostic literals, promotion/demotion, and system-header handling. |
| `P3F-MM-FASTIRQ-EARLY-RETURN` | WCH-fast return lowering for every CFG exit, including frame-free early/tail exits. |
| `P3F-MM-FASTIRQ-NORETURN-REGALLOC` | WCH-fast hard-register liveness and allocation for non-returning handlers. |

Every ledger row has a nonempty mechanism, gate impact, evidence pointer, and
repair surface. All 10 rows describe the frozen GCC3+binutils6 snapshot; the
current GCC9+binutils6 column remains `UNTESTED` in this Phase 3f package.

## Linux T6 four-pass evidence

This was reviewed as separate Phase 3d/Linux evidence requested by the final
audit. It does not expand Phase 3f's darwin-arm64 scope and does not retroactively
test the Phase 3f 35-feature matrix on GCC9+binutils6.

The independent semantic traversal re-hashed the 5,224-entry closed-world
ledger against 5,224 sealed files plus its completion marker, then parsed all
5,192 checkpoint JSON files and both lane ledgers:

- four passes each contain 1,298/1,298 `PASS` checkpoints, 1,298 conversion,
  build, and bin stages, and zero build failures;
- each pass records 96,400 artifacts: 47,797 gate artifacts and 48,603
  auxiliary artifacts;
- the gate denominator per pass is 45,201 `.o`, 1,298 `.elf`, and 1,298
  `.bin` files;
- `official-double` has 47,797/47,797 gate matches and all 48,603 auxiliary
  matches;
- `official-ours` has 47,797/47,797 gate matches, zero gate diff/missing/extra,
  and 819 auxiliary differences. Those auxiliary rows are diagnostic and are
  not silently counted as gate equality;
- the command ledger has 15,576 successful, non-timeout commands: 5,192 each
  for conversion, build, and objcopy;
- the final audit has `mismatch_count=0`, 191,188 raw rehashes and 95,594 lane
  byte comparisons as finalizer attestations.

Fresh/restore evidence is internally consistent: `resume=false`, every pass
starts with a clean 1,298-checkpoint domain, host and container writer
preflight sets are empty, the 25,076-row EVT entry and restored manifests are
byte-identical, all nine patched-target guards are byte-identical, both aliases
match their entry targets, and runner/cleanup return codes are zero. Fourteen
historical input-exit checks are all true and their entry identities are bound
by the contract.

Important proof boundary: the validator result is
`proof_scope=SEALED-FINALIZER-ATTESTATION`, not a replay of the raw comparison.
`raw_work_tree_frozen=false`; the roughly 7.1 GiB work tree is absent from the
reviewer manifest, so this review did not repeat the finalizer's 191,188 raw
rehashes or 95,594 original byte comparisons. Historical non-EVT exit state is
recorded as booleans rather than a complete exit-hash snapshot. The host
cleanup source, zero cleanup rc, empty writer preflight, and current lock
absence are verified, but there is no persistent historical receipt sampled
after finalizer lock release. These three limitations are findings
`P3F-IR-V3-002` through `004`; they constrain the evidence wording rather than
turning attested gate differences into matches.

Principal T6 hashes independently recomputed are:

| Object | SHA-256 |
| --- | --- |
| completion marker | `0e2c7f8124667a4c262c0586eb081ba9db589ddd266f5c6be2e01b11f3c2ec31` |
| contract | `28cd80991b334bc4efbc7f2df013fb047827c25d382dea2d5ac58af11ff57b28` |
| run summary | `2c012ee15cbe364f3944234fef64dcd76052356ff9ec39c11a9141ed1bd9b9c7` |
| golden identity | `c81cff8f55765b01c58d25d06af366f598db15c9d944c898f36584b56f3c2b30` |
| golden audit | `47c6c2d07a54692664cc10149fa90236248cc2cab4d3ff442e76b3fd814f7808` |
| final audit summary | `5510b7419d602709720a543cd002b37f732e888e9b592c3827da076d4137bc14` |
| final mismatch ledger | `c8eaab28f9f777efe2fb355f0649bd6d8454e1e9f5de5c3f64c8970e0e881d6e` |
| published Linux full manifest | `d6394902d54ea7ec616995108715d58ab2fcc207455656bda42ee2f7ef7b8738` |

## T5 host-Mach-O adjudication

The path census contains 58 WCH Mach-O paths: 47 four-side byte-different
paths and 11 non-tilable/negative paths. The 47 paths produce 188 complete
file-side tilings and 8,166 nonoverlapping, contiguous interval rows.

The 1,340 functional rows exactly equal the raw ledger's 188
`FUNCTIONAL-CODE` plus 1,152 `FUNCTIONAL-DATA-TABLE` rows. Their terminal
split is 748 feature-mapped, 388 pure-host ABI, and 204 generic pure-host data.
All mapping fields join back to the raw region identifiers without a
difference. The remaining 6,826 intervals are pure host bytes with
`RULED-OUT-OF-GATE` dispositions.

All 1,090 negative candidates are unique and terminally mapped: 1,089
`MAPPED-TERMINAL` plus the retained fastirq/vector
`MAPPED-GAP-TERMINAL`; unmapped candidates are zero. The reject ledger has
13,050 buckets, 1,566,507 observations, and 151 deterministic samples. Its 12
declared audit inputs re-hash exactly.

The historical projection contains 172 `SUPERSEDED-BY-V2` semantic
obligations and 349 unique historical region rows. Twenty host-zstd rows map
to the retained zstd GAP; the other 329 are ruled out after interval closure.
Thus the whole-host attribution obligation can be ruled out without swallowing
the separately retained target-facing GAP.

The T5 decision record uses the repository rule excluding whole host-tool
Mach-O identity, states full stripped-Mach-O attribution as the rejected
alternative and its cost, and requires feature-directed reopening for a new
target-facing candidate.

## slim-LTO, tuning, and errata

All six formal slim-LTO objects re-hash to their matrix rows and differ at the
logical stream level. The `.decls` main stream differs 6/6 while declaration
state and strings are exact. Four O2/O2+g3 `.icf` streams differ only in the
serialized `sem_item::get_hash()` field. WCH has 24 bounded debug
`BEGIN_STMT` markers in the O2+g3 body views while V2 has zero.

The three cause-level unresolved identifiers are:

- `DECL-MAIN-NODE-FIELD-OR-ORDER`;
- `ICF-HASH-INPUT-CAUSE`;
- `DEBUG-STATEMENT-FRONTIER-ORIGIN`.

All six final ELF/BIN consumers and all 12 direct cc1/cc1plus/lto1 controls
are exact. Those controls narrow propagation but do not waive the `.o` gate or
resolve the three producer causes.

Tuning validation has 1,056 selector compile rows and 276/276 exact WCH/V2
comparisons. Static closure covers 11/11 tune rows, 9/9 tune-parameter
structures, 4/4 vector-cost components, 27/27 null alignment-pointer fields,
11/11 pipeline selectors, and 67/67 generated reservation strings on each
side. It finds no implicit QingKe/HPE generation tuning selector; it does not
claim whole-binary DFA identity.

The errata denominator is 44 findings: 28 constructible and 16 individually
not applicable. The 84 constructible cells are 81 exact and three different;
all three are O0/O2/Os observations of `L2-ERR-038`. The compiler behavior is
an in-gate `BLOCKING-BACKEND-BYTE-MISMATCH`: WCH omits vector saves while
frozen V2 saves/restores v0-v31. On-device HPE/vector nesting and calling-ABI
safety is separately `RULED-OUT-OF-GATE` because compile-only evidence cannot
observe it. That is an explicit residual risk and must not override the
compiler GAP or be read as proof of hardware safety.

## Provenance, seals, and aggregate semantics

The frozen snapshot remains exact: OURS-V2 3,177/3,177 with zero writable
entries, WCH 3,234/3,234, UPSTREAM-P2 3,177/3,177, and UPSTREAM-MATCHED
716/716. The frozen bases, staged trees, and manifest remain bound to GCC3 +
binutils6 and `SOURCE_DATE_EPOCH=1767225600`.

The final post-state independently identifies current series bytes as GCC9 +
binutils6, with series SHA-256 values
`cc444a70a5bd2fdd1e2329462ed4e32f461c97d6eb0de004043c8b0c09a75ce8`
and `ee2719d2991a1d7494a4531be087f5372383b135e00e4dc647da0c53b56ad5c5`.
The Phase 3f snapshot does not cover that series. The historical single-writer
violation remains proven, so a later clean endpoint cannot change `INVALID`.

The exact pre-review seal has 12/12 bindings, identical captured/live
fingerprints and output commitments, fresh exact control rehashes, exact tool
identities, and no writer conflict. All 12 wrapped validators have rc 0,
stable declared inputs, and stable or captured outputs. The primary
runner/validator manifest re-hashes 392/392 with SHA-256
`bb8b47280b4d1a3b16e344a2020c80daafd5d6adf3a15e02ce223feb02550034`.
The 19-stage final graph is acyclic.

`phase3f-final.json` has `status=PASS` only because its aggregate consistency
checks pass. The same JSON explicitly records formal `INVALID`, frozen
`COUNTERFACTUAL-FAIL`, current `UNTESTED`, three unresolved causes, and 10 GAP
classes. Aggregate `PASS` must never be reported as Phase 3f `PASS`.

## Reproduction commands

The final signing checks used these repository-local commands:

```sh
python3 -I -B tmp/phase3f-evidence/scripts/validate-reviewer-freeze.py --version v3 --check-only
python3 -I -B tmp/phase3f-evidence/scripts/validate-t6-four-pass-evidence.py
python3 -I -B tmp/phase3f-evidence/scripts/validate-final-sequence.py
```

Additional read-only one-shot Python projections independently traversed the
closure/event tables, all T6 checkpoints and lane rows, LTO ledgers, T5
interval joins, errata rows, seal bindings, and the 392-row primary manifest;
their results and evidence pointers are preserved in `recomputations.tsv`.

## Review verdict

The final reviewer-v3 package is coherent within its explicitly stated proof
scope. It has no open package contradiction: one freeze-coverage finding was
corrected before signing and three T6 evidence limitations are disclosed.
This reviewer status cannot upgrade formal Phase 3f, the frozen byte-gate
failure, or current-series coverage, and it cannot be used to declare the
toolchain project complete.
