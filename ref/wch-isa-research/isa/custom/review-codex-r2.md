# WCH 自定义 ISA 独立评审（Codex R2）

日期：2026-08-04（Asia/Tokyo）

范围：`review-wch-custom-isa-prompt.md` 指定的两份成稿、四份素材、provenance、`isa-research-codex/`、census 工具与结果，以及原始 PDF/SDK/归档/对象/ROM/PIOC 产物。

原则：假阴性优先；抽取文本只作检索；版本标签不等于硅片能力；阴性结果必须同时给语料、选择规则和方法限制。

## 1. 结论

### `isa-research-claude/`：修订后 PASS

进入本轮时不能直接 PASS：两份主成稿已基本正确，但三份素材仍保留与现有证据冲突的旧句——原理图被称为“无文本”、D+C+XW 被称为“静默禁用 c.fld”、CSR 0x804 被写成无条件 core-family 规则。本轮先独立复现，再直接修正；最终主成稿、素材和账本的关键范围已一致，没有剩余阻断性返工项。

### `isa-research-codex/` 质量评价

`isa-research-codex/` 的主要修正可靠，特别是 XW 全量编码、PIOC 39/27 覆盖、ELF64 对象漏扫、ROM framing、H417 批号范围、schematic 可读性和 CSR 逐文档账本；不足是若干正确发现没有完全同步回第一轮素材，且它未先发现 `mcpy` 的 rs1/rs3 角色冲突。

## 2. 用户提出的四项裁定

| # | 裁定 | 独立证据 | 为什么旧说法无法确认 / 应如何处理 |
|---:|---|---|---|
| 1 | **确认：IQmath 的 3 库命中记载不可复现，应撤回。** | 新脚本重新发现 40 个物理 IQmath archive、9 个 SHA-256 内容组；整文件重叠搜索小端 `0f70b560`、反向 `60b5700f`，以及每字节偏移、放开 rs1/rs2/rs3 的 `(word & 0x06007fff)==0x0000700f`，三项总数均为 0。 | 旧句没有能回到当前文件的 path/hash/offset/member/section，且目标字节在比 ELF 节更宽的整 archive 搜索中也不存在。保留 `.a` executable-section 的 custom-32 零命中，删除该假阳性故事。 |
| 2 | **确认：12/0/11 是 EVT 口径，不是全语料。** | 不导入旧审计模块，按 SHA-256 在三个 scope 内重分组，再对 187 个代表归档调用 GCC15 `readelf -A`：`xw2p2=62`、`xw2p0=4`、未声明 XW 版本 121；116 组有属性节、71 组无属性节，后者覆盖 167 个物理路径。完整 census 为 311/187。 | 旧成稿把 EVT 的 12 个 `xw2p2` 与全语料混写，还被 4 个 `xw2p0` 直接反证。GCC15 的 `_xw` 规范化结果和 `__riscv_xw=2000000` 只能证明当前工具链标签行为，不能证明硬件 2.0 语义。 |
| 3 | **确认：CH587 ROM 的 `mcpy` 是必须处理项。** | 对原始 `CH587BLE_ROMx.hex` 直接反汇编：`0x40960/62/64` 检查三参数非零，`0x40966 add a2,a2,a1`，`0x40968 50b6700f mcpy a2,a1,a0`，随后 `ret`。 | “custom-32 可以先不管”只有在“仅重写已统计的 `.a` 且排除 ROM/独立对象”时成立。原句缺失 ROM 范围警示，会造成真实指令漏实现。 |
| 4 | **确认：V407RM 的 rs1/rs3 地址角色文字与已出货接口冲突，固定编码骨架并未互证语义。** | 新探针在 GCC12/GCC15 都生成 `mcpy a0,a1,a2 = 0x60b5700f`，字段 rs1=10、rs2=11、rs3=12。V407RM PDF p58 写 rs1=目标、rs2=起始、rs3=结束；四份 `ASM_MCPY(DA,SA,EA)` 都发射 `mcpy EA,SA,DA`，CH587 ROM 也构造 EA 后使用同一顺序。 | assembler 只能确认文本操作数进入哪些 bit field，不能确认地址角色。当前重写应采用 SDK/ROM 的 rs1=EA、rs2=SA、rs3=DA，并把手册角色文字列为疑似互换；交换 rs1/rs3 有向错误地址写入的数据破坏风险。尚无硅片实验把这个判断提升为硬件语义定论。 |

## 3. 本轮新增发现与修复

1. `wch-evt-pdf-instr-reg-index.md` 把 schematic/PCB 写成“无文本、纯图形”。直接 SHA 盘点为 13 个物理文件/11 个内容组；各组可抽 18–125 个 pin/mux token，代表页可读 `PA13/SWDIO`、`PA4/ADC4/OP3_O1/DAC1`、`PIOC_IO0/1` 等。已改成：限定寄存器/地址正则为 0，不作全页图形阴性证明。
2. `qingke-custom-isa.md` §7.3 仍写 D+C+XW “静默禁用”。新失败探针显示 `-march=rv32imafdc_zicsr_xw` 下 `c.fld fa0,0(a1)` 明确报 `illegal operands`；已改成精确诊断。
3. `qingke-custom-isa.md` 与 `wch-doc-instr-reg-findings.md` 仍把 CSR 0x804/0xBC0 按 core family 普遍化。原始 PDF 只支持逐文档集合：X315/V407/H417 为 `HW_POPDM_CTLR`；八份其他 chip RM 和四本 core manual 为 `INTSYSCR`；CH32xRM 没有 0x804 literal。相关标题、总表、结论和差异表已改为逐文档限定。

历史 `isa-research-review-codex-followup.md` 保留原貌作为 REWORK 过程记录，不用它代表最终材料状态。

## 4. 亲手复现记录

### 4.1 XW、F/D/Zcb 与 SP 形式

新增 probe 同时汇编：

```asm
c.lbu   a0, 0(a1)
c.lhusp s0, 30(sp)
c.shsp  a5, 30(sp)
c.flw   fa0, 0(a1)
mcpy    a0, a1, a2
```

GCC12、GCC15 在 `rv32imafc_xw/ilp32f` 下均 exit 0，`.text` 都是：

```text
88 21  a0 87  fc 87  88 61  0f 70 b5 60
```

对应 `c.lbu=0x2188`、`c.lhusp=0x87a0`、`c.shsp=0x87fc`、`c.flw=0x6188`、`mcpy=0x60b5700f`。这同时确认 Q0/f3=4 SP 形式、半字立即数乱序和 F+C+XW 可共存。

同一 `c.lbu a0,0(a1)`：XW 为 `0x2188`，GCC8 objdump 按 D 槽显示 `c.fld fa0,0(a1)`；GCC15 Zcb 为 `0x8188`。因此 D 是同槽冲突，Zcb 是同名异码，不可混为一个结论。

### 4.2 XW 标签透传

对同一源分别使用 `_xw`、`_xw2p2`、`_xw3p0`，三次均 exit 0、字节均为 `88 21`；`readelf -A` 分别记录 `xw1p0/xw2p2/xw3p0`。全量复跑还覆盖 GCC12/GCC15 × 五标签，每次 8,704 个不同 halfword、0 mismatch。

### 4.3 census、自测与二进制边界

完整 census 写到 `/tmp/review-r2-census`，没有覆盖仓库结果：

```text
files=311 groups=187 members=1177 bytes=3350246 insns=1137897
summary_total=1137897 coverage_groups=187
rvc 27 OK; rv32 97 OK; xw 16 OK
GetChipID: lui lhu andi c.jr; control OK
```

重新运行五个 `round2_*_audit.py` 与 touch 检查均 exit 0：XW 19,344；归档 objdump 指令行 1,137,897，non-XW unresolved=0，`0x0000=198`；独立 RISC-V `.o=822`；PIOC 66 个手册规则、样本覆盖 39、未覆盖 27，7,307 条非 DW failure=0。

### 4.4 原始 PDF 与 schematic

直接对原始 PDF 使用 `pdftotext -f/-l -layout`，并查看既有渲染页：

- QingKe V3 p55：delay 的 imm/rs1/match/div/sel/低 7 位表。
- CH32V407RM p58：mcpy 固定位、rs1/rs2/rs3 字段与冲突的地址角色文字。
- X315/V407/H417 的 0x804 页：`HW_POPDM_CTLR`；V003 和 QingKe V2 的对应页：`INTSYSCR`。
- CH587、V407、H417QEU 代表 schematic：pin/mux 文本可读。

## 5. 覆盖与全称句审计

- PDF：4 本 core manual/167 页；13 份 application notes/4,373 页；EVT 109 个物理 PDF、81 个内容组、855 个去重页。所有组做文本/页级查询，高风险页和代表图做视觉检查；不声称 4,500+ 页逐页人工目检。
- 二进制：311 个物理 `.a`/187 组/1,177 ELF member；1,108 个独立 `.o` 中 822 个 RISC-V；5 个 ROM HEX；40 个 IQmath archive。
- PIOC：30 ASM（15 程序 + 15 EQU-only include）、15 组 LST/BIN/C array。
- 对两份成稿、四份素材和 Codex findings 重搜“不存在/全部/没有任何/均无/零命中/全语料/可以先不管/无文本”。最终全称句均邻接语料或方法边界；历史 REWORK 报告中的旧问题描述不视作现行结论。

## 6. 仍无法确认的 8 项，以及原因

| # | 仍无法确认 | 原因 / 需要的新增证据 |
|---:|---|---|
| 1 | XW Q0/funct3=4 剩余 1,536 个 pattern 的硬件合法性，以及 1.0/2.0/2.2 同码语义差异 | GAS 无助记符、语料零命中和标签同字节都只是软件/样本阴性；需要供应商规格或多版本硅片行为测试。 |
| 2 | custom-0/1/2/3 未命名 header 的真实实现与异常行为 | `.insn` 接受只证明可发射任意字节，objdump raw 只证明未命名；需要硬件执行、异常记录或官方 decoder 规格。 |
| 3 | `mrsl/mrslu/wexti` 的完整语义、适用芯片和版本矩阵 | 当前只有 SDK 接口、assembler/decoder 编码和简短 MRS 线索，没有完整手册语义或跨芯片实测。 |
| 4 | delay 的 sel=1/rs2 精确布局、时序、跨核一致性，以及它与 WCH-X/MRS 的集合关系 | 手册位表没有闭合 sel=1 的所有操作数字段，当前工具链也无官方助记符；需要更完整手册或硬件 timing test。 |
| 5 | `mcpy` 的区间端点、完成时 SA/DA、粒度、可中断性、跨芯片对齐行为和 SDK 顺序的硅片确认 | V407RM 只给概述/位表且角色文字冲突；SDK/ROM 足以指导兼容顺序，但不是硅片语义测试。 |
| 6 | ROM 中 `0x5f9b34fb`、`0x3b352f2b` 等 data-like custom-major 词是否可达 | HEX 混合 code/data 且缺完整符号、段图和 CFG；需要供应商 code/data map、符号文件或可靠控制流恢复。已确认的 `mcpy@0x40968` 不受此项影响。 |
| 7 | 27 个无样本 RISC8B 格式的 WASM53B 动态接受，以及 PIOC 多字节原子性/精确 cycle 相位 | macOS 未运行 Windows `WASM53B.EXE`；手册只闭合单寄存器优先级、握手和部分单周期 bit transfer。需要原工具动态组装、更多样本或硬件时序测试。 |
| 8 | `tmp/wch-riscv` 514、MRS 19、`tmp/upstream` 3 个仅盘点 PDF 的逐页内容 | 当前只完成路径/数量盘点，未做与主语料同等级的逐页文本和视觉审阅；它们仍是明确覆盖盲区。 |

## 7. 可复现产物

```text
tmp/isa-research-codex/review-r2-independent.py
  sha256 1d792fdedb2979f28b5e9c6d07d45e1023dd6d0861b0c6ffca34ab8daf0ce5b8
tmp/isa-research-codex/review-r2-independent.json
  sha256 9c13ef9e9140016840f75ba4e5adb8a50dffbaf94b46a2e1d9705854ff327a23
```

独立脚本不导入旧 census/round2 模块，重新发现归档、按 scope 做 SHA-256 分组、通过外部 `readelf -A` 读取属性，并对整 IQmath archive 做字节搜索。运行：

```sh
python3 tmp/isa-research-codex/review-r2-independent.py
python3 audit-report-f/followup/tools/isa_census.py selftest /tmp/review-r2-selftest
python3 audit-report-f/followup/tools/isa_census.py control
python3 tmp/isa-research-codex/round2_verify.py
```

## 8. 值得保留的优点

1. RISC-V 与 RISC8B/PIOC 的体系、单位和重写决策已分开。
2. XW 的 SP 槽、乱序立即数、D/Zcb 冲突和版本差集效力边界足以直接转成 decoder 测试。
3. `.a`、独立 `.o`、ROM 和原始 archive 字节搜索分层报告，避免把局部零命中扩大成“硬件不存在”。
4. `mcpy` 的编码骨架、接口顺序和手册角色冲突现在分开陈述，明确标出数据破坏风险。
5. PIOC 把“手册 66”与“样本 39/未采样 27”分开，并保留 OTP/NOP 补丁位约束。
