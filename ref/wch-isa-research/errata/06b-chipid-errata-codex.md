# 06b ChipID/revision and implicit-errata audit — independent round two

evidence_manifest_sha256: `5705ee8e29bf33d986b2ce880dfbd27b00076896d356a020c9f4d2002b12bc78`

## 1. Executive summary by finding, source site, and path

The second execution does **not** support a repository-wide “no hidden ChipID branch” conclusion. It independently closes three behavior classes and leaves all broader negatives bounded:

- Eight physical soft-WCHNET `eth_api.o` occurrences (two byte groups) read an unsigned halfword at `0x1ffff706`, mask `0xf0`, and select an extra Tx-descriptor recovery path for `0x30` or `0x80`. The path clears owner bit 31 after unsigned elapsed time `>99` or counter `>0x8000`. This is `ID-READ` + `ID-SELECT` and a defensive `WORKAROUND-CANDIDATE`; no material or experiment closes a silicon-defect cause.
- The two V317 float `eth_api.o` occurrences have no `GetChipID` and no `0x1ffff706` load. They are compile-time `STATIC-VARIANT-SPECIALIZATION`, correcting two false first-round ID-select findings.
- Three selected `IocHub.o` occurrences read 16 bytes at `0x1ffff7e0` for `chipType` 1..5 and feed registration/auth derivation. This is `ID-READ/ID-FLOW`, not an errata selector; invalid `chipType` uses zeros.
- CH587 ROM bytes at `0x40968` are a parcel-aligned `mcpy` positive control, but the jump-table recursive CFG does **not** reach that local block. The V407 manual’s operand-role prose conflicts with assembler/SDK/ROM convention; this is a document-erratum candidate, not silicon errata.

No `ERRATA-CONFIRMED` finding is made. Presence, available-map selection, and runtime applicability remain separate in every finding row.

## 2. Prompt, inputs, tools, evidence, Git, and claim ledger

Prompt SHA-256 is `ad8c8142887afa5ccb60f32af3d58e22991c7f1c6048570efb99255176dca1c8`. The immutable run root is `tmp/chipid-errata-06b/runs/20260804T045257Z-ad8c8142887a-00`; original baseline HEAD is `19ca29d15b4d5a06c75c7b59e10cc4eed17cfe1e`. The sanitized input manifest contains 31,908 original inputs totaling 8,889,818,628 bytes; every file was rehashed before finalization with no drift. The bundle records tool/script hashes and normalized command templates whose command IDs include the corresponding tool hash.

The Git scope control compares filtered porcelain-v2 state plus allowed-path-excluded worktree/index binary diffs. During this long audit, unrelated agents advanced HEAD to `12bb348a5b98e8918865921d8a4c59c6447e52ac` through ancestor commits touching 2500 paths (delta hash `743e5db38731b99efc00d11913cf8515e7eac517c29cbce00781bc3a034fbede`) and no authorized 06b result path. A further 2 unrelated worktree/index transition(s) were observed after that head change (chain hash `4c0a55ee0e232c0fce90f42108cc4f279c0bb00325d43dcd71389c16d66c771d`). Consequently the literal original status/diff hashes cannot match and are recorded as external transitions, not hidden. Each concurrency rebaseline was allowed only after proving ancestor lineage, no allowed-path overlap, and zero drift in all 31,908 analysis inputs; the selected head/status/worktree/index hashes then remain byte-identical through finalization. The run tree is excluded because it is an authorized, ignored execution location. Isolated staging/commit verification is performed after this report and is reported in the final receipt.

The complete prior/prompt correction ledger is `machine/claim-ledger.tsv`. Material corrections include independent-parser replacement, Linux GCC15 inclusion, ROM reachability/framing correction, CSR semantic correction, two float false-positive removals, and IoCHub narrowing.

## 3. Scope, members, hashes, and failures

Physical scope: 4,566 artifacts; 3,221 archives; 1,218 standalone objects; 680,924 logical archive-member occurrences; 682,142 member-or-standalone occurrences. Archive parsing found zero failures. EVT closure is 49 physical archives, 21 basenames, 23 archive-content groups, 848 member occurrences, and 381 unique member hashes.

The newly discovered `MRS_Toolchain_Linux_X64_V250` contribution is 435 archives plus 110 standalone objects. Source-set occurrence counts and scope counts are machine-bound in `machine/expected-scan-closure.json`. The MRS 2.5 package closure matches all 11,032 extracted non-directory target entries; the other 8,330 of 19,362 package entries are AppleDouble metadata sidecars, not silently omitted payloads.

The object ledger has 8,046,952 rows: 566,520 native occurrences ×14 required rows, 115,622 non-native occurrences ×1 scope row, and five ROMs ×10 rows. Parser failures are zero; semantic partials are retained rather than converted to negatives.

## 4. ID dictionary and document semantics

| source | class | audit interpretation |
|---|---|---|
| `0xF11/0xF12/0xF13/0xF14` | vendor/architecture/implementation/hart CSRs | raw standard-CSR discovery; hardware identity semantics only when the matching RM supports it |
| `0x301`, implementation CSR such as `0xFC0` | capability | capability source only if the read value controls behavior |
| `0x804`, `0xBC0` | chip-dependent vendor CSR | never transfer names/fields across chips (`INTSYSCR` vs `HW_POPDM_CTLR`; `CORECFGR` vs `CPU_RUN_CTLR`) |
| `0x1ffff706` | unknown system-info halfword field | observed WCHNET model/revision selector candidate; exact public field mapping unavailable |
| `0x1ffff7e0` | factory/system-info bytes | IoCHub identity/auth flow candidate; exact byte semantics and server use unresolved |
| DBGMCU/system-info addresses and API names | dynamic source seeds | discovery seeds, never a cap on all absolute/literal/relocation discovery |

Identity CSRs are visible in the checked X315 V1.1, V407 V1.1, and H417 V1.7 RMs; nine other listed RM versions do not contain them. This is document-version visibility only, not proof of hardware absence. H417 p1/p66 condition only memory protection/core-0 PMP on lot digit five, while p53–54 separately condition core-0 trigger registers; it is not a global lot switch for all PMP/debug capability.

## 5. All-family and all-variant result matrix

| family | physical artifacts | result strength |
|---|---:|---|
| WCHNET | 6 | 8 soft source→select positives; 2 float static-specialization occurrences |
| WCHUSB/other USB | 3 | no closed ID-select finding; limited primitive negative plus explicit semantic partials |
| RV3UFI/CHRV3UFI | 16 | no closed ID-select finding; limited primitive negative plus explicit semantic partials |
| UHSIF | 1 | no closed ID-select finding; limited primitive negative plus explicit semantic partials |
| ISP585 | 0 | 0 physical; 28 current project-link references, missing-referenced |
| IQMath | 50 | no closed ID-select finding; limited primitive negative plus explicit semantic partials |
| printf | 72 | no closed ID-select finding; limited primitive negative plus explicit semantic partials |
| printfloat | 72 | no closed ID-select finding; limited primitive negative plus explicit semantic partials |
| sh | 72 | no closed ID-select finding; limited primitive negative plus explicit semantic partials |
| shfloat | 72 | no closed ID-select finding; limited primitive negative plus explicit semantic partials |
| BLE | 10 | no closed ID-select finding; limited primitive negative plus explicit semantic partials |
| BLE ROM | 1 | 5 physical ROM payloads are separately scanned; count here is candidate-artifact label only |
| Mesh | 3 | no closed ID-select finding; limited primitive negative plus explicit semantic partials |
| Mesh ROM | 4 | no closed ID-select finding; limited primitive negative plus explicit semantic partials |
| LWNS | 4 | no closed ID-select finding; limited primitive negative plus explicit semantic partials |
| Touch | 11 | physical variants scanned; two missing referenced spellings; four old names are exclusions |
| IoCHub | 4 | 3 selected ID-READ/ID-FLOW positives; not workaround selection |
| Voice | 1 | no closed ID-select finding; limited primitive negative plus explicit semantic partials |
| Motor | 2 | no closed ID-select finding; limited primitive negative plus explicit semantic partials |
| Other WCH blob | 3652 | broad other-target/unknown-provenance bucket; not all 3,652 artifacts are proven WCH-owned; all native units were deep-scanned |
| generic runtime | 506 | candidate label only, not upstream attribution; retained in unknown-provenance native deep-scan scope |

Every physical artifact remains an inventory row even when bytes duplicate another path. The matrix’s “no closed finding” wording is deliberately not “no ID logic exists”: raw candidate discovery is complete for stated domains, while XW semantics, stripped interprocedural consumers, final-link GP/PCREL resolution, callbacks, and runtime domains remain partial where listed.

## 6. Positive controls and scanner independence

Two separately implemented archive/ELF/ROM parsers compare equal across 3,221 archives, 682,142 occurrences, 235,234 unique scan units, and five ROM payloads (zero field mismatches). Unique-unit candidate totals are: 4,601,786 address-form, 24,830 CSR, 22,625,459 literal, 2 relocation-source, 58,794 symbol/debug, and 462,014 XW-slot candidates. Canonical domain totals are 138,988,742 executable bytes, 180,778,878 allocatable bytes, and 27,364,764 relocation records.

Assembler fixture closure is 8,704 theoretical XW source cases and 8,704 emitted encodings for each executable GCC8/GCC12/GCC15 profile, with identical stream hash and zero invalid boundaries. GCC12/GCC15 emit `mcpy a0,a1,a2` bytes `0f70b560`; GCC8 rejects `mcpy` but, contrary to the prompt expectation, accepts all tested versioned `_xw` spellings. The D+C+XW march string is accepted while overlapping `c.fld` source is rejected as illegal.

Legacy XW boundary control covers 311 physical archives/187 build groups, 100 boundary-proven XW groups and 19,344 occurrences; profile counts are undeclared=121, xw2p0=4, xw2p2=62. Current scope including Linux is 385/259/136. Raw-slot anchors reproduce CH58xBLE=5,592, V317 soft/float=2,274, MESHROM=1,750, and MESH/libwchble=0. They are occurrence controls, not reachability proofs.

IQMath’s limited mcpy negative covers 50 physical archives/9 content groups (the old denominator was 40): exact LE, reverse display order, and every-byte masked operand scans are all zero. The EVT LUI controls remain 178 and 237, proving the scanner did not simply miss those objects.

## 7. Positive source → flow → select → sink chains

WCHNET pseudocode, preserving observed unsigned order:

```text
field = load_u16_le(0x1ffff706) & 0x00f0
counter = 0
loop:
    status = descriptor_status()
    if status >= 0: timer_anchor = 0; return descriptor_buffer
    if field == 0x30 || field == 0x80:
        if uint32(LocalTime - timer_anchor) > 99 || counter > 0x8000:
            descriptor.owner_bit31 = 0
    counter = counter + 1
    goto loop
```

The exact object sequence initializes the counter to zero and increments only after a failed descriptor test. The binary’s observed default for every other masked value is the ordinary polling path. A hardened “unknown ID → fail closed” policy would be an intentional non-equivalent engineering change and is not presented as the rewrite target.

IoCHub’s chain is `chipType range → 16 factory bytes (or zeros) → EncInit/Update/Final → registration/auth material → eight-byte local ID`. It has an identity sink but no closed low-level workaround sink.

## 8. WCHNET special analysis

All five soft physical WCHNET archives are selected by available link maps; duplicate `eth_api.o` ordinals are preserved, yielding eight source sites. Available-map selection has 1,122 soft rows. The five archives reduce to two soft object hashes with equivalent source/predicate/sink semantics.

V317 float has two physical member occurrences of one hash. Five real `.wvproj` project-link references exist, plus 15 exclusion rows; no available map selects float `eth_api.o`, while generated maps select soft. Therefore `selected_in_link=unknown`, not `no`. The first round’s two float ID-select rows are replaced by static-specialization rows.

The 12 checked WCHNET documents have zero exact hits for `GetChipID`, `0x1ffff706`, the `0x30/0x80` predicate, `LocalTime`, and `0x8000` under the recorded spellings. This is restricted to listed document hashes/query forms and does not establish that no vendor material documents the behavior elsewhere.

## 9. ROM special analysis

Five physical HEX payloads reduce to three byte groups and all independently normalize identically between parsers. Jump-table recursive walks prove only seeded code. Whole-run framing is explicitly mixed code/data and stops at reserved >=192-bit prefixes or truncation; all-even-address IALIGN prefix results are a boundary superset only.

For CH587, the local `0x40960..0x4096e` parcel starts are `0x40960,62,64,66,68,6c`; `mcpy` bytes at `0x40968` are `0f70b650`. Recursive JT reachability is false. The old `0x07f805fb@0x6b8d4` lies inside a 12-byte mixed-run parcel beginning `0x6b8d0` and is unclassified by recursive code analysis. The previous “actual 6/10/12/14-byte instructions” claim is withdrawn: recursive proven code contains 2/4-byte parcels; long mixed parcels do not prove executable instructions.

V407RM V1.1 p58 supplies a fixed layout and says no alignment restriction, but its operand-role prose conflicts with assembler output, four `ASM_MCPY(DA,SA,EA)` macros, and ROM convention `rs1=EA, rs2=SA, rs3=DA`. SA/DA are read-write macro operands and their completion values remain unresolved. Treating the prose literally could reverse source-end and destination roles, so this is a rewrite risk and document-erratum candidate.

## 10. Identity/configuration/static-specialization false positives

Eight EVT CSR-word occurrences are retained as a positive scanner control, but decoded operands show zero identity/capability hardware reads; they cannot support an ID claim. `mhartid`, implementation CSR, or lot capability controls would require downstream behavior selection before classification as an ID workaround.

IoCHub factory-byte flow is identity/authentication, not a recovery selector. H417 lot gating is documented capability differentiation, not evidence of hidden errata. V317 float is compile-time specialization, not runtime ID selection. Raw address constants, strings, custom-major fingerprints, LUI/AUIPC shapes, or `fld/fsd` presentation under missing attributes remain candidates until boundary, dereference, and flow close.

## 11. Documents, headers, EVT metadata, binary controls, and differences

The local WCH PDF corpus is 126 physical files/98 content groups with zero extraction failures, 1,541 page-hit rows, and 12 rendered pages visually reviewed. Thirteen schematic/PCB PDFs form 11 groups; pin/mux sanity tokens prove useful extracted text, but one Chinese PCB guide has zero text and remains a visual/OCR blind spot. Another 995 derived/current PDF paths (75 content groups) under broader tmp trees were provenance-excluded rather than treated as negative evidence.

Map/reference analysis enumerated 26,639 maps and 25,521 ELFs; 1,140 maps contain relevant selections and 1,646 selection rows. All five soft WCHNET, three IoCHub, and two MESHROM archives are selected in available maps. ISP585 has 28 current project-link rows but no physical archive. Touch has 12 uppercase and 8 lowercase missing-reference rows. Twenty old TKY rows are exclusion metadata. `CHRV3UFI.lib` has no newly verifiable current readable link row; a legacy `.wvproj` is opaque.

The original raw scanner hash matches the prompt’s expected hash and its NUL-delimited EVT smoke run exits zero, but it contributes no final negative: it lacks attributes, full framing, CFG/dataflow, and fail-closed format coverage.

## 12. Limited negatives and their denominators

The only negative claims are lane- and corpus-bounded:

- Primary and independent primitive candidate sets match exactly for all enumerated native object domains and five ROMs. `pass-no-hit` means no matching primitive in that exact domain/start set; it is never promoted to “no ID behavior.”
- IQMath has no tested `mcpy` encoding in 50 physical archives/9 byte groups under exact/reverse/masked scans; other ID mechanisms and unresolved XW behavior are outside that statement.
- The checked WCHNET documents have no queried hidden-predicate terms; unreviewed external versions, images/OCR, and different wording remain uncovered.
- No available map selects V317 float `eth_api.o`; this does not prove it is never linked.
- No `ERRATA-CONFIRMED` causal chain was found in the listed artifacts/documents. Static analysis and absent hardware experiments cannot prove no silicon workaround exists.

## 13. Rewrite ledger

An observationally equivalent rewrite of soft WCHNET must preserve the unsigned halfword read, `&0xf0`, equality values, counter initialization/check/increment order, unsigned LocalTime subtraction and wrap behavior, strict `>99`/`>0x8000`, descriptor owner-bit clear, ordinary polling default, and success timer clear. Unknown masked values follow the ordinary path in the binary.

IoCHub equivalence requires the inclusive chipType 1..5 test, 16-byte read order, zero-material default, identity transform order, caller field copies, and exposed eight-byte local ID. Float behavior must remain a separate static variant unless an intentional API/design change is documented. `mcpy` rewrites must follow observed SDK/ROM operand convention while isolating unresolved endpoint/writeback behavior; blindly following conflicting manual prose is unsafe.

Any hardened fallback, new timeout, extra fence, altered volatile order, or unknown-ID fail-safe is a non-equivalent engineering policy and must be reviewed separately.

## 14. Partial, failed, limitations, blind spots, and residual risks

No archive/ELF/HEX parser failed, but “zero failures” is not “complete semantics.” Partial categories are: XW candidate classification outside boundary-proven streams; missing/conflicting attributes; stripped objects; unresolved indirect calls/callbacks; weak/strong/archive resolution outside available maps; GP/PCREL final-link values; data/code ambiguity; ROM unclassified populated bytes; mixed-run long framing; unknown `0x1ffff706` field semantics; IoCHub server semantics; runtime hardware input domains; and absent silicon experiments.

The Linux GCC15 executables could not run on macOS, so its bytes were parsed independently but assembler execution controls use executable macOS GCC8/12/15 tools. PDF extraction is supplemented only by the 12 listed visual pages, not exhaustive image/OCR review. No new official material was downloaded. The bundle is compact: full canonical domains are gzip-compressed, while non-decisive full disassemblies and diagnostics remain in the immutable run.

All required semantic partials are rows in the object ledger, and all correction/limit categories are machine-readable. No partial is silently counted as a negative.

## 15. Reproduction, commands, scripts, manifest, and files

Run from the repository root:

```sh
python3 tmp/chipid-errata-06b/runs/20260804T045257Z-ad8c8142887a-00/r2_acceptance.py --run-root tmp/chipid-errata-06b/runs/20260804T045257Z-ad8c8142887a-00 --require-report
git diff --check -- audit-report-f/followup/results/06b-chipid-errata-codex.md audit-report-f/followup/results/06b-chipid-errata-inventory.tsv audit-report-f/followup/results/06b-chipid-errata-object-scan.tsv audit-report-f/followup/results/06b-chipid-errata-findings.tsv audit-report-f/followup/results/06b-chipid-errata-evidence
```

The bundle’s `machine/command-ledger.tsv` contains normalized recipes and tool-bound command IDs; `machine/tool-manifest.tsv` and `scripts/` freeze every decisive serializer/scanner. The fixed outputs are:

- `audit-report-f/followup/results/06b-chipid-errata-codex.md`
- `audit-report-f/followup/results/06b-chipid-errata-inventory.tsv`
- `audit-report-f/followup/results/06b-chipid-errata-object-scan.tsv`
- `audit-report-f/followup/results/06b-chipid-errata-findings.tsv`
- `audit-report-f/followup/results/06b-chipid-errata-evidence/`

Every bundle evidence ID is indexed below so manifest reference closure is independently checkable.

| evidence_id | path | role |
|---|---|---|
| `ev-f60f9848ae02e7d9e2f856c478c3ef120c48e7f50f521d41b9ab109b0a88b115` | `controls/build/build-context-summary.json` | build-context-control |
| `ev-49263ac35a084f4ab09c935a67c992a90d5a588bd58799aab8046a82764e3c7c` | `controls/build/linked-map-selection.tsv` | build-context-control |
| `ev-22d1fa8065b1d19463027a138262930049c8b90c16138d6e27c91528761fddff` | `controls/build/project-reference-ledger.tsv` | build-context-control |
| `ev-f20958ca1888d37d194177dc997955049b961722dff9246929d88f2a1bd47bea` | `controls/core/control-summary.json` | scanner-control |
| `ev-782de9dc53cb8c46ba7e7a90c7740b094f52035234c4777fb20ca1174a2f0f54` | `controls/core/evt-csr-control-occurrences.tsv` | scanner-control |
| `ev-e3f0b26d61eda30924adc4ec8be539899d50dea5f82f53cf6e7b6f763992b5ed` | `controls/core/evt-csr-control-summary.json` | scanner-control |
| `ev-ca97a9515711456202db2b5ad9b499f84ddc00da9c84348bda4023b76c640d12` | `controls/core/iqmath-control-summary.json` | scanner-control |
| `ev-57d8abd693560ba203eeccaf94db0406c053f7fa3499ab02b7f65d8f66e915db` | `controls/core/iqmath-mcpy-negative-control.tsv` | scanner-control |
| `ev-fe22096c78e6c46bee3fa2f0f3fa668adbdf748af38518f9902c8bc498e51740` | `controls/core/rawscan-smoke-summary.json` | raw-scanner-smoke |
| `ev-6933ddbd3346ebade8211ccfe379a1b7f5672c06d056f745398c2cf4812f673e` | `controls/core/rawscan-smoke.stderr` | raw-scanner-smoke |
| `ev-f204a3dfb8992bd6e0aaa062aad70f0085119d49a76216f3208910b46fb8e1bd` | `controls/core/rawscan-smoke.stdout` | raw-scanner-smoke |
| `ev-2b8d5a9fe7a40c00bf7f4e206f3ccf8c2565bdec93ad20eddf9c338fd087dabf` | `controls/core/scope-and-archive-closure.json` | scanner-control |
| `ev-8e39105e4cdcdeaeec22eeae9e1e2d72258e054a28fcf4d2088d7833b61c8dd1` | `controls/core/xw-and-archive-anchor-counts.json` | scanner-control |
| `ev-21de3e403c2caac9df503ebe18c8cd5ac01fd456a3fda205824072f57f9aded6` | `controls/core/xw-archive-profile-matrix.json` | scanner-control |
| `ev-8f728fc6dd4d6cd1b56def61ab3c5fba62fde22223c3d8d3aed9fabfe9922824` | `controls/documents/broad-pdf-exclusions.tsv` | document-control |
| `ev-f21a7a2c7fe1a8be2a00ce9b956d4133a0bd76de03353c9f11be5fee48f8f5d4` | `controls/documents/document-control-summary.json` | document-control |
| `ev-e5535eec413970b2ddf261b572c8fc2b8f40384b166f2a1c2fd3e37e9770259f` | `controls/documents/document-manifest.tsv` | document-control |
| `ev-160da1bc6e8faae09ca71f4bdff419248e7723bc4ef5ad1ad75d05eb86a340c4` | `controls/documents/document-query-hits.tsv` | document-control |
| `ev-9f29140a8bf8e81a29f387ebe88692fee4fe268f14aac28dbf41d46e2286e861` | `controls/documents/document-query-summary.json` | document-control |
| `ev-eedcf1613392743f66b4153d1e2530290b2cfe8543907ad837994a71d9ff2f96` | `controls/documents/h417-lot-page-excerpts.tsv` | document-control |
| `ev-f2f76feb0d274fdc2bca8c60b61b51d135bc1177d4b051c552377ef575842b9b` | `controls/documents/rm-register-visibility.tsv` | document-control |
| `ev-13c712a4b2972b61fd9635ca5d161d7888c3b85e23cee70aa0273503af46df3c` | `controls/documents/schematic-text-sanity.tsv` | document-control |
| `ev-55cf0b236240f211cb99fe1ec00f4b3f2d620c8b07f262dc5e73e76563daf67d` | `controls/documents/visual-page-review.tsv` | document-control |
| `ev-bf3521d50c4ba76530e049a31a5b227f0861133ec0c11f07da7adb9260f55332` | `controls/documents/visual-pages/h417-p1-001.png` | document-control |
| `ev-dea100588b20532420e7a6f946f59488f259e32bb79fef6434dfbf862b41b266` | `controls/documents/visual-pages/h417-p44-044.png` | document-control |
| `ev-66cfb5a760c7edaf9e03f1c10a30aecad971ec684c4cf32b4c541d02c13369ea` | `controls/documents/visual-pages/h417-pmp-066.png` | document-control |
| `ev-22d4f45b9743ac3af04313fed424c8f5a2dcd2a8588b445779762623955dc527` | `controls/documents/visual-pages/h417-trigger-053.png` | document-control |
| `ev-775d9d12c38c8f687ad14f5cebe2772e7bd476a44ac439997b8c8ac4ff24b87f` | `controls/documents/visual-pages/h417-trigger-054.png` | document-control |
| `ev-d22b3cf4bb2049cf610abbfa6275dd54a87bdc9c986a85b9a660ebff242700e1` | `controls/documents/visual-pages/qkv3-54.png` | document-control |
| `ev-a4a26e9ff8e397ab1534f4464852728818e37d3c6a96528c0d0296589a3b532c` | `controls/documents/visual-pages/qkv3-55.png` | document-control |
| `ev-b75389864e811648ea5290f53ee267f1bc6282e1c1ea78c404f856bd7b4aa28b` | `controls/documents/visual-pages/qkv3-56.png` | document-control |
| `ev-a4e01f7bac223842097957b8b8b83de8a5ac654efa353b72b0472f108c11b815` | `controls/documents/visual-pages/v407-057.png` | document-control |
| `ev-9e14da61356834bb6882d723690cc191ac7b36b2ac3a93f764c7fd5a92411670` | `controls/documents/visual-pages/v407-058.png` | document-control |
| `ev-b1e33e7f44a5bd778ae28f8415c13530f4367116e5bffc6d79c5d73b8b7e6535` | `controls/documents/visual-pages/wchnet-01.png` | document-control |
| `ev-62fc97c446b6e09238656a708e5706f439ffeadabb5936f0b18a955b5e6d5629` | `controls/documents/visual-pages/wchnet-02.png` | document-control |
| `ev-76a4cbbafc5e410136d2071ddc5c57241a646734f66a28560b67073442f2510b` | `controls/documents/wchnet-document-gap.tsv` | document-control |
| `ev-47ec52c0a9a9beb860e954442841444acc5ee84ada12db735535492853b9ef8f` | `controls/positive/disassembly/0b196fff0b9f666fc30cd4dcebe90ef299f1fed37fff6b66f460951515e494ca-GetChipID.txt` | positive-semantic-evidence |
| `ev-bd2eebed2fd00dc4e90c11fc8860fa2bb549c6bf101a250643fccc416898bda7` | `controls/positive/disassembly/0b196fff0b9f666fc30cd4dcebe90ef299f1fed37fff6b66f460951515e494ca-getTxBuffAddr.txt` | positive-semantic-evidence |
| `ev-269fc6efa960188298903ec4d445612b6c41b99a0b8f55b9f33a5c016b222a41` | `controls/positive/disassembly/0b196fff0b9f666fc30cd4dcebe90ef299f1fed37fff6b66f460951515e494ca-symbols.txt` | positive-semantic-evidence |
| `ev-560d2c3d0e8941a4dd9d6a9cf09ada0a0b6f5ae8bccf9eb6cb168389da86a563` | `controls/positive/disassembly/0c796a85a0123d5338803c1a144d3dbac76e906a6f652f73155cd6a8a6f28ac4-GetChipID.txt` | positive-semantic-evidence |
| `ev-da6be7eeb0f41fb55c2215ca23a49db16201a2879f1d6929121de1fcca500d8a` | `controls/positive/disassembly/0c796a85a0123d5338803c1a144d3dbac76e906a6f652f73155cd6a8a6f28ac4-getTxBuffAddr.txt` | positive-semantic-evidence |
| `ev-0d6f3c57c3380fdbef863e4d329fc36098f137ed60adf5fb368a74f59d55ce63` | `controls/positive/disassembly/0c796a85a0123d5338803c1a144d3dbac76e906a6f652f73155cd6a8a6f28ac4-symbols.txt` | positive-semantic-evidence |
| `ev-7eaf17f9e7cc16a92dd1322da1078e54db6206734c3aa5a13732b508efdbe9e0` | `controls/positive/disassembly/845388710f117bcbf29deeda982d7d480fa4482405d10a558489b9ab40b3546d-getTxBuffAddr.txt` | positive-semantic-evidence |
| `ev-acd897310d9840cb5dc31ddc8a748c3798b8525e00d19ed644ea716fffd01a46` | `controls/positive/disassembly/845388710f117bcbf29deeda982d7d480fa4482405d10a558489b9ab40b3546d-symbols.txt` | positive-semantic-evidence |
| `ev-3e9313abb197bfeb1656c9451447498ff4467893e7b3b441832e1efa9e46dc78` | `controls/positive/disassembly/b0698d11172d8f34a48b26652eb34b238f93959175a73305bddefa342eb2914c-IoCHub_CliConnAutoReg.txt` | positive-semantic-evidence |
| `ev-31fe4b83bd557f92bad6c4be4e46abc81d99df2ec53ef64cdd1a8dfedf06cab4` | `controls/positive/disassembly/b0698d11172d8f34a48b26652eb34b238f93959175a73305bddefa342eb2914c-WCHIOCHUB_GetLocalID.txt` | positive-semantic-evidence |
| `ev-6037347778423f13d1b68dc347b820da1896698f7af970c791c389b590ad37fb` | `controls/positive/disassembly/b0698d11172d8f34a48b26652eb34b238f93959175a73305bddefa342eb2914c-WCHIOCHUB_Init.txt` | positive-semantic-evidence |
| `ev-25a565582be78769deec2fe35be7dad3b3a166675c619414783b067d16d02073` | `controls/positive/disassembly/b0698d11172d8f34a48b26652eb34b238f93959175a73305bddefa342eb2914c-WCHIOCHUB_Start.txt` | positive-semantic-evidence |
| `ev-40ee95e9bca1be2b854e72658c3e6eeaf0106ebee5ac3830a4bdab372a8458fc` | `controls/positive/disassembly/b0698d11172d8f34a48b26652eb34b238f93959175a73305bddefa342eb2914c-symbols.txt` | positive-semantic-evidence |
| `ev-ee90c4c655a4f14af4f0e6e63b0e8adc5afb677940bf166e1432691ec18e487a` | `controls/positive/objects/0b196fff0b9f666fc30cd4dcebe90ef299f1fed37fff6b66f460951515e494ca.o` | positive-semantic-evidence |
| `ev-ad2661cad1394a9720655f9003b786d52bfdb4de12c76eb641ed63618f42be0d` | `controls/positive/objects/0c796a85a0123d5338803c1a144d3dbac76e906a6f652f73155cd6a8a6f28ac4.o` | positive-semantic-evidence |
| `ev-0b8ce347a9855fccea3ade49d8a35c2a946602e27e2bf399b6fd89fc0806f191` | `controls/positive/objects/845388710f117bcbf29deeda982d7d480fa4482405d10a558489b9ab40b3546d.o` | positive-semantic-evidence |
| `ev-65ae4c4ce588c36eff0e970103b9d53a343d9c49bae78dd10480b28ecaa2bf8a` | `controls/positive/objects/b0698d11172d8f34a48b26652eb34b238f93959175a73305bddefa342eb2914c.o` | positive-semantic-evidence |
| `ev-0c0b67bf847b36d95829f18efe6830c4dfe21408897aa699a80c30bf824d2b8d` | `controls/positive/positive-occurrences.tsv` | positive-semantic-evidence |
| `ev-b490efbfb3202b05ed209cf52a67b8beada9c110b5d435da900213bb87b035ec` | `controls/positive/positive-summary.json` | positive-semantic-evidence |
| `ev-3bdfe921f6d86d5d4f47731a2211bf16eddad979439af8e00faacde164d003e1` | `controls/positive/semantic-chain.json` | positive-semantic-evidence |
| `ev-b1739f51884e7dd161e630bb537fb2844cfbceabf2d68b2296ea275b3de46cc6` | `controls/rom/rom-code-parcels.tsv` | rom-control |
| `ev-7011196ef133b94117b531f4227d4b5f6b43836197a0ff808b4f19f109a77717` | `controls/rom/rom-control-summary.json` | rom-control |
| `ev-d9cbdf9aea8647a04e646c493ad22a40ed3bd2838a430633c6e1b508efc7b8bd` | `controls/rom/rom-fingerprints.tsv` | rom-control |
| `ev-4f81fa3399b76aa876b33c729c2305e8142cfa30eb394aed80906db17b9ba3f2` | `controls/rom/rom-header-ledger.tsv` | rom-control |
| `ev-ca58c808601ccb75eef2aec25b23750b2f5ca852351d279123b257dd30e04acb` | `controls/rom/rom-jt-seeds.tsv` | rom-control |
| `ev-a8f39349845c6e6639cd56a468ee344603820e1a80f7c3fab8d45bdbd7fdb68e` | `controls/rom/rom-length-prefix-candidates.tsv` | rom-control |
| `ev-85e5df7fe546da574f35e51df86b525492b172862a566304a1b8934bf6ce3e35` | `controls/tar/package-extracted-byte-closure.tsv` | package-closure |
| `ev-0241c4db7b5ad7333bdefa3fc03b9019815740c341957c18a6c1cbce924c347d` | `controls/tar/package-extracted-closure-summary.json` | package-closure |
| `ev-9dfc4479254643a25e318914c3de8910c8e831695592d36be4d637659a8bcf5c` | `controls/xw/fixtures/gcc12-mcpy.S` | xw-control |
| `ev-866892685851beaad33910fd99f97eb7b73f7626fa259c28b96115794ea85626` | `controls/xw/fixtures/gcc12-mcpy.bin` | xw-control |
| `ev-14bc91f7c3412eff30ce59428579424d173a26ecc1f2cf75caf2cb9e356a3d6e` | `controls/xw/fixtures/gcc12-mcpy.o` | xw-control |
| `ev-65e9e433d4a39ceadfd489aa64a11e536a1ed8aa69883a3da82a245ffd440415` | `controls/xw/fixtures/gcc8-mcpy-rejected.S` | xw-control |
| `ev-07a520c3a981a3242385ec27735c8a1aeea9214d9e3d7112cf12d20d2e55f482` | `controls/xw/xw-boundary-build-groups.tsv` | xw-control |
| `ev-e2f73605b308120bf14ef7cbcb0245bf23bb861167e78777357c6d59564140ec` | `controls/xw/xw-boundary-lines.tsv` | xw-control |
| `ev-dbff1b983457345517d1834d30d9117566dabc0b6cd4866f1657008f692528ff` | `controls/xw/xw-boundary-summary.json` | xw-control |
| `ev-687984dec6e32880289da5e645319f49122982d8fd2f155e93c2efc09cc0c539` | `controls/xw/xw-fixture-summary.json` | xw-control |
| `ev-b5045b61d8fd8279efd1f1a2f4309d327d8ed26ad8072d5b4850902de72a4d4c` | `controls/xw/xw-physical-diagnostics.tsv` | xw-control |
| `ev-960572f8b32e2d3780cbb99a83019e5ee45843c4724d743f7ded6672f3585df1` | `controls/xw/xw-source-encoding-map.tsv` | xw-control |
| `ev-3053e949adaa30b4fb9022186329a830d9665e53b51ed22d2249d49f65b4082e` | `controls/xw/xw-theoretical-encoding-set.tsv` | xw-control |
| `ev-c70b4bc27ca2baf2aecc73adca3d87efc221e0ef5c8c4f4119a86ebcdac21a04` | `input/analysis-input-manifest.tsv` | input-snapshot |
| `ev-175a7098da4d4651121c35102e9c496e1855254e54ff65565d8b850110d30ae1` | `input/prior-artifact-manifest.tsv` | input-snapshot |
| `ev-0a83540a81ed02fdf83813e73561931ec91d2762545f0340c7c469b246881a24` | `input/prior-complete-read-audit.json` | input-snapshot |
| `ev-aabab8beaee7acfe766030ed4108ca48afe149c4ab0027547eda11480146dd0b` | `input/prior-fixed-output-baseline.tsv` | input-snapshot |
| `ev-cd01fd44d691c6baff9714f822861ec4621c894c9214eebd9d61c6ac5df1d61f` | `input/prompt.sha256` | input-snapshot |
| `ev-9fafac8c2d4ab9f75fa7d270e748210fbc42fb30fd92db5506a1889f0f003014` | `machine/archive-summary.jsonl` | primary-machine-ledger |
| `ev-872ce366058fb436b3339445b94fad063ce2512d0282782ec9d87cfbc0c2d186` | `machine/canonical-unit-domain-records.jsonl.gz` | canonical-domain-set |
| `ev-38f8b48b3cbaab5c84261b5c4d3045ee5c84e69249a4684f9fe6c7d2363640b9` | `machine/claim-ledger.tsv` | deterministic-control-ledger |
| `ev-864a03ff5137af0c297106d99964333cb8ee53f4abcd6c5b05c36f93ba7e08a0` | `machine/command-ledger.tsv` | deterministic-control-ledger |
| `ev-28360a594e0e53977fef4ec688585cee10d8fbd53399868a1c5d8407d1292b94` | `machine/compact-set-summary.json` | canonical-domain-set |
| `ev-aa5c2f70ab906c45b799e4a2300a050b95738d1e7dd488010ffece857e352bb0` | `machine/comparison-mismatches.jsonl` | independent-comparison |
| `ev-c37400dc24d8a928a106d58af730ed4e41f2d8e9c825297a114214d034d03582` | `machine/comparison-summary.json` | independent-comparison |
| `ev-47e7899086c09aa024c61988014228c5e9152da1fa42e2f30f13609216726e02` | `machine/expected-scan-closure.json` | deterministic-control-ledger |
| `ev-92610759ec696a82a10fb65ec68ae599771468c91ff42e34b2c72f176c249ac4` | `machine/family-summary.tsv` | deterministic-control-ledger |
| `ev-c1548dd9b5bd39e27df115ea05dc7710eb12155c0a1a53574c3fee9d0e43f295` | `machine/git-scope-check.tsv` | deterministic-control-ledger |
| `ev-4b1f1a1df7d59db6886d042a4a7b87d8ce077ca230fff2a07ce1de00ad595ae6` | `machine/input-drift.tsv` | deterministic-control-ledger |
| `ev-a1b3b275f0edd9930452ce6565afa061d63a6a8a16650c27de88c04d1b3568f5` | `machine/lane-policy.json` | deterministic-control-ledger |
| `ev-9afbb8d8ea9da6aac95c63881208c45521ea7aa6a08255d9d4ea06d7ef493376` | `machine/primary-artifacts.jsonl` | primary-machine-ledger |
| `ev-4c3ec48e7e5d92661b60d5741ba6420997617aa8dfb16fe2f10c1b21b4facb62` | `machine/primary-counts.json` | primary-machine-ledger |
| `ev-99f76ff36c693247522ec1d9d48f8e545439b822a2dfdaacdf0ff4c25e310d0a` | `machine/tool-manifest.tsv` | deterministic-control-ledger |
| `ev-23bbcc077ddba6a49b989d8984032f097e2dee887d9821063d2b9a2edb8d95e3` | `scripts/baseline_r2.py` | reproduction-script |
| `ev-90dcdf138c4d4c1540b82191a961afb5667103e4de61a1651592fc8e15617a65` | `scripts/r2_acceptance.py` | reproduction-script |
| `ev-95395703696d30dc5ad7773c5861f5be2a182b66c45c03d8105ab19024b02250` | `scripts/r2_build_contexts.py` | reproduction-script |
| `ev-1b26ab0eb25a01383283880a96bd6d0f364a46d27c3c2c39c2209011356e3065` | `scripts/r2_compact_sets.py` | reproduction-script |
| `ev-e12f7f4da3c3fd71a5ecd622bfb89b1aca72aca5e7a2f2ad102c7c4225f51918` | `scripts/r2_compare.py` | reproduction-script |
| `ev-ddb270ff32d2177473c5637205e0bbc2f61c9ec5add0ff1173a06e8e0a10f187` | `scripts/r2_controls.py` | reproduction-script |
| `ev-58c0c6232eb4c84395daec93a55e6888b69d82ecad44f99f06d4d2e157debd12` | `scripts/r2_doc_controls.py` | reproduction-script |
| `ev-f6a13e029feb10c8ba97e4ea777fe8d551c214e45b4439789271e3fc404600b1` | `scripts/r2_docs.py` | reproduction-script |
| `ev-e31228d3e9b31d58ed8332271aff0eb7a53474eb51bec26c144622613cc9121f` | `scripts/r2_finalize.py` | reproduction-script |
| `ev-f24f8ed866e3e1da94bae2e864d9f327a2232667fee459010703391789e8ceb5` | `scripts/r2_independent.py` | reproduction-script |
| `ev-161d11eb19f38936b80a37a0f3761f75a641ec0d334516ec870e3682bf1194a2` | `scripts/r2_positive_evidence.py` | reproduction-script |
| `ev-4825c876ce9e202dfccde199c3bf894c5c6b2e31af6ef57269534e65f97a9fc2` | `scripts/r2_primary.py` | reproduction-script |
| `ev-5c44b974edad7d1f0aea81e958c874030d5ef1276e8749060a4ca2c1f0076d42` | `scripts/r2_rom_control.py` | reproduction-script |
| `ev-04f6ad815acffeeff123be84c9f6c61e1ebe887a5e97208e8a43cad5524793e9` | `scripts/r2_tar_closure.py` | reproduction-script |
| `ev-fd6bafe07ecd1af90d1430c97065aabdc5293b53c1e6f198f75c8974999e21b0` | `scripts/r2_xw_boundaries.py` | reproduction-script |
| `ev-f99cca0f9b448ec0fd92659f12c45898b5a25917cf767dfbf45f488b18161b41` | `scripts/r2_xw_fixture.py` | reproduction-script |
| `ev-159b07755bef9c8070a1c5d944c7c95b57b06c6cf2615d9e4ecfabe6193424ba` | `scripts/rawscan.py` | reproduction-script |
| `ev-6d9022a795ed7a4fe78404105fc40b5e951dc0a2cfc13d1c1463e569a2b45a09` | `scripts/review_prior_r2.py` | reproduction-script |
