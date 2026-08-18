#!/usr/bin/env python3
"""Read and audit every byte of the mandated prior inputs and round-one outputs."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[4]
RUN = Path(__file__).resolve().parent
RESULTS = ROOT / "audit-report-f/followup/results"
EVIDENCE = RESULTS / "06b-chipid-errata-evidence"

MANDATED = [
    "qingke_processor.md",
    "isa-research-review-codex-r2.md",
    "isa-research-codex/findings.md",
    "isa-research-claude/qingke-custom-isa.md",
    "isa-research-claude/wch-custom-isa-reference.md",
    "isa-research-claude/wch-isa-usage-in-libraries.md",
    "isa-research-claude/wch-doc-instr-reg-findings.md",
    "isa-research-claude/wch-evt-pdf-instr-reg-index.md",
    "tmp/isa-research-codex/review-r2-independent.py",
    "tmp/isa-research-codex/review-r2-independent.json",
    "tmp/isa-research-codex/round2-binary-audit.json",
    "tmp/isa-research-codex/round2-xw-audit.json",
    "tmp/isa-research-codex/round2-doc-audit.json",
    "tmp/wch-evt/eval/manual-text/QingKeV2_Processor_Manual.txt",
    "tmp/wch-evt/eval/manual-text/QingKeV3_Processor_Manual.txt",
    "tmp/wch-evt/eval/manual-text/QingKeV4_Processor_Manual.txt",
    "tmp/wch-evt/eval/manual-text/QingKeV5_Processor_Manual.txt",
]

FIXED = [
    "06b-chipid-errata-codex.md",
    "06b-chipid-errata-inventory.tsv",
    "06b-chipid-errata-object-scan.tsv",
    "06b-chipid-errata-findings.tsv",
]

ABSOLUTE = re.compile(rb"/(?:Users|private|tmp|var)/[^\x00\t\r\n ]+")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def walk_scalars(value: Any, path: tuple[str, ...] = ()) -> Iterable[tuple[tuple[str, ...], Any]]:
    if isinstance(value, dict):
        for key in sorted(value):
            yield from walk_scalars(value[key], path + (str(key),))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from walk_scalars(item, path + (str(index),))
    else:
        yield path, value


def inspect_mandated() -> list[dict[str, Any]]:
    rows = []
    for relative in MANDATED:
        path = ROOT / relative
        data = path.read_bytes()
        row: dict[str, Any] = {
            "path": relative,
            "size_bytes": len(data),
            "line_count": len(data.splitlines()),
            "sha256": sha256_bytes(data),
            "absolute_path_tokens": len(ABSOLUTE.findall(data)),
        }
        if path.suffix == ".json":
            parsed = json.loads(data)
            scalars = list(walk_scalars(parsed))
            row.update(
                json_scalar_count=len(scalars),
                json_false_paths=[".".join(key) for key, value in scalars if value is False],
                json_statuses=sorted(
                    {str(value) for key, value in scalars if key and key[-1] == "status"}
                ),
                json_top_level=sorted(parsed) if isinstance(parsed, dict) else ["<array>"],
            )
        rows.append(row)
    return rows


def read_tsv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def inspect_evidence() -> dict[str, Any]:
    manifest_path = EVIDENCE / "evidence-manifest.tsv"
    fields, rows = read_tsv(manifest_path)
    errors: list[str] = []
    ids = Counter(row["evidence_id"] for row in rows)
    paths = Counter(row["path"] for row in rows)
    producer_ids = Counter(row["producer_command_id"] for row in rows)
    absolute_files = []
    for row in rows:
        target = EVIDENCE / row["path"]
        if not target.is_file():
            errors.append(f"missing:{row['path']}")
            continue
        data = target.read_bytes()
        if len(data) != int(row["size_bytes"]):
            errors.append(f"size:{row['path']}")
        if sha256_bytes(data) != row["sha256"]:
            errors.append(f"sha256:{row['path']}")
        if ABSOLUTE.search(data):
            absolute_files.append(row["path"])

    referenced = Counter()
    duplicate_within_field = []
    fixed_stats = {}
    manifest_hashes = Counter()
    for filename in FIXED[1:]:
        fixed_fields, fixed_rows = read_tsv(RESULTS / filename)
        fixed_stats[filename] = {"fields": fixed_fields, "rows": len(fixed_rows)}
        for row_number, row in enumerate(fixed_rows, 2):
            manifest_hashes[row.get("evidence_manifest_sha256", "")] += 1
            tokens = [token for token in row.get("evidence_ids", "").split(";") if token]
            if len(tokens) != len(set(tokens)):
                duplicate_within_field.append(f"{filename}:{row_number}")
            referenced.update(tokens)
    missing_refs = sorted(set(referenced) - set(ids))
    unreferenced = sorted(set(ids) - set(referenced))
    return {
        "manifest_fields": fields,
        "manifest_rows": len(rows),
        "manifest_sha256": sha256_bytes(manifest_path.read_bytes()),
        "duplicate_evidence_ids": sorted(key for key, count in ids.items() if count != 1),
        "duplicate_paths": sorted(key for key, count in paths.items() if count != 1),
        "producer_id_reuse_count": sum(count > 1 for count in producer_ids.values()),
        "file_errors": errors,
        "files_containing_absolute_paths": sorted(absolute_files),
        "fixed_tsv": fixed_stats,
        "manifest_hash_values_in_fixed_tsv": dict(sorted(manifest_hashes.items())),
        "missing_referenced_ids": missing_refs,
        "unreferenced_ids": unreferenced,
        "duplicate_ids_within_evidence_field": duplicate_within_field,
        "reference_counts": dict(sorted(referenced.items())),
    }


def inspect_round_one_tables() -> dict[str, Any]:
    inventory_fields, inventory = read_tsv(RESULTS / FIXED[1])
    findings_fields, findings = read_tsv(RESULTS / FIXED[3])
    scan_path = RESULTS / FIXED[2]
    lane_method = Counter()
    statuses = Counter()
    bad_methods = Counter()
    scan_rows = 0
    with scan_path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        scan_fields = list(reader.fieldnames or [])
        for row in reader:
            scan_rows += 1
            lane_method[(row["lane"], row["method"])] += 1
            statuses[row["status"]] += 1
            if row["method"] not in {"primary", "independent"}:
                bad_methods[row["method"]] += 1
    return {
        "inventory_fields": inventory_fields,
        "inventory_rows": len(inventory),
        "inventory_scope_class": dict(sorted(Counter(row["scope_class"] for row in inventory).items())),
        "inventory_failed_paths": [row["path_or_reference"] for row in inventory if row["scan_status"] == "failed"],
        "scan_fields": scan_fields,
        "scan_rows": scan_rows,
        "scan_lane_method": {f"{lane}|{method}": count for (lane, method), count in sorted(lane_method.items())},
        "scan_statuses": dict(sorted(statuses.items())),
        "scan_bad_methods": dict(sorted(bad_methods.items())),
        "findings_fields": findings_fields,
        "findings_rows": len(findings),
        "findings_levels": dict(sorted(Counter(row["evidence_level"] for row in findings).items())),
        "float_findings": [row["finding_id"] for row in findings if "float" in row["physical_path"].lower()],
    }


def main() -> None:
    result = {
        "mandated_inputs": inspect_mandated(),
        "round_one_evidence": inspect_evidence(),
        "round_one_tables": inspect_round_one_tables(),
    }
    output = RUN / "prior-complete-read-audit.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
