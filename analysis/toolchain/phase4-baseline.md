# Phase 4 baseline — WCH GCC 12.2.0 for darwin-arm64

This document freezes the source and build provenance used by Phase 4 before
the vanilla compiler build starts.  The acceptance specification remains the
WCH binaries under `ref/gcc/darwin-arm64/12.2.0`; public xPack material is a
provenance and recipe reference, not a substitute for observed behavior.

## Decision

The packaging and recipe anchor is xPack
[`v12.2.0-3`](https://github.com/xpack-dev-tools/riscv-none-elf-gcc-xpack/tree/v12.2.0-3),
commit `1737182ba53adb0422ead7faefe23d29f03ecfc4` (high confidence).
The WCH package is a later fork/rebuild of that release rather than an
unmodified stock asset:

- the bundled `distro-info/scripts/VERSION` is exactly `12.2.0-3`;
- bundled `CHANGELOG.md`, `build.sh`, `test.sh`, `tests/run.sh`, three release
  templates, `README-OUT.md`, and `patches/README.md` are byte-identical to
  the public tag;
- the two substantive recipe differences are WCH's application/target rename
  to `riscv-wch-elf` and its 42-entry explicit multilib list;
- the official compiler embeds the v3-style repository-local path
  `/Users/mrs/Work/riscv-none-elf-gcc-xpack.git/build/darwin-arm64/...`.

Stock `v12.2.0-1`, `-2`, and `-3` each name 55 explicit multilib inputs plus
the omitted default, while the bundled WCH recipe names 42 plus the default.
The latter exactly explains the observed 43-line `-print-multi-lib` output.
The old `v12.2.0-1` helper layout instead used a separate
`$HOME/Work/riscv-none-elf-gcc-${version}` work tree, so it is only a
historical ancestor, not the Phase 4 recipe anchor.  `v12.2.0-2` used the new
layout but is contradicted by the bundled v3 files and was superseded for a
packaging defect.

The corresponding public helper reference is xbb-helper `v1.4.7`, annotated
tag object `84d5a156ec6e0f61cb89b348b2a4c2a098c44485`, peeled commit
`17982a305d16b7946ad336509b02aecda260d823`.  Its GCC configure argument order
matches the official line.  This is deliberately recorded as a *reference*,
not the exact WCH helper revision: the xPack dependency was `^1.4.7`, the WCH
helper fork is absent from `distro-info`, stock helper rejects the renamed
target, and stock helper does not add `--with-isa-spec=2.2`.

Therefore Phase 4 uses a two-layer reconstruction:

1. xPack v12.2.0-3 supplies source provenance, directory layout, component
   versions, multilib-generator workflow, and build-stage ordering;
2. the actual compiler build directly replays the WCH `gcc -v` configure argv
   byte for byte, generates `t-elf-multilib` from the bundled WCH 42-token
   recipe, and injects the official target libraries/sysroot byte for byte.

Running the complete stock xPack pipeline is rejected because it would use a
different target/multilib surface and unnecessarily rebuild newlib, libgcc,
and GDB.  Acceptance is based on equal observable literals and target bytes,
not on reproducing an unavailable helper fork.

## Source anchors

xPack v12.2.0-3 downloads GNU release tarballs, not repository snapshots.
The release tarballs preserve the release-generated files and exact source
contents.  Local Git commits track patch deltas; pristine replay starts from
a freshly verified tarball extraction.  Git does not preserve tarball mtimes.

| Component | Public source and verified digest | Tag object | Peeled commit | Public xPack patch surface |
|---|---|---|---|---|
| GCC | [`gcc-12.2.0.tar.xz`](https://gcc.gnu.org/pub/gcc/releases/gcc-12.2.0/gcc-12.2.0.tar.xz), SHA256 `e549cf9cf3594a00e27b6589d4322d70e0720cdd213f39beb4181e06926230ff`; [GNU SHA512 list](https://gcc.gnu.org/pub/gcc/releases/gcc-12.2.0/sha512.sum) gives `e9e857bd81bf7a370307d6848c81b2f5403db8c7b5207f54bce3f3faac3bde63445684092c2bc1a2427cddb6f7746496d9fbbef05fbbd77f2810b2998f1f9173` | `58051b1d9986afc5262c335a42e50b4730bc82b0` | `2ee5e4300186a92ad73f1a1a64cb918dc76c8d67` | none for the public v3/v1.4.7 reference (`XBB_GCC_PATCH_FILE_NAME` is empty) |
| binutils | [`binutils-2.38.tar.xz`](https://ftp.gnu.org/gnu/binutils/binutils-2.38.tar.xz), SHA256 `e316477a914f567eccc34d5d29785b8b0f5a10208d36bbacedcc39048ecfe024` ([GNU release announcement](https://lists.gnu.org/archive/html/info-gnu/2022-02/msg00009.html)) | `d954964ee6f5aeb1bac5ddf9a014f8a335faad78` | `20756b0fbe065a84710aa38f2457563b57546440` | none for the public v3/v1.4.7 reference; its named optional patch is absent and that helper skips it |

The Git tag/commit values are provenance cross-checks, not claims that a Git
tree is byte-identical to a release tarball.  The local patch-management
imports are GCC commit `3280576e992d8fcd57fabd4bb85944fcf2bfaddb`
(tree `e66ae7537f9afc0ad8af700e2f19eb6b8b35c9d2`) and binutils commit
`dc5b5e8935f95730fcd9ac603627d834d52fef64`
(tree `d66ce22b2d9b8ecdf6348b9a85137b63cd93e4bd`).  Both import commits use
`SOURCE_DATE_EPOCH=1767225600`; the source baseline itself remains the
verified tarball content.

The same recipe identifies newlib `4.2.0.20211231`, GDB `12.1`, GMP `6.2.1`,
MPFR `4.1.0`, MPC `1.2.1`, ISL `0.24`, and zlib `1.2.12`.  Target newlib,
libgcc, CRTs, C++ libraries, specs, and sysroot content are not rebuilt in this
project.  GDB is out of scope.

## Official literal surface

The authoritative small evidence bundle is
`tmp/phase4-evidence/s1-official/README.md`.  The complete configured-with line
is retained verbatim in `configured-with.txt` (1435 bytes including LF,
SHA256 `3028beb3525140d50c5a8417aac51ddfcd04859d6657cb0881246e758886aad4`).
Its key values are:

```text
source=/Users/mrs/Work/riscv-none-elf-gcc-xpack.git/build/darwin-arm64/sources/gcc-12.2.0/configure
prefix=/Users/mrs/Work/riscv-none-elf-gcc-xpack.git/build/darwin-arm64/application
build=host=aarch64-apple-darwin23.6.0
target=riscv-wch-elf
pkgversion=xPack GNU RISC-V Embedded GCC arm64
arch=rv32imac abi=ilp32 isa-spec=2.2 multilib=enabled
languages=c,c++,fortran
```

Other frozen surfaces are:

| Surface | Official result |
|---|---|
| GCC / AS / LD versions | `(xPack GNU RISC-V Embedded GCC arm64) 12.2.0`; GNU assembler/ld with the same branding, version 2.38 |
| linker search path | `SEARCH_DIR("/Users/mrs/Work/riscv-none-elf-gcc-xpack.git/build/darwin-arm64/application/riscv-wch-elf/lib");` |
| multilib | 43 lines, 2117 bytes, SHA256 `2110407089b92d9ef1b54be866ca942fa0823a823bad4aed6d1de7874fa183ae` |
| `.comment` | 51 bytes: `00 "GCC: (xPack GNU RISC-V Embedded GCC arm64) 12.2.0" 00` |
| GCC bare XW object attribute | `xw1p0`; concatenated and underscore spellings are byte-identical |
| standalone GAS default ISA spec | 2.2; omitted and explicit 2.2 objects are byte-identical |
| binutils 2.38 mapping symbol | plain `$x`; architecture/version is carried in `.riscv.attributes`, not the symbol name |

The official tool hashes, exact streams, four-way ISA-spec comparison,
33-case diagnostic/acceptance matrix, and positive encoding anchors are all
recorded below `tmp/phase4-evidence/s1-official/`.  These diagnostics are part
of the Phase 4 byte-fidelity surface from the first repair round onward.

## Premise register

| Premise | Evidence | Status |
|---|---|---|
| Packaging/recipe fork is based on xPack v12.2.0-3 | bundled version and byte-identical recipe files; embedded v3 directory layout | verified, high confidence |
| Public helper reference is v1.4.7, but its exact WCH fork SHA is unavailable | v3 dependency and configure ordering; missing helper source plus WCH-only target/ISA branches | bounded uncertainty; direct argv replay selected |
| Selected upstream baselines are the GNU 12.2.0/2.38 release tarballs used by the public v3 recipe | verified tarball digests, v3 `versioning.sh`, official version output | verified baseline; their identity as WCH's exact pre-patch trees is a high-confidence provenance inference, not directly verified |
| Public xPack applies no GCC/binutils source patch relevant to this build | v3 plus helper v1.4.7 reference: application `patches/README.md`, empty GCC patch name, absent optional binutils patch | verified for that public reference; exact WCH helper patch surface unavailable |
| WCH multilib surface is 42 explicit inputs plus default | bundled `versioning.sh` and official 43-line output | verified |
| Bare XW canonicalizes to `xw1p0` | official GCC and GAS object probes | verified |
| Standalone GAS defaults to ISA spec 2.2 and emits plain `$x` | omitted/explicit object comparison and symbol/attribute probes | verified |
| Triple rename has no additional hidden behavioral effect | complete dumpspecs/SEARCH_DIR/multilib/version comparisons plus the final diagnostics, behavioral probes, and 274-artifact gate; every target delta is assigned to an explicit source patch | verified |
