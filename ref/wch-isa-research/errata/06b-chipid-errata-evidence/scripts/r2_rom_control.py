#!/usr/bin/env python3
"""Independent ROM controls for the five SDK images.

The jump-table recursive walk proves only the code it reaches.  A separate
whole-range linear framing pass is deliberately labelled mixed code/data and
is used only to test parcel boundaries and byte-fingerprint classification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import struct
from collections import Counter, deque


IMAGES = (
    ("tmp/wch-evt/evt/QingkeV3C_CH587_EVT/EXAM/BLE/LIB/CH587BLE_ROMx.hex",
     "tmp/wch-evt/evt/QingkeV3C_CH587_EVT/EXAM/BLE/LIB/CH58xBLE_ROM.h", "CH587", "ordinary"),
    ("tmp/wch-evt/evt/QingkeV4B_CH32V203_EVT/EXAM/BLE/LIB/wchble_rom.hex",
     "tmp/wch-evt/evt/QingkeV4B_CH32V203_EVT/EXAM/BLE/LIB/wchble_rom.h", "CH32V203", "ordinary"),
    ("tmp/wch-evt/evt/QingkeV4B_CH32V203_EVT/EXAM/BLE/MESH/MESH_LIB/wchble_rom_mesh.hex",
     "tmp/wch-evt/evt/QingkeV4B_CH32V203_EVT/EXAM/BLE/LIB/wchble_rom.h", "CH32V203", "mesh"),
    ("tmp/wch-evt/evt/QingkeV4C_CH32V20x_EVT/EXAM/BLE/LIB/wchble_rom.hex",
     "tmp/wch-evt/evt/QingkeV4C_CH32V20x_EVT/EXAM/BLE/LIB/wchble_rom.h", "CH32V20x", "ordinary"),
    ("tmp/wch-evt/evt/QingkeV4C_CH32V20x_EVT/EXAM/BLE/MESH/MESH_LIB/wchble_rom_mesh.hex",
     "tmp/wch-evt/evt/QingkeV4C_CH32V20x_EVT/EXAM/BLE/LIB/wchble_rom.h", "CH32V20x", "mesh"),
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encode_record(values: tuple[object, ...]) -> bytes:
    out = bytearray(struct.pack(">I", len(values)))
    for value in values:
        raw = str(value).encode("utf-8")
        out += struct.pack(">Q", len(raw)) + raw
    return bytes(out)


def normalized_hash(memory: dict[int, int]) -> str:
    h = hashlib.sha256(b"wch-rom-address-byte-v2\0")
    for address in sorted(memory):
        h.update(encode_record((address, memory[address])))
    return h.hexdigest()


def parse_hex(data: bytes) -> dict[str, object]:
    memory: dict[int, int] = {}
    errors: list[str] = []
    records = Counter()
    base = 0
    eof = False
    for lineno, raw_line in enumerate(data.splitlines(), 1):
        line = raw_line.strip()
        if not line:
            continue
        if eof:
            errors.append(f"data-after-eof:{lineno}")
        if not line.startswith(b":"):
            errors.append(f"missing-colon:{lineno}")
            continue
        try:
            record = bytes.fromhex(line[1:].decode("ascii"))
        except (ValueError, UnicodeDecodeError):
            errors.append(f"bad-hex:{lineno}")
            continue
        if len(record) < 5 or len(record) != record[0] + 5:
            errors.append(f"bad-length:{lineno}")
            continue
        if sum(record) & 0xFF:
            errors.append(f"bad-checksum:{lineno}")
            continue
        count, offset, kind = record[0], int.from_bytes(record[1:3], "big"), record[3]
        payload = record[4:4 + count]
        records[kind] += 1
        if kind == 0:
            absolute = base + offset
            if absolute > 0xFFFFFFFF or absolute + count > 0x100000000:
                errors.append(f"address-overflow:{lineno}")
                continue
            for index, value in enumerate(payload):
                address = absolute + index
                old = memory.get(address)
                if old is not None and old != value:
                    errors.append(f"address-conflict:{lineno}:0x{address:x}")
                memory[address] = value
        elif kind == 1:
            if count or offset:
                errors.append(f"bad-eof:{lineno}")
            eof = True
        elif kind == 2:
            if count != 2 or offset:
                errors.append(f"bad-esa:{lineno}")
            else:
                base = int.from_bytes(payload, "big") << 4
        elif kind == 3:
            if count != 4 or offset:
                errors.append(f"bad-start-segment:{lineno}")
        elif kind == 4:
            if count != 2 or offset:
                errors.append(f"bad-ela:{lineno}")
            else:
                base = int.from_bytes(payload, "big") << 16
        elif kind == 5:
            if count != 4 or offset:
                errors.append(f"bad-start-linear:{lineno}")
        else:
            errors.append(f"unknown-record:{lineno}:{kind}")
    if not eof:
        errors.append("missing-eof")
    return {"memory": memory, "errors": errors, "records": dict(sorted(records.items())), "eof": eof}


def ranges(memory: dict[int, int]) -> list[tuple[int, int]]:
    if not memory:
        return []
    out = []
    keys = sorted(memory)
    first = previous = keys[0]
    for address in keys[1:]:
        if address != previous + 1:
            out.append((first, previous + 1))
            first = address
        previous = address
    out.append((first, previous + 1))
    return out


def contiguous(memory: dict[int, int], address: int, size: int) -> bytes | None:
    if all(address + index in memory for index in range(size)):
        return bytes(memory[address + index] for index in range(size))
    return None


def parcel_length(memory: dict[int, int], address: int) -> tuple[int | None, str]:
    raw = contiguous(memory, address, 2)
    if raw is None:
        return None, "truncated-first-parcel"
    halfword = int.from_bytes(raw, "little")
    if halfword & 3 != 3:
        return 2, "known"
    if (halfword >> 2) & 7 != 7:
        return 4, "known"
    if (halfword >> 5) & 1 == 0:
        return 6, "known"
    if (halfword >> 6) & 1 == 0:
        return 8, "known"
    nnn = (halfword >> 12) & 7
    if nnn != 7:
        return 10 + 2 * nnn, "known"
    return None, "reserved-ge-192"


def signed(value: int, bits: int) -> int:
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


def jal_imm(word: int) -> int:
    value = ((word >> 31) & 1) << 20
    value |= ((word >> 21) & 0x3FF) << 1
    value |= ((word >> 20) & 1) << 11
    value |= ((word >> 12) & 0xFF) << 12
    return signed(value, 21)


def branch_imm(word: int) -> int:
    value = ((word >> 31) & 1) << 12
    value |= ((word >> 25) & 0x3F) << 5
    value |= ((word >> 8) & 0xF) << 1
    value |= ((word >> 7) & 1) << 11
    return signed(value, 13)


def cj_imm(hw: int) -> int:
    value = ((hw >> 12) & 1) << 11
    value |= ((hw >> 11) & 1) << 4
    value |= ((hw >> 9) & 3) << 8
    value |= ((hw >> 8) & 1) << 10
    value |= ((hw >> 7) & 1) << 6
    value |= ((hw >> 6) & 1) << 7
    value |= ((hw >> 3) & 7) << 1
    value |= ((hw >> 2) & 1) << 5
    return signed(value, 12)


def cb_imm(hw: int) -> int:
    value = ((hw >> 12) & 1) << 8
    value |= ((hw >> 10) & 3) << 3
    value |= ((hw >> 5) & 3) << 6
    value |= ((hw >> 3) & 3) << 1
    value |= ((hw >> 2) & 1) << 5
    return signed(value, 9)


def successors(memory: dict[int, int], address: int, length: int) -> tuple[list[int], str]:
    fallthrough = address + length
    if length == 2:
        hw = int.from_bytes(contiguous(memory, address, 2) or b"\0\0", "little")
        quadrant, funct3 = hw & 3, (hw >> 13) & 7
        if quadrant == 1 and funct3 in (1, 5):
            target = address + cj_imm(hw)
            return ([target, fallthrough], "c.jal") if funct3 == 1 else ([target], "c.j")
        if quadrant == 1 and funct3 in (6, 7):
            return [address + cb_imm(hw), fallthrough], "c.branch"
        if quadrant == 2 and funct3 == 4 and (hw >> 2) & 0x1F == 0:
            rs1 = (hw >> 7) & 0x1F
            if rs1 == 0:
                return [], "c.ebreak-or-reserved"
            return ([fallthrough], "c.jalr-indirect") if (hw >> 12) & 1 else ([], "c.jr-indirect")
        return [fallthrough], "fallthrough"
    if length == 4:
        word = int.from_bytes(contiguous(memory, address, 4) or b"\0" * 4, "little")
        opcode = word & 0x7F
        if opcode == 0x63:
            return [address + branch_imm(word), fallthrough], "branch"
        if opcode == 0x6F:
            target = address + jal_imm(word)
            return ([target], "jal-jump") if ((word >> 7) & 0x1F) == 0 else ([target, fallthrough], "jal-call")
        if opcode == 0x67:
            return ([fallthrough], "jalr-call-indirect") if ((word >> 7) & 0x1F) != 0 else ([], "jalr-jump-indirect")
        if word in (0x00000073, 0x00100073):
            return [], "environment-stop"
        return [fallthrough], "fallthrough"
    return [fallthrough], "long-fallthrough"


def recursive_code(memory: dict[int, int], seeds: set[int], data_bytes: set[int]) -> dict[str, object]:
    queue = deque(sorted(seeds))
    seen: set[int] = set()
    parcels: list[dict[str, object]] = []
    errors: list[dict[str, object]] = []
    code_bytes: set[int] = set()
    overlap_bytes: set[int] = set()
    while queue:
        address = queue.popleft()
        if address in seen or address in data_bytes:
            continue
        seen.add(address)
        if address & 1 or address not in memory:
            errors.append({"address": address, "reason": "bad-target"})
            continue
        length, reason = parcel_length(memory, address)
        if length is None or contiguous(memory, address, length) is None:
            errors.append({"address": address, "reason": reason})
            continue
        occupied = set(range(address, address + length))
        overlap_bytes |= occupied & code_bytes
        code_bytes |= occupied
        next_addresses, flow = successors(memory, address, length)
        raw = contiguous(memory, address, length) or b""
        parcels.append({
            "address": address, "length": length, "raw_hex": raw.hex(),
            "flow": flow, "successors": sorted(set(next_addresses)),
        })
        for target in sorted(set(next_addresses)):
            if target in memory and target not in data_bytes and target not in seen:
                queue.append(target)
    parcels.sort(key=lambda x: int(x["address"]))
    return {"parcels": parcels, "errors": errors, "code_bytes": code_bytes, "overlap_bytes": overlap_bytes}


def linear_mixed_frames(memory: dict[int, int]) -> dict[str, object]:
    """Frame each populated contiguous run from its first address.

    HEX has no complete code map, so these frames are not called instructions
    or reachable code.  Reserved >=192-bit prefixes and truncation terminate
    the current run; there is no byte-skipping resynchronization.
    """
    parcels: list[dict[str, object]] = []
    errors: list[dict[str, object]] = []
    for begin, end in ranges(memory):
        address = begin
        while address < end:
            length, reason = parcel_length(memory, address)
            if length is None:
                errors.append({"run_start": begin, "address": address, "reason": reason})
                break
            raw = contiguous(memory, address, length)
            if raw is None or address + length > end:
                errors.append({"run_start": begin, "address": address, "reason": "truncated-parcel"})
                break
            parcels.append({
                "run_start": begin, "address": address, "length": length,
                "raw_hex": raw.hex(),
            })
            address += length
    return {"parcels": parcels, "errors": errors}


def ialign_prefix_candidates(memory: dict[int, int]) -> dict[str, object]:
    """Classify the parcel-length prefix at every populated even start.

    This is an intentional boundary superset.  It proves decoder handling and
    physical prefix presence, not that any candidate is an instruction start.
    """
    rows: list[dict[str, object]] = []
    histogram = Counter()
    ambiguous = Counter()
    for address in sorted(memory):
        if address & 1:
            continue
        length, reason = parcel_length(memory, address)
        if length is None:
            if contiguous(memory, address, 2) is not None:
                ambiguous[reason] += 1
                rows.append({"address": address, "length": "unknown", "reason": reason})
            continue
        if contiguous(memory, address, length) is None:
            ambiguous["truncated-or-gap"] += 1
            rows.append({"address": address, "length": "unknown", "reason": "truncated-or-gap"})
            continue
        histogram[length] += 1
        if length >= 6:
            rows.append({"address": address, "length": length, "reason": "known-prefix"})
    return {"rows": rows, "histogram": histogram, "ambiguous": ambiguous}


def local_linear_block(memory: dict[int, int], begin: int, end: int) -> dict[str, object]:
    """Frame one explicitly bounded local block without claiming reachability."""
    parcels: list[dict[str, object]] = []
    errors: list[dict[str, object]] = []
    address = begin
    while address < end:
        length, reason = parcel_length(memory, address)
        if length is None or address + length > end:
            errors.append({"address": address, "reason": reason if length is None else "crosses-block-end"})
            break
        raw = contiguous(memory, address, length)
        if raw is None:
            errors.append({"address": address, "reason": "gap"})
            break
        next_addresses, flow = successors(memory, address, length)
        parcels.append({
            "address": address, "length": length, "raw_hex": raw.hex(),
            "flow": flow, "successors": sorted(set(next_addresses)),
        })
        address += length
    return {"parcels": parcels, "errors": errors, "ends_at_bound": address == end}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-root", required=True)
    args = ap.parse_args()
    repo = pathlib.Path.cwd().resolve()
    run = (repo / args.run_root).resolve()
    out = run / "controls" / "rom-r2"
    out.mkdir(parents=True, exist_ok=True)

    primary_rom = {}
    with (run / "primary" / "rom-primary.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row["scope_class"] == "rom-payload":
                primary_rom[str(row["physical_path"])] = row
    independent_rom = {}
    with (run / "independent" / "rom-independent.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            independent_rom[str(row["physical_path"])] = row

    header_rows = []
    header_cache = {}
    for _image, header_path, chip, _variant in IMAGES:
        if header_path in header_cache:
            continue
        data = (repo / header_path).read_bytes()
        text = data.decode("utf-8", "replace")
        function_slots = sorted({int(x) for x in re.findall(r"BLE_LIB_JT\(\s*(\d+)\s*\)", text)} - {0})
        base_match = re.search(r"#define\s+LIB_FLASH_BASE_ADDRESSS\s+(0x[0-9A-Fa-f]+)", text)
        version_match = re.search(r"\* Version\s*:\s*([^\r\n]+)", text)
        row = {
            "path": header_path, "chip": chip, "sha256": sha(data), "size": len(data),
            "default_base": int(base_match.group(1), 16) if base_match else "unknown",
            "jt_offset": 0x34, "slot0_semantics": "VER_LIB-data-pointer",
            "function_slot_count": len(function_slots), "maximum_function_slot": max(function_slots),
            "function_slots": function_slots,
            "version": version_match.group(1).strip() if version_match else "unknown",
        }
        header_cache[header_path] = row
        header_rows.append(row)

    jt_path = out / "rom-jt-seeds.tsv"
    parcel_path = out / "rom-code-parcels.tsv"
    mixed_path = out / "rom-linear-mixed-parcels.tsv"
    prefix_path = out / "rom-length-prefix-candidates.tsv"
    fingerprint_path = out / "rom-fingerprints.tsv"
    jt_handle = jt_path.open("w", encoding="utf-8", newline="")
    parcel_handle = parcel_path.open("w", encoding="utf-8", newline="")
    mixed_handle = mixed_path.open("w", encoding="utf-8", newline="")
    prefix_handle = prefix_path.open("w", encoding="utf-8", newline="")
    fp_handle = fingerprint_path.open("w", encoding="utf-8", newline="")
    jt_handle.write("schema_version\timage_path\tslot\tslot_address\tvalue\tclassification\tvalid_seed\n")
    parcel_handle.write("schema_version\timage_path\taddress\tlength\traw_hex\tflow\tsuccessors\n")
    mixed_handle.write("schema_version\timage_path\trun_start\taddress\tlength\traw_hex\n")
    prefix_handle.write("schema_version\timage_path\taddress\tlength\tclassification\tfirst_halfword_hex\n")
    fp_handle.write(
        "schema_version\timage_path\tfingerprint\taddress\trecursive_classification\t"
        "recursive_parcel_start\trecursive_parcel_length\tlinear_mixed_classification\t"
        "linear_mixed_parcel_start\tlinear_mixed_parcel_length\n"
    )

    results = []
    for image_path, header_path, chip, variant in IMAGES:
        raw = (repo / image_path).read_bytes()
        parsed = parse_hex(raw)
        memory: dict[int, int] = parsed["memory"]  # type: ignore[assignment]
        image_ranges = ranges(memory)
        base = min(memory)
        header = header_cache[header_path]
        jt_base = base + int(header["jt_offset"])
        max_slot = int(header["maximum_function_slot"])
        jt_end = jt_base + 4 * (max_slot + 1)
        data_bytes = {address for address in memory if base <= address < jt_end}
        seeds = set()
        jt_rows = []
        slot0_raw = contiguous(memory, jt_base, 4)
        slot0_value = int.from_bytes(slot0_raw, "little") if slot0_raw else None
        jt_rows.append((0, jt_base, slot0_value, "data-pointer", False))
        for slot in header["function_slots"]:  # type: ignore[union-attr]
            slot_address = jt_base + 4 * int(slot)
            value_raw = contiguous(memory, slot_address, 4)
            value = int.from_bytes(value_raw, "little") if value_raw else None
            valid = value is not None and value & 1 == 0 and value in memory and value not in data_bytes
            if valid:
                seeds.add(value)
            jt_rows.append((slot, slot_address, value, "function-pointer", valid))
        for slot, address, value, classification, valid in jt_rows:
            jt_handle.write(f"2\t{image_path}\t{slot}\t0x{address:08x}\t{('unknown' if value is None else f'0x{value:08x}')}\t{classification}\t{str(valid).lower()}\n")

        recursive = recursive_code(memory, seeds, data_bytes)
        parcels: list[dict[str, object]] = recursive["parcels"]  # type: ignore[assignment]
        code_bytes: set[int] = recursive["code_bytes"]  # type: ignore[assignment]
        for parcel in parcels:
            successors = ";".join(f"0x{x:08x}" for x in parcel["successors"]) or "-"  # type: ignore[union-attr]
            parcel_handle.write(
                f"2\t{image_path}\t0x{int(parcel['address']):08x}\t{parcel['length']}\t{parcel['raw_hex']}\t{parcel['flow']}\t"
                + successors + "\n"
            )
        recursive_histogram = Counter(int(x["length"]) for x in parcels)
        recursive_parcel_by_byte = {}
        for parcel in parcels:
            for address in range(int(parcel["address"]), int(parcel["address"]) + int(parcel["length"])):
                recursive_parcel_by_byte.setdefault(address, parcel)

        linear = linear_mixed_frames(memory)
        mixed_parcels: list[dict[str, object]] = linear["parcels"]  # type: ignore[assignment]
        mixed_histogram = Counter(int(x["length"]) for x in mixed_parcels)
        mixed_parcel_by_byte = {}
        for parcel in mixed_parcels:
            mixed_handle.write(
                f"2\t{image_path}\t0x{int(parcel['run_start']):08x}\t0x{int(parcel['address']):08x}\t"
                f"{parcel['length']}\t{parcel['raw_hex']}\n"
            )
            for address in range(int(parcel["address"]), int(parcel["address"]) + int(parcel["length"])):
                mixed_parcel_by_byte.setdefault(address, parcel)

        prefix_candidates = ialign_prefix_candidates(memory)
        for row in prefix_candidates["rows"]:  # type: ignore[union-attr]
            first = contiguous(memory, int(row["address"]), 2) or b""
            prefix_handle.write(
                f"2\t{image_path}\t0x{int(row['address']):08x}\t{row['length']}\t{row['reason']}\t{first.hex()}\n"
            )

        fingerprint_rows = []
        for word in (0x07F805FB, 0x5F9B34FB, 0x3B352F2B):
            needle = word.to_bytes(4, "little")
            for address in sorted(memory):
                if contiguous(memory, address, 4) == needle:
                    recursive_parcel = recursive_parcel_by_byte.get(address)
                    if recursive_parcel and int(recursive_parcel["address"]) == address:
                        recursive_classification = "reachable-parcel-start"
                    elif recursive_parcel:
                        recursive_classification = "inside-reachable-parcel"
                    else:
                        recursive_classification = "unclassified-populated-byte"
                    mixed_parcel = mixed_parcel_by_byte.get(address)
                    if mixed_parcel and int(mixed_parcel["address"]) == address:
                        mixed_classification = "linear-mixed-parcel-start"
                    elif mixed_parcel and int(mixed_parcel["length"]) > 4:
                        mixed_classification = "inside-linear-mixed-long-parcel"
                    elif mixed_parcel:
                        mixed_classification = "inside-linear-mixed-short-parcel"
                    else:
                        mixed_classification = "outside-complete-linear-mixed-frames"
                    fingerprint_rows.append({
                        "word": word, "address": address,
                        "recursive_classification": recursive_classification,
                        "recursive_parcel": recursive_parcel,
                        "linear_mixed_classification": mixed_classification,
                        "linear_mixed_parcel": mixed_parcel,
                    })
                    recursive_start = "not-applicable" if not recursive_parcel else f"0x{int(recursive_parcel['address']):08x}"
                    recursive_length = "not-applicable" if not recursive_parcel else str(recursive_parcel["length"])
                    mixed_start = "not-applicable" if not mixed_parcel else f"0x{int(mixed_parcel['address']):08x}"
                    mixed_length = "not-applicable" if not mixed_parcel else str(mixed_parcel["length"])
                    fp_handle.write(
                        f"2\t{image_path}\t0x{word:08x}\t0x{address:08x}\t{recursive_classification}\t"
                        f"{recursive_start}\t{recursive_length}\t{mixed_classification}\t{mixed_start}\t{mixed_length}\n"
                    )

        populated = set(memory)
        data_only = data_bytes - code_bytes
        unclassified = populated - code_bytes - data_only
        norm = normalized_hash(memory)
        primary = primary_rom[image_path]
        independent = independent_rom[image_path]
        mcpy_raw = contiguous(memory, 0x40968, 4) if chip == "CH587" else None
        mcpy_recursive_parcel = next((x for x in parcels if int(x["address"]) == 0x40968), None)
        mcpy_mixed_parcel = next((x for x in mixed_parcels if int(x["address"]) == 0x40968), None)
        mcpy_local = local_linear_block(memory, 0x40960, 0x4096E) if chip == "CH587" else {
            "parcels": [], "errors": [], "ends_at_bound": False,
        }
        mcpy_local_parcel = next((x for x in mcpy_local["parcels"] if int(x["address"]) == 0x40968), None)  # type: ignore[index]
        result = {
            "path": image_path, "header": header_path, "chip": chip, "variant": variant,
            "raw_sha256": sha(raw), "line_count": len(raw.splitlines()),
            "parse_errors": parsed["errors"], "record_types": parsed["records"], "eof": parsed["eof"],
            "base": base, "ranges": image_ranges, "populated_bytes": len(populated),
            "normalized_sha256": norm,
            "primary_normalized_sha256": primary["normalized_sha256"],
            "independent_normalized_sha256": independent["normalized_sha256"],
            "jt_base": jt_base, "jt_end": jt_end, "slot0_value": slot0_value,
            "function_slots": len(header["function_slots"]),
            "valid_function_seeds": len(seeds), "invalid_function_slots": sum(not x[4] for x in jt_rows if x[0] != 0),
            "reachable_parcels": len(parcels),
            "recursive_framing_histogram": dict(sorted(recursive_histogram.items())),
            "recursive_errors": recursive["errors"], "overlap_bytes": len(recursive["overlap_bytes"]),
            "linear_mixed_framing": {
                "interpretation": "whole populated runs framed from each run start; mixed code/data, not reachability",
                "parcels": len(mixed_parcels), "histogram": dict(sorted(mixed_histogram.items())),
                "errors": linear["errors"],
            },
            "ialign_prefix_candidates": {
                "interpretation": "every populated even start; boundary superset, not instruction reachability",
                "histogram": dict(sorted(prefix_candidates["histogram"].items())),  # type: ignore[union-attr]
                "ambiguous": dict(sorted(prefix_candidates["ambiguous"].items())),  # type: ignore[union-attr]
            },
            "coverage": {
                "proven_code_bytes": len(code_bytes),
                "proven_data_or_jt_or_padding_bytes": len(data_only),
                "unclassified_populated_bytes": len(unclassified),
                "populated_bytes": len(populated),
                "equation_ok": len(code_bytes) + len(data_only) + len(unclassified) == len(populated),
            },
            "mcpy_control": {
                "address": "0x00040968", "raw_hex": mcpy_raw.hex() if mcpy_raw else "not-applicable",
                "recursive_reachable_parcel_start": mcpy_recursive_parcel is not None,
                "linear_mixed_parcel_start": mcpy_mixed_parcel is not None,
                "local_block_start": "0x00040960" if chip == "CH587" else "not-applicable",
                "local_block_end_exclusive": "0x0004096e" if chip == "CH587" else "not-applicable",
                "local_block_parcel_starts": [f"0x{int(x['address']):08x}" for x in mcpy_local["parcels"]],  # type: ignore[index]
                "local_block_errors": mcpy_local["errors"],
                "local_block_ends_at_bound": mcpy_local["ends_at_bound"],
                "local_parcel_start": mcpy_local_parcel is not None,
                "prelude_0x40960_0x40970": (contiguous(memory, 0x40960, 0x12) or b"").hex() if chip == "CH587" else "not-applicable",
            },
            "fingerprints": [
                {
                    "word": f"0x{int(x['word']):08x}", "address": f"0x{int(x['address']):08x}",
                    "recursive_classification": x["recursive_classification"],
                    "linear_mixed_classification": x["linear_mixed_classification"],
                    "linear_mixed_parcel_start": (
                        "not-applicable" if not x["linear_mixed_parcel"]
                        else f"0x{int(x['linear_mixed_parcel']['address']):08x}"
                    ),
                    "linear_mixed_parcel_length": (
                        "not-applicable" if not x["linear_mixed_parcel"]
                        else int(x["linear_mixed_parcel"]["length"])
                    ),
                }
                for x in fingerprint_rows
            ],
            "primitive_candidate_counts": {
                key: len(primary["result"]["candidates"][key])
                for key in ("csr-opcode", "xw-slot", "address-or-literal")
            },
        }
        results.append(result)
    jt_handle.close()
    parcel_handle.close()
    mixed_handle.close()
    prefix_handle.close()
    fp_handle.close()

    header_path_out = out / "rom-header-ledger.tsv"
    with header_path_out.open("w", encoding="utf-8", newline="") as handle:
        handle.write("schema_version\tpath\tchip\tsha256\tsize\tversion\tdefault_base\tjt_offset\tslot0_semantics\tfunction_slot_count\tmaximum_function_slot\n")
        for row in sorted(header_rows, key=lambda x: str(x["path"]).encode()):
            handle.write(
                f"2\t{row['path']}\t{row['chip']}\t{row['sha256']}\t{row['size']}\t{row['version']}\t"
                f"0x{int(row['default_base']):08x}\t0x{int(row['jt_offset']):x}\t{row['slot0_semantics']}\t"
                f"{row['function_slot_count']}\t{row['maximum_function_slot']}\n"
            )

    expected_long = {
        "CH587": {6, 10, 12, 14},
        "ordinary": {6, 8, 10},
        "mesh": {6, 10},
    }
    long_controls = []
    for result in results:
        seen = {int(x) for x in result["ialign_prefix_candidates"]["histogram"] if int(x) >= 6}
        required = expected_long["CH587"] if result["chip"] == "CH587" else expected_long[str(result["variant"])]
        long_controls.append({
            "path": result["path"], "method": "all-populated-IALIGN-prefix-candidates",
            "required": sorted(required), "seen": sorted(seen), "pass": required <= seen,
            "interpretation": "prefix/decoder control only; starts are not promoted to reachable instructions",
        })
    cross = [
        x for result in results for x in result["fingerprints"]
        if x["word"] == "0x07f805fb" and x["address"] == "0x0006b8d4"
    ]
    wrappers = []
    with (run / "primary" / "artifacts.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row["role"] == "rom-wrapper-archive":
                wrappers.append({"path": row["path"], "sha256": row["sha256"], "member_occurrences": row["member_occurrences"]})
    summary = {
        "schema_version": "2",
        "status": "pass" if (
            len(results) == 5
            and len({x["normalized_sha256"] for x in results}) == 3
            and all(not x["parse_errors"] for x in results)
            and all(x["normalized_sha256"] == x["primary_normalized_sha256"] == x["independent_normalized_sha256"] for x in results)
            and all(x["coverage"]["equation_ok"] for x in results)
            and all(x["pass"] for x in long_controls)
            and results[0]["mcpy_control"]["raw_hex"] == "0f70b650"
            and not results[0]["mcpy_control"]["recursive_reachable_parcel_start"]
            and results[0]["mcpy_control"]["linear_mixed_parcel_start"]
            and results[0]["mcpy_control"]["local_parcel_start"]
            and results[0]["mcpy_control"]["local_block_ends_at_bound"]
            and not results[0]["mcpy_control"]["local_block_errors"]
            and len(cross) == 1
            and cross[0]["recursive_classification"] == "unclassified-populated-byte"
            and cross[0]["linear_mixed_classification"] == "inside-linear-mixed-long-parcel"
            and len(wrappers) == 2
        ) else "failed",
        "images": results, "headers": header_rows, "wrappers": wrappers,
        "long_framing_controls": long_controls,
        "files": {
            "jt_seeds_sha256": sha(jt_path.read_bytes()),
            "code_parcels_sha256": sha(parcel_path.read_bytes()),
            "linear_mixed_parcels_sha256": sha(mixed_path.read_bytes()),
            "length_prefix_candidates_sha256": sha(prefix_path.read_bytes()),
            "fingerprints_sha256": sha(fingerprint_path.read_bytes()),
            "header_ledger_sha256": sha(header_path_out.read_bytes()),
        },
    }
    (out / "rom-control-summary.json").write_text(json.dumps(summary, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({
        "status": summary["status"], "content_groups": len({x["normalized_sha256"] for x in results}),
        "long_controls": long_controls, "mcpy": results[0]["mcpy_control"], "cross": cross,
    }, sort_keys=True))
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
