#!/usr/bin/env python3
"""Independently audit and seal one XW + LTO four-lane evidence tree.

This module deliberately imports no runner code.  It duplicates the closed
contract, rehashes and byte-compares the raw evidence, and writes a seal only
when every fail-closed check succeeds.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import platform as host_platform
import stat
import sys
from typing import Any, Iterable


SUITE = Path(__file__).resolve().parent
REPO = SUITE.parents[1]
REPO_TMP = REPO / "tmp"
CONTRACT_PATH = SUITE / "contract.json"
LANES = ("official-1", "official-2", "ours-1", "ours-2")
PAIRS = (
    ("official-self", "self-consistency", "official-1", "official-2"),
    ("ours-self", "self-consistency", "ours-1", "ours-2"),
    ("parity-run-1", "official-vs-ours", "official-1", "ours-1"),
    ("parity-run-2", "official-vs-ours", "official-2", "ours-2"),
)
ASM_CASES = (
    (
        "xw-eight",
        "fixtures/xw-eight.S",
        "rv32imac_xw",
        "xw_eight",
        "xw-eight-tu",
        "xw-eight-link",
        0,
        "8821aa21a8b1caa188822883c88368848280",
    ),
    (
        "zcb-only",
        "fixtures/same-mnemonic.S",
        "rv32imac_zcb",
        "same_mnemonic",
        "zcb-only-tu",
        "zcb-only-link",
        0,
        "88818280",
    ),
    (
        "zcb-xw-priority",
        "fixtures/same-mnemonic.S",
        "rv32imac_zcb_xw",
        "same_mnemonic",
        "zcb-xw-priority-tu",
        "zcb-xw-priority-link",
        0,
        "88218280",
    ),
    (
        "dc-xw-cfld-negative",
        "fixtures/dc-xw-cfld.S",
        "rv32imafdc_xw",
        "dc_xw_cfld",
        "dc-xw-cfld-negative-tu",
        None,
        1,
        None,
    ),
    (
        "fc-xw-coexist",
        "fixtures/fc-xw-coexist.S",
        "rv32imafc_xw",
        "fc_xw_coexist",
        "fc-xw-coexist-tu",
        "fc-xw-coexist-link",
        0,
        "886188218280",
    ),
)
LTO_TUS = (
    ("lto-attrs", "fixtures/lto-attrs.c", "lto-xw-attrs-tu"),
    ("lto-entry", "fixtures/lto-entry.c", "lto-xw-entry-tu"),
)
LTRANS_TOKENS = (
    "lto_xw_global:",
    "lto_xw_added:",
    "lto_xw_versioned:",
    "xw2p0",
    "xw9p9",
    "c.lbu a0, 0(a1)",
    "c.lhu a0, 2(a1)",
    "c.sb a0, 3(a1)",
    "c.sh a0, 4(a1)",
    "c.lbusp a0, 5(sp)",
    "c.lhusp a0, 6(sp)",
    "c.sbsp a0, 7(sp)",
    "c.shsp a0, 8(sp)",
)
FUNCTION_ARCH_TOKENS = {
    "lto_xw_global": "zca_xw",
    "lto_xw_added": "xw2p0",
    "lto_xw_versioned": "xw9p9",
}
TOOL_INPUTS = (
    "bin/riscv32-wch-elf-gcc",
    "bin/riscv32-wch-elf-as",
    "bin/riscv32-wch-elf-objcopy",
    "bin/riscv32-wch-elf-lto-dump",
    "bin/riscv32-wch-elf-ld",
    "riscv32-wch-elf/bin/as",
    "riscv32-wch-elf/bin/ld",
    "libexec/gcc/riscv32-wch-elf/15.2.0/cc1",
    "libexec/gcc/riscv32-wch-elf/15.2.0/lto1",
    "libexec/gcc/riscv32-wch-elf/15.2.0/lto-wrapper",
    "libexec/gcc/riscv32-wch-elf/15.2.0/liblto_plugin.so",
    "libexec/gcc/riscv32-wch-elf/15.2.0/collect2",
)
OPTIONAL_TOOL_INPUTS = (
    "bin/libzstd.1.dylib",
    "riscv32-wch-elf/bin/libzstd.1.dylib",
)
SUITE_FILES = {
    "README.md",
    "audit_and_seal.py",
    "contract.json",
    "run.py",
    "fixtures/dc-xw-cfld.S",
    "fixtures/fc-xw-coexist.S",
    "fixtures/lto-attrs.c",
    "fixtures/lto-entry.c",
    "fixtures/same-mnemonic.S",
    "fixtures/xw-eight.S",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def files_equal(left: Path, right: Path) -> bool:
    if left.stat().st_size != right.stat().st_size:
        return False
    with left.open("rb") as left_stream, right.open("rb") as right_stream:
        while True:
            left_block = left_stream.read(1024 * 1024)
            right_block = right_stream.read(1024 * 1024)
            if left_block != right_block:
                return False
            if not left_block:
                return True


def freeze_evidence_tree(root: Path) -> None:
    """Remove every write bit, with the evidence root frozen last."""
    paths = sorted(root.rglob("*"), key=lambda path: len(path.parts), reverse=True)
    for path in paths:
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode):
            raise RuntimeError(f"refusing to freeze evidence symlink: {path}")
        if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
            raise RuntimeError(f"refusing to freeze special evidence file: {path}")
        path.chmod(stat.S_IMODE(mode) & ~0o222)
    root.chmod(stat.S_IMODE(root.lstat().st_mode) & ~0o222)


def writable_entry_count(root: Path) -> int:
    return sum(
        1
        for path in (root, *root.rglob("*"))
        if stat.S_IMODE(path.lstat().st_mode) & 0o222
    )


def finalize_readonly_seal(root: Path, seal_path: Path, final_value: Any) -> None:
    """Publish SEALED only after the payload is frozen and verified."""
    placeholder = {
        "schema": "openwch-xw-lto-seal-pending-v1",
        "state": "SEALING_NOT_VALID",
    }
    write_json_atomic(seal_path, placeholder)
    freeze_evidence_tree(root)
    if writable_entry_count(root) != 0:
        raise RuntimeError("evidence payload still has writable entries before seal publish")
    final_data = (json.dumps(final_value, indent=2, sort_keys=True) + "\n").encode("utf-8")
    seal_path.chmod(0o644)
    descriptor = os.open(seal_path, os.O_WRONLY | os.O_TRUNC)
    try:
        # Permission is checked at open; the live descriptor remains usable
        # after the inode returns to read-only mode.
        seal_path.chmod(0o444)
        offset = 0
        while offset < len(final_data):
            offset += os.write(descriptor, final_data[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    if writable_entry_count(root) != 0:
        raise RuntimeError("published evidence tree has writable entries")


def write_bytes_atomic(path: Path, data: bytes) -> None:
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def write_json_atomic(path: Path, value: Any) -> None:
    write_bytes_atomic(
        path,
        (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )


def tsv_bytes(header: Iterable[str], rows: Iterable[Iterable[Any]]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, delimiter="\t", lineterminator="\n")
    writer.writerow(list(header))
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def suite_manifest_bytes() -> bytes:
    rows: list[tuple[str, int, str]] = []
    discovered: set[str] = set()
    for path in sorted(SUITE.rglob("*"), key=lambda p: p.relative_to(SUITE).as_posix()):
        relative = path.relative_to(SUITE).as_posix()
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            raise RuntimeError(f"bytecode/cache file is forbidden in contract tree: {relative}")
        if path.is_symlink():
            raise RuntimeError(f"suite contract contains symlink {relative}")
        if path.is_file():
            discovered.add(relative)
            rows.append((relative, path.stat().st_size, sha256_file(path)))
    if discovered != SUITE_FILES:
        raise RuntimeError(
            f"suite file denominator changed: missing={sorted(SUITE_FILES-discovered)} "
            f"extra={sorted(discovered-SUITE_FILES)}"
        )
    return tsv_bytes(("path", "size", "sha256"), rows)


def tool_manifest_bytes(roots: dict[str, Path]) -> bytes:
    rows: list[tuple[str, str, str, str, int, str]] = []
    for category in ("official", "ours"):
        root = roots[category]
        for relative in (*TOOL_INPUTS, *OPTIONAL_TOOL_INPUTS):
            path = root / relative
            if os.path.lexists(path):
                mode = path.lstat().st_mode
                if path.is_symlink() or not stat.S_ISREG(mode):
                    raise RuntimeError(f"unsafe tool manifest input: {category}:{relative}")
                if not is_within(path.resolve(strict=True), root):
                    raise RuntimeError(f"tool manifest input escapes root: {category}:{relative}")
                state_value, size, digest = (
                    "PRESENT",
                    path.stat().st_size,
                    sha256_file(path),
                )
            else:
                state_value, size, digest = "MISSING", 0, "-"
            link_target = "-"
            rows.append(
                (category, str(root), relative, state_value, size, digest + ":" + link_target)
            )
    return tsv_bytes(
        ("category", "resolved_root", "path", "state", "size", "sha256_and_link_target"),
        rows,
    )


class Auditor:
    def __init__(self, evidence: Path, allow_smoke: bool) -> None:
        self.evidence = evidence
        self.allow_smoke = allow_smoke
        self.failures: list[str] = []
        self.check_count = 0
        self.context: dict[str, Any] = {}
        self.mode = "unknown"
        self.audit_name = "AUDIT.json"
        self.seal_name = "SEAL.json"
        self.manifest_name = "audit-manifest.tsv"
        self.declared_files: set[str] = set()
        self.command_file_map: dict[tuple[str, str], Path] = {}
        self.artifact_file_map: dict[tuple[str, str], Path | None] = {}

    def require(self, condition: bool, message: str) -> None:
        self.check_count += 1
        if not condition:
            self.failures.append(message)

    def json_file(self, name: str) -> dict[str, Any]:
        path = self.evidence / name
        self.require(path.is_file() and not path.is_symlink(), f"missing regular {name}")
        if not path.is_file() or path.is_symlink():
            return {}
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except Exception as error:
            self.failures.append(f"invalid JSON {name}: {error}")
            return {}
        self.declared_files.add(name)
        return value

    def tsv_file(self, name: str, header: tuple[str, ...]) -> list[dict[str, str]]:
        path = self.evidence / name
        self.require(path.is_file() and not path.is_symlink(), f"missing regular {name}")
        if not path.is_file() or path.is_symlink():
            return []
        data = path.read_bytes()
        first = data.splitlines()[0].decode("utf-8") if data else ""
        self.require(first.split("\t") == list(header), f"{name} header changed")
        try:
            rows = list(csv.DictReader(io.StringIO(data.decode("utf-8")), delimiter="\t"))
        except Exception as error:
            self.failures.append(f"invalid TSV {name}: {error}")
            return []
        self.declared_files.add(name)
        return rows

    def evidence_file(self, relative: str, label: str) -> Path | None:
        candidate = Path(relative)
        if candidate.is_absolute() or ".." in candidate.parts or relative in ("", "-"):
            self.failures.append(f"{label}: unsafe evidence path {relative!r}")
            return None
        path = self.evidence / candidate
        try:
            resolved = path.resolve(strict=True)
        except FileNotFoundError:
            self.failures.append(f"{label}: missing evidence file {relative}")
            return None
        if not is_within(resolved, self.evidence.resolve(strict=True)):
            self.failures.append(f"{label}: evidence path escapes root: {relative}")
            return None
        current = self.evidence
        for part in candidate.parts:
            current = current / part
            if current.is_symlink():
                self.failures.append(f"{label}: symlink in evidence path {relative}")
                return None
        if not path.is_file():
            self.failures.append(f"{label}: not a regular file: {relative}")
            return None
        self.declared_files.add(candidate.as_posix())
        return path

    def validate_contract(self) -> dict[str, Any]:
        try:
            contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        except Exception as error:
            self.failures.append(f"cannot load live contract: {error}")
            return {}
        self.require(contract.get("schema") == "openwch-xw-lto-contract-v1", "schema changed")
        self.require(contract.get("suite_version") == 1, "suite version changed")
        self.require(contract.get("target") == "riscv32-wch-elf", "target changed")
        self.require(contract.get("abi") == "ilp32", "ABI changed")
        self.require(contract.get("gcc_version") == "15.2.0", "GCC version changed")
        self.require(contract.get("source_date_epoch") == 1767225600, "epoch changed")
        self.require(tuple(contract.get("lanes", [])) == LANES, "lane order changed")
        observed_pairs = tuple(
            (row.get("id"), row.get("phase"), row.get("left"), row.get("right"))
            for row in contract.get("comparison_pairs", [])
        )
        self.require(observed_pairs == PAIRS, "comparison pair/phase contract changed")

        observed_asm = tuple(
            (
                row.get("id"),
                row.get("fixture"),
                row.get("march"),
                row.get("entry"),
                row.get("compile_seed"),
                row.get("link_seed"),
                row.get("expected_compile_rc"),
                row.get("expected_text_hex"),
            )
            for row in contract.get("asm_cases", [])
        )
        self.require(observed_asm == ASM_CASES, "assembly case contract changed")
        lto = contract.get("lto_case", {})
        self.require(lto.get("id") == "lto-xw-stream", "LTO case id changed")
        self.require(lto.get("compile_march") == "rv32imac_xw", "LTO compile march changed")
        self.require(
            lto.get("positive_link_march") == "rv32imac_xw", "positive LTO march changed"
        )
        self.require(
            lto.get("negative_link_march") == "rv32imac", "negative LTO march changed"
        )
        self.require(lto.get("entry") == "_start", "LTO entry changed")
        self.require(lto.get("flto_jobs") == 1, "LTO job count changed")
        observed_tus = tuple(
            (row.get("stem"), row.get("fixture"), row.get("seed"))
            for row in lto.get("translation_units", [])
        )
        self.require(observed_tus == LTO_TUS, "LTO TU contract changed")
        self.require(
            lto.get("positive_link_seed") == "lto-xw-positive-link",
            "positive LTO link seed changed",
        )
        self.require(
            lto.get("negative_link_seed") == "lto-xw-base-negative-link",
            "negative LTO link seed changed",
        )
        self.require(lto.get("expected_compile_rc") == 0, "LTO compile rc changed")
        self.require(lto.get("expected_positive_link_rc") == 0, "positive link rc changed")
        self.require(lto.get("expected_negative_link_rc") == 1, "negative link rc changed")
        self.require(
            tuple(lto.get("required_ltrans_tokens", [])) == LTRANS_TOKENS,
            "ltrans token contract changed",
        )
        self.require(
            lto.get("required_function_arch_tokens") == FUNCTION_ARCH_TOKENS,
            "function-bound ltrans arch contract changed",
        )
        seeds = [row[4] for row in ASM_CASES]
        seeds.extend(row[5] for row in ASM_CASES if row[5] is not None)
        seeds.extend(row[2] for row in LTO_TUS)
        seeds.extend(("lto-xw-positive-link", "lto-xw-base-negative-link"))
        self.require(len(seeds) == len(set(seeds)), "TU/link random seeds are not unique")
        fixture = (SUITE / "fixtures/xw-eight.S").read_text(encoding="utf-8")
        for mnemonic in ("c.lbu", "c.lhu", "c.sb", "c.sh", "c.lbusp", "c.lhusp", "c.sbsp", "c.shsp"):
            self.require(f"\t{mnemonic} " in fixture, f"xw-eight fixture lacks {mnemonic}")
        return contract

    def validate_context(self) -> tuple[dict[str, Path], str, str]:
        self.context = self.json_file("context.json")
        self.mode = str(self.context.get("mode", "unknown"))
        if self.mode == "smoke-identical-roots":
            self.audit_name = "SMOKE_AUDIT.json"
            self.seal_name = "SMOKE_SEAL.json"
            self.manifest_name = "smoke-audit-manifest.tsv"
        platform_name = str(self.context.get("platform", ""))
        self.require(
            self.context.get("schema") == "openwch-xw-lto-run-context-v1",
            "context schema changed",
        )
        self.require(platform_name in ("darwin-arm64", "linux-amd64"), "invalid platform")
        self.require(
            self.mode in ("formal", "smoke-identical-roots"), "invalid evidence mode"
        )
        self.require(
            self.context.get("source_date_epoch") == 1767225600, "context epoch changed"
        )
        self.require(self.context.get("normalization") == "NONE", "normalization was enabled")
        self.require(
            self.context.get("evidence_root_preexisted") is False,
            "runner did not record a fresh evidence root",
        )
        self.require(tuple(self.context.get("lane_order", [])) == LANES, "context lanes changed")
        self.require(
            self.context.get("repository") == str(REPO.resolve(strict=True)),
            "repository path changed",
        )
        self.require(
            self.context.get("suite") == str(SUITE), "suite absolute path changed"
        )
        self.require(
            self.context.get("evidence_root") == str(self.evidence),
            "evidence absolute path changed",
        )
        fixed_cwd = str(self.evidence / "shared-work")
        alias = str(self.evidence / "shared-work/toolchain-current")
        self.require(self.context.get("fixed_work_cwd") == fixed_cwd, "fixed cwd changed")
        self.require(
            self.context.get("fixed_toolchain_alias") == alias, "fixed alias path changed"
        )
        self.require(
            self.context.get("gcc_exec_prefix") == alias + "/lib/gcc/",
            "fixed GCC_EXEC_PREFIX changed",
        )
        self.require(
            self.context.get("subprocess_path") == "/usr/bin:/bin",
            "subprocess PATH contract changed",
        )
        self.require(
            self.context.get("environment_policy") == "CLEAN_ALLOWLIST_V1",
            "subprocess environment policy changed",
        )
        self.require(
            self.context.get("subprocess_environment_keys")
            == [
                "GCC_COLORS",
                "GCC_EXEC_PREFIX",
                "LANG",
                "LC_ALL",
                "NO_COLOR",
                "PATH",
                "SOURCE_DATE_EPOCH",
                "TERM",
                "TMPDIR",
                "TZ",
                "ZERO_AR_DATE",
            ],
            "subprocess environment allowlist changed",
        )

        system = host_platform.system()
        machine = host_platform.machine().lower()
        self.require(self.context.get("host_system") == system, "host system record changed")
        self.require(
            str(self.context.get("host_machine", "")).lower() == machine,
            "host machine record changed",
        )
        if platform_name == "darwin-arm64":
            host_ok = system == "Darwin" and machine in ("arm64", "aarch64")
        else:
            host_ok = system == "Linux" and machine in ("x86_64", "amd64")
        self.require(host_ok, f"platform/host mismatch: {platform_name} vs {system}/{machine}")

        official = Path(str(self.context.get("official_root_resolved", "")))
        ours = Path(str(self.context.get("ours_root_resolved", "")))
        requested_official = Path(str(self.context.get("official_root_requested", "")))
        requested_ours = Path(str(self.context.get("ours_root_requested", "")))
        expected_official = (REPO / "ref/gcc" / platform_name / "15.2.0").resolve(strict=True)
        self.require(official.is_absolute() and official.is_dir(), "official root invalid")
        self.require(ours.is_absolute() and ours.is_dir(), "ours root invalid")
        self.require(
            requested_official.resolve(strict=True) == expected_official,
            "official root is not this platform's canonical package",
        )
        self.require(official.resolve(strict=True) == expected_official, "official resolved root changed")
        self.require(
            requested_ours.resolve(strict=True) == ours.resolve(strict=True),
            "ours requested/resolved roots disagree",
        )
        repo_root = REPO.resolve(strict=True)
        self.require(is_within(official.resolve(strict=True), repo_root), "official root outside repo")
        self.require(is_within(ours.resolve(strict=True), repo_root), "ours root outside repo")
        for label, root in (("official", official), ("ours", ours)):
            for relative in TOOL_INPUTS:
                path = root / relative
                safe = False
                if not path.is_symlink() and path.is_file():
                    mode = path.lstat().st_mode
                    safe = stat.S_ISREG(mode) and is_within(path.resolve(strict=True), root)
                self.require(safe, f"{label} unsafe/missing tool input: {relative}")
            for relative in OPTIONAL_TOOL_INPUTS:
                path = root / relative
                if os.path.lexists(path):
                    mode = path.lstat().st_mode
                    self.require(
                        not path.is_symlink()
                        and stat.S_ISREG(mode)
                        and is_within(path.resolve(strict=True), root),
                        f"{label} unsafe optional tool input: {relative}",
                    )
        if self.mode == "formal":
            self.require(official.resolve() != ours.resolve(), "formal roots are identical")
            for relative in TOOL_INPUTS:
                left, right = official / relative, ours / relative
                if not left.is_symlink() and not right.is_symlink() and left.is_file() and right.is_file():
                    self.require(
                        not os.path.samestat(left.lstat(), right.lstat()),
                        f"formal roots share tool input inode: {relative}",
                    )
                else:
                    self.require(False, f"formal inode check unavailable: {relative}")
        else:
            self.require(self.allow_smoke, "smoke evidence requires --allow-smoke")
            self.require(official.resolve() == ours.resolve(), "smoke roots are not identical")
        return {"official": official.resolve(), "ours": ours.resolve()}, fixed_cwd, alias

    def expected_commands(self, alias: str) -> dict[tuple[str, str], tuple[list[str], int]]:
        gcc = alias + "/bin/riscv32-wch-elf-gcc"
        objcopy = alias + "/bin/riscv32-wch-elf-objcopy"
        lto_dump = alias + "/bin/riscv32-wch-elf-lto-dump"
        expected: dict[tuple[str, str], tuple[list[str], int]] = {}
        for case_id, _, march, entry, compile_seed, link_seed, compile_rc, _ in ASM_CASES:
            obj = case_id + ".o"
            expected[(case_id, "compile")] = (
                [
                    gcc,
                    f"-march={march}",
                    "-mabi=ilp32",
                    f"-frandom-seed={compile_seed}",
                    "-save-temps=obj",
                    "-c",
                    case_id + ".S",
                    "-o",
                    obj,
                ],
                compile_rc,
            )
            if compile_rc == 0:
                expected[(case_id, "link")] = (
                    [
                        gcc,
                        f"-march={march}",
                        "-mabi=ilp32",
                        f"-frandom-seed={link_seed}",
                        "-nostdlib",
                        "-nostartfiles",
                        "-nodefaultlibs",
                        f"-Wl,-e,{entry}",
                        "-Wl,--no-relax",
                        obj,
                        "-o",
                        case_id + ".elf",
                    ],
                    0,
                )
                expected[(case_id, "objcopy-bin")] = (
                    [objcopy, "-O", "binary", case_id + ".elf", case_id + ".bin"],
                    0,
                )
                expected[(case_id, "objcopy-text")] = (
                    [
                        objcopy,
                        "-j",
                        ".text",
                        "-O",
                        "binary",
                        obj,
                        case_id + ".text.bin",
                    ],
                    0,
                )

        for stem, _, seed in LTO_TUS:
            expected[("lto-xw-stream", "compile-" + stem)] = (
                [
                    gcc,
                    "-O2",
                    "-flto=1",
                    "-fno-fat-lto-objects",
                    "-save-temps=obj",
                    "-march=rv32imac_xw",
                    "-mabi=ilp32",
                    f"-frandom-seed={seed}",
                    "-c",
                    stem + ".c",
                    "-o",
                    stem + ".o",
                ],
                0,
            )
            expected[("lto-xw-stream", "own-read-" + stem)] = (
                [lto_dump, "-list", stem + ".o"],
                0,
            )
        objects = [stem + ".o" for stem, _, _ in LTO_TUS]
        expected[("lto-xw-stream", "link-base-negative")] = (
            [
                gcc,
                "-O2",
                "-flto=1",
                "-save-temps=obj",
                "-march=rv32imac",
                "-mabi=ilp32",
                "-frandom-seed=lto-xw-base-negative-link",
                "-nostdlib",
                "-nostartfiles",
                "-nodefaultlibs",
                "-Wl,-e,_start",
                "-Wl,--no-relax",
                *objects,
                "-o",
                "negative.elf",
            ],
            1,
        )
        expected[("lto-xw-stream", "link-positive")] = (
            [
                gcc,
                "-O2",
                "-flto=1",
                "-save-temps=obj",
                "-march=rv32imac_xw",
                "-mabi=ilp32",
                "-frandom-seed=lto-xw-positive-link",
                "-nostdlib",
                "-nostartfiles",
                "-nodefaultlibs",
                "-Wl,-e,_start",
                "-Wl,--no-relax",
                *objects,
                "-o",
                "final.elf",
            ],
            0,
        )
        expected[("lto-xw-stream", "objcopy-bin")] = (
            [objcopy, "-O", "binary", "final.elf", "final.bin"],
            0,
        )
        expected[("lto-xw-stream", "objcopy-text")] = (
            [objcopy, "-j", ".text", "-O", "binary", "final.elf", "final.text.bin"],
            0,
        )
        return expected

    def expected_artifacts(self) -> dict[tuple[str, str], str]:
        expected: dict[tuple[str, str], str] = {}
        for case_id, _, _, _, _, _, compile_rc, _ in ASM_CASES:
            if compile_rc == 0:
                names = (
                    case_id + ".s",
                    case_id + ".o",
                    case_id + ".elf",
                    case_id + ".bin",
                    case_id + ".text.bin",
                )
                for name in names:
                    expected[(case_id, name)] = "PRESENT"
            else:
                expected[(case_id, case_id + ".s")] = "PRESENT"
                expected[(case_id, case_id + ".o")] = "ABSENT"
        for stem, _, _ in LTO_TUS:
            for suffix in (".i", ".s", ".o"):
                expected[("lto-xw-stream", stem + suffix)] = "PRESENT"
        for prefix in ("negative.elf", "final.elf"):
            for suffix in (
                ".res",
                ".ltrans0.ltrans.s",
                ".ltrans0.o",
                ".ltrans_args",
                ".ltrans0.ltrans_args",
                ".wpa.args.0",
                ".ltrans0.ltrans.args.0",
                ".ltrans.out",
            ):
                expected[("lto-xw-stream", prefix + suffix)] = "PRESENT"
        expected[("lto-xw-stream", "negative.elf")] = "ABSENT"
        for name in ("final.elf", "final.bin", "final.text.bin"):
            expected[("lto-xw-stream", name)] = "PRESENT"
        return expected

    def validate_commands(self, fixed_cwd: str, alias: str) -> list[dict[str, str]]:
        header = (
            "lane",
            "case",
            "stage",
            "cwd",
            "argv_json",
            "expected_rc",
            "actual_rc",
            "rc_path",
            "rc_sha256",
            "stdout_path",
            "stdout_size",
            "stdout_sha256",
            "stderr_path",
            "stderr_size",
            "stderr_sha256",
        )
        rows = self.tsv_file("commands.tsv", header)
        expected = self.expected_commands(alias)
        expected_keys = {(lane, case, stage) for lane in LANES for case, stage in expected}
        observed_keys = {(r.get("lane"), r.get("case"), r.get("stage")) for r in rows}
        self.require(len(rows) == len(expected_keys) == 100, "command denominator is not 100")
        self.require(observed_keys == expected_keys, "command key universe changed")
        self.require(len(observed_keys) == len(rows), "duplicate command rows")
        for row in rows:
            lane, case, stage = row.get("lane", ""), row.get("case", ""), row.get("stage", "")
            spec = expected.get((case, stage))
            if lane not in LANES or spec is None:
                continue
            argv, expected_rc = spec
            self.require(row.get("cwd") == fixed_cwd, f"{lane}:{case}:{stage}: cwd changed")
            try:
                observed_argv = json.loads(row.get("argv_json", ""))
            except Exception:
                observed_argv = None
            self.require(observed_argv == argv, f"{lane}:{case}:{stage}: argv changed")
            self.require(row.get("expected_rc") == str(expected_rc), f"{lane}:{case}:{stage}: expected rc ledger changed")
            self.require(row.get("actual_rc") == str(expected_rc), f"{lane}:{case}:{stage}: actual rc mismatch")
            components = (
                ("rc", "rc_path", "rc_sha256", None),
                ("stdout", "stdout_path", "stdout_sha256", "stdout_size"),
                ("stderr", "stderr_path", "stderr_sha256", "stderr_size"),
            )
            for component, path_key, hash_key, size_key in components:
                canonical = f"lanes/{lane}/raw/{case}/{stage}.{component}"
                self.require(
                    row.get(path_key) == canonical,
                    f"{lane}:{case}:{stage}:{component}: raw path is not canonical",
                )
                path = self.evidence_file(
                    row.get(path_key, ""), f"{lane}:{case}:{stage}:{component}"
                )
                if path is None:
                    continue
                self.require(
                    sha256_file(path) == row.get(hash_key),
                    f"{lane}:{case}:{stage}:{component}: hash ledger mismatch",
                )
                if size_key:
                    self.require(
                        str(path.stat().st_size) == row.get(size_key),
                        f"{lane}:{case}:{stage}:{component}: size ledger mismatch",
                    )
                else:
                    self.require(
                        path.read_bytes() == f"{expected_rc}\n".encode("ascii"),
                        f"{lane}:{case}:{stage}: raw rc bytes changed",
                    )
                item = f"raw/{case}/{stage}.{component}"
                self.command_file_map[(lane, item)] = path
        return rows

    def validate_artifacts(self) -> list[dict[str, str]]:
        header = (
            "lane",
            "case",
            "artifact",
            "expected_state",
            "actual_state",
            "size",
            "sha256",
            "evidence_path",
        )
        rows = self.tsv_file("artifacts.tsv", header)
        expected = self.expected_artifacts()
        expected_keys = {(lane, case, name) for lane in LANES for case, name in expected}
        observed_keys = {(r.get("lane"), r.get("case"), r.get("artifact")) for r in rows}
        self.require(len(expected) == 48, "per-lane artifact denominator is not 48")
        self.require(len(rows) == len(expected_keys) == 192, "artifact denominator is not 192")
        self.require(observed_keys == expected_keys, "artifact key universe changed")
        self.require(len(observed_keys) == len(rows), "duplicate artifact rows")
        for row in rows:
            lane, case, name = row.get("lane", ""), row.get("case", ""), row.get("artifact", "")
            state_value = expected.get((case, name))
            if lane not in LANES or state_value is None:
                continue
            self.require(row.get("expected_state") == state_value, f"{lane}:{case}:{name}: expected state changed")
            self.require(row.get("actual_state") == state_value, f"{lane}:{case}:{name}: actual state mismatch")
            item = f"artifact/{case}/{name}"
            if state_value == "PRESENT":
                path = self.evidence_file(row.get("evidence_path", ""), f"{lane}:{case}:{name}")
                if path is None:
                    continue
                self.require(str(path.stat().st_size) == row.get("size"), f"{lane}:{case}:{name}: size mismatch")
                self.require(sha256_file(path) == row.get("sha256"), f"{lane}:{case}:{name}: hash mismatch")
                canonical = f"lanes/{lane}/artifacts/{case}/{name}"
                self.require(row.get("evidence_path") == canonical, f"{lane}:{case}:{name}: artifact path changed")
                self.artifact_file_map[(lane, item)] = path
            else:
                self.require(row.get("size") == "0", f"{lane}:{case}:{name}: absent size changed")
                self.require(row.get("sha256") == "-", f"{lane}:{case}:{name}: absent hash changed")
                self.require(row.get("evidence_path") == "-", f"{lane}:{case}:{name}: absent path changed")
                canonical = self.evidence / f"lanes/{lane}/artifacts/{case}/{name}"
                self.require(not os.path.lexists(canonical), f"{lane}:{case}:{name}: expected-absent artifact exists")
                self.artifact_file_map[(lane, item)] = None
        return rows

    def validate_aliases(self, roots: dict[str, Path], fixed_cwd: str, alias: str) -> None:
        header = ("lane", "category", "cwd", "alias_path", "link_target", "resolved_target")
        rows = self.tsv_file("alias-ledger.tsv", header)
        self.require(len(rows) == 4, "alias ledger is not four rows")
        self.require(tuple(row.get("lane") for row in rows) == LANES, "alias lane order changed")
        for row in rows:
            lane = row.get("lane", "")
            category = "official" if lane.startswith("official-") else "ours"
            self.require(row.get("category") == category, f"{lane}: alias category changed")
            self.require(row.get("cwd") == fixed_cwd, f"{lane}: alias cwd changed")
            self.require(row.get("alias_path") == alias, f"{lane}: alias pathname changed")
            self.require(row.get("link_target") == str(roots[category]), f"{lane}: alias target changed")
            self.require(row.get("resolved_target") == str(roots[category]), f"{lane}: resolved alias target changed")
        self.require(not os.path.lexists(self.evidence / "shared-work"), "shared work was not removed")

    def validate_semantics(self, command_rows: list[dict[str, str]]) -> None:
        for lane in LANES:
            for case_id, _, _, _, _, _, compile_rc, expected_hex in ASM_CASES:
                if compile_rc == 0 and expected_hex is not None:
                    path = self.artifact_file_map.get((lane, f"artifact/{case_id}/{case_id}.text.bin"))
                    self.require(path is not None and path.read_bytes().hex() == expected_hex, f"{lane}:{case_id}: text encoding changed")
            for prefix in ("negative.elf", "final.elf"):
                key = f"artifact/lto-xw-stream/{prefix}.ltrans0.ltrans.s"
                path = self.artifact_file_map.get((lane, key))
                if path is None:
                    self.failures.append(f"{lane}:{prefix}: ltrans assembly unavailable")
                else:
                    data = path.read_bytes()
                    for token in LTRANS_TOKENS:
                        self.require(token.encode("utf-8") in data, f"{lane}:{prefix}: missing {token!r}")
                    text = data.decode("utf-8", "strict")
                    for function, arch_token in FUNCTION_ARCH_TOKENS.items():
                        start = text.find(function + ":")
                        end = text.find("\t.size\t" + function, start + 1)
                        block = text[start:end] if start >= 0 and end > start else ""
                        self.require(
                            ".option arch" in block and arch_token in block,
                            f"{lane}:{prefix}:{function}: bound arch token {arch_token!r} missing",
                        )
            for stem, _, _ in LTO_TUS:
                own = [r for r in command_rows if r.get("lane") == lane and r.get("case") == "lto-xw-stream" and r.get("stage") == "own-read-" + stem]
                self.require(len(own) == 1, f"{lane}:{stem}: lto-dump row missing")
                if own:
                    stdout = self.evidence_file(own[0]["stdout_path"], f"{lane}:{stem}:lto-dump stdout")
                    stderr = self.evidence_file(own[0]["stderr_path"], f"{lane}:{stem}:lto-dump stderr")
                    self.require(stdout is not None and stdout.stat().st_size > 0, f"{lane}:{stem}: lto-dump stdout empty")
                    self.require(stderr is not None and stderr.stat().st_size == 0, f"{lane}:{stem}: lto-dump stderr nonempty")
            negative = [r for r in command_rows if r.get("lane") == lane and r.get("case") == "lto-xw-stream" and r.get("stage") == "link-base-negative"]
            if negative:
                stdout = self.evidence_file(negative[0]["stdout_path"], f"{lane}:negative stdout")
                stderr = self.evidence_file(negative[0]["stderr_path"], f"{lane}:negative stderr")
                self.require(stdout is not None and stdout.stat().st_size == 0, f"{lane}:negative stdout is not empty")
                self.require(stderr is not None and stderr.stat().st_size > 0, f"{lane}:negative stderr is empty")

    def validate_comparisons(self) -> None:
        header = (
            "pair",
            "phase",
            "left_lane",
            "right_lane",
            "item",
            "left_state",
            "right_state",
            "left_sha256",
            "right_sha256",
            "left_size",
            "right_size",
            "comparison",
        )
        rows = self.tsv_file("comparisons.tsv", header)
        item_maps: dict[tuple[str, str], Path | None] = {}
        item_maps.update(self.command_file_map)
        item_maps.update(self.artifact_file_map)
        per_lane_items = {item for lane, item in item_maps if lane == LANES[0]}
        self.require(len(per_lane_items) == 123, "per-lane comparison denominator is not 123")
        for lane in LANES[1:]:
            self.require({item for item_lane, item in item_maps if item_lane == lane} == per_lane_items, f"{lane}: item universe differs")
        expected_order = [
            (pair, phase, left, right, item)
            for pair, phase, left, right in PAIRS
            for item in sorted(per_lane_items)
        ]
        observed_order = [
            (r.get("pair"), r.get("phase"), r.get("left_lane"), r.get("right_lane"), r.get("item"))
            for r in rows
        ]
        self.require(len(rows) == len(expected_order) == 492, "comparison denominator is not 492")
        self.require(observed_order == expected_order, "comparison rows/order changed")
        self.require(len(set(observed_order)) == len(observed_order), "duplicate comparison rows")
        for row in rows:
            left, right, item = row.get("left_lane", ""), row.get("right_lane", ""), row.get("item", "")
            left_path = item_maps.get((left, item))
            right_path = item_maps.get((right, item))
            left_state = "PRESENT" if left_path is not None else "ABSENT"
            right_state = "PRESENT" if right_path is not None else "ABSENT"
            left_size = left_path.stat().st_size if left_path is not None else 0
            right_size = right_path.stat().st_size if right_path is not None else 0
            left_hash = sha256_file(left_path) if left_path is not None else "-"
            right_hash = sha256_file(right_path) if right_path is not None else "-"
            if left_state == right_state == "ABSENT":
                comparison = "BOTH_ABSENT"
            elif left_state == right_state == "PRESENT":
                comparison = (
                    "EXACT"
                    if left_size == right_size
                    and left_hash == right_hash
                    and files_equal(left_path, right_path)
                    else "DIFF"
                )
            else:
                comparison = "STATE_DIFF"
            self.require(row.get("left_state") == left_state, f"{row.get('pair')}:{item}: left state ledger mismatch")
            self.require(row.get("right_state") == right_state, f"{row.get('pair')}:{item}: right state ledger mismatch")
            self.require(row.get("left_sha256") == left_hash, f"{row.get('pair')}:{item}: left hash mismatch")
            self.require(row.get("right_sha256") == right_hash, f"{row.get('pair')}:{item}: right hash mismatch")
            self.require(row.get("left_size") == str(left_size), f"{row.get('pair')}:{item}: left size mismatch")
            self.require(row.get("right_size") == str(right_size), f"{row.get('pair')}:{item}: right size mismatch")
            self.require(row.get("comparison") == comparison, f"{row.get('pair')}:{item}: comparison ledger mismatch")
            self.require(comparison in ("EXACT", "BOTH_ABSENT"), f"{row.get('pair')}:{item}: {comparison}")

    def validate_run_markers(self, contract_digest: str) -> None:
        running = self.json_file("RUNNING.json")
        summary = self.json_file("runner-summary.json")
        complete = self.json_file("RUN_COMPLETE.json")
        self.require(not (self.evidence / "RUN_ABORTED.json").exists(), "RUN_ABORTED marker exists")
        self.require(running.get("schema") == "openwch-xw-lto-running-v1", "running schema changed")
        self.require(running.get("state") == "RUNNING", "running state changed")
        self.require(running.get("contract_sha256") == contract_digest, "running contract digest mismatch")
        self.require(summary.get("schema") == "openwch-xw-lto-run-summary-v1", "summary schema changed")
        self.require(summary.get("status") == "PASS", "runner did not pass")
        self.require(summary.get("mode") == self.mode, "summary mode changed")
        self.require(summary.get("platform") == self.context.get("platform"), "summary platform changed")
        self.require(summary.get("lane_count") == 4, "summary lane count changed")
        self.require(summary.get("command_count") == 100, "summary command count changed")
        self.require(summary.get("artifact_count") == 192, "summary artifact count changed")
        self.require(summary.get("comparison_count") == 492, "summary comparison count changed")
        self.require(summary.get("comparison_failure_count") == 0, "summary comparison failures")
        self.require(summary.get("semantic_failure_count") == 0, "summary semantic failures")
        self.require(summary.get("semantic_failures") == [], "summary semantic ledger nonempty")
        self.require(summary.get("comparison_failures") == [], "summary comparison ledger nonempty")
        self.require(summary.get("contract_sha256") == contract_digest, "summary contract mismatch")
        self.require(summary.get("tool_inputs_stable") is True, "tool inputs unstable")
        self.require(summary.get("contract_stable") is True, "contract unstable")
        self.require(summary.get("source_date_epoch") == 1767225600, "summary epoch changed")
        self.require(summary.get("normalization") == "NONE", "summary normalization changed")
        self.require(complete.get("schema") == "openwch-xw-lto-run-complete-v1", "complete schema changed")
        self.require(complete.get("state") == "COMPLETE", "run is not complete")
        self.require(complete.get("status") == "PASS", "complete status is not pass")
        self.require(complete.get("mode") == self.mode, "complete mode changed")
        self.require(complete.get("platform") == self.context.get("platform"), "complete platform changed")
        self.require(complete.get("contract_sha256") == contract_digest, "complete contract mismatch")
        self.require(complete.get("runner_summary_sha256") == sha256_file(self.evidence / "runner-summary.json"), "runner summary hash mismatch")
        self.require(complete.get("formal_seal_eligible") is (self.mode == "formal"), "formal eligibility changed")

    def validate_closed_world(self) -> None:
        expected_globals = {
            "RUNNING.json",
            "RUN_COMPLETE.json",
            "alias-ledger.tsv",
            "artifacts.tsv",
            "commands.tsv",
            "comparisons.tsv",
            "context.json",
            "contract-files.after.tsv",
            "contract-files.before.tsv",
            "runner-summary.json",
            "tool-inputs.after.tsv",
            "tool-inputs.before.tsv",
        }
        self.declared_files.update(expected_globals)
        actual: set[str] = set()
        for path in sorted(self.evidence.rglob("*")):
            relative = path.relative_to(self.evidence).as_posix()
            mode = path.lstat().st_mode
            self.require(not stat.S_ISLNK(mode), f"symlink in evidence tree: {relative}")
            self.require(stat.S_ISDIR(mode) or stat.S_ISREG(mode), f"special file in evidence tree: {relative}")
            if stat.S_ISREG(mode):
                actual.add(relative)
        self.require(actual == self.declared_files, f"closed-world file mismatch: missing={sorted(self.declared_files-actual)} extra={sorted(actual-self.declared_files)}")

    def evidence_manifest(self) -> bytes:
        rows: list[tuple[str, int, str]] = []
        for path in sorted(self.evidence.rglob("*"), key=lambda p: p.relative_to(self.evidence).as_posix()):
            if path.is_file() and not path.is_symlink():
                relative = path.relative_to(self.evidence).as_posix()
                rows.append((relative, path.stat().st_size, sha256_file(path)))
        return tsv_bytes(("path", "size", "sha256"), rows)

    def audit(self) -> int:
        contract = self.validate_contract()
        roots, fixed_cwd, alias = self.validate_context()
        if self.mode == "smoke-identical-roots" and not self.allow_smoke:
            print("xw-lto auditor: FAIL: smoke evidence requires --allow-smoke", file=sys.stderr)
            return 1
        forbidden = (
            "AUDIT.json",
            "SEAL.json",
            "audit-manifest.tsv",
            "SMOKE_AUDIT.json",
            "SMOKE_SEAL.json",
            "smoke-audit-manifest.tsv",
        )
        existing = [name for name in forbidden if os.path.lexists(self.evidence / name)]
        if existing:
            print(f"xw-lto auditor: FAIL: audit/seal output already exists: {existing}", file=sys.stderr)
            return 1

        try:
            live_contract = suite_manifest_bytes()
        except Exception as error:
            self.failures.append(str(error))
            live_contract = b""
        before_path = self.evidence / "contract-files.before.tsv"
        after_path = self.evidence / "contract-files.after.tsv"
        self.require(before_path.is_file(), "contract before manifest missing")
        self.require(after_path.is_file(), "contract after manifest missing")
        if before_path.is_file():
            self.declared_files.add("contract-files.before.tsv")
        if after_path.is_file():
            self.declared_files.add("contract-files.after.tsv")
        self.require(before_path.is_file() and before_path.read_bytes() == live_contract, "before contract does not match live suite")
        self.require(after_path.is_file() and after_path.read_bytes() == live_contract, "after contract does not match live suite")
        contract_digest = sha256_bytes(live_contract)

        tool_before = self.evidence / "tool-inputs.before.tsv"
        tool_after = self.evidence / "tool-inputs.after.tsv"
        self.require(tool_before.is_file(), "tool before manifest missing")
        self.require(tool_after.is_file(), "tool after manifest missing")
        if tool_before.is_file():
            self.declared_files.add("tool-inputs.before.tsv")
        if tool_after.is_file():
            self.declared_files.add("tool-inputs.after.tsv")
        try:
            live_tools = tool_manifest_bytes(roots)
        except Exception as error:
            self.failures.append(f"cannot rehash tool inputs: {error}")
            live_tools = b""
        self.require(tool_before.is_file() and tool_before.read_bytes() == live_tools, "before tool inputs differ from live")
        self.require(tool_after.is_file() and tool_after.read_bytes() == live_tools, "after tool inputs differ from live")

        self.validate_run_markers(contract_digest)
        self.validate_aliases(roots, fixed_cwd, alias)
        commands = self.validate_commands(fixed_cwd, alias)
        self.validate_artifacts()
        self.validate_semantics(commands)
        self.validate_comparisons()
        self.validate_closed_world()

        report = {
            "schema": "openwch-xw-lto-audit-v1",
            "status": "PASS" if not self.failures else "FAIL",
            "mode": self.mode,
            "platform": self.context.get("platform"),
            "check_count": self.check_count,
            "failure_count": len(self.failures),
            "failures": self.failures,
            "contract_sha256": contract_digest,
            "auditor_sha256": sha256_file(Path(__file__).resolve()),
            "audited_at": utc_now(),
        }
        if self.failures:
            write_json_atomic(self.evidence / self.audit_name, report)
            freeze_evidence_tree(self.evidence)
            print(json.dumps(report, sort_keys=True))
            return 1

        manifest = self.evidence_manifest()
        write_bytes_atomic(self.evidence / self.manifest_name, manifest)
        report["evidence_manifest_sha256"] = sha256_bytes(manifest)
        report["evidence_file_count"] = max(0, len(manifest.splitlines()) - 1)
        write_json_atomic(self.evidence / self.audit_name, report)
        seal = {
            "schema": "openwch-xw-lto-seal-v1",
            "state": "SEALED" if self.mode == "formal" else "SMOKE_SEALED",
            "scope": "FORMAL" if self.mode == "formal" else "HARNESS_SMOKE_ONLY",
            "mode": self.mode,
            "platform": self.context.get("platform"),
            "contract_sha256": contract_digest,
            "evidence_manifest_sha256": sha256_bytes(manifest),
            "evidence_file_count": report["evidence_file_count"],
            "audit_sha256": sha256_file(self.evidence / self.audit_name),
            "auditor_sha256": report["auditor_sha256"],
            "runner_sha256": next(
                row.split("\t")[2]
                for row in live_contract.decode("utf-8").splitlines()[1:]
                if row.split("\t")[0] == "run.py"
            ),
            "runner_summary_sha256": sha256_file(self.evidence / "runner-summary.json"),
            "tree_policy": "RECURSIVE_NO_WRITE_BITS",
            "writable_entries_after_seal": 0,
            "sealed_at": utc_now(),
        }
        finalize_readonly_seal(self.evidence, self.evidence / self.seal_name, seal)
        print(json.dumps(seal, sort_keys=True))
        return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-root", required=True)
    parser.add_argument(
        "--allow-smoke",
        action="store_true",
        help="audit explicit smoke-identical-roots evidence; never emits formal SEAL.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    candidate = Path(args.evidence_root)
    if not candidate.is_absolute():
        print("xw-lto auditor: FAIL: evidence root must be absolute", file=sys.stderr)
        return 1
    try:
        evidence = candidate.resolve(strict=True)
        tmp_root = REPO_TMP.resolve(strict=True)
    except Exception as error:
        print(f"xw-lto auditor: FAIL: cannot resolve evidence: {error}", file=sys.stderr)
        return 1
    if not evidence.is_dir() or evidence.is_symlink() or not is_within(evidence, tmp_root):
        print("xw-lto auditor: FAIL: evidence must be a real directory below repo tmp/", file=sys.stderr)
        return 1
    try:
        return Auditor(evidence, args.allow_smoke).audit()
    except Exception as error:
        # An auditor bug or malformed tree must never result in a seal.
        print(f"xw-lto auditor: FAIL-CLOSED exception: {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
