#!/usr/bin/env python3
"""phase-6 S3 full-EVT buildability census with the official 8.2.0 toolchain.

Adapted copy of the sealed phase-3b Stage-A runner
(tmp/phase3b-evidence/stage-a/runner.py, read-only history).  Differences,
all deliberate:

  * canonical side only -- there is no "ours" 8.2.0 compiler yet, so every
    cross-side diff, gate-mismatch ledger and canonical/ours self-check is
    removed.  What remains is a buildability census plus raw artifact hashes.
  * toolchain prefix riscv-none-embed- (target riscv-none-embed), official
    tree ref/gcc/darwin-arm64/8.2.0 (x86_64 binaries, run under Rosetta).
  * converter is invoked with --compiler-path only; --gcc-major is ignored by
    wvproj_to_make.py whenever --compiler-path is given (main(), line 1282f),
    and the path resolves into the versioned ref/gcc tree, so the GCC8 -march
    dialect is selected by the converter itself.
  * failing projects get a serial diagnostic re-run (workers=1, make -j1) when
    the parallel pass produced no compiler/assembler diagnostic, or timed out,
    or hit an internal error.  Classification never rests on -j2 stderr jitter.

Everything else -- enumeration (harness.selected_projects("full")), EVT patch
backup/restore, per-project work path contract, debug-prefix-map neutralisation,
16 workers x make -j2, atomic writes, command ledger -- is kept byte-for-byte in
behaviour so the phase-3b/3d denominator and path contract carry over.
"""

from __future__ import annotations

import concurrent.futures
import csv
import dataclasses
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
if not (REPO / "ref/wch-evt/tools/wvproj_to_make.py").is_file():
    raise SystemExit(f"REPO resolution failed: {REPO}")

MODE = sys.argv[1] if len(sys.argv) > 1 else "full"
if MODE not in {"full", "smoke"}:
    raise SystemExit("usage: census_runner.py [full|smoke]")

EVIDENCE = REPO / "tmp/toolchain_8.2.0/evidence/s3/full-census"
STAGE = EVIDENCE / ("stage-a" if MODE == "full" else "stage-smoke")
WORK = REPO / "tmp/toolchain_8.2.0/full-census"
PROJECTS = WORK / "projects"
EVT = REPO / "ref/wch-evt"
CONVERTER = EVT / "tools/wvproj_to_make.py"
CANONICAL = (REPO / "ref/gcc/darwin-arm64/8.2.0").resolve()
PREFIX = "riscv-none-embed-"
PROMPT = REPO / "tmp/prompts/phase-6.md"
EPOCH = "1767225600"
WORKERS = 16
MAKE_JOBS = 2
CONVERTER_TIMEOUT = 300
BUILD_TIMEOUT = 1800

SMOKE_PROJECTS = (
    "QingkeV3A_CH32V103/EXAM/GPIO/GPIO_Toggle/GPIO_Toggle.wvproj",
    "QingkeV3C_CH587_EVT/EXAM/LED/LED.wvproj",
    "QingkeV3F_CH32X315/EXAM/GPIO/GPIO_Toggle/GPIO_Toggle.wvproj",
)

STOP = threading.Event()
ACTIVE_LOCK = threading.Lock()
ACTIVE: dict[int, subprocess.Popen] = {}
LEDGER_LOCK = threading.Lock()
LEDGER_FILE: Path | None = None
CURRENT_JOBS = MAKE_JOBS


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fsync_file(path: Path) -> None:
    with path.open("rb") as stream:
        os.fsync(stream.fileno())


def fsync_dir(path: Path) -> None:
    try:
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        pass


def atomic_write(path: Path, data: bytes, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(temporary, mode)
    os.replace(temporary, path)
    fsync_dir(path.parent)


def write_text(path: Path, text: str) -> None:
    atomic_write(path, text.encode("utf-8", "surrogateescape"))


def safe_rel(path: Path, base: Path) -> str:
    return os.fsdecode(os.fsencode(path.relative_to(base)))


def path_manifest(root: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    if not root.exists() and not root.is_symlink():
        return rows
    paths: list[Path] = []
    if root.is_symlink() or root.is_file():
        paths = [root]
    else:
        for current, dirs, files in os.walk(root, topdown=True, followlinks=False):
            current_path = Path(current)
            dirs[:] = sorted(dirs, key=lambda x: os.fsencode(x))
            files[:] = sorted(files, key=lambda x: os.fsencode(x))
            for name in dirs + files:
                candidate = current_path / name
                if candidate.is_symlink() or candidate.is_file():
                    paths.append(candidate)
    for path in sorted(paths, key=lambda x: os.fsencode(safe_rel(x, root.parent) if x != root else x.name)):
        relative = safe_rel(path, root) if path != root else "."
        stat = os.lstat(path)
        mode = stat.st_mode & 0o7777
        if os.path.islink(path):
            rows.append({"path": relative, "kind": "symlink", "mode": mode, "link": os.readlink(path)})
        else:
            rows.append({"path": relative, "kind": "file", "mode": mode, "size": stat.st_size, "sha256": sha256_file(path)})
    return rows


def save_manifest(path: Path, rows: list[dict[str, object]]) -> str:
    text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows)
    write_text(path, text)
    return sha256_file(path)


def command_env() -> dict[str, str]:
    return {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "LC_ALL": "C",
        "SOURCE_DATE_EPOCH": EPOCH,
        "TMPDIR": str(WORK / "tmp"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "WVPROJ_WORKERS": str(WORKERS),
        "MAKE_JOBS": str(CURRENT_JOBS),
    }


def record_command(command: list[str], cwd: Path, started: str, ended: str, rc: int, stdout: Path, stderr: Path, timeout: bool = False) -> None:
    if LEDGER_FILE is None:
        return
    with LEDGER_LOCK:
        with LEDGER_FILE.open("a", encoding="utf-8", newline="") as stream:
            csv.writer(stream, delimiter="\t", lineterminator="\n").writerow([
                started, ended, os.fsdecode(os.fsencode(cwd)), json.dumps(command, ensure_ascii=False), rc,
                os.fsdecode(os.fsencode(stdout)), os.fsdecode(os.fsencode(stderr)), "TIMEOUT" if timeout else "",
            ])


def terminate_process(proc: subprocess.Popen) -> None:
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except OSError:
        pass
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            pass
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass


def run_command(command: list[str], cwd: Path, stdout: Path, stderr: Path, timeout: int | None) -> tuple[int, bool]:
    stdout.parent.mkdir(parents=True, exist_ok=True)
    stderr.parent.mkdir(parents=True, exist_ok=True)
    started = now()
    timed_out = False
    stdout_stream = stdout.open("wb")
    stderr_stream = stderr.open("wb")
    proc = subprocess.Popen(command, cwd=str(cwd), env=command_env(), stdout=stdout_stream, stderr=stderr_stream, start_new_session=True)
    with ACTIVE_LOCK:
        ACTIVE[proc.pid] = proc
    try:
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            terminate_process(proc)
        if STOP.is_set() and proc.poll() is None:
            terminate_process(proc)
        rc = proc.returncode if proc.returncode is not None else 124
    finally:
        with ACTIVE_LOCK:
            ACTIVE.pop(proc.pid, None)
        stdout_stream.close()
        stderr_stream.close()
    record_command(command, cwd, started, now(), rc, stdout, stderr, timed_out)
    return rc, timed_out


def copy_if_exists(source: Path, target: Path) -> None:
    if source.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def clear_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for child in list(path.iterdir()):
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()


def atomic_symlink(link: Path, target: Path) -> None:
    temporary = link.with_name(f".{link.name}.{os.getpid()}.linktmp")
    try:
        temporary.unlink()
    except FileNotFoundError:
        pass
    os.symlink(target, temporary)
    os.replace(temporary, link)
    fsync_dir(link.parent)


def tool_path(root: Path, name: str) -> Path:
    return root / "bin" / f"{PREFIX}{name}"


def run_capture(command: list[str], cwd: Path, stem: str) -> dict[str, object]:
    out = STAGE / "identity" / f"{stem}.stdout"
    err = STAGE / "identity" / f"{stem}.stderr"
    rc, timed = run_command(command, cwd, out, err, 300)
    data = out.read_bytes() if out.exists() else b""
    return {"command": command, "returncode": rc, "timeout": timed, "stdout": data.decode("utf-8", "replace"), "stdout_path": str(out), "stderr_path": str(err)}


def tool_identity(root: Path, side: str) -> dict[str, object]:
    gcc = tool_path(root, "gcc")
    if not gcc.is_file():
        raise RuntimeError(f"missing expected GCC: {gcc}")
    tools: dict[str, object] = {"root": str(root), "side": side, "compiler": str(gcc), "target": ""}
    for name in ("gcc", "as", "ld", "objcopy", "objdump"):
        path = tool_path(root, name)
        if not path.is_file() or not os.access(path, os.X_OK):
            raise RuntimeError(f"missing tool {path}")
        tools[name] = {"path": str(path), "sha256": sha256_file(path), "size": path.stat().st_size}
    tools["target"] = run_capture([str(gcc), "-dumpmachine"], REPO, f"{side}-dumpmachine")["stdout"].strip()
    tools["dumpversion"] = run_capture([str(gcc), "-dumpversion"], REPO, f"{side}-dumpversion")["stdout"].strip()
    tools["version"] = run_capture([str(gcc), "--version"], REPO, f"{side}-version")
    tools["arch"] = run_capture(["/usr/bin/file", str(gcc)], REPO, f"{side}-file")["stdout"].strip()
    tools["toolchain_real_root"] = str(root)
    probes: dict[str, object] = {}
    for name in ("cc1", "collect2", "as", "ld"):
        probes[f"prog:{name}"] = run_capture([str(gcc), f"-print-prog-name={name}"], REPO, f"{side}-prog-{name}")
    for name in ("libgcc.a", "libc.a", "crt0.o"):
        probes[f"file:{name}"] = run_capture([str(gcc), f"-print-file-name={name}"], REPO, f"{side}-file-{name}")
    tools["resolution_probes"] = probes
    return tools


def patch_targets() -> list[Path]:
    targets: list[Path] = []
    for patch in sorted((EVT / "patches").glob("*.patch")):
        for line in patch.read_text(encoding="utf-8").splitlines():
            match = re.match(r"diff --git a/(.+) b/", line)
            if match:
                path = EVT / match.group(1)
                if path not in targets:
                    targets.append(path)
    return targets


def backup_target(path: Path, index: int) -> dict[str, object]:
    backup = STAGE / "evt-originals" / f"{index:04d}"
    backup.mkdir(parents=True, exist_ok=True)
    if not path.exists() and not path.is_symlink():
        return {"path": str(path), "kind": "missing", "mode": None, "backup": None}
    stat = os.lstat(path)
    mode = stat.st_mode & 0o7777
    if os.path.islink(path):
        return {"path": str(path), "kind": "symlink", "mode": mode, "link": os.readlink(path), "backup": None}
    destination = backup / "bytes"
    atomic_write(destination, path.read_bytes(), mode)
    return {"path": str(path), "kind": "file", "mode": mode, "size": stat.st_size, "sha256": sha256_file(path), "backup": str(destination)}


def restore_backup(rows: list[dict[str, object]]) -> None:
    for row in rows:
        path = Path(str(row["path"]))
        kind = row["kind"]
        if kind == "missing":
            if path.is_symlink() or path.exists():
                if path.is_dir() and not path.is_symlink():
                    shutil.rmtree(path)
                else:
                    path.unlink()
            continue
        if kind == "symlink":
            if path.exists() or path.is_symlink():
                path.unlink()
            temporary = path.with_name(f".{path.name}.{os.getpid()}.restore")
            os.symlink(str(row["link"]), temporary)
            os.replace(temporary, path)
            continue
        data = Path(str(row["backup"])).read_bytes()
        temporary = path.with_name(f".{path.name}.{os.getpid()}.restore")
        atomic_write(temporary, data, int(row["mode"]))
        os.replace(temporary, path)
    fsync_dir(EVT)


def write_harness(path: Path) -> None:
    write_text(path, "override CFLAGS += -fdebug-prefix-map=$(DEBUG_PREFIX_FROM)=$(DEBUG_PREFIX_TO)\noverride ASFLAGS += -fdebug-prefix-map=$(DEBUG_PREFIX_FROM)=$(DEBUG_PREFIX_TO)\n")


def rel_files(root: Path) -> list[str]:
    if not root.is_dir():
        return []
    return sorted((path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()), key=lambda x: os.fsencode(x))


def artifact_info(side_root: Path) -> dict[str, dict[str, object]]:
    obj = side_root / "obj"
    result: dict[str, dict[str, object]] = {}
    for name in rel_files(obj):
        path = obj / name
        cls = "gate" if name.endswith((".o", ".elf", ".bin")) else "aux"
        result[name] = {"class": cls, "size": path.stat().st_size, "sha256": sha256_file(path), "path": f"obj/{name}"}
    return result


MAKE_NOISE = re.compile(r"^(?:make|gmake)(\[\d+\])?:")
ERROR_TOKENS = (
    "error:", "Error:", "fatal error", "undefined reference", "cannot find",
    "No such file or directory", "No rule to make target", "unrecognized",
    "unsupported", "illegal", "Assembler messages", "internal compiler error",
    "collect2:", "Assembler message:",
)
WARNING_TOKENS = ("warning:", "Warning:")


def extract_diagnostics(paths: list[Path], limit: int = 40) -> tuple[str, str, int]:
    """Return (first_error_line, first_line_of_any_kind, error_line_count).

    Only compiler/assembler/linker error lines count.  ``make`` wrapper noise
    ("*** Waiting for unfinished jobs") and warnings never become the first
    diagnostic, because the classification keys on this field and a wrapper
    line carries no information about why 8.2.0 refused the project.
    """
    errors: list[str] = []
    warnings: list[str] = []
    fallback = ""
    for path in paths:
        if not path.is_file():
            continue
        try:
            data = path.read_bytes()[: 4 * 1024 * 1024]
        except OSError:
            continue
        for raw in data.decode("utf-8", "replace").splitlines():
            line = raw.strip().replace("\t", " ")
            if not line:
                continue
            if not fallback:
                fallback = line
            if MAKE_NOISE.match(line):
                continue
            if line.endswith(("Assembler messages:", "Assembler message:")):
                # gas prints a per-file banner before the real diagnostic; it
                # names the file, never the reason.
                continue
            if any(token in line for token in ERROR_TOKENS):
                if line not in errors:
                    errors.append(line)
                if len(errors) >= limit:
                    break
            elif any(token in line for token in WARNING_TOKENS) and line not in warnings:
                warnings.append(line)
    first = errors[0] if errors else (warnings[0] if warnings else "")
    return first, fallback, len(errors)


@dataclasses.dataclass
class SideResult:
    conversion: str = "NOT-RUN"
    build: str = "NOT-RUN"
    bin_status: str = "NOT-RUN"
    reason: str = ""
    elapsed: float = 0.0
    config: Path | None = None
    makefile: Path | None = None
    obj: Path | None = None
    artifacts: dict[str, dict[str, object]] = dataclasses.field(default_factory=dict)
    first_diagnostic: str = ""
    fallback_line: str = ""
    diagnostic_count: int = 0
    log_dir: str = ""


def build_side(index: int, project: Path, project_root: Path, side: str, toolchain: Path, jobs: int) -> SideResult:
    result = SideResult()
    started = time.monotonic()
    side_root = project_root / side
    work = project_root / "work"
    neutral = project_root / "toolchain-current"
    logs = project_root / "logs"
    compiler = neutral / "bin" / f"{PREFIX}gcc"
    objcopy = neutral / "bin" / f"{PREFIX}objcopy"
    result.log_dir = str(logs)
    clear_directory(work)
    clear_directory(side_root)
    atomic_symlink(neutral, toolchain)
    convert_out = logs / f"{side}-convert.stdout"
    convert_err = logs / f"{side}-convert.stderr"
    command = ["python3", "-B", str(CONVERTER), str(project), "--output", str(work), "--compiler-path", str(compiler), "--quiet"]
    rc, timed = run_command(command, REPO, convert_out, convert_err, CONVERTER_TIMEOUT)
    if timed:
        result.conversion = "TIMEOUT"
        result.reason = "converter timeout"
    elif rc != 0:
        result.conversion = "FAIL"
        result.reason = "converter exit %d" % rc
    else:
        result.conversion = "PASS"
    if (work / "config.json").is_file():
        copy_if_exists(work / "config.json", side_root / "config.json")
        copy_if_exists(work / "Makefile", side_root / "Makefile")
        result.config, result.makefile = side_root / "config.json", side_root / "Makefile"
    if result.conversion != "PASS" or STOP.is_set():
        result.build = "NOT-RUN" if STOP.is_set() else "FAIL"
        result.bin_status = "NOT-RUN" if STOP.is_set() else "FAIL"
        result.first_diagnostic, result.fallback_line, result.diagnostic_count = extract_diagnostics([convert_err, convert_out])
        result.elapsed = time.monotonic() - started
        return result
    write_harness(work / "harness.mk")
    copy_if_exists(work / "harness.mk", side_root / "harness.mk")
    build_out = logs / f"{side}-build.stdout"
    build_err = logs / f"{side}-build.stderr"
    command = [
        "make", "-f", "Makefile", "-f", "harness.mk", f"-j{jobs}",
        "COMPILER_PATH=" + str(compiler),
        "TOOLCHAIN_BIN=" + str(neutral / "bin"),
        "CROSS_PREFIX=" + PREFIX,
        "DEBUG_PREFIX_FROM=" + str(toolchain),
        "DEBUG_PREFIX_TO=" + str(neutral),
        "all",
    ]
    rc, timed = run_command(command, work, build_out, build_err, BUILD_TIMEOUT)
    if timed:
        result.build = "TIMEOUT"
        result.reason = "build timeout"
    elif rc != 0:
        result.build = "FAIL"
        result.reason = "build exit %d" % rc
    else:
        result.build = "PASS"
    if result.build == "PASS":
        elfs = sorted((work / "obj").glob("*.elf")) if (work / "obj").is_dir() else []
        if len(elfs) != 1:
            result.build = "FAIL"
            result.bin_status = "FAIL"
            result.reason = "expected exactly one ELF, observed %d" % len(elfs)
        else:
            elf = elfs[0]
            bin_path = elf.with_suffix(".bin")
            rc, timed = run_command([str(objcopy), "-O", "binary", str(elf), str(bin_path)], work, logs / f"{side}-objcopy.stdout", logs / f"{side}-objcopy.stderr", 300)
            if timed:
                result.bin_status = "TIMEOUT"
                result.reason = "objcopy timeout"
            elif rc != 0:
                result.bin_status = "FAIL"
                result.reason = "objcopy exit %d" % rc
            else:
                result.bin_status = "PASS"
    else:
        result.bin_status = "NOT-RUN"
    if (work / "obj").is_dir():
        os.replace(work / "obj", side_root / "obj")
        result.obj = side_root / "obj"
        result.artifacts = artifact_info(side_root)
    if not (result.conversion == result.build == result.bin_status == "PASS"):
        result.first_diagnostic, result.fallback_line, result.diagnostic_count = extract_diagnostics([build_err, build_out, convert_err])
    result.elapsed = time.monotonic() - started
    return result


def config_fields(config: Path | None, makefile: Path | None) -> dict[str, str]:
    unknown = {key: "UNKNOWN" for key in ("metadata_format", "native_major", "march", "abi", "optimization", "debug_flags", "encrypted_fallback", "selected_version")}
    if config is None or not config.exists():
        return unknown
    try:
        data = json.loads(config.read_text(encoding="utf-8"))
        flags = data.get("resolved_flags", {})
        opt = data.get("optimization", {})
        debug = data.get("debugging", {})
        make_text = makefile.read_text(encoding="utf-8") if makefile and makefile.exists() else ""
        debug_flags = ",".join(re.findall(r"(?:TARGET_FLAGS|CPPFLAGS|CFLAGS|ASFLAGS)\s*:=([^\n]*)", make_text))
        return {
            "metadata_format": str(data.get("format", "UNKNOWN")),
            "native_major": str(data.get("toolchain_major", "UNKNOWN")),
            "march": str((flags.get("march") or ["UNKNOWN"])[0]),
            "abi": str((flags.get("abi") or ["UNKNOWN"])[0]),
            "optimization": str(opt.get("level", "UNKNOWN")),
            "debug_flags": debug_flags or str(debug.get("debug_level", "none")),
            "encrypted_fallback": "yes" if data.get("encrypted_wvproj") else "no",
            "selected_version": str((data.get("toolchain") or {}).get("version", "UNKNOWN")),
        }
    except (OSError, ValueError, TypeError, KeyError):
        return unknown


def project_dir_for(index: int, project: Path) -> Path:
    project_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", project.relative_to(EVT).as_posix()).strip("_")
    return PROJECTS / f"{index:04d}-{project_id}"


def run_project(index: int, project: Path, jobs: int) -> tuple[list[str], list[list[str]], dict[str, str]]:
    project_root = project_dir_for(index, project)
    project_root.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    result = build_side(index, project, project_root, "canonical", CANONICAL, jobs)
    status = "PASS" if result.conversion == result.build == result.bin_status == "PASS" else "FAIL"
    relative = project.relative_to(EVT).as_posix()
    summary = [
        str(index), project.relative_to(EVT).parts[0], relative,
        result.conversion, result.build, result.bin_status, status, result.reason,
        result.first_diagnostic[:512], result.fallback_line[:512], str(result.diagnostic_count),
        str(len([1 for info in result.artifacts.values() if info["class"] == "gate"])),
        "%.3f" % (time.monotonic() - started), str(jobs),
        str(project_root.relative_to(WORK)),
    ]
    rows: list[list[str]] = []
    if status == "PASS":
        for name in sorted(result.artifacts, key=lambda x: os.fsencode(x)):
            info = result.artifacts[name]
            rows.append([str(index), relative, f"obj/{name}", str(info["class"]), str(info["size"]), str(info["sha256"])])
    inventory = config_fields(result.config, result.makefile)
    return summary, rows, inventory


def write_tsv(path: Path, header: list[str], rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)
    fsync_file(path)


def signal_handler(signum: int, _frame: object) -> None:
    STOP.set()
    with ACTIVE_LOCK:
        processes = list(ACTIVE.values())
    for proc in processes:
        terminate_process(proc)


SUMMARY_HEADER = [
    "index", "evt_root", "project", "conversion", "build", "bin", "status", "reason",
    "first_diagnostic", "fallback_line", "diagnostic_count", "gate_artifacts",
    "elapsed_s", "make_jobs", "evidence",
]
INVENTORY_HEADER = [
    "index", "evt_root", "project_dir", "project_name", "wvproj", "cproject",
    "metadata_format", "native_major", "selected_version", "march", "abi",
    "optimization", "debug_flags", "encrypted_fallback",
]


def looks_debuggable(path: Path) -> bool:
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8", errors="ignore")
    return bool(re.search(r'superClass="[^"]*debugging\.level"[^>]*value="[^"]*\.(?!default|none)[^"]+"', text))


def determinism_selfcheck(projects: list[Path]) -> dict[str, object]:
    """Two raw builds of the same project at the same path must hash identically.

    Mirrors the phase-3b runner's canonical/canonical self-check.  The
    canonical/ours half of that self-check has no 8.2.0 counterpart yet and is
    dropped.  A second pair is run on the first enumerated project so both a
    debug-enabled and a debug-free project are covered.
    """
    root = STAGE / "selfcheck"
    root.mkdir(parents=True, exist_ok=True)
    outcome: dict[str, object] = {"pairs": [], "verdict": "UNVERIFIED"}
    debug_candidates = [p for p in projects if looks_debuggable(p.parent / ".cproject")][:8]
    plan = [("debug", debug_candidates), ("first", [projects[0]])]
    verdicts: list[bool] = []
    for label, candidates in plan:
        for candidate in candidates:
            pair_root = root / label
            clear_directory(pair_root)
            first = build_side(0, candidate, pair_root, "run1", CANONICAL, MAKE_JOBS)
            if first.build != "PASS":
                outcome["pairs"].append({"label": label, "project": candidate.relative_to(EVT).as_posix(), "state": "SKIPPED-BUILD-FAIL", "reason": first.reason, "first_diagnostic": first.first_diagnostic})
                continue
            second = build_side(0, candidate, pair_root, "run2", CANONICAL, MAKE_JOBS)
            same = first.artifacts.keys() == second.artifacts.keys() and all(first.artifacts[k]["sha256"] == second.artifacts[k]["sha256"] for k in first.artifacts)
            outcome["pairs"].append({
                "label": label, "project": candidate.relative_to(EVT).as_posix(), "state": "COMPARED",
                "artifacts": len(first.artifacts), "identical": same,
                "run1": {k: v["sha256"] for k, v in sorted(first.artifacts.items())},
                "run2": {k: v["sha256"] for k, v in sorted(second.artifacts.items())},
            })
            verdicts.append(same)
            break
    outcome["verdict"] = "PASS" if verdicts and all(verdicts) else ("FAIL" if verdicts else "UNVERIFIED")
    write_text(root / "result.json", json.dumps(outcome, ensure_ascii=False, indent=2))
    return outcome


def main() -> int:
    global LEDGER_FILE, CURRENT_JOBS
    os.umask(0o022)
    STAGE.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    PROJECTS.mkdir(parents=True, exist_ok=True)
    (WORK / "tmp").mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ") + "-" + str(os.getpid())
    write_text(STAGE / "run-id.txt", run_id + "\n")
    LEDGER_FILE = STAGE / "command-ledger.tsv"
    write_tsv(LEDGER_FILE, ["started_utc", "ended_utc", "cwd", "command_json", "returncode", "stdout", "stderr", "timeout"], [])
    atomic_write(STAGE / "inherited-environment.txt", "".join(f"{key}={value}\n" for key, value in sorted(os.environ.items())).encode("utf-8", "surrogateescape"))
    prompt_sha = sha256_file(PROMPT) if PROMPT.is_file() else "MISSING"

    identity = tool_identity(CANONICAL, "canonical")
    write_text(STAGE / "identity/toolchains.json", json.dumps({"canonical": identity}, ensure_ascii=False, indent=2))

    pre_evt = path_manifest(EVT)
    pre_evt_hash = save_manifest(STAGE / "evt-pre-state.jsonl", pre_evt)
    immutable = [REPO / "patches", CONVERTER, EVT / "tests/test_wvproj_to_make.py", EVT / "patches", EVT / "README.md"]
    immutable_pre = {
        str(p.relative_to(REPO)): save_manifest(STAGE / "state" / (re.sub(r"[^A-Za-z0-9_.-]+", "_", str(p.relative_to(REPO))) + "-pre.jsonl"), path_manifest(p))
        if p.is_dir() else sha256_file(p) if p.is_file() else "MISSING"
        for p in immutable
    }

    targets = patch_targets()
    allowlist = ["0001-pmp-select-ch32v20x-d8w.patch", "0002-fix-eight-wvproj-builds.patch", "apply.sh"]
    patch_files = sorted((EVT / "patches").iterdir())
    if [p.name for p in patch_files] != allowlist or not all(p.is_file() for p in patch_files):
        raise RuntimeError("EVT patch allowlist mismatch")
    backups = [backup_target(path, i) for i, path in enumerate(targets, 1)]
    atomic_write(STAGE / "evt-originals/manifest.json", json.dumps(backups, ensure_ascii=False, indent=2).encode("utf-8"))

    from importlib.util import module_from_spec, spec_from_file_location
    spec = spec_from_file_location("wvproj_test_harness", EVT / "tests/test_wvproj_to_make.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load existing EVT harness")
    harness = module_from_spec(spec)
    sys.modules[spec.name] = harness
    spec.loader.exec_module(harness)
    applied_originals = harness.apply_test_patches()
    if set(applied_originals) != set(targets):
        raise RuntimeError("harness patch targets differ from verified allowlist")
    all_projects = harness.selected_projects("full")
    if not all_projects:
        raise RuntimeError("full inventory is empty")
    write_text(STAGE / "inventory-discovery.txt", "\n".join(f"{i}\t{p.relative_to(EVT).as_posix()}" for i, p in enumerate(all_projects, 1)) + "\n")

    indexed = list(enumerate(all_projects, 1))
    if MODE == "smoke":
        wanted = set(SMOKE_PROJECTS)
        indexed = [(i, p) for i, p in indexed if p.relative_to(EVT).as_posix() in wanted]
        if len(indexed) != len(wanted):
            raise RuntimeError(f"smoke selection resolved {len(indexed)} of {len(wanted)} projects")

    selfcheck = determinism_selfcheck([p for _, p in indexed] if MODE == "smoke" else all_projects)

    results: dict[int, list[str]] = {}
    artifacts: dict[int, list[list[str]]] = {}
    inventory: dict[int, dict[str, str]] = {}
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    started_all = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = {executor.submit(run_project, i, p, MAKE_JOBS): (i, p) for i, p in indexed}
        for number, future in enumerate(concurrent.futures.as_completed(futures), 1):
            index, project = futures[future]
            try:
                summary, rows, fields = future.result()
            except Exception as exc:
                root = project_dir_for(index, project)
                root.mkdir(parents=True, exist_ok=True)
                write_text(root / "runner-exception.txt", traceback.format_exc())
                summary = [str(index), project.relative_to(EVT).parts[0], project.relative_to(EVT).as_posix(), "ERROR", "ERROR", "ERROR", "FAIL", repr(exc)[:512], "", "", "0", "0", "0.000", str(MAKE_JOBS), str(root.relative_to(WORK))]
                rows, fields = [], config_fields(None, None)
            results[index] = summary
            artifacts[index] = rows
            inventory[index] = fields
            if number % 25 == 0 or number == len(indexed):
                print(f"progress {number}/{len(indexed)} elapsed={time.monotonic() - started_all:.0f}s", flush=True)
            if STOP.is_set():
                break

    # Serial diagnostic re-run: any failure without a usable compiler/assembler
    # diagnostic, plus every TIMEOUT/ERROR, is rebuilt alone with make -j1 so a
    # classification never rests on -j2 interleaving or host contention.
    retry_indices = [
        index for index, row in sorted(results.items())
        if row[6] != "PASS" and (row[10] == "0" or "TIMEOUT" in (row[3], row[4], row[5]) or "ERROR" in (row[3], row[4], row[5]))
    ]
    retry_log: list[dict[str, object]] = []
    if retry_indices and not STOP.is_set():
        print(f"serial-retry {len(retry_indices)} projects", flush=True)
        CURRENT_JOBS = 1
        by_index = dict(indexed)
        for number, index in enumerate(retry_indices, 1):
            project = by_index[index]
            before = list(results[index])
            try:
                summary, rows, fields = run_project(index, project, 1)
            except Exception as exc:
                retry_log.append({"index": index, "project": project.relative_to(EVT).as_posix(), "state": "RETRY-EXCEPTION", "error": repr(exc)})
                continue
            results[index] = summary
            artifacts[index] = rows
            inventory[index] = fields
            retry_log.append({
                "index": index, "project": project.relative_to(EVT).as_posix(), "state": "RETRIED",
                "before": {"status": before[6], "conversion": before[3], "build": before[4], "bin": before[5], "diagnostics": before[10], "first": before[8]},
                "after": {"status": summary[6], "conversion": summary[3], "build": summary[4], "bin": summary[5], "diagnostics": summary[10], "first": summary[8]},
            })
            if number % 10 == 0 or number == len(retry_indices):
                print(f"serial-retry {number}/{len(retry_indices)}", flush=True)
            if STOP.is_set():
                break
        CURRENT_JOBS = MAKE_JOBS
    write_text(STAGE / "serial-retry.json", json.dumps(retry_log, ensure_ascii=False, indent=2))

    result_rows = [results[i] for i in sorted(results)]
    artifact_rows = [row for i in sorted(artifacts) for row in artifacts[i]]
    write_tsv(STAGE / "project-results.tsv", SUMMARY_HEADER, result_rows)
    write_tsv(STAGE / "artifact-results.tsv", ["index", "project", "artifact", "class", "size", "sha256"], artifact_rows)
    inv_rows = []
    for index, project in indexed:
        fields = inventory.get(index, config_fields(None, None))
        project_dir = project.parent
        inv_rows.append([
            str(index), project.relative_to(EVT).parts[0], project_dir.relative_to(EVT).as_posix(), project_dir.name,
            project.relative_to(EVT).as_posix(),
            (project_dir / ".cproject").relative_to(EVT).as_posix() if (project_dir / ".cproject").exists() else "",
            fields["metadata_format"], fields["native_major"], fields["selected_version"], fields["march"], fields["abi"],
            fields["optimization"], fields["debug_flags"], fields["encrypted_fallback"],
        ])
    write_tsv(STAGE / "effective-project-inventory.tsv", INVENTORY_HEADER, inv_rows)

    post_evt = path_manifest(EVT)
    post_evt_hash = save_manifest(STAGE / "evt-post-state.jsonl", post_evt)
    restore_backup(backups)
    restored_evt = path_manifest(EVT)
    restored_hash = save_manifest(STAGE / "evt-restored-state.jsonl", restored_evt)
    evt_exact = restored_evt == pre_evt
    immutable_post = {
        str(p.relative_to(REPO)): save_manifest(STAGE / "state" / (re.sub(r"[^A-Za-z0-9_.-]+", "_", str(p.relative_to(REPO))) + "-post.jsonl"), path_manifest(p))
        if p.is_dir() else sha256_file(p) if p.is_file() else "MISSING"
        for p in immutable
    }

    passed = sum(1 for row in result_rows if row[6] == "PASS")
    summary = {
        "schema": "phase6-s3-full-census-v1",
        "mode": MODE,
        "run_id": run_id,
        "state": "COLLECTED",
        "prompt_sha256": prompt_sha,
        "project_total": len(indexed),
        "enumeration_total": len(all_projects),
        "projects_completed": len(result_rows),
        "projects_pass": passed,
        "projects_fail": len(result_rows) - passed,
        "gate_artifacts": len(artifact_rows),
        "canonical_root": str(CANONICAL),
        "toolchain_identity": {name: identity[name] for name in ("gcc", "as", "ld", "objcopy", "objdump")},
        "toolchain_target": identity["target"],
        "toolchain_version": identity["version"]["stdout"].splitlines()[0] if identity["version"]["stdout"] else "",
        "toolchain_arch": identity["arch"],
        "work_root": str(WORK.relative_to(REPO)),
        "path_contract": "work_root/projects/{index:04d}-{sanitised-project}/work (cwd) with sibling canonical/, logs/, toolchain-current -> canonical root",
        "debug_prefix_map": f"{CANONICAL}=>{{project_root}}/toolchain-current",
        "converter_invocation": "python3 -B tools/wvproj_to_make.py <wvproj> --output <work> --compiler-path <project_root>/toolchain-current/bin/riscv-none-embed-gcc --quiet",
        "inventory_hash": sha256_file(STAGE / "effective-project-inventory.tsv"),
        "project_results_hash": sha256_file(STAGE / "project-results.tsv"),
        "artifact_results_hash": sha256_file(STAGE / "artifact-results.tsv"),
        "evt_pre_hash": pre_evt_hash,
        "evt_post_hash": post_evt_hash,
        "evt_restored_hash": restored_hash,
        "evt_exact_restored": evt_exact,
        "stop_requested": STOP.is_set(),
        "selfcheck": selfcheck,
        "serial_retry_count": len(retry_log),
        "immutable_pre": immutable_pre,
        "immutable_post": immutable_post,
        "source_date_epoch": EPOCH,
        "workers": WORKERS,
        "make_jobs": MAKE_JOBS,
        "elapsed_s": round(time.monotonic() - started_all, 3),
    }
    atomic_write(STAGE / "summary.json", json.dumps(summary, ensure_ascii=False, indent=2).encode("utf-8"))

    ledger_files = [p for p in STAGE.rglob("*") if p.is_file() and p.name != "STAGE_COMPLETE.json" and "selfcheck" not in p.relative_to(STAGE).parts]
    ledger_hashes = {str(p.relative_to(STAGE)): sha256_file(p) for p in sorted(ledger_files, key=lambda p: os.fsencode(str(p.relative_to(STAGE))))}
    marker = {
        "schema": "phase6-s3-full-census-complete-v1",
        "run_id": run_id,
        "mode": MODE,
        "state": "COLLECTED",
        "sealed_at_utc": now(),
        "input_hashes": {
            "evt_pre_manifest": pre_evt_hash,
            "evt_post_manifest": post_evt_hash,
            "evt_restored_manifest": restored_hash,
            "inventory": summary["inventory_hash"],
            "patch_allowlist": sha256_bytes("\n".join(f"{p.name}\t{sha256_file(p)}" for p in patch_files).encode()),
            "canonical_root": str(CANONICAL),
            "converter": sha256_file(CONVERTER),
            "runner": sha256_file(Path(__file__).resolve()),
        },
        "ledger_hashes": ledger_hashes,
        "summary_hash": sha256_file(STAGE / "summary.json"),
        "evt_exact_restored": evt_exact,
        "project_total": len(indexed),
        "projects_pass": passed,
    }
    atomic_write(STAGE / "STAGE_COMPLETE.json", json.dumps(marker, ensure_ascii=False, indent=2).encode("utf-8"))
    fsync_dir(STAGE)
    print(f"CENSUS_DONE mode={MODE} total={len(indexed)} pass={passed} fail={len(result_rows) - passed} evt_exact={evt_exact}", flush=True)
    return 0 if evt_exact and len(result_rows) == len(indexed) else 1


if __name__ == "__main__":
    raise SystemExit(main())
