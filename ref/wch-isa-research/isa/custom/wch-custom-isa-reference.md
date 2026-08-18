# WCH 自定义指令参考

目标：为 WCH 库实现指令/特性等价的开源重写，区分已证实事实、工具链行为和仍未知的硅片语义。

## 0. 证据规则与一手件

- 【手册】= 原始 PDF 明文；正文给文档名、版本、完整 SHA256 和页码。
- 【实测】= 本机工具链、字节探针或归档扫描；正文给输入范围、命令或脚本和结果。
- 【SDK】= EVT 源码、头文件或随包产物。
- 【规范】= RISC-V 官方字段/编码规范。
- 【推断】= 从前述证据推导，不能当成硬件行为。
- 抽取文本只用于检索；一手引用始终回到原始 PDF。

主要 provenance：

| 原始 PDF | 版本/页码用途 | SHA256 | 证据 |
|---|---|---|---|
| tmp/wch-evt/manual/QingKeV2_Processor_Manual.PDF | V1.3；p2、p4、p11、p13、p24–25 | 5430356218fca280023429a2516c3ac4aa200477a7fedd7d21af2f3562d70e7b | 【手册】【实测】原始 PDF 首页、页码与 `shasum -a 256` |
| tmp/wch-evt/manual/QingKeV3_Processor_Manual.PDF | V1.5；p2、p54–55 | fcc16b54d8818b04b9f8a7a7fbce6c504b87ca3787f0933edecc4da7112438d5 | 【手册】【实测】同上 |
| tmp/wch-evt/manual/QingKeV4_Processor_Manual.PDF | V1.5；p2、p11、p14–15 | b543a875a199a67091193afc16e0f7c4ec365df3b8d35bf93b4cc6546e362591 | 【手册】【实测】同上 |
| tmp/wch-evt/manual/QingKeV5_Processor_Manual.PDF | V1.0；p2、p13、p17、p36 | 0a849c719d1358856f0a5cf6409060a6fa8c3b7f501e0986cea0485b26a22a1b | 【手册】【实测】同上 |
| tmp/wch-evt/application_notes/CH32V407RM.PDF | V1.1；§9.2.1.3–9.2.1.4，physical p57–58 / printed p55–56 | 63625af9027af6abfff57a58f8d2afdb2b68ee7d31c323e407da6ea786573c56 | 【手册】【实测】同上 |
| tmp/wch-evt/application_notes/CH32H417RM.PDF | V1.7；p1、p44、p53–60 | b57ebb0c0ae2cd772d32cb9ddeb6a6315fcc3916bcd3576e5a83eaeb7dfa6967 | 【手册】【实测】同上 |
| tmp/wch-evt/application_notes/CH32X315RM.PDF | V1.1；p71、p74、p80、p83、p301、p306 | b6a752f9e9bdbb1d1fd9c8ba62f6e52633620c06c0d21fbc450925541a0c2785 | 【手册】【实测】同上 |
| tmp/wch-evt/application_notes/CH32M030RM.PDF | V1.2；p32、p45–46 | 109a7bb0ab9b7029f82f05bbf8ba212f879b32a20b00a0c3e1a8f5948629ae | 【手册】【实测】同上 |
| tmp/wch-evt/application_notes/CH32V205RM.PDF | V1.2；p76–77 | b1ed9ef040455a1f9a32f1ab9f9be0e9d3391709bc0b6fa141b2f581593b6c59 | 【手册】【实测】同上 |
| tmp/wch-evt/evt/QingkeV2C_CH32V006_EVT/EXAM/PIOC/Tool_Manual/Manual/CHRISC8B.PDF | v2B；p1、p10 | 38231bec89ea50abb7273c76f8d84adfdd0557829628ece8be8bf752e78281f5 | 【手册】【实测】同上 |
| PIOC.PDF（完整路径见 `wch-doc-provenance.md`） | 版本 1；PIOC interface/manual | 61e543eb2dcdf538deaabf40afccae53fbd8166bb2b64890112bd885da0ede43 | 【手册】【实测】原始 PDF 首页与 `shasum -a 256` |
| PIOC-EN.pdf（完整路径见 `wch-doc-provenance.md`） | Version V1；p3、p10、p12 | d8b62cd7359d53c123e52e249abc135cfa75a756833b38ca9d0e50818fcd56f4 | 【手册】【实测】同上 |

## 1. 两套不相干的指令体系

【手册】【实测】RISC-V 主核和 RISC8B/PIOC 是两套执行体系，统计和语义不能合并：

| 项 | RISC-V 侧 | RISC8B/PIOC 侧 | 证据 |
|---|---|---|---|
| 执行者 | QingKe V2/V3/V4/V5 主核 | 片上 PIOC 协处理器 | 【手册】§0 provenance 所列 core/PIOC PDF |
| 宽度 | `.a` 主语料为 16/32 位混合；ROM framing 另观察到 6–14-byte 前缀 | 16 位定长 | 【实测】`round2-binary-audit.json`；【手册】CHRISC8B v2B p1 |
| 本文自定义部分 | 当前手册/工具链可见的 XW 8 个压缩形式；4 个已命名 32 位操作，另有无官方助记符的 delay encoding | RISC8B 手册列 66 个格式 | 【手册】【实测】§3、§5、§8 的逐项证据 |
| 统计范围 | WCH ELF 归档及另列的 .o/ROM | ASM/LST/C array；不进入 RISC-V .a census | 【实测】`round2-binary-audit.json`、`round2-pioc-audit.json` |

RISC-V 讨论是第 2–7 节；RISC8B/PIOC 从第 8 节开始。

## 2. 标准扩展的边界

【手册】【规范】四份 QingKe core manual（V2 V1.3 `543035…`、V3 V1.5 `fcc16b…`、V4 V1.5 `b543a8…`、V5 V1.0 `0a849c…`，完整 SHA256 见 §0）的 PDF p1–2 ISA 字符串是主核支持矩阵的直接来源；手册未列出的逐条子集不能用先验知识补齐。Zba/Zbb/Zbs 的实际用量由第二份文档的 census 标记为【实测】；Zicsr/Zifencei 未出现在 ISA 字符串但由用法推定，仍是【推断】，不是手册明文。

【实测】四份 core manual 的 XW 关键词检索使用原始 PDF，例如：

~~~sh
pdftotext -layout tmp/wch-evt/manual/QingKeV3_Processor_Manual.PDF - |
  rg -n 'c\\.lbu|c\\.lbusp|XW|xw'
~~~

【实测】该检索和同方法的其余 core manual 没有得到 XW 位域表；这只说明所查手册未给 XW 位编码，不影响 CH32V407RM 和 QingKeV3 对 32 位非标准 encoding 的独立编码证据。

## 3. XW：当前可验证的 8 个 16 位压缩形式

【手册】`QingKeV2_Processor_Manual.PDF` V1.3，SHA256 5430356218fca280023429a2516c3ac4aa200477a7fedd7d21af2f3562d70e7b；QingKeV3 V1.5 `fcc16b…`、V4 V1.5 `b543a8…`、V5 V1.0 `0a849c…`（完整 SHA256 见 §0），四份 PDF p2 均列 `c.lbu/c.lhu/c.sb/c.sh/c.lbusp/c.lhusp/c.sbsp/c.shsp`，但未给位编码。这是当前已知清单，不是 XW 硅片全集证明。

### 3.1 槽位和操作数

【实测】由 GCC12/GCC15 fixture 和 audit-report-f/followup/tools/isa_census.py 的 dec16 交叉确认：

| 指令 | 槽位 | 操作数/立即数 | 证据 |
|---|---|---|---|
| c.lbu / c.sb | Q0/funct3=001/101 | x8–x15 基址和数据寄存器；byte offset 0–31 | 【实测】`round2-xw-audit.json` |
| c.lhu / c.sh | Q2/funct3=001/101 | x8–x15；halfword offset 0–62、步长 2 | 【实测】同上 |
| c.lbusp / c.lhusp / c.sbsp / c.shsp | Q0/funct3=100，bits[6:5] 区分 | x8–x15 与 sp；byte offset 0–15，halfword offset 0–30、步长 2 | 【实测】同上 |

【实测】半字形式要求 2-byte offset 对齐；c.lhusp/c.shsp 的立即数不是线性低位映射：uimm[1..3] 到 instruction bits[8..10]，uimm[4] 到 bit[7]。这描述的是汇编器可生成的编码约束，不单独证明每个芯片的执行语义。

关键同码 probe：

~~~sh
"MRS_Toolchain_MAC_V240/Toolchain/RISC-V Embedded GCC12/bin/riscv-wch-elf-objdump" -s -j .text \
  tmp/mrs-diff/probes/xw/mrs24/GCC12/known-c.lbu.o
~~~

【实测】结果 bytes=8821，即 little-endian halfword 0x2188。fixture 源是 `c.lbu a0,0(a1)`；GCC12 WCH objdump 对该对象显示 `.2byte 0x2188`，旧 GCC8 objdump 按标准 D 槽显示 `c.fld fa0,0(a1)`。因此 c.fld 和 c.lbu 同为 0x2188，是编码槽位冲突证据，不是两个可同时使用的压缩槽语义。

### 3.2 F/C/D/Zcb 互斥边界

【实测】组合的正确范围如下：

| 组合 | 结论 | 解释 | 证据 |
|---|---|---|---|
| C + XW | 可汇编 | XW 直接使用 C 槽位 | 【手册】【实测】core manual p2 与 EVT/GAS fixture |
| F + C + XW | 可行 | GCC multilib 与 fixture 均接受；普通 F 指令不等于 compressed F 槽 | 【实测】`rv32imafc_xw/ilp32f` 与 `qingke-custom-isa.md` §1.4 |
| D + C + XW | 不能作为完整扩展组合使用 | 四个 compressed-D 访存槽被 XW 占用；非压缩 D 指令是否可用是另一问题 | 【实测】`0x2188/0xa188` 对撞与 GAS fixture |
| Zcb + XW | 不能作为完整扩展组合使用 | Q0/f4 的同名访存形式编码冲突；未重叠的 Q1 形式不因此消失 | 【实测】Zcb `0x8188` 与 XW `0x2188` |
| Zcmp/Zcmt + XW | 不能无条件组合 | Q2/f5 等已有冲突；必须按实际重叠形式处理，不能假定完整扩展可用 | 【实测】`qingke-custom-isa.md` §1.4 槽位 fixture |

【实测】直接证据是 c.fld/c.lbu=0x2188、c.fsd/c.sb=0xa188，以及 c.fld fixture 的 GAS 诊断。不要把“静默禁用”写成硬件行为；对重叠的 c.fld 形式，汇编器可报非法 operands，objdump 也可能按当前 ISA 选择标准名字。Zcb 的不重叠 Q1 zext/sext/mul 形式不能由 Q0/f4 冲突推成整体不可用。

【实测】同名异码必须写进解码器测试：标准 Zcb 的 c.lbu a0,0(a1) 是 0x8188，WCH XW 同一源句是 0x2188。助记符相同不代表编码或芯片能力相同。

## 4. XW 版本标签和差集效力

### 4.1 标签是 passthrough，不是能力证明

【实测】下列三种标签均接受同一 c.lbu 源句；编码相同：

~~~sh
for tag in xw xw2p2 xw3p0; do
  printf '.text\n.option rvc\nc.lbu a0,0(a1)\n' |
    "MRS_Toolchain_MAC_V240/Toolchain/RISC-V Embedded GCC12/bin/riscv-wch-elf-as" \
    -march=rv32imac_$tag -mabi=ilp32 \
    -o /dev/null /dev/stdin
done
~~~

三次 exit=0；已有 xw1p0 object 的 .text 也是 8821。独立全量 fixture 在 GCC12/GCC15、xw/xw1p0/xw2p0/xw2p2/xw3p0 五个标签下均为 8,704 cases、0 mismatch、同一 stream SHA256 d3a6a0647389d3aee2661916eb420ca58da4a29b8e59bdfb3626b8c810651a05。【实测】这证明工具链标签透传和当前可生成编码相同，不证明硬件语义相同。

### 4.2 组数必须带统计单位

【实测】独立 parser 得到的 archive attribute group：

| 来源范围 | physical | content group | xw2p2 | xw2p0 | 未声明 XW 版本 | 证据 |
|---|---:|---:|---:|---:|---:|---|
| EVT | 49 | 23 | 12 | 0 | 11 | 【实测】`round2-xw-audit.json` `corpus.archives` |
| MRS24 | 168 | 100 | 31 | 4 | 65 | 【实测】同上 |
| MRS25 | 94 | 64 | 19 | 0 | 45 | 【实测】同上 |
| 合计 | 311 | 187 | 62 | 4 | 121 | 【实测】同上；这里是全部组，不等于 XW 使用组 |

表中的 121 表示没有可用的 XW 版本声明，不等于“没有 `.riscv.attributes`”：`round2-xw-audit.json` 的 `corpus.attribute_presence` 记录后者是 71 个内容组，另有 50 组存在属性节但没有 XW 版本标签。libwchnet.a 必须按芯片树分别计：V407/H417 的样本是 xw2p2，V203/V20x/V317 的样本无可用 XW 版本属性；basename 不能合并。【实测】实际出现 XW 的 100 组另分为 xw2p2=62、xw2p0=4、版本未声明=34；对应 distinct word 为 1,971、9、1,130。这些 distinct 数不是 content-group 数。

### 4.3 差集的效力边界

【实测】在 311 个 .a 的 executable PROGBITS/SHF_EXECINSTR 范围，xw2p2 的 1,971 distinct XW words 全在本机 1.0 可生成集合内，差集 0；全量 GAS 可生成 8,704 distinct words。1.0 已占满其他四槽，只有 Q0/funct3=4 仍有判别力，共 1,536 个可检测 pattern，当前归档中零命中。

【推断】这排除“在该可检测范围内出现本机不能生成的新编码”，不能排除 2.2 在相同编码上的语义变化，也不能给 q0/f4 的 1,536 个未命中 pattern 下硅片语义结论。

## 5. 32 位非标准操作：4 个已命名形式，另有 delay encoding

【实测】assembler 有四个已命名形式：`mcpy/wexti/mrslu/mrsl`。【手册】QingKeV3/CH32V407RM 另定义一类无官方助记符的 delay encoding，完整出处见 §5.3。本文不再用“共 4 条”涵盖 delay。

### 5.1 mcpy

【手册】CH32V407RM V1.1，SHA256 63625af9027af6abfff57a58f8d2afdb2b68ee7d31c323e407da6ea786573c56，§9.2.1.4，PDF physical p58/printed p56：bits[31:27]=rs3、[26:25]=reserved 00、[24:20]=rs2、[19:15]=rs1、[14:12]=func3=111、[11:7]=funct5=00000、[6:0]=func7=0001111。按【规范】字段位置，末字段是 opcode；正文保留手册原字段名并注明该勘误。

【实测】`mcpy a0,a1,a2` 的 bytes=`0f70b560`，即 word `0x60b5700f`；汇编文本第一、二、三个操作数分别进入 rs1、rs2、rs3，字段为 rs1=10、rs2=11、rs3=12、funct3=7、opcode=15。固定字段和寄存器位位置与手册一致。

【手册】【SDK】【实测】但手册的地址角色文字与随包接口冲突：CH32V407RM p58 写 rs1=目标、rs2=起始、rs3=结束；四份 `core_riscv.h` 的 `ASM_MCPY(DA,SA,EA)` 却发射 `mcpy EA,SA,DA`，即 rs1=EA、rs2=SA、rs3=DA。CH587 ROM 的三参数包装先做 `a2 += a1`，再发射 `mcpy a2,a1,a0`，同样支持 SDK 顺序。【推断】等价重写应采用已出货 SDK/ROM 的 `EA,SA,DA` 约定，并把手册 rs1/rs3 地址角色列作勘误；若按手册角色列交换 rs1/rs3，会把源结束与目的地址装反并可能向错误地址写入，属于数据破坏风险。尚未做硅片行为测试。

【手册】同一 §9.2.1.4 明确 all addresses have no alignment requirement。因此 CH32V407RM 范围内不应把地址对齐列为未知。未确认项仅包括区间端点闭合性、完成时 SA/DA 的精确值、粒度、可中断性和其他芯片是否复用同一语义。

【SDK】【实测】`core_riscv.h` 的 `ASM_MCPY(DA,SA,EA)` 约束显示 SA/DA 被改写、EA 只读；这仍不能推出所有芯片的微架构时序。

### 5.2 wexti、mrslu、mrsl

【实测】这些是工具链可接受的独立形式，使用 custom-0 相关字段；【SDK】core_riscv.h 提供融合移位/乘移接口。【手册】QingKeV3_Processor_Manual.PDF V1.5，SHA256 fcc16b54d8818b04b9f8a7a7fbce6c504b87ca3787f0933edecc4da7112438d5，PDF p54（印刷 p53）仅给 V3B 的 MRS 线索，不给 mrsl/mrslu/wexti 完整 bit table，不能把手册线索扩大为全部语义。

### 5.3 delay

【手册】QingKeV3 V1.5，SHA256 fcc16b54d8818b04b9f8a7a7fbce6c504b87ca3787f0933edecc4da7112438d5，PDF physical p55/printed p54 给 delay：bits[31:20]=imm、[19:15]=rs1、[14:12]=001、[11:9]=match、bit8=div、bit7=sel、[6:0]=0001011。CH32V407RM V1.1，SHA256 63625af9027af6abfff57a58f8d2afdb2b68ee7d31c323e407da6ea786573c56，§9.2.1.3、physical p57/printed p55 给对应 custom delay 表。QingKeV3 手册明确要求 mimpid≥3。

【实测】当前 GCC12/GCC15 没有 delay 助记符；需要 .insn 手工编码。sel=1 时 rs2 的确切位置和官方助记符仍未知。

## 6. 自定义 CSR、HPE 与器件边界

### 6.1 CSR 同址异义必须按具体文档

【手册】逐文档 ledger 的结果：

| 地址 | 文档中出现的名字 | 范围 | 证据 |
|---|---|---|---|
| 0x804 | HW_POPDM_CTLR | CH32X315RM V1.1 `b6a752…` p83；CH32V407RM V1.1 `63625a…` p67；CH32H417RM V1.7 `b57ebb…` p52 | 【手册】原始 PDF；完整 SHA256 见 §0 |
| 0x804 | INTSYSCR | 例：CH32M030RM V1.2 `109a7b…` p45；CH32V205RM V1.2 `b1ed9e…` p76；完整逐文档表见 `wch-doc-instr-reg-findings.md` §2.1 | 【手册】原始 PDF；完整 SHA256 见 §0 |
| 0xBC0 | CORECFGR/CPU_RUN_CTLR 等 | M030 p45–46、V205 p76–77、V407 p70–71、X315 p74/p80、H417 p54–60；版本和完整 SHA256 见 provenance | 【手册】原始 PDF |

【手册】不能把 0x804/0xBC0 按“V3F/V3V/V5F 一律同名”归纳。上述原始 PDF 表列出 0x00000001、0x00000000、0x12370000、0x12370300 四种复位值；这是逐手册结果，不是硬件读回实测，也不能合并成单一默认值。

### 6.2 H417 的批号条件拆开

【手册】CH32H417RM V1.7，SHA256 b57ebb0c0ae2cd772d32cb9ddeb6a6315fcc3916bcd3576e5a83eaeb7dfa6967，PDF p1 对 memory protection 给出批号条件；p53–54 对 trigger 分核说明：core-0 的 TSELECT/TDATA1/2 有批号条件，core-1 有四个 trigger。旧稿“PMP 与全部硬件断点都由第五位决定”删除，改为逐核逐功能陈述。

### 6.3 HPE/VTF

【手册】【实测】QingKeV2 V1.3 `543035…` PDF p13、V3 V1.5 `fcc16b…` p22–23、V4 V1.5 `b543a8…` p14–15、V5 V1.0 `0a849c…` p17（完整 SHA256 见 §0）给出不同 HPE 布局；GCC12 fixture 显示 fast interrupt 的整型寄存器由硬件保存，启用 F 时浮点寄存器仍由软件保存。V2 48-byte frame 中手册只解释 40 bytes，剩余 8 bytes 未知。命令和反汇编见 `qingke-custom-isa.md` §4.2。

## 7. WFE、`fence.i` 与器件边界

【手册】CH32V407RM V1.1，SHA256 63625af9027af6abfff57a58f8d2afdb2b68ee7d31c323e407da6ea786573c56，PDF p101；CH32X315RM V1.1，SHA256 b6a752f9e9bdbb1d1fd9c8ba62f6e52633620c06c0d21fbc450925541a0c2785，PDF p71：`PFIC_SCTLR.WFITOWFE` 使后续标准 `wfi` 按 WFE 行为执行。现有文档没有公开一个可直接发射的独立 `wfe` opcode。

【手册】以下四份参考手册明确要求屏蔽中断后追加 `fence.i`：CH32FV2x_V3xRM V2.5，SHA256 6bdc58b159a95c40e815eb9973df1f7e7309b08e8018bad1991a71c792cefb95，PDF p95；CH32L103RM V2.2，SHA256 27a1b969cb2cb99d296ac562cac134ec63d52e4f0c75cf9d6bad7c696bc66fe3，p57；CH32M030RM V1.2，SHA256 109a7bb0ab9b7029f82f05bbf8ba212f879b32a20b00a0c3e1a8f5948629ae，p32；CH32V003RM V1.9，SHA256 7a6bf439ecd68e0b87ffdd6765da2ef9b1796ce16084b7d1f25a658380c3bcfe，p37。结论只覆盖这四份已核对手册。

## 8. RISC8B/PIOC

【手册】CHRISC8B v2B，SHA256 38231bec89ea50abb7273c76f8d84adfdd0557829628ece8be8bf752e78281f5，p1 列 66 个 16-bit 格式；独立 PIOC 轮次的 15 个 LST 实际覆盖 39/66，另 27 个无样本。【实测】因此可以说“手册列出 66、当前样本观测到 39”，不能说 66 条均已由二进制逐条验证。

【手册】CHRISC8B v2B，SHA256 38231bec89ea50abb7273c76f8d84adfdd0557829628ece8be8bf752e78281f5，PDF p10 §8.6：OTP ROM 原则上只能烧录一次，建议关键模块前预留 NOP，以便将来替换为跳转等指令。【SDK】RGB1W.ASM 与 C array 的 NOP/word 对齐例子与此一致。等价重写不能把这种 NOP 作为普通冗余优化删除。

【实测】PIOC 与 RISC-V 的频率统计分开；RISC8B 的 27 个未采样格式、WASM53B 在当前 macOS 上的动态执行结果都未确认。39 个已采样格式的静态直方图见 `round2-pioc-audit.json`。

## 9. 未确认清单

1. 【推断】XW q0/funct3=4 的 1,536 个未命中 pattern 的硅片语义。
2. 【推断】XW 1.0/2.0/2.2 在相同可检测编码上的语义差异。
3. 【推断】custom major、MRS/wexti、mrsl/mrslu 的完整硬件支持和异常行为。
4. 【推断】delay sel=1/rs2、精确时序和跨核一致性。
5. 【推断】mcpy 的端点、完成时 SA/DA、粒度、可中断性、SDK 顺序的硅片行为复核，以及 CH32V407RM 之外的对齐语义。
6. 【推断】WCH-X 的完整规范；CH32H417RM V1.7 `b57ebb…` PDF p44 只有概述。
7. 【推断】ROM 中 mixed code/data 的其他 custom-like fingerprint 是否可达；CH587 `0x40968 mcpy` 是已确认的局部反汇编证据。
8. 【推断】PIOC 27 个无样本格式、事务原子性和精确 cycle phase。
9. 【实测】`tmp/wch-riscv` 514 PDFs、MRS 19 PDFs、`tmp/upstream` 3 PDFs 只做路径盘点，逐页审查仍是覆盖盲区。

## 10. 手册勘误与内部矛盾

1. 【手册】【规范】CH32V407RM V1.1 `63625a…` PDF p57–58 把 bits[6:0] 标成 `func7`；按字段位置应解释为 opcode。
2. 【手册】QingKeV2 V1.3 `543035…` PDF p24–25 的 marchid Serial 描述与示例冲突；QingKeV5 V1.0 `0a849c…` p36 有同类复位值冲突。
3. 【手册】QingKeV2 V1.3 `543035…` p11、QingKeV4 V1.5 `b543a8…` p11 把 `0xE000E04C` 表头写作 `PFIC_CFGR`，同页语义对应 `PFIC_GISR`。
4. 【手册】QingKeV5 V1.0 `0a849c…` p13 的 `PFIC_EWUPR` 表格误写为 `PFIC_EENR/0xE000EC84`。
5. 【手册】QingKeV3 V1.5 `fcc16b…` p11–12 与 p54 对 V3B `PFIC_IPRIOR` 位宽冲突；当前材料按 p54 的 V3B=[7:6] 处理。
6. 【手册】QingKeV2 V1.3 `543035…` 表 7-1 把 `intsyscr` 标为 URW，而同手册 §3.2 标 MRW；不能据单表外推用户态可写。
7. 【手册】【规范】QingKeV5 V1.0 `0a849c…` 表 8-1 把 `0xBC2–0xBC8/0xBD0/0xFC0` 称为标准 CSR；它们是厂商自定义地址/功能。
8. 【手册】CH32X315RM V1.1 `b6a752…` p15/p43/p301/p306 对 IWDG 时钟源写出 LSI/HSI 冲突；CH32X035RM V1.9，SHA256 c7e301eac4790ca1ba112f946bf057139ec7f36be28e142cafc1c286bcc9daa4，p13/p23/p234 一致使用 HSI/1024，是不同芯片证据。
9. 【手册】CH32V407RM V1.1 `63625a…` PDF p62 的 MISA 表值与 p63–64 的 M 字段复位说明冲突；保留原表值并标注冲突，不把推断写成硬件读回。完整 SHA256 见 §0。
10. 【手册】【SDK】【实测】CH32V407RM V1.1 `63625a…` PDF p58 把 rs1/rs3 地址角色写为目标/结束，而四份 `core_riscv.h` 和 CH587 ROM 一致采用 rs1=EA、rs3=DA；固定编码位无冲突，角色文字按已出货 SDK/ROM 约定处理。完整 SHA256 见 §0。

## 11. 复现索引

~~~sh
python3 audit-report-f/followup/tools/isa_census.py selftest .
python3 audit-report-f/followup/tools/isa_census.py control
python3 audit-report-f/followup/tools/isa_census.py provenance
python3 tmp/isa-research-codex/round2_verify.py
~~~

【实测】编码、全量 XW、ROM、PIOC 和文档审计的既有可读产物分别在 tmp/isa-research-codex/round2-xw-audit.json、round2-binary-audit.json、round2-pioc-audit.json、round2-doc-audit.json；引用时以原始 PDF 和本机命令为证据源，不以抽取 .txt 代替。
