#!/usr/bin/env python3
"""Freeze independently re-extracted positive-member evidence.

Extraction is keyed by physical archive path and logical ar order.  The WCH
objdump output is only a presentation cross-check; semantic claims remain
anchored to raw member hashes/bytes and the independent scanner ledgers.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import pathlib
import re
import subprocess
import sys
from collections import Counter


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_primary(run: pathlib.Path):
    spec = importlib.util.spec_from_file_location("r2_primary_extract", run / "r2_primary.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load primary extractor")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def normalized_output(raw: str, repo: pathlib.Path, run: pathlib.Path) -> str:
    text = raw.replace(str(repo) + "/", "<REPO>/")
    text = text.replace(run.relative_to(repo).as_posix(), "<RUN_ROOT>")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def run_tool(tool: pathlib.Path, args: list[str], repo: pathlib.Path, run: pathlib.Path) -> str:
    proc = subprocess.run(
        [str(tool), *args], cwd=repo, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"tool failed rc={proc.returncode}: {tool.name} {' '.join(args)}\n{proc.stdout}")
    return normalized_output(proc.stdout, repo, run)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", required=True)
    args = parser.parse_args()
    repo = pathlib.Path.cwd().resolve()
    run = (repo / args.run_root).resolve()
    out = run / "controls" / "positive-r2"
    obj_dir = out / "objects"
    dis_dir = out / "disassembly"
    obj_dir.mkdir(parents=True, exist_ok=True)
    dis_dir.mkdir(parents=True, exist_ok=True)

    primary = load_primary(run)
    selected: list[dict[str, object]] = []
    with (run / "primary" / "occurrences.jsonl").open("r", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            path = str(row["physical_path"])
            name = str(row["member_name"])
            if name == "eth_api.o" and "/ETH/NetLib/libwchnet" in path:
                row["evidence_family"] = "wchnet"
                selected.append(row)
            elif name == "IocHub.o" and path.endswith("/libwchiochub.a"):
                row["evidence_family"] = "iochub"
                selected.append(row)

    selected.sort(key=lambda row: (
        str(row["physical_path"]).encode("utf-8"), int(row["logical_order"]),
    ))
    extracted: dict[str, pathlib.Path] = {}
    for row in selected:
        archive = repo / str(row["physical_path"])
        parsed = primary.parse_ar_primary(archive, archive.read_bytes())
        if parsed.errors:
            raise RuntimeError(f"archive parse failed {archive}: {parsed.errors}")
        member = next(
            (item for item in parsed.members if not item.metadata and item.logical_order == int(row["logical_order"])),
            None,
        )
        if member is None or member.payload is None:
            raise RuntimeError(f"member order missing: {archive}:{row['logical_order']}")
        if member.name != row["member_name"] or member.same_name_ordinal != int(row["same_name_ordinal"]):
            raise RuntimeError(f"member identity mismatch: {archive}:{row['logical_order']}")
        digest = sha256(member.payload)
        if digest != row["member_sha256"]:
            raise RuntimeError(f"member hash mismatch: {archive}:{row['logical_order']}")
        target = obj_dir / f"{digest}.o"
        if not target.exists():
            target.write_bytes(member.payload)
        elif sha256(target.read_bytes()) != digest:
            raise RuntimeError(f"existing extracted object mismatch: {target}")
        extracted[digest] = target

    tool_root = repo / "MRS_Toolchain_MAC_V240/Toolchain/RISC-V Embedded GCC12/bin"
    objdump = tool_root / "riscv-wch-elf-objdump"
    nm = tool_root / "riscv-wch-elf-nm"
    tool_rows = []
    for tool in (objdump, nm):
        tool_rows.append({"path": tool.relative_to(repo).as_posix(), "sha256": sha256(tool.read_bytes())})

    variant_rows: list[dict[str, object]] = []
    for digest, target in sorted(extracted.items()):
        occurrence_rows = [row for row in selected if row["member_sha256"] == digest]
        family = str(occurrence_rows[0]["evidence_family"])
        functions = (
            ["GetChipID", "getTxBuffAddr"] if family == "wchnet"
            else ["IoCHub_CliConnAutoReg", "WCHIOCHUB_Init", "WCHIOCHUB_Start", "WCHIOCHUB_GetLocalID"]
        )
        rel_target = target.relative_to(repo).as_posix()
        nm_text = run_tool(nm, ["-a", "-n", rel_target], repo, run)
        (dis_dir / f"{digest}-symbols.txt").write_text(nm_text, encoding="utf-8", newline="\n")
        function_presence: dict[str, bool] = {}
        disassembly_hashes: dict[str, str] = {}
        for function in functions:
            present = re.search(rf"(?:^|\s){re.escape(function)}$", nm_text, re.M) is not None
            function_presence[function] = present
            if not present:
                continue
            text = run_tool(objdump, ["-drw", f"--disassemble={function}", rel_target], repo, run)
            path = dis_dir / f"{digest}-{function}.txt"
            path.write_text(text, encoding="utf-8", newline="\n")
            disassembly_hashes[function] = sha256(path.read_bytes())

        raw = target.read_bytes()
        variant = {
            "scan_unit_sha256": digest,
            "family": family,
            "occurrence_count": len(occurrence_rows),
            "physical_paths": sorted({str(row["physical_path"]) for row in occurrence_rows}, key=lambda s: s.encode()),
            "function_presence": function_presence,
            "raw_markers": {
                "lui_1ffff_word_le": raw.count(bytes.fromhex("b7f7ff1f")),
                "lhu_706_word_le": raw.count(bytes.fromhex("03d56770")),
                "andi_f0_word_le": raw.count(bytes.fromhex("1375050f")),
                "lui_1ffff_iochub_word_le": raw.count(bytes.fromhex("37f7ff1f")),
                "addi_7e0_word_le": raw.count(bytes.fromhex("1307077e")),
            },
            "disassembly_sha256": disassembly_hashes,
        }
        variant_rows.append(variant)

    soft = [row for row in variant_rows if row["family"] == "wchnet" and row["function_presence"].get("GetChipID")]
    floating = [row for row in variant_rows if row["family"] == "wchnet" and not row["function_presence"].get("GetChipID")]
    io = [row for row in variant_rows if row["family"] == "iochub"]
    if sum(int(row["occurrence_count"]) for row in soft) != 8:
        raise RuntimeError("expected eight soft WCHNET eth_api occurrences")
    if sum(int(row["occurrence_count"]) for row in floating) != 2:
        raise RuntimeError("expected two float WCHNET eth_api occurrences")
    if sum(int(row["occurrence_count"]) for row in io) != 3:
        raise RuntimeError("expected three IoCHub IocHub occurrences")
    if not all(row["raw_markers"]["lhu_706_word_le"] == 1 for row in soft):
        raise RuntimeError("soft WCHNET GetChipID raw marker control failed")
    if not all(row["raw_markers"]["lhu_706_word_le"] == 0 for row in floating):
        raise RuntimeError("float WCHNET source-absence control failed")
    if not all(row["raw_markers"]["addi_7e0_word_le"] >= 1 for row in io):
        raise RuntimeError("IoCHub 0x1ffff7e0 raw marker control failed")

    occurrence_path = out / "positive-occurrences.tsv"
    with occurrence_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow([
            "schema_version", "evidence_family", "physical_path", "archive_sha256", "logical_order",
            "member_name", "same_name_ordinal", "member_sha256", "member_size",
        ])
        for row in selected:
            writer.writerow([
                "2", row["evidence_family"], row["physical_path"], row["archive_sha256"], row["logical_order"],
                row["member_name"], row["same_name_ordinal"], row["member_sha256"], row["member_size"],
            ])

    semantic_chain = {
        "schema_version": "2",
        "wchnet_soft": {
            "source": "GetChipID performs unsigned halfword load from 0x1ffff706 and masks with 0x00f0",
            "predicate": "masked_field == 0x80 || masked_field == 0x30",
            "special_path": "after failed descriptor status, clear owner bit31 when uint32(LocalTime-start)>99 or counter>0x8000",
            "default_path": "poll until descriptor status is nonnegative; clear timer anchor on success",
            "ordering": "counter initializes to zero and increments after each failed status test",
            "classification": "WORKAROUND-CANDIDATE; silicon defect cause not established",
        },
        "wchnet_float": {
            "source": "no GetChipID symbol and no 0x1ffff706 raw load marker",
            "behavior": "descriptor-only getTxBuffAddr specialization",
            "classification": "STATIC-VARIANT-SPECIALIZATION; no runtime ID-SELECT",
        },
        "iochub": {
            "source": "IoCHub_CliConnAutoReg reads 16 bytes at 0x1ffff7e0 when uint8(chipType-1)<=4",
            "flow": "bytes feed IoCHub_EncInit/Update/Final and registration-frame identity material; GetLocalID exposes derived eight-byte local ID",
            "caller_fields": "WCHIOCHUB_Init stores chipType; WCHIOCHUB_Start accepts caller device ID/secret",
            "classification": "ID-READ/ID-FLOW in registration/auth material; not an ID-SELECT workaround",
        },
        "limits": [
            "objdump is a presentation cross-check and does not make the two parsers non-independent",
            "remote server interpretation and runtime hardware behavior are opaque",
            "WCHNET workaround purpose remains a candidate absent a vendor defect statement or hardware experiment",
        ],
    }
    chain_path = out / "semantic-chain.json"
    chain_path.write_text(json.dumps(semantic_chain, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8", newline="\n")

    summary = {
        "schema_version": "2", "status": "pass", "variants": variant_rows,
        "occurrence_counts": dict(Counter(str(row["evidence_family"]) for row in selected)),
        "soft_wchnet_occurrences": sum(int(row["occurrence_count"]) for row in soft),
        "float_wchnet_occurrences": sum(int(row["occurrence_count"]) for row in floating),
        "iochub_occurrences": sum(int(row["occurrence_count"]) for row in io),
        "tool_files": tool_rows,
        "files": {
            "positive_occurrences_sha256": sha256(occurrence_path.read_bytes()),
            "semantic_chain_sha256": sha256(chain_path.read_bytes()),
        },
    }
    summary_path = out / "positive-summary.json"
    summary_path.write_text(json.dumps(summary, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({
        "status": "pass", "selected_occurrences": len(selected), "unique_objects": len(extracted),
        "soft": summary["soft_wchnet_occurrences"], "float": summary["float_wchnet_occurrences"],
        "iochub": summary["iochub_occurrences"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
