#!/usr/bin/env python3
"""Exact document controls for CSR visibility, H417 lot boundaries, and WCHNET gaps."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pathlib
import re


RM_EXPECTED = {
    "CH32V003RM.PDF": (False, "INTSYSCR", None),
    "CH32V00XRM.PDF": (False, "INTSYSCR", None),
    "CH641RM.PDF": (False, "INTSYSCR", None),
    "CH32X035RM.PDF": (False, "INTSYSCR", None),
    "CH32L103RM.PDF": (False, "INTSYSCR", None),
    "CH32FV2x_V3xRM.PDF": (False, "INTSYSCR", None),
    "CH32M030RM.PDF": (False, "INTSYSCR", "CORECFGR"),
    "CH32V205RM.PDF": (False, "INTSYSCR", "CORECFGR"),
    "CH32X315RM.PDF": (True, "HW_POPDM_CTLR", "CPU_RUN_CTLR"),
    "CH32V407RM.PDF": (True, "HW_POPDM_CTLR", "CPU_RUN_CTLR"),
    "CH32H417RM.PDF": (True, "HW_POPDM_CTLR", "CPU_RUN_CTLR"),
    "CH32xRM.PDF": (False, None, None),
}


def digest(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def count(text: str, pattern: str) -> int:
    return len(re.findall(pattern, text, re.I))


def pages_with(text: str, pattern: str) -> list[int]:
    regex = re.compile(pattern, re.I)
    return [index for index, page in enumerate(text.split("\f"), 1) if regex.search(page)]


def excerpt(page: str, pattern: str) -> str:
    match = re.search(pattern, page, re.I)
    if not match:
        return "not-found"
    begin = max(0, match.start() - 180)
    end = min(len(page), match.end() + 320)
    return re.sub(r"[\t\r\n]+", " ", page[begin:end]).strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-root", required=True)
    args = ap.parse_args()
    repo = pathlib.Path.cwd().resolve()
    out = repo / args.run_root / "controls" / "docs-r2"
    text_dir = out / "text"
    manifest = {}
    with (out / "document-manifest.tsv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            manifest[row["path"]] = row

    register_rows = []
    matrix_ok = True
    for basename, (identity_expected, csr804_expected, csrbc0_expected) in RM_EXPECTED.items():
        rel = f"tmp/wch-evt/application_notes/{basename}"
        row = manifest[rel]
        text = (text_dir / f"{row['sha256']}.txt").read_text(encoding="utf-8", errors="replace")
        identity_count = count(text, r"mvendorid|marchid|mimpid|mhartid|0xF11\b|0xF12\b|0xF13\b|0xF14\b")
        identity_seen = identity_count > 0
        csr804_seen = next((name for name in ("HW_POPDM_CTLR", "INTSYSCR") if count(text, re.escape(name))), None)
        csrbc0_seen = next((name for name in ("CPU_RUN_CTLR", "CORECFGR") if count(text, re.escape(name))), None)
        csr804_literal = count(text, r"0x804\b|804H\b")
        csrbc0_literal = count(text, r"0xBC0\b|BC0H\b")
        status = "pass" if (
            identity_seen == identity_expected
            and csr804_seen == csr804_expected
            and csrbc0_seen == csrbc0_expected
            and ((csr804_expected is None and csr804_literal == 0) or csr804_expected is not None)
        ) else "mismatch"
        matrix_ok &= status == "pass"
        register_rows.append({
            "path": rel, "sha256": row["sha256"], "version": row["version"],
            "identity_expected": identity_expected, "identity_seen": identity_seen,
            "identity_term_count": identity_count,
            "csr804_expected": csr804_expected or "no-literal-entry",
            "csr804_seen": csr804_seen or "none", "csr804_literal_count": csr804_literal,
            "csrbc0_expected": csrbc0_expected or "not-controlled",
            "csrbc0_seen": csrbc0_seen or "none", "csrbc0_literal_count": csrbc0_literal,
            "status": status,
        })

    register_path = out / "rm-register-visibility.tsv"
    with register_path.open("w", encoding="utf-8", newline="") as handle:
        columns = (
            "path", "sha256", "version", "identity_expected", "identity_seen", "identity_term_count",
            "csr804_expected", "csr804_seen", "csr804_literal_count", "csrbc0_expected",
            "csrbc0_seen", "csrbc0_literal_count", "status",
        )
        handle.write("schema_version\t" + "\t".join(columns) + "\n")
        for row in register_rows:
            handle.write("2\t" + "\t".join(str(row[key]) for key in columns) + "\n")

    h417_rel = "tmp/wch-evt/application_notes/CH32H417RM.PDF"
    h417_row = manifest[h417_rel]
    h417_text = (text_dir / f"{h417_row['sha256']}.txt").read_text(encoding="utf-8", errors="replace")
    h417_pages = h417_text.split("\f")
    h417_controls = (
        (1, r"批号|batch|lot", "front-matter lot-conditioned capability scope"),
        (44, r"批号|batch|lot|第五位", "lot-number field wording"),
        (53, r"TSELECT|TDATA1|TDATA2|trigger|断点", "core-0 trigger condition"),
        (54, r"TSELECT|TDATA1|TDATA2|trigger|断点", "core-1 four-trigger statement"),
        (66, r"PMP|memory protection|内存保护|第五位", "memory protection/core-0 PMP condition"),
    )
    h417_path = out / "h417-lot-page-excerpts.tsv"
    h417_ok = True
    with h417_path.open("w", encoding="utf-8", newline="") as handle:
        handle.write("schema_version\tpath\tsha256\tpage\tcontrol\texcerpt\tstatus\n")
        for page, pattern, control in h417_controls:
            text = h417_pages[page - 1] if page <= len(h417_pages) else ""
            value = excerpt(text, pattern)
            visual = repo / args.run_root / "pdf-review" / "h417-p44-044.png"
            status = (
                "pass-text" if value != "not-found"
                else "pass-visual-only" if page == 44 and visual.is_file()
                else "failed"
            )
            h417_ok &= status.startswith("pass")
            handle.write(f"2\t{h417_rel}\t{h417_row['sha256']}\t{page}\t{control}\t{value}\t{status}\n")

    wchnet_rows = []
    wchnet_ok = True
    exact_patterns = {
        "GetChipID": r"\bGetChipID\b",
        "1ffff704-or-706": r"1ffff70[46]",
        "LocalTime": r"\bLocalTime\b",
        "counter-0x8000": r"0x8000\b",
    }
    for rel, row in sorted(manifest.items(), key=lambda item: item[0].encode("utf-8")):
        if "WCHNET" not in rel.upper():
            continue
        text = (text_dir / f"{row['sha256']}.txt").read_text(encoding="utf-8", errors="replace")
        counts = {name: count(text, pattern) for name, pattern in exact_patterns.items()}
        status = "pass-no-exact-hidden-predicate" if not any(counts.values()) else "hit-requires-review"
        wchnet_ok &= status == "pass-no-exact-hidden-predicate"
        wchnet_rows.append({"path": rel, "sha256": row["sha256"], "pages": row["pages"], "counts": counts, "status": status})
    wchnet_path = out / "wchnet-document-gap.tsv"
    with wchnet_path.open("w", encoding="utf-8", newline="") as handle:
        handle.write("schema_version\tpath\tsha256\tpages\tGetChipID\t1ffff704_or_706\tLocalTime\tcounter_0x8000\tstatus\n")
        for row in wchnet_rows:
            counts = row["counts"]
            handle.write(
                f"2\t{row['path']}\t{row['sha256']}\t{row['pages']}\t{counts['GetChipID']}\t"
                f"{counts['1ffff704-or-706']}\t{counts['LocalTime']}\t{counts['counter-0x8000']}\t{row['status']}\n"
            )

    v407_rel = "tmp/wch-evt/application_notes/CH32V407RM.PDF"
    v407_row = manifest[v407_rel]
    v407_text = (text_dir / f"{v407_row['sha256']}.txt").read_text(encoding="utf-8", errors="replace")
    mcpy_pages = pages_with(v407_text, r"\bmcpy\b")
    mcpy_ok = 58 in mcpy_pages or 57 in mcpy_pages

    summary = {
        "schema_version": "2",
        "status": "pass" if matrix_ok and h417_ok and wchnet_ok and mcpy_ok else "failed",
        "rm_matrix_pass": matrix_ok,
        "identity_csr_visible_documents": [row["path"] for row in register_rows if row["identity_seen"]],
        "identity_csr_not_visible_documents": [row["path"] for row in register_rows if not row["identity_seen"]],
        "h417_page_controls_pass": h417_ok,
        "wchnet_physical_documents_checked": len(wchnet_rows),
        "wchnet_exact_hidden_predicate_terms_zero": wchnet_ok,
        "wchnet_limit": "term/page negative is restricted to listed document hashes and query spellings; it is not proof no workaround is documented elsewhere",
        "v407_mcpy_pages": mcpy_pages,
        "v407_mcpy_control_pass": mcpy_ok,
        "files": {
            "rm_register_visibility_sha256": digest(register_path),
            "h417_excerpts_sha256": digest(h417_path),
            "wchnet_document_gap_sha256": digest(wchnet_path),
        },
    }
    summary_path = out / "document-control-summary.json"
    summary_path.write_text(json.dumps(summary, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({
        "status": summary["status"], "rm_matrix": matrix_ok, "h417": h417_ok,
        "wchnet_docs": len(wchnet_rows), "wchnet_zero": wchnet_ok, "mcpy_pages": mcpy_pages,
    }, sort_keys=True))
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
