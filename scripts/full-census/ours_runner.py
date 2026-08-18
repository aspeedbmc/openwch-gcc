#!/usr/bin/env python3
"""phase-6 S3 ours-lane full-EVT gate.

The canonical lane already ran and is sealed under
``evidence/s3/full-census/stage-a`` with the official artifacts parked in each
project's ``canonical/`` directory.  This runner rebuilds only the ours side of
the same 1170-project gate face with the D1+D2+D4 toolchain and compares every
artifact against that baseline.

The lane mechanics are not re-implemented: ``census_runner.build_side`` is
imported and called verbatim with ``side="ours"``, so the cwd contract
(``full-census/projects/{index:04d}-{sanitised}/work``), the converter
invocation, the per-lane re-pointing of the neutral ``toolchain-current``
symlink and the ``-fdebug-prefix-map`` neutralisation are byte-for-byte the
same mechanism the canonical lane used.  This mirrors the phase-3b/3d sealed
dual-lane runner, whose two lanes likewise share one ``work`` directory and
stash their products into per-lane sibling directories.

``OURS`` is ``.resolve()``d for the same reason ``CANONICAL`` is in the census
runner: GCC canonicalises argv[0] before deriving its include search paths, so
the string that reaches DWARF is the real path, and the prefix map has to key
on that real path or the toolchain include directories stay unmapped.
"""

from __future__ import annotations

import concurrent.futures
import csv
import importlib.util
import json
import os
import re
import signal
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
TOOLS = REPO / "tmp/toolchain_8.2.0/tools/full-census"
CENSUS_STAGE = REPO / "tmp/toolchain_8.2.0/evidence/s3/full-census/stage-a"
EVIDENCE = REPO / "tmp/toolchain_8.2.0/evidence/s3/full-ours"
STAGE = EVIDENCE / os.environ.get("OURS_STAGE", "stage-ours")
GOLDEN = REPO / "analysis/golden/8.2.0-darwin-arm64-full.tsv"
EXCLUSIONS = REPO / "analysis/golden/8.2.0-darwin-arm64-full-exclusions.tsv"
OURS_LINK = Path("/Users/wch/Work/riscv-none-embed-gcc-10.2.0-1.2/darwin-x64/install/riscv-none-embed-gcc")
OURS = OURS_LINK.resolve()

_argv = sys.argv
sys.argv = [_argv[0], "full"]
_spec = importlib.util.spec_from_file_location("census_runner", TOOLS / "census_runner.py")
m = importlib.util.module_from_spec(_spec)
sys.modules["census_runner"] = m
_spec.loader.exec_module(m)
sys.argv = _argv

LIMIT = int(os.environ.get("OURS_LIMIT", "0"))  # >0 restricts the gate face, for rehearsal only


# --------------------------------------------------------------------------
# baselines
# --------------------------------------------------------------------------

def read_tsv(path: Path) -> tuple[list[str], list[list[str]]]:
    rows: list[list[str]] = []
    with path.open(encoding="utf-8", newline="") as stream:
        for row in csv.reader(stream, delimiter="\t"):
            if row and row[0].startswith("#"):
                continue
            rows.append(row)
    return rows[0], rows[1:]


def load_baseline() -> tuple[dict[int, dict[str, tuple[str, int, str]]], dict[int, str]]:
    """Canonical artifact map per index plus the project path, from the sealed census."""
    _header, rows = read_tsv(CENSUS_STAGE / "artifact-results.tsv")
    baseline: dict[int, dict[str, tuple[str, int, str]]] = {}
    projects: dict[int, str] = {}
    for index, project, artifact, cls, size, sha in rows:
        i = int(index)
        baseline.setdefault(i, {})[artifact] = (cls, int(size), sha)
        projects[i] = project
    return baseline, projects


def load_golden() -> dict[int, dict[str, tuple[str, int, str]]]:
    _header, rows = read_tsv(GOLDEN)
    gold: dict[int, dict[str, tuple[str, int, str]]] = {}
    for index, _project, artifact, cls, size, sha in rows:
        gold.setdefault(int(index), {})[artifact] = (cls, int(size), sha)
    return gold


def load_exclusions() -> list[dict[str, str]]:
    _header, rows = read_tsv(EXCLUSIONS)
    out: list[dict[str, str]] = []
    for slug, cls, keyword, excerpt, pointer in rows:
        match = re.search(r"projects/(\d{4})-", pointer)
        out.append({
            "slug": slug, "class": cls, "keyword": keyword,
            "excerpt": excerpt, "pointer": pointer,
            "index": int(match.group(1)) if match else 0,
        })
    return out


LD_PATH = re.compile(r"\S*riscv-none-embed/bin/ld:")


def excerpt(text: str) -> str:
    """Path-normalised diagnostic quote, reusing render_manifest's placeholders.

    The ours root is folded onto the same ``<TC>`` token as the canonical root:
    the two lanes name their toolchain differently by construction, so a raw
    comparison of the two diagnostics could never agree even when the failure
    is identical.
    """
    line = LD_PATH.sub("<TC>/bin/ld:", text.replace("\t", " "))
    for prefix, token in (
        (str(m.WORK), "<WORK>"),
        (str(REPO / "ref/wch-evt"), "<EVT>"),
        (str(m.CANONICAL), "<TC>"),
        (str(OURS), "<TC>"),
        (str(OURS_LINK), "<TC>"),
        (str(REPO), "<REPO>"),
    ):
        line = line.replace(prefix, token)
    return line.encode("utf-8", "replace")[:240].decode("utf-8", "ignore")


# --------------------------------------------------------------------------
# per-project ours lane
# --------------------------------------------------------------------------

GATE_SUFFIXES = (".o", ".elf", ".bin")


def classify(name: str) -> str:
    return "gate" if name.endswith(GATE_SUFFIXES) else "aux"


def compare(index: int, baseline: dict[str, tuple[str, int, str]], ours: dict[str, dict[str, object]],
            project: str) -> tuple[list[list[str]], dict[str, int]]:
    rows: list[list[str]] = []
    counts = {k: 0 for k in (
        "gate_match", "gate_diff", "gate_missing", "gate_extra",
        "aux_match", "aux_diff", "aux_missing", "aux_extra")}
    ours_map = {f"obj/{name}": info for name, info in ours.items()}
    for artifact in sorted(set(baseline) | set(ours_map), key=os.fsencode):
        base = baseline.get(artifact)
        mine = ours_map.get(artifact)
        if base is not None and mine is not None:
            cls = base[0]
            status = "MATCH" if base[2] == mine["sha256"] else "DIFF"
            row = [str(index), project, artifact, cls, str(base[1]), str(mine["size"]), base[2], str(mine["sha256"]), status]
        elif base is not None:
            cls = base[0]
            status = "MISSING"
            row = [str(index), project, artifact, cls, str(base[1]), "", base[2], "", status]
        else:
            cls = classify(artifact)
            status = "EXTRA"
            row = [str(index), project, artifact, cls, "", str(mine["size"]), "", str(mine["sha256"]), status]
        counts[f"{cls}_{status.lower()}"] += 1
        rows.append(row)
    return rows, counts


def run_project(index: int, project: Path, baseline: dict[str, tuple[str, int, str]], jobs: int):
    started = time.monotonic()
    root = m.project_dir_for(index, project)
    root.mkdir(parents=True, exist_ok=True)
    link = root / "toolchain-current"
    before = os.readlink(link) if link.is_symlink() else ""
    result = m.build_side(index, project, root, "ours", OURS, jobs)
    after = os.readlink(link) if link.is_symlink() else ""
    rows, counts = compare(index, baseline, result.artifacts, project.relative_to(m.EVT).as_posix())
    stages_ok = result.conversion == result.build == result.bin_status == "PASS"
    gate_clean = counts["gate_diff"] == counts["gate_missing"] == counts["gate_extra"] == 0
    status = "MATCH" if stages_ok and gate_clean else ("OURS-FAIL" if not stages_ok else "GATE-MISMATCH")
    summary = [
        str(index), project.relative_to(m.EVT).parts[0], project.relative_to(m.EVT).as_posix(),
        result.conversion, result.build, result.bin_status, status,
        str(counts["gate_match"]), str(counts["gate_diff"]), str(counts["gate_missing"]), str(counts["gate_extra"]),
        str(counts["aux_match"]), str(counts["aux_diff"]), str(counts["aux_missing"]), str(counts["aux_extra"]),
        "%.3f" % (time.monotonic() - started), str(jobs), before, after,
        result.reason, excerpt(result.first_diagnostic)[:300], str(root.relative_to(m.WORK)),
    ]
    counts["project_match"] = int(status == "MATCH")
    return summary, rows, counts


# --------------------------------------------------------------------------
# determinism self-check: ours/ours, one -g project and one without
# --------------------------------------------------------------------------

def determinism_selfcheck(projects: list[Path]) -> dict[str, object]:
    root = STAGE / "selfcheck"
    root.mkdir(parents=True, exist_ok=True)
    outcome: dict[str, object] = {"lane": "ours/ours", "pairs": [], "verdict": "UNVERIFIED"}
    debug_candidates = [p for p in projects if m.looks_debuggable(p.parent / ".cproject")][:8]
    verdicts: list[bool] = []
    for label, candidates in (("debug", debug_candidates), ("first", [projects[0]])):
        for candidate in candidates:
            pair_root = root / label
            m.clear_directory(pair_root)
            first = m.build_side(0, candidate, pair_root, "run1", OURS, m.MAKE_JOBS)
            if first.build != "PASS":
                outcome["pairs"].append({"label": label, "project": candidate.relative_to(m.EVT).as_posix(),
                                         "state": "SKIPPED-BUILD-FAIL", "reason": first.reason,
                                         "first_diagnostic": excerpt(first.first_diagnostic)})
                continue
            second = m.build_side(0, candidate, pair_root, "run2", OURS, m.MAKE_JOBS)
            same = first.artifacts.keys() == second.artifacts.keys() and all(
                first.artifacts[k]["sha256"] == second.artifacts[k]["sha256"] for k in first.artifacts)
            outcome["pairs"].append({
                "label": label, "project": candidate.relative_to(m.EVT).as_posix(), "state": "COMPARED",
                "artifacts": len(first.artifacts), "identical": same,
                "run1": {k: v["sha256"] for k, v in sorted(first.artifacts.items())},
                "run2": {k: v["sha256"] for k, v in sorted(second.artifacts.items())},
            })
            verdicts.append(same)
            break
    outcome["verdict"] = "PASS" if verdicts and all(verdicts) else ("FAIL" if verdicts else "UNVERIFIED")
    m.write_text(root / "result.json", json.dumps(outcome, ensure_ascii=False, indent=2))
    return outcome


# --------------------------------------------------------------------------
# EXCLUDED spot-check: the 128 official failures must still fail for us
# --------------------------------------------------------------------------

def excluded_sample(all_projects: list[Path], canonical_diag: dict[int, str]) -> list[dict[str, object]]:
    rows = load_exclusions()
    by_keyword: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_keyword.setdefault(row["keyword"], []).append(row)
    plan = {"opcode:mcpy": 5, "isa-attr:z-subset": 4, "lib:missing": 1}
    picked: list[dict[str, str]] = []
    for keyword, want in plan.items():
        pool = sorted(by_keyword.get(keyword, []), key=lambda r: r["index"])
        if not pool:
            continue
        step = max(1, len(pool) // want)
        chosen = [pool[i] for i in range(0, len(pool), step)][:want]
        picked.extend(chosen)
    out: list[dict[str, object]] = []
    for entry in picked:
        index = entry["index"]
        project = all_projects[index - 1]
        if project.relative_to(m.EVT).as_posix() != entry["slug"]:
            raise RuntimeError(f"exclusion index {index} does not resolve to {entry['slug']}")
        root = m.project_dir_for(index, project)
        result = m.build_side(index, project, root, "ours-excluded", OURS, 1)
        stages_ok = result.conversion == result.build == result.bin_status == "PASS"
        ours_excerpt = excerpt(result.first_diagnostic)
        out.append({
            "index": index, "project": entry["slug"], "keyword": entry["keyword"], "class": entry["class"],
            "ours_conversion": result.conversion, "ours_build": result.build, "ours_bin": result.bin_status,
            "ours_built_successfully": stages_ok,
            "canonical_excerpt": entry["excerpt"],
            "canonical_first_diagnostic": excerpt(canonical_diag.get(index, "")),
            "ours_first_diagnostic": ours_excerpt,
            "same_shape": (not stages_ok) and ours_excerpt == entry["excerpt"],
            "verdict": "SUPERSET-SIGNAL" if stages_ok else ("SAME" if ours_excerpt == entry["excerpt"] else "DIFFERENT-DIAGNOSTIC"),
        })
    return out


# --------------------------------------------------------------------------

PROJECT_HEADER = [
    "index", "evt_root", "project", "ours_conversion", "ours_build", "ours_bin", "project_status",
    "gate_match", "gate_diff", "gate_missing", "gate_extra",
    "aux_match", "aux_diff", "aux_missing", "aux_extra",
    "elapsed_s", "make_jobs", "symlink_before", "symlink_after", "reason", "first_diagnostic", "evidence",
]
ARTIFACT_HEADER = [
    "index", "project", "artifact", "class", "canonical_size", "ours_size",
    "canonical_sha256", "ours_sha256", "status",
]


def triage(rows: list[list[str]]) -> list[dict[str, object]]:
    """One objdump -h section-size line per DIFF project's first gate artifact."""
    seen: set[int] = set()
    out: list[dict[str, object]] = []
    objdump = m.tool_path(m.CANONICAL, "objdump")
    for row in rows:
        index, project, artifact, cls, _cs, _os, _ch, _oh, status = row
        if cls != "gate" or status != "DIFF" or int(index) in seen:
            continue
        seen.add(int(index))
        root = m.WORK / "projects" / sorted(p.name for p in (m.WORK / "projects").iterdir() if p.name.startswith(f"{int(index):04d}-"))[0]
        entry: dict[str, object] = {"index": int(index), "project": project, "artifact": artifact}
        sections: list[str] = []
        for side in ("canonical", "ours"):
            path = root / side / artifact
            if not path.is_file():
                sections.append(f"{side}:MISSING")
                continue
            out_path = STAGE / "triage" / f"{int(index):04d}-{side}.txt"
            m.run_command([str(objdump), "-h", str(path)], root, out_path, STAGE / "triage" / f"{int(index):04d}-{side}.err", 120)
            sizes = {}
            for line in out_path.read_text(errors="replace").splitlines():
                match = re.match(r"\s*\d+\s+(\S+)\s+([0-9a-f]{8})\s", line)
                if match:
                    sizes[match.group(1)] = int(match.group(2), 16)
            entry[f"{side}_sections"] = sizes
        a = entry.get("canonical_sections") or {}
        b = entry.get("ours_sections") or {}
        deltas = {k: (a.get(k), b.get(k)) for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)}
        entry["section_deltas"] = deltas
        entry["one_line"] = f"{project} {artifact}: " + (
            ", ".join(f"{k} {x}->{y}" for k, (x, y) in deltas.items()) if deltas
            else "identical section sizes (content-only difference)")
        out.append(entry)
    return out


def main() -> int:
    os.umask(0o022)
    STAGE.mkdir(parents=True, exist_ok=True)
    (STAGE / "identity").mkdir(parents=True, exist_ok=True)
    (STAGE / "triage").mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ") + "-" + str(os.getpid())
    m.write_text(STAGE / "run-id.txt", run_id + "\n")
    m.STAGE = STAGE
    m.LEDGER_FILE = STAGE / "command-ledger.tsv"
    m.write_tsv(m.LEDGER_FILE, ["started_utc", "ended_utc", "cwd", "command_json", "returncode", "stdout", "stderr", "timeout"], [])
    m.atomic_write(STAGE / "inherited-environment.txt",
                   "".join(f"{k}={v}\n" for k, v in sorted(os.environ.items())).encode("utf-8", "surrogateescape"))

    # --- pre-flight 1: the canonical side has not moved since the census -----
    census_summary = json.loads((CENSUS_STAGE / "summary.json").read_text(encoding="utf-8"))
    canonical_identity = m.tool_identity(m.CANONICAL, "canonical")
    ours_identity = m.tool_identity(OURS, "ours")
    tool_drift = {
        name: {"census": census_summary["toolchain_identity"][name]["sha256"], "now": canonical_identity[name]["sha256"]}
        for name in ("gcc", "as", "ld", "objcopy", "objdump")
        if census_summary["toolchain_identity"][name]["sha256"] != canonical_identity[name]["sha256"]
    }
    if tool_drift:
        raise RuntimeError(f"canonical toolchain drifted since the census: {tool_drift}")
    m.write_text(STAGE / "identity/toolchains.json", json.dumps(
        {"canonical": canonical_identity, "ours": ours_identity,
         "ours_link": str(OURS_LINK), "ours_resolved": str(OURS),
         "ours_link_chain": [f"{p} -> {os.readlink(p)}" for p in
                             [Path(*OURS_LINK.parts[:i + 1]) for i in range(len(OURS_LINK.parts))]
                             if p.is_symlink()]},
        ensure_ascii=False, indent=2))

    # --- pre-flight 2: golden TSV reconciles with the sealed census rows -----
    # Since the P2-21 product-level extension (DECISIONS 2026-08-17) the golden
    # manifest carries two partitions, tagged by its own class column:
    #   gate            census gate face, this lane's face
    #   gate-link-only  objects of the 33 link-only projects, covered by
    #                   linkonly_runner.py
    # Reconcile against a view derived from the CURRENT manifest by that marker
    # rather than against a hard-coded row count, so extending the manifest can
    # never again silently outdate this check (phase-8 finding P8-F1).
    baseline, baseline_projects = load_baseline()
    golden_all = load_golden()
    def _partition(cls: str) -> dict[int, dict[str, tuple[str, int, str]]]:
        view = {i: {a: v for a, v in arts.items() if v[0] == cls} for i, arts in golden_all.items()}
        return {i: arts for i, arts in view.items() if arts}
    golden = _partition("gate")
    golden_link_only = _partition("gate-link-only")
    gate_from_census = {i: {a: v for a, v in arts.items() if v[0] == "gate"} for i, arts in baseline.items()}
    gate_from_census = {i: arts for i, arts in gate_from_census.items() if arts}
    reconcile = {
        "golden_projects": len(golden),
        "census_gate_projects": len(gate_from_census),
        "golden_gate_rows": sum(len(v) for v in golden.values()),
        "census_gate_rows": sum(len(v) for v in gate_from_census.values()),
        "identical": golden == gate_from_census,
        "golden_link_only_projects": len(golden_link_only),
        "golden_link_only_rows": sum(len(v) for v in golden_link_only.values()),
        "golden_total_projects": len(golden_all),
        "golden_total_rows": sum(len(v) for v in golden_all.values()),
    }
    m.write_text(STAGE / "baseline-reconcile.json", json.dumps(reconcile, ensure_ascii=False, indent=2))
    if not reconcile["identical"]:
        raise RuntimeError(f"golden/census baseline reconciliation failed: {reconcile}")
    if reconcile["golden_projects"] + reconcile["golden_link_only_projects"] != reconcile["golden_total_projects"]:
        raise RuntimeError(f"golden project partition is not exhaustive: {reconcile}")
    if reconcile["golden_gate_rows"] + reconcile["golden_link_only_rows"] != reconcile["golden_total_rows"]:
        raise RuntimeError(f"golden row partition is not exhaustive: {reconcile}")

    # --- pre-flight 3: freeze the ours install tree --------------------------
    ours_pre = m.save_manifest(STAGE / "ours-install-pre.jsonl", m.path_manifest(OURS))

    # --- EVT patch application, mirrored from the census ---------------------
    pre_evt = m.path_manifest(m.EVT)
    pre_evt_hash = m.save_manifest(STAGE / "evt-pre-state.jsonl", pre_evt)
    patch_files = sorted((m.EVT / "patches").iterdir())
    allowlist = ["0001-pmp-select-ch32v20x-d8w.patch", "0002-fix-eight-wvproj-builds.patch", "apply.sh"]
    if [p.name for p in patch_files] != allowlist or not all(p.is_file() for p in patch_files):
        raise RuntimeError("EVT patch allowlist mismatch")
    targets = m.patch_targets()
    backups = [m.backup_target(path, i) for i, path in enumerate(targets, 1)]
    m.atomic_write(STAGE / "evt-originals/manifest.json", json.dumps(backups, ensure_ascii=False, indent=2).encode("utf-8"))

    harness_spec = importlib.util.spec_from_file_location("wvproj_test_harness", m.EVT / "tests/test_wvproj_to_make.py")
    harness = importlib.util.module_from_spec(harness_spec)
    sys.modules["wvproj_test_harness"] = harness
    harness_spec.loader.exec_module(harness)
    applied = harness.apply_test_patches()
    if set(applied) != set(targets):
        raise RuntimeError("harness patch targets differ from the verified allowlist")

    rc = 1
    caught: str | None = None
    try:
        rc = run_gate(run_id, baseline, baseline_projects, golden, harness, census_summary, ours_pre, pre_evt, pre_evt_hash)
    except BaseException:
        caught = traceback.format_exc()
        m.write_text(STAGE / "runner-exception.txt", caught)
    finally:
        m.restore_backup(backups)
        restored = m.path_manifest(m.EVT)
        restored_hash = m.save_manifest(STAGE / "evt-restored-state.jsonl", restored)
        m.write_text(STAGE / "evt-restore.json", json.dumps(
            {"evt_pre_hash": pre_evt_hash, "evt_restored_hash": restored_hash,
             "evt_exact_restored": restored == pre_evt}, ensure_ascii=False, indent=2))
    if caught is not None:
        print(caught, file=sys.stderr, end="")
        return 1
    return rc


def run_gate(run_id, baseline, baseline_projects, golden, harness, census_summary, ours_pre, pre_evt, pre_evt_hash) -> int:
    all_projects = harness.selected_projects("full")
    if len(all_projects) != census_summary["enumeration_total"]:
        raise RuntimeError(f"enumeration changed: {len(all_projects)} vs {census_summary['enumeration_total']}")
    for index, slug in baseline_projects.items():
        if all_projects[index - 1].relative_to(m.EVT).as_posix() != slug:
            raise RuntimeError(f"index {index} no longer resolves to {slug}")
    m.write_text(STAGE / "inventory-discovery.txt",
                 "\n".join(f"{i}\t{p.relative_to(m.EVT).as_posix()}" for i, p in enumerate(all_projects, 1)) + "\n")

    gate_indices = sorted(golden)
    if LIMIT:
        gate_indices = gate_indices[:LIMIT]
    print(f"gate face: {len(gate_indices)} projects", flush=True)

    selfcheck = determinism_selfcheck([all_projects[i - 1] for i in gate_indices])
    print(f"selfcheck verdict={selfcheck['verdict']}", flush=True)

    results: dict[int, list[str]] = {}
    artifacts: dict[int, list[list[str]]] = {}
    per_project_counts: dict[int, dict[str, int]] = {}
    signal.signal(signal.SIGINT, m.signal_handler)
    signal.signal(signal.SIGTERM, m.signal_handler)
    started_all = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=m.WORKERS) as executor:
        futures = {executor.submit(run_project, i, all_projects[i - 1], baseline[i], m.MAKE_JOBS): i for i in gate_indices}
        for number, future in enumerate(concurrent.futures.as_completed(futures), 1):
            index = futures[future]
            try:
                summary, rows, counts = future.result()
            except Exception as exc:
                root = m.project_dir_for(index, all_projects[index - 1])
                root.mkdir(parents=True, exist_ok=True)
                m.write_text(root / "ours-runner-exception.txt", traceback.format_exc())
                summary = [str(index), all_projects[index - 1].relative_to(m.EVT).parts[0],
                           all_projects[index - 1].relative_to(m.EVT).as_posix(), "ERROR", "ERROR", "ERROR",
                           "OURS-FAIL"] + ["0"] * 8 + ["0.000", str(m.MAKE_JOBS), "", "", repr(exc)[:300], "", str(root.relative_to(m.WORK))]
                rows, counts = [], {k: 0 for k in ("gate_match", "gate_diff", "gate_missing", "gate_extra",
                                                   "aux_match", "aux_diff", "aux_missing", "aux_extra", "project_match")}
            results[index] = summary
            artifacts[index] = rows
            per_project_counts[index] = counts
            if number % 25 == 0 or number == len(gate_indices):
                print(f"progress {number}/{len(gate_indices)} elapsed={time.monotonic() - started_all:.0f}s", flush=True)
            if m.STOP.is_set():
                break

    # Serial -j1 re-run of every ours-side failure, mirroring the census policy:
    # a classification must never rest on -j2 stderr interleaving.
    retry_indices = [i for i, row in sorted(results.items())
                     if row[6] == "OURS-FAIL" or "TIMEOUT" in (row[3], row[4], row[5]) or "ERROR" in (row[3], row[4], row[5])]
    retry_log: list[dict[str, object]] = []
    if retry_indices and not m.STOP.is_set():
        print(f"serial-retry {len(retry_indices)} projects", flush=True)
        m.CURRENT_JOBS = 1
        for number, index in enumerate(retry_indices, 1):
            before = list(results[index])
            summary, rows, counts = run_project(index, all_projects[index - 1], baseline[index], 1)
            results[index] = summary
            artifacts[index] = rows
            per_project_counts[index] = counts
            retry_log.append({"index": index, "project": summary[2],
                              "before": {"status": before[6], "build": before[4], "first": before[20]},
                              "after": {"status": summary[6], "build": summary[4], "first": summary[20]}})
            print(f"serial-retry {number}/{len(retry_indices)}", flush=True)
        m.CURRENT_JOBS = m.MAKE_JOBS
    m.write_text(STAGE / "serial-retry.json", json.dumps(retry_log, ensure_ascii=False, indent=2))

    canonical_diag = {}
    _h, crows = read_tsv(CENSUS_STAGE / "project-results.tsv")
    for row in crows:
        canonical_diag[int(row[0])] = row[8]
    print("excluded sample", flush=True)
    excluded = excluded_sample(all_projects, canonical_diag)
    m.write_text(STAGE / "excluded-sample.json", json.dumps(excluded, ensure_ascii=False, indent=2))

    result_rows = [results[i] for i in sorted(results)]
    artifact_rows = [row for i in sorted(artifacts) for row in artifacts[i]]
    m.write_tsv(STAGE / "ours-project-results.tsv", PROJECT_HEADER, result_rows)
    m.write_tsv(STAGE / "ours-artifact-results.tsv", ARTIFACT_HEADER, artifact_rows)
    gate_mismatch = [r for r in artifact_rows if r[3] == "gate" and r[8] != "MATCH"]
    aux_mismatch = [r for r in artifact_rows if r[3] == "aux" and r[8] != "MATCH"]
    m.write_tsv(STAGE / "gate-mismatches.tsv", ARTIFACT_HEADER, gate_mismatch)
    m.write_tsv(STAGE / "aux-mismatches.tsv", ARTIFACT_HEADER, aux_mismatch)

    triage_rows = triage(gate_mismatch)
    m.write_text(STAGE / "gate-diff-triage.json", json.dumps(triage_rows, ensure_ascii=False, indent=2))

    # restore the neutral symlink of every touched project to the canonical root
    restored_links = 0
    for index in sorted(set(gate_indices) | {e["index"] for e in excluded}):
        link = m.project_dir_for(index, all_projects[index - 1]) / "toolchain-current"
        if link.is_symlink() and os.readlink(link) != str(m.CANONICAL):
            m.atomic_symlink(link, m.CANONICAL)
            restored_links += 1

    ours_post = m.save_manifest(STAGE / "ours-install-post.jsonl", m.path_manifest(OURS))
    totals = {k: sum(c.get(k, 0) for c in per_project_counts.values()) for k in (
        "project_match", "gate_match", "gate_diff", "gate_missing", "gate_extra",
        "aux_match", "aux_diff", "aux_missing", "aux_extra")}
    summary = {
        "schema": "phase6-s3-full-ours-v1",
        "run_id": run_id,
        "lane": "ours",
        "canonical_root": str(m.CANONICAL),
        "ours_root": str(OURS),
        "ours_link": str(OURS_LINK),
        "gate_denominator": len(gate_indices),
        "projects_completed": len(result_rows),
        "counts": totals,
        "gate_total_compared": totals["gate_match"] + totals["gate_diff"] + totals["gate_missing"] + totals["gate_extra"],
        "aux_total_compared": totals["aux_match"] + totals["aux_diff"] + totals["aux_missing"] + totals["aux_extra"],
        "ours_install_pre_hash": ours_pre,
        "ours_install_post_hash": ours_post,
        "ours_install_stable": ours_pre == ours_post,
        "evt_pre_hash": pre_evt_hash,
        "selfcheck": selfcheck,
        "serial_retry_count": len(retry_log),
        "excluded_sample": [{k: e[k] for k in ("index", "project", "keyword", "verdict")} for e in excluded],
        "excluded_superset_signals": [e["project"] for e in excluded if e["verdict"] == "SUPERSET-SIGNAL"],
        "symlinks_restored_to_canonical": restored_links,
        "path_contract": census_summary["path_contract"],
        "debug_prefix_map": f"{OURS}=>{{project_root}}/toolchain-current",
        "source_date_epoch": m.EPOCH,
        "workers": m.WORKERS,
        "make_jobs": m.MAKE_JOBS,
        "stop_requested": m.STOP.is_set(),
        "elapsed_s": round(time.monotonic() - started_all, 3),
    }
    m.atomic_write(STAGE / "summary.json", json.dumps(summary, ensure_ascii=False, indent=2).encode("utf-8"))

    ledger_files = [p for p in STAGE.rglob("*") if p.is_file() and p.name != "STAGE_COMPLETE.json"
                    and "selfcheck" not in p.relative_to(STAGE).parts and "triage" not in p.relative_to(STAGE).parts]
    marker = {
        "schema": "phase6-s3-full-ours-complete-v1",
        "run_id": run_id,
        "sealed_at_utc": m.now(),
        "input_hashes": {
            "golden": m.sha256_file(GOLDEN),
            "exclusions": m.sha256_file(EXCLUSIONS),
            "census_artifact_results": m.sha256_file(CENSUS_STAGE / "artifact-results.tsv"),
            "census_stage_complete": m.sha256_file(CENSUS_STAGE / "STAGE_COMPLETE.json"),
            "converter": m.sha256_file(m.CONVERTER),
            "census_runner": m.sha256_file(TOOLS / "census_runner.py"),
            "ours_runner": m.sha256_file(Path(__file__).resolve()),
        },
        "ledger_hashes": {str(p.relative_to(STAGE)): m.sha256_file(p)
                          for p in sorted(ledger_files, key=lambda p: os.fsencode(str(p.relative_to(STAGE))))},
        "summary_hash": m.sha256_file(STAGE / "summary.json"),
        "counts": totals,
    }
    m.atomic_write(STAGE / "STAGE_COMPLETE.json", json.dumps(marker, ensure_ascii=False, indent=2).encode("utf-8"))
    m.fsync_dir(STAGE)
    print("OURS_GATE_DONE projects={} gate_match={} gate_diff={} gate_missing={} gate_extra={} aux_diff={}".format(
        len(result_rows), totals["gate_match"], totals["gate_diff"], totals["gate_missing"],
        totals["gate_extra"], totals["aux_diff"]), flush=True)
    ok = (not m.STOP.is_set() and len(result_rows) == len(gate_indices)
          and selfcheck["verdict"] == "PASS" and summary["ours_install_stable"])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
