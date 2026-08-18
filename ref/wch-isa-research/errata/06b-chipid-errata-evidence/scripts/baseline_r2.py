#!/usr/bin/env python3
"""Freeze the independent round-two 06b baseline before any result replacement."""
from __future__ import annotations

import hashlib
import os
import pathlib
import shutil
import subprocess
from datetime import datetime, timezone


RUN = pathlib.Path(__file__).resolve().parent
REPO = RUN.parents[3]
ALLOWED = (
    "audit-report-f/followup/results/06b-chipid-errata-codex.md",
    "audit-report-f/followup/results/06b-chipid-errata-inventory.tsv",
    "audit-report-f/followup/results/06b-chipid-errata-object-scan.tsv",
    "audit-report-f/followup/results/06b-chipid-errata-findings.tsv",
    "audit-report-f/followup/results/06b-chipid-errata-evidence",
)
PRIOR_SPECS = (
    "audit-report-f/followup/results/06-chipid*",
    "audit-report-f/followup/results/06b-chipid-errata-*",
    "tmp/chipid-06",
    "tmp/chipid-errata-06b",
    "isa-research-review-codex-r2.md",
    "isa-research-codex/findings.md",
    "isa-research-claude/qingke-custom-isa.md",
    "isa-research-claude/wch-custom-isa-reference.md",
    "isa-research-claude/wch-isa-usage-in-libraries.md",
    "isa-research-claude/wch-doc-instr-reg-findings.md",
    "isa-research-claude/wch-evt-pdf-instr-reg-index.md",
    "tmp/isa-research-codex",
)


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def git(*args: str) -> bytes:
    return subprocess.check_output(("git", *args), cwd=REPO)


def repo_rel(path: pathlib.Path) -> str:
    return path.relative_to(REPO).as_posix()


def files_below(path: pathlib.Path):
    if path.is_file() or path.is_symlink():
        yield path
        return
    if path.is_dir():
        for child in sorted(path.rglob("*"), key=lambda item: item.as_posix().encode("utf-8")):
            if child.is_file() or child.is_symlink():
                yield child


def filtered_status() -> bytes:
    excludes = tuple(f":(exclude){item}" for item in ALLOWED)
    return git("status", "--porcelain=v2", "--untracked-files=all", "--", ".", *excludes)


def diff_digest(cached: bool) -> str:
    args = ["diff"]
    if cached:
        args.append("--cached")
    args.extend(("--binary", "--", "."))
    args.extend(f":(exclude){item}" for item in ALLOWED)
    return digest_bytes(git(*args))


def copy_preserving(src: pathlib.Path, dst: pathlib.Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_symlink():
        os.symlink(os.readlink(src), dst)
    else:
        shutil.copy2(src, dst)


def main() -> int:
    existing = {item.name for item in RUN.iterdir()}
    if not existing.issubset({"baseline_r2.py", "__pycache__"}):
        raise SystemExit("run directory is not pristine; refusing to reuse it")

    prompt = REPO / "06b-chipid-errata-codex.md"
    head = git("rev-parse", "HEAD").decode("ascii").strip()
    full_status = git("status", "--porcelain=v2", "--untracked-files=all")
    outside_status = filtered_status()
    worktree_hash = diff_digest(False)
    index_hash = diff_digest(True)

    (RUN / "initial-git-head").write_text(head + "\n", encoding="ascii")
    (RUN / "initial-git-status.porcelain-v2").write_bytes(full_status)
    (RUN / "initial-git-status.sha256").write_text(digest_bytes(full_status) + "\n", encoding="ascii")
    (RUN / "initial-out-of-scope-status.porcelain-v2").write_bytes(outside_status)
    (RUN / "initial-out-of-scope-status.sha256").write_text(digest_bytes(outside_status) + "\n", encoding="ascii")
    (RUN / "initial-out-of-scope-worktree-diff.sha256").write_text(worktree_hash + "\n", encoding="ascii")
    (RUN / "initial-out-of-scope-index-diff.sha256").write_text(index_hash + "\n", encoding="ascii")
    (RUN / "run-meta.txt").write_text(
        "schema_version=2\n"
        f"run_id={RUN.name}\n"
        f"created_utc={datetime.now(timezone.utc).isoformat()}\n"
        f"head={head}\n"
        f"prompt_sha256={digest_file(prompt)}\n",
        encoding="utf-8",
    )

    fixed_rows = ["path\tstatus\tsize_bytes\tmtime_ns\tsha256"]
    copied = 0
    for allowed in ALLOWED:
        source = REPO / allowed
        found = list(files_below(source))
        if not found:
            fixed_rows.append(f"{allowed}\tnot-present\tnot-applicable\tnot-applicable\tnot-applicable")
            continue
        for item in found:
            stat = item.lstat()
            relative = repo_rel(item)
            sha = digest_file(item) if not item.is_symlink() else digest_bytes(os.readlink(item).encode())
            fixed_rows.append(f"{relative}\tpresent\t{stat.st_size}\t{stat.st_mtime_ns}\t{sha}")
            copy_preserving(item, RUN / "prior-output" / relative)
            copied += 1
    (RUN / "fixed-output-baseline.tsv").write_text("\n".join(fixed_rows) + "\n", encoding="utf-8")

    candidates: set[pathlib.Path] = set()
    missing: list[str] = []
    for spec in PRIOR_SPECS:
        matches = list(REPO.glob(spec))
        if not matches:
            missing.append(spec)
        for match in matches:
            for item in files_below(match):
                if item == RUN or RUN in item.parents:
                    continue
                candidates.add(item)

    prior_rows = ["schema_version\tartifact_class\tpath\tsize_bytes\tmtime_ns\tsha256\tstatus"]
    for spec in sorted(missing, key=lambda value: value.encode("utf-8")):
        prior_rows.append(f"2\tprior-spec\t{spec}\tnot-applicable\tnot-applicable\tnot-applicable\tnot-present")
    for item in sorted(candidates, key=lambda value: repo_rel(value).encode("utf-8")):
        stat = item.lstat()
        relative = repo_rel(item)
        kind = "custom-isa-r2" if "isa-research" in relative else "prior-06-06b"
        sha = digest_file(item) if not item.is_symlink() else digest_bytes(os.readlink(item).encode())
        prior_rows.append(f"2\t{kind}\t{relative}\t{stat.st_size}\t{stat.st_mtime_ns}\t{sha}\tpresent")
    (RUN / "prior-artifact-manifest.tsv").write_text("\n".join(prior_rows) + "\n", encoding="utf-8")
    (RUN / "prior-artifact-manifest.sha256").write_text(
        digest_file(RUN / "prior-artifact-manifest.tsv") + "\n", encoding="ascii"
    )

    print(f"run_id={RUN.name}")
    print(f"head={head}")
    print(f"prompt_sha256={digest_file(prompt)}")
    print(f"fixed_output_files_copied={copied}")
    print(f"prior_artifact_files={len(candidates)}")
    print(f"out_of_scope_status_sha256={digest_bytes(outside_status)}")
    print(f"out_of_scope_worktree_diff_sha256={worktree_hash}")
    print(f"out_of_scope_index_diff_sha256={index_hash}")
    print(f"prior_manifest_sha256={digest_file(RUN / 'prior-artifact-manifest.tsv')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
