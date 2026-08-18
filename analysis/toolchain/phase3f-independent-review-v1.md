# Phase 3f independent review v1

## Signed conclusions

**Review-package internal consistency: `FAIL`.** The frozen evidence and machine ledgers are independently reproducible, but the main closure report contains one material provenance-documentation contradiction: it says the final runner/validator manifest is 111/111 exact with SHA-256 `8cd6db20e5087dc738c28036c7fd3e2e6475b23c2db6dc4b0fc8c165a3089c9e`. The frozen manifest actually contains 112 data rows, all 112 re-hash exactly, and its SHA-256 is `14d28b8277cd45f6741a1ab52ca4ab005b23415d4eaddbb9120a00dd9abc8263`. Its sidecar and frozen validation JSON agree with the latter values.

This documentation defect does not change the substantive three-layer result:

- Formal Phase 3f verdict: **`INVALID`**.
- Immutable GCC 3 + binutils 6 snapshot: **`COUNTERFACTUAL-FAIL`**.
- Current GCC 4 + binutils 6 series: **`UNTESTED`**.

No toolchain milestone or byte-equality gate is complete.

Reviewer: `/root/independent_reviewer` (independent of the primary analysis)  
Review date: 2026-08-13  
Frozen logical-input manifest: `730ce4978d9e2ecfd8f53c9ed6578924af540c3a8fa64f599b1d073e37db5d91`

## Frozen input verification

I read the complete Phase 3f task book before review. I then checked only the 51 logical inputs named by `tmp/phase3f-evidence/reviewer/reviewer-inputs.tsv`. The manifest itself has the required SHA-256 above. All 51 paths were present, and mode, size, and SHA-256 were exact for 51/51 entries with zero differences. I did not inspect a bulk WCH executable, dump, or strings output.

The independent machine recomputations are in `tmp/phase3f-evidence/reviewer/recomputations.tsv`; the complete finding set is in `tmp/phase3f-evidence/reviewer/findings.tsv`.

## Independent accounting

The immutable registration has 636 unique obligations and all begin as `PENDING`. The event ledger has 637 rows for 636 unique obligations. Only `P3F-CLOSURE-0108` has two events; taking the greatest numeric `event_sequence` per obligation produces:

| Disposition | Count |
| --- | ---: |
| `RULED-OUT-OF-GATE` | 353 |
| `SUPERSEDED-BY-V2` | 181 |
| `RESOLVED-EXACT` | 55 |
| `RECLASSIFIED-GAP` | 27 |
| `RECLASSIFIED-COVERED` | 13 |
| `RESOLVED-EXPLAINED` | 7 |
| `STILL-UNRESOLVED` | 0 |
| **Total** | **636** |

The published 636-row table has the same identifier set as the immutable registration and the latest-event projection. I found zero differences in its immutable registration fields or latest disposition/pointer/evidence fields.

The fixed feature denominator is 35 unique terminal rows: 18 `COVERED-BYTE-EXACT`, 11 `COVERED-BEHAVIOR-EXACT`, one `UPSTREAM-IDENTICAL`, and five `GAP`. The five fixed-denominator GAPs are zstd, default fastirq vector-save policy, slim-LTO, `norvc-explicit` diagnostic precedence, and elfedit mmap. The two append-only parameter candidates, `highcode-gen-section-name` and `ccv-abi`, are both terminal `GAP` and remain outside the fixed 35. Therefore the frozen snapshot has seven de-duplicated terminal mismatch classes.

Lane-local counts are reproducible but must not be added: driver is 29/14 raw/1 physical-control/13 substantive; backend has 72 OURS-V2 artifact rows with six differences; GAS targeted is 43 cases with one diagnostic-only difference; L4 is 57/12 raw/6 physical-controls/6 substantive. Zstd overlaps driver and L4, slim-LTO overlaps driver and backend, and two elfedit rows are one capability class.

The errata denominator is 44 unique findings: 28 constructible and 16 individually not applicable. The constructible denominator is 84 optimization cells, 81 exact and three different. All three differences are O0/O2/Os for `L2-ERR-038`, one default fastirq vector-save backend GAP. The hardware HPE/vector-nesting safety question remains explicitly `RULED-OUT-OF-GATE` as a residual risk; that rule-out neither waives the compiler byte mismatch nor proves runtime ABI safety.

## T5 and gate anchors

The V2 host denominator independently resolves to 47 four-side byte-different Mach-O paths, 188 file-sides, and 8,166 mechanically tiled intervals. The functional subset is 188 code plus 1,152 data-table rows, all 1,340 mapped to terminal canonical features with no join error. The remaining 6,826 rows are pure-host and `RULED-OUT-OF-GATE`. The negative-space table has 74 terminally mapped candidates, including an explicitly retained fastirq/vector GAP.

The historical projection is exactly 172 semantic obligations to `SUPERSEDED-BY-V2`; the final obligation table contains exactly 349 historical host-region rows adjudicated `RULED-OUT-OF-GATE`. I checked the T5 decision record: it anchors the decision in the repository rule excluding whole host-tool Mach-O byte identity, records full stripped-Mach-O function attribution as the rejected alternative, states its cost, and retains the obligation to reopen feature-directed analysis for any new target-facing candidate. Thus the rule-out does not consume target artifacts, observable literals, or the seven forwarded GAPs.

## Provenance, freeze, and verdict separation

The frozen snapshot provenance is GCC base `5115c7e447fc07457443df874bf57840e8316d5f`, binutils base `2bc7af1ff7732451b6a7b09462a815c3284f9613`, GCC staged tree `3686efe41d20184032d5ba9b2860ed3e0e8de733` after three patches, binutils staged tree `918ab266a63da3dba7cceb51efb02a7a6731b74a` after six patches, and `SOURCE_DATE_EPOCH=1767225600`. The frozen manifest is `1e242655eea550193e650fa2ffc2da127638b5c32c319e3035bfebe5d9f24dba`. Rehash evidence is OURS-V2 3177/3177, WCH 3234/3234, UPSTREAM-P2 3177/3177, and UPSTREAM-MATCHED 716/716 exact; OURS-V2 has zero writable entries.

That intact snapshot does not make the phase valid. After freeze, the protected series changed from GCC3 to GCC4, active GCC changed and became dirty, active output changed in 581/3177 rows, and the golden alias was not restored; the `/Users/mrs` link was restored. Phase 3f sections 2 and 10 make the broken run-wide single-writer boundary an `INVALID` condition. The historical Phase 3c `INVALID` obligation is superseded only for frozen-snapshot analysis; Phase 3f has its own new `INVALID` finding. The seven proven frozen-snapshot GAPs make its substantive result `COUNTERFACTUAL-FAIL`, while no result in this matrix may be credited to the current GCC4+binutils6 series, which remains `UNTESTED`.

## Finding requiring correction in a future package

`P3F-IR-V1-001` is the sole independent review finding. In the frozen main report at lines 40--42, replace neither data nor files as part of this review; simply note that its stated 111/111 and `8cd6…` runner-manifest provenance does not match the frozen 112/112 and `14d28…` evidence. Because a signed closure report must agree with its frozen provenance, the package-level consistency verdict is `FAIL` even though all substantive verdicts and counts above remain supported.
