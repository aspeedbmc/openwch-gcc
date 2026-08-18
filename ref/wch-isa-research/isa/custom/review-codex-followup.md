# WCH 自定义 ISA 研究终稿独立审查

审查者：Codex

日期：2026-08-04（Asia/Tokyo）

结论：**REWORK**

审查对象：

- isa-research-claude/wch-custom-isa-reference.md
- isa-research-claude/wch-isa-usage-in-libraries.md

独立轮次评价：**可靠，且关键修正可复现**（见第 7 节）。

本文件是本轮唯一新增的审查输出。按 review-wch-custom-isa-prompt.md 的约束，本轮没有修改上述两份终稿、来源文档、脚本、原始 PDF 或既有中间产物，也没有执行 Git commit。

## 1. 审查范围、方法和工作树状态

阅读和核对了：

- review-wch-custom-isa-prompt.md 全文；
- 两份待审终稿；
- isa-research-claude/ 中的来源、文档 provenance 和 Findings；
- isa-research-codex/findings.md、isa-research-codex/round2-review.md 及 tmp/isa-research-codex/round2-*.json、脚本和页面图；
- audit-report-f/followup/tools/isa_census.py、audit-report-f/followup/results/isa-census.tsv；
- 原始 CH32V407RM、QingKeV3、CHRISC8B 和 PIOC PDF 的直接 pdftotext 输出，并对三个关键页面作了图像复核。

本轮开始时 git status --short --branch 的首行是：

~~~
## main
~~~

工作树此前已有大量用户/既有轮次修改和新增文件，例如 isa-research-codex/、tmp/isa-research-codex/、tmp/mrs-diff/ 等；本轮不清理、不回滚、不覆盖这些改动。开始时没有发现已有 isa-research-review-*.md 审查输出，因此使用本文件名作为本轮独立产物。

文档行数核对结果：

~~~
99  review-wch-custom-isa-prompt.md
269 isa-research-claude/wch-custom-isa-reference.md
167 isa-research-claude/wch-isa-usage-in-libraries.md
203 isa-research-codex/findings.md
60  isa-research-codex/round2-review.md
798 total
~~~

## 2. 总体判定

两份 Claude 终稿目前不能 PASS，原因不是所有数字都错，而是关键结论的证据链和范围边界不足，且存在至少一个直接反例：.a 归档扫描之外的 CH587 ROM 中确实有 mcpy。因此，终稿必须在保留可复现数字的同时做一次范围、来源和证据标记重写。

触发 REWORK 的硬门槛如下：

1. 多个结论、表格和“全部/零使用/没有例外”等表述没有按提示要求附 【手册】、【实测】、【推断】 证据链标记。
2. mcpy 的对齐限制被写成未确认；CH32V407RM V1.1 原文明确写出所有地址无对齐要求。
3. “custom-32 共 4 条”与正文实际列出的 mcpy、wexti、mrslu、mrsl、delay 五个不同编码/助记符形式不一致。
4. 使用文档将 .a 归档范围的零结果扩展成“全语料/交付库/current binaries”结论；CH587 ROM 的直接反汇编在 0x40968 得到 mcpy a2,a1,a0。
5. xw2p2 12 / no attributes 11 是 EVT 子集的组数，不是完整三批归档语料的组数；使用文档还把 9 和 1130 个 distinct encoding 写成了“组”。
6. 标准扩展互斥、CSR 分组、H417 批次条件、RISC8B 覆盖和“所有解码/全部 padding”也有范围或证据链问题。

## 3. 必须整改的问题

下表按“编号—位置—问题—证据—修复”给出可执行清单。行号以本轮审查时的文件版本为准。

### R1. 证据链标记和引用不满足强制门槛

- 位置：wch-custom-isa-reference.md:23-35,43-61,71-96,108-143,151-185,193-240,261-269；wch-isa-usage-in-libraries.md:15-61,65-80,84-116,120-157。
- 问题：大量表格、编码、数量、互斥结论和经验性归因没有逐项或逐组标记。即使标题带有 【实测】，其下的每一个结论仍需能回到命令、输出或来源页。
- 证据：参考文档 :9,13-14 自己规定了标记规则；但例如参考文档 :55-61 的 XW/SP 表、:85-96 的互斥表、使用文档 :46-61 的零使用结论均没有完整证据标记。引用为 【手册】 的地方还缺少统一的“文档名/版本/完整 SHA256/页码”。
- 修复：为每个表格行或可独立核验的结论增加 【手册】、【实测】 或 【推断】；【手册】 一律给出 PDF 文件、版本、完整 SHA256 和物理/印刷页码；【实测】 给出可复制命令、输入范围、工具版本和结果摘要；【推断】 明写前提和不能推出的部分。

### R2. mcpy 对齐限制写反，且手册页码不完整

- 位置：wch-custom-isa-reference.md:118-121,251。
- 问题：文档把“地址对齐要求”列为未确认事项；这会误导后续实现和使用者。
- 证据：直接读取原始 tmp/wch-evt/application_notes/CH32V407RM.PDF：PDF physical p58、印刷 p56、§9.2.1.4 mcpy 段落写明“all addresses have no alignment requirement”，并给出位域 [31:27] rs3、[26:25] reserved 00、[24:20] rs2、[19:15] rs1、[14:12] func3=111、[11:7] func5=00000、[6:0] func7=0001111。SHA256 为 63625af9027af6abfff57a58f8d2afdb2b68ee7d31c323e407da6ea786573c56。
- 修复：删除“对齐要求未确认”；改为“CH32V407RM V1.1 明确无地址对齐要求，其他核心/芯片是否相同仍需分别核验”。保留端点更新、粒度、异常/中断等真正未确认项，并补齐 §9.2.1.4、physical/printed page、完整 SHA256。

### R3. custom-32 数量定义不一致

- 位置：wch-custom-isa-reference.md:112-114；wch-isa-usage-in-libraries.md:48-55。
- 问题：正文说“共 4 条 32-bit custom instructions”，但后文实际有 mcpy、wexti、mrslu、mrsl、delay 五个不同的助记符/编码形式。若把 mrslu/mrsl 合并为一族，也应明确“4 个 family、5 个形式”，不能把两种统计口径混写。
- 证据：参考文档 §4.1、§4.2、§4.3 分别列出上述五种形式；tmp/mrs-diff/probes/syntax/ 下也有对应语法 probe。
- 修复：给出明确的枚举定义：例如“4 个 custom-32 family；按独立编码/助记符计为 5 个形式”，并在两个终稿、统计脚本和表格统一采用同一口径。

### R4. custom-32“全语料零使用”超出扫描范围，并被 ROM 反例否定

- 位置：wch-isa-usage-in-libraries.md:48-59,147-149,159-167。
- 问题：:15-27 和 :159-167 实际把主体统计限制为 311 个 .a、可执行 ELF section，排除了 .o 和 ROM；但标题/结论使用“全语料零使用”“交付库”“current binaries”等全称，容易被读成已经覆盖 ROM 和独立 .o。
- 证据：直接执行 GCC15 objdump：

~~~
"GCC15/bin/riscv32-wch-elf-objdump" -D -b ihex -m riscv:rv32 \
  --start-address=0x40958 --stop-address=0x40980 \
  tmp/wch-evt/evt/QingkeV3C_CH587_EVT/EXAM/BLE/LIB/CH587BLE_ROMx.hex
~~~

结果包含：

~~~
40960 beqz a0,0x4096c
40962 beqz a1,0x4096c
40964 beqz a2,0x4096c
40966 add a2,a2,a1
40968 50b6700f mcpy a2,a1,a0
4096c ret
~~~

0x50b6700f 是 mcpy 的实际编码布局。tmp/isa-research-codex/round2-binary-audit.json 记录了 5 个 HEX、3 个 ROM group，并确认 CH587 的 mcpy 位于 0x40968；其他 custom-like 值需继续区分代码和数据。独立 .o 扫描还记录了 1108 个物理文件、822 个 ELF、52,200 executable bytes、14,982 frames，未发现 custom/mcpy，但这不等于 ROM 结论。
- 修复：将结论改成“在 311 个 .a 归档的 executable PROGBITS/SHF_EXECINSTR 范围内未检测到 custom-32 实例”；单列 .o、ROM/HEX 和 mixed code/data 的结果。将“可推迟 custom-32 章节”改成“对该 .a 子集可推迟，对 ROM/其他镜像仍未知或已知存在 mcpy”。

### R5. XW 版本/组数口径混用

- 位置：wch-custom-isa-reference.md:98-110；wch-isa-usage-in-libraries.md:82-90,107。
- 问题：参考文档的“12 个 xw2p2 和 11 个无属性”没有标注是 EVT 子集；使用文档把 xw2p0 组(9个)、undeclared 组(1130个)写成组数，但 9 和 1130 实际是 distinct encoding 数。
- 证据：独立 parser 的 archive attribute group 统计：

~~~
evt:   physical=49 groups=23  {'xw2p2':12, '(undeclared)':11}
mrs24: physical=168 groups=100 {'(undeclared)':65, 'xw2p2':31, 'xw2p0':4}
mrs25: physical=94 groups=64  {'(undeclared)':45, 'xw2p2':19}
total: content groups=187
~~~

因此完整语料按 attribute-bearing archive group 是 xw2p2=62、xw2p0=4、undeclared=121；按独立编码是 xw2p2=1971、xw2p0=9、undeclared=1130。后者与 tmp/isa-research-codex/round2-xw-audit.json 的 version_groups 相符。xw2p2 是工具链/ELF attribute 的 passthrough label，不是已经证明的硬件语义版本差异。
- 修复：所有数字附 scope 和统计单位，至少分“EVT / MRS24 / MRS25、physical path / content group / distinct word / occurrence”。保留已有正确的 effect boundary：其他四个 slot 饱和时只有 q0/f3=4 仍有 1536 个可检测模式，当前没有命中；不得将标签差异写成语义差异。

### R6. H417 批次条件把 PMP 和硬件断点混为一谈

- 位置：wch-custom-isa-reference.md:178-185，特别是 :184。
- 问题：文档说 H417 的 PMP 和硬件断点都依赖批次字符串第五位；独立手册核对表明两类条件不同。
- 证据：tmp/isa-research-codex/round2-doc-pages/ch32h417-p1-001.png、ch32h417-trigger-053.png、ch32h417-trigger-054.png 对应的手册页面：PMP 是 memory-protection 条件；trigger 表中 core-0 的 TSELECT/TDATA1/2 有批次条件，而 core-1 明确有四个 trigger。不能合并成一个“PMP+breakpoint 同时由第五位决定”的结论。
- 修复：拆成芯片/核/寄存器维度的表，分别引用页码和完整 SHA256；对 H417 至少写清 core-0 与 core-1 的差异，以及“条件只针对哪一功能”。

### R7. CSR 0x804/0xBC0 按核心族群概括过度

- 位置：wch-custom-isa-reference.md:145-160，尤其 :153-156。
- 问题：将 0x804/0xBC0 归纳成若干 core family 的统一含义，可能把不同文档中同一地址的不同命名/功能合并了。
- 证据：独立 ledger 对照：X315/V407/H417 的页面将其写为 HW_POPDM_CTLR；其他多个芯片 RM 及四份 core manual 中相同地址出现 INTSYSCR。现有证据支持“按具体文档和芯片区分”，不支持无条件的 family-level mapping。
- 修复：改成“每份手册的原名/功能/复位值”表；若提出跨芯片映射，必须列出全部纳入的文档、页码和反例，并标为推断而非硬件普遍事实。

### R8. C/Zcb/D/XW 互斥表述过宽，且“静默禁用”不准确

- 位置：wch-custom-isa-reference.md:85-96。
- 问题：当前文字容易读成整个 Zcb 或整个 D 扩展与 XW 冲突，也把重叠形式写成“静默禁用”。实际是部分编码槽位重叠、部分形式不可用；未必是整个扩展消失。
- 证据：QingKeV3 手册对应编码说明显示，Q0/f4 的重叠槽位不可访问；但 Q1 的 Zcb zext/sext/mul 形式仍可保留。直接 c.fld probe 还表现为非法 operands/不可汇编，而非可无声使用后被硬件静默关闭。
- 修复：逐个列出“编码槽位—受影响形式—仍可用形式—GAS 诊断”；写成“overlapping forms unavailable”，不要写成“whole Zcb/D unavailable”。说明 C+F+D+XW 的限制是 compressed D forms 的编码冲突，而非普通 F/D 指令整体不可用。

### R9. “全解出、无 >=48 bit、所有尾部都是 padding”等全称缺少范围限定

- 位置：wch-isa-usage-in-libraries.md:46,50,74,76,98-116。
- 问题：这些结论把线性反汇编/模式扫描结果说成语义上的全覆盖；:76 还把 XW SP 出现与 stack overflow/reload path 的因果联系写成事实，没有单独证据。
- 证据：fresh corpus scan 的明确范围是 311 个 .a、187 个 content groups、1177 ELF members、3,350,246 executable bytes；该范围下 XW occurrence=19,344、distinct word=2,253。objdump identity 也确实复核为 12,112 + 7,232 = 19,344，但对象是 XW identity，不是“所有 instruction lines identical”：跨代表组仍有 delta_nonzero=28 的普通 objdump 行数差异。混合代码/数据、ROM 和未执行路径不由线性 objdump 证明。
- 修复：写明“在指定 archive executable section、指定 framing 和当前 objdump/parser 下”；将 tail padding 限定到已有 section-level 证据的样本；把 SP 归因改为“与若干 reload/stack 相关样本共现，尚未证明因果”，或补充编译器/调用图证据。

### R10. RISC8B 的“公开、逐条 ground truth、complete”说法需拆分

- 位置：wch-custom-isa-reference.md:189-205,209-240；wch-isa-usage-in-libraries.md:118-135。
- 问题：公开手册、模型定义、实际观测覆盖、二进制使用频率是四种不同命题；现文档把它们混成“完全公开/逐条对得上/ground truth”，且手册引用不完整。
- 证据：tmp/wch-evt/evt/QingkeV2C_CH32V006_EVT/EXAM/PIOC/Tool_Manual/Manual/CHRISC8B.PDF 的 provenance SHA256 为 38231bec89ea50abb7273c76f8d84adfdd0557829628ece8be8bf752e78281f5。原始 PDF p10 §8.6 明确说明 OTP ROM 只能烧录一次，因此在关键模块前预留 NOP 以便未来替换；这支持 OTP/NOP 约束，但不自动证明所有 66 个格式的硬件语义。独立 PIOC 轮次报告 15 个 LST 只覆盖 39/66 formats，另有 27 个没有样本。
- 修复：分别标注“手册明确”“模型/源代码列出”“LST/二进制观察到”“未观察到/未执行验证”；引用 CHRISC8B v2B 的具体页码、版本和完整 hash；不要用 ground truth 覆盖未观测格式。保留 OTP/NOP 作为已直接核验的手册事实。

### R11. 章节导航和手册 errata 未完成内部一致性

- 位置：wch-custom-isa-reference.md:35,261-269。
- 问题：:35 将 RISC8B 说成 §7，但当前手册结构中 PIOC/RISC8B 内容从 §8 开始，§7 是设备信息；§10 errata 列表也没有逐项来源和证据标记。
- 证据：直接读取 CHRISC8B/PIOC 原始 PDF 的目录和 §8.6；wch-doc-provenance.md 仅提供了 provenance 总表，不替代每个 erratum 的具体页码。
- 修复：修正章节导航；每个 erratum 给出“芯片/手册/版本/SHA256/page/影响范围”，将未确认项保留为单独列表而非无来源结论。

### R12. 版本差异、同名陷阱和“仅 passthrough”需在正文中连同验证方法呈现

- 位置：wch-custom-isa-reference.md:49-61,98-110；wch-isa-usage-in-libraries.md:82-92。
- 问题：XW 的名字、GCC 接受、ELF attribute 和硬件语义是不同层次。当前结论方向基本正确，但证据链未落到正文；“all coding is measured”没有给读者可复跑入口。
- 证据：直接 GAS acceptance：c.lbu、mcpy 均 exit 0；xw、xw2p2、xw3p0 均 exit 0。已有 xw1p0 object 的 .text 为 8821、attribute 是 _xw1p0。独立全交叉审计 8704 cases 在 GCC12/GCC15、xw/xw1p0/xw2p0/xw2p2/xw3p0 下 mismatch=0，全部 stream SHA 为 d3a6a0647389d3aee2661916eb420ca58da4a29b8e59bdfb3626b8c810651a05。
- 修复：把“标签 passthrough、编码相同、语义未知”三列分开；正文至少保留 8704/0 mismatch、版本标签和 q0/f3=4 边界，并链接到可复制脚本/JSON。

## 4. 强制复现项目、命令和结果

以下命令均为只读检查，或将 assembler 输出定向到 /dev/null；没有通过本轮命令改写既有工作产物。

### 4.1 库清单、provenance 和控制检查

~~~sh
python3 audit-report-f/followup/tools/isa_census.py inventory
python3 audit-report-f/followup/tools/isa_census.py provenance
python3 audit-report-f/followup/tools/isa_census.py control
~~~

关键输出：

~~~
evt: 49 files, 23 content groups
mrs24: 168 files, 100 content groups
mrs25: 94 files, 64 content groups
assembler ... GCC12 ... 2.38
objdump ... GCC12 ... 2.38
objdump_gcc15 ... 2.45
eth_api.o/.text.GetChipID: lui(RVI) lhu(RVI) andi(RVI) c.jr(RVC-std)
control OK
~~~

对现有 isa-census.tsv 做只读字段统计：

~~~
data_rows=9246 XW=19344 unknown=198
~~~

该 unknown=198 是 census 行层面的识别结果，不能被终稿改写成“硬件存在 198 个未知指令”；它需要和 section、工具、framing scope 一起解释。

### 4.2 c.fld / c.lbu 和 mcpy 的强制编码检查

~~~sh
GCC12/bin/riscv32-wch-elf-objdump -s -j .text \
  tmp/mrs-diff/probes/xw/mrs24/GCC12/known-c.lbu.o

GCC12/bin/riscv32-wch-elf-objdump -s -j .text \
  tmp/mrs-diff/probes/syntax/mcpy_a0__a1__a2.s.o
~~~

关键原始 bytes：

~~~
known-c.lbu.o: 8821
mcpy_a0__a1__a2.s.o: 0f70b560
~~~

按 little-endian 解码：

~~~
c.fld fa0,0(a1) -> 0x2188  (GCC12 objdump 的标准 RV/F 解码)
c.lbu a0,0(a1) -> 0x2188
mcpy a0,a1,a2  -> 0x60b5700f
~~~

0x60b5700f 字段拆解结果：

~~~
{'word':'0x60b5700f','rs3':12,'reserved':0,'rs2':11,'rs1':10,
 'funct3':7,'funct5':0,'opcode':15}
~~~

直接 GAS 接受性 probe：

~~~sh
printf '.text\n.option rvc\nc.lbu a0,0(a1)\n' |
  GCC12/bin/riscv32-wch-elf-as -march=rv32imac_xw -mabi=ilp32 -o /dev/null /dev/stdin
# c.lbu exit=0

printf '.text\nmcpy a0,a1,a2\n' |
  GCC12/bin/riscv32-wch-elf-as -march=rv32i -mabi=ilp32 -o /dev/null /dev/stdin
# mcpy exit=0
~~~

手册交叉核验：CH32V407RM.PDF §9.2.1.4、PDF physical p58/printed p56 的 mcpy 位域正好与上述 0x60b5700f 相符，并明确“all addresses have no alignment requirement”。

### 4.3 XW 版本 passthrough

~~~sh
for tag in xw xw2p2 xw3p0; do
  printf '.text\n.option rvc\nc.lbu a0,0(a1)\n' |
    GCC12/bin/riscv32-wch-elf-as -march=rv32imac_$tag -mabi=ilp32 \
    -o /dev/null /dev/stdin
done
~~~

结果：三个标签全部 exit=0。现有 xw1p0 object 的 .text 是 8821，readelf -A 显示 Tag_RISCV_arch: ..._xw1p0，说明标签变化没有改变该 probe 的编码。

已有独立 JSON tmp/isa-research-codex/round2-xw-audit.json 的完整交叉结果：

~~~
case_count=8704
GCC12/GCC15 × xw/xw1p0/xw2p0/xw2p2/xw3p0: mismatch_count=0
all expected distinct=8704
identical stream sha256=d3a6a0647389d3aee2661916eb420ca58da4a29b8e59bdfb3626b8c810651a05
~~~

另外，用内存 parser 读取 xw2p2 archive 的现有 ELF member，得到：

~~~
member=gap.o section=.text.GAP_ProcessEvent attrs=xw2p2 c.lbu bytes=8821 offset=226
~~~

### 4.4 规模、两个样本和 no-attribute 样本

fresh round2_xw_audit.scan_corpus()（不写 JSON）输出：

~~~
totals={
  'physical_archives':311, 'content_groups':187, 'elf_members':1177,
  'exec_bytes':3350246, 'xw_occurrences':19344,
  'xw_distinct_words':2253
}

sample V407 libwchnet.a:
  physical_paths=1 member_count=56 exec_bytes=82712
  xw_occurrences=2320 xw_distinct_words=536 version_group=xw2p2

sample CH587 libCH58xBLE.a:
  physical_paths=1 member_count=62 exec_bytes=190942
  xw_occurrences=5592 xw_distinct_words=1482 version_group=xw2p2
~~~

同 basename libwchnet.a 的属性/规模核对：

~~~
V407 attrs=['xw2p2'] members=56 xw=2320
V203 attrs=[]       members=28 xw=1137
V20x attrs=[]       members=28 xw=1137
V317 attrs=[]       members=56 xw=2274
H417 attrs=['xw2p2'] members=56 xw=2320
~~~

no-attribute 样本：

~~~
path=tmp/wch-evt/evt/QingkeV4B_CH32V203_EVT/EXAM/ETH/NetLib/libwchnet.a
attributes=[]
instruction_lines=14210 fld=786 fsd=336 raw_directives=15
786 + 336 + 15 = 1137 XW occurrences
~~~

这验证了“no-attribute 样本仍含 XW”的事实，但不支持把 attribute 缺失解释为芯片/硬件版本本身。

### 4.5 objdump identity

对 187 个 representative content groups 做 fresh isa_census.xcheck：

~~~
archives_checked=187
objdump_undecoded=12112
objdump_phantom_fld_fsd=7232
xw=19344
identity=19344 ok=True
delta_nonzero=28
~~~

可以确认的是：在 xw_split_ok 样本中，objdump_undecoded + objdump_phantom_fld_fsd 恰好解释 XW identity。不能把这个恒等式扩大成“所有反汇编行无差异”或“所有 unknown 都是工具幻象”；delta_nonzero=28 是必须保留的范围提示。

### 4.6 ROM 反例

~~~sh
GCC15/bin/riscv32-wch-elf-objdump -D -b ihex -m riscv:rv32 \
  --start-address=0x40958 --stop-address=0x40980 \
  tmp/wch-evt/evt/QingkeV3C_CH587_EVT/EXAM/BLE/LIB/CH587BLE_ROMx.hex
~~~

输出中的关键五行：

~~~
40960 beqz a0,0x4096c
40962 beqz a1,0x4096c
40964 beqz a2,0x4096c
40966 add a2,a2,a1
40968 50b6700f mcpy a2,a1,a0
4096c ret
~~~

这不是对 .a 统计的反驳，而是对“全语料/交付库/custom-32 当前二进制绝对零使用”这些更宽主张的反例。

## 5. 手册、版本和页面证据

本轮使用的主要 PDF provenance：

| 文档 | 版本/用途 | SHA256 |
|---|---|---|
| tmp/wch-evt/manual/QingKeV3_Processor_Manual.PDF | QingKeV3 V1.5；delay、CSR、XW/压缩编码 | fcc16b54d8818b04b9f8a7a7fbce6c504b87ca3787f0933edecc4da7112438d5 |
| tmp/wch-evt/application_notes/CH32V407RM.PDF | CH32V407RM V1.1；mcpy/delay | 63625af9027af6abfff57a58f8d2afdb2b68ee7d31c323e407da6ea786573c56 |
| tmp/wch-evt/evt/QingkeV2C_CH32V006_EVT/EXAM/PIOC/Tool_Manual/Manual/CHRISC8B.PDF | CHRISC8B v2B；PIOC/OTP/NOP | 38231bec89ea50abb7273c76f8d84adfdd0557829628ece8be8bf752e78281f5 |
| PIOC v1 provenance entry in wch-doc-provenance.md | PIOC model/document provenance | 61e543eb2dcdf538deaabf40afccae53fbd8166bb2b64890112bd885da0ede43 |

三项手工页面复核：

1. CH32V407RM：直接 pdftotext -f 55 -l 60 -layout .../CH32V407RM.PDF -；PDF physical p57/printed p55 是 delay，physical p58/printed p56 是 §9.2.1.4 mcpy。已查看 tmp/isa-research-codex/round2-doc-pages/ch32v407-058.png。
2. QingKeV3：直接 pdftotext -f 53 -l 57 -layout .../QingKeV3_Processor_Manual.PDF -；physical p55 的 delay table 可见完整 [31:20] imm、[19:15] rs1、f3=001、match/div/sel、opcode 0001011。已查看 tmp/isa-research-codex/round2-doc-pages/qingkev3-55.png。
3. CHRISC8B：直接 pdftotext -layout .../CHRISC8B.PDF - | rg ...；p10 §8.6 说明 OTP ROM 原则上只能烧录一次，并建议关键模块前预留 NOP 以便未来替换。

本轮没有把任何抽取 .txt 当作 primary citation；tmp/isa-research-codex/manual-text/*.txt 仅作为既有轮次的辅助产物，最终引用应回到原始 PDF。

## 6. 覆盖声明和统计口径

可确认的主体 archive scope 是：

~~~
311 physical .a archives
187 content groups
1177 ELF members
3,350,246 executable bytes
19,344 XW occurrences
2,253 distinct XW words
~~~

统计含义：

- 主体是 .a 内 ELF executable/SHF_EXECINSTR 代码；不自动涵盖 standalone .o、HEX/ROM、未标记为 executable 的数据、真实执行路径或硬件语义。
- 311 是 physical archive 路径数；187 是 content groups；二者不能互换。
- 19,344 是 XW occurrence；2,253 是 distinct 32-bit word；不是 instruction semantic count。
- 统一 objdump 对照确认了 12,112 + 7,232 = 19,344 的 XW identity，但不是全部解码结论。
- .a 主体中 custom-32 为零的旧结果可保留，但必须明确这是 .a scope；独立 .o 扫描和 ROM/HEX 扫描是另外的覆盖层。
- PIOC 文档/模型覆盖不能由 .a 使用频率替代；PIOC 实例级频率尚未统计，ROM 也没有纳入 .a 主体。

## 7. 对 isa-research-codex 轮次的单独评价

评价：**可靠，且关键修正可复现。**

优点：

- isa-research-codex/findings.md:13 正确修正了“只有 CH32V407RM 给出 32-bit custom encoding”的第一轮错误：QingKeV3 V1.5 p55 确实有完整 delay encoding。
- :31-42 的 XW 8704 全组合、GCC12/GCC15、多标签零 mismatch 结论有既有 JSON 和本轮直接 GAS/bytes probe 支撑。
- :46-61 正确保留了 q0/f3=4 的 1536 个可检测模式边界，没有把标签差异宣称为硬件语义差异。
- :65-73 明确了 PIOC 只观察到 39/66 formats，另有 27 个无样本；没有把静态样本写成完整硬件验证。
- :77-87,93-105 把 .o、ROM 和 .a 分开，并发现 CH587 ROM 的 mcpy 反例；同时没有把 mixed code/data 指纹全部计成指令。
- :151-168 列出了 XW q0/f4 语义、WCH-X、ROM reachability、PIOC atomicity 等真正未解决事项。

需要提醒的边界：xw2p2 62 在 Codex findings 中是 usage/content-group 口径；ELF attribute-bearing EVT 子集仍是 12 个 xw2p2 与 11 个 undeclared。只要在最终文档中把单位写清楚，两者并不矛盾。

主要不足不是 Codex 轮次本身的复现性，而是这些修正尚未完整传播到两份 Claude 终稿；终稿仍保留了 R2、R4、R6、R7、R8 等硬问题。

## 8. 优点（整改时应保留）

- 两份终稿已经把 RISC-V custom/XW 与 RISC8B/PIOC 分成两套体系，这是结构上的正确方向；修正 §7/§8 导航即可。
- XW 的四种 SP form、寄存器/立即数约束、版本标签 passthrough 和 q0/f3=4 effect boundary 已有很好的整理基础。
- 19,344、311/187/1177、3,350,246、XW distinct/occurrence 等数量大体有脚本和既有产物支撑；objdump identity 本轮也独立复核通过。
- 使用文档有价值地把零使用类别转成“可推迟审查”的工程建议；只需改成严格的 .a 子集结论，并把 ROM/.o 反例和未确认项放回边界内。
- PIOC 的 OTP/NOP 约束和 RISC8B 与 RISC-V 的分离值得保留，但应把手册事实、模型事实和样本观察分层。

## 9. 尚未能确认的事项

以下项目不应在整改中被填成无依据的肯定结论：

1. XW q0/f3=4 的 1536 个可检测编码模式在各芯片上的真实硬件语义。
2. XW 2.2、2.5 或版本标签在可检测位域之外的语义差异。
3. custom major opcode 在每个芯片/核上的完整硬件支持集合。
4. mrsl/mrslu 的全部语义、异常行为和模型差异。
5. delay 的 sel=1、rs2、精确计时/中断行为是否跨核一致。
6. WCH-X 相关编码/属性的完整覆盖。
7. CH587 ROM mcpy 的所有调用路径、芯片执行可达性以及其他 mixed code/data fingerprint 的真实身份。
8. PIOC 缺失的 27/66 formats、运行时/WASM 语义、原子性和 cycle phase。
9. tmp/wch-riscv 仍未完整复核的 514 PDFs、19 MRS 文档和 3 个上游文件。
10. PIOC 实例级频率和 ROM 中 PIOC/其他 RISC8B 指令的完整统计。

## 10. 建议的整改后验收条件

整改版重新提交时，至少应满足：

- 每个最终结论都有可追溯的证据标记；“手册”引用补齐文档、版本、完整 SHA256、页码。
- 四项强制 probe 和两个 archive 样本仍可复跑，输出与本报告一致或解释差异。
- mcpy 无对齐要求、CH587 ROM 反例、QingKeV3 delay p55、XW 8704/0 mismatch、19344 identity 均进入正文。
- .a、.o、ROM/HEX、PIOC LST/模型的 scope 分开；所有 zero/all/none/no exception 句子改为带范围和方法的句子。
- XW SP forms、RISC-V/RISC8B 分离、C/F/D/Zcb/XW 部分互斥和 same-name trap 有明确的“受影响形式”表。
- custom-32 统计统一为 family/form 两种单位之一并在全文声明。
- 重新执行 git diff --check，并确认本审查输出之外没有被本轮修改的文件。

## 11. Git 交付记录

本轮创建：isa-research-review-codex.md。

本轮没有 commit，原因是审查提示明确要求独立 reviewer 不提交 Git commit；工作树中的既有用户/其他轮次变更均未清理、回滚或覆盖。本文件可直接通过：

~~~
git diff --check -- isa-research-review-codex.md
git status --short -- isa-research-review-codex.md
git diff -- isa-research-review-codex.md
~~~

最终判定仍为：两份 Claude 终稿 **REWORK**；isa-research-codex 轮次 **可靠，关键修正可复现**。
