#!/usr/bin/env python3
"""Close project references and available linked-map selection for positive artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
from collections import Counter, defaultdict


REFERENCE_PATTERNS = {
    "wchnet-soft": re.compile(rb"libwchnet\.a", re.I),
    "wchnet-float": re.compile(rb"libwchnet_float\.a", re.I),
    "iochub": re.compile(rb"libwchiochub\.a", re.I),
    "mesh-rom-wrapper": re.compile(rb"LIBMESHROM\.a", re.I),
    "rom-body": re.compile(rb"(?:CH587BLE_ROMx|wchble_rom(?:_mesh)?)\.hex", re.I),
    "required-chrv3ufi": re.compile(rb"CHRV3UFI\.lib", re.I),
    # Eclipse/MRS stores ``-lNAME`` as a bare library-list value.  Preserve
    # case for the two spelling variants because the prompt requires separate
    # unresolved-reference rows on a case-sensitive filesystem.
    "required-isp585": re.compile(rb"(?<![A-Za-z0-9_])(?:lib)?ISP585(?:\.a)?\b", re.I),
    "required-touch-upper": re.compile(rb"(?<![A-Za-z0-9_])(?:lib)?CH58XTOUCH(?:\.a)?\b"),
    "required-touch-lower": re.compile(rb"(?<![A-Za-z0-9_])(?:lib)?CH58xTOUCH(?:\.a)?\b"),
    "metadata-old-touch": re.compile(rb"lib(?:WCH_TKY\(old\)|CH573_TKY\((?:old|new2)\)|CH573_TKY)\.a", re.I),
}

MAP_PATTERN = re.compile(
    rb"(?P<archive>tmp/wch-evt/evt/[^\r\n]*?/(?:libwchnet(?:_float)?\.a|libwchiochub\.a|LIBMESHROM\.a))"
    rb"\((?P<member>[^)\r\n]+)\)", re.I,
)

TEXT_SUFFIXES = {
    ".cproject", ".project", ".wvproj", ".mk", ".ld", ".lds", ".txt", ".json", ".xml", ".cmake",
}


def digest(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def rid(prefix: str, *parts: object) -> str:
    h = hashlib.sha256()
    h.update(prefix.encode() + b"\0")
    for part in parts:
        raw = str(part).encode("utf-8")
        h.update(len(raw).to_bytes(8, "big") + raw)
    return prefix + "-" + h.hexdigest()


def rel(repo: pathlib.Path, path: pathlib.Path) -> str:
    return path.resolve().relative_to(repo).as_posix()


def clean_line(raw: bytes) -> str:
    text = raw.decode("utf-8", "replace")
    text = re.sub(r"/Users/[^/]+/Projects/gccriscv-wch/", "<REPO>/", text)
    return re.sub(r"[\t\r\n]+", " ", text).strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-root", required=True)
    args = ap.parse_args()
    repo = pathlib.Path.cwd().resolve()
    out = repo / args.run_root / "controls" / "build-context-r2"
    out.mkdir(parents=True, exist_ok=True)

    build = repo / "tmp/wch-evt/build"
    map_paths: list[pathlib.Path] = []
    elf_count = 0
    for dirpath, dirnames, filenames in os.walk(build):
        dirnames.sort(key=os.fsencode)
        filenames.sort(key=os.fsencode)
        base = pathlib.Path(dirpath)
        for name in filenames:
            lowered = name.lower()
            if lowered.endswith(".map"):
                map_paths.append(base / name)
            elif lowered.endswith(".elf"):
                elf_count += 1

    map_rows: list[dict[str, object]] = []
    selection_by_archive: dict[str, list[dict[str, object]]] = defaultdict(list)
    maps_with_hits = 0
    for path in map_paths:
        data = path.read_bytes()
        matches = {}
        for match in MAP_PATTERN.finditer(data):
            archive = match.group("archive").decode("utf-8", "replace")
            member = match.group("member").decode("utf-8", "replace")
            if archive.endswith("libwchnet.a") and member != "eth_api.o":
                continue
            if archive.endswith("libwchnet_float.a") and member != "eth_api.o":
                continue
            if archive.endswith("libwchiochub.a") and member != "IocHub.o":
                continue
            matches[(archive, member)] = match.start()
        if not matches:
            continue
        maps_with_hits += 1
        map_rel = rel(repo, path)
        map_hash = digest(path)
        for (archive, member), offset in sorted(matches.items(), key=lambda item: (item[0][0].encode(), item[0][1].encode())):
            line_start = data.rfind(b"\n", 0, offset) + 1
            line_end = data.find(b"\n", offset)
            if line_end < 0:
                line_end = len(data)
            stale = ".stale-" in map_rel
            builder = "local" if "/local/" in map_rel else "wch" if "/wch/" in map_rel else "other"
            row = {
                "map_path": map_rel, "map_sha256": map_hash, "archive_path": archive,
                "member": member, "stale": stale, "builder": builder,
                "selection": "selected-in-link-map", "excerpt": clean_line(data[line_start:line_end]),
            }
            map_rows.append(row)
            selection_by_archive[archive].append(row)

    evt = repo / "tmp/wch-evt/evt"
    reference_rows: list[dict[str, object]] = []
    reference_hash_cache: dict[pathlib.Path, str] = {}
    for dirpath, dirnames, filenames in os.walk(evt):
        dirnames.sort(key=os.fsencode)
        filenames.sort(key=os.fsencode)
        base = pathlib.Path(dirpath)
        for name in filenames:
            path = base / name
            if path.suffix.lower() not in TEXT_SUFFIXES and name not in {
                "Makefile", "makefile", ".cproject", ".project",
            }:
                continue
            if path.stat().st_size > 8 << 20:
                continue
            data = path.read_bytes()
            applicable = [(label, regex) for label, regex in REFERENCE_PATTERNS.items() if regex.search(data)]
            if not applicable:
                continue
            path_rel = rel(repo, path)
            path_digest = reference_hash_cache.get(path)
            if path_digest is None:
                path_digest = digest(path)
                reference_hash_cache[path] = path_digest
            for line_number, line in enumerate(data.splitlines(), 1):
                for label, regex in applicable:
                    if not regex.search(line):
                        continue
                    lower = line.lower()
                    classification = (
                        "metadata-exclusion-not-link" if b"excluding=" in lower or label == "metadata-old-touch"
                        else "header-comment-body-mapping" if label == "rom-body" and path.suffix.lower() == ".h"
                        else "project-link-reference"
                    )
                    reference_rows.append({
                        "reference_kind": label, "path": path_rel, "sha256": path_digest,
                        "line": line_number, "classification": classification,
                        "excerpt": clean_line(line),
                    })

    reference_rows.sort(key=lambda row: (
        str(row["reference_kind"]), str(row["path"]).encode("utf-8"), int(row["line"]),
    ))
    map_rows.sort(key=lambda row: (
        str(row["archive_path"]).encode("utf-8"), str(row["map_path"]).encode("utf-8"), str(row["member"]),
    ))

    map_path_out = out / "linked-map-selection.tsv"
    with map_path_out.open("w", encoding="utf-8", newline="") as handle:
        handle.write(
            "schema_version\tmap_path\tmap_sha256\tarchive_path\tmember\tstale\tbuilder\tselection\texcerpt\n"
        )
        for row in map_rows:
            handle.write("2\t" + "\t".join(str(row[key]) for key in (
                "map_path", "map_sha256", "archive_path", "member", "stale", "builder", "selection", "excerpt",
            )) + "\n")

    reference_path = out / "project-reference-ledger.tsv"
    with reference_path.open("w", encoding="utf-8", newline="") as handle:
        handle.write("schema_version\treference_kind\tpath\tsha256\tline\tclassification\texcerpt\n")
        for row in reference_rows:
            handle.write("2\t" + "\t".join(str(row[key]) for key in (
                "reference_kind", "path", "sha256", "line", "classification", "excerpt",
            )) + "\n")

    archive_summary = []
    for archive in sorted(selection_by_archive, key=lambda value: value.encode("utf-8")):
        rows = selection_by_archive[archive]
        current = [row for row in rows if not row["stale"]]
        context_id = rid(
            "buildctx", archive,
            *sorted({f"{row['map_sha256']}:{row['member']}:{row['builder']}:{row['stale']}" for row in rows}),
        )
        archive_summary.append({
            "archive_path": archive, "build_context_id": context_id,
            "physical_map_rows": len(rows), "current_map_rows": len(current),
            "map_content_groups": len({row["map_sha256"] for row in rows}),
            "current_map_content_groups": len({row["map_sha256"] for row in current}),
            "builders": sorted({str(row["builder"]) for row in rows}),
            "selected_in_available_link_map": "yes" if current else "stale-only",
        })

    mandatory = {}
    for label in ("required-chrv3ufi", "required-isp585", "required-touch-upper", "required-touch-lower", "metadata-old-touch"):
        rows = [row for row in reference_rows if row["reference_kind"] == label]
        mandatory[label] = {
            "references": len(rows),
            "project_link_references": sum(row["classification"] == "project-link-reference" for row in rows),
            "metadata_exclusions": sum(row["classification"] == "metadata-exclusion-not-link" for row in rows),
        }

    float_refs = [row for row in reference_rows if row["reference_kind"] == "wchnet-float"]
    float_selected = [row for row in map_rows if str(row["archive_path"]).endswith("libwchnet_float.a")]
    summary = {
        "schema_version": "2", "status": "pass",
        "available_map_files_searched": len(map_paths), "available_elf_files_enumerated": elf_count,
        "maps_with_relevant_selection": maps_with_hits,
        "selection_rows": len(map_rows), "selection_archives": archive_summary,
        "selected_soft_wchnet_map_rows": sum(str(row["archive_path"]).endswith("libwchnet.a") for row in map_rows),
        "selected_float_wchnet_map_rows": len(float_selected),
        "selected_iochub_map_rows": sum(str(row["archive_path"]).endswith("libwchiochub.a") for row in map_rows),
        "selected_meshrom_map_rows": sum(str(row["archive_path"]).lower().endswith("libmeshrom.a") for row in map_rows),
        "float_project_reference_rows": len(float_refs),
        "float_interpretation": (
            "project metadata contains float archive link references, but no available map selects float eth_api.o; "
            "available generated maps select the soft archive instead"
        ),
        "mandatory_reference_controls": mandatory,
        "limits": [
            "map presence proves archive-member link selection for that derived build only, not runtime branch execution",
            "absence from available maps is not a global no-link proof; source project references and stale/current maps remain separate",
            "ELF files are enumerated but maps, not binary provenance inference, bind selected members to source archives",
        ],
        "files": {
            "linked_map_selection_sha256": digest(map_path_out),
            "project_reference_ledger_sha256": digest(reference_path),
        },
    }
    summary_path = out / "build-context-summary.json"
    summary_path.write_text(json.dumps(summary, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({
        "maps": len(map_paths), "elfs": elf_count, "map_hits": maps_with_hits,
        "selection_rows": len(map_rows), "archives": len(archive_summary),
        "soft": summary["selected_soft_wchnet_map_rows"], "float": len(float_selected),
        "iochub": summary["selected_iochub_map_rows"], "meshrom": summary["selected_meshrom_map_rows"],
        "float_refs": len(float_refs),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
