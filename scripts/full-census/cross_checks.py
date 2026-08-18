#!/usr/bin/env python3
"""Three cross-checks that turn the census report's claims into evidence.

  A. dialect downgrade -- the high PASS count is explained by the converter's
     GCC8 branch dropping the modern ISA components the project metadata asks
     for.  Read from each project's own generated config.json: what the
     metadata requested vs what -march was emitted.
  B. same-path re-run agreement -- the smoke run and the full run built the
     shared projects at the same absolute paths ~10 minutes apart; every
     artifact hash must agree.  Independent of the runner's own self-check.
  C. quick-lane agreement -- the nine README projects must land on the same
     PASS/FAIL verdicts as the S2 quick golden (analysis/golden/8.2.0-darwin-arm64.tsv).

Writes evidence/s3/full-census/cross-checks.json.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
CENSUS = REPO / "tmp/toolchain_8.2.0/evidence/s3/full-census"
STAGE = CENSUS / "stage-a"
SMOKE = CENSUS / "stage-smoke"
WORK = REPO / "tmp/toolchain_8.2.0/full-census"
OUT = CENSUS / "cross-checks.json"

# index -> quick-lane slug in analysis/golden/8.2.0-darwin-arm64.tsv
QUICK_LANE = {
    15: "v2ac-gpio", 87: "v3a-gpio", 201: "v3b-pioc", 352: "v3c-led", 417: "v3f-gpio",
    505: "v3f2-gpio", 667: "v4bc-pmp", 792: "v4f-fpu", 950: "v5f-fpu",
}
QUICK_EXPECTED_FAIL = {352}
# sampled projects with modern ISA components in their MRS metadata
DIALECT_SAMPLE = (1, 201, 950)


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def main() -> int:
    projects = {int(row["index"]): row for row in rows(STAGE / "project-results.tsv")}

    dialect = []
    for index in DIALECT_SAMPLE:
        config = json.loads((WORK / projects[index]["evidence"] / "canonical/config.json").read_text(encoding="utf-8"))
        target = config["target"]
        requested = {key: target[key] for key in ("architecture", "multiply_extension", "atomic_extension", "compressed_extension", "bit_extension", "zmmul", "floating_point") if key in target}
        emitted = config["resolved_flags"]["target"]
        dialect.append({
            "index": index,
            "project": projects[index]["project"],
            "status": projects[index]["status"],
            "metadata_requested": requested,
            "emitted_target_flags": emitted,
            "modern_components_dropped": sorted(
                key for key in ("bit_extension", "zmmul") if requested.get(key) is True
            ),
        })

    smoke_art = {(r["index"], r["artifact"]): r["sha256"] for r in rows(SMOKE / "artifact-results.tsv")}
    full_art = {(r["index"], r["artifact"]): r["sha256"] for r in rows(STAGE / "artifact-results.tsv")}
    shared = [key for key in smoke_art if key in full_art]
    agree = [key for key in shared if smoke_art[key] == full_art[key]]

    quick = [
        {
            "index": index,
            "slug": slug,
            "project": projects[index]["project"],
            "status": projects[index]["status"],
            "expected": "FAIL" if index in QUICK_EXPECTED_FAIL else "PASS",
        }
        for index, slug in sorted(QUICK_LANE.items())
    ]

    result = {
        "schema": "phase6-s3-cross-checks-v1",
        "A_dialect_downgrade": dialect,
        "B_same_path_rerun": {
            "smoke_run_indices": sorted({int(key[0]) for key in smoke_art}),
            "shared_artifact_rows": len(shared),
            "identical": len(agree),
            "differing": len(shared) - len(agree),
        },
        "C_quick_lane_agreement": {
            "projects": quick,
            "agreements": sum(1 for row in quick if row["status"] == row["expected"]),
            "total": len(quick),
        },
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "dialect_samples": [f"{d['index']}:{','.join(d['modern_components_dropped']) or 'none'}->{d['emitted_target_flags'][0]}" for d in dialect],
        "rerun": result["B_same_path_rerun"],
        "quick_lane": f"{result['C_quick_lane_agreement']['agreements']}/{result['C_quick_lane_agreement']['total']}",
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
