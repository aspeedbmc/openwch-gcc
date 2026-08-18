# WCH 自定义 ISA 独立审查（codex，修订后复审）

初审日期：2026-08-04（Asia/Tokyo）

修订后复审日期：2026-08-04（Asia/Tokyo）

审查对象：`isa-research-claude/` 两份成稿及其素材、`isa-research-codex/` 第二轮复查、`audit-report-f/followup/results/isa-census*` 与对应扫描器。

审查原则：假阴性代价高于假阳性；“手册未写”不等于“芯片不存在”；不作许可判断。初审曾判 REWORK，本报告记录修订后的重新审查结果，当前结论取代初审结论。

## 1. 结论

### 对 `isa-research-claude/` 两份成稿：PASS

初审的证据链、范围、版本口径、ROM 漏项、PIOC 覆盖和素材不同步问题均已关闭。修订后的两份成稿满足评审硬门槛：

| 门槛 | 复审判定 | 主要依据 |
|---|---|---|
| 证据链 | **通过** | 技术表均有逐行证据列；【手册】出处可回到原始 PDF，主要一手件在 `wch-custom-isa-reference.md` §0 给出版本、完整 SHA256 和页码；【实测】给出命令或账本。 |
| 两套体系分离 | **通过** | RISC-V 主核与 RISC8B/PIOC 在参考文档 §1、使用实况 §6 中分开定义和统计。 |
| XW sp 形式与互斥 | **通过** | Q0/funct3=100 四个 sp 形式、x8–x15、立即数范围、半字乱序 immediate、F+C+XW、D/Zcb 冲突和同名异码均写明并有 fixture 证据。 |
| 版本与差集边界 | **通过** | 版本标签明确为 assembler passthrough；EVT 12/0/11、全语料 62/4/121 与实际使用 XW 的 62/4/34 分开；121 个未声明 XW 版本又与 71 个无属性节分开；差集 0 与方法盲区同时报告。 |
| 使用实况与自检 | **通过** | 311/187/1,177/3,350,246/1,137,897 可复算；GAS、`GetChipID`、XW 六库三项自检均写实并通过。 |
| 零使用边界 | **通过** | custom-32/RVA/Zbc/RVD 的 0 只限定于 `.a` executable sections；独立 `.o` 和 ROM 分列，CH587 `mcpy@0x40968` 已进入必须处理项。 |
| 阴性与全称句 | **通过** | “全部”“没有”“零”等表述均邻接材料范围、解析方法或反例边界；8 个 XW 只称“当前已知/可验证形式”。 |
| 重写可用性 | **通过** | 必须支持、可后置、分析陷阱均有本文证据；PIOC 66 个手册格式与 39/27 样本边界分开；OTP/NOP 补丁位保留。 |
| 内部一致性 | **通过** | 两份成稿、四份素材、census notes 与第二轮账本的关键数字和范围已同步；勘误清单补齐。 |

本轮没有剩余的阻断性返工项。

### 对 `isa-research-codex/`：复查质量评价

第二轮复查质量可靠。其 delay 手册漏项、PIOC 分类器修正、ELF64 `.o` 漏扫、ROM framing、CH587 `mcpy`、CSR 0x804 和 H417 批号边界均经本轮重新核对后成立。它对 assembler、parser、文件产物的结论证据充分，并明确没有把这些结果扩大成硅片语义。

第二轮仍有一个可补强点：它验证了 `mcpy` 固定位与手册一致，却未指出 CH32V407RM p58 的 rs1/rs3 地址角色文字和 SDK/ROM 顺序冲突。本次复审补出了该冲突，现已同步到主参考、`qingke-custom-isa.md`、`wch-doc-instr-reg-findings.md` 和勘误清单。

## 2. 初审返工闭环

| # | 初审问题 | 修订后状态 |
|---:|---|---|
| 1 | 技术断言缺逐条证据标签 | 两份成稿的技术表均增加“证据”列，段落和决策项逐条带【手册】/【实测】/【SDK】/【规范】/【推断】。 |
| 2 | 手册引用缺版本、hash、页码 | 参考文档 §0 建立完整 SHA256 provenance；正文给页码并回指 §0，PIOC 决策项也补入完整出处。 |
| 3 | `mcpy` 对齐被误列为未知 | 改为 CH32V407RM p58 明确“所有地址均无对齐要求”；未知项只保留端点、写回、粒度、中断和跨芯片语义。 |
| 4 | 把 8 个 XW 形式写成全集 | 改为“当前工具链/手册可验证的 8 个形式”，明确不能证明 XW 硅片全集。 |
| 5 | XW 内容组口径混用 | EVT 全部 23 组为 12/0/11；全语料 187 组为 62/4/121，其中 71 组无属性节；实际使用 XW 的 100 组另列 62/4/34。 |
| 6 | custom-32 零使用越过 `.a` 范围 | 零命中只覆盖 311 个 `.a`；822 个 RISC-V 独立对象和 ROM 单列，CH587 ROM 的真实 `mcpy` 不再遗漏。 |
| 7 | 自检和 unknown 边界写得不够近 | 三项自检给出期望、实际、命令；unknown=198 紧邻 SHF_EXECINSTR、线性 framing、当前 decoder 和混入数据限制。 |
| 8 | 差集 0 的效力容易被高估 | 保留并突出“四槽已占满、只有 Q0/f3=4 的 1,536 点有判别力且零命中”。 |
| 9 | C/F/D/Zcb 互斥表缺行级依据 | 每种组合增加 fixture/编码证据；D、Zcb、Zcmp/Zcmt 改为“不能作为完整扩展无条件组合”，不抹掉未重叠形式。 |
| 10 | 32 位操作总数与 major 分类混杂 | 改为 4 个已命名形式，另有无官方助记符 delay；`mcpy` 明确位于 MISC-MEM 0x0f，而非 custom major。 |
| 11 | PIOC 66 格式容易被读成全部验证 | 改为手册 66、15 个程序 LST 静态覆盖 39、另 27 无样本；明确 WASM53B 未在 macOS 动态运行。 |
| 12 | 主文档勘误清单不完整 | 补入 PFIC、CSR 分类、MISA、IWDG 等条目，当前参考文档 §10 共 10 项。 |
| 13 | 素材保留旧数字/旧结论 | `qingke-custom-isa.md`、PIOC findings、文档 findings 与 census notes 已同步当前口径。 |
| 14 | 复审新增：`mcpy` 地址角色冲突 | CH32V407RM 写 rs1=目标、rs3=结束；四份 SDK 宏和 CH587 ROM 一致采用 rs1=EA、rs3=DA。固定编码位一致，角色文字列为手册勘误，并明确交换两者属于数据破坏风险。 |
| 15 | 追加复核：IQmath `mcpy` 假阳性不可复现 | 撤回原非执行数据命中记载；对全部 40 个物理 IQmath archive 做精确小端、反向精确和任意操作数逐字节掩码扫描，三项均为 0，并纳入独立账本与验证断言。 |

## 3. 亲手复现记录

以下命令均从仓库根运行，结果与修订后文档一致。

### 3.1 `c.fld` 与 XW `c.lbu` 同码

```text
$ riscv-wch-elf-objdump -s -j .text known-c.lbu.o
0000 8821

$ riscv-none-embed-objdump -d -M no-aliases known-c.lbu.o
0: 2188  c.fld fa0,0(a1)
```

fixture 源为 `c.lbu a0,0(a1)`，小端 bytes `88 21` 即 halfword `0x2188`。这确认编码槽冲突，不证明两个语义可同时启用。

### 3.2 `mcpy a0,a1,a2` 与手册位域

```text
$ riscv-wch-elf-objdump -s -j .text custom-mcpy.o
0000 0f70b560
```

word 为 `0x60b5700f`：rs1=10、rs2=11、rs3=12、funct3=7、opcode=0x0f，与 CH32V407RM V1.1、SHA256 `63625af9027af6abfff57a58f8d2afdb2b68ee7d31c323e407da6ea786573c56`、PDF p58 的固定字段和寄存器位置一致。

同页角色文字写 rs1=目标、rs2=起始、rs3=结束；SDK 的 `ASM_MCPY(DA,SA,EA)` 发射 `mcpy EA,SA,DA`。CH587 ROM 在 `0x40966` 先执行 `a2 += a1`，随后 `mcpy a2,a1,a0`，支持 SDK 顺序。故固定编码一致，rs1/rs3 角色文字冲突。

### 3.3 XW 版本标签透传

```text
xw     8821
xw2p2 8821
xw3p0 8821
```

三次 assembly exit=0，同一源均编码为 `0x2188`。第二轮全量账本还覆盖 GCC12/GCC15 × 五标签，每次 8,704 case、0 mismatch、同一 stream SHA256 `d3a6a0647389d3aee2661916eb420ca58da4a29b8e59bdfb3626b8c810651a05`。这只证明标签透传和当前可生成字节一致。

### 3.4 census 与自检

```text
data_rows=9246 total_count=1137897 XW=19344 unknown=198 custom32=0
rvc    27 insns, OK
rv32   97 insns, OK
xw     16 insns, OK
eth_api.o/.text.GetChipID: lui(RVI) lhu(RVI) andi(RVI) c.jr(RVC-std)
control OK
```

`custom32=0` 只解释为 `.a` executable-section 结果。无 attributes 的 `LIBMESHROM.a` 另复现为 1,478 条幻影 fld/fsd、272 条 raw、原始 XW 1,750，满足 `272+1,478=1,750`。

IQmath 争议项另按整个 archive 的原始字节复算，不依赖 ELF 节分类：40 个物理文件中，精确小端 `0f70b560`、反向精确 `60b5700f`、任意 rs1/rs2/rs3 的 little-endian `mcpy` 掩码窗口均为 0。结果在 `round2-binary-audit.json` 的 `archives.iqmath_raw_mcpy_scan`，并由 `round2_verify.py` 断言。

### 3.5 第二轮账本

```text
$ python3 tmp/isa-research-codex/round2_verify.py
assertion_groups=6
status=pass
```

`python3 -m py_compile tmp/isa-research-codex/*.py` 通过；全部 `round2-*.json` 通过 `jq empty`。

### 3.6 原始 PDF 抽查

直接读取原始 PDF，而不是把抽取文本当出处：

1. QingKeV2 V1.3，SHA256 `5430356218fca280023429a2516c3ac4aa200477a7fedd7d21af2f3562d70e7b`，PDF p2：列出 8 个 XW 助记符。
2. QingKeV3 V1.5，SHA256 `fcc16b54d8818b04b9f8a7a7fbce6c504b87ca3787f0933edecc4da7112438d5`，PDF p55：给出 delay 的 imm/rs1/match/div/sel/opcode 位表。
3. CH32V407RM V1.1，SHA256 `63625af9027af6abfff57a58f8d2afdb2b68ee7d31c323e407da6ea786573c56`，PDF p58：给出 mcpy 位表并明确地址无对齐要求。

## 4. 两轮冲突的最终裁定

| 主题 | 裁定 |
|---|---|
| delay 编码来源 | 第二轮正确：QingKe V3 p55 与 V407 p57 均有完整位表；第一轮素材已同步。 |
| XW 标签 | 第二轮全量实验成立；只能证明 assembler/字节行为，不能证明硅片能力。 |
| PIOC unknown | 第二轮正确：241 个合法 d=0 byte-op、12 个 DW；7,307 条非 DW failure=0，但只覆盖 39/66。 |
| 独立 `.o` | 第二轮的 822 个 RISC-V 对象正确，旧 466 漏了 ELF64；不并入 `.a` 口径。 |
| custom-32 零使用 | `.a` executable sections 为 0；40 个 IQmath archive 的原始字节补扫也为 0；CH587 ROM 则有真实 `mcpy`。 |
| `mcpy` 对齐 | V407RM 明确无对齐要求；不再列未知。 |
| `mcpy` 地址角色 | 固定位与 assembler 一致；手册 rs1/rs3 角色文字与 SDK/ROM 冲突，按 SDK/ROM 约定并保留硅片测试缺口。 |
| XW 内容组 | EVT inventory 为 12/0/11；全语料为 62/4/121，其中 71 组无属性节；全语料 XW 使用组为 62/4/34；`xw2p0` 的 4 是组数，9 是 distinct words。 |
| RISC8B 完整性 | 手册定义 66；随包样本验证 39，27 未采样。 |

## 5. 抽查覆盖声明

已检查：

- 两份成稿的全部章节、技术表证据列、范围限定和决策项；
- 四份 QingKe core manual provenance，直接抽查 V2 p2、V3 p55；
- CH32V407RM p57–58，以及 mcpy 的 SDK 宏和 CH587 ROM 局部控制流；
- XW 八个已知形式、sp 槽、互斥、标签透传和 8,704 词全量账本；
- 311 个 `.a` 的关键总量、版本组、unknown、objdump 恒等式、无属性库样本，以及 40 个 IQmath archive 的原始字节 `mcpy` 补扫；
- 822 个独立 RISC-V `.o` 与 5 个 ROM HEX 的第二轮边界；
- PIOC 66/39/27、15 组产物静态闭环和 OTP/NOP 约束；
- 成稿与四份素材、census notes、第二轮 findings 的关键冲突。

没有声称已经证明：

- XW 已知 8 形式之外的硅片全集，或 1.0/2.0/2.2 的硬件语义相同；
- `mrsl/mrslu/wexti`、WCH-X、delay、mcpy 的完整微架构语义；
- ROM data-like custom words 的控制流可达性；
- WASM53B 对 27 个未采样 RISC8B 格式的动态接受；
- PIOC 多字节事务原子性和精确时序；
- 只做路径盘点的 514+19+3 个 PDF 的逐页内容。

这些限制已在参考文档 §9 和使用实况 §8 显式列出，因此不是 PASS 判定中的隐藏缺口。

## 6. 值得保留的优点

1. RISC-V 与 RISC8B/PIOC 分界清楚，统计单位不会交叉污染。
2. XW 最易漏掉的 Q0/funct3=100 四个 sp 形式已覆盖，立即数乱序和 Zcb 同名异码写得可直接用于 decoder 测试。
3. 版本差集同时报告“0”与方法上限，避免把字节相同误写成语义相同。
4. 40 个 IQmath archive 的三种原始字节复查为零，CH587 ROM 真实 `mcpy` 则单列为必须处理，未再保留不可复现的假阳性故事。
5. objdump 两种失效模式和 `12,112 + 7,232 = 19,344` 为实际二进制分析提供了可靠护栏。
6. PIOC OTP/NOP 补丁位约束已进入“必须支持”，不会在开源重写时被当作普通冗余删除。
