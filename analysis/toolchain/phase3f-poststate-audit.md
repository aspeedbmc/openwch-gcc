# Phase 3f provenance and post-state audit

The strict Phase 3f post-state verdict is **`INVALID`**.

The frozen OURS-V2 snapshot is not contaminated. Its manifest SHA-256 is
`1e242655eea550193e650fa2ffc2da127638b5c32c319e3035bfebe5d9f24dba`; all
3177/3177 entries
re-hash exactly and no entry is writable. The preserved controls also re-hash
exactly: WCH 3234/3234,
UPSTREAM-P2 3177/3177,
and UPSTREAM-MATCHED 716/716.

UPSTREAM-MATCHED additionally has a closed-world proof over
756 entries: 716
file/symlink leaves and 40 directories. Its
re-enumerated tree has no unregistered leaf, missing leaf, missing ancestor,
or special entry; verdict `PASS`.

The immutable matrix was built from **GCC3+binutils6**. The final stable
capture reads the protected series bytes as **GCC9+binutils6**, which is
**`UNTESTED`** against that frozen matrix. Current GCC series SHA-256:
`cc444a70a5bd2fdd1e2329462ed4e32f461c97d6eb0de004043c8b0c09a75ce8`. Current binutils series SHA-256:
`ee2719d2991a1d7494a4531be087f5372383b135e00e4dc647da0c53b56ad5c5`.
Post-freeze GCC appends captured in that series are:

- GCC 0004 `0004-c-family-match-WCH-.highcode-section-semantics.patch`: `82ef0240439a35fb73dea4e13224645288566623bd078318500c0da6d6cb9970`.
- GCC 0005 `0005-c-match-WCH-implicit-function-diagnostics.patch`: `38506eeb4735054dc8d75e539304ca2ec67ea4d6313d188a77825da13d07b737`.
- GCC 0006 `0006-RISC-V-use-mret-for-WCH-fast-simple-returns.patch`: `70f670d8877a8742c740dbde6cbeef05d169471e06de7775a77642c9396f3bb6`.
- GCC 0007 `0007-RISC-V-match-WCH-fast-interrupt-vector-saves.patch`: `16050bee59bf8291ac41955d3d865fc5301fd85e59b6fff29ad77f405d4572b9`.
- GCC 0008 `0008-RISC-V-keep-WCH-fast-interrupt-rename-targets-live.patch`: `b263ef6264b561959ef7a2218c580e738ba36b91e375615303d27aea8bd3b8a6`.
- GCC 0009 `0009-RISC-V-match-WCH-LTO-option-streaming.patch`: `fc5a171cd4af42ac2052421a9311a9987cc43ceeb2694a44fff2d8fb6e33a653`.

The capture performed three complete reads of the full protected-file
universe (both series and every patch byte), complete active GCC/binutils Git
snapshots (including diffs and untracked-content hashes), both aliases,
frozen-tree write permissions, and the complete active-output
tree. All reads agreed; configured writer matches before/after were
0/0. Capture
time: `2026-08-15T02:32:11.764626+00:00`. The preceding immutable generation is
`tmp/phase3f-evidence/poststate-generations/generation-20260815T021618.720504Z`.

Active GCC is HEAD `dfe977da306659c746385781cffc0367dfed7ae9`, index tree
`0785aaf06ea20bd0f44b5084007d05497bc35e80`, with 0
tracked and 0 untracked changes. Active
binutils is HEAD `169c561ddd844aeab247940f49ada09c8e6d6f50`, index tree
`918ab266a63da3dba7cceb51efb02a7a6731b74a`, with
0 tracked and
0 untracked changes.

Against the Phase 3f pre-state, active output has
3163 exact and 14
different rows across a 3177-row union. Field differences are:
mode=0, sha256=14,
size=14, type=0,
link_target=0, added=0,
missing=0. The post manifest SHA-256 is
`ff4022bde81e0d91684df0f31f9e45155f777f7d3aaeb0cdb0691930918bccb9`. `/Users/mrs/riscv-gnu-toolchain` is
`EXACT` versus pre-state;
`tmp/golden/toolchain-current` is `DIFF`.

Phase 3f sections 2 and 10 make the broken run-wide single-writer boundary a
formal **`INVALID`**, not a substantive `FAIL`. The immutable GCC3+binutils6
measurements remain internally reproducible and substantively
**`COUNTERFACTUAL-FAIL`**. The current-series coverage status is separately
reported as
**`UNTESTED`**.

Machine sources of truth are under `tmp/phase3f-evidence/poststate/current/`, notably
`capture.json`, `summary.json`, `protected-current.tsv`,
`active-source-comparison.tsv`, `active-output-comparison.tsv`, `audit.tsv`,
`timeline.tsv`, and `validation.json`. Historical normalized tables are not
consumed by this raw-byte audit.
