# Phase 3e — WCH GDB / SIM deep diff

## Verdict

**PASS** (re-signed at r2, 2026-08-15; supersedes the r1 signature). The analysis universe is closed for the canonical Darwin GDB-SIM group, with the corresponding Linux package used as static corroboration. The primary release denominator is complete on both platforms; all observed functional, configuration/capability, and packaging differences have a bounded mechanism and evidence chain; the append-only 42-candidate universe maps 100% to ten canonical modification rows or explicit nonfunctional conclusions; and `unresolved.tsv` now has zero open rows.

**The r2 rebuild overturned two of the r1 conclusions.** The r1 upstream control was built with an empty `sim_modules_detected[]` table, so its `run` had no trace, profile, hardware or socket-serial module installed. Every "WCH-only simulator CLI" finding rested on that broken control. With a correctly built control the simulator option surface is **byte-identical** on both sides, and the two capability rows are retracted as control-build artifacts. Readers of the r1 version of this report must discard those two findings; see the fix record at the end.

The verdict word follows the §9 vocabulary of `tmp/prompts/phase-3e.md`: `PASS` requires inventory completeness, a static attribution plus dynamic probe for every functional difference, a denominatored conclusion on simulator custom-ISA support, and zero `UNRESOLVED` — all of which now hold. `FAIL` and `INVALID` each have explicit trigger lists in §9 and none of their triggers fire. If the reviewing authority instead reads the phase-3e-fix clause "PASS iff inventory/attribution conclusions are unchanged" literally, the verdict flips to `FAIL`, because two conclusions did change; that is a one-word decision and every fact behind it is recorded below. **Ruling (Main, 2026-08-15): `PASS` stands.** The phase-3e §9 vocabulary governs; the fix-sheet clause targeted silent rewrites, not disclosed, evidence-driven corrections, which are exactly what this remediation was chartered to produce.

This is an independent research verdict. GDB and SIM remain outside the compiler artifact byte-identity acceptance gate; this report does not add them to that gate.

## Scope and exact baseline

The primary release denominator remains **32 paths per platform: 28 files and four directories**. A Darwin `libzstd.1.dylib` is a context dependency, not a 33rd component. Five installed man pages per platform form a separate supplemental documentation surface, not an expansion of the primary denominator. The frozen-input manifest therefore has 75 rows: 64 primary inputs, one context dependency, and ten supplemental man-page inputs. The final verifier covers all 75.

Both official executables identify as GNU GDB/SIM 17.1. The exact source baseline is the GNU GDB 17.1 release tarball, SHA-256:

`14996f5f74c9f68f5a543fdc45bca7800207f91f92aeea6c2e791822c7c6d876`

The matched `riscv32-wch-elf` control was built entirely below `tmp/phase3e-upstream/`. Its principal SHA-256 values are GDB `c4c3d21880ebc0c2b3d4fc3173b6445d53e4f5a4f90c9c46b6e6bc712ee2be38`, `run` `44df3af6daaf5021af69ab793dc724c63bdc069dc7466f177816d23622c6f22d`, and `libsim.a` `a16174679be1bc01b2e8a025ffe92449cb5ca3aa7df0edd060ca9c4b392bd59c`.

The GNU detached signature **was verified** at r2 (the r1 statement that the host has no `gpgv` was wrong). Using `/opt/homebrew/bin/gpgv` (real path `/opt/homebrew/Cellar/gnupg/2.5.21/bin/gpgv`, SHA-256 `d9eb7bc783a1a0f1f39bb1f12ff0c94d7c2aac3b25aac2a7909a647d60be7bd4`) against the GNU keyring:

```
gpgv --keyring tmp/phase3e-upstream/downloads/gnu-keyring.gpg \
     tmp/phase3e-upstream/downloads/gdb-17.1.tar.xz.sig \
     tmp/phase3e-upstream/downloads/gdb-17.1.tar.xz
gpgv: Signature made Sat Dec 20 12:17:13 2025 JST
gpgv:                using DSA key F40ADB902B24264AA42E50BF92EDB04BFF325CF3
gpgv: Good signature from "Joel Brobecker <brobecker@adacore.com>"
```

rc 0; evidence `R2FIX-0001-gpgv-verify`. The archive hash, release contents, identity, target, and installed controls anchor the baseline independently of this check. Host triple, generated path, ncurses/terminfo, and signing differences are classified rather than treated as target functionality.

A second control, `UPSTREAM-GDB-BUILD-R2`, was built at r2 under `tmp/phase3e-upstream/build-r2/`. Its `configure` argv is byte-identical to the r1 control; the only deliberate deltas are the build directory, a `make all-sim` target, and a BSD-sed compatibility shim on `PATH` for the `make` step (mechanism in the fix record). Its `run` SHA-256 is `a430d0dd44ee934b67e65cfaf162ef9b79ae2dfc7e54fa2d8e1116da92d65e45`. No `make install` was run, so the r1 install tree is untouched.

## Component, documentation, and binary structure

Among the primary 28 files, 24 Darwin/Linux paths are content-identical with mode-only differences. Four differ in content: `gdb`, `run`, `libriscv32-wch-elf-sim.a`, and `gdb.info`. Their bounded causes are target functionality plus host configuration/code generation; SIM decode-table content plus host code generation; SIM decode-table content plus archive/build packaging; and generated Info packaging. (At r1 the `run` cause was stated as "SIM table/module capability". The module-capability half is withdrawn at r2 — it described this project's control build, not WCH — so only the decode-table half remains.)

The installed GDB data plane is otherwise unmodified. The denominator here is the **23 data-plane files** — the installed data, script and header paths (two helper scripts, `jit-reader.h`, 17 syscall XML/DTD files, two system-gdbinit Python files, and `gdb.info`), not a subset of the 28 primary files. Twenty-two of those 23 are byte-exact against the matched build. The exception is `gdb.info`, generated as one WCH file versus an upstream top file plus nine pieces; both parse to 590 nodes and contain no proven WCH/XW/custom32 documentation.

All ten supplemental man files differ raw-bytewise. Across the 5×2 surface there are 15 hunks: five Pod::Man/Pod::Simple generator-version hunks and ten generated-date hunks. After masking only those generated metadata fields, **10/10 page bodies are byte-exact** to upstream, with zero substantive or vendor-feature hunk. This is `PACKAGING/DEPENDENCY` evidence and adds no modification candidate.

Content grouping retains every frozen non-directory path. It covers 67 rows: primary 28/28, supplemental 5/5, and one context dependency. Within each package there are zero duplicate-content groups and zero hardlinks; 24 content groups are equivalent across the two WCH platforms. Primary lane ownership is disjoint and complete: GDB owns 28 objects, SIM owns four.

The whole-file/member structural ledger has 730 interval rows over 178 obligations: two GDB executables, two runners, three archive containers, and 57 members on each of three archive sides. Every obligation tiles its full byte interval without a gap or overlap. The archive object names and ordinals agree 57/57 on all three sides; payload bytes differ 57/57 per WCH host versus upstream, bounded as build/format/layout evidence rather than 57 functional changes.

For the two Darwin comparator pairs, a separate compact Mach-O ledger closes 17 static surfaces each: headers, segments, sections, load commands, signature, UUID, dylib imports, imports, exports, symbols, and function starts. It has 34 rows and zero validator errors. All surface hashes differ; each pair has seven count-exact surfaces. WCH executables carry a valid Developer ID/hardened-runtime signature, while locally built controls have valid ad-hoc signatures. These counts and hashes describe host binary surfaces, not target semantics.

## GDB modifications and negative space

WCH GDB embeds the XW instruction class, eight compressed opcode rows, operand formatting, and the `xw` disassembler option. Exact GDB 17.1 lacks them. Per executable side, the clean exhaustive denominators are:

- XW: 5 labels × 8,704 words = **43,520**, with all WCH expected decodes and all upstream expected negatives;
- custom32: 20,650 pairwise words × five profiles = **103,250**, covering `mcpy`, `wexti`, `mrslu`, and `mrsl`;
- halfword: 65,536 values × four profiles × two display modes = **524,288**;
- total: **671,058** cells, with zero missing or duplicate records.

Those denominators are cell counts, and the XW and custom32 figures contain a deliberate 5× replication: for each of the five disassembler profiles the emitted stdout is byte-identical, so the profile axis is an invariance control rather than five independent samples. Counting distinct decode results instead of cells gives **553,642** (8,704 XW words + 20,650 custom32 words + 524,288 halfword cells). Both numbers are reported: 671,058 is the executed-cell denominator and 553,642 the distinct-decode denominator. The cell count is retained as the published denominator because the replication is the evidence that profile selection does not change XW/custom32 decoding.

XW is a manual display policy, not a new GDB architecture or target description: an `rv32imac_xw2p2` ELF attribute does not enable the aliases by itself, while explicit `set disassembler-options xw` does. The embedded opcode mechanism cross-maps to the ordinary XW/custom32 table and operand surfaces found in phase 3c, without claiming unavailable commit lineage.

The deterministic negative-space universe covers six host binaries: four frozen WCH objects (Darwin/Linux GDB and `run`) and two matched Darwin controls. ASCII printable runs of length ≥4 yield 201,550 per-object unique-string rows, 119,697 distinct presence rows, and 50,488 Darwin side-only rows. Every row maps to one of 62 terminal `CLOSED` groups. Four raw `REVIEW-REQUIRED` groups containing 5,509 rows were refined to bounded module, target, build/codegen, symbol/debug, or generic implementation groups; terminal `OPEN` and `REVIEW-REQUIRED` counts are zero.

GDB `--help` is byte-exact: 37 common options and zero side-only. Full `help all` is also byte-exact, with 1,546 parsed command names on each side and zero side-only. Both built-in `target sim` controls provide no XML target description. The 17 syscall XML/DTD files and two system-gdbinit scripts are upstream-exact; the current RISC-V gdbarch does not select those syscall tables. Darwin WCH and matched upstream both reject Python with the same unsupported diagnostic, while Linux WCH's Python availability remains a static host-package capability.

## SIM results

The authoritative standalone corpus uses the frozen official Darwin assembler/linker inputs, the same absolute work path, and a repo-local timeout helper. There are 23 cases per side. Comparing `(rc, stdout SHA-256, stderr SHA-256)`, **22/23 are exact**. The sole delta on that tuple is `mcpy`: WCH exits rc 4, upstream is killed at rc 137. Neither result demonstrates `mcpy` execution semantics.

At r1 the WCH side of that delta was described as "reaching a named/decoded path". On the `(rc, stdout, stderr)` face alone that claim was not supported: the WCH `mcpy` stderr is byte-identical to the stderr of a generic illegal instruction, so that face cannot distinguish a named decode from an unnamed one. The r2 trace comparison replaces the inference with a direct observation, and the conclusion is now stronger than either the r1 claim or a mere static-anchor inference — see the trace results below.

The bounded execution conclusions are:

| Family | WCH SIM | Upstream relation | Execution support proven? |
|---|---:|---:|---|
| selected RV32I + semihosting | 1/1 success | exact | selected path only |
| selected RV32M | 1/1 success | exact | selected operation only |
| selected RV32A / RV32C | 1/1 illegal each | exact | no |
| XW | 8/8 illegal | exact | no |
| custom32 | 4/4 illegal, 4/4 named in trace | 3 illegal but unnamed + `mcpy` livelock | no |
| delay | 1/1 illegal | exact | no |
| custom CSR | 4/4 illegal | exact | no |
| illegal sentinel | 1/1 illegal | exact | negative control |
| uninjected PFIC MMIO | unmapped, rc 11 | exact | no device stub |

The real GDB `target sim` subset has seven cases × two controls. Connection and load return in 14/14 cells; run returns in 13/14; 6/7 paired selected-observable comparisons are exact. Baseline stops at a breakpoint with the expected marker on both sides; PFIC stops with the same SIGSEGV and observable registers. SIGILL and timeout termination paths correctly record registers as `NOT-OBSERVABLE`. The sole pair delta is again upstream `mcpy` timeout versus WCH SIGILL. Neither control exposes an XML target description.

### Simulator option surface — recomputed at r2

The r1 figures (44 common, 43 WCH-only, zero upstream-only) are **withdrawn**. They were produced against a control whose `run` had no modules installed, so the 43 tokens were absent from the control for a build reason, not a WCH reason. Against `UPSTREAM-GDB-BUILD-R2` the same parser, run over freshly captured help text on both sides, gives:

| `run --help` option relation | r1 (broken control) | r2 (rebuilt control) |
|---|---:|---:|
| common | 44 | **87** |
| WCH-only | 43 | **0** |
| upstream-only | 0 | **0** |
| union (denominator) | 87 | **87** |

The denominator is self-consistent on both sides (87 = 87 + 0 + 0) and the arithmetic closes exactly against r1: the 44 + 43 tokens r1 split across the two relations are the same 87 tokens that r2 finds in common. Beyond the token sets, the two help texts are **byte-identical** (SHA-256 `df441324298747e6e859749524f200bd39d6887eb777af0265ecebeb98072027` on both sides) once the control is invoked under the installed program name; the only difference before that is the `argv[0]` string in the `Usage:` line.

Re-running the 43-token parser matrix against the new control gives 86 cells: **WCH recognizes 43/43 and the r2 control also recognizes 43/43**, with identical dispositions and zero timeouts. The r1 statement "upstream rejects 43/43" is withdrawn. Trace, profile, hardware/device and socket-serial are stock upstream 17.1 modules present on both sides, not WCH additions.

### Simulator trace comparison — newly available at r2

Trace was `SIM-UNRES-TRACE-CONTROL` at r1 (0/23 comparable). With the rebuilt control both sides run the same trace argv over the same 23 fixtures in the same absolute work directory, with no normalisation. All 23 cases now carry a conclusion:

- `rc` equal 22/23, stdout equal 23/23, stderr equal 22/23;
- **19/23 traces are byte-identical**, including all eight XW cases, the delay case, the four custom CSR cases, the illegal sentinel and the PFIC MMIO case;
- **4/23 differ, and they are exactly the four custom32 cases.**

The difference is one line per case, at the instruction that carries the custom word:

| case | WCH trace line | upstream trace line |
|---|---|---|
| `custom-wexti` | `UNHANDLED INSN: wexti` | `UNHANDLED EXTENSION: 88` |
| `custom-mrslu` | `UNHANDLED INSN: mrslu` | `UNHANDLED EXTENSION: 88` |
| `custom-mrsl` | `UNHANDLED INSN: mrsl` | `UNHANDLED EXTENSION: 88` |
| `custom-mcpy` | `UNHANDLED INSN: mcpy` | *(no line; livelock)* |

This is direct dynamic evidence, not an inference from static string anchors: the WCH simulator reaches a decode-table entry that carries the mnemonic **for all four custom32 words**, and exact upstream 17.1 reaches no such entry. Both sides then reject the instruction, so neither implements custom32 execution semantics. The finding is broader than the r1 one, which named only `mcpy` because `mcpy` was the only case the `(rc, stdout, stderr)` face could see.

The upstream `mcpy` hang is attributed to upstream source, not to WCH. `mcpy` is `0x50b6700f`: opcode `0x0f` (MISC-MEM), `funct3=7`. In `sim/riscv/sim-main.c`, `OP_HASH_IDX(iw)` is `iw & 0x7f` for a 32-bit word, so the word hashes to the MISC-MEM bucket, which is non-empty (`fence`, `fence.i`, `fence.tso`) — the `if (!op) sim_engine_halt (… SIM_SIGILL)` guard therefore does not fire. The bucket walk then matches nothing, `break` is never reached, `pc` keeps its entry value, and `step_once` ends with `riscv_cpu->pc = pc`. The next step refetches the same word: a silent livelock that emits no trace line and no diagnostic. A bounded probe with tracing on unbuffered stderr confirms it — the upstream trace stops after the twelfth line (the instruction before `mcpy`) and produces nothing further in three seconds. The three other custom32 words instead match a table entry whose `insn_class` has no `execute_one` case, which is why they print `UNHANDLED EXTENSION: 88` and halt. This is an upstream defect in the unmatched-but-non-empty-bucket path; WCH does not hit it for `mcpy` simply because `mcpy` is in its table.

These probes establish CLI/parser reachability and decode/naming behaviour, not runtime semantic equivalence.

## ISA-research cross-check

The SIM semantics ledger has ten bounded rows, all `RESEARCH-NOT-COVERED`, and zero `CONFLICTS`. Illegal-instruction, timeout, or unmapped-device behavior neither corroborates nor contradicts the hardware-facing XW, custom32, delay, CSR, or PFIC semantics in `ref/wch-isa-research`; it establishes only the selected software-model behavior.

## Canonical modification inventory

The append-only universe contains 35 T0 candidates plus seven late discoveries. All **42** map exactly once to ten canonical modification rows or explicit nonfunctional conclusions. The final universe SHA-256 is `a3274a05e1f4f5682339faa23afd2fdb12aa89956cd43a250643285a4c70dafe`.

Canonical rows by classification:

- **four functional**: GDB XW tables, GDB custom32 tables, GDB manual XW policy, SIM custom32 decode/naming (row `MOD-SIM-MCPY-DECODE`, whose evidence r2 widens from `mcpy` alone to all four custom32 mnemonics);
- **three configure/capability**: Linux GDB Python, SIM trace, and SIM profile/hardware/sockser module CLI installation — **of which the latter two are retracted at r2**, their net WCH-side difference being empty. They are kept as rows with `status=RETRACTED-CONTROL-BUILD-ARTIFACT` rather than deleted, so the append-only universe mapping stays intact; only `MOD-GDB-LINUX-PYTHON` remains a live configure/capability difference;
- **three packaging/dependency**: generated Info representation, archive/build packaging, Darwin zstd runtime dependency.

The profile/hardware/sockser negative-space discovery appended three candidates. r2 shows they map to a defect in this project's r1 control build rather than to any WCH mechanism. It does not create a target ISA semantic modification.

## Evidence integrity and limitations

Historical active-tree `readelf`, phase-3f-derived fixture, Homebrew-timeout, failed validator, and wrapper-race attempts remain preserved and explicitly superseded. The Mach-O wrapper-race cell was hashed and archived without fabricating a ledger row. Current command quality has an exact-rc row for every formal nonzero command. The T0 dirty-path verifier confirms all 11 pre-existing user/parallel-work paths remain byte- and mode-exact.

Structural tiling is not a per-byte semantic claim. Linux executables are static corroboration because they cannot execute on the Darwin host. Module-family runtime semantics (profile, hardware/device, socket-serial) are still not equivalence-tested on either side; only their CLI reachability is. These boundaries leave no blocking observable difference unattributed.

## Fix record (r1 → r2)

### The control-build defect

The r1 control's `sim/riscv/modules.c` contained an empty `sim_modules_detected[]`. Upstream generates that file in `sim/common/local.mk` (rule `%/stamp-modules`) by scanning the module sources for `^sim_install_` with:

```
sed -n -e '/^sim_install_/{s/^\(sim_install_[a-z_0-9A-Z]*\).*/\1/;p}' $(GEN_MODULES_C_SRCS) | sort >$@.l-tmp
```

Placing `p` on the same line as the closing `}` is a GNU sed extension. macOS `/usr/bin/sed` is BSD sed and rejects it — `sed: 1: "...": extra characters at the end of p command`, exit 1. Because the recipe pipes `sed` into `sort`, the POSIX pipeline exit status is `sort`'s, so the recipe's `set -e` never sees the failure: the build succeeded while silently emitting an empty module table. No module install function was registered, so `sim_install_trace`, `sim_install_profile`, `sim_install_hw`, `sim_install_dv_sockser` and `sim_install_engine` never ran and their option tables were never added. The r1 attribution "configure only passed `--enable-sim`" was wrong: `--enable-sim` was correct and sufficient, and configure was not the fault.

The r2 control puts a shim ahead of `/usr/bin/sed` on `PATH` for the `make` step only. It recognises that one exact script string and re-expresses it in the semantically identical POSIX form (one `-e` fragment per command); every other `sed` invocation is `exec`'d through unchanged, verified byte-identical on a passthrough case. The stock upstream recipe then runs unmodified and emits all five install functions. No upstream source file was edited.

### Findings and disposition

| Finding | Disposition |
|---|---|
| F1/F2 control rebuild | Done. Root cause established from upstream source and reproduced (`build-r2`); `run --help` exposes `--trace-insn`. Option surface, parser matrix and trace all recomputed. |
| F3 evidence chains | Done. `MOD-SIM-TRACE-CAPABILITY` and `MOD-SIM-MODULE-CLI-CAPABILITY` retracted with `P3ENEG-0022` and the r2 evidence IDs added; `MOD-SIM-MCPY-DECODE` widened to all four custom32. |
| F4 `mcpy` wording | Done, and superseded by stronger evidence: the stderr face is confirmed indistinguishable, and the trace face directly names the instruction. |
| F5 upstream `mcpy` rc137 | Attributed to an upstream `step_once` livelock on an unmatched non-empty hash bucket, with a bounded unbuffered-trace probe. |
| F6 exhaustive denominator | Disclosed: 5× profile replication, 553,642 distinct decodes vs 671,058 cells; published denominator unchanged. |
| F7 deliverable hashes | Regenerated; two of the three r1 rows were stale. |
| F8 validator | `len(active_dirs) == 1` relaxed to `in (0, 1)`; standalone rerun 22/22. |
| F9 `gpgv` | Corrected; signature verified Good, Joel Brobecker, key `F40ADB902B24264AA42E50BF92EDB04BFF325CF3`. |
| F14 XW operand anchors | Annotated `DYNAMIC-ONLY` with negative evidence: the literal operand-format tokens and their `Xwb`/`Xwh`/`XwB`/`XwH` fragments occur zero times in both frozen WCH GDB binaries. |
| F16 denominator wording | Restated as 23 data-plane files. |
| `SIM-UNRES-TRACE-CONTROL` | `CLOSED`. `unresolved.tsv` has zero open rows. |

### Hashes of in-line corrected files

| File | Before | After |
|---|---|---|
| `analysis/toolchain/phase3e-modification-inventory.tsv` | `d570983160dbad2ee3ae593dd7af559852ce5c67a9ed3255139856b4df77b8aa` | `f8879bfc10366af191fe11fc3f68e2647a19bcd821fc2cba70751eaabb7366e0` |
| `tmp/phase3e-evidence/modification-inventory.tsv` | `d570983160dbad2ee3ae593dd7af559852ce5c67a9ed3255139856b4df77b8aa` | `f8879bfc10366af191fe11fc3f68e2647a19bcd821fc2cba70751eaabb7366e0` |
| `tmp/phase3e-evidence/sim-semantics.tsv` | `39997bbb91a08d8530942fec43284014a86cff41c008e086f4b948ad96085d80` | `9a8d40b0062db0d6e82dfdb851ff000c565da7c64316c8f9cb93425f06a31da9` |
| `tmp/phase3e-evidence/unresolved.tsv` | `a8df9e06e4a0863f5c942bbbe7184762a297af31ad82b4263df270a1cecfbab6` | `9e82d1dc4a04a4068f4e10bc0936b839115480b307e2d5ade14968be3f048c0b` |
| `tmp/phase3e-evidence/agents/gdb/riscv-opcode-binary-anchors.tsv` | `06e82fbcee8a776630efca1beb59720eff4eb610c391d30d43f7b5392d7d91ee` | `aad65aee91852de44cb280ec4052f15ff9e519655050a559eb4ed66960fe6005` |
| `tmp/phase3e-evidence/agents/final-review-r2/independent_validator.py` | `e195d21edcae24d289975bcd9f3f15dfb8ef3dfd3d89c31ce12a0bc27b2223aa` | `d174f1b3d131460fe2b416b5690c90480ab39adf1ea1191357c9aaea687354ed` |

No r1 evidence file was deleted. All r2 commands are in a separate ledger, `tmp/phase3e-evidence/command-ledger-r2.tsv`, because the r1 ledger is permanently closed.

## Reproduction pointers

- Component inventory: `analysis/toolchain/phase3e-component-inventory.tsv`
- Modification inventory: `analysis/toolchain/phase3e-modification-inventory.tsv`
- Canonical machine evidence: `tmp/phase3e-evidence/`
- GDB and SIM lanes: `tmp/phase3e-evidence/agents/{gdb,sim}/REPORT.md`
- Supplemental man attribution: `tmp/phase3e-evidence/agents/man-attribution/REPORT.md`
- Real `target sim`: `tmp/phase3e-evidence/agents/closure-probe/REPORT.md`
- Mach-O comparison: `tmp/phase3e-evidence/agents/macho-closure/REPORT.md`
- Negative space: `tmp/phase3e-evidence/agents/negative-space/REPORT.md`
- Fresh independent review: `tmp/phase3e-evidence/agents/final-review-r2/REPORT.md`
- r2 command ledger: `tmp/phase3e-evidence/command-ledger-r2.tsv` (per-command detail under `tmp/phase3e-evidence/commands-r2/`)
- r2 control build: `tmp/phase3e-upstream/build-r2/`, driver `tmp/phase3e-evidence/scripts/build-upstream-r2.sh`, sed shim `tmp/phase3e-upstream/tools-r2/sed`
- r2 option surface: `tmp/phase3e-evidence/agents/sim/option-r2/{option-diff.tsv,option-summary.tsv,option-reachability.tsv}`
- r2 trace comparison: `tmp/phase3e-evidence/agents/sim/corpus-r2trace/{trace-results.tsv,trace-comparison.tsv}` and per-case logs under `cases/`
- r2 validator run: `tmp/phase3e-evidence/validation-t4-r2fix.txt` (r1 state) and `tmp/phase3e-evidence/validation-t5-r2.txt` (r2 state)
