#!/usr/bin/env python3
"""Build an independent local WCH document corpus, query ledger, and page review ledger."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
from collections import Counter, defaultdict


INCLUDED_ROOTS = (
    pathlib.Path("tmp/wch-evt/manual"),
    pathlib.Path("tmp/wch-evt/application_notes"),
    pathlib.Path("tmp/wch-evt/evt"),
)
EXCLUDED_ROOTS = (
    (pathlib.Path("tmp/wch-riscv"), "derived/upstream toolchain build corpus; not WCH chip/library documentation"),
    (pathlib.Path("MRS_Toolchain_MAC_V240"), "generic compiler/debugger manuals; not WCH chip/library documentation"),
    (pathlib.Path("tmp/upstream"), "non-WCH comparison material; not evidence for WCH hardware behavior"),
)

QUERIES = {
    "global": {
        "id-terms": r"(?i)(?:\b(?:chip|cpu|device|factory|unique|rom)[ _-]?(?:id|identifier)\b|芯片.{0,8}(?:ID|编号|标识)|唯一.{0,8}(?:ID|编号|标识))",
        "revision-errata": r"(?i)(?:\brevision\b|\brevid\b|\bstepping\b|\berrata?\b|\bwork-?around\b|\bfix(?:ed)?\b|修订|版本|勘误|规避|兼容)",
        "identity-csr": r"(?i)(?:mvendorid|marchid|mimpid|mhartid|\bmisa\b|(?:0x)?f11\b|(?:0x)?f12\b|(?:0x)?f13\b|(?:0x)?f14\b)",
        "known-addresses": r"(?i)(?:1ffff704|1ffff706|1ffff7c4|1ffff884|1ffff7e0|e0042[0-9a-f]{3}|40001[0-9a-f]{3})",
        "silicon-package-lot": r"(?i)(?:\bsilicon\b|\bpackage\b|\blot\b|\bbatch\b|硅|封装|批号|批次)",
    },
    "finding": {
        "mcpy": r"(?i)(?:\bmcpy\b|ASM_MCPY|memory copy instruction|内存复制指令)",
        "wchnet-chip-field": r"(?i)(?:GetChipID|ChipID|1ffff70[46]|LocalTime|descriptor|描述符|0x30|0x80)",
        "iochub-identity": r"(?i)(?:IoCHub|unique.{0,12}(?:id|key)|factory.{0,12}(?:id|key)|register|registration|auth|认证|注册)",
        "csr-address-meaning": r"(?i)(?:0x804|804H|0xBC0|BC0H|INTSYSCR|HW_POPDM_CTLR|CORECFGR|CPU_RUN_CTLR)",
        "h417-lot-capability": r"(?i)(?:PMP|TSELECT|TDATA1|TDATA2|trigger|断点|批号.{0,20}第五位|第五位.{0,20}批号)",
    },
}

VISUAL_REVIEWS = (
    ("tmp/wch-evt/application_notes/CH32V407RM.PDF", 57, "pdf-review/v407-057.png", "mcpy/delay instruction layout and operand-field diagram visually reviewed"),
    ("tmp/wch-evt/application_notes/CH32V407RM.PDF", 58, "pdf-review/v407-058.png", "mcpy prose says no address-alignment restriction; prose operand roles conflict with SDK macros and ROM local block"),
    ("tmp/wch-evt/manual/QingKeV3_Processor_Manual.PDF", 54, "pdf-review/qkv3-54.png", "V3 model and custom-instruction section visually reviewed"),
    ("tmp/wch-evt/manual/QingKeV3_Processor_Manual.PDF", 55, "pdf-review/qkv3-55.png", "MRS support boundary and mimpid-related conditions visually reviewed"),
    ("tmp/wch-evt/manual/QingKeV3_Processor_Manual.PDF", 56, "pdf-review/qkv3-56.png", "delay/Zicond and U_NONS_DLY_0 CSR 0x8c0 context visually reviewed"),
    ("tmp/wch-evt/application_notes/CH32H417RM.PDF", 1, "pdf-review/h417-p1-001.png", "title/version/front-matter and lot-conditioned feature note visually reviewed"),
    ("tmp/wch-evt/application_notes/CH32H417RM.PDF", 44, "pdf-review/h417-p44-044.png", "lot/batch identifier location and wording visually reviewed"),
    ("tmp/wch-evt/application_notes/CH32H417RM.PDF", 53, "pdf-review/h417-trigger-053.png", "core-0 trigger register availability condition visually reviewed"),
    ("tmp/wch-evt/application_notes/CH32H417RM.PDF", 54, "pdf-review/h417-trigger-054.png", "core-1 four-trigger statement visually reviewed separately from core-0 condition"),
    ("tmp/wch-evt/application_notes/CH32H417RM.PDF", 66, "pdf-review/h417-pmp-066.png", "memory-protection/core-0 PMP fifth-lot-digit condition visually reviewed"),
    ("tmp/wch-evt/evt/QingkeV4B_CH32V203_EVT/EXAM/ETH/WCHNET Protocol Stack Library Application Note.pdf", 1, "pdf-review/wchnet-01.png", "WCHNET application-note title/version page visually reviewed"),
    ("tmp/wch-evt/evt/QingkeV4B_CH32V203_EVT/EXAM/ETH/WCHNET Protocol Stack Library Application Note.pdf", 2, "pdf-review/wchnet-02.png", "configuration/checksum material visually reviewed; no ChipID predicate or descriptor workaround shown on reviewed pages"),
)


def digest_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def repo_path(repo: pathlib.Path, path: pathlib.Path) -> str:
    return path.resolve().relative_to(repo).as_posix()


def pdf_info(path: pathlib.Path) -> tuple[dict[str, str], str]:
    proc = subprocess.run(["pdfinfo", str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    info: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            info[key.strip()] = value.strip()
    status = "pass" if proc.returncode == 0 else f"failed:{proc.returncode}:{proc.stderr.strip()}"
    return info, status


def infer_chip(path: str, text: str) -> str:
    combined = path + "\n" + text[:20000]
    chips = sorted(set(re.findall(r"\bCH(?:32|4|5|6)[A-Z0-9x]*\b", combined)))
    return ";".join(chips[:20]) if chips else "not-specific"


def infer_version(text: str) -> str:
    patterns = (
        r"(?i)\b(?:version|版本)\s*[:：]?\s*(V?\d+(?:\.\d+){0,2}[A-Za-z]?)",
        r"\bV\d+(?:\.\d+){1,2}\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text[:50000])
        if match:
            return match.group(1) if match.lastindex else match.group(0)
    return "not-extracted"


def clean(value: object) -> str:
    return re.sub(r"[\t\r\n]+", " ", str(value)).strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-root", required=True)
    args = ap.parse_args()
    repo = pathlib.Path.cwd().resolve()
    run = repo / args.run_root
    out = run / "controls" / "docs-r2"
    text_dir = out / "text"
    text_dir.mkdir(parents=True, exist_ok=True)

    included: list[pathlib.Path] = []
    seen_paths: set[str] = set()
    for root_rel in INCLUDED_ROOTS:
        root = repo / root_rel
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() != ".pdf":
                continue
            rel = repo_path(repo, path)
            if rel in seen_paths:
                continue
            seen_paths.add(rel)
            included.append(path)
    included.sort(key=lambda path: repo_path(repo, path).encode("utf-8"))

    manifest_rows: list[dict[str, object]] = []
    text_by_sha: dict[str, str] = {}
    representative_by_sha: dict[str, str] = {}
    query_rows: list[dict[str, object]] = []
    query_totals = Counter()
    page_hit_totals = Counter()
    extraction_failures: list[str] = []
    schematic_rows: list[dict[str, object]] = []

    for path in included:
        rel = repo_path(repo, path)
        digest = digest_file(path)
        info, info_status = pdf_info(path)
        representative = representative_by_sha.setdefault(digest, rel)
        if digest not in text_by_sha:
            target = text_dir / f"{digest}.txt"
            proc = subprocess.run(
                ["pdftotext", "-layout", "-enc", "UTF-8", str(path), str(target)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            if proc.returncode == 0 and target.exists():
                text_by_sha[digest] = target.read_text(encoding="utf-8", errors="replace")
            else:
                text_by_sha[digest] = ""
                extraction_failures.append(f"{rel}:{proc.returncode}:{proc.stderr.strip()}")
        text = text_by_sha[digest]
        pages = text.split("\f")
        if pages and not pages[-1].strip():
            pages = pages[:-1]
        title = info.get("Title") or path.stem
        language = "mixed-or-chinese" if re.search(r"[\u3400-\u9fff]", text) else "latin-script-or-empty"
        manifest_rows.append({
            "path": rel, "sha256": digest, "size": path.stat().st_size,
            "title": title, "version": infer_version(text),
            "date": info.get("CreationDate", "not-extracted"), "language": language,
            "pages": info.get("Pages", len(pages)), "chip_or_core": infer_chip(rel, text),
            "provenance": "local-wch-evt-or-manual", "relevance": "included-full-text-query",
            "extraction_method": "Poppler pdftotext -layout -enc UTF-8",
            "extraction_status": "pass" if text else "empty-or-failed",
            "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "byte_representative": representative, "pdfinfo_status": info_status,
        })

        for query_set, definitions in QUERIES.items():
            for query_id, pattern in definitions.items():
                regex = re.compile(pattern)
                document_matches = 0
                document_page_hits = 0
                for page_number, page in enumerate(pages, 1):
                    matches = list(regex.finditer(page))
                    if not matches:
                        continue
                    document_matches += len(matches)
                    document_page_hits += 1
                    first = matches[0]
                    begin = max(0, first.start() - 120)
                    end = min(len(page), first.end() + 180)
                    excerpt = clean(page[begin:end])
                    query_rows.append({
                        "path": rel, "sha256": digest, "query_set": query_set,
                        "query_id": query_id, "page": page_number,
                        "match_count_on_page": len(matches), "excerpt": excerpt,
                    })
                query_totals[(query_set, query_id)] += document_matches
                page_hit_totals[(query_set, query_id)] += document_page_hits

        if "/PUB/" in rel and re.search(r"(?i)(?:SCH|PCB)", path.name):
            tokens = re.findall(r"\bP[A-G](?:\d{1,2}|IO\d+)\b|\b(?:SWDIO|SWCLK|ADC\d+|DAC\d+|PIOC_IO[01])\b", text)
            schematic_rows.append({
                "path": rel, "sha256": digest, "token_occurrences": len(tokens),
                "distinct_tokens": len(set(tokens)), "samples": ";".join(sorted(set(tokens))[:20]),
                "limit": "text tokens prove partial extractability, not complete graphical coverage",
            })

    excluded_rows: list[dict[str, object]] = []
    for root_rel, reason in EXCLUDED_ROOTS:
        root = repo / root_rel
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() == ".pdf":
                rel = repo_path(repo, path)
                excluded_rows.append({
                    "path": rel, "sha256": digest_file(path), "size": path.stat().st_size,
                    "root": root_rel.as_posix(), "reason": reason,
                })
    excluded_rows.sort(key=lambda row: str(row["path"]).encode("utf-8"))

    manifest_path = out / "document-manifest.tsv"
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        columns = (
            "path", "sha256", "size", "title", "version", "date", "language", "pages",
            "chip_or_core", "provenance", "relevance", "extraction_method", "extraction_status",
            "text_sha256", "byte_representative", "pdfinfo_status",
        )
        handle.write("schema_version\t" + "\t".join(columns) + "\n")
        for row in manifest_rows:
            handle.write("2\t" + "\t".join(clean(row[column]) for column in columns) + "\n")

    exclusions_path = out / "broad-pdf-exclusions.tsv"
    with exclusions_path.open("w", encoding="utf-8", newline="") as handle:
        handle.write("schema_version\tpath\tsha256\tsize\troot\treason\n")
        for row in excluded_rows:
            handle.write(
                f"2\t{clean(row['path'])}\t{row['sha256']}\t{row['size']}\t{row['root']}\t{clean(row['reason'])}\n"
            )

    query_rows.sort(key=lambda row: (
        str(row["path"]).encode("utf-8"), str(row["query_set"]), str(row["query_id"]), int(row["page"]),
    ))
    hits_path = out / "document-query-hits.tsv"
    with hits_path.open("w", encoding="utf-8", newline="") as handle:
        handle.write("schema_version\tpath\tsha256\tquery_set\tquery_id\tpage\tmatch_count_on_page\texcerpt\n")
        for row in query_rows:
            handle.write("2\t" + "\t".join(clean(row[key]) for key in (
                "path", "sha256", "query_set", "query_id", "page", "match_count_on_page", "excerpt",
            )) + "\n")

    schematic_path = out / "schematic-text-sanity.tsv"
    with schematic_path.open("w", encoding="utf-8", newline="") as handle:
        handle.write("schema_version\tpath\tsha256\ttoken_occurrences\tdistinct_tokens\tsamples\tlimit\n")
        for row in schematic_rows:
            handle.write("2\t" + "\t".join(clean(row[key]) for key in (
                "path", "sha256", "token_occurrences", "distinct_tokens", "samples", "limit",
            )) + "\n")

    visual_path = out / "visual-page-review.tsv"
    with visual_path.open("w", encoding="utf-8", newline="") as handle:
        handle.write("schema_version\tpath\tsha256\tpage\trendered_image\trendered_image_sha256\tobservation\n")
        for rel, page, image_rel, observation in VISUAL_REVIEWS:
            source = repo / rel
            image = run / image_rel
            handle.write(
                f"2\t{rel}\t{digest_file(source)}\t{page}\t{image_rel}\t{digest_file(image)}\t{clean(observation)}\n"
            )

    query_summary = [
        {
            "query_set": query_set, "query_id": query_id, "regex": QUERIES[query_set][query_id],
            "matches": query_totals[(query_set, query_id)],
            "page_hits": page_hit_totals[(query_set, query_id)],
        }
        for query_set in sorted(QUERIES)
        for query_id in sorted(QUERIES[query_set])
    ]
    summary = {
        "schema_version": "2", "status": "pass" if not extraction_failures else "partial",
        "included_physical_pdfs": len(manifest_rows),
        "included_content_groups": len({row["sha256"] for row in manifest_rows}),
        "full_text_extraction_failures": extraction_failures,
        "excluded_broad_pdf_paths": len(excluded_rows),
        "excluded_broad_content_groups": len({row["sha256"] for row in excluded_rows}),
        "excluded_by_root": dict(sorted(Counter(str(row["root"]) for row in excluded_rows).items())),
        "query_sets": query_summary,
        "visual_review_pages": len(VISUAL_REVIEWS),
        "schematic_physical_files": len(schematic_rows),
        "schematic_content_groups": len({row["sha256"] for row in schematic_rows}),
        "schematic_token_range": [
            min((int(row["token_occurrences"]) for row in schematic_rows), default=0),
            max((int(row["token_occurrences"]) for row in schematic_rows), default=0),
        ],
        "limits": [
            "full-text queries cover the listed local WCH manual/application-note/EVT PDFs only",
            "derived/upstream/generic-toolchain PDFs are path+hash excluded by provenance and are not hardware-negative evidence",
            "visual review is limited to the explicit page ledger; unreviewed image-only/table content remains a document blind spot",
        ],
        "files": {
            "document_manifest_sha256": digest_file(manifest_path),
            "broad_exclusions_sha256": digest_file(exclusions_path),
            "query_hits_sha256": digest_file(hits_path),
            "visual_review_sha256": digest_file(visual_path),
            "schematic_sanity_sha256": digest_file(schematic_path),
        },
    }
    summary_path = out / "document-query-summary.json"
    summary_path.write_text(json.dumps(summary, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({
        "status": summary["status"], "included": len(manifest_rows),
        "included_groups": summary["included_content_groups"], "excluded": len(excluded_rows),
        "visual_pages": len(VISUAL_REVIEWS), "schematics": len(schematic_rows),
        "query_page_rows": len(query_rows),
    }, sort_keys=True))
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
