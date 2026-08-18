# 第二轮独立审查矩阵

日期：2026-08-03（Asia/Tokyo）

本文件记录 `research-wch-custom-isa-prompt.md` A–F 各问题如何被第二轮独立复核。主结论见 `findings.md`；机器可读账本见 `tmp/isa-research-codex/round2-*-audit.json`。

## Git 与轮次边界

- 第一轮产物已在进入第二轮时位于 Git index；第二轮修改保持在 worktree，不覆盖 index 中的第一轮快照。
- 因此 `git diff --cached -- isa-research-codex tmp/isa-research-codex` 表示第一轮基线，`git diff -- isa-research-codex tmp/isa-research-codex` 表示第二轮相对第一轮的修正。
- 新增第二轮文件只使用 intent-to-add 使其进入 unstaged diff；未提交 commit，未改 `isa-research-claude/`。

## A–F 要求矩阵

| 要求 | 第二轮状态 | 证据/边界 |
|---|---|---|
| A：重枚举 4 本 core、13 份 application notes、109 份 EVT PDF | 完成 | `round2_doc_audit.py`：4/167 页，13/4373 页，EVT 109 物理/81 内容组/855 unique pages（物理重复计 1238 页） |
| A：其他未扫文档 | 有限完成 | MRS 文档候选 77 个、EVT prose-like 170 个做精确术语检索；`tmp/wch-riscv` 514 PDF、MRS 19 PDF、`tmp/upstream` 3 PDF 仅盘点，列为盲区 |
| A：11 份 schematic/PCB | 完成并修正 | 精确选择 13 物理/11 内容组；全部文本抽取，3 页渲染；pin/mux 可读，限定查询未见寄存器表，未做全页人工目检 |
| A：触摸公式 | 复跑并视觉复核 | `touch_formula_check.py` 重跑；CH587 p3–4、V006 p3 渲染逐字符核对 |
| A：工具链自身文档/帮助/宏 | 完成 | GCC15 `-march=help` 列 `xw 2.0`；GCC12 不支持该 help；宏为 0/2000000；77 个 bundled doc 候选未出现精确 vendor 术语 |
| B：独立穷举 XW | 完成 | 两代 assembler × 5 个 version tag × 8704 全量，10/10 字节一致；fresh encoder/decoder 与本地 opcode 常量交叉检查 |
| B：GCC12/15 差异 | 完成 | 编码/操作数集合一致；help、canonical march、`__riscv_xw` 版本接口不同 |
| B：拒绝槽位 | 完成且限界 | 8 个命名形式覆盖 8704；q0/f3=4 余 1536 pattern 无命名映射；不能推出硬件非法 |
| B：1971 分布 | 完成 | `xw2p2` 的 8 助记符次数/不同词、寄存器、立即数、top operand tuples 全部入 JSON |
| C：全部 custom major assembler 空间 | 完成且限界 | `.insn r` 5×8×128=5120 个 header 全测；objdump 481,280 个一轴变化词；不是 5×2^25 硅语义穷举 |
| C：无助记符接受点 | 完成且限界 | 472,224/481,280 在两个 objdump 均保持 raw；这是 directive/decoder 行为，不是硬件实现 |
| C：其他手册 custom/WCH-X | 完成并发现漏项 | QingKe V3 p55 完整 delay；V3 p2/p54 有 mcpy/MRS 描述；V407 p57–58；H417 p44 WCH-X |
| C：SDK 内联汇编/裸编码 | 完成 | 24,225 源文件、325 MB；3 条 `.insn`、20 条精确命名文本/10 条 asm code；1732 个数字发射均非目标 major |
| D：独立 `.o` | 完成并修正 | 1108 物理 `.o`；822 RISC-V（726 ELF32+96 ELF64），14982 frames，custom/mcpy 0；均为 CRT/start 路径 |
| D：5 份 ROM HEX | 完成并修正 | 5 物理/3 内容组；checksum 全通过；支持 6/8/10/12/14-byte framing；CH587 0x40968 为 mcpy，其余限定为 mixed-code/data fingerprint |
| D：非标准 executable section | 完成 | 所有 `SHF_EXECINSTR` section；物理归档 `.highcode` exact 67/family 220，220 均 executable；code-name/non-exec heuristic 为 0 |
| D：unknown 198 | 独立复现 | 187 个代表归档直接 objdump 共 1,137,897 行；未命名非 XW 为 0，XW 未命名 12112，`0x0000 c.unimp` 198 |
| E：PIOC 直方图 | 完成并修正 | 7307 非 DW；MOVA 185、RET 78、RETURN 0；完整 histogram 在 JSON |
| E：66 格式逐条对撞 | 样本范围完成 | 7307/7307 匹配；39 格式有样本、27 无样本，故不称 66 条均被产物验证 |
| E：交互与并行约束 | 部分确认 | p3 同址写 host 优先；p10 双向握手；p12 DATA_EXCH 单周期位传输；事务原子性/精确延迟仍未知 |
| E：不运行 WASM53B 的验证 | 完成 | ASM→LST、补 ORG 后 LST→BIN、C array→BIN 均 15/15；EXE 只静态 hash/banner/BAT 链，不声称已执行 |
| F：全称/无出处表述挑战 | 完成 | `findings.md` 的 13 条修正逐项给出受限版本，阴性结论均写材料、方法和未覆盖范围 |

## 第一轮错误与第二轮修复

1. 第一轮脚本只测 `.insn r` 40 个点却写成 5120：第二轮实际组装 5120。
2. version tag 只抽 8 点/标签却写成一致：第二轮 8704×10 全量。
3. 3,178,496 个 named Cartesian 只测 4 行却称穷举：改为字段推断；实际 pairwise 20,650。
4. 缺失 1,971 个 XW 的操作数分布：补齐 8 个助记符、寄存器、立即数、top tuple。
5. PIOC raw classifier 把 253 个词称 unknown：修正为 241 个合法 d=0 byte-op + 12 个显式 DW。
6. PIOC 把 3 个 `RETURN:` 标签当指令、18 个 DW 0 当 NOP：修正直方图。
7. 独立 `.o` 解析只计 466：加入 ELF64/扩展 section header 后为 822。
8. ROM 固定 2/4-byte framing 把长指令内部 `0x07f805fb` 当候选：支持 6–24-byte 前缀并降级重叠窗口为 fingerprint。
9. “CH32V407 是唯一给编码手册”：QingKe V3 p55 构成直接反例。
10. “批号第五位决定 PMP 与硬件断点”：拆成 p1 的 PMP 条件与 p53–54 的 core-0 trigger 条件；core 1 恒有四通道。
11. CSR 0x804 以 core family 泛化：改为逐文档 `INTSYSCR`/`HW_POPDM_CTLR` 账本。

## 结论强度规则

- assembler 接受仅证明工具语法/字段映射；不证明芯片实现。
- objdump 给助记符仅证明该工具识别；不证明控制流可达或硬件语义。
- ELF `SHF_EXECINSTR` 线性扫描是 section 范围普查；不证明每条可达。
- HEX 无完整 code/data map；只有结合正确 instruction framing 和局部控制流的 `0x40968 mcpy` 被列为强证据。
- “未发现”始终附材料、查询和盲区；未对仓库或 WCH 产品线作全称否定。
