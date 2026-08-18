# openwch

An open-source rebuild of the WCH QingKe RISC-V GCC toolchains, reproduced from pristine
upstream sources plus a reviewable patch series, and held to one acceptance criterion:
byte-for-byte equality with the official WCH package.

[中文版 README](README.zh-CN.md)

## What this is

WCH ships three GCC toolchains for its QingKe RISC-V microcontrollers inside MounRiver
Studio. This repository rebuilds all three from pristine upstream GCC and binutils, and
proves the rebuild by comparing artifacts — `.o`, `.elf`, `.bin` — against what the official
toolchain produces from the same EVT project with the same compile configuration.

| Version | Target triple | binutils | Patches (GCC + binutils) | Host platforms |
| --- | --- | --- | --- | --- |
| GCC 15.2.0 | `riscv32-wch-elf` | 2.45 | 9 + 7 | darwin-arm64, linux-amd64 |
| GCC 12.2.0 | `riscv-wch-elf` | 2.38 | 9 + 7 | darwin-arm64 |
| GCC 8.2.0 | `riscv-none-embed` | 2.32 | 4 + 2, plus one host-build patch | darwin (x86_64 build, Rosetta on Apple Silicon) |

The comparison is always **per platform**: a darwin build against the darwin official
package, a linux build against the linux official package. The two official packages differ
from each other at link level, so cross-platform equality is neither a fact nor a goal here.
And this repository ships the compiler only — GCC and binutils patches, build scripts and
the comparison harness. The target libraries (libgcc, newlib, crt, specs, sysroot) are
reused byte-for-byte from the official package and injected by the build scripts.

## Background

WCH distributes modified GCC and binutils binaries without releasing the corresponding
modified sources. This project starts from the pristine upstream releases and reconstructs
every modification as an ordered, explainable patch series — for GPL compliance and public
research into the QingKe custom ISA.

## What we did

**39 patch files**, exported as `git format-patch` mails with a stable patch-ID ledger
(`patch-id.tsv`) per version:

| Version | GCC | binutils | Other | Total | Series README |
| --- | --- | --- | --- | --- | --- |
| 15.2.0 | 9 | 7 | — | 16 | [patches/15.2.0/README.md](patches/15.2.0/README.md) |
| 12.2.0 | 9 | 7 | — | 16 | [patches/12.2.0/README.md](patches/12.2.0/README.md) |
| 8.2.0 | 4 | 2 | 1 (`host/`, build-only) | 7 | [patches/8.2.0/README.md](patches/8.2.0/README.md) |

The changes are ordinary upstream-shaped source work — machine-description patterns, opcode
table rows, `-march` parsing and ELF attribute logic, option registration, diagnostics —
each traceable to one observed behavioural difference, which the series READMEs tabulate
patch by patch.

**Custom ISA support.** The largest surface is the WCH `XW` compressed byte/halfword
load-store extension (eight forms, register and stack-relative) on the assembler,
disassembler and ELF-attribute sides, plus the WCH fast-interrupt ABI, `.highcode` section
semantics, the four 32-bit custom opcodes, and the hidden `--w_priv_spec`, `--wchsoftlib`
and `objdump -M xw` option surfaces. See [wch-xw.md](wch-xw.md) for what XW is and
[ref/wch-isa-research/](ref/wch-isa-research/) for the ISA facts — this repository does not
rediscover encodings, it verifies what the toolchain accepts and what bytes it produces.

**Acceptance is a byte gate**, on two levels:

| Level | Corpus | 15.2.0 | 12.2.0 | 8.2.0 |
| --- | --- | --- | --- | --- |
| quick (per-round regression) | 9 selected EVT projects | 274 / 274 per platform | 274 / 274 | 242 / 242 (8 projects) |
| full (closing gate) | whole buildable EVT tree | 47,797 artifacts across 1,298 projects, on each of darwin-arm64 and linux-amd64 | — | 43,969 artifacts across 1,203 projects |

"Byte-for-byte identical" here means precisely: identical under a two-sided symmetric
`-fdebug-prefix-map` normalisation of the toolchain prefix, with zero normalisation at the
comparison stage itself; `.map` and `.lst` are diagnostic aids, not gate artifacts. Every
round was audited by an independent reviewer that did not author the work, and every
adjudication is logged — reports in [analysis/](analysis/), decisions in [DECISIONS.md](DECISIONS.md).

## Getting the inputs

Two external inputs have to be put in place yourself; neither is tracked here.

### Official reference packages

The comparison baseline. Both land in `ref/gcc/<platform>/<version>/`, which is gitignored.

* **darwin** — download MounRiver Studio 2 from mounriver.com, place it as
  `ref/MounRiver Studio 2.app`, then run
  [`scripts/extract-wch-toolchain.sh`](scripts/extract-wch-toolchain.sh) to extract each
  bundled toolchain into `ref/gcc/darwin-arm64/<version>/`.
* **linux** — [`ref/wch-evt/tools/fetch_wch_toolchain.py`](ref/wch-evt/tools/fetch_wch_toolchain.py)
  resolves the current signed URL through the official MounRiver API and accepts the archive
  only on a matching size and SHA-256. CI drives it through
  [`scripts/ci/provision-official.sh`](scripts/ci/provision-official.sh).

### EVT test corpus

`ref/wch-evt/` keeps its small parts in the repository — `tools/`, `patches/`, `tests/`,
`README.md`, `download-evt.sh`. The nine `Qingke*/` example-project directories, which are
the actual test corpus, are not tracked and have to be put in place:

```sh
scripts/fetch-evt.sh --url "$EVT_PACK_URL" --apply   # distribution URL, published with the release
scripts/fetch-evt.sh --file <local-pack> --apply     # a local copy of the same pack
```

The pack's SHA-256 is verified before unpacking, with no override — the corpus is an input
to a byte-equality gate. Alternatively, rebuild the tree package by package from the WCH
website: [`ref/wch-evt/download-evt.sh`](ref/wch-evt/download-evt.sh) looks each EVT archive
up in Chrome's download history, fetches it, and unpacks its `EVT/` directory into the
matching `Qingke*` directory.

**`--apply` runs [`ref/wch-evt/patches/apply.sh`](ref/wch-evt/patches/apply.sh) for you; if
you put the corpus in place any other way, run it yourself.** It is not optional. Without
it, projects such as `v4bc-pmp` do not build, and — the part that bites — `evt-golden.sh`
silently drops them: the manifest comes out at 246 gate rows instead of 274, with no
non-zero exit anywhere, so a comparison against that shrunken manifest reports a clean pass.
Reproduced in a fresh-clone experiment,
[phase10-opensource-readiness.md](analysis/toolchain/phase10-opensource-readiness.md) §3.1-B6.

## Build and verify

### Host prerequisites

macOS on Apple Silicon (darwin-arm64) for the darwin legs; the linux 15.2.0 leg runs in a
pinned `debian:bookworm` container. The literal build roots `/Users/mrs` and `/Users/wch`
must exist and be writable, which takes one `sudo` the first time: the official binaries
embed those build paths as literals (configure line, `DW_AT_comp_dir`, `SEARCH_DIR`), and
byte equality means reproducing them rather than normalising them away. The build scripts
symlink them onto the source tree under `tmp/`;
[`scripts/ci/setup-literal-paths.sh`](scripts/ci/setup-literal-paths.sh) is the CI-side
equivalent.

### Build

```sh
scripts/ci/prepare-sources.sh 15.2.0     # fetch upstream, verify pins, apply the series
BUILD_JOBS=16 scripts/build-toolchain-15.2.0.sh <source-tree>
```

Same shape for `12.2.0` and `8.2.0`. `BUILD_JOBS=16` is the project convention — the scripts
default to 8, and every recorded timing was taken at 16. 15.2.0 has a second leg,
[`scripts/build-toolchain-15.2.0-linux.sh`](scripts/build-toolchain-15.2.0-linux.sh), run
inside the container. Each build script installs the host executables it just built and then
injects the frozen official target libraries byte-for-byte.

### Verify

The recommended flow generates the manifest yourself, in your own checkout:

```sh
scripts/evt-golden.sh 15.2.0                                   # official package -> manifest
scripts/evt-compare.sh 15.2.0 <path-to-our-gcc-or-toolchain>   # our build -> compare
```

The reason is mechanical. Building with `-g` writes the absolute working directory into
`DW_AT_comp_dir`, so an object built under one path can never equal one built under another.
The manifests checked in under [analysis/golden/](analysis/golden/) therefore carry the
absolute cwd they were generated in and are a raw-drift diagnostic elsewhere, not a verdict;
generating golden and comparing in one run and one directory removes the variable entirely.

## CI

[`.github/workflows/toolchain-ci.yml`](.github/workflows/toolchain-ci.yml) runs the quick
byte gate on push and pull request in four legs — `linux-15-2-0`, `darwin-15-2-0`,
`darwin-12-2-0`, `darwin-8-2-0` — each provisioning the official package, preparing sources,
building, generating the manifest and comparing, all in one run. A checkout that does not carry the EVT corpus fetches the pack through `scripts/fetch-evt.sh`; set the `EVT_PACK_URL` repository variable (Settings → Secrets and variables → Actions → Variables) to the published pack URL. Because the verifier
derives its expected total from the manifest it is about to check, each leg also asserts the
absolute constants (274/274/274/242 gate rows, 9/9/9/8 projects) *before* comparing, which
is what makes a silently shrunken corpus fail instead of pass. The full EVT tree
deliberately stays out of hosted CI — every candidate runner ships 14 GB of disk in total
and every job is killed at 6 hours — and remains a local, operator-driven closing gate.

[`.github/workflows/release.yml`](.github/workflows/release.yml) triggers on a `v*` tag,
repeats the same build and gate, and publishes a reproducible tarball only if the gate is
green — the complete installed tree, including the byte-for-byte injected official target
libraries. Workflows are verified locally with `act` through
[`scripts/ci/act-verify.sh`](scripts/ci/act-verify.sh), which runs on a throwaway working
copy and asserts the host is left untouched. Design notes and capacity measurements:
[analysis/toolchain/phase7-ci-cd.md](analysis/toolchain/phase7-ci-cd.md).

## Repository map

| Path | Contents |
| --- | --- |
| [patches/](patches/) | The deliverable: three ordered patch series, `series` files, stable patch-ID ledgers, per-version READMEs |
| [scripts/](scripts/) | Build, extraction, golden/compare harness, patch export; [`scripts/ci/`](scripts/ci/) holds the CI entry points |
| [analysis/](analysis/) | Forensic, audit and closure reports, plus the golden manifests |
| [tests/](tests/) | Versioned cross-platform suites, such as the XW+LTO gate |
| [plans/](plans/) | Phase roadmap and per-version workflow task sheets |
| [ref/](ref/) | Reference inputs: EVT projects, ISA research, WCH manuals |
| `tmp/` | Upstream checkouts, build trees and phase evidence — gitignored, never distributed |

**Evidence-pointer convention.** Patch commit messages cite `tmp/...` paths. Those are
evidence coordinates on the development machine and do not travel with the repository: they
record where a measurement was taken, not something you can open in a clone. The conclusions
they support live in the `analysis/` reports, and the rv64 specification measurements are
copied into the tracked tree as
[phase9-rv64-spec-15.2.0.md](analysis/toolchain/phase9-rv64-spec-15.2.0.md) and
[phase9-rv64-spec-12.2.0.md](analysis/toolchain/phase9-rv64-spec-12.2.0.md).

## Glossary

* **EVT** — WCH's example project trees, one per QingKe generation; the test corpus, i.e.
  real vendor projects built with real vendor settings.
* **golden manifest** — a TSV of SHA-256 sums for every artifact the official toolchain
  produces from a corpus, in one run and one directory ([analysis/golden/](analysis/golden/)).
* **quick gate / full gate** — the 9-project regression set that must stay green after every
  change, versus the whole EVT tree that closes a version.
* **phase-N** — a unit of work in this project's roadmap; each has a task sheet in
  [plans/](plans/) and a closure or review report in `analysis/toolchain/`.
* **RC0x** — a repair round inside phase-3d (RC01 = the `.highcode` round, RC02 = implicit
  declarations, RC04 = `mret`).

## Key documents

* [AGENTS.md](AGENTS.md) — project rules, acceptance semantics, scope decisions
* [plans/roadmap.md](plans/roadmap.md) — every phase, its inputs, its verdict
* [analysis/toolchain/phase8-closure.md](analysis/toolchain/phase8-closure.md) — final gate
  numbers for all three versions
* [ref/wch-evt/README.md](ref/wch-evt/README.md) — the corpus and the nine selected projects

## Status

All three versions reach zero difference against their platform's official package
(2026-08): 15.2.0 on darwin-arm64 and linux-amd64, 12.2.0 and 8.2.0 on darwin.
