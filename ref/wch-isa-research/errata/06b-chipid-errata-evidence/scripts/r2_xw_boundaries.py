#!/usr/bin/env python3
"""Classify raw WCH-X slots at producer-objdump instruction boundaries."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
from collections import Counter, defaultdict


FORMS = (
    ("c.lbu", 0x2000, 0xE003), ("c.lhu", 0x2002, 0xE003),
    ("c.sb", 0xA000, 0xE003), ("c.sh", 0xA002, 0xE003),
    ("c.lbusp", 0x8000, 0xF863), ("c.lhusp", 0x8020, 0xF863),
    ("c.sbsp", 0x8040, 0xF863), ("c.shsp", 0x8060, 0xF863),
)

TOOLS = {
    "gcc8-mrs24": "MRS_Toolchain_MAC_V240/Toolchain/RISC-V Embedded GCC/bin/riscv-none-embed-objdump",
    "gcc8-mrs25": "tmp/mrs-2.5/WCH/Toolchain/RISC-V Embedded GCC/bin/riscv-none-embed-objdump",
    "gcc12-mrs24": "MRS_Toolchain_MAC_V240/Toolchain/RISC-V Embedded GCC12/bin/riscv-wch-elf-objdump",
    "gcc12-mrs25": "tmp/mrs-2.5/WCH/Toolchain/RISC-V Embedded GCC12/bin/riscv-wch-elf-objdump",
    "gcc15-macos": "MRS_Toolchain_MAC_V240/Toolchain/RISC-V Embedded GCC15/bin/riscv32-wch-elf-objdump",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def form(word: int) -> str | None:
    for name, match, mask in FORMS:
        if word & mask == match:
            return name
    return None


def profile(text: str) -> str:
    low = text.lower()
    for value in ("xw3p0", "xw2p2", "xw2p0", "xw1p0"):
        if value in low:
            return value
    return "xw-version-undeclared"


def cohort(source_set: object) -> str:
    value = str(source_set)
    if value.startswith("mrs-2.4-"):
        return "mrs-2.4"
    if value.startswith("mrs-2.5-macos-"):
        return "mrs-2.5-macos"
    if value.startswith("mrs-2.5-linux-"):
        return "mrs-2.5-linux"
    return value


def producer(source_set: object) -> str:
    value = str(source_set)
    if value == "mrs-2.4-riscv-gcc8":
        return "gcc8-mrs24"
    if value == "mrs-2.5-macos-arm64-gcc8":
        return "gcc8-mrs25"
    if value == "mrs-2.4-riscv-gcc12":
        return "gcc12-mrs24"
    if value == "mrs-2.5-macos-arm64-gcc12":
        return "gcc12-mrs25"
    # Linux binaries cannot execute on this host.  GCC15 macOS is an explicit
    # cross-generation diagnostic path over the same ELF input bytes.
    return "gcc15-macos"


def run_objdump(repo: pathlib.Path, tool_label: str, path: str) -> dict[str, object]:
    tool_rel = TOOLS[tool_label]
    tool = repo / tool_rel
    try:
        p = subprocess.run([str(tool), "-d", path], cwd=repo, capture_output=True)
    except OSError as exc:
        return {"returncode": "not-executable", "stderr": repr(exc), "lines": [], "tool": tool_rel}
    text = p.stdout.decode("utf-8", "replace")
    member = "standalone"
    section = "unknown"
    lines: list[dict[str, object]] = []
    mnemonic_counts = Counter()
    for line in text.splitlines():
        match_member = re.match(r"^(.*):\s+file format\s+", line)
        if match_member:
            member = match_member.group(1)
            continue
        match_section = re.match(r"^Disassembly of section (.*):$", line)
        if match_section:
            section = match_section.group(1)
            continue
        match_inst = re.match(r"^\s*([0-9a-fA-F]+):\s+([0-9a-fA-F]{4})(?:\s+|$)(.*)$", line)
        if not match_inst:
            continue
        word = int(match_inst.group(2), 16)
        label = form(word)
        if not label:
            continue
        tail = match_inst.group(3).strip()
        mnemonic = tail.split(None, 1)[0] if tail else "unknown"
        mnemonic_counts[mnemonic] += 1
        lines.append({
            "member": member, "section": section,
            "offset": int(match_inst.group(1), 16), "halfword": word,
            "form": label, "objdump_mnemonic": mnemonic,
            "rendering": tail,
        })
    stderr = p.stderr.decode("utf-8", "replace").replace(str(repo), "<REPO_ROOT>")
    return {
        "returncode": p.returncode, "stderr": stderr, "tool": tool_rel,
        "occurrences": len(lines), "distinct_words": len({int(x["halfword"]) for x in lines}),
        "word_set": sorted({int(x["halfword"]) for x in lines}),
        "forms": dict(sorted(Counter(str(x["form"]) for x in lines).items())),
        "raw_directive_occurrences": sum(count for name, count in mnemonic_counts.items() if name in {".insn", ".2byte", ".short", ".half"}),
        "fld_fsd_occurrences": sum(count for name, count in mnemonic_counts.items() if name in {"fld", "fsd", "c.fld", "c.fsd"}),
        "lines": lines,
    }


def set_sha(values: set[int]) -> str:
    return sha(b"".join(x.to_bytes(2, "little") for x in sorted(values)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-root", required=True)
    args = ap.parse_args()
    repo = pathlib.Path.cwd().resolve()
    run = (repo / args.run_root).resolve()
    out = run / "controls" / "xw-boundaries-r2"
    out.mkdir(parents=True, exist_ok=True)

    artifacts = []
    by_path = {}
    with (run / "primary" / "artifacts.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            artifacts.append(row)
            by_path[str(row["path"])] = row
    selected = [
        a for a in artifacts
        if (a["scope_class"] == "wch-closed" and a["role"] == "target-archive")
        or a["role"] == "rom-wrapper-archive"
    ]

    units = {}
    with (run / "controls" / "core-r2" / "unit-control-extract.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            units[str(row["scan_unit_sha256"])] = row
    physical = defaultdict(lambda: {
        "raw_occurrences": 0, "raw_words": set(), "attrs": set(), "attrs_any": False,
    })
    selected_paths = {str(a["path"]) for a in selected}
    with (run / "primary" / "occurrences.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            occ = json.loads(line)
            path = str(occ["physical_path"])
            if path not in selected_paths:
                continue
            unit = units.get(str(occ["member_sha256"]))
            if not unit:
                continue
            state = physical[path]
            state["raw_occurrences"] = int(state["raw_occurrences"]) + int(unit["xw_count"])
            state["raw_words"].update(int(x) for x in unit["xw_words"])
            state["attrs_any"] = bool(state["attrs_any"]) or bool(unit["attrs_present"])
            if unit["attrs_text"]:
                state["attrs"].add(str(unit["attrs_text"]))

    digest_paths = defaultdict(list)
    for artifact in selected:
        digest_paths[str(artifact["sha256"])].append(artifact)
    cache: dict[tuple[str, str], dict[str, object]] = {}
    for number, (digest, variants) in enumerate(sorted(digest_paths.items()), 1):
        representative = min(str(x["path"]) for x in variants)
        needed = {"gcc12-mrs24", "gcc15-macos"} | {producer(x["source_set"]) for x in variants}
        for tool_label in sorted(needed):
            cache[(digest, tool_label)] = run_objdump(repo, tool_label, representative)
        if number % 25 == 0:
            print(f"phase=xw-objdump archive_sha={number}/{len(digest_paths)}", flush=True)

    # Freeze canonical matched boundary lines once per raw archive SHA using
    # GCC15; build-cohort and physical tables map back to these rows.
    line_path = out / "xw-boundary-lines.tsv"
    with line_path.open("w", encoding="utf-8", newline="") as handle:
        handle.write("schema_version\tarchive_sha256\trepresentative_path\tmember\tsection\toffset\thalfword_hex\tform\tobjdump_mnemonic\trendering\n")
        for digest, variants in sorted(digest_paths.items()):
            representative = min(str(x["path"]) for x in variants)
            result = cache[(digest, "gcc15-macos")]
            for row in result["lines"]:  # type: ignore[index]
                rendering = str(row["rendering"]).replace("\t", " ").replace("\n", " ")
                handle.write(
                    f"2\t{digest}\t{representative}\t{row['member']}\t{row['section']}\t{row['offset']}\t"
                    f"0x{int(row['halfword']):04x}\t{row['form']}\t{row['objdump_mnemonic']}\t{rendering}\n"
                )

    # One row per delivery-cohort/content group reproduces the prompt's 187
    # denominator without conflating it with the 122 global raw SHA groups.
    build_groups = {}
    for artifact in selected:
        key = (cohort(artifact["source_set"]), str(artifact["sha256"]))
        build_groups.setdefault(key, []).append(artifact)
    build_path = out / "xw-boundary-build-groups.tsv"
    build_rows = []
    for (cohort_name, digest), variants in sorted(build_groups.items()):
        representative_artifact = min(variants, key=lambda x: str(x["path"]).encode())
        path = str(representative_artifact["path"])
        attrs = "\n".join(sorted(physical[path]["attrs"]))
        tool_label = producer(representative_artifact["source_set"])
        result = cache[(digest, tool_label)]
        build_rows.append({
            "cohort": cohort_name, "archive_sha256": digest,
            "representative_path": path, "producer_tool": tool_label,
            "profile": profile(attrs), "attrs_present": bool(physical[path]["attrs_any"]),
            "boundary_xw_occurrences": result["occurrences"],
            "boundary_xw_distinct": result["distinct_words"],
            "raw_directive_occurrences": result["raw_directive_occurrences"],
            "fld_fsd_occurrences": result["fld_fsd_occurrences"],
            "objdump_returncode": result["returncode"],
        })
    build_cols = tuple(build_rows[0].keys())
    with build_path.open("w", encoding="utf-8", newline="") as handle:
        handle.write("schema_version\t" + "\t".join(build_cols) + "\n")
        for row in build_rows:
            handle.write("2\t" + "\t".join(str(row[c]).lower() if isinstance(row[c], bool) else str(row[c]) for c in build_cols) + "\n")

    diagnostic_path = out / "xw-physical-diagnostics.tsv"
    diagnostic_rows = []
    for artifact in sorted(selected, key=lambda x: str(x["path"]).encode()):
        path = str(artifact["path"])
        digest = str(artifact["sha256"])
        state = physical[path]
        attrs = "\n".join(sorted(state["attrs"]))
        p = profile(attrs)
        canonical = cache[(digest, "gcc15-macos")]
        boundary_count = int(canonical["occurrences"])
        competing_count = int(canonical["fld_fsd_occurrences"])
        confirmed_count = boundary_count - competing_count
        unresolved_count = int(state["raw_occurrences"]) - boundary_count
        raw_set = set(int(x) for x in state["raw_words"])
        boundary_set = set(int(x) for x in canonical["word_set"])
        competing_set = {
            int(x["halfword"]) for x in canonical["lines"]  # type: ignore[index]
            if str(x["objdump_mnemonic"]) in {"fld", "fsd", "c.fld", "c.fsd"}
        }
        confirmed_set = boundary_set - competing_set
        unresolved_set = raw_set - boundary_set
        union_set = confirmed_set | competing_set | unresolved_set
        gcc12 = cache[(digest, "gcc12-mrs24")]
        gcc15 = canonical
        diagnostic_rows.append({
            "path": path, "source_set": artifact["source_set"], "archive_sha256": digest,
            "profile": p, "attrs_present": bool(state["attrs_any"]),
            "raw_slot_occurrences": state["raw_occurrences"],
            "classified_noncode_or_padding": 0,
            "confirmed_xw": confirmed_count,
            "confirmed_competing_semantics": competing_count,
            "invalid_or_unresolved": unresolved_count,
            "occurrence_equation_ok": int(state["raw_occurrences"]) == confirmed_count + competing_count + unresolved_count,
            "raw_distinct": len(raw_set), "raw_set_sha256": set_sha(raw_set),
            "confirmed_xw_distinct": len(confirmed_set),
            "competing_distinct": len(competing_set),
            "unresolved_distinct": len(unresolved_set),
            "category_union_distinct": len(union_set),
            "category_union_sha256": set_sha(union_set),
            "distinct_union_ok": raw_set == union_set,
            "gcc12_raw_directives": gcc12["raw_directive_occurrences"],
            "gcc12_fld_fsd": gcc12["fld_fsd_occurrences"],
            "gcc15_raw_directives": gcc15["raw_directive_occurrences"],
            "gcc15_fld_fsd": gcc15["fld_fsd_occurrences"],
        })
    diag_cols = tuple(diagnostic_rows[0].keys())
    with diagnostic_path.open("w", encoding="utf-8", newline="") as handle:
        handle.write("schema_version\t" + "\t".join(diag_cols) + "\n")
        for row in diagnostic_rows:
            handle.write("2\t" + "\t".join(str(row[c]).lower() if isinstance(row[c], bool) else str(row[c]) for c in diag_cols) + "\n")

    tool_manifest = {}
    for label, relpath in sorted(TOOLS.items()):
        data = (repo / relpath).read_bytes()
        tool_manifest[label] = {"path": relpath, "size": len(data), "sha256": sha(data)}
    legacy_rows = [x for x in build_rows if x["cohort"] != "mrs-2.5-linux"]
    legacy_using = [x for x in legacy_rows if int(x["boundary_xw_occurrences"]) > 0]
    summary = {
        "schema_version": "2",
        "status": "pass" if (
            len(legacy_rows) == 187
            and len(legacy_using) == 100
            and sum(int(x["boundary_xw_occurrences"]) for x in legacy_rows) == 19344
            and all(x["occurrence_equation_ok"] and x["distinct_union_ok"] for x in diagnostic_rows)
        ) else "failed",
        "legacy": {
            "build_groups": len(legacy_rows),
            "boundary_xw_using_groups": len(legacy_using),
            "boundary_xw_occurrences": sum(int(x["boundary_xw_occurrences"]) for x in legacy_rows),
            "using_profile_groups": dict(sorted(Counter(str(x["profile"]) for x in legacy_using).items())),
        },
        "current": {
            "physical_archives": len(diagnostic_rows), "build_groups": len(build_rows),
            "boundary_xw_using_groups": sum(int(x["boundary_xw_occurrences"]) > 0 for x in build_rows),
        },
        "tools": tool_manifest,
        "files": {
            "boundary_lines_sha256": sha(line_path.read_bytes()),
            "build_groups_sha256": sha(build_path.read_bytes()),
            "physical_diagnostics_sha256": sha(diagnostic_path.read_bytes()),
        },
    }
    (out / "xw-boundary-summary.json").write_text(json.dumps(summary, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": summary["status"], "legacy": summary["legacy"], "current": summary["current"]}, sort_keys=True))
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
