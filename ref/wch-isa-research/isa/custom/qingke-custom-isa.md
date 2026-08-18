# 青稞(QingKe)V2/V3/V4/V5 处理器自定义指令扩展与内核架构技术参考

## 0. 来源与版本

本文引用的一手手册及其指纹(sha256 已在本机对 PDF 原件复算核对,与账本 `isa-research-claude/wch-doc-provenance.md` 一致):

| 简写 | 文件(`tmp/wch-evt/manual/`) | 版本 | sha256(前16) | 总页数 | 本文实际引用页 |
|---|---|---|---|---|---|
| **V2手册** | `QingKeV2_Processor_Manual.PDF` | V1.3 | `5430356218fca280` | 27 | 1–2, 4–14, 17, 24–26 |
| **V3手册** | `QingKeV3_Processor_Manual.PDF` | V1.5 | `fcc16b54d8818b04` | 56 | 1–2, 4–24, 41–44, 54–56 |
| **V4手册** | `QingKeV4_Processor_Manual.PDF` | V1.5 | `b543a875a199a670` | 37 | 1–2, 4–19, 30–37 |
| **V5手册** | `QingKeV5_Processor_Manual.PDF` | V1.0 | `0a849c719d135885` | 47 | 1–2, 3–18, 35–47 |

**引用约定**:正文中 `V2手册 pN`(以及旧式简写 `V2 pN`)一律等价于完整出处 `QingKeV2_Processor_Manual.PDF V1.3 (sha256:5430356218fca280) 第 N 页`,其余三份同理按上表展开;页码为 PDF 物理页码(与页脚印刷页码相差 1 页)。每个章节的首个手册出处使用完整格式,其后使用简写。

**版本错位纪律**:四份手册版本并不相同(V2=V1.3、V3/V4=V1.5、V5=V1.0)。跨代比较中某项内容在某代"没有",只能证明**该版手册未见记载**,不必然等于该代硬件不支持——本文所有此类结论均写作"该版手册未见";§7.3 的 mcpy 案例(V2/V5 手册未见、SDK 实际出货)即为实例。

预抽取文本 `tmp/wch-evt/eval/manual-text/*.txt` 仅作检索用,**非一手件**,本文出处一律指向上表 PDF;文本抽取覆盖了全部 167 页(页标记连续无缺),关键页(四份手册 §1.1、V3手册 p55–56、概览表)已另经图像复核。

其余证据类别:

- **【实测】** 用 MRS 工具链汇编器/编译器实测(本机 `MRS_Toolchain_MAC_V240`):
  - GCC12:`riscv-wch-elf-as`(binutils,GCC 12.2.0 套件)
  - GCC15:`riscv32-wch-elf-as`(GCC 15.2.0 套件)
  - GCC8(旧版):`riscv-none-embed-as`(xPack GCC 8.2.0 WCH 定制)
- **【SDK】** WCH EVT 固件包头文件(`tmp/wch-evt/evt/*/EXAM/SRC/Core/core_riscv.h`)。
- **【规范】** RISC-V 官方规范(Unprivileged ISA 20191213 / RVV 1.0 / Zb* 1.0 等)——仅用于展开标准扩展的指令清单,手册本身未逐条列出(见 §7)。

关键结论先行:**四份手册均未给出 XW 的位编码**(仅一句助记符清单,已对全部 167 页文本抽取并对关键页做图像复核确认)。本文当前可验证的 8 个 XW 形式编码来自汇编器实测；32 位侧则有两类独立手册证据：QingKe V3 V1.5 p55 给 delay 位表，CH32V407RM V1.1 p57–58 给 delay/mcpy 位表。

---

## 1. XW 压缩指令扩展(自定义 16 位指令)

### 1.1 手册记载(全部原文内容)

四份手册对 XW 的记载相同且仅此一处(§1.1 指令集节):`QingKeV2_Processor_Manual.PDF V1.3 (sha256:5430356218fca280) 第 2 页`、`QingKeV3_Processor_Manual.PDF V1.5 (sha256:fcc16b54d8818b04) 第 2 页`、`QingKeV4_Processor_Manual.PDF V1.5 (sha256:b543a875a199a670) 第 2 页`、`QingKeV5_Processor_Manual.PDF V1.0 (sha256:0a849c719d135885) 第 2 页`:

> XW:自扩展字节和半字操作的 16 位压缩指令
> 注:为进一步提高代码密度,扩展 XW 子集,增加以下压缩指令 c.lbu/c.lhu/c.sb/c.sh/c.lbusp/c.lhusp/c.sbsp/c.shsp,使用时需要基于 MRS 编译器或者其提供的工具链。

**手册未给出位编码、操作数约束、立即数范围、版本号。** 以下全部为【实测】。

### 1.2 指令清单与语义

| 助记符 | 语义 | 汇编格式 |
|---|---|---|
| `c.lbu rd', uimm5(rs1')` | 零扩展字节加载,rd' = zext(mem8[rs1'+uimm]) | uimm ∈ [0,31],步进 1 |
| `c.lhu rd', uimm6(rs1')` | 零扩展半字加载 | uimm ∈ [0,62],2 字节对齐 |
| `c.sb rs2', uimm5(rs1')` | 存储字节 | uimm ∈ [0,31],步进 1 |
| `c.sh rs2', uimm6(rs1')` | 存储半字 | uimm ∈ [0,62],2 字节对齐 |
| `c.lbusp rd', uimm4(sp)` | 基于 sp 的零扩展字节加载 | uimm ∈ [0,15],步进 1 |
| `c.lhusp rd', uimm5(sp)` | 基于 sp 的零扩展半字加载 | uimm ∈ [0,30],2 字节对齐 |
| `c.sbsp rs2', uimm4(sp)` | 基于 sp 的存储字节 | uimm ∈ [0,15],步进 1 |
| `c.shsp rs2', uimm5(sp)` | 基于 sp 的存储半字 | uimm ∈ [0,30],2 字节对齐 |

注意:**没有符号扩展形式**(`c.lb`/`c.lh` 被汇编器拒绝,【实测】);标准 Zcb 有 `c.lh`,XW 没有。

### 1.3 位编码表(【实测】,GCC8/12/15 一致)

寄存器字段均为 RVC 3 位压缩寄存器编码(x8–x15,即 s0,s1,a0–a5);`rd'`/`rs2'` 在 [4:2],`rs1'` 在 [9:7]。**sp 形式的目的/源寄存器同样只能是 x8–x15**(a6/t0/t6/ra/zero 均被拒绝,【实测】)。负偏移一律拒绝。

寄存器基址形式(CL/CS 布局,分布在两个象限):

| 指令 | 15:13 | 12 | 11:10 | 9:7 | 6 | 5 | 4:2 | 1:0 | 占用的标准槽位 |
|---|---|---|---|---|---|---|---|---|---|
| `c.lbu` | 001 | uimm[0] | uimm[4:3] | rs1' | uimm[2] | uimm[1] | rd' | **00** | C.FLD(RV32DC,象限 0) |
| `c.lhu` | 001 | uimm[5] | uimm[4:3] | rs1' | uimm[2] | uimm[1] | rd' | **10** | C.FLDSP(RV32DC,象限 2) |
| `c.sb` | 101 | uimm[0] | uimm[4:3] | rs1' | uimm[2] | uimm[1] | rs2' | **00** | C.FSD(RV32DC,象限 0) |
| `c.sh` | 101 | uimm[5] | uimm[4:3] | rs1' | uimm[2] | uimm[1] | rs2' | **10** | C.FSDSP(RV32DC,象限 2) |

sp 基址形式(全部挤在象限 0 funct3=100 —— 标准 RVC 的保留行;子操作码在 [6:5]):

| 指令 | 15:13 | 12:11 | 10:7 | 6:5 | 4:2 | 1:0 |
|---|---|---|---|---|---|---|
| `c.lbusp` | 100 | 00 | uimm[3:0] | **00** | rd' | 00 |
| `c.lhusp` | 100 | 00 | uimm[3:1]=[10:8], uimm[4]=[7] | **01** | rd' | 00 |
| `c.sbsp` | 100 | 00 | uimm[3:0] | **10** | rs2' | 00 |
| `c.shsp` | 100 | 00 | uimm[3:1]=[10:8], uimm[4]=[7] | **11** | rs2' | 00 |

注意 c.lhusp/c.shsp 的立即数是打乱的:bit7 = uimm[4](不是 uimm[0]),[10:8] = uimm[3:1]。位 [12:11] 恒为 0(超出该立即数范围的值一律被汇编器拒绝,无其他编码点被接受)。

实测样例(可用作反汇编对照):

```
c.lbu  a0,0(a1)=0x2188   c.lbu a5,3(a1)=0x31bc   c.lbu a0,31(a1)=0x3de8
c.lhu  a0,0(a1)=0x218a   c.lhu a0,62(a1)=0x3dea
c.sb   a0,0(a1)=0xa188   c.sb  a0,31(a1)=0xbde8
c.sh   a0,0(a1)=0xa18a   c.sh  a0,62(a1)=0xbdea
c.lbusp a0,0(sp)=0x8008  c.lbusp a0,15(sp)=0x8788
c.lhusp a0,0(sp)=0x8028  c.lhusp a0,16(sp)=0x80a8  c.lhusp a0,30(sp)=0x87a8
c.sbsp  a0,0(sp)=0x8048  c.shsp  a0,0(sp)=0x8068   c.shsp  a0,30(sp)=0x87e8
```

### 1.4 编码空间占用与互斥关系(工具链配置关键)

XW 占用的 RVC 编码点(【实测】推得):

1. **象限 0 funct3=001/101 与象限 2 funct3=001/101** —— 即 RV32 **D 扩展压缩指令 C.FLD / C.FSD / C.FLDSP / C.FSDSP 的全部四个槽位**。实测直接对撞证据:`rv32iafdc_zicsr` 下 `c.fld fa0,0(a1)` = **0x2188** = XW `c.lbu a0,0(a1)`;`c.fsd fa0,0(a1)` = **0xa188** = XW `c.sb a0,0(a1)`。→ **完整的 D+C 压缩双精度访存形式不能与 XW 同时使用**；这不否定非压缩 D 指令。GCC12 汇编器接受 `-march=rv32imafdc_zicsr_xw` 这种字符串,但重叠的 c.fld/c.fsd/c.fldsp/c.fsdsp 随后报 illegal operands——不要依赖这种组合。
2. **象限 0 funct3=100(标准 RVC 保留行,[12:11]=00 区)** —— 四条 sp 形式。这正是后来批准的标准 **Zcb** 扩展放 `c.lbu/c.lhu/c.lh/c.sb/c.sh` 的行,且 **Zcmp/Zcmt** 也占象限 2 funct3=101(与 XW `c.sh` 冲突)。实测对撞:同一 16 位值 **0x8000**,在 `-march=rv32imac_zcb`(GCC15)下是标准 `c.lbu s0,0(s0)`,在 `-march=rv32imac_xw` 下是 XW `c.lbusp s0,0(sp)`。→ **不能把完整 Zcb/Zcmp/Zcmt 与 XW 无条件组合**；Q1 等未重叠形式不因这些冲突消失。
3. **F 扩展的压缩槽位完全不受影响**:C.FLW(Q0/011)、C.FSW(Q0/111)、C.FLWSP(Q2/011)、C.FSWSP(Q2/111)与 XW 零重叠。实测:`rv32imafc_xw` 下 `c.flw fa0,0(a1)`=0x6188 与 `c.lbu a0,0(a1)`=0x2188 同文件共存;实际编译(`-Os`)的目标文件里 XW 指令与 c.flw 交错出现。**F+C+XW 是工具链明确支持的组合**(multilib 中有 `rv32imafc_xw/ilp32f`)。

结论表:

| 组合 | 可行性 | 依据 |
|---|---|---|
| C + XW | ✔ | 全部 EVT 默认配置 |
| F + C + XW | ✔ | multilib `rv32imafc_xw`;槽位无重叠【实测】 |
| D + C + XW | ✘(c.fld 族不可用) | 四个 D 压缩槽位全被 XW 占用【实测】 |
| Zcb / Zcmp / Zcmt + XW | 不能作为完整扩展组合 | Q0/100 行与 Q2/101 槽位冲突【实测】;GCC15 接受 `_zcb_xw` 但同名助记符按 XW 编码,Zcb 的 Q0 访存指令不可达(Q1 的 c.zext.b/c.mul 仍可用) |

**同名异码陷阱**:`c.lbu/c.lhu/c.sb/c.sh` 四个助记符在标准 Zcb 与 WCH XW 中编码完全不同(Zcb `c.lbu a0,0(a1)`=0x8188,XW 同句=0x2188,【实测】GCC15)。看到这些助记符必须先确认 `-march` 里是 `_zcb` 还是 `_xw`。

### 1.5 工具链事实(【实测】)

- `-march` 拼写:GCC12/GCC15 用下划线后缀 **`_xw`**(`rv32ec_xw`、`rv32ec_zmmul_xw`、`rv32imac_xw`、`rv32imafc_xw`、GCC15 另有 `rv32imac_zaamo_zalrsc_xw` 等);GCC8 旧工具链用无下划线拼写 **`rv32ecxw` / `rv32imacxw` / `rv32imafcxw`**。
- ELF arch 属性记录版本为 **`xw1p0`**(例:`rv32i2p0_m2p0_a2p0_c2p0_zmmul1p0_xw1p0`)。手册无 XW 版本号。

> **【实测·后补】XW 版本标签、语料口径与差分边界**
>
> 上一条"未发现 2.x 存在的证据"仅对**本机工具链的产物**成立。对 WCH **交付的库**复核后发现:凡在 `.riscv.attributes` 中声明了 XW 版本的 EVT archive,**全部是 `xw2p2`,无一为 1.0**——按内容组计共 **12 个**:`libIQMath_RV32EC_ZMMUL_XW.a`、`libM12014SV_M007_LIB_20250115.a`、`libvoilent_fan_SRC-Lib.a`、`libCH32V205_TOUCH_CS.a`、`libCH32V205_TOUCH_CT.a`、`libCH32V00X_TOUCH.a`(以上 V006 树)、`libCH58xBLE.a`、`libCH587_TOUCH.a`(CH587 树)、**`libwchnet.a`(V407)**、**`libwchnet.a`(H417)**、`libCH32H417_TOUCH.a`、`libUHSIF.a`(H417 树)。
>
> **注意 `libwchnet.a` 按芯片树分属两类**:V407/H417 的声明 `xw2p2`,而 V203/V20x/V317 的**没有 `.riscv.attributes` 节**。因此"按 basename 列清单"必然出错——同名 archive 的不同芯片构建必须分别计。(此处初稿曾按 basename 取首份副本而误记为 10 个,由二进制普查单元发现并经本轮复算确认为 12。)
>
> **【再修正】版本号是透传标签,不代表汇编器有版本化行为。** 上面这条初次记录时曾被表述为"本机汇编器仅支持 1.0",经实测**该表述过度**,现更正:
>
> ```
> -march=rv32imac_xw      → 接受,attr=xw1p0,c.lbu a0,0(a1) 编码 0x2188
> -march=rv32imac_xw2p2   → 接受,attr=xw2p2,编码同为 0x2188
> -march=rv32imac_xw3p0   → 接受(用于透传探针,不主张存在相应芯片),attr=xw3p0,编码同为 0x2188
> ```
>
> 汇编器对任意 XW 版本号照单全收、原样写入 `.riscv.attributes`,而**产生的编码不因版本号改变**。`xw1p0` 只是写 `_xw` 时的默认标签,并非"所支持的版本上限"。
>
> 因此正确的结论收窄为:**`xw2p2` 只证明 WCH 建库用的是另一套工具链构建,并不单独证明 XW 2.2 的指令集与 1.0 不同。**
>
> 本机汇编器只能生成它认识的 8 个形式，若其它 WCH 工具链另有助记符，本机无从直接生成。第二轮已完成集合差：GCC12/GCC15 × `xw/xw1p0/xw2p0/xw2p2/xw3p0` 各 8,704 个词均相同。全语料 187 个内容组的版本分组是 `xw2p2` 62、`xw2p0` 4、未声明 XW 版本 121；121 中 71 组没有 `.riscv.attributes`，另 50 组有属性节但没有 XW 标签。筛到实际使用 XW 的 100 组后才是 62 组/11,633 次、4 组/28 次、34 组/7,683 次，均无本地集合之外的编码。该差分只在 Q0/funct3=4 剩余 1,536 个点有判别力且命中 0；其它四槽已被本地集合占满，所以不能排除语义重定义。证据：`tmp/isa-research-codex/round2-xw-audit.json` 与 `audit-report-f/followup/results/isa-census-notes.md`。
>
> 复现:
> ```sh
> B="MRS_Toolchain_MAC_V240/Toolchain/RISC-V Embedded GCC12/bin"
> printf '\tc.lbu a0,0(a1)\n' > /tmp/x.s && "$B/riscv-wch-elf-as" -march=rv32imac_xw /tmp/x.s -o /tmp/x.o
> "$B/riscv-wch-elf-readelf" -A /tmp/x.o | grep -o 'xw[0-9]p[0-9]'          # -> xw1p0
> "$B/riscv-wch-elf-readelf" -A tmp/wch-evt/evt/QingkeV3C_CH587_EVT/EXAM/BLE/LIB/libCH58xBLE.a \
>   | grep -o 'xw[0-9]p[0-9]' | sort -u                                      # -> xw2p2
> ```
>
> 另注：EVT 的 23 个内容组中，12 组声明 `xw2p2`，另 11 组没有 `.riscv.attributes`；这 11 组里只有 4 组实际出现 XW。12/0/11 是 EVT inventory 口径，62/4/121 是全语料 inventory 口径，62/4/34 则是全语料中“实际出现 XW”的筛选口径，三者不能混用。
- 汇编器自动压缩:`_xw` 生效时,范围内的 `lbu/lhu/sb/sh`(含以 sp 为基址)会被 GAS 自动压缩成 XW 16 位形式(`lbu a0,3(a1)` → 0x31a8,2 字节)。链接器松弛同理,反推:**同一 .s 在有/无 `_xw` 下产物尺寸与编码不同**。
- **三个工具链的 objdump 都不能反汇编 XW**:GCC12 打印 `.2byte 0x2188`,GCC15 打印 `.insn 2, 0x2188`;**GCC8 的 objdump 更危险——把 XW 误反汇编成 `fld fa0,0(a1)`/`fsd`(按 D 扩展解码)**,分析二进制时务必对照 §1.3 的编码表人工识别。
- 编译器在 `WCH-Interrupt-fast` 与普通代码中都会生成 XW 指令(实测 `-Os` 产物含 0x31bc=c.lbu a5,3(a1) 等)。

### 1.6 各代支持矩阵

| 内核 | XW 支持(【手册】表 1-1) |
|---|---|
| V2A / V2C | ✔ / ✔(V2 p2) |
| V3A | ✘;V3B/V3C/V3F/V3V ✔(V3 p2) |
| V4A | ✘;V4B/V4C/V4F/V4J ✔(V4 p2) |
| V5F | ✔(V5 p2) |

四份手册列出的 8 个助记符相同；这只证明四个当前版本手册的已知清单一致，不证明 XW 全集或硅片语义不存在代际差异。

---

## 2. 其他自定义指令(32 位)

四份**青稞内核**处理器手册对这些指令的记载极少(见各小节),以下编码均为【实测】,语义来自【SDK】头文件注释。**三条 custom-0 指令与 mcpy 在 GCC12/GCC15 中不受任何 `-march` 扩展门控(连 `rv32i` 都接受);GCC8 完全不认识它们。**

> **【后补】芯片参考手册给出了位编码,且与本节实测逐位吻合**
>
> 本节初稿写作时只查了四份青稞内核手册。后续复核确认两条手册路径：`QingKeV3_Processor_Manual.PDF V1.5 (sha256:fcc16b54d8818b04) PDF p55` 给出完整 delay 位表；12 份芯片参考手册中，`CH32V407RM V1.1 (sha256:63625af9027af6ab) PDF p57–58` 给出 delay 与 mcpy 位表。
>
> - §9.2.1.4 `自定义 mcpy 指令`:`[14:12] func3 = 111b`、`[6:0] = 0001111b`
> - §9.2.1.3 `自定义延时指令`:`[14:12] func3 = 001b`、`[6:0] = 0001011b`,另有 match/div/sel 字段(其中 `111` = 匹配指定 func3 与 opcode 的指令)
>
> 与本节由汇编器实测得到的编码对撞:`mcpy a0,a1,a2` = `0x60b5700f` → opcode `[6:0]` = `0b0001111`(0x0F,MISC-MEM)、funct3 `[14:12]` = `0b111`。**固定编码位和寄存器位位置一致**；但手册 rs1/rs3 的地址角色文字与 SDK 顺序冲突，见 §2.1。延时指令的 custom-0(`0b0001011` = 0x0B)与 funct3=001 同样一致。
>
> **手册自身的字段命名有误**:该手册把 `[6:0]` 标注为 `func7`,而按 RISC-V 惯例该字段是 opcode(func7 应在 `[31:25]`)。引用时按位区间理解,勿照抄字段名。
>
> 另注:`CH32H417RM V1.7` 只提到"WCH-X 扩展指令集"之名,**未给任何编码**。

### 2.1 mcpy —— 存储器块拷贝(MISC-MEM 空间)

- 【手册】仅 `QingKeV3_Processor_Manual.PDF V1.5 (sha256:fcc16b54d8818b04) 第 2 页` §1.1 注 3 一句:"V3B/C 支持内存拷贝指令,具体使用方法可参考库函数且配合 MRS 编译器或其提供的工具链。"(无名称、无编码)
- 【SDK】`core_riscv.h` 中 `ASM_MCPY(DA,SA,EA)` 封装,出现在 QingkeV2C_CH32V006、V3B_CH32V205、V3V_CH32V407、V5F_CH32H417 四个 EVT 中(V2手册 V1.3、V4手册 V1.5、V5手册 V1.0 均未见记载)。语义:把源区间 SA(源起始)…EA(源结束)的连续数据拷贝到 DA(目的起始);内联汇编约束 `"+r"(SA), "+r"(DA), "r"(EA)` 表明 **SA、DA 两个寄存器会被指令改写**(EA 只读)。【手册】CH32V407RM V1.1 (sha256:63625af9027af6ab) PDF p58 明确“所有地址均无对齐要求”；仍未确认的是区间端点闭性、结束时 SA/DA、搬运粒度和可中断性。
- 汇编格式:`mcpy rs1, rs2, rs3` = `mcpy EA, SA, DA`(SDK 用法 `"mcpy %2, %0, %1"`)。
- 编码(【实测】,`mcpy a0,a1,a2` = 0x60b5700f):

| 31:27 | 26:25 | 24:20 | 19:15 | 14:12 | 11:7 | 6:0 |
|---|---|---|---|---|---|---|
| rs3=DA(目的,写回) | 00 | rs2=SA(源起始,写回) | rs1=EA(源结束) | **111** | 00000(恒 0) | **0001111**(MISC-MEM) |

  【手册】【SDK】【实测】上表采用已出货 SDK 顺序，不是照抄手册角色列。CH32V407RM p58 写 rs1=目标、rs2=起始、rs3=结束；四份 `core_riscv.h` 均发射 `mcpy EA,SA,DA`，而 CH587 ROM 先执行 `a2 += a1` 再发射 `mcpy a2,a1,a0`，也对应 rs1=EA、rs2=SA、rs3=DA。故手册 rs1/rs3 的地址角色文字应列为冲突/疑似互换；固定 bit layout 不受影响。若按手册角色列直译而交换 rs1/rs3，会把源结束与目的地址装反，可能向错误地址写入，属于数据破坏风险。

  三个寄存器操作数均可用 x0–x31(t6 实测接受)。占用标准 **MISC-MEM(0x0F)funct3=111** 未分配点(标准只用 000=fence、001=fence.i、010=cbo.*)。

### 2.2 wexti / mrslu / mrsl —— 融合移位与乘移(custom-0 空间)

- 【手册】仅 `QingKeV3_Processor_Manual.PDF V1.5 (sha256:fcc16b54d8818b04) 第 54 页` 第 9 章差异表中一行:"MRS(移位乘法自定义指令):V3A 无 / **V3B 有** / V3C 无 / V3F 无"(无助记符、无编码)。V2手册 V1.3、V4手册 V1.5、V5手册 V1.0 均未见记载。
- 【SDK】封装出现在 QingkeV2C_CH32V006 与 V3B_CH32V205 两个 EVT:
  - `wexti rd, rs1, rs2, uimm5`:rd = (((rs2<<32)|rs1) >> uimm)[31:0](64 位拼接右移取低 32,漏斗移位)
  - `mrslu rd, rs1, rs2, uimm5`:rd = (unsigned(rs1)×unsigned(rs2)) >> uimm(取低 32)
  - `mrsl  rd, rs1, rs2, uimm5`:rd = (signed(rs1)×signed(rs2)) >> uimm(取低 32)
- 编码(【实测】,`wexti a0,a1,a2,0` = 0x00c5850b):

| 31:27 | 26:25 | 24:20 | 19:15 | 14:12 | 11:7 | 6:0 |
|---|---|---|---|---|---|---|
| uimm[4:0](0–31) | funct2:**00**=wexti,**10**=mrslu,**11**=mrsl(01 未见) | rs2 | rs1 | **000** | rd | **0001011**(custom-0) |

  寄存器均可 x0–x31;uimm=32 拒绝。

### 2.3 延时指令(手册记载,汇编器无助记符)

- 【手册】`QingKeV3_Processor_Manual.PDF V1.5 (sha256:fcc16b54d8818b04) 第 54 页` 第 9 章:"mimpid[7:0]=3:新增自定义延时指令;支持 zicond 指令";同手册第 55–56 页附录 1 给出完整位表(下表为手册原文转录,已经图像复核):

| 位 | 名称 | 手册描述 |
|---|---|---|
| [31:20] | imm | 延时立即数(时钟周期数或分频后周期数) |
| [19:15] | rs1 | 匹配的 rs1 寄存器编码 |
| [14:12] | func3 | **001b** |
| [11:9] | match | 000 保留 / 001 匹配 load / 010 匹配 store / 011 匹配 load+store / 100 匹配 delay / 101 保留 / 110 匹配所有指令(流水线暂停)/ 111 匹配指定 func3+opcode(值由 CSR 配置) |
| [8] | div | 1=按分频周期计数(分频系数由 CSR 配置);0=按主频周期计数 |
| [7] | sel | 延时数选择:1=rs1+rs2;0=rs1+imm |
| [6:0] | func7 | **0001011b**(即 custom-0,与 §2.2 同一主操作码,funct3=001 区分) |

  附注(手册):以 sp 为基地址的读写指令不受 match=001/010/011 限制。配套 CSR:**U_NONS_DLY_0,地址 0x8C0**(字段见 §3.2 V3 部分)。
- 手册歧义:sel=1 时的 rs2 字段位置未给出(推测复用 [24:20],即 imm 域低段,**未证实**)。
- 【实测】GCC12/15/8 均无该指令助记符(`dly` 等尝试均拒绝);只能用 `.insn`/`.word` 手工编码。

### 2.4 自定义 32 位指令的编码空间小结

| 空间 | funct3 | 指令 | 门控 |
|---|---|---|---|
| custom-0(opcode 0001011) | 000 | wexti/mrslu/mrsl(funct2 00/10/11) | 汇编器不门控;适用线索为 V2C(SDK)/V3B(手册+SDK)，不是硅片行为验证 |
| custom-0(opcode 0001011) | 001 | 延时指令(手册,V3 mimpid≥3) | 无汇编器支持 |
| MISC-MEM(0001111) | 111 | mcpy | 汇编器不门控;适用线索为 V3B/C(手册)+V2C/V3V/V5F(SDK)，CH587 ROM 有真实产物用例 |

**风险提示**:汇编器不按 `-march` 拒绝这些指令,写错目标芯片不会在汇编期报错；运行时可能触发非法指令异常，也可能因芯片存在其它实现而有不同结果，不能由汇编器行为预判。

---

## 3. 自定义 CSR

### 3.1 总表(地址 → 各代存在性)

| CSR | 地址 | V2 | V3 | V4 | V5 | 说明 |
|---|---|---|---|---|---|---|
| gintenr | 0x800 | – | ✔(非 V3A) | ✔ | ✔ | 用户态全局中断使能(mstatus.MIE/MPIE 映射) |
| 0x804（名称见 §3.2） | 0x804 | ✔* | ✔* | ✔* | ✔* | 四本 core manual 均列 `INTSYSCR`；芯片 RM 存在 `INTSYSCR` / `HW_POPDM_CTLR` 同址异义，必须逐文档解释 |
| vcontrol | 0x805 | – | V3V | – | – | 向量控制(ABI/堆栈保护/嵌套深度) |
| vppaddr | 0x806 | – | V3V | – | – | 向量寄存器压栈基地址(1KB 对齐,复位 0x20000000) |
| vcause | 0x808 | – | V3V | – | – | 向量异常原因 |
| vtval | 0x809 | – | V3V | – | – | 向量异常 PC |
| U_NONS_DLY_0 | 0x8C0 | – | mimpid≥3 | – | – | 延时指令控制 |
| corecfgr | 0xBC0 | – | ✔(非 V3A) | ✔(无字段定义) | ✔ | 微处理器配置(流水线/预取/浮点分频等) |
| inestcr | 0xBC1 | – | ✔(非 V3A) | – | ✔ | 中断嵌套控制(NEST_LVL/NEST_STA/NEST_OV) |
| cstrcr / cache_strtg_ctlr | 0xBC2 | – | – | V4J | ✔ | 缓存策略(V4/V5 字段布局不同) |
| cpmpocr / cache_pmp_ovr | 0xBC3 | – | – | V4J | ✔ | 缓存策略覆盖 PMP |
| hw_popdm_addr | 0xBC4 | – | – | – | ✔ | **硬件压栈地址**(DTCM 区,[19:9] 可写,512bit 对齐) |
| memary_cfgr | 0xBC5 | – | – | – | ✔ | 存储器配置(TCM 访问优先级/权限/分支预测地址匹配) |
| tcm_rrduty_cfgr | 0xBC6 | – | – | – | ✔ | TCM 轮询优先时长 |
| mie(nest_mie) | 0xBC8 | – | – | – | ✔ | 各嵌套级 MIE 镜像([8:0],bit0=mstatus.MIE,bit1=MPIE)。注意:与标准 mie(0x304)地址不同,是 WCH 自义 |
| cmcr / opcache_ctlr | 0xBD0 | – | – | V4J | ✔ | 缓存操作(Icache invalidate) |
| cinfor / meminfo | 0xFC0 | – | – | V4J | ✔ | 缓存/内存信息(只读) |

`0x804` 行的 `✔*` 只表示对应 core manual 记载了该地址；芯片 RM 的名称和字段仍须按 §3.2 逐文档确认。

出处:`QingKeV2_Processor_Manual.PDF V1.3 (sha256:5430356218fca280) 第 24 页` 表 7-1;`QingKeV3_Processor_Manual.PDF V1.5 (sha256:fcc16b54d8818b04) 第 41–42 页` 表 8-1/8-2 + 第 55 页;`QingKeV4_Processor_Manual.PDF V1.5 (sha256:b543a875a199a670) 第 30 页` 表 8-1;`QingKeV5_Processor_Manual.PDF V1.0 (sha256:0a849c719d135885) 第 35–36 页` 表 8-1。表中"–"表示**该版手册未见该 CSR**(参 §0 版本错位纪律)。V5 手册把 0xBC2–0xBC8/0xBD0/0xFC0 放在"RISC-V 标准 CSR"栏目下,属分类错误(0xBCx/0xFC0 为自定义地址段),本表按实际性质归为自定义。

【实测】三个工具链的汇编器都**不认识**这些 CSR 名字(`csrr t0, intsyscr` 报 unknown CSR),必须写数字地址:`csrr t0, 0x804`。

### 3.2 CSR 0x804 逐文档同址异义（禁止按内核家族外推）

> **【后补·重要】0x804 与 0xBC0 存在同址异义,不可跨文档套用**
>
> 当前原始 PDF 只支持以下逐文档归属；括号里的 core 名称只能描述这些样本，不能反推同族所有芯片：
>
> | 地址 | 名称 A（当前明确列出的芯片 RM） | 名称 B（当前明确列出的芯片 RM） |
> |---|---|---|
> | `0x804` | `INTSYSCR`：V003、V00X、CH641、X035、L103、FV2x/V3x、M030、V205 | `HW_POPDM_CTLR`：X315、V407、H417 |
> | `0xBC0` | `CORECFGR`：M030、V205 | `CPU_RUN_CTLR`：X315、V407、H417 |
>
> 四本 QingKe core manual 的 0x804 均写 `INTSYSCR`；`CH32xRM.PDF` 未检出 0x804 字面量。`0xBC0` 的上述逐手册复位值共有 **四种**:`0x00000001` / `0x00000000` / `0x12370000` / `0x12370300`；这不是硬件读回实测。
>
> 因此下面的字段表只是在汇总四本 core manual 的 `INTSYSCR` 模式；只有目标芯片 RM 也把 0x804 命名为 `INTSYSCR` 时才能套用。分析二进制时,见到 `csrrs 0x804` 必须先锁定具体芯片和手册版本——例如 X315/V407/H417 的相同 CSR 编码应按 `HW_POPDM_CTLR` 解释。

| 位 | V2(复位 0x0) | V3(复位 0x0000E002) | V4(复位 0x0) | V5(复位 0x00000002) |
|---|---|---|---|---|
| 31 | – | LOCK(1 后仅 M 态可写;1.0 后版本有效) | – | LOCK |
| [15:8] | – | – | PMTSTA 抢占位状态(仅 V4F,RO) | – |
| 5 | – | GIHWSTKNEN 全局中断+硬件压栈关断(RTOS 上下文切换用,mret 后硬件自动清) | GIHWSTKNEN | GIHWSTKNEN |
| 4 | – | – | HWSTKOVEN 硬件压栈溢出后中断是否继续 | – |
| [3:2] | – | PMTCFG 抢占位个数 0–3(1.0 后有效) | PMTCFG 嵌套深度 无/2/4/8 级(仅 V4F 有效) | PMTCFG |
| 2 | EABIEN(EABI 使能,语义手册未展开) | – | – | – |
| 1 | INESTEN 嵌套使能 | INESTEN(固定 1;实际级数由 0xBC1.NEST_LVL 控制) | INESTEN | INESTEN(固定 1) |
| 0 | HWSTKEN 硬件压栈使能 | HWSTKEN | HWSTKEN | HWSTKEN |

出处:V2 p12(§3.2);V3 p19(§3.2);V4 p13–14(§3.2);V5 p14–15(§3.2)。V2 手册自相矛盾:表 7-1 标 URW、§3.2 表标 MRW(V2 仅有机器模式,URW 无意义)。

### 3.3 corecfgr(0xBC0)与 inestcr(0xBC1)

corecfgr:V3(V3B/C 复位 0x1;V3F 0x12370000)与 V5(0x12370300)字段见 V3 p20–21 / V5 p15–16:FADD/FMUL/FMAC/FDIV_CLKDIV[31:16](浮点分频,V3F/V5F)、CSTA_FAULT_IE[7]、INT_FENCE[6](V3:fence 指令清中断请求)、IE_REMAP_EN[5](0x800 映射使能)、V3 特有 ROM_LOOP_ACC[3]/ROM_JUMP_ACC[2]/FETCH_MODE[1:0](预取模式),V5 特有 NLP_EN[15]/GHR_EN[14](分支预测)/LSU_DUAL[10](访存双发射)。V4 手册仅给名字与"启动文件已配置默认值",**无字段定义**(V4 p34)。

inestcr:V3(p22)NEST_OV[30] 嵌套溢出标志、NEST_STA[11:8](0/1/11/111/1111b)、NEST_LVL[1:0](00 禁止/01 一级嵌套);V5(p16–17)加 LSU_NMI_STA[31],NEST_LVL 扩为 [2:0](000 禁止 … 111 允许八级)。

### 3.4 V2 独有:mstatus 自定义位

V2 的 mstatus(0x300)在标准位之外自定义了 **MPOP[23]、MPPOP[24]**:当前/次活跃中断"是否需要出栈"标志,进入中断时 MPPOP←MPOP、MPOP←本次出栈标志,mret 时 MPOP←MPPOP(V2 p24 表 7-5,p5 §2.2)。V3/V4/V5 无此二位。V2 无 mtval;V2 misa 报 X 位(非标准扩展存在,例值 0x40800014,V2 p25)。

---

## 4. 中断与异常架构扩展(对汇编/ABI 的影响)

### 4.1 PFIC(可编程快速中断控制器)

各代均以内存映射寄存器组(0xE000E000 起,兼容式布局)管理最多 256 个中断:ISR/IPR(状态)、IENR/IRER(使能置/清)、IPSR/IPRR(挂起置/清)、IACTR(激活)、IPRIOR0–255(8bit 优先级)、ITHRESDR(阈值)、SCTLR(睡眠控制/复位)。出处:`QingKeV2_Processor_Manual.PDF V1.3 (sha256:5430356218fca280) 第 6–11 页`、`QingKeV3_Processor_Manual.PDF V1.5 (sha256:fcc16b54d8818b04) 第 8–18 页`、`QingKeV4_Processor_Manual.PDF V1.5 (sha256:b543a875a199a670) 第 6–13 页`、`QingKeV5_Processor_Manual.PDF V1.0 (sha256:0a849c719d135885) 第 6–14 页`。

固定中断编号(各代一致的核):2=NMI、3=EXC、12=SysTick、14=软件中断;外部中断 16–255。V3B/C 把 5=ECALL-M、8=ECALL-U、9=BREAKPOINT 独立成入口(V3A 与 EXC 共用);V3F/V5F 向量表再加 0=RESET、13=SysTick1、16–19=IPC_CH0–3、28=HSEM,外部中断从 32 起。V2 的 NMI/EXC 优先级 -2/-1;V3/V4 系 -5…-1;V3F/V5F 加 RESET=-6。

**软件纪律(全代通用,手册反复强调)**:用寄存器屏蔽任意中断或用 CSR 关全局中断后,**必须补一条 `fence.i`** 同步内核与中断使能状态(V2 p8、V3 p10、V4 p8、V5 p8)。

优先级位宽(IPRIOR[7:x],数值越小优先级越高;高位为抢占位):V2 [7:6];V3A/V3V [7:4]、V3B [7:6]、V3C/V3F [7:5](V3 手册 p11 同时把 V3B 列进 [7:5] 组,与 p54 第 9 章"V3B 宽度 2"矛盾,见 §7);V4A [7:4]、V4B/C/J [7:5]、V4F [7:5](抢占位 1–3 个,对应嵌套 2/4/8);V5 [7:4](抢占位数由 intsyscr.PMTCFG 决定)。

### 4.2 HPE(硬件压栈,Hardware Prologue/Epilogue)

| 代 | 深度 | 保存对象 | 保存位置 | 出处 |
|---|---|---|---|---|
| V2 | 2 级 | 10 个整型 Caller-saved:x1,x5–x7,x10–x15 | **用户堆栈**(SP 自动 −48;表只列 40 字节,其余 8 字节用途未说明) | V2 p13 表 3-3 |
| V3 | 2 级 | 16 个:x1,x5–7,x10–17,x28–31 | 内部专用堆栈(用户不可见),单周期 | V3 p22–23 |
| V4 | V4F 3 级,其余 2 级 | 同 V3 的 16 个 | 内部堆栈;溢出后若 HWSTKOVEN=1 转存用户堆栈 | V4 p14–15 |
| V5 | 8 级 | 同 V3 的 16 个 | **DTCM 区**,地址由 CSR 0xBC4(hw_popdm_addr)配置 | V5 p17 |

ABI 影响(【手册】V2 p13 / V3 p23 / V4 p15 注 + 【实测】GCC12):

- 使用 HPE 的中断函数声明 `__attribute__((interrupt("WCH-Interrupt-fast")))`,普通软件压栈用 `__attribute__((interrupt))`。
- 实测序言差异:`interrupt` 版本自行 `addi sp,sp,-16; sw ...` 保存用到的 caller-saved 整型寄存器,`mret` 返回;`WCH-Interrupt-fast` 版本**完全不保存整型寄存器**(交给硬件),但在启用硬件浮点时**编译器仍软件保存/恢复全部 caller-saved 浮点寄存器到用户栈**(实测 fsw ft0…ft11,与 V4 手册 p15 注 3 一致)。
- 中断内切换上下文的 RTOS 用 intsyscr.GIHWSTKNEN 暂关"全局中断+硬件出栈",mret 后硬件自动清位(V3/V4/V5)。
- V2 的 HPE 写用户栈:中断函数内 SP 之上 48 字节是硬件帧,汇编手写中断时不可覆盖。

### 4.3 VTF(免表中断,Vector Table Free)

不查向量表、直达服务函数的通道:V2 2 路(PFIC_VTFIDR[15:0] 两个 ID + VTFADDRR0/1,地址[31:1]+使能[0]);V3/V4/V5 4 路。**V3A 例外方案**:VTFBADDRR(0xE000E044,高 4 位基址)+ VTFADDRR<i>([31:24]=中断号,[23:0]=低位地址,低 20 位有效),无使能位;V3B/C/F/V、V4、V5 用 VTFIDR+VTFADDRR([31:1] 两字节对齐地址 + [0] 使能)。出处:V2 p10/p13、V3 p14–16/p24、V4 p11–12/p16、V5 p12。

### 4.4 入口模式与向量表(mtvec)

mtvec[0](MODE0):0=统一入口,1=按"中断号×4"偏移;mtvec[1](MODE1):0=向量表放**跳转指令**,1=向量表放**服务函数绝对地址**(WCH 特有的识别模式)。各代 MCU 启动文件默认 MODE[1:0]=11(绝对地址+编号偏移)。对齐:V2 要求向量表基址 1KB 对齐(p4);V3/V5 规定 BASEADDR[9:2] 固定 0(等效 1KB 对齐,V3 p19 / V5 p15);V4 手册未写对齐约束(p14)。V3A 只支持跳转指令模式(MODE1 仅 V3B/C/F/V 有效)。汇编后果:MODE1=1 时向量表项是 `.word Handler`,MODE1=0 时是 `j Handler`。

### 4.5 异常进入/返回细节(写汇编必知)

- mepc 更新:中断→下一条未执行指令;异常→当前指令。因此 ecall/ebreak 处理后须软件 `mepc += 4`(c.ebreak 为 +2)再 mret(V2 p4、V3 p5、V4 p4、V5 p4)。
- 嵌套设计:进入"最后一级"中断前 MIE 不清零(各代;V3/V5 按嵌套深度更新),mret 时 MIE←MPIE;V2 另有 MPOP/MPPOP(§3.4)。
- 精确/非精确异步:Load/Store 访存错误(mcause=5/7)为非精确异步,V5 将 Load 访存错误改为同步(V5 p3 表 2-1)。
- WFE 不是指令:**无 WFE 操作码**(汇编器拒绝,【实测】);"WFE 睡眠"= 置 PFIC_SCTLR.WFITOWFE 后执行 `wfi`(各代手册低功耗章)。配套位:SETEVENT/SEVONPEND/SLEEPDEEP/SLEEPONEXIT。
- 用户态中断控制:gintenr(0x800)把 mstatus.MIE/MPIE 映射给 U 态,需 corecfgr[5](IE_REMAP_EN)使能(V3/V5;V4 手册未给 corecfgr 字段)。

---

## 5. 各代差异总表

| 特性 | V2(V2A/V2C) | V3(A/B/C/F/V) | V4(A/B/C/F/J) | V5(V5F) |
|---|---|---|---|---|
| 基础 ISA | RV32E(16 寄存器) | RV32I | RV32I | RV32I |
| ISA 字符串(手册) | RV32EC / RV32EmC | IMAC / I[M]C[B]+XW / IMCB+XW / IMAFCB+XW / IMACB+Zve64x+Zvbb+XW | IMAC(F 仅 V4F)/ V4A 无 XW | RV32IMABCF+XW |
| m/M | V2C 仅乘法(=Zmmul) | M(V3B 可选) | M | M(单周期乘,硬件除) |
| A | – | V3A/V3V 有;**V3A 的 lr/sc 退化为 lw/sw,sc 恒成功** | 全系 A,lr/sc 同上退化 | A(手册无退化注) |
| B(位操作) | – | V3B(可选)/C/F/V;子集手册未说明 | – | 有;子集手册未说明 |
| F | – | V3F | V4F | 有 |
| V | – | V3V:Zve64x+Zvbb,VLEN=64 | – | – |
| XW | ✔ | 除 V3A | 除 V4A | ✔ |
| 自定义 32 位指令 | 该版手册未见(SDK:V2C 有 mcpy/wexti/mrslu/mrsl) | mcpy(V3B/C)、mrslu/mrsl(V3B)、延时指令(mimpid≥3) | 该版手册未见 | 该版手册未见(SDK:mcpy) |
| 流水线 | 2 级 | 3 级 | 3 级 | 7–9 级 |
| 分支预测 | 静态 | 静态 | BHT/BTB/RAS | 动态 |
| 特权模式 | 仅 M | M+U | M+U | M+U |
| PMP | 无 | 4 区域(V3A/C/F/V;V3B 无) | 4 区域(V4B 为 0) | 4 区域(pmpcfg 加自定义 IC_Str 位 6) |
| 硬件压栈 | 2 级→用户栈 | 2 级→内部 | 2/3 级→内部(可溢出转用户栈) | 8 级→DTCM(0xBC4) |
| 嵌套深度 | 2 | 2 | 2(V4F 至 8) | 8 |
| VTF 通道 | 2 | 4(V3A 方案特殊) | 4 | 4 |
| 优先级位 | [7:6] | [7:4]/[7:6]/[7:5](见 §4.1) | [7:4]/[7:5] | [7:4] |
| SysTick | 32 位增计数,4 寄存器 | V3A 64 位(8 位写);B/C/F/V 32 位增/减 | 64 位增/减 | 32 位,寄存器布局改(0xE000F080 起) |
| mtval | 无 | 有 | 有 | 有 |
| 自定义 CSR | intsyscr(+EABIEN);mstatus.MPOP/MPPOP | gintenr/intsyscr/corecfgr/inestcr(+V3V 向量组、0x8C0) | gintenr/intsyscr/corecfgr + V4J 缓存组 | gintenr/intsyscr/corecfgr/inestcr + 缓存/TCM/nest_mie 组 |
| marchid 例值 | 0xDC68D841(WCH-V2A) | V3A 读 0 | 0xDC68D886(WCH-V4F) | 手册未给例值 |
| 调试 | DM 0.13.2,单线(V2A)/双线 | +硬件断点(V3B 指令址;V3C/F 指令+数据址)、capabi/config | 硬件断点 V4C/F/J | 断点指令+数据址;DM 含 dcsr/dpc 映射 |
| 事件(WFE 唤醒)寄存器 | 无 | EENR/EPR/EWUPR(部分芯片) | 无 | EENR/EPR/EWUPR |

注:本表比较的是**不同版本的四份手册**(V2=V1.3、V3/V4=V1.5、V5=V1.0,指纹见 §0);表中"无/–"一律读作"该版手册未见记载",不排除硬件实际具备而手册滞后(实例见 §7.3)。

---

## 6. 各代完整指令扩展枚举(对照表用)

约定:**§0 的四份 core manual 对标准扩展只给 ISA 字符串/一句话描述,均未逐条列标准指令**；自定义部分的例外是 XW 的 8 条已知助记符和 V3 delay 位表。因此下面每个标准扩展的指令清单一律标 【规范】=引用 RISC-V 规范展开,非手册内容;手册出处仅证明"该代(该版手册)支持此扩展"。自定义扩展的当前可验证编码见 §1–§2。本节各表"手册出处"列的 `pN` 按 §0 约定展开为带版本与 sha256 的完整出处(V2手册=V1.3/`5430356218fca280`,V3手册=V1.5/`fcc16b54d8818b04`,V4手册=V1.5/`b543a875a199a670`,V5手册=V1.0/`0a849c719d135885`);"无/未提"一律指该版手册未见。

### 6.0 标准扩展指令清单(各代共用的展开,【规范】)

- **RV32I 基础整数**(Unprivileged ISA 20191213,I 2.1;RV32E 与 RV32I 指令集相同、仅寄存器数 16):
  `lui auipc jal jalr beq bne blt bge bltu bgeu lb lh lw lbu lhu sb sh sw addi slti sltiu xori ori andi slli srli srai add sub sll slt sltu xor srl sra or and fence ecall ebreak`
- **Zicsr**:`csrrw csrrs csrrc csrrwi csrrsi csrrci`;**Zifencei**:`fence.i`。各代手册的 ISA 字符串都没写这两个名字,但正文明确使用 CSR 指令与 fence.i(如 V2 p8),GCC12/15 需在 march 中显式或由 `i` 隐含(工具链 multilib 见 §1.5);按事实上全代支持处理。
- **特权指令**(手册正文使用):`mret`(异常返回,各代 §2.4)、`wfi`(低功耗章)。无 `wfe` 操作码(§4.5)。
- **M**:`mul mulh mulhsu mulhu div divu rem remu`;**Zmmul** 为其乘法子集:`mul mulh mulhsu mulhu`。
- **A(RV32)**:`lr.w sc.w amoswap.w amoadd.w amoxor.w amoand.w amoor.w amomin.w amomax.w amominu.w amomaxu.w`(= Zalrsc + Zaamo;GCC15 multilib 即按 `zaamo_zalrsc` 拼写)。
- **C(RV32,无浮点寄存器时)**:`c.addi4spn c.lw c.sw c.nop c.addi c.jal c.li c.addi16sp c.lui c.srli c.srai c.andi c.sub c.xor c.or c.and c.j c.beqz c.bnez c.slli c.lwsp c.jr c.mv c.ebreak c.jalr c.add c.swsp`;带 F 的型号(V3F/V4F/V5F)另含 `c.flw c.flwsp c.fsw c.fswsp`;启用 XW 时 `c.fld/c.fsd/c.fldsp/c.fsdsp` 的压缩编码槽被占用,不能再作为完整 D+C 形式使用(§1.4)。
- **F(RV32)**:`flw fsw fmadd.s fmsub.s fnmsub.s fnmadd.s fadd.s fsub.s fmul.s fdiv.s fsqrt.s fsgnj.s fsgnjn.s fsgnjx.s fmin.s fmax.s fcvt.w.s fcvt.wu.s fmv.x.w feq.s flt.s fle.s fclass.s fcvt.s.w fcvt.s.wu fmv.w.x`(+ CSR fflags/frm/fcsr)。
- **位操作 B**:手册各代仅写"B:支持位操作指令",**未指明子扩展构成**;工具链 multilib 按 `zba_zbb_zbc_zbs` 组合建库(【实测】),按此展开:
  - Zba:`sh1add sh2add sh3add`
  - Zbb(RV32):`andn orn xnor clz ctz cpop max maxu min minu sext.b sext.h zext.h rol ror rori orc.b rev8`
  - Zbc:`clmul clmulh clmulr`
  - Zbs:`bclr bclri bext bexti binv binvi bset bseti`
- **Zicond**(V3 mimpid≥3,V3 p54):`czero.eqz czero.nez`。【实测】GCC15 需 `-march=..._zicond`;GCC12/GCC8 不支持该扩展名。
- **Zve64x + Zvbb**(仅 V3V;V3 p2 注明按《RISC-V "V" vector Extension 1.0》,VLEN=64,支持 8/16/32/64bit 元素;64bit EEW 需 vcontrol 配置)。【规范】RVV 1.0 展开(手册仅给名字):
  - 配置:`vsetvli vsetivli vsetvl`
  - 载入/存储(eew ∈ {8,16,32,64}):`vle{eew}.v vse{eew}.v vlse{eew}.v vsse{eew}.v vluxei{eew}.v vloxei{eew}.v vsuxei{eew}.v vsoxei{eew}.v vle{eew}ff.v`;分段(nf=2–8):`vlseg<nf>e{eew}.v vsseg<nf>e{eew}.v vlsseg<nf>e{eew}.v vssseg<nf>e{eew}.v vluxseg<nf>ei{eew}.v vloxseg<nf>ei{eew}.v vsuxseg<nf>ei{eew}.v vsoxseg<nf>ei{eew}.v`;整寄存器:`vl<n>re{eew}.v vs<n>r.v`(n∈{1,2,4,8});掩码:`vlm.v vsm.v`
  - 整数算术:`vadd vsub vrsub vwaddu vwadd vwsubu vwsub vwaddu.w vwadd.w vwsubu.w vwsub.w vzext.vf{2,4,8} vsext.vf{2,4,8} vadc vmadc vsbc vmsbc vand vor vxor vsll vsrl vsra vnsrl vnsra vmseq vmsne vmsltu vmslt vmsleu vmsle vmsgtu vmsgt vminu vmin vmaxu vmax vmul vmulh vmulhu vmulhsu vdivu vdiv vremu vrem vwmul vwmulu vwmulsu vmacc vnmsac vmadd vnmsub vwmaccu vwmacc vwmaccsu vwmaccus vmerge vmv.v`(各带 .vv/.vx/.vi 等合法后缀)
  - 定点:`vsaddu vsadd vssubu vssub vaadd vaaddu vasub vasubu vsmul vssrl vssra vnclipu vnclip`
  - 归约:`vredsum vredmaxu vredmax vredminu vredmin vredand vredor vredxor vwredsumu vwredsum`
  - 掩码运算:`vmand.mm vmnand.mm vmandn.mm vmxor.mm vmor.mm vmnor.mm vmorn.mm vmxnor.mm vcpop.m vfirst.m vmsbf.m vmsif.m vmsof.m viota.m vid.v`
  - 排列/移动:`vmv.x.s vmv.s.x vslideup vslidedown vslide1up vslide1down vrgather vrgatherei16 vcompress.vm vmv<n>r.v`
  - Zvbb:`vandn.{vv,vx} vbrev.v vbrev8.v vrev8.v vclz.v vctz.v vcpop.v vrol.{vv,vx} vror.{vv,vx,vi} vwsll.{vv,vx,vi}`
  - (无浮点向量指令——Zve64x 为纯整数向量)

### 6.1 V2(手册 V1.3)

| 扩展 | 型号 | 手册出处 | 指令清单 |
|---|---|---|---|
| RV32E | V2A/V2C | p1 说明、p2 §1.1("E:RV32I 子集,仅支持 16 个通用寄存器") | 手册只给字符串;清单见 §6.0 RV32I(寄存器限 x0–x15)【规范】 |
| C | V2A/V2C | p2 §1.1 | 手册只给字符串;§6.0 C(无浮点形式)【规范】 |
| m = Zmmul | 仅 V2C | p1、p2 注 2("m 扩展仅包括硬件乘法指令,即 Zmmul 扩展") | `mul mulh mulhsu mulhu`【规范】;**无除法指令** |
| XW | V2A/V2C | p2 表 1-1、注 1 | 8 条,完整编码见 §1【实测】 |
| Zicsr/Zifencei/特权 | 全部 | 正文使用(p8 fence.i、p24 CSR 表、p4 mret、p17 wfi) | §6.0【规范】 |
| mcpy/wexti/mrslu/mrsl | V2C(CH32V006) | **该版手册(V1.3)未见记载**;【SDK】CH32V006 EVT `core_riscv.h` | §2【实测】 |

工具链对应 march:`rv32ec_xw`、`rv32ec_zmmul_xw`(GCC12/15);`rv32ecxw`(GCC8)。

### 6.2 V3(手册 V1.5)

型号 ISA 字符串(p1 说明,原样转录;方括号表示部分芯片可选):V3A `RV32IMAC`;V3B `RV32I[M]C[B]` + XW;V3C `RV32IMCB` + XW;V3F `RV32IMAFCB` + XW;V3V `RV32IMACB_Zve64x_zvbb` + XW。**手册只给 ISA 字符串,未逐条列指令。**

| 扩展 | 型号 | 手册出处 | 指令清单 |
|---|---|---|---|
| I | 全部 | p2 §1.1 | §6.0【规范】 |
| M | A/C/F/V,B 可选 | p1/p2 | §6.0【规范】 |
| A | V3A/V3V | p2("其中 V3A 对 lr、sc 指令进行了简单化处理,仅作为 lw,sw 执行,且 sc 结果返回总是成功") | §6.0【规范】;注意 V3A 的 lr/sc 语义退化(手册明示) |
| C | 全部 | p2 | §6.0【规范】;V3F 含 c.flw 族 |
| B | B(可选)/C/F/V | p2("B:支持位操作指令",无子集) | 子集构成手册未说明;按工具链 `zba_zbb_zbc_zbs` 展开【实测+规范】 |
| F | V3F | p2 | §6.0 F【规范】 |
| V=Zve64x+Zvbb | V3V | p2("支持 zve64x 和 zvbb 指令集,向量寄存器位宽 64 位") | §6.0【规范】 |
| XW | B/C/F/V | p2 表 1-1、注 2 | §1【实测】 |
| Zicond | mimpid≥3 | p54 第 9 章 | `czero.eqz czero.nez`【规范】 |
| 延时指令 | mimpid≥3 | p54–56(附录 1,含位表) | §2.3(手册位表 + 无汇编器支持) |
| 内存拷贝 = mcpy | V3B/C | p2 注 3(无名称/编码) | §2.1【实测+SDK】 |
| "MRS 移位乘法"线索；工具链候选为 mrslu/mrsl(+wexti) | V3B | p54 第 9 章(仅一行,不能据此证明名称等同) | §2.2【实测+SDK】 |
| Zicsr/Zifencei/特权 | 全部 | 正文使用 | §6.0【规范】 |

第 9 章(p54)其余代内差异:AMO(V3A/F 有,B/C 无)、PMP(A/C/F 有,B 无)、LSU_TRIGGER(C/F 有)、优先级宽度 4/2/3/3;mimpid[7:0]=1(仅 CH32M030/CH585)、=2(软件复位/STK_CTLR[31] 软中断标志/嵌套使能屏蔽/抢占位宽配置)、=3(延时指令、zicond)。

### 6.3 V4(手册 V1.5)

| 扩展 | 型号 | 手册出处 | 指令清单 |
|---|---|---|---|
| I/M/A/C | 全部(ISA=RV32IMAC) | p1 说明、p2 表 1-1、§1.1 | 手册只给字符串;§6.0【规范】。**A 的 lr/sc 全系退化为 lw/sw、sc 恒成功**(p2 §1.1,与 V3A 同措辞) |
| F | V4F(RV32IMACF) | p1/p2 | §6.0 F【规范】 |
| XW | B/C/F/J(V4A 无) | p1 说明、p2 表 1-1、注 2 | §1【实测】 |
| B/V 等 | 无 | – | 该版手册(V1.5)未见任何位操作/向量扩展记载 |
| Zicsr/Zifencei/特权 | 全部 | 正文使用 | §6.0【规范】 |
| 自定义 32 位指令 | 该版手册(V1.5)未见记载 | – | V4 各 EVT 头文件亦未包含 mcpy 等封装【SDK】 |

V4J 的 I-Cache 是 CSR 控制的微架构特性(cstrcr/cpmpocr/cmcr/cinfor,§3.1),不新增指令。

### 6.4 V5(手册 V1.0)

| 扩展 | 型号 | 手册出处 | 指令清单 |
|---|---|---|---|
| I/M/A/B/C/F | V5F(ISA=RV32IMABCF;封面特点表写作 RV32IMABCFX) | p1 说明、p2 表 1-1、§1.1 | 手册只给字符串;§6.0【规范】。M:"支持单周期乘法和硬件除法"(p1);A:无 lr/sc 退化注(与 V3A/V4 不同);B 子集未说明(工具链按 zba_zbb_zbc_zbs) |
| XW | V5F | p1/p2、注 1 | §1【实测】 |
| Zicsr/Zifencei/特权 | 全部 | 正文使用 | §6.0【规范】 |
| mcpy | V5F(CH32H417) | 该版手册(V1.0)未见记载;【SDK】CH32H417 EVT | §2.1【实测】 |

### 6.5 独有/通用速查

- 四份当前 core manual 都记载 C、Zicsr/Zifencei 的正文用法以及 PFIC/HPE/VTF 架构；XW 按 §1.6 的具体型号矩阵，0x804 的名称和字段必须按 §3.2 的具体文档解释。
- 单代/单型号独有:RV32E+Zmmul(V2);Zve64x/Zvbb、向量 CSR 组、延时指令、zicond(V3V/V3 新版);wexti/mrslu/mrsl(V2C+V3B);EABIEN、mstatus.MPOP/MPPOP(V2);I-Cache CSR 组(V4J/V5F 各自布局);hw_popdm_addr/nest_mie/TCM CSR(V5);B 扩展(V3 B/C/F/V 与 V5)。
- 同名不同实现:A 扩展(V3A/V4 退化 lr/sc vs V5 未注明退化);HPE(4 代 4 种深度/落地);SysTick(4 种布局);优先级位宽(§4.1)。
- 本速查中"独有/除外"均以各代**对应版本手册**的记载为准(版本与指纹见 §0);跨版本空缺的解释纪律见 §0。

---

## 7. 手册未给出/未能确认的内容、勘误与冲突

### 7.1 手册未给出(本文以实测/SDK 补齐,已标注)

1. **XW 全部位编码、操作数约束、立即数范围、版本号**——手册只有一句助记符清单。编码全部来自汇编器实测(GCC8/12/15 三方一致;ELF 属性版本 xw1p0)。
2. **mcpy 的精确运行语义仍未完全确认**:CH32V407RM V1.1 p58 已给名称、编码并明确“所有地址均无对齐要求”；其 rs1/rs3 地址角色文字与 SDK/ROM 的 `EA,SA,DA` 顺序冲突。仍缺源区间端点闭性、执行后 SA/DA、搬运粒度、可否中断和硅片行为复核。
3. **"MRS 移位乘法自定义指令"的名称与编码**(手册仅一行"V3B 有")——按 SDK 对应到 mrslu/mrsl;**wexti 连名字都未在任何手册出现**,仅存在于 SDK 与汇编器。custom-0 funct2=01 编码点用途未知。
4. **延时指令**:无官方助记符;sel=1 时 rs2 字段位置未给出;三个工具链均无汇编支持。
5. V4 的 **corecfgr(0xBC0)字段定义**(手册明说不展开)。
6. **B 扩展子集构成**(V3/V5)——手册只写"支持位操作指令";zba_zbb_zbc_zbs 是工具链 multilib 推断。
7. V2 **EABIEN** 的具体行为(仅"EABI 使能"四字)。
8. V2 HPE 压栈 48 字节中仅列出 40 字节的寄存器布局,剩余 8 字节用途未说明。
9. Zicsr/Zifencei 未出现在任何一代的 ISA 字符串中(由正文用法推定支持)。
10. 手册中的流程/结构插图(V2 图 2-1/3-2,V3 图 3-1/3-2,V4 图 2-1/3-2,V5 图 3-1/3-2)为图片,文本抽取仅得零散标注;经图像复核,其内容为示意图,不含编码表,无信息损失风险。
11. **【后补·重要】XW 编码表的覆盖上限**:EVT inventory 是 12/0/11；全语料 187 组是 62/4/121，其中 71 组无 attributes；全语料中实际使用 XW 的 100 组才是 62/4/34。集合差已完成且为 0，但只在 Q0/funct3=4 剩余 1,536 个点有判别力且零命中；其它四槽语义重定义、五槽外新编码和本地工具链未知助记符仍不能排除。详见 §1.5 与 `round2-xw-audit.json`。

### 7.2 手册自身勘误(原文如此,引用时当心)

1. `QingKeV2_Processor_Manual.PDF V1.3 (sha256:5430356218fca280) 第 24 页` 表 7-2:marchid Serial 字段描述"青稞 V2 系列,固定为数字 4",与第 25 页示例 0xDC68D841(解码 Serial=2)矛盾;疑从 V4 手册复制(V4手册 p30–31 的"数字 4"与示例 0xDC68D886 解码一致)。
2. V5 p36:marchid Serial 描述"固定为数字 5"而复位值列写 0x03(疑复制自 V3)。
3. V2 p11 / V4 p11:中断全局状态寄存器小节表头把 0xE000E04C 的寄存器名写成 PFIC_CFGR(应为 PFIC_GISR)。
4. V5 p13:事件唤醒寄存器(PFIC_EWUPR)表格中名称/地址误写为 PFIC_EENR/0xE000EC84。
5. V3 p11–12:PFIC_IPRIOR 描述先给"V3B:[7:6]"又出现"V3B/V3C/V3F:[7:5]"分组,与 p54 第 9 章"V3B 宽度 2"矛盾;按第 9 章取 V3B=[7:6] 为准,[7:5] 组疑为"V3C/V3F"笔误。
6. V2 表 7-1 将 intsyscr 访问权限标为 URW,但 V2 仅实现机器模式(§3.2 表又标 MRW)。
7. V5 表 8-1 把 0xBC2–0xBC8/0xBD0/0xFC0 归入"RISC-V 标准 CSR"(实为厂商自定义地址段)。
8. CH32V407RM V1.1 p58 的 mcpy 表写 rs1=目标、rs3=结束；四份 `core_riscv.h` 与 CH587 ROM 一致采用 rs1=EA、rs3=DA。固定编码位一致，地址角色文字疑似互换。

### 7.3 手册记载与汇编器实测的冲突

- **固定编码位的对撞结果**：QingKe V3 p55 与 CH32V407RM p57 的 delay 位表一致，CH32V407RM p58 的 mcpy 固定位/寄存器位置与 assembler `0x60b5700f` 一致；rs1/rs3 地址角色文字冲突见 §2.1。XW 手册仍无位编码。另需记录这些**手册未提示的工具链行为**:
  1. 汇编器可接受 D+C+XW 的 `-march` 字符串，但对重叠的 `c.fld/c.fsd/c.fldsp/c.fsdsp` 源句报 `illegal operands`；不是静默禁用(§1.4);
  2. Zcb 与 XW 同名异码(§1.4);
  3. 三个 objdump 均不能正确反汇编 XW：GCC12/15 打 raw，GCC8 objdump 会误反汇编为 fld/fsd(§1.5);
  4. mcpy/wexti/mrslu/mrsl 不受 `-march` 门控,错芯片不报汇编错误(§2.4);
  5. 自定义 CSR 无符号名,须用数字地址(§3.1)。
- **该版手册未见但 SDK 已提供接口**:V2C(CH32V006)与 V5F(CH32H417)的 SDK 出货了 mcpy(V2C 另含 wexti/mrslu/mrsl)封装,而 V2手册 V1.3 与 V5手册 V1.0 对这些指令只字未提。不能据当前版手册断言"V2/V5 不支持"，也不能只凭 SDK 封装声称所有对应硅片均已行为验证。
