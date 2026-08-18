# WCH 文档来源账本(sha256 + 版本号)

本轮指令相关工作所引用的**一手文档**的追踪账本。凡在后续文档中引用这些材料,必须带此处的 sha256(前 16 位即可)与版本号;引用其他未列入本表的材料时,应先把它补进本表。

- 采集日期:2026-08-03
- 哈希算法:SHA-256(`shasum -a 256`),表中为**前 16 位**,全量值可由下方命令复算
- 版本号:取自文档首页的"版本/Version"字样;空白表示文档未标注版本
- 路径相对仓库根 `/Users/apple/Projects/gccriscv-wch`

## 1. 青稞内核处理器手册(`tmp/wch-evt/manual/`)

| sha256(前16) | 版本 | 字节 | 文件 |
|---|---|---|---|
| `5430356218fca280` | V1.3 | 455,773 | `QingKeV2_Processor_Manual.PDF` |
| `fcc16b54d8818b04` | V1.5 | 793,505 | `QingKeV3_Processor_Manual.PDF` |
| `b543a875a199a670` | V1.5 | 564,663 | `QingKeV4_Processor_Manual.PDF` |
| `0a849c719d135885` | V1.0 | 704,001 | `QingKeV5_Processor_Manual.PDF` |

另有预抽取文本 `tmp/wch-evt/eval/manual-text/QingKeV{2,3,4,5}_Processor_Manual.txt`(抽取产物,非一手件;引用时应指向上表 PDF)。

## 2. 芯片参考手册与应用指南(`tmp/wch-evt/application_notes/`)

| sha256(前16) | 版本 | 字节 | 文件 |
|---|---|---|---|
| `6bdc58b159a95c40` | V2.5 | 7,345,516 | `CH32FV2x_V3xRM.PDF` |
| `b57ebb0c0ae2cd77` | V1.7 | 8,188,806 | `CH32H417RM.PDF` |
| `27a1b969cb2cb99d` | V2.2 | 3,331,776 | `CH32L103RM.PDF` |
| `109a7bb0ab9a0b70` | V1.2 | 4,563,783 | `CH32M030RM.PDF` |
| `7a6bf439ecd68e0b` | V1.9 | 2,155,889 | `CH32V003RM.PDF` |
| `7d216d69fd04d990` | V1.5 | 3,211,719 | `CH32V00XRM.PDF` |
| `b1ed9ef040455a1f` | V1.2 | 4,718,058 | `CH32V205RM.PDF` |
| `63625af9027af6ab` | V1.1 | 5,214,830 | `CH32V407RM.PDF` |
| `c7e301eac4790ca1` | V1.9 | 2,578,952 | `CH32X035RM.PDF` |
| `b6a752f9e9bdbb1d` | V1.1 | 3,113,343 | `CH32X315RM.PDF` |
| `b4ade26ba00e0f03` | V2.0 | 4,281,279 | `CH32xRM.PDF` |
| `af83c6fca780cfed` | V1.4 | 1,904,409 | `CH641RM.PDF` |
| `38ebe89c93b5a0aa` | V1.0 | 2,654,317 | `WCH_TouchApplicationGuide.PDF` |

## 3. PIOC / RISC8B 子系统(EVT 树内)

| sha256(前16) | 版本 | 字节 | 文件 | 跨树副本 |
|---|---|---|---|---|
| `38231bec89ea50ab` | 版本:2B | 184,327 | `EXAM/PIOC/Tool_Manual/Manual/CHRISC8B.PDF` | **3 份逐字节相同**(V006 / V205 / H417) |
| `a3b0ac3fa84387ee` | Version: 2B | 200,432 | `.../CHRISC8B-EN.pdf`(H417) | 仅 1 份 |
| `61e543eb2dcdf538` | 版本:1 | 143,828 | `EXAM/PIOC/Tool_Manual/Manual/PIOC.PDF`(中文完整手册,12 页级) | **3 份逐字节相同**(V006 / V205 / H417) |
| `d8b62cd7359d53c1` | Version: V1 | 174,525 | `.../PIOC-EN.pdf`(H417)—— **`PIOC.PDF` 的真正英文对应版,12 页** | 仅 1 份 |
| `62b3ed245b6a43b2` | Version: V1.0 | 140,167 | `.../PIOC User Manual-EN.pdf`(H417)—— **名不副实:实为 2 页 1-Wire 快速入门** | 仅 1 份 |
| `4407b61b208a48ed` | V1.0 | 4,190 | `EXAM/PIOC/PIOC_UART/Asm/PIOC_INC.ASM`(V006) | 未逐一比对其余副本 |
| `754262d76a010c8c` | —(未标注) | 27,201 | `EXAM/PIOC/PIOC_1_Wire/Asm/RGB1W.ASM`(V006) | 未逐一比对 |
| `b23125ee811a1078` | —(未标注) | 9,339 | `EXAM/PIOC/PIOC_1_Wire/Asm/RGB1W_inc.h`(V006) | 未逐一比对 |

中英文版的 `CHRISC8B` 同为版本 **2B**,已逐行核对**内容一致**,可互相印证。

**PIOC 文档的对应关系此前记错,已更正**(由 EVT PDF 扫描单元发现、本轮实测确认):`PIOC User Manual-EN.pdf` **不是** `PIOC.PDF` 的英文版——它只有 **2 页**,是 1-Wire 快速入门,对应的中文件是 `PIOC 使用说明.pdf`。`PIOC.PDF`(中文完整手册)的真正英文对应版是 **`PIOC-EN.pdf`**(12 页,`d8b62cd7359d53c1`,Version: V1),已逐节与寄存器表核对一致。这是 WCH 自己 EVT 树里的**文件名与内容不符**,引用时务必按内容而非文件名选取。

工具二进制 `WASM53B.EXE`、`BIN_HEX.EXE` 位于 `EXAM/PIOC/Tool_Manual/Tool/`,本轮未运行、未计哈希;若后续要用,补入本表。

## 4. 复算命令

```sh
# 单文件全量哈希
shasum -a 256 "tmp/wch-evt/manual/QingKeV4_Processor_Manual.PDF"

# 跨树副本一致性(以 CHRISC8B 为例)
find tmp/wch-evt/evt -name 'CHRISC8B.PDF' -print0 | xargs -0 shasum -a 256

# 版本号来源:文档首页
pdftotext -f 1 -l 2 -layout "<pdf>" - | grep -iE '版本|Version'
```

## 5. 使用约定

1. 后续两份指令文档中的**每一条来自文档的结论**,出处写作:`文档名 vX.Y (sha256:前16位) 第 N 页`。
2. 本表未收录的材料(如 EVT 树内其余约 100 份 PDF)由对应的扫描单元自行建表,格式同上,最终合并进本表。
3. 抽取产物(`*-text/` 下的 `.txt`)不是一手件,**不得作为出处**;出处始终指向原始 PDF 及其哈希。
4. 同一文档跨树存在多份副本时,先验证是否逐字节相同:相同则记一个内容组并列出路径;不同则**分别成条**,不可合并。
