#!/usr/bin/env python3
"""Fetch and verify the pinned Linux WCH GCC15 toolchain used by CI.

The download flow follows the canonical-package pattern used by
``~/Projects/gccriscv-wch``: a cached archive is accepted only when its size
and SHA-256 match, the official MounRiver API is used to resolve the current
signed URL, and the extracted GCC executable is checked before it is used.

Use ``--archive`` for an already downloaded MounRiver archive.  The normal CI
path downloads it from the official API, while local ``act`` runs can skip
the download entirely by setting ``COMPILER_PATH`` in the workflow command.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import posixpath
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath


ARCHIVE_NAME = "MounRiverStudio_Linux_X64_V2.5.0.tar.xz"
ARCHIVE_BYTES = 669264336
ARCHIVE_SHA256 = "1fcb13722eaa9119ba4b652f896f2dc1288387a5d1b7a449c0a141b46ec49cf5"
GCC_SHA256 = "9527827d2004aaddfeb3ecac030d0a0ec19678e9601e3ffdb18f9a3100b9bd99"
GCC_RELATIVE = "bin/riscv32-wch-elf-gcc"
TOOLCHAIN_MEMBER = "MRS2/MRS-linux-x64/resources/app/resources/linux/components/WCH/Toolchain/RISC-V Embedded GCC15"
DOWNLOAD_API = "https://api.mounriver.com/mountriver/api/version/getDownloadUrl"
RESOURCE_ID = "2071903155399995393"


class ToolchainError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_archive(path: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise ToolchainError(f"toolchain archive is not a regular file: {path}")
    actual_bytes = path.stat().st_size
    if actual_bytes != ARCHIVE_BYTES:
        raise ToolchainError(f"toolchain archive size mismatch: {actual_bytes} != {ARCHIVE_BYTES}")
    actual_sha = sha256_file(path)
    if actual_sha != ARCHIVE_SHA256:
        raise ToolchainError(f"toolchain archive SHA-256 mismatch: {actual_sha} != {ARCHIVE_SHA256}")


def signed_download_url() -> str:
    query = urllib.parse.urlencode({"resourceId": RESOURCE_ID})
    request = urllib.request.Request(
        f"{DOWNLOAD_API}?{query}",
        headers={"Accept": "application/json", "User-Agent": "openwch-wch-evt/1"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except (OSError, ValueError) as exc:
        raise ToolchainError(f"cannot resolve MounRiver download URL: {exc}") from exc
    url = payload.get("result") if isinstance(payload, dict) else None
    parsed = urllib.parse.urlsplit(url or "")
    if parsed.scheme != "https" or not parsed.netloc:
        raise ToolchainError("MounRiver API returned an invalid HTTPS download URL")
    return url


def copy_verified(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.part.{os.getpid()}")
    try:
        shutil.copyfile(source, temporary)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def download_archive(destination: Path, url: str | None) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        try:
            validate_archive(destination)
            print(f"WCH_TOOLCHAIN_CACHE_HIT archive={destination}", flush=True)
            return destination
        except ToolchainError as exc:
            print(f"WCH_TOOLCHAIN_CACHE_REJECTED archive={destination} reason={exc}", flush=True)
            destination.unlink(missing_ok=True)

    download_url = url or signed_download_url()
    temporary = destination.with_name(f".{destination.name}.part.{os.getpid()}")
    try:
        request = urllib.request.Request(download_url, headers={"User-Agent": "openwch-wch-evt/1"})
        print(f"WCH_TOOLCHAIN_NETWORK_DOWNLOAD archive={ARCHIVE_NAME}", flush=True)
        with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as output:
            while True:
                block = response.read(4 * 1024 * 1024)
                if not block:
                    break
                output.write(block)
        validate_archive(temporary)
        temporary.replace(destination)
    except (OSError, ToolchainError) as exc:
        raise ToolchainError(f"could not download verified WCH toolchain archive: {exc}") from exc
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def safe_member_name(name: str, prefix: str) -> str | None:
    normalized = name.rstrip("/")
    prefix_with_slash = prefix.rstrip("/") + "/"
    if normalized == prefix.rstrip("/"):
        return ""
    if not name.startswith(prefix_with_slash):
        return None
    relative = name[len(prefix_with_slash) :].rstrip("/")
    if not relative:
        return ""
    path = PurePosixPath(relative)
    if path.is_absolute() or ".." in path.parts:
        raise ToolchainError(f"unsafe member path in toolchain archive: {name}")
    return str(path)


def safe_link_target(member_name: str, link_name: str) -> None:
    if not link_name or link_name.startswith("/"):
        raise ToolchainError(f"unsafe link in toolchain archive: {member_name} -> {link_name}")
    parent = posixpath.dirname(member_name)
    resolved = posixpath.normpath(posixpath.join(parent, link_name))
    if resolved == ".." or resolved.startswith("../"):
        raise ToolchainError(f"link escapes toolchain root: {member_name} -> {link_name}")


def extract_toolchain(archive: Path, destination: Path) -> Path:
    gcc = destination / GCC_RELATIVE
    if gcc.is_file() and sha256_file(gcc) == GCC_SHA256:
        print(f"WCH_TOOLCHAIN_INSTALL_HIT root={destination}", flush=True)
        return gcc

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{destination.name}.", dir=destination.parent) as temporary:
        temporary_root = Path(temporary)
        selected: list[tarfile.TarInfo] = []
        with tarfile.open(archive, mode="r:xz") as tar:
            prefix = TOOLCHAIN_MEMBER.rstrip("/")
            for member in tar:
                relative = safe_member_name(member.name, prefix)
                if relative is None or relative == "":
                    continue
                member.name = relative
                if member.issym() or member.islnk():
                    safe_link_target(relative, member.linkname)
                selected.append(member)
            if not selected:
                raise ToolchainError(f"toolchain member not found in archive: {TOOLCHAIN_MEMBER}")
            tar.extractall(temporary_root, members=selected)

        extracted_gcc = temporary_root / GCC_RELATIVE
        if not extracted_gcc.is_file() or sha256_file(extracted_gcc) != GCC_SHA256:
            raise ToolchainError("extracted WCH GCC is missing or has an unexpected SHA-256")
        if destination.exists():
            shutil.rmtree(destination)
        temporary_root.rename(destination)
    return destination / GCC_RELATIVE


def verify_compiler(gcc: Path) -> None:
    if not gcc.is_file() or not os.access(gcc, os.X_OK):
        raise ToolchainError(f"extracted compiler is not executable: {gcc}")
    if sha256_file(gcc) != GCC_SHA256:
        raise ToolchainError(f"compiler SHA-256 mismatch: {gcc}")
    try:
        version = subprocess.run([str(gcc), "--version"], check=True, text=True, capture_output=True, timeout=30)
        machine = subprocess.run([str(gcc), "-dumpmachine"], check=True, text=True, capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as exc:
        raise ToolchainError(f"compiler smoke test failed: {gcc}") from exc
    if "15.2.0" not in version.stdout.splitlines()[0] or machine.stdout.strip() != "riscv32-wch-elf":
        raise ToolchainError(f"unexpected WCH compiler identity: {version.stdout.strip()} / {machine.stdout.strip()}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True, help="toolchain root containing bin/")
    parser.add_argument("--archive", type=Path, help="use and verify a local MounRiver archive")
    parser.add_argument("--cache-dir", type=Path, default=Path(os.environ.get("WCH_TOOLCHAIN_CACHE_DIR", ".cache/wch-evt")))
    parser.add_argument("--url", help="override the resolved signed download URL (normally for a mirror)")
    args = parser.parse_args()

    try:
        if args.archive:
            archive = args.archive.expanduser().resolve()
            validate_archive(archive)
        else:
            cache_archive = args.cache_dir.expanduser().resolve() / ARCHIVE_NAME
            archive = download_archive(cache_archive, args.url)
        gcc = extract_toolchain(archive, args.destination.expanduser().resolve())
        verify_compiler(gcc)
        print(f"COMPILER_PATH={gcc}")
        return 0
    except (OSError, ToolchainError, ValueError) as exc:
        print(f"fetch_wch_toolchain.py: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
