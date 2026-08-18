#!/usr/bin/env python3
"""Render the 8.2.0 darwin-arm64 full-EVT golden manifest and exclusion table.

Independent of the census runner: every gate artifact named by the sealed
stage ledger is re-hashed from the raw work tree before it may enter the
manifest, the ledger's own hashes are re-verified against the marker, and the
manifest body is rendered twice and byte-compared before publication (the
double-entry check the 15.2.0 generator uses).

Classification of the non-PASS projects is keyword-driven over the raw build
logs.  Order of decision, deliberately capability-dominant so that -j2 stderr
interleaving cannot move a project between classes:

  1. any capability keyword anywhere in the build log  -> EXCLUDED-capability
  2. conversion stage did not PASS                     -> EXCLUDED-config (converter)
  3. a known configuration keyword matches             -> EXCLUDED-config (build)
  4. anything else                                     -> UNRESOLVED (never forced)
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
STAGE = REPO / "tmp/toolchain_8.2.0/evidence/s3/full-census/stage-a"
WORK = REPO / "tmp/toolchain_8.2.0/full-census"
EVIDENCE = REPO / "tmp/toolchain_8.2.0/evidence/s3/full-census"
OUTPUT = REPO / "analysis/golden/8.2.0-darwin-arm64-full.tsv"
EXCLUSIONS = REPO / "analysis/golden/8.2.0-darwin-arm64-full-exclusions.tsv"
AUDIT = EVIDENCE / "render-audit.json"
EXPECTED_PROJECTS = 1298
EXCERPT_BYTES = 240

# (label, category, regex).  Capability entries are ISA/tooling gaps of the
# 8.2.0 toolchain itself; config entries are project/converter problems that
# say nothing about 8.2.0's capabilities.  Evaluated in order.
CAPABILITY_RULES: list[tuple[str, str]] = [
    # gas 2.32 in the 8.2.0 package knows XW but none of the later QingKe
    # memory/bit instructions; the mnemonics come from EVT inline assembly.
    ("opcode:mcpy", r"unrecognized opcode `mcpy"),
    ("opcode:mrslu", r"unrecognized opcode `mrslu"),
    ("opcode:mrsl", r"unrecognized opcode `mrsl"),
    ("opcode:wexti", r"unrecognized opcode `wexti"),
    ("opcode:other", r"unrecognized opcode"),
    ("csr:unknown", r"unknown CSR|Error: unknown (?:csr|CSR)"),
    # bfd 2.32 cannot merge .riscv.attributes whose Tag_arch names a z*
    # subset (zmmul / zba / zbb / zbc / zbs).  Triggered by the prebuilt WCH
    # .a archives shipped inside EVT projects, i.e. a binutils capability gap,
    # not anything the converter or our compiler can influence.
    ("isa-attr:z-subset", r"unsupported ISA subset `z'"),
    ("isa-attr:other", r"unsupported ISA sub(?:set|string)|failed to merge target specific data"),
    ("march:zb", r"-march=[^ '\"]*_?zb\w"),
    ("march:zmmul", r"-march=[^ '\"]*zmmul"),
    ("march:vector", r"-march=[^ '\"]*(?:_zve|_v\d)"),
    ("march:zicsr", r"-march=[^ '\"]*zicsr"),
    ("march:rejected", r"unrecognized argument in option '-march=|Error: unknown architecture"),
    ("mabi:rejected", r"unrecognized argument in option '-mabi=|invalid ABI option"),
    ("attribute:interrupt", r"'interrupt' attribute (?:argument|directive)|argument to 'interrupt' attribute"),
    ("builtin:missing", r"implicit declaration of function '__builtin_riscv|undefined reference to `__builtin_riscv"),
    ("option:unknown", r"unrecognized command line option|unrecognized command-line option"),
    # A library the project asks for that the 8.2.0 package does not ship
    # (e.g. -lprintfloat): a packaged-library gap of this toolchain, permanent
    # for both the official and our future 8.2.0 build.
    ("lib:missing", r"cannot find -l\S+"),
]

CONFIG_RULES: list[tuple[str, str]] = [
    ("source:missing", r"fatal error: .*No such file or directory"),
    ("make:no-rule", r"No rule to make target"),
    ("link:region-overflow", r"region `?[\w.]+'? overflowed|will not fit in region|section .* overlaps section"),
    ("link:script", r"cannot open linker script|undefined symbol .* referenced in expression"),
    ("link:undefined", r"undefined reference to"),
    ("ice", r"internal compiler error"),
]
# Deliberately no catch-all: a failure matching nothing above stays UNRESOLVED
# and is reported as such rather than being folded into either class.


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_tsv(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        rows = list(csv.reader(stream, delimiter="\t"))
    return rows[0], rows[1:]


def repo_rel(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


LD_PATH = re.compile(r"\S*riscv-none-embed/bin/ld:")


def excerpt(text: str) -> str:
    """Path-normalised, byte-capped quote of the deciding diagnostic.

    The absolute toolchain/EVT/work prefixes are collapsed to placeholders so
    the 240-byte budget is spent on the message rather than on a 120-character
    ld search path; the placeholders are the manifest header's own paths.
    """
    line = LD_PATH.sub("<TC>/bin/ld:", text.replace("\t", " "))
    for prefix, token in ((str(WORK), "<WORK>"), (str(REPO / "ref/wch-evt"), "<EVT>"), (str(REPO / "ref/gcc/darwin-arm64/8.2.0"), "<TC>"), (str(REPO), "<REPO>")):
        line = line.replace(prefix, token)
    return line.encode("utf-8", "replace")[:EXCERPT_BYTES].decode("utf-8", "ignore")


def log_text(evidence: str) -> str:
    chunks: list[str] = []
    logs = WORK / evidence / "logs"
    for name in ("canonical-build.stderr", "canonical-build.stdout", "canonical-convert.stderr", "canonical-convert.stdout", "canonical-objcopy.stderr"):
        path = logs / name
        if path.is_file():
            try:
                chunks.append(path.read_bytes()[: 4 * 1024 * 1024].decode("utf-8", "replace"))
            except OSError:
                continue
    return "\n".join(chunks)


def matching_line(text: str, pattern: str) -> str:
    match = re.search(pattern, text)
    if match is None:
        return ""
    start = text.rfind("\n", 0, match.start()) + 1
    end = text.find("\n", match.end())
    return text[start : end if end != -1 else len(text)].strip().replace("\t", " ")


def classify(row: dict[str, str]) -> tuple[str, str, str]:
    """(category, keyword, excerpt).  The excerpt is the line the rule matched,
    so the table quotes the diagnostic that decided the class rather than
    whichever line happened to come first under -j2."""
    text = log_text(row["evidence"])
    fallback = row["first_diagnostic"] or row["fallback_line"] or row["reason"]
    for label, pattern in CAPABILITY_RULES:
        line = matching_line(text, pattern)
        if line:
            return "EXCLUDED-capability", label, line
    if row["conversion"] != "PASS":
        return "EXCLUDED-config", f"converter:{row['conversion'].lower()}", fallback
    for label, pattern in CONFIG_RULES:
        line = matching_line(text, pattern)
        if line:
            return "EXCLUDED-config", label, line
    if row["build"] == "TIMEOUT" or row["bin"] == "TIMEOUT":
        return "EXCLUDED-config", "host:timeout", row["reason"]
    return "UNRESOLVED", "unmapped", fallback


def main() -> int:
    marker = json.loads((STAGE / "STAGE_COMPLETE.json").read_text(encoding="utf-8"))
    summary = json.loads((STAGE / "summary.json").read_text(encoding="utf-8"))
    identity = json.loads((STAGE / "identity/toolchains.json").read_text(encoding="utf-8"))["canonical"]
    audit: dict[str, object] = {"schema": "phase6-s3-render-audit-v1"}

    # 1. sealed-ledger integrity
    bad = [rel for rel, expected in sorted(marker["ledger_hashes"].items()) if sha256_file(STAGE / rel) != expected]
    if bad:
        raise SystemExit(f"stage ledger hash mismatch: {bad[:5]}")
    audit["ledger_recheck"] = f"{len(marker['ledger_hashes'])}/{len(marker['ledger_hashes'])}"
    if summary["evt_exact_restored"] is not True:
        raise SystemExit("census did not restore the EVT tree exactly")
    if marker["project_total"] != EXPECTED_PROJECTS or summary["enumeration_total"] != EXPECTED_PROJECTS:
        raise SystemExit(f"denominator is not {EXPECTED_PROJECTS}")

    # 2. project ledger
    header, rows = read_tsv(STAGE / "project-results.tsv")
    projects = [dict(zip(header, row)) for row in rows]
    if len(projects) != EXPECTED_PROJECTS:
        raise SystemExit(f"project-results rows = {len(projects)}")
    indices = [int(row["index"]) for row in projects]
    if sorted(indices) != list(range(1, EXPECTED_PROJECTS + 1)):
        raise SystemExit("project indices are not exactly 1..1298")
    discovery = (STAGE / "inventory-discovery.txt").read_text(encoding="utf-8").splitlines()
    if len(discovery) != EXPECTED_PROJECTS:
        raise SystemExit("inventory-discovery line count mismatch")
    for row, line in zip(sorted(projects, key=lambda r: int(r["index"])), discovery):
        number, name = line.split("\t", 1)
        if number != row["index"] or name != row["project"]:
            raise SystemExit(f"enumeration/result mismatch at index {number}")

    passed = {int(row["index"]): row for row in projects if row["status"] == "PASS"}
    failed = [row for row in projects if row["status"] != "PASS"]

    # 3. re-hash every gate artifact from the raw work tree
    art_header, art_rows = read_tsv(STAGE / "artifact-results.tsv")
    gate: list[tuple[int, str, str, str, int, str]] = []
    rehash_ok = 0
    rehash_bad: list[str] = []
    suffixes: Counter[str] = Counter()
    for row in art_rows:
        index, project, artifact, cls, size, digest = int(row[0]), row[1], row[2], row[3], int(row[4]), row[5]
        if cls != "gate":
            continue
        if index not in passed:
            rehash_bad.append(f"{index}:{artifact}:project-not-PASS")
            continue
        path = WORK / passed[index]["evidence"] / "canonical" / artifact
        if not path.is_file():
            rehash_bad.append(f"{index}:{artifact}:missing")
            continue
        actual_size, actual_hash = path.stat().st_size, sha256_file(path)
        if actual_size != size or actual_hash != digest:
            rehash_bad.append(f"{index}:{artifact}:changed")
            continue
        rehash_ok += 1
        suffixes[Path(artifact).suffix] += 1
        gate.append((index, project, artifact, cls, size, digest))
    if rehash_bad:
        raise SystemExit(f"gate re-hash failures ({len(rehash_bad)}): {rehash_bad[:5]}")
    # every PASS project must contribute exactly one ELF, one BIN and >=1 object
    per_project: dict[int, Counter[str]] = {}
    for index, _project, artifact, _cls, _size, _digest in gate:
        per_project.setdefault(index, Counter())[Path(artifact).suffix] += 1
    shape_bad = [
        index for index in passed
        if per_project.get(index, Counter())[".elf"] != 1
        or per_project.get(index, Counter())[".bin"] != 1
        or per_project.get(index, Counter())[".o"] < 1
    ]
    if shape_bad:
        raise SystemExit(f"PASS projects with unexpected gate shape: {shape_bad[:5]}")
    audit["gate_shape_checked"] = len(passed)
    gate.sort(key=lambda item: (item[0], os.fsencode(item[2])))
    audit["raw_rehash"] = f"{rehash_ok}/{rehash_ok}"
    audit["gate_breakdown"] = dict(sorted(suffixes.items()))

    # 4. classification
    classified: list[tuple[str, str, str, str, str]] = []
    counts: Counter[str] = Counter()
    keywords: Counter[str] = Counter()
    for row in sorted(failed, key=lambda r: int(r["index"])):
        category, keyword, first = classify(row)
        counts[category] += 1
        keywords[f"{category}|{keyword}"] += 1
        pointer = repo_rel(WORK / row["evidence"] / "logs")
        classified.append((row["project"], category, keyword, excerpt(first), pointer))
    unresolved = counts["UNRESOLVED"]
    total_check = len(passed) + counts["EXCLUDED-capability"] + counts["EXCLUDED-config"] + unresolved
    if total_check != EXPECTED_PROJECTS:
        raise SystemExit(f"class partition {total_check} != {EXPECTED_PROJECTS}")

    with EXCLUSIONS.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(["slug", "class", "keyword", "first_error_excerpt", "log_pointer"])
        writer.writerows(classified)
    exclusions_hash = sha256_file(EXCLUSIONS)

    # 5. manifest
    def render() -> bytes:
        lines = [
            "# golden_manifest_version=2",
            "# manifest_kind=full-evt-gate",
            "# platform=darwin-arm64",
            f"# target={identity['target']}",
            f"# toolchain={summary['toolchain_version']}",
            "# toolchain_version=8.2.0",
            f"# toolchain_real_root={identity['root']}",
            f"# toolchain_exec=x86_64-via-rosetta on darwin-arm64 host ({identity['arch'].split(': ', 1)[-1]})",
            f"# canonical_gcc_sha256={identity['gcc']['sha256']}",
            f"# canonical_as_sha256={identity['as']['sha256']}",
            f"# canonical_ld_sha256={identity['ld']['sha256']}",
            f"# canonical_objcopy_sha256={identity['objcopy']['sha256']}",
            f"# canonical_objdump_sha256={identity['objdump']['sha256']}",
            f"# SOURCE_DATE_EPOCH={summary['source_date_epoch']}",
            f"# source_run_id={summary['run_id']}",
            f"# source_run_path={repo_rel(STAGE / 'run-id.txt')}",
            f"# source_run_sha256={sha256_file(STAGE / 'run-id.txt')}",
            f"# source_marker_path={repo_rel(STAGE / 'STAGE_COMPLETE.json')}",
            f"# source_marker_sha256={sha256_file(STAGE / 'STAGE_COMPLETE.json')}",
            f"# source_summary_path={repo_rel(STAGE / 'summary.json')}",
            f"# source_summary_sha256={sha256_file(STAGE / 'summary.json')}",
            f"# source_artifact_results_path={repo_rel(STAGE / 'artifact-results.tsv')}",
            f"# source_artifact_results_sha256={sha256_file(STAGE / 'artifact-results.tsv')}",
            f"# source_project_results_path={repo_rel(STAGE / 'project-results.tsv')}",
            f"# source_project_results_sha256={sha256_file(STAGE / 'project-results.tsv')}",
            f"# source_inventory_path={repo_rel(STAGE / 'effective-project-inventory.tsv')}",
            f"# source_inventory_sha256={sha256_file(STAGE / 'effective-project-inventory.tsv')}",
            f"# source_enumeration_path={repo_rel(STAGE / 'inventory-discovery.txt')}",
            f"# source_enumeration_sha256={sha256_file(STAGE / 'inventory-discovery.txt')}",
            f"# runner_path={repo_rel(REPO / 'tmp/toolchain_8.2.0/tools/full-census/census_runner.py')}",
            f"# runner_sha256={marker['input_hashes']['runner']}",
            f"# converter_path={repo_rel(REPO / 'ref/wch-evt/tools/wvproj_to_make.py')}",
            f"# converter_sha256={marker['input_hashes']['converter']}",
            f"# patch_allowlist_sha256={marker['input_hashes']['patch_allowlist']}",
            f"# source_evt_manifest_sha256={summary['evt_pre_hash']}",
            "# enumeration=ref/wch-evt/tests/test_wvproj_to_make.py:selected_projects(\"full\") after patches/apply.sh (phase-3b denominator)",
            f"# work_root={summary['work_root']}",
            f"# path_contract={summary['path_contract']}",
            f"# cwd_example={WORK}/projects/0001-<sanitised-project-path>/work",
            f"# debug_prefix_map={summary['debug_prefix_map']}",
            f"# converter_invocation={summary['converter_invocation']}",
            f"# make_invocation=make -f Makefile -f harness.mk -j{summary['make_jobs']} COMPILER_PATH=<project_root>/toolchain-current/bin/riscv-none-embed-gcc TOOLCHAIN_BIN=<project_root>/toolchain-current/bin CROSS_PREFIX=riscv-none-embed- DEBUG_PREFIX_FROM=<real> DEBUG_PREFIX_TO=<neutral> all",
            f"# concurrency=workers={summary['workers']},make_jobs={summary['make_jobs']}",
            "# determinism_policy=single full pass; two-run same-path raw-hash self-check on one -g project and one non-g project (phase-3b canonical/canonical self-check, canonical-only); no full double run",
            f"# determinism_selfcheck={summary['selfcheck']['verdict']}",
            f"# serial_retry_projects={summary['serial_retry_count']}",
            f"# canonical_projects={len(passed)}/{EXPECTED_PROJECTS}",
            f"# excluded_capability={counts['EXCLUDED-capability']}",
            f"# excluded_config={counts['EXCLUDED-config']}",
            f"# unresolved={unresolved}",
            f"# class_partition={len(passed)}+{counts['EXCLUDED-capability']}+{counts['EXCLUDED-config']}+{unresolved}={EXPECTED_PROJECTS}",
            f"# exclusions_path={repo_rel(EXCLUSIONS)}",
            f"# exclusions_sha256={exclusions_hash}",
            f"# raw_rehash={rehash_ok}/{rehash_ok}",
            "# gate_breakdown=" + ",".join(f"{suffix}={count}" for suffix, count in sorted(suffixes.items())),
            "# sorting=int(index),os.fsencode(artifact)",
            "index\tproject\tartifact\tclass\tsize\tsha256",
        ]
        body = "".join(f"{index}\t{project}\t{artifact}\t{cls}\t{size}\t{digest}\n" for index, project, artifact, cls, size, digest in gate)
        return ("\n".join(lines) + "\n" + body).encode("utf-8")

    first_render, second_render = render(), render()
    if first_render != second_render:
        raise SystemExit("manifest renders are not byte-identical")
    OUTPUT.write_bytes(first_render)

    audit.update({
        "manifest_path": repo_rel(OUTPUT),
        "manifest_sha256": sha256_file(OUTPUT),
        "manifest_double_render_identical": True,
        "exclusions_path": repo_rel(EXCLUSIONS),
        "exclusions_sha256": exclusions_hash,
        "projects_total": EXPECTED_PROJECTS,
        "projects_pass": len(passed),
        "counts": {key: counts[key] for key in ("EXCLUDED-capability", "EXCLUDED-config", "UNRESOLVED")},
        "keyword_distribution": dict(sorted(keywords.items(), key=lambda item: (-item[1], item[0]))),
        "determinism": summary["selfcheck"]["verdict"],
        "run_id": summary["run_id"],
    })
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: audit[key] for key in ("projects_pass", "counts", "raw_rehash", "manifest_sha256", "exclusions_sha256")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
