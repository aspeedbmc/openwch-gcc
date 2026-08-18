# Phase 4 literal surface — GCC 12.2.0 / binutils 2.38

This records the final S2 compiler-only build before any WCH ISA behavior
patch.  The build uses GCC source HEAD
`65fe1a3ae3e06d279bdf3a0669ae6cfa2b0c287d` and binutils source HEAD
`dc5b5e8935f95730fcd9ac603627d834d52fef64`.  The GCC history contains only
the WCH multilib configuration layer and upstream GCC 12 backport
`a995fded34fe488153b06bb41e026277f01efded` for recent libc++ host builds;
neither is a WCH ISA behavior repair.

## Build and path anchors

- physical project root:
  `tmp/toolchain_12.2.0/riscv-none-elf-gcc-xpack.git`;
- required literal symlink:
  `/Users/mrs/Work/riscv-none-elf-gcc-xpack.git` → the physical root above;
- source roots, prefix, sysroot, host dependency prefix, target triple, and
  configure argv match the official observable paths under that symlink;
- `SOURCE_DATE_EPOCH=1767225600`, `TZ=UTC`, `LC_ALL=C`, `umask 022`, and a
  fixed system `PATH` are explicit in `scripts/build-toolchain-12.2.0.sh`;
- historical S2 build-script SHA256:
  `d6a3805ecc5a090eac06fcb74b699e16786bb85d03809a718e88298f179b0cc2`.

The script rebuilt binutils and `all-gcc`/`install-gcc`, but no target
library.  It injected only the official target headers, picolibc tree,
target libraries (excluding self-built linker scripts), target CRT/libgcc
payload, specs, and multilib directories.  Six independent injected files
match their official sources byte for byte; see
`tmp/phase4-evidence/s2-literals-final/injection-samples.tsv`.

## Byte comparisons

All comparisons below were run directly against
`ref/gcc/darwin-arm64/12.2.0` and the final S2 output.  Small authoritative
streams, hashes, and comparison results live under
`tmp/phase4-evidence/s2-literals-final/`.

| Surface | Result |
|---|---|
| complete `Configured with:` line | byte equal; 1435 B, SHA256 `3028beb3525140d50c5a8417aac51ddfcd04859d6657cb0881246e758886aad4` |
| `gcc --version` stdout/stderr | byte equal |
| `as --version` stdout/stderr | byte equal |
| `ld --version` stdout/stderr | byte equal |
| linker `SEARCH_DIR` line | byte equal; SHA256 `918ad753ed7e45212cb35e9e66f23b2cdff3ffecd2762bbcd82dc805d36ee737` |
| `gcc -print-multi-lib` | byte equal; 43 lines, SHA256 `2110407089b92d9ef1b54be866ca942fa0823a823bad4aed6d1de7874fa183ae` |
| complete `gcc -dumpspecs` | byte equal |
| compiled object's `.comment` section | byte equal; 51 B, SHA256 `bfa8df204ba5b16e671de2fb23465fd5aa8e29fd1fe59c55571ad1f776930cc9` |

The `.comment` bytes are exactly
`00 4743433a20 28785061636b20474e5520524953432d5620456d626564646564204743432061726d3634292031322e322e30 00`, i.e. a leading NUL,
`GCC: (xPack GNU RISC-V Embedded GCC arm64) 12.2.0`, and a trailing NUL.

## Host capability and binary boundary

The final GCC child configure has both `HAVE_ZSTD_H=1` and `HAVE_isl=1`.
The pinned static host libraries are linked into cc1/lto1; no repository,
Homebrew, or private absolute dylib dependency remains.  This preserves the
official ZSTD LTO stream choice without requiring host binary identity,
which is outside the gate.

Directed official binary inspection found only the expected source,
application, and host dependency roots.  It found no recoverable object build
directory or build timestamp.  Runtime driver paths (`COLLECT_GCC`, LTO
wrapper, search dirs, specs) are relocatable from the invocation root, so EVT
comparison continues to use the shared neutral toolchain path.

## S2 residual differences

The tiny C object used to sample `.comment` is not byte-identical (official
752 B versus S2 744 B), while its `.comment` is identical.  That is expected
at the vanilla measurement point: remaining target behavior/attribute/ISA
differences are classified by the first full EVT compare in
`phase4-diff-inventory.md`; no behavior repair was made in S2.

## Final one-sided strings classification

The final-stage audit intentionally compares complete sorted-unique string
sets rather than requiring whole Mach-O host binaries to match.  Its
executable, hash-bound workflow is
`tmp/phase4-evidence/s4-final/strings-audit/run-strings-audit.sh`.  The final
active result is
`tmp/phase4-evidence/final-active-strings-v2-20260813T010000Z/`; the final
pristine replay result is
`tmp/phase4-evidence/final-pristine-strings-20260813T012000Z/`.  Each retains
only compact `summary.tsv`, `one-sided-classification.tsv`, and
`provenance.tsv` records, never raw one-sided string dumps.

The preliminary audit found three official-only target behaviors that the EVT
gate did not exercise: the `highcode-gen-section-name` parameter, independent
Zmmul state with an M+Zmmul conflict diagnostic, and GAS `wchsoftlib`.  Each
was live-probed against official 12.2 before implementation.  `wchsoftlib` is
not a no-op: it accepts one or two leading dashes and ORs `0x01000000` into
ELF `e_flags`.  The final source series implements all three with normal GCC
parameter/attribute logic, target option state, and GAS ELF-flag handling.

Other one-sided sets are classified rather than concealed:

- host compiler, SDK, Mach-O linkage, and static-versus-dynamic dependency
  signatures are excluded host-binary surfaces under the project boundary;
- extra upstream source filenames and target breadth are implementation
  provenance, not observable WCH literals;
- every `/Users` path is separately checked against the approved
  `/Users/mrs/Work/riscv-none-elf-gcc-xpack.git` root;
- complete date/time patterns and unexpected build-root sets must be empty;
- configure argv, application prefix, branding, versions, SEARCH_DIR,
  multilib, dumpspecs, and `.comment` remain exact byte gates.

Both final lanes cover 20 high-risk unexpected-root and WCH target-behavior
rows; every such set is empty.  The ten additional temporal-literal rows are
medium risk and are also all empty.  In each lane the highcode,
M+Zmmul-conflict, and wchsoftlib probe streams byte-match the official tool.
The broader observable-literal runner also passes all 13/13 surfaces for both
active and pristine applications:
`final-active-literals-20260813T004000Z/` and
`final-pristine-literals-20260813T012000Z/`.

The final build script SHA256 is
`6951c4f3d245a58791190d0f3c522e462f7e7f844f1ace0f5c2a177072a53c4e`.
The S2 script SHA above is retained only as historical provenance for the
measurement point described by this report.
