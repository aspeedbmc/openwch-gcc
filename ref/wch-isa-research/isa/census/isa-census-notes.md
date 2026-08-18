# RISC-V 指令普查(ISA census)方法与结果说明

对 WCH 交付的二进制库做纯静态指令统计。本文是二进制侧的来源账本,与文档侧的 `wch-doc-provenance.md`
对应:凡引用本轮数字,必须能指回「哪个文件、哪代工具、什么时候跑的」。

## 来源与可复算

- **采集日期**:2026-08-03;**仓库根** `/Users/apple/Projects/gccriscv-wch`,以下路径均相对该根
- **脚本**:`audit-report-f/followup/tools/isa_census.py`
  sha256 `a4cd4d32c25e3ef338ee1659ddcd6fc096b2c9ce3f7b43ed8fe40f3a76828ee3`
- **哈希算法**:SHA-256(`shasum -a 256`);表中 archive 取**前 16 位**,全量值可用该命令复算

| 工具 | 用途 | 版本首行 |
|---|---|---|
| `python3` | 运行脚本 | `Python 3.14.6`(`/opt/homebrew/opt/python@3.14/bin/python3.14`) |
| `.../RISC-V Embedded GCC12/bin/riscv-wch-elf-as` | 自检 fixture | `GNU assembler (xPack GNU RISC-V Embedded GCC arm64) 2.38` |
| `.../RISC-V Embedded GCC12/bin/riscv-wch-elf-objdump` | **交叉对照实际所用** | `GNU objdump (xPack GNU RISC-V Embedded GCC arm64) 2.38` |
| `.../RISC-V Embedded GCC15/bin/riscv32-wch-elf-objdump` | 仅记录,未用于对照 | `GNU objdump (GNU Binutils) 2.45` |

工具前缀均为 `MRS_Toolchain_MAC_V240/Toolchain/`;fixture 用 `-march=rv32imac_zba_zbb_zbc_zbs_xw -mabi=ilp32`。

**两代 objdump 必须区分**:对 V317 `libwchnet.a` 实测,GCC12(2.38)把无法解码的 XW 打成 30 行
`.2byte`,GCC15(2.45)打成 30 行 `.insn`;两者指令行数(28,420)与误报的 `fld`/`fsd` 数(2,244)
相同。凡引用「objdump 未解码行数」必须写明是哪一代;本文所有对照数字均出自 **GCC12 / 2.38**。

复算命令(`S=audit-report-f/followup/tools/isa_census.py`,顺序即依赖顺序):`python3 $S provenance`
→ `selftest .`(fixture 自检)→ `control`(正控制)→ `scan`(出两张 TSV)→ `xcheck <a.a>`
(objdump 对照)→ `xwdiff .`(XW 版本差分)。两张 TSV 开头都重复了同一份 provenance 注释块。

## 方法

对每个 `.a` 顺序遍历全部 ar 成员(不按名字去重覆盖),对 32 位小端 ELF 的每个 `SHF_EXECINSTR
+ SHT_PROGBITS` 节做线性扫描:低 2 位 `!=3` 取 16 位,`==3` 取 32 位,低 5 位 `==0x1F` 的更长
编码保守前进 2 字节并计入 `unknown`。每条指令解出「类别 + 助记符」。

XW(`xw2p2`)占用的 RVC 槽位,由本机汇编器 fixture 反推确认:

| 槽位 | 助记符 | 标准 RVC 原槽 |
|---|---|---|
| 象限 0,funct3=1 / 5 | `c.lbu` / `c.sb` | `c.fld` / `c.fsd` |
| 象限 2,funct3=1 / 5 | `c.lhu` / `c.sh` | `c.fldsp` / `c.fsdsp` |
| 象限 0,funct3=4,bits[6:5]=0/1/2/3 | `c.lbusp`/`c.lhusp`/`c.sbsp`/`c.shsp` | RVC 保留槽 |

当前 GAS/四本 core manual 可见的 XW 清单共 8 个形式,与本轮 fixture 一致;这不证明 XW 硅片全集没有其它形式。**主统计不走 objdump**:有
`.riscv.attributes` 时 objdump 拒解 XW;无该节时它回落到含 D 的默认 ISA,把同样的半字**静默**解成
`fld`/`fsd`。objdump 只用于交叉对照。

## 自检:三项**全部通过**

1. **汇编器 fixture —— 通过**。汇编 140 条指令,期望编码由汇编器产出(不手写):标准 RVC 27 条、
   标准 32 位 97 条(含 Zba/Zbb/Zbc/Zbs 全套与 `mcpy`)、XW 16 条(8 助记符 × sp/非 sp 与不同
   偏移),逐条助记符全对,0 处不符。
2. **`GetChipID` 正控制 —— 通过**。`QingkeV4B_CH32V203_EVT/EXAM/ETH/NetLib/libwchnet.a` 的
   `eth_api.o/.text.GetChipID` 被脚本解出且恰好四条:`lui(RVI) lhu(RVI) andi(RVI) c.jr(RVC-std)`
   —— 第四条编码 `0x8082` 即 `c.jr ra`,也就是反汇编里显示的 `ret`(本脚本一律输出规范名 `c.jr`,
   不输出别名 `ret`)。
3. **XW 计数 —— 6 项全中**:`libCH58xBLE.a`=5592、`LIBMESHROM.a`=1750、V317 `libwchnet.a`=2274、
   V317 `libwchnet_float.a`=2274、`LIBMESH.a`=0、`libwchble.a`=0。槽位定义先由汇编器 fixture 独立
   反推确定,再跑对照,**没有为了对上数字反过来调整槽位定义**。

## 覆盖口径

| 范围 | 物理 `.a` | 内容组(sha256) | ELF 成员 | 可执行节字节 | 指令数 |
|---|---|---|---|---|---|
| evt | 49 | 23 | 549 | 1,309,880 | 441,551 |
| mrs24 | 168 | 100 | 332 | 1,057,510 | 361,968 |
| mrs25 | 94 | 64 | 296 | 982,856 | 334,378 |
| 合计 | **311** | **187** | **1,177** | **3,350,246** | **1,137,897** |

`isa-census.tsv` 每行带内容组代表的 `sha256_16`,开头 `#` 注释行给出每组代表覆盖的全部物理路径;
去重跨 basename:`libMESH.a` 与 `LIBMESH.a` 字节相同,归同一组。

**明确排除 RISC8B / PIOC**:那是与 RISC-V 无关的另一套 16 位指令集,本脚本只解 RISC-V 侧。实测
其资产不在扫描面内 —— 扫到的 311 个 `.a` 无一路径命中 `pioc|risc8b`,1,177 个成员里也没有任何
名字含 `pioc|risc8` 的节(可执行或非可执行都没有);PIOC 素材以 `.ASM` 源码和 `EXAM/PIOC/` 下的
`PIOC_*_CODE` 数组形式存在,不是 archive,不会进入线性扫描。

## 全局类别分布

| 类别 | 次数 | 占比 | 助记符数 | | 类别 | 次数 | 占比 | 助记符数 |
|---|---|---|---|---|---|---|---|---|
| RVC-std | 581,094 | 51.07% | 26 | | system | 227 | 0.02% | 4 |
| RVI | 484,396 | 42.57% | 36 | | unknown | 198 | 0.02% | 1 |
| RVM | 46,200 | 4.06% | 8 | | RVF | 79 | 0.01% | 13 |
| **XW** | **19,344** | **1.70%** | **8** | | RVC-F | 35 | <0.01% | 4 |
| Zbb | 3,247 | 0.29% | 8 | | Zicsr | 4 | <0.01% | 2 |
| Zba | 2,401 | 0.21% | 3 | | Zbs | 672 | 0.06% | 7 |

**本次 `.a` 扫描零命中**:`RVA`(原子)、`Zbc`、`Zb?`、`RVD`、`custom-32` 为 0 次 —— Zbc 虽在多个 multilib 的
attributes 里被声明,实际一条 `clmul*` 都没用到。`system` 227 次(`ebreak` 120、`fence.i` 102、
`mret` 4、`ecall` 1),`Zicsr` 仅 4 次(`csrrs` 2、`csrrw` 2)。

## XW 实际使用情况

`c.lbu` 9,011 · `c.sb` 3,942 · `c.lhu` 3,435 · `c.sh` 1,709 · `c.sbsp` 551 · `c.shsp` 370 ·
`c.lbusp` 184 · `c.lhusp` 142,合计 19,344(evt 18,775 / mrs24+mrs25 569),100 个内容组用到。

象限 0/funct3=4 那组(4 条 sp-relative 形式)共 1,247 次,占 XW 的 6.4%;漏掉该槽
会少算这一整块。用量最大:`libCH58xBLE.a` 5592、V407/H417 `libwchnet.a` 各 2320、V317
`libwchnet.a` 与 `libwchnet_float.a` 各 2274、`LIBMESHROM.a` 1750、V203 `libwchnet.a` 1137;
其余 TOUCH/UHSIF/IQMath 类在 10~250 量级,MRS 侧每个 `_xw` multilib 变体 6~13 条。

## 专项:库里的 XW 2.2 是否用到了 1.0 之外的编码

**动机**:随包汇编器比库旧。GCC12 的 `as -march=rv32imac_xw` 默认产出 `xw1p0`,而语料里凡声明 XW
版本的 archive 无一是 1.0(EVT 12 组全是 `xw2p2`,MRS GCC15 有 4 组 `xw2p0`)。更关键的实测:该
汇编器**只有一张 XW 指令表** —— `-march=..._xw1p0/xw2p0/xw2p2` 产出的 `.text` **逐字节相同**,连
并无硬件版本证据的 `xw3p0` 标签也照收(版本号仅透传进 attributes)。所以本机 fixture **只覆盖本机这一张已知 XW 表**;
若 2.2 新增了编码点,解码器会按 1.0 语义静默解错。故做如下差分。

**方法**(`xwdiff` 子命令):① 用 `-march=rv32imac_xw1p0` 穷举 8 条 XW 助记符的全部合法操作数组合
(寄存器逐一试探得 x8–x15;立即数 `c.lbu`/`c.sb` 0–31、`c.lhu`/`c.sh` 0–62 步长 2、四条 sp 形式
0–15 与 0–30 步长 2),GAS 拒绝的行自动剔除,得 **8,704 个 distinct 编码 = 本机已知 8 形式的完整可生成集合**;
② 枚举各 archive 落在 XW 五槽的全部 distinct 编码;③ 按声明版本分组做集合差。

**结论:差集为空 —— 三组全部 0。**

| 声明版本 | 内容组 | 槽位指令数 | distinct 编码 | 在 1.0 集合内 | **不在 1.0 集合内** |
|---|---|---|---|---|---|
| `xw2p2` | 62 | 11,633 | 1,971 | 1,971 | **0 种 / 0 次** |
| `xw2p0` | 4 | 28 | 9 | 9 | **0 种 / 0 次** |
| 版本未声明 | 34 | 7,683 | 1,130 | 1,130 | **0 种 / 0 次** |

**这个结论的效力边界(必须一并读)**:每个槽位有 2^11 = 2,048 个编码点,五槽共 10,240。XW 1.0
已经把 q0/f3=1、q0/f3=5、q2/f3=1、q2/f3=5 四个槽**各占满 100%**,只有 q0/f3=4 槽 1.0 仅用 512 个
(25%),留下 1,536 个「一旦出现即可判定为 1.0 之外」的编码点。也就是说:

- 本差分**只在 q0/f3=4 槽具备判别力**,而 xw2p2 组在该槽用到 151 个 distinct 编码,**全部落在
  1.0 的 512 个之内**,那 1,536 个可判别点一个都没碰(xw2p0 组 5 个、未声明组 134 个,同样全部在内)。
- 另外四个槽已被 1.0 占满,2.2 若在那里改动只能是**对既有编码重新赋予语义**,任何字节级普查
  都无法发现 —— 这不是本方法的疏漏,是方法本身的上限。
- 若 2.2 把新指令放在 XW 五槽**之外**,本差分也看不到;本次 311 个 `.a` 的 executable sections 中
  `unknown` 只有 `0x0000` 一种,仅说明当前 decoder 在该范围没有其它 raw 编码(仍无法排除新指令占用了某个可正常解码的标准槽)。

**版本未声明**(没有可用的 XW 版本属性,版本不可知,单列一栏):其中确实用到
XW 的是 `LIBMESHROM.a` 1750、V317 `libwchnet.a` 与 `libwchnet_float.a` 各 2274、V203 `libwchnet.a`
1137,加 MRS 侧 `_xw` multilib 的 30 组小量;它们同样零个 1.0 之外的编码。

**与背景清单的差异**:背景给的 `xw2p2` EVT archive 是 10 个,实测为 **12 个内容组** —— 多出 V407 与
H417 的 `libwchnet.a`(各 2320 条 XW)。同一 basename `libwchnet.a` 在不同芯片树里分属两类:
V407/H417 声明 `xw2p2`,V203/V317 无 attributes,故按 basename 列清单会漏。

## 32 位非标准目标 encoding:本次 `.a` 范围 0 条

custom 空间(`0x0b`/`0x2b`/`0x5b`/`0x7b`)与 `0x0f`(MISC-MEM,WCH 把 `mcpy` 放在此处 funct3=7)
在 1,137,897 条指令里都没有出现非标准编码;`0x0f` 只有 `fence`/`fence.i`,已归 `system`。

补充原始字节复查覆盖全部 40 个物理 IQmath archive:精确小端串 `0f 70 b5 60` 为 0、反向字节串
`60 b5 70 0f` 为 0,并对任意逐字节偏移的 4 字节 little-endian 窗口应用
`(word & 0x06007fff) == 0x0000700f`(rs1/rs2/rs3 任意),结果仍为 0。可复算账本见
`round2-binary-audit.json` 的 `archives.iqmath_raw_mcpy_scan`。先前关于 IQmath 非执行数据命中的记载
无法复现,已撤回;上段 executable-section 零使用结论不依赖该错误佐证。

## 与 objdump(GCC12 / 2.38)的交叉对照

对全部 187 个内容组逐个跑 `objdump -d`(远超要求的 3 个)。核心恒等式**无一例外成立**:
「objdump 未解码行(`.2byte`)+ objdump 报出的 `fld`/`fsd` 行 = 本脚本 XW 数」,全局
12,112 + 7,232 = 19,344。

| archive | 有 attributes | 本脚本 | objdump 行 | 未解码 | 报成 fld/fsd | 本脚本 XW |
|---|---|---|---|---|---|---|
| `LIBMESHROM.a` (V203) | 否 | 37,320 | 37,320 | 272 | **1,478** | 1,750 |
| `libwchnet.a` (V317) | 否 | 28,420 | 28,420 | 30 | **2,244** | 2,274 |
| `libwchnet_float.a` (V317) | 否 | 28,360 | 28,360 | 30 | **2,244** | 2,274 |
| `libwchnet.a` (V203) | 否 | 14,210 | 14,210 | 15 | **1,122** | 1,137 |
| `libwchnet.a` (V407/H417) | 是 | 28,188 | 28,188 | 2,320 | 0 | 2,320 |
| `libCH58xBLE.a` | 是 | 67,262 | 67,262 | 5,592 | 0 | 5,592 |
| `libwchble.a` | 否 | 75,859 | 75,857 | 0 | 0 | 0 |

读法:**无 attributes 的库里 objdump 一共把 7,232 条 XW 报成了 `fld`/`fsd`**(evt 7,088 + mrs 144),
不带任何标记;剩下的 XW(evt 11,687 + mrs 425)落在象限 0/funct3=4 这个 RVC 保留槽,objdump 只能打
`.2byte`。有 attributes 时 objdump 把全部 XW 打成 `.2byte`,一条也不误解 —— 两种失效模式的定量确认。

指令总数:本脚本 1,137,897 条 vs objdump 1,137,755 行,差 142 行,全部来自 objdump 对节尾连零的
折叠(一段连零里前几个仍按 `unimp` 逐行打印,只折叠尾巴成一行 `...`),不涉及任何解码分歧。

**助记符级对照**(比条数对照更强):把「编码值 → 助记符」当纯函数比对,取 evt 全部 23 组加
mrs24 前 30 组共 39,834 个不同编码,94.34% 助记符完全相同;其余观察到的差异均可归为 objdump 的
XW 局限(XW → `.2byte` 或幻影 `c.fld`/`c.fsd`),另有 1 个编码 `0x0000` 本脚本记 `unknown`、objdump 记
`c.unimp`。这说明该对照范围内没有发现新的分类分歧；objdump 与本脚本若共享同一错误语义，仍不能由此排除。

## unknown 表

`isa-census-unknown.tsv` 共 57 行、198 次,**只有 1 种编码 `0x0000`**(RVC 定义的非法编码,
objdump 记 `c.unimp`),观察位置均为节尾对齐填充;在当前 311 个 `.a`、`SHF_EXECINSTR`、线性 framing
和 decoder 范围内未见其它 raw 编码或 ≥48 位前缀。该表对本次扫描输出完备:每个不同编码值一行,
含首次出现的成员与「节+偏移」;它不证明未扫描 ROM/独立对象或硬件重定义的标准外观编码不存在。

## 已知限制

1. **线性扫描,无控制流分析**。可执行节里若混入数据会被当成指令。实测 unknown 只有 0x0000
   一种，只说明当前 decoder 未把其它字节标成 raw；能解成标准外观的混入数据不会被该指标发现。
2. **XW 槽位判定是无条件的**,会覆盖标准 `c.fld`/`c.fsd`/`c.fldsp`/`c.fsdsp`。前提已核实:本次 `.a` 语料
   1,177 个成员的 `.riscv.attributes` 里最高只出现 `f2p0`、**无一声明 `d`**,故不存在被误判的真
   RVC-D 指令;把本脚本用于含 D 的对象时该前提失效。
3. **Zmmul 与 M 在编码上不可分**(`mul` 编码相同),统一记 `RVM`(attributes 显示大量成员实际
   只声明 `zmmul1p0`)。同理 `Zicsr`/`Zifencei` 按编码归类,不看 attributes。
4. **同 archive 内同名重复成员按两份计**(各占一份代码)。例:V317/V407/H417 的 `libwchnet.a` 为
   56 成员 / 28 唯一名,每名两次。
5. **背景里「无 `.riscv.attributes` 的 EVT archive 有 10 个」实测应为 11 个内容组**:除给定的 9 组
   (`libMESH.a` 与 `LIBMESH.a` 同组)外,`libwchnet.a` 的 V203 与 V317 两份也没有该节,V407/H417
   的则有。本次 `.a` 语料无该节的内容组共 71 个 / 167 个物理路径。
6. **不解析立即数与寄存器**,只做助记符普查(XW 与 custom 无法确定助记符时输出编码特征串);
   计数是**静态出现次数**,不代表运行时执行频率。
7. `libwchble.a` 有一个成员名带空格(`ll_periodic .o`),ar 解析按原样保留;用 `\S+` 之类的正则
   匹配 objdump 成员标题会错配,写对照脚本时需注意。
