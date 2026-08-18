#!/usr/bin/env python3
"""Byte-close the MRS 2.5 package's two RISC-V trees to the extracted copy."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import tarfile


PACKAGE = pathlib.Path("tmp/archives/MounRiver_Studio_MacOS_ARM64_V2.5.0.tar")
EXTRACTED = pathlib.Path("tmp/mrs-2.5/WCH/Toolchain")
MARKER = "/WCH/Toolchain/"
ROOTS = ("RISC-V Embedded GCC/", "RISC-V Embedded GCC12/")


def digest_stream(handle) -> str:
    h = hashlib.sha256()
    for block in iter(lambda: handle.read(1 << 20), b""):
        h.update(block)
    return h.hexdigest()


def digest_file(path: pathlib.Path) -> str:
    with path.open("rb") as handle:
        return digest_stream(handle)


def normalized_tail(name: str) -> str | None:
    clean = name.removeprefix("./")
    marker = MARKER.removeprefix("/")
    at = clean.find(marker)
    if at < 0:
        return None
    tail = clean[at + len(marker):]
    if not tail.startswith(ROOTS):
        return None
    if tail.startswith("/") or ".." in pathlib.PurePosixPath(tail).parts:
        raise ValueError(f"unsafe target member: {name!r}")
    return tail


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-root", required=True)
    args = ap.parse_args()
    repo = pathlib.Path.cwd().resolve()
    package = repo / PACKAGE
    extracted = repo / EXTRACTED
    out = repo / args.run_root / "controls" / "tar-closure-r2"
    out.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, object]] = []
    package_paths: set[str] = set()
    duplicate_paths: list[str] = []
    with tarfile.open(package, mode="r:") as archive:
        for member in archive:
            tail = normalized_tail(member.name)
            if tail is None or member.isdir():
                continue
            if tail in package_paths:
                duplicate_paths.append(tail)
            package_paths.add(tail)
            target = extracted / pathlib.PurePosixPath(tail)
            if member.isfile():
                source = archive.extractfile(member)
                if source is None:
                    tar_hash = "unreadable"
                else:
                    with source:
                        tar_hash = digest_stream(source)
                if target.is_file() and not target.is_symlink():
                    extracted_kind = "file"
                    extracted_size: int | str = target.stat().st_size
                    extracted_value = digest_file(target)
                elif target.is_symlink():
                    extracted_kind = "symlink"
                    extracted_size = "not-applicable"
                    extracted_value = os.readlink(target)
                else:
                    extracted_kind = "missing"
                    extracted_size = "not-applicable"
                    extracted_value = "not-applicable"
                is_appledouble = pathlib.PurePosixPath(tail).name.startswith("._")
                status = (
                    "excluded-appledouble-sidecar" if is_appledouble and extracted_kind == "missing"
                    else "match" if (
                        extracted_kind == "file"
                        and extracted_size == member.size
                        and extracted_value == tar_hash
                    ) else "mismatch"
                )
                rows.append({
                    "path": tail, "package_kind": "file", "package_size": member.size,
                    "package_value": tar_hash, "extracted_kind": extracted_kind,
                    "extracted_size": extracted_size, "extracted_value": extracted_value,
                    "status": status,
                })
            elif member.issym():
                extracted_kind = "symlink" if target.is_symlink() else ("file" if target.is_file() else "missing")
                extracted_value = os.readlink(target) if target.is_symlink() else "not-applicable"
                status = "match" if extracted_kind == "symlink" and extracted_value == member.linkname else "mismatch"
                rows.append({
                    "path": tail, "package_kind": "symlink", "package_size": "not-applicable",
                    "package_value": member.linkname, "extracted_kind": extracted_kind,
                    "extracted_size": "not-applicable", "extracted_value": extracted_value,
                    "status": status,
                })
            elif member.islnk():
                rows.append({
                    "path": tail, "package_kind": "hardlink", "package_size": "not-applicable",
                    "package_value": member.linkname,
                    "extracted_kind": "file" if target.is_file() else "missing",
                    "extracted_size": target.stat().st_size if target.is_file() else "not-applicable",
                    "extracted_value": digest_file(target) if target.is_file() else "not-applicable",
                    "status": "manual-hardlink-resolution-required",
                })
            else:
                rows.append({
                    "path": tail, "package_kind": f"tar-type-{member.type!r}",
                    "package_size": member.size, "package_value": "not-applicable",
                    "extracted_kind": "not-applicable", "extracted_size": "not-applicable",
                    "extracted_value": "not-applicable", "status": "unsupported-type",
                })

    extracted_paths: set[str] = set()
    for root_name in ("RISC-V Embedded GCC", "RISC-V Embedded GCC12"):
        root = extracted / root_name
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            dirnames.sort(key=os.fsencode)
            filenames.sort(key=os.fsencode)
            base = pathlib.Path(dirpath)
            for name in filenames:
                extracted_paths.add((base / name).relative_to(extracted).as_posix())
            for name in list(dirnames):
                child = base / name
                if child.is_symlink():
                    extracted_paths.add(child.relative_to(extracted).as_posix())

    extra = sorted(extracted_paths - package_paths, key=lambda x: x.encode("utf-8"))
    for tail in extra:
        target = extracted / pathlib.PurePosixPath(tail)
        rows.append({
            "path": tail, "package_kind": "missing", "package_size": "not-applicable",
            "package_value": "not-applicable",
            "extracted_kind": "symlink" if target.is_symlink() else "file",
            "extracted_size": "not-applicable" if target.is_symlink() else target.stat().st_size,
            "extracted_value": os.readlink(target) if target.is_symlink() else digest_file(target),
            "status": "extra-extracted",
        })

    rows.sort(key=lambda row: str(row["path"]).encode("utf-8"))
    ledger = out / "package-extracted-byte-closure.tsv"
    with ledger.open("w", encoding="utf-8", newline="") as handle:
        handle.write(
            "schema_version\tpath\tpackage_kind\tpackage_size\tpackage_value\t"
            "extracted_kind\textracted_size\textracted_value\tstatus\n"
        )
        for row in rows:
            handle.write("2\t" + "\t".join(str(row[key]) for key in (
                "path", "package_kind", "package_size", "package_value", "extracted_kind",
                "extracted_size", "extracted_value", "status",
            )) + "\n")

    mismatches = [row for row in rows if row["status"] not in {"match", "excluded-appledouble-sidecar"}]
    metadata_sidecars = [row for row in rows if row["status"] == "excluded-appledouble-sidecar"]
    summary = {
        "schema_version": "2",
        "status": "pass" if not mismatches and not duplicate_paths else "failed",
        "package_path": PACKAGE.as_posix(),
        "package_size": package.stat().st_size,
        "package_sha256": digest_file(package),
        "extracted_root": EXTRACTED.as_posix(),
        "target_roots": [x.removesuffix("/") for x in ROOTS],
        "package_non_directory_members": len(package_paths),
        "extracted_non_directory_entries": len(extracted_paths),
        "matched_entries": sum(row["status"] == "match" for row in rows),
        "excluded_appledouble_metadata_sidecars": len(metadata_sidecars),
        "mismatch_count": len(mismatches),
        "mismatch_samples": mismatches[:20],
        "duplicate_package_paths": sorted(set(duplicate_paths), key=lambda x: x.encode("utf-8")),
        "ledger_sha256": digest_file(ledger),
    }
    summary_path = out / "package-extracted-closure-summary.json"
    summary_path.write_text(json.dumps(summary, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({key: summary[key] for key in (
        "status", "package_non_directory_members", "extracted_non_directory_entries",
        "matched_entries", "mismatch_count", "package_sha256",
    )}, sort_keys=True))
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
