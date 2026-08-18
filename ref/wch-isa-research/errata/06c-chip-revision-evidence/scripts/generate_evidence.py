#!/usr/bin/env python3
"""Generate the compact 06c CHIPID/revision/errata evidence bundle.

The source corpus and build trees live below tmp/ and are intentionally not
copied wholesale.  This script records hashes, emits line-numbered excerpts,
extracts the reviewed PDF pages, copies the visually reviewed renders, and
produces focused disassembly with the WCH cross objdump.
"""
from __future__ import annotations

import csv
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
from typing import Iterable


def find_repo(start: pathlib.Path) -> pathlib.Path:
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("repository root not found")


SCRIPT = pathlib.Path(__file__).resolve()
REPO = find_repo(SCRIPT.parent)
BUNDLE = SCRIPT.parent.parent
RUN = REPO / "tmp/chipid-revision-06c/runs/20260804T100258Z-27480e4af493-00"
EVT = REPO / "tmp/wch-evt/evt"
OBJdump = REPO / "MRS_Toolchain_MAC_V240/Toolchain/RISC-V Embedded GCC15/bin/riscv32-wch-elf-objdump"


def sha_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: pathlib.Path) -> str:
    return path.relative_to(REPO).as_posix()


def ensure_file(path: pathlib.Path) -> pathlib.Path:
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def clean_field(value: object) -> str:
    text = str(value)
    if not text or "\t" in text or "\n" in text or "\r" in text:
        raise ValueError(f"invalid TSV field: {text!r}")
    return text


def write_tsv(name: str, header: list[str], rows: Iterable[Iterable[object]]) -> None:
    path = BUNDLE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(header)
        count = 0
        for row in rows:
            values = [clean_field(value) for value in row]
            if len(values) != len(header):
                raise ValueError(f"{name}: row width {len(values)} != {len(header)}")
            writer.writerow(values)
            count += 1
    if count == 0:
        raise ValueError(f"{name}: no data rows")


def numbered_excerpt(source: pathlib.Path, ranges: list[tuple[int, int]]) -> str:
    lines = [line.rstrip() for line in source.read_text(encoding="utf-8", errors="replace").splitlines()]
    output = [f"source\t{rel(source)}", f"sha256\t{sha_file(source)}"]
    for start, end in ranges:
        if start < 1 or end < start or end > len(lines):
            raise ValueError(f"bad line range {source}:{start}-{end}/{len(lines)}")
        output.append(f"range\t{start}-{end}")
        for number in range(start, end + 1):
            body = lines[number - 1]
            output.append(f"{number:06d}\t{body}" if body else f"{number:06d}")
    return "\n".join(output) + "\n"


EXCERPTS: dict[str, tuple[str, list[tuple[int, int]]]] = {
    "source-excerpts/field-v203-dbgmcu.txt": (
        "tmp/wch-evt/evt/QingkeV4B_CH32V203_EVT/EXAM/SRC/Peripheral/src/ch32v20x_dbgmcu.c",
        [(14, 37), (102, 126)],
    ),
    "source-excerpts/field-v205-dbgmcu.txt": (
        "tmp/wch-evt/evt/QingkeV3B_CH32V205_EVT/EXAM/SRC/Peripheral/src/ch32v205_dbgmcu.c",
        [(14, 38), (108, 124)],
    ),
    "source-excerpts/field-v317-dbgmcu.txt": (
        "tmp/wch-evt/evt/QingkeV4F_CH32V317_EVT/EXAM/SRC/Peripheral/src/ch32v30x_dbgmcu.c",
        [(14, 37), (103, 128)],
    ),
    "source-excerpts/field-h417-dbgmcu.txt": (
        "tmp/wch-evt/evt/QingkeV5F_CH32H417_EVT/EXAM/SRC/Peripheral/src/ch32h417_dbgmcu.c",
        [(14, 39), (122, 138)],
    ),
    "source-excerpts/v317-can-revision.txt": (
        "tmp/wch-evt/evt/QingkeV4F_CH32V317_EVT/EXAM/SRC/Peripheral/src/ch32v30x_can.c",
        [(87, 180)],
    ),
    "source-excerpts/v317-tim-revision.txt": (
        "tmp/wch-evt/evt/QingkeV4F_CH32V317_EVT/EXAM/SRC/Peripheral/src/ch32v30x_tim.c",
        [(106, 127)],
    ),
    "source-excerpts/v317-eth-rmii-revision.txt": (
        "tmp/wch-evt/evt/QingkeV4F_CH32V317_EVT/EXAM/ETH/NetLib/eth_driver_RMII.c",
        [(511, 535), (904, 971)],
    ),
    "source-excerpts/v317-eth-rgmii-revision.txt": (
        "tmp/wch-evt/evt/QingkeV4F_CH32V317_EVT/EXAM/ETH/NetLib/eth_driver_RGMII.c",
        [(241, 300), (610, 680)],
    ),
    "source-excerpts/v317-eth-10m-revision.txt": (
        "tmp/wch-evt/evt/QingkeV4F_CH32V317_EVT/EXAM/ETH/NetLib/eth_driver_10M.c",
        [(152, 159), (460, 548), (845, 907)],
    ),
    "source-excerpts/h417-can-revision.txt": (
        "tmp/wch-evt/evt/QingkeV5F_CH32H417_EVT/EXAM/SRC/Peripheral/src/ch32h417_can.c",
        [(91, 205)],
    ),
    "source-excerpts/h417-gpio-revision-and-model.txt": (
        "tmp/wch-evt/evt/QingkeV5F_CH32H417_EVT/EXAM/SRC/Peripheral/src/ch32h417_gpio.c",
        [(582, 625)],
    ),
    "source-excerpts/h417-adc-revision.txt": (
        "tmp/wch-evt/evt/QingkeV5F_CH32H417_EVT/EXAM/ADC/DualADC_FastInterleaved/Common/hardware.c",
        [(50, 70)],
    ),
    "source-excerpts/h417-emmc-revision.txt": (
        "tmp/wch-evt/evt/QingkeV5F_CH32H417_EVT/EXAM/SDMMC/SDMMC_eMMC/Common/sdmmc_emmc.c",
        [(92, 112)],
    ),
    "source-excerpts/h417-pwr-revision.txt": (
        "tmp/wch-evt/evt/QingkeV5F_CH32H417_EVT/EXAM/PWR/Stop_Mode/Common/hardware.c",
        [(120, 165)],
    ),
    "source-excerpts/h417-usbss-revision.txt": (
        "tmp/wch-evt/evt/QingkeV5F_CH32H417_EVT/EXAM/USBSS/DEVICE/UVC/UVC-DVP/Common/ch32h417_usbss_device.c",
        [(65, 82), (444, 465)],
    ),
    "source-excerpts/h417-usbss-revision-source.txt": (
        "tmp/wch-evt/evt/QingkeV5F_CH32H417_EVT/EXAM/USBSS/DEVICE/UVC/UVC-DVP/V3F/User/main.c",
        [(44, 58)],
    ),
    "source-excerpts/v407-eth-model.txt": (
        "tmp/wch-evt/evt/QingkeV3V_CH32V407_EVT/EXAM/ETH/NetLib/eth_driver.c",
        [(670, 700)],
    ),
    "source-excerpts/v407-gpio-revision-masked.txt": (
        "tmp/wch-evt/evt/QingkeV3V_CH32V407_EVT/EXAM/SRC/Peripheral/src/ch32v4x7_gpio.c",
        [(593, 610)],
    ),
    "source-excerpts/v006-model-revision-masked.txt": (
        "tmp/wch-evt/evt/QingkeV2C_CH32V006_EVT/EXAM/TIM/SLTIM_DMA/User/main.c",
        [(65, 100), (112, 170)],
    ),
    "source-excerpts/x315-gpio-revision-masked.txt": (
        "tmp/wch-evt/evt/QingkeV3F_CH32X315_EVT/EXAM/SRC/Peripheral/src/ch32x3x5_gpio.c",
        [(582, 600)],
    ),
}


DOCUMENT_ROWS = [
    ("DOC-REV-001", "tmp/wch-evt/application_notes/CH32V205RM.PDF", "b1ed9ef040455a1f9a32f1ab9f9be0e9d3391709bc0b6fa141b2f581593b6c59", "V1.2", 261, "CHIPID 倒数第二位为 1", "CC Source 端口必须配置为上拉输入", "DOCUMENTED-REVISION-REQUIREMENT", "V205 ChipID 表 0x205...05x0 将倒数第二个十六进制位闭合到 full CHIPID[7:4]；这是跨证据推断", "visual-pages/CH32V205RM-p261.png"),
    ("DOC-REV-002", "tmp/wch-evt/application_notes/CH32L103RM.PDF", "27a1b969cb2cb99d296ac562cac134ec63d52e4f0c75cf9d6bad7c696bc66fe3", "V2.2", 262, "CHIPID 倒数第二位为 1", "CC Source 端口必须配置为上拉输入", "DOCUMENTED-CHIPID-REQUIREMENT", "本地材料未闭合同一位到 L103 的 DBGMCU_GetREVID", "visual-pages/CH32L103RM-p262.png"),
    ("LOT-H417-001", "tmp/wch-evt/application_notes/CH32H417RM.PDF", "b57ebb0c0ae2cd772d32cb9ddeb6a6315fcc3916bcd3576e5a83eaeb7dfa6967", "V1.7", 375, "批号倒数第五位小于 3", "I3C 主机接收无数据 IBI 时 IBIF 不生效；手册指向官网 EVT 例程处理", "DOCUMENTED-LOT-ERRATUM", "checked local and official sources did not map printed lot position to REVID", "visual-pages/CH32H417RM-p375.png"),
    ("LOT-H417-002", "tmp/wch-evt/application_notes/CH32H417RM.PDF", "b57ebb0c0ae2cd772d32cb9ddeb6a6315fcc3916bcd3576e5a83eaeb7dfa6967", "V1.7", 1, "批号第五位不为 0", "支持内存保护；后文还限定 Core0 PMP 和 trigger", "LOT-GATED-CAPABILITY", "not mapped to REVID", "visual-pages/CH32H417RM-p001.png"),
    ("LOT-H417-003", "tmp/wch-evt/application_notes/CH32H417RM.PDF", "b57ebb0c0ae2cd772d32cb9ddeb6a6315fcc3916bcd3576e5a83eaeb7dfa6967", "V1.7", 672, "批号倒数第五位小于 3", "I2S FSPOL=0 时须外接上拉电阻", "DOCUMENTED-LOT-LIMITATION", "not mapped to REVID", "not-rendered"),
    ("LOT-H417-004", "tmp/wch-evt/application_notes/CH32H417RM.PDF", "b57ebb0c0ae2cd772d32cb9ddeb6a6315fcc3916bcd3576e5a83eaeb7dfa6967", "V1.7", 682, "批号倒数第五位小于 3", "QSPI 内存映射地址只能数据访问，不能指令访问", "DOCUMENTED-LOT-LIMITATION", "not mapped to REVID", "not-rendered"),
    ("LOT-H417-005", "tmp/wch-evt/application_notes/CH32H417RM.PDF", "b57ebb0c0ae2cd772d32cb9ddeb6a6315fcc3916bcd3576e5a83eaeb7dfa6967", "V1.7", 859, "批号倒数第五位小于 3", "GPHA MODE=011b 时 PL 必须大于 0", "DOCUMENTED-LOT-LIMITATION", "not mapped to REVID", "not-rendered"),
    ("LOT-FV3X-001", "tmp/wch-evt/application_notes/CH32FV2x_V3xRM.PDF", "6bdc58b159a95c40e815eb9973df1f7e7309b08e8018bad1991a71c792cefb95", "V2.5", 148, "批号倒数第五位/倒数第六位组合", "DMA1 跨 64K 或 128K 边界受限，通道范围随批次变化", "DOCUMENTED-LOT-LIMITATION", "not mapped to REVID", "visual-pages/CH32FV2x_V3xRM-p148.png"),
    ("LOT-V407-001", "tmp/wch-evt/application_notes/CH32V407RM.PDF", "63625af9027af6abfff57a58f8d2afdb2b68ee7d31c323e407da6ea786573c56", "V1.1", 11, "批号倒数第五位为 0", "待机前未作唤醒用途的 GPIO 必须配置为模拟输入", "DOCUMENTED-LOT-REQUIREMENT", "not mapped to REVID", "not-rendered"),
    ("LOT-V407-002", "tmp/wch-evt/application_notes/CH32V407RM.PDF", "63625af9027af6abfff57a58f8d2afdb2b68ee7d31c323e407da6ea786573c56", "V1.1", 7, "批号倒数第五位大于 0", "非零等待区支持 RVV 指令和 DMA 64 位访问", "LOT-GATED-CAPABILITY", "not mapped to REVID", "not-rendered"),
    ("LOT-V003-001", "tmp/wch-evt/application_notes/CH32V003RM.PDF", "7a6bf439ecd68e0b87ffdd6765da2ef9b1796ce16084b7d1f25a658380c3bcfe", "V1.9", 175, "批号第五位小于 2", "SPI 高速读模式仅在时钟 2 分频时有效", "DOCUMENTED-LOT-LIMITATION", "not mapped to REVID", "not-rendered"),
    ("LOT-X103-001", "tmp/wch-evt/application_notes/CH32xRM.PDF", "b4ade26ba00e0f03ea8c13d89badf5491bcdebbfa10957c4839ecc60f34b3cad", "V2.0", 210, "批号第五位小于等于 5", "SPI 高速读模式仅在时钟 2 分频时有效", "DOCUMENTED-LOT-LIMITATION", "not mapped to REVID", "not-rendered"),
    ("LOT-X315-001", "tmp/wch-evt/application_notes/CH32X315RM.PDF", "b6a752f9e9bdbb1d1fd9c8ba62f6e52633620c06c0d21fbc450925541a0c2785", "V1.1", 13, "批号第五位大于 0", "时钟树中标蓝功能可用", "LOT-GATED-CAPABILITY", "not mapped to REVID", "not-rendered"),
    ("LOT-H417-GUIDE-001", "tmp/wch-evt/evt/QingkeV5F_CH32H417_EVT/PUB/CH32H417∆¿π¿∞ÂÀµ√˜ È.pdf", "14ea6def0bf9288233d32080b9f0541767f76f3a21b0417dbf832f0f0faf4d7b", "V1.1-local", 11, "批号第五位不为 0", "支持 WCHISPTool 的 USB/串口下载", "LOT-GATED-CAPABILITY", "not mapped to REVID", "not-rendered"),
]


REVISION_FINDINGS = [
    ("REV-WCH-001", "CH32V30x/V31x", "full CHIPID[7:4]", "4..7", "CAN_Init 在常规初始化前执行额外 CAN/RCC 复位、过滤器状态清理和总线状态序列", "REVISION-WORKAROUND-CANDIDATE", "candidate-only: no checked manual states the defect", "source plus emitted object", "V317 peripheral CAN", "ch32v30x_can.c:91-169"),
    ("REV-WCH-002", "CH32V30x/V31x", "full CHIPID[7:4]", "4..8", "TIM1/8/9/10 初始化额外置 CTLR1 bit13", "REVISION-WORKAROUND-CANDIDATE", "candidate-only: undocumented bit purpose", "source plus emitted object", "V317 peripheral TIM", "ch32v30x_tim.c:110-116"),
    ("REV-WCH-003", "CH32V30x/V31x Ethernet RMII/MII/RGMII", "full CHIPID[7:4]", "0..2", "PHY 状态零值重试、重复状态抑制；漏帧计数异常时重建 MAC 并恢复 DMA", "REVISION-WORKAROUND-CANDIDATE", "candidate-only: recovery shape without causal document", "source; 20 physical copies", "V317 ETH three interface modes", "eth_driver_{RMII,MII,RGMII}.c"),
    ("REV-WCH-004", "CH32V30x/V31x Ethernet RGMII", "full CHIPID[7:4]", "6..15", "千兆链路将 TXC 延迟从 (0,4) 改为 (1,2)", "REVISION-COMPATIBILITY", "timing tuning; not classified as erratum", "source", "V317 ETH RGMII", "eth_driver_RGMII.c:270-295"),
    ("REV-WCH-005", "CH32V30x/V31x internal 10M PHY", "full CHIPID[7:4]", "2", "漏帧时重建 MAC；自动协商失败时切换 P/N 极性", "REVISION-WORKAROUND-CANDIDATE", "candidate-only: recovery shape without causal document", "source plus linked ELF", "V317 ETH 10M", "eth_driver_10M.c:152-159,460-548"),
    ("REV-WCH-006", "CH32V30x/V31x internal 10M PHY", "full CHIPID[7:4]", "1", "RBU 中断时归还下一 Rx 描述符 OWN 并恢复接收 DMA", "REVISION-WORKAROUND-CANDIDATE", "candidate-only: recovery shape without causal document", "source plus linked ELF", "V317 ETH 10M", "eth_driver_10M.c:845-861"),
    ("REV-WCH-007", "CH32H415/H416/H417", "full CHIPID[7:4]", "0", "CAN_Init 在常规初始化前执行三路 CAN/RCC 复位、过滤器状态清理和总线状态序列", "REVISION-WORKAROUND-CANDIDATE", "candidate-only: no checked manual states the defect", "source plus linked ELF", "H417 peripheral CAN", "ch32h417_can.c:95-191"),
    ("REV-WCH-008", "CH32H415/H416/H417", "full CHIPID[7:4]", "0", "GPIO_IPD_Unused 临时开 SWPMI 时钟并置 OR bit0；随后另行屏蔽 revision 做型号/封装 switch", "REVISION-WORKAROUND-CANDIDATE", "candidate-only: side-by-side revision and model gates", "source plus linked ELF", "H417 peripheral GPIO", "ch32h417_gpio.c:598-607"),
    ("REV-WCH-009", "CH32H415/H416/H417 ADC examples", "full CHIPID[7:4]", "0", "ADC1 校准后调用 ADC_HD_CalibrationCmd(DISABLE)", "REVISION-WORKAROUND-CANDIDATE", "example-only; no causal document", "six source copies", "H417 dual-ADC examples", "six ADC hardware.c files"),
    ("REV-WCH-010", "CH32H415/H416/H417 eMMC examples", "full CHIPID[7:4]", "0", "eMMC GPIO 初始化前开 SWPMI 时钟并置 OR bit0", "REVISION-WORKAROUND-CANDIDATE", "example-only; no causal document", "three source copies", "H417 eMMC examples", "three sdmmc_emmc.c files"),
    ("REV-WCH-011", "CH32H415/H416/H417 stop mode example", "full CHIPID[7:4]", "0/1/2", "按 revision 选择三组停止模式低功耗稳压配置", "REVISION-COMPATIBILITY", "calibration/configuration delta; not necessarily a defect", "source", "H417 PWR example", "Stop_Mode/Common/hardware.c:128-158"),
    ("REV-WCH-012", "CH32H415/H416/H417 USBSS/UHSIF", "full CHIPID[7:4]", "below 3 versus 3 and above", "新 revision 使能 RX_SET_FC；旧 revision 软件处理 SET_LINK_FUNC 并更新 U1/U2", "REVISION-COMPATIBILITY", "feature evolution; no causal defect document", "five ID assignments plus three driver copies", "H417 USBSS/UHSIF", "three ch32h417_usbss_device.c groups"),
]


def generate_source_excerpts() -> list[pathlib.Path]:
    sources: list[pathlib.Path] = []
    for destination, (source_rel, ranges) in EXCERPTS.items():
        source = ensure_file(REPO / source_rel)
        sources.append(source)
        target = BUNDLE / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(numbered_excerpt(source, ranges), encoding="utf-8")
    return sources


def pdf_pages(path: pathlib.Path) -> int:
    result = subprocess.run(["pdfinfo", str(path)], check=True, text=True, capture_output=True)
    match = re.search(r"^Pages:\s+(\d+)\s*$", result.stdout, re.MULTILINE)
    if not match:
        raise RuntimeError(f"Pages not found in pdfinfo output: {path}")
    return int(match.group(1))


def generate_documents() -> list[pathlib.Path]:
    documents: dict[str, pathlib.Path] = {}
    page_counts: dict[str, int] = {}
    for row in DOCUMENT_ROWS:
        path = ensure_file(REPO / row[1])
        if sha_file(path) != row[2]:
            raise AssertionError(f"document hash drift: {row[1]}")
        documents[row[1]] = path
        page_counts[row[1]] = pdf_pages(path)
        output = BUNDLE / "document-excerpts" / f"{row[0]}-p{int(row[4]):03d}.txt"
        output.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            ["pdftotext", "-f", str(row[4]), "-l", str(row[4]), "-layout", "-enc", "UTF-8", str(path), "-"],
            check=True,
            capture_output=True,
        )
        output.write_bytes(result.stdout.replace(b"\r\n", b"\n").replace(b"\r", b"\n"))

    visual_map = {
        "CH32V205RM-p261.png": "CH32V205RM-261.png",
        "CH32L103RM-p262.png": "CH32L103RM-262.png",
        "CH32H417RM-p001.png": "CH32H417RM-p001-001.png",
        "CH32H417RM-p375.png": "CH32H417RM-p375-375.png",
        "CH32FV2x_V3xRM-p148.png": "CH32FV2x_V3xRM-p148-148.png",
    }
    for destination, source_name in visual_map.items():
        source = ensure_file(RUN / "pdf-render" / source_name)
        target = BUNDLE / "visual-pages" / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)

    rows = []
    for row in DOCUMENT_ROWS:
        rows.append(("1", *row[:4], page_counts[row[1]], *row[4:]))
    write_tsv(
        "document-review.tsv",
        ["schema_version", "document_id", "path", "sha256", "version", "pdf_pages", "pdf_page", "condition", "documented_behavior", "classification", "runtime_revid_mapping", "visual_evidence"],
        rows,
    )
    write_tsv(
        "visual-review.tsv",
        ["schema_version", "document_id", "pdf_page", "printed_page", "image", "review_result"],
        [
            ("1", "DOC-REV-001", 261, 256, "visual-pages/CH32V205RM-p261.png", "manual image confirms CHIPID condition and pull-up-input requirement"),
            ("1", "DOC-REV-002", 262, 257, "visual-pages/CH32L103RM-p262.png", "manual image confirms CHIPID condition and pull-up-input requirement"),
            ("1", "LOT-H417-002", 1, "front-matter", "visual-pages/CH32H417RM-p001.png", "manual image confirms lot-gated memory-protection note"),
            ("1", "LOT-H417-001", 375, 371, "visual-pages/CH32H417RM-p375.png", "manual image confirms IBIF failure and EVT handling reference"),
            ("1", "LOT-FV3X-001", 148, 145, "visual-pages/CH32FV2x_V3xRM-p148.png", "manual image confirms DMA boundary restrictions and lot conditions"),
        ],
    )
    return list(documents.values())


def run_objdump(source: pathlib.Path, function: str, destination: str) -> None:
    ensure_file(OBJdump)
    ensure_file(source)
    result = subprocess.run(
        [str(OBJdump), "-dr", f"--disassemble={function}", str(source)],
        check=True,
        text=True,
        capture_output=True,
    )
    target = BUNDLE / "disassembly" / destination
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(result.stdout.replace("\r\n", "\n").replace("\r", "\n"), encoding="utf-8")


def generate_binary_evidence() -> list[pathlib.Path]:
    v317_touch = REPO / "tmp/wch-evt/validation/round2/byte-identical-r12b-run/wch/QingkeV4F_CH32V317_EVT_EXAM_TOUCHKEY_TKey--80ecbef700c9"
    h417_can = REPO / "tmp/wch-evt/validation/round2/byte-identical-r12b-run/wch/QingkeV5F_CH32H417_EVT_EXAM_CAN_TestMode_V3F--258624070cce"
    v317_eth = RUN / "build-v317-eth-mac-raw"
    targets = [
        (v317_touch / "obj/0004_ch32v30x_can.o", "CAN_Init", "v317-CAN_Init.txt"),
        (v317_touch / "obj/0025_ch32v30x_tim.o", "TIM_TimeBaseInit", "v317-TIM_TimeBaseInit.txt"),
        (h417_can / "obj/0007_ch32h417_can.o", "CAN_Init", "h417-CAN_Init.txt"),
        (h417_can / "obj/0020_ch32h417_gpio.o", "GPIO_IPD_Unused", "h417-GPIO_IPD_Unused.txt"),
        (v317_eth / "MAC_RAW.elf", "ETH_PHYLink", "v317-10m-ETH_PHYLink-linked.txt"),
        (v317_eth / "MAC_RAW.elf", "WCHNET_RecProcess", "v317-10m-WCHNET_RecProcess-linked.txt"),
        (v317_eth / "MAC_RAW.elf", "WCHNET_ETHIsr", "v317-10m-WCHNET_ETHIsr-linked.txt"),
        (v317_eth / "MAC_RAW.elf", "ETH_Init", "v317-10m-ETH_Init-linked.txt"),
    ]
    for source, function, destination in targets:
        run_objdump(source, function, destination)

    old = REPO / "audit-report-f/followup/results/06b-chipid-errata-evidence/controls/positive"
    copies = [
        "disassembly/0b196fff0b9f666fc30cd4dcebe90ef299f1fed37fff6b66f460951515e494ca-GetChipID.txt",
        "disassembly/0b196fff0b9f666fc30cd4dcebe90ef299f1fed37fff6b66f460951515e494ca-getTxBuffAddr.txt",
        "disassembly/0c796a85a0123d5338803c1a144d3dbac76e906a6f652f73155cd6a8a6f28ac4-GetChipID.txt",
        "disassembly/0c796a85a0123d5338803c1a144d3dbac76e906a6f652f73155cd6a8a6f28ac4-getTxBuffAddr.txt",
        "positive-occurrences.tsv",
        "positive-summary.json",
        "semantic-chain.json",
    ]
    for item in copies:
        source = ensure_file(old / item)
        target = BUNDLE / "wchnet-binary" / pathlib.Path(item).name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)

    build_rows = []
    build_specs = [
        ("BUILD-V317-ETH", v317_eth, "MAC_RAW.elf", "linked", "ETH_PHYLink,WCHNET_RecProcess,WCHNET_ETHIsr,ETH_Init,ChipId"),
        ("BUILD-V317-PERIPH", v317_touch, "obj/0004_ch32v30x_can.o", "object-emitted; functions discarded by unrelated TOUCHKEY link", "CAN_Init; TIM_TimeBaseInit in sibling object"),
        ("BUILD-H417-CAN", h417_can, "TestMode_V3F.elf", "linked", "CAN_Init,GPIO_IPD_Unused"),
    ]
    for build_id, directory, artifact_rel, link_state, symbols in build_specs:
        artifact = ensure_file(directory / artifact_rel)
        status_file = ensure_file(directory / "build-status.txt")
        exit_file = ensure_file(directory / "exit-code.txt")
        build_rows.append((
            "1", build_id, rel(directory), status_file.read_text(encoding="utf-8").strip(),
            exit_file.read_text(encoding="utf-8").strip(), rel(artifact), sha_file(artifact), link_state, symbols,
        ))
    write_tsv(
        "build-evidence.tsv",
        ["schema_version", "build_id", "build_directory", "build_status", "exit_code", "artifact", "artifact_sha256", "link_state", "relevant_symbols"],
        build_rows,
    )
    return [source for source, _, _ in targets]


def generate_tables() -> None:
    write_tsv(
        "chipid-layout.tsv",
        ["schema_version", "source_api_or_load", "address_or_expression", "full_chipid_bits", "semantic_field", "selector_example", "conclusion", "source_anchor"],
        [
            ("1", "DBGMCU_GetCHIPID", "u32 load @0x1FFFF704", "31:0", "CHIPID", "entire word", "combined model/package/revision identity word", "V317 dbg source:103-127"),
            ("1", "DBGMCU_GetREVID", "u32 load &0x0000FFFF", "15:0", "REVID", "vendor API names low half revision identifier", "low half is revision identifier; do not assume every bit is a monotonic revision number", "V317 dbg source:17-25"),
            ("1", "runtime revision selector", "CHIPID >>4 &0xF", "7:4", "REVID wildcard nibble", "V317/H417 branches", "same model can take different paths; published CHIPID lists mark this nibble x/X", "V317 ChipID list:108-123"),
            ("1", "DBGMCU_GetDEVID", "u32 load >>16", "31:16", "DEVID", "vendor API names high half device identifier", "model/package identity half", "V317 dbg source:29-37"),
            ("1", "WCHNET GetChipID", "lhu @0x1FFFF706", "31:16", "DEVID", "little-endian halfword at base+2", "reads DEVID, not REVID", "06b binary GetChipID disassembly plus SDK field split"),
            ("1", "WCHNET predicate", "lhu @0x1FFFF706 &0x00F0", "23:20", "DEVID model-family nibble", "equals 0x30 or 0x80", "cross-chip model-family select, not same-chip revision select", "WCHNET binary plus vendor CHIPID lists"),
        ],
    )
    write_tsv(
        "revision-findings.tsv",
        ["schema_version", "finding_id", "device_scope", "selector_field", "affected_revisions", "behavior_delta", "classification", "errata_status", "evidence_strength", "source_group", "source_anchor"],
        [("1", *row) for row in REVISION_FINDINGS],
    )
    write_tsv(
        "wchnet-model-domain.tsv",
        ["schema_version", "archive_scope", "documented_model_families", "full_chipid_23_20_values", "predicate_0x30_reachable", "predicate_0x80_reachable", "classification"],
        [
            ("1", "QingkeV4B_CH32V203_EVT", "CH32V203;CH32V208", "0x30;0x80", "yes: V203", "yes: V208", "MODEL-SELECT; both binary special values are model families"),
            ("1", "QingkeV4C_CH32V20x_EVT", "CH32V203;CH32V208", "0x30;0x80", "yes: V203", "yes: V208", "MODEL-SELECT; both binary special values are model families"),
            ("1", "QingkeV4F_CH32V317_EVT", "CH32V303;CH32V305;CH32V307;CH32V317", "0x30;0x50;0x70", "yes: V303", "no", "MODEL-SELECT; 0x80 unreachable in published package family list"),
            ("1", "QingkeV3V_CH32V407_EVT", "CH32V407;CH32V467", "0x70", "no", "no", "MODEL-SELECT; copied/dead special branch for published target families"),
            ("1", "QingkeV5F_CH32H417_EVT", "CH32H415;CH32H416;CH32H417", "0x50;0x60;0x70", "no", "no", "MODEL-SELECT; copied/dead special branch for published target families"),
        ],
    )
    write_tsv(
        "selector-classification.tsv",
        ["schema_version", "group_id", "package_or_family", "selector_expression", "full_chipid_bits", "physical_sites", "classification", "revision_sensitive", "rationale", "representative_path"],
        [
            ("1", "SEL-WCHNET", "five WCHNET archives", "lhu 0x1FFFF706 &0xF0 ==0x30/0x80", "23:20", "8 archive-member occurrences; 2 object hashes", "MODEL-SELECT", "no", "SDK names high half DEVID and model tables map values to V203/V208/V303 families", "wchnet-binary/*-GetChipID.txt"),
            ("1", "SEL-V317-CAN", "V317 package", "CHIPID>>4 &0xF in 4..7", "7:4", "1 source", "REVISION-SELECT", "yes", "published model patterns keep model digits fixed and wildcard this nibble", "ch32v30x_can.c"),
            ("1", "SEL-V317-TIM", "V317 package", "CHIPID[7:4] in 4..8", "7:4", "1 source", "REVISION-SELECT", "yes", "same model can select alternate timer setup", "ch32v30x_tim.c"),
            ("1", "SEL-V317-ETH", "V317 package", "ChipId &0xF0 thresholds/equalities", "7:4", "20 source files; 4 semantic modes", "REVISION-SELECT", "yes", "recovery/tuning varies within a published model pattern", "EXAM/ETH/NetLib/eth_driver_*.c"),
            ("1", "SEL-H417-CAN", "H417 package", "ChipId &0xF0 ==0", "7:4", "1 source", "REVISION-SELECT", "yes", "revision-zero alternate CAN sequence", "ch32h417_can.c"),
            ("1", "SEL-H417-GPIO-REV", "H417 package", "CHIPID &0xF0 ==0", "7:4", "1 source", "REVISION-SELECT", "yes", "revision-zero SWPMI operation", "ch32h417_gpio.c:598-604"),
            ("1", "SEL-H417-GPIO-MODEL", "H417 package", "CHIPID &~0xF0 then switch", "all except 7:4", "1 source", "REVISION-INSENSITIVE-MODEL-SELECT", "no", "code explicitly removes revision nibble before model/package switch", "ch32h417_gpio.c:605-607"),
            ("1", "SEL-H417-ADC", "H417 package", "CHIPID &0xF0 ==0", "7:4", "6 source files", "REVISION-SELECT", "yes", "revision-zero calibration delta", "EXAM/ADC/DualADC_*/Common/hardware.c"),
            ("1", "SEL-H417-EMMC", "H417 package", "ChipID &0xF0 ==0", "7:4", "3 source files", "REVISION-SELECT", "yes", "revision-zero SWPMI operation", "three sdmmc_emmc.c copies"),
            ("1", "SEL-H417-PWR", "H417 package", "CHIPID[7:4] switch 0/1/2", "7:4", "1 source", "REVISION-SELECT", "yes", "per-revision regulator configuration", "PWR/Stop_Mode/Common/hardware.c"),
            ("1", "SEL-H417-USBSS", "H417 package", "Chip=CHIPID[7:4]; Chip<3/>=3", "7:4", "5 assignments plus 3 driver copies", "REVISION-SELECT", "yes", "link feature handling changes by revision", "USBSS/UHSIF ch32h417_usbss_device.c"),
            ("1", "SEL-V407-ETH", "V407 package", "CHIPID>>16 &0xF ==2/5", "19:16", "2 source files", "MODEL/PACKAGE-SELECT", "no", "high-half DEVID package subcode selects LED/PHY pin mapping", "V407 ETH eth_driver.c"),
            ("1", "SEL-V407-GPIO", "V407 package", "CHIPID &~0xF0 then switch", "all except 7:4", "1 source", "REVISION-INSENSITIVE-MODEL-SELECT", "no", "revision nibble removed", "ch32v4x7_gpio.c"),
            ("1", "SEL-V006-SLTIM", "V006 package", "CHIPID &~0xF0 ==0x00700800", "all except 7:4", "7 tests in 1 source", "REVISION-INSENSITIVE-MODEL-SELECT", "no", "revision nibble removed", "SLTIM_DMA/User/main.c"),
            ("1", "SEL-X315-GPIO", "X315 package", "VCfg_Init() &~0xF0 then switch", "all except 7:4", "1 source", "REVISION-INSENSITIVE-MODEL-SELECT", "no", "revision nibble removed", "ch32x3x5_gpio.c"),
        ],
    )


def source_callsite_summary() -> dict[str, object]:
    files = sorted((*EVT.rglob("*.c"), *EVT.rglob("*.h")), key=lambda p: p.as_posix().encode())
    decoded: dict[pathlib.Path, str] = {path: path.read_text(encoding="utf-8", errors="replace") for path in files}

    def symbol_stats(symbol: str) -> tuple[int, int]:
        selected = [(path, text) for path, text in decoded.items() if symbol in text]
        return sum(text.count(symbol) for _, text in selected), len(selected)

    def behavior_uses(symbol: str) -> list[str]:
        uses: list[str] = []
        declaration = re.compile(rf"^\s*(?:uint32_t|u32)\s+{re.escape(symbol)}\s*\(")
        for path, text in decoded.items():
            for lineno, line in enumerate(text.splitlines(), 1):
                if symbol not in line:
                    continue
                stripped = line.strip()
                if "@fn" in stripped or stripped.startswith("*") or stripped.startswith("//"):
                    continue
                if declaration.search(line):
                    continue
                uses.append(f"{rel(path)}:{lineno}:{stripped}")
        return uses

    revid_uses = behavior_uses("DBGMCU_GetREVID")
    devid_uses = behavior_uses("DBGMCU_GetDEVID")
    if revid_uses or devid_uses:
        raise AssertionError(f"unexpected direct REVID/DEVID behavior uses: {revid_uses[:2]} {devid_uses[:2]}")

    patterns = {
        "v317_eth_revision_files": (REPO / "tmp/wch-evt/evt/QingkeV4F_CH32V317_EVT", re.compile(r"ChipId\s*&\s*0xf0")),
        "h417_adc_revision_files": (REPO / "tmp/wch-evt/evt/QingkeV5F_CH32H417_EVT/EXAM/ADC", re.compile(r"ADC_HD_CalibrationCmd\s*\(\s*ADC1\s*,\s*DISABLE\s*\)")),
        "h417_emmc_revision_files": (REPO / "tmp/wch-evt/evt/QingkeV5F_CH32H417_EVT/EXAM", re.compile(r"ChipID\s*&\s*0xF0\s*\)\s*==\s*0")),
        "h417_usbss_revision_driver_files": (REPO / "tmp/wch-evt/evt/QingkeV5F_CH32H417_EVT/EXAM", re.compile(r"Chip\s*<\s*3")),
    }
    groups: dict[str, list[str]] = {}
    for name, (root, pattern) in patterns.items():
        groups[name] = sorted(
            rel(path) for path in root.rglob("*.c")
            if pattern.search(path.read_text(encoding="utf-8", errors="replace"))
        )

    document_manifest = REPO / "audit-report-f/followup/results/06b-chipid-errata-evidence/controls/documents/document-manifest.tsv"
    with document_manifest.open("r", encoding="utf-8", newline="") as stream:
        document_rows = list(csv.DictReader(stream, delimiter="\t"))

    chipid_tokens, chipid_files = symbol_stats("DBGMCU_GetCHIPID")
    revid_tokens, revid_files = symbol_stats("DBGMCU_GetREVID")
    devid_tokens, devid_files = symbol_stats("DBGMCU_GetDEVID")
    summary = {
        "schema_version": "1",
        "source_scope": "tmp/wch-evt/evt/**/*.c,*.h",
        "source_files_scanned": len(files),
        "DBGMCU_GetCHIPID": {"text_occurrences": chipid_tokens, "files": chipid_files},
        "DBGMCU_GetREVID": {"text_occurrences": revid_tokens, "files": revid_files, "behavior_uses_outside_declaration_definition": 0},
        "DBGMCU_GetDEVID": {"text_occurrences": devid_tokens, "files": devid_files, "behavior_uses_outside_declaration_definition": 0},
        "behavior_groups": groups,
        "local_pdf_corpus": {
            "physical_files": len(document_rows),
            "content_hash_groups": len({row["sha256"] for row in document_rows}),
            "extraction_failures": sum(row["extraction_status"] != "pass" for row in document_rows),
        },
        "limits": [
            "text occurrence counts are not behavior counts",
            "selector groups were manually reviewed after broad text search",
            "printed lot-code positions are not treated as REVID without a mapping source",
        ],
    }
    if len(groups["v317_eth_revision_files"]) != 20:
        raise AssertionError("V317 ETH source-copy count drift")
    if len(groups["h417_adc_revision_files"]) != 6:
        raise AssertionError("H417 ADC source-copy count drift")
    if len(groups["h417_emmc_revision_files"]) != 3:
        raise AssertionError("H417 eMMC source-copy count drift")
    if len(groups["h417_usbss_revision_driver_files"]) != 3:
        raise AssertionError("H417 USBSS source-copy count drift")
    return summary


def write_source_hashes(paths: Iterable[pathlib.Path]) -> None:
    unique = sorted({ensure_file(path).resolve() for path in paths}, key=lambda p: rel(p).encode())
    write_tsv(
        "source-hashes.tsv",
        ["schema_version", "path", "size_bytes", "sha256"],
        [("1", rel(path), path.stat().st_size, sha_file(path)) for path in unique],
    )


def write_manifest() -> None:
    manifest = BUNDLE / "evidence-manifest.tsv"
    files = sorted(
        (path for path in BUNDLE.rglob("*") if path.is_file() and path != manifest),
        key=lambda p: p.relative_to(BUNDLE).as_posix().encode("utf-8"),
    )
    rows = []
    for path in files:
        relative = path.relative_to(BUNDLE).as_posix()
        digest = sha_file(path)
        if relative.startswith("scripts/"):
            role = "reproduction"
        elif relative.startswith("visual-pages/"):
            role = "visual-document-evidence"
        elif relative.startswith("document-excerpts/"):
            role = "document-text-evidence"
        elif relative.startswith("source-excerpts/"):
            role = "source-evidence"
        elif relative.startswith("disassembly/") or relative.startswith("wchnet-binary/"):
            role = "binary-evidence"
        else:
            role = "index-or-summary"
        evidence_id = "ev-" + hashlib.sha256((relative + "\0" + digest).encode("utf-8")).hexdigest()
        rows.append(("1", evidence_id, relative, role, path.stat().st_size, digest))
    write_tsv(
        "evidence-manifest.tsv",
        ["schema_version", "evidence_id", "path", "role", "size_bytes", "sha256"],
        rows,
    )


def main() -> None:
    for directory in ("source-excerpts", "document-excerpts", "visual-pages", "disassembly", "wchnet-binary"):
        target = BUNDLE / directory
        if target.exists():
            shutil.rmtree(target)
    generate_tables()
    source_paths = generate_source_excerpts()
    document_paths = generate_documents()
    binary_paths = generate_binary_evidence()
    summary = source_callsite_summary()
    (BUNDLE / "callsite-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    search_summary = {
        "schema_version": "1",
        "local_scope": "126 physical PDFs / 98 content hashes from the frozen 06b document manifest, plus EVT C/H source and selected builds",
        "official_sources_checked": [
            "https://github.com/openwch/ch32v20x",
            "https://github.com/openwch/ch32v307",
        ],
        "result": "official SDK distribution was found; no checked official source mapped printed package lot-code positions to DBGMCU_GetREVID values",
        "negative_claim_limit": "bounded to the recorded local corpus, query forms, and checked official repositories; not a universal absence claim",
    }
    (BUNDLE / "search-summary.json").write_text(
        json.dumps(search_summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_source_hashes((*source_paths, *document_paths, *binary_paths))
    write_manifest()
    print(f"generated {BUNDLE.relative_to(REPO)}")


if __name__ == "__main__":
    main()
