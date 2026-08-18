# WCH 自定义 ISA：第二轮独立复核结果

日期：2026-08-03（Asia/Tokyo）

本报告重新审计 `research-wch-custom-isa-prompt.md` 的 A–F 项，并把第一轮 `findings.md` 仅作为待证伪线索。机器可读账本是 `tmp/isa-research-codex/round2-{xw,custom,binary,pioc,doc}-audit.json`；逐项闭环见 `round2-review.md`。

证据标签沿用任务定义：【手册】一手 PDF；【实测】本轮可重跑命令；【SDK】随包源/产物；【规范】RISC-V 编码规范；【推断】仅能由现有证据推导、尚缺硬件确认。

## 1. 执行摘要

相对第一轮，本轮得到 **新增 8 项、修正 13 项、仍无法确认 8 项**。最重要的三项是：

1. 【手册】第一轮漏掉了 `QingKeV3_Processor_Manual.PDF` V1.5、SHA-256 `fcc16b54d8818b04b9f8a7a7fbce6c504b87ca3787f0933edecc4da7112438d5`、PDF p55（印刷 p54）的完整 custom-delay 编码表。因此“只有 CH32V407RM 给出 32-bit custom 编码”错误。
2. 【实测】PIOC 的“253 个 unknown”是分类器错误：241 个是合法 `d=0` byte-op，12 个是显式 `DW 0x0fff`；15 个 LST 中 7,307 条非 `DW` 指令全部符合对应手册 mask。实际只覆盖 66 个格式中的 39 个，另外 27 个仍无随包样本。
3. 【实测】归档、独立 `.o` 与 ROM 的边界已重做：187 个去重归档直接反汇编复现 1,137,897 条及 `0x0000` 198 次；独立 RISC-V `.o` 是 822 个而非 466 个；ROM 旧候选 `0x07f805fb` 位于 12-byte 指令内部，只有 CH587 `0x40968: 50b6700f mcpy a2,a1,a0` 具备清楚的局部执行流证据。

## 2. 新增发现（8 项）

### 2.1 QingKe V3 本身给出完整 delay 编码

【手册】`tmp/wch-evt/manual/QingKeV3_Processor_Manual.PDF` V1.5（hash 如上）PDF p55（印刷 p54）给出：`[31:20]=imm`、`[19:15]=rs1`、`[14:12]=001b`、`[11:9]=match`、bit 8=`div`、bit 7=`sel`、`[6:0]=0001011b`。页面已用 `pdftoppm` 渲染为 `tmp/isa-research-codex/round2-doc-pages/qingkev3-55.png` 并视觉核对。

【手册】【规范】该 PDF 把 `[6:0]` 标为 `func7`；按标准 32-bit 指令字段术语，它处于 opcode 位置。报告保留手册原标签，同时不把这个标签误当作标准字段名。

### 2.2 V3B 的 MRS 与 V3B/C 的 memory-copy 线索

【手册】同一 QingKe V3 V1.5：PDF p2（印刷 p1）明确列出八个 XW 助记符，并注明 V3B/C 支持内存拷贝指令；PDF p54（印刷 p53）把 `MRS（移位乘法自定义指令）` 只列在 V3B 栏，且写明 `mimpid[7:0]=3` 新增自定义延时指令。这里没有给 MRS/memory-copy 的完整 bit table，因此只能作为型号/功能线索，不能据此等同 `MRS` 与工具链的 `mrsl/mrslu`。

### 2.3 XW 的两代、五标签全量结果

【实测】`round2_xw_audit.py` 用独立 encoder/decoder 生成每个标签全部 8,704 个合法源组合，并分别交给 GCC12/GCC15 assembler。`xw`、`xw1p0`、`xw2p0`、`xw2p2`、`xw3p0` 共 10 次全量运行、87,040 个 case，均为 8,704 个不同 halfword、0 mismatch、同一 stream SHA-256 `d3a6a0647389d3aee2661916eb420ca58da4a29b8e59bdfb3626b8c810651a05`。

| 指令 | 数据/基址 | 合法 offset | 每条不同词数 |
|---|---|---:|---:|
| `c.lbu` / `c.sb` | x8–x15 / x8–x15 | 0–31 | 2,048 |
| `c.lhu` / `c.sh` | x8–x15 / x8–x15 | 偶数 0–62 | 2,048 |
| `c.lbusp` / `c.sbsp` | x8–x15 / sp | 0–15 | 128 |
| `c.lhusp` / `c.shsp` | x8–x15 / sp | 偶数 0–30 | 128 |

【实测】`c.lhusp/c.shsp` 的非线性 immediate 映射也逐词验证：`uimm[1..3]→instr[8..10]`，`uimm[4]→instr[7]`。本地 `tmp/wch-riscv/port/binutils/include/opcode/riscv-opc.h`（SHA-256 `fd8f85375f85fb092fff0f21fbee8030688a1eda8db95eebe2afea5b97228b4f`）中的八组 match/mask 与独立常量完全一致。

【实测】工具链接口并不完全一致：GCC15 `-march=help` 列出 `xw 2.0`，把 `rv32imac_xw` canonicalize 为 `rv32imac_zmmul_zaamo_zalrsc_zca_xw`，宏 `__riscv_xw=2000000`；GCC12 不支持 `-march=help`，保留 `rv32imac_xw`，宏为 `0`。这是版本接口差异，不是已观察到的编码差异。

### 2.4 `xw2p2` 的 1,971 个词已有完整操作数分布

【实测】对 311 个物理归档按三个来源各自 SHA-256 去重为 187 组，fresh ar/ELF parser 在所有 `SHF_EXECINSTR` section 中得到 `xw2p2` 62 个使用组、11,633 次、1,971 个不同词：

| 助记符 | 次数 | 不同词 |
|---|---:|---:|
| `c.lbu` | 5,177 | 686 |
| `c.lhu` | 2,141 | 483 |
| `c.sb` | 2,473 | 371 |
| `c.sh` | 1,062 | 280 |
| `c.lbusp` | 134 | 23 |
| `c.lhusp` | 56 | 29 |
| `c.sbsp` | 373 | 58 |
| `c.shsp` | 217 | 41 |

【实测】最高频完整 tuple 是 `c.lbu x15,13(x15)` 124 次；明显集中的 SP tuple 包括 `c.lbusp x10,15(sp)` 55 次和 `c.shsp x15,8(sp)` 94 次。完整 data/base register、immediate 和 top-tuple histogram 在 `round2-xw-audit.json`，不能仅凭集中度推导特殊硬件语义。

【实测】同一 187 组的正确指令边界上，q0/funct3=4 中不属于四个 SP 形式的候选为 0；这个阴性结果只覆盖该归档语料。剩余 1,536 个 bit-pattern 没有八个 GAS 助记符映射，不等于硬件非法。

### 2.5 PIOC：66 格式账本与实际覆盖边界

【手册】`CHRISC8B.PDF` v2B、SHA-256 `38231bec89ea50abb7273c76f8d84adfdd0557829628ece8be8bf752e78281f5`、10 页给出 66 个 16-bit 格式。【实测】第二轮为 66 个格式逐条建立 mnemonic-specific mask；15 个随包 LST 的 7,307 条非 `DW` 行全部匹配其助记符格式，failure=0、unknown mnemonic=0。样本只实际出现 39 个格式；`BG1F/BP1F/CLRWDT/.../WRCODE` 等 27 个无样本，故不能宣称“66 条均被 assembler 动态验证”。

【实测】30 个 `.ASM` 已全部盘点：15 个程序源 + 15 个 `PIOC_INC.ASM`；后者在本语料中是 EQU-only SFR/bit 定义，指令发射为 0。15 个程序的 source mnemonic 序列与 LST 15/15 一致。

### 2.6 PIOC：同址写优先级与 DATA_EXCH 边界

【手册】`PIOC-EN.pdf` V1.0、SHA-256 `d8b62cd7359d53c123e52e249abc135cfa75a756833b38ca9d0e50818fcd56f4`：PDF p3 明确同一 SFR 同时写时 host 优先、eMCU 写被丢弃；p10 明确 `SB_DATA_SW_MR`/`SB_DATA_MW_SR` 的置位与消费后清零；p12 明确共享 `SFR_DATA_*` 同样由 host 写优先，且 `SFR_DATA_EXCH` 支持 one-cycle bit-transfer instruction。p3/p4/p10/p12 均已渲染并视觉核对。

【推断】这些文字足以回答冲突优先级和两个 CTRL 寄存器的 ready/consume 方向，但不足以证明多字节事务原子性、host 总线与 eMCU cycle 的精确相位关系或端到端延迟。

### 2.7 独立 `.o` 中此前漏掉 96 个 ELF64 RISC-V

【实测】fresh ELF32/ELF64 parser 扫描 MRS240 的 752 个和 MRS2.5 的 356 个独立 `.o`：1,108 个物理文件中 822 个为 little-endian `EM_RISCV`，其中 ELF32=726、ELF64=96，SHA-256 内容组 506。它们均位于 CRT/start 路径；全部 executable sections 共 52,200 bytes、14,982 个 frame，XW 42 次，目标 custom-major/mcpy 为 0。

【实测】这是“这些 822 个 RISC-V `.o` 的 executable `SHT_PROGBITS` sections 内未发现目标 32-bit raw pattern”，不是“所有独立对象/所有代码都不存在 custom 指令”。

### 2.8 ROM 必须处理 6–14 byte 指令前缀

【实测】5 个物理 ROM HEX 对应 3 个内容组，Intel HEX checksum 全通过。按 RISC-V 变长 framing，CH587 镜像实际遇到 6/10/12/14-byte 前缀，normal 镜像遇到 6/8/10-byte，mesh 镜像遇到 6/10-byte。第一轮固定按 2/4 byte 推进会失同步。

【SDK】【实测】CH587 ROM（SHA-256 `34f1d44af3e418d8825e5e2e63989c9566ed06a98942ddac7364ee53978e903d`）`0x40968` 位于三个非零参数检查、地址加法和 `ret` 之间；GCC15 objdump 直接显示 `50b6700f mcpy a2,a1,a0`。这是预构建真实产物中最强的 named-custom 使用证据。

【实测】同镜像旧候选 `0x07f805fb@0x6b8d4` 是 12-byte 指令内部的 2-byte 重叠窗口，已撤销。正确线性 framing 还在三组 ROM 的明显 data-like 重复区看到 `0x5f9b34fb`、`0x3b352f2b` 等 custom-major 词；因 HEX 混合代码/数据且无完整 map，这些只记 fingerprint，不称指令。

## 3. 对第一轮的修正（13 项）

| # | 第一轮表述/方法 | 第二轮可保留的精确版本 |
|---:|---|---|
| 1 | CH32V407RM 是主要手册中唯一给 32-bit custom 编码者 | QingKe V3 V1.5 p55 已给完整 delay；V407 p57–58 另给 delay/mcpy。 |
| 2 | `.insn r` 已测 5×8×128=5,120 | 第一轮只固定 `funct7=0` 测 40；第二轮才实际组装全部 5,120，两个 assembler mismatch=0。 |
| 3 | 3,178,496 个 named custom 词已穷举 | 该数是 `3×32^4+32^3` 的字段独立性推断；第二轮实际组装的是覆盖每对 operand 的 20,650 个 pairwise case。 |
| 4 | version tags 完全一致 | 第一轮只抽 8 点/标签；第二轮对两代、五标签各自全 8,704 点后才成立。 |
| 5 | PIOC raw classifier 有 253 unknown | 241 个是合法 `d=0` byte-op（ADD 177、IOR 31、INC 21、XOR 6、AND/SUB 各 3），12 个是显式 `DW 0x0fff`。 |
| 6 | `MOVA=182, RETURN=3`，`0x0000` 可计 NOP | `RETURN:` 是 3 个 label；正确为 `MOVA=185, RETURN=0, RET=78`。18 个 `DW 0x0000` 是数据，不计 NOP。 |
| 7 | 1,108 个 `.o` 中仅 466 个 RISC-V | 正确为 822（726 ELF32+96 ELF64）；旧 parser 漏掉 ELF64/扩展布局。 |
| 8 | “unknown 只有 0x0000×198”未能独立复现 | 现已对 187 个真实代表归档逐个直接 objdump：1,137,897 行；未命名非 XW=0，未命名 XW=12,112，`0000 c.unimp`=198。 |
| 9 | ROM `0x07f805fb@0x6b8d4` 是 custom 候选 | 它在 12-byte 指令内部；只能作为重叠字节 fingerprint，不能算 instruction boundary。 |
| 10 | “custom-32 全语料零使用” | 187 个归档和 822 个独立 `.o` 的限定 executable-section 扫描为 0；CH587 ROM `0x40968` 明确有 `mcpy`，所以全局说法错误。 |
| 11 | 批号第五位决定 PMP 与全部硬件断点 | H417 p1 只条件化 memory protection；p53–54 条件化 core-0 的 TSELECT/TDATA1/2，而 core 1 恒有四通道 trigger。 |
| 12 | CSR `0x804` 可按 V3F/V3V/V5F 统一命名 | 必须逐文档限定：X315/V407/H417 为 `HW_POPDM_CTLR`；8 本其他 chip RM 和 4 本 core manual 为 `INTSYSCR`；CH32xRM 文本无 literal hit。 |
| 13 | 11 份 schematic/PCB PDF “抽取不可读” | 13 个物理文件/11 内容组都可抽出大量 pin/mux label；限定 register/address regex 为 0，但未逐页人工证明完全无图形寄存器信息。 |

## 4. 证据加强

### 4.1 32-bit assembler/decoder 命名边界

【规范】【实测】`custom-0/1/2/3` major opcode 是 `0x0b/0x2b/0x5b/0x7b`；`0x0f` 是标准 MISC-MEM major。第二轮仍按任务要求把五者一起测试，但不再把 `0x0f` 错叫 custom major。两代 assembler 对 5 opcode×8 funct3×128 funct7、固定 x1/x2/x3 的 5,120 个 `.insn r` 全部接受且字节相同；directive 接受不证明硅实现。

【实测】named custom 的 pairwise 覆盖为 `mcpy=2,977`、`wexti/mrslu/mrsl` 各 5,891，共 20,650 个不同词、两代 mismatch=0。由字段独立性推得完整可命名 Cartesian namespace 3,178,496；该数明确标为【推断】，没有假装实际组装全部词。

【实测】对五个 opcode 的全部 funct3/funct7，并让 rd/rs1/rs2 各自单轴遍历 0–31，共反汇编 481,280 个不同词。两代结果除 raw 打印名 `.4byte`/`.insn` 外一致：`mcpy=32`，`wexti=mrslu=mrsl=3,008`，其余 472,224 保持 raw。这个 sweep 仍可能漏掉“必须两个以上非基线寄存器同时满足”的隐藏 decoder pattern，且不能证明硬件语义。

### 4.2 SDK 内联汇编与 delay 宏边界

【SDK】【实测】在 `tmp/wch-evt/evt` 下 24,225 个 `.c/.h/.cpp/.hpp/.s/.asm/.inc`、325,361,674 bytes 范围：精确命名词共 20 个文本行、其中 10 个 asm code line，分布在 4 个 `core_riscv.h`；`.insn` 只有 3 行（CH587 mcpy 一行、V407 delay 两行）。1,732 个数值 `.word/.4byte/.long` operand 经只解析 directive operand 的过滤后，目标 major/mcpy literal 为 0。这个阴性结果不覆盖宏计算、链接库、ROM 或逐字节编码。

【SDK】【实测】V407 `DelayIntrisic` 的条件是 `__builtin_constant_p(imm) && imm < 0xFFFu`。无符号常量 2048–4094 因被送入 I-type immediate 而在两代 assembler 都失败，共 2,047 个值；2047 成功，4095 因不满足 `<0xFFF` 转入 register form 而成功。该结论是 SDK 宏的 compile-time bug/限制，不是 delay ISA 只支持 11 bit。

### 4.3 归档 census、section 与 unknown

【实测】三个来源物理归档为 EVT 49、MRS240 168、MRS2.5 94，共 311；分别按 SHA-256 去重为 23+100+64=187 组，RISC-V ELF member=549+332+296=1,177，exec bytes=3,350,246，RISC-V framing=600,671 个 16-bit +537,226 个 32-bit=1,137,897。

【实测】GCC15 objdump 对 187 个真实 archive 直接执行 `-d --disassemble-zeroes -Mno-aliases,numeric`，instruction line 同为 1,137,897；12,112 个 raw 未命名 halfword 全落入八个 XW mask，除此之外 unresolved=0，`0x0000` 198 次。objdump 命名仍不能发现“硬件把标准外观编码重定义”的情况。

【实测】物理归档中 `.highcode` 精确名 67 次、`.highcode*` family 220 次，220 次全有 `SHF_EXECINSTR`；扫描器按 flag 而非只按 `.text`，因此覆盖这些 section。限定的 code-looking/non-exec 名称 heuristic 未见候选；它不是任意自定义 section 的完备语义分类。

### 4.4 PIOC 产物链和直方图

【SDK】【实测】15 个 LST banner 均为 `MCU CH53X ASSEMBLER: WASM53B Ver 3.1`、build `B211121`、info/warning/error=`0/0/0`。ASM→LST mnemonic 15/15；按 `P=` 地址补三份 RGB1W 各 3 个 ORG 零词后 LST→BIN 15/15；C `PIOC_*CODE` array→BIN 15/15；BIN/C 总词数均为 7,346。`WASM53B.EXE` 没有在 macOS 执行，故这里只是随包产物的静态闭环。

【实测】非 `DW` top histogram 为：CALL 979、NOP 865、BTSC 555、WAITB 549、BS 506、BC 477、MOV 408、JMP 341、CLR 288、JNC 247、BTSS 245、MOVL 212、INC 189、MOVA 185、ADD 177；完整表在 JSON。

### 4.5 CSR 0x804、H417 与 WCH-X

【手册】`CH32H417RM.PDF` V1.7、SHA-256 `b57ebb0c0ae2cd772d32cb9ddeb6a6315fcc3916bcd3576e5a83eaeb7dfa6967`：PDF p44（印刷 p40）只说明 V5 实现 WCH-X、提升代码密度/计算性能；本轮在该页及全文文本层未得到 WCH-X 完整语义表。

【手册】`0x804` 页账本：`HW_POPDM_CTLR` 在 X315 p74/83、V407 p62/67、H417 p46/52；`INTSYSCR` 在 FV2x/V3x p109、L103 p72、M030 p44–45、V003 p47、V00X p58、V205 p75–76、X035 p50、CH641 p42，以及四本 QingKe core manual 的相应页。该结果支持“同址异义必须按文档限定”，不支持按内核名无条件外推。

### 4.6 Schematic 与触摸公式

【实测】精确规则“文件名以 `SCH.pdf` 结尾，或位于 `SCHPCB/` 下”得到 13 个物理 PDF、11 个 SHA-256 内容组；全部页面做 `pdftotext -layout`，每组抽到 18–125 个不同 pin/mux token，代表页视觉确认 `PA12/USB`、`PA4/ADC4/OP3_O1/DAC1`、`PIOC_IO0/1`、`SWDIO` 等。限定的 `CSR|SFR_|register|寄存器|0x...` 查询为 0；未对所有图形元素做 OCR/人工逐页否定。

【手册】【实测】触摸脚本已重跑并重新查看渲染页：CH587 touch V1.1、SHA-256 `bf50109705ef8acbf0c3573ecd43689d2ae2a976dce9f4a56d04a7478e05359a` p3–4 清楚显示 `η=Cf/Cb=maxvar/chBaseline`、`value=maxvar×Baseline/chBaseline`、`th=(level/10)×value`；V006 文档 SHA-256 `9c0f28254428f03947e846db9d687ce02eed6dcc1d603245e3d28b61b688d8b3` p3 显示 `Cx=Cp+Cf`、`ΔC=Cf≈0.1–5 pF`。这两组公式不再依赖上下文重建。

## 5. 仍无法确认（8 项）

1. 【推断】XW q0/funct3=4 剩余 1,536 个 pattern 的硬件合法性/语义；GAS 无助记符、归档没出现都不是硅级否定。
2. 【推断】`0x2b/0x5b/0x7b` 及 custom-0 其他 header 的实际实现；`.insn` 接受和 objdump raw 不能回答。
3. 【推断】`mrsl/mrslu/wexti` 的完整微架构语义、异常行为、适用芯片与版本；现有 SDK/decoder 只给接口和编码。
4. 【推断】WCH-X 的完整规范，以及 XW、MRS、memory-copy、delay 与各 V3/V5 子版本的精确集合关系；H417 的一句功能描述不够。
5. 【推断】ROM 中 data-like `0x5f9b34fb/0x3b352f2b` 是否可达；需要供应商 code/data map、符号或控制流恢复。`mcpy@0x40968` 不受此项影响。
6. 【推断】27 个没有随包样本的 RISC8B 格式是否被 WASM53B v3.1 正确接受；需要运行该 EXE、获得更多 LST/BIN 或另一实现交叉组装。
7. 【推断】PIOC 多字节数据交换的原子性、精确 cycle 相位和端到端延迟；手册只确认单寄存器冲突优先级、状态握手和 DATA_EXCH 的单周期 bit transfer。
8. 【实测】`tmp/wch-riscv` 的 514 个 PDF、MRS 的 19 个 PDF、`tmp/upstream` 的 3 个 PDF 只做路径盘点，没有同等逐页文本/视觉审阅；样本显示多数为通用构建依赖，但它们仍是明确覆盖盲区。

## 6. 覆盖声明与方法限制

【实测】主要 PDF 覆盖：4 本 QingKe core manual 共 167 页；13 份 application notes 共 4,373 页（12 本 chip RM 为 4,362 页，另 11 页 touch guide）；EVT 109 个物理 PDF、81 个内容组，去重后 855 页，按物理重复计 1,238 页。所有内容组均做 `pdftotext -layout` 和页级关键词账本；只有高风险页、PIOC/Touch 公式页和三张代表 schematic 做视觉渲染，不声称 4,540+ 页逐页人工目检。

【实测】非 PDF 覆盖：EVT prose-like `.txt/.md/.rst/.html/.htm` 170 个文件、945,264 bytes 做精确 vendor term 搜索；两套工具链的 bundled doc/info/man/distro-info 候选共 77 个文件做同一搜索，未发现精确 XW/custom mnemonic 文档。GCC15 的 `-march=help` 和预定义宏构成更强的本机工具证据；GCC12 不提供该 help 表。

【实测】源/二进制覆盖：24,225 个 EVT 源文件；311 个物理/187 个去重归档；1,177 个 archive ELF member；1,108 个独立 `.o`；5 个 ROM HEX；30 个 PIOC ASM、15 个 LST/BIN/C array 组。路径由 Python `os.walk/Path` 或 `find -print0` 处理，未依赖乱码文件名手打。

【推断】任何阴性结论均仅限上述文件、当前 SHA-256、当前 parser/query 和 executable-section/linear-framing 范围；没有对所有 WCH 历史版本、未入仓库 SDK、实际硅片或不可提取图形内容作全称结论。

## 7. 复现命令

从仓库根运行：

```sh
python3 tmp/isa-research-codex/round2_xw_audit.py
python3 tmp/isa-research-codex/round2_custom_audit.py
python3 tmp/isa-research-codex/round2_binary_audit.py
python3 tmp/isa-research-codex/round2_pioc_audit.py
python3 tmp/isa-research-codex/round2_doc_audit.py
python3 tmp/isa-research-codex/touch_formula_check.py
python3 -m py_compile tmp/isa-research-codex/*.py
find tmp/isa-research-codex -maxdepth 1 -name 'round2-*.json' -print0 | xargs -0 -n1 jq empty
git diff --check -- isa-research-codex tmp/isa-research-codex
```

CH587 `mcpy` 的直接上下文：

```sh
"MRS_Toolchain_MAC_V240/Toolchain/RISC-V Embedded GCC15/bin/riscv32-wch-elf-objdump" \
  -D -b ihex -m riscv:rv32 --start-address=0x40958 --stop-address=0x40980 \
  tmp/wch-evt/evt/QingkeV3C_CH587_EVT/EXAM/BLE/LIB/CH587BLE_ROMx.hex
```

## 8. 产物与轮次追踪

- 主报告：`isa-research-codex/findings.md`
- 要求矩阵与第一轮修复表：`isa-research-codex/round2-review.md`
- 第二轮脚本/JSON：`tmp/isa-research-codex/round2_{xw,custom,binary,pioc,doc}_audit.py` 与对应 `round2-*-audit.json`
- 子 agent 记录：`tmp/isa-research-codex/round2-subagent-reports.md`
- PDF 视觉证据：`tmp/isa-research-codex/round2-doc-pages/` 与 `tmp/isa-research-codex/touch-formulas/`
- 命令与校验记录：`tmp/isa-research-codex/round2-run-log.md`

【实测】进入第二轮时，第一轮文件内容保留在 Git index；第二轮修订保持 unstaged，可分别用 `git diff --cached -- ...` 与 `git diff -- ...` 对照。没有执行 git commit，也没有修改 `isa-research-claude/`。
