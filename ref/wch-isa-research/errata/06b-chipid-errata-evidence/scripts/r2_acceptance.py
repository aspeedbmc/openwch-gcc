#!/usr/bin/env python3
"""Fail-closed acceptance checks for the round-two 06b fixed deliverables.

This verifier never writes into the evidence bundle or fixed result paths.  It
streams the multi-gigabyte object ledger, checks the exact schemas and closure
invariants, and writes only a deterministic receipt below the selected run
root.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pathlib
import re
import subprocess
from collections import Counter


INVENTORY_HEADER = [
    "schema_version", "source_set", "scope_class", "path_or_reference", "family",
    "role", "physical_present", "target_chip", "build_context", "sha256",
    "normalized_sha256", "parent_package_sha256", "file_format", "member_occurrences",
    "byte_group_id", "byte_representative_path", "scan_status", "evidence_ids",
    "evidence_manifest_sha256",
]
SCAN_HEADER = [
    "schema_version", "scan_row_id", "physical_path", "logical_member_order",
    "member_name", "same_name_ordinal", "scan_unit_sha256", "semantic_context_id",
    "resolution_context_id", "lane", "method", "tool_profile_id", "domain_kind",
    "domain_units", "domain_set_sha256", "candidate_starts", "candidate_start_set_sha256",
    "boundary_known_semantic_unresolved_units", "boundary_ambiguous_units",
    "candidate_count", "status", "representative_scan_row_id", "hit_ids", "evidence_ids",
    "evidence_manifest_sha256",
]
FINDING_HEADER = [
    "schema_version", "finding_id", "source_scan_row_id", "physical_path", "build_context_id",
    "member_section_offset", "semantic_context_id", "source", "access_width_and_field",
    "transform_and_predicate", "path_a", "path_b", "observed_default", "evidence_level",
    "purpose_and_workaround", "reachability_triplet", "unresolved", "evidence_ids",
    "evidence_manifest_sha256",
]
MANIFEST_HEADER = [
    "schema_version", "evidence_id", "path", "role", "size_bytes", "sha256",
    "producer_command_id", "required_by",
]
HEX64 = re.compile(r"^[0-9a-f]{64}$")
ID64 = re.compile(r"^[a-z][a-z0-9-]*-[0-9a-f]{64}$")
ALLOWED = (
    "audit-report-f/followup/results/06b-chipid-errata-codex.md",
    "audit-report-f/followup/results/06b-chipid-errata-inventory.tsv",
    "audit-report-f/followup/results/06b-chipid-errata-object-scan.tsv",
    "audit-report-f/followup/results/06b-chipid-errata-findings.tsv",
    "audit-report-f/followup/results/06b-chipid-errata-evidence",
)


def sha_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def check_header(path: pathlib.Path, expected: list[str]) -> None:
    with path.open("r", encoding="utf-8", newline="") as stream:
        actual = next(csv.reader(stream, delimiter="\t"))
    if actual != expected:
        raise AssertionError(f"header mismatch: {path.name}: {actual!r}")


def split_ids(value: str) -> list[str]:
    if value == "not-applicable":
        return []
    return value.split(";")


def filtered_status(data: bytes, run: pathlib.Path, repo: pathlib.Path) -> bytes:
    prefixes = list(ALLOWED) + [run.relative_to(repo).as_posix()]
    return b"".join(
        line for line in data.splitlines(keepends=True)
        if not any(prefix in line.decode("utf-8", "surrogateescape") for prefix in prefixes)
    )


def validate_scope_state(run: pathlib.Path, repo: pathlib.Path) -> dict[str, str]:
    baseline_path = run / "concurrency-rebaseline.json"
    if baseline_path.exists():
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    else:
        initial_status = filtered_status((run / "initial-git-status.porcelain-v2").read_bytes(), run, repo)
        baseline = {
            "mode": "original-baseline",
            "head": (run / "initial-git-head").read_text().strip(),
            "status_sha256": hashlib.sha256(initial_status).hexdigest(),
            "worktree_diff_sha256": (run / "initial-out-of-scope-worktree-diff.sha256").read_text().strip(),
            "index_diff_sha256": (run / "initial-out-of-scope-index-diff.sha256").read_text().strip(),
        }
    excludes = [f":(exclude){item}" for item in ALLOWED]
    current_status = subprocess.check_output(
        ["git", "status", "--porcelain=v2", "--untracked-files=all"], cwd=repo
    )
    current = {
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip(),
        "status_sha256": hashlib.sha256(filtered_status(current_status, run, repo)).hexdigest(),
        "worktree_diff_sha256": hashlib.sha256(subprocess.check_output(
            ["git", "diff", "--binary", "--", ".", *excludes], cwd=repo
        )).hexdigest(),
        "index_diff_sha256": hashlib.sha256(subprocess.check_output(
            ["git", "diff", "--cached", "--binary", "--", ".", *excludes], cwd=repo
        )).hexdigest(),
    }
    for key, value in current.items():
        if value != baseline[key]:
            raise AssertionError(f"out-of-scope state drift after selected baseline:{key}")
    return {"mode": baseline["mode"], **current}


def validate_small_tsv(
    path: pathlib.Path,
    header: list[str],
    manifest_sha: str,
    evidence_ids: set[str],
    referenced: set[str],
) -> tuple[int, set[str], set[str]]:
    check_header(path, header)
    row_ids: set[str] = set()
    source_ids: set[str] = set()
    rows = 0
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        for lineno, row in enumerate(reader, 2):
            rows += 1
            if None in row or any(value is None or value == "" for value in row.values()):
                raise AssertionError(f"empty or extra field: {path.name}:{lineno}")
            if row["schema_version"] != "2":
                raise AssertionError(f"bad schema version: {path.name}:{lineno}")
            if row["evidence_manifest_sha256"] != manifest_sha:
                raise AssertionError(f"manifest binding mismatch: {path.name}:{lineno}")
            for evidence_id in split_ids(row["evidence_ids"]):
                if evidence_id not in evidence_ids:
                    raise AssertionError(f"unknown evidence ID: {path.name}:{lineno}:{evidence_id}")
                referenced.add(evidence_id)
            if "finding_id" in row:
                if not ID64.fullmatch(row["finding_id"]):
                    raise AssertionError(f"bad finding ID: {path.name}:{lineno}")
                if row["finding_id"] in row_ids:
                    raise AssertionError(f"duplicate finding ID: {row['finding_id']}")
                row_ids.add(row["finding_id"])
                source_ids.add(row["source_scan_row_id"])
    return rows, row_ids, source_ids


def validate_manifest(bundle: pathlib.Path) -> tuple[str, dict[str, dict[str, str]]]:
    manifest = bundle / "evidence-manifest.tsv"
    check_header(manifest, MANIFEST_HEADER)
    rows: dict[str, dict[str, str]] = {}
    last_key: bytes | None = None
    with manifest.open("r", encoding="utf-8", newline="") as stream:
        for lineno, row in enumerate(csv.DictReader(stream, delimiter="\t"), 2):
            if None in row or any(value is None or value == "" for value in row.values()):
                raise AssertionError(f"empty manifest field:{lineno}")
            if row["schema_version"] != "2" or not ID64.fullmatch(row["evidence_id"]):
                raise AssertionError(f"bad manifest identity:{lineno}")
            if not HEX64.fullmatch(row["sha256"]) or not ID64.fullmatch(row["producer_command_id"]):
                raise AssertionError(f"bad manifest hash/command:{lineno}")
            rel = pathlib.PurePosixPath(row["path"])
            if rel.is_absolute() or ".." in rel.parts or row["path"] == "evidence-manifest.tsv":
                raise AssertionError(f"unsafe or recursive manifest path:{lineno}")
            key = row["path"].encode("utf-8")
            if last_key is not None and key <= last_key:
                raise AssertionError(f"manifest not strictly UTF-8-byte sorted:{lineno}")
            last_key = key
            target = bundle.joinpath(*rel.parts)
            if not target.is_file():
                raise AssertionError(f"manifest target missing:{row['path']}")
            if int(row["size_bytes"]) != target.stat().st_size or sha_file(target) != row["sha256"]:
                raise AssertionError(f"manifest target drift:{row['path']}")
            if row["evidence_id"] in rows:
                raise AssertionError(f"duplicate evidence ID:{row['evidence_id']}")
            rows[row["evidence_id"]] = row
    actual_files = {
        item.relative_to(bundle).as_posix()
        for item in bundle.rglob("*")
        if item.is_file() and item != manifest
    }
    listed_files = {row["path"] for row in rows.values()}
    if actual_files != listed_files:
        raise AssertionError(
            f"bundle file closure mismatch missing={sorted(actual_files-listed_files)[:3]} "
            f"extra={sorted(listed_files-actual_files)[:3]}"
        )
    return sha_file(manifest), rows


def scan_large_ledger(
    path: pathlib.Path,
    manifest_sha: str,
    evidence_ids: set[str],
    referenced: set[str],
    expected: dict[str, object],
    finding_sources: set[str],
) -> dict[str, object]:
    check_header(path, SCAN_HEADER)
    rows = 0
    nul_bytes = 0
    cr_bytes = 0
    lanes: Counter[str] = Counter()
    statuses: Counter[str] = Counter()
    methods: Counter[str] = Counter()
    found_sources: set[str] = set()
    pending_primary: dict[str, str] | None = None
    paired = 0
    paired_fields = [
        "physical_path", "logical_member_order", "member_name", "same_name_ordinal",
        "scan_unit_sha256", "semantic_context_id", "resolution_context_id", "lane",
        "domain_kind", "domain_units", "domain_set_sha256", "candidate_starts",
        "candidate_start_set_sha256", "boundary_known_semantic_unresolved_units",
        "boundary_ambiguous_units", "candidate_count", "status", "hit_ids",
    ]
    primitive_lanes = {
        "csr-opcode", "xw-slot", "address-form-opcode", "literal-pointer",
        "relocation-source", "rom-csr-opcode", "rom-xw-slot", "rom-address-or-literal",
    }
    with path.open("rb") as stream:
        header = stream.readline()
        nul_bytes += header.count(b"\0")
        cr_bytes += header.count(b"\r")
        for lineno, raw in enumerate(stream, 2):
            rows += 1
            nul_bytes += raw.count(b"\0")
            cr_bytes += raw.count(b"\r")
            values = raw.rstrip(b"\n").decode("utf-8").split("\t")
            if len(values) != len(SCAN_HEADER) or any(value == "" for value in values):
                raise AssertionError(f"bad scan row shape:{lineno}:{len(values)}")
            row = dict(zip(SCAN_HEADER, values, strict=True))
            if row["schema_version"] != "2" or row["evidence_manifest_sha256"] != manifest_sha:
                raise AssertionError(f"scan schema/manifest mismatch:{lineno}")
            if not ID64.fullmatch(row["scan_row_id"]) or not ID64.fullmatch(row["semantic_context_id"]):
                raise AssertionError(f"bad scan identity:{lineno}")
            if row["method"] not in {"primary", "independent"}:
                raise AssertionError(f"invalid method:{lineno}:{row['method']}")
            for evidence_id in split_ids(row["evidence_ids"]):
                if evidence_id not in evidence_ids:
                    raise AssertionError(f"unknown scan evidence ID:{lineno}:{evidence_id}")
                referenced.add(evidence_id)
            lanes[row["lane"]] += 1
            statuses[row["status"]] += 1
            methods[row["method"]] += 1
            if row["scan_row_id"] in finding_sources:
                found_sources.add(row["scan_row_id"])
            if row["lane"] in primitive_lanes:
                if row["method"] == "primary":
                    if pending_primary is not None:
                        raise AssertionError(f"unpaired primary primitive before line:{lineno}")
                    pending_primary = row
                else:
                    if pending_primary is None:
                        raise AssertionError(f"independent primitive lacks adjacent primary:{lineno}")
                    if any(pending_primary[field] != row[field] for field in paired_fields):
                        raise AssertionError(f"primary/independent primitive mismatch:{lineno}")
                    pending_primary = None
                    paired += 1
            elif pending_primary is not None:
                raise AssertionError(f"unpaired primary primitive at line:{lineno}")
    if pending_primary is not None:
        raise AssertionError("trailing unpaired primary primitive")
    if nul_bytes or cr_bytes:
        raise AssertionError(f"forbidden byte in object ledger:nul={nul_bytes}:cr={cr_bytes}")
    if rows != int(expected["expected_scan_rows"]):
        raise AssertionError(f"scan row count mismatch:{rows}!={expected['expected_scan_rows']}")
    expected_lanes = {key: int(value) for key, value in expected["expected_lane_counts"].items()}
    if dict(sorted(lanes.items())) != dict(sorted(expected_lanes.items())):
        raise AssertionError("scan lane-count closure mismatch")
    if found_sources != finding_sources:
        raise AssertionError(f"finding source rows missing:{sorted(finding_sources-found_sources)[:3]}")
    return {
        "rows": rows,
        "lane_counts": dict(sorted(lanes.items())),
        "status_counts": dict(sorted(statuses.items())),
        "method_counts": dict(sorted(methods.items())),
        "paired_primitive_rows": paired,
        "finding_source_rows": len(found_sources),
        "nul_bytes": nul_bytes,
        "cr_bytes": cr_bytes,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", required=True, type=pathlib.Path)
    parser.add_argument("--require-report", action="store_true")
    args = parser.parse_args()
    run = args.run_root.resolve()
    repo = run.parents[3]
    results = repo / "audit-report-f/followup/results"
    bundle = results / "06b-chipid-errata-evidence"
    inventory = results / "06b-chipid-errata-inventory.tsv"
    object_scan = results / "06b-chipid-errata-object-scan.tsv"
    findings = results / "06b-chipid-errata-findings.tsv"
    report = results / "06b-chipid-errata-codex.md"

    scope = validate_scope_state(run, repo)
    manifest_sha, manifest_rows = validate_manifest(bundle)
    evidence_ids = set(manifest_rows)
    referenced: set[str] = set()
    inventory_rows, _, _ = validate_small_tsv(
        inventory, INVENTORY_HEADER, manifest_sha, evidence_ids, referenced
    )
    finding_rows, _, finding_sources = validate_small_tsv(
        findings, FINDING_HEADER, manifest_sha, evidence_ids, referenced
    )
    expected = json.loads((bundle / "machine/expected-scan-closure.json").read_text(encoding="utf-8"))
    scan_summary = scan_large_ledger(
        object_scan, manifest_sha, evidence_ids, referenced, expected, finding_sources
    )

    report_sha = "not-required"
    if args.require_report:
        body = report.read_text(encoding="utf-8")
        headings = re.findall(r"^## (\d+)\.", body, flags=re.MULTILINE)
        if headings != [str(index) for index in range(1, 16)]:
            raise AssertionError(f"report section order mismatch:{headings}")
        if f"evidence_manifest_sha256: `{manifest_sha}`" not in body:
            raise AssertionError("report lacks exact manifest binding")
        for evidence_id in evidence_ids:
            if evidence_id in body:
                referenced.add(evidence_id)
        report_sha = sha_file(report)
        if referenced != evidence_ids:
            missing = sorted(evidence_ids - referenced)
            raise AssertionError(f"unreferenced evidence IDs:{missing[:5]}")

    receipt = {
        "schema_version": "2",
        "status": "pass",
        "require_report": args.require_report,
        "manifest_sha256": manifest_sha,
        "evidence_files": len(manifest_rows),
        "git_scope": scope,
        "referenced_evidence_ids": len(referenced),
        "inventory_rows": inventory_rows,
        "finding_rows": finding_rows,
        "scan": scan_summary,
        "fixed_sha256": {
            "inventory": sha_file(inventory),
            "object_scan": sha_file(object_scan),
            "findings": sha_file(findings),
            "report": report_sha,
        },
    }
    destination = run / ("acceptance-final.json" if args.require_report else "acceptance-pre-report.json")
    destination.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
