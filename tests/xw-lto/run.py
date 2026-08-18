#!/usr/bin/env python3
"""Run the four-lane, byte-exact WCH XW + LTO parity gate.

The runner is intentionally an evidence producer, not the authority that
seals its own output.  audit_and_seal.py independently checks the closed
denominators and every recorded byte.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform as host_platform
import shutil
import stat
import subprocess
import sys
import traceback
from typing import Any, Iterable


SUITE = Path(__file__).resolve().parent
REPO = SUITE.parents[1]
REPO_TMP = REPO / "tmp"
CONTRACT_PATH = SUITE / "contract.json"
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
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


def write_bytes_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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
    import io

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
    for path in sorted(SUITE.rglob("*"), key=lambda p: p.relative_to(SUITE).as_posix()):
        relative = path.relative_to(SUITE).as_posix()
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            raise RuntimeError(f"bytecode/cache file is forbidden in contract tree: {relative}")
        if path.is_symlink():
            raise RuntimeError(f"contract tree contains a symlink: {relative}")
        if path.is_file():
            rows.append((relative, path.stat().st_size, sha256_file(path)))
    return tsv_bytes(("path", "size", "sha256"), rows)


def load_contract() -> dict[str, Any]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract.get("schema") != "openwch-xw-lto-contract-v1":
        raise RuntimeError("unsupported or missing contract schema")
    if contract.get("source_date_epoch") != 1767225600:
        raise RuntimeError("SOURCE_DATE_EPOCH contract changed")
    if contract.get("target") != "riscv32-wch-elf":
        raise RuntimeError("target contract changed")
    if contract.get("abi") != "ilp32":
        raise RuntimeError("ABI contract changed")
    expected_lanes = ["official-1", "official-2", "ours-1", "ours-2"]
    if contract.get("lanes") != expected_lanes:
        raise RuntimeError("four-lane order contract changed")
    seeds: list[str] = []
    for case in contract.get("asm_cases", []):
        seeds.append(case["compile_seed"])
        if case.get("link_seed"):
            seeds.append(case["link_seed"])
    lto = contract["lto_case"]
    seeds.extend(tu["seed"] for tu in lto["translation_units"])
    seeds.extend((lto["positive_link_seed"], lto["negative_link_seed"]))
    if len(seeds) != len(set(seeds)):
        raise RuntimeError("translation-unit/link random seeds are not unique")
    return contract


def validate_root(raw: str, label: str) -> tuple[Path, Path]:
    requested = Path(raw)
    if not requested.is_absolute():
        raise RuntimeError(f"{label} must be an absolute path")
    lexical = Path(os.path.abspath(requested))
    resolved = lexical.resolve(strict=True)
    repo_resolved = REPO.resolve(strict=True)
    if not is_within(lexical, repo_resolved) or not is_within(resolved, repo_resolved):
        raise RuntimeError(f"{label} is outside the repository")
    if not resolved.is_dir():
        raise RuntimeError(f"{label} is not a directory")
    for relative in TOOL_INPUTS:
        path = resolved / relative
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"{label} lacks required tool input: {relative}")
        mode = path.lstat().st_mode
        if not stat.S_ISREG(mode) or not is_within(path.resolve(strict=True), resolved):
            raise RuntimeError(f"{label} has unsafe tool input: {relative}")
    for relative in OPTIONAL_TOOL_INPUTS:
        path = resolved / relative
        if os.path.lexists(path):
            mode = path.lstat().st_mode
            if path.is_symlink() or not stat.S_ISREG(mode):
                raise RuntimeError(f"{label} has unsafe optional tool input: {relative}")
            if not is_within(path.resolve(strict=True), resolved):
                raise RuntimeError(f"{label} optional tool input escapes root: {relative}")
    return lexical, resolved


def validate_evidence_root(raw: str) -> Path:
    candidate = Path(raw)
    if not candidate.is_absolute():
        raise RuntimeError("--evidence-root must be an absolute path")
    if candidate.name in ("", ".", ".."):
        raise RuntimeError("invalid evidence-root basename")
    parent = candidate.parent.resolve(strict=True)
    evidence = parent / candidate.name
    tmp_resolved = REPO_TMP.resolve(strict=True)
    if not is_within(evidence, tmp_resolved):
        raise RuntimeError("evidence root must be below the repository tmp/ directory")
    if os.path.lexists(evidence):
        raise RuntimeError("evidence root already exists; attempts are append-only")
    return evidence


def validate_host(platform_name: str) -> None:
    system = host_platform.system()
    machine = host_platform.machine().lower()
    if platform_name == "darwin-arm64":
        valid = system == "Darwin" and machine in ("arm64", "aarch64")
    else:
        valid = system == "Linux" and machine in ("x86_64", "amd64")
    if not valid:
        raise RuntimeError(
            f"--platform={platform_name} does not match host {system}/{machine}"
        )


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
                state, size, digest = "PRESENT", path.stat().st_size, sha256_file(path)
            else:
                state, size, digest = "MISSING", 0, "-"
            link_target = "-"
            rows.append((category, str(root), relative, state, size, digest + ":" + link_target))
    return tsv_bytes(
        ("category", "resolved_root", "path", "state", "size", "sha256_and_link_target"),
        rows,
    )


class GateRun:
    def __init__(
        self,
        contract: dict[str, Any],
        evidence: Path,
        platform_name: str,
        mode: str,
        requested_roots: dict[str, Path],
        roots: dict[str, Path],
    ) -> None:
        self.contract = contract
        self.evidence = evidence
        self.platform_name = platform_name
        self.mode = mode
        self.requested_roots = requested_roots
        self.roots = roots
        self.work = evidence / "shared-work"
        self.alias = self.work / "toolchain-current"
        self.commands: list[dict[str, Any]] = []
        self.artifacts: list[dict[str, Any]] = []
        self.alias_rows: list[tuple[Any, ...]] = []
        self.semantic_failures: list[str] = []
        self.command_items: dict[tuple[str, str], tuple[str, Path]] = {}
        self.artifact_items: dict[tuple[str, str], tuple[str, Path | None]] = {}

    def lane_category(self, lane: str) -> str:
        return "official" if lane.startswith("official-") else "ours"

    def environment(self) -> dict[str, str]:
        # Start empty: compiler/loader/Python variables inherited from the
        # invoking shell are intentionally outside the execution contract.
        return {
            "SOURCE_DATE_EPOCH": str(self.contract["source_date_epoch"]),
            "LC_ALL": "C",
            "LANG": "C",
            "TZ": "UTC",
            "TMPDIR": str(self.work / "tmp"),
            "ZERO_AR_DATE": "1",
            "PATH": "/usr/bin:/bin",
            "TERM": "dumb",
            "NO_COLOR": "1",
            "GCC_COLORS": "",
            # Keep subprogram names in raw diagnostics on the fixed alias.
            # Without this, GCC resolves the symlink and a failing LTO link
            # prints the lane-specific installation root for ld.
            "GCC_EXEC_PREFIX": str(self.alias / "lib/gcc") + os.sep,
        }

    def reset_work(self, lane: str) -> tuple[Path, Path]:
        if self.work.exists() or self.work.is_symlink():
            shutil.rmtree(self.work)
        self.work.mkdir(parents=True)
        (self.work / "tmp").mkdir()
        category = self.lane_category(lane)
        target = self.roots[category]
        os.symlink(str(target), self.alias)
        self.alias_rows.append(
            (
                lane,
                category,
                str(self.work),
                str(self.alias),
                os.readlink(self.alias),
                str(self.alias.resolve(strict=True)),
            )
        )
        gcc = self.alias / "bin/riscv32-wch-elf-gcc"
        objcopy = self.alias / "bin/riscv32-wch-elf-objcopy"
        return gcc, objcopy

    def run_command(
        self,
        lane: str,
        case_id: str,
        stage: str,
        argv: list[str],
        expected_rc: int,
        prerequisite: bool = True,
    ) -> int:
        raw_dir = self.evidence / "lanes" / lane / "raw" / case_id
        raw_dir.mkdir(parents=True, exist_ok=True)
        rc_path = raw_dir / f"{stage}.rc"
        stdout_path = raw_dir / f"{stage}.stdout"
        stderr_path = raw_dir / f"{stage}.stderr"
        if prerequisite:
            try:
                process = subprocess.run(
                    argv,
                    cwd=self.work,
                    env=self.environment(),
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )
                rc, stdout, stderr = process.returncode, process.stdout, process.stderr
            except OSError as error:
                rc, stdout = 126, b""
                stderr = (f"runner exec error: {error}\n").encode("utf-8", "backslashreplace")
        else:
            rc, stdout, stderr = 125, b"", b"runner: prerequisite artifact missing\n"
        write_bytes_atomic(rc_path, f"{rc}\n".encode("ascii"))
        write_bytes_atomic(stdout_path, stdout)
        write_bytes_atomic(stderr_path, stderr)
        relative_rc = rc_path.relative_to(self.evidence).as_posix()
        relative_stdout = stdout_path.relative_to(self.evidence).as_posix()
        relative_stderr = stderr_path.relative_to(self.evidence).as_posix()
        self.commands.append(
            {
                "lane": lane,
                "case": case_id,
                "stage": stage,
                "cwd": str(self.work),
                "argv_json": json.dumps(argv, separators=(",", ":")),
                "expected_rc": expected_rc,
                "actual_rc": rc,
                "rc_path": relative_rc,
                "rc_sha256": sha256_file(rc_path),
                "stdout_path": relative_stdout,
                "stdout_size": len(stdout),
                "stdout_sha256": sha256_bytes(stdout),
                "stderr_path": relative_stderr,
                "stderr_size": len(stderr),
                "stderr_sha256": sha256_bytes(stderr),
            }
        )
        for component, path in (("rc", rc_path), ("stdout", stdout_path), ("stderr", stderr_path)):
            key = f"raw/{case_id}/{stage}.{component}"
            self.command_items[(lane, key)] = ("PRESENT", path)
        if rc != expected_rc:
            self.semantic_failures.append(
                f"{lane}:{case_id}:{stage}: expected rc {expected_rc}, got {rc}"
            )
        return rc

    def record_artifact(
        self,
        lane: str,
        case_id: str,
        name: str,
        source: Path,
        expected_state: str,
    ) -> None:
        destination = self.evidence / "lanes" / lane / "artifacts" / case_id / name
        present = source.is_file()
        actual_state = "PRESENT" if present else "ABSENT"
        if present:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            size = destination.stat().st_size
            digest = sha256_file(destination)
            relative = destination.relative_to(self.evidence).as_posix()
            item_path: Path | None = destination
        else:
            size, digest, relative, item_path = 0, "-", "-", None
        self.artifacts.append(
            {
                "lane": lane,
                "case": case_id,
                "artifact": name,
                "expected_state": expected_state,
                "actual_state": actual_state,
                "size": size,
                "sha256": digest,
                "evidence_path": relative,
            }
        )
        key = f"artifact/{case_id}/{name}"
        self.artifact_items[(lane, key)] = (actual_state, item_path)
        if actual_state != expected_state:
            self.semantic_failures.append(
                f"{lane}:{case_id}:{name}: expected {expected_state}, got {actual_state}"
            )

    def copy_fixture(self, fixture: str, destination_name: str) -> Path:
        source = SUITE / fixture
        destination = self.work / destination_name
        shutil.copyfile(source, destination)
        return destination

    def run_asm_case(
        self, lane: str, case: dict[str, Any], gcc: Path, objcopy: Path
    ) -> None:
        case_id = case["id"]
        source = self.copy_fixture(case["fixture"], case_id + ".S")
        obj = self.work / (case_id + ".o")
        assembly = self.work / (case_id + ".s")
        elf = self.work / (case_id + ".elf")
        binary = self.work / (case_id + ".bin")
        text_binary = self.work / (case_id + ".text.bin")
        compile_argv = [
            str(gcc),
            f"-march={case['march']}",
            f"-mabi={self.contract['abi']}",
            f"-frandom-seed={case['compile_seed']}",
            "-save-temps=obj",
            "-c",
            source.name,
            "-o",
            obj.name,
        ]
        compile_rc = self.run_command(
            lane,
            case_id,
            "compile",
            compile_argv,
            int(case["expected_compile_rc"]),
        )
        if int(case["expected_compile_rc"]) == 0:
            link_argv = [
                str(gcc),
                f"-march={case['march']}",
                f"-mabi={self.contract['abi']}",
                f"-frandom-seed={case['link_seed']}",
                "-nostdlib",
                "-nostartfiles",
                "-nodefaultlibs",
                f"-Wl,-e,{case['entry']}",
                "-Wl,--no-relax",
                obj.name,
                "-o",
                elf.name,
            ]
            link_rc = self.run_command(
                lane, case_id, "link", link_argv, 0, prerequisite=obj.is_file()
            )
            bin_argv = [str(objcopy), "-O", "binary", elf.name, binary.name]
            self.run_command(
                lane,
                case_id,
                "objcopy-bin",
                bin_argv,
                0,
                prerequisite=link_rc == 0 and elf.is_file(),
            )
            text_argv = [
                str(objcopy),
                "-j",
                ".text",
                "-O",
                "binary",
                obj.name,
                text_binary.name,
            ]
            self.run_command(
                lane,
                case_id,
                "objcopy-text",
                text_argv,
                0,
                prerequisite=compile_rc == 0 and obj.is_file(),
            )
            artifact_contract = (
                (assembly.name, assembly, "PRESENT"),
                (obj.name, obj, "PRESENT"),
                (elf.name, elf, "PRESENT"),
                (binary.name, binary, "PRESENT"),
                (text_binary.name, text_binary, "PRESENT"),
            )
        else:
            artifact_contract = (
                (assembly.name, assembly, "PRESENT"),
                (obj.name, obj, "ABSENT"),
            )
        for name, path, expected in artifact_contract:
            self.record_artifact(lane, case_id, name, path, expected)
        if case.get("expected_text_hex") and text_binary.is_file():
            actual = text_binary.read_bytes().hex()
            if actual != case["expected_text_hex"]:
                self.semantic_failures.append(
                    f"{lane}:{case_id}: .text bytes {actual} != {case['expected_text_hex']}"
                )

    def run_lto_case(self, lane: str, gcc: Path, objcopy: Path) -> None:
        case = self.contract["lto_case"]
        case_id = case["id"]
        objects: list[Path] = []
        for tu in case["translation_units"]:
            source = self.copy_fixture(tu["fixture"], tu["stem"] + ".c")
            obj = self.work / (tu["stem"] + ".o")
            argv = [
                str(gcc),
                "-O2",
                f"-flto={case['flto_jobs']}",
                "-fno-fat-lto-objects",
                "-save-temps=obj",
                f"-march={case['compile_march']}",
                f"-mabi={self.contract['abi']}",
                f"-frandom-seed={tu['seed']}",
                "-c",
                source.name,
                "-o",
                obj.name,
            ]
            self.run_command(
                lane,
                case_id,
                "compile-" + tu["stem"],
                argv,
                int(case["expected_compile_rc"]),
            )
            objects.append(obj)

        lto_dump = self.alias / "bin/riscv32-wch-elf-lto-dump"
        for tu, obj in zip(case["translation_units"], objects):
            self.run_command(
                lane,
                case_id,
                "own-read-" + tu["stem"],
                [str(lto_dump), "-list", obj.name],
                0,
                prerequisite=obj.is_file(),
            )

        object_names = [path.name for path in objects]
        negative_elf = self.work / "negative.elf"
        negative_argv = [
            str(gcc),
            "-O2",
            f"-flto={case['flto_jobs']}",
            "-save-temps=obj",
            f"-march={case['negative_link_march']}",
            f"-mabi={self.contract['abi']}",
            f"-frandom-seed={case['negative_link_seed']}",
            "-nostdlib",
            "-nostartfiles",
            "-nodefaultlibs",
            f"-Wl,-e,{case['entry']}",
            "-Wl,--no-relax",
            *object_names,
            "-o",
            negative_elf.name,
        ]
        objects_ready = all(path.is_file() for path in objects)
        self.run_command(
            lane,
            case_id,
            "link-base-negative",
            negative_argv,
            int(case["expected_negative_link_rc"]),
            prerequisite=objects_ready,
        )

        final_elf = self.work / "final.elf"
        positive_argv = [
            str(gcc),
            "-O2",
            f"-flto={case['flto_jobs']}",
            "-save-temps=obj",
            f"-march={case['positive_link_march']}",
            f"-mabi={self.contract['abi']}",
            f"-frandom-seed={case['positive_link_seed']}",
            "-nostdlib",
            "-nostartfiles",
            "-nodefaultlibs",
            f"-Wl,-e,{case['entry']}",
            "-Wl,--no-relax",
            *object_names,
            "-o",
            final_elf.name,
        ]
        positive_rc = self.run_command(
            lane,
            case_id,
            "link-positive",
            positive_argv,
            int(case["expected_positive_link_rc"]),
            prerequisite=objects_ready,
        )
        final_bin = self.work / "final.bin"
        final_text = self.work / "final.text.bin"
        self.run_command(
            lane,
            case_id,
            "objcopy-bin",
            [str(objcopy), "-O", "binary", final_elf.name, final_bin.name],
            0,
            prerequisite=positive_rc == 0 and final_elf.is_file(),
        )
        self.run_command(
            lane,
            case_id,
            "objcopy-text",
            [
                str(objcopy),
                "-j",
                ".text",
                "-O",
                "binary",
                final_elf.name,
                final_text.name,
            ],
            0,
            prerequisite=positive_rc == 0 and final_elf.is_file(),
        )

        artifacts: list[tuple[str, Path, str]] = []
        for tu in case["translation_units"]:
            stem = tu["stem"]
            artifacts.extend(
                (
                    (stem + ".i", self.work / (stem + ".i"), "PRESENT"),
                    (stem + ".s", self.work / (stem + ".s"), "PRESENT"),
                    (stem + ".o", self.work / (stem + ".o"), "PRESENT"),
                )
            )
        for prefix in ("negative.elf", "final.elf"):
            artifacts.extend(
                (
                    (prefix + ".res", self.work / (prefix + ".res"), "PRESENT"),
                    (
                        prefix + ".ltrans0.ltrans.s",
                        self.work / (prefix + ".ltrans0.ltrans.s"),
                        "PRESENT",
                    ),
                    (prefix + ".ltrans0.o", self.work / (prefix + ".ltrans0.o"), "PRESENT"),
                    (prefix + ".ltrans_args", self.work / (prefix + ".ltrans_args"), "PRESENT"),
                    (
                        prefix + ".ltrans0.ltrans_args",
                        self.work / (prefix + ".ltrans0.ltrans_args"),
                        "PRESENT",
                    ),
                    (prefix + ".wpa.args.0", self.work / (prefix + ".wpa.args.0"), "PRESENT"),
                    (
                        prefix + ".ltrans0.ltrans.args.0",
                        self.work / (prefix + ".ltrans0.ltrans.args.0"),
                        "PRESENT",
                    ),
                    (prefix + ".ltrans.out", self.work / (prefix + ".ltrans.out"), "PRESENT"),
                )
            )
        artifacts.extend(
            (
                ("negative.elf", negative_elf, "ABSENT"),
                ("final.elf", final_elf, "PRESENT"),
                ("final.bin", final_bin, "PRESENT"),
                ("final.text.bin", final_text, "PRESENT"),
            )
        )
        for name, path, expected in artifacts:
            self.record_artifact(lane, case_id, name, path, expected)

        for prefix in ("negative.elf", "final.elf"):
            ltrans = self.work / (prefix + ".ltrans0.ltrans.s")
            if ltrans.is_file():
                data = ltrans.read_bytes()
                for token in case["required_ltrans_tokens"]:
                    if token.encode("utf-8") not in data:
                        self.semantic_failures.append(
                            f"{lane}:{case_id}:{prefix}: missing ltrans token {token!r}"
                        )
                text = data.decode("utf-8", "strict")
                for function, arch_token in case["required_function_arch_tokens"].items():
                    start = text.find(function + ":")
                    end = text.find("\t.size\t" + function, start + 1)
                    block = text[start:end] if start >= 0 and end > start else ""
                    if ".option arch" not in block or arch_token not in block:
                        self.semantic_failures.append(
                            f"{lane}:{case_id}:{prefix}: {function} lacks bound arch token {arch_token}"
                        )

    def run_lane(self, lane: str) -> None:
        gcc, objcopy = self.reset_work(lane)
        for case in self.contract["asm_cases"]:
            self.run_asm_case(lane, case, gcc, objcopy)
        self.run_lto_case(lane, gcc, objcopy)

    def write_ledgers(self) -> None:
        command_header = (
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
        command_rows = ([row[column] for column in command_header] for row in self.commands)
        write_bytes_atomic(self.evidence / "commands.tsv", tsv_bytes(command_header, command_rows))

        artifact_header = (
            "lane",
            "case",
            "artifact",
            "expected_state",
            "actual_state",
            "size",
            "sha256",
            "evidence_path",
        )
        artifact_rows = ([row[column] for column in artifact_header] for row in self.artifacts)
        write_bytes_atomic(
            self.evidence / "artifacts.tsv", tsv_bytes(artifact_header, artifact_rows)
        )
        write_bytes_atomic(
            self.evidence / "alias-ledger.tsv",
            tsv_bytes(
                (
                    "lane",
                    "category",
                    "cwd",
                    "alias_path",
                    "link_target",
                    "resolved_target",
                ),
                self.alias_rows,
            ),
        )

    def compare(self) -> tuple[list[dict[str, Any]], list[str]]:
        all_items: dict[tuple[str, str], tuple[str, Path | None]] = {}
        all_items.update(self.command_items)
        all_items.update(self.artifact_items)
        comparison_rows: list[dict[str, Any]] = []
        failures: list[str] = []
        for pair in self.contract["comparison_pairs"]:
            left, right = pair["left"], pair["right"]
            keys = sorted(
                {key for lane, key in all_items if lane == left}
                | {key for lane, key in all_items if lane == right}
            )
            for key in keys:
                left_state, left_path = all_items.get((left, key), ("UNDECLARED", None))
                right_state, right_path = all_items.get((right, key), ("UNDECLARED", None))
                left_hash = sha256_file(left_path) if left_path is not None else "-"
                right_hash = sha256_file(right_path) if right_path is not None else "-"
                left_size = left_path.stat().st_size if left_path is not None else 0
                right_size = right_path.stat().st_size if right_path is not None else 0
                if left_state == right_state == "ABSENT":
                    result = "BOTH_ABSENT"
                elif left_state == right_state == "PRESENT":
                    result = (
                        "EXACT"
                        if left_size == right_size
                        and left_hash == right_hash
                        and files_equal(left_path, right_path)
                        else "DIFF"
                    )
                else:
                    result = "STATE_DIFF"
                row = {
                    "pair": pair["id"],
                    "phase": pair["phase"],
                    "left_lane": left,
                    "right_lane": right,
                    "item": key,
                    "left_state": left_state,
                    "right_state": right_state,
                    "left_sha256": left_hash,
                    "right_sha256": right_hash,
                    "left_size": left_size,
                    "right_size": right_size,
                    "comparison": result,
                }
                comparison_rows.append(row)
                if result not in ("EXACT", "BOTH_ABSENT"):
                    failures.append(f"{pair['id']}:{key}:{result}")
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
        write_bytes_atomic(
            self.evidence / "comparisons.tsv",
            tsv_bytes(header, ([row[column] for column in header] for row in comparison_rows)),
        )
        return comparison_rows, failures

    def execute(self) -> int:
        before_contract = suite_manifest_bytes()
        write_bytes_atomic(self.evidence / "contract-files.before.tsv", before_contract)
        write_bytes_atomic(
            self.evidence / "tool-inputs.before.tsv", tool_manifest_bytes(self.roots)
        )
        context = {
            "schema": "openwch-xw-lto-run-context-v1",
            "started_at": utc_now(),
            "platform": self.platform_name,
            "mode": self.mode,
            "host_system": host_platform.system(),
            "host_machine": host_platform.machine(),
            "repository": str(REPO.resolve(strict=True)),
            "suite": str(SUITE),
            "evidence_root": str(self.evidence),
            "fixed_work_cwd": str(self.work),
            "fixed_toolchain_alias": str(self.alias),
            "source_date_epoch": self.contract["source_date_epoch"],
            "lane_order": self.contract["lanes"],
            "official_root_requested": str(self.requested_roots["official"]),
            "official_root_resolved": str(self.roots["official"]),
            "ours_root_requested": str(self.requested_roots["ours"]),
            "ours_root_resolved": str(self.roots["ours"]),
            "evidence_root_preexisted": False,
            "normalization": "NONE",
            "gcc_exec_prefix": str(self.alias / "lib/gcc") + os.sep,
            "subprocess_path": "/usr/bin:/bin",
            "environment_policy": "CLEAN_ALLOWLIST_V1",
            "subprocess_environment_keys": [
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
                "ZERO_AR_DATE"
            ],
        }
        write_json_atomic(self.evidence / "context.json", context)
        write_json_atomic(
            self.evidence / "RUNNING.json",
            {
                "schema": "openwch-xw-lto-running-v1",
                "state": "RUNNING",
                "started_at": context["started_at"],
                "contract_sha256": sha256_bytes(before_contract),
            },
        )

        for lane in self.contract["lanes"]:
            self.run_lane(lane)
        if self.work.exists():
            shutil.rmtree(self.work)

        self.write_ledgers()
        comparison_rows, comparison_failures = self.compare()
        after_contract = suite_manifest_bytes()
        write_bytes_atomic(self.evidence / "contract-files.after.tsv", after_contract)
        before_tools = (self.evidence / "tool-inputs.before.tsv").read_bytes()
        after_tools = tool_manifest_bytes(self.roots)
        write_bytes_atomic(self.evidence / "tool-inputs.after.tsv", after_tools)
        if after_contract != before_contract:
            self.semantic_failures.append("suite contract changed while runner was active")
        if after_tools != before_tools:
            self.semantic_failures.append("tool input changed while runner was active")

        status = "PASS" if not self.semantic_failures and not comparison_failures else "FAIL"
        summary = {
            "schema": "openwch-xw-lto-run-summary-v1",
            "status": status,
            "mode": self.mode,
            "platform": self.platform_name,
            "lane_count": len(self.contract["lanes"]),
            "command_count": len(self.commands),
            "artifact_count": len(self.artifacts),
            "comparison_count": len(comparison_rows),
            "comparison_failure_count": len(comparison_failures),
            "semantic_failure_count": len(self.semantic_failures),
            "semantic_failures": self.semantic_failures,
            "comparison_failures": comparison_failures,
            "contract_sha256": sha256_bytes(before_contract),
            "tool_inputs_stable": after_tools == before_tools,
            "contract_stable": after_contract == before_contract,
            "source_date_epoch": self.contract["source_date_epoch"],
            "normalization": "NONE",
        }
        write_json_atomic(self.evidence / "runner-summary.json", summary)
        complete = {
            "schema": "openwch-xw-lto-run-complete-v1",
            "state": "COMPLETE" if status == "PASS" else "FAILED",
            "status": status,
            "mode": self.mode,
            "platform": self.platform_name,
            "finished_at": utc_now(),
            "runner_summary_sha256": sha256_file(self.evidence / "runner-summary.json"),
            "contract_sha256": summary["contract_sha256"],
            "formal_seal_eligible": status == "PASS" and self.mode == "formal",
        }
        write_json_atomic(self.evidence / "RUN_COMPLETE.json", complete)
        print(json.dumps(summary, sort_keys=True))
        return 0 if status == "PASS" else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", required=True, choices=("darwin-arm64", "linux-amd64"))
    parser.add_argument("--official-root", required=True)
    parser.add_argument("--ours-root", required=True)
    parser.add_argument("--evidence-root", required=True)
    parser.add_argument(
        "--smoke-identical-roots",
        action="store_true",
        help="explicit harness-only mode; can produce only a SMOKE_SEAL",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    evidence: Path | None = None
    try:
        contract = load_contract()
        validate_host(args.platform)
        requested_official, official = validate_root(args.official_root, "official root")
        requested_ours, ours = validate_root(args.ours_root, "ours root")
        expected_official = (REPO / "ref/gcc" / args.platform / "15.2.0").resolve(
            strict=True
        )
        if official != expected_official:
            raise RuntimeError(
                "official root is not the canonical package for the selected platform"
            )
        mode = "smoke-identical-roots" if args.smoke_identical_roots else "formal"
        if mode == "formal" and official == ours:
            raise RuntimeError("formal mode rejects identical resolved official/ours roots")
        if mode == "formal":
            for relative in TOOL_INPUTS:
                if os.path.samestat((official / relative).stat(), (ours / relative).stat()):
                    raise RuntimeError(
                        f"formal tool roots share the same input inode: {relative}"
                    )
        if mode == "smoke-identical-roots" and official != ours:
            raise RuntimeError("smoke-identical-roots mode requires identical resolved roots")
        evidence = validate_evidence_root(args.evidence_root)
        os.mkdir(evidence, 0o755)
        runner = GateRun(
            contract,
            evidence,
            args.platform,
            mode,
            {"official": requested_official, "ours": requested_ours},
            {"official": official, "ours": ours},
        )
        return runner.execute()
    except Exception as error:  # Fail closed and preserve a created attempt.
        if evidence is not None and evidence.is_dir():
            aborted = {
                "schema": "openwch-xw-lto-run-aborted-v1",
                "state": "ABORTED",
                "error_type": type(error).__name__,
                "error": str(error),
                "traceback": traceback.format_exc(),
                "finished_at": utc_now(),
            }
            aborted_path = evidence / "RUN_ABORTED.json"
            if not aborted_path.exists():
                write_json_atomic(aborted_path, aborted)
        print(f"xw-lto runner: FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
