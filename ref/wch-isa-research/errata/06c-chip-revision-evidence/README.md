# 06c CHIPID / revision / errata evidence

This bundle supports `../06c-chip-revision-errata.md`.  Its central invariant is
that a selector is called revision-sensitive only when it reads the vendor
`REVID` half of CHIPID (in the reviewed families, the wildcard nibble at full
CHIPID bits `[7:4]`) and can change behavior within one chip model.  Reads from
`DEVID`, package/model subfields, compile-time variants, core revision CSRs, and
printed package lot codes remain separate classes.

The bundle contains:

- field-layout and selector-classification tables;
- twelve same-chip runtime revision findings;
- focused, line-numbered SDK excerpts and WCH disassembly;
- five visually reviewed PDF page renders plus Poppler text extracts;
- model-domain closure for the WCHNET `0x30/0x80` predicate;
- representative successful V317/H417 builds; and
- hashes for every source input and every bundled artifact.

The committed PNG pages were rendered with Poppler and visually inspected, as
required by the PDF review workflow.  Text extraction alone was not used to
accept page layout or wording.

Reproduce from the repository root (the frozen `tmp/wch-evt` corpus and WCH
toolchain must be present):

```sh
python3 audit-report-f/followup/results/06c-chip-revision-evidence/scripts/generate_evidence.py
python3 audit-report-f/followup/results/06c-chip-revision-evidence/scripts/acceptance.py
```

The generator is deterministic for fixed inputs.  `evidence-manifest.tsv`
binds every bundle file except itself; the acceptance script checks that exact
file closure and independently re-hashes the recorded source inputs.
