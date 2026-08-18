# WCH GCC 15.2.0 patch series

This directory contains the ordered GCC and binutils 2.45 changes required to
reproduce the WCH 15.2.0 platform-local darwin-arm64 and linux-amd64 gate
artifacts.  Apply each `series` file from top to bottom to pristine upstream
checkouts.

Phase 3.1 adds the binutils diagnostics patch -- `0005` in the current
numbering -- to match the official GAS diagnostics for disabled XW compressed
candidates and the sticky XW/Zcd conflict.  The
same audit also fixes the standalone assembler default through
`--with-isa-spec=2.2` in `scripts/build-toolchain-15.2.0.sh`; that configure
choice is intentionally not a source patch.

Phase 3d first extended the GCC series from three to eight patches using the
full-EVT RC01, RC02, RC04, RC05, and RC07 findings.  The eight-patch active
frozen-path run matches all 47,797 gate artifacts across 1,298 projects; its
sealed evidence is in
`tmp/phase3d-evidence/t5-darwin-active-frozen-stage-a/`.  A fresh upstream
replay has the same staged source trees and independently matches the same
47,797 artifacts; its seal is
`tmp/phase3d-evidence/t5-darwin-pristine-frozen-stage-a/`.

The XW+LTO closure adds a ninth GCC patch.  It registers the exact WCH option
state used by LTO so fixed-seed slim objects remain byte-compatible and each
compiler can consume the other compiler's streams.  The versioned two-platform
gate for that surface lives in `tests/xw-lto/`.

The 2026-08-15 metadata-corrective re-export preserves every source tree and
stable patch ID while repairing two evidence descriptions: patch 0004 no longer
claims an unobserved unnamed-declaration ICE, and patch 0006 now cites its
official shape/specification evidence in the commit message.  Corrected commits
0004 through 0009 were created sequentially, and each exact source tree passed
the 274/274 quick gate after its corrected commit was created and before the
next commit.  The corrected final GCC commit of that phase is
`dfe977da306659c746385781cffc0367dfed7ae9`, and its tree
`0785aaf06ea20bd0f44b5084007d05497bc35e80` is the tree the sealed Darwin and
Linux byte gates of phases 3d through 3h were run on.  The Phase 8 cleanup
below is the first change to that tree since.  The old final commit remains reachable through
the preserved `refs/openwch/phase3d-pre-metadata-correction-20260815` ref.

Phase 3g closes the last three surfaces on which the built toolchain still
behaved differently from the official package.  Only one of them is a source
change: the first XW gate in the diagnostics patch -- `0005` in the current
numbering -- no longer tests the sticky XW eligibility, so an XW candidate is
rejected before the operand diagnostic is reset whenever compressed assembly is
off, which is what every EVT project configures.
`xw-compressed-norvc-xw-fail` covers all eight XW forms, well-formed and
malformed, through the `-march` entry point;
`xw-compressed-attribute-norvc-fail` covers the ELF `.attribute arch` entry
point on one register form and one stack form, again well-formed and malformed;
and `xw-compressed-rvc-cycle` asserts that the eight aliases fall back to their
32-bit encodings while compressed assembly is off and that the XW encoding
returns when it is switched back on.

The other two are build configuration, and `scripts/build-toolchain-15.2.0.sh`
carries them.  binutils is configured `--with-zstd` with `ZSTD_CFLAGS` and
`ZSTD_LIBS` pinned to the Homebrew zstd 1.5.7 the official package links; the
`-L`/`-l` shape matters, because only that shape reaches `dependency_libs` in
`libbfd.la` and thereby every BFD consumer rather than `readelf` alone.  The
GCC configure that follows then probes an assembler that accepts
`--compress-debug-sections=zstd`, which is what puts the `%{gz=zstd:...}`
clause into `*asm_options`; the only permitted change in `gcc/auto-host.h` is
`HAVE_AS_COMPRESS_DEBUG` moving from 1 to 2, and the script fails the build if
that value is not reached.  `ac_cv_func_mmap_fixed_mapped=yes` is preset
because the autoconf run-time probe is killed by the kernel on darwin-arm64 at
its `MAP_FIXED` step regardless of whether mmap works, which is what suppressed
the `elfedit` x86-feature options.  Finally both official `libzstd.1.dylib`
copies -- they are the same code signed twice, so each install location gets
its own -- are shipped next to the programs that load them, and the load
commands are rewritten to `@loader_path` exactly where the official package
did, including the single program it left with an absolute install name.

The final Darwin and Linux full-EVT runs each pass 1,298 projects and compare
47,797 gate artifacts byte-for-byte against that platform's official package.
The versioned XW+LTO seals on both hosts each cover 100 commands, 192 artifacts,
and 492 comparisons with zero failures.  Evidence pointers and hashes are in
`tmp/prompts/phase-3d.checklist.md`.

The two observed bare-XW version strings belong to different byte surfaces:
GCC explicitly emits `xw2p0` in `.riscv.attributes`, while standalone GAS uses
`xw2p2` in mapping symbols.  The series deliberately preserves both.  The GAS-side registration now carries 2.2 from
patch 0001 itself; the separate follow-up patch that used to correct it has
been folded in.

| Component | Patch | Observed difference addressed |
| --- | --- | --- |
| GCC | `gcc/0001-RISC-V-accept-XW-march-strings-blocked-in-all-EVT-pr.patch` | All nine EVT projects stopped while parsing XW multilib entries. |
| GCC | `gcc/0002-RISC-V-match-WCH-unknown-X-diagnostic-bytes.patch` | The unsupported-X diagnostic did not contain WCH's literal `non-standard111` spelling. |
| GCC | `gcc/0003-RISC-V-match-WCH-fast-interrupt-EVT-frames.patch` | Returning fast-ISR objects in v3b, v3c, and v4bc had different frames, exit liveness, and return instructions. |
| GCC | `gcc/0004-c-family-match-WCH-.highcode-section-semantics.patch` | The exact `.highcode` section was still inlineable and `--param=highcode-gen-section-name=1` did not split it by declaration name. |
| GCC | `gcc/0005-c-match-WCH-implicit-function-diagnostics.patch` | C99-and-later implicit function declarations were errors instead of WCH warnings, and four diagnostic literals differed. |
| GCC | `gcc/0006-RISC-V-use-mret-for-WCH-fast-simple-returns.patch` | Shrink-wrapped `simple_return` exits in fast interrupt handlers emitted `ret` instead of `mret`. |
| GCC | `gcc/0007-RISC-V-match-WCH-fast-interrupt-vector-saves.patch` | Fast interrupts software-saved vector registers by default instead of implementing WCH's `ccv-abi` 0/1 policy. |
| GCC | `gcc/0008-RISC-V-keep-WCH-fast-interrupt-rename-targets-live.patch` | Register renaming could select a previously unused `t0` in non-returning fast handlers instead of retaining the live `a5` chain. |
| GCC | `gcc/0009-RISC-V-match-WCH-LTO-option-streaming.patch` | LTO omitted the highcode optimization field and the XW target mask, producing incompatible option streams and different slim objects. |
| binutils | `binutils/0001-RISC-V-accept-bare-XW-arch-attributes-in-EVT-assembl.patch` | GAS rejected XW arch strings emitted by the EVT builds, and registered the extension at a version its own assembler does not use. |
| binutils | `binutils/0002-RISC-V-emit-WCH-XW-compressed-EVT-load-store-bytes.patch` | Ordinary byte/halfword loads and stores did not use the eight observed XW encodings. |
| binutils | `binutils/0003-RISC-V-assemble-custom-opcodes-blocking-v3c-EVT.patch` | v3c stopped at `mcpy`; the four WCH 32-bit custom opcodes were unavailable. |
| binutils | `binutils/0004-RISC-V-make-the-attribute-section-write-out-opt-in.patch` | 43 objects differed only because upstream GAS synthesized or rewrote RISC-V attributes. |
| binutils | `binutils/0005-RISC-V-match-WCH-XW-gate-diagnostic-bytes.patch` | Disabled XW candidates and the XW/Zcd conflict emitted GAS diagnostics different from the official assembler. |
| binutils | `binutils/0006-RISC-V-mark-objects-built-against-the-WCH-software-l.patch` | The official assembler carries an undocumented `--wchsoftlib` option that sets an ELF header flag ours had no way to set. |
| binutils | `binutils/0007-RISC-V-disassemble-the-WCH-XW-compressed-encodings-o.patch` | `objdump -Mxw` was rejected outright, and the XW opcode rows sat behind the encodings they reuse. |

`patch-id.tsv` records the stable patch ID for all sixteen ordered patches.
Phase 3d regenerated both numbered mail series, Phase 3h re-exported the
binutils series, and Phase 8 re-exported both; every re-export verifies each ID
against the corresponding active source commit before pristine replay.

## Apply and build

The following sequence creates pristine GCC `releases/gcc-15.2.0` and
binutils `binutils-2_45` checkouts, verifies the complete ordered patch sets
before applying either one, and builds through the required literal
`/Users/mrs/riscv-gnu-toolchain` path.

```bash
set -euo pipefail
repo=/Users/apple/Projects/openwch
tree="$repo/tmp/toolchain_15.2.0-cleanroom/riscv-gnu-toolchain"
active="$repo/tmp/toolchain_15.2.0/riscv-gnu-toolchain"

mkdir -p "$(dirname "$tree")"
git clone --depth 1 --single-branch --branch releases/gcc-15.2.0 \
  https://github.com/gcc-mirror/gcc.git "$tree/gcc"
git clone --depth 1 --single-branch --branch binutils-2_45 \
  https://git.sr.ht/~sourceware/binutils-gdb "$tree/binutils"
test "$(git -C "$tree/gcc" rev-parse HEAD)" = \
  5115c7e447fc07457443df874bf57840e8316d5f
test "$(git -C "$tree/binutils" rev-parse HEAD)" = \
  2bc7af1ff7732451b6a7b09462a815c3284f9613

gcc_patches=()
while IFS= read -r patch; do
  gcc_patches+=("$repo/patches/15.2.0/gcc/$patch")
done < "$repo/patches/15.2.0/gcc/series"
binutils_patches=()
while IFS= read -r patch; do
  binutils_patches+=("$repo/patches/15.2.0/binutils/$patch")
done < "$repo/patches/15.2.0/binutils/series"

# Later patches refine lines introduced by earlier patches.  Validate each
# complete ordered series in an isolated index before touching the checkout.
validate_series() {
  component=$1
  shift
  scratch_index=$(mktemp "$repo/tmp/$component-patch-index.XXXXXX")
  rm "$scratch_index"
  GIT_INDEX_FILE="$scratch_index" git -C "$tree/$component" read-tree HEAD
  for patch in "$@"; do
    GIT_INDEX_FILE="$scratch_index" \
      git -C "$tree/$component" apply --cached --check "$patch"
    GIT_INDEX_FILE="$scratch_index" \
      git -C "$tree/$component" apply --cached "$patch"
  done
  rm "$scratch_index"
}
validate_series gcc "${gcc_patches[@]}"
validate_series binutils "${binutils_patches[@]}"

(
  cd "$tree/gcc"
  for patch in "${gcc_patches[@]}"; do
    git apply --index "$patch"
  done
  cp "$active/gcc/gettext-0.22.tar.gz" .
  cp "$active/gcc/gmp-6.2.1.tar.bz2" .
  cp "$active/gcc/mpfr-4.1.0.tar.bz2" .
  cp "$active/gcc/mpc-1.2.1.tar.gz" .
  cp "$active/gcc/isl-0.24.tar.bz2" .
  ./contrib/download_prerequisites --verify --sha512
)
(
  cd "$tree/binutils"
  for patch in "${binutils_patches[@]}"; do
    git apply --index "$patch"
  done
)

golden_link="$repo/tmp/golden/toolchain-current"
original_target=$(readlink /Users/mrs/riscv-gnu-toolchain)
original_golden_target=$(readlink "$golden_link")
restore_link() {
  ln -sfn "$original_target" /Users/mrs/riscv-gnu-toolchain
  ln -sfn "$original_golden_target" "$golden_link"
  test "$(readlink /Users/mrs/riscv-gnu-toolchain)" = "$original_target"
  test "$(readlink "$golden_link")" = "$original_golden_target"
}
trap restore_link EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
ln -sfn "$(cd "$tree" && pwd -P)" /Users/mrs/riscv-gnu-toolchain
test "$(readlink /Users/mrs/riscv-gnu-toolchain)" = "$(cd "$tree" && pwd -P)"

export SOURCE_DATE_EPOCH=1767225600
BUILD_JOBS=16 bash "$repo/scripts/build-toolchain-15.2.0.sh" "$tree"
bash "$repo/scripts/evt-compare.sh" 15.2.0 \
  "$tree/output/bin/riscv32-wch-elf-gcc"
restore_link
trap - EXIT HUP INT TERM
```

`build-toolchain-15.2.0.sh` installs the locally built host executables and
then injects only the three frozen official target-library trees documented by
Phase 2.  It does not build target runtime libraries.

## binutils patch 0004: the vendor special case is gone

Earlier revisions of `binutils/0004` gated `riscv_write_out_attrs()` with
`strcmp (TARGET_VENDOR, "wch")`.  `TARGET_VENDOR` is a compile-time string
literal, so the comparison folded to a constant and the call disappeared
together with the function and its exclusive diagnostic string
`internal: bad RISC-V privileged spec (%s)`, which both upstream builds and the
official assembler retain.  The EVT corpus never reaches that path, so the byte
gate could not see the loss; the upstream-versus-ours strings differential
(SR-01) is what found it.

`binutils/0004-RISC-V-make-the-attribute-section-write-out-opt-in.patch`
replaces that with the mechanism the official assembler actually uses: a
run-time flag set by a `--w_priv_spec` long option that no help text lists,
combined with the upstream condition, i.e.
`w_priv_spec && (arch_attr || explicit_attr)`, with `DEFAULT_RISCV_ATTR` left
at 1.  Because a flag rather than the target now decides, the upstream
attribute tests run again on this target instead of being excluded from it, and
the diagnostic is back in the assembler.

## Phase 3h

Phase 3h reworks patch 0004 into that shape, folds the XW mapping-symbol
correction into patch 0001 so the series no longer contradicts itself, and adds
the last two behavioural gaps the official package had over ours: the
`--wchsoftlib` ELF flag and the `-Mxw` disassembler option.  The binutils series
therefore goes from six patches to seven.  Four of the seven patch ids change --
the two that were rewritten and the two that are new -- while `0002`, `0003` and
the renumbered `0005` keep the ids they had, which is the direct evidence that
the patches this phase did not touch were in fact not touched.  The
XW opcode rows move ahead of the Zcd and Zcb rows they overlap, which an
exhaustive 65,536-halfword sweep across four architecture profiles and four
disassembler modes shows is what the official objdump does; the same sweep
confirms the default and `-Mno-aliases` modes are unchanged.

## Phase 8

Phase 8 is a cleanup round: every line has to be explainable, the byte gate must
not move, and whatever only the series' own history explains is removed.  One
deletion it first attempted did change behaviour and has been reverted; see the
last bullet.

* Two self-cancelling pairs are folded away, so no patch now adds something a
  later patch takes back: the fast-interrupt register-rename exception (added in
  GCC `0003`, removed in GCC `0008`) and the Zcd subset tightening (added in
  binutils `0002`, reverted in binutils `0005`).  GCC `0008` therefore becomes
  the regression test on its own.  The intermediate states that carry measured
  evidence -- the XW diagnostic state table in binutils `0005` and the
  65,536-halfword table-order sweep in binutils `0007` -- are deliberately left
  as they are.
* Two unreachable `case INSN_CLASS_XW` arms leave `bfd/elfxx-riscv.c`.  Both
  callers of the shared subset queries exclude the class before consulting them,
  which the binutils `0005` message already says in prose.  The binutils series
  now touches BFD in exactly one place: the extension table row in `0001`.
* `riscv_wch_fast_interrupt_saved_reg_p` keeps `|| regno ==
  RETURN_ADDR_REGNUM`, and its comment now says why.  The cleanup first removed
  that test, on the reasoning that ra is listed in both `FIXED_REGISTERS` and
  `CALL_USED_REGISTERS` and so is already covered by
  `call_used_or_fixed_reg_p`.  That reasoning is wrong: `fix_register()`
  declines only the stack and frame pointers, so `-fcall-saved-ra` clears both
  of those bits for ra, and without the explicit test the handler then
  software-saves a register the hardware already saved -- measured against the
  official assembler, which does not.  The removal was reverted; what remains
  from that edit is the documentation comment, which had drifted onto the wrong
  function and stated the opposite of what the function returns.
* The three XW mapping-symbol tests keep their `riscv*-wch-elf` restriction and
  now say why: every input that could vary by target is pinned in the test
  itself, but the expectation has only ever been measured on that target.
* The GCC patches carry ChangeLog entries, and the commit messages are rewrapped
  and no longer describe superseded revisions of themselves.

The Phase 8 round produced the source trees
`5bb6a45665c03f5f67eee83f7a7598d135a679e1` (GCC) and
`22849f4548da2e1055a71b95cd78ddef3cbb5625` (binutils).  Ten of the sixteen
patch ids were unchanged, which is the direct evidence that the patches that
round did not touch were in fact not touched.

## Phase 9: the XW rows lost their xlen restriction

The XW opcode table rows used to carry `xlen_requirement = 32`, which the
official toolchain does not.  Phase 9 measured the official rv64 surface on
both 15.2.0 and 12.2.0 -- 184 probes a side, rv32 and rv64 paired column by
column -- and found the official XW rows unrestricted on every one of them:
acceptance, encoding bytes, diagnostic text and all four disassembler modes
read the same on rv64 as on rv32.  The only rows whose behaviour tracks xlen
at all are the ones upstream restricts itself (`c.jal`, `c.ld`, `c.sd`).

Setting the column to 0 closed four divergences at once, the quietest of
which produced no diagnostic: with the rows filtered out on rv64 the
`lbu`/`lhu`/`sb`/`sh` aliases still assembled, as their four-byte base forms,
so an rv64 object silently grew instead of failing.  The other three were the
outright rejection of `c.lbu` and friends, the `illegal operands` versus
`unrecognized opcode` diagnostic split, and `objdump -Mxw` printing
`.insn`/`.2byte` where the official prints the XW mnemonic.  rv32 is
unaffected: the two column values are equivalent there, and the rv32 gate
artifacts are byte-identical across the change.

New tests pin the rv64 surface in both directions -- `xw-compressed-rv64.d`
(the sixteen forms assemble to the rv32 bytes), `xw-compressed-rv64-fail.d`
(rv64 without `xw` is rejected, with the official wording) and
`xw-compressed-dis-rv64.d` (an elf64 object decodes under `-Mxw`).  The
expectation text is the official 15.2.0 wording and is *not* interchangeable
with the 12.2.0 series': binutils 2.38 has no Zcb, so its diagnostics lack the
`, extension 'zcb' required` tail and its default disassembly prints `.2byte`
rather than `.insn`.

The series now produces the source trees
`5bb6a45665c03f5f67eee83f7a7598d135a679e1` (GCC, untouched this round) and
`1321f9e24fd6843db33411451b0d382260f20cb0` (binutils).  The pre-Phase-9
binutils history is kept as `refs/openwch/phase9-pre-xlen-binutils`.  All
three series -- 8.2.0, 12.2.0 and 15.2.0 -- now encode these rows with no
xlen requirement.
The divergence was first recorded as finding P3-2 in
`analysis/toolchain/phase3-review.md`; the measurement that closed it is
`tmp/phase9-evidence/15.2.0/spec.md`.

## CI

`.github/workflows/toolchain-ci.yml` runs this sequence unattended on both
platforms via `scripts/ci/prepare-sources.sh 15.2.0`, with the prerequisite
archives fetched by `contrib/download_prerequisites` itself rather than copied
from an active tree.  Details: `analysis/toolchain/phase7-ci-cd.md` §3.7.
