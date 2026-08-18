#!/usr/bin/env python3
"""phase-6 S4 link-only extension (P2-21 ruling, DECISIONS 4f5dedb).

The S3 census excluded 128 projects at *project* granularity.  33 of them fail
only in ``collect2``/``ld``: every translation unit compiles, so both sides do
produce a full set of ``.o``.  The user ruling of 2026-08-17 tightens the
exclusion to *artifact* granularity -- those ``.o`` join the byte gate, only the
``.elf``/``.bin`` stay excluded.

This runner materialises that ruling:

  leg 1  official double run  (side ``official-r1`` / ``official-r2``) --- the
         two passes must agree object-for-object before anything is admitted to
         the golden manifest.
  leg 2  ours run             (side ``ours-linkonly``) --- compared against the
         official ``official-r1`` set, MATCH / DIFF / MISSING per row, EXTRA
         listed separately and never gated.

The lane mechanics are not re-implemented.  ``census_runner.build_side`` is
imported and called verbatim, so the cwd contract
(``full-census/projects/{index:04d}-{sanitised}/work``), the converter
invocation, the per-lane re-pointing of the neutral ``toolchain-current``
symlink and the ``-fdebug-prefix-map`` neutralisation are the very mechanism the
sealed census and the sealed ours lane used.  The sealed ``canonical/`` and
``ours-excluded/`` product directories of those runs are never touched: this
runner only ever writes its own side directories.

``OURS`` is ``.resolve()``d, per the ours-lane run record §4: GCC canonicalises
argv[0] before deriving its include search paths, so the prefix map has to key
on the real toolchain root or the toolchain include directories stay unmapped.

Stop-the-world conditions (any one aborts the run and leaves the repository
untouched):
  * canonical toolchain sha drift against the sealed census summary;
  * an official r1/r2 pair that is not object-for-object identical;
  * a ``.elf`` or ``.bin`` in any side's ``obj/`` (these projects must not link);
  * conversion != PASS, TIMEOUT/ERROR, or a first diagnostic that does not carry
    the ledgered failure signature of that project;
  * any ours-side gate DIFF or MISSING.
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
import threading
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
TOOLS = REPO / "tmp/toolchain_8.2.0/tools/full-census"
CENSUS_STAGE = REPO / "tmp/toolchain_8.2.0/evidence/s3/full-census/stage-a"
EVIDENCE = REPO / "tmp/toolchain_8.2.0/evidence/s4/linkonly-extension"
STAGE = EVIDENCE / os.environ.get("LINKONLY_STAGE", "stage-a")
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

SIDE_R1 = "official-r1"
SIDE_R2 = "official-r2"
SIDE_OURS = "ours-linkonly"

# The three ledgered link-stage failure keywords, with the substring that has to
# appear in the build log for the project to stay inside its ledger row.
#
# The check runs over the raw build logs, not over ``first_diagnostic``:
# ``extract_diagnostics`` keys on a fixed ERROR_TOKENS list, and the ld capacity
# messages ("will not fit in region", "overflowed by") carry none of those
# tokens, so index 938 legitimately reports ``collect2: error: ld returned 1``
# as its first diagnostic while the ledger excerpt (produced by
# render_manifest's rule-triggering-line policy) quotes the capacity message.
LINK_ONLY_KEYWORDS = {
    "isa-attr:z-subset": "unsupported ISA subset `z'",
    "lib:missing": "cannot find -lprintfloat",
    "link:region-overflow": "overflowed by",
}
GATE_SUFFIXES = (".o", ".elf", ".bin")
FORBIDDEN_SUFFIXES = (".elf", ".bin")

HALT: list[dict[str, object]] = []
HALT_LOCK = threading.Lock()


def halt(reason: str, detail: dict[str, object]) -> None:
    """Record a stop condition and short-circuit every remaining project.

    ``m.STOP`` makes ``build_side`` return before it launches anything else, so
    the run winds down instead of continuing to burn the host after the first
    real signal.  Projects that wind down that way are reported ABORTED, never
    as a second stop condition.
    """
    with HALT_LOCK:
        HALT.append({"reason": reason, **detail})
    m.STOP.set()


def read_tsv(path: Path) -> tuple[list[str], list[list[str]]]:
    rows: list[list[str]] = []
    with path.open(encoding="utf-8", newline="") as stream:
        for row in csv.reader(stream, delimiter="\t"):
            if row and row[0].startswith("#"):
                continue
            rows.append(row)
    return rows[0], rows[1:]


def load_link_only() -> list[dict[str, object]]:
    """The 33 link-only rows of the exclusions ledger, index-resolved.

    Both the pre-relabel keyword (``isa-attr:z-subset``) and the post-relabel
    form (``link-only:isa-attr:z-subset``) are accepted so the runner stays
    re-runnable after the ledger is restamped.
    """
    _header, rows = read_tsv(EXCLUSIONS)
    out: list[dict[str, object]] = []
    for slug, cls, keyword, excerpt, pointer in rows:
        base = keyword.split("link-only:", 1)[-1]
        if base not in LINK_ONLY_KEYWORDS:
            continue
        match = re.search(r"projects/(\d{4})-", pointer)
        if not match:
            raise RuntimeError(f"exclusions row without a resolvable index: {slug}")
        out.append({
            "index": int(match.group(1)), "slug": slug, "class": cls,
            "keyword": base, "excerpt": excerpt, "pointer": pointer,
            "signature": LINK_ONLY_KEYWORDS[base],
        })
    out.sort(key=lambda row: row["index"])
    only = os.environ.get("LINKONLY_ONLY", "").strip()
    if only:  # rehearsal hook: comma-separated indices, never used for evidence
        wanted = {int(x) for x in only.split(",")}
        out = [row for row in out if row["index"] in wanted]
    return out


LD_PATH = re.compile(r"\S*riscv-none-embed/bin/ld:")


def normalise(text: str) -> str:
    """Path-normalised diagnostic quote, same placeholders render_manifest uses.

    Both toolchain roots fold onto ``<TC>``: the two lanes name their toolchain
    differently by construction, so a raw comparison of the two link diagnostics
    could never agree even when the failure is identical.
    """
    line = LD_PATH.sub("<TC>/bin/ld:", text.replace("\t", " ")).strip()
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


def signature_line(log_dir: str, side: str, signature: str) -> str:
    """First build-log line carrying the ledgered failure signature, normalised."""
    for name in (f"{side}-build.stderr", f"{side}-build.stdout"):
        path = Path(log_dir) / name
        if not path.is_file():
            continue
        try:
            data = path.read_bytes()[: 8 * 1024 * 1024]
        except OSError:
            continue
        for raw in data.decode("utf-8", "replace").splitlines():
            if signature in raw:
                return normalise(raw)
    return ""


def artifact_rows(artifacts: dict[str, dict[str, object]]) -> list[tuple[str, str, int, str]]:
    rows = []
    for name in sorted(artifacts, key=lambda x: os.fsencode(x)):
        info = artifacts[name]
        rows.append((f"obj/{name}", str(info["class"]), int(info["size"]), str(info["sha256"])))
    return rows


def gate_map(artifacts: dict[str, dict[str, object]]) -> dict[str, tuple[int, str]]:
    return {f"obj/{name}": (int(info["size"]), str(info["sha256"]))
            for name, info in artifacts.items() if info["class"] == "gate"}


def check_side(entry: dict[str, object], side: str, result) -> tuple[bool, str]:
    """Ledger conformance of one build: compiled but did not link, same reason.

    Returns ``(ok, signature_line)``; the signature line is the normalised build
    log line that carries this project's ledgered failure, so the two sides can
    be shown to fail for the same reason and not merely to fail.
    """
    index, slug = entry["index"], entry["slug"]
    if m.STOP.is_set() and result.build == "NOT-RUN":
        return False, ""
    forbidden = sorted(name for name in result.artifacts if name.endswith(FORBIDDEN_SUFFIXES))
    if forbidden:
        halt("linked-artifact-present", {"index": index, "project": slug, "side": side,
                                         "artifacts": forbidden, "log_dir": result.log_dir})
        return False, ""
    if result.conversion != "PASS":
        halt("conversion-not-pass", {"index": index, "project": slug, "side": side,
                                     "conversion": result.conversion, "reason": result.reason,
                                     "log_dir": result.log_dir})
        return False, ""
    if result.build != "FAIL":
        halt("build-status-off-ledger", {"index": index, "project": slug, "side": side,
                                         "build": result.build, "reason": result.reason,
                                         "log_dir": result.log_dir})
        return False, ""
    line = signature_line(result.log_dir, side, str(entry["signature"]))
    if not line:
        halt("diagnostic-off-ledger", {"index": index, "project": slug, "side": side,
                                       "expected_signature": entry["signature"],
                                       "first_diagnostic": result.first_diagnostic[:512],
                                       "log_dir": result.log_dir})
        return False, ""
    if not gate_map(result.artifacts):
        halt("no-objects", {"index": index, "project": slug, "side": side, "log_dir": result.log_dir})
        return False, ""
    return True, line


def run_project(entry: dict[str, object], project: Path, jobs: int):
    """official r1 -> official r2 -> stability gate -> ours -> compare."""
    index = int(entry["index"])
    slug = str(entry["slug"])
    started = time.monotonic()
    root = m.project_dir_for(index, project)
    root.mkdir(parents=True, exist_ok=True)
    link = root / "toolchain-current"
    link_before = os.readlink(link) if link.is_symlink() else ""

    state = {
        "index": index, "project": slug, "keyword": entry["keyword"], "class": entry["class"],
        "link_before": link_before, "link_after": "", "jobs": jobs,
        "official_r1": {}, "official_r2": {}, "ours": {},
        "double_run": "NOT-RUN", "compare": "NOT-RUN",
        "counts": {"gate_match": 0, "gate_diff": 0, "gate_missing": 0, "gate_extra": 0,
                   "aux_match": 0, "aux_diff": 0, "aux_missing": 0, "aux_extra": 0},
        "objects": 0, "elapsed_s": 0.0,
        "official_signature_line": "", "ours_signature_line": "", "signature_lines_equal": "",
    }
    double_rows: list[list[str]] = []
    compare_rows: list[list[str]] = []
    if m.STOP.is_set():
        state["double_run"] = state["compare"] = "ABORTED"
        return state, double_rows, compare_rows

    r1 = m.build_side(index, project, root, SIDE_R1, m.CANONICAL, jobs)
    state["official_r1"] = {"conversion": r1.conversion, "build": r1.build, "bin": r1.bin_status,
                            "first_diagnostic": r1.first_diagnostic[:512], "artifacts": len(r1.artifacts)}
    ok, state["official_signature_line"] = check_side(entry, SIDE_R1, r1)
    if not ok:
        state["elapsed_s"] = round(time.monotonic() - started, 3)
        return state, double_rows, compare_rows

    r2 = m.build_side(index, project, root, SIDE_R2, m.CANONICAL, jobs)
    state["official_r2"] = {"conversion": r2.conversion, "build": r2.build, "bin": r2.bin_status,
                            "first_diagnostic": r2.first_diagnostic[:512], "artifacts": len(r2.artifacts)}
    ok, _r2_line = check_side(entry, SIDE_R2, r2)
    if not ok:
        state["elapsed_s"] = round(time.monotonic() - started, 3)
        return state, double_rows, compare_rows

    g1, g2 = gate_map(r1.artifacts), gate_map(r2.artifacts)
    stable = g1 == g2
    for name in sorted(set(g1) | set(g2), key=os.fsencode):
        a, b = g1.get(name), g2.get(name)
        double_rows.append([str(index), slug, name, "gate",
                            str(a[0]) if a else "", a[1] if a else "",
                            str(b[0]) if b else "", b[1] if b else "",
                            "STABLE" if a == b else "UNSTABLE"])
    state["double_run"] = "STABLE" if stable else "UNSTABLE"
    state["objects"] = len(g1)
    if not stable:
        halt("official-double-run-unstable", {
            "index": index, "project": slug,
            "only_in_r1": sorted(set(g1) - set(g2)), "only_in_r2": sorted(set(g2) - set(g1)),
            "sha_differs": sorted(n for n in set(g1) & set(g2) if g1[n] != g2[n]),
            "log_dir": r1.log_dir})
        state["elapsed_s"] = round(time.monotonic() - started, 3)
        return state, double_rows, compare_rows

    ours = m.build_side(index, project, root, SIDE_OURS, OURS, jobs)
    link_after = os.readlink(link) if link.is_symlink() else ""
    state["link_after"] = link_after
    state["ours"] = {"conversion": ours.conversion, "build": ours.build, "bin": ours.bin_status,
                     "first_diagnostic": ours.first_diagnostic[:512], "artifacts": len(ours.artifacts)}
    ok, state["ours_signature_line"] = check_side(entry, SIDE_OURS, ours)
    state["signature_lines_equal"] = str(state["official_signature_line"] == state["ours_signature_line"])
    if not ok:
        state["elapsed_s"] = round(time.monotonic() - started, 3)
        return state, double_rows, compare_rows
    if state["signature_lines_equal"] != "True":
        halt("link-diagnostic-divergence", {
            "index": index, "project": slug,
            "official": state["official_signature_line"], "ours": state["ours_signature_line"],
            "official_log_dir": r1.log_dir, "ours_log_dir": ours.log_dir})
        state["elapsed_s"] = round(time.monotonic() - started, 3)
        return state, double_rows, compare_rows

    base_all = {name: (str(info["class"]), int(info["size"]), str(info["sha256"]))
                for name, info in ((f"obj/{k}", v) for k, v in r1.artifacts.items())}
    ours_all = {name: (str(info["class"]), int(info["size"]), str(info["sha256"]))
                for name, info in ((f"obj/{k}", v) for k, v in ours.artifacts.items())}
    counts = state["counts"]
    for name in sorted(set(base_all) | set(ours_all), key=os.fsencode):
        base, mine = base_all.get(name), ours_all.get(name)
        if base is not None and mine is not None:
            cls = base[0]
            status = "MATCH" if base[2] == mine[2] else "DIFF"
            row = [str(index), slug, name, cls, str(base[1]), str(mine[1]), base[2], mine[2], status]
        elif base is not None:
            cls, status = base[0], "MISSING"
            row = [str(index), slug, name, cls, str(base[1]), "", base[2], "", status]
        else:
            cls = "gate" if name.endswith(GATE_SUFFIXES) else "aux"
            status = "EXTRA"
            row = [str(index), slug, name, cls, "", str(mine[1]), "", mine[2], status]
        counts[f"{cls}_{status.lower()}"] += 1
        compare_rows.append(row)
    state["compare"] = "MATCH" if counts["gate_diff"] == counts["gate_missing"] == 0 else "MISMATCH"
    if state["compare"] != "MATCH":
        offenders = [r for r in compare_rows if r[3] == "gate" and r[8] in ("DIFF", "MISSING")]
        halt("ours-gate-mismatch", {
            "index": index, "project": slug, "rows": offenders,
            "official_log_dir": r1.log_dir, "ours_log_dir": ours.log_dir,
            "official_build_stdout": f"{r1.log_dir}/{SIDE_R1}-build.stdout",
            "official_build_stderr": f"{r1.log_dir}/{SIDE_R1}-build.stderr",
            "ours_build_stdout": f"{ours.log_dir}/{SIDE_OURS}-build.stdout",
            "ours_build_stderr": f"{ours.log_dir}/{SIDE_OURS}-build.stderr"})
    state["elapsed_s"] = round(time.monotonic() - started, 3)
    return state, double_rows, compare_rows


PROJECT_HEADER = [
    "index", "project", "keyword", "exclusion_class", "double_run", "compare", "objects",
    "gate_match", "gate_diff", "gate_missing", "gate_extra",
    "aux_match", "aux_diff", "aux_missing", "aux_extra",
    "official_r1_build", "official_r2_build", "ours_build",
    "official_first_diagnostic", "ours_first_diagnostic",
    "official_signature_line", "ours_signature_line", "signature_lines_equal",
    "symlink_before", "symlink_after", "elapsed_s", "make_jobs",
]
DOUBLE_HEADER = ["index", "project", "artifact", "class", "r1_size", "r1_sha256", "r2_size", "r2_sha256", "status"]
COMPARE_HEADER = ["index", "project", "artifact", "class", "official_size", "ours_size",
                  "official_sha256", "ours_sha256", "status"]


def project_row(state: dict[str, object]) -> list[str]:
    c = state["counts"]
    return [
        str(state["index"]), str(state["project"]), str(state["keyword"]), str(state["class"]),
        str(state["double_run"]), str(state["compare"]), str(state["objects"]),
        str(c["gate_match"]), str(c["gate_diff"]), str(c["gate_missing"]), str(c["gate_extra"]),
        str(c["aux_match"]), str(c["aux_diff"]), str(c["aux_missing"]), str(c["aux_extra"]),
        str(state["official_r1"].get("build", "NOT-RUN")),
        str(state["official_r2"].get("build", "NOT-RUN")),
        str(state["ours"].get("build", "NOT-RUN")),
        str(state["official_r1"].get("first_diagnostic", ""))[:300],
        str(state["ours"].get("first_diagnostic", ""))[:300],
        str(state["official_signature_line"]), str(state["ours_signature_line"]),
        str(state["signature_lines_equal"]),
        str(state["link_before"]), str(state["link_after"]),
        "%.3f" % float(state["elapsed_s"]), str(state["jobs"]),
    ]


def main() -> int:
    os.umask(0o022)
    STAGE.mkdir(parents=True, exist_ok=True)
    (STAGE / "identity").mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ") + "-" + str(os.getpid())
    # every census_runner helper writes into module-level STAGE / LEDGER_FILE;
    # both are re-pointed before a single command runs so nothing lands in the
    # sealed census evidence directory.
    m.STAGE = STAGE
    m.LEDGER_FILE = STAGE / "command-ledger.tsv"
    m.write_text(STAGE / "run-id.txt", run_id + "\n")
    m.write_tsv(m.LEDGER_FILE, ["started_utc", "ended_utc", "cwd", "command_json", "returncode", "stdout", "stderr", "timeout"], [])
    m.atomic_write(STAGE / "inherited-environment.txt",
                   "".join(f"{k}={v}\n" for k, v in sorted(os.environ.items())).encode("utf-8", "surrogateescape"))

    # --- pre-flight 1: the official toolchain has not moved since the census --
    census_summary = json.loads((CENSUS_STAGE / "summary.json").read_text(encoding="utf-8"))
    canonical_identity = m.tool_identity(m.CANONICAL, "canonical")
    ours_identity = m.tool_identity(OURS, "ours")
    drift = {name: {"census": census_summary["toolchain_identity"][name]["sha256"],
                    "now": canonical_identity[name]["sha256"]}
             for name in ("gcc", "as", "ld", "objcopy", "objdump")
             if census_summary["toolchain_identity"][name]["sha256"] != canonical_identity[name]["sha256"]}
    if drift:
        raise RuntimeError(f"canonical toolchain drifted since the census: {drift}")
    m.write_text(STAGE / "identity/toolchains.json", json.dumps(
        {"canonical": canonical_identity, "ours": ours_identity,
         "ours_link": str(OURS_LINK), "ours_resolved": str(OURS),
         "canonical_drift_vs_census": "none",
         "ours_link_chain": [f"{p} -> {os.readlink(p)}" for p in
                             [Path(*OURS_LINK.parts[:i + 1]) for i in range(len(OURS_LINK.parts))]
                             if p.is_symlink()]},
        ensure_ascii=False, indent=2))

    # --- pre-flight 2: the ledger resolves to exactly the 33 link-only rows ---
    entries = load_link_only()
    expected = len({int(x) for x in os.environ["LINKONLY_ONLY"].split(",")}) if os.environ.get("LINKONLY_ONLY", "").strip() else 33
    if len(entries) != expected:
        raise RuntimeError(f"link-only ledger resolved {len(entries)} rows, expected {expected}")
    m.write_tsv(STAGE / "link-only-ledger.tsv",
                ["index", "project", "exclusion_class", "keyword", "signature", "log_pointer"],
                [[str(e["index"]), e["slug"], e["class"], e["keyword"], e["signature"], e["pointer"]] for e in entries])

    # --- pre-flight 3: freeze the ours install tree --------------------------
    ours_pre = m.save_manifest(STAGE / "ours-install-pre.jsonl", m.path_manifest(OURS))

    # --- EVT patch application, mirrored from the census / ours lanes --------
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
        rc = run_extension(run_id, entries, harness, census_summary, ours_pre, pre_evt, pre_evt_hash)
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


def run_extension(run_id, entries, harness, census_summary, ours_pre, pre_evt, pre_evt_hash) -> int:
    all_projects = harness.selected_projects("full")
    if len(all_projects) != census_summary["enumeration_total"]:
        raise RuntimeError(f"enumeration changed: {len(all_projects)} vs {census_summary['enumeration_total']}")
    for entry in entries:
        resolved = all_projects[int(entry["index"]) - 1].relative_to(m.EVT).as_posix()
        if resolved != entry["slug"]:
            raise RuntimeError(f"index {entry['index']} resolves to {resolved}, ledger says {entry['slug']}")
    m.write_text(STAGE / "inventory-discovery.txt",
                 "\n".join(f"{i}\t{p.relative_to(m.EVT).as_posix()}" for i, p in enumerate(all_projects, 1)) + "\n")

    print(f"link-only face: {len(entries)} projects", flush=True)
    states: dict[int, dict[str, object]] = {}
    doubles: dict[int, list[list[str]]] = {}
    compares: dict[int, list[list[str]]] = {}
    signal.signal(signal.SIGINT, m.signal_handler)
    signal.signal(signal.SIGTERM, m.signal_handler)
    started_all = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=m.WORKERS) as executor:
        futures = {executor.submit(run_project, e, all_projects[int(e["index"]) - 1], m.MAKE_JOBS): int(e["index"])
                   for e in entries}
        for number, future in enumerate(concurrent.futures.as_completed(futures), 1):
            index = futures[future]
            try:
                state, double_rows, compare_rows = future.result()
            except Exception as exc:
                halt("runner-exception", {"index": index, "error": repr(exc), "traceback": traceback.format_exc()})
                continue
            states[index] = state
            doubles[index] = double_rows
            compares[index] = compare_rows
            print(f"progress {number}/{len(entries)} index={index} double={state['double_run']} "
                  f"compare={state['compare']} objects={state['objects']}", flush=True)

    project_rows = [project_row(states[i]) for i in sorted(states)]
    double_rows = [r for i in sorted(doubles) for r in doubles[i]]
    compare_rows = [r for i in sorted(compares) for r in compares[i]]
    m.write_tsv(STAGE / "linkonly-project-results.tsv", PROJECT_HEADER, project_rows)
    m.write_tsv(STAGE / "official-double-run.tsv", DOUBLE_HEADER, double_rows)
    m.write_tsv(STAGE / "compare-artifacts.tsv", COMPARE_HEADER, compare_rows)
    m.write_tsv(STAGE / "gate-mismatches.tsv", COMPARE_HEADER,
                [r for r in compare_rows if r[3] == "gate" and r[8] != "MATCH"])
    m.write_tsv(STAGE / "extra-observations.tsv", COMPARE_HEADER,
                [r for r in compare_rows if r[8] == "EXTRA"])
    m.write_text(STAGE / "halt-conditions.json", json.dumps(HALT, ensure_ascii=False, indent=2))

    # golden rows to append: official r1 gate objects, project/artifact ordered
    golden_rows: list[list[str]] = []
    if not HALT:
        for index in sorted(states):
            state = states[index]
            for row in doubles[index]:
                if row[8] != "STABLE":
                    continue
                golden_rows.append([row[0], row[1], row[2], "gate-link-only", row[4], row[5]])
    m.write_tsv(STAGE / "golden-append-rows.tsv", ["index", "project", "artifact", "class", "size", "sha256"], golden_rows)

    # restore every touched neutral symlink to the official root
    restored_links = 0
    for entry in entries:
        link = m.project_dir_for(int(entry["index"]), all_projects[int(entry["index"]) - 1]) / "toolchain-current"
        if link.is_symlink() and os.readlink(link) != str(m.CANONICAL):
            m.atomic_symlink(link, m.CANONICAL)
            restored_links += 1

    ours_post = m.save_manifest(STAGE / "ours-install-post.jsonl", m.path_manifest(OURS))
    totals = {k: sum(int(s["counts"][k]) for s in states.values()) for k in
              ("gate_match", "gate_diff", "gate_missing", "gate_extra",
               "aux_match", "aux_diff", "aux_missing", "aux_extra")}
    summary = {
        "schema": "phase6-s4-linkonly-extension-v1",
        "run_id": run_id,
        "ruling": "P2-21 (DECISIONS 4f5dedb, 2026-08-17): artifact-level exclusion; .o of link-only projects enter the gate",
        "projects_expected": len(entries),
        "projects_completed": len(states),
        "objects_total": sum(int(s["objects"]) for s in states.values()),
        "double_run_stable_projects": sum(1 for s in states.values() if s["double_run"] == "STABLE"),
        "compare_match_projects": sum(1 for s in states.values() if s["compare"] == "MATCH"),
        "signature_lines_equal_projects": sum(1 for s in states.values() if s["signature_lines_equal"] == "True"),
        "counts": totals,
        "golden_append_rows": len(golden_rows),
        "halt_conditions": HALT,
        "canonical_root": str(m.CANONICAL),
        "ours_root": str(OURS),
        "ours_link": str(OURS_LINK),
        "ours_install_pre_hash": ours_pre,
        "ours_install_post_hash": ours_post,
        "ours_install_stable": ours_pre == ours_post,
        "evt_pre_hash": pre_evt_hash,
        "symlinks_restored_to_canonical": restored_links,
        "path_contract": census_summary["path_contract"],
        "debug_prefix_map_official": f"{m.CANONICAL}=>{{project_root}}/toolchain-current",
        "debug_prefix_map_ours": f"{OURS}=>{{project_root}}/toolchain-current",
        "sides": {"official_run_1": SIDE_R1, "official_run_2": SIDE_R2, "ours": SIDE_OURS},
        "source_date_epoch": m.EPOCH,
        "workers": m.WORKERS,
        "make_jobs": m.MAKE_JOBS,
        "stop_requested": m.STOP.is_set(),
        "elapsed_s": round(time.monotonic() - started_all, 3),
    }
    m.atomic_write(STAGE / "summary.json", json.dumps(summary, ensure_ascii=False, indent=2).encode("utf-8"))

    ledger_files = [p for p in STAGE.rglob("*") if p.is_file() and p.name != "STAGE_COMPLETE.json"]
    marker = {
        "schema": "phase6-s4-linkonly-extension-complete-v1",
        "run_id": run_id,
        "sealed_at_utc": m.now(),
        "input_hashes": {
            "golden": m.sha256_file(GOLDEN),
            "exclusions": m.sha256_file(EXCLUSIONS),
            "census_artifact_results": m.sha256_file(CENSUS_STAGE / "artifact-results.tsv"),
            "census_stage_complete": m.sha256_file(CENSUS_STAGE / "STAGE_COMPLETE.json"),
            "converter": m.sha256_file(m.CONVERTER),
            "census_runner": m.sha256_file(TOOLS / "census_runner.py"),
            "linkonly_runner": m.sha256_file(Path(__file__).resolve()),
        },
        "ledger_hashes": {str(p.relative_to(STAGE)): m.sha256_file(p)
                          for p in sorted(ledger_files, key=lambda p: os.fsencode(str(p.relative_to(STAGE))))},
        "summary_hash": m.sha256_file(STAGE / "summary.json"),
        "counts": totals,
    }
    m.atomic_write(STAGE / "STAGE_COMPLETE.json", json.dumps(marker, ensure_ascii=False, indent=2).encode("utf-8"))
    m.fsync_dir(STAGE)
    print("LINKONLY_DONE projects={} objects={} gate_match={} gate_diff={} gate_missing={} gate_extra={} halts={}".format(
        len(states), summary["objects_total"], totals["gate_match"], totals["gate_diff"],
        totals["gate_missing"], totals["gate_extra"], len(HALT)), flush=True)
    ok = (not HALT and len(states) == len(entries) and summary["ours_install_stable"]
          and totals["gate_diff"] == 0 and totals["gate_missing"] == 0
          and summary["double_run_stable_projects"] == len(entries)
          and summary["compare_match_projects"] == len(entries)
          and summary["signature_lines_equal_projects"] == len(entries))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
