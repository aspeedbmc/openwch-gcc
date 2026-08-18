# Phase 3f closure report

## Verdict and scope

The formal Phase 3f verdict is **`INVALID`**. The
adjudicated platform scope is **darwin-arm64 only**; linux-amd64 is not a
Phase 3f denominator. The immutable controls remain exact, but the run-wide
single-writer boundary was broken after the V2 freeze. Therefore three states
must remain separate:

1. Formal Phase 3f: `INVALID`.
2. Frozen GCC 3 + binutils 6: `COUNTERFACTUAL-FAIL`, with
   10 de-duplicated mismatch classes.
3. Captured current series: **GCC 9 + binutils 6** (`GCC-9+BINUTILS-6`), status
   **`UNTESTED`** against the frozen matrix.

No toolchain milestone or byte-equality gate is complete.

## Frozen provenance

The frozen trees were built from GCC base `5115c7e447fc07457443df874bf57840e8316d5f`
and binutils base `2bc7af1ff7732451b6a7b09462a815c3284f9613`. Their staged trees
are `3686efe41d20184032d5ba9b2860ed3e0e8de733` and
`918ab266a63da3dba7cceb51efb02a7a6731b74a`. The OURS-V2 manifest is
`1e242655eea550193e650fa2ffc2da127638b5c32c319e3035bfebe5d9f24dba` and re-hashes 3177/3177
exactly with 0 writable entries. Preserved controls
re-hash exactly: WCH 3234/3234,
UPSTREAM-P2 3177/3177,
and UPSTREAM-MATCHED 716/716.

The strengthened UPSTREAM-MATCHED inventory covers
756 entries (716 leaves
and 40 directories), verdict `PASS`.
The validated primary runner/validator manifest contains
392 registered entries, all exact; its SHA-256 is
`bb8b47280b4d1a3b16e344a2020c80daafd5d6adf3a15e02ce223feb02550034`.

## Closure of the historical obligations

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

There are 2,117 append-only events for the 636 registered
obligations. The published table SHA-256 is `9d4a5caad573f57edda52e55a6364602aeeb1dc1537e3c950d5d087c5a83617e`. Three
slim-LTO obligations remain `STILL-UNRESOLVED` at cause-attribution level;
they do not create additional mismatch classes.

### T5 host-Mach-O closure

T5 covers 47 four-side
byte-different Mach-O paths, 188 file-sides,
and 8,166 intervals. Its
1,340 functional rows split into
748 terminal feature rows,
388 pure-host ABI rows, and
204 pure-host data rows. The
negative-space audit scans 58 WCH Mach-O
paths, maps all 1,090 candidates, and reproduces
1,566,507 rejected observations in
13,050 buckets with a
151-row deterministic sample. This paragraph
is bound to wrapped `FINAL-VALIDATE-T5` stdout SHA-256
`0799492c638a9dd825c8d7dd07e60cfcf6b7a75f1d8bc999543f971b4b5993a1`; it does not consume the older ad-hoc T5 log.
The functional split is a measured supersession of Phase 3c's over-broad
`FUNCTIONAL-*` label. The later published-closure pointer check is confirmatory and is
not used as its own premise.

## Feature, errata, and matrix results

| Feature status | Rows |
| --- | ---: |
| `COVERED-BYTE-EXACT` | 18 |
| `COVERED-BEHAVIOR-EXACT` | 11 |
| `UPSTREAM-IDENTICAL` | 1 |
| `GAP` | 5 |
| **Total** | **35** |

The frozen 35-feature denominator contains
5 feature GAPs. The append-only
candidate table contains 5
new candidate GAPs. After cross-lane de-duplication, those are the
10 terminal mismatch classes below;
raw lane rows are never added together.

### T4 backend and errata closure

T4's backend denominator contains 72 OURS-V2 rows.
Return code, stdout, and stderr are exact in all rows; artifacts are
65 exact, 1 both
absent, and 6 different. The different artifacts are
retained in the slim-LTO class rather than hidden by exact final consumers.

The errata audit covers 44 findings:
28 constructible findings over
84 WCH-versus-V2 cells and
16 individually not applicable. It has
81/84
exact cells; the only mismatch finding is
`L2-ERR-038`.

Lane-local counts are diagnostics and are not additive:

| Lane | Denominator | Initial raw differences | Physical controls | Substantive rows |
| --- | ---: | ---: | ---: | ---: |
| DRIVER | 29 | 14 | 1 | 13 |
| BACKEND | 72 | 6 | 0 | 6 |
| GAS-TARGETED | 43 | 1 | 0 | 1 |
| L4-MANDATORY | 57 | 12 | 6 | 6 |
| RC02-DIRECT | 1 | 1 | 0 | 1 |
| KNOWN-CLUSTER-DIRECT | 2 | 2 | 0 | 2 |

## Attributed terminal mismatch classes

1. **P3F-MM-ZSTD** (`CARRIED`). WCH has the GCC assembler zstd spec clause, BFD zstd capability, and loader-relative zstd runtime packaging; frozen OURS-V2 lacks them. Gate impact: Debug objects and the generation, consumption, decompression, recompression, and decoding surfaces differ. Repair surface: GCC/binutils configure capability plus loader-relative zstd dependency packaging; no target-ISA source patch.
2. **P3F-MM-FASTIRQ-VECTOR-DEFAULT** (`NEW-V2`). For a WCH-Interrupt-fast handler, WCH default does not software-save tested vector clobbers while frozen OURS-V2 saves/restores v0-v31 with dynamic-vlen whole-register slots. Gate impact: Prologue/epilogue assembly and object bytes differ; Phase 3b RC05 is the same default-vector policy. Hardware nested-vector runtime safety remains outside the byte gate and is a residual risk. Repair surface: GCC RISC-V WCH-Interrupt-fast default vector register-save/frame policy.
3. **P3F-MM-SLIM-LTO** (`CARRIED-PARTIALLY-ATTRIBUTED-IN-V2`). Six slim LTO objects have logical-stream differences: all six .decls main streams differ, four O2/O2+g3 .icf streams differ in the serialized sem_item::get_hash() field, and O2+g3 has a WCH debug statement frontier absent in V2. The exact node-field-versus-order, hash-input, and frontier creation-versus-serialization causes remain unresolved. Gate impact: The .o byte gate fails even though all six final ELF/BIN pairs and the bounded direct controls are exact; those exact consumers do not waive the object gate or close the three producer-cause questions. Repair surface: GCC declaration SCC/tree-record production and inputs; sem_item::get_hash() inputs; frontend/GIMPLE debug statement-frontier creation versus serialization. No narrower source patch is justified before those causes close.
4. **P3F-MM-NORVC-DIAGNOSTIC** (`CARRIED`). With an explicit XW instruction disabled by norvc, WCH and frozen OURS-V2 choose different diagnostic categories: illegal operands versus unrecognized opcode. Gate impact: Raw diagnostic behavior differs; no artifact is produced in this negative probe. Repair surface: binutils GAS tc-riscv.c:riscv_ip disabled-candidate diagnostic precedence.
5. **P3F-MM-ELFEDIT-MMAP** (`CARRIED`). WCH was configured with the mmap-gated elfedit x86 feature option surface; frozen OURS-V2 omits it. Gate impact: ELFEDIT-X86-FEATURE is rejected and ELFEDIT-HELP omits the option surface. Repair surface: binutils host configure HAVE_MMAP capability for elfedit.
6. **P3F-MM-HIGHCODE-PARAM** (`NEW-V2-EXPANDED-BY-PHASE3B-CLUSTERS`). WCH-only bounded GCC parameter; value 1 rewrites only exact case-sensitive .highcode declarations to .highcode.<source declaration name> for functions and variables The same WCH .highcode default no-inline/placement policy absorbs Phase 3b RC03, RC06, RC08, and RC09. Gate impact: OURS-V2 rejects accepted canonical parameter spellings; phase3b RC01 historically blocked 4 EVT projects and 188 member-project gate artifacts The merged Phase 3b clusters cover 45, 3, 1, and 1 projects respectively; their affected-gate counts overlap and are not additive. Repair surface: GCC parameter registration/diagnostics/help plus declaration section-name selection; preserve default/value 0 and exact-match/source-name semantics
7. **P3F-MM-CCV-ABI-PARAM** (`NEW-V2`). WCH-only bounded GCC parameter; value 1 makes WCH-Interrupt-fast save tested clobbered vector-ABI callee-saved v1-v7 and v24-v31 using vlenb-sized whole-register slots Gate impact: OURS-V2 rejects accepted 0/1 spellings and cannot select WCH value-1 prologue/epilogue bytes; existing default fast-IRQ mismatch remains separate Repair surface: GCC parameter registration/diagnostics/help plus RISC-V WCH-fast frame-save decision for the bounded tested register set; retain default/value 0 behavior
8. **P3F-MM-IMPLICIT-FUNCTION-DIAGNOSTICS** (`RECOVERED-OMITTED-PHASE3B-RC02`). For a C99 implicit function declaration without an explicit -Werror override, WCH emits its function0/function1 warning diagnostic and continues while frozen OURS-V2 emits an error and stops Gate impact: Frozen OURS-V2 fails accepted WCH compilation behavior; Phase 3b RC02 affected 5 EVT projects and 417 member-project gate artifacts Repair surface: GCC C frontend implicit-function-declaration default severity, WCH diagnostic literals, option promotion/demotion behavior, and system-header handling
9. **P3F-MM-FASTIRQ-EARLY-RETURN** (`RECOVERED-OMITTED-PHASE3B-RC04`). For a returning WCH-Interrupt-fast handler with multiple control-flow exits, WCH lowers every exit to mret while frozen OURS-V2 can lower a frame-free exit to ret even though its framed/common exit remains mret Gate impact: Frozen OURS-V2 emits target instruction bytes different from WCH; Phase 3b RC04 affected 59 EVT projects and 267 member-project gate artifacts Repair surface: GCC RISC-V WCH-fast epilogue/return lowering across all CFG exits, including frame-free early/tail exits
10. **P3F-MM-FASTIRQ-NORETURN-REGALLOC** (`RECOVERED-OMITTED-PHASE3B-RC07`). For a non-returning WCH-Interrupt-fast handler, WCH uses an ordinary ABI temporary for the final address while frozen OURS-V2 reserves and uses t0 Gate impact: Frozen OURS-V2 emits target instruction bytes different from WCH; Phase 3b RC07 affected 5 EVT projects and 15 member-project gate artifacts Repair surface: GCC RISC-V WCH-fast hard-register usage/liveness and allocation policy for non-returning handlers; keep distinct from vector-save and return-lowering policies

## LTO, tuning, and residual-risk boundary

Slim-LTO retains 3 cause-level unresolved questions.
Their machine-ledger IDs are `DECL-MAIN-NODE-FIELD-OR-ORDER`, `ICF-HASH-INPUT-CAUSE`, `DEBUG-STATEMENT-FRONTIER-ORIGIN`.
All 6 formal objects differ, while all
6 final ELF/BIN artifacts and
12 direct controls are exact. Exact consumers do not
waive the object-byte gate.

Tuning validation covers 1,056 selector compile
rows and 276 exact WCH/V2 comparisons. Static
closure covers 11/11
tune rows, 9/
9 tune-parameter objects,
4/
4 vector-cost components,
27/
27 NULL alignment-pointer fields, and
11/
11 pipeline selectors. The generated
reservation vocabulary is 67/
67
on WCH and 67/
67
on OURS-V2; this is not whole-binary DFA identity.

Hardware HPE/vector nesting and calling-ABI safety remains
`RULED-OUT-OF-GATE`: Phase 3f has no hardware-in-loop, while the project gate
is target artifact bytes plus observable literals. This limitation does not
waive any in-gate compiler mismatch.

## Dynamic post-state

The stable capture time is `2026-08-15T02:32:11.764626+00:00`. Current GCC series
SHA-256 is `cc444a70a5bd2fdd1e2329462ed4e32f461c97d6eb0de004043c8b0c09a75ce8`; current binutils series SHA-256 is
`ee2719d2991a1d7494a4531be087f5372383b135e00e4dc647da0c53b56ad5c5`. Post-freeze GCC appends are:

- GCC 0004 `0004-c-family-match-WCH-.highcode-section-semantics.patch`: `82ef0240439a35fb73dea4e13224645288566623bd078318500c0da6d6cb9970`.
- GCC 0005 `0005-c-match-WCH-implicit-function-diagnostics.patch`: `38506eeb4735054dc8d75e539304ca2ec67ea4d6313d188a77825da13d07b737`.
- GCC 0006 `0006-RISC-V-use-mret-for-WCH-fast-simple-returns.patch`: `70f670d8877a8742c740dbde6cbeef05d169471e06de7775a77642c9396f3bb6`.
- GCC 0007 `0007-RISC-V-match-WCH-fast-interrupt-vector-saves.patch`: `16050bee59bf8291ac41955d3d865fc5301fd85e59b6fff29ad77f405d4572b9`.
- GCC 0008 `0008-RISC-V-keep-WCH-fast-interrupt-rename-targets-live.patch`: `b263ef6264b561959ef7a2218c580e738ba36b91e375615303d27aea8bd3b8a6`.
- GCC 0009 `0009-RISC-V-match-WCH-LTO-option-streaming.patch`: `fc5a171cd4af42ac2052421a9311a9987cc43ceeb2694a44fff2d8fb6e33a653`.

Active GCC is HEAD `dfe977da306659c746385781cffc0367dfed7ae9`, index tree
`0785aaf06ea20bd0f44b5084007d05497bc35e80`, with 0 tracked
and 0 untracked changes. Active binutils is
HEAD `169c561ddd844aeab247940f49ada09c8e6d6f50`, index tree
`918ab266a63da3dba7cceb51efb02a7a6731b74a`, with
0 tracked and
0 untracked changes.

Active output has 3163 exact and 14
different rows across 3177 union rows
(14/3177 different); the post-manifest
SHA-256 is `ff4022bde81e0d91684df0f31f9e45155f777f7d3aaeb0cdb0691930918bccb9`. The users-mrs alias is
`EXACT` versus pre-state and
golden-current is `DIFF`.

Thus the frozen GCC 3 + binutils 6 measurements remain internally reproducible,
but they do not adjudicate captured GCC 9 + binutils 6. The current label, counts,
series hashes, Git state, output counts, primary manifest count/SHA, and
closure event count/SHA in this report are rendered from machine evidence
rather than fixed literals.

## Formal deliverables and validation order

The acyclic final order is: atomic post-state capture -> wrapped validators ->
wrapper coverage -> closure build/validation -> primary runner-manifest
validation -> this report builder -> aggregate validation -> pre-review live
seal -> reviewer-v3 freeze/validation -> independent review -> final live
seal. The reviewer-v1 and reviewer-v2 remain immutable historical packages.
The current report never reads aggregate or reviewer outputs, and aggregate
must consume wrapped evidence rather than rerun side-effecting validators.
