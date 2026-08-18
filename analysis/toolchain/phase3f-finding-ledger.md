# Phase 3f finding/mismatch ledger

This ledger keeps three conclusions separate:

- The formal Phase 3f verdict is **`INVALID`** because the run-wide
  protected/active/symlink single-writer boundary was broken after the frozen
  snapshot was captured.
- The immutable GCC 3 + binutils 6 snapshot has a substantive
  **`COUNTERFACTUAL-FAIL`**.  Ten de-duplicated terminal mismatch classes are
  proven for that snapshot.
- The current series is captured dynamically from the two `series` files and
  remains **`UNTESTED`** by the frozen Phase 3f matrix.  The machine summary
  records its actual patch counts, series SHA-256 values, patch names, and patch
  SHA-256 values; no post-freeze GCC patch count is hard-coded.

The ten frozen classes comprise five `GAP` rows from the fixed 35-feature table
and five append-only candidates:

1. zstd capability/packaging;
2. default fast-interrupt vector save policy;
3. slim-LTO serialization/debug frontier;
4. explicit-XW-under-norvc diagnostic precedence;
5. elfedit mmap-gated option surface;
6. `.highcode` option, section, default no-inline, and emission-order policy;
7. opt-in `ccv-abi=1` selective vector saves;
8. implicit-function-declaration severity and diagnostic literals;
9. fast-interrupt early-return lowering (`mret` versus `ret`);
10. non-returning fast-interrupt hard-register allocation (`a*` versus `t0`).

The Phase 3b RC01-RC09 universe is accounted for without double counting.
RC01, RC03, RC06, RC08, and RC09 merge into the highcode class; RC02 is the
implicit-function class; RC04 and RC07 are independent fast-interrupt classes;
RC05 merges into the existing default-vector class.  The seven-row RC03-RC09
join and representative RC04/RC07 frozen probes are in
`tmp/phase3f-evidence/agents/binary-analysis/known-cluster-v2/`.

Slim-LTO remains one byte-gate mismatch class, but its attribution is only
partial.  Three cause-level obligations remain `STILL-UNRESOLVED`: declaration
node field versus SCC/tree-record order, the input responsible for the
serialized ICF hash difference, and debug-frontier creation versus
serialization.  They are registered in
`tmp/phase3f-evidence/agents/binary-analysis/lto-v2/analysis/unresolved-ledger.tsv`;
they do not inflate the ten-class mismatch denominator.

Lane raw counts remain observations, not independent terminal classes.  zstd
appears in driver and L4, slim-LTO appears in driver and backend, and
representative cluster probes corroborate classes outside the original fixed
matrix.  These counts must not be added.

| Lane | Denominator | Initial raw mismatch | Same-physical controls | Substantive rows |
|---|---:|---:|---:|---:|
| Driver | 29 | 14 | 1 | 13 |
| Backend artifacts | 72 | 6 | 0 | 6 |
| GAS targeted surface | 43 | 1 | 0 | 1 |
| L4 mandatory | 57 | 12 | 6 | 6 |
| RC02 representative direct probe | 1 | 1 | 0 | 1 |
| RC04/RC07 representative direct probes | 2 | 2 | 0 | 2 |

Rebuild and validate with:

```sh
python3 tmp/phase3f-evidence/scripts/build-finding-ledger.py
python3 tmp/phase3f-evidence/scripts/validate-finding-ledger.py
```

The primary TSV is `analysis/toolchain/phase3f-finding-ledger.tsv`.
`tmp/phase3f-evidence/finding-ledger/summary.json` is the machine summary,
`current-series.tsv` is the dynamic current-series capture, and
`lane-raw-counts.tsv` carries non-additive lane accounting.
