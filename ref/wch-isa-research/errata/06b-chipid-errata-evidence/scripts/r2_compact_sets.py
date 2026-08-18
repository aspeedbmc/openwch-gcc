#!/usr/bin/env python3
"""Strip canonical unit records to the fields needed by final serialization."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import pathlib
from collections import Counter


def sha_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", required=True)
    args = parser.parse_args()
    repo = pathlib.Path.cwd().resolve()
    run = (repo / args.run_root).resolve()
    source = run / "comparison" / "primary-unit-compact.jsonl"
    out = run / "controls" / "compact-r2"
    out.mkdir(parents=True, exist_ok=True)
    target = out / "unit-domain-summary.jsonl"
    canonical_gzip = out / "canonical-unit-domain-records.jsonl.gz"

    rows = 0
    native = 0
    duplicate = 0
    seen: set[str] = set()
    machines: Counter[str] = Counter()
    candidate_totals: Counter[str] = Counter()
    domain_totals: Counter[str] = Counter()
    with source.open("rb") as src_raw, target.open("w", encoding="utf-8", newline="\n") as dst, canonical_gzip.open("wb") as gz_raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=gz_raw, compresslevel=9, mtime=0) as gz:
          for raw_line in src_raw:
            gz.write(raw_line)
            line = raw_line.decode("utf-8")
            row = json.loads(line)
            unit = str(row["scan_unit_sha256"])
            if unit in seen:
                duplicate += 1
                continue
            seen.add(unit)
            rows += 1
            applicable = bool(row["native_scan_applicable"])
            native += applicable
            machines[str(row["machine"])] += 1
            candidate_counts = row.get("candidate_counts") or {}
            candidate_hashes = row.get("candidate_set_sha256") or {}
            for key, value in candidate_counts.items():
                candidate_totals[key] += int(value)
            for key in ("exec_domain", "alloc_domain", "relocation_domain"):
                if row.get(key):
                    domain_totals[key] += int(row[key]["units"])
            compact = {
                "scan_unit_sha256": unit,
                "file_size": row["file_size"],
                "magic": row["magic"],
                "elf_valid": row["elf_valid"],
                "elf_class": row["elf_class"],
                "endian": row["endian"],
                "etype": row["etype"],
                "machine": row["machine"],
                "native_scan_applicable": applicable,
                "attrs_sha256": row.get("attrs_sha256", "not-applicable"),
                "exec_domain": ({"units": row["exec_domain"]["units"], "set_sha256": row["exec_domain"]["set_sha256"]} if row.get("exec_domain") else None),
                "alloc_domain": ({"units": row["alloc_domain"]["units"], "set_sha256": row["alloc_domain"]["set_sha256"]} if row.get("alloc_domain") else None),
                "relocation_domain": ({"units": row["relocation_domain"]["units"], "set_sha256": row["relocation_domain"]["set_sha256"]} if row.get("relocation_domain") else None),
                "grids": row.get("grids") or {},
                "candidate_counts": candidate_counts,
                "candidate_set_sha256": candidate_hashes,
                "coverage": row["coverage"],
                "semantic_sources": row.get("semantic_sources") or [],
                "elf_errors": row["elf_errors"],
            }
            dst.write(json.dumps(compact, sort_keys=True, separators=(",", ":")) + "\n")

    comparison = json.loads((run / "comparison" / "summary.json").read_text(encoding="utf-8"))
    status = (
        duplicate == 0
        and rows == int(comparison["unit_rows_compared"])
        and native == int(comparison["native_unique_units"])
        and dict(candidate_totals) == comparison["unique_unit_candidate_totals"]
        and domain_totals["exec_domain"] == comparison["unique_unit_domain_totals_nonphysical_nonadditive"]["exec_bytes"]
        and domain_totals["alloc_domain"] == comparison["unique_unit_domain_totals_nonphysical_nonadditive"]["alloc_bytes"]
        and domain_totals["relocation_domain"] == comparison["unique_unit_domain_totals_nonphysical_nonadditive"]["relocation_entries"]
    )
    summary = {
        "schema_version": "2", "status": "pass" if status else "failed",
        "source": "comparison/primary-unit-compact.jsonl",
        "source_sha256": sha_file(source),
        "unit_rows": rows, "native_unique_units": native, "duplicate_unit_rows": duplicate,
        "machine_counts": dict(sorted(machines.items())),
        "candidate_totals": dict(sorted(candidate_totals.items())),
        "domain_totals_nonadditive": dict(sorted(domain_totals.items())),
        "unit_domain_summary_sha256": sha_file(target),
        "canonical_unit_domain_records_gzip_sha256": sha_file(canonical_gzip),
        "canonical_unit_domain_records_gzip_size": canonical_gzip.stat().st_size,
        "comparison_summary_sha256": sha_file(run / "comparison" / "summary.json"),
        "serialization": "UTF-8 JSONL; sorted keys; compact separators; one row per scan_unit_sha256 in source order",
        "limits": [
            "this stripped file retains canonical set hashes/counts, not every record",
            "the full canonical domain records remain in the run comparison stream and are reproducible from the bundled scanners and input manifest",
        ],
    }
    summary_path = out / "compact-set-summary.json"
    summary_path.write_text(json.dumps(summary, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": summary["status"], "rows": rows, "native": native, "output_sha256": summary["unit_domain_summary_sha256"]}, sort_keys=True))
    return 0 if status else 1


if __name__ == "__main__":
    raise SystemExit(main())
