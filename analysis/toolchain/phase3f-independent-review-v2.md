# Phase 3f independent review v2

## Signed conclusions

**Frozen review-package internal consistency: `PASS`.** I found no new
package-level contradiction in the 54-input reviewer-v2 package. The sole v1
finding, `P3F-IR-V1-001`, is accurately corrected: the current primary
runner/validator manifest has 112 data rows, all 112 re-hash exactly, and its
SHA-256 is
`702cd591c1dee9bd62d4aa0f639c9df32de0de1cc99ddf4dd9663e62538d01d5`.
The manifest, sidecar, dedicated validation JSON, and corrected main report
agree. The old 111-row claim and old hashes remain only as preserved audit
history.

Package consistency does not change the substantive verdict layers:

1. Formal Phase 3f verdict: **`INVALID`**.
2. Immutable GCC 3 + binutils 6 snapshot: **`COUNTERFACTUAL-FAIL`**.
3. Current GCC 4 + binutils 6 series: **`UNTESTED`**.

No toolchain milestone or byte-equality gate is complete.

Reviewer: `/root/independent_reviewer_v2` (independent of the primary analysis
and v1 review)  
Review date: 2026-08-13  
Frozen logical-input manifest SHA-256:
`a0c3a71c0906b0a345ab1cf9965b6e7d2eed2730b58618a9b86837302f635783`

## Frozen-input verification

I read the complete Phase 3f task book, then reviewed only the 54 paths listed
by `tmp/phase3f-evidence/reviewer-v2/reviewer-inputs.tsv`. The list contains 54
unique paths; mode, size, and SHA-256 are exact for 54/54 entries. I did not
inspect a bulk WCH executable, dump, or strings output.

The machine-readable independent results are in
`tmp/phase3f-evidence/reviewer-v2/recomputations.tsv`, the finding history in
`findings.tsv`, and the signed summary in `validation.json`.

## Independent accounting

The immutable registration has 636 unique obligations, all initially
`PENDING`. The append-only event ledger has 637 unique events for 636
obligations. Only `P3F-CLOSURE-0108` has two events; projecting the greatest
numeric `event_sequence` per obligation yields:

| Latest disposition | Rows |
| --- | ---: |
| `RULED-OUT-OF-GATE` | 353 |
| `SUPERSEDED-BY-V2` | 181 |
| `RESOLVED-EXACT` | 55 |
| `RECLASSIFIED-GAP` | 27 |
| `RECLASSIFIED-COVERED` | 13 |
| `RESOLVED-EXPLAINED` | 7 |
| `STILL-UNRESOLVED` | 0 |
| **Total** | **636** |

The published table has the same 636 identifiers as the registration and the
latest-event projection. Its seven immutable registration fields and its
latest disposition, pointer, and evidence fields have zero differences.

The fixed feature denominator is 35 unique terminal rows: 18
`COVERED-BYTE-EXACT`, 11 `COVERED-BEHAVIOR-EXACT`, one
`UPSTREAM-IDENTICAL`, and five `GAP`. The fixed-denominator GAPs are zstd,
default fastirq vector-save policy, slim-LTO objects, `norvc-explicit`
diagnostic precedence, and elfedit mmap. The append-only parameters
`highcode-gen-section-name` and `ccv-abi` are separately terminal `GAP`, so
the frozen snapshot has seven de-duplicated mismatch classes.

Lane-local raw counts are reproducible and non-additive: driver
29/14-raw/1-physical-control/13-substantive; backend 72 OURS-V2 artifact rows
with six differences; GAS targeted 43 cases with one diagnostic difference;
and L4 57/12-raw/6-physical-controls/6-substantive. Zstd overlaps driver and
L4, slim-LTO overlaps driver and backend, and two elfedit observations are one
terminal class.

The errata denominator is 44 unique findings: 28 constructible and 16
individually not applicable. The constructible denominator is 84 optimization
cells, with 81 exact and three different. The three differences are the
O0/O2/Os observations of one finding, `L2-ERR-038`, and one default fastirq
vector-save backend GAP. Hardware HPE/vector-nesting runtime safety remains
`RULED-OUT-OF-GATE` as an explicit residual risk; this does not waive the
compiler mismatch or prove ABI safety.

## T5 and gate-boundary review

The V2 host denominator independently resolves to 47 four-side byte-different
Mach-O paths, 188 file-sides, and 8,166 mechanically tiled intervals. All
1,340 functional rows (188 code plus 1,152 data-table) map to terminal
features; the remaining 6,826 pure-host rows are `RULED-OUT-OF-GATE`. All 74
negative-space candidates are terminally mapped, including the retained
fastirq/vector GAP.

The historical projection contains exactly 172 semantic obligations marked
`SUPERSEDED-BY-V2`, and the published obligation table contains exactly 349
historical host-region rows marked `RULED-OUT-OF-GATE`. The decision record
anchors this in the repository rule excluding whole host-tool Mach-O identity,
states full stripped-Mach-O attribution as the rejected alternative and its
cost, and requires feature-directed reopening for any new target-facing
candidate. It does not consume target artifacts, observable literals, or any
of the seven forwarded GAPs.

## Provenance, post-state, and verdict separation

The frozen snapshot provenance is GCC base
`5115c7e447fc07457443df874bf57840e8316d5f`, binutils base
`2bc7af1ff7732451b6a7b09462a815c3284f9613`, GCC staged tree
`3686efe41d20184032d5ba9b2860ed3e0e8de733` after three patches, binutils
staged tree `918ab266a63da3dba7cceb51efb02a7a6731b74a` after six patches, and
`SOURCE_DATE_EPOCH=1767225600`. The frozen OURS-V2 manifest is
`1e242655eea550193e650fa2ffc2da127638b5c32c319e3035bfebe5d9f24dba`.
Re-hash results are OURS-V2 3177/3177, WCH 3234/3234, UPSTREAM-P2 3177/3177,
and UPSTREAM-MATCHED 716/716 exact; OURS-V2 has zero writable entries.

The phase nevertheless remains formally `INVALID`: after freeze, the
protected series changed from GCC3 to GCC4, active GCC changed and became
dirty, active output changed in 581/3177 rows, and the golden alias was not
restored. The `/Users/mrs` link was restored. The immutable snapshot therefore
supports only its `COUNTERFACTUAL-FAIL` result with seven terminal GAP classes;
it cannot adjudicate the current GCC4+binutils6 series, which remains
`UNTESTED`.

## Review verdict

The reviewer-v2 frozen package is internally consistent and receives
**`PASS`**. `P3F-IR-V1-001` is **`CORRECTED`**, and no new independent finding
was identified. This package-level PASS must not be reported as Phase 3f PASS:
the formal phase verdict is `INVALID`, the tested frozen snapshot fails the
byte gate, and the current series is untested.
