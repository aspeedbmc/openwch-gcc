#!/usr/bin/env python3
"""Derive the census report's numbers from the published ledgers.

Reads only the two published TSVs plus the sealed stage ledgers, so every
figure quoted in the S3 census report can be recomputed without re-running the
census.  Writes evidence/s3/full-census/census-stats.json.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
STAGE = REPO / "tmp/toolchain_8.2.0/evidence/s3/full-census/stage-a"
OUT = REPO / "tmp/toolchain_8.2.0/evidence/s3/full-census/census-stats.json"
MANIFEST = REPO / "analysis/golden/8.2.0-darwin-arm64-full.tsv"
EXCLUSIONS = REPO / "analysis/golden/8.2.0-darwin-arm64-full-exclusions.tsv"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    projects = list(csv.DictReader((STAGE / "project-results.tsv").open(encoding="utf-8"), delimiter="\t"))
    exclusions = list(csv.DictReader(EXCLUSIONS.open(encoding="utf-8"), delimiter="\t"))
    inventory = list(csv.DictReader((STAGE / "effective-project-inventory.tsv").open(encoding="utf-8"), delimiter="\t"))
    summary = json.loads((STAGE / "summary.json").read_text(encoding="utf-8"))

    total = Counter(row["evt_root"] for row in projects)
    passed = Counter(row["evt_root"] for row in projects if row["status"] == "PASS")
    by_root = {
        root: {"total": total[root], "pass": passed[root], "excluded": total[root] - passed[root]}
        for root in sorted(total)
    }
    keyword = Counter(row["keyword"] for row in exclusions)
    category = Counter(row["class"] for row in exclusions)
    root_keyword = Counter((row["slug"].split("/")[0], row["keyword"]) for row in exclusions)
    # The inventory's `march` column is UNKNOWN by inheritance: the phase-3b
    # field extractor reads config.json's resolved_flags["march"], but the
    # converter stores the target flags under resolved_flags["target"].  The
    # value is still present verbatim in the debug_flags column (the generated
    # Makefile's TARGET_FLAGS line), so it is recovered from there.
    def dialect(row: dict[str, str]) -> str:
        match = re.search(r"-march=(\S+)", row["debug_flags"])
        return match.group(1) if match else "UNKNOWN"

    march = Counter(dialect(row) for row in inventory)
    march_pass = Counter(
        dialect(row) for row, project in zip(inventory, projects) if project["status"] == "PASS"
    )

    stats = {
        "schema": "phase6-s3-census-stats-v1",
        "run_id": summary["run_id"],
        "denominator": len(projects),
        "pass": sum(passed.values()),
        "excluded": len(exclusions),
        "category_counts": dict(sorted(category.items())),
        "keyword_counts": dict(sorted(keyword.items(), key=lambda item: (-item[1], item[0]))),
        "root_keyword_counts": {f"{root}|{key}": count for (root, key), count in sorted(root_keyword.items())},
        "by_evt_root": by_root,
        "march_dialects_all": dict(sorted(march.items())),
        "march_dialects_pass": dict(sorted(march_pass.items())),
        "elapsed_s": summary["elapsed_s"],
        "serial_retry_count": summary["serial_retry_count"],
        "determinism_selfcheck": summary["selfcheck"]["verdict"],
        "manifest_sha256": sha256_file(MANIFEST),
        "exclusions_sha256": sha256_file(EXCLUSIONS),
    }
    OUT.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: stats[k] for k in ("denominator", "pass", "category_counts", "keyword_counts")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
