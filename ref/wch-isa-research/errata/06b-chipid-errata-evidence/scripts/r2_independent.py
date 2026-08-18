#!/usr/bin/env python3
"""Independent primitive scanner for the second-round chip-ID audit.

This implementation intentionally shares no module, parser class, or
intermediate representation with r2_primary.py.  It re-walks the source roots,
re-parses archives and ELF/HEX bytes, and emits compact occurrence/domain/start
and primitive-candidate set hashes for a strict equality comparison.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import sys
from collections import Counter
from typing import Iterable, Iterator, Sequence


EM_RISCV = 243
ET_REL = 1
SHT_PROGBITS = 1
SHT_SYMTAB = 2
SHT_RELA = 4
SHT_NOBITS = 8
SHT_REL = 9
SHT_DYNSYM = 11
SHF_ALLOC = 2
SHF_EXEC = 4
XINDEX = 0xFFFF

ROOT_SPECS = (
    "MRS_Toolchain_MAC_V240/Toolchain/RISC-V Embedded GCC",
    "MRS_Toolchain_MAC_V240/Toolchain/RISC-V Embedded GCC12",
    "MRS_Toolchain_MAC_V240/Toolchain/RISC-V Embedded GCC15",
    "MRS_Toolchain_MAC_V240/Toolchain/arm-none-eabi-gcc",
    "tmp/mrs-2.5/WCH/Toolchain/RISC-V Embedded GCC",
    "tmp/mrs-2.5/WCH/Toolchain/RISC-V Embedded GCC12",
    "MRS_Toolchain_Linux_X64_V250/Toolchain/RISC-V Embedded GCC15",
    "tmp/wch-evt/evt",
)

ROM_BODIES = {
    "tmp/wch-evt/evt/QingkeV3C_CH587_EVT/EXAM/BLE/LIB/CH587BLE_ROMx.hex",
    "tmp/wch-evt/evt/QingkeV4B_CH32V203_EVT/EXAM/BLE/LIB/wchble_rom.hex",
    "tmp/wch-evt/evt/QingkeV4B_CH32V203_EVT/EXAM/BLE/MESH/MESH_LIB/wchble_rom_mesh.hex",
    "tmp/wch-evt/evt/QingkeV4C_CH32V20x_EVT/EXAM/BLE/LIB/wchble_rom.hex",
    "tmp/wch-evt/evt/QingkeV4C_CH32V20x_EVT/EXAM/BLE/MESH/MESH_LIB/wchble_rom_mesh.hex",
}

KNOWN = {0x1FFFF704, 0x1FFFF706, 0x1FFFF7C4, 0x1FFFF7E0, 0x1FFFF884}
INTEREST_CSRS = {0xF11, 0xF12, 0xF13, 0xF14, 0x301, 0xFC0}
XW = (
    ("c.lbu", 0x2000, 0xE003), ("c.lhu", 0x2002, 0xE003),
    ("c.sb", 0xA000, 0xE003), ("c.sh", 0xA002, 0xE003),
    ("c.lbusp", 0x8000, 0xF863), ("c.lhusp", 0x8020, 0xF863),
    ("c.sbsp", 0x8040, 0xF863), ("c.shsp", 0x8060, 0xF863),
)
RELOC_SOURCE = re.compile(
    r"(?i)(?:chip[_ -]?id|cpu[_ -]?id|cpuid|device[_ -]?id|devid|revid|"
    r"revision|stepping|mvendorid|marchid|mimpid|mhartid|factory|"
    r"unique[_ -]?(?:id|key)|getchipid|dbgmcu_get)"
)


def key8(s: str) -> bytes:
    return s.encode("utf-8", "surrogateescape")


def record_blob(values: Sequence[object]) -> bytes:
    out = len(values).to_bytes(4, "big")
    for value in values:
        raw = str(value).encode("utf-8", "surrogateescape")
        out += len(raw).to_bytes(8, "big") + raw
    return out


def set_digest(values: Iterable[Sequence[object]], ordered: bool = False) -> str:
    rows = values if ordered else sorted(values, key=lambda row: tuple(key8(str(x)) for x in row))
    digest = hashlib.sha256(b"wch-audit-set-v2\0")
    for row in rows:
        digest.update(record_blob(row))
    return digest.hexdigest()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def emit(obj: object) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def safe_replace(path: pathlib.Path, payload: str) -> None:
    scratch = path.with_suffix(path.suffix + ".new-r2")
    scratch.write_text(payload, encoding="utf-8", newline="\n")
    os.replace(scratch, path)


def descend(base: pathlib.Path) -> Iterator[pathlib.Path]:
    """scandir recursion, separate from the primary os.walk discovery."""
    pending = [base]
    while pending:
        here = pending.pop()
        try:
            entries = list(os.scandir(here))
        except OSError:
            continue
        entries.sort(key=lambda e: key8(e.name), reverse=True)
        files: list[pathlib.Path] = []
        dirs: list[pathlib.Path] = []
        for entry in entries:
            try:
                if entry.is_dir(follow_symlinks=False):
                    dirs.append(pathlib.Path(entry.path))
                elif entry.is_file(follow_symlinks=True):
                    files.append(pathlib.Path(entry.path))
            except OSError:
                pass
        # Stack is LIFO; reverse insertion yields ascending traversal.
        pending.extend(dirs)
        for file in reversed(files):
            yield file


def rel(repo: pathlib.Path, path: pathlib.Path) -> str:
    return path.resolve().relative_to(repo).as_posix()


def kind(data: bytes) -> str:
    if data[:8] == b"!<arch>\n":
        return "ar"
    if data[:8] == b"!<thin>\n":
        return "thin-ar"
    if data[:4] == b"\x7fELF":
        return "ELF"
    if data[:4] in {b"BC\xc0\xde", b"\xde\xc0\x17\x0b"}:
        return "LLVM-bitcode"
    if data[:4] in {
        b"\xfe\xed\xfa\xce", b"\xce\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xcf\xfa\xed\xfe",
        b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca",
    }:
        return "Mach-O"
    return "unknown"


def integer(raw: bytes, order: str, signed: bool = False) -> int:
    return int.from_bytes(raw, order, signed=signed)


def cstring(table: bytes, at: int) -> str:
    if at < 0 or at >= len(table):
        return f"<bad-name-{at}>"
    end = table.find(b"\0", at)
    if end < 0:
        end = len(table)
    return table[at:end].decode("utf-8", "surrogateescape")


def parse_archive(file: pathlib.Path, blob: bytes) -> tuple[list[dict[str, object]], dict[str, object]]:
    thin = blob[:8] == b"!<thin>\n"
    pos = 8
    raw_no = 0
    logical_no = 0
    occurrences: Counter[str] = Counter()
    names = b""
    output: list[dict[str, object]] = []
    errors: list[str] = []
    metadata = 0
    while pos < len(blob):
        if len(blob) - pos < 60:
            errors.append(f"short-header@{pos}")
            break
        header = memoryview(blob)[pos:pos + 60]
        if bytes(header[58:60]) != b"`\n":
            errors.append(f"header-tail@{pos}")
            break
        raw_no += 1
        token = bytes(header[:16]).decode("utf-8", "surrogateescape").rstrip(" ")
        size_text = bytes(header[48:58]).decode("ascii", "replace").strip()
        try:
            declared = int(size_text, 10)
        except ValueError:
            errors.append(f"size@{pos}:{size_text}")
            break
        special = token in {"/", "//", "/SYM64/"} or token.startswith("__.SYMDEF")
        carried = declared
        if thin and not special:
            carried = int(token[3:].strip()) if token.startswith("#1/") else 0
        start = pos + 60
        finish = start + carried
        if finish > len(blob):
            errors.append(f"body@{pos}")
            break
        body = bytes(memoryview(blob)[start:finish])
        member_name = token[:-1] if token.endswith("/") else token
        is_metadata = special
        prefix_name = b""
        if token == "//":
            names = body
        elif token.startswith("/") and token[1:].isdigit():
            offset = int(token[1:])
            if offset >= len(names):
                member_name = f"<bad-long-name-{offset}>"
                errors.append(f"longname@{pos}:{offset}")
            else:
                stop = names.find(b"/\n", offset)
                if stop < 0:
                    stop = names.find(b"\n", offset)
                if stop < 0:
                    stop = len(names)
                member_name = names[offset:stop].decode("utf-8", "surrogateescape").rstrip("/")
            is_metadata = False
        elif token.startswith("#1/"):
            try:
                amount = int(token[3:].strip())
            except ValueError:
                amount = 0
                errors.append(f"bsd-name@{pos}")
            prefix_name = body[:amount]
            member_name = prefix_name.decode("utf-8", "surrogateescape").rstrip("\0")
            if not thin:
                body = body[amount:]
            is_metadata = member_name.startswith("__.SYMDEF")
        if is_metadata:
            metadata += 1
        else:
            logical_no += 1
            occurrences[member_name] += 1
            payload: bytes | None
            if thin:
                target = pathlib.Path(member_name)
                if not target.is_absolute():
                    target = file.parent / target
                try:
                    payload = target.read_bytes()
                except OSError:
                    payload = None
                    errors.append(f"external@{logical_no}")
            else:
                payload = body
            output.append({
                "logical_order": logical_no,
                "member_name": member_name,
                "same_name_ordinal": occurrences[member_name],
                "payload": payload,
                "declared_size": declared,
            })
        pos = finish + (carried & 1)
    summary = {
        "thin": thin,
        "raw_record_count": raw_no,
        "archive_metadata_records": metadata,
        "member_occurrences": logical_no,
        "errors": errors,
        "trailing_bytes": len(blob) - pos if pos <= len(blob) else 0,
    }
    return output, summary


def parse_elf(blob: bytes) -> dict[str, object]:
    result: dict[str, object] = {
        "valid": False, "errors": [], "class": 0, "endian": "unknown",
        "etype": 0, "machine": 0, "sections": [], "symbols": {}, "relocations": [],
    }
    errors: list[str] = result["errors"]  # type: ignore[assignment]
    if len(blob) < 20 or blob[:4] != b"\x7fELF":
        errors.append("not-elf")
        return result
    cls, encoding = blob[4], blob[5]
    if cls not in (1, 2) or encoding not in (1, 2):
        errors.append("ident")
        return result
    order = "little" if encoding == 1 else "big"
    result["class"] = cls
    result["endian"] = order
    result["etype"] = integer(blob[16:18], order)
    result["machine"] = integer(blob[18:20], order)
    if cls == 1:
        if len(blob) < 52:
            errors.append("header")
            return result
        section_at = integer(blob[32:36], order)
        entry_size = integer(blob[46:48], order)
        count_field = integer(blob[48:50], order)
        string_field = integer(blob[50:52], order)
        expected = 40
    else:
        if len(blob) < 64:
            errors.append("header")
            return result
        section_at = integer(blob[40:48], order)
        entry_size = integer(blob[58:60], order)
        count_field = integer(blob[60:62], order)
        string_field = integer(blob[62:64], order)
        expected = 64
    if section_at == 0:
        result["valid"] = True
        return result
    if entry_size < expected or section_at + entry_size > len(blob):
        errors.append("section-table")
        return result

    def one(index: int) -> dict[str, int] | None:
        at = section_at + entry_size * index
        if at + expected > len(blob):
            return None
        row = blob[at:at + expected]
        if cls == 1:
            widths = (4, 4, 4, 4, 4, 4, 4, 4, 4, 4)
        else:
            widths = (4, 4, 8, 8, 8, 8, 4, 4, 8, 8)
        vals: list[int] = []
        cursor = 0
        for width in widths:
            vals.append(integer(row[cursor:cursor + width], order))
            cursor += width
        return dict(zip(("name", "type", "flags", "addr", "offset", "size", "link", "info", "align", "entsize"), vals))

    section_zero = one(0)
    if section_zero is None:
        errors.append("section-zero")
        return result
    count = section_zero["size"] if count_field == 0 else count_field
    string_index = section_zero["link"] if string_field == XINDEX else string_field
    if count <= 0 or count > 1_000_000:
        errors.append(f"count:{count}")
        return result
    raw_sections: list[dict[str, int]] = []
    for idx in range(count):
        row = one(idx)
        if row is None:
            errors.append(f"section:{idx}")
            return result
        raw_sections.append(row)
    if not 0 <= string_index < len(raw_sections):
        errors.append("shstr-index")
        return result
    string_row = raw_sections[string_index]
    so, ss = string_row["offset"], string_row["size"]
    if so > len(blob) or ss > len(blob) - so:
        errors.append("shstr-range")
        return result
    strings = blob[so:so + ss]
    sections: list[dict[str, object]] = []
    for idx, raw in enumerate(raw_sections):
        name = cstring(strings, raw["name"])
        off, size, typ = raw["offset"], raw["size"], raw["type"]
        if typ == SHT_NOBITS:
            body = b""
        elif off <= len(blob) and size <= len(blob) - off:
            body = blob[off:off + size]
        else:
            body = b""
            errors.append(f"range:{idx}:{name}")
        # Keep the decoded section name.  ``raw`` also contains the numeric
        # sh_name offset, so it must be expanded before the canonical name.
        sections.append({**raw, "index": idx, "name": name, "data": body, "domain_id": f"section:{idx}:{name}"})
    result["sections"] = sections

    # Parse every symbol table into a table-index keyed map.
    symbol_tables: dict[int, dict[int, str]] = {}
    for sec in sections:
        if sec["type"] not in (SHT_SYMTAB, SHT_DYNSYM) or not sec["data"]:
            continue
        link = int(sec["link"])
        if not 0 <= link < len(sections):
            errors.append(f"sym-link:{sec['index']}")
            continue
        names_blob: bytes = sections[link]["data"]  # type: ignore[assignment]
        body: bytes = sec["data"]  # type: ignore[assignment]
        minimum = 16 if cls == 1 else 24
        stride = int(sec["entsize"]) or minimum
        if stride < minimum or len(body) % stride:
            errors.append(f"sym-shape:{sec['index']}")
        table: dict[int, str] = {}
        for n in range(len(body) // stride):
            at = n * stride
            name_offset = integer(body[at:at + 4], order)
            table[n] = cstring(names_blob, name_offset)
        symbol_tables[int(sec["index"])] = table
    result["symbols"] = symbol_tables

    relocations: list[tuple[object, ...]] = []
    for sec in sections:
        typ = int(sec["type"])
        if typ not in (SHT_REL, SHT_RELA) or not sec["data"]:
            continue
        target_index = int(sec["info"])
        target_name = str(sections[target_index]["name"]) if 0 <= target_index < len(sections) else "<bad-target>"
        body: bytes = sec["data"]  # type: ignore[assignment]
        if cls == 1:
            minimum = 12 if typ == SHT_RELA else 8
            offset_width = info_width = 4
            add_width = 4
        else:
            minimum = 24 if typ == SHT_RELA else 16
            offset_width = info_width = 8
            add_width = 8
        stride = int(sec["entsize"]) or minimum
        if stride < minimum or len(body) % stride:
            errors.append(f"rel-shape:{sec['index']}")
        table = symbol_tables.get(int(sec["link"]), {})
        for n in range(len(body) // stride):
            at = n * stride
            roff = integer(body[at:at + offset_width], order)
            info = integer(body[at + offset_width:at + offset_width + info_width], order)
            if cls == 1:
                symbol_index, rtype = info >> 8, info & 0xFF
            else:
                symbol_index, rtype = info >> 32, info & 0xFFFFFFFF
            if typ == SHT_RELA:
                add_at = at + offset_width + info_width
                addend: object = integer(body[add_at:add_at + add_width], order, signed=True)
            else:
                addend = "implicit"
            relocations.append((
                target_index, target_name, int(sec["index"]), str(sec["name"]),
                n, roff, rtype, symbol_index, table.get(symbol_index, ""), addend,
            ))
    result["relocations"] = relocations
    result["valid"] = True
    return result


def is_address(value: int) -> bool:
    value &= 0xFFFFFFFF
    return (
        value in KNOWN or 0x1FFF0000 <= value < 0x20000000
        or 0x40000000 <= value < 0x60000000
        or 0xE0000000 <= value < 0xF0000000
    )


def xw_name(value: int) -> str | None:
    for label, match, mask in XW:
        if value & mask == match:
            return label
    return None


def csr_fields(word: int) -> tuple[int, int, int, int] | None:
    if word & 0x7F != 0x73:
        return None
    f3 = word >> 12 & 7
    if f3 == 0:
        return None
    return word >> 20 & 0xFFF, f3, word >> 7 & 31, word >> 15 & 31


def digest_grid(sections: list[dict[str, object]], width: int, stride: int) -> tuple[int, str]:
    digest = hashlib.sha256(b"wch-audit-set-v2\0")
    count = 0
    for sec in sorted(sections, key=lambda x: (int(x["index"]), key8(str(x["name"])))):
        body: bytes = sec["data"]  # type: ignore[assignment]
        for at in range(0, len(body) - width + 1, stride):
            digest.update(record_blob((sec["domain_id"], at)))
            count += 1
    return count, digest.hexdigest()


def primitive_scan(blob: bytes) -> dict[str, object]:
    unit_sha = sha(blob)
    elf = parse_elf(blob)
    compact: dict[str, object] = {
        "scan_unit_sha256": unit_sha,
        "file_size": len(blob),
        "magic": kind(blob),
        "elf_valid": elf["valid"],
        "elf_errors": elf["errors"],
        "elf_class": elf["class"],
        "endian": elf["endian"],
        "etype": elf["etype"],
        "machine": elf["machine"],
        "native_scan_applicable": False,
    }
    if not elf["valid"] or elf["machine"] != EM_RISCV or elf["endian"] != "little":
        return compact
    compact["native_scan_applicable"] = True
    sections: list[dict[str, object]] = elf["sections"]  # type: ignore[assignment]
    executable = [s for s in sections if int(s["type"]) != SHT_NOBITS and int(s["flags"]) & SHF_EXEC and s["data"]]
    allocatable = [s for s in sections if int(s["type"]) != SHT_NOBITS and int(s["flags"]) & SHF_ALLOC and s["data"]]
    exec_records = [(s["domain_id"], 0, len(s["data"])) for s in executable]
    alloc_records = [(s["domain_id"], 0, len(s["data"])) for s in allocatable]
    relocs: list[tuple[object, ...]] = elf["relocations"]  # type: ignore[assignment]
    grid32 = digest_grid(executable, 4, 2)
    grid16 = digest_grid(executable, 2, 2)
    grid_literal = digest_grid(allocatable, 4, 1)
    csr: list[tuple[object, ...]] = []
    xw: list[tuple[object, ...]] = []
    forms: list[tuple[object, ...]] = []
    literals: list[tuple[object, ...]] = []
    relocation_sources: list[tuple[object, ...]] = []
    identity_csr: list[dict[str, object]] = []
    for sec in executable:
        body: bytes = sec["data"]  # type: ignore[assignment]
        domain = sec["domain_id"]
        for at in range(0, len(body) - 3, 2):
            word = integer(body[at:at + 4], "little")
            fields = csr_fields(word)
            if fields:
                csr_id, f3, rd, rs1 = fields
                csr.append((domain, at, word, csr_id, f3, rd, rs1))
                reads = f3 in (2, 3, 6, 7) or (f3 in (1, 5) and rd != 0)
                writes = f3 in (1, 5) or (f3 in (2, 3, 6, 7) and rs1 != 0)
                if csr_id in INTEREST_CSRS and reads:
                    identity_csr.append({
                        "domain_id": domain, "offset": at, "word": f"0x{word:08x}",
                        "csr": csr_id, "funct3": f3, "rd": rd, "rs1_or_zimm": rs1,
                        "hardware_read": reads, "hardware_write": writes, "gpr_result": rd != 0,
                    })
            opcode = word & 0x7F
            if opcode in (0x17, 0x37):
                forms.append((domain, at, word, opcode))
        for at in range(0, len(body) - 1, 2):
            halfword = integer(body[at:at + 2], "little")
            label = xw_name(halfword)
            if label:
                xw.append((domain, at, halfword, label))
    for sec in allocatable:
        body: bytes = sec["data"]  # type: ignore[assignment]
        domain = sec["domain_id"]
        for at in range(0, len(body) - 3):
            value = integer(body[at:at + 4], "little")
            if is_address(value):
                literals.append((domain, at, value))
    for record in relocs:
        symbol_name = str(record[8])
        if symbol_name and RELOC_SOURCE.search(symbol_name):
            relocation_sources.append((record[0], record[1], record[2], record[4], record[5], record[6], symbol_name, record[9]))
    candidates = {
        "csr-opcode": csr,
        "xw-slot": xw,
        "address-form-opcode": forms,
        "literal-pointer": literals,
        "relocation-source": relocation_sources,
    }
    compact.update({
        "exec_domain": {"units": sum(len(s["data"]) for s in executable), "records": exec_records, "set_sha256": set_digest(exec_records)},
        "alloc_domain": {"units": sum(len(s["data"]) for s in allocatable), "records": alloc_records, "set_sha256": set_digest(alloc_records)},
        "relocation_domain": {"units": len(relocs), "records": relocs, "set_sha256": set_digest(relocs)},
        "grids": {
            "exec-width4-step2": {"count": grid32[0], "set_sha256": grid32[1]},
            "exec-width2-step2": {"count": grid16[0], "set_sha256": grid16[1]},
            "alloc-width4-step1": {"count": grid_literal[0], "set_sha256": grid_literal[1]},
        },
        "candidate_counts": {name: len(rows) for name, rows in candidates.items()},
        "candidate_set_sha256": {name: set_digest(rows) for name, rows in candidates.items()},
        "identity_csr_reads": identity_csr,
    })
    return compact


def parse_hex(blob: bytes) -> tuple[dict[int, int], list[str], Counter[int]]:
    mem: dict[int, int] = {}
    errors: list[str] = []
    counts: Counter[int] = Counter()
    upper = 0
    ended = False
    for number, raw in enumerate(blob.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if ended:
            errors.append(f"after-eof:{number}")
        if line[:1] != b":":
            errors.append(f"colon:{number}")
            continue
        try:
            rec = bytes.fromhex(line[1:].decode("ascii"))
        except Exception:
            errors.append(f"hex:{number}")
            continue
        if len(rec) < 5 or len(rec) != rec[0] + 5:
            errors.append(f"length:{number}")
            continue
        if sum(rec) % 256:
            errors.append(f"checksum:{number}")
            continue
        amount = rec[0]
        low = integer(rec[1:3], "big")
        rtype = rec[3]
        body = rec[4:4 + amount]
        counts[rtype] += 1
        if rtype == 0:
            start = upper + low
            if start > 0xFFFFFFFF or start + amount > 0x100000000:
                errors.append(f"overflow:{number}")
                continue
            for delta, value in enumerate(body):
                address = start + delta
                if address in mem and mem[address] != value:
                    errors.append(f"conflict:{number}:0x{address:x}")
                mem[address] = value
        elif rtype == 1:
            if amount or low:
                errors.append(f"eof-shape:{number}")
            ended = True
        elif rtype == 2:
            if amount != 2 or low:
                errors.append(f"segment-shape:{number}")
            else:
                upper = integer(body, "big") << 4
        elif rtype == 4:
            if amount != 2 or low:
                errors.append(f"linear-shape:{number}")
            else:
                upper = integer(body, "big") << 16
        elif rtype in (3, 5):
            if amount != 4 or low:
                errors.append(f"start-shape:{number}")
        else:
            errors.append(f"type:{number}:{rtype}")
    if not ended:
        errors.append("missing-eof")
    return mem, errors, counts


def ranges(mem: dict[int, int]) -> list[tuple[int, int]]:
    addresses = sorted(mem)
    if not addresses:
        return []
    answer: list[tuple[int, int]] = []
    first = last = addresses[0]
    for address in addresses[1:]:
        if address != last + 1:
            answer.append((first, last + 1))
            first = address
        last = address
    answer.append((first, last + 1))
    return answer


def rom_hash(mem: dict[int, int]) -> str:
    digest = hashlib.sha256(b"wch-rom-address-byte-v2\0")
    for address in sorted(mem):
        digest.update(record_blob((address, mem[address])))
    return digest.hexdigest()


def rom_starts(mem: dict[int, int], width: int) -> tuple[list[tuple[int, int]], str]:
    output: list[tuple[int, int]] = []
    for begin, end in ranges(mem):
        at = begin + (-begin % 2)
        while at + width <= end:
            output.append((begin, at))
            at += 2
    return output, set_digest(output, ordered=True)


def independent_rom(path: str, blob: bytes) -> dict[str, object]:
    mem, errors, counts = parse_hex(blob)
    spans = ranges(mem)
    domain = [(f"range:0x{a:08x}", a, b - a) for a, b in spans]
    starts4, starts4_hash = rom_starts(mem, 4)
    starts2, starts2_hash = rom_starts(mem, 2)
    csr: list[tuple[object, ...]] = []
    xw: list[tuple[object, ...]] = []
    address: list[tuple[object, ...]] = []
    for origin, at in starts4:
        word = sum(mem[at + i] << (i * 8) for i in range(4))
        decoded = csr_fields(word)
        if decoded:
            csr_id, f3, rd, rs1 = decoded
            csr.append((f"range:0x{origin:08x}", at, word, csr_id, f3, rd, rs1))
        opcode = word & 0x7F
        if is_address(word) or opcode in (0x17, 0x37):
            address.append((f"range:0x{origin:08x}", at, word, opcode))
    for origin, at in starts2:
        hw = mem[at] | mem[at + 1] << 8
        label = xw_name(hw)
        if label:
            xw.append((f"range:0x{origin:08x}", at, hw, label))
    candidates = {"csr-opcode": csr, "xw-slot": xw, "address-or-literal": address}
    return {
        "physical_path": path,
        "raw_sha256": sha(blob),
        "normalized_sha256": rom_hash(mem),
        "parse_errors": errors,
        "record_type_counts": {str(k): counts[k] for k in sorted(counts)},
        "ranges": spans,
        "domain": {"units": len(mem), "records": domain, "set_sha256": set_digest(domain)},
        "grids": {
            "rom-width4-align2": {"count": len(starts4), "set_sha256": starts4_hash},
            "rom-width2-align2": {"count": len(starts2), "set_sha256": starts2_hash},
        },
        "candidate_counts": {name: len(rows) for name, rows in candidates.items()},
        "candidate_set_sha256": {name: set_digest(rows) for name, rows in candidates.items()},
    }


def discover(repo: pathlib.Path) -> tuple[list[pathlib.Path], list[pathlib.Path]]:
    binaries: dict[str, pathlib.Path] = {}
    roms: dict[str, pathlib.Path] = {}
    for spec in ROOT_SPECS:
        base = repo / spec
        for path in descend(base):
            path_rel = rel(repo, path)
            try:
                with path.open("rb") as stream:
                    head = stream.read(64)
            except OSError:
                continue
            k = kind(head)
            if k in ("ar", "thin-ar"):
                binaries[path_rel] = path
            elif k == "ELF":
                try:
                    header = path.read_bytes()
                except OSError:
                    continue
                parsed = parse_elf(header)
                if parsed["valid"] and parsed["etype"] == ET_REL:
                    binaries[path_rel] = path
            if spec == "tmp/wch-evt/evt" and path.suffix.lower() in (".hex", ".bin"):
                roms[path_rel] = path
    return ([binaries[k] for k in sorted(binaries, key=key8)], [roms[k] for k in sorted(roms, key=key8)])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-root", required=True)
    ns = ap.parse_args()
    repo = pathlib.Path.cwd().resolve()
    target = (repo / ns.run_root / "independent").resolve()
    target.mkdir(parents=True, exist_ok=True)
    binaries, rom_candidates = discover(repo)
    unit_cache: dict[str, dict[str, object]] = {}
    archive_cache: dict[str, tuple[list[dict[str, object]], dict[str, object]]] = {}
    occurrence_rows: list[dict[str, object]] = []
    archive_rows: list[dict[str, object]] = []
    archive_total = 0
    object_total = 0
    for number, path in enumerate(binaries, 1):
        path_rel = rel(repo, path)
        blob = path.read_bytes()
        raw_kind = kind(blob)
        raw_sha = sha(blob)
        if raw_kind in ("ar", "thin-ar"):
            archive_total += 1
            if raw_sha in archive_cache:
                members, summary = archive_cache[raw_sha]
            else:
                members, summary = parse_archive(path, blob)
                archive_cache[raw_sha] = (members, summary)
            archive_rows.append({"physical_path": path_rel, "archive_sha256": raw_sha, **summary})
            for member in members:
                payload: bytes | None = member["payload"]  # type: ignore[assignment]
                if payload is None:
                    msha = "unknown"
                    compact = {"magic": "unreadable-thin-member", "machine": "unknown", "elf_class": "unknown", "elf_errors": ["member-unreadable"]}
                else:
                    msha = sha(payload)
                    if msha not in unit_cache:
                        unit_cache[msha] = primitive_scan(payload)
                    compact = unit_cache[msha]
                occurrence_rows.append({
                    "physical_path": path_rel,
                    "logical_order": member["logical_order"],
                    "member_name": member["member_name"],
                    "same_name_ordinal": member["same_name_ordinal"],
                    "member_sha256": msha,
                    "member_size": len(payload) if payload is not None else "unknown",
                    "file_format": compact.get("magic", "unknown"),
                    "machine": compact.get("machine", "unknown"),
                    "elf_class": compact.get("elf_class", "unknown"),
                    "parse_errors": compact.get("elf_errors", []),
                })
        else:
            object_total += 1
            if raw_sha not in unit_cache:
                unit_cache[raw_sha] = primitive_scan(blob)
            compact = unit_cache[raw_sha]
            occurrence_rows.append({
                "physical_path": path_rel,
                "logical_order": "not-applicable",
                "member_name": "not-applicable",
                "same_name_ordinal": "not-applicable",
                "member_sha256": raw_sha,
                "member_size": len(blob),
                "file_format": compact.get("magic", "unknown"),
                "machine": compact.get("machine", "unknown"),
                "elf_class": compact.get("elf_class", "unknown"),
                "parse_errors": compact.get("elf_errors", []),
            })
        if number % 200 == 0:
            print(f"phase=independent-binary artifact={number}/{len(binaries)} units={len(unit_cache)}", flush=True)
    rom_rows = [independent_rom(rel(repo, p), p.read_bytes()) for p in rom_candidates if rel(repo, p) in ROM_BODIES]
    occurrence_rows.sort(key=lambda r: (key8(str(r["physical_path"])), -1 if r["logical_order"] == "not-applicable" else int(r["logical_order"]), key8(str(r["member_name"]))))
    archive_rows.sort(key=lambda r: key8(str(r["physical_path"])))
    rom_rows.sort(key=lambda r: key8(str(r["physical_path"])))
    safe_replace(target / "occurrences.jsonl", "".join(emit(row) + "\n" for row in occurrence_rows))
    safe_replace(target / "archive-summary.jsonl", "".join(emit(row) + "\n" for row in archive_rows))
    safe_replace(target / "unit-independent.jsonl", "".join(emit(unit_cache[k]) + "\n" for k in sorted(unit_cache)))
    safe_replace(target / "rom-independent.jsonl", "".join(emit(row) + "\n" for row in rom_rows))
    counts = {
        "binary_artifacts": len(binaries), "archives": archive_total, "standalone_objects": object_total,
        "occurrences": len(occurrence_rows), "unique_scan_units": len(unit_cache),
        "rom_candidates_discovered": len(rom_candidates), "rom_payloads_scanned": len(rom_rows),
    }
    safe_replace(target / "counts.json", json.dumps(counts, sort_keys=True, indent=2) + "\n")
    print(emit(counts), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
