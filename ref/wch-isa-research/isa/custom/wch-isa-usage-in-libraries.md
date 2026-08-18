# WCH 交付物中的指令使用实况

本文回答“当前仓库中的 WCH 交付物实际使用了哪些指令”。统计结果按 `.a`、独立 `.o`、ROM HEX 和 RISC8B/PIOC 样本分开报告；任何“零使用”只在紧邻写明的扫描范围内成立。

> 路径均相对仓库根 `/Users/apple/Projects/gccriscv-wch`。指令语义和编码见 `wch-custom-isa-reference.md`。

## 0. 方法、命令和自检

【实测】`.a` 主统计由 `audit-report-f/followup/tools/isa_census.py` 对 ELF `SHF_EXECINSTR + SHT_PROGBITS` 节做线性 RISC-V framing，不以 objdump 的助记符作为分类基线。结果为 `audit-report-f/followup/results/isa-census.tsv`；方法、输入和限制为 `isa-census-notes.md`。

复算顺序：

```sh
S=audit-report-f/followup/tools/isa_census.py
python3 "$S" provenance
python3 "$S" selftest .
python3 "$S" control
python3 "$S" scan
python3 "$S" xwdiff .
```

【实测】三项自检均通过，详细输出保存在 `isa-census-notes.md` 的“自检”节：

| 自检 | 期望 | 实际 | 判定 | 证据 |
|---|---|---|---|---|
| GAS fixture | 140 条标准/XW/`mcpy` fixture 与汇编器期望编码一致 | 140/140，0 mismatch | 通过 | 【实测】`python3 audit-report-f/followup/tools/isa_census.py selftest .` |
| `GetChipID` 正控制 | `eth_api.o/.text.GetChipID` 解出 `lui/lhu/andi/c.jr` | 恰为四条，末条 `0x8082=c.jr ra` | 通过 | 【实测】`python3 audit-report-f/followup/tools/isa_census.py control` |
| XW 六库计数 | 5,592 / 1,750 / 2,274 / 2,274 / 0 / 0 | 六项全部相等 | 通过 | 【实测】`selftest .` 的 `xw` 项与 `isa-census.tsv` |

【实测】第二轮独立验证入口：

```sh
python3 tmp/isa-research-codex/round2_verify.py
python3 tmp/isa-research-codex/round2_xw_audit.py
python3 tmp/isa-research-codex/round2_binary_audit.py
python3 tmp/isa-research-codex/round2_pioc_audit.py
find tmp/isa-research-codex -maxdepth 1 -name 'round2-*.json' -print0 | xargs -0 -n1 jq empty
```

## 1. `.a` 归档统计范围

【实测】下表只覆盖 EVT 与 MRS 2.4/2.5 的归档，数据来自 `isa-census.tsv` provenance 和 `isa-census-notes.md`：

| 来源 | 物理 `.a` | sha256 内容组 | RISC-V ELF 成员 | 可执行节字节 | 静态指令 | 证据 |
|---|---:|---:|---:|---:|---:|---|
| EVT | 49 | 23 | 549 | 1,309,880 | 441,551 | 【实测】`isa-census.tsv` provenance |
| MRS 2.4 | 168 | 100 | 332 | 1,057,510 | 361,968 | 【实测】同上 |
| MRS 2.5 | 94 | 64 | 296 | 982,856 | 334,378 | 【实测】同上 |
| 合计 | **311** | **187** | **1,177** | **3,350,246** | **1,137,897** | 【实测】`isa-census-notes.md`“覆盖口径”复算 |

【实测】同名 archive 的不同芯片构建按 sha256 内容组分别统计；同 archive 内同名重复成员也按实际成员顺序保留。PIOC 素材是 `.ASM`/C array，不在这 311 个归档内；路径与成员名检查均未发现 PIOC archive。证据为 `isa-census-notes.md` 的“覆盖口径”节。

### 1.1 `.a` 类别分布

【实测】下表由 `isa-census.tsv` 第 206 行后的数据按 category 求和复算：

| 类别 | 次数 | 占比 | 当前解码到的助记符数 | 证据 |
|---|---:|---:|---:|---|
| RVC-std | 581,094 | 51.07% | 26 | 【实测】`isa-census.tsv` category 汇总 |
| RVI | 484,396 | 42.57% | 36 | 【实测】同上 |
| RVM | 46,200 | 4.06% | 8 | 【实测】同上 |
| **XW（当前已知 8 形式）** | **19,344** | **1.70%** | **8** | 【实测】同上；独立核对见 `round2-xw-audit.json` |
| Zbb | 3,247 | 0.29% | 8 | 【实测】`isa-census.tsv` category 汇总 |
| Zba | 2,401 | 0.21% | 3 | 【实测】同上 |
| Zbs | 672 | 0.06% | 7 | 【实测】同上 |
| system | 227 | 0.02% | 4 | 【实测】同上 |
| unknown | 198 | 0.02% | 1 | 【实测】同上；位置见 `isa-census-unknown.tsv` |
| RVF | 79 | 0.01% | 13 | 【实测】`isa-census.tsv` category 汇总 |
| RVC-F | 35 | <0.01% | 4 | 【实测】同上 |
| Zicsr | 4 | <0.01% | 2 | 【实测】同上 |

【实测】`unknown` 仅为 `0x0000×198`，当前 objdump 称 `c.unimp`，首次位置账本在 `isa-census-unknown.tsv`。这个阴性结论只适用于上述 311 个 `.a` 的 `SHF_EXECINSTR` 节、当前线性 framing 和当前 decoder；可执行节若混入数据、硬件若重定义一个可正常解码的标准编码，均不会由“unknown=198”自动发现。

## 2. 零命中必须按范围读取

【实测】下表中的“0”只指第 1 节的 311 个物理 `.a` / 187 内容组，不包括独立 `.o`、ROM HEX、未来 SDK 或实际芯片动态路径：

| 类别 | `.a` 中结果 | 方法边界 | 证据 |
|---|---:|---|---|
| 已命名 WCH 32 位操作和 delay 目标 encoding | 0 | 仅 executable sections；`mcpy` 位于 MISC-MEM `0x0f/funct3=7`，另扫 custom majors | 【实测】`isa-census.tsv` custom-32 汇总与 `round2-binary-audit.json` |
| RVA | 0 | 当前 decoder 的原子指令集合 | 【实测】`isa-census.tsv` RVA 汇总 |
| Zbc | 0 | attributes 中虽可声明 Zbc，但 `clmul*` 静态次数为 0 | 【实测】`isa-census.tsv` Zbc 汇总 |
| RVD | 0 | 归档 attributes 未声明 D；XW 还占用压缩 D 访存槽 | 【实测】`isa-census.tsv` RVD 汇总与 attribute ledger |

【实测】补充对全部 40 个物理 IQmath archive 的原始字节复查：逐字节搜索精确小端串 `0f 70 b5 60` 为 0，反向字节串 `60 b5 70 0f` 为 0；再把每个 4 字节窗口按 little-endian 解码，以 `(word & 0x06007fff) == 0x0000700f` 放开 rs1/rs2/rs3，仍为 0。账本为 `round2-binary-audit.json` 的 `archives.iqmath_raw_mcpy_scan`。先前关于 IQmath 非执行数据命中的记载不可复现，已撤回；`.a` 的指令级零命中仍由 executable-section 扫描独立成立。

【实测】第二轮另扫 1,108 个独立 `.o`：822 个是 little-endian RISC-V（726 ELF32+96 ELF64），其 executable `SHT_PROGBITS` 中目标 custom/mcpy pattern 为 0，XW 为 42。该结论只覆盖这 822 个对象和 `round2-binary-audit.json` 所列 section。

【SDK】【实测】ROM 不是零：CH587 BLE ROM HEX（sha256 `34f1d44af3e418d8825e5e2e63989c9566ed06a98942ddac7364ee53978e903d`）在 `0x40968` 有 `50b6700f mcpy a2,a1,a0`，前有三个参数检查与地址加法，后接 `ret`。证据为 `round2-binary-audit.json` 和以下复现：

```sh
"MRS_Toolchain_MAC_V240/Toolchain/RISC-V Embedded GCC15/bin/riscv32-wch-elf-objdump" \
  -D -b ihex -m riscv:rv32 --start-address=0x40958 --stop-address=0x40980 \
  tmp/wch-evt/evt/QingkeV3C_CH587_EVT/EXAM/BLE/LIB/CH587BLE_ROMx.hex
```

【推断】因此“32 位非标准操作可以先不管”只在“重写第 1 节 `.a` 且不包含 ROM”时成立；只要目标包含 CH587 ROM 等价行为，`mcpy` 就是必须处理的指令。

## 3. XW 的实际使用

【实测】`.a` 中当前已知 8 个 XW 形式全部出现；“全部”只指工具链/手册列出的这 8 个形式，不宣称 XW ISA 没有其它形式：

| 助记符 | 次数 | 助记符 | 次数 | 证据 |
|---|---:|---|---:|---|
| `c.lbu` | 9,011 | `c.sbsp` | 551 | 【实测】`isa-census.tsv` XW mnemonic 汇总 |
| `c.sb` | 3,942 | `c.shsp` | 370 | 【实测】同上 |
| `c.lhu` | 3,435 | `c.lbusp` | 184 | 【实测】同上 |
| `c.sh` | 1,709 | `c.lhusp` | 142 | 【实测】同上 |

【实测】合计 19,344，其中 EVT 18,775、MRS 569；100 个内容组出现 XW。Q0/funct3=100 的四个 sp 形式合计 1,247，占 XW 6.4%。来源为 `isa-census.tsv` 和 `round2-xw-audit.json`。

【实测】代表性库计数：`libCH58xBLE.a` 5,592；V407/H417 `libwchnet.a` 各 2,320；V317 `libwchnet.a` 与 `libwchnet_float.a` 各 2,274；`LIBMESHROM.a` 1,750；V203 `libwchnet.a` 1,137。逐路径/sha256 在 `isa-census.tsv`。

## 4. XW 版本标签与差集边界

【实测】版本计数必须同时写出语料范围和筛选条件，不能把 EVT、全语料与“实际出现 XW”三种口径混写：

| 口径 | `xw2p2` | `xw2p0` | 无可用 XW 版本声明 | 说明 | 证据 |
|---|---:|---:|---:|---|---|
| EVT 全部 23 个内容组 | 12 | 0 | 11 | 11 组没有 `.riscv.attributes`；其中 4 组实际出现 XW | 【实测】`round2-xw-audit.json` `corpus.archives` |
| EVT+MRS 全部 187 个内容组 | 62 | 4 | 121 | 121 表示未声明 XW 版本；其中 71 组没有 `.riscv.attributes`，另 50 组有该节但没有 XW 版本标签 | 【实测】同上 `corpus.attribute_presence` 与逐组字段 |
| EVT+MRS 中出现 XW 的 100 组 | 62 | 4 | 34 | 次数分别为 11,633 / 28 / 7,683 | 【实测】同上，按 XW occurrence>0 过滤 |

【实测】`xw2p0` 的 4 是内容组数；9 是这 4 组中出现的 distinct XW 编码数。逐组数据来自 `round2-xw-audit.json` `corpus.archives`。

【实测】本地已知 8 形式穷举得到 8,704 个 distinct halfword。与语料求差：

| 分组 | 内容组 | 语料 distinct | 不在本地集合内 | 证据 |
|---|---:|---:|---:|---|
| `xw2p2` | 62 | 1,971 | 0 种 / 0 次 | 【实测】`round2-xw-audit.json` version scope/diff |
| `xw2p0` | 4 | 9 | 0 种 / 0 次 | 【实测】同上 |
| 版本未声明且出现 XW | 34 | 1,130 | 0 种 / 0 次 | 【实测】同上 |

【实测】【推断】差集零的效力边界必须与结果一起保留：Q0/f3=1、Q0/f3=5、Q2/f3=1、Q2/f3=5 四槽已被本地 1.0 形式占满，只有 Q0/f3=4 剩余 1,536 个可判别点；当前语料对这些点命中 0。该方法不能发现其它槽的语义重定义、XW 五槽外的新编码或语料未触发的行为。

## 5. objdump 的两种失效方式

【实测】对 187 个内容组逐组成立：

```text
GCC12 objdump 未命名 XW 12,112
+ 被误解为 fld/fsd 的 XW 7,232
= 原始解码器 XW 19,344
```

【实测】因此恒等式为 `12,112 + 7,232 = 19,344`；逐内容组数据见 `isa-census-notes.md`。

【实测】有可用 XW attributes 时 GCC12 多打印 `.2byte`；没有 attributes 时会回落到含 D 的默认解释，把部分 XW 静默打印为 `c.fld/c.fsd/c.fldsp/c.fsdsp`。完整逐组表在 `isa-census-notes.md`。

【实测】无 attributes 的 `LIBMESHROM.a` 可直接复现：objdump 的 fld/fsd 行为 1,478，未命名 272，原始 decoder 的 XW 为 1,750，满足 `272+1,478=1,750`。

```sh
"tmp/mrs-2.5/WCH/Toolchain/RISC-V Embedded GCC/bin/riscv-none-embed-objdump" \
  -d -M no-aliases \
  tmp/wch-evt/evt/QingkeV4B_CH32V203_EVT/EXAM/BLE/MESH/MESH_LIB/LIBMESHROM.a |
awk '$0 ~ /[[:space:]]c?\.(fld|fsd)(sp)?[[:space:]]/ {n++} END {print n+0}'
```

【推断】因此不能以 `.2byte/.insn` 的数量判断 XW 是否存在，也不能把软浮点库中成千上万的 `fld/fsd` 不加检查地当作真实 D 扩展。

## 6. RISC8B/PIOC 样本使用

【手册】`CHRISC8B.PDF` v2B，SHA256 `38231bec89ea50abb7273c76f8d84adfdd0557829628ece8be8bf752e78281f5`，PDF p1–10 定义 66 个 16 位格式。【实测】`round2-pioc-audit.json` 对 15 个程序 LST 的 7,307 条非 `DW` 行逐条套用 mnemonic-specific mask：failure=0、unknown mnemonic=0；实际只出现 39/66 格式，另 27 格式无随包样本。

【实测】30 个 ASM 文件由 15 个程序和 15 个 EQU-only `PIOC_INC.ASM` 构成；程序的 ASM→LST mnemonic 15/15、LST→BIN 15/15、C array→BIN 15/15，BIN/C 总词数均为 7,346。`WASM53B.EXE` 没有在当前 macOS 环境执行，所以这是随包产物静态闭环，不是重新动态组装 66 格式。

【手册】【SDK】`RGB1W` 样本中 word 2–3 的 `NOP=0x0000`、word 4 的 `JMP 0x025=0x6025` 与 word 37 落点一致。手册出处为 `CHRISC8B.PDF` v2B、SHA256 `38231bec89ea50abb7273c76f8d84adfdd0557829628ece8be8bf752e78281f5`、PDF p2/p9；样本散列见 `wch-doc-provenance.md`。

【手册】`CHRISC8B.PDF` v2B、SHA256 `38231bec89ea50abb7273c76f8d84adfdd0557829628ece8be8bf752e78281f5`、PDF p10 对 OTP 目标建议预留全零 NOP 作为后续跳转补丁位。【推断】面向该类 OTP 目标的重写不得把预留 NOP 一概优化掉；非 OTP 目标不能仅凭此句外推同一物理限制。

## 7. 对等价重写的决策

### 必须支持

1. 【实测】若重写第 1 节的 `.a`，必须支持当前语料实际出现的 8 个已知 XW 形式，尤其 1,247 条 sp 形式。
2. 【实测】同一 `.a` 范围实际使用 RVI/RVC/RVM、Zba/Zbb/Zbs；具体次数见第 1 节。是否需要 RVF/RVC-F 取决于所选内容组，不能按全局汇总盲目启用或禁用。
3. 【SDK】【实测】若范围包含 CH587 ROM，必须处理已确认的 `mcpy@0x40968`。
4. 【手册】【实测】若目标是通用 RISC8B 兼容实现，手册定义的 66 格式都是规格输入；若只复现当前 15 个样本，至少 39 个已出现格式必须支持，27 个未采样格式仍应列为未验证而非零使用。手册出处为 `CHRISC8B.PDF` v2B、SHA256 `38231bec89ea50abb7273c76f8d84adfdd0557829628ece8be8bf752e78281f5`、PDF p1；实测账本见 §6。
5. 【手册】面向 OTP PIOC 目标时保留 NOP 补丁位语义；出处为同一 `CHRISC8B.PDF` v2B、相同 SHA256、PDF p10。

### 仅在明确范围内可后置

1. 【实测】只重写第 1 节 `.a` 且排除 ROM/独立对象时，已命名 32 位 WCH 操作和 delay encoding 在该范围静态次数为 0；这不是硬件不存在。
2. 【实测】Zbc/RVA/RVD 在第 1 节 `.a` 中为 0；若项目还要编译新代码或覆盖其它交付物，必须重新评估。
3. 【推断】WCH-X、MRS 精确语义等不能用“当前语料未触发”代替规格，相关缺口见参考文档 §9。

### 分析陷阱

1. 【实测】不要把 objdump 当 XW 存在性基线；见第 5 节。
2. 【实测】不要按 basename 合并 archive；V407/H417 与 V203/V317 的 `libwchnet.a` 属不同内容组/属性类别。
3. 【实测】不要用 attributes 推断实际用量；Zbc 声明但 `.a` 中静态次数为 0。
4. 【实测】不要用 archive 原始字节搜索代替 executable-section framing；40 个 IQmath archive 的原始字节复查为零，而 CH587 ROM 有真实 `mcpy`，两者范围不同。
5. 【手册】【SDK】【实测】重写 `mcpy` 不可按 V407RM 的角色文字直译；随包接口与 ROM 使用 `EA,SA,DA`。交换 rs1/rs3 会装反源结束和目的地址，存在数据破坏风险。
6. 【实测】archive 内同名成员可能重复；普通 `ar x` 会覆盖，扫描器按成员顺序解析。

## 8. 未覆盖与限制

| 事项 | 当前状态 |
|---|---|
| XW 1.0/2.2 硅片语义差异 | 【推断】字节差分只在 1,536 个点有判别力；没有行为规格 |
| 独立 `.o` | 【实测】第二轮覆盖 822 个 RISC-V 对象；不是所有历史/外部对象 |
| ROM | 【实测】5 个物理 HEX/3 内容组已做 framing；只有 CH587 `mcpy` 有清楚局部执行流，data-like custom words 可达性未定 |
| RISC8B 逐格式动态接受 | 【实测】39 格式有样本，27 无样本；WASM53B 未在本环境执行 |
| PIOC 多字节原子性/时序 | 【推断】手册只闭合单寄存器优先级和部分握手 |
| 函数级语义 | 【实测】当前主统计是静态分布，不是调用频率或逐函数行为分析 |
| 额外 PDF | 【实测】`tmp/wch-riscv` 514、MRS 19、`tmp/upstream` 3 只做路径盘点 |
