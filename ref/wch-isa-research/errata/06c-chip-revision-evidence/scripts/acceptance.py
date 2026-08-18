#!/usr/bin/env python3
"""Fail-closed acceptance checks for the 06c revision/errata deliverables."""
from __future__ import annotations

import csv
import hashlib
import json
import pathlib
import re
import subprocess


def find_repo(start: pathlib.Path) -> pathlib.Path:
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("repository root not found")


SCRIPT = pathlib.Path(__file__).resolve()
REPO = find_repo(SCRIPT.parent)
BUNDLE = SCRIPT.parent.parent
REPORT = BUNDLE.parent / "06c-chip-revision-errata.md"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
EVIDENCE_ID = re.compile(r"^ev-[0-9a-f]{64}$")


def sha_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_tsv(name: str, expected_header: list[str]) -> list[dict[str, str]]:
    path = BUNDLE / name
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if reader.fieldnames != expected_header:
            raise AssertionError(f"{name}: header mismatch: {reader.fieldnames!r}")
        rows = list(reader)
    if not rows:
        raise AssertionError(f"{name}: no rows")
    for lineno, row in enumerate(rows, 2):
        if None in row or any(value is None or value == "" for value in row.values()):
            raise AssertionError(f"{name}:{lineno}: empty or extra field")
        if row.get("schema_version") != "1":
            raise AssertionError(f"{name}:{lineno}: schema version")
    return rows


def check_manifest() -> dict[str, dict[str, str]]:
    rows = read_tsv(
        "evidence-manifest.tsv",
        ["schema_version", "evidence_id", "path", "role", "size_bytes", "sha256"],
    )
    listed: dict[str, dict[str, str]] = {}
    previous: bytes | None = None
    ids: set[str] = set()
    for row in rows:
        path_text = row["path"]
        key = path_text.encode("utf-8")
        if previous is not None and key <= previous:
            raise AssertionError("manifest paths are not strictly UTF-8-byte sorted")
        previous = key
        pure = pathlib.PurePosixPath(path_text)
        if pure.is_absolute() or ".." in pure.parts or path_text == "evidence-manifest.tsv":
            raise AssertionError(f"unsafe/recursive manifest path: {path_text}")
        if not EVIDENCE_ID.fullmatch(row["evidence_id"]) or row["evidence_id"] in ids:
            raise AssertionError(f"bad/duplicate evidence id: {row['evidence_id']}")
        ids.add(row["evidence_id"])
        if not HEX64.fullmatch(row["sha256"]):
            raise AssertionError(f"bad manifest hash: {path_text}")
        target = BUNDLE.joinpath(*pure.parts)
        if not target.is_file():
            raise AssertionError(f"manifest target missing: {path_text}")
        if target.stat().st_size != int(row["size_bytes"]) or sha_file(target) != row["sha256"]:
            raise AssertionError(f"manifest target drift: {path_text}")
        listed[path_text] = row
    actual = {
        path.relative_to(BUNDLE).as_posix()
        for path in BUNDLE.rglob("*")
        if path.is_file() and path.name != "evidence-manifest.tsv"
    }
    if actual != set(listed):
        raise AssertionError(f"manifest closure mismatch: unlisted={sorted(actual-set(listed))[:4]} missing={sorted(set(listed)-actual)[:4]}")
    return listed


def check_source_hashes() -> int:
    rows = read_tsv(
        "source-hashes.tsv",
        ["schema_version", "path", "size_bytes", "sha256"],
    )
    paths: set[str] = set()
    for row in rows:
        if row["path"] in paths:
            raise AssertionError(f"duplicate source path: {row['path']}")
        paths.add(row["path"])
        target = REPO / row["path"]
        if not target.is_file():
            raise AssertionError(f"source missing: {row['path']}")
        if target.stat().st_size != int(row["size_bytes"]) or sha_file(target) != row["sha256"]:
            raise AssertionError(f"source drift: {row['path']}")
    return len(rows)


def check_png(path: pathlib.Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR" or len(data) < 100_000:
        raise AssertionError(f"invalid/tiny PNG: {path}")
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    if width < 1000 or height < 1000:
        raise AssertionError(f"unexpected render dimensions: {path}:{width}x{height}")
    return width, height


def require_text(path: pathlib.Path, markers: list[str]) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    for marker in markers:
        if marker not in text:
            raise AssertionError(f"missing marker {marker!r}: {path}")


def main() -> None:
    manifest = check_manifest()
    source_count = check_source_hashes()

    layout = read_tsv(
        "chipid-layout.tsv",
        ["schema_version", "source_api_or_load", "address_or_expression", "full_chipid_bits", "semantic_field", "selector_example", "conclusion", "source_anchor"],
    )
    if len(layout) != 6:
        raise AssertionError("chipid layout row count")
    wchnet_layout = [row for row in layout if row["source_api_or_load"] == "WCHNET predicate"]
    if len(wchnet_layout) != 1 or wchnet_layout[0]["full_chipid_bits"] != "23:20" or "not same-chip revision" not in wchnet_layout[0]["conclusion"]:
        raise AssertionError("WCHNET field classification not closed")

    findings = read_tsv(
        "revision-findings.tsv",
        ["schema_version", "finding_id", "device_scope", "selector_field", "affected_revisions", "behavior_delta", "classification", "errata_status", "evidence_strength", "source_group", "source_anchor"],
    )
    expected_findings = {f"REV-WCH-{number:03d}" for number in range(1, 13)}
    if {row["finding_id"] for row in findings} != expected_findings:
        raise AssertionError("revision finding closure")
    if any(row["classification"] not in {"REVISION-WORKAROUND-CANDIDATE", "REVISION-COMPATIBILITY"} for row in findings):
        raise AssertionError("unexpected runtime revision classification")
    if any("ERRATA-CONFIRMED" in row["classification"] for row in findings):
        raise AssertionError("source-only runtime path promoted to confirmed erratum")

    selectors = read_tsv(
        "selector-classification.tsv",
        ["schema_version", "group_id", "package_or_family", "selector_expression", "full_chipid_bits", "physical_sites", "classification", "revision_sensitive", "rationale", "representative_path"],
    )
    by_group = {row["group_id"]: row for row in selectors}
    if by_group["SEL-WCHNET"]["classification"] != "MODEL-SELECT" or by_group["SEL-WCHNET"]["revision_sensitive"] != "no":
        raise AssertionError("WCHNET selector regression")
    for key in ("SEL-V317-CAN", "SEL-V317-TIM", "SEL-V317-ETH", "SEL-H417-CAN", "SEL-H417-GPIO-REV", "SEL-H417-ADC", "SEL-H417-EMMC", "SEL-H417-PWR", "SEL-H417-USBSS"):
        if by_group[key]["classification"] != "REVISION-SELECT" or by_group[key]["full_chipid_bits"] != "7:4":
            raise AssertionError(f"revision selector regression: {key}")
    for key in ("SEL-H417-GPIO-MODEL", "SEL-V407-GPIO", "SEL-V006-SLTIM", "SEL-X315-GPIO"):
        if by_group[key]["classification"] != "REVISION-INSENSITIVE-MODEL-SELECT":
            raise AssertionError(f"revision masking regression: {key}")

    model_rows = read_tsv(
        "wchnet-model-domain.tsv",
        ["schema_version", "archive_scope", "documented_model_families", "full_chipid_23_20_values", "predicate_0x30_reachable", "predicate_0x80_reachable", "classification"],
    )
    if len(model_rows) != 5:
        raise AssertionError("WCHNET archive-domain count")
    domains = {row["archive_scope"]: row for row in model_rows}
    if domains["QingkeV4F_CH32V317_EVT"]["predicate_0x30_reachable"] != "yes: V303":
        raise AssertionError("V317 package domain")
    if domains["QingkeV3V_CH32V407_EVT"]["predicate_0x30_reachable"] != "no" or domains["QingkeV5F_CH32H417_EVT"]["predicate_0x80_reachable"] != "no":
        raise AssertionError("V407/H417 unreachable branch domain")

    documents = read_tsv(
        "document-review.tsv",
        ["schema_version", "document_id", "path", "sha256", "version", "pdf_pages", "pdf_page", "condition", "documented_behavior", "classification", "runtime_revid_mapping", "visual_evidence"],
    )
    document_ids = {row["document_id"] for row in documents}
    for required in ("DOC-REV-001", "DOC-REV-002", "LOT-H417-001", "LOT-FV3X-001", "LOT-V407-001", "LOT-V003-001"):
        if required not in document_ids:
            raise AssertionError(f"document finding missing: {required}")
    h417_ibi = next(row for row in documents if row["document_id"] == "LOT-H417-001")
    if h417_ibi["classification"] != "DOCUMENTED-LOT-ERRATUM" or "did not map" not in h417_ibi["runtime_revid_mapping"]:
        raise AssertionError("lot/revision separation for H417 IBI")
    for row in documents:
        if row["document_id"].startswith("LOT-") and "not mapped" not in row["runtime_revid_mapping"] and "did not map" not in row["runtime_revid_mapping"]:
            raise AssertionError(f"lot row lacks REVID separation: {row['document_id']}")

    visuals = read_tsv(
        "visual-review.tsv",
        ["schema_version", "document_id", "pdf_page", "printed_page", "image", "review_result"],
    )
    if len(visuals) != 5:
        raise AssertionError("visual review row count")
    dimensions = {row["image"]: check_png(BUNDLE / row["image"]) for row in visuals}

    require_text(BUNDLE / "document-excerpts/DOC-REV-001-p261.txt", ["CHIPID 倒数第二位为 1", "上拉输入"])
    require_text(BUNDLE / "document-excerpts/LOT-H417-001-p375.txt", ["批号倒数第五位小于 3", "该位不生效", "EVT 例程"])
    require_text(BUNDLE / "document-excerpts/LOT-FV3X-001-p148.txt", ["不得超过 64K 边界", "不得超过 128K 边界"])
    require_text(BUNDLE / "source-excerpts/field-v317-dbgmcu.txt", ["DBGMCU_GetREVID", "0x1FFFF704", ">> 16", "0x303305x4", "0x3170B5X8"])
    require_text(BUNDLE / "source-excerpts/field-v205-dbgmcu.txt", ["DBGMCU_GetREVID", "DBGMCU_GetDEVID", "CH32V205CCT-0x205205x0", "CH32V205VCT-0x205005x0"])
    require_text(BUNDLE / "source-excerpts/h417-gpio-revision-and-model.txt", ["0x000000F0", "~0x000000F0", "SWPMI->OR"])
    require_text(BUNDLE / "source-excerpts/v317-eth-10m-revision.txt", ["(ChipId & 0xf0) == 0x20", "(ChipId & 0xf0) == 0x10", "ETH_DMARxDesc_OWN"])

    for disassembly, marker in (
        ("disassembly/v317-CAN_Init.txt", "<CAN_Init>"),
        ("disassembly/v317-TIM_TimeBaseInit.txt", "<TIM_TimeBaseInit>"),
        ("disassembly/h417-CAN_Init.txt", "<CAN_Init>"),
        ("disassembly/h417-GPIO_IPD_Unused.txt", "<GPIO_IPD_Unused>"),
        ("disassembly/v317-10m-ETH_Init-linked.txt", "<ETH_Init>"),
        ("wchnet-binary/0b196fff0b9f666fc30cd4dcebe90ef299f1fed37fff6b66f460951515e494ca-GetChipID.txt", "1ffff706"),
    ):
        require_text(BUNDLE / disassembly, [marker])

    builds = read_tsv(
        "build-evidence.tsv",
        ["schema_version", "build_id", "build_directory", "build_status", "exit_code", "artifact", "artifact_sha256", "link_state", "relevant_symbols"],
    )
    if {row["build_id"] for row in builds} != {"BUILD-V317-ETH", "BUILD-V317-PERIPH", "BUILD-H417-CAN"}:
        raise AssertionError("build evidence closure")
    for row in builds:
        if row["exit_code"] != "0" or not any(word in row["build_status"].lower() for word in ("pass", "success")):
            raise AssertionError(f"build failed/not accepted: {row['build_id']}:{row['build_status']}:{row['exit_code']}")
        artifact = REPO / row["artifact"]
        if sha_file(artifact) != row["artifact_sha256"]:
            raise AssertionError(f"build artifact drift: {row['build_id']}")

    callsites = json.loads((BUNDLE / "callsite-summary.json").read_text(encoding="utf-8"))
    if callsites["DBGMCU_GetCHIPID"]["files"] != 980 or callsites["DBGMCU_GetCHIPID"]["text_occurrences"] < 900:
        raise AssertionError("whole-EVT CHIPID scan closure")
    if callsites["DBGMCU_GetREVID"]["behavior_uses_outside_declaration_definition"] != 0 or callsites["DBGMCU_GetDEVID"]["behavior_uses_outside_declaration_definition"] != 0:
        raise AssertionError("unexpected direct field API users")
    groups = callsites["behavior_groups"]
    expected_counts = {
        "v317_eth_revision_files": 20,
        "h417_adc_revision_files": 6,
        "h417_emmc_revision_files": 3,
        "h417_usbss_revision_driver_files": 3,
    }
    if {key: len(groups[key]) for key in expected_counts} != expected_counts:
        raise AssertionError("behavior-group copy counts")
    if callsites["local_pdf_corpus"] != {"physical_files": 126, "content_hash_groups": 98, "extraction_failures": 0}:
        raise AssertionError("PDF corpus closure")

    search = json.loads((BUNDLE / "search-summary.json").read_text(encoding="utf-8"))
    if "no checked official source mapped" not in search["result"] or "not a universal absence claim" not in search["negative_claim_limit"]:
        raise AssertionError("bounded official-source negative missing")

    require_text(REPORT, [
        "06b 结论修正",
        "MODEL-SELECT",
        "full CHIPID[23:20]",
        "full CHIPID[7:4]",
        "DOCUMENTED-LOT-ERRATUM",
        "REVISION-WORKAROUND-CANDIDATE",
        "打印批号",
        "不得等同于运行时 REVID",
    ])
    subprocess.run(["git", "diff", "--check", "--", str(REPORT.relative_to(REPO)), str(BUNDLE.relative_to(REPO))], cwd=REPO, check=True)

    receipt = {
        "status": "pass",
        "manifest_files": len(manifest),
        "source_inputs_rehashed": source_count,
        "runtime_revision_findings": len(findings),
        "document_findings": len(documents),
        "visual_pages": dimensions,
        "builds": {row["build_id"]: row["build_status"] for row in builds},
        "critical_correction": "WCHNET selector is DEVID/model full CHIPID[23:20], not REVID full CHIPID[7:4]",
    }
    print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
