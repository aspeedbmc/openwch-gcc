# WCH 芯片参考手册与触摸库说明：特殊指令与特殊寄存器索引

本文索引 13 份 WCH 参考手册/应用指南 + 6 份触摸库说明中**讲解非标准指令与厂商自定义寄存器**的段落，用于底层代码编写时的接口核对。

---

## 0. 使用约定与文档账本

### 0.1 出处格式

每条结论的出处写作 `文档名 vX.Y (sha256:前16位) 第 N 页`。

- **N 是 PDF 物理页码**（`pdftotext` 页序，从 1 开始）。手册页脚印刷页码普遍比物理页码小 1～4（封面/目录不计入），需要时正文中会附注。
- 引用一律指向**原始 PDF**。`tmp/wch-evt/eval/appnote-text/*.txt` 是本轮的抽取产物，非一手件，不作为出处。
- 「手册明确写的」与「本文推断」严格分开，后者一律以 **[推断]** 开头。

### 0.2 文档账本（13 份参考手册/应用指南）

引自 `/Users/apple/Projects/gccriscv-wch/wch-doc-provenance.md` §2，目录 `tmp/wch-evt/application_notes/`：

| 文档 | 版本 | sha256(前16) | PDF 页数 |
|---|---|---|---|
| CH32FV2x_V3xRM | V2.5 | `6bdc58b159a95c40` | 553 |
| CH32H417RM | V1.7 | `b57ebb0c0ae2cd77` | 879 |
| CH32L103RM | V2.2 | `27a1b969cb2cb99d` | 313 |
| CH32M030RM | V1.2 | `109a7bb0ab9a0b70` | 251 |
| CH32V003RM | V1.9 | `7a6bf439ecd68e0b` | 194 |
| CH32V00XRM | V1.5 | `7d216d69fd04d990` | 229 |
| CH32V205RM | V1.2 | `b1ed9ef040455a1f` | 389 |
| CH32V407RM | V1.1 | `63625af9027af6ab` | 537 |
| CH32X035RM | V1.9 | `c7e301eac4790ca1` | 246 |
| CH32X315RM | V1.1 | `b6a752f9e9bdbb1d` | 310 |
| CH32xRM | V2.0 | `b4ade26ba00e0f03` | 286 |
| CH641RM | V1.4 | `af83c6fca780cfed` | 175 |
| WCH_TouchApplicationGuide | V1.0 | `38ebe89c93b5a0aa` | 11 |

### 0.3 文档账本（6 份触摸库说明，本轮新计）

哈希算法与账本一致（`shasum -a 256`，取前 16 位）。文件名在磁盘上是 **GBK 字节被按 MacRoman 解码后再 UTF-8 编码**的双重损坏形式，下表「原始文件名」是还原值（`name.encode('mac_roman').decode('gbk')`）。

| sha256(前16) | 版本 | 字节 | 原始文件名 | 仓库路径 |
|---|---|---|---|---|
| `bf50109705ef8acb` | V1.1 | 269,024 | `WCH_touch_V3库使用说明.pdf` | `tmp/wch-evt/evt/QingkeV3C_CH587_EVT/EXAM/TOUCH/` |
| `1d55728072da8f86` | —（未标注） | 375,168 | `WCH_touchkey_lite库使用说明.pdf` | `tmp/wch-evt/evt/QingkeV2C_CH32V006_EVT/EXAM/TOUCHKEY/DOC_SCH_PCB/` |
| `9c0f28254428f039` | —（未标注） | 3,037,502 | `WCH触摸应用指南.pdf` | 同上 |
| `9693ef4c83762e3e` | —（原理图） | 101,244 | `CH32V00x_Touch_Kit.pdf` | 同上 |
| `6544e5b72df170db` | —（原理图） | 56,996 | `WCH_TOUCH_Kit_EX001.pdf` | 同上 |
| `2c860b1092ea0cd3` | —（原理图） | 42,142 | `WCH_TOUCH_Kit_EX002.pdf` | 同上 |

复算命令（zsh，避开乱码文件名手打）：

```sh
cd /Users/apple/Projects/gccriscv-wch
find tmp/wch-evt/evt/QingkeV3C_CH587_EVT/EXAM/TOUCH \
     tmp/wch-evt/evt/QingkeV2C_CH32V006_EVT/EXAM/TOUCHKEY/DOC_SCH_PCB \
     -maxdepth 1 -name '*.pdf' -print0 | xargs -0 shasum -a 256
```

**版本标注说明**：`WCH_touch_V3库使用说明.pdf` 每页页脚印有 `V1.1`。另两份（`WCH_touchkey_lite库使用说明.pdf`、`WCH触摸应用指南.pdf`）全文无版本/修订记录字样，故记为「未标注」；引用时以 sha256 为唯一标识。3 份 Kit PDF 是 Altium 导出的原理图，无版本页也无寄存器内容。

### 0.4 内核对应关系（后文差异分析的基线）

各手册首页「RISC-V 内核版本概览」表：

| 手册 | 版本 | 内核 | 手册给出的指令集串 | 出处 |
|---|---|---|---|---|
| CH32V003RM | V1.9 | 青稞 V2A | `RV32EC` | `7a6bf439ecd68e0b` 第 1 页 |
| CH641RM | V1.4 | 青稞 V2A | `RV32EC` | `af83c6fca780cfed` 第 1 页 |
| CH32V00XRM | V1.5 | 青稞 V2C | `RV32EmC` | `7d216d69fd04d990` 第 1 页 |
| CH32M030RM | V1.2 | 青稞 V3B | `IMCB` | `109a7bb0ab9a0b70` 第 1 页 |
| CH32V205RM | V1.2 | 青稞 V3B | `IMCB` | `b1ed9ef040455a1f` 第 1 页 |
| CH32X315RM | V1.1 | 青稞 V3F | `IMAFBC-X` | `b6a752f9e9bdbb1d` 第 1 页 |
| CH32V407RM | V1.1 | 青稞 V3V | `IMACV-X` | `63625af9027af6ab` 第 1 页 |
| CH32X035RM | V1.9 | 青稞 V4C | `IMAC` | `c7e301eac4790ca1` 第 1 页 |
| CH32L103RM | V2.2 | 青稞 V4C | `IMAC` | `27a1b969cb2cb99d` 第 1 页 |
| CH32FV2x_V3xRM | V2.5 | 青稞 V4B/V4C/V4F | `IMAC` / `IMAC` / `IMAFC` | `6bdc58b159a95c40` 第 1、3 页 |
| CH32H417RM | V1.7 | 青稞 V3F + V5F 双核 | 两核均 `IMABCF-X` | `b57ebb0c0ae2cd77` 第 1 页 |
| CH32xRM | V2.0 | Cortex-M3（CH32F103x）/ 青稞 V3A（CH32V103x） | `RV32IMAC` | `b4ade26ba00e0f03` 第 1 页 |

> **CH32xRM 特别提示**：该手册同时覆盖 ARM Cortex-M3 的 CH32F103x 与 RISC-V 的 CH32V103x，第 1 页有专门的对比表（「中断控制器 NVIC / PFIC」「位段映射 支持 / 不支持」「TKEY_F / TKEY_V 用法不同」）。读其寄存器章节时必须先确认所述是哪一支。

各手册均在首页写明「有关 RISC-V 内核的相关信息，可参考 QingKeVx 微处理手册」——**指令编码层面的权威定义在青稞处理器手册而非本批参考手册**（CH32H417RM 与 CH32V407RM 例外，见第 1、2 节）。

---

## 1. 非标准 / 厂商自定义指令

### 1.1 CH32V407（青稞 V3V）——本批 13 份芯片/应用手册中唯一给出**位编码**的自定义指令

出处：CH32V407RM V1.1 (`63625af9027af6ab`) 第 57–58 页（第 9 章 中央处理器（CPU），页脚印刷页 55–56）。

原文（第 57 页）：「**9.2.1.3 自定义延时指令** — 自定义延时指令是以单指令开销为代价的精确延时指令，可延时指定匹配的指令精确至时钟周期精度，避免定时器，延时等操作中指令跳转执行的不确定性，指令可自动匹配指令编码、配置延时周期、时钟分频系数」。
EN: a single-instruction precise-delay instruction, cycle-accurate, avoiding branch jitter of timer/delay loops.

**延时指令（dly）位编码**（照抄原表，跨第 57–58 页）：

| 位 | 名称 | 描述（原文） |
|---|---|---|
| [31:20] | `imm` | 延时立即数，根据配置可表示延时的时钟周期数或分频后的周期数。 |
| [19:15] | `rs1` | 匹配的 rs1 寄存器编码。 |
| [14:12] | `func3` | **固定值 001b**。 |
| [11:9] | `match` | 匹配的指令类型，在延时未结束时匹配的指令类型无法执行。`000`：保留；`001`：匹配 load 指令；`010`：匹配 store 指令；`011`：匹配 load/store 指令；`100`：匹配 delay 指令；`101`：保留；`110`：匹配所有指令（流水线暂停）；`111`：匹配指定 func3 和 opcode 的指令（匹配值由 csr 寄存器配置）。 |
| 8 | `div` | 使用主频时钟或分频时钟计数。`1`：使用分频周期计数（分频系数由 CSR 寄存器配置）；`0`：使用主频周期计数。 |
| 7 | `sel` | 延时数选择：`1`：`rs1 + rs2`；`0`：`rs1 + imm`。 |
| [6:0] | `func7` | **固定值 0001011b**。 |

原文脚注（第 58 页）：「注：以 sp 寄存器为基地址的读写指令执行不受匹配 load/store 指令（match=001/010/011）限制。」
EN: load/store using `sp` as base are exempt from the match=001/010/011 stall.

> **[推断]** 手册把 `[6:0]` 一栏标为 `func7`，但 RISC-V 中 `[6:0]` 是 **opcode** 字段（`0001011b` = `custom-0`），`func7` 通常指 `[31:25]`。这是手册的字段命名错误，编码值本身（`0001011b` 落在 custom-0 空间）自洽。同理 `[11:9] match` 与 `[8] div`、`[7] sel` 占据了标准 R/I 型的 `rd` 位置——该指令不写通用寄存器。写内联汇编时以位值为准，不要按字段名推导。

**mcpy 指令位编码**（CH32V407RM V1.1 `63625af9027af6ab` 第 58 页）：

原文：「**9.2.1.4 自定义 mcpy 指令** — mcpy 指令用于替代 memcpy 函数，实现连续的内存搬运功能，指令寄存器中保存起始地址，目标地址，结束地址的地址信息，所有地址均无对齐要求。」
EN: replaces `memcpy`; source/dest/end addresses in registers; **no alignment requirement on any address**.

| 位 | 名称 | 描述（原文） |
|---|---|---|
| [31:27] | `rs3` | 结束地址寄存器编码。 |
| [26:25] | `Reserved` | 固定值 `00b`。 |
| [24:20] | `rs2` | 起始地址寄存器编码。 |
| [19:15] | `rs1` | 目标地址寄存器编码。 |
| [14:12] | `func3` | 固定值 `111b`。 |
| [11:7] | `func5` | 固定值 `00000b`。 |
| [6:0] | `func7` | 固定值 `0001111b`。 |

> **[推断]** `[6:0]=0001111b` 是 RISC-V 的 **MISC-MEM** opcode（`fence` 所在空间），不是 custom 空间；`func3=111b` 在标准 MISC-MEM 中未分配，WCH 借此扩展。字段名 `func5` 实际占 `rd` 位置。同上，以位值为准。

> **[手册][SDK][实测] 地址角色冲突**：汇编文本的第一、二、三个操作数分别进入 rs1、rs2、rs3。四份 `core_riscv.h` 的 `ASM_MCPY(DA,SA,EA)` 均发射 `mcpy EA,SA,DA`，CH587 ROM 也先计算 `EA=SA+len` 再发射该顺序；因此随包约定是 rs1=EA、rs2=SA、rs3=DA。它与上表手册原文的 rs1=目标、rs3=结束相反；固定编码位一致，但角色文字疑似互换。按手册角色列交换 rs1/rs3 会装反源结束和目的地址，存在数据破坏风险；硅片行为仍需测试。

**未给出的信息**：两条指令手册均**未给出助记符**（汇编写法）与 GCC 内建函数名，也未说明触发异常的条件。要在代码里使用，需要 `.insn` 手工编码或查 MounRiver 工具链。

### 1.2 CH32H417（青稞 V5F）——WCH-X 扩展指令集，仅提名不给编码

出处：CH32H417RM V1.7 (`b57ebb0c0ae2cd77`) 第 44 页（第 4 章 中央处理器（CPU），页脚印刷页 40）。

原文：「CH32H417 系列集成双内核结构，RISC-V5F 与 RISC-V3F 双内核均支持 32 位 I、C、M、A、B、F 和扩展指令集。……此外 **RISC-V5 实现了 WCH-X 扩展指令集**，在代码密度，计算性能上均有所提高。」
EN: V5F implements the "WCH-X" extension improving code density and compute performance.

同页两个内核的特性清单里各有一条「**自定义扩展指令**」与「硬件压栈」。
**手册未给出 WCH-X 的任何助记符、语义或位编码。**

### 1.3 向量指令集（CH32V407 独有）

出处：CH32V407RM V1.1 (`63625af9027af6ab`) 第 57 页。

原文：「青稞 V3V 处理器支持 RISC-V V1.0 指令集中向量整型和定点运算指令，不支持向量浮点指令，向量操作使用 32 组 64bit 宽的向量寄存器，向量指令最大 EEW 为 64bit，配置符合向量嵌入式扩展 **Zve64x** 扩展集」；「**9.2.1.2 RISC-V zvbb** — zvbb 是向量指令集的扩展位基础操作子集。完全支持 Zve64x 扩展集。」
原文注：「1、zve64x 扩展指令集均为 RVV1.0 手册中定义指令，具体指令功能参考《RISC-V "V" vector Extension 1.0》；2、访存指令全部支持 eew=64，iew=64 操作，但标量地址位宽 XLEN=32 位，**不支持 64 位寻址**，符合手册 Zve64x 规范。」

这是标准扩展，不是自定义指令；但其配套的 4 个控制 CSR 是自定义的（见 §2.3）。

### 1.4 WFE —— 被手册明写为「自定义指令」

出处（两处，字面相同）：
- CH32V407RM V1.1 (`63625af9027af6ab`) 第 101 页，PFIC_SCTLR 寄存器 bit3 `WFITOWFE` 说明；
- CH32X315RM V1.1 (`b6a752f9e9bdbb1d`) 第 71 页，同一寄存器同一位。

原文：「WFI 命令执行为 WFE，**WFE 是自定义指令**，本寄存器置 1 后，内核执行 WFI 指令后进入低功耗状态，等待外部事件发生后可唤醒内核。1：WFI 指令后等待事件唤醒内核；0：WFI 指令后等待中断唤醒内核。」
EN: WFE is a WCH-custom instruction; setting `WFITOWFE` makes the core treat subsequent `WFI` as `WFE`.

其余手册（CH32V003RM V1.9 第 47 页、CH32V00XRM V1.5 第 58 页、CH32X035RM V1.9 第 50 页、CH641RM V1.4 第 42 页、CH32FV2x_V3xRM V2.5 第 109 页等）同一位只写「将 WFI 指令当成是 WFE 执行」，**不带「WFE 是自定义指令」这句话**。

> 实践含义：目标代码里不要直接写 `wfe`——RISC-V 标准没有这条指令，应通过 `PFIC_SCTLR.WFITOWFE` + `wfi` 达到同样效果。

### 1.5 `fence.i` 的强制使用场景（所有 RISC-V 手册通用）

原文（逐字相同，见于多份手册）：「注：在使用 PFIC_IENRx 寄存器屏蔽任意中断或使用 CSR 寄存器屏蔽全局中断时，**追加一条"fence.i"指令**，用于内核控制状态和中断使能状态之间的同步。」
EN: after masking interrupts via `PFIC_IENRx` or a CSR, you must append a `fence.i` to synchronize core control state with the interrupt-enable state.

出处：CH32FV2x_V3xRM V2.5 (`6bdc58b159a95c40`) 第 95 页 · CH32L103RM V2.2 (`27a1b969cb2cb99d`) 第 57 页 · CH32M030RM V1.2 (`109a7bb0ab9a0b70`) 第 32 页 · CH32V003RM V1.9 (`7a6bf439ecd68e0b`) 第 37 页。

配套的 CSR 位：`int_fence`（CPU_RUN_CTLR bit6，见 §2.2）——「1：执行 fence 指令时清除中断请求；0：执行 fence 指令时不清除中断请求」。

### 1.6 内存序与 fence（仅 CH32H417 V5F 乱序核）

出处：CH32H417RM V1.7 (`b57ebb0c0ae2cd77`) 第 44–45 页。

原文（第 45 页）：「表 4-3 A1/A2 访问的内存类型及其指令类型」给出 store/load × device/normal 的 4×4 重排序矩阵（`order` / `re-order`），注：「对于所有乱序访问，**均可通过插入 fence 指令强制顺序**」。这是本批手册中唯一定义内存模型的地方；V3F 与其余单核不涉及。

### 1.7 MISA 中的 X 位（所有 RISC-V 核）

各手册 MISA `bit23 X = 1`，描述统一为「本内核支持执行自定义指令集」。出处示例：CH32H417RM V1.7 (`b57ebb0c0ae2cd77`) 第 48 页 · CH32V407RM V1.1 (`63625af9027af6ab`) 第 64 页 · CH32X315RM V1.1 (`b6a752f9e9bdbb1d`) 第 75 页。
即：硬件自报有自定义指令；在本轮 12 份芯片参考手册中只有 CH32V407RM 给了 delay/mcpy 编码。另一路 core manual 证据是 QingKeV3 V1.5 p55 的 delay 位表，不能把“芯片参考手册范围唯一”写成所有手册唯一。

---

## 2. 自定义 CSR

各手册对本节的表述统一为：「CH32xxx 芯片除了 RISC-V 特权架构文档中定义的标准寄存器外，还增加了一些**厂商自定义寄存器**，需要使用 csr 指令进行访问」，并注明「标注为"MRW，MRO，MRW1"属性的需要系统在机器模式下才能访问」。

**CSR 章节的覆盖深度差异极大**（这本身就是最重要的跨手册差异，详见 §7.1）：

| 手册（版本） | CSR 章节位置 | 列出的 CSR 数 | 是否含 MVENDORID/MARCHID/MISA |
|---|---|---|---|
| CH32V003RM V1.9 | 6.5.3，第 47–48 页 | 2（INTSYSCR、MTVEC） | 否 |
| CH32V00XRM V1.5 | 6.5.3，第 58 页 | 2 | 否 |
| CH641RM V1.4 | 5.5.3，第 42–43 页 | 2 | 否 |
| CH32X035RM V1.9 | 7.5.3–7.5.4，第 50–53 页 | 2 + 5 (PMP) | 否 |
| CH32L103RM V2.2 | 9.5.3–9.5.4，第 72–75 页 | 2 + 5 (PMP) | 否 |
| CH32FV2x_V3xRM V2.5 | 9.5.3–9.5.4，第 109–113 页 | 2 + 5 (PMP) | 否 |
| CH32M030RM V1.2 | 5.5.4，第 44–47 页 | **5**（含 GINTENR/CORECFGR/INESTCR） | 否 |
| CH32V205RM V1.2 | 9.5.4，第 75–77 页 | **5** | 否 |
| CH32X315RM V1.1 | 9.5.4，第 73–84 页 | **24** | **是** |
| CH32V407RM V1.1 | 9.2.2–9.2.4，第 58–73 页 | **10 向量 + 25 通用 + 5 自定义** | **是** |
| CH32H417RM V1.7 | 4.2.1–4.3，第 46–68 页 | **34 通用 + 4 (V3F) + 16 (V5F) + 5 (PMP)** | **是** |

### 2.1 CSR 0x804 —— 同址异义，最容易踩的坑

**同一地址 0x804 在当前不同芯片手册中是两个不同的寄存器**。下列 core 名称是具体手册样本的标签，不构成对整个内核家族的外推：

**(a) `INTSYSCR` 中断系统控制寄存器**（当前芯片 RM：V003、V00X、CH641、X035、L103、FV2x/V3x、M030、V205；四本 QingKe core manual 也使用此名）

- CH32V003RM V1.9 (`7a6bf439ecd68e0b`) 第 47–48 页：仅 2 位。`bit1 INESTEN` 中断嵌套使能、`bit0 HWSTKEN` 硬件压栈使能，`[31:2] Reserved MRO`，复位值 0。
- CH641RM V1.4 (`af83c6fca780cfed`) 第 42 页、CH32V00XRM V1.5 (`7d216d69fd04d990`) 第 58 页：同上 2 位布局。
- CH32L103RM V2.2 (`27a1b969cb2cb99d`) 第 72 页：多出 `bit5 GIHWSTKNEN`。
- CH32FV2x_V3xRM V2.5 (`6bdc58b159a95c40`) 第 109–110 页（V4 核，最全）：
  - `[15:8] PMTSTA` MRO 抢占位状态指示，复位 `0x00`。取值：`0x00` 无抢占位不嵌套；`0x80` 最高位为抢占位、2 级嵌套；`0xC0` 高 2 位、4 级嵌套；`0xE0` 高 3 位、8 级嵌套。注：**此位仅适用于青稞 V4F 内核：CH32V30x_D8、CH32V30x_D8C、CH32V31x_D8C**。
  - `bit5 GIHWSTKNEN` MRW1 全局中断和硬件压栈关闭使能。原文注：「该位常使用于实时操作系统中，中断切换上下文时，置位该位，可关闭全局中断和硬件压栈出栈，当上下文切换完成，执行完中断返回后，**硬件自动清除该位**」。
  - `bit4 HWSTKOVEN` MRW 硬件压栈溢出后中断使能。注：「此位仅适用于 CH32V30x_D8、CH32V30x_D8C、CH32V31x_D8C，其**硬件压栈深度为 3 级**，当配置嵌套等级大于 3 级，若该位设置 1，需要将低优先级的三级中断配置为硬件压栈，高优先级配置为软件压栈。」
  - `[3:2] PMTCFG[1:0]` MRW 中断嵌套深度配置：`00` 无嵌套抢占位 0；`01` 2 级嵌套抢占位 1；`10` 4 级嵌套抢占位 2；`11` 8 级嵌套抢占位 3。注：仅适用青稞 V4F。
  - `bit1 INESTEN`、`bit0 HWSTKEN`。
- CH32M030RM V1.2 (`109a7bb0ab9a0b70`) 第 45 页、CH32V205RM V1.2 (`b1ed9ef040455a1f`) 第 76 页（V3B 核）：复位值 **`0x0000E002`**（M030）/ **`0x00000004`**（V205，见表 9-6）。`[31:6] Reserved URO 保留，复位值 0x380`；`bit5 GIHWSTKNEN URW1`；`bit1 INESTEN` **URO 固定值 1**，注「实际嵌套级数由 CSR 0xBC1 中 NEST_LVL 控制」；`bit0 HWSTKEN URW`。
  → 注意 V3B 上 `INESTEN` **是只读常 1**，不能靠写它关嵌套。

**(b) `HW_POPDM_CTLR` 硬件压栈控制寄存器**（当前芯片 RM：X315、V407、H417）

出处：CH32H417RM V1.7 (`b57ebb0c0ae2cd77`) 第 52–53 页 · CH32V407RM V1.1 (`63625af9027af6ab`) 第 67 页 · CH32X315RM V1.1 (`b6a752f9e9bdbb1d`) 第 83–84 页。复位值 `0x00000004`。

| 位 | 名称 | 描述（原文） |
|---|---|---|
| 31 | `lock` RW | 用户模式锁定标志，锁定后用户模式不可改写本组寄存器配置：1 锁定，仅机器模式可配置；0 非锁定。 |
| [30:6] | Reserved RO | 保留。 |
| 5 | `hw_pop_off` RW | 一次性硬件出栈关闭，**退出中断后自动复位**：1 下一次退出中断时屏蔽硬件出栈；0 不屏蔽。 |
| 4 | Reserved RO | 保留。 |
| [3:2] | `preempt[1:0]` RW | 抢占优先级位宽：`00` 位宽 0，任何优先级中断无法嵌套；`01` 位宽 1（优先级寄存器 [7] 位）；`10` 位宽 2（[7:6]）；`11` 位宽 3（[7:5]）。复位 `0x1`。 |
| 1 | `nest_en` RW | 中断嵌套使能。 |
| 0 | `hw_stk_en` RW | 硬件堆栈保护使能。 |

> **同址异义的实际后果**：一段在 CH32V003 上写 `csrw 0x804, 3`（开嵌套+硬件压栈）的代码，搬到 CH32X315/CH32V407/CH32H417 上会被解释为 `nest_en=1, hw_stk_en=1`——语义碰巧接近；但写 `0x804` 的 `[3:2]` 在前者是 Reserved、在后者是抢占位宽配置，行为完全不同。

### 2.2 CSR 0xBC0 / 0xBC1 / 0xBC8 —— 当前文档中名称/字段不完全对应

**0xBC0**：M030/V205 两份 RM 叫 `CORECFGR`（微处理器配置寄存器）；X315/V407/H417 三份 RM 叫 `CPU_RUN_CTLR`（处理器运行控制寄存器）。这些样本与各自标注的 core 类型相关，但当前证据不足以把命名规则无条件推广到整个 core family。

- `CORECFGR`，CH32M030RM V1.2 (`109a7bb0ab9a0b70`) 第 45–46 页，复位 `0x00000001`：
  `bit7 CSTA_FAULT_IE` 内核状态错误中断使能（1 发生状态错误时产生 NMI 中断）；`bit6 Reserved MRO 保留，保持 0`；`bit5 IE_REMAP_EN` MIE 寄存器映射使能（1：CSR 0x800 的 bit3/bit7 分别映射为 MSTATUS 的 MIE/MPIE；0：CSR 0x800 只读）；`[1:0] FETCH_MODE[1:0]` 取指模式，复位 `0x1`。
  CH32V205RM V1.2 (`b1ed9ef040455a1f`) 第 76–77 页同名同址，复位 `0x00000001`。
- `CPU_RUN_CTLR`，复位值分三种：
  - CH32V407RM V1.1 (`63625af9027af6ab`) 第 70–71 页：**`0x00000000`**，字段只有 `bit7 nmi_ie` / `bit6 int_fence` / `bit5 non_usta` / `[1:0] pipe_acc`。
  - CH32X315RM V1.1 (`b6a752f9e9bdbb1d`) 第 74、80 页：**`0x12370000`**。
  - CH32H417RM V1.7 (`b57ebb0c0ae2cd77`) 第 54–55 页（V3F）：**`0x12370000`**；第 57、60 页（V5F）：**`0x12370300`**。
    V3F/V5F 版多出浮点分频字段：`[31:28] fadd_clkdiv` 复位 `0x1`、`[27:24] fmul_clkdiv` 复位 `0x2`、`[23:20] fmac_clkdiv` 复位 `0x3`、`[19:16] fdiv_clkdiv` 复位 `0x7`。
    V5F 另有 `bit15 nlp_en` 下一行分支预测使能、`bit14 ghr_en` 全局历史寄存器使能、`bit10 lsu_dual` 访存指令并行发射使能。

  **浮点分频的硬约束**（CH32H417RM V1.7 `b57ebb0c0ae2cd77` 第 55 页 V3F / 第 60 页 V5F）：

  | 内核 | fadd_freq(max) | fmul_freq(max) | fmac_freq(max) | fdiv_freq(max) |
  |---|---|---|---|---|
  | V3F | 80MHz | 53MHz | 40MHz | 20MHz |
  | V5F | 128MHz | 96MHz | 76MHz | 38MHz |

  原文：「浮点算数指令为多周期指令……根据处理器的运行频率，用户需配置浮点运算分频系数，使分频后的频率不高于上表所示的最大运行频率。`fxxx—freq(max) ≥ 内核主频 / fxxx—clkdiv`」。
  EN: FP arithmetic is multi-cycle; software **must** program the divider so the divided clock stays under the per-op max.
  → 这是一条**软件必须主动满足的时序约束**，复位值只在默认主频下安全。

**0xBC1**：M030/V205 两份 RM 叫 `INESTCR`（CH32M030RM V1.2 第 46–47 页、CH32V205RM V1.2 第 77 页），字段 `NEST_OV` / `NEST_STA[3:0]` / `NEST_LVL[1:0]`；X315/V407/H417 三份 RM 叫 `INEST_CTLR`，字段 `nest_ovr` / `nest_sta` / `nest_max`。这里同样只陈述当前文档样本。

嵌套深度编码在 V5F 上被拓宽（CH32H417RM V1.7 `b57ebb0c0ae2cd77` 第 61 页）：
`nest_sta` 由 [11:8] 4 位（V3B/V3F）变成 **[15:8] 8 位**，取值 `0x00` 无中断 … `0xFF` 八级嵌套；`nest_max` 由 [1:0] 2 位变成 **[2:0] 3 位**，`000` 禁止嵌套 … `111` 允许八级嵌套。V5F 另有 `bit31 lsu_nmi_sta`（访存单元产生不可屏蔽中断标记，通常为写总线返回错误，写 1 复位）。

**探测芯片最大嵌套级数的官方手法**（V3B / V3F）——原文注：「（2）写入 11b 时，读该寄存器，可获得芯片的最高嵌套等级。」对 `nest_max`/`NEST_LVL` 写 `10b` 或 `11b` 时寄存器被置为 `01b`。出处：CH32M030RM V1.2 (`109a7bb0ab9a0b70`) 第 47 页 · CH32V407RM V1.1 (`63625af9027af6ab`) 第 71 页 · CH32H417RM V1.7 (`b57ebb0c0ae2cd77`) 第 56 页。

**0xBC8 `MIE` 机器中断寄存器**（注意：**不是** RISC-V 标准的 `mie` CSR 0x304）
原文：「机器中断寄存器，保存多级中断嵌套中每级中断的 mie 信息：`status.mie=nest_mie[0]`；`status.mpie=nest_mie[1]`。」
位宽随嵌套级数变化：V3F/V3V 为 `[4:0] nest_mie[4:0]`（CH32V407RM V1.1 第 72 页、CH32H417RM V1.7 第 56 页）；V5F 为 **`[8:0] nest_mie`**（CH32H417RM V1.7 第 64–65 页）。

### 2.3 CH32V407 专属：向量 CSR（4 个自定义 + 6 个标准）

出处：CH32V407RM V1.1 (`63625af9027af6ab`) 第 58–62 页，表 9-1。

| 名称 | CSR 地址 | 描述 | 复位值 |
|---|---|---|---|
| VXSAT | 0x009 | 定点饱和状态寄存器 | 0x00000000 |
| VXRM | 0x00A | 定点舍入寄存器 | 0x00000000 |
| VCSR | 0x00F | 向量控制和状态寄存器 | 0x00000000 |
| VL | 0xC20 | 元素体长度寄存器 | 0x00000000 |
| VTYPE | 0xC21 | 向量数据类型寄存器 | 0x00000000 |
| VLENB | 0xC22 | 向量寄存器字节长度寄存器 | 0x00000000 |
| **VCONTROL** | **0x805** | **自定义**向量控制寄存器 | **0x00000X0C** |
| **VPPADDR** | **0x806** | **自定义**向量寄存器压栈基地址寄存器 | 0x00000000 |
| **VCAUSE** | **0x808** | **自定义**向量异常源寄存器 | 0x00000000 |
| **VTVAL** | **0x809** | **自定义**向量异常自陷信息寄存器 | 0x00000000 |

`VCONTROL`(0x805) 关键字段（第 60–61 页）：
- `bit31 VEC_ILL` URW1C 向量指令异常标记，「当 NMI_EN 寄存器被使能时，向量异常将进入 NMI 异常」。
- `[23:22] NEST_INT_PTR` URO 中断嵌套深度；`[21:20] VEC_INT_PTR` URW 向量流水线中断嵌套深度，原文：「当中断服务函数中未使用向量指令时，向量流水中断嵌套深度保持前值」。
- `[19:16] VEC_REG_STATE` URW 向量寄存器状态，共 4 位对应最大四层深度，1 表示脏。
- `bit9 VEC_ILL_INFO` URW 复位值 **1**，置 1 后 VCAUSE 和 VTVAL 保存向量异常信息。
- **`bit8 Reserved URO 保留，不可写 0`**，复位值 `x`。← 典型「禁止修改」位，见 §6。
- `bit3 LSU_WAX_ON` 强制写顺序使能，复位 **1**；`bit2 LSU_RAW_ON` 强制读顺序使能，复位 **1**。
- `bit1 VEC_HW_PP_ABI` 向量寄存器硬件堆栈保护 ABI：「1：调用变体 ABI，硬件堆栈保护 V0，V8-V23 寄存器；0：调用标准 ABI，硬件堆栈保护 V0-V31 寄存器」。注：参考《RISC-V ABIS SPECIFICATION V1.1》。
- `bit0 VEC_HW_PP_EN` 向量寄存器硬件堆栈保护使能。

`VPPADDR`(0x806)：「向量寄存器堆栈保护内存地址寄存器……**低 10bit 固定为 0，内存中 1KB 对齐**」，复位值 `0x20000000`。

`VCAUSE`(0x808) / `VTVAL`(0x809) 共同的注：「**调试模式将导致异常原因信息丢失，无法在调试模式中使用**」。← 调试期不可复现的坑，见 §6。

**延时指令控制寄存器 `U_NONS_DLY_0`，CSR 0x8C0**（CH32V407RM V1.1 `63625af9027af6ab` 第 73 页，复位 `0xXXXX0XXX`）——与 §1.1 的 dly 指令配套：

| 位 | 名称 | 描述（原文） |
|---|---|---|
| [31:24] | `dly_mask` URW | dly 指令 match=111 时匹配的指令参数掩膜。 |
| [23:16] | `dly_data` URW | dly 指令 match=111 时匹配的 `{func, opcode}`。 |
| 15 | `CPU_dly_busy_sta` URO | 内核处于延时状态标志。 |
| 14 | `dly_tout` RW1Z | 超时信息，在延时范围内无匹配的指令请求。 |
| 13 | `dly_ie` URW | 延时中断请求，使能后如果产生超时情况，即产生一个软件中断请求。 |
| 12 | `dly_priv` URW | 1：机器模式和用户模式均允许匹配；0：在用户模式下执行的 delay 操作不匹配机器模式中的指令。 |
| [11:10] | Reserved URO | 保留。 |
| [9:0] | `dly_freq` URW | 延时计数分频系数配置，**若配置为主频时钟频率，可实现 us 为单位延时**。 |

### 2.4 CH32H417 V5F 专属：缓存 / TCM / 内存信息 CSR

出处：CH32H417RM V1.7 (`b57ebb0c0ae2cd77`) 第 57–66 页，表 4-6「RISC-V5F 内核自定义寄存器列表」。

| 名称 | CSR 地址 | 描述 | 复位值 |
|---|---|---|---|
| MCOUNT_INHIBIT | 0x320 | 计数器屏蔽寄存器 | 0x00000000 |
| DCSR | 0x7B0 | 调试控制和状态寄存器 | 0x40000000 |
| MCYCLE | 0xB00 | 机器周期计数器寄存器 | 0x00000000 |
| MINSTRET | 0xB02 | 机器指令计数器寄存器 | 0x00000000 |
| UCYCLE | 0xC00 | 用户模式周期计数器寄存器 | 0x00000000 |
| UINSTRET | 0xC02 | 用户模式指令计数器寄存器 | 0x00000000 |
| CPU_RUN_CTLR | 0xBC0 | 处理器运行控制寄存器 | 0x12370300 |
| INEST_CTLR | 0xBC1 | 中断嵌套控制寄存器 | 0x00000000 |
| **CACHE_STRTG_CTLR** | **0xBC2** | 缓存策略控制寄存器 | **0x0F000003** |
| **CACHE_PMP_OVR** | **0xBC3** | 缓存策略 PMP 覆盖寄存器 | 0x00000000 |
| **HW_POPDM_ADDR** | **0xBC4** | 硬件压栈地址寄存器 | **0x20060000** |
| **MEMARY_CFGR** | **0xBC5** | 存储器配置寄存器 | **0x600F0FFF** |
| **TCM_RRDUTY_CFGR** | **0xBC6** | TCM 优先访问时长配置寄存器 | 0x00000000 |
| MIE | 0xBC8 | 机器中断寄存器 | 0x00000000 |
| **OPCACHE_CTLR** | **0xBD0** | 缓存操作寄存器 | 0x00000000 |
| **MEMINFO** | **0xFC0** | 内存信息寄存器 | **0x12220030** |

要点：

- **`CACHE_STRTG_CTLR`(0xBC2)** 第 61–62 页：`bit27 ic_mem1_strtg` 对 `0x80000000-0x9fffffff` 区域指令缓存使能（复位 1）；`bit26 ic_mem0_strtg` 对 `0x60000000-0x7fffffff`（复位 1）；`bit25 ic_sram_strtg` 对 `0x20000000-0x3fffffff`（复位 1）；`bit24 ic_code_strtg` 对 `0x00000000-0x1fffffff`（复位 1）；`bit1 ic_disable`「指令缓存失能标志位，**为 0 开启指令缓存功能**」复位 1；`bit0 Reserved RO` 复位 **1**。
  → 复位后 `ic_disable=1`，**I-Cache 默认关闭**，需软件清零开启。
- **`CACHE_PMP_OVR`(0xBC3)** 第 62 页，注：「当指令或数据地址与受 PMP 通道控制的地址匹配时，**不执行缓存策略控制寄存器（0xBC2）中的策略**，执行本寄存器中与 PMP 通道匹配的策略。」
- **`HW_POPDM_ADDR`(0xBC4)** 第 62 页：`[31:20] MRO` DTCM 区域的固定首地址 `0x200`；`[19:9] hw_stk_vector` MRW DTCM 区域块地址，**512bit 对齐**，复位 `0x600`；`[8:0] MRO` 固定为 0。注：「通常指向 DTCM 区域的底部」。
- **`MEMARY_CFGR`(0xBC5)** 第 62–64 页：`[31:20] MEM0_addr_hi[11:0]` 分支预测器地址匹配寄存器，复位 `0x600`；**原文注：「请勿配置为内部存储器的高位地址（0x000，0x200，0x201）」**。另含 `dtcm_rr_mode[1:0]` / `itcm_rr_mode[1:0]`（复位均 `0x3` 强制轮询优先级）与 6 组 2 位的 DMA/C0_LSU/C0_IFU 对 ITCM/DTCM 的读写权限位（复位均 `0x3`）。
- **`OPCACHE_CTLR`(0xBD0)** 第 65 页：`[31:5] Vaddr[27:0]` WO 操作地址或索引信息；`bit2 Idx_mode` WO；`[1:0] Opcode[1:0]` WO：**`00`：Icache invalidate；其他：无效**。这是唯一的缓存维护接口（全 WO）。
- **`MEMINFO`(0xFC0)** 第 65–66 页，MRO 只读的容量自述寄存器，复位 `0x12220030`：
  `[29:26] DTCM datasize` 复位 `0100b` → 表中示例 `64KB*2 = 256KB`；`[25:24] DTCM LineSize` 复位 `10b`（32 字节）；`[21:18] ITCM datasize` 复位 `0010b` → `64KB*2 = 128KB`；`[17:16] ITCM LineSize` 复位 `10b`；`[6:5] Icache_way` 复位 `01b`（2-way）；`[4:2] Icache_datasize` 复位 `100b`（32KB）；`[1:0] Icache linesize` 复位 `0`。
  编码表：Icache_way `00`=1-way / `01`=2-way / `10`=4-way / `11`=8-way；Icache_datasize `000` NONE / `001` 4KB / `010` 8KB / `011` 16KB / `100` 32KB / `101` 64KB / `110` 128KB / `111` 256KB；linesize `00`=8 / `01`=16 / `10`=32 / `11`=64 byte。
  → **运行期探测缓存/TCM 规格的正规途径**，属于第 3 类（器件标识）性质但位于 CSR 空间。

### 2.5 CH32H417 V3F 专属自定义 CSR

出处：CH32H417RM V1.7 (`b57ebb0c0ae2cd77`) 第 54 页表 4-5：`CPU_RUN_CTLR` 0xBC0（0x12370000）、`INEST_CTLR` 0xBC1、`MIE` 0xBC8、`DCSR` 0x7B0（0x40000000）。仅 4 个，无缓存/TCM 组。

### 2.6 CSR 0x800 —— 三个名字，一套机制

| 名称 | 手册 | 出处 |
|---|---|---|
| `GINTENR` 用户模式全局中断使能寄存器 | CH32M030RM V1.2 / CH32V205RM V1.2 | `109a7bb0ab9a0b70` 第 45 页 / `b1ed9ef040455a1f` 第 75 页 |
| `UACCES_MSTATUS` 用户访问机器状态寄存器 | CH32V407RM V1.1 / CH32X315RM V1.1 / CH32H417RM V1.7 | `63625af9027af6ab` 第 66 页 / `b6a752f9e9bdbb1d` 第 82 页 / `b57ebb0c0ae2cd77` 第 51–52 页 |

机制相同：默认为只读、返回 MSTATUS 的值；只有当 0xBC0 的 bit5（`IE_REMAP_EN` / `non_usta`）置 1 后，`bit3`/`bit7` 才分别映射为 MSTATUS 的 `MIE`/`MPIE`，供用户模式改写。
CH32M030RM 原文（第 45 页）：「全局中断使能寄存器 gintenr 是 mstatus 中 MIE 和 MPIE 的映射，用户模式下可以通过操作 gintenr，用于 MIE 和 MPIE 的置位和清零。」

### 2.7 DBGMCU —— 位于 CSR 空间的外设调试寄存器

**所有 12 份 RISC-V 手册中，调试 MCU 配置寄存器都在 CSR 0x7C0，而非内存映射。**

| 手册（版本） | 寄存器名 | CSR 地址 | 出处页 |
|---|---|---|---|
| CH32V003RM V1.9 | DBGMCU_CR | 0x7C0 | `7a6bf439ecd68e0b` 第 193 页 |
| CH32V00XRM V1.5 | DBGMCU_CR | 0x7C0 | `7d216d69fd04d990` 第 228 页 |
| CH641RM V1.4 | DBGMCU_CTRL | 0x7C0 | `af83c6fca780cfed` 第 174 页 |
| CH32X035RM V1.9 | DBGMCU_CR | 0x7C0 | `c7e301eac4790ca1` 第 245 页 |
| CH32L103RM V2.2 | DBGMCU_CR | 0x7C0 | `27a1b969cb2cb99d` 第 310 页 |
| CH32V205RM V1.2 | DBGMCU_CR | 0x7C0 | `b1ed9ef040455a1f` 第 383 页 |
| CH32FV2x_V3xRM V2.5 | DBGMCU_CR | 0x7C0（另有 ARM 版内存映射，第 550 页） | `6bdc58b159a95c40` 第 548 页 |
| CH32X315RM V1.1 | DBGMCU_CR | 0x7C0 | `b6a752f9e9bdbb1d` 第 290 页 |
| CH32V407RM V1.1 | DBGMCU_CR | 0x7C0 | `63625af9027af6ab` 第 535 页 |
| CH32H417RM V1.7 | R32_DBGMCU_CR | 0x7C0 | `b57ebb0c0ae2cd77` 第 862 页 |
| **CH32M030RM V1.2** | **DBGMCU_CR1 / DBGMCU_CR2** | **0x7C0 / 0x7C4** | `109a7bb0ab9a0b70` 第 250 页 |
| **CH32xRM V2.0** | **DBGMCU_CR1 / DBGMCU_CR2** | （RISC-V 支路） | `b4ade26ba00e0f03` 第 284–285 页 |

CH32X315RM/CH32V407RM/CH32H417RM 的 CPU 章节另把它列作 `DBGMCU_0`「调试寄存器 0」，字段简化为 `[31:8] dbg_mode_stop` MRW +`[7:0]` 保留（CH32H417RM V1.7 `b57ebb0c0ae2cd77` 第 50–51 页）。同一地址在同一份手册的两个章节里字段划分不同——CPU 章节按「注册模块」抽象描述，DBG 章节按具体外设逐位列出。

### 2.7.1 CH32H417 双核 CSR 身份值

出处：CH32H417RM V1.7 (`b57ebb0c0ae2cd77`) 第 46–47 页。

| CSR | 地址 | V3F（内核 0） | V5F（内核 1） |
|---|---|---|---|
| MVENDORID | 0xF11 | 0x00000000 | 0x00000000 |
| MARCHID | 0xF12 | **0xDC68D86D** | **0xDC68D8AE** |
| MIMPID | 0xF13 | **0xDC688002** | **0xDC688001** |
| MHARTID | 0xF14 | **0** | **1** |

其余手册的对应值：CH32V407RM V1.1 (`63625af9027af6ab`) 第 62–63 页 MARCHID **0xDC68D876**、MIMPID **0xDC688003**；CH32X315RM V1.1 (`b6a752f9e9bdbb1d`) 第 74 页 MARCHID **0xDC68D86D**、MIMPID **0xDC688002**、MHARTID 0x00000000。
→ CH32X315 的 (MARCHID, MIMPID) 与 CH32H417 的 V3F 内核**完全相同**，与两份手册首页都写「青稞 V3F」一致。**这是运行期区分内核代际最可靠的手段**（MVENDORID 全为 0，不可用）。

---

## 3. 系统信息 / 器件标识类寄存器

### 3.1 电子签名（ESIG）—— 12 份手册全部有，地址有一处例外

寄存器组固定为 4 个。以 CH32V003RM V1.9 (`7a6bf439ecd68e0b`) 第 177–178 页（第 15 章，页脚印刷页 175–176）为范本：

| 名称 | 访问地址 | 描述 | 复位值 |
|---|---|---|---|
| R16_ESIG_FLACAP | **0x1FFFF7E0** | 闪存容量寄存器 | 0xXXXX |
| R32_ESIG_UNIID1 | **0x1FFFF7E8** | UID 寄存器 1 | 0xXXXXXXXX |
| R32_ESIG_UNIID2 | **0x1FFFF7EC** | UID 寄存器 2 | 0xXXXXXXXX |
| R32_ESIG_UNIID3 | **0x1FFFF7F0** | UID 寄存器 3 | 0xXXXXXXXX |

位域（各手册逐字一致）：
- `ESIG_FLACAP`：**16 位**寄存器。`[15:0] F_SIZE[15:0]` **RO** —「以 Kbyte 为单位的闪存容量。例：`0x0080` = 128K 字节。」复位值 `X`。
- `ESIG_UNIID1`：`[31:0] U_ID[31:0]` RO —「UID 的 0-31 位。」
- `ESIG_UNIID2`：`[31:0] U_ID[63:32]` RO —「UID 的 32-63 位。」
- `ESIG_UNIID3`：`[31:0] U_ID[95:64]` RO —「UID 的 64-95 位。」

功能描述（各手册一致）：「唯一身份标识：**96 位**二进制码，对任意一个微控制器都是唯一的，用户只能读访问不能修改。……以上内容用户都可以按 **8/16/32 位**进行读访问。」「它由厂家在出厂时烧录到存储器模块的系统存储区域，可以通过 SWD（SDI）或者应用代码读取。」

各手册章节位置与出处：

| 手册（版本，sha256 前16） | 章节 | ESIG 基址 | 页 |
|---|---|---|---|
| CH32V003RM V1.9 `7a6bf439ecd68e0b` | 第 15 章 | 0x1FFFF7E0 | 177–178 |
| CH641RM V1.4 `af83c6fca780cfed` | 第 13 章 | 0x1FFFF7E0 | 146–147 |
| CH32V00XRM V1.5 `7d216d69fd04d990` | 第 19 章 | 0x1FFFF7E0 | 225–226 |
| CH32X035RM V1.9 `c7e301eac4790ca1` | 第 19 章 | 0x1FFFF7E0 | 223–224 |
| CH32X315RM V1.1 `b6a752f9e9bdbb1d` | 第 22 章 | 0x1FFFF7E0 | 292–293 |
| CH32xRM V2.0 `b4ade26ba00e0f03` | 第 23 章 | 0x1FFFF7E0 | 268–269 |
| CH32L103RM V2.2 `27a1b969cb2cb99d` | 第 27 章 | 0x1FFFF7E0 | 312–313 |
| CH32V205RM V1.2 `b1ed9ef040455a1f` | 第 29 章 | 0x1FFFF7E0 | 385–386 |
| CH32FV2x_V3xRM V2.5 `6bdc58b159a95c40` | 第 31 章 | 0x1FFFF7E0 | 530–531 |
| CH32V407RM V1.1 `63625af9027af6ab` | 第 31 章 | 0x1FFFF7E0 | 511–512 |
| CH32H417RM V1.7 `b57ebb0c0ae2cd77` | 第 39 章 | 0x1FFFF7E0 | 719–720 |
| **CH32M030RM V1.2 `109a7bb0ab9a0b70`** | **第 18 章** | **0x1FFFF3A0 / 3A8 / 3AC / 3B0** | **229–230** |

> **CH32M030 的 ESIG 整组下移到 `0x1FFFF3A0`**，与其信息块整体位置一致（用户选择字 `0x1FFFF300–0x1FFFF37F`、厂商配置字 `0x1FFFF380–0x1FFFF3FF`，见 CH32M030RM V1.2 `109a7bb0ab9a0b70` 第 231 页）。**这是芯片差异而非手册版本差异**——同一份手册内部两处（信息块表与 ESIG 表）互相印证。

### 3.2 特征信息指示寄存器（FEATURE_SIGN）—— 仅 2 份手册有

出处：CH32FV2x_V3xRM V2.5 (`6bdc58b159a95c40`) 第 545、547 页 · CH32V407RM V1.1 (`63625af9027af6ab`) 第 525 页。

`R32_FEATURE_SIGN`，访问地址 **0x1FFFF7D0**，复位值 **0xE339XXXX**。位域（CH32FV2x_V3xRM V2.5 第 547 页，§33.2.3）：

| 位 | 名称 | 访问 | 描述（原文） | 复位值 |
|---|---|---|---|---|
| [31:16] | Reserved | RO | 保留。 | **0xE339** |
| [15:8] | Reserved | RO | **bit[15:8]复位值为 bit[7:0]复位值取反。** | X |
| [7:1] | Reserved | RO | 保留。 | **0x7F** |
| 0 | **VLEVEL** | RO | VDD 支持最低供电电压：`0`：**1.8V**；`1`：**2.4V**。 | x |

原文注：「**仅适用于 bit[7:0]复位值与 bit[15:8]复位值取反的产品。若非取反，则 VDD 支持最低供电电压为 2.4V。**」
EN: valid only when `[15:8]` is the bitwise complement of `[7:0]`; otherwise assume 2.4V minimum VDD.

> 读法：先校验 `((v >> 8) & 0xFF) == (~v & 0xFF)`，通过才可信 `VLEVEL`，否则按 2.4V 处理。高 16 位恒为 `0xE339`（与擦除后 FLASH 的读出值一致，见 §6.3）。

### 3.3 用户选择字（Option Bytes）—— 全 12 份有，地址与字段各不相同

**通用结构**（各手册逐字一致）：「用户选择字信息块总共有 8 个字节（4 个字节为写保护，1 个字节为读保护，1 个字节为配置选项，2 个字节存储用户数据），**每个位都有其反码位用于装载过程中的校验**。」

32 位选择字格式划分（表头一致）：

| [31:24] | [23:16] | [15:8] | [7:0] |
|---|---|---|---|
| 选择字字节 1 反码 | 选择字字节 1 | 选择字字节 0 反码 | 选择字字节 0 |

**基址与第 4 字（0x…80C）内容的差异**：

| 手册（版本，sha256 前16） | 选择字基址 | 0x…800 | 0x…804 | 0x…808 | 0x…80C | 出处页 |
|---|---|---|---|---|---|---|
| CH32V003RM V1.9 `7a6bf439ecd68e0b` | 0x1FFFF800 | nUSER/USER/nRDPR/RDPR | nData1/Data1/nData0/Data0 | nWRPR1/WRPR1/nWRPR0/WRPR0 | **Reserved ×4** | 188 |
| CH32L103RM V2.2 `27a1b969cb2cb99d` | 0x1FFFF800 | 同上 | 同上 | 同上 | **Reserved ×4** | 306 |
| CH32V00XRM V1.5 `7d216d69fd04d990` | 0x1FFFF800 | 同上 | 同上 | 同上 | **nWRPR3/WRPR3/nWRPR2/WRPR2** | 222 |
| CH32X035RM V1.9 `c7e301eac4790ca1` | 0x1FFFF800 | 同上 | 同上 | 同上 | **nWRPR3/WRPR3/nWRPR2/WRPR2** | 234 |
| CH32FV2x_V3xRM V2.5 `6bdc58b159a95c40` | 0x1FFFF800 | 同上 | 同上 | 同上 | **nWRPR3/WRPR3/nWRPR2/WRPR2** | 542 |
| CH32H417RM V1.7 `b57ebb0c0ae2cd77` | 0x1FFFF800 | 同上 | 同上 | 同上 | **nWRPR3/WRPR3/nWRPR2/WRPR2** | 876 |
| **CH32M030RM V1.2 `109a7bb0ab9a0b70`** | **0x1FFFF300** | 同上（基址 0x1FFFF300） | 0x1FFFF304 | 0x1FFFF308 | **表中只列 3 个字** | 240 |

**RDPR 读保护字节**（各手册一致的取值语义）：
「`0xA5`：若此字节为 `0xA5`（**nRDP 必须为 `0x5A`**），表示当前代码处于非读保护状态，可以读出；其他值：表示代码读保护状态，不可读，**0-N 页将自动写保护，不受 WRPR0 控制**。」复位值 `0xA5`。
自动写保护范围随芯片不同：

| 手册（版本） | 自动写保护范围（原文） | 出处 |
|---|---|---|
| CH32V003RM V1.9 | 0-31 页（**2K**） | `7a6bf439ecd68e0b` 第 188 页 |
| CH32V00XRM V1.5 | 0-7 页（**2K**） | `7d216d69fd04d990` 第 222 页 |
| CH32X035RM V1.9 | 0-7 页（**2K**） | `c7e301eac4790ca1` 第 234 页 |
| CH32L103RM V2.2 | 0-31 页（**4K**） | `27a1b969cb2cb99d` 第 306 页 |
| CH32FV2x_V3xRM V2.5 | 0-15 页（**4K**） | `6bdc58b159a95c40` 第 542 页 |
| CH32H417RM V1.7 | DBMODE=1 时 0-31 页（**8K**）；DBMODE=0 时 0-15 页（**4K**） | `b57ebb0c0ae2cd77` 第 876 页 |

**USER 字节字段** —— 型号相关性最强的一张表：

**(a) CH32FV2x_V3xRM V2.5 (`6bdc58b159a95c40`) 第 542–543 页**（含 CODE/RAM 容量分配，本任务最有价值的取值→型号映射之一）：

| 位 | 名称 | 取值含义（原文照抄） | 复位值 |
|---|---|---|---|
| [7:5] | `RAM_CODE_MOD` | `00x`：CODE-192KB + RAM-128KB；`01x`：CODE-224KB + RAM-96KB；`10x`：CODE-256KB + RAM-64KB；`110`：CODE-128KB + RAM-192KB；`111`：CODE-288KB + RAM-32KB。**注：（1）适用于 CH32V303RC、CH32V303VC、CH32V307RC、CH32V307WC、CH32V307VC、CH32F203RC、CH32F203VC、CH32F207VC、CH32V317VC、CH32V317WC、CH32V317SC 系列芯片；（2）`110b` 仅适用于批号倒数第六位不为 0 的产品。** | x |
| （同 [7:5]，另一组型号） | `RAM_CODE_MOD` | `00x`：CODE-128KB + RAM-64KB；`01x`：CODE-144KB + RAM-48KB；`1xx`：CODE-160KB + RAM-32KB。**注：适用于 CH32V20x_D8W、CH32V20x_D8、CH32F20x_D8W 系列芯片。** | x |
| [4:3] | Reserved | 保留。 | **11b** |
| 2 | `STANDYRST` | 待机模式下系统复位控制：`0` 启用，进入待机模式产生系统复位；`1` 不启用。 | 1 |
| 1 | `STOPRST` | 停止模式下系统复位控制：`0` 启用；`1` 不启用。 | 1 |
| 0 | `IWDGSW` | 独立看门狗硬件使能位：`0` 由硬件开启（随 LSI 时钟决定）；`1` 由软件开启，禁止硬件开启。 | 1 |

同页 WRPR 说明：「每个比特位用于控制主存储器中 1 个扇区（**4K 字节/扇区**）……4 个字节用于保护总共 **480K** 字节的主存储器。WRPR3：位 0-6 提供第 24-30 扇区的写保护；**位 7 提供第 31-119 扇区的写保护**。」复位 `0xFFFFFFFF`。

**(b) CH32V407RM V1.1 (`63625af9027af6ab`) 第 523 页**：`RAM_CODE_MOD` 只有 1 位——「`1`：CODE-576KB + RAM-136KB；`0`：CODE-512KB + RAM-200KB」。

**(c) CH32V003RM V1.9 (`7a6bf439ecd68e0b`) 第 188 页**：

| 位 | 名称 | 取值含义（原文） | 复位值 |
|---|---|---|---|
| [7:6] | Reserved | **保留（必须为 1）** | 11b |
| 5 | `START_MODE` | 上电启动方式：`1` 从 BOOT 区启动；`0` 从用户区启动。**注：该功能不适用于批号倒数第 5 位为 0 的产品。** | 1 |
| [4:3] | `RST_MODE` | PD7 复用为外部引脚复位。`00`：开启复用功能，上电复位忽略 **128us** 以内的引脚状态，上电复位时间至少保持 128us；`01`：忽略 **1ms**；`10`：忽略 **12ms**；`11`：复用功能关闭，RST 为 IO 功能。 | **10b** |
| 2 | `STANDYRST` | `1` 不启用；`0` 启用，进入待机模式产生系统复位。 | 1 |
| 1 | Reserved | 保留。 | 1 |
| 0 | `IWDG_SW` | `1` 由软件开启，禁止硬件开启；`0` 由硬件自行开启（LSI 会自动开启）。**注：调试模式下内核停止，看门狗硬件使能将失效。** | 1 |

WRPR：「每个比特位……1 个扇区（**1K 字节/扇区**）……2 个字节用于保护总共 **16K** 字节。WRP2：保留；WRP3：保留。」复位 `FFFFh`。

**(d) CH32V00XRM V1.5 (`7d216d69fd04d990`) 第 222–223 页** —— `RST_MODE` 复位值分型号：

原文：「`00`：开启复用功能，上电复位忽略 128μs 以内的引脚状态；`01`：忽略 1ms；`10`：忽略 12ms；`11`：复用功能关闭，RST 为 IO 功能。」复位值列写作「**CH32V007/CH32M007 芯片复位值：`11b`；其他芯片复位值为：`10b`**」。
WRPR：「每个比特位用于控制主存储器中 **2 个扇区（1K 字节/扇区）**……4 个字节用于保护总共 **65K** 字节的主存储器。……WRP3：位 0-6 提供第 48-61 扇区的写保护；**位 7 提供第 62 扇区（3328 字节的系统存储器）的写保护**。」

**(e) CH32X035RM V1.9 (`c7e301eac4790ca1`) 第 234 页**：

| 位 | 名称 | 取值含义（原文） | 复位值 |
|---|---|---|---|
| [7:5] | Reserved | 保留。 | `xxxb` |
| [4:3] | `RST_MODE` | 外部复位引脚 RST 使能：**`00`：开启 RST 复用功能；`11`：复用功能关闭，PA21/PC3/PB7 为 GPIO 功能。**（**手册只列 `00` 与 `11` 两档，未说明 `01`/`10`**） | `11b` |
| 2 | `STANDYRST` | `1` 不启用；`0` 启用，进入待机模式产生系统复位。 | 1 |
| 1 | `STOPRST` | `1` 不启用，进入停止模式不复位系统；`0` 启用。 | 1 |
| 0 | `IWDGSW` | `1` 由软件开启，禁止硬件开启；`0` 由硬件开启（**随 HSI 时钟决定**）。 | 1 |

`RST_MODE` 原文注：「不同封装的复位引脚，参考数据手册中引脚说明。例如，**64 脚 R8T6 和 48 脚 C8T6 封装中 PA21 可以复用作为外部复位引脚**。」← 封装→引脚映射，属本类要点。
WRPR：「每个比特位用于控制主存储器中 **2 个扇区（1K 字节/扇区）**……4 个字节用于保护总共 **65K** 字节。……WRP3：位 0-6 提供第 48-61 扇区的写保护；**位 7 提供第 62 扇区（3328 字节的系统存储器）的写保护**」，复位 `0xFFFFFFFF`。

> **`IWDGSW` 的 HSI 是真差异**：CH32X035RM V1.9 全文「LSI」出现 **0 次**；第 23 页第 5 章「IWDG 时钟源来自于**内部高速时钟 HSI 的 1024 分频（47KHz）**」，第 13 页 §3.3.3.3「HSI 振荡器将被强制打开，并且不能被关闭」，第 7 页「待机模式下可工作模块：独立看门狗（IWDG）。此模式高频时钟（HSI）域被关闭」。四处一致 ⇒ **该芯片无 LSI，IWDG 走 HSI/1024**。对比 CH32X315 的同一表述则是手册内部矛盾，见 §6.7。
> 另：`RST_MODE` 只定义了 `00`/`11` 两档，而 CH32V003/CH641/CH32V00X/CH32M030 都定义了 4 档（含不同的上电忽略时长）。**无法区分**是 CH32X035 硬件只有 2 档还是手册省略——写驱动时不要假定 `01`/`10` 可用。

**(f) CH32X315RM V1.1 (`b6a752f9e9bdbb1d`) 第 306 页** —— USER 字节与其它芯片**完全不同**，含两个下载功能开关：

| 位 | 名称 | 取值含义（原文） | 复位值 |
|---|---|---|---|
| 7 | `USARTDLEN` | BOOT 使能 **USART 免按键下载**功能[1]：`1` 开启；`0` 关闭。 | 1 |
| 6 | `USBHSDLEN` | BOOT 使能 **USBHS 下载**功能[1]：`1` 开启；`0` 关闭。 | 1 |
| 5 | Reserved | 保留。 | 1 |
| 4 | `START_MD` | 启动模式配置：`1` 有 BOOT 时，上电之后系统从 BOOT 区启动；`0` 从用户区启动。 | 1 |
| 3 | `CFGRSTEN` | 外部引脚复位使能：**`1` 关闭；`0` 开启**（低有效）。 | 1 |
| [2:1] | Reserved | 保留。 | 11b |
| 0 | `IWDGSW` | `1` 由软件开启，禁止硬件开启；`0` 由硬件开启（**随 HSI 时钟决定**）。 | 1 |

注[1]（第 307 页原文）：「此功能的具体操作方式和注意事项请参考 **CH32X315 评估板说明书**。」
WRPR：「1 个扇区（**4K 字节/扇区**）……4 个字节用于保护总共 **480K** 字节」，复位 `0xFFFFFFFF`。

> **CH32X315 的 `IWDGSW` 时钟源在手册内部自相矛盾**（详见 §6.7）：选择字表（p306）与 `FLASH_OBR`（p301）都写「随 **HSI** 时钟决定」，但同一手册第 7 章（p43）写「IWDG 时钟源来自于 **LSI**」、结构框图标注 **LSI (40kHz)**，§3.3.5.3（p15）也写「**LSI** 振荡器将被强制打开」。**以 LSI 为准**（3 处对 2 处，且框图给了频率）。

**CH32X035 的 HSI 则是真差异，不是笔误**：CH32X035RM V1.9 (`c7e301eac4790ca1`) 全文 **「LSI」出现 0 次**；第 23 页第 5 章原文「IWDG 时钟源来自于**内部高速时钟 HSI 的 1024 分频（47KHz）**」，第 13 页 §3.3.3.3「如果独立看门狗已经由硬件配置设置或软件启动，**HSI 振荡器将被强制打开**，并且不能被关闭」，第 7 页「待机模式下……此模式高频时钟（HSI）域被关闭」。四处一致 ⇒ **芯片差异**（CH32X035 无 LSI）。

**(g) CH32H417RM V1.7 (`b57ebb0c0ae2cd77`) 第 876 页**：

| 位 | 名称 | 取值含义（原文） | 复位值 |
|---|---|---|---|
| 7 | `USARTDLEN` | BOOT 使能 USART 免按键下载功能[1]。 | 1 |
| 6 | `USBFSDLEN` | BOOT 使能 **USBFS**（非 USBHS）下载功能[1]。 | 1 |
| [5:1] | Reserved | 保留。 | **0x1F** |
| 0 | `IWDGSW` | `0` 由硬件开启（随 LSI 时钟决定）；`1` 由软件开启。 | 1 |

WRPR：「1 个扇区（**当 DBMODE=1 时：8K 字节/扇区；当 DBMODE=0 时：4K 字节/扇区**）」，复位 `0xFFFFFFFF`。
→ **同一颗芯片上写保护的扇区粒度随 DBMODE 变化**，与 §3.5 的双模式一致。

**(h) CH641RM V1.4 (`af83c6fca780cfed`) 第 157 页**：

| 位 | 名称 | 取值含义（原文） | 复位值 |
|---|---|---|---|
| [7:6] | Reserved | **保留（必须为 1）** | 11b |
| 5 | `START_MODE` | `1` 从 BOOT 区启动；`0` 从用户区启动，**BOOT 区也可以放置用户应用程序**。 | 1 |
| [4:3] | `RST_MODE[1:0]` | **PA6** 复用为外部复位引脚 NRST。`00` 忽略 128μs；`01` 忽略 1ms；`10` 忽略 12ms；`11` 复用功能关闭，**PA6 为 IO 功能**。 | **11b** |
| 2 | `STANDYRST` | `1` 不启用；`0` 启用，进入待机模式产生系统复位。 | 1 |
| 1 | Reserved | 保留。 | 1 |
| 0 | **Reserved** | **保留**（← 此处**没有** IWDG_SW 位） | 1 |

WRPR：「1 个扇区（**1K 字节/扇区**）……2 个字节用于保护总共 **16K** 字节。WRP2：保留；WRP3：保留」，复位 `0xFFFF`。
> CH641 与 CH32V003 同为青稞 V2A，但 **CH641 的 bit0 是 Reserved 而 CH32V003 是 `IWDG_SW`**，且 `RST_MODE` 复位值 `11b`（V003 为 `10b`）、复位引脚是 PA6（V003 为 PD7）。判为**芯片差异**（CH641RM V1.4 vs CH32V003RM V1.9，两份各自表内自洽）。

**(i) CH32V205RM V1.2 (`b1ed9ef040455a1f`) 第 380–381 页** 与 **CH32L103RM V2.2 (`27a1b969cb2cb99d`) 第 306–307 页** —— 两者 USER 字节**逐字相同**，且都含一个 CAN 相关位：

| 位 | 名称 | 取值含义（原文） | 复位值 |
|---|---|---|---|
| [7:6] | Reserved | 保留。 | X |
| 5 | **`CFGCANM`** | **配置 CAN 离线恢复时间**：`1` 从离线恢复到正常更快一些；`0` 从离线恢复到正常符合 CAN 协议。 | 1 |
| [4:3] | Reserved | 保留。 | `11b`（V205）/ `X`（L103） |
| 2 | `STANDYRST` | `1` 不启用，进入待机模式系统不复位；`0` 启用。 | 1 |
| 1 | `STOPRST` | 停止模式下系统复位控制：`1` 不启用，进入停止模式不复位系统；`0` 启用。 | 1 |
| 0 | `IWDGSW` | `1` 由软件开启；`0` 由硬件开启（随 LSI 时钟决定）。 | 1 |

WRPR 差异（**芯片差异**）：
- CH32V205RM V1.2 第 381 页：「每个比特位用于控制主存储器中 **4 个扇区（2K 字节/扇区）**……**4 个字节**用于保护总共 **256K** 字节。WRPO：第 0-31 扇区；WRP1：第 32-63 扇区；WRP2：第 64-95 扇区；WRP3：第 96-127 扇区」，复位 `FFFFFFFFh`；`0x…80C` = `nWRPR3/WRPR3/nWRPR2/WRPR2`。
- CH32L103RM V2.2 第 307 页：「**2 个扇区（2K 字节/扇区）**……**2 个字节**用于保护总共 **64K** 字节。WRPO：第 0-15 扇区；WRP1：第 16-31 扇区；**WRP2：保留；WRP3：保留**」，复位 `FFFFh`；`0x…80C` = `Reserved ×4`。

**(j) CH32M030RM V1.2 (`109a7bb0ab9a0b70`) 第 240–241 页** —— 唯一带**复位引脚选择位**的：

| 位 | 名称 | 取值含义（原文） | 复位值 |
|---|---|---|---|
| 6 | Reserved | 保留。 | x |
| 5 | **`RST_PIN_SEL`** | **复位引脚选择位：`1`：PA15；`0`：PC0。** | 1 |
| [4:3] | `RST_MODE[1:0]` | 复用为外部引脚复位。`00` 忽略 **128us**；`01` 忽略 **512us**；`10` 忽略 **1ms**；`11` 复用功能关闭，RST 为 IO 功能。**注：默认关闭引脚复位功能。** | **11b** |
| 2 | `STANDYRST` | 待机模式的低功耗管理复位配置：`1` 禁止；`0` 使能。 | 1 |
| 1 | `STOPRST` | 停止模式的低功耗管理复位配置：`1` 禁止；`0` 使能。 | 1 |
| 0 | Reserved | 保留。 | 1 |

WRPR：「每个比特位用于控制主存储器中 **4K 字节**的写保护状态……**2 个字节**用于保护总共 **64K** 字节。WRPO：**0–32K 字节地址**存储写保护控制；WRP1：**32K–64K 字节地址**存储写保护控制」，复位 `0xFFFFFFFF`。
> `RST_MODE` 的**第二档取值是 512us**，而所有其它芯片都是 1ms——照抄勿套用。

**(k) CH32xRM V2.0 (`b4ade26ba00e0f03`) 第 279 页** —— 唯一带**上电复位时间配置**的：

| 位 | 名称 | 取值含义（原文） | 复位值 |
|---|---|---|---|
| [7:6] | Reserved | 保留。 | 11b |
| 5 | **`PORCTR`** | **上电复位时间配置：`1` 复位时间 16.384ms；`0` 复位时间 40.96ms。** | 1 |
| [4:3] | Reserved | 保留 | 1 |
| 2 | `STANDYRST` | `1` 不启用；`0` 启用。 | 1 |
| 1 | `STOPRST` | `1` 不启用，进入停止模式不复位系统；`0` 启用。 | 1 |
| 0 | `IWDGSW` | `1` 由软件开启；`0` 由硬件开启（随 LSI 时钟决定）。 | 1 |

`RDPR` 复位值在该手册写作 **`0`**（其余 11 份均写 `0xA5`）。**[推断]** 这是排版遗漏（正文仍写「`0xA5`：……表示当前代码处于非读保护状态」），实际应为 `0xA5`；需实测确认。

#### 3.3.1 USER 字节跨芯片字段对照（bit5 / bit[4:3] 是分歧最大的两处）

所有出处均为各手册的「用户选择字信息结构」表，页码见上文 (a)–(k)。

| 手册（版本 sha256前16） | bit7 | bit6 | bit5 | bit[4:3] | bit2 | bit1 | bit0 |
|---|---|---|---|---|---|---|---|
| CH32V003RM V1.9 `7a6bf439ecd68e0b` p188 | Rsvd(=1) | Rsvd(=1) | `START_MODE` | `RST_MODE`(PD7) 复位 `10b` | `STANDYRST` | Rsvd | `IWDG_SW` |
| CH641RM V1.4 `af83c6fca780cfed` p157 | Rsvd(=1) | Rsvd(=1) | `START_MODE` | `RST_MODE`(PA6) 复位 `11b` | `STANDYRST` | Rsvd | **Rsvd** |
| CH32V00XRM V1.5 `7d216d69fd04d990` p222 | Rsvd(=1) | Rsvd(=1) | `START_MODE` | `RST_MODE` 复位 `11b`(V007/M007) / `10b`(其它) | `STANDYRST` | Rsvd | `IWDG_SW` |
| CH32X035RM V1.9 `c7e301eac4790ca1` p234 | Rsvd | Rsvd | Rsvd | `RST_MODE`(PA21/PC3/PB7) 复位 `11b`，**仅 2 档** | `STANDYRST` | `STOPRST` | `IWDGSW`(**HSI**) |
| CH32M030RM V1.2 `109a7bb0ab9a0b70` p240–241 | — | Rsvd | **`RST_PIN_SEL`** | `RST_MODE` 复位 `11b`（档位含 **512us**） | `STANDYRST` | `STOPRST` | **Rsvd** |
| CH32V205RM V1.2 `b1ed9ef040455a1f` p380–381 | Rsvd | Rsvd | **`CFGCANM`** | Rsvd `11b` | `STANDYRST` | `STOPRST` | `IWDGSW` |
| CH32L103RM V2.2 `27a1b969cb2cb99d` p306–307 | Rsvd | Rsvd | **`CFGCANM`** | Rsvd `X` | `STANDYRST` | `STOPRST` | `IWDGSW` |
| CH32xRM V2.0 `b4ade26ba00e0f03` p279 | Rsvd | Rsvd | **`PORCTR`** | Rsvd | `STANDYRST` | `STOPRST` | `IWDGSW` |
| CH32FV2x_V3xRM V2.5 `6bdc58b159a95c40` p542–543 | ← `RAM_CODE_MOD[7:5]` → | | | Rsvd `11b` | `STANDYRST` | `STOPRST` | `IWDGSW` |
| CH32V407RM V1.1 `63625af9027af6ab` p523 | ← `RAM_CODE_MOD`(1 位) → | | | — | — | — | — |
| CH32X315RM V1.1 `b6a752f9e9bdbb1d` p306 | **`USARTDLEN`** | **`USBHSDLEN`** | Rsvd | `START_MD`(bit4) + `CFGRSTEN`(bit3) | Rsvd | Rsvd | `IWDGSW`(HSI) |
| CH32H417RM V1.7 `b57ebb0c0ae2cd77` p876 | **`USARTDLEN`** | **`USBFSDLEN`** | ← Rsvd `[5:1]`=`0x1F` → | | | | `IWDGSW` |

**判定**：以上全部为**芯片差异**——每份手册的 USER 表与该芯片的复位引脚、外设（CAN/USB/以太网）、Flash 容量一一对应，且表内字段名、复位值、正文说明三处自洽。**唯一无法区分的是 CH32X315 的 `IWDGSW=0` 写「随 HSI 时钟决定」**（其余 11 份写 LSI），以及 CH32xRM 的 `RDPR` 复位值写 `0`（其余写 `0xA5`）——这两处更像笔误，但无第二来源可证。

**通用移植警告**：`STANDYRST` / `STOPRST` / `IWDGSW` **全部是低电平有效**（`0` = 启用该功能），与直觉相反；`CFGRSTEN`（X315）也是 `1` 关闭、`0` 开启。擦除后的选择字全 `1`，等价于「全部禁用」。

### 3.4 FLASH_OBR 选择字寄存器 —— 复位后自动装载的只读镜像

CH32V00XRM V1.5 (`7d216d69fd04d990`) 第 217–218 页，偏移地址 `0x1C`：

| 位 | 名称 | 访问 | 描述 | 复位值 |
|---|---|---|---|---|
| [31:26] | Reserved | RO | 保留。 | 0 |
| [25:18] | `DATA1[7:0]` | RO | 数据字节 1。 | X |
| [17:10] | `DATA0[7:0]` | RO | 数据字节 0。 | X |
| [9:8] | `FIX_11` | RO | **固定为 11。** | 11b |
| 7 | `STATR_MODE` | RO | 上电启动方式：1 从 BOOT 区启动；0 从用户区启动。 | 1 |
| [6:5] | `RST_MODE` | RO | 配置字复位延迟时间。 | X |
| 4 | `STANDY_RST` | RO | 待机模式下系统复位控制，**低电平有效**。 | X |
| 3 | Reserved | RO | 保留。 | X |
| 2 | `IWDG_SW` | RO | 独立看门狗硬件使能位，**低电平有效**。 | 1 |
| 1 | `RDPRT` | RO | 读保护状态。1：表示闪存当前读保护有效。 | 1 |
| 0 | `OBERR` | RO | 选择字错误。**1：表示选择字和它的反码不匹配。** | 0 |

原文注：「**USER 和 RDPRT 在系统复位后从用户选择字区域加载。**」
同页 `FLASH_WPR`（偏移 `0x20`）注：「WPR 在系统复位后从用户选择字区域加载」，`[31:0] WPR` RO「1：写保护失效；0：写保护有效。每个比特位代表 2K 字节（8 页）」。

对应 CH32V003RM V1.9 (`7a6bf439ecd68e0b`) 第 183 页字段名为 `2'b11`（而非 `FIX_11`）；CH32M030RM V1.2 (`109a7bb0ab9a0b70`) 第 235 页多出 `0V_CFG`、`RST_PIN_S`、`STOPRST`、`OPTERR` 等位。

### 3.5 系统存储区 / 厂商配置字 —— 容量与地址逐芯片不同

| 手册（版本，sha256 前16） | bootloader（系统存储器） | 厂商配置字 | 用户选择字 | 出处页 |
|---|---|---|---|---|
| CH32V003RM V1.9 `7a6bf439ecd68e0b` | — | **64B**「出厂前固化，用户不可修改」 | 64 字节区域 | 4；189 |
| CH32M030RM V1.2 `109a7bb0ab9a0b70` | — | **128B**（`0x1FFFF380–0x1FFFF3FF`） | `0x1FFFF300–0x1FFFF37F`（128B） | 4；231 |
| CH32FV2x_V3xRM V2.5 `6bdc58b159a95c40` | **28K**（`0x1FFF8000–0x1FFFEFFF`） | **128B** | `0x1FFFF800–0x1FFFF87F`（128B） | 18；532 |
| CH32L103RM V2.2 `27a1b969cb2cb99d` | **3K+256**（`0x1FFF0000–0x1FFF0CFF`） | **256B** | `0x1FFFF800–0x1FFFF8FF`（256B） | 6；298 |
| CH32H417RM V1.7 `b57ebb0c0ae2cd77` | **56K**（`0x1FFF0000–0x1FFFDFFF`，DBMODE=1）/ **28K**（`0x1FFF0000–0x1FFF6FFF`，DBMODE=0） | **256B** | `0x1FFFF800–0x1FFFF8FF`（256B） | 7；865 |
| CH32xRM V2.0 `b4ade26ba00e0f03` | 系统引导代码存储 1 `0x1FFFF000–0x1FFFF7FF`（2K） | — | — | 270 |

CH32H417RM V1.7 第 7 页原文：「用户区和 BOOT 区大小通过 `R32_FLASH_CFGR0` 寄存器 **DBMODE 位读取**：当 `DBMODE=1` 时，芯片内置 960K 字节非零等待的程序闪存存储区……等效频率约 25MHz。内置最大 56K 字节系统存储区……当 `DBMODE=0` 时，芯片内置 480K 字节……等效频率约 12.5MHz。内置最大 28K 字节系统存储区。」
→ **CH32H417 上 Flash 容量与页大小是运行期可读的双模式，不能编译期写死。**

### 3.6 出厂校准值

- **HSI 校准**（所有 RISC-V 手册通用）：「制造工艺的差异会导致每个芯片的 RC 振荡频率不同，所以在芯片出厂前，会为每颗芯片进行 HSI 校准。系统复位后，**工厂校准值被装载到 `RCC_CTLR` 寄存器的 `HSICAL[7:0]` 中**。」出处：CH32FV2x_V3xRM V2.5 (`6bdc58b159a95c40`) 第 31、37 页 · CH32H417RM V1.7 (`b57ebb0c0ae2cd77`) 第 18、23 页 · CH32L103RM V2.2 (`27a1b969cb2cb99d`) 第 17、21 页 · CH32M030RM V1.2 (`109a7bb0ab9a0b70`) 第 12、14 页。
- **`R32_ISINK_ADJ` ISINK 灌电流校准值寄存器**（CH32M030 独有）：访问地址 **`0x1FFFF390`**，复位值 `0x00XX00XX`。`[21:16] ISINK2_ADJ[5:0]` RO、`[5:0] ISINK1_ADJ[5:0]` RO。出处：CH32M030RM V1.2 (`109a7bb0ab9a0b70`) 第 245、249 页。
  原文注（第 249 页）：「**`ISINK1_CFGR` 不可读，改写寄存器时，`ISINK1_ADJ[5:0]` 数值来自 ISINK 灌电流校准值寄存器**」——即写 ISINK 配置前必须先从 `0x1FFFF390` 读出校准值再回填，**属于「上电后需先读取」类**。
- **`0x1FFFF72A`（CH32L103 独有的裸地址）**：CH32L103RM V2.2 (`27a1b969cb2cb99d`) 第 21 页，`RCC_CTLR.bit2 HSILP` 说明中的注：「**HSI 进入内部低功耗模式时要把 `0x1FFFF72A` 地址的值加载到 `HSITRIM[4:0]` 里，实现低功耗模式下的修正**」。手册未给该地址任何寄存器名或位域说明——**纯魔数**，见 §6。

### 3.7 CH32H417 双核私有外设（内存映射，非 CSR）

出处：CH32H417RM V1.7 (`b57ebb0c0ae2cd77`) 第 69、75–77 页。

- **IPC 核间通信**（表 4-8，第 69 页）：`R32_IPC_CTLR` 0xE000D000、`R32_IPC_ISR` 0xE000D004、`R32_IPC_ISM` 0xE000D008、`R32_IPC_ENA` 0xE000D010、`R32_IPC_STS` 0xE000D014、`R32_IPC_SET` 0xE000D018、`R32_IPC_CLR` 0xE000D01C、`R32_IPC_MSG0–3` 0xE000D020/024/028/02C。
- **HSEM 硬件信号量**（第 75–77 页）：32 通道，`R32_HSEM_RXy` 偏移 `0x000+4y`、`R32_HSEM_RLRXy` 偏移 `0x100+4y`、`R32_HSEM_LSE` 0xE000C200、`R32_HSEM_CLR` 0xE000C208、**`R32_HSEM_KEY` 0xE000C20C 复位值 `0x5AA50003`**、`R32_HSEM_IER` 0xE000C300、`R32_HSEM_ISR` 0xE000C308、`R32_HSEM_ISM` 0xE000C310、`R32_HSEM_LSM` 0xE000C318。
  `HSEM_CLR.[31:16] CLR_KEY` WO：「解锁关键字，当写数据与匹配关键字相等时操作有效，否则无效。**键值为 `0x5AA5`**。」`HSEM_KEY.[31:16] KEY_VALUE` RO 复位 `0x5AA5`。
  `HSEM_RXy`：`bit31 LOCK`、`[9:8] CID`（1 通道被内核 1 锁定 / 0 空闲或被内核 0 锁定）、`[7:0] PID`。
  原文注（第 75 页）：「寄存器中标注有"**内核私有寄存器**"的为外设中存在多组功能相同，数据相互独立，**数据不可被其他内核访问或改写**的寄存器，仅内核对其访问地址相同。」← 同一地址在两个核上是两份独立存储，调试器读到的值取决于挂在哪个核。

### 3.8 PFIC 免表中断（VTF）寄存器 —— WCH 特有的核内外设

原文（CH32FV2x_V3xRM V2.5 `6bdc58b159a95c40` 第 77 页）：「特有**免表 VTF（Vector Table Free）中断响应机制**，4 路可编程直达中断向量地址」。

寄存器（同手册第 94 页表）：`R32_PFIC_VTFIDR` 0xE000E050、`R32_PFIC_VTFADDRR0` 0xE000E060、`…R1` 0xE000E064、`…R2` 0xE000E068、`…R3` 0xE000E06C。
CH32H417RM V1.7 (`b57ebb0c0ae2cd77`) 第 80、88 页同址同名（「提供 4 路免表中断（VTF）」）；CH32L103RM V2.2 (`27a1b969cb2cb99d`) 第 51、57 页同址，复位值写作 `0x00000000`（CH32FV2x 写作 `0xXXXXXXXX`）。

---

## 4. 触摸控制器（TKY / TKEY）编程模型

### 4.1 硬件侧：TKEY 寄存器集合 —— 四套互不兼容的实现

**关键共性：TKEY 寄存器全部叠加映射在 ADC 寄存器上，读写语义不同。**

**(a) 「充电时间」型（最简），CH32V00X**
出处：CH32V00XRM V1.5 (`7d216d69fd04d990`) 第 101–103 页（第 10 章 触摸按键检测（TKEY））。

| 名称 | 访问地址 | 偏移 | 描述 | 复位值 |
|---|---|---|---|---|
| R32_TKEY_CHG | 0x4001243C | 0x3C | TKEY 充电时间配置寄存器 | 0x00000000 |
| R32_TKEY_DISCHG | 0x4001244C | 0x4C | TKEY 启动和放电时间配置寄存器 | 0x00000000 |
| R32_TKEY_DR | **0x4001244C** | 0x4C | TKEY 数据寄存器 | 0x00000000 |

- `R32_TKEY_CHG`：`[10:0] TKCHARGE[10:0]` **WO**「TKEY 充电时间。（单位：系统时钟周期）」。
  原文注：「此寄存器**映射 ADC 模块的注入数据寄存器 1（ADC_IDATAR1）**。因此当该地址寄存器进行"写操作"时，作为 TKEY 充电时间执行；进行"读操作"时，作为 ADC_IDATAR1 执行。」
- `R32_TKEY_DISCHG`：`[10:0] TKACT_DCG[10:0]` **WO**「**写放电时间并启动一次 TKEY 通道检测**」。注：映射 `ADC_RDATAR`。
- `R32_TKEY_DR`：`[15:0] DATA[15:0]` RO「转换的数据」。注：映射 `ADC_RDATAR`。

> **同一地址 `0x4001244C`：写 = 设置放电时间并启动转换；读 = 取转换结果。** 读改写会直接触发采样。

操作步骤（第 101–102 页原文）：「1）初始化 ADC……将 `ADC_CTLR1` 寄存器的 `TKENABLE` 位置 1，打开 TKEY 单元。2）设置要转换的通道，将通道号写入 ADC 规则组序列中第一个转换位置（`ADC_RSQR3[4:0]`），设置 `L[3:0]` 为 1。3）设置通道的充电采样时间，写 `R32_TKEY_CHG` 寄存器，单位：HBCLK。4）写 `R32_TKEY_DISCHG` 寄存器，设置放电时间，单位：HBCLK，**硬件自动启动一次 TKEY 的采样和转换**。5）等待 ADC 状态寄存器的 EOC……读取 `ADC_DR`。」

**(b) 「逐通道充电时间 + 偏移量」型，CH32X035 / CH32FV2x / CH32H417 / CH32L103**
出处：CH32X035RM V1.9 (`c7e301eac4790ca1`) 第 101–104 页（第 11 章）。

| 名称 | 访问地址 | 偏移 | 描述 |
|---|---|---|---|
| R32_TKEY1_CHARGE1 | 0x4001240C | 0x0C | TKEY 充电采样时间寄存器 1 |
| R32_TKEY1_CHARGE2 | 0x40012410 | 0x10 | TKEY 充电采样时间寄存器 2 |
| R32_TKEY1_CHGOFFSET | 0x4001243C | 0x3C | TKEY 充电时间偏移量寄存器 |
| R32_TKEY1_ACT_DCG | 0x4001244C | 0x4C | TKEY 启动和放电时间寄存器 |
| R32_TKEY1_DR | **0x4001244C** | 0x4C | TKEY 数据寄存器 |

- `TKEYx_CHARGE1`：`[23:0] TKCGx[2:0]`（x=10–17）**RW**，每通道 3 位。取值（原文）：`000`：4 周期；`001`：6 周期；`010`：8 周期；`011`：10 周期；`100`：5 周期；`101`：7 周期；`110`：9 周期；`111`：11 周期。「**时间基准：ADC 时钟**」。注：映射 `ADC_SAMPTR1`。
  → 注意取值**不是单调递增**（`000`=4、`100`=5、`001`=6、`101`=7 …），照抄勿推导。
- `TKEYx_CHARGE2`：`[29:0] TKCGx[2:0]`（x=0–9），同上编码。注：映射 `ADC_SAMPTR2`。
- `TKEYx_CHGOFFSET`：`[7:0] TKCGOFFSET[7:0]` **WO**「总充电时间 `TCHG=TKCGOFFSET`（单位：**系统时钟周期**）」。注：映射 `ADC_IDATAR1`（写=偏移量，读=注入数据）。
- `TKEYx_ACT_DCG`：`[7:0] TKACT_DCG[7:0]` **WO**「写放电时间并启动一次 TKEY 通道检测」。注：映射 `ADC_RDATAR`。
- `TKEYx_DR`：`[15:0] DATA[15:0]` RO。

原文（第 101 页）：「充电周期数为 `TKEY_CHARGE1` 和 `TKEY_CHARGE2` 寄存器中的 `TKCGx[2:0]` 配置值**加上 `TKEY_CHGOFFSET` 偏移量之和**，每个通道可以分别用不同的充电周期来调整采样电压。」
→ **两段时基混用**：`TKCGx` 以 ADC 时钟计，`TKCGOFFSET` 以系统时钟周期计。

CH32FV2x_V3xRM V2.5 (`6bdc58b159a95c40`) 第 188 页与 CH32H417RM V1.7 (`b57ebb0c0ae2cd77`) 第 195 页有**两组**（TKEY1 @0x4001240C…、**TKEY2 @0x4001280C / 0x40012810 / 0x4001283C / 0x4001284C**）；CH32L103RM V2.2 (`27a1b969cb2cb99d`) 第 127 页只有一组且无 `CHARGE1/2`（仅 `CHGOFFSET`/`ACT_DCG`/`DR`）。

**(c) 「电荷搬移 / 电流源」型（最复杂），CH32V205**
出处：CH32V205RM V1.2 (`b1ed9ef040455a1f`) 第 124–131 页（第 13 章）。

| 名称 | 访问地址 | 偏移 | 描述 |
|---|---|---|---|
| R32_TKEY_CTLR | — | 0x58 | TKEY 控制寄存器 |
| R32_TKEY_TRANS_CFG | — | 0x5C | 电荷搬移配置寄存器 |
| R32_CAP_CFG | 0x40012460 | 0x60 | 电容配置寄存器 |
| R32_DRV_CFG | 0x40012464 | 0x64 | 驱动屏蔽配置寄存器 |
| R32_TKEY_CDCC | 0x40012468 | 0x68 | TKEY 充电放电配置寄存器 |
| R32_TKEY_SR | 0x4001246C | 0x6C | TKEY 状态寄存器 |
| R32_TKEY_RSQR1/2/3 | 0x4001242C / 0x40012430 / 0x40012434 | 0x2C/0x30/0x34 | TKEY 通道序列寄存器 1/2/3 |

`R32_TKEY_CTLR`（第 128–129 页）：
`[15:12] SCANNUM[3:0]` 扫描通道个数（`0000` 1 个 … `1111` 16 个）；`bit11 SCANEN` 通道扫描使能；`bit10 SCANIE` 扫描中断使能；`bit8 TKACT` **WO**「写 1 将触发 TKEY 工作，**硬件自动清零**」；`bit3 CHSEL`「1：通道选择由 TKEY 模块控制；0：由 ADC 模块控制。**注：TKEN 使能后，该位置 1……TKEN 关闭时，该位置 0**」；`bit2 MODE`「1：电流源充电模式；0：电荷搬移模式」；`bit1 ITUNE`「1：充电电流减半；0：**充电电流为 35uA**」；`bit0 TKEN`。

`R32_TKEY_TRANS_CFG`（第 129 页）：
`[14:13] TKSW[1:0]` 开关切换时间：`00` 1Tclk / `01` 2Tclk / `10` 4Tclk / `11` 8Tclk；
`[12:3] TRANSN[9:0]`「实际搬移周期数为 **TRANSN+1**，即最大 1024 个搬移周期」；
`[2:0] TRANSCC[2:0]` 充电 T2 与搬移 T4 时间：`000`：T2=16Tclk, T4=128Tclk；`001`：T2=16, T4=192；`010`：T2=32, T4=128；`011`：T2=32, T4=192；`100`：T2=32, T4=256；`101`：T2=32, T4=320；`110`：T2=48, T4=320；`111`：T2=48, T4=384。「注：时间基准系统时钟 Tclk。」

`R32_CAP_CFG`（第 129–130 页）：`[19:4] SELCS[15:0]` 位掩码选通道（`0000000000000001` 选中 ADC 通道 0 …）「注：在 TKEY 通道扫描模式下，此寄存器配置**第 1 个扫描的通道**」；`[3:0] SELCX[3:0]`「电荷搬移模式下，配置**外接参考电容的通道**，电流源充电模式下，此位无效」。

`R32_DRV_CFG`：`[31:16] DRVOUTSEL[15:0]` 驱动屏蔽通道选择，高电平有效；`bit0 DRVEN`。
`R32_TKEY_CDCC`：`[26:16] TKCC[10:0]` 电流源充电模式下充电时间；`[10:0] TKCD[10:0]` 放电时间。时基系统时钟。
`R32_TKEY_SR`：`bit0 SCANIF` **RW0**「TKEY 通道扫描结束中断标志，**软件写 0 清除，写 1 无效**」。

**(d) CH32xRM V2.0（TKEY_F / TKEY_V 两支）**
CH32xRM V2.0 (`b4ade26ba00e0f03`) 第 1 页对比表明写「TKEY_F / TKEY_V **用法不同**」，寄存器细节在第 110、114 页附近。本轮未逐位抄录（该手册同时覆盖 ARM 与 RISC-V 两支，需先按型号分流）。

### 4.2 软件侧：触摸库 API 与硬件参数的对应

#### 4.2.1 `WCH_touchkey_lite`（`1d55728072da8f86`，未标注版本，10 页）

适用范围（第 1 页原文）：「支持 CH57x、CH58x、CH59X、**CH32V00X、CH32L103、CH32V20X、CH32V30X** 系列 MCU，共有滤波模式 **3、CS10**。」

滤波器模式对比（第 1 页表）：
- `CS10`：「可以通过 IEC 61000-4-6 标准的抗扰度三级测试，即 CS10V 动态测试」；备注「目前支持单按键识别……**轮询函数中有最大 8us 的随机阻塞式延迟**」。
- `3`：「轮询函数需要定时调用……可休眠部分通道，适合对功耗要求较高的场合；支持多按键和单按键」；备注「**轮询函数阻塞运行，扫描触摸通道越多时间越长，最多在 400us 左右**」。

使用流程（图 1）：`TKY_BaseInit` → `TKY_CHInit`（逐通道）→ `TKY_PollForFilterMode_3` 取键值。

**`TKY_BaseInitTypeDef`**（第 2 页，照抄）：
```c
typedef struct {
    uint8_t  maxQueueNum;            //--测试队列数量--
    uint8_t  singlePressMod;         //--单按键模式---
    uint8_t  shieldEn;               //--屏蔽使能---
    uint8_t  filterMode;             //--滤波器模式--
    uint8_t  filterGrade;            //--滤波器等级--
    uint8_t  peakQueueNum;           //--按键最大偏移队列---
    uint8_t  peakQueueOffset;        //--按键最大偏移队列的偏移值---
    uint8_t  baseRefreshOnPress;     //--基线在按键按下时是否进行--
    uint8_t  baseUpRefreshDouble;    //--基线向上刷新倍速参数---
    uint8_t  baseDownRefreshSlow;    //--基线向下更新降速参数---
    uint8_t  rfu[2];                 //--保留--
    uint32_t baseRefreshSampleNum;   //--基线刷新采样次数--
    uint32_t *tkyBufP;               //--测试通道数据缓冲区指针--
} TKY_BaseInitTypeDef;
```
返回值：`0x00` 成功；`0x01` 滤波器模式参数错误；`0x02` 滤波器等级参数错误。

参数取值（第 2–3 页原文要点）：
- `singlePressMod`：`0` 多按键；`1` 单按键（输出变化量最大的键值）；`2` 互斥单按键（只有当前按键释放后才可触发下一个）。
- `shieldEn`：「该功能**需要硬件支持**……目前仅 **CH58x、CH59x、CH32V006、CH32L103** 系列支持。」
- `filterGrade`：**0～15**。「该参数为 0 时，并不代表滤波器未启用，只是滤波器未得到进一步加强。」
- `baseRefreshSampleNum`：**0～65535**，「设置为 0 时，关闭基线刷新」。
- `baseUpRefreshDouble`：**0～255**，「设置为 0 或 1 时不加速」。
- `baseDownRefreshSlow`：**0～65535**。
- `tkyBufP`：「**该缓冲区地址需要 4 字节对齐**」。示例：`uint32_t tkyBuf[(MAX_QUEUEBUF_LEN-1)/4 + 1] = {0};`

**`TKY_ChannelInitTypeDef`**（第 4 页，照抄）：
```c
typedef struct {
    uint8_t  queueNum;       //--该通道在测试队列的序号--
    uint8_t  channelNum;     //--该通道对应的 ADC 通道标号--
    uint16_t chargeTime;     //--该通道充电时间--
    uint16_t disChargeTime;  //--该通道放电时间--
    uint16_t baseLine;       //--基线--
    uint16_t threshold;      //--阈值--
    uint16_t threshold2;     //--阈值 2--
    uint8_t  sleepStatus;    //--休眠--
} TKY_ChannelInitTypeDef;
```
返回值：`0x00` 成功；`0x01` 触摸通道参数有错；`0x02` 通道转换队列位置错误；`0x04` 基线值设置错误；`0x08` 阈值设置错误。

**→ 与 §4.1 硬件寄存器的对应关系（库文档明写的映射）**：
- `chargeTime` / `disChargeTime`：「当前通道充放电时间，**取值范围参考各芯片手册**」（第 4 页）；`TKY_SetCurQueueChargeTime` 处进一步写「参数值含义请查阅**芯片手册中的寄存器相关参数**」（第 7 页）。
  → 即分别对应 CH32V00X 的 `R32_TKEY_CHG.TKCHARGE[10:0]` 与 `R32_TKEY_DISCHG.TKACT_DCG[10:0]`；在 (b) 型芯片上对应 `TKEY_CHGOFFSET` 与 `TKEY_ACT_DCG`。
- `channelNum`：「触摸按键通道编号，通常也是 **ADC 通道编号**」——对应写入 `ADC_RSQR3[4:0]` 的通道号。
- `baseLine`：「**最大不得超过 4095**，建议通过调整充放电时间，使基线值处于 **3000～3600** 之间」——4095 即 12 位 ADC 满量程，对应 `TKEY_DR.DATA[15:0]` 的有效范围。
- `threshold` / `threshold2`：上升/下降阈值，「当基线值和当前检测值的差值大于/小于该参数值时，则认为有按键按下/释放」——纯软件判决，无对应寄存器。

API 清单（第 5–10 页）：`TKY_GetCurChannelMean`、`TKY_GetCurQueueValue`、`TKY_PollForFilterMode_3`、`TKY_PollForFilterMode_CS10`、`TKY_ScanForWakeUp`、`TKY_SetCurQueueSleepStatus`、`TKY_SetSleepStatusValue`、`TKY_ReadSleepStatusValue`、`TKY_SetCurQueueChargeTime`、`TKY_SetCurQueueThreshold`、`TKY_GetCurIdleStatus`、`TKY_GetCurVersion`、`TKY_GetCurQueueBaseLine`、`TKY_SetBaseRefreshSampleNum`、`TKY_SetBaseUpRefreshDouble`、`TKY_SetBaseDownRefreshSlow`、`TKY_SetFilterMode`、`TKY_ClearHistoryData`、`TKY_SaveAndStop`、`TKY_LoadAndRun`。

**与 ADC 共用的硬约束**（第 9–10 页原文）：
- `TKY_SaveAndStop`：「**保存触摸相关寄存器值**，并且在判断触摸扫描空闲时暂停触摸功能，以**腾出 ADC 模块用于 ADC 转换**」；`TKY_LoadAndRun`：「载入触摸相关寄存器值，并重新启动被暂停的触摸按键功能」。
- 多处「**为确保安全更新设置，请查询空闲状态（`TKY_GetCurIdleStatus`），在空闲时进行更新**」（`TKY_SetCurQueueChargeTime`、`TKY_SetCurQueueThreshold`、`TKY_SetBaseRefreshSampleNum` 等）。
- `TKY_GetCurIdleStatus`：「查询当前 toucnKey 是否空闲状态，**若处于空闲状态，可以切换 ADC 状态**」。
- **返回值位序警告**（多处重复）：「返回值各个位对应各个队列的按键，例如队列 0 的触摸通道有按键，对应最低位置 1。**注意并非 ADC 通道编号**。」

#### 4.2.2 `WCH_touch_V3`（`bf50109705ef8acb` V1.1，18 页）

适用范围（第 1 页）：「本库专为沁恒微电子 **CH585 系列和 CH595 系列**微控制器优化设计」。
→ 与其所在目录 `QingkeV3C_CH587_EVT/EXAM/TOUCH/` 的芯片（CH587）**不一致**；使用前需确认。

队列模型（第 2 页）：`TKY_QUEUE_0` … 共 **24 个**队列 ID（`TKY_QUEUE_END`）。

`TouchKey_CFG.h` 核心配置宏（第 2 页表，照抄）：
`TKY_FILTER_MODE`（滤波模式）、`TKY_FILTER_GRADE`（滤波等级）、`TKY_BASE_REFRESH_ON_PRESS`、`TKY_BASE_UP_REFRESH_DOUBLE`（按键释放基准跌落恢复的刷新加快倍数）、`TKY_BASE_DOWN_REFRESH_SLOW`（按键触发基准向触发方向刷新抑制倍数）、`TKY_BASE_REFRESH_SAMPLE_NUM`、`TKY_SHIELD_EN`、`TKY_SINGLE_PRESS_MODE`、`TKY_TOUCH_QUEUE_NUM`、`TKY_SLEEP_QUEUE_NUM`、`TKY_MAX_QUEUE_NUM`（触摸+休眠）、`TKY_MAX_NOISE_CH_COUNT`、**`TKY_CX_CH_IDX`（外接电容的 adc 通道索引）**。

通道参数宏（第 2 页）：`GEN_TKY_CH_INIT(qNum, chNum, hyswin, chBaseline, maxvar, level)`
- `chNum`：「ADC 通道号**或位掩码**」；`hyswin`：迟滞窗口，库内部软件实现迟滞比较器用于消抖；`chBaseline` 参考基线；`maxvar` 参考最大变化量；`level` 灵敏度等级 **1~10**，值越小越灵敏。

**双队列结构**（第 3 页原文）：
- 触摸队列（单通道检测）：「通过 ADC 通道号方式确定扫描通道……对应配置中的前 `TKY_TOUCH_QUEUE_NUM` 个队列」。
- 休眠队列（多通道组合检测）：「采用**位掩码**方式选择扫描通道；**芯片内部将选中通道连接在一起，可一次扫描多个通道**；主要用于低功耗扫描，降低扫描时间；对应配置中的后 `TKY_SLEEP_QUEUE_NUM` 个队列」。

**阈值计算公式**（第 4 页，照抄符号，PDF 中数学排版部分抽取受损，见 §8）：
```
th = (maxvar * Baseline / chBaseline) * level / 10
```
其中「Baseline：实际应用中上电触摸通道初始化程序校准出来的基线值；value：实际应用中的实际最大变化量；level：灵敏度等级」。原文另给判据：「一般来说（变化率）大于 **5%**，我们认为是一个设计健康的触摸产品。」

典型参数（第 4–5 页，照抄）：
```c
#define TKY_FILTER_MODE              3
#define TKY_FILTER_GRADE             2
#define TKY_BASE_REFRESH_ON_PRESS    0
#define TKY_BASE_UP_REFRESH_DOUBLE   10
#define TKY_BASE_DOWN_REFRESH_SLOW   0
#define TKY_BASE_REFRESH_SAMPLE_NUM  500
#define TKY_SHIELD_EN                1
#define TKY_SINGLE_PRESS_MODE        2
#define TKY_TOUCH_QUEUE_NUM          12
#define TKY_SLEEP_QUEUE_NUM          12
#define TKY_MAX_QUEUE_NUM   (TKY_TOUCH_QUEUE_NUM+TKY_SLEEP_QUEUE_NUM)
#define TKY_MAX_NOISE_CH_COUNT       3
#define TKY_CX_CH_IDX                13
```
通道表示例（第 5 页）：队列 0–11 用裸通道号（`9, 8, 6, 10, 7, 5, 1, 3, 4, 0, 2, 11`），队列 12–23 用位掩码（`(1<<9)`, `(1<<8)`, …）——同一物理通道在两个队列中以两种编码出现。

**与 lite 库的结构体差异**（第 6、8 页）：
```c
// V3 库 TKY_BaseInitTypeDef 相对 lite 库：rfu[2] 被替换为
    uint8_t maxNoiseChCount;   //干扰通道数量
    uint8_t sleepChNum;        //睡眠通道数量
// baseDownRefreshSlow 范围由 0~65535 改为 0~255
// 返回值：0x00 成功；0x01 滤波等级超出上限（最大为 16）
```
```c
// V3 库 TKY_ChannelInitTypeDef —— 与 lite 库完全不同
typedef struct {
    uint16_t queueNum;           //该通道在测试队列的序号
    uint16_t channelNum;         //该通道对应的 ADC 通道标号
    uint16_t hysteresisWindow;   //迟滞比较窗口
    uint16_t baseLine;           //参考基线
    uint16_t maxVar;             //参考最大变化量
    uint16_t sensitivityLevel;   //灵敏度 1~10
} TKY_ChannelInitTypeDef;
```
→ **V3 库取消了 `chargeTime`/`disChargeTime`/`threshold`/`threshold2`/`sleepStatus` 字段**，改由 `CTransN`/`CTransCC` 一对参数在专用 API 中设置：

`TKY_SetCurQueueChargeTime(uint8_t curQueueNum, uint16_t CTransN, uint16_t CTransCC)`（第 11 页）：
- `CTransN`：「转换次数参数，**范围 1~1023**」——对应 §4.1(c) 的 `TRANSN[9:0]`（`TRANSN+1`，最大 1024）。
- `CTransCC`：「转换控制参数，**`CTransCC[1:0]`--控制参数；`CTransCC[15:2]`--保留**」。
  → **注意**：CH32V205 的 `TRANSCC` 是 **3 位**（`[2:0]`，8 档 T2/T4 组合），而 V3 库只暴露 **2 位**。两者不是同一芯片（V3 库面向 CH585/CH595），**无法据此断定是芯片差异还是库文档笔误**。

V3 库独有 API（第 11–13 页）：`TKY_SetGroupCurQueueChargeTime(groupidx, …)`「该函数给每个触摸队列配置**最多四组充电参数**」、`TKY_GetGroupCurQueueChargeTime`、`TKY_SetCurQueueBaseLine`、`TKY_GetCurQueueThreshold`。
`TKY_GetCurChannelData(curChNum, CTransN, CTransCC, scanArray, dataNum)` 取代 lite 库的 `TKY_GetCurChannelMean`（注意：**文档小节标题仍写作 `3.3 TKY_GetCurChannelMean`，正文函数名却是 `TKY_GetCurChannelData`**——文档笔误）。
`TKY_ScanForWakeUp` 签名由 lite 的 `(uint16_t scanBitValue)` 改为 **`(void)`**，返回值语义也变（`0` 不满足唤醒条件 / `1` 满足 / `2` 睡眠通道配置出错）。
`TKY_GetCurVersion`：「例如返回值为 **300**，则代表版本号为 3.0.0」（lite 库为「假设当前版本为 1.03，则输出 103」）。
`TKY_PollForFilterMode_CS10` 在 V3 库中是「**非阻塞**方式轮询，占用 CPU 资源小。需要高频调用」——与 lite 库的「有阻塞式随机延迟(0～8us)」相反。

版本一致性校验（第 7 页示例代码）：
```c
if ( memcmp( TOUCH_VER_LIB, TOUCH_VER_FILE, strlen( TOUCH_VER_FILE ) ) )
{ PRINT( "head file error...\n" ); while ( 1 ); }
```
→ 库与 `TouchKey_CFG.h` 版本不匹配时死循环，属硬失败。

### 4.3 触摸应用指南（两份，内容近同、术语不同）

- `WCH触摸应用指南.pdf`（`9c0f28254428f039`，未标注版本，11 页）
- `WCH_TouchApplicationGuide.PDF` V1.0（`38ebe89c93b5a0aa`，11 页；第 11 页有「第 5 章 修改记录 | V1.0 | 2025.02.12 | 初版发行」）

内容以 PCB/硬件设计为主，寄存器信息极少，但有两条与编程接口相关：

1. **增强功能的术语在两份中不同**：`9c0f28254428f039` 第 2 页作「**驱动屏蔽**和密集模式」，`38ebe89c93b5a0aa` 第 2 页作「**主动屏蔽**和密集模式」。指同一功能。
   支持范围（两份一致）：「低功耗蓝牙系列 CH58x/CH59x 芯片，RISC-V 通用系列 CH32L103 芯片，**CH32V006/CH32V007** 芯片支持驱动屏蔽/主动屏蔽技术；青稞 RISC-V 通用系列、Cortex-M 通用系列、低功耗蓝牙系列**支持密集模式**。」
2. **密集模式的通道代价**（`38ebe89c93b5a0aa` 第 9 页）：「**密集模式需额外占用一个触摸通道**」——即 §4.2.2 中的 `TKY_CX_CH_IDX`（外接电容的 ADC 通道索引）。
   同页：「主动屏蔽……需**通过对应寄存器开启（具体见芯片手册）**。主动屏蔽引脚走线应包裹所有触摸按键走线」——对应 §4.1(c) 的 `R32_DRV_CFG.DRVEN` / `DRVOUTSEL[15:0]`。

检测原理（两份一致，第 2 页）：「沁恒微电子的电容触摸按键检测方案主要为**电流源充电方案**……触摸使能后，该模块对等效电容进行充放电操作……相同的充电时间，通过单片机内部 ADC 采集触摸通道的电压值，与未按下时的值作差，再根据定义的阈值识别按键按下与抬起。」引起的电容变化 `Δ = Cf ≈ 0.1~5pF`。

低功耗触摸（`9c0f28254428f039` 第 3 页）：「RTC 定时唤醒芯片，执行单次按键扫描，若扫描到疑似按键按下，则会执行快速扫描确定按键状态……官方示例中定时时间为 **500ms**……**按键个数以及扫描次数对功耗影响较小，仅唤醒时间间隔对平均功耗有明显影响**。」

### 4.4 3 份 Touch Kit PDF —— 无寄存器/指令内容

`9693ef4c83762e3e`（CH32V00x_Touch_Kit.pdf）、`6544e5b72df170db`（WCH_TOUCH_Kit_EX001.pdf）、`2c860b1092ea0cd3`（WCH_TOUCH_Kit_EX002.pdf）均为 Altium 导出的**单页原理图**，抽取结果为网表标号（`PIRB101`、`COP2`、`SEG_3`、`TS0` 等）。无寄存器、无指令、无 API。本任务不采信其抽取文本，需要引脚级信息时应看原 PDF 图形。

---

## 5. 跨手册差异（判定与说明）

> **判定纪律**：本批 12 份参考手册版本从 **V1.1 到 V2.5** 不等。某寄存器/字段在 A 有、B 无，可能是芯片确实不同，也可能只是 B 手册版本较旧尚未收录。以下每条都同时标出双方版本，并明确归类为「**芯片差异**」「**手册版本差异**」或「**无法区分**」。汇总表见 §7。

判定所用的证据类型：

- **判为芯片差异**：同一份手册内部有交叉印证（如 CH32M030 的信息块表与 ESIG 表都用 `0x1FFFF3xx`）；或差异与首页内核型号表一致（如 V5F 独有缓存 CSR，而 V3F 表中确无）；或手册明写「适用于 XXX 系列/型号」。
- **判为手册版本差异**：新版手册补写了旧版没有的通用章节，且该章节内容与芯片型号无关（如 CSR 身份寄存器组）。
- **无法区分**：既无内部印证也无型号限定语。

三条最重要的结论先行：

1. **CSR 0x804 必须逐芯片手册解释**：X315/V407/H417 三份 RM 列 `HW_POPDM_CTLR`；V003/V00X/CH641/X035/L103/FV2x-V3x/M030/V205 八份 RM 与四本 QingKe core manual 列 `INTSYSCR`；CH32xRM 未检出 0x804 字面量。两组字段语义不同，可判为这些文档所覆盖芯片之间的差异，但不能据此写成无条件的 core-family 规则。这是移植代码时最易踩的一条。
2. **只有 CH32X315RM V1.1 / CH32V407RM V1.1 / CH32H417RM V1.7 列出了 MVENDORID/MARCHID/MIMPID/MISA 等身份 CSR**，其余 9 份（版本 V1.2 ~ V2.5）完全不提。这三份都是较新的青稞 V3F/V3V/V5F 手册。**无法区分**是「V2/V4 核不实现这些 CSR」还是「旧手册未收录」——按 RISC-V 特权规范这些 CSR 是必需的，[推断] 更可能是**手册版本差异**（旧手册未收录），但需实测确认。
3. **TKEY 寄存器集合分四套**，与内核代际无关、与芯片型号强相关（同为 V4C 的 CH32X035 与 CH32L103 就分属两套）——判为**芯片差异**。

---

## 6. 手册自己标注的特殊之处（保留 / 必须写 / 禁止修改 / 魔数 / 批号相关）

### 6.1 「保留，但必须保持特定值」

| 内容（原文） | 手册（版本，sha256 前16） | 页 |
|---|---|---|
| USER `[7:6] Reserved` — **保留（必须为 1）**，复位 `11b` | CH32V003RM V1.9 `7a6bf439ecd68e0b` | 188 |
| `EXTEN_CTLR0 [23:20] Reserved RW` — **保留，写入时必须保持原值 `1010b`**，复位 `0xA` | CH32M030RM V1.2 `109a7bb0ab9a0b70` | 246 |
| `VCONTROL bit8 Reserved URO` — **保留，不可写 0**，复位 `x` | CH32V407RM V1.1 `63625af9027af6ab` | 61 |
| `[3:1] RW` — **保留，必须写入 `110b`**，复位 `110b` | CH32FV2x_V3xRM V2.5 `6bdc58b159a95c40` | 494 |
| `[7:5] Reserved RW` — **保留，Bit5 必须写 0**，复位 `010b`；`bit3 Reserved RW` — **必须写 0** | CH32H417RM V1.7 `b57ebb0c0ae2cd77` | 629 |
| `MEMARY_CFGR [31:20]` — **请勿配置为内部存储器的高位地址（`0x000`，`0x200`，`0x201`）** | CH32H417RM V1.7 `b57ebb0c0ae2cd77` | 62 |
| `0：保留，必须保持复位值` | CH32H417RM V1.7 `b57ebb0c0ae2cd77` | 762 |
| `CACHE_STRTG_CTLR bit0 Reserved RO` 复位值 **1**（非 0） | CH32H417RM V1.7 `b57ebb0c0ae2cd77` | 62 |
| `INTSYSCR [31:6] Reserved URO 保留，复位值 0x380` | CH32M030RM V1.2 `109a7bb0ab9a0b70` | 45 |

> 通用做法：这些位不能用「读-改-写」以外的方式处理，更不能整字写 0。

### 6.2 「厂商配置字：出厂前固化，用户不可修改 / 不可访问」

原文（各手册首页「说明」段与 FLASH 章节脚注）：「内置 N 字节空间用于**厂商配置字存储，出厂前固化，用户不可修改**」；FLASH 组织表脚注：「除了"**厂商配置字**"区域出厂锁定，**用户不可访问**，其他区域在一定条件下用户可操作。」

| 容量 | 手册（版本，sha256 前16） | 页 |
|---|---|---|
| 64B | CH32V003RM V1.9 `7a6bf439ecd68e0b` | 4 |
| 128B | CH32FV2x_V3xRM V2.5 `6bdc58b159a95c40` | 18, 532 |
| 128B（`0x1FFFF380–0x1FFFF3FF`） | CH32M030RM V1.2 `109a7bb0ab9a0b70` | 4, 231 |
| 256B | CH32L103RM V2.2 `27a1b969cb2cb99d` | 6 |
| 256B | CH32H417RM V1.7 `b57ebb0c0ae2cd77` | 7, 865 |

### 6.3 魔数与固定序列

| 魔数 | 用途 | 出处 |
|---|---|---|
| `KEY1 = 0x45670123`, `KEY2 = 0xCDEF89AB` | FLASH_KEYR / FLASH_OBKEYR / FLASH_MODEKEYR / FLASH_BOOT_MODEKEYR 解锁序列；**顺序强制**（原文：「第 1 步必须是 KEY1」「第 2 步必须是 KEY2」） | CH32FV2x_V3xRM V2.5 `6bdc58b159a95c40` 第 538–539、541、543 页；CH32V003RM V1.9 `7a6bf439ecd68e0b` 第 189 页；CH32V00XRM V1.5 `7d216d69fd04d990` 第 218、223 页；CH32L103RM V2.2 `27a1b969cb2cb99d` 第 297 页；CH32X315RM V1.1 `b6a752f9e9bdbb1d` 第 297 页 |
| **同上两个 KEY** 用于 `EXTEN_KEYR`（0x40023804）解锁 EXTEN_CTLR0/1 | 「输入下面序列解锁控制器 0 和 1 的配置操作」 | CH32M030RM V1.2 `109a7bb0ab9a0b70` 第 247 页 |
| `RDPR = 0xA5`（`nRDP` 必须为 `0x5A`） | 解除读保护；**写入该值会先触发整片擦除** | CH32V003RM V1.9 `7a6bf439ecd68e0b` 第 190 页；CH32FV2x_V3xRM V2.5 `6bdc58b159a95c40` 第 544 页 |
| `0x5AA5` | HSEM 解锁关键字（`HSEM_CLR[31:16] CLR_KEY`，`HSEM_KEY[31:16] KEY_VALUE` 复位 `0x5AA5`） | CH32H417RM V1.7 `b57ebb0c0ae2cd77` 第 76 页 |
| `0x5AA55AA5` | 用户选择字快速编程示例：`*(uint32_t*)0x1FFFF804 = 0x5AA55AA5;` | CH32V00XRM V1.5 `7d216d69fd04d990` 第 223 页 |
| `0xe339e339` / `0xe339` / `0x39` / `0xe3` | **擦除后 FLASH 的读出值**（非 0xFF）：「擦除成功后，字读- `0xe339e339`，半字读- `0xe339`，偶地址字节读- `0x39`，奇地址读 `0xe3`」 | CH32FV2x_V3xRM V2.5 `6bdc58b159a95c40` 第 542、544 页 |
| `0xFF` | 同上位置在 CH32V00X 上是「擦除成功后，字读- `0xFF`」 | CH32V00XRM V1.5 `7d216d69fd04d990` 第 222 页 |
| **`0x1FFFF72A`** | 裸地址魔数，无寄存器名、无位域：「HSI 进入内部低功耗模式时要把 `0x1FFFF72A` 地址的值加载到 `HSITRIM[4:0]` 里」 | CH32L103RM V2.2 `27a1b969cb2cb99d` 第 21 页 |
| `0xE339`（FEATURE_SIGN 高 16 位复位值） | 见 §3.2；与擦除值同源 | CH32FV2x_V3xRM V2.5 `6bdc58b159a95c40` 第 547 页 |

> 擦除后读出值 `0xe339e339` vs `0xFF` 是**芯片差异**（两份手册各自内部一致），会直接影响「空白页检测」逻辑。

### 6.4 「上电后需先读取」类

- **`R32_ISINK_ADJ`（0x1FFFF390）**：「`ISINK1_CFGR` **不可读**，改写寄存器时，`ISINK1_ADJ[5:0]` 数值**来自 ISINK 灌电流校准值寄存器**」——必须先读 `0x1FFFF390` 再写配置。出处：CH32M030RM V1.2 (`109a7bb0ab9a0b70`) 第 249 页。
- **`R32_FLASH_CFGR0.DBMODE`**：CH32H417 的用户区/BOOT 区容量「通过 `R32_FLASH_CFGR0` 寄存器 DBMODE 位**读取**」，决定 Flash 页大小（8K vs 4K）、总容量（960K vs 480K）与自动写保护范围。出处：CH32H417RM V1.7 (`b57ebb0c0ae2cd77`) 第 7、865、876 页。
- **`FEATURE_SIGN` 反码校验**：见 §3.2，须先验 `[15:8] == ~[7:0]` 才能采信 `VLEVEL`。
- **`MEMINFO`（CSR 0xFC0）**：运行期读缓存/TCM 规格，不应编译期写死。出处：CH32H417RM V1.7 (`b57ebb0c0ae2cd77`) 第 65–66 页。
- **`nest_max` 写 `11b` 再读回**取芯片最高嵌套等级（§2.2）。

### 6.5 「行为随芯片版本 / 批次不同」—— 批号相关注记

**这是本批手册中最密集的一类陷阱。** WCH 用「批号倒数第 N 位」作为版本判据，共两种句式：「批号倒数第五位」「批号倒数第六位」（CH32FV2x/CH32V407 系）与「批号第五位」（CH32H417/CH32V003/CH32xRM 系）。

CH32FV2x_V3xRM V2.5 (`6bdc58b159a95c40`) 中出现在 **30 余处**页面，覆盖时钟树、DMA、ADC、ETH、USB、SPI、FLASH、EXTEN 等。代表性条目：

| 内容（原文摘） | 页 |
|---|---|
| 「上图 3-4 中蓝色虚线框出来的部分**仅适用于批号倒数第五位大于 0 的 CH32V203RB 芯片**」 | 30 |
| 「批号倒数第五位小于 4 且倒数第六位等于 0 的 CH32V307R，CH32V305R，CH32V305G，CH32V305F，…」 | 124 |
| 「**DMA1 在使用时需注意**，对于批号倒数第五位小于 3 且倒数第六位等于 0 的，DMA1 所有通道……目的地址+传输数据只能在 0-64K，或 64K-128K 区域，**不可出现 63K-65K 类似情况**」 | 148 |
| 「`EXTEN_CTR2` 寄存器**仅适用于** CH32F20x_D8、CH32F20x_D8C、CH32V30x_D8、CH32V30x_D8C、CH32V31x_D8C **批号倒数第六位不为 0 的产品**」 | 547 |
| 「`R32_ETH_MACCFG0` 寄存器**仅适用于批号倒数第六位不为 0 的** CH32F207、CH32V307、CH32V317 产品」 | 474 |
| USER `RAM_CODE_MOD`「`110b` **仅适用于批号倒数第六位不为 0 的产品**」 | 537, 543 |
| SPI 高速读「对于……批号倒数第五位小于 2 的，只支持该模式仅在时钟 2 分频（即 `CTLR1` 寄存器的 `BR = 000`）时有效，其他批次不受限制」 | 319 |

CH32H417RM V1.7 (`b57ebb0c0ae2cd77`) 中的**内核级**批号依赖（最需注意）：

| 内容（原文） | 页 |
|---|---|
| 「注[1]：**仅批号第五位不为 0 的芯片支持内存保护**」 | 1 |
| 「图 3-2 时钟树框图（**仅适用于批号第五位为 0 的芯片**）」/「图 3-3 时钟树框图（**适用于批号第五位大于 0 的芯片**）」——**两张不同的时钟树** | 16, 17 |
| 「（2）**内核 0 的 `TSELECT` 寄存器仅适用于批号第五位不为 0 的芯片**」 | 53 |
| 「（2）内核 0 的 `TDATA1` 寄存器仅适用于批号第五位不为 0 的芯片」 | 54 |
| 「注：内核 0 的 `TDATA2` 寄存器仅适用于批号第五位不为 0 的芯片」 | 54 |
| 「注：**内核 0 的 PMP 功能仅适用于批号第五位不为 0 的芯片**」 | 66 |

CH32V003RM V1.9 (`7a6bf439ecd68e0b`)：
- USER `bit5 START_MODE`：「该功能**不适用于批号倒数第 5 位为 0 的产品**」（第 188 页）。
- SPI 高速读 `HSRXEN`：「……时有效，其他批次不受限制，**该位只写**」（第 176 页，接续第 175 页）。

CH32xRM V2.0 (`b4ade26ba00e0f03`) 第 210 页：「对于**批号第五位≤5** 的只支持该模式仅在时钟 2 分频（即 `CTLR1` 寄存器的 `BR = 000`）时有效，其他批次不受限制，该位只写。」

> **实践含义**：CH32H417 的 V3F 内核上，**PMP 与硬件断点（TSELECT/TDATA1/TDATA2）是否存在取决于批号**。调试器/RTOS 代码不能假定这些 CSR 一定可用，需运行期探测（写后读回）。

### 6.6 其它明确标注的行为限制

| 内容（原文摘） | 手册（版本，sha256 前16） | 页 |
|---|---|---|
| 「在进行 FLASH 相关操作时，**强烈建议系统主频不大于 120M**。若……大于 120M，需注意：首先将 HCLK 进行 2 分频……保证 FLASH 访问时钟频率**不超过 60MHz**（`FLASH_CTLR` bit[25] `SCKMOD`……默认配置为系统时钟的一半）」 | CH32FV2x_V3xRM V2.5 `6bdc58b159a95c40` | 532 |
| 「当修改选择字中的"读保护"变成"非保护"状态时，**会自动执行一次整片擦除主存储区操作**。如果修改"读保护"之外的选型，则不会出现整片擦除」 | CH32V003RM V1.9 `7a6bf439ecd68e0b` / CH32FV2x_V3xRM V2.5 `6bdc58b159a95c40` | 189 / 544 |
| 「对用户选择字进行编程时，**FPEC 只使用半字中的低字节，并自动计算出高字节（高字节为低字节的反码）**」 | CH32V003RM V1.9 `7a6bf439ecd68e0b` | 189 |
| 「LOCK……只能写'1'……**在一次不成功的解锁操作后，直到下次系统复位前，该位不会再改变**」 | CH32V00XRM V1.5 `7d216d69fd04d990` / CH32M030RM V1.2 `109a7bb0ab9a0b70` | 217 / 235 |
| `VCAUSE`/`VTVAL`：「**调试模式将导致异常原因信息丢失，无法在调试模式中使用**」 | CH32V407RM V1.1 `63625af9027af6ab` | 61–62 |
| `nest_ovr`：「此时异常和 NMI 中断正常进入，但是 **CPU 堆栈溢出，不可从此异常和 NMI 中断退出**」 | CH32V407RM V1.1 `63625af9027af6ab` / CH32H417RM V1.7 `b57ebb0c0ae2cd77` / CH32M030RM V1.2 `109a7bb0ab9a0b70` | 71 / 55 / 46 |
| PPB 区域「访问为**固定优先级，V5 内核高于 V3 内核**，须注意带宽限制对 V3 性能的影响」 | CH32H417RM V1.7 `b57ebb0c0ae2cd77` | 45 |
| IWDG 硬件使能：「注：**调试模式下内核停止，看门狗硬件使能将失效**」 | CH32V003RM V1.9 `7a6bf439ecd68e0b` / CH32V00XRM V1.5 `7d216d69fd04d990` | 188 / 223 |
| `TKEY_SR.SCANIF` **RW0**「软件写 0 清除，**写 1 无效**」 | CH32V205RM V1.2 `b1ed9ef040455a1f` | 131 |
| AUTOENx 非自动更新时：「发送端先写状态使能位、后写 `IPC_STS` 的操作顺序**可能引入额外的发送端中断**」 | CH32H417RM V1.7 `b57ebb0c0ae2cd77` | 68 |

### 6.7 手册内部自相矛盾（需实测确认）

**CH32V407RM V1.1 (`63625af9027af6ab`) 的 MISA：表值与字段表不一致。**
- 第 62 页表 9-2：`MISA 0x301 机器指令集寄存器 **0x40B01107**`。
- 第 63–64 页 §9.2.3.5 字段表：`bit12 M ... 复位值 **0**`；`bit5 F ... 复位值 0`；`bit1 B ... 复位值 1`。

`0x40B01107` 的 bit12 = **1**（`0x1107` 的 `0x1000` 位），与字段表所写的 M=0 **矛盾**。首页写该芯片指令集为 `IMACV-X`（含 M），故 **[推断] 字段表的「M 复位值 0」是排版/校对错误，实际 M=1**。同页 F=0 与 `0x40B01107` 一致（bit5=0），无矛盾。
另：首页 ISA 串 `IMACV-X` 不含 B，但 MISA bit1 B=1 且值 `0x40B01107` 的 bit1=1；结合第 57 页「支持……zvbb」（向量位操作子集），**[推断] B 位反映的是标量 Zb* 而非仅 zvbb，但手册未澄清**。编译选项（`-march`）应以实测 MISA 为准，不要照抄首页 ISA 串。

**CH32X315RM V1.1 (`b6a752f9e9bdbb1d`) 的 IWDG 时钟源：同一手册内 3 处对 2 处。**

| 位置 | 表述 |
|---|---|
| p43 第 7 章开篇 | 「IWDG 时钟源来自于 **LSI**」 |
| p43 图 7-1 独立看门狗的结构框图 | 时钟源方框标注 **`LSI (40kHz)`** |
| p15 §3.3.5.3 独立看门狗时钟 | 「如果独立看门狗已经由硬件配置设置或软件启动，**LSI** 振荡器将被强制打开」 |
| p301 `FLASH_OBR` | 「0：IWDG 功能由硬件开启（随 **HSI** 时钟决定）」 |
| p306 用户选择字 USER `IWDGSW` | 「0：IWDG 功能由硬件开启（随 **HSI** 时钟决定）」 |

**结论：以 LSI 为准**（3 处，且框图给出 40kHz 具体频率；p9 亦把 LSI 列为停止模式下可工作模块）。**[推断]** 后两处系从 CH32X035 手册复制——CH32X035 上 HSI 是正确的（该芯片无 LSI，见 §3.3(e) 补注）。影响：按 HSI/1024≈47kHz 估算 CH32X315 的看门狗超时会**偏差约 15%**（LSI 标称 40kHz）。建议实测。

---

## 7. 跨手册差异汇总表

### 7.1 CSR 空间

| CSR 地址 | 名称 A | 出现于（手册 版本 sha256前16） | 名称 B | 出现于 | 判定 |
|---|---|---|---|---|---|
| **0x804** | `INTSYSCR` 中断系统控制寄存器 | CH32V003RM V1.9 `7a6bf439ecd68e0b` p47 · CH32V00XRM V1.5 `7d216d69fd04d990` p58 · CH641RM V1.4 `af83c6fca780cfed` p42 · CH32X035RM V1.9 `c7e301eac4790ca1` p50 · CH32L103RM V2.2 `27a1b969cb2cb99d` p72 · CH32FV2x_V3xRM V2.5 `6bdc58b159a95c40` p109 · CH32M030RM V1.2 `109a7bb0ab9a0b70` p45 · CH32V205RM V1.2 `b1ed9ef040455a1f` p76 | `HW_POPDM_CTLR` 硬件压栈控制寄存器 | CH32V407RM V1.1 `63625af9027af6ab` p67 · CH32X315RM V1.1 `b6a752f9e9bdbb1d` p83 · CH32H417RM V1.7 `b57ebb0c0ae2cd77` p52 | **当前文档覆盖的芯片差异**；字段语义不同，不能外推为无条件 core-family 规则 |
| **0x800** | `GINTENR` 用户模式全局中断使能寄存器 | CH32M030RM V1.2 `109a7bb0ab9a0b70` p45 · CH32V205RM V1.2 `b1ed9ef040455a1f` p75 | `UACCES_MSTATUS` 用户访问机器状态寄存器 | CH32V407RM V1.1 `63625af9027af6ab` p66 · CH32X315RM V1.1 `b6a752f9e9bdbb1d` p82 · CH32H417RM V1.7 `b57ebb0c0ae2cd77` p51 | **仅命名差异**（机制逐字相同，均由 0xBC0 bit5 使能） |
| **0xBC0** | `CORECFGR` 微处理器配置寄存器，复位 `0x00000001` | CH32M030RM V1.2 `109a7bb0ab9a0b70` p45 · CH32V205RM V1.2 `b1ed9ef040455a1f` p76 | `CPU_RUN_CTLR` 处理器运行控制寄存器，复位 `0x00000000` / `0x12370000` / `0x12370300` | CH32V407RM V1.1 `63625af9027af6ab` p70 · CH32X315RM V1.1 `b6a752f9e9bdbb1d` p80 · CH32H417RM V1.7 `b57ebb0c0ae2cd77` p54,60 | **芯片差异**（复位值与字段集均不同；浮点分频字段仅存在于有 FPU 的核） |
| **0xBC1** | `INESTCR`，`NEST_LVL[1:0]` | CH32M030RM V1.2 p46 · CH32V205RM V1.2 p77 | `INEST_CTLR`，`nest_max[1:0]`（V3F/V3V）/ `nest_max[2:0]`（V5F） | CH32V407RM V1.1 p71 · CH32H417RM V1.7 p55(V3F),61(V5F) | **芯片差异**（V5F 嵌套 8 级，字段位宽随之加宽） |
| **0xBC8** | `MIE`，`nest_mie[4:0]` | CH32V407RM V1.1 p72 · CH32H417RM V1.7 p56 · CH32X315RM V1.1 p82 | `MIE`，`nest_mie[8:0]` | CH32H417RM V1.7 p64 (V5F) | **芯片差异**（同上） |
| **0x7C0** | `DBGMCU_CR`（单个） | 除 CH32M030RM/CH32xRM 外全部 | `DBGMCU_CR1` + `DBGMCU_CR2`(0x7C4) | CH32M030RM V1.2 `109a7bb0ab9a0b70` p250 · CH32xRM V2.0 `b4ade26ba00e0f03` p284–285 | **芯片差异**（外设数量不同导致需要第二个寄存器） |
| **0x805/0x806/0x808/0x809** | `VCONTROL`/`VPPADDR`/`VCAUSE`/`VTVAL` | **仅** CH32V407RM V1.1 `63625af9027af6ab` p60–62 | — | — | **芯片差异**（仅 V3V 有向量单元） |
| **0x8C0** | `U_NONS_DLY_0` 延时指令控制寄存器 | **仅** CH32V407RM V1.1 `63625af9027af6ab` p73 | — | — | **芯片差异**（与 dly 自定义指令配套） |
| **0xBC2–0xBC6, 0xBD0, 0xFC0** | 缓存/TCM/内存信息 CSR 组 | **仅** CH32H417RM V1.7 `b57ebb0c0ae2cd77` p57–66（V5F） | — | — | **芯片差异**（同手册 V3F 表 4-5 明确只有 4 个自定义 CSR） |
| **0xF11/0xF12/0xF13/0xF14/0x301** | MVENDORID/MARCHID/MIMPID/MHARTID/MISA | CH32X315RM V1.1 `b6a752f9e9bdbb1d` p74 · CH32V407RM V1.1 `63625af9027af6ab` p62 · CH32H417RM V1.7 `b57ebb0c0ae2cd77` p46 | **未收录** | 其余 9 份（V1.2 ~ V2.5） | **无法区分是型号差异还是手册版本差异**。三份收录者恰为较新的 V3F/V3V/V5F 手册；[推断] 更可能是旧手册未收录（这些 CSR 是 RISC-V 特权规范必需项），需实测 |
| **0x3A0/0x3B0–0x3B3** | PMP 组 | CH32X035RM V1.9 p52 · CH32L103RM V2.2 p73 · CH32FV2x_V3xRM V2.5 p111 · CH32H417RM V1.7 p66 | **未收录** | CH32V003RM V1.9 · CH32V00XRM V1.5 · CH641RM V1.4 · CH32M030RM V1.2 · CH32V205RM V1.2 | **芯片差异**（V2A/V2C 核确无 PMP，与首页内核表一致；V3B 的 CH32M030/CH32V205 未列 PMP —— 此项**无法区分**） |
| **0x009/0x00A/0x00F/0xC20–0xC22** | 向量标准 CSR | **仅** CH32V407RM V1.1 p58–60 | — | — | **芯片差异** |
| **0x320/0xB00/0xB02/0xC00/0xC02** | 计数器 CSR | CH32V407RM V1.1 p69–70 · CH32H417RM V1.7 p57–60 | **未收录** | 其余 10 份 | **无法区分** |
| **0x7A0/0x7A1/0x7A2/0x7A4** | 触发器 CSR（硬件断点） | CH32V407RM V1.1 p66,68–69 · CH32H417RM V1.7 p50,53–54 · CH32X315RM V1.1 p74（表中列 TINFO 0x7A4） | **未收录** | 其余 | **无法区分**；且 CH32H417 上内核 0 的 TSELECT/TDATA1/TDATA2 还**受批号约束**（§6.5） |

**MTVEC(0x305) 的三种位域划分** —— 直接影响向量表对齐要求：

| 划分 | 手册（版本 sha256前16，页） | 对齐要求 |
|---|---|---|
| `[31:2] BASEADDR[31:2]` + `bit1 MODE1` + `bit0 MODE0` | CH32V003RM V1.9 `7a6bf439ecd68e0b` p48 | 4 字节 |
| `[31:2] BASEADDR[31:2]`，**「其中位[9:2]固定为 0」** | CH32M030RM V1.2 `109a7bb0ab9a0b70` p44 · CH32V205RM V1.2 `b1ed9ef040455a1f` p75 | 1KB |
| `[31:10] mtvec_base[21:0]`，「**1kB 对齐**，实际 32 位基地址 `BASE = {mtvec_base,10'h0}`」 | CH32V407RM V1.1 `63625af9027af6ab` p64 · CH32X315RM V1.1 `b6a752f9e9bdbb1d` p76 · CH32H417RM V1.7 `b57ebb0c0ae2cd77` p48 | 1KB |

判定：**芯片差异**。后两种表述等价（都是 1KB 对齐），第一种（CH32V003/V2A）允许 4 字节对齐。链接脚本里的 `.vector` 段对齐必须按目标芯片设定。

MTVEC 的 MODE 位语义在两组间也不同：
- V2/V3B 表述：`MODE1` 「1：按绝对地址识别，支持全范围，但必须跳转；0：按跳转指令识别，有限范围，支持非跳指令」；`MODE0`「1：根据中断编号*4 进行地址偏移；0：使用统一入口地址」。
- V3F/V3V/V5F 表述：`mode1`「1：中断向量表中存放跳转地址；0：中断向量表中存放跳转指令」；`mode0`「1：所有中断/异常独立入口，跳转地址为 `BASE+4*IRQ/EXC ID`；0：所有中断/异常统一入口」。
两者语义一致，仅措辞不同。CH32M030RM V1.2 第 45 页另有一条实用注记：「对于 V3 系列微处理器的 MCU，**启动文件里默认配置了 MODE0 为 1**……**V3B 微处理器既可以是一条跳转指令也可以使用中断函数的绝对地址，默认启动文件中将其配置为绝对地址**。」

### 7.2 系统信息 / 器件标识

| 项目 | 主流值 | 例外 | 判定 |
|---|---|---|---|
| ESIG 基址 | `0x1FFFF7E0/7E8/7EC/7F0`（11 份） | **CH32M030RM V1.2 `109a7bb0ab9a0b70` p229：`0x1FFFF3A0/3A8/3AC/3B0`** | **芯片差异**（同手册 p231 信息块表用 `0x1FFFF3xx` 交叉印证） |
| 用户选择字基址 | `0x1FFFF800`（11 份） | **CH32M030RM V1.2 p240：`0x1FFFF300`** | **芯片差异**（同上印证） |
| 用户选择字第 4 字（0x…80C） | `nWRPR3/WRPR3/nWRPR2/WRPR2`：CH32V00XRM V1.5 p222 · CH32X035RM V1.9 p234 · CH32FV2x_V3xRM V2.5 p542 · CH32H417RM V1.7 p876 | **`Reserved ×4`**：CH32V003RM V1.9 p188 · CH32L103RM V2.2 p306；**表中只列 3 个字**：CH32M030RM V1.2 p240 | **芯片差异**（Flash 容量决定需要几个 WRPR 字节；CH32V003 明写「WRP2：保留；WRP3：保留」） |
| `FEATURE_SIGN` (0x1FFFF7D0) | 仅 CH32FV2x_V3xRM V2.5 `6bdc58b159a95c40` p545,547 与 CH32V407RM V1.1 `63625af9027af6ab` p525 | 其余 10 份无 | **无法区分是型号差异还是手册版本差异**。两份手册版本相差大（V2.5 / V1.1），无型号限定语；[推断] 该寄存器可能是全系通用而旧手册未收录 |
| `R32_ISINK_ADJ` (0x1FFFF390) | 仅 CH32M030RM V1.2 `109a7bb0ab9a0b70` p245 | — | **芯片差异**（ISINK 是 M030 的电机外设特性） |
| `0x1FFFF72A`（HSI 低功耗修正） | 仅 CH32L103RM V2.2 `27a1b969cb2cb99d` p21 | — | **无法区分**（无型号限定语；其它手册的 HSILP 位说明中无此注） |
| 厂商配置字容量 | 64B / 128B / 256B | 见 §6.2 表 | **芯片差异**（各手册首页均按本芯片明写） |
| 擦除后 FLASH 读出值 | `0xe339e339`：CH32FV2x_V3xRM V2.5 p542,544 | `0xFF`：CH32V00XRM V1.5 p222 | **芯片差异**（各自手册内部一致，影响空白检测逻辑） |
| USER `RAM_CODE_MOD` 宽度 | 3 位（[7:5]，5 档）：CH32FV2x_V3xRM V2.5 p542 | **1 位**（2 档）：CH32V407RM V1.1 p523；**无此字段**：CH32V003RM V1.9 p188 · CH32V00XRM V1.5 p222 · CH32X035RM V1.9 p234 | **芯片差异**（有/无可配 CODE/RAM 分割是硬件特性） |
| USER 字节 bit5 语义 | `START_MODE`（V003/641/V00X）· **`RST_PIN_SEL`**（M030）· **`CFGCANM`**（V205/L103）· **`PORCTR`**（CH32x）· Rsvd（X035/X315/H417）· 属 `RAM_CODE_MOD`（FV2x/V407） | 见 §3.3.1 全表 | **芯片差异**（12 份各自表内自洽，且与该芯片外设/引脚一一对应） |
| USER 字节 bit7/bit6 | 多数为 Reserved | **`USARTDLEN` + `USBHSDLEN`**：CH32X315RM V1.1 p306；**`USARTDLEN` + `USBFSDLEN`**：CH32H417RM V1.7 p876 | **芯片差异**（X315 用 USBHS、H417 用 USBFS 下载，与各自 USB 外设一致） |
| USER 字节无 `IWDGSW` 位 | 10 份都有 | **CH641RM V1.4 `af83c6fca780cfed` p157** 与 **CH32M030RM V1.2 `109a7bb0ab9a0b70` p241**：bit0 明写「保留」 | **芯片差异**（两份表内 bit0 逐字写「保留」，非抽取缺失） |
| `IWDGSW=0` 的时钟源 | 「随 **LSI** 时钟决定」（10 份） | **CH32X035RM V1.9 `c7e301eac4790ca1` p234：随 HSI** | **芯片差异（已确证）**：该手册全文无「LSI」，p23 明写 IWDG 时钟源为「HSI 的 1024 分频（47KHz）」，p13/p7 佐证 |
| 同上 | — | **CH32X315RM V1.1 `b6a752f9e9bdbb1d` p301, p306：随 HSI** | **手册内部矛盾**（非芯片差异）：同手册 p43 第 7 章写「IWDG 时钟源来自于 **LSI**」、框图标 **LSI (40kHz)**，p15 §3.3.5.3 写「LSI 振荡器将被强制打开」。**以 LSI 为准**；[推断] 选择字表系从 CH32X035 手册复制而来 |
| `RDPR` 复位值 | `0xA5`（11 份） | **`0`**：CH32xRM V2.0 `b4ade26ba00e0f03` p279 | **无法区分**（同页正文仍按 `0xA5` 叙述，[推断] 为排版遗漏） |
| WRPR 保护粒度 × 字节数 | 1K×2B/16K（V003、CH641）· 1K×4B/65K（V00X）· 2K×2B/64K（L103）· 2K×4B/256K（V205）· 4K×2B/64K（M030）· 4K×4B/480K（FV2x、X315）· 8K 或 4K×4B（H417，随 DBMODE） | — | **芯片差异**（与各自 Flash 容量一致） |
| `FLASH_OBR [9:8]` 字段名 | `FIX_11`：CH32V00XRM V1.5 p217 · CH32X035RM V1.9 p229 | `2'b11`：CH32V003RM V1.9 p183；CH32M030RM V1.2 p235 该位置改为 `0V_CFG`/`RST_PIN_S`/`STOPRST`/`OPTERR` 等 | 前两者**仅命名差异**；CH32M030 为**芯片差异** |

### 7.3 触摸控制器（TKEY）

| 手册（版本 sha256前16） | 章节 | 寄存器集合 | 单元数 | 判定 |
|---|---|---|---|---|
| CH32V00XRM V1.5 `7d216d69fd04d990` p101–103 | 第 10 章 | `TKEY_CHG`(0x…43C) / `TKEY_DISCHG`(0x…44C) / `TKEY_DR`(0x…44C) | 1 | 四套实现互不兼容，均为 **芯片差异**（每份手册按本芯片完整描述，无版本残缺迹象） |
| CH32X035RM V1.9 `c7e301eac4790ca1` p101–104 | 第 11 章 | `TKEY1_CHARGE1`(0x…40C) / `CHARGE2`(0x…410) / `CHGOFFSET`(0x…43C) / `ACT_DCG`(0x…44C) / `DR`(0x…44C) | 1 | 同上 |
| CH32FV2x_V3xRM V2.5 `6bdc58b159a95c40` p187–188 | 第 13 章 | 同 X035，**双单元**：TKEY1 @0x4001240C… + TKEY2 @0x4001280C / 0x40012810 / 0x4001283C / 0x4001284C | **2** | 同上 |
| CH32H417RM V1.7 `b57ebb0c0ae2cd77` p194–195 | 第 13 章 | `TKEY1/2_CHGOFFSET`(0x…43C/0x…83C) / `ACT_DCG` / `DR`（表中未列 CHARGE1/2） | **2** | 同上 |
| CH32L103RM V2.2 `27a1b969cb2cb99d` p126–128 | 第 13 章 | `TKEY_CHGOFFSET`(10 位) / `ACT_DCG`(10 位) / `DR`；**逐通道充电时间写 `ADC_SMPPTR2`** | 1 | 同上 |
| CH32V205RM V1.2 `b1ed9ef040455a1f` p124–131 | 第 13 章 | `TKEY_CTLR`/`TRANS_CFG`/`CAP_CFG`/`DRV_CFG`/`TKEY_CDCC`/`TKEY_SR`/`TKEY_RSQR1-3`，含电荷搬移与电流源双模式 | 1 | 同上 |
| CH32xRM V2.0 `b4ade26ba00e0f03` p110–114 | — | `TKEY_F` / `TKEY_V` 两支 | — | **芯片差异**（该手册首页明写 ARM 支与 RISC-V 支「用法不同」） |
| CH32V003RM V1.9 / CH641RM V1.4 / CH32M030RM V1.2 / CH32X315RM V1.1 | 无 TKEY 章节 | — | — | **芯片差异**（无触摸外设） |

通道数差异（原文）：CH32V205「检测通道复用 ADC 的 **16 个**外部通道」（p124）；CH32X035「复用 ADC 的 **14 个**外部通道」（p101）。**芯片差异**。

**CH32H417 与 CH32X035 的「充电时间」机制不同 —— 判为芯片差异（已交叉印证，非手册漏列）**：

| | CH32X035RM V1.9 `c7e301eac4790ca1` p101–103 | CH32H417RM V1.7 `b57ebb0c0ae2cd77` p194–195 |
|---|---|---|
| 逐通道充电时间寄存器 | 有：`TKEY1_CHARGE1`(0x…40C) / `CHARGE2`(0x…410)，每通道 3 位 `TKCGx` | **无** |
| 0x…43C 寄存器名 | `TKEY1_CHGOFFSET` **充电时间偏移量**寄存器 | `R32_TKEY1_CHGOFFSET` **充电时间**寄存器 |
| 该寄存器有效位宽 | `[7:0] TKCGOFFSET[7:0]`（操作步骤写「低八位有效」） | **`[15:0] TKCGOFFSET[15:0]`**（操作步骤写「**低 16 位有效**」） |
| 总充电时间 | `TKCGx`（ADC 时钟）+ `TKCGOFFSET`（系统时钟） | 仅 `TKCGOFFSET` 一项 |
| 0x…44C 有效位宽 | `[7:0] TKACT_DCG[7:0]` | 「低 16 位有效」 |

判定依据：H417 第 194 页的操作步骤第 3/4 步逐字写「写 TKEY_CHGOFFSET 寄存器，**设置通道的充电时间**（低 16 位有效）」「写 TKEY_ACT_DCG 寄存器，设置放电时间（**低 16 位有效**）」，与表 13-1 只列 3 个寄存器**互相印证**；X035 第 101 页则写「充电周期数为 `TKEY_CHARGE1` 和 `TKEY_CHARGE2` 寄存器中的 `TKCGx[2:0]` 配置值**加上** `TKEY_CHGOFFSET` 偏移量之和」。两份手册各自内部自洽，故判为**芯片差异**而非版本残缺。

> 移植后果：X035 上「每通道不同充电时间」靠 `TKCGx` 实现；H417 上没有这个机制，只能在每次转换前重写 `TKEY_CHGOFFSET`（16 位，粒度更细但需软件逐通道切换）。

**CH32L103 是第三种变体**（出处：CH32L103RM V2.2 `27a1b969cb2cb99d` 第 126–128 页）：表 13-1 同样只有 `TKEY_CHGOFFSET`/`TKEY_ACT_DCG`/`TKEY_DR` 三个，但

- 寄存器名保留「**充电时间偏移量**」（同 X035，异于 H417 的「充电时间」）；
- 位宽是**第三种**：`TKEY_CHGOFFSET` 为 `[9:0] TKEY_CHG[9:0]`、`TKEY_ACT_DCG` 为 `[9:0] TKACT_DCG[9:0]` WO「写放电时间并启动一次 TKEY 通道检测。**单位：系统时钟**」，操作步骤逐字写「（**低 10 位有效**）」；
- **逐通道充电时间不经 TKEY 命名的寄存器，而是直接写 ADC 寄存器**——第 126 页步骤 3 原文：「设置通道的充电采样时间，写 **`ADC_SMPPTR2`** 寄存器，可为每个通道配置不同的充电时间。」

即三家的 `CHGOFFSET`/`ACT_DCG` 有效位宽分别是 **8 位（X035）/ 10 位（L103）/ 16 位（H417）**，且逐通道充电时间的入口分别是 `TKEY_CHARGE1/2`（X035）、`ADC_SMPPTR2`（L103）、无（H417）。三份手册各自内部（表 + 操作步骤 + 位域图）三重自洽，故全部判为**芯片差异**。

### 7.4 触摸库

| 项目 | `WCH_touchkey_lite`（`1d55728072da8f86`，未标注版本） | `WCH_touch_V3` V1.1（`bf50109705ef8acb`） | 判定 |
|---|---|---|---|
| 适用芯片 | CH57x/CH58x/CH59X/CH32V00X/CH32L103/CH32V20X/CH32V30X | **CH585/CH595** | 芯片差异（两个库面向不同产品线） |
| 队列数 | 由 `MAX_QUEUE_NUM` 宏定 | 固定 **24**（`TKY_QUEUE_0` … `TKY_QUEUE_END`） | 芯片/库差异 |
| 通道初始化结构 | `chargeTime`/`disChargeTime`/`threshold`/`threshold2`/`sleepStatus`/`baseLine` | `hysteresisWindow`/`baseLine`/`maxVar`/`sensitivityLevel`（**取消充放电时间与阈值字段**） | 库版本差异（V3 改为由灵敏度等级推导阈值） |
| 充电参数 API | `TKY_SetCurQueueChargeTime(q, chargeTime, disChargeTime)` | `TKY_SetCurQueueChargeTime(q, CTransN, CTransCC)`，另有 `TKY_SetGroupCurQueueChargeTime`（**最多四组**） | 库版本差异 |
| `baseDownRefreshSlow` 范围 | 0～65535 | **0～255** | 库版本差异 |
| `TKY_ScanForWakeUp` 签名 | `(uint16_t scanBitValue)` | **`(void)`**，返回 0/1/2 | 库版本差异 |
| `CS10` 轮询特性 | 「有阻塞式随机延迟(0～8us)」 | 「**非阻塞**方式轮询，占用 CPU 资源小。需要高频调用」 | 库版本差异 |
| 屏蔽功能（`shieldEn`） | 「需要硬件支持……仅 CH58x、CH59x、**CH32V006**、CH32L103 支持」 | 「开启后可显著降低触摸的基础电容」（未限定型号） | 库版本差异 |
| 版本号编码 | 「1.03 → 输出 103」 | 「返回 300 → 版本 3.0.0」 | 库版本差异 |

术语差异：`WCH触摸应用指南.pdf`（`9c0f28254428f039`）用「**驱动屏蔽**」，`WCH_TouchApplicationGuide.PDF` V1.0（`38ebe89c93b5a0aa`）用「**主动屏蔽**」。同一功能的两次改名，**文档版本差异**；两份支持型号列表一致（CH58x/CH59x/CH32L103/CH32V006/CH32V007）。**两份文档的先后顺序无法确定**（`9c0f28254428f039` 无版本号也无修订记录页）。

---

## 8. 未能抽取 / 需人工复核的文档与页码清单

### 8.1 抽取总体情况

19 份 PDF **全部抽取成功**，无失败文档。工具：`/opt/homebrew/bin/pdftotext -layout -enc UTF-8`（另同时生成了无 `-layout` 的 raw 版本用于交叉比对）。产物目录：`/Users/apple/Projects/gccriscv-wch/tmp/wch-evt/eval/appnote-text/`，含 `_manifest.tsv`。

页数与 form-feed 数逐份吻合（见 §0.2/§0.3 表），无丢页。中文与寄存器位域表格（`31 30 29 … 1 0` 表头行、`位/名称/访问/描述/复位值` 四列表）在 `-layout` 模式下**结构完整可读**，本文所有位域表均据此照抄。

### 8.2 逐页扫描结果

对全部 19 份做了「每页去空白后字符数 < 80」的稀疏页扫描，命中项逐一人工核对：

| 文档（版本 sha256前16） | 稀疏页 | 核对结论 |
|---|---|---|
| CH32FV2x_V3xRM V2.5 `6bdc58b159a95c40` | p252 | 表格跨页续行（仅剩「停止。」二字），非抽取失败 |
| CH32H417RM V1.7 `b57ebb0c0ae2cd77` | p414, p676, p779 | 同上，均为寄存器描述续行 |
| CH32L103RM V2.2 `27a1b969cb2cb99d` | p264, p297 | 同上（p297 为 FLASH KEY 序列续行） |
| **CH32M030RM V1.2 `109a7bb0ab9a0b70`** | **p93** | **纯图形页：「图 9-1 高级定时器的结构框图」——无文本可抽，需视觉复核（若需定时器结构细节）** |
| CH32V003RM V1.9 `7a6bf439ecd68e0b` | p72, p176 | 表格跨页续行 |
| CH32V00XRM V1.5 `7d216d69fd04d990` | p197 | 同上 |
| CH32V205RM V1.2 `b1ed9ef040455a1f` | p34, p46, p325 | 同上 |
| CH32V407RM V1.1 `63625af9027af6ab` | p49 | 同上 |
| CH32X035RM V1.9 `c7e301eac4790ca1` | p195 | 同上 |
| CH32X315RM V1.1 `b6a752f9e9bdbb1d` | p84, p99, p111, p297 | 同上 |
| CH32xRM V2.0 `b4ade26ba00e0f03` | p70 | 同上 |
| CH641RM V1.4 `af83c6fca780cfed` | — | 无 |
| WCH_TouchApplicationGuide V1.0 `38ebe89c93b5a0aa` | p11 | 修改记录页，内容完整 |
| 触摸库 3 份文本类 | — | 无 |

### 8.3 明确需要人工 / 视觉复核的条目

| # | 文档（版本 sha256前16） | 页 | 问题 |
|---|---|---|---|
| 1 | CH32M030RM V1.2 `109a7bb0ab9a0b70` | 93 | 纯图形页（图 9-1 高级定时器结构框图），文本抽取为空。本任务不涉及定时器，未复核。 |
| 2 | `WCH_touch_V3库使用说明` V1.1 `bf50109705ef8acb` | 3–4 | **阈值/变化率公式区为数学排版，抽取严重错乱**。原文中变量名被替换成 `!"`、`$%&'%(`、`)ℎ+%,-./0-`、`3ℎ` 等乱码（PDF 内嵌数学字体的字形映射缺失）。本文 §4.2.2 给出的公式 `th = (maxvar*Baseline/chBaseline)*level/10` 是**据上下文的中文说明重建**，**未逐字符验证**。需要精确公式时**必须看原 PDF 第 3–4 页图形**。 |
| 3 | `WCH触摸应用指南` `9c0f28254428f039` | 2 | 电容模型公式区（`C总 = Cp + Cf`）同样有数学字体乱码：抽取为 `# = ! + "`。语义可由上下文确定，符号形式需看原图。 |
| 4 | 3 份 Touch Kit 原理图 `9693ef4c83762e3e` / `6544e5b72df170db` / `2c860b1092ea0cd3` | 全部 | Altium 矢量原理图，抽取结果为网表标号碎片（`PIRB101`、`COP2`、`SEG_3`…），**不可作为引脚/网络信息来源**。需引脚级信息时看原 PDF 图形。 |
| 5 | CH32X035RM V1.9 `c7e301eac4790ca1` | 101 | 「图 11-1 TKEY 工作时序图」的时序波形以 ASCII 形式部分抽出（`TKENABLE` / `TKCLK` / `TKACT` / `tDISCHG` / `tCHG` / `tSTAB` 等标号可读），但**各信号的相对时序关系与边沿位置无法从文本判定**。需要精确时序时须视觉复核。 |
| 6 | CH32H417RM V1.7 `b57ebb0c0ae2cd77` | 16, 17 | 图 3-2 / 图 3-3 两张时钟树框图（按批号第五位分版本）。**图形内容未抽取**。涉及 PLL/时钟源选型时须视觉复核，且必须先确定芯片批号。 |
| 7 | CH32V205RM V1.2 `b1ed9ef040455a1f` | 124–127 | TKEY 电荷搬移/电流源模式的 `t1`~`t5` 时序定义分散在正文与时序图中。寄存器字段（`TKSW`/`TRANSCC`/`TKCC`/`TKCD`）已完整抄录，但 **t1–t5 与各字段的对应关系依赖图形**，本文未给出。 |
| 8 | CH32xRM V2.0 `b4ade26ba00e0f03` | 110, 114 | TKEY_F / TKEY_V 两支的寄存器细节本轮未逐位抄录（该手册同时覆盖 ARM Cortex-M3 与 RISC-V 两条产品线，需先按型号分流）。**属本轮未完成项，非抽取失败。** |
| 9 | CH32X315RM V1.1 `b6a752f9e9bdbb1d` | 43 | 「图 7-1 独立看门狗的结构框图」的时钟源方框文字（`LSI (40kHz)`）**已成功抽出**，是判定 §6.7 矛盾的关键证据之一；但框图其余连线关系未抽取。若要确认分频链细节须视觉复核。 |

**以上 9 条中，属于「明显有表但抽取不可读」的只有第 2、3 两条**（触摸库的数学公式区，PDF 内嵌数学字体字形映射缺失）。其余为纯图形页（1、5、6、9）、非文本源（4）、或本轮范围外未抄录（7、8）。**12 份参考手册的寄存器位域表无一抽取失败。**

### 8.3.1 手册本身的内容缺口 / 自相矛盾（非抽取问题，但同样不可凭上下文猜）

| 文档（版本 sha256前16） | 页 | 问题 |
|---|---|---|
| CH32X315RM V1.1 `b6a752f9e9bdbb1d` | 15, 43 vs 301, 306 | **IWDG 时钟源自相矛盾**（LSI ×3 vs HSI ×2）。已判 LSI 为准，详见 §6.7。 |
| CH32V407RM V1.1 `63625af9027af6ab` | 62 vs 63–64 | **MISA 表值 `0x40B01107` 与字段表「M 复位值 0」矛盾**。已判 M=1，详见 §6.7。 |
| CH32xRM V2.0 `b4ade26ba00e0f03` | 279 | `RDPR` 复位值列写作 `0`，与同页正文及其余 11 份手册的 `0xA5` 不符。**[推断] 排版遗漏**，需实测。 |
| CH32X035RM V1.9 `c7e301eac4790ca1` | 234 | `RST_MODE[1:0]` **只定义 `00` 与 `11` 两档**，未说明 `01`/`10`。无法判断是硬件只有 2 档还是手册省略。 |
| CH32V407RM V1.1 `63625af9027af6ab` | 57–58 | dly / mcpy 两条自定义指令的**字段命名与 RISC-V 惯例不符**（`[6:0]` 标为 `func7`，实为 opcode；`[11:7]` 标为 `func5`，实为 `rd` 位置）。位值本身自洽，详见 §1.1。 |
| CH32V407RM V1.1 `63625af9027af6ab` | 57–58 | dly / mcpy **未给助记符、未给异常条件、未给编译器内建名**。无法直接写内联汇编，需 `.insn` 手工编码。 |
| CH32H417RM V1.7 `b57ebb0c0ae2cd77` | 44 | **WCH-X 扩展指令集只提名，无任何助记符/语义/编码**。 |

### 8.4 本轮未展开（超出任务范围或需要另行取证）

- **青稞处理器手册**（`tmp/wch-evt/manual/`，V2/V3/V4/V5 共 4 份）不在本任务的 19 份材料内，但**自定义指令的权威定义在那里**（本批参考手册中 10 份明确写「可参考 QingKeVx 微处理手册」）。已有预抽取文本 `tmp/wch-evt/eval/manual-text/`，账本见 `wch-doc-provenance.md` §1。若需 XW 压缩指令扩展、缓存操作指令等的助记符与编码，应从那 4 份取证。
- **CH32H417 的 WCH-X 扩展指令集**：本批手册只提名不给编码（§1.2）。
- **CH32V407 dly/mcpy 指令的汇编助记符与编译器内建**：手册未给（§1.1），需查 MounRiver 工具链或 EVT 例程实证。
- §6.7 的两处矛盾需**实测确认**：CH32V407 MISA 读回值（判 M 位）、CH32X315 IWDG 实际计时（判 40kHz LSI 还是 47kHz HSI）。
- §7.1 / §7.2 中标为「**无法区分**」的各项，**结论只能由硬件实测或更新版手册给出**，现列全如下：

| 项 | 涉及手册（版本） | 判不了的原因 |
|---|---|---|
| 身份 CSR（MVENDORID/MARCHID/MIMPID/MHARTID/MISA）在 V2/V3B/V4 上是否实现 | 收录：X315 V1.1 / V407 V1.1 / H417 V1.7；未收录：其余 9 份（V1.2–V2.5） | 三份收录者恰为较新的 V3F/V3V/V5F 手册，既可能是型号差异也可能是旧手册未收录；按 RISC-V 特权规范这些是必需项 |
| 计数器 CSR（0x320/0xB00/0xB02/0xC00/0xC02） | 收录：V407 V1.1 / H417 V1.7；未收录：其余 10 份 | 同上 |
| 触发器 CSR（0x7A0–0x7A2、0x7A4，硬件断点） | 收录：V407 V1.1 / H417 V1.7 / X315 V1.1；未收录：其余 | 同上；且 H417 上内核 0 的这三个还**受批号约束**（§6.5），实现与否本就非全芯片一致 |
| PMP 在青稞 V3B（CH32M030 V1.2 / CH32V205 V1.2）上的有无 | 未收录 PMP 章节 | V2A/V2C 无 PMP 已由首页内核表印证，但 V3B 两份既无 PMP 章节也无「不支持」的明确表述 |
| `FEATURE_SIGN`（0x1FFFF7D0）的适用范围 | 仅 FV2x V2.5 / V407 V1.1 有 | 无型号限定语；可能全系通用而旧手册未收录 |
| `0x1FFFF72A`（HSI 低功耗修正魔数）的适用范围 | 仅 L103 V2.2 有 | 其它手册的 `HSILP` 位说明中无此注，也未说不适用 |
| CH32X035 `RST_MODE` 的 `01`/`10` 两档是否存在 | X035 V1.9 只列 `00`/`11` | 同系列其它芯片（V003/641/V00X/M030）都是 4 档 |
| CH32xRM `RDPR` 复位值 `0` vs `0xA5` | CH32x V2.0 | 同页正文与其余 11 份均为 `0xA5`，疑排版遗漏 |

> 本文所有**未**标「无法区分」的跨手册差异，均已在正文给出该判定所依据的交叉印证（同手册内两处以上互证、或手册明写型号限定语）。
