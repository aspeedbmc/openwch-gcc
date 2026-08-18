# XW + LTO parity gate

This directory contains the versioned, platform-local parity gate for the WCH
XW extension.  It deliberately covers behavior that the EVT tree does not:

- all eight XW compressed byte/halfword load/store forms;
- slim-LTO option serialization and `lto1` re-materialization of global
  `-march=..._xw`, `target("arch=+xw")`, and a versioned XW target attribute;
- Zcb-only encoding, XW-over-Zcb encoding priority, the D+C+XW `c.fld`
  rejection, and F+C+XW coexistence.

The gate runs four lanes, in order: `official-1`, `official-2`, `ours-1`, and
`ours-2`.  Every command runs in one shared absolute working directory and
invokes a fixed `toolchain-current` symlink.  The symlink target changes
between lanes; its pathname and the command cwd do not.  The runner first
checks the two self-consistency pairs, then the two official-vs-ours pairs.
It compares raw return-code files, stdout, stderr, and every declared artifact
byte for byte.  Nothing is normalized.

The LTO artifact set includes the preprocessed and LTO assembly for each TU,
both slim `.o` files, linker resolution files, saved WPA/ltrans argument
files, re-materialized ltrans assembly and `.o`, and the positive final
ELF/bin.  `-flto=1 -save-temps=obj` retains those ltrans files directly.  The
positive link uses global `-march=rv32imac_xw`; an additional base-march link
is an expected failure even though its ltrans assembly re-materializes the
function-level XW options.  This records GAS's file-level sticky XW gate as
raw rc/stdout/stderr rather than hiding it.

Each lane also runs its own `riscv32-wch-elf-lto-dump -list` over both slim
objects.  Those reader rc/stdout/stderr bytes are part of the same parity
matrix.  Formal runs additionally reject a `--platform` value that does not
match the Darwin/arm64 or Linux/x86_64 host executing the suite.

## Formal Darwin run

The evidence path must be absolute, below this repository's `tmp/`, and must
not exist.  A failed or interrupted attempt is immutable history; choose a new
path rather than reusing it.

```sh
repo=$(pwd)
python3 tests/xw-lto/run.py \
  --platform darwin-arm64 \
  --official-root "$repo/ref/gcc/darwin-arm64/15.2.0" \
  --ours-root "$repo/tmp/toolchain_15.2.0/riscv-gnu-toolchain/output" \
  --evidence-root "$repo/tmp/phase3d-evidence/xw-lto-darwin-attempt-N"

python3 tests/xw-lto/audit_and_seal.py \
  --evidence-root "$repo/tmp/phase3d-evidence/xw-lto-darwin-attempt-N"
```

The formal result is valid only when both commands return zero and the second
command creates `SEAL.json` with state `SEALED`.

## Formal Linux run

Run inside the Linux build/gate environment whose repository mount has the
same absolute path for all four lanes (the phase-5 container uses
`/work/openwch`).  Compare against the Linux official package, not Darwin's.

```sh
repo=$(pwd)
python3 tests/xw-lto/run.py \
  --platform linux-amd64 \
  --official-root "$repo/ref/gcc/linux-amd64/15.2.0" \
  --ours-root "$repo/tmp/toolchain_15.2.0-linux-phase3d-0009-20260814/riscv-gnu-toolchain/output" \
  --evidence-root "$repo/tmp/phase3d-evidence/xw-lto-linux-attempt-N"

python3 tests/xw-lto/audit_and_seal.py \
  --evidence-root "$repo/tmp/phase3d-evidence/xw-lto-linux-attempt-N"
```

## Harness-only smoke mode

Formal mode rejects identical resolved official/ours roots.  For a quick
harness smoke test, the explicit option below permits one toolchain on both
sides.  The auditor also requires an explicit opt-in and emits only
`SMOKE_SEAL.json`; smoke evidence can never acquire a formal `SEAL.json`.

```sh
repo=$(pwd)
root="$repo/ref/gcc/darwin-arm64/15.2.0"
python3 tests/xw-lto/run.py \
  --platform darwin-arm64 \
  --official-root "$root" \
  --ours-root "$root" \
  --evidence-root "$repo/tmp/xw-lto-smoke-attempt-N" \
  --smoke-identical-roots

python3 tests/xw-lto/audit_and_seal.py \
  --evidence-root "$repo/tmp/xw-lto-smoke-attempt-N" \
  --allow-smoke
```

Both programs are fail-closed.  The runner atomically creates the evidence
root and refuses a pre-existing path.  The independent auditor imports no
runner code, rehashes the complete suite contract and all evidence, checks the
closed command/artifact denominators, and writes a seal only after every
check passes.  Its final action removes all user/group/other write bits from
every evidence file and directory, including the evidence root; a sealed tree
is therefore recursively read-only.  Never chmod and reuse it: any new run or
audit attempt gets a fresh evidence root.
