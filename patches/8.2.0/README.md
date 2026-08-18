# WCH GCC 8.2.0 patch series

This directory contains the ordered GCC 8.2.0 and binutils 2.32 changes
required to reproduce the WCH 8.2.0 (`riscv-none-embed`) darwin gate
artifacts.  Both upstream trees are the xPack forks the official package was
built from, `xpack-dev-tools/riscv-gcc` and
`xpack-dev-tools/riscv-binutils-gdb`, and both start from the same tag,
`v8.2.0-3.1`.  Apply the top-level `series` file from top to bottom to
pristine checkouts of those two tags.

Unlike the 15.2.0 and 12.2.0 series, this one is split three ways.  `gcc/`
and `binutils/` hold the changes that move target artifact bytes, and `host/`
holds the one change that only lets the 2018-era sources compile on a modern
Darwin host.  Keeping the host slice out of the behaviour surface is a
phase-6 requirement, so the patch count that matters for the byte gate is six
GCC-and-binutils patches, not seven files.

## Numbering and the `host/` split

The patch number is the position in its own source tree's commit stack, not a
per-directory counter: the GCC tree contributes one five-commit stack, so its
patches are numbered `0001` through `0005` and moving the second one into
`host/` leaves a visible gap at `0002` in `gcc/`.  That keeps `series`, the
file names and the `Subject: [PATCH n/5]` prefixes consistent with each other.
Neither existing version settles the question: 15.2.0 has one directory per
source tree, and 12.2.0's equivalent host patch
(`gcc/0002-Backport-safe-ctype-include-ordering-for-recent-libc.patch`) was
never moved out of `gcc/`, so neither shows what to do when a patch changes
directory.  The rule used here is the self-consistent one — the number is the
stack position — and the `host/` split changes which directory a patch belongs
to, never the stack order.  The binutils tree contributes an independent
two-commit stack, `binutils/0001` and `binutils/0002`.

| Component | Patch | Observed difference addressed |
| --- | --- | --- |
| GCC | `gcc/0001-riscv-regenerate-t-elf-multilib-from-the-WCH-GCC_MUL.patch` | The stock tree carried the SiFive 7-row default multilib table; the official build reports 23 rows, including `rv32ecxw/ilp32e`, `rv32imacxw/ilp32` and `rv32imafcxw/ilp32f`. |
| Host | `host/0002-host-move-C-standard-header-includes-before-safe-cty.patch` | `gcc/system.h` includes the C++ standard headers after `safe-ctype.h`, so modern libc++ declarations such as `char_type toupper(char_type)` hit the poisoned macros and the build fails. |
| GCC | `gcc/0003-riscv-accept-the-WCH-QingKe-xw-march-spelling.patch` | Every `-march` string the EVT projects use died with `unsupported ISA substring 'xw'`. |
| GCC | `gcc/0004-riscv-accept-the-WCH-QingKe-WCH-Interrupt-fast-inter.patch` | `interrupt("WCH-Interrupt-fast")` was rejected with `unrecognized argument`, so handlers got an ordinary frame and left through `ret` where the official objects leave through `mret`. |
| GCC | `gcc/0005-c-family-add-the-WCH-highcode-gen-section-name-param.patch` | The `.highcode` section had no special meaning: the declaration was still inlineable, and `--param=highcode-gen-section-name=1` did not exist to split it per declaration name. |
| binutils | `binutils/0001-RISC-V-add-the-WCH-XW-compressed-byte-and-halfword-a.patch` | The eight XW 16-bit byte/halfword load and store forms were unavailable, so ordinary `lbu`/`lhu`/`sb`/`sh` never took the short encoding the vendor assembler picks. |
| binutils | `binutils/0002-RISC-V-decode-the-WCH-XW-compressed-accesses-under-o.patch` | `objdump -M xw` was rejected outright, so XW halfwords disassembled through the double-precision slots they occupy. |

`patch-id.tsv` records the stable patch ID and the source commit of all seven
ordered patches.  Every ID was verified against the corresponding source
commit after the author header rewrite and again after the final file names
were fixed; the patch ID depends on the diff alone, so it is what proves the
rewrite changed nothing but the header.

The `source_commit` column was re-derived once more when the commit messages
were revised for clarity and the `gcc/system.h` comment was brought in line
with the block it introduces: rewriting a message rewrites the commit, so
every SHA below `gcc/0001` changed, while the stable patch IDs stayed put
except for `host/0002`, whose diff genuinely grew by those two comment lines.
So the column tracks the current commits, not the ones phase 6 first
published; the stable patch IDs are the stable handle across both rewrites.

## The multilib patch is build infrastructure

`gcc/0001` regenerates `gcc/config/riscv/t-elf-multilib` from the
`GCC_MULTILIB` list WCH ships in its own build configuration
(`ref/gcc/darwin-arm64/8.2.0/distro-info/scripts/common-versions-source.sh`),
which is exactly what the xPack framework does whenever that variable is set.
It is generated output, not a behavioural change to the RISC-V backend, and
it is listed separately in the phase-6 checklist for that reason -- the same
accounting phase 4 used.  Its correctness is validated downstream by
comparing our `gcc -print-multi-lib` byte-for-byte against the official
23-row table, not by reading the table.

## `host/`: host adaptation, separated from behaviour

`host/0002` reorders includes in `gcc/system.h` and changes no code.  It
affects how the compiler is built on a modern Darwin host and cannot reach
target code generation; later upstream releases adopted the same ordering for
the same class of conflict.  It is kept out of `gcc/` so that the behaviour
surface under audit stays exactly the patches that move artifact bytes.

## Host adaptations that are not patches

The remaining modern-host accommodations live in
`scripts/build-toolchain-8.2.0.sh` rather than in this patch set, because
they are build flags and pinned dependency versions rather than source
changes, and none of them is observable in a gate artifact:

- Four `-Wno-` flags in the host `CFLAGS`
  (`-Wno-implicit-function-declaration`, `-Wno-implicit-int`,
  `-Wno-int-conversion`, `-Wno-incompatible-function-pointer-types`) demote
  the K&R-isms clang 16 promoted to hard errors, so the 2018/2019-era sources
  stay pristine.
- The host dependency prefix pins ISL to 0.18, the version this GCC expects.
- The pinned zlib is built by copying its source into the build directory
  (it does not support VPATH builds) with `-UTARGET_OS_MAC` appended, so the
  2012-era configure probes do not mistake the modern macOS SDK.  The
  authoritative eight-item enumeration of these script-level adaptations
  lives in `analysis/toolchain/phase6-closure.md` §4.
- The script re-execs itself through `arch -x86_64` when started from an
  arm64 shell, because the official configure literal is
  `--build/--host=x86_64-apple-darwin17.7.0` and the runtime checks have to
  see an x86_64 host.  The `-arch x86_64` flag stays in `CC`/`CXX` anyway,
  since clang keeps defaulting to arm64 code generation inside that shell.
- The binutils phase exports `ac_cv_lib_dl_dlopen=no`.  On the darwin17
  host the official build ran on, libtool's darwin branch finds `-ldl`
  unusable and leaves `LIBDL` empty; modern macOS SDKs alias `libdl.tbd`
  to the whole of `libSystem.tbd`, so `-ldl` links, lands ahead of
  `libiberty.a` on the libtool link line, and its getopt wins over
  libiberty's — which degrades the tools' "unrecognized option" prefix
  from argv[0] verbatim to a basename.  Pinning the probe result restores
  the official link line.  It is exported (recursive sub-configures keep
  private `config.cache` files, so an `env VAR=val ./configure` prefix is
  not enough) and unset before the GCC phase.  Same class of
  environment replication as `MACOSX_DEPLOYMENT_TARGET=10.13`, not a
  source change.
- The injection step copies `lib/bfd-plugins/liblto_plugin.so` from the
  official package byte-for-byte.  The official darwin 8.2.0 package
  ships it as a 59-byte text file — a symlink flattened by WCH's own
  packaging (12.2.0 darwin and 15.2.0 linux carry real binaries there).
  `nm` and friends dlopen it and print a diagnostic; defect fidelity
  means shipping the same bytes, not a working plugin or a repaired
  symlink.

## Apply

Each file is a `git format-patch` mail, so the whole set applies with
`git am`.  The `host/` line goes to the GCC checkout like the `gcc/` lines;
only the `binutils/` lines go to the binutils checkout.

```bash
set -euo pipefail
repo=/Users/apple/Projects/openwch
tree=/path/to/pristine/checkouts

git clone https://github.com/xpack-dev-tools/riscv-gcc.git "$tree/gcc"
git clone https://github.com/xpack-dev-tools/riscv-binutils-gdb.git "$tree/binutils"
git -C "$tree/gcc" checkout v8.2.0-3.1
git -C "$tree/binutils" checkout v8.2.0-3.1
test "$(git -C "$tree/gcc" rev-parse HEAD)" = \
  0c7a874f0b6f452eeafde57731646e5f460187e4
test "$(git -C "$tree/binutils" rev-parse HEAD)" = \
  82b51c7b5087ddb77988287cd7a2dd8921331bfd

while IFS= read -r patch; do
  case "$patch" in
    binutils/*) component=binutils ;;
    *)          component=gcc ;;
  esac
  git -C "$tree/$component" am "$repo/patches/8.2.0/$patch"
done < "$repo/patches/8.2.0/series"

test "$(git -C "$tree/gcc" rev-parse HEAD^{tree})" = \
  97b81fa8f52fa7037045f428f41e37099ba16fdf
test "$(git -C "$tree/binutils" rev-parse HEAD^{tree})" = \
  8d0d7da3c3b3376d07ef0f76f0f00b6b913dcf40
```

The two tree hashes are the acceptance condition for the export itself: they
are the phase-8 final trees, the ones the current gate artifacts were built
from.  The gcc value moved from the phase-6 figure when the phase-8 cleanup
synchronised the `gcc/system.h` comment; the binutils tree was untouched by
that change and still carries its phase-6 value.  The build that
follows is driven by `scripts/build-toolchain-8.2.0.sh`, which needs the
literal `/Users/wch/Work/riscv-none-embed-gcc-10.2.0-1.2` path and
`SOURCE_DATE_EPOCH=1767225600`, and which injects the official target
libraries bytewise rather than building them.

## CI

`scripts/ci/prepare-sources.sh 8.2.0` performs the block above unattended and
fetches the five pinned host dependencies; it must not use this tree's
`contrib/download_prerequisites`, whose versions differ from the build's.
Details: `analysis/toolchain/phase7-ci-cd.md` §3.7.
