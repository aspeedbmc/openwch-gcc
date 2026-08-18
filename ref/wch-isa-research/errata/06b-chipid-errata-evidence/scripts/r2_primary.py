#!/usr/bin/env python3
"""Second-round primary discovery and conservative binary scanner.

This program deliberately does not import any first-round audit code.  It
discovers artifacts by magic, preserves raw archive-member occurrence
semantics, parses ELF32/ELF64, validates Intel HEX, and emits byte-domain and
candidate sets.  Semantic lanes are conservative: a complete primitive scan
does not become an object-level no-ID claim when instruction/data-flow
semantics remain unresolved.

Run from the repository root:
  python3 <RUN_ROOT>/r2_primary.py --run-root <RUN_ROOT>
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import pathlib
import re
import stat
import struct
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Iterable, Iterator, Sequence


SCHEMA = "2"
EM_RISCV = 243
EM_ARM = 40
ET_REL = 1
SHT_PROGBITS = 1
SHT_SYMTAB = 2
SHT_RELA = 4
SHT_NOBITS = 8
SHT_REL = 9
SHT_DYNSYM = 11
SHF_ALLOC = 0x2
SHF_EXECINSTR = 0x4
SHN_XINDEX = 0xFFFF
RUN_PLACEHOLDER = "<RUN_ROOT>"

ID_CSRS = {0xF11, 0xF12, 0xF13, 0xF14, 0x301, 0xFC0}
KNOWN_ADDRESSES = {
    0x1FFFF704,
    0x1FFFF706,
    0x1FFFF7C4,
    0x1FFFF7E0,
    0x1FFFF884,
}

# Eight WCH-X compressed forms.  These masks are verified independently by
# the assembler fixture; their union contains 8,704 halfwords.
XW_FORMS = (
    ("c.lbu", 0x2000, 0xE003),
    ("c.lhu", 0x2002, 0xE003),
    ("c.sb", 0xA000, 0xE003),
    ("c.sh", 0xA002, 0xE003),
    ("c.lbusp", 0x8000, 0xF863),
    ("c.lhusp", 0x8020, 0xF863),
    ("c.sbsp", 0x8040, 0xF863),
    ("c.shsp", 0x8060, 0xF863),
)

KEYWORD_RE = re.compile(
    rb"(?i)(?:chip|cpu|device|devid|revid|revision|stepping|"
    rb"workaround|errata|compat(?:ibility)?|factory|unique[_ -]?(?:id|key)|"
    rb"mvendorid|marchid|mimpid|mhartid|cpuid|wa(?:_|$)|fix)"
)
SOURCE_NAME_RE = re.compile(
    r"(?i)(?:chip[_ -]?id|cpu[_ -]?id|cpuid|device[_ -]?id|devid|revid|"
    r"revision|stepping|mvendorid|marchid|mimpid|mhartid|factory|"
    r"unique[_ -]?(?:id|key)|getchipid|dbgmcu_get)"
)

WCH_CLOSED_BASENAMES = {
    "iqmath_rv32.a",
    "libiqmath_rv32.a",
    "libiqmath_rv32ec_zmmul_xw.a",
    "libprintf.a",
    "libprintfloat.a",
    "libshlib.a",
    "libshflib.a",
    "librv3ufi.a",
    "libuhsif.a",
    "libch58xble.a",
    "libwchble.a",
    "libmesh.a",
    "libmeshrom.a",
    "libwchlwns.a",
    "libch32h417_touch.a",
    "libch32v00x_touch.a",
    "libch32v205_touch_cs.a",
    "libch32v205_touch_ct.a",
    "libch587_touch.a",
    "libwchnet.a",
    "libwchnet_float.a",
    "libwchiochub.a",
    "libvoicercg.a",
    "libm12014sv_m007_lib_20250115.a",
    "libvoilent_fan_src-lib.a",
}

ROM_PAYLOADS = {
    "tmp/wch-evt/evt/QingkeV3C_CH587_EVT/EXAM/BLE/LIB/CH587BLE_ROMx.hex",
    "tmp/wch-evt/evt/QingkeV4B_CH32V203_EVT/EXAM/BLE/LIB/wchble_rom.hex",
    "tmp/wch-evt/evt/QingkeV4B_CH32V203_EVT/EXAM/BLE/MESH/MESH_LIB/wchble_rom_mesh.hex",
    "tmp/wch-evt/evt/QingkeV4C_CH32V20x_EVT/EXAM/BLE/LIB/wchble_rom.hex",
    "tmp/wch-evt/evt/QingkeV4C_CH32V20x_EVT/EXAM/BLE/MESH/MESH_LIB/wchble_rom_mesh.hex",
}

ROM_HEADERS = {
    "tmp/wch-evt/evt/QingkeV3C_CH587_EVT/EXAM/BLE/LIB/CH58xBLE_ROM.h",
    "tmp/wch-evt/evt/QingkeV4B_CH32V203_EVT/EXAM/BLE/LIB/wchble_rom.h",
    "tmp/wch-evt/evt/QingkeV4C_CH32V20x_EVT/EXAM/BLE/LIB/wchble_rom.h",
}

DISCOVERY_ROOTS = (
    ("mrs-2.4-riscv-gcc8", "MRS_Toolchain_MAC_V240/Toolchain/RISC-V Embedded GCC"),
    ("mrs-2.4-riscv-gcc12", "MRS_Toolchain_MAC_V240/Toolchain/RISC-V Embedded GCC12"),
    ("mrs-2.4-riscv-gcc15", "MRS_Toolchain_MAC_V240/Toolchain/RISC-V Embedded GCC15"),
    ("mrs-2.4-arm", "MRS_Toolchain_MAC_V240/Toolchain/arm-none-eabi-gcc"),
    ("mrs-2.5-macos-arm64-gcc8", "tmp/mrs-2.5/WCH/Toolchain/RISC-V Embedded GCC"),
    ("mrs-2.5-macos-arm64-gcc12", "tmp/mrs-2.5/WCH/Toolchain/RISC-V Embedded GCC12"),
    ("mrs-2.5-linux-x64-gcc15", "MRS_Toolchain_Linux_X64_V250/Toolchain/RISC-V Embedded GCC15"),
    ("evt", "tmp/wch-evt/evt"),
)

PACKAGE_PATH = "tmp/archives/MounRiver_Studio_MacOS_ARM64_V2.5.0.tar"


def utf8_key(value: str) -> bytes:
    return value.encode("utf-8", "surrogateescape")


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: pathlib.Path, chunk: int = 8 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def encode_record(fields: Sequence[object]) -> bytes:
    out = bytearray(struct.pack(">I", len(fields)))
    for value in fields:
        b = str(value).encode("utf-8", "surrogateescape")
        out += struct.pack(">Q", len(b))
        out += b
    return bytes(out)


def hash_records(records: Iterable[Sequence[object]], *, presorted: bool = False) -> str:
    seq = records if presorted else sorted(records, key=lambda r: tuple(utf8_key(str(x)) for x in r))
    h = hashlib.sha256(b"wch-audit-set-v2\0")
    for record in seq:
        h.update(encode_record(record))
    return h.hexdigest()


def rid(prefix: str, *parts: object) -> str:
    h = hashlib.sha256(b"wch-audit-id-v2\0")
    h.update(encode_record(parts))
    return f"{prefix}-{h.hexdigest()}"


def repo_rel(root: pathlib.Path, path: pathlib.Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def json_dump_line(obj: object) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def atomic_write_text(path: pathlib.Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp-r2")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def walk_files(path: pathlib.Path) -> Iterator[pathlib.Path]:
    if not path.exists():
        return
    for dirpath, dirnames, filenames in os.walk(path, followlinks=False):
        dirnames.sort(key=utf8_key)
        filenames.sort(key=utf8_key)
        base = pathlib.Path(dirpath)
        for name in filenames:
            p = base / name
            try:
                if p.is_file():
                    yield p
            except OSError:
                continue


def read_head(path: pathlib.Path, amount: int = 64) -> bytes:
    try:
        with path.open("rb") as f:
            return f.read(amount)
    except OSError:
        return b""


def magic_kind(head: bytes) -> str:
    if head.startswith(b"!<arch>\n"):
        return "ar"
    if head.startswith(b"!<thin>\n"):
        return "thin-ar"
    if head.startswith(b"\x7fELF"):
        return "ELF"
    if head[:4] in {
        b"\xfe\xed\xfa\xce", b"\xce\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xcf\xfa\xed\xfe",
        b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca",
    }:
        return "Mach-O"
    if head.startswith(b"BC\xc0\xde") or head.startswith(b"\xde\xc0\x17\x0b"):
        return "LLVM-bitcode"
    return "unknown"


def xw_form(hw: int) -> str | None:
    for name, match, mask in XW_FORMS:
        if hw & mask == match:
            return name
    return None


def address_candidate(value: int) -> bool:
    value &= 0xFFFFFFFF
    return (
        value in KNOWN_ADDRESSES
        or 0x1FFF0000 <= value < 0x20000000
        or 0x40000000 <= value < 0x60000000
        or 0xE0000000 <= value < 0xF0000000
    )


def infer_chip(path: str) -> str:
    for pattern, chip in (
        ("CH32H417", "CH32H417"), ("CH32V407", "CH32V407"),
        ("CH32V317", "CH32V317"), ("CH32V20x", "CH32V20X"),
        ("CH32V203", "CH32V203"), ("CH32V205", "CH32V205"),
        ("CH32V103", "CH32V103"), ("CH32V003", "CH32V003"),
        ("CH32V006", "CH32V006"), ("CH32X315", "CH32X315"),
        ("CH587", "CH587"), ("CH58", "CH58x"), ("CH641", "CH641"),
    ):
        if pattern.lower() in path.lower():
            return chip
    return "unknown"


def infer_abi(path: str, elf_class: int | None = None) -> str:
    low = path.lower()
    if "ilp32e" in low:
        return "ilp32e"
    if "ilp32f" in low:
        return "ilp32f"
    if "ilp32d" in low:
        return "ilp32d"
    if "ilp32" in low:
        return "ilp32"
    if elf_class == 2:
        return "elf64-abi-unknown"
    return "abi-unknown"


def infer_profile(path: str, attrs: bytes) -> str:
    text = attrs.decode("latin1", "ignore").lower()
    path_low = path.lower()
    for version in ("xw3p0", "xw2p2", "xw2p0", "xw1p0"):
        if version in text or version in path_low:
            return version
    if re.search(r"(?:^|[_\W])xw(?:$|[_\W])", text) or "xw" in path_low:
        return "xw-version-undeclared"
    return "xw-not-declared"


def family_for(path: str) -> str:
    name = pathlib.PurePosixPath(path).name.lower()
    low = path.lower()
    if "wchnet" in name:
        return "WCHNET"
    if "iochub" in name:
        return "IoCHub"
    if "iqmath" in name:
        return "IQMath"
    if name == "libprintf.a":
        return "printf"
    if name == "libprintfloat.a":
        return "printfloat"
    if name == "libshlib.a":
        return "sh"
    if name == "libshflib.a":
        return "shfloat"
    if "meshrom" in name or "rom_mesh" in low:
        return "Mesh ROM"
    if "mesh" in name:
        return "Mesh"
    if "ble" in name or "ble_rom" in low:
        return "BLE"
    if "touch" in name or "tky" in name:
        return "Touch"
    if "ufi" in name:
        return "RV3UFI"
    if "uhsif" in name:
        return "UHSIF"
    if "usb" in name:
        return "WCHUSB/other USB"
    if "lwns" in name:
        return "LWNS"
    if "voice" in name:
        return "VoiceRcg"
    if "m12014" in name or "voilent" in name:
        return "Motor"
    if "rom" in name:
        return "ROM candidate"
    if name.startswith("libgcc") or name.startswith("libc.") or name in {"libc.a", "libm.a"}:
        return "generic-runtime-candidate"
    return "other target artifact"


def source_set_for(path: str) -> str:
    for source_set, prefix in DISCOVERY_ROOTS:
        if path == prefix or path.startswith(prefix + "/"):
            return source_set
    if path == PACKAGE_PATH:
        return "mrs-2.5-macos-arm64-package"
    return "unknown"


def is_wch_closed(path: str) -> bool:
    return pathlib.PurePosixPath(path).name.lower() in WCH_CLOSED_BASENAMES


def build_context_label(path: str) -> str:
    parts = pathlib.PurePosixPath(path).parts
    for part in parts:
        if part.endswith("_EVT"):
            return rid("buildctx", part)
    return rid("buildctx", source_set_for(path), infer_abi(path))


@dataclass
class ArMember:
    raw_index: int
    logical_order: int
    same_name_ordinal: int
    name: str
    raw_name: str
    metadata: bool
    payload: bytes | None
    external_path: str | None
    declared_size: int
    header_offset: int


@dataclass
class ArParse:
    thin: bool
    members: list[ArMember]
    errors: list[str]
    trailing_bytes: int


def parse_ar_primary(path: pathlib.Path, data: bytes) -> ArParse:
    """Parse regular/GNU/BSD/thin ar without using vendor ar output."""
    if data.startswith(b"!<thin>\n"):
        thin = True
    elif data.startswith(b"!<arch>\n"):
        thin = False
    else:
        return ArParse(False, [], ["bad-magic"], len(data))
    off = 8
    raw_index = 0
    logical_order = 0
    ordinals: Counter[str] = Counter()
    longnames = b""
    members: list[ArMember] = []
    errors: list[str] = []
    while off < len(data):
        if off + 60 > len(data):
            errors.append(f"truncated-header@{off}")
            break
        hdr = data[off:off + 60]
        if hdr[58:60] != b"`\n":
            errors.append(f"bad-header-terminator@{off}")
            break
        raw_index += 1
        raw_name = hdr[:16].decode("utf-8", "surrogateescape").rstrip(" ")
        raw_size = hdr[48:58].decode("ascii", "replace").strip()
        if not raw_size.isdigit():
            errors.append(f"bad-size@{off}:{raw_size}")
            break
        declared = int(raw_size)
        body_at = off + 60
        metadata_name = raw_name in {"/", "//", "/SYM64/"} or raw_name.startswith("__.SYMDEF")
        embedded_len = declared
        if thin and not metadata_name:
            embedded_len = 0
            if raw_name.startswith("#1/"):
                try:
                    embedded_len = int(raw_name[3:].strip())
                except ValueError:
                    errors.append(f"bad-bsd-name-length@{off}")
                    break
        body_end = body_at + embedded_len
        if body_end > len(data):
            errors.append(f"truncated-body@{off}")
            break
        embedded = data[body_at:body_end]

        name = raw_name.rstrip("/")
        payload: bytes | None = None
        external: str | None = None
        metadata = metadata_name
        if raw_name == "//":
            longnames = embedded
        elif raw_name.startswith("/") and raw_name[1:].isdigit():
            index = int(raw_name[1:])
            if index >= len(longnames):
                errors.append(f"long-name-offset-out-of-range@{off}:{index}")
                name = f"<bad-long-name-{index}>"
            else:
                end = longnames.find(b"/\n", index)
                if end < 0:
                    end = longnames.find(b"\n", index)
                if end < 0:
                    end = len(longnames)
                name = longnames[index:end].decode("utf-8", "surrogateescape").rstrip("/")
            metadata = False
        elif raw_name.startswith("#1/"):
            nlen = int(raw_name[3:].strip())
            if nlen > len(embedded) and not thin:
                errors.append(f"bsd-name-out-of-range@{off}")
                nlen = len(embedded)
            name = embedded[:nlen].decode("utf-8", "surrogateescape").rstrip("\0")
            embedded = embedded[nlen:] if not thin else b""
            metadata = name.startswith("__.SYMDEF")
        elif raw_name.endswith("/"):
            name = raw_name[:-1]

        if not metadata:
            logical_order += 1
            ordinals[name] += 1
            if thin:
                external = name
                target = pathlib.Path(name)
                if not target.is_absolute():
                    target = path.parent / target
                try:
                    payload = target.read_bytes()
                except OSError as exc:
                    errors.append(f"thin-member-read:{logical_order}:{type(exc).__name__}")
            else:
                payload = embedded
        else:
            payload = embedded
        members.append(ArMember(
            raw_index=raw_index,
            logical_order=logical_order if not metadata else 0,
            same_name_ordinal=ordinals[name] if not metadata else 0,
            name=name,
            raw_name=raw_name,
            metadata=metadata,
            payload=payload,
            external_path=external,
            declared_size=declared,
            header_offset=off,
        ))
        off = body_end + (embedded_len & 1)
    return ArParse(thin, members, errors, len(data) - off if off <= len(data) else 0)


@dataclass
class Section:
    index: int
    name: str
    typ: int
    flags: int
    addr: int
    offset: int
    size: int
    link: int
    info: int
    align: int
    entsize: int
    data: bytes

    @property
    def domain_id(self) -> str:
        return f"section:{self.index}:{self.name}"


@dataclass
class Symbol:
    table_section: int
    index: int
    name: str
    value: int
    size: int
    info: int
    other: int
    shndx: int


@dataclass
class Relocation:
    reloc_section: int
    reloc_name: str
    target_section: int
    target_name: str
    entry_index: int
    offset: int
    typ: int
    symbol_index: int
    symbol_name: str
    addend: int | str

    def record(self) -> tuple[object, ...]:
        return (
            self.target_section, self.target_name, self.reloc_section,
            self.reloc_name, self.entry_index, self.offset, self.typ,
            self.symbol_index, self.symbol_name, self.addend,
        )


class ELFPrimary:
    def __init__(self, data: bytes):
        self.data = data
        self.valid = False
        self.errors: list[str] = []
        self.elf_class = 0
        self.endian = "unknown"
        self.etype = 0
        self.machine = 0
        self.entry = 0
        self.sections: list[Section] = []
        self.symbols: list[Symbol] = []
        self.relocations: list[Relocation] = []
        self.attrs = b""
        self._parse()

    def _parse(self) -> None:
        d = self.data
        if len(d) < 16 or d[:4] != b"\x7fELF":
            self.errors.append("not-elf")
            return
        self.elf_class = d[4]
        ei_data = d[5]
        if self.elf_class not in (1, 2) or ei_data not in (1, 2):
            self.errors.append("unsupported-ident")
            return
        self.endian = "little" if ei_data == 1 else "big"
        e = "<" if ei_data == 1 else ">"
        try:
            self.etype, self.machine = struct.unpack_from(e + "HH", d, 16)
            if self.elf_class == 1:
                if len(d) < 52:
                    raise struct.error
                self.entry = struct.unpack_from(e + "I", d, 24)[0]
                shoff = struct.unpack_from(e + "I", d, 32)[0]
                shentsize, shnum_raw, shstr_raw = struct.unpack_from(e + "HHH", d, 46)
                shfmt = e + "IIIIIIIIII"
            else:
                if len(d) < 64:
                    raise struct.error
                self.entry = struct.unpack_from(e + "Q", d, 24)[0]
                shoff = struct.unpack_from(e + "Q", d, 40)[0]
                shentsize, shnum_raw, shstr_raw = struct.unpack_from(e + "HHH", d, 58)
                shfmt = e + "IIQQQQIIQQ"
        except struct.error:
            self.errors.append("truncated-elf-header")
            return
        shcalc = struct.calcsize(shfmt)
        if shoff == 0:
            self.valid = True
            return
        if shentsize < shcalc or shoff + shentsize > len(d):
            self.errors.append("bad-section-table")
            return

        def raw_sh(index: int) -> tuple[int, ...] | None:
            at = shoff + index * shentsize
            if at + shcalc > len(d):
                return None
            return struct.unpack_from(shfmt, d, at)

        zero = raw_sh(0)
        if zero is None:
            self.errors.append("missing-section-zero")
            return
        shnum = int(zero[5]) if shnum_raw == 0 else shnum_raw
        shstr = int(zero[6]) if shstr_raw == SHN_XINDEX else shstr_raw
        if shnum <= 0 or shnum > 1_000_000:
            self.errors.append(f"invalid-section-count:{shnum}")
            return
        raws: list[tuple[int, ...]] = []
        for index in range(shnum):
            row = raw_sh(index)
            if row is None:
                self.errors.append(f"truncated-section-header:{index}")
                return
            raws.append(row)
        if not (0 <= shstr < len(raws)):
            self.errors.append(f"bad-shstr-index:{shstr}")
            return
        strrow = raws[shstr]
        st_off, st_size = int(strrow[4]), int(strrow[5])
        if st_off > len(d) or st_size > len(d) - st_off:
            self.errors.append("bad-shstr-range")
            return
        shstrings = d[st_off:st_off + st_size]

        for index, row in enumerate(raws):
            name_at, typ, flags, addr, off, size, link, info, align, entsize = map(int, row)
            if name_at < len(shstrings):
                end = shstrings.find(b"\0", name_at)
                if end < 0:
                    end = len(shstrings)
                name = shstrings[name_at:end].decode("utf-8", "surrogateescape")
            else:
                name = f"<bad-name-{index}>"
                self.errors.append(f"section-name-out-of-range:{index}")
            if typ == SHT_NOBITS:
                body = b""
            elif off <= len(d) and size <= len(d) - off:
                body = d[off:off + size]
            else:
                body = b""
                self.errors.append(f"section-range:{index}:{name}")
            sec = Section(index, name, typ, flags, addr, off, size, link, info, align, entsize, body)
            self.sections.append(sec)
            if name == ".riscv.attributes":
                self.attrs = body
        self._parse_symbols(e)
        self._parse_relocations(e)
        self.valid = True

    def _parse_symbols(self, e: str) -> None:
        d = self.data
        for sec in self.sections:
            if sec.typ not in (SHT_SYMTAB, SHT_DYNSYM) or not sec.data:
                continue
            if not (0 <= sec.link < len(self.sections)):
                self.errors.append(f"symbol-bad-strtab:{sec.index}")
                continue
            strings = self.sections[sec.link].data
            expected = 16 if self.elf_class == 1 else 24
            entsize = sec.entsize or expected
            if entsize < expected or len(sec.data) % entsize:
                self.errors.append(f"symbol-entry-shape:{sec.index}")
            count = len(sec.data) // entsize
            for idx in range(count):
                at = idx * entsize
                try:
                    if self.elf_class == 1:
                        name_at, value, size, info, other, shndx = struct.unpack_from(e + "IIIBBH", sec.data, at)
                    else:
                        name_at, info, other, shndx, value, size = struct.unpack_from(e + "IBBHQQ", sec.data, at)
                except struct.error:
                    self.errors.append(f"symbol-truncated:{sec.index}:{idx}")
                    break
                if name_at < len(strings):
                    end = strings.find(b"\0", name_at)
                    if end < 0:
                        end = len(strings)
                    name = strings[name_at:end].decode("utf-8", "surrogateescape")
                else:
                    name = f"<bad-symbol-name-{name_at}>"
                self.symbols.append(Symbol(sec.index, idx, name, value, size, info, other, shndx))

    def _parse_relocations(self, e: str) -> None:
        symbols_by_table: dict[int, dict[int, Symbol]] = defaultdict(dict)
        for sym in self.symbols:
            symbols_by_table[sym.table_section][sym.index] = sym
        for sec in self.sections:
            if sec.typ not in (SHT_REL, SHT_RELA) or not sec.data:
                continue
            target = self.sections[sec.info] if 0 <= sec.info < len(self.sections) else None
            if target is None:
                self.errors.append(f"reloc-bad-target:{sec.index}")
            if self.elf_class == 1:
                fmt = e + ("IIi" if sec.typ == SHT_RELA else "II")
            else:
                fmt = e + ("QQq" if sec.typ == SHT_RELA else "QQ")
            expected = struct.calcsize(fmt)
            entsize = sec.entsize or expected
            if entsize < expected or len(sec.data) % entsize:
                self.errors.append(f"reloc-entry-shape:{sec.index}")
            for idx in range(len(sec.data) // entsize):
                at = idx * entsize
                try:
                    vals = struct.unpack_from(fmt, sec.data, at)
                except struct.error:
                    self.errors.append(f"reloc-truncated:{sec.index}:{idx}")
                    break
                offset, info = int(vals[0]), int(vals[1])
                addend: int | str = int(vals[2]) if sec.typ == SHT_RELA else "implicit"
                if self.elf_class == 1:
                    sym_index, typ = info >> 8, info & 0xFF
                else:
                    sym_index, typ = info >> 32, info & 0xFFFFFFFF
                sym = symbols_by_table.get(sec.link, {}).get(sym_index)
                self.relocations.append(Relocation(
                    sec.index, sec.name,
                    target.index if target else -1, target.name if target else "<bad-target>",
                    idx, offset, typ, sym_index, sym.name if sym else "", addend,
                ))

    def exec_sections(self) -> list[Section]:
        return [s for s in self.sections if s.typ != SHT_NOBITS and s.flags & SHF_EXECINSTR and s.data]

    def alloc_sections(self) -> list[Section]:
        return [s for s in self.sections if s.typ != SHT_NOBITS and s.flags & SHF_ALLOC and s.data]


def parcel_length(data: bytes, off: int) -> tuple[int | None, str]:
    if off + 2 > len(data):
        return None, "truncated-first-parcel"
    hw = int.from_bytes(data[off:off + 2], "little")
    if hw & 0x3 != 0x3:
        return 2, "known"
    if (hw >> 2) & 0x7 != 0x7:
        return 4, "known"
    if ((hw >> 5) & 0x1) == 0:
        return 6, "known"
    if ((hw >> 6) & 0x1) == 0:
        return 8, "known"
    nnn = (hw >> 12) & 0x7
    if nnn != 0x7:
        return 10 + 2 * nnn, "known"
    return None, "reserved-ge-192"


def iter_grid(sections: Sequence[Section], width: int, step: int) -> Iterator[tuple[str, int]]:
    for sec in sorted(sections, key=lambda s: (s.index, utf8_key(s.name))):
        stop = len(sec.data) - width
        if stop < 0:
            continue
        for off in range(0, stop + 1, step):
            yield sec.domain_id, off


def hash_grid(sections: Sequence[Section], width: int, step: int) -> tuple[int, str]:
    h = hashlib.sha256(b"wch-audit-set-v2\0")
    count = 0
    for domain_id, off in iter_grid(sections, width, step):
        h.update(encode_record((domain_id, off)))
        count += 1
    return count, h.hexdigest()


def candidate_set_hash(candidates: Sequence[Sequence[object]]) -> str:
    return hash_records(candidates)


def decode_csr(word: int) -> dict[str, object] | None:
    if word & 0x7F != 0x73:
        return None
    funct3 = (word >> 12) & 0x7
    if funct3 == 0:
        return None
    rd = (word >> 7) & 0x1F
    rs1 = (word >> 15) & 0x1F
    csr = (word >> 20) & 0xFFF
    reads = funct3 in (2, 3, 6, 7) or (funct3 in (1, 5) and rd != 0)
    writes = funct3 in (1, 5) or (funct3 in (2, 3, 6, 7) and rs1 != 0)
    return {
        "csr": csr,
        "funct3": funct3,
        "rd": rd,
        "rs1_or_zimm": rs1,
        "hardware_read": reads,
        "hardware_write": writes,
        "gpr_result": rd != 0,
        "identity_or_capability": csr in ID_CSRS and reads,
    }


def addi_imm(word: int) -> int:
    value = (word >> 20) & 0xFFF
    return value - 0x1000 if value & 0x800 else value


def scan_metadata(elf: ELFPrimary) -> list[tuple[object, ...]]:
    candidates: set[tuple[object, ...]] = set()
    for sym in elf.symbols:
        if sym.name and KEYWORD_RE.search(sym.name.encode("utf-8", "surrogateescape")):
            candidates.add(("symbol", sym.table_section, sym.index, sym.name))
    for sec in elf.sections:
        if sec.name and KEYWORD_RE.search(sec.name.encode("utf-8", "surrogateescape")):
            candidates.add(("section-name", sec.index, 0, sec.name))
    # Scan printable strings section-by-section so every candidate has a stable
    # physical section offset and no file-layout padding is mistaken for text.
    printable = re.compile(rb"[\x20-\x7e]{4,}")
    for sec in elf.sections:
        if not sec.data:
            continue
        for match in printable.finditer(sec.data):
            value = match.group(0)
            if KEYWORD_RE.search(value):
                candidates.add(("string", sec.index, match.start(), value.decode("ascii", "replace")))
    for rel in elf.relocations:
        if rel.symbol_name and KEYWORD_RE.search(rel.symbol_name.encode("utf-8", "surrogateescape")):
            candidates.add(("relocation-symbol", rel.reloc_section, rel.entry_index, rel.symbol_name))
    return sorted(candidates, key=lambda r: tuple(utf8_key(str(x)) for x in r))


def scan_exec_candidates(elf: ELFPrimary) -> dict[str, object]:
    exec_secs = elf.exec_sections()
    csr_candidates: list[tuple[object, ...]] = []
    xw_candidates: list[tuple[object, ...]] = []
    address_forms: list[tuple[object, ...]] = []
    semantic_sources: list[dict[str, object]] = []
    framing_hist: Counter[int] = Counter()
    boundary_known = 0
    boundary_ambiguous = 0
    decoded = 0
    classified_noncode = 0

    # Primitive grids are a deliberate superset of real instruction starts.
    for sec in exec_secs:
        for off in range(0, max(0, len(sec.data) - 3), 2):
            if off + 4 > len(sec.data):
                break
            word = int.from_bytes(sec.data[off:off + 4], "little")
            csr = decode_csr(word)
            if csr is not None:
                csr_candidates.append((sec.domain_id, off, word, csr["csr"], csr["funct3"], csr["rd"], csr["rs1_or_zimm"]))
            opcode = word & 0x7F
            if opcode in (0x17, 0x37):
                address_forms.append((sec.domain_id, off, word, opcode))
        for off in range(0, max(0, len(sec.data) - 1), 2):
            if off + 2 > len(sec.data):
                break
            hw = int.from_bytes(sec.data[off:off + 2], "little")
            form = xw_form(hw)
            if form:
                xw_candidates.append((sec.domain_id, off, hw, form))

        # Conservative linear framing and a bounded value tracker.  The
        # tracker discovers candidates but is not claimed as a complete CFG.
        regs: list[int | None] = [None] * 32
        regs[0] = 0
        off = 0
        while off < len(sec.data):
            length, why = parcel_length(sec.data, off)
            if length is None or off + length > len(sec.data):
                boundary_ambiguous += len(sec.data) - off
                break
            framing_hist[length] += 1
            boundary_known += length
            if length == 4:
                word = int.from_bytes(sec.data[off:off + 4], "little")
                opcode = word & 0x7F
                rd = (word >> 7) & 0x1F
                rs1 = (word >> 15) & 0x1F
                rs2 = (word >> 20) & 0x1F
                funct3 = (word >> 12) & 7
                if opcode == 0x37:  # LUI, sign-extended on RV32
                    value = word & 0xFFFFF000
                    regs[rd] = value if rd else 0
                elif opcode == 0x17:  # AUIPC needs final placement/relocation
                    regs[rd] = None if rd else 0
                elif opcode == 0x13 and funct3 == 0:  # ADDI
                    regs[rd] = ((regs[rs1] + addi_imm(word)) & 0xFFFFFFFF) if regs[rs1] is not None else None
                elif opcode == 0x13 and funct3 == 6:  # ORI
                    regs[rd] = ((regs[rs1] | (addi_imm(word) & 0xFFFFFFFF)) & 0xFFFFFFFF) if regs[rs1] is not None else None
                elif opcode == 0x13 and funct3 == 7:  # ANDI
                    regs[rd] = ((regs[rs1] & (addi_imm(word) & 0xFFFFFFFF)) & 0xFFFFFFFF) if regs[rs1] is not None else None
                elif opcode == 0x33 and funct3 == 0 and ((word >> 25) & 0x7F) == 0:
                    regs[rd] = ((regs[rs1] + regs[rs2]) & 0xFFFFFFFF) if regs[rs1] is not None and regs[rs2] is not None else None
                elif opcode == 0x33 and funct3 == 6:
                    regs[rd] = ((regs[rs1] | regs[rs2]) & 0xFFFFFFFF) if regs[rs1] is not None and regs[rs2] is not None else None
                elif opcode == 0x03:  # integer load
                    base = regs[rs1]
                    effective = ((base + addi_imm(word)) & 0xFFFFFFFF) if base is not None else None
                    if effective is not None and address_candidate(effective):
                        semantic_sources.append({
                            "kind": "absolute-load",
                            "section": sec.name,
                            "section_index": sec.index,
                            "offset": off,
                            "word": f"0x{word:08x}",
                            "address": f"0x{effective:08x}",
                            "funct3": funct3,
                            "rd": rd,
                            "rs1": rs1,
                        })
                    regs[rd] = None if rd else 0
                else:
                    # Calls, branches, stores and unknown operations terminate
                    # only affected register facts; this remains a candidate
                    # finder, never a completeness claim.
                    if rd and opcode in (0x03, 0x07, 0x0F, 0x1B, 0x2F, 0x33, 0x3B, 0x67, 0x6F, 0x73):
                        regs[rd] = None
                csr = decode_csr(word)
                if csr and csr["identity_or_capability"]:
                    semantic_sources.append({
                        "kind": "identity-csr-read",
                        "section": sec.name,
                        "section_index": sec.index,
                        "offset": off,
                        "word": f"0x{word:08x}",
                        **csr,
                    })
            off += length

    return {
        "csr_candidates": csr_candidates,
        "xw_candidates": xw_candidates,
        "address_form_candidates": address_forms,
        "semantic_sources": semantic_sources,
        "coverage": {
            "semantic_decoded_code_bytes": decoded,
            "boundary_known_semantic_unresolved_bytes": boundary_known,
            "classified_noncode_or_padding_bytes": classified_noncode,
            "boundary_ambiguous_bytes": boundary_ambiguous,
            "executable_bytes": sum(len(s.data) for s in exec_secs),
            "framing_length_histogram": {str(k): framing_hist[k] for k in sorted(framing_hist)},
        },
    }


def scan_literals(elf: ELFPrimary) -> list[tuple[object, ...]]:
    out: list[tuple[object, ...]] = []
    for sec in elf.alloc_sections():
        for off in range(0, max(0, len(sec.data) - 3)):
            if off + 4 > len(sec.data):
                break
            value = int.from_bytes(sec.data[off:off + 4], "little")
            if address_candidate(value):
                out.append((sec.domain_id, off, value))
    return out


def scan_relocation_sources(elf: ELFPrimary) -> list[tuple[object, ...]]:
    return [
        (r.target_section, r.target_name, r.reloc_section, r.entry_index, r.offset, r.typ, r.symbol_name, r.addend)
        for r in elf.relocations
        if r.symbol_name and SOURCE_NAME_RE.search(r.symbol_name)
    ]


def unit_scan_primary(data: bytes) -> dict[str, object]:
    sha = sha_bytes(data)
    elf = ELFPrimary(data)
    base: dict[str, object] = {
        "scan_unit_sha256": sha,
        "file_size": len(data),
        "magic": magic_kind(data[:64]),
        "elf_valid": elf.valid,
        "elf_errors": elf.errors,
        "elf_class": elf.elf_class,
        "endian": elf.endian,
        "etype": elf.etype,
        "machine": elf.machine,
    }
    if not elf.valid or elf.machine != EM_RISCV or elf.endian != "little":
        base["native_scan_applicable"] = False
        return base
    base["native_scan_applicable"] = True
    exec_secs = elf.exec_sections()
    alloc_secs = elf.alloc_sections()
    exec_records = [(s.domain_id, 0, len(s.data)) for s in exec_secs]
    alloc_records = [(s.domain_id, 0, len(s.data)) for s in alloc_secs]
    reloc_records = [r.record() for r in elf.relocations]
    grid32_n, grid32_sha = hash_grid(exec_secs, 4, 2)
    grid16_n, grid16_sha = hash_grid(exec_secs, 2, 2)
    literal_grid_n, literal_grid_sha = hash_grid(alloc_secs, 4, 1)
    exec_scan = scan_exec_candidates(elf)
    metadata = scan_metadata(elf)
    literals = scan_literals(elf)
    relocation_sources = scan_relocation_sources(elf)
    csr = exec_scan["csr_candidates"]
    xw = exec_scan["xw_candidates"]
    address_forms = exec_scan["address_form_candidates"]
    base.update({
        "attrs_hex": elf.attrs.hex(),
        "exec_domain": {
            "units": sum(len(s.data) for s in exec_secs),
            "records": exec_records,
            "set_sha256": hash_records(exec_records),
        },
        "alloc_domain": {
            "units": sum(len(s.data) for s in alloc_secs),
            "records": alloc_records,
            "set_sha256": hash_records(alloc_records),
        },
        "relocation_domain": {
            "units": len(reloc_records),
            "records": reloc_records,
            "set_sha256": hash_records(reloc_records),
        },
        "grids": {
            "exec-width4-step2": {"count": grid32_n, "set_sha256": grid32_sha},
            "exec-width2-step2": {"count": grid16_n, "set_sha256": grid16_sha},
            "alloc-width4-step1": {"count": literal_grid_n, "set_sha256": literal_grid_sha},
        },
        "candidates": {
            "symbol-string-debug": metadata,
            "csr-opcode": csr,
            "xw-slot": xw,
            "address-form-opcode": address_forms,
            "literal-pointer": literals,
            "relocation-source": relocation_sources,
        },
        "candidate_set_sha256": {
            "symbol-string-debug": candidate_set_hash(metadata),
            "csr-opcode": candidate_set_hash(csr),
            "xw-slot": candidate_set_hash(xw),
            "address-form-opcode": candidate_set_hash(address_forms),
            "literal-pointer": candidate_set_hash(literals),
            "relocation-source": candidate_set_hash(relocation_sources),
        },
        "semantic_sources": exec_scan["semantic_sources"],
        "coverage": exec_scan["coverage"],
    })
    return base


@dataclass
class HexParse:
    memory: dict[int, int]
    records: Counter[int]
    errors: list[str]
    eof_seen: bool
    start_linear: int | None
    start_segment: tuple[int, int] | None


def parse_ihex_primary(data: bytes) -> HexParse:
    memory: dict[int, int] = {}
    records: Counter[int] = Counter()
    errors: list[str] = []
    base = 0
    eof = False
    start_linear: int | None = None
    start_segment: tuple[int, int] | None = None
    for lineno, raw in enumerate(data.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if eof:
            errors.append(f"data-after-eof:{lineno}")
        if not line.startswith(b":"):
            errors.append(f"missing-colon:{lineno}")
            continue
        try:
            rec = bytes.fromhex(line[1:].decode("ascii"))
        except (ValueError, UnicodeDecodeError):
            errors.append(f"bad-hex:{lineno}")
            continue
        if len(rec) < 5:
            errors.append(f"short-record:{lineno}")
            continue
        count = rec[0]
        if len(rec) != count + 5:
            errors.append(f"length:{lineno}:{len(rec)}:{count}")
            continue
        if sum(rec) & 0xFF:
            errors.append(f"checksum:{lineno}")
            continue
        offset = int.from_bytes(rec[1:3], "big")
        typ = rec[3]
        payload = rec[4:4 + count]
        records[typ] += 1
        if typ == 0:
            absolute = base + offset
            if absolute > 0xFFFFFFFF or absolute + count > 0x100000000:
                errors.append(f"address-overflow:{lineno}")
                continue
            for i, value in enumerate(payload):
                addr = absolute + i
                old = memory.get(addr)
                if old is not None and old != value:
                    errors.append(f"address-conflict:{lineno}:0x{addr:x}:{old}:{value}")
                memory[addr] = value
        elif typ == 1:
            if count != 0 or offset != 0:
                errors.append(f"bad-eof:{lineno}")
            eof = True
        elif typ == 2:
            if count != 2 or offset != 0:
                errors.append(f"bad-esa:{lineno}")
            else:
                base = int.from_bytes(payload, "big") << 4
        elif typ == 3:
            if count != 4 or offset != 0:
                errors.append(f"bad-start-segment:{lineno}")
            else:
                start_segment = (int.from_bytes(payload[:2], "big"), int.from_bytes(payload[2:], "big"))
        elif typ == 4:
            if count != 2 or offset != 0:
                errors.append(f"bad-ela:{lineno}")
            else:
                base = int.from_bytes(payload, "big") << 16
        elif typ == 5:
            if count != 4 or offset != 0:
                errors.append(f"bad-start-linear:{lineno}")
            else:
                start_linear = int.from_bytes(payload, "big")
        else:
            errors.append(f"unknown-record-type:{lineno}:{typ}")
    if not eof:
        errors.append("missing-eof")
    return HexParse(memory, records, errors, eof, start_linear, start_segment)


def memory_ranges(memory: dict[int, int]) -> list[tuple[int, int]]:
    if not memory:
        return []
    keys = sorted(memory)
    out: list[tuple[int, int]] = []
    start = prev = keys[0]
    for addr in keys[1:]:
        if addr != prev + 1:
            out.append((start, prev + 1))
            start = addr
        prev = addr
    out.append((start, prev + 1))
    return out


def normalized_memory_hash(memory: dict[int, int]) -> str:
    h = hashlib.sha256(b"wch-rom-address-byte-v2\0")
    for addr in sorted(memory):
        h.update(encode_record((addr, memory[addr])))
    return h.hexdigest()


def rom_grid(memory: dict[int, int], width: int, alignment: int = 2) -> tuple[list[tuple[int, int]], str]:
    starts: list[tuple[int, int]] = []
    for begin, end in memory_ranges(memory):
        at = begin + ((-begin) % alignment)
        while at + width <= end:
            starts.append((begin, at))
            at += alignment
    return starts, hash_records(starts, presorted=True)


def rom_scan_primary(data: bytes) -> dict[str, object]:
    parsed = parse_ihex_primary(data)
    ranges = memory_ranges(parsed.memory)
    domain_records = [(f"range:0x{start:08x}", start, end - start) for start, end in ranges]
    grid4, grid4_sha = rom_grid(parsed.memory, 4)
    grid2, grid2_sha = rom_grid(parsed.memory, 2)
    csr: list[tuple[object, ...]] = []
    xw: list[tuple[object, ...]] = []
    address: list[tuple[object, ...]] = []
    for range_start, at in grid4:
        word = sum(parsed.memory[at + i] << (8 * i) for i in range(4))
        c = decode_csr(word)
        if c:
            csr.append((f"range:0x{range_start:08x}", at, word, c["csr"], c["funct3"], c["rd"], c["rs1_or_zimm"]))
        opcode = word & 0x7F
        if address_candidate(word) or opcode in (0x17, 0x37):
            address.append((f"range:0x{range_start:08x}", at, word, opcode))
    for range_start, at in grid2:
        hw = parsed.memory[at] | (parsed.memory[at + 1] << 8)
        form = xw_form(hw)
        if form:
            xw.append((f"range:0x{range_start:08x}", at, hw, form))
    return {
        "parse_errors": parsed.errors,
        "record_type_counts": {str(k): parsed.records[k] for k in sorted(parsed.records)},
        "eof_seen": parsed.eof_seen,
        "start_linear": parsed.start_linear,
        "start_segment": parsed.start_segment,
        "normalized_sha256": normalized_memory_hash(parsed.memory),
        "ranges": ranges,
        "domain": {
            "units": len(parsed.memory),
            "records": domain_records,
            "set_sha256": hash_records(domain_records),
        },
        "grids": {
            "rom-width4-align2": {"count": len(grid4), "set_sha256": grid4_sha},
            "rom-width2-align2": {"count": len(grid2), "set_sha256": grid2_sha},
        },
        "candidates": {"csr-opcode": csr, "xw-slot": xw, "address-or-literal": address},
        "candidate_set_sha256": {
            "csr-opcode": candidate_set_hash(csr),
            "xw-slot": candidate_set_hash(xw),
            "address-or-literal": candidate_set_hash(address),
        },
    }


def classify_archive(path: str, logical: Sequence[dict[str, object]]) -> tuple[str, str]:
    machines = Counter(str(x.get("machine", "unknown")) for x in logical if x.get("file_format") == "ELF")
    formats = Counter(str(x.get("file_format", "unknown")) for x in logical)
    name = pathlib.PurePosixPath(path).name.lower()
    if name == "libmeshrom.a":
        return "rom-wrapper", "rom-wrapper-archive"
    if is_wch_closed(path):
        return "wch-closed", "target-archive"
    if machines and set(machines) == {str(EM_ARM)}:
        return "foreign-target", "foreign-target-archive"
    if machines and str(EM_RISCV) in machines:
        return "unknown-provenance", "target-archive"
    if formats and all(k == "Mach-O" for k in formats):
        return "host", "host-archive"
    return "unknown-provenance", "unresolved-archive"


def classify_standalone(path: str, elf: ELFPrimary) -> tuple[str, str]:
    if elf.valid and elf.machine == EM_RISCV:
        return ("wch-closed" if is_wch_closed(path) else "unknown-provenance", "standalone-object")
    if elf.valid and elf.machine == EM_ARM:
        return "foreign-target", "standalone-object"
    return "host", "host-object"


def discovery_candidates(root: pathlib.Path) -> tuple[list[tuple[str, pathlib.Path, str]], list[pathlib.Path], list[pathlib.Path]]:
    binaries: list[tuple[str, pathlib.Path, str]] = []
    rom_candidates: list[pathlib.Path] = []
    metadata: list[pathlib.Path] = []
    seen_binary: set[str] = set()
    seen_rom: set[str] = set()
    seen_meta: set[str] = set()
    metadata_suffixes = {
        ".cproject", ".project", ".wvproj", ".wvsln", ".json", ".map", ".ld", ".lds",
        ".h", ".c", ".s", ".asm", ".txt", ".md", ".rst", ".html", ".htm", ".pdf",
    }
    for source_set, relroot in DISCOVERY_ROOTS:
        base = root / relroot
        for path in walk_files(base):
            relpath = repo_rel(root, path)
            head = read_head(path)
            kind = magic_kind(head)
            if kind in {"ar", "thin-ar"}:
                if relpath not in seen_binary:
                    binaries.append((source_set, path, kind))
                    seen_binary.add(relpath)
            elif kind == "ELF":
                # Inventory standalone target objects by ELF type, not suffix.
                mini = ELFPrimary(path.read_bytes())
                if mini.valid and mini.etype == ET_REL and relpath not in seen_binary:
                    binaries.append((source_set, path, kind))
                    seen_binary.add(relpath)
            if source_set == "evt":
                suffix = path.suffix.lower()
                if suffix in {".hex", ".bin"} and relpath not in seen_rom:
                    rom_candidates.append(path)
                    seen_rom.add(relpath)
                if suffix in metadata_suffixes and relpath not in seen_meta:
                    metadata.append(path)
                    seen_meta.add(relpath)
            elif path.suffix.lower() in {".pdf", ".txt", ".md", ".rst", ".info"} and relpath not in seen_meta:
                metadata.append(path)
                seen_meta.add(relpath)
    binaries.sort(key=lambda x: utf8_key(repo_rel(root, x[1])))
    rom_candidates.sort(key=lambda p: utf8_key(repo_rel(root, p)))
    metadata.sort(key=lambda p: utf8_key(repo_rel(root, p)))
    return binaries, rom_candidates, metadata


def input_manifest_rows(root: pathlib.Path, paths: Iterable[tuple[str, pathlib.Path]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    seen: set[str] = set()
    for source_set, path in sorted(paths, key=lambda x: utf8_key(repo_rel(root, x[1]))):
        relpath = repo_rel(root, path)
        if relpath in seen:
            continue
        seen.add(relpath)
        st = path.stat()
        out.append({
            "schema_version": SCHEMA,
            "source_set": source_set,
            "path": relpath,
            "size_bytes": st.st_size,
            "mtime_ns": st.st_mtime_ns,
            "sha256": sha_file(path),
        })
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", required=True)
    args = parser.parse_args()
    root = pathlib.Path.cwd().resolve()
    run = (root / args.run_root).resolve()
    if root not in run.parents:
        raise SystemExit("run root must be inside repository")
    outdir = run / "primary"
    outdir.mkdir(parents=True, exist_ok=True)

    binaries, rom_candidates, metadata = discovery_candidates(root)
    unit_results: dict[str, dict[str, object]] = {}
    artifacts: list[dict[str, object]] = []
    occurrences: list[dict[str, object]] = []
    archive_summaries: list[dict[str, object]] = []
    archive_cache: dict[str, tuple[ArParse, list[dict[str, object]]]] = {}
    archive_count = 0
    standalone_count = 0

    package = root / PACKAGE_PATH
    package_sha = sha_file(package) if package.exists() else "not-present"

    for idx, (source_set, path, kind) in enumerate(binaries, 1):
        relpath = repo_rel(root, path)
        data = path.read_bytes()
        artifact_sha = sha_bytes(data)
        if kind in {"ar", "thin-ar"}:
            archive_count += 1
            if artifact_sha in archive_cache:
                parsed, logical_template = archive_cache[artifact_sha]
                logical = [dict(x) for x in logical_template]
            else:
                parsed = parse_ar_primary(path, data)
                logical = []
                for member in parsed.members:
                    if member.metadata:
                        continue
                    payload = member.payload
                    if payload is None:
                        logical.append({
                            "logical_order": member.logical_order,
                            "member_name": member.name,
                            "same_name_ordinal": member.same_name_ordinal,
                            "member_size": "unknown",
                            "member_sha256": "unknown",
                            "file_format": "unreadable-thin-member",
                            "machine": "unknown",
                            "elf_class": "unknown",
                            "parse_errors": ["member-unreadable"],
                        })
                        continue
                    msha = sha_bytes(payload)
                    if msha not in unit_results:
                        unit_results[msha] = unit_scan_primary(payload)
                    unit = unit_results[msha]
                    logical.append({
                        "logical_order": member.logical_order,
                        "member_name": member.name,
                        "same_name_ordinal": member.same_name_ordinal,
                        "member_size": len(payload),
                        "member_sha256": msha,
                        "file_format": unit["magic"],
                        "machine": unit.get("machine", "unknown"),
                        "elf_class": unit.get("elf_class", "unknown"),
                        "parse_errors": unit.get("elf_errors", []),
                    })
                archive_cache[artifact_sha] = (parsed, [dict(x) for x in logical])
            scope, role = classify_archive(relpath, logical)
            meta_count = sum(1 for m in parsed.members if m.metadata)
            raw_count = len(parsed.members)
            summary = {
                "schema_version": SCHEMA,
                "physical_path": relpath,
                "archive_sha256": artifact_sha,
                "thin": parsed.thin,
                "raw_record_count": raw_count,
                "archive_metadata_records": meta_count,
                "member_occurrences": len(logical),
                "unique_member_names": len({str(x["member_name"]) for x in logical}),
                "unique_member_sha256": len({str(x["member_sha256"]) for x in logical}),
                "parser_errors": parsed.errors,
                "trailing_bytes": parsed.trailing_bytes,
            }
            archive_summaries.append(summary)
            for record in logical:
                occurrences.append({
                    "schema_version": SCHEMA,
                    "source_set": source_set,
                    "scope_class": scope,
                    "physical_path": relpath,
                    "archive_sha256": artifact_sha,
                    **record,
                })
            artifact = {
                "schema_version": SCHEMA,
                "source_set": source_set,
                "scope_class": scope,
                "path": relpath,
                "family": family_for(relpath),
                "role": role,
                "physical_present": "yes",
                "target_chip": infer_chip(relpath),
                "build_context": build_context_label(relpath),
                "sha256": artifact_sha,
                "normalized_sha256": "not-applicable",
                "parent_package_sha256": package_sha if source_set.startswith("mrs-2.5-macos-arm64") else "not-applicable",
                "file_format": kind,
                "member_occurrences": len(logical),
                "archive_errors": parsed.errors,
            }
            artifacts.append(artifact)
        else:
            standalone_count += 1
            unit = unit_scan_primary(data)
            unit_results.setdefault(artifact_sha, unit)
            elf = ELFPrimary(data)
            scope, role = classify_standalone(relpath, elf)
            occurrences.append({
                "schema_version": SCHEMA,
                "source_set": source_set,
                "scope_class": scope,
                "physical_path": relpath,
                "archive_sha256": "not-applicable",
                "logical_order": "not-applicable",
                "member_name": "not-applicable",
                "same_name_ordinal": "not-applicable",
                "member_size": len(data),
                "member_sha256": artifact_sha,
                "file_format": unit["magic"],
                "machine": unit.get("machine", "unknown"),
                "elf_class": unit.get("elf_class", "unknown"),
                "parse_errors": unit.get("elf_errors", []),
            })
            artifacts.append({
                "schema_version": SCHEMA,
                "source_set": source_set,
                "scope_class": scope,
                "path": relpath,
                "family": family_for(relpath),
                "role": role,
                "physical_present": "yes",
                "target_chip": infer_chip(relpath),
                "build_context": build_context_label(relpath),
                "sha256": artifact_sha,
                "normalized_sha256": "not-applicable",
                "parent_package_sha256": package_sha if source_set.startswith("mrs-2.5-macos-arm64") else "not-applicable",
                "file_format": kind,
                "member_occurrences": "not-applicable",
                "archive_errors": [],
            })
        if idx % 200 == 0:
            print(f"phase=primary-binary artifact={idx}/{len(binaries)} units={len(unit_results)}", flush=True)

    rom_results: list[dict[str, object]] = []
    for path in rom_candidates:
        relpath = repo_rel(root, path)
        data = path.read_bytes()
        raw_sha = sha_bytes(data)
        is_hex = path.suffix.lower() == ".hex"
        if is_hex:
            rom = rom_scan_primary(data)
            normalized = str(rom["normalized_sha256"])
            parse_errors = list(rom["parse_errors"])
            fmt = "Intel HEX"
        else:
            rom = {
                "parse_errors": ["raw-binary-base-and-isa-unproven"],
                "normalized_sha256": "not-applicable",
                "domain": {"units": len(data), "records": [("raw-file", 0, len(data))], "set_sha256": hash_records([("raw-file", 0, len(data))])},
            }
            normalized = "not-applicable"
            parse_errors = list(rom["parse_errors"])
            fmt = "raw binary"
        payload = relpath in ROM_PAYLOADS
        scope = "rom-payload" if payload else "derived"
        role = "rom-payload" if payload else ("storage-payload" if "cd-rom" in relpath.lower() or "cdrom" in relpath.lower() else "example-firmware")
        rom_row = {
            "schema_version": SCHEMA,
            "physical_path": relpath,
            "raw_sha256": raw_sha,
            "normalized_sha256": normalized,
            "scope_class": scope,
            "role": role,
            "target_chip": infer_chip(relpath),
            "result": rom,
        }
        rom_results.append(rom_row)
        artifacts.append({
            "schema_version": SCHEMA,
            "source_set": "evt",
            "scope_class": scope,
            "path": relpath,
            "family": family_for(relpath),
            "role": role,
            "physical_present": "yes",
            "target_chip": infer_chip(relpath),
            "build_context": build_context_label(relpath),
            "sha256": raw_sha,
            "normalized_sha256": normalized,
            "parent_package_sha256": "not-applicable",
            "file_format": fmt,
            "member_occurrences": "not-applicable",
            "archive_errors": parse_errors,
        })

    # Three ROM API/JT headers are physical scope artifacts but not native code.
    for relpath in sorted(ROM_HEADERS, key=utf8_key):
        path = root / relpath
        if path.exists():
            artifacts.append({
                "schema_version": SCHEMA,
                "source_set": "evt",
                "scope_class": "rom-wrapper",
                "path": relpath,
                "family": "ROM API/JT header",
                "role": "rom-api-jt-header",
                "physical_present": "yes",
                "target_chip": infer_chip(relpath),
                "build_context": build_context_label(relpath),
                "sha256": sha_file(path),
                "normalized_sha256": "not-applicable",
                "parent_package_sha256": "not-applicable",
                "file_format": "text-header",
                "member_occurrences": "not-applicable",
                "archive_errors": [],
            })

    if package.exists():
        artifacts.append({
            "schema_version": SCHEMA,
            "source_set": "mrs-2.5-macos-arm64-package",
            "scope_class": "source-package",
            "path": PACKAGE_PATH,
            "family": "MounRiver Studio package",
            "role": "package-container",
            "physical_present": "yes",
            "target_chip": "not-applicable",
            "build_context": "not-applicable",
            "sha256": package_sha,
            "normalized_sha256": "not-applicable",
            "parent_package_sha256": "not-applicable",
            "file_format": "tar",
            "member_occurrences": "not-applicable",
            "archive_errors": [],
        })

    artifacts.sort(key=lambda x: utf8_key(str(x["path"])))
    occurrences.sort(key=lambda x: (
        utf8_key(str(x["physical_path"])),
        -1 if x["logical_order"] == "not-applicable" else int(x["logical_order"]),
        utf8_key(str(x["member_name"])),
    ))
    archive_summaries.sort(key=lambda x: utf8_key(str(x["physical_path"])))
    rom_results.sort(key=lambda x: utf8_key(str(x["physical_path"])))

    def write_jsonl(name: str, rows: Iterable[object]) -> None:
        text = "".join(json_dump_line(row) + "\n" for row in rows)
        atomic_write_text(outdir / name, text)

    write_jsonl("artifacts.jsonl", artifacts)
    write_jsonl("occurrences.jsonl", occurrences)
    write_jsonl("archive-summary.jsonl", archive_summaries)
    write_jsonl("unit-primary.jsonl", (unit_results[k] for k in sorted(unit_results)))
    write_jsonl("rom-primary.jsonl", rom_results)

    manifest_paths: list[tuple[str, pathlib.Path]] = []
    for source_set, path, _ in binaries:
        manifest_paths.append((source_set + "/binary", path))
    for path in rom_candidates:
        manifest_paths.append(("evt/rom-candidate", path))
    for path in metadata:
        manifest_paths.append(("evt-or-toolchain/metadata-or-doc", path))
    for relpath in ROM_HEADERS:
        path = root / relpath
        if path.exists():
            manifest_paths.append(("evt/rom-header", path))
    if package.exists():
        manifest_paths.append(("mrs-2.5/package", package))
    manifest_paths.append(("task", root / "06b-chipid-errata-codex.md"))
    manifest = input_manifest_rows(root, manifest_paths)
    header = ["schema_version", "source_set", "path", "size_bytes", "mtime_ns", "sha256"]
    tmp = outdir / "analysis-input-manifest.tsv.tmp-r2"
    with tmp.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(manifest)
    os.replace(tmp, outdir / "analysis-input-manifest.tsv")

    counts = {
        "schema_version": SCHEMA,
        "binary_artifacts": len(binaries),
        "archives": archive_count,
        "standalone_objects": standalone_count,
        "inventory_artifacts_including_rom_headers_package": len(artifacts),
        "logical_member_or_standalone_occurrences": len(occurrences),
        "unique_scan_units": len(unit_results),
        "rom_candidates": len(rom_candidates),
        "rom_payloads": sum(1 for x in rom_results if x["scope_class"] == "rom-payload"),
        "metadata_or_docs": len(metadata),
        "input_manifest_files": len(manifest),
        "package_sha256": package_sha,
        "scope_counts": dict(sorted(Counter(str(x["scope_class"]) for x in artifacts).items())),
        "source_set_counts": dict(sorted(Counter(str(x["source_set"]) for x in artifacts).items())),
    }
    atomic_write_text(outdir / "counts.json", json.dumps(counts, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    print(json_dump_line(counts), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
