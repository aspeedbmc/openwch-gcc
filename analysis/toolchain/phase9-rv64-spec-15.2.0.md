<!-- 来源：tmp/phase9-evidence/15.2.0/spec.md（开发机证据树原件；按 2026-08-18 用户裁定「影响复现的指针目标复制入库」执行，内容零改动，补丁 message 指针不改写） -->

# phase-9 S1 规格表 · 15.2.0（binutils 2.45）

**规格来源**：官方 `ref/gcc/darwin-arm64/15.2.0/` 二进制现场探测，2026-08-17。
**结论一句话**：官方 15.2.0 的 16 个 XW opcode 表项**不带任何 xlen 限制**（等价于 `xlen_requirement = 0`）；
我方现文写 `32`，导致 rv64 面四类分歧、rv32 面零分歧。修法 = 16 行 `32` → `0`。

---

## 1. 探测机器与侧参 provenance

驱动 `tmp/phase9-evidence/s1-probe.py`（stdlib-only，只读；两侧工具前缀由 `--side NAME=PREFIX` 显式传入，
脚本内无任何默认侧）。

| 侧 | 工具前缀 | as sha256 | objdump sha256 |
| --- | --- | --- | --- |
| official | `ref/gcc/darwin-arm64/15.2.0/bin/riscv32-wch-elf-` | `c958f659…8152` | `8e236c74…5dd9` |
| ours | `tmp/phase3h-evidence/ours-p8r-frozen/bin/riscv32-wch-elf-` | `b27619c0…6aea` | `e9d1ffec…6c44` |

我方侧取 **P8-R 冻结 install 树**（DEC:81 锚定的那一棵），不是 `tmp/golden/toolchain-current`
（其现指 phase3g `ours-v3.0-frozen`，是更早的树）。本阶段 S1 全程未触碰 `toolchain-current`。
逐侧四工具全表：`s1/runA/provenance.tsv`。

**探针面**：184 个探针 × 2 侧 = 368 行。七组：
`canon`（8 个规范助记符）· `alias`（8 个裸助记符别名形式）· `alias-norvc`（别名在 `.option norvc` 下）·
`boundary`（17 个边界/越界立即数）· `regs`（5 个压缩寄存器集边界）· `dcollide`（4 个 D+C 撞车槽）·
`control`（3 个上游自带 xlen 限定行，作正对照）。
march 面：`rv32imac_xw` / `rv64imac_xw` / `rv32imafdc_xw` / `rv64imafdc_xw` / `rv32imac` / `rv64imac`
（撞车组另加 `rv32imafdc` / `rv64imafdc`）。

## 2. 判据器三关自证（phase-8 closure §9 纪律）

| 关 | 做法 | 结果 |
| --- | --- | --- |
| ① 量的是谁 | 侧参显式传入 + 每次运行落 `provenance.tsv` 记两侧四工具 sha256 与绝对路径 | 通过 |
| ② 判据列确定不确定 | 同输入连跑 `runA`/`runB`，`probes.tsv` 逐字节 diff | **0 行差异** |
| ③ 量不量得出差别 | 内建 must-fire 四类共 8 条，fail-closed（不满足即 rc=2 不出结果） | **8/8 PASS** |

must-fire 明细（`s1/runA/mustfire.tsv`）：MF-1 `c.jal`（上游 xlen=32 行）rv32 收/rv64 拒；
MF-2 `c.ld`（上游 xlen=64 行）rv32 拒/rv64 收；MF-3 `c.lbu` 在无 `_xw` 的 rv32imac 下被拒；
MF-4 `c.lbu` 在 rv32imac_xw 下收且编码 `8821`。四条 × 两侧 = 8。
MF-1/MF-2 是**本任务的核心判别力自证**：它们证明「表项 xlen 字段在 rv64 上被过滤」这一机制
在本探针面上确实可观测——否则「官方无限制」的结论只会是探针盲。

**判据器缺陷（已修，如实登记）**：首版把绝对路径传给 `as`，源文件路径进了诊断文本，
`runA`/`runB` 的 336 行"差异"全是 run-tag 泄漏。改为 `cwd=workdir` + 裸文件名后 0 差异。
原始日志 `raw-*.log` 仍有 2080 行 run-tag 差异，经逐行核实**全部**是 objdump 输出首行的
`<path>: file format elf..` 横幅，不进判据列。

## 3. 规格：官方 rv64 面 = 官方 rv32 面（逐列实证，非推断）

对官方一侧做 rv32↔rv64 配对逐列比较（92 对 × 7 列 = 644 单元）：

| 组 | 单元数 | rv32≠rv64 | 涉及助记符 |
| --- | --- | --- | --- |
| canon | 168 | **0** | — |
| alias | 168 | **0** | — |
| alias-norvc | 56 | **0** | — |
| boundary | 119 | **0** | — |
| regs | 35 | **0** | — |
| dcollide | 56 | **0** | — |
| control | 42 | 42 | `c.jal` `c.ld` `c.sd` |
| **合计** | **644** | **42** | 仅上游自带 xlen 限定行 |

即：官方侧唯一随 xlen 变化的行为，全部来自**上游本来就带 xlen 限定的三个对照助记符**；
16 个 XW 行在 rv32 与 rv64 上 rc、编码字节、诊断文本、四种反汇编模式**逐列相同**。

**规格明细（官方，rv32 与 rv64 取值相同）**

| 形式 | 助记符 | 样例 | 编码 | 立即数范围 | 寄存器 |
| --- | --- | --- | --- | --- | --- |
| 规范 | `c.lbu` | `c.lbu a0,0(a1)` | `8821`（半字 `0x2188`） | 0–31 步长 1 | x8–x15 |
| 规范 | `c.lhu` | `c.lhu a0,0(a1)` | `8a21` | 0–62 步长 2 | x8–x15 |
| 规范 | `c.sb` | `c.sb a0,0(a1)` | `88a1` | 0–31 步长 1 | x8–x15 |
| 规范 | `c.sh` | `c.sh a0,0(a1)` | `8aa1` | 0–62 步长 2 | x8–x15 |
| SP | `c.lbusp` | `c.lbusp a0,0(sp)` | `0880` | 0–15 步长 1 | x8–x15 |
| SP | `c.lhusp` | `c.lhusp a0,0(sp)` | `2880` | 0–30 步长 2 | x8–x15 |
| SP | `c.sbsp` | `c.sbsp a0,0(sp)` | `4880` | 0–15 步长 1 | x8–x15 |
| SP | `c.shsp` | `c.shsp a0,0(sp)` | `6880` | 0–30 步长 2 | x8–x15 |
| 别名 | `lbu`/`lhu`/`sb`/`sh` | `lbu a0,0(a1)` | 同规范行 | 同上 | 同上 |
| 别名 SP | 同上 | `lbu a0,0(sp)` | 同 SP 行 | 同上 | 同上 |

边界（rv64 与 rv32 取值相同）：`c.lbu a0,31(a1)`=`e83d` 收 / `c.lbu a0,32(a1)` 拒；
`c.lhu a0,62(a1)`=`ea3d` 收 / `63`（奇）拒 / `64` 拒；`c.lbusp a0,15(sp)`=`8887` 收 / `16` 拒；
`c.lhusp a0,30(sp)`=`a887` 收 / `32` 拒（`c.sb*`/`c.sh*`/`c.sbsp`/`c.shsp` 同形，见 `probes.tsv`）。
`.option norvc` 下 8 个别名一律回落 4 字节 I 形式（rv32/rv64 同），如 `lbu a0,0(a1)`=`03c50500`。

**属性/mapping 面**（`readelf -sW` 全宽取录，无截断——首版用默认宽度导致符号名被截，
`_xw2p2` 尾巴是推断而非观测，已改正并重取）：

| 侧 | march | mapping 符号 |
| --- | --- | --- |
| official | rv32imac_xw | `$xrv32i2p0_m2p0_a2p0_c2p0_zmmul1p0_zaamo1p0_zalrsc1p0_zca1p0_xw2p2` |
| official | rv64imac_xw | `$xrv64i2p0_m2p0_a2p0_c2p0_zmmul1p0_zaamo1p0_zalrsc1p0_zca1p0_xw2p2` |
| ours | rv32imac_xw | 与 official rv32 行**逐字节相同** |
| ours | rv64imac_xw | 无对象（汇编失败） |

即官方 rv64 的 mapping 串与其 rv32 串**仅 `rv32`→`rv64` 前缀之差**，`xw2p2` 照常注册
（`2p2` 是 15.2.0 的裸 xw 规范串，DEC:42 REWORK-0005 的既有结论；12.2.0 为 `xw1p0`，属版本差异）。
15.2.0 因补丁 0004 使属性段写出为 opt-in，本探针默认路径下 `Tag_RISCV_arch` 两侧皆空。
该面无独立分歧：我方 rv64 无对象可比，属性/mapping 差异是"官方产出、我方未产出"的派生结果，
预期随 xlen 修复自动闭合——**但按协调器里程碑 1 回执 ④(b)，S3 须以探针背书而非静态推断**。

## 4. 我方现状与分歧分类

我方侧同一配对比较：644 单元中 **332 不同**（= 42 个与官方相同的 control 行 + **290 个 XW 行**）。
官方↔我方直接对拍：316 个分歧单元，**全部落在 rv64 探针**，rv32 探针 92 个 × 7 列 **零分歧**
（`side-diff.tsv` 中不含任何 rv32 probe_id）——这是"rv32 面零扰动"可达的直接证据。

分歧四类（rv64，92 个探针）：

| 类 | 数量 | 现象 | 危害等级 |
| --- | --- | --- | --- |
| **A 静默编码分歧** | 16 | 8 个别名形式两侧 `rc=0` 均成功，官方发 **2 字节** XW 编码，我方回落 **4 字节** I 形式。无任何诊断。 | **最高**——无错无警，直接改变生成码大小 |
| B 接受面分歧 | 26 | 官方 `rc=0`，我方 `rc=1`（`unrecognized opcode … extension 'zcb' required`） | 高 |
| C 诊断文本分歧 | 20 | 两侧皆拒，官方 `illegal operands`，我方 `unrecognized opcode`（表项被 xlen 过滤 ⇒ 助记符整体不存在） | 中（诊断文本在保真面内，DEC 2026-08-13） |
| D 反汇编分歧 | 20 | 两侧皆产出对象，`objdump -d -M xw` 官方解出 XW、我方打 `.insn`／保留 `fld` | 中 |

**A 类明细**（q4-probe 未覆盖、本轮新发现）：

```
lbu a0,0(a1)   official=8821(2B)      ours=03c50500(4B)
lhu a0,0(a1)   official=8a21(2B)      ours=03d50500(4B)
sb  a0,0(a1)   official=88a1(2B)      ours=2380a500(4B)
sh  a0,0(a1)   official=8aa1(2B)      ours=2390a500(4B)
lbu a0,0(sp)   official=0880(2B)      ours=03450100(4B)
lhu a0,0(sp)   official=2880(2B)      ours=03550100(4B)
sb  a0,0(sp)   official=4880(2B)      ours=2300a100(4B)
sh  a0,0(sp)   official=6880(2B)      ours=2310a100(4B)
```
（`rv64imac_xw` 与 `rv64imafdc_xw` 各一份，故 8×2=16 单元。）
机理：别名行被 xlen 过滤后，基础 I 形式 `{"lbu", 0, INSN_CLASS_I, "d,o(s)"}` 照常匹配，
于是"成功但换了编码"。这是本任务里唯一**不产生任何诊断**的分歧类。

**D 类的 D+C 撞车面**（rv64，`-M xw` 对无 xw 属性的纯 `rv64imafdc` 对象）：

| 输入 | 编码 | official 默认 | official `-M xw` | ours 默认 | ours `-M xw` |
| --- | --- | --- | --- | --- | --- |
| `c.fld fa0,0(a1)` | `2188` | `fld fa0,0(a1)` | **`lbu a0,0(a1)`** | `fld fa0,0(a1)` | `fld fa0,0(a1)` |
| `c.fsd fa0,0(a1)` | `a188` | `fsd fa0,0(a1)` | **`sb a0,0(a1)`** | `fsd fa0,0(a1)` | `fsd fa0,0(a1)` |
| `c.fldsp fa0,0(sp)` | `2502` | `fld fa0,0(sp)` | **`lhu s0,8(a0)`** | `fld fa0,0(sp)` | `fld fa0,0(sp)` |
| `c.fsdsp fa0,0(sp)` | `a02a` | `fsd fa0,0(sp)` | **`sh a0,2(s0)`** | `fsd fa0,0(sp)` | `fsd fa0,0(sp)` |

**默认模式两侧相同**——`-M xw` 是显式 opt-in 开关，故 gate 中性成立（全部 EVT 产物走默认模式）。
汇编侧撞车（`rv64imafdc_xw` 下 `c.fld` 等四条）**两侧均 rc=1**，互斥门已正确实现且与 xlen 无关，
本次不动。

## 5. 与 8.2.0 `xlen=0` 参照系的异同

| 项 | 8.2.0（参照，不动） | 15.2.0 目标态 |
| --- | --- | --- |
| xlen 字段 | `0` | `0`（本次由 `32` 改为 `0`） |
| 表项条数 | 8（仅 `c.*` 规范形式） | 16（8 规范 + 8 别名） |
| 门机制 | `match_with_wch_rvc_extension` 函数式互斥 | `INSN_CLASS_XW` + `xw_enabled` 子集门 |
| 表结构 | `{"C", 0}` 字符串子集数组（2.30 形态） | `INSN_CLASS_*` 枚举（2.45 形态） |

**异同的性质**：条数与门机制的差异是两代 binutils 表结构差异，各自复刻各自官方，
**不是本次要统一的对象**；本次统一的只有 xlen 字段一项。8.2.0 用 `0` 且经 rv64 实测与官方一致，
本次探测独立地在 15.2.0 官方上得出同一取值——两条独立证据链指向同一规格。

## 6. 落到补丁的改动位点（S2 输入）

`xlen_requirement` 字段在两处被读，语义同为「0 = 无限制」：

- 汇编：`gas/config/tc-riscv.c:2901` `if ((insn->xlen_requirement != 0) && (xlen != insn->xlen_requirement))`
- 反汇编：`opcodes/riscv-dis.c:1068-1069` 同形

故**单一字段改动同时修复汇编与反汇编两面**，无需分别处理。

**改动面已被上界证明限定在表项内**：我方现文对 `-march=rv64imac_xw` 的**解析与 arch 注册本身正常**
——同一 march 下 `c.ld`=`8861`、`c.sd`=`88e1` 两侧逐字节相同（`control` 组）。
即 march 串接受面、subset 注册、门逻辑（`xw_enabled`）在 rv64 上均已正确工作，
唯一失效点是 opcode 表的 xlen 字段。故本次改动**不需要**触碰 march 解析、属性写出、
`INSN_CLASS_XW` 门或反汇编器的 `pd->xw` 开关。

改动位点（现文实测计数）：

| 补丁片 | 添加侧 `+{... 32, INSN_CLASS_XW ...}` | 删除侧 `-{...}` | 说明 |
| --- | --- | --- | --- |
| `binutils/0002-*.patch` | **16** 行（505/506/513/514/522/523/527/528 别名 8 行；536/538/541/543 规范 4 行；552–555 SP 4 行） | — | 全部 16 个表项在此片首次落地 |
| `binutils/0007-*.patch` | 8 行 | 8 行 | 表序迁移片：把 4 SP + 4 规范行移到 XW 段（同一批行的位移，两侧须同步改） |

每行仅第二字段 `32` → `0`，共 **16 个表项 / 32 处补丁行文**（0007 的增删两侧）。gcc 面不涉及。

## 7. 原始输出指针

| 件 | 路径 |
| --- | --- |
| 逐探针判据表（runA/runB 逐字节相同） | `tmp/phase9-evidence/15.2.0/s1/run{A,B}/probes.tsv` |
| 官方侧原始 stdout/stderr/objdump/readelf 全量 | `…/run{A,B}/raw-official.log` |
| 我方侧同 | `…/run{A,B}/raw-ours.log` |
| 两侧差异逐单元 | `…/run{A,B}/side-diff.tsv` |
| must-fire 自证 | `…/run{A,B}/mustfire.tsv` |
| 侧参 provenance | `…/run{A,B}/provenance.tsv` |
| 成品对象（供逐字节复算） | `…/run{A,B}/raw/*.o` |
| mapping 符号面 | `tmp/phase9-evidence/mapping-symbols.txt` |
| p8 既有 q4 证据（本表的前身，结论一致） | `tmp/phase8-evidence/15.2.0/impl/q4-probe/` |
