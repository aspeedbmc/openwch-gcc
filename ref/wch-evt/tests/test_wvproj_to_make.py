#!/usr/bin/env python3
"""Build the README smoke projects, or every EVT ``.wvproj`` project.

The test deliberately builds into a temporary directory.  The EVT tree is
only changed transiently while the repository patches are applied; the exact
bytes captured before the test are restored before it exits.

Set ``MODE=fast`` (the default) to build the projects listed in README.md.
Set ``MODE=full`` to build every ``Qingke*/EXAM/**/*.wvproj`` project.
``COMPILER_PATH`` may point at an explicit WCH GCC executable.  The workflow
uses that variable so the same test can run with a downloaded Linux compiler
or with a compiler mounted into an ``act`` container.
"""

from __future__ import annotations

import concurrent.futures
import dataclasses
import json
import os
import platform as host_platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
CONVERTER = ROOT / "tools" / "wvproj_to_make.py"
PATCH_DIR = ROOT / "patches"


@dataclasses.dataclass(frozen=True)
class BuildResult:
    index: int
    project: Path
    passed: bool
    elapsed: float
    detail: str = ""


def command_output(result: subprocess.CompletedProcess[str]) -> str:
    output = "\n".join(part for part in (result.stdout, result.stderr) if part)
    return output[-6000:] if output else "(no command output)"


def run_command(
    command: list[str],
    *,
    cwd: Path = ROOT,
    timeout: int | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )


def readme_projects() -> list[Path]:
    """Read the project-directory column from README's representative table."""

    text = README.read_text(encoding="utf-8")
    try:
        table = text.split("下面每个 EVT 根目录至少选择一个项目。", 1)[1]
        table = table.split("### 编译和验证口径", 1)[0]
    except IndexError as exc:
        raise RuntimeError("README representative-project table markers are missing") from exc

    projects: list[Path] = []
    for line in table.splitlines():
        if not line.startswith("|") or line.lstrip().startswith("|---"):
            continue
        match = re.search(r"`(\./Qingke[^`]+)`", line)
        if match:
            projects.append(Path(match.group(1)[2:]))
    if not projects:
        raise RuntimeError("README representative-project table is empty")
    return projects


def project_file(project_dir: Path) -> Path:
    candidates = sorted(project_dir.glob("*.wvproj"))
    if len(candidates) != 1:
        names = ", ".join(str(path) for path in candidates) or "none"
        raise RuntimeError(f"expected one .wvproj under {project_dir}, found {names}")
    return candidates[0]


def selected_projects(mode: str) -> list[Path]:
    readme_dirs = readme_projects()
    readme_roots = {path.parts[0] for path in readme_dirs}
    evt_roots = {path.name for path in ROOT.glob("Qingke*") if path.is_dir()}
    if readme_roots != evt_roots:
        missing = ", ".join(sorted(evt_roots - readme_roots)) or "none"
        extra = ", ".join(sorted(readme_roots - evt_roots)) or "none"
        raise RuntimeError(f"README coverage differs from EVT roots (missing={missing}; extra={extra})")

    if mode == "fast":
        files = [project_file(ROOT / project_dir) for project_dir in readme_dirs]
    elif mode == "full":
        files = sorted(ROOT.glob("Qingke*/EXAM/**/*.wvproj"))
    else:
        raise RuntimeError(f"MODE must be fast or full, got {mode!r}")

    if not files:
        raise RuntimeError(f"no .wvproj projects found for MODE={mode}")
    selected_roots = {path.relative_to(ROOT).parts[0] for path in files}
    if selected_roots != evt_roots:
        raise RuntimeError(f"{mode} mode does not cover every EVT root")
    return files


def compiler_candidates() -> list[Path]:
    candidates: list[Path] = []
    explicit = os.environ.get("COMPILER_PATH")
    if explicit:
        candidates.append(Path(explicit).expanduser())

    toolchain_bin = os.environ.get("WCH_TOOLCHAIN_BIN")
    if toolchain_bin:
        root = Path(toolchain_bin).expanduser()
        if root.name.endswith("gcc"):
            candidates.append(root)
        else:
            candidates.extend(
                root / name
                for name in (
                    "riscv32-wch-elf-gcc",
                    "riscv-wch-elf-gcc",
                    "riscv-none-embed-gcc",
                    "riscv-none-elf-gcc",
                )
            )

    gcc_root_value = os.environ.get("WCH_GCC_ROOT")
    gcc_root = Path(gcc_root_value).expanduser() if gcc_root_value else ROOT.parent / "gcc"
    if gcc_root.is_dir():
        system = host_platform.system().lower()
        machine = host_platform.machine().lower()
        preferred = "darwin-arm64" if system == "darwin" and machine in {"arm64", "aarch64"} else "linux-amd64"
        platform_dirs = [gcc_root / preferred]
        platform_dirs.extend(path for path in sorted(gcc_root.iterdir()) if path.is_dir() and path not in platform_dirs)
        for platform_dir in platform_dirs:
            versions = sorted((path for path in platform_dir.iterdir() if path.is_dir()), reverse=True)
            for version in versions:
                candidates.extend(
                    version / "bin" / name
                    for name in (
                        "riscv32-wch-elf-gcc",
                        "riscv-wch-elf-gcc",
                        "riscv-none-embed-gcc",
                        "riscv-none-elf-gcc",
                    )
                )
    return candidates


def resolve_compiler() -> Path:
    candidates = compiler_candidates()
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate.resolve()
    rendered = "\n  ".join(str(path) for path in candidates) or "(no candidates)"
    raise RuntimeError(
        "no executable WCH GCC found; set COMPILER_PATH or WCH_TOOLCHAIN_BIN. "
        f"Candidates:\n  {rendered}"
    )


def verify_compiler(compiler: Path) -> str:
    version = run_command([str(compiler), "--version"])
    if version.returncode != 0:
        raise RuntimeError(f"cannot run compiler {compiler}:\n{command_output(version)}")
    machine = run_command([str(compiler), "-dumpmachine"])
    if machine.returncode != 0 or machine.stdout.strip() != "riscv32-wch-elf":
        raise RuntimeError(
            f"unexpected compiler target for {compiler}: {machine.stdout.strip()!r}\n"
            f"{command_output(machine)}"
        )
    return version.stdout.splitlines()[0]


def patch_targets(patch_files: list[Path]) -> list[Path]:
    targets: list[Path] = []
    for patch_file in patch_files:
        for line in patch_file.read_text(encoding="utf-8").splitlines():
            match = re.match(r"diff --git a/(.+) b/", line)
            if match:
                target = ROOT / match.group(1)
                if target not in targets:
                    targets.append(target)
    return targets


def restore_files(originals: dict[Path, bytes]) -> None:
    for path, content in originals.items():
        path.write_bytes(content)


def apply_test_patches() -> dict[Path, bytes]:
    patch_files = sorted(PATCH_DIR.glob("*.patch"))
    if not patch_files:
        return {}
    originals = {target: target.read_bytes() for target in patch_targets(patch_files)}
    result = run_command([str(PATCH_DIR / "apply.sh")])
    if result.returncode != 0:
        restore_files(originals)
        raise RuntimeError(f"could not apply EVT patches:\n{command_output(result)}")
    return originals


def build_one(index: int, project: Path, compiler: Path, output_root: Path, make_jobs: int) -> BuildResult:
    started = time.monotonic()
    output = output_root / f"{index:04d}"
    relative_project = project.relative_to(ROOT)
    try:
        converted = run_command(
            [
                sys.executable,
                str(CONVERTER),
                str(project),
                "--compiler-path",
                str(compiler),
                "--output",
                str(output),
                "--quiet",
            ]
        )
        if converted.returncode != 0:
            return BuildResult(index, relative_project, False, time.monotonic() - started, f"conversion failed:\n{command_output(converted)}")

        manifest_path = output / "config.json"
        makefile_path = output / "Makefile"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        selected = Path(manifest["toolchain"]["compiler"]).resolve()
        if not manifest["toolchain"].get("explicit_compiler") or selected != compiler:
            return BuildResult(
                index,
                relative_project,
                False,
                time.monotonic() - started,
                f"explicit compiler was not preserved (manifest={selected}, expected={compiler})",
            )
        makefile = makefile_path.read_text(encoding="utf-8")
        if f"COMPILER_PATH ?= {compiler}" not in makefile or "CC := $(COMPILER_PATH)" not in makefile:
            return BuildResult(index, relative_project, False, time.monotonic() - started, "generated Makefile does not use explicit COMPILER_PATH")

        built = run_command(["make", "-C", str(output), f"-j{make_jobs}", "all"])
        if built.returncode != 0:
            return BuildResult(index, relative_project, False, time.monotonic() - started, f"build failed:\n{command_output(built)}")
        elf_files = sorted((output / "obj").glob("*.elf"))
        if not elf_files:
            return BuildResult(index, relative_project, False, time.monotonic() - started, "build completed without an ELF output")

        cleaned = run_command(["make", "-C", str(output), "clean"])
        if cleaned.returncode != 0:
            return BuildResult(index, relative_project, False, time.monotonic() - started, f"clean failed:\n{command_output(cleaned)}")
        if (output / "obj").exists() or list(output.rglob("*.elf")):
            return BuildResult(index, relative_project, False, time.monotonic() - started, "clean left generated obj/ or ELF files")
        return BuildResult(index, relative_project, True, time.monotonic() - started)
    except (OSError, UnicodeError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        return BuildResult(index, relative_project, False, time.monotonic() - started, f"test harness error: {exc}")


def run_builds(projects: list[Path], compiler: Path, mode: str) -> int:
    try:
        make_jobs = int(os.environ.get("MAKE_JOBS", "2"))
        workers = int(os.environ.get("WVPROJ_WORKERS", "2"))
    except ValueError as exc:
        raise RuntimeError("MAKE_JOBS and WVPROJ_WORKERS must be positive integers") from exc
    if make_jobs < 1 or workers < 1:
        raise RuntimeError("MAKE_JOBS and WVPROJ_WORKERS must be positive integers")

    with tempfile.TemporaryDirectory(prefix=f"wch-evt-{mode}-") as temporary:
        output_root = Path(temporary)
        results: list[BuildResult] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(build_one, index, project, compiler, output_root, make_jobs): (index, project)
                for index, project in enumerate(projects, 1)
            }
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                results.append(result)
                status = "PASS" if result.passed else "FAIL"
                print(f"[{result.index:04d}/{len(projects):04d}] {status} {result.project} ({result.elapsed:.1f}s)", flush=True)

        failures = sorted((result for result in results if not result.passed), key=lambda result: result.index)
        if failures:
            print("\nFailure details:", file=sys.stderr)
            for result in failures:
                print(f"\n[{result.index:04d}] {result.project}\n{result.detail}", file=sys.stderr)
            return 1
    print(f"MODE={mode}: {len(projects)} projects built and cleaned successfully")
    return 0


def main() -> int:
    mode = os.environ.get("MODE", "fast").strip().lower()
    if mode not in {"fast", "full"}:
        print(f"test_wvproj_to_make.py: MODE must be fast or full, got {mode!r}", file=sys.stderr)
        return 2
    for required in (CONVERTER, README, PATCH_DIR / "apply.sh"):
        if not required.exists():
            print(f"test_wvproj_to_make.py: missing {required}", file=sys.stderr)
            return 2
    for command in ("make", "perl", "patch"):
        if shutil.which(command) is None:
            print(f"test_wvproj_to_make.py: missing host command: {command}", file=sys.stderr)
            return 2

    try:
        projects = selected_projects(mode)
        compiler = resolve_compiler()
        version = verify_compiler(compiler)
        print(f"MODE={mode}; projects={len(projects)}; compiler={compiler}")
        print(f"{version}")
        original_files = apply_test_patches()
        try:
            return run_builds(projects, compiler, mode)
        finally:
            # Restore the exact bytes captured before testing so a local run
            # also preserves any pre-existing user state and partial patch
            # applications.
            restore_files(original_files)
            if original_files:
                print("restored EVT source tree after test patches", flush=True)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"test_wvproj_to_make.py: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
