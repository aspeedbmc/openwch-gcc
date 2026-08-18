#!/usr/bin/env python3
"""Strictly compare primary and independent occurrence/domain/start/hit sets."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
from collections import Counter
from typing import Iterator


def rows(path: pathlib.Path) -> Iterator[dict]:
    with path.open("r", encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"invalid JSON {path}:{number}: {exc}")


def compact_primary(row: dict) -> dict:
    out = {
        key: row.get(key)
        for key in (
            "scan_unit_sha256", "file_size", "magic", "elf_valid", "elf_errors",
            "elf_class", "endian", "etype", "machine", "native_scan_applicable",
            "coverage", "semantic_sources",
        )
    }
    if row.get("native_scan_applicable"):
        out["attrs_sha256"] = hashlib.sha256(bytes.fromhex(row.get("attrs_hex", ""))).hexdigest()
        out["exec_domain"] = row["exec_domain"]
        out["alloc_domain"] = row["alloc_domain"]
        out["relocation_domain"] = row["relocation_domain"]
        out["grids"] = row["grids"]
        out["candidate_counts"] = {name: len(items) for name, items in row["candidates"].items()}
        out["candidate_set_sha256"] = row["candidate_set_sha256"]
    return out


def unit_diff(primary: dict, independent: dict) -> list[str]:
    failures: list[str] = []
    for key in (
        "scan_unit_sha256", "file_size", "magic", "elf_valid", "elf_class",
        "endian", "etype", "machine", "native_scan_applicable",
    ):
        if primary.get(key) != independent.get(key):
            failures.append(key)
    if not primary.get("native_scan_applicable") or not independent.get("native_scan_applicable"):
        return failures
    for domain in ("exec_domain", "alloc_domain", "relocation_domain"):
        for key in ("units", "set_sha256", "records"):
            if primary[domain].get(key) != independent[domain].get(key):
                failures.append(f"{domain}.{key}")
    if primary.get("grids") != independent.get("grids"):
        for grid in sorted(set(primary.get("grids", {})) | set(independent.get("grids", {}))):
            if primary.get("grids", {}).get(grid) != independent.get("grids", {}).get(grid):
                failures.append(f"grids.{grid}")
    pc = {name: len(items) for name, items in primary["candidates"].items() if name != "symbol-string-debug"}
    if pc != independent.get("candidate_counts"):
        for lane in sorted(set(pc) | set(independent.get("candidate_counts", {}))):
            if pc.get(lane) != independent.get("candidate_counts", {}).get(lane):
                failures.append(f"candidate_counts.{lane}")
    ps = {name: value for name, value in primary["candidate_set_sha256"].items() if name != "symbol-string-debug"}
    if ps != independent.get("candidate_set_sha256"):
        for lane in sorted(set(ps) | set(independent.get("candidate_set_sha256", {}))):
            if ps.get(lane) != independent.get("candidate_set_sha256", {}).get(lane):
                failures.append(f"candidate_set_sha256.{lane}")
    return failures


def occurrence_identity(row: dict) -> dict:
    return {
        key: row.get(key)
        for key in (
            "physical_path", "logical_order", "member_name", "same_name_ordinal",
            "member_sha256", "member_size", "file_format", "machine", "elf_class",
        )
    }


def compare_rom(primary: dict, independent: dict) -> list[str]:
    failures: list[str] = []
    result = primary["result"]
    for key in ("raw_sha256", "normalized_sha256"):
        pv = primary.get(key)
        iv = independent.get(key)
        if pv != iv:
            failures.append(key)
    if result["domain"] != independent["domain"]:
        failures.append("domain")
    if result["grids"] != independent["grids"]:
        failures.append("grids")
    pcounts = {name: len(items) for name, items in result["candidates"].items()}
    if pcounts != independent["candidate_counts"]:
        failures.append("candidate_counts")
    if result["candidate_set_sha256"] != independent["candidate_set_sha256"]:
        failures.append("candidate_set_sha256")
    if result["ranges"] != independent["ranges"]:
        failures.append("ranges")
    if bool(result["parse_errors"]) != bool(independent["parse_errors"]):
        failures.append("parse_error_presence")
    return failures


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-root", required=True)
    ns = ap.parse_args()
    run = pathlib.Path(ns.run_root)
    primary_dir = run / "primary"
    independent_dir = run / "independent"
    output = run / "comparison"
    output.mkdir(parents=True, exist_ok=True)
    mismatches: list[dict] = []
    mismatch_fields: Counter[str] = Counter()
    compact_path = output / "primary-unit-compact.jsonl.new-r2"
    primary_iter = rows(primary_dir / "unit-primary.jsonl")
    independent_iter = rows(independent_dir / "unit-independent.jsonl")
    unit_count = 0
    native_count = 0
    candidate_totals: Counter[str] = Counter()
    domain_totals: Counter[str] = Counter()
    relevant_sources: list[dict] = []
    with compact_path.open("w", encoding="utf-8", newline="\n") as compact_out:
        while True:
            try:
                p = next(primary_iter)
            except StopIteration:
                p = None
            try:
                i = next(independent_iter)
            except StopIteration:
                i = None
            if p is None and i is None:
                break
            unit_count += 1
            if p is None or i is None:
                mismatch = {"kind": "unit-length", "primary": p and p.get("scan_unit_sha256"), "independent": i and i.get("scan_unit_sha256")}
                mismatches.append(mismatch)
                mismatch_fields["unit-length"] += 1
                continue
            diff = unit_diff(p, i)
            if diff:
                mismatches.append({"kind": "unit", "scan_unit_sha256": p.get("scan_unit_sha256"), "fields": diff})
                mismatch_fields.update(diff)
            c = compact_primary(p)
            compact_out.write(json.dumps(c, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
            if p.get("native_scan_applicable"):
                native_count += 1
                for lane, items in p["candidates"].items():
                    candidate_totals[lane] += len(items)
                domain_totals["exec_bytes"] += p["exec_domain"]["units"]
                domain_totals["alloc_bytes"] += p["alloc_domain"]["units"]
                domain_totals["relocation_entries"] += p["relocation_domain"]["units"]
                for source in p.get("semantic_sources", []):
                    if source.get("kind") == "identity-csr-read" or source.get("address") in {
                        "0x1ffff704", "0x1ffff706", "0x1ffff7c4", "0x1ffff7e0", "0x1ffff884"
                    }:
                        relevant_sources.append({"scan_unit_sha256": p["scan_unit_sha256"], **source})
            if unit_count % 50000 == 0:
                print(f"phase=compare-units rows={unit_count} mismatches={len(mismatches)}", flush=True)
    os.replace(compact_path, output / "primary-unit-compact.jsonl")

    occurrence_count = 0
    po = rows(primary_dir / "occurrences.jsonl")
    io = rows(independent_dir / "occurrences.jsonl")
    while True:
        try:
            p = next(po)
        except StopIteration:
            p = None
        try:
            i = next(io)
        except StopIteration:
            i = None
        if p is None and i is None:
            break
        occurrence_count += 1
        if p is None or i is None:
            mismatches.append({"kind": "occurrence-length", "primary": p and occurrence_identity(p), "independent": i and occurrence_identity(i)})
            mismatch_fields["occurrence-length"] += 1
            continue
        pi, ii = occurrence_identity(p), occurrence_identity(i)
        if pi != ii:
            fields = [key for key in pi if pi.get(key) != ii.get(key)]
            mismatches.append({"kind": "occurrence", "row": occurrence_count, "fields": fields, "primary": pi, "independent": ii})
            mismatch_fields.update(f"occurrence.{x}" for x in fields)
        if occurrence_count % 200000 == 0:
            print(f"phase=compare-occurrences rows={occurrence_count} mismatches={len(mismatches)}", flush=True)

    # Archive structural counters are compared per physical path.  Parser
    # diagnostic wording is deliberately not required to match.
    archive_count = 0
    pa = rows(primary_dir / "archive-summary.jsonl")
    ia = rows(independent_dir / "archive-summary.jsonl")
    for p, i in zip(pa, ia):
        archive_count += 1
        fields = []
        mapping = {
            "physical_path": "physical_path", "archive_sha256": "archive_sha256",
            "thin": "thin", "raw_record_count": "raw_record_count",
            "archive_metadata_records": "archive_metadata_records",
            "member_occurrences": "member_occurrences", "trailing_bytes": "trailing_bytes",
        }
        for pk, ik in mapping.items():
            if p.get(pk) != i.get(ik):
                fields.append(pk)
        if bool(p.get("parser_errors")) != bool(i.get("errors")):
            fields.append("parser_error_presence")
        if fields:
            mismatches.append({"kind": "archive", "physical_path": p.get("physical_path"), "fields": fields})
            mismatch_fields.update(f"archive.{x}" for x in fields)

    primary_rom = {r["physical_path"]: r for r in rows(primary_dir / "rom-primary.jsonl") if r["scope_class"] == "rom-payload"}
    independent_rom = {r["physical_path"]: r for r in rows(independent_dir / "rom-independent.jsonl")}
    for path in sorted(set(primary_rom) | set(independent_rom)):
        if path not in primary_rom or path not in independent_rom:
            fields = ["path-presence"]
        else:
            fields = compare_rom(primary_rom[path], independent_rom[path])
        if fields:
            mismatches.append({"kind": "rom", "physical_path": path, "fields": fields})
            mismatch_fields.update(f"rom.{x}" for x in fields)

    mismatch_tmp = output / "mismatches.jsonl.new-r2"
    mismatch_tmp.write_text("".join(json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for x in mismatches), encoding="utf-8", newline="\n")
    os.replace(mismatch_tmp, output / "mismatches.jsonl")
    source_tmp = output / "relevant-semantic-sources.jsonl.new-r2"
    source_tmp.write_text("".join(json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for x in relevant_sources), encoding="utf-8", newline="\n")
    os.replace(source_tmp, output / "relevant-semantic-sources.jsonl")
    summary = {
        "schema_version": "2",
        "status": "pass" if not mismatches else "failed",
        "unit_rows_compared": unit_count,
        "native_unique_units": native_count,
        "occurrence_rows_compared": occurrence_count,
        "archive_rows_compared": archive_count,
        "rom_payloads_compared": len(set(primary_rom) | set(independent_rom)),
        "mismatch_count": len(mismatches),
        "mismatch_fields": dict(sorted(mismatch_fields.items())),
        "unique_unit_candidate_totals": dict(sorted(candidate_totals.items())),
        "unique_unit_domain_totals_nonphysical_nonadditive": dict(sorted(domain_totals.items())),
        "relevant_semantic_source_count": len(relevant_sources),
    }
    temp = output / "summary.json.new-r2"
    temp.write_text(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")
    os.replace(temp, output / "summary.json")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0 if not mismatches else 1


if __name__ == "__main__":
    raise SystemExit(main())
