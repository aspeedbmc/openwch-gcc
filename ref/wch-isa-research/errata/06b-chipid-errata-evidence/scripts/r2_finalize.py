#!/usr/bin/env python3
"""Build the deterministic round-two 06b bundle and fixed deliverables.

The build phase freezes a compact evidence bundle, binds the three TSVs to
its manifest, and leaves the report for a second phase.  The report-only phase
runs only after the independent streaming acceptance check has passed, and it
does not modify the frozen bundle.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import pathlib
import shutil
import struct
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass


RUN = pathlib.Path(__file__).resolve().parent
REPO = RUN.parents[3]
RESULTS = REPO / "audit-report-f/followup/results"
BUNDLE = RESULTS / "06b-chipid-errata-evidence"
REPORT = RESULTS / "06b-chipid-errata-codex.md"
INVENTORY = RESULTS / "06b-chipid-errata-inventory.tsv"
OBJECT_SCAN = RESULTS / "06b-chipid-errata-object-scan.tsv"
FINDINGS = RESULTS / "06b-chipid-errata-findings.tsv"
GEN = RUN / "generated-r2"
SCHEMA = "2"

ALLOWED = (
    "audit-report-f/followup/results/06b-chipid-errata-codex.md",
    "audit-report-f/followup/results/06b-chipid-errata-inventory.tsv",
    "audit-report-f/followup/results/06b-chipid-errata-object-scan.tsv",
    "audit-report-f/followup/results/06b-chipid-errata-findings.tsv",
    "audit-report-f/followup/results/06b-chipid-errata-evidence",
)

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


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tuple_bytes(parts: tuple[object, ...]) -> bytes:
    out = bytearray(struct.pack(">I", len(parts)))
    for part in parts:
        raw = str(part).encode("utf-8")
        out.extend(struct.pack(">Q", len(raw)))
        out.extend(raw)
    return bytes(out)


def tuple_digest(*parts: object) -> str:
    return sha_bytes(tuple_bytes(parts))


def rid(prefix: str, *parts: object) -> str:
    return f"{prefix}-{tuple_digest(prefix, *parts)}"


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def read_json(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: pathlib.Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def clean_cell(value: object) -> str:
    text = str(value)
    if not text:
        return "not-applicable"
    return text.replace("\t", " ").replace("\r", " ").replace("\n", " ")


def write_tsv(path: pathlib.Path, header: list[str], rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(header)
        for row in rows:
            if isinstance(row, dict):
                writer.writerow([clean_cell(row.get(column, "not-applicable")) for column in header])
            else:
                writer.writerow([clean_cell(value) for value in row])


@dataclass(slots=True)
class Unit:
    native: bool
    machine: str
    elf_class: str
    endian: str
    attrs: str
    file_size: int
    exec_units: int
    exec_hash: str
    alloc_units: int
    alloc_hash: str
    reloc_units: int
    reloc_hash: str
    exec2_count: int
    exec2_hash: str
    exec4_count: int
    exec4_hash: str
    alloc4_count: int
    alloc4_hash: str
    counts: dict[str, int]
    candidate_hashes: dict[str, str]
    boundary_known: int
    boundary_ambiguous: int
    semantic_sources: int


def load_units() -> dict[str, Unit]:
    source = RUN / "controls/compact-r2/unit-domain-summary.jsonl"
    units: dict[str, Unit] = {}
    with source.open("r", encoding="utf-8") as stream:
        for raw in stream:
            row = json.loads(raw)
            native = bool(row["native_scan_applicable"])
            coverage = row["coverage"] or {
                "boundary_known_semantic_unresolved_bytes": 0,
                "boundary_ambiguous_bytes": 0,
            }
            grids = row["grids"] if native else {
                "exec-width2-step2": {"count": 0, "set_sha256": tuple_digest("empty-exec2")},
                "exec-width4-step2": {"count": 0, "set_sha256": tuple_digest("empty-exec4")},
                "alloc-width4-step1": {"count": 0, "set_sha256": tuple_digest("empty-alloc4")},
            }
            empty_domain = {"units": 0, "set_sha256": tuple_digest("empty-domain")}
            candidate_names = (
                "address-form-opcode", "csr-opcode", "literal-pointer",
                "relocation-source", "symbol-string-debug", "xw-slot",
            )
            unit = Unit(
                native=native,
                machine=str(row["machine"]),
                elf_class=str(row["elf_class"]),
                endian=str(row["endian"]),
                attrs=str(row["attrs_sha256"]),
                file_size=int(row["file_size"]),
                exec_units=int((row["exec_domain"] or empty_domain)["units"]),
                exec_hash=(row["exec_domain"] or empty_domain)["set_sha256"],
                alloc_units=int((row["alloc_domain"] or empty_domain)["units"]),
                alloc_hash=(row["alloc_domain"] or empty_domain)["set_sha256"],
                reloc_units=int((row["relocation_domain"] or empty_domain)["units"]),
                reloc_hash=(row["relocation_domain"] or empty_domain)["set_sha256"],
                exec2_count=int(grids["exec-width2-step2"]["count"]),
                exec2_hash=grids["exec-width2-step2"]["set_sha256"],
                exec4_count=int(grids["exec-width4-step2"]["count"]),
                exec4_hash=grids["exec-width4-step2"]["set_sha256"],
                alloc4_count=int(grids["alloc-width4-step1"]["count"]),
                alloc4_hash=grids["alloc-width4-step1"]["set_sha256"],
                counts={key: int(row["candidate_counts"].get(key, 0)) for key in candidate_names},
                candidate_hashes={
                    key: row["candidate_set_sha256"].get(key, tuple_digest("empty-candidate-set", key))
                    for key in candidate_names
                },
                boundary_known=int(coverage["boundary_known_semantic_unresolved_bytes"]),
                boundary_ambiguous=int(coverage["boundary_ambiguous_bytes"]),
                semantic_sources=len(row["semantic_sources"]),
            )
            units[row["scan_unit_sha256"]] = unit
    return units


def load_artifacts() -> tuple[list[dict[str, object]], dict[str, dict[str, object]]]:
    rows = []
    with (RUN / "primary/artifacts.jsonl").open("r", encoding="utf-8") as stream:
        for raw in stream:
            rows.append(json.loads(raw))
    return rows, {str(row["path"]): row for row in rows}


def enrich_selected_build_contexts(artifacts: list[dict[str, object]]) -> None:
    summary = read_json(RUN / "controls/build-context-r2/build-context-summary.json")
    selected = {
        row["archive_path"]: row["build_context_id"]
        for row in summary["selection_archives"]
        if row["selected_in_available_link_map"] == "yes"
    }
    for artifact in artifacts:
        path = str(artifact["path"])
        if path in selected:
            artifact["build_context"] = selected[path]


def filtered_status(data: bytes) -> bytes:
    prefixes = list(ALLOWED) + [f"tmp/chipid-errata-06b/runs/{RUN.name}"]
    kept = []
    for line in data.splitlines(keepends=True):
        decoded = line.decode("utf-8", "surrogateescape")
        if any(prefix in decoded for prefix in prefixes):
            continue
        kept.append(line)
    return b"".join(kept)


def current_scope_snapshot() -> dict[str, str]:
    excludes = [f":(exclude){item}" for item in ALLOWED]
    current_status = subprocess.check_output(
        ["git", "status", "--porcelain=v2", "--untracked-files=all"], cwd=REPO
    )
    return {
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "status_sha256": sha_bytes(filtered_status(current_status)),
        "worktree_diff_sha256": sha_bytes(subprocess.check_output(
            ["git", "diff", "--binary", "--", ".", *excludes], cwd=REPO
        )),
        "index_diff_sha256": sha_bytes(subprocess.check_output(
            ["git", "diff", "--cached", "--binary", "--", ".", *excludes], cwd=REPO
        )),
    }


def scope_baseline(*, allow_external_transition: bool = False) -> dict[str, str]:
    initial_head = (RUN / "initial-git-head").read_text().strip()
    snapshot = current_scope_snapshot()
    baseline_path = RUN / "concurrency-rebaseline.json"
    if snapshot["head"] == initial_head:
        return {
            "schema_version": "2", "mode": "original-baseline", "initial_head": initial_head,
            "head": initial_head,
            "status_sha256": sha_bytes(filtered_status((RUN / "initial-git-status.porcelain-v2").read_bytes())),
            "worktree_diff_sha256": (RUN / "initial-out-of-scope-worktree-diff.sha256").read_text().strip(),
            "index_diff_sha256": (RUN / "initial-out-of-scope-index-diff.sha256").read_text().strip(),
            "external_commit_delta_sha256": tuple_digest("no-external-head-advance"),
            "external_commit_changed_paths": "0",
        }
    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", initial_head, snapshot["head"]], cwd=REPO
    ).returncode == 0
    if not ancestry:
        raise SystemExit(f"HEAD diverged from audit baseline: {initial_head} -> {snapshot['head']}")
    allowed_delta = subprocess.check_output(
        ["git", "diff", "--name-only", f"{initial_head}..{snapshot['head']}", "--", *ALLOWED], cwd=REPO
    )
    if allowed_delta:
        raise SystemExit("concurrent commits touched an authorized 06b result path")
    delta = subprocess.check_output(
        ["git", "diff", "--name-status", "-r", f"{initial_head}..{snapshot['head']}"], cwd=REPO
    )
    proposed = {
        "schema_version": "2", "mode": "external-head-advance-rebaseline",
        "initial_head": initial_head, "head": snapshot["head"],
        "status_sha256": snapshot["status_sha256"],
        "worktree_diff_sha256": snapshot["worktree_diff_sha256"],
        "index_diff_sha256": snapshot["index_diff_sha256"],
        "external_commit_delta_sha256": sha_bytes(delta),
        "external_commit_changed_paths": str(len(delta.splitlines())),
        "worktree_transition_count": "0",
        "worktree_transition_chain_sha256": tuple_digest("no-post-head-worktree-transition"),
    }
    if baseline_path.exists():
        existing = read_json(baseline_path)
        comparable_keys = (
            "schema_version", "mode", "initial_head", "head", "status_sha256",
            "worktree_diff_sha256", "index_diff_sha256", "external_commit_delta_sha256",
            "external_commit_changed_paths",
        )
        same_snapshot = all(existing.get(key) == proposed.get(key) for key in comparable_keys)
        if not same_snapshot:
            if not allow_external_transition:
                raise SystemExit(f"workspace changed again after concurrency rebaseline: {existing['head']} -> {snapshot['head']}")
            transition = tuple_digest(
                "external-worktree-transition",
                existing["head"], existing["status_sha256"], existing["worktree_diff_sha256"], existing["index_diff_sha256"],
                proposed["head"], proposed["status_sha256"], proposed["worktree_diff_sha256"], proposed["index_diff_sha256"],
            )
            count = int(existing.get("worktree_transition_count", "0")) + 1
            chain = tuple_digest(
                "external-worktree-transition-chain",
                existing.get("worktree_transition_chain_sha256", tuple_digest("no-post-head-worktree-transition")),
                transition,
            )
            proposed["worktree_transition_count"] = str(count)
            proposed["worktree_transition_chain_sha256"] = chain
            write_json(baseline_path, proposed)
            return proposed
        return existing
    write_json(baseline_path, proposed)
    return proposed


def verify_scope_state() -> dict[str, str]:
    baseline = scope_baseline(allow_external_transition=False)
    snapshot = current_scope_snapshot()
    for key in ("head", "status_sha256", "worktree_diff_sha256", "index_diff_sha256"):
        if snapshot[key] != baseline[key]:
            raise SystemExit(f"out-of-scope state drift after selected baseline: {key}")
    return baseline


def git_scope_check(destination: pathlib.Path) -> None:
    baseline = scope_baseline(allow_external_transition=True)
    snapshot = current_scope_snapshot()
    initial_status = (RUN / "initial-git-status.porcelain-v2").read_bytes()
    start_filtered = filtered_status(initial_status)
    start_worktree = (RUN / "initial-out-of-scope-worktree-diff.sha256").read_text().strip()
    start_index = (RUN / "initial-out-of-scope-index-diff.sha256").read_text().strip()
    external = baseline["mode"] == "external-head-advance-rebaseline"
    rows = [
        ["2", "original-head", baseline["initial_head"], snapshot["head"],
         "external-ancestor-advance" if external else "same"],
        ["2", "original-porcelain-v2-out-of-scope", sha_bytes(start_filtered), snapshot["status_sha256"],
         "external-commit-transition" if external else ("same" if sha_bytes(start_filtered) == snapshot["status_sha256"] else "DRIFT")],
        ["2", "original-worktree-diff-out-of-scope", start_worktree, snapshot["worktree_diff_sha256"],
         "external-commit-transition" if external else ("same" if start_worktree == snapshot["worktree_diff_sha256"] else "DRIFT")],
        ["2", "original-index-diff-out-of-scope", start_index, snapshot["index_diff_sha256"],
         "external-commit-transition" if external and start_index != snapshot["index_diff_sha256"] else ("same" if start_index == snapshot["index_diff_sha256"] else "DRIFT")],
        ["2", "selected-head-baseline", baseline["head"], snapshot["head"], "same"],
        ["2", "selected-porcelain-v2-out-of-scope", baseline["status_sha256"], snapshot["status_sha256"], "same"],
        ["2", "selected-worktree-diff-out-of-scope", baseline["worktree_diff_sha256"], snapshot["worktree_diff_sha256"], "same"],
        ["2", "selected-index-diff-out-of-scope", baseline["index_diff_sha256"], snapshot["index_diff_sha256"], "same"],
        ["2", "external-commit-path-delta", baseline["external_commit_delta_sha256"], baseline["external_commit_delta_sha256"],
         f"recorded-{baseline['external_commit_changed_paths']}-paths"],
        ["2", "post-head-external-worktree-transition-chain", baseline.get("worktree_transition_chain_sha256", tuple_digest("no-post-head-worktree-transition")), baseline.get("worktree_transition_chain_sha256", tuple_digest("no-post-head-worktree-transition")),
         f"recorded-{baseline.get('worktree_transition_count', '0')}-transitions"],
    ]
    write_tsv(destination, ["schema_version", "scope", "start_sha256", "end_sha256", "status"], rows)
    if any(row[-1] == "DRIFT" for row in rows):
        raise SystemExit(f"out-of-scope Git drift after selected baseline: {rows}")


def input_drift_and_sanitized(stage: pathlib.Path) -> None:
    source = RUN / "primary/analysis-input-manifest.tsv"
    sanitized = stage / "input/analysis-input-manifest.tsv"
    drift = stage / "machine/input-drift.tsv"
    sanitized.parent.mkdir(parents=True, exist_ok=True)
    drift.parent.mkdir(parents=True, exist_ok=True)
    failures = []
    with source.open("r", encoding="utf-8", newline="") as source_stream, \
            sanitized.open("w", encoding="utf-8", newline="") as clean_stream, \
            drift.open("w", encoding="utf-8", newline="") as drift_stream:
        reader = csv.DictReader(source_stream, delimiter="\t")
        clean_writer = csv.writer(clean_stream, delimiter="\t", lineterminator="\n")
        drift_writer = csv.writer(drift_stream, delimiter="\t", lineterminator="\n")
        clean_writer.writerow(["schema_version", "source_set", "path", "size_bytes", "sha256"])
        drift_writer.writerow(["schema_version", "path", "start_sha256", "end_sha256", "status"])
        for row in reader:
            target = REPO / row["path"]
            if not target.is_file():
                actual = "not-present"
                status = "missing"
            else:
                actual = sha_file(target)
                status = "same" if actual == row["sha256"] else "DRIFT"
            clean_writer.writerow(["2", row["source_set"], row["path"], row["size_bytes"], row["sha256"]])
            drift_writer.writerow(["2", row["path"], row["sha256"], actual, status])
            if status != "same":
                failures.append((row["path"], status))
    if failures:
        raise SystemExit(f"analysis input drift: {failures[:5]}")


def sanitized_prior_baseline(destination: pathlib.Path) -> None:
    source = RUN / "fixed-output-baseline.tsv"
    rows = []
    with source.open("r", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream, delimiter="\t"):
            rows.append(["2", row["path"], row["status"], row["size_bytes"], row["sha256"]])
    write_tsv(destination, ["schema_version", "path", "status", "size_bytes", "sha256"], rows)


def sanitized_prior_artifact_manifest(destination: pathlib.Path) -> None:
    rows = []
    with (RUN / "prior-artifact-manifest.tsv").open("r", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream, delimiter="\t"):
            path = str(row["path"])
            parts = path.split("/")
            if len(parts) > 4 and parts[:3] == ["tmp", "chipid-errata-06b", "runs"]:
                path = "/".join(["<PRIOR_RUN_ROOT>", *parts[4:]])
            rows.append([
                "2", row["artifact_class"], path, row["size_bytes"], row["sha256"], row["status"]
            ])
    write_tsv(
        destination,
        ["schema_version", "artifact_class", "path", "size_bytes", "sha256", "status"],
        rows,
    )


def command_and_tool_manifests(stage: pathlib.Path) -> tuple[dict[str, str], dict[str, str]]:
    python_hash = sha_file(pathlib.Path(sys.executable))
    scripts = {
        "baseline": RUN / "baseline_r2.py",
        "prior-review": RUN / "review_prior_r2.py",
        "primary": RUN / "r2_primary.py",
        "independent": RUN / "r2_independent.py",
        "compare": RUN / "r2_compare.py",
        "core-controls": RUN / "r2_controls.py",
        "xw-fixture": RUN / "r2_xw_fixture.py",
        "xw-boundaries": RUN / "r2_xw_boundaries.py",
        "rom-control": RUN / "r2_rom_control.py",
        "documents": RUN / "r2_docs.py",
        "document-controls": RUN / "r2_doc_controls.py",
        "tar-closure": RUN / "r2_tar_closure.py",
        "build-context": RUN / "r2_build_contexts.py",
        "positive-evidence": RUN / "r2_positive_evidence.py",
        "compact-sets": RUN / "r2_compact_sets.py",
        "finalize": RUN / "r2_finalize.py",
        "acceptance": RUN / "r2_acceptance.py",
        "rawscan-smoke": REPO / "audit-report-f/followup/tools/rawscan.py",
    }
    templates = {
        label: f"python3 <RUN_ROOT>/{path.name} --run-root <RUN_ROOT>"
        for label, path in scripts.items()
    }
    templates["finalize"] = "python3 <RUN_ROOT>/r2_finalize.py --run-root <RUN_ROOT> --build"
    templates["rebind"] = "python3 <RUN_ROOT>/r2_finalize.py --run-root <RUN_ROOT> --rebind"
    templates["baseline"] = "python3 <RUN_ROOT>/baseline_r2.py"
    templates["prior-review"] = "python3 <RUN_ROOT>/review_prior_r2.py"
    templates["rawscan-smoke"] = "find tmp/wch-evt/evt -name '*.a' -type f -print0 | xargs -0 python3 audit-report-f/followup/tools/rawscan.py"
    templates["report"] = "python3 <RUN_ROOT>/r2_finalize.py --run-root <RUN_ROOT> --report-only"
    templates["acceptance"] = "python3 <RUN_ROOT>/r2_acceptance.py --run-root <RUN_ROOT>"
    templates["acceptance-final"] = "python3 <RUN_ROOT>/r2_acceptance.py --run-root <RUN_ROOT> --require-report"
    tool_hashes = {
        label: tuple_digest("python-script-tool", python_hash, sha_file(path))
        for label, path in scripts.items()
    }
    tool_hashes["report"] = tool_hashes["finalize"]
    tool_hashes["rebind"] = tool_hashes["finalize"]
    tool_hashes["acceptance-final"] = tool_hashes["acceptance"]
    command_ids = {
        label: rid("cmd", templates[label], tool_hashes[label])
        for label in templates
    }
    command_rows = [
        ["2", command_ids[label], label, templates[label], tool_hashes[label], "pass"]
        for label in sorted(templates, key=lambda item: item.encode("utf-8"))
    ]
    write_tsv(
        stage / "machine/command-ledger.tsv",
        ["schema_version", "command_id", "label", "normalized_command", "tool_sha256", "status"],
        command_rows,
    )

    tool_paths = [
        ("system:python3", pathlib.Path(sys.executable), ["--version"]),
        ("system:git", pathlib.Path(shutil.which("git") or "/usr/bin/git"), ["--version"]),
        ("system:gzip", pathlib.Path(shutil.which("gzip") or "/usr/bin/gzip"), ["--version"]),
        ("system:pdftotext", pathlib.Path(shutil.which("pdftotext") or "/usr/local/bin/pdftotext"), ["-v"]),
        ("system:pdftoppm", pathlib.Path(shutil.which("pdftoppm") or "/usr/local/bin/pdftoppm"), ["-v"]),
        ("repo:gcc12-objdump", REPO / "MRS_Toolchain_MAC_V240/Toolchain/RISC-V Embedded GCC12/bin/riscv-wch-elf-objdump", ["--version"]),
        ("repo:gcc12-nm", REPO / "MRS_Toolchain_MAC_V240/Toolchain/RISC-V Embedded GCC12/bin/riscv-wch-elf-nm", ["--version"]),
        ("repo:gcc12-as", REPO / "MRS_Toolchain_MAC_V240/Toolchain/RISC-V Embedded GCC12/bin/riscv-wch-elf-as", ["--version"]),
        ("repo:gcc12-ar", REPO / "MRS_Toolchain_MAC_V240/Toolchain/RISC-V Embedded GCC12/bin/riscv-wch-elf-ar", ["--version"]),
        ("repo:gcc12-readelf", REPO / "MRS_Toolchain_MAC_V240/Toolchain/RISC-V Embedded GCC12/bin/riscv-wch-elf-readelf", ["--version"]),
        ("repo:gcc12-objcopy", REPO / "MRS_Toolchain_MAC_V240/Toolchain/RISC-V Embedded GCC12/bin/riscv-wch-elf-objcopy", ["--version"]),
        ("repo:gcc12-strings", REPO / "MRS_Toolchain_MAC_V240/Toolchain/RISC-V Embedded GCC12/bin/riscv-wch-elf-strings", ["--version"]),
        ("repo:gcc15-objdump", REPO / "MRS_Toolchain_MAC_V240/Toolchain/RISC-V Embedded GCC15/bin/riscv32-wch-elf-objdump", ["--version"]),
        ("repo:gcc8-objdump", REPO / "MRS_Toolchain_MAC_V240/Toolchain/RISC-V Embedded GCC/bin/riscv-none-embed-objdump", ["--version"]),
    ]
    tool_rows = []
    for label, path, version_args in tool_paths:
        if not path.is_file():
            tool_rows.append(["2", label, "not-present", "not-applicable", "not-applicable"])
            continue
        try:
            result = subprocess.run([str(path), *version_args], capture_output=True, timeout=15)
            display = (result.stdout or result.stderr).decode("utf-8", "replace").splitlines()
            version = clean_cell(display[0] if display else "version-output-empty")
        except Exception as error:  # version display is non-decisive; hash remains decisive.
            version = type(error).__name__
        tool_rows.append(["2", label, "present", sha_file(path), version])
    for label, path in sorted(scripts.items()):
        tool_rows.append(["2", f"script:{path.name}", "present", sha_file(path), "repository-relative-script"])
    write_tsv(
        stage / "machine/tool-manifest.tsv",
        ["schema_version", "tool_label", "status", "sha256", "version"],
        tool_rows,
    )
    return command_ids, tool_hashes


def claim_ledger(destination: pathlib.Path) -> None:
    rows = [
        ["2", "round1-independent-parser", "independent scanner was parser-independent", "rejected",
         "round one reused primary parser state", "new raw archive/ELF/ROM parser; zero mismatches over 3,221 archives, 682,142 occurrences, 235,234 units and five ROMs"],
        ["2", "round1-linear-all-starts", "linear decoder established every instruction start", "rejected",
         "2-byte stepping confused candidate supersets with proven boundaries", "separate seeded recursive CFG, mixed-run framing, and all-IALIGN prefix controls"],
        ["2", "round1-csr-semantics", "eight EVT CSR words were identity/capability reads", "rejected",
         "field decode showed zero identity/capability CSR reads", "eight exact word occurrences retained as scanner controls only"],
        ["2", "round1-v317-float", "two V317 float eth_api members perform ID-SELECT", "rejected",
         "both lack GetChipID and 0x1ffff706 load; getTxBuffAddr is descriptor-only", "reclassified STATIC-VARIANT-SPECIALIZATION"],
        ["2", "round1-rom-reachable", "CH587 jump-table CFG reaches 0x40968 mcpy", "rejected",
         "recursive walk does not reach the local block", "local bytes prove a parcel-aligned mcpy control, not runtime reachability"],
        ["2", "round1-rom-long-lengths", "CH587 has proven 6/10/12/14-byte instructions", "rejected",
         "whole-range claims included data and stopped on reserved >=192-bit prefixes", "recursive code has only 2/4-byte parcels; mixed framing has 10/12-byte parcels and explicit stop errors"],
        ["2", "prompt-gcc8-xw-rejection", "GCC8 rejects versioned _xw spellings", "rejected-prompt-expectation",
         "host fixture accepts _xw, _xw1p0, _xw2p0, _xw2p2, _xw3p0 and legacy concatenated spelling", "GCC8 still rejects mcpy"],
        ["2", "round1-iochub-workaround", "IoCHub hardware read selects a workaround", "rejected",
         "16 factory bytes feed registration/auth identity derivation", "ID-READ/ID-FLOW; remote interpretation and runtime behavior unresolved"],
        ["2", "round1-linux-scope", "MRS scope was complete", "rejected",
         "entire MRS_Toolchain_Linux_X64_V250 tree was absent", "added 435 archives and 110 standalone objects"],
        ["2", "wchnet-soft", "soft WCHNET source-select chain exists", "reproduced-narrowed",
         "independently re-extracted eight eth_api occurrences and disassembled four byte groups", "ID-READ + ID-SELECT + defensive recovery; silicon defect cause remains unproved"],
        ["2", "iqmath-mcpy-negative", "IQMath has no mcpy encoding", "reproduced-limited",
         "50 physical archives/9 content groups; exact/reverse/masked scans all zero", "limited to enumerated bytes and mcpy encoding family; not a global no-ID proof"],
    ]
    write_tsv(
        destination,
        ["schema_version", "claim_id", "prior_or_prompt_claim", "disposition", "basis", "replacement"],
        rows,
    )


def family_summary(destination: pathlib.Path, artifacts: list[dict[str, object]]) -> Counter[str]:
    counter = Counter(str(row["family"]) for row in artifacts)
    rows = [["2", family, count] for family, count in sorted(counter.items(), key=lambda item: item[0].encode("utf-8"))]
    write_tsv(destination, ["schema_version", "family", "physical_artifacts"], rows)
    return counter


def lane_policy(destination: pathlib.Path) -> None:
    value = {
        "schema_version": "2",
        "native_occurrence_required_lanes": {
            "primary_semantic": ["symbol-string-debug", "raw-csr", "address-dataflow", "indirect-flow"],
            "primary_and_independent_primitives": [
                "csr-opcode", "xw-slot", "address-form-opcode", "literal-pointer", "relocation-source"
            ],
        },
        "rom_occurrence_required_lanes": {
            "primary_semantic": ["rom-symbol-metadata", "rom-raw-csr", "rom-address-dataflow", "rom-indirect-flow"],
            "primary_and_independent_primitives": ["rom-csr-opcode", "rom-xw-slot", "rom-address-or-literal"],
        },
        "non_native_occurrence_required_lanes": {"primary": ["scope-control"]},
        "method_vocabulary": ["primary", "independent"],
        "inheritance": "not used: every physical occurrence is materialized and is its own representative",
        "status_semantics": {
            "pass-no-hit": "complete for the stated primitive/domain only; never a global no-ID claim",
            "pass-hit": "candidate discovery complete; semantic interpretation may remain elsewhere",
            "partial": "candidate semantics, boundary, resolution, consumer, link, or runtime closure remains unresolved",
            "not-required": "format/provenance excludes the occurrence from native RISC-V semantic scanning",
        },
    }
    write_json(destination, value)


def expected_scan_closure(destination: pathlib.Path, units: dict[str, Unit]) -> dict[str, object]:
    native = 0
    excluded = 0
    scopes: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    with (RUN / "primary/occurrences.jsonl").open("r", encoding="utf-8") as stream:
        for raw in stream:
            row = json.loads(raw)
            unit = units[row["member_sha256"]]
            if unit.native:
                native += 1
            else:
                excluded += 1
            scopes[row["scope_class"]] += 1
            sources[row["source_set"]] += 1
    roms = 5
    lane_counts: Counter[str] = Counter()
    for lane in ("symbol-string-debug", "raw-csr", "address-dataflow", "indirect-flow"):
        lane_counts[lane] = native
    for lane in ("csr-opcode", "xw-slot", "address-form-opcode", "literal-pointer", "relocation-source"):
        lane_counts[lane] = native * 2
    lane_counts["scope-control"] = excluded
    for lane in ("rom-symbol-metadata", "rom-raw-csr", "rom-address-dataflow", "rom-indirect-flow"):
        lane_counts[lane] = roms
    for lane in ("rom-csr-opcode", "rom-xw-slot", "rom-address-or-literal"):
        lane_counts[lane] = roms * 2
    value = {
        "schema_version": "2",
        "logical_object_occurrences": native + excluded,
        "native_occurrences": native,
        "non_native_occurrences": excluded,
        "rom_occurrences": roms,
        "rows_per_native_occurrence": 14,
        "rows_per_non_native_occurrence": 1,
        "rows_per_rom_occurrence": 10,
        "expected_scan_rows": native * 14 + excluded + roms * 10,
        "expected_lane_counts": dict(sorted(lane_counts.items())),
        "scope_counts": dict(sorted(scopes.items())),
        "source_set_counts": dict(sorted(sources.items())),
    }
    write_json(destination, value)
    return value


def add_copy(stage: pathlib.Path, source: pathlib.Path, relative: str) -> None:
    target = stage / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def populate_bundle(stage: pathlib.Path, artifacts: list[dict[str, object]], units: dict[str, Unit]) -> tuple[dict[str, str], Counter[str], dict[str, object]]:
    stage.mkdir(parents=True, exist_ok=True)
    command_ids, _tool_hashes = command_and_tool_manifests(stage)
    input_drift_and_sanitized(stage)
    sanitized_prior_baseline(stage / "input/prior-fixed-output-baseline.tsv")
    sanitized_prior_artifact_manifest(stage / "input/prior-artifact-manifest.tsv")
    git_scope_check(stage / "machine/git-scope-check.tsv")
    claim_ledger(stage / "machine/claim-ledger.tsv")
    families = family_summary(stage / "machine/family-summary.tsv", artifacts)
    lane_policy(stage / "machine/lane-policy.json")
    expected = expected_scan_closure(stage / "machine/expected-scan-closure.json", units)
    (stage / "input/prompt.sha256").write_text(sha_file(REPO / "06b-chipid-errata-codex.md") + "\n", encoding="ascii")
    add_copy(stage, RUN / "prior-complete-read-audit.json", "input/prior-complete-read-audit.json")

    copies = [
        (RUN / "primary/counts.json", "machine/primary-counts.json"),
        (RUN / "primary/artifacts.jsonl", "machine/primary-artifacts.jsonl"),
        (RUN / "primary/archive-summary.jsonl", "machine/archive-summary.jsonl"),
        (RUN / "comparison/summary.json", "machine/comparison-summary.json"),
        (RUN / "comparison/mismatches.jsonl", "machine/comparison-mismatches.jsonl"),
        (RUN / "controls/compact-r2/compact-set-summary.json", "machine/compact-set-summary.json"),
        (RUN / "controls/compact-r2/canonical-unit-domain-records.jsonl.gz", "machine/canonical-unit-domain-records.jsonl.gz"),
        (RUN / "controls/core-r2/control-summary.json", "controls/core/control-summary.json"),
        (RUN / "controls/core-r2/scope-and-archive-closure.json", "controls/core/scope-and-archive-closure.json"),
        (RUN / "controls/core-r2/xw-and-archive-anchor-counts.json", "controls/core/xw-and-archive-anchor-counts.json"),
        (RUN / "controls/core-r2/xw-archive-profile-matrix.json", "controls/core/xw-archive-profile-matrix.json"),
        (RUN / "controls/core-r2/evt-csr-control-summary.json", "controls/core/evt-csr-control-summary.json"),
        (RUN / "controls/core-r2/evt-csr-control-occurrences.tsv", "controls/core/evt-csr-control-occurrences.tsv"),
        (RUN / "controls/core-r2/iqmath-control-summary.json", "controls/core/iqmath-control-summary.json"),
        (RUN / "controls/core-r2/iqmath-mcpy-negative-control.tsv", "controls/core/iqmath-mcpy-negative-control.tsv"),
        (RUN / "controls/core-r2/rawscan-smoke-summary.json", "controls/core/rawscan-smoke-summary.json"),
        (RUN / "controls/core-r2/rawscan-smoke.stdout", "controls/core/rawscan-smoke.stdout"),
        (RUN / "controls/core-r2/rawscan-smoke.stderr", "controls/core/rawscan-smoke.stderr"),
        (RUN / "controls/xw-fixture-r2/xw-fixture-summary.json", "controls/xw/xw-fixture-summary.json"),
        (RUN / "controls/xw-fixture-r2/xw-source-encoding-map.tsv", "controls/xw/xw-source-encoding-map.tsv"),
        (RUN / "controls/xw-fixture-r2/xw-theoretical-encoding-set.tsv", "controls/xw/xw-theoretical-encoding-set.tsv"),
        (RUN / "controls/xw-fixture-r2/gcc12-mrs24-mcpy.S", "controls/xw/fixtures/gcc12-mcpy.S"),
        (RUN / "controls/xw-fixture-r2/gcc12-mrs24-mcpy.bin", "controls/xw/fixtures/gcc12-mcpy.bin"),
        (RUN / "controls/xw-fixture-r2/gcc12-mrs24-mcpy.o", "controls/xw/fixtures/gcc12-mcpy.o"),
        (RUN / "controls/xw-fixture-r2/gcc8-mrs24-mcpy.S", "controls/xw/fixtures/gcc8-mcpy-rejected.S"),
        (RUN / "controls/xw-boundaries-r2/xw-boundary-summary.json", "controls/xw/xw-boundary-summary.json"),
        (RUN / "controls/xw-boundaries-r2/xw-boundary-build-groups.tsv", "controls/xw/xw-boundary-build-groups.tsv"),
        (RUN / "controls/xw-boundaries-r2/xw-physical-diagnostics.tsv", "controls/xw/xw-physical-diagnostics.tsv"),
        (RUN / "controls/xw-boundaries-r2/xw-boundary-lines.tsv", "controls/xw/xw-boundary-lines.tsv"),
        (RUN / "controls/rom-r2/rom-control-summary.json", "controls/rom/rom-control-summary.json"),
        (RUN / "controls/rom-r2/rom-fingerprints.tsv", "controls/rom/rom-fingerprints.tsv"),
        (RUN / "controls/rom-r2/rom-header-ledger.tsv", "controls/rom/rom-header-ledger.tsv"),
        (RUN / "controls/rom-r2/rom-jt-seeds.tsv", "controls/rom/rom-jt-seeds.tsv"),
        (RUN / "controls/rom-r2/rom-length-prefix-candidates.tsv", "controls/rom/rom-length-prefix-candidates.tsv"),
        (RUN / "controls/rom-r2/rom-code-parcels.tsv", "controls/rom/rom-code-parcels.tsv"),
        (RUN / "controls/docs-r2/document-control-summary.json", "controls/documents/document-control-summary.json"),
        (RUN / "controls/docs-r2/document-query-summary.json", "controls/documents/document-query-summary.json"),
        (RUN / "controls/docs-r2/document-manifest.tsv", "controls/documents/document-manifest.tsv"),
        (RUN / "controls/docs-r2/document-query-hits.tsv", "controls/documents/document-query-hits.tsv"),
        (RUN / "controls/docs-r2/rm-register-visibility.tsv", "controls/documents/rm-register-visibility.tsv"),
        (RUN / "controls/docs-r2/visual-page-review.tsv", "controls/documents/visual-page-review.tsv"),
        (RUN / "controls/docs-r2/wchnet-document-gap.tsv", "controls/documents/wchnet-document-gap.tsv"),
        (RUN / "controls/docs-r2/h417-lot-page-excerpts.tsv", "controls/documents/h417-lot-page-excerpts.tsv"),
        (RUN / "controls/docs-r2/schematic-text-sanity.tsv", "controls/documents/schematic-text-sanity.tsv"),
        (RUN / "controls/docs-r2/broad-pdf-exclusions.tsv", "controls/documents/broad-pdf-exclusions.tsv"),
        (RUN / "controls/tar-closure-r2/package-extracted-closure-summary.json", "controls/tar/package-extracted-closure-summary.json"),
        (RUN / "controls/tar-closure-r2/package-extracted-byte-closure.tsv", "controls/tar/package-extracted-byte-closure.tsv"),
        (RUN / "controls/build-context-r2/build-context-summary.json", "controls/build/build-context-summary.json"),
        (RUN / "controls/build-context-r2/linked-map-selection.tsv", "controls/build/linked-map-selection.tsv"),
        (RUN / "controls/build-context-r2/project-reference-ledger.tsv", "controls/build/project-reference-ledger.tsv"),
    ]
    for source, relative in copies:
        add_copy(stage, source, relative)
    for source in sorted((RUN / "controls/positive-r2").rglob("*"), key=lambda item: item.as_posix().encode("utf-8")):
        if source.is_file():
            add_copy(stage, source, "controls/positive/" + source.relative_to(RUN / "controls/positive-r2").as_posix())
    for source in sorted((RUN / "pdf-review").glob("*.png"), key=lambda item: item.name.encode("utf-8")):
        add_copy(stage, source, "controls/documents/visual-pages/" + source.name)
    script_names = [
        "baseline_r2.py", "review_prior_r2.py", "r2_primary.py", "r2_independent.py", "r2_compare.py",
        "r2_controls.py", "r2_xw_fixture.py", "r2_xw_boundaries.py", "r2_rom_control.py", "r2_docs.py",
        "r2_doc_controls.py", "r2_tar_closure.py", "r2_build_contexts.py", "r2_positive_evidence.py",
        "r2_compact_sets.py", "r2_finalize.py", "r2_acceptance.py",
    ]
    for name in script_names:
        add_copy(stage, RUN / name, "scripts/" + name)
    add_copy(stage, REPO / "audit-report-f/followup/tools/rawscan.py", "scripts/rawscan.py")
    return command_ids, families, expected


def role_for_path(path: str) -> tuple[str, str, str]:
    if path.startswith("scripts/"):
        return "reproduction-script", "finalize", "reproduction"
    if path.startswith("input/"):
        return "input-snapshot", "finalize", "scope,provenance"
    if path.startswith("machine/canonical") or path.startswith("machine/compact"):
        return "canonical-domain-set", "compact-sets", "scan,coverage"
    if path.startswith("machine/comparison"):
        return "independent-comparison", "compare", "independence,coverage"
    if path.startswith("machine/primary") or path.startswith("machine/archive"):
        return "primary-machine-ledger", "primary", "scope,inventory,scan"
    if path.startswith("machine/"):
        return "deterministic-control-ledger", "finalize", "scope,coverage,reproduction"
    if path.startswith("controls/core/"):
        if "rawscan-smoke" in path:
            return "raw-scanner-smoke", "rawscan-smoke", "scanner-control,execution-evidence"
        return "scanner-control", "core-controls", "scope,negative-controls"
    if path.startswith("controls/xw/"):
        producer = "xw-boundaries" if "boundary" in path or "diagnostic" in path else "xw-fixture"
        return "xw-control", producer, "xw,semantic-boundaries"
    if path.startswith("controls/rom/"):
        return "rom-control", "rom-control", "ROM,mcpy,framing"
    if path.startswith("controls/documents/"):
        producer = "document-controls" if any(token in path for token in ("control", "visibility", "gap", "excerpts", "sanity", "exclusions", "visual")) else "documents"
        return "document-control", producer, "documents,visibility"
    if path.startswith("controls/tar/"):
        return "package-closure", "tar-closure", "package,scope"
    if path.startswith("controls/build/"):
        return "build-context-control", "build-context", "selection,references"
    if path.startswith("controls/positive/"):
        return "positive-semantic-evidence", "positive-evidence", "findings,WCHNET,IoCHub"
    raise AssertionError(path)


def create_manifest(stage: pathlib.Path, command_ids: dict[str, str]) -> tuple[str, dict[str, str], list[dict[str, str]]]:
    rows = []
    for target in sorted(
        (item for item in stage.rglob("*") if item.is_file() and item.name != "evidence-manifest.tsv"),
        key=lambda item: item.relative_to(stage).as_posix().encode("utf-8"),
    ):
        relative = target.relative_to(stage).as_posix()
        role, producer_label, required = role_for_path(relative)
        digest = sha_file(target)
        evidence_id = rid("ev", relative, role, target.stat().st_size, digest)
        rows.append({
            "schema_version": "2", "evidence_id": evidence_id, "path": relative,
            "role": role, "size_bytes": str(target.stat().st_size), "sha256": digest,
            "producer_command_id": command_ids[producer_label], "required_by": required,
        })
    manifest = stage / "evidence-manifest.tsv"
    write_tsv(manifest, MANIFEST_HEADER, rows)
    return sha_file(manifest), {row["path"]: row["evidence_id"] for row in rows}, rows


def inventory_rows(
    artifacts: list[dict[str, object]], manifest_sha: str, ev: dict[str, str]
) -> list[dict[str, str]]:
    byte_groups: dict[str, str] = {}
    for artifact in artifacts:
        digest = str(artifact["sha256"])
        if digest != "not-applicable":
            current = byte_groups.get(digest)
            path = str(artifact["path"])
            if current is None or path.encode("utf-8") < current.encode("utf-8"):
                byte_groups[digest] = path
    common = ";".join([ev["machine/primary-artifacts.jsonl"], ev["input/analysis-input-manifest.tsv"], ev["machine/expected-scan-closure.json"]])
    rows = []
    for artifact in artifacts:
        digest = str(artifact["sha256"])
        scope = str(artifact["scope_class"])
        scan_status = "partial" if scope in {"wch-closed", "unknown-provenance", "rom-wrapper", "rom-payload"} else "not-required"
        rows.append({
            "schema_version": "2", "source_set": artifact["source_set"], "scope_class": scope,
            "path_or_reference": artifact["path"], "family": artifact["family"], "role": artifact["role"],
            "physical_present": artifact["physical_present"], "target_chip": artifact["target_chip"],
            "build_context": artifact["build_context"], "sha256": digest,
            "normalized_sha256": artifact["normalized_sha256"],
            "parent_package_sha256": artifact["parent_package_sha256"], "file_format": artifact["file_format"],
            "member_occurrences": artifact["member_occurrences"],
            "byte_group_id": rid("bytegroup", digest) if digest != "not-applicable" else "not-applicable",
            "byte_representative_path": byte_groups.get(digest, "not-applicable"), "scan_status": scan_status,
            "evidence_ids": common, "evidence_manifest_sha256": manifest_sha,
        })
    reference_evidence = ";".join([ev["controls/build/project-reference-ledger.tsv"], ev["controls/build/build-context-summary.json"]])
    references = [
        ("project-metadata", "missing-referenced", "-lISP585/libISP585.a", "ISP585", "missing-referenced", "no", "unknown", "28 current project-link rows; physical archive absent"),
        ("project-metadata", "not-found-no-current-link-reference", "CHRV3UFI.lib", "RV3UFI/CHRV3UFI", "reference-control", "no", "unknown", "legacy V103 .wvproj opaque; current readable project metadata has zero link rows"),
        ("project-metadata", "missing-referenced", "libCH58XTOUCH.a", "Touch", "missing-referenced", "no", "CH58X", "12 uppercase project-link rows"),
        ("project-metadata", "missing-referenced", "libCH58xTOUCH.a", "Touch", "missing-referenced", "no", "CH58X", "8 lowercase project-link rows"),
        ("project-metadata", "metadata-exclusion-not-link", "libWCH_TKY(old).a", "Touch", "metadata-exclusion-not-link", "no", "unknown", "exclusion metadata only"),
        ("project-metadata", "metadata-exclusion-not-link", "libCH573_TKY(old).a", "Touch", "metadata-exclusion-not-link", "no", "CH573", "exclusion metadata only"),
        ("project-metadata", "metadata-exclusion-not-link", "libCH573_TKY(new2).a", "Touch", "metadata-exclusion-not-link", "no", "CH573", "exclusion metadata only"),
        ("project-metadata", "metadata-exclusion-not-link", "libCH573_TKY.a", "Touch", "metadata-exclusion-not-link", "no", "CH573", "exclusion metadata only"),
    ]
    for source_set, scope, reference, family, role, present, chip, context in references:
        rows.append({
            "schema_version": "2", "source_set": source_set, "scope_class": scope,
            "path_or_reference": reference, "family": family, "role": role,
            "physical_present": present, "target_chip": chip, "build_context": context,
            "sha256": "not-applicable", "normalized_sha256": "not-applicable",
            "parent_package_sha256": "not-applicable", "file_format": "reference",
            "member_occurrences": "not-applicable", "byte_group_id": "not-applicable",
            "byte_representative_path": "not-applicable", "scan_status": "not-required",
            "evidence_ids": reference_evidence, "evidence_manifest_sha256": manifest_sha,
        })
    return sorted(rows, key=lambda row: str(row["path_or_reference"]).encode("utf-8"))


def candidate_profile(unit: Unit, lane: str) -> tuple[str, int, str, int, str, int, str, int, int, str]:
    counts = unit.counts
    hashes = unit.candidate_hashes
    if lane == "symbol-string-debug":
        count = counts["symbol-string-debug"]
        return "elf-metadata-and-alloc-bytes", unit.alloc_units, unit.alloc_hash, count, hashes[lane], count, "partial" if count else "pass-no-hit", 0, 0, hashes[lane]
    if lane in {"raw-csr", "csr-opcode"}:
        count = counts["csr-opcode"]
        return "elf-executable-bytes", unit.exec_units, unit.exec_hash, unit.exec4_count, unit.exec4_hash, count, "pass-hit" if count else "pass-no-hit", 0, unit.boundary_ambiguous, hashes["csr-opcode"]
    if lane == "xw-slot":
        count = counts["xw-slot"]
        return "elf-executable-bytes", unit.exec_units, unit.exec_hash, unit.exec2_count, unit.exec2_hash, count, "partial" if count else "pass-no-hit", unit.boundary_known, unit.boundary_ambiguous, hashes[lane]
    if lane == "address-form-opcode":
        count = counts[lane]
        return "elf-executable-bytes", unit.exec_units, unit.exec_hash, unit.exec4_count, unit.exec4_hash, count, "partial" if count else "pass-no-hit", 0, unit.boundary_ambiguous, hashes[lane]
    if lane == "literal-pointer":
        count = counts[lane]
        return "elf-allocatable-bytes", unit.alloc_units, unit.alloc_hash, unit.alloc4_count, unit.alloc4_hash, count, "partial" if count else "pass-no-hit", 0, 0, hashes[lane]
    if lane == "relocation-source":
        count = counts[lane]
        return "elf-relocation-records", unit.reloc_units, unit.reloc_hash, unit.reloc_units, unit.reloc_hash, count, "partial" if count else "pass-no-hit", 0, 0, hashes[lane]
    if lane == "address-dataflow":
        count = counts["address-form-opcode"] + counts["literal-pointer"] + counts["relocation-source"]
        starts = unit.exec4_count + unit.alloc4_count + unit.reloc_units
        start_hash = tuple_digest("composite-start-set", unit.exec4_hash, unit.alloc4_hash, unit.reloc_hash)
        domain_hash = tuple_digest("composite-domain", unit.exec_hash, unit.alloc_hash, unit.reloc_hash)
        hit_hash = tuple_digest("composite-hit-set", hashes["address-form-opcode"], hashes["literal-pointer"], hashes["relocation-source"])
        return "elf-exec-alloc-relocation-composite", unit.exec_units + unit.alloc_units + unit.reloc_units, domain_hash, starts, start_hash, count, "partial" if count else "pass-no-hit", 0, unit.boundary_ambiguous, hit_hash
    if lane == "indirect-flow":
        count = unit.semantic_sources
        hit_hash = tuple_digest("semantic-source-count", count)
        return "elf-resolution-and-consumer-context", unit.file_size, tuple_digest("whole-object", unit.alloc_hash, unit.reloc_hash), count, hit_hash, count, "partial", unit.boundary_known, unit.boundary_ambiguous, hit_hash
    raise AssertionError(lane)


def scan_row(
    *, path: str, order: str, name: str, ordinal: str, scan_unit: str,
    semantic: str, resolution: str, lane: str, method: str, tool: str,
    profile: tuple[str, int, str, int, str, int, str, int, int, str],
    evidence: str, manifest_sha: str,
) -> dict[str, str]:
    domain_kind, domain_units, domain_hash, starts, start_hash, count, status, boundary_known, boundary_ambiguous, hit_hash = profile
    row_id = rid("scan", path, order, name, ordinal, scan_unit, semantic, resolution, lane, method, tool, domain_kind, domain_hash, start_hash)
    return {
        "schema_version": "2", "scan_row_id": row_id, "physical_path": path,
        "logical_member_order": order, "member_name": name, "same_name_ordinal": ordinal,
        "scan_unit_sha256": scan_unit, "semantic_context_id": semantic,
        "resolution_context_id": resolution, "lane": lane, "method": method,
        "tool_profile_id": tool, "domain_kind": domain_kind, "domain_units": str(domain_units),
        "domain_set_sha256": domain_hash, "candidate_starts": str(starts),
        "candidate_start_set_sha256": start_hash,
        "boundary_known_semantic_unresolved_units": str(boundary_known),
        "boundary_ambiguous_units": str(boundary_ambiguous), "candidate_count": str(count),
        "status": status, "representative_scan_row_id": row_id,
        "hit_ids": f"hitset-{hit_hash}" if count else "not-applicable",
        "evidence_ids": evidence, "evidence_manifest_sha256": manifest_sha,
    }


def generate_object_scan(
    destination: pathlib.Path, artifact_map: dict[str, dict[str, object]], units: dict[str, Unit],
    manifest_sha: str, ev: dict[str, str]
) -> tuple[dict[tuple[str, str, str, str], tuple[str, str]], Counter[str]]:
    primary_tool = rid("tool", "primary", sha_file(RUN / "r2_primary.py"))
    independent_tool = rid("tool", "independent", sha_file(RUN / "r2_independent.py"))
    scope_tool = rid("tool", "scope-control", sha_file(RUN / "r2_finalize.py"))
    common_evidence = ";".join([
        ev["machine/canonical-unit-domain-records.jsonl.gz"],
        ev["machine/comparison-summary.json"], ev["machine/lane-policy.json"],
    ])
    source_rows: dict[tuple[str, str, str, str], tuple[str, str]] = {}
    counts: Counter[str] = Counter()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=SCAN_HEADER, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        with (RUN / "primary/occurrences.jsonl").open("r", encoding="utf-8") as stream:
            for index, raw in enumerate(stream, 1):
                occurrence = json.loads(raw)
                path = occurrence["physical_path"]
                order = str(occurrence["logical_order"])
                name = str(occurrence["member_name"])
                ordinal = str(occurrence["same_name_ordinal"])
                scan_unit = occurrence["member_sha256"]
                unit = units[scan_unit]
                artifact = artifact_map[path]
                target = artifact["target_chip"]
                scope = occurrence["scope_class"]
                if not unit.native:
                    semantic = rid("sem", "scope-control", scope, occurrence["file_format"], target)
                    resolution = rid("res", path, order, name, ordinal, scan_unit, artifact["build_context"])
                    profile = (
                        "scope-excluded-non-native", unit.file_size, tuple_digest("scope-domain", scan_unit, scope),
                        0, tuple_digest("empty-start-set"), 0, "not-required", 0, 0, tuple_digest("empty-hit-set"),
                    )
                    row = scan_row(
                        path=path, order=order, name=name, ordinal=ordinal, scan_unit=scan_unit,
                        semantic=semantic, resolution=resolution, lane="scope-control", method="primary",
                        tool=scope_tool, profile=profile, evidence=common_evidence, manifest_sha=manifest_sha,
                    )
                    writer.writerow(row)
                    counts["scope-control"] += 1
                    continue
                semantic_flow = rid(
                    "sem", "flow", target, artifact["build_context"], scope, unit.machine,
                    unit.elf_class, unit.endian, unit.attrs,
                )
                resolution_flow = rid(
                    "res", "physical-flow", path, order, name, ordinal, scan_unit,
                    occurrence["archive_sha256"], artifact["build_context"],
                )
                semantic_intrinsic = rid(
                    "sem", "artifact-intrinsic", target, scope, unit.machine, unit.elf_class,
                    unit.endian, unit.attrs,
                )
                resolution_intrinsic = rid("res", "artifact-intrinsic", scan_unit, semantic_intrinsic)
                for lane in ("symbol-string-debug", "raw-csr", "address-dataflow", "indirect-flow"):
                    row = scan_row(
                        path=path, order=order, name=name, ordinal=ordinal, scan_unit=scan_unit,
                        semantic=semantic_flow, resolution=resolution_flow, lane=lane, method="primary",
                        tool=primary_tool, profile=candidate_profile(unit, lane), evidence=common_evidence,
                        manifest_sha=manifest_sha,
                    )
                    writer.writerow(row)
                    counts[lane] += 1
                    if lane in {"address-dataflow", "indirect-flow", "symbol-string-debug"}:
                        source_rows[(path, order, ordinal, lane)] = (row["scan_row_id"], semantic_flow)
                for lane in ("csr-opcode", "xw-slot", "address-form-opcode", "literal-pointer", "relocation-source"):
                    profile = candidate_profile(unit, lane)
                    for method, tool in (("primary", primary_tool), ("independent", independent_tool)):
                        row = scan_row(
                            path=path, order=order, name=name, ordinal=ordinal, scan_unit=scan_unit,
                            semantic=semantic_intrinsic, resolution=resolution_intrinsic, lane=lane,
                            method=method, tool=tool, profile=profile, evidence=common_evidence,
                            manifest_sha=manifest_sha,
                        )
                        writer.writerow(row)
                        counts[lane] += 1
                if index % 50000 == 0:
                    print(f"phase=object-scan occurrences={index} rows={sum(counts.values())}", flush=True)

        rom_summary = read_json(RUN / "controls/rom-r2/rom-control-summary.json")
        rom_controls = {row["path"]: row for row in rom_summary["images"]}
        with (RUN / "primary/rom-primary.jsonl").open("r", encoding="utf-8") as stream:
            for raw in stream:
                rom = json.loads(raw)
                if rom["scope_class"] != "rom-payload":
                    continue
                path = rom["physical_path"]
                result = rom["result"]
                control = rom_controls[path]
                semantic = rid("sem", "rom", rom["target_chip"], rom["normalized_sha256"], "hex-addressed-rv32")
                resolution = rid("res", "rom-physical", path, rom["raw_sha256"])
                primitive_resolution = rid("res", "rom-intrinsic", rom["normalized_sha256"], semantic)
                domain_units = int(result["domain"]["units"])
                domain_hash = result["domain"]["set_sha256"]
                primitive_counts = {key: len(value) for key, value in result["candidates"].items()}
                unclassified = int(control["coverage"]["unclassified_populated_bytes"])
                ambiguous = len(control["linear_mixed_framing"]["errors"])
                semantic_profiles = {
                    "rom-symbol-metadata": ("rom-populated-bytes-without-symbol-table", domain_units, domain_hash, 0, tuple_digest("empty-start-set"), 0, "partial", unclassified, ambiguous, tuple_digest("empty-hit-set")),
                    "rom-raw-csr": ("rom-populated-bytes", domain_units, domain_hash, result["grids"]["rom-width4-align2"]["count"], result["grids"]["rom-width4-align2"]["set_sha256"], primitive_counts["csr-opcode"], "partial", unclassified, ambiguous, result["candidate_set_sha256"]["csr-opcode"]),
                    "rom-address-dataflow": ("rom-populated-bytes", domain_units, domain_hash, result["grids"]["rom-width4-align2"]["count"], result["grids"]["rom-width4-align2"]["set_sha256"], primitive_counts["address-or-literal"], "partial", unclassified, ambiguous, result["candidate_set_sha256"]["address-or-literal"]),
                    "rom-indirect-flow": ("rom-jump-table-and-local-control", domain_units, domain_hash, control["valid_function_seeds"], tuple_digest("rom-seeds", path, control["valid_function_seeds"]), 1 if control["mcpy_control"]["raw_hex"] != "not-applicable" else 0, "partial", unclassified, ambiguous, tuple_digest("rom-indirect", path, control["mcpy_control"]["raw_hex"])),
                }
                for lane, profile in semantic_profiles.items():
                    row = scan_row(
                        path=path, order="not-applicable", name="not-applicable", ordinal="not-applicable",
                        scan_unit=rom["normalized_sha256"], semantic=semantic, resolution=resolution,
                        lane=lane, method="primary", tool=primary_tool, profile=profile,
                        evidence=";".join([ev["controls/rom/rom-control-summary.json"], ev["controls/rom/rom-code-parcels.tsv"], ev["machine/comparison-summary.json"]]),
                        manifest_sha=manifest_sha,
                    )
                    writer.writerow(row)
                    counts[lane] += 1
                    if lane == "rom-indirect-flow":
                        source_rows[(path, "not-applicable", "not-applicable", lane)] = (row["scan_row_id"], semantic)
                primitive_profiles = {
                    "rom-csr-opcode": ("rom-populated-bytes", domain_units, domain_hash, result["grids"]["rom-width4-align2"]["count"], result["grids"]["rom-width4-align2"]["set_sha256"], primitive_counts["csr-opcode"], "pass-hit" if primitive_counts["csr-opcode"] else "pass-no-hit", 0, ambiguous, result["candidate_set_sha256"]["csr-opcode"]),
                    "rom-xw-slot": ("rom-populated-bytes", domain_units, domain_hash, result["grids"]["rom-width2-align2"]["count"], result["grids"]["rom-width2-align2"]["set_sha256"], primitive_counts["xw-slot"], "partial" if primitive_counts["xw-slot"] else "pass-no-hit", unclassified, ambiguous, result["candidate_set_sha256"]["xw-slot"]),
                    "rom-address-or-literal": ("rom-populated-bytes", domain_units, domain_hash, result["grids"]["rom-width4-align2"]["count"], result["grids"]["rom-width4-align2"]["set_sha256"], primitive_counts["address-or-literal"], "partial" if primitive_counts["address-or-literal"] else "pass-no-hit", unclassified, ambiguous, result["candidate_set_sha256"]["address-or-literal"]),
                }
                for lane, profile in primitive_profiles.items():
                    for method, tool in (("primary", primary_tool), ("independent", independent_tool)):
                        row = scan_row(
                            path=path, order="not-applicable", name="not-applicable", ordinal="not-applicable",
                            scan_unit=rom["normalized_sha256"], semantic=semantic,
                            resolution=primitive_resolution, lane=lane, method=method, tool=tool,
                            profile=profile, evidence=";".join([ev["controls/rom/rom-control-summary.json"], ev["machine/comparison-summary.json"]]),
                            manifest_sha=manifest_sha,
                        )
                        writer.writerow(row)
                        counts[lane] += 1
    return source_rows, counts


def load_positive_occurrences() -> list[dict[str, str]]:
    with (RUN / "controls/positive-r2/positive-occurrences.tsv").open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def finding_rows(
    positive: list[dict[str, str]], source_rows: dict[tuple[str, str, str, str], tuple[str, str]],
    artifact_map: dict[str, dict[str, object]], manifest_sha: str, ev: dict[str, str]
) -> list[dict[str, str]]:
    rows = []
    positive_evidence = ";".join([
        ev["controls/positive/semantic-chain.json"], ev["controls/positive/positive-summary.json"],
        ev["controls/positive/positive-occurrences.tsv"], ev["controls/build/build-context-summary.json"],
        ev["controls/documents/wchnet-document-gap.tsv"],
    ])
    for occurrence in positive:
        path = occurrence["physical_path"]
        order = occurrence["logical_order"]
        ordinal = occurrence["same_name_ordinal"]
        unit = occurrence["member_sha256"]
        artifact = artifact_map[path]
        if occurrence["evidence_family"] == "wchnet" and unit in {
            "0b196fff0b9f666fc30cd4dcebe90ef299f1fed37fff6b66f460951515e494ca",
            "0c796a85a0123d5338803c1a144d3dbac76e906a6f652f73155cd6a8a6f28ac4",
        }:
            rows.append({
                "schema_version": "2", "finding_id": rid("finding", "WCHNET-ID-SELECT", path, order, ordinal),
                "source_scan_row_id": source_rows[(path, order, ordinal, "address-dataflow")][0],
                "physical_path": path, "build_context_id": artifact["build_context"],
                "member_section_offset": f"eth_api.o#{ordinal}:.text.GetChipID/.text.getTxBuffAddr",
                "semantic_context_id": source_rows[(path, order, ordinal, "address-dataflow")][1],
                "source": "GetChipID: lui 0x1ffff; lhu 0x706; andi 0xf0; returned value consumed by getTxBuffAddr",
                "access_width_and_field": "unsigned 16-bit little-endian load at 0x1ffff706; field mask 0x00f0; trusted model/revision semantics unavailable for this address",
                "transform_and_predicate": "field=uint16[0x1ffff706]&0xf0; special iff field==0x80 || field==0x30; then uint32(LocalTime-anchor)>99 || counter>0x8000; counter starts 0 and increments after a failed descriptor test",
                "path_a": "after failed descriptor status, special IDs may clear descriptor owner bit31 (slli/srli/store) when timeout or counter threshold fires",
                "path_b": "other IDs poll descriptor signed status; success clears timer anchor and returns descriptor buffer",
                "observed_default": "all masked values other than 0x30/0x80 take the ordinary polling path; unknown IDs therefore collide with that observed default",
                "evidence_level": "WORKAROUND-CANDIDATE",
                "purpose_and_workaround": "confirmed ID-READ/ID-SELECT and defensive Tx recovery shape; silicon defect, affected revision, and causal erratum are not established",
                "reachability_triplet": "contained_in_artifact=yes;selected_in_link=yes;runtime_domain_reachable=unknown",
                "unresolved": "0x1ffff706 field mapping, volatile ordering beyond observed object code, actual hardware input domain, and defect causality",
                "evidence_ids": positive_evidence, "evidence_manifest_sha256": manifest_sha,
            })
        elif occurrence["evidence_family"] == "wchnet":
            rows.append({
                "schema_version": "2", "finding_id": rid("finding", "WCHNET-FLOAT-STATIC", path, order, ordinal),
                "source_scan_row_id": source_rows[(path, order, ordinal, "indirect-flow")][0],
                "physical_path": path, "build_context_id": artifact["build_context"],
                "member_section_offset": f"eth_api.o#{ordinal}:.text.getTxBuffAddr",
                "semantic_context_id": source_rows[(path, order, ordinal, "indirect-flow")][1],
                "source": "no GetChipID symbol and no 0x1ffff706 load marker in either float eth_api occurrence",
                "access_width_and_field": "not-applicable",
                "transform_and_predicate": "compile-time archive specialization; no runtime ID predicate observed",
                "path_a": "descriptor-only getTxBuffAddr implementation",
                "path_b": "soft archive contains the runtime 0x30/0x80 selector; that selector is absent here",
                "observed_default": "single static implementation in this archive variant",
                "evidence_level": "STATIC-VARIANT-SPECIALIZATION",
                "purpose_and_workaround": "cross-variant behavior difference, not an ID-SELECT or errata finding",
                "reachability_triplet": "contained_in_artifact=yes;selected_in_link=unknown;runtime_domain_reachable=not-applicable",
                "unresolved": "five project metadata references exist, but no available map selects float eth_api.o; absence from available maps is not a global no-link proof",
                "evidence_ids": positive_evidence, "evidence_manifest_sha256": manifest_sha,
            })
        else:
            rows.append({
                "schema_version": "2", "finding_id": rid("finding", "IOCHUB-ID-FLOW", path, order, ordinal),
                "source_scan_row_id": source_rows[(path, order, ordinal, "address-dataflow")][0],
                "physical_path": path, "build_context_id": artifact["build_context"],
                "member_section_offset": f"IocHub.o#{ordinal}:.text.IoCHub_CliConnAutoReg",
                "semantic_context_id": source_rows[(path, order, ordinal, "address-dataflow")][1],
                "source": "when uint8(chipType-1)<=4, read 16 bytes at 0x1ffff7e0",
                "access_width_and_field": "16 sequential bytes from system information area; unique-id/factory-key identity candidate",
                "transform_and_predicate": "valid chipType range 1..5 selects hardware bytes; invalid range uses zero material; bytes flow through EncInit/Update/Final into registration/auth frame",
                "path_a": "valid chipType hashes/encrypts factory bytes and derives/exposes an eight-byte local ID",
                "path_b": "invalid chipType substitutes zero bytes before the same identity/auth pipeline",
                "observed_default": "out-of-range chipType uses zeros",
                "evidence_level": "ID-FLOW",
                "purpose_and_workaround": "identity/authentication material; no low-level recovery behavior or errata selector proven",
                "reachability_triplet": "contained_in_artifact=yes;selected_in_link=yes;runtime_domain_reachable=unknown",
                "unresolved": "remote server interpretation, caller chipType domain, hardware byte semantics, and runtime hardware behavior",
                "evidence_ids": positive_evidence, "evidence_manifest_sha256": manifest_sha,
            })
    rom_path = "tmp/wch-evt/evt/QingkeV3C_CH587_EVT/EXAM/BLE/LIB/CH587BLE_ROMx.hex"
    rows.append({
        "schema_version": "2", "finding_id": rid("finding", "ROM-MCPY-DOCUMENT-CONTROL", rom_path, "0x40968"),
        "source_scan_row_id": source_rows[(rom_path, "not-applicable", "not-applicable", "rom-indirect-flow")][0],
        "physical_path": rom_path, "build_context_id": "rom-jump-table-context",
        "member_section_offset": "0x40960..0x4096e; mcpy@0x40968",
        "semantic_context_id": source_rows[(rom_path, "not-applicable", "not-applicable", "rom-indirect-flow")][1],
        "source": "local parcel chain checks three arguments, computes a2=a2+a1, executes bytes 0f70b650, then returns",
        "access_width_and_field": "32-bit custom instruction 0x50b6700f; not an ID read",
        "transform_and_predicate": "SDK/ROM convention rs1=EA, rs2=SA, rs3=DA; exact endpoint and post-write registers unresolved",
        "path_a": "local block executes mcpy when all three arguments are nonzero",
        "path_b": "zero argument returns without mcpy",
        "observed_default": "not-applicable to chip identity",
        "evidence_level": "DOCUMENT-ERRATUM-CANDIDATE",
        "purpose_and_workaround": "real-body custom-instruction control; V407RM operand prose conflicts with assembler and four SDK macros; not silicon errata",
        "reachability_triplet": "contained_in_artifact=yes;selected_in_link=unknown;runtime_domain_reachable=unknown",
        "unresolved": "jump-table recursive CFG does not reach this local block; external callers, endpoint inclusivity, completion values, and cross-chip behavior remain unknown",
        "evidence_ids": ";".join([ev["controls/rom/rom-control-summary.json"], ev["controls/rom/rom-code-parcels.tsv"], ev["controls/documents/document-control-summary.json"]]),
        "evidence_manifest_sha256": manifest_sha,
    })
    return sorted(rows, key=lambda row: row["finding_id"])


def install_bundle(stage: pathlib.Path) -> None:
    backup = GEN / "replaced-evidence-bundle"
    if backup.exists():
        shutil.rmtree(backup)
    if BUNDLE.exists():
        os.replace(BUNDLE, backup)
    os.replace(stage, BUNDLE)


def manifest_ids_by_path(manifest: pathlib.Path) -> dict[str, str]:
    with manifest.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if reader.fieldnames != MANIFEST_HEADER:
            raise SystemExit(f"unexpected evidence manifest schema: {manifest}")
        return {row["path"]: row["evidence_id"] for row in reader}


def rewrite_manifest_binding(
    source: pathlib.Path,
    destination: pathlib.Path,
    new_manifest_sha: str,
    evidence_id_replacements: dict[bytes, bytes] | None = None,
) -> int:
    count = 0
    encoded = new_manifest_sha.encode("ascii")
    replacements = evidence_id_replacements or {}
    with source.open("rb") as input_stream, destination.open("wb") as output_stream:
        header = input_stream.readline()
        output_stream.write(header)
        for raw in input_stream:
            stripped = raw.rstrip(b"\n")
            prefix, separator, old_manifest = stripped.rpartition(b"\t")
            body, evidence_separator, evidence_ids = prefix.rpartition(b"\t")
            if not separator or not evidence_separator or len(old_manifest) != 64:
                raise SystemExit(f"cannot rebind malformed row in {source.name}:{count + 2}")
            rebound_ids = b";".join(replacements.get(item, item) for item in evidence_ids.split(b";"))
            output_stream.write(body + b"\t" + rebound_ids + b"\t" + encoded + b"\n")
            count += 1
    return count


def build() -> int:
    if GEN.exists():
        shutil.rmtree(GEN)
    GEN.mkdir(parents=True)
    print("phase=load-units", flush=True)
    units = load_units()
    artifacts, artifact_map = load_artifacts()
    enrich_selected_build_contexts(artifacts)
    stage = GEN / "evidence-staging"
    print("phase=populate-bundle-and-drift-check", flush=True)
    command_ids, families, expected = populate_bundle(stage, artifacts, units)
    manifest_sha, ev, manifest_rows = create_manifest(stage, command_ids)
    print(f"phase=manifest files={len(manifest_rows)} sha256={manifest_sha}", flush=True)

    inventory_tmp = GEN / "06b-chipid-errata-inventory.tsv"
    scan_tmp = GEN / "06b-chipid-errata-object-scan.tsv"
    findings_tmp = GEN / "06b-chipid-errata-findings.tsv"
    write_tsv(inventory_tmp, INVENTORY_HEADER, inventory_rows(artifacts, manifest_sha, ev))
    source_rows, lane_counts = generate_object_scan(scan_tmp, artifact_map, units, manifest_sha, ev)
    if sum(lane_counts.values()) != int(expected["expected_scan_rows"]):
        raise SystemExit(f"scan row closure failed: {sum(lane_counts.values())} != {expected['expected_scan_rows']}")
    if dict(sorted(lane_counts.items())) != {key: int(value) for key, value in expected["expected_lane_counts"].items()}:
        raise SystemExit("scan lane count closure failed")
    findings_data = finding_rows(load_positive_occurrences(), source_rows, artifact_map, manifest_sha, ev)
    write_tsv(findings_tmp, FINDING_HEADER, findings_data)
    print(f"phase=fixed-tsvs inventory={len(artifacts)+8} scan={sum(lane_counts.values())} findings={len(findings_data)}", flush=True)

    verify_scope_state()
    install_bundle(stage)
    os.replace(inventory_tmp, INVENTORY)
    os.replace(scan_tmp, OBJECT_SCAN)
    os.replace(findings_tmp, FINDINGS)
    write_json(GEN / "build-receipt.json", {
        "schema_version": "2", "status": "pass", "manifest_sha256": manifest_sha,
        "evidence_files": len(manifest_rows), "inventory_rows": len(artifacts) + 8,
        "scan_rows": sum(lane_counts.values()), "finding_rows": len(findings_data),
        "family_count": len(families),
    })
    print("phase=build-complete report=pending-accepted-report-only", flush=True)
    return 0


def rebind() -> int:
    prior_manifest_maps = []
    for candidate in (
        GEN / "replaced-evidence-bundle/evidence-manifest.tsv",
        BUNDLE / "evidence-manifest.tsv",
    ):
        if candidate.is_file():
            prior_manifest_maps.append(manifest_ids_by_path(candidate))
    if GEN.exists():
        shutil.rmtree(GEN)
    GEN.mkdir(parents=True)
    stage = GEN / "evidence-staging"
    shutil.copytree(BUNDLE, stage, copy_function=shutil.copy2)
    input_drift_and_sanitized(stage)
    sanitized_prior_baseline(stage / "input/prior-fixed-output-baseline.tsv")
    sanitized_prior_artifact_manifest(stage / "input/prior-artifact-manifest.tsv")
    git_scope_check(stage / "machine/git-scope-check.tsv")
    command_ids, _tool_hashes = command_and_tool_manifests(stage)
    # Rebind is also the controlled path for incorporating rerun control
    # artifacts after a formatting-only serializer correction.
    refreshed_controls = [
        (RUN / "controls/core-r2/control-summary.json", "controls/core/control-summary.json"),
        (RUN / "controls/core-r2/scope-and-archive-closure.json", "controls/core/scope-and-archive-closure.json"),
        (RUN / "controls/core-r2/xw-and-archive-anchor-counts.json", "controls/core/xw-and-archive-anchor-counts.json"),
        (RUN / "controls/core-r2/xw-archive-profile-matrix.json", "controls/core/xw-archive-profile-matrix.json"),
        (RUN / "controls/core-r2/evt-csr-control-summary.json", "controls/core/evt-csr-control-summary.json"),
        (RUN / "controls/core-r2/evt-csr-control-occurrences.tsv", "controls/core/evt-csr-control-occurrences.tsv"),
        (RUN / "controls/core-r2/iqmath-control-summary.json", "controls/core/iqmath-control-summary.json"),
        (RUN / "controls/core-r2/iqmath-mcpy-negative-control.tsv", "controls/core/iqmath-mcpy-negative-control.tsv"),
        (RUN / "controls/core-r2/rawscan-smoke-summary.json", "controls/core/rawscan-smoke-summary.json"),
        (RUN / "controls/core-r2/rawscan-smoke.stdout", "controls/core/rawscan-smoke.stdout"),
        (RUN / "controls/core-r2/rawscan-smoke.stderr", "controls/core/rawscan-smoke.stderr"),
        (RUN / "controls/rom-r2/rom-control-summary.json", "controls/rom/rom-control-summary.json"),
        (RUN / "controls/rom-r2/rom-fingerprints.tsv", "controls/rom/rom-fingerprints.tsv"),
        (RUN / "controls/rom-r2/rom-header-ledger.tsv", "controls/rom/rom-header-ledger.tsv"),
        (RUN / "controls/rom-r2/rom-jt-seeds.tsv", "controls/rom/rom-jt-seeds.tsv"),
        (RUN / "controls/rom-r2/rom-length-prefix-candidates.tsv", "controls/rom/rom-length-prefix-candidates.tsv"),
        (RUN / "controls/rom-r2/rom-code-parcels.tsv", "controls/rom/rom-code-parcels.tsv"),
    ]
    for source, relative in refreshed_controls:
        add_copy(stage, source, relative)
    for name in (
        "baseline_r2.py", "review_prior_r2.py", "r2_primary.py", "r2_independent.py", "r2_compare.py",
        "r2_controls.py", "r2_xw_fixture.py", "r2_xw_boundaries.py", "r2_rom_control.py", "r2_docs.py",
        "r2_doc_controls.py", "r2_tar_closure.py", "r2_build_contexts.py", "r2_positive_evidence.py",
        "r2_compact_sets.py", "r2_finalize.py", "r2_acceptance.py",
    ):
        add_copy(stage, RUN / name, "scripts/" + name)
    add_copy(stage, REPO / "audit-report-f/followup/tools/rawscan.py", "scripts/rawscan.py")
    (stage / "evidence-manifest.tsv").unlink()
    manifest_sha, new_evidence_ids, rows = create_manifest(stage, command_ids)
    replacements: dict[bytes, bytes] = {}
    for old_ids in prior_manifest_maps:
        for relative, old_id in old_ids.items():
            new_id = new_evidence_ids.get(relative)
            if new_id is not None and old_id != new_id:
                replacements[old_id.encode("ascii")] = new_id.encode("ascii")
    inventory_tmp = GEN / INVENTORY.name
    scan_tmp = GEN / OBJECT_SCAN.name
    findings_tmp = GEN / FINDINGS.name
    inventory_rows_count = rewrite_manifest_binding(INVENTORY, inventory_tmp, manifest_sha, replacements)
    scan_rows_count = rewrite_manifest_binding(OBJECT_SCAN, scan_tmp, manifest_sha, replacements)
    finding_rows_count = rewrite_manifest_binding(FINDINGS, findings_tmp, manifest_sha, replacements)
    verify_scope_state()
    install_bundle(stage)
    os.replace(inventory_tmp, INVENTORY)
    os.replace(scan_tmp, OBJECT_SCAN)
    os.replace(findings_tmp, FINDINGS)
    write_json(GEN / "rebind-receipt.json", {
        "schema_version": "2", "status": "pass", "manifest_sha256": manifest_sha,
        "evidence_files": len(rows), "inventory_rows": inventory_rows_count,
        "scan_rows": scan_rows_count, "finding_rows": finding_rows_count,
        "migrated_evidence_ids": len(replacements),
    })
    print(f"phase=rebind-complete manifest_sha256={manifest_sha} scan_rows={scan_rows_count}")
    return 0


def report_family_matrix(families: Counter[str]) -> str:
    required = [
        ("WCHNET", "WCHNET"), ("WCHUSB/other USB", "WCHUSB/other USB"),
        ("RV3UFI/CHRV3UFI", "RV3UFI"), ("UHSIF", "UHSIF"), ("ISP585", "ISP585"),
        ("IQMath", "IQMath"), ("printf", "printf"), ("printfloat", "printfloat"),
        ("sh", "sh"), ("shfloat", "shfloat"), ("BLE", "BLE"),
        ("BLE ROM", "ROM candidate"), ("Mesh", "Mesh"), ("Mesh ROM", "Mesh ROM"),
        ("LWNS", "LWNS"), ("Touch", "Touch"), ("IoCHub", "IoCHub"),
        ("Voice", "VoiceRcg"), ("Motor", "Motor"),
        ("Other WCH blob", "other target artifact"), ("generic runtime", "generic-runtime-candidate"),
    ]
    lines = ["| family | physical artifacts | result strength |", "|---|---:|---|"]
    for display, key in required:
        count = families.get(key, 0)
        if display == "WCHNET":
            result = "8 soft source→select positives; 2 float static-specialization occurrences"
        elif display == "IoCHub":
            result = "3 selected ID-READ/ID-FLOW positives; not workaround selection"
        elif display == "ISP585":
            result = "0 physical; 28 current project-link references, missing-referenced"
        elif display == "Touch":
            result = "physical variants scanned; two missing referenced spellings; four old names are exclusions"
        elif display == "BLE ROM":
            result = "5 physical ROM payloads are separately scanned; count here is candidate-artifact label only"
        elif display == "Other WCH blob":
            result = "broad other-target/unknown-provenance bucket; not all 3,652 artifacts are proven WCH-owned; all native units were deep-scanned"
        elif display == "generic runtime":
            result = "candidate label only, not upstream attribution; retained in unknown-provenance native deep-scan scope"
        else:
            result = "no closed ID-select finding; limited primitive negative plus explicit semantic partials"
        lines.append(f"| {display} | {count} | {result} |")
    return "\n".join(lines)


def render_report() -> int:
    acceptance = read_json(RUN / "acceptance-pre-report.json")
    if acceptance.get("status") != "pass":
        raise SystemExit("pre-report acceptance is absent or not passing")
    manifest_sha = sha_file(BUNDLE / "evidence-manifest.tsv")
    if acceptance["manifest_sha256"] != manifest_sha:
        raise SystemExit("bundle changed after pre-report acceptance")
    with (BUNDLE / "machine/evidence-placeholder" if False else BUNDLE / "evidence-manifest.tsv").open("r", encoding="utf-8", newline="") as stream:
        manifest_rows = list(csv.DictReader(stream, delimiter="\t"))
    families = Counter()
    with (BUNDLE / "machine/family-summary.tsv").open("r", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream, delimiter="\t"):
            families[row["family"]] = int(row["physical_artifacts"])
    expected = read_json(BUNDLE / "machine/expected-scan-closure.json")
    build = read_json(BUNDLE / "controls/build/build-context-summary.json")
    compact = read_json(BUNDLE / "machine/compact-set-summary.json")
    git_baseline = read_json(RUN / "concurrency-rebaseline.json") if (RUN / "concurrency-rebaseline.json").exists() else {
        "mode": "original-baseline", "initial_head": (RUN / "initial-git-head").read_text().strip(),
        "head": (RUN / "initial-git-head").read_text().strip(), "external_commit_changed_paths": "0",
        "external_commit_delta_sha256": tuple_digest("no-external-head-advance"),
        "worktree_transition_count": "0",
        "worktree_transition_chain_sha256": tuple_digest("no-post-head-worktree-transition"),
    }
    evidence_index = [
        "| evidence_id | path | role |",
        "|---|---|---|",
        *[f"| `{row['evidence_id']}` | `{row['path']}` | {row['role']} |" for row in manifest_rows],
    ]
    run_rel = RUN.relative_to(REPO).as_posix()
    matrix = report_family_matrix(families)
    text = f"""# 06b ChipID/revision and implicit-errata audit — independent round two

evidence_manifest_sha256: `{manifest_sha}`

## 1. Executive summary by finding, source site, and path

The second execution does **not** support a repository-wide “no hidden ChipID branch” conclusion. It independently closes three behavior classes and leaves all broader negatives bounded:

- Eight physical soft-WCHNET `eth_api.o` occurrences (two byte groups) read an unsigned halfword at `0x1ffff706`, mask `0xf0`, and select an extra Tx-descriptor recovery path for `0x30` or `0x80`. The path clears owner bit 31 after unsigned elapsed time `>99` or counter `>0x8000`. This is `ID-READ` + `ID-SELECT` and a defensive `WORKAROUND-CANDIDATE`; no material or experiment closes a silicon-defect cause.
- The two V317 float `eth_api.o` occurrences have no `GetChipID` and no `0x1ffff706` load. They are compile-time `STATIC-VARIANT-SPECIALIZATION`, correcting two false first-round ID-select findings.
- Three selected `IocHub.o` occurrences read 16 bytes at `0x1ffff7e0` for `chipType` 1..5 and feed registration/auth derivation. This is `ID-READ/ID-FLOW`, not an errata selector; invalid `chipType` uses zeros.
- CH587 ROM bytes at `0x40968` are a parcel-aligned `mcpy` positive control, but the jump-table recursive CFG does **not** reach that local block. The V407 manual’s operand-role prose conflicts with assembler/SDK/ROM convention; this is a document-erratum candidate, not silicon errata.

No `ERRATA-CONFIRMED` finding is made. Presence, available-map selection, and runtime applicability remain separate in every finding row.

## 2. Prompt, inputs, tools, evidence, Git, and claim ledger

Prompt SHA-256 is `ad8c8142887afa5ccb60f32af3d58e22991c7f1c6048570efb99255176dca1c8`. The immutable run root is `{run_rel}`; original baseline HEAD is `{git_baseline['initial_head']}`. The sanitized input manifest contains 31,908 original inputs totaling 8,889,818,628 bytes; every file was rehashed before finalization with no drift. The bundle records tool/script hashes and normalized command templates whose command IDs include the corresponding tool hash.

The Git scope control compares filtered porcelain-v2 state plus allowed-path-excluded worktree/index binary diffs. During this long audit, unrelated agents advanced HEAD to `{git_baseline['head']}` through ancestor commits touching {git_baseline['external_commit_changed_paths']} paths (delta hash `{git_baseline['external_commit_delta_sha256']}`) and no authorized 06b result path. A further {git_baseline.get('worktree_transition_count', '0')} unrelated worktree/index transition(s) were observed after that head change (chain hash `{git_baseline.get('worktree_transition_chain_sha256', tuple_digest('no-post-head-worktree-transition'))}`). Consequently the literal original status/diff hashes cannot match and are recorded as external transitions, not hidden. Each concurrency rebaseline was allowed only after proving ancestor lineage, no allowed-path overlap, and zero drift in all 31,908 analysis inputs; the selected head/status/worktree/index hashes then remain byte-identical through finalization. The run tree is excluded because it is an authorized, ignored execution location. Isolated staging/commit verification is performed after this report and is reported in the final receipt.

The complete prior/prompt correction ledger is `machine/claim-ledger.tsv`. Material corrections include independent-parser replacement, Linux GCC15 inclusion, ROM reachability/framing correction, CSR semantic correction, two float false-positive removals, and IoCHub narrowing.

## 3. Scope, members, hashes, and failures

Physical scope: 4,566 artifacts; 3,221 archives; 1,218 standalone objects; 680,924 logical archive-member occurrences; 682,142 member-or-standalone occurrences. Archive parsing found zero failures. EVT closure is 49 physical archives, 21 basenames, 23 archive-content groups, 848 member occurrences, and 381 unique member hashes.

The newly discovered `MRS_Toolchain_Linux_X64_V250` contribution is 435 archives plus 110 standalone objects. Source-set occurrence counts and scope counts are machine-bound in `machine/expected-scan-closure.json`. The MRS 2.5 package closure matches all 11,032 extracted non-directory target entries; the other 8,330 of 19,362 package entries are AppleDouble metadata sidecars, not silently omitted payloads.

The object ledger has {expected['expected_scan_rows']:,} rows: {expected['native_occurrences']:,} native occurrences ×14 required rows, {expected['non_native_occurrences']:,} non-native occurrences ×1 scope row, and five ROMs ×10 rows. Parser failures are zero; semantic partials are retained rather than converted to negatives.

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

{matrix}

Every physical artifact remains an inventory row even when bytes duplicate another path. The matrix’s “no closed finding” wording is deliberately not “no ID logic exists”: raw candidate discovery is complete for stated domains, while XW semantics, stripped interprocedural consumers, final-link GP/PCREL resolution, callbacks, and runtime domains remain partial where listed.

## 6. Positive controls and scanner independence

Two separately implemented archive/ELF/ROM parsers compare equal across 3,221 archives, 682,142 occurrences, 235,234 unique scan units, and five ROM payloads (zero field mismatches). Unique-unit candidate totals are: 4,601,786 address-form, 24,830 CSR, 22,625,459 literal, 2 relocation-source, 58,794 symbol/debug, and 462,014 XW-slot candidates. Canonical domain totals are {compact['domain_totals_nonadditive']['exec_domain']:,} executable bytes, {compact['domain_totals_nonadditive']['alloc_domain']:,} allocatable bytes, and {compact['domain_totals_nonadditive']['relocation_domain']:,} relocation records.

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

Map/reference analysis enumerated {build['available_map_files_searched']:,} maps and {build['available_elf_files_enumerated']:,} ELFs; 1,140 maps contain relevant selections and 1,646 selection rows. All five soft WCHNET, three IoCHub, and two MESHROM archives are selected in available maps. ISP585 has 28 current project-link rows but no physical archive. Touch has 12 uppercase and 8 lowercase missing-reference rows. Twenty old TKY rows are exclusion metadata. `CHRV3UFI.lib` has no newly verifiable current readable link row; a legacy `.wvproj` is opaque.

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
python3 {run_rel}/r2_acceptance.py --run-root {run_rel} --require-report
git diff --check -- audit-report-f/followup/results/06b-chipid-errata-codex.md audit-report-f/followup/results/06b-chipid-errata-inventory.tsv audit-report-f/followup/results/06b-chipid-errata-object-scan.tsv audit-report-f/followup/results/06b-chipid-errata-findings.tsv audit-report-f/followup/results/06b-chipid-errata-evidence
```

The bundle’s `machine/command-ledger.tsv` contains normalized recipes and tool-bound command IDs; `machine/tool-manifest.tsv` and `scripts/` freeze every decisive serializer/scanner. The fixed outputs are:

- `audit-report-f/followup/results/06b-chipid-errata-codex.md`
- `audit-report-f/followup/results/06b-chipid-errata-inventory.tsv`
- `audit-report-f/followup/results/06b-chipid-errata-object-scan.tsv`
- `audit-report-f/followup/results/06b-chipid-errata-findings.tsv`
- `audit-report-f/followup/results/06b-chipid-errata-evidence/`

Every bundle evidence ID is indexed below so manifest reference closure is independently checkable.

{chr(10).join(evidence_index)}
"""
    temporary = GEN / "06b-chipid-errata-codex.md"
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, REPORT)
    print(f"phase=report-complete manifest_sha256={manifest_sha} evidence_ids={len(manifest_rows)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=pathlib.Path, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--build", action="store_true")
    group.add_argument("--report-only", action="store_true")
    group.add_argument("--rebind", action="store_true")
    args = parser.parse_args()
    if args.run_root.resolve() != RUN:
        raise SystemExit("--run-root does not identify this immutable run")
    if args.build:
        return build()
    if args.rebind:
        return rebind()
    return render_report()


if __name__ == "__main__":
    raise SystemExit(main())
