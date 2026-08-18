#!/usr/bin/env python3
"""Fresh, exhaustive WCH-X producer-tool fixture for the second-round audit.

The accepted source corpus is generated from operand constraints, assembled by
every locally delivered vendor producer, and checked against masks inferred
from the emitted halfwords.  Rejected boundary cases are run one at a time so
one diagnostic cannot hide acceptance of another illegal operand.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import struct
import subprocess
from collections import Counter


FORMS = (
    # mnemonic, match, mask, is_sp, immediate values
    ("c.lbu",   0x2000, 0xE003, False, tuple(range(0, 32))),
    ("c.lhu",   0x2002, 0xE003, False, tuple(range(0, 64, 2))),
    ("c.sb",    0xA000, 0xE003, False, tuple(range(0, 32))),
    ("c.sh",    0xA002, 0xE003, False, tuple(range(0, 64, 2))),
    ("c.lbusp", 0x8000, 0xF863, True,  tuple(range(0, 16))),
    ("c.lhusp", 0x8020, 0xF863, True,  tuple(range(0, 32, 2))),
    ("c.sbsp",  0x8040, 0xF863, True,  tuple(range(0, 16))),
    ("c.shsp",  0x8060, 0xF863, True,  tuple(range(0, 32, 2))),
)

TOOLS = (
    ("gcc8-mrs24", "MRS_Toolchain_MAC_V240/Toolchain/RISC-V Embedded GCC/bin/riscv-none-embed"),
    ("gcc8-mrs25", "tmp/mrs-2.5/WCH/Toolchain/RISC-V Embedded GCC/bin/riscv-none-embed"),
    ("gcc12-mrs24", "MRS_Toolchain_MAC_V240/Toolchain/RISC-V Embedded GCC12/bin/riscv-wch-elf"),
    ("gcc12-mrs25", "tmp/mrs-2.5/WCH/Toolchain/RISC-V Embedded GCC12/bin/riscv-wch-elf"),
    ("gcc15-macos", "MRS_Toolchain_MAC_V240/Toolchain/RISC-V Embedded GCC15/bin/riscv32-wch-elf"),
    ("gcc15-linux", "MRS_Toolchain_Linux_X64_V250/Toolchain/RISC-V Embedded GCC15/bin/riscv32-wch-elf"),
)

PROFILES = (
    "rv32ecxw", "rv32imacxw", "rv32imafcxw",
    "rv32ec_xw", "rv32imac_xw", "rv32imafc_xw",
    "rv32imac_xw1p0", "rv32imac_xw2p0", "rv32imac_xw2p2", "rv32imac_xw3p0",
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def clean(value: str, repo: pathlib.Path, run: pathlib.Path) -> str:
    return value.replace(str(run), "<RUN_ROOT>").replace(str(repo), "<REPO_ROOT>")


def safe_tag(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def corpus() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for mnemonic, match, mask, is_sp, immediates in FORMS:
        for data_reg in range(8, 16):
            bases = (2,) if is_sp else tuple(range(8, 16))
            for base_reg in bases:
                for immediate in immediates:
                    base = "sp" if is_sp else f"x{base_reg}"
                    rows.append({
                        "index": len(rows), "mnemonic": mnemonic,
                        "data_reg": data_reg, "base_reg": base_reg,
                        "immediate": immediate, "match": match, "mask": mask,
                        "source": f"{mnemonic} x{data_reg}, {immediate}({base})",
                    })
    return rows


def invalid_cases() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for mnemonic, _match, _mask, is_sp, immediates in FORMS:
        base = "sp" if is_sp else "x8"
        rows.extend((
            {"form": mnemonic, "reason": "data-register-low", "source": f"{mnemonic} x7, 0({base})"},
            {"form": mnemonic, "reason": "data-register-high", "source": f"{mnemonic} x16, 0({base})"},
            {"form": mnemonic, "reason": "immediate-low", "source": f"{mnemonic} x8, -1({base})"},
            {"form": mnemonic, "reason": "immediate-high", "source": f"{mnemonic} x8, {max(immediates) + (2 if mnemonic in ('c.lhu', 'c.lhusp', 'c.sh', 'c.shsp') else 1)}({base})"},
        ))
        if mnemonic in ("c.lhu", "c.lhusp", "c.sh", "c.shsp"):
            rows.append({"form": mnemonic, "reason": "immediate-odd", "source": f"{mnemonic} x8, 1({base})"})
        if not is_sp:
            rows.extend((
                {"form": mnemonic, "reason": "base-register-low", "source": f"{mnemonic} x8, 0(x7)"},
                {"form": mnemonic, "reason": "base-register-high", "source": f"{mnemonic} x8, 0(x16)"},
            ))
    return rows


def run_process(argv: list[str], *, input_text: str | None = None, repo: pathlib.Path, run: pathlib.Path) -> dict[str, object]:
    try:
        p = subprocess.run(argv, input=input_text, text=True, capture_output=True)
        return {
            "returncode": p.returncode,
            "stdout": clean(p.stdout, repo, run),
            "stderr": clean(p.stderr, repo, run),
        }
    except OSError as exc:
        return {"returncode": "not-executable", "stdout": "", "stderr": clean(repr(exc), repo, run)}


def assemble(
    prefix: pathlib.Path, profile: str, source: str, tag: str,
    out: pathlib.Path, repo: pathlib.Path, run: pathlib.Path,
) -> dict[str, object]:
    src = out / f"{tag}.S"
    obj = out / f"{tag}.o"
    raw = out / f"{tag}.bin"
    src.write_text(source, encoding="ascii", newline="\n")
    abi = "ilp32e" if profile.startswith("rv32e") else "ilp32"
    as_path = pathlib.Path(str(prefix) + "-as")
    result = run_process(
        [str(as_path), f"-march={profile}", f"-mabi={abi}", "-o", str(obj), str(src)],
        repo=repo, run=run,
    )
    if result["returncode"] == 0:
        objcopy = pathlib.Path(str(prefix) + "-objcopy")
        copied = run_process(
            [str(objcopy), "-O", "binary", "--only-section=.text", str(obj), str(raw)],
            repo=repo, run=run,
        )
        result["objcopy"] = copied
        if copied["returncode"] == 0:
            data = raw.read_bytes()
            result["raw_size"] = len(data)
            result["raw_sha256"] = sha(data)
    return result


def probe_stdin(prefix: pathlib.Path, profile: str, statement: str, repo: pathlib.Path, run: pathlib.Path) -> dict[str, object]:
    abi = "ilp32e" if profile.startswith("rv32e") else "ilp32"
    as_path = pathlib.Path(str(prefix) + "-as")
    source = ".text\n.option rvc\n" + statement + "\n"
    result = run_process(
        [str(as_path), f"-march={profile}", f"-mabi={abi}", "-o", "/dev/null", "-"],
        input_text=source, repo=repo, run=run,
    )
    result["statement"] = statement
    return result


def classify_word(word: int) -> list[str]:
    return [mnemonic for mnemonic, match, mask, _sp, _imms in FORMS if word & mask == match]


def tool_record(label: str, prefix_rel: str, repo: pathlib.Path, run: pathlib.Path) -> dict[str, object]:
    prefix = repo / prefix_rel
    files: dict[str, object] = {}
    for suffix in ("as", "objcopy", "objdump"):
        path = pathlib.Path(str(prefix) + "-" + suffix)
        files[suffix] = {
            "path": str(path.relative_to(repo)),
            "present": path.is_file(),
            "size": path.stat().st_size if path.is_file() else "not-applicable",
            "sha256": sha(path.read_bytes()) if path.is_file() else "not-applicable",
        }
    version = run_process([str(prefix) + "-as", "--version"], repo=repo, run=run)
    return {"label": label, "prefix": prefix_rel, "files": files, "assembler_version": version}


def set_hash(values: list[int]) -> str:
    payload = b"".join(struct.pack("<H", value) for value in sorted(values))
    return sha(payload)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", required=True)
    args = parser.parse_args()
    repo = pathlib.Path.cwd().resolve()
    run = (repo / args.run_root).resolve()
    out = run / "controls" / "xw-fixture-r2"
    out.mkdir(parents=True, exist_ok=True)

    rows = corpus()
    invalid = invalid_cases()
    if len(rows) != 8704:
        raise SystemExit(f"bad corpus cardinality: {len(rows)}")

    theoretical: dict[str, list[int]] = {}
    overlap_words: list[int] = []
    for word in range(65536):
        matches = classify_word(word)
        if len(matches) > 1:
            overlap_words.append(word)
        for name in matches:
            theoretical.setdefault(name, []).append(word)
    theoretical_union = sorted({x for values in theoretical.values() for x in values})
    if len(theoretical_union) != 8704 or overlap_words:
        raise SystemExit("mask family union/overlap invariant failed")

    source = ".text\n.option rvc\n.globl _start\n_start:\n" + "\n".join(str(row["source"]) for row in rows) + "\n"
    tools: dict[str, object] = {}
    canonical_data: bytes | None = None
    canonical_from: str | None = None
    accepted_stream_hashes: set[str] = set()

    for label, prefix_rel in TOOLS:
        prefix = repo / prefix_rel
        record = tool_record(label, prefix_rel, repo, run)
        profile_results: dict[str, object] = {}
        for profile in PROFILES:
            probe = probe_stdin(prefix, profile, "c.lbu x8, 0(x8)", repo, run)
            entry: dict[str, object] = {"probe": probe}
            if probe["returncode"] == 0:
                tag = safe_tag(f"{label}-{profile}-corpus")
                full = assemble(prefix, profile, source, tag, out, repo, run)
                entry["full_corpus"] = full
                raw = out / f"{tag}.bin"
                if full["returncode"] == 0 and full.get("objcopy", {}).get("returncode") == 0:  # type: ignore[union-attr]
                    data = raw.read_bytes()
                    words = list(struct.unpack(f"<{len(data) // 2}H", data)) if len(data) % 2 == 0 else []
                    family_errors = []
                    for row, word in zip(rows, words):
                        if classify_word(word) != [row["mnemonic"]]:
                            family_errors.append([row["index"], row["source"], f"0x{word:04x}", classify_word(word)])
                    entry["verification"] = {
                        "word_count": len(words),
                        "distinct_words": len(set(words)),
                        "set_sha256": set_hash(words),
                        "family_error_count": len(family_errors),
                        "family_errors": family_errors[:20],
                    }
                    if len(words) == len(rows) and len(set(words)) == 8704 and not family_errors:
                        accepted_stream_hashes.add(sha(data))
                        if canonical_data is None:
                            canonical_data = data
                            canonical_from = f"{label}:{profile}"
                boundary_results = []
                for case in invalid:
                    result = probe_stdin(prefix, profile, case["source"], repo, run)
                    boundary_results.append({**case, **result})
                entry["invalid_boundaries"] = {
                    "case_count": len(boundary_results),
                    "unexpected_accept_count": sum(1 for x in boundary_results if x["returncode"] == 0),
                    "cases": boundary_results,
                }
            profile_results[profile] = entry

        # Keep the ISA-string acceptance observation separate from source-form
        # rejection in the D/C/XW overlapping slot.
        overlap_profile = "rv32imafdc_xw2p2"
        record["d_c_xw_overlap"] = {
            "xw_source": probe_stdin(prefix, overlap_profile, "c.lbu x8, 0(x8)", repo, run),
            "c_fld_source": probe_stdin(prefix, overlap_profile, "c.fld f8, 0(x8)", repo, run),
        }
        record["mcpy"] = probe_stdin(prefix, "rv32imac_xw2p2", "mcpy a0, a1, a2", repo, run)
        record["profiles"] = profile_results
        tools[label] = record

    if canonical_data is None:
        raise SystemExit("no producer assembled the complete corpus")
    canonical_words = list(struct.unpack(f"<{len(canonical_data) // 2}H", canonical_data))
    mapping_path = out / "xw-source-encoding-map.tsv"
    with mapping_path.open("w", encoding="utf-8", newline="") as handle:
        handle.write("schema_version\tindex\tmnemonic\tdata_reg\tbase_reg\timmediate\tsource\thalfword_hex\tmask_hex\tmatch_hex\tclassification\n")
        for row, word in zip(rows, canonical_words):
            handle.write(
                "2\t{index}\t{mnemonic}\t{data_reg}\t{base_reg}\t{immediate}\t{source}\t0x{word:04x}\t0x{mask:04x}\t0x{match:04x}\t{classification}\n".format(
                    **row, word=word, classification=classify_word(word)[0]
                )
            )

    theoretical_path = out / "xw-theoretical-encoding-set.tsv"
    with theoretical_path.open("w", encoding="utf-8", newline="") as handle:
        handle.write("schema_version\thalfword_hex\tform\n")
        for word in theoretical_union:
            handle.write(f"2\t0x{word:04x}\t{classify_word(word)[0]}\n")

    # Build an exact mcpy byte control with every executable producer that
    # accepts it.  The profile probe above cannot preserve emitted bytes.
    mcpy_emitted: dict[str, object] = {}
    for label, prefix_rel in TOOLS:
        prefix = repo / prefix_rel
        tag = safe_tag(f"{label}-mcpy")
        result = assemble(
            prefix, "rv32imac_xw2p2",
            ".text\n.globl _start\n_start:\n mcpy a0, a1, a2\n",
            tag, out, repo, run,
        )
        raw = out / f"{tag}.bin"
        if raw.is_file():
            result["raw_hex"] = raw.read_bytes().hex()
        mcpy_emitted[label] = result

    form_counts = Counter(str(row["mnemonic"]) for row in rows)
    summary = {
        "schema_version": "2",
        "status": "pass" if len(accepted_stream_hashes) == 1 else "failed",
        "corpus": {
            "case_count": len(rows),
            "form_counts": dict(sorted(form_counts.items())),
            "source_sha256": sha(source.encode("ascii")),
            "canonical_from": canonical_from,
            "canonical_stream_sha256": sha(canonical_data),
            "canonical_set_sha256": set_hash(canonical_words),
            "accepted_stream_hashes": sorted(accepted_stream_hashes),
            "mapping_sha256": sha(mapping_path.read_bytes()),
        },
        "theoretical_masks": {
            "union_count": len(theoretical_union),
            "union_set_sha256": set_hash(theoretical_union),
            "overlap_count": len(overlap_words),
            "per_form_count": {name: len(theoretical[name]) for name, *_ in FORMS},
            "set_file_sha256": sha(theoretical_path.read_bytes()),
        },
        "invalid_case_count_per_profile": len(invalid),
        "mcpy_emitted": mcpy_emitted,
        "tools": tools,
    }
    summary_path = out / "xw-fixture-summary.json"
    summary_path.write_text(json.dumps(summary, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({
        "status": summary["status"],
        "case_count": len(rows),
        "mask_union": len(theoretical_union),
        "accepted_stream_hashes": sorted(accepted_stream_hashes),
        "tools": len(tools),
    }, sort_keys=True))
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
