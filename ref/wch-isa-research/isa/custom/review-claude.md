# WCH 自定义指令两份文档评审报告(评审者:claude)

- 评审日期:2026-08-04
- 被审对象:`isa-research-claude/`(两份成稿 + 四份素材 + 一手件账本)、`isa-research-codex/`(独立复查轮 `findings.md`、`round2-review.md`)
- 评审方式:全程只读;所有关键实测在本机亲手重跑(命令与输出见 §3);除本文件外未改动任何文件,未 git commit。

## 1. 结论

| 对象 | 结论 |
|---|---|
| `wch-custom-isa-reference.md` | **REWORK**(2 项,R2、R5;整体质量高,缺陷局部) |
| `wch-isa-usage-in-libraries.md` | **REWORK**(4 项,R1–R4;统计主体全部复现无误,缺陷在个别佐证与建议措辞) |

**对 `isa-research-codex/` 复查质量的评价**:其**测量结果可靠**——我亲手复现的每一项(CH587 ROM `0x40968` `mcpy`、全语料 xw2p2 62 组、1,971 个 distinct 编码、GCC15 `__riscv_xw=2000000`)全部成立;但其"对第一轮的修正(13 项)"**大部分修正的是 codex 自己的前一轮,不是 `isa-research-claude/`**,且至少 3 项(#1、#11、#12)若读作对 claude 轮的修正则**判断有误**(逐条裁定见 §2.4)。采信 codex 的数字,但不要按其"修正"标签直接扣在 claude 成稿上。

触发 REWORK 的判据:复核清单第 1 条(一条【实测】记载不可复现,R1)与第 6 条("凡声明了 XW 版本的都是 xw2p2"是被证伪的全称句,R2);第 7 条("可以先不管"清单含已证实有使用的指令,R4,清单定义的最严重类别)。清单第 3 条(sp 形式)、第 4 条(效力边界)、第 5 条(自检写实)三道门**全部通过**。

## 2. 返工清单

### R1(最高优先)|`wch-isa-usage-in-libraries.md` §2|`mcpy` 假阳性佐证不可复现

- **问题**:"它的字节序列 `0f 70 b5 60` 在 3 个 IQmath 库里确实出现过,但位置在 `.rodata.atan2PUTable` 内"(同源:`audit-report-f/followup/results/isa-census-notes.md` 第 147 行)。
- **证据**:我对语料内**全部 40 个物理 IQmath 库**(MRS 2.4 + MRS 2.5 + EVT,含 GCC8/GCC12/GCC15 全部 multilib)做了三种搜索:①字面序列 `0f 70 b5 60`——0 次;②大端变体 `60 b5 70 0f`——0 次;③mcpy 掩码窗口(`(w & 0x06007FFF) == 0x700F`,任意操作数、**逐字节偏移**)——0 次。`atan2PUTable` 节名本身在这 40 个库里都存在,但其中没有任何 mcpy 形态的字。
- **影响**:零使用的**结论**不受影响(反而更强:连数据巧合都没有);但一条标为【实测】的具体记载查无实据,直接击穿第 1 条证据链纪律。
- **改法**:删除该句,或给出可复现命令重新推导;若最初命中的是别的字节形态/别的文件集,如实改写并附命令。`isa-census-notes.md` 对应行同步修。

### R2 |`wch-custom-isa-reference.md` §3.4 与 `wch-isa-usage-in-libraries.md` §4|版本声明计数是 EVT-only 口径,却写成全语料;"凡声明皆 xw2p2"被证伪

- **问题**:两处均称"WCH 交付的库里,凡声明了 XW 版本的都是 `xw2p2`(按内容组计 12 个);另有 11 个内容组没有 `.riscv.attributes` 节"。
- **证据**(我对 187 个代表 archive 逐个跑 `readelf -A` 复算):全语料声明 `xw2p2` 的是 **62 个**内容组(EVT 恰 12);**另有 4 个组声明 `xw2p0`**(MRS 2.4 内 GCC15 自带 multilib 的 libprintf/libprintfloat/libshlib/libshflib——成因已实测:GCC15 把 `_xw` 规范化为 2.0,`__riscv_xw=2000000`);无属性节的是 **71 个**内容组(EVT 恰 11)。素材 `isa-census-notes.md` 第 106、120–122 行本来就记对了(62/4/EVT 12),是成稿压缩时把 EVT-only 数字放大成了全称。
- **连带**:usage §4 结果句自己就引用了"`xw2p0` 组",与两行之前"凡声明版本的都是 `xw2p2`"**同节自相矛盾**;且"`xw2p0` 组(9 个)"的"9"是 distinct 编码数(实为 4 组 / 28 次 / 9 个 distinct),与背景句"(12 个内容组)"单位不一致,极易误读成 9 个组。
- **改法**:按 notes 的表改写:全语料 xw2p2 62 组 / xw2p0 4 组 / 未声明 34 组(XW 使用者中),无属性 71 组;需要讲 EVT 侧的地方明确加"EVT 侧"限定。`libwchnet.a` 按芯片树分家的表述(V407/H417=xw2p2、V203/V20x/V317 无属性)我已逐组核对,**正确,保留**。

### R3 |`wch-isa-usage-in-libraries.md` §5|"无 `.riscv.attributes`(11 个内容组)"同为 EVT-only 误标;"不留任何标记"过度概括

- **证据**:notes 第 166 行明确 7,232 条误报 = evt 7,088 + **mrs 144**——MRS 的无属性组同样参与,"11 个"不成立(应 71 个,或注明 EVT 11)。另外我实测 V203 `libwchnet.a`(无属性):GCC15 objdump 把 1,122 条 fld/fsd 槽位形式**静默错解**(fld 786 + fsd 336,恰等于该库 c.lbu/c.sb/c.lhu/c.sh 计数和),但 **4 条 sp 形式共 15 条仍以 raw(`.insn`)呈现**——"静默错解、不留任何标记"只对 fld/fsd 槽位形式成立,sp 形式在无属性对象里仍是可见失败。
- **改法**:计数改 71(或标注 EVT-only);"不留任何标记"限定到 fld/fsd 槽位的四条助记符。恒等式本身(12,112 + 7,232 = 19,344)与逐库分解我抽验通过,保留。

### R4 |`wch-isa-usage-in-libraries.md` §7"可以先不管"第 1 条|custom-32 的缓建建议缺 ROM 警示——清单定义的最严重错误类别

- **问题**:"4 条 32 位自定义指令——交付库中零使用……当前二进制里用不到"。".a 语料零使用"本身为真(§0/§8 也诚实给了范围与未覆盖清单),但 **CH587 BLE ROM 镜像 `0x40968` 处确有一条 `mcpy`**(codex 发现,我已复现:`50b6700f mcpy a2,a1,a0`,前有三个参数非零检查与 `add a2,a2,a1`,后接 `ret`,是标准 memcpy 形态,控制流清晰)。ROM 镜像正是 §8 列为"未统计"的交付物;读者按 §7 建议跳过 mcpy,重写 CH587 BLE ROM 等价物时必挂。
- **改法**:§7 该条追加"ROM 镜像不在统计内,且 CH587 BLE ROM 已证实含 `mcpy`(见 §8);若重写范围含 ROM 常驻代码,`mcpy` 不可跳过",或把 `mcpy` 单独挪到"坑"一节。

### R5 |`wch-custom-isa-reference.md` §4.1 / §10|`mcpy` 操作数角色:手册字段表与 SDK/ROM 用法**互相矛盾**,两轮均未点出(本评审新发现)

- **证据**:`CH32V407RM V1.1 (63625af9027af6ab)` §9.2.1.4 字段表写 **rs1[19:15] = 目标地址、rs3[31:27] = 结束地址**;而 SDK `core_riscv.h` 的 `ASM_MCPY`(`"mcpy %2, %0, %1"`,%0=SA,%1=DA,%2=EA)给出 **rs1=EA(源结束)、rs2=SA、rs3=DA(目的)**——rs1/rs3 角色正好互换。CH587 ROM `0x40968` 的现场可裁定:`add a2,a2,a1`(end = src+len)后执行 `mcpy a2,a1,a0`(a0=目的、a1=源、a2=源结束),**与 SDK 一致、与手册字段描述相反**。手册 §9.2.1.4 的"描述"列应判为勘误(与其 `func7`/`func5` 字段命名错误同源的粗疏)。
- **影响**:成稿 §4.1 声称"编码获得了独立互证……逐位一致"——互证覆盖的只是 opcode/funct3/固定位,**不含操作数角色**;把 rs1/rs3 语义装反的重写会把"目的起始"当"源结束"用,属数据破坏级错误。
- **改法**:§4.1 明写两来源的角色分配矛盾及 ROM 现场裁定(SDK 侧胜);§10 勘误清单加一条;"逐位一致"限定为"编码骨架逐位一致,操作数角色以 SDK+ROM 为准"。

### R6(裁量)|两份成稿 §0 口径|"内容组(按 sha256 去重)"实为**分来源**去重

- 187 = evt 23 + mrs24 100 + mrs25 64(按 (来源, sha256) 计);全局 sha 去重是 **122**——65 个内容组在 mrs24/mrs25 各计一次。"100 个内容组用到 XW"同口径(全局 66)。数字都能复算、两轮口径一致,但"按 sha256 去重"的字面含义是全局去重,应补一句"跨来源同内容分别计"。

### R7(裁量)|`wch-custom-isa-reference.md` §1 表|"仅 1 份芯片手册给了 2 条 32 位指令的编码"易误读

- 字面为真("芯片手册"= chip RM,不含内核手册),但读者易理解成"全部文档中仅此一份"。§4.3 自己就引了 `QingKeV3` 附录 1 的完整延时位表。建议在 §1 表格处加括注"(内核手册另有 QingKeV3 附录 1 延时位表,见 §4.3)"。

### 2.4 两轮冲突的逐条裁定

| # | 冲突 | 裁定 |
|---|---|---|
| 1 | codex 头号"新增":QingKeV3 V1.5 PDF p55 有完整 delay 编码表,"'只有 CH32V407RM 给出 32-bit custom 编码'错误" | **相对 claude 轮不成立**。claude 成稿 §4.3 明写"QingKeV3 手册附录 1 亦有位表,要求 mimpid ≥ 3";素材 `qingke-custom-isa.md` §2.3 已整表转录(第 54–56 页,注明已图像复核)。"只有 V407RM"这句话 claude 从未说过——codex 修正的是它自己的前一轮。 |
| 2 | codex #10:"custom-32 全语料零使用"全局说法错误,CH587 ROM 有 `mcpy` | **实质成立**(我已复现 ROM `mcpy` 与其控制流)。但 claude 的原句带明确范围(".a 语料"+§8 未覆盖清单),错的不是事实句而是 §7 的建议(→R4)。 |
| 3 | codex #11:"批号第五位决定 PMP 与硬件断点"应拆分,"p1 只条件化 memory protection" | **codex 此条作为对 claude 的修正不成立**。H417 手册明文:"内核 0(RISC-V3F)的 PMP 功能仅适用于批号第五位不为 0 的芯片"+ TSELECT/TDATA1/TDATA2 三条同款注释(内核 0 = V3F,手册 4.1 节明确);claude 原句本来就限定"V3F 内核",从未外推到 V5F。codex 说"p1 只条件化 memory protection"反而漏了 PMP 章节里的明文注释。 |
| 4 | codex #12:CSR 0x804 不可按内核名外推,须逐文档账本 | **无实际冲突**。codex 自己的账本(X315/V407/H417=`HW_POPDM_CTLR`,其余=`INTSYSCR`)与 claude §5.1 的按代次表逐一对应(X315=V3F、V407=V3V、H417=V5F、V205=V3B→INTSYSCR 侧)。作为审慎提醒可取,作为"修正"标签误导。 |
| 5 | 计数 12 vs 62(xw2p2 内容组) | **codex 对**(全语料 62);claude 的 12 是 EVT-only 误标(→R2)。这是 codex 数字对 claude 成稿构成实质修正的唯一一处。 |
| 6 | codex #2–#9、#13(`.insn` 穷举规模、版本标签抽样、PIOC 直方图 MOVA/RETURN、`.o` 466→822、ROM framing、schematic 可读性) | 全部针对 **codex 自己第一轮**的方法缺陷;claude 成稿与素材中不存在被修正的对应表述(如 claude 从未给过 MOVA=182、466 个 `.o`、`0x07f805fb` 候选)。 |

**codex 真正的新增**(claude 轮确实没有、有价值):两代汇编器 × 5 标签 × 8,704 全量一致性(把 claude 的 3 点抽样升级为穷举);xw2p2 的 1,971 词操作数分布;RISC8B 66 格式中仅 39 个有随包样本(27 个无样本——把 claude §9 第 10 条的"未逐条对撞"量化了);PIOC-EN 同址写 host 优先/握手方向;独立 `.o` 822 个中 XW 42 次、custom 0;ROM 变长 framing 与 `mcpy@0x40968`。这些应在返工时并入两份成稿(标注 codex 来源)。

## 3. 亲手复现记录

工具链:仓库内 MRS GCC12(`riscv-wch-elf-*`,binutils 2.38)与 GCC15(`riscv32-wch-elf-*`,binutils 2.45)。

| # | 实验 | 结果 |
|---|---|---|
| 1 | `c.lbu a0,0(a1)`(`-march=rv32imac_xw`,GCC12 as)与 `c.fld fa0,0(a1)`(`rv32imafdc`) | **同为 `0x2188`** ✓;`-march=rv32imafdc_zicsr_xw` 被接受,此时显式写 `c.fld` 报 illegal operands(XW 胜出)✓ |
| 2 | `mcpy a0,a1,a2` | `0x60b5700f` ✓;`-march=rv32i` 同样接受(无门控)✓;与 V407RM §9.2.1.4 的 opcode `0001111b`/funct3 `111b` 逐位一致 ✓ |
| 3 | `_xw`/`_xw2p2`/`_xw3p0` 三个标签 | 编码均 `0x2188`,attributes 分别 `xw1p0`/`xw2p2`/`xw3p0` 原样透传 ✓;GCC15 `-march=rv32imac_xw` 宏 `__riscv_xw=2000000` ✓(codex 2.3 成立) |
| 4 | 普查数字(从 `isa-census.tsv` 9,246 数据行复算) | 总指令 1,137,897 ✓;12 个类别计数**逐格全中**;XW=19,344、8 助记符逐条一致、EVT 18,775/MRS 569、sp 形式 1,247=6.4%、XW 大户库前 7 名全部一致 ✓;187 组=分来源 (scope,sha) 口径、XW 使用组=100 ✓(全局 sha 去重则为 122/66,→R6) |
| 5 | objdump 恒等式抽验(V203 `libwchnet.a`,无属性节) | GCC15 objdump 总行 14,210 = 普查该组总数 ✓;fld 786+fsd 336=1,122 = 普查四条非 sp 形式之和 ✓;raw 15 = 四条 sp 形式之和 ✓;1,122+15=1,137 与文档所载该库 XW 数一致 ✓ |
| 6 | 正控制 `GetChipID` | `lui/lhu/andi/ret(c.jr)` 四条 ✓ |
| 7 | §3.2 编码样例与操作数约束 | 8 个样例编码全中(`31bc/3de8/3dea/8788/80a8/87a8/87e8/8048`);`a6`、奇数半字立即数、`c.lbusp` imm=16 均被拒 ✓;`c.lhusp` 乱序立即数逐位验证 ✓ |
| 8 | Zcb 同名异码 | GCC15 `-march=rv32imac_zcb` 下 `c.lbu a0,0(a1)` = `0x8188` ✓ |
| 9 | F+C+XW | 官方 multilib `rv32imafc_xw`(GCC12)、`rv32imafcxw`(GCC8)目录实存 ✓ |
| 10 | CH587 ROM `mcpy`(codex 复现命令) | `0x40968: 50b6700f mcpy a2,a1,a0`,上下文 = 三参数非零检查 + `add a2,a2,a1` + `ret`(memcpy 形态);相邻 `0x4096e` 是 memset 形态 ✓ |
| 11 | SDK `ASM_MCPY` | V407 `core_riscv.h`:`"mcpy %2, %0, %1"`,%0=SA/%1=DA/%2=EA → rs1=EA/rs2=SA/rs3=DA,与手册字段表 rs1=目标矛盾(→R5) |
| 12 | RGB1W 产物(claude 自附命令) | 1,358 字节=679 词、word4=`6025`、w[37]=`5E1C` ✓ |
| 13 | 40 个物理 IQmath 库三种方式搜 mcpy 字节 | 全部 0 命中(→R1) |
| 14 | 187 个代表 archive 逐个 `readelf -A` | xw2p2=62(EVT 12)、xw2p0=4、无属性=71(EVT 11)(→R2/R3) |
| 15 | 【手册】引用抽查(超过要求的 3 条) | V407RM §9.2.1.4 位表 ✓;QingKeV3 附录 1 延时位表与 CSR 0x8C0 ✓;四份内核手册 XW 仅一行助记符清单、无编码 ✓;H417 批号注释(PMP + TSELECT/TDATA1/TDATA2,内核 0=V3F)✓;V2 手册 marchid "青稞V2系列固定为数字4" ✓;`PFIC_GISR`/`PFIC_CFGR` 同址双名(V2、V4)✓。PDF sha256 抽验 2 份(QingKeV3、V407RM)与账本一致 ✓ |

## 4. 抽查覆盖声明

- **查了**:上表全部;两份成稿全文;素材 `wch-doc-provenance.md`、`wch-pioc-risc8b-findings.md` 全文,`qingke-custom-isa.md`、`wch-doc-instr-reg-findings.md`、`wch-evt-pdf-instr-reg-index.md` 定向抽读(mcpy/延时/勘误/66 条表相关段落);codex 两份文档全文;`isa-census-notes.md` 定向抽读;全称句全文扫描(两份成稿)。
- **没查**:RISC8B 66 条指令表的逐条位编码抄录质量(成稿 §9 第 10 条自己已声明未逐条对撞,codex 给出 39/27 有无样本的量化,我未第三次重做);codex 的 5 个 round2 脚本未逐个重跑(只复现了其关键结论:ROM mcpy、GCC15 宏、62 组、1,971 distinct 由两轮独立得出且与我第 14 项复算互证);全语料恒等式 12,112+7,232 未对 187 组逐组重跑(抽 1 组分解验证 + 两轮独立同数);HPE/中断、CSR 位域、USER 选择字节等第 5–7 节内容仅抽 H417 批号与 0x804 两点;ROM 镜像与独立 `.o` 未自行普查(采信 codex 并抽验其最强结论);`WASM53B.EXE` 未运行(两轮亦均未运行)。

## 5. 值得保留的优点(返工时勿动)

1. **证据分级纪律与一手件账本**:五级标记贯穿全文,sha256+版本+页码的引用格式实测可直接定位;"抽取文本不作一手件"的纪律在成稿中确被执行。
2. **Q0/funct3=100 槽整组收录**(§3.1)并把"最易漏"讲透——这正是本清单第 3 条的一票否决点,过了。
3. **XW 版本号透传 + 差集效力边界**(ref §3.4 + usage §4):"差集为 0 只在 q0/f3=4 槽有判别力、1,536 个可判别点未碰"这段是全文最诚实的一段,第 4 条一票否决点,过了。
4. **objdump 恒等式与两种失败模式的区分**(usage §5):经我逐库分解验证成立,是给后续所有分析者的关键方法学警告(仅按 R3 修计数与"无标记"措辞)。
5. **三项自检写实**(usage §0):文档所述与 notes 记录一致,我独立复现其中两项。
6. **两套指令体系的强制分离**(ref §1)与 PIOC 侧文档陷阱(名不副实的 `PIOC User Manual-EN.pdf`)、OTP/NOP 补丁位约束(ref §8.5 / usage §6)——第 7 条清单要求的 RISC8B 补丁位警告明确在位。
7. **同址异义 CSR、批号陷阱、ESIG 地址例外**(ref §5.1/§7):抽验无误,且"见到 `csrrs 0x804` 先定内核代次"的操作性表述优于按文档逐本罗列。
8. **手册勘误清单**(ref §10):抽验两条全部属实;返工时按 R5 增补 mcpy 操作数角色一条即可。
