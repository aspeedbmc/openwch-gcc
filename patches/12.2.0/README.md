# WCH GCC 12.2.0 patch series

This directory contains the ordered GCC 12.2.0 and binutils 2.38 changes
required to reproduce the WCH 12.2.0 darwin-arm64 EVT gate artifacts.  Apply
the nine GCC patches and seven binutils patches from each component's `series`
file, top to bottom, to the pristine GNU release tarballs recorded below.

The GCC series has three deliberately separate kinds of changes:

- `0001` freezes the observed WCH multilib configuration: the 42 recipe
  entries plus the configured default `rv32imac`/`ilp32` tuple, which together
  reproduce the official 43-line `-print-multi-lib` selection surface.
- `0002` is an upstream host-build compatibility backport for recent libc++.
- `0003` through `0009` implement or test target behavior observed in the WCH
  compiler.  The XW parser itself already accepts generic lowercase vendor
  extensions; its patch therefore adds the observed acceptance/version tests
  without inventing a GCC-side XW default.

The build script reproduces the official configure text and literal path
`/Users/mrs/Work/riscv-none-elf-gcc-xpack.git`, pins
`SOURCE_DATE_EPOCH=1767225600`, builds host GCC/binutils only, and injects the
official target libraries/sysroot byte-for-byte.

`scripts/export-patches-12.2.0.sh` regenerates both series from the frozen
component histories, verifies sequential apply and final tree hashes, and
rebuilds the stable patch-ID table.  Each mail patch carries the real commit
hash of the frozen history in its `From` line, and `patch-id.tsv` records that
hash in a `source_commit` column alongside the stable patch ID, so every
exported patch can be traced back to the commit it came from.  The exporter
refuses to write the table unless each `From` hash is a full 40-hex object that
is reachable from the corresponding component `HEAD`.

With the eight pinned source archives listed below already present in
`tmp/toolchain_12.2.0/downloads/`, the complete pristine source preparation,
ordered patch application, compiler-only build, official payload injection,
and EVT gate is one command from the repository root:

```sh
scripts/replay-toolchain-12.2.0.sh
```

The wrapper deliberately does not download network inputs during a replay.  A
missing archive is a fail-closed precondition error; every present archive is
verified before extraction.  The official target payload must likewise have
been extracted under `ref/gcc/darwin-arm64/12.2.0/` as described by the root
repository instructions.  The wrapper then creates
fresh Git patch-management trees, runs `git apply --check` before every
`git am`, temporarily points the required literal symlink at the replay tree,
uses `CLEAN_HOST_DEPS=1`, and restores the previous symlink on exit.

## Verified upstream inputs

| Component | Release tarball | SHA256 |
| --- | --- | --- |
| GCC | `gcc-12.2.0.tar.xz` | `e549cf9cf3594a00e27b6589d4322d70e0720cdd213f39beb4181e06926230ff` |
| binutils | `binutils-2.38.tar.xz` | `e316477a914f567eccc34d5d29785b8b0f5a10208d36bbacedcc39048ecfe024` |
| GMP | `gmp-6.2.1.tar.xz` | `fd4829912cddd12f84181c3451cc752be224643e87fac497b69edddadc49b4f2` |
| MPFR | `mpfr-4.1.0.tar.xz` | `0c98a3f1732ff6ca4ea690552079da9c597872d30e96ec28414ee23c95558a7f` |
| MPC | `mpc-1.2.1.tar.gz` | `17503d2c395dfcf106b622dc142683c1199431d095367c6aacba6eec30340459` |
| ISL | `isl-0.24.tar.xz` | `043105cc544f416b48736fff8caf077fb0663a717d06b1113f16e391ac99ebad` |
| zlib | `zlib-1.2.12.tar.gz` | `91844808532e5ce316b3c010929493c0244f3d37593afd6de04f71821d5136d9` |
| zstd | `zstd-1.5.2-release.tar.gz` | `7c42d56fac126929a6a85dbc73ff1db2411d04f104fae9bdea51305663a83fd0` |

## Behavioral patch map

| Component | Patch | Difference addressed |
| --- | --- | --- |
| GCC | `0003` | Cover concatenated, underscore, bare, and explicit XW march strings while leaving bare `_xw` for GAS to default to `xw1p0`. |
| GCC | `0004` | Avoid the RV32 Zbs single-bit constant ICE and emit the observed `bseti` move. |
| GCC | `0005` | Model WCH hardware-saved fast-interrupt GPRs and emit the observed `mret`; preserve the typo warning/`ret` behavior. |
| GCC | `0006` | Treat standard Zmmul as multiply-only code-generation capability without enabling division. |
| GCC | `0007` | Recognize RV32 bit 31 in Zbs `bseti`/`bclri` masks. |
| GCC | `0008` | Truncate RV32 constant-building intermediates to the target mode, selecting the observed `LUI + ADDI` form. |
| GCC | `0009` | Add the standard `highcode-gen-section-name` parameter, exact `.highcode` no-inline behavior, and per-declaration section splitting. |
| binutils | `0001` | Accept bare and explicit XW attributes with the observed `xw1p0` default. |
| binutils | `0002` | Add standard Zmmul instructions and the `M`-implies-Zmmul attribute relation. |
| binutils | `0003` | Add the four observed WCH 32-bit custom opcodes and diagnostics. |
| binutils | `0004` | Add eight WCH XW compressed load/store forms, aliases, gates, and diagnostics, and decode them under the hidden `objdump -M xw`. |
| binutils | `0005` | Synthesize the finish-time privilege attributes only under the hidden `--w_priv_spec`, which defaults off. |
| binutils | `0006` | Accept only the observed vendor-X names (`xw` and bare `x`) and reject other unknown X extensions with WCH diagnostics. |
| binutils | `0007` | Accept hidden `-wchsoftlib`/`--wchsoftlib` and OR the observed `0x01000000` ELF flag without changing relaxation. |

The target-independent placement of GCC `0009` is also taken directly from
the official compiler's option classification: its `--help=params` output
lists `--param=highcode-gen-section-name=<0,1>` with the observed `.highcode`
description, while `--help=target` has no highcode entry.  That evidence makes
the parameter `Common` and places the behavior in generic C-family section
attribute processing rather than a RISC-V target option or backend hook.  The
saved official output and the complete probe conclusion are referenced in the
patch commit message and `analysis/toolchain/phase4-review.md` P2-2.

`patch-id.tsv` records stable patch IDs for integrity checks.  Phase 4.1
regenerated both component series and this table after adding the official
placement evidence to GCC `0009`; their bytes, including the `0009` stable
patch ID, remain unchanged because `git patch-id --stable` intentionally
excludes commit-message metadata, while the exported `0009` mail-patch bytes
changed.  The message-only refresh moved active GCC HEAD from
`9e5c14891ec80c7f4576a2da832b4eb443a87b43` to
`419ca42a7bae83ba43b84e63bf6100e7d6f52a8f`; its source tree remains
`37559608d0be1a87979d1beedff5c4f6cb286b4c`.  That Phase-4.1 export record, which
predates the `From`-line change described below, is in
`tmp/phase4-evidence/final-patch-export/`.

Phase 8 reworked both series in two passes.  They are described here in the
order they were performed; only the second one produced the final state.

The first pass was a message-only refresh of the GCC series: every GCC commit
gained a `contrib/gcc-changelog` section, `0004` gained the two saved ICE
observations behind its rationale, and `0005` states which register classes the
WCH hardware frame covers.  It moved GCC HEAD from
`419ca42a7bae83ba43b84e63bf6100e7d6f52a8f` to
`0dcdfa56eae7a7de7de203866703472e1152c837` with an unchanged source tree
`37559608d0be1a87979d1beedff5c4f6cb286b4c`, unchanged `series` files and an
unchanged `patch-id.tsv`; the binutils series was not touched.  Its pre-refresh
history is kept as `refs/openwch/phase8-12.2.0-pre-u2-20260817T021645Z`.

The second pass carried the comment, dead-code and structural cleanups, and
made two hidden option surfaces of the official build reachable in this series
after measuring both on the official 12.2.0 binaries.  GAS gained
`--w_priv_spec`, which defaults off and reproduces the previous behavior
exactly when absent, replacing a `TARGET_VENDOR` string comparison; objdump
gained `-M xw`, which decodes the XW compressed encodings and is likewise off
by default.  Neither affects any default-mode output.  The same pass moved the
vendor-extension table rename from `0006` into `0001`, so the series no longer
renames a symbol it introduced two patches earlier; `bfd/elfxx-riscv.c` is
byte-identical before and after that rework.  A follow-up fix folded into
`binutils/0004` exempts the XW rows from the architecture test once `-M xw` has
enabled them, which is what the official build does; without it the eight XW
encodings do not decode at all under the option.  `binutils/0005` was renamed
to match its new subject.  The pre-rework histories are kept as
`refs/openwch/phase8-12.2.0-pre-u3-{gcc,binutils}-*` and
`refs/openwch/phase8-12.2.0-pre-f2-binutils-*`.

The resulting Phase-8 final state was GCC HEAD
`9731e5ee701047373429a191b45a6f07f3e149a7` (tree
`af74531c952c78bab9089ee93af50e3a7fe992ea`) and binutils HEAD
`dfb77909835d602e540ee245392d12fa16e80c81` (tree
`cb7b9681acb401984e98a5e5172bbdfde09eb62e`).  The verification record is in
`tmp/phase8-evidence/12.2.0/`.

A last Phase-8 pass replaced the zero `From` hashes this directory used to
export with the real commit hashes, so that all three toolchain versions in
this repository now share one export convention, and added the `source_commit`
column to `patch-id.tsv`.  It touched the mail-patch envelope only: all sixteen
stable patch IDs were unchanged, both source trees were unchanged, every patch
file differed from its predecessor in its `From` line and nowhere else, and the
sequential replay still landed on the two Phase-8 trees named above.

## Phase 9: the XW rows lost their xlen restriction

`binutils/0004` used to give its sixteen XW opcode table rows
`xlen_requirement = 32`.  The official 12.2 toolchain has no such restriction,
and Phase 9 established that by measuring it here rather than assuming it from
the 15.2.0 result: 184 probes a side, rv32 and rv64 paired column by column,
found the official XW rows identical on rv64 and rv32 in acceptance, encoding
bytes, diagnostic text and all four disassembler modes.  The only rows whose
behaviour tracks xlen are the ones upstream restricts itself (`c.jal`,
`c.ld`, `c.sd`).

Setting the column to 0 closed four divergences, the quietest of which
produced no diagnostic at all: with the rows filtered out on rv64 the
`lbu`/`lhu`/`sb`/`sh` aliases still assembled as their four-byte base forms,
so an rv64 object silently grew rather than failing.  rv32 is unaffected --
the two column values are equivalent there.

New tests pin the rv64 surface both ways: `wch-xw-compressed-rv64.d`,
`wch-xw-rv64-fail.d` and `wch-xw-disassemble-rv64.d`.  Their expectation text
is the official 12.2.0 wording and is deliberately *not* shared with the
15.2.0 series: binutils 2.38 has no Zcb, so these diagnostics have no
`, extension 'zcb' required` tail, and default disassembly prints `.2byte`
where 2.45 prints `.insn`.

The Phase-9 final state, which is what this directory exports, is GCC HEAD
`9731e5ee701047373429a191b45a6f07f3e149a7` (tree
`af74531c952c78bab9089ee93af50e3a7fe992ea`, untouched this round) and binutils
HEAD `c397a553b1ab0bb3a7063077a825da74dd34519a` (tree
`0d01a497ae860ce540c463320ce0a4436e880a05`).  The pre-Phase-9 binutils history
is kept as `refs/openwch/phase9-pre-xlen-binutils`.  All three series --
8.2.0, 12.2.0 and 15.2.0 -- now encode these rows with no xlen requirement.
The measurement is `tmp/phase9-evidence/12.2.0/spec.md`.

The Phase-4 verification record -- the 16-patch replay, clean source state,
final trees matching *that* round's, clean host-dependency rebuild, and
internal 274/274 gate -- is in
`tmp/phase4-evidence/final-pristine-replay-v2-20260813T010000Z/`; the separate
final pristine probes and gate are indexed by
`tmp/prompts/phase-4.checklist.md`.  The content-addressed final provenance
directory named there binds the sources, patch series, runners, applications,
EVT inputs, and both active and pristine evidence lanes.

## CI

CI cannot call `scripts/replay-toolchain-12.2.0.sh` (it compares against a
local active tree that a clean checkout does not have);
`scripts/ci/prepare-sources.sh 12.2.0` reproduces its semantics instead and
downloads the eight pinned archives.  Details:
`analysis/toolchain/phase7-ci-cd.md` §3.6 and §3.7.
