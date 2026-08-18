# Phase 4 S2 vanilla difference inventory

This inventory freezes the first full comparison before any WCH ISA behavior
patch was applied.  Its compiler sources are GCC HEAD `65fe1a3a…` and
binutils HEAD `dc5b5e89…`; both trees were clean.  Exact logs are under
`tmp/phase4-evidence/s2-first-compare/`.

## Full gate result

`scripts/evt-compare.sh 12.2.0 <S2-application>` returned 1:

```text
SUMMARY gate_pass=1 gate_total=274 gate_fail=273 aux_match=27 aux_diff=250
```

The only passing gate artifact was `v3a-gpio/obj/GPIO_Toggle.bin`; that
project does not request XW.  Its other gate artifacts already differed, so
the pass is a useful code-byte anchor rather than evidence of whole-project
parity.

As a control, the same current manifest and work paths rebuilt with the
official 12.2.0 toolchain returned 0 with `274/274` gate and `277/277` aux
matches.  Evidence:
`tmp/phase4-evidence/s2-golden-stability-final/compare.{stdout,stderr,rc}`.

## First blocking difference: bare XW attribute acceptance

Every project that reaches an XW compile fails when vanilla GCC emits an
unversioned `.attribute arch, ..._xw` and vanilla binutils 2.38 reparses it:

```text
Error: x ISA extension `xw' must be set with the versions
...s:3: Error: x ISA extension `xw' must be set with the versions
```

This is not a driver spelling problem: official 12.2 accepts both concatenated
and underscore bare XW, canonicalizes them to `xw1p0`, and preserves explicit
versions.  Independent official GCC and GAS probes are frozen in
`tmp/phase4-evidence/s1-official/{bare-xw.tsv,diagnostics.tsv}`.  At this S2
measurement point the working hypothesis was to register XW default version
**1.0** in both GCC 12.2 and binutils 2.38.  Later direct `-S` probes refined
that hypothesis: official GCC deliberately preserves unversioned `_xw`, while
GAS alone normalizes it to `xw1p0` in object attributes.  The final series
therefore leaves GCC's generic lowercase vendor-X parser unversioned and
implements the 1.0 default only in binutils.  The 15.2 default 2.0/2.2 is not
copied.

## Known next differences, already bounded by official S1 probes

These are not inferred from 15.2 patches; each has a direct 12.2 official
fixture and will be revalidated only after the preceding blocker is removed.

| Surface | Official 12.2 behavior | Expected implementation locus |
|---|---|---|
| XW compressed byte/halfword loads/stores | eight explicit mnemonics and eight ordinary aliases have text `88218a2188a18aa10880288048806880`; initial-XW/RVC gate is sticky | binutils opcode table, operand parser, ordinary alias ordering, candidate gate |
| custom32 instructions | `mcpy`, `wexti`, `mrslu`, `mrsl` accepted even at `rv32i`; text `0f70b5600b85c5180b85c51c0b85c51e` | binutils opcode/operand tables |
| WCH fast interrupt | exact `WCH-Interrupt-fast` uses hardware-saved frame and `mret`; typo warns and returns normally | GCC RISC-V interrupt attribute/frame hooks |
| unsupported lowercase X extension | GCC `-S` accepts `_xq`, GAS rejects; full `-pipe -c` yields the official two-line GAS diagnostic | likely already upstream-12 behavior; probe before changing |
| uppercase `_XW` | GCC rejects with `unsupported ISA subset 'X'` | likely already upstream-12 behavior; preserve |
| XW/ZCD and RVC diagnostics | 2.38 text has no newer `extension ... required` suffix; option/attribute resets retain initial XW eligibility | binutils candidate state, with official 12.2 `.l` text only |
| GAS mapping symbol | always plain `$x`; arch/version lives in attributes | no 15.2 versioned-mapping patch |
| generated attributes | measured only after successful objects exist | classify after XW acceptance; do not pre-apply 15.2 suppression |

## Explicitly excluded blind ports

- No 15.2 `xw2p0`/`xw2p2` default is applicable; 12.2 requires `xw1p0` and
  plain `$x` mapping symbols.
- No 15.2 GAS diagnostic expectation is applicable; binutils 2.38 official
  diagnostics are separately frozen.
- No attribute-suppression, mapping-symbol, or unknown-extension typo patch is
  applied until a post-XW full comparison or an exact 12.2 probe demonstrates
  that difference.
- Target libraries remain official injected payload and are never rebuilt or
  patched.
