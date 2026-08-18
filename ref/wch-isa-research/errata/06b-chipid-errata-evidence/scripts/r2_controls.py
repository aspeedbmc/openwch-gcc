#!/usr/bin/env python3
"""Second-round aggregate controls over fresh primary/independent outputs."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
from collections import Counter, defaultdict


INTEREST_CSRS = {0xF11, 0xF12, 0xF13, 0xF14, 0x301, 0xFC0, 0x804, 0x341, 0xBC0}
IDENTITY_CSRS = {0xF11, 0xF12, 0xF13, 0xF14, 0x301, 0xFC0}
IQ_NAMES = {"iqmath_rv32.a", "libiqmath_rv32.a", "libiqmath_rv32ec_zmmul_xw.a"}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def dump(path: pathlib.Path, value: object) -> None:
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8", newline="\n")


def profile(attrs: str) -> str:
    low = attrs.lower()
    for value in ("xw3p0", "xw2p2", "xw2p0", "xw1p0"):
        if value in low:
            return value
    return "xw-version-undeclared"


def hardware_semantics(csr: int, funct3: int, rd: int, rs1: int) -> dict[str, object]:
    reads = funct3 in (2, 3, 6, 7) or (funct3 in (1, 5) and rd != 0)
    writes = funct3 in (1, 5) or (funct3 in (2, 3, 6, 7) and rs1 != 0)
    names = {1: "CSRRW", 2: "CSRRS", 3: "CSRRC", 5: "CSRRWI", 6: "CSRRSI", 7: "CSRRCI"}
    return {
        "mnemonic": names.get(funct3, "unknown"),
        "hardware_read": reads,
        "hardware_write": writes,
        "gpr_result": rd != 0,
        "identity_or_capability_read": csr in IDENTITY_CSRS and reads,
    }


def overlapping(data: bytes, needle: bytes) -> int:
    count = 0
    at = 0
    while True:
        at = data.find(needle, at)
        if at < 0:
            return count
        count += 1
        at += 1


def rawscan_smoke(repo: pathlib.Path, run: pathlib.Path, out: pathlib.Path) -> dict[str, object]:
    canonical = (
        "find tmp/wch-evt/evt -name '*.a' -type f -print0 | "
        "xargs -0 python3 audit-report-f/followup/tools/rawscan.py"
    )
    p = subprocess.run(["zsh", "-o", "pipefail", "-c", canonical], cwd=repo, capture_output=True)
    stdout = p.stdout.replace(str(repo).encode(), b"<REPO_ROOT>")
    stderr = p.stderr.replace(str(repo).encode(), b"<REPO_ROOT>")
    # The scanner's human-readable table pads an empty detail column.  Keep
    # the content while making the frozen text artifact whitespace-clean.
    stdout = b"\n".join(line.rstrip(b" \t") for line in stdout.split(b"\n"))
    stderr = b"\n".join(line.rstrip(b" \t") for line in stderr.split(b"\n"))
    (out / "rawscan-smoke.stdout").write_bytes(stdout)
    (out / "rawscan-smoke.stderr").write_bytes(stderr)
    tool = repo / "audit-report-f/followup/tools/rawscan.py"
    return {
        "canonical_command": canonical,
        "returncode": p.returncode,
        "stdout_size": len(stdout),
        "stdout_sha256": sha(stdout),
        "stderr_size": len(stderr),
        "stderr_sha256": sha(stderr),
        "rawscan_sha256": sha(tool.read_bytes()),
        "output_normalization": "repository root redacted; trailing horizontal whitespace stripped per line",
        "expected_clue_sha256": "9545ee7a09376ffab9f353daa6c41a75836371353ea069a9817a4204efbfb3cb",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-root", required=True)
    args = ap.parse_args()
    repo = pathlib.Path.cwd().resolve()
    run = (repo / args.run_root).resolve()
    primary = run / "primary"
    out = run / "controls" / "core-r2"
    out.mkdir(parents=True, exist_ok=True)

    artifacts: list[dict[str, object]] = []
    artifact_by_path: dict[str, dict[str, object]] = {}
    with (primary / "artifacts.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            artifacts.append(row)
            artifact_by_path[str(row["path"])] = row

    # Extract only facts needed by controls from the large, conclusion-bearing
    # unit stream.  This is a new pass over the primary output, not a read of a
    # first-round table.
    units: dict[str, dict[str, object]] = {}
    extract_path = out / "unit-control-extract.jsonl"
    with (primary / "unit-primary.jsonl").open(encoding="utf-8") as source, extract_path.open("w", encoding="utf-8", newline="") as target:
        for number, line in enumerate(source, 1):
            row = json.loads(line)
            if not row.get("native_scan_applicable"):
                continue
            filtered_csr = []
            for item in row["candidates"]["csr-opcode"]:
                if int(item[3]) in INTEREST_CSRS:
                    filtered_csr.append(item)
            lui_400 = [
                item for item in row["candidates"]["address-form-opcode"]
                if int(item[3]) == 0x37 and int(item[2]) & 0xFFFFF000 == 0x40000000
            ]
            attrs_hex = str(row.get("attrs_hex", ""))
            attrs_text = bytes.fromhex(attrs_hex).decode("latin1", "ignore") if attrs_hex else ""
            xw_forms = Counter(str(item[3]) for item in row["candidates"]["xw-slot"])
            compact = {
                "scan_unit_sha256": row["scan_unit_sha256"],
                "attrs_present": bool(attrs_hex),
                "attrs_text": attrs_text,
                "csr": filtered_csr,
                "lui_40000000": lui_400,
                "xw_count": len(row["candidates"]["xw-slot"]),
                "xw_words": sorted({int(item[2]) for item in row["candidates"]["xw-slot"]}),
                "xw_forms": dict(sorted(xw_forms.items())),
                "coverage": row["coverage"],
            }
            units[str(row["scan_unit_sha256"])] = compact
            target.write(json.dumps(compact, sort_keys=True, separators=(",", ":")) + "\n")
            if number % 50000 == 0:
                print(f"phase=control-extract units={number}", flush=True)

    archive_summary: dict[str, dict[str, object]] = {}
    with (primary / "archive-summary.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            archive_summary[str(row["physical_path"])] = row

    physical: dict[str, dict[str, object]] = defaultdict(lambda: {
        "occurrences": 0, "native_occurrences": 0, "unique_units": set(),
        "xw_count": 0, "xw_words": set(), "xw_forms": Counter(), "attrs_any": False,
        "attrs_text": set(), "csr": [], "lui_40000000": [],
    })
    group: dict[str, dict[str, object]] = defaultdict(lambda: {
        "paths": set(), "units": set(), "xw_count": 0, "attrs_any": False, "attrs_text": set(),
    })
    evt_csr_rows: list[dict[str, object]] = []
    with (primary / "occurrences.jsonl").open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            occ = json.loads(line)
            path = str(occ["physical_path"])
            value = physical[path]
            value["occurrences"] = int(value["occurrences"]) + 1
            unit_sha = str(occ["member_sha256"])
            if unit_sha not in units:
                continue
            unit = units[unit_sha]
            value["native_occurrences"] = int(value["native_occurrences"]) + 1
            value["unique_units"].add(unit_sha)  # type: ignore[union-attr]
            value["xw_count"] = int(value["xw_count"]) + int(unit["xw_count"])
            value["xw_words"].update(unit["xw_words"])  # type: ignore[union-attr]
            value["xw_forms"].update(unit["xw_forms"])  # type: ignore[union-attr]
            value["attrs_any"] = bool(value["attrs_any"]) or bool(unit["attrs_present"])
            if unit["attrs_text"]:
                value["attrs_text"].add(str(unit["attrs_text"]))  # type: ignore[union-attr]
            artifact = artifact_by_path[path]
            if artifact["role"] in ("target-archive", "rom-wrapper-archive"):
                archive_sha = str(artifact["sha256"])
                g = group[archive_sha]
                g["paths"].add(path)  # type: ignore[union-attr]
                g["units"].add(unit_sha)  # type: ignore[union-attr]
                g["xw_count"] = int(g["xw_count"]) + int(unit["xw_count"])
                g["attrs_any"] = bool(g["attrs_any"]) or bool(unit["attrs_present"])
                if unit["attrs_text"]:
                    g["attrs_text"].add(str(unit["attrs_text"]))  # type: ignore[union-attr]
            for candidate in unit["csr"]:
                csr, funct3, rd, rs1 = map(int, candidate[3:7])
                row = {
                    "physical_path": path,
                    "logical_order": occ["logical_order"],
                    "member_name": occ["member_name"],
                    "same_name_ordinal": occ["same_name_ordinal"],
                    "scan_unit_sha256": unit_sha,
                    "domain_id": candidate[0], "offset": candidate[1],
                    "word": f"0x{int(candidate[2]):08x}", "csr": f"0x{csr:03x}",
                    "funct3": funct3, "rd": rd, "rs1_or_zimm": rs1,
                    **hardware_semantics(csr, funct3, rd, rs1),
                }
                value["csr"].append(row)  # type: ignore[union-attr]
                if str(artifact["source_set"]) == "evt" and str(artifact["path"]).lower().endswith(".a"):
                    evt_csr_rows.append(row)
            for candidate in unit["lui_40000000"]:
                value["lui_40000000"].append({  # type: ignore[union-attr]
                    "member_name": occ["member_name"], "domain_id": candidate[0],
                    "offset": candidate[1], "word": f"0x{int(candidate[2]):08x}",
                })
            if number % 200000 == 0:
                print(f"phase=control-occurrences rows={number}", flush=True)

    # Scope and archive closure.
    scope_counts = Counter(str(a["scope_class"]) for a in artifacts)
    source_counts = Counter(str(a["source_set"]) for a in artifacts)
    evt_archives = [a for a in artifacts if a["source_set"] == "evt" and str(a["path"]).lower().endswith(".a")]
    global_archives = list(archive_summary.values())
    closure = {
        "schema_version": "2",
        "artifact_count": len(artifacts),
        "scope_counts": dict(sorted(scope_counts.items())),
        "source_set_counts": dict(sorted(source_counts.items())),
        "evt": {
            "physical_archives": len(evt_archives),
            "basenames": len({pathlib.PurePosixPath(str(a["path"])).name for a in evt_archives}),
            "archive_sha256_groups": len({str(a["sha256"]) for a in evt_archives}),
            "member_occurrences": sum(int(archive_summary[str(a["path"])]["member_occurrences"]) for a in evt_archives),
            "unique_member_sha256": len({
                str(occ_sha) for a in evt_archives
                for occ_sha in physical[str(a["path"])]["unique_units"]  # type: ignore[union-attr]
            }),
        },
        "all_archives": {
            "physical": len(global_archives),
            "raw_records": sum(int(x["raw_record_count"]) for x in global_archives),
            "metadata_records": sum(int(x["archive_metadata_records"]) for x in global_archives),
            "logical_member_occurrences": sum(int(x["member_occurrences"]) for x in global_archives),
            "parse_failure_count": sum(1 for x in global_archives if x["parser_errors"] or int(x["trailing_bytes"]) != 0),
        },
    }
    dump(out / "scope-and-archive-closure.json", closure)

    # WCH closed XW profile/attribute matrix, preserving the 311-archive
    # historical denominator and the newly discovered Linux-GCC15 additions.
    closed_archives = [
        a for a in artifacts
        if (a["scope_class"] == "wch-closed" and a["role"] == "target-archive")
        or a["role"] == "rom-wrapper-archive"
    ]
    legacy = [a for a in closed_archives if a["source_set"] != "mrs-2.5-linux-x64-gcc15"]

    def cohort(source_set: object) -> str:
        value = str(source_set)
        if value.startswith("mrs-2.4-"):
            return "mrs-2.4"
        if value.startswith("mrs-2.5-macos-"):
            return "mrs-2.5-macos"
        if value.startswith("mrs-2.5-linux-"):
            return "mrs-2.5-linux"
        return value

    def xw_snapshot(selected: list[dict[str, object]]) -> dict[str, object]:
        # The prompt's "content/build group" deliberately keeps the MRS 2.4,
        # MRS 2.5 and EVT delivery cohorts separate even when raw archive bytes
        # are identical.  A global raw-SHA grouping would collapse 187 to 121.
        build_groups = {(cohort(a["source_set"]), str(a["sha256"])) for a in selected}
        profiles = Counter()
        used_profiles = Counter()
        attrs_groups = 0
        no_attrs_groups = 0
        for _cohort, digest in build_groups:
            g = group[digest]
            attrs_joined = "\n".join(sorted(g["attrs_text"]))  # type: ignore[arg-type]
            p = profile(attrs_joined)
            profiles[p] += 1
            attrs_groups += int(bool(g["attrs_any"]))
            no_attrs_groups += int(not bool(g["attrs_any"]))
            if int(g["xw_count"]) > 0:
                used_profiles[p] += 1
        return {
            "physical_archives": len(selected),
            "content_build_groups": len(build_groups),
            "global_raw_sha256_groups": len({digest for _cohort, digest in build_groups}),
            "profile_groups": dict(sorted(profiles.items())),
            "groups_with_attributes": attrs_groups,
            "groups_without_attributes": no_attrs_groups,
            "xw_using_groups": sum(used_profiles.values()),
            "xw_using_profile_groups": dict(sorted(used_profiles.items())),
            "all_members_attributes_absent_physical_paths": sum(1 for a in selected if not physical[str(a["path"])]["attrs_any"]),
        }

    basename_attrs: dict[str, dict[str, int]] = defaultdict(lambda: {"paths": 0, "all_members_attrs_absent": 0})
    for artifact in closed_archives:
        name = pathlib.PurePosixPath(str(artifact["path"])).name
        basename_attrs[name]["paths"] += 1
        basename_attrs[name]["all_members_attrs_absent"] += int(not physical[str(artifact["path"])]["attrs_any"])
    xw_matrix = {
        "schema_version": "2",
        "legacy_without_linux_gcc15": xw_snapshot(legacy),
        "current_with_linux_gcc15": xw_snapshot(closed_archives),
        "basename_attributes": dict(sorted(basename_attrs.items())),
    }
    dump(out / "xw-archive-profile-matrix.json", xw_matrix)

    anchors = []
    for artifact in evt_archives:
        path = str(artifact["path"])
        name = pathlib.PurePosixPath(path).name
        if name.lower() in {"libch58xble.a", "libwchnet.a", "libwchnet_float.a", "libmeshrom.a", "libmesh.a", "libwchble.a"}:
            anchors.append({
                "path": path, "basename": name, "archive_sha256": artifact["sha256"],
                "member_occurrences": archive_summary[path]["member_occurrences"],
                "unique_member_names": archive_summary[path]["unique_member_names"],
                "unique_member_sha256": archive_summary[path]["unique_member_sha256"],
                "xw_occurrences": physical[path]["xw_count"],
                "xw_forms": dict(sorted(physical[path]["xw_forms"].items())),  # type: ignore[union-attr]
                "all_members_attrs_absent": not physical[path]["attrs_any"],
            })
    dump(out / "xw-and-archive-anchor-counts.json", {"schema_version": "2", "archives": anchors})

    # CSR exact semantics and EVT negative control.
    expected_words = {0x8045A073, 0x34159073, 0x341025F3}
    for row in evt_csr_rows:
        row["expected_control_word"] = int(str(row["word"]), 16) in expected_words
    evt_csr_rows.sort(key=lambda x: (
        str(x["physical_path"]).encode(), int(x["logical_order"]) if x["logical_order"] != "not-applicable" else -1,
        str(x["domain_id"]).encode(), int(x["offset"]), str(x["word"]),
    ))
    csr_path = out / "evt-csr-control-occurrences.tsv"
    csr_columns = (
        "physical_path", "logical_order", "member_name", "same_name_ordinal", "scan_unit_sha256",
        "domain_id", "offset", "word", "csr", "funct3", "rd", "rs1_or_zimm", "mnemonic",
        "hardware_read", "hardware_write", "gpr_result", "identity_or_capability_read", "expected_control_word",
    )
    with csr_path.open("w", encoding="utf-8", newline="") as handle:
        handle.write("schema_version\t" + "\t".join(csr_columns) + "\n")
        for row in evt_csr_rows:
            handle.write("2\t" + "\t".join(str(row[c]).lower() if isinstance(row[c], bool) else str(row[c]) for c in csr_columns) + "\n")
    csr_summary = {
        "schema_version": "2", "evt_archive_count": len(evt_archives),
        "evt_archive_content_groups": len({str(a["sha256"]) for a in evt_archives}),
        "relevant_raw_candidate_occurrences": len(evt_csr_rows),
        "identity_or_capability_hardware_read_occurrences": sum(bool(x["identity_or_capability_read"]) for x in evt_csr_rows),
        "expected_control_word_occurrences": sum(bool(x["expected_control_word"]) for x in evt_csr_rows),
        "expected_control_physical_paths": sorted({str(x["physical_path"]) for x in evt_csr_rows if x["expected_control_word"]}),
        "tsv_sha256": sha(csr_path.read_bytes()),
    }
    dump(out / "evt-csr-control-summary.json", csr_summary)

    # IQMath exact byte-level negative controls over every current physical
    # archive, plus the prompt's original 40-path denominator without Linux.
    iq_artifacts = [a for a in artifacts if pathlib.PurePosixPath(str(a["path"])).name.lower() in IQ_NAMES]
    iq_rows = []
    for artifact in sorted(iq_artifacts, key=lambda a: str(a["path"]).encode()):
        data = (repo / str(artifact["path"])).read_bytes()
        masked = 0
        for at in range(0, len(data) - 3):
            word = int.from_bytes(data[at:at + 4], "little")
            masked += int(word & 0x06007FFF == 0x0000700F)
        path = str(artifact["path"])
        iq_rows.append({
            "source_set": artifact["source_set"], "path": path,
            "sha256": artifact["sha256"], "size": len(data),
            "exact_little_0f70b560": overlapping(data, bytes.fromhex("0f70b560")),
            "reverse_60b5700f": overlapping(data, bytes.fromhex("60b5700f")),
            "masked_any_operands_every_byte": masked,
            "lui_0x40000000_exec_start_candidates": len(physical[path]["lui_40000000"]),
        })
    iq_path = out / "iqmath-mcpy-negative-control.tsv"
    iq_columns = tuple(iq_rows[0].keys())
    with iq_path.open("w", encoding="utf-8", newline="") as handle:
        handle.write("schema_version\t" + "\t".join(iq_columns) + "\n")
        for row in iq_rows:
            handle.write("2\t" + "\t".join(str(row[c]) for c in iq_columns) + "\n")
    legacy_iq = [x for x in iq_rows if x["source_set"] != "mrs-2.5-linux-x64-gcc15"]
    iq_summary = {
        "schema_version": "2",
        "legacy_prompt_denominator": {"physical_archives": len(legacy_iq), "content_groups": len({x["sha256"] for x in legacy_iq})},
        "current_denominator": {"physical_archives": len(iq_rows), "content_groups": len({x["sha256"] for x in iq_rows})},
        "search_totals": {
            key: sum(int(x[key]) for x in iq_rows)
            for key in ("exact_little_0f70b560", "reverse_60b5700f", "masked_any_operands_every_byte")
        },
        "evt_lui_controls": [
            {"path": x["path"], "count": x["lui_0x40000000_exec_start_candidates"]}
            for x in iq_rows if x["source_set"] == "evt"
        ],
        "tsv_sha256": sha(iq_path.read_bytes()),
    }
    dump(out / "iqmath-control-summary.json", iq_summary)

    smoke = rawscan_smoke(repo, run, out)
    dump(out / "rawscan-smoke-summary.json", smoke)

    summary = {
        "schema_version": "2",
        "status": "pass" if (
            closure["evt"]["physical_archives"] == 49
            and closure["evt"]["archive_sha256_groups"] == 23
            and csr_summary["identity_or_capability_hardware_read_occurrences"] == 0
            and iq_summary["search_totals"] == {
                "exact_little_0f70b560": 0,
                "reverse_60b5700f": 0,
                "masked_any_operands_every_byte": 0,
            }
            and smoke["returncode"] == 0
        ) else "failed",
        "scope_closure": closure,
        "xw_matrix": xw_matrix,
        "csr": csr_summary,
        "iqmath": iq_summary,
        "rawscan": smoke,
    }
    dump(out / "control-summary.json", summary)
    print(json.dumps({
        "status": summary["status"], "evt_archives": closure["evt"]["physical_archives"],
        "csr_expected": csr_summary["expected_control_word_occurrences"],
        "iq_current": len(iq_rows), "xw_legacy": xw_matrix["legacy_without_linux_gcc15"],
    }, sort_keys=True))
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
