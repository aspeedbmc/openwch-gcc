# WCH XW 的设计谱系与实现来源分析

日期：2026-08-13

## 摘要结论

现有证据不支持把 XW 简单归类为“WCH 完全从零设计”，也不足以证明 WCH 购买或复制了某家完整 CPU IP。

最强事实是：WCH XW 的四条非 SP 指令 `c.lbu/c.lhu/c.sb/c.sh`，与 Huawei/HCC 最迟在 2020 年公开、并声称已经在 HiMiDeer SV100/V200 硅片中实现的四条压缩访存指令，在以下各项上全部相同：

- 助记符；
- 运算语义；
- x8–x15 压缩寄存器窗口；
- byte/halfword offset 范围与对齐要求；
- funct3、quadrant、寄存器字段；
- 被打散的立即数字段位置，即逐位编码。

这种一致性远强于“两个团队独立解决相同代码密度问题”通常产生的功能相似，因而高度支持二者属于同一 ISA 设计谱系。它使“WCH 复用或借鉴 Huawei/HCC 已公开设计”成为很合理的解释，但现有材料不能确定传播渠道，也不能证明 WCH 获得过 Huawei 的 CPU RTL、核 IP、许可证或源码。

XW 的另外四条 SP 形式 `c.lbusp/c.lhusp/c.sbsp/c.shsp` 不在 Huawei 2020 年的编码提案中。Huawei 2021 年的代码尺寸分析脚本出现过同样名称，但没有给出编码，也不能证明已成为 Huawei ISA 或硅片实现。因此，这四条可能是 WCH 的补充设计，也可能来自尚未公开的共同草案；目前无法定案。

标准 Zcb 不是 XW 的直接来源：Zcb 出现和批准都更晚，虽然四条指令同名同义，但立即数范围和编码不同。

最准确的总判断是：

> XW 很可能是在 Huawei/HCC 压缩访存设计谱系上形成的 WCH vendor extension；WCH 至少自行完成了 QingKe 集成、工具链与产品化工作，并可能自行增加了四条 SP 形式。现有证据无法判断其微架构/RTL 实现是否借用了任何第三方 CPU IP。

## 1. 问题边界：ISA 设计不等于 CPU IP 实现

需要把三个问题分开：

1. **指令集设计来源**：指令名称、语义、操作数约束和位编码从哪里来。
2. **工具链实现来源**：GCC、GAS、objdump 如何接受、生成和标记这些指令。
3. **处理器实现来源**：译码器、流水线、存储单元和 RTL 是否来自第三方核 IP。

四条指令逐位相同，可以强力说明共享或复用了同一 ISA 设计，但不能单独证明共享 CPU RTL。一个厂商完全可以采用已有的公开指令编码，再在自己的处理器、汇编器和软件栈中独立实现。

本文中的“同源”“复用”或“借鉴”默认指 **ISA 设计谱系**，不等同于“购买或复制 CPU IP”。

## 2. WCH XW 的已确认事实

### 2.1 官方定义与当前已知集合

QingKe V2、V3、V4、V5 当前版本处理器手册均将 XW 描述为用于提高代码密度的“字节和半字操作的 16 位压缩指令”，并列出八个形式：

- `c.lbu`
- `c.lhu`
- `c.sb`
- `c.sh`
- `c.lbusp`
- `c.lhusp`
- `c.sbsp`
- `c.shsp`

手册没有给出位编码、操作数约束、立即数范围或可信的版本演化史。这些内容是本项目通过官方工具链与交付库实测恢复的。

本地证据入口：

- [QingKe 自定义 ISA 深入分析](ref/wch-isa-research/isa/custom/qingke-custom-isa.md)，§1.1–§1.6；
- [WCH/QingKe 自定义 ISA 参考](ref/wch-isa-research/isa/custom/wch-custom-isa-reference.md)，§3–§4；
- [WCH GCC 工具链调查](analysis/toolchain/wch-gcc-toolchain-survey.md)，XW 接受面与编码部分。

XW 不是所有 WCH 私有指令的总称。`mcpy/wexti/mrslu/mrsl` 四个 32 位 custom 指令不受 XW `-march` 开关控制；delay、CSR 和其它 QingKe 功能也不能自动归入 XW。手册另有更宽泛的 `WCH-X` 表述，但其完整集合关系仍未确认。

### 2.2 非 SP 四条的操作数和编码

四条非 SP 指令的实测约束如下：

| 指令 | 数据和基址寄存器 | offset |
|---|---|---|
| `c.lbu` | x8–x15 | 0–31，步长 1 |
| `c.lhu` | x8–x15 | 0–62，步长 2 |
| `c.sb` | x8–x15 | 0–31，步长 1 |
| `c.sh` | x8–x15 | 0–62，步长 2 |

立即数映射为：

- `c.lbu/c.sb`：instruction bit 12 = `uimm[0]`，bits 11:10 = `uimm[4:3]`，bits 6:5 = `uimm[2:1]`；
- `c.lhu/c.sh`：instruction bit 12 = `uimm[5]`，bits 11:10 = `uimm[4:3]`，bits 6:5 = `uimm[2:1]`。

寄存器字段使用标准 RVC 的三位压缩寄存器编码。代表性样例：

```text
c.lbu a0,0(a1) = 0x2188
c.lhu a0,0(a1) = 0x218a
c.sb  a0,0(a1) = 0xa188
c.sh  a0,0(a1) = 0xa18a
```

GCC 8、12、15 的 WCH 工具链对这些形式产生相同编码。

### 2.3 四条 SP 形式

四条 SP 形式的实测约束如下：

| 指令 | 数据寄存器 | 基址 | offset |
|---|---|---|---|
| `c.lbusp` | x8–x15 | sp | 0–15，步长 1 |
| `c.lhusp` | x8–x15 | sp | 0–30，步长 2 |
| `c.sbsp` | x8–x15 | sp | 0–15，步长 1 |
| `c.shsp` | x8–x15 | sp | 0–30，步长 2 |

它们位于 quadrant 0、funct3=100、bits 12:11=00 的区域，以 bits 6:5 区分四个形式。代表性样例：

```text
c.lbusp a0,0(sp) = 0x8008
c.lhusp a0,0(sp) = 0x8028
c.sbsp  a0,0(sp) = 0x8048
c.shsp  a0,0(sp) = 0x8068
```

### 2.4 编码冲突反映的设计背景

XW 非 SP 四条复用了 RV32 D+C 的四个压缩双精度浮点访存槽：

- `C.FLD`
- `C.FLDSP`
- `C.FSD`
- `C.FSDSP`

例如同一半字 `0x2188` 在不同 ISA 解释下可以是 XW `c.lbu a0,0(a1)`，也可以是 `c.fld fa0,0(a1)`。所以完整的 D+C 压缩双精度访存形式不能与 XW 同时工作；这不影响非压缩 D 指令本身。

SP 四条又占用了后来 Zcb 使用的 quadrant 0、funct3=100 区域。XW 还与 Zcmp/Zcmt 的部分槽位冲突。因此 XW 更像在标准 Zc 家族定型前，针对 MCU 代码密度缺口进行的一次 vendor 编码分配。

F+C+XW 则可以共存，因为 RV32 的压缩单精度浮点槽与 XW 不重叠，WCH multilib 也明确包含 `rv32imafc_xw/ilp32f`。

### 2.5 GCC 和 GAS 的职责

WCH GCC 对 XW 的已确认职责是：

- 接受 `-march` 中的 XW 名称和版本；
- 定义 `__riscv_xw`；
- 保存 function target attribute 中的 XW 状态；
- 选择含 XW 的 multilib。

没有发现 XW 专用 GCC MD pattern、builtin、intrinsic、`-mxw` 开关或独立选指逻辑。GCC backend 正常输出普通 `lbu/lhu/sb/sh`；GAS 在 XW 开启且操作数满足约束时，将其自动压缩为 16 位 XW 编码。

因此，最终 GCC 驱动产物会出现 XW 字节，但完成指令压缩选择和编码的是 GAS，而不是 GCC backend。

## 3. Huawei/HCC 的直接设计先例

### 3.1 2020 年公开材料

RISC-V code-size reduction 工作组仓库在 2020-09-04 收录了一份 Huawei Custom Extension/HCC 压缩 byte/halfword load/store 提案：

- [2020-09-04 原始提交](https://github.com/riscvarchive/riscv-code-size-reduction/commit/eb1ef0f66d92db9a16a17ed79e954185a0fe4975)
- [2020-11-10 修订提交](https://github.com/riscvarchive/riscv-code-size-reduction/commit/3e958ca838da2ae438d1ec3a84b8fae2edc97fd7)
- [对应规范原文](https://raw.githubusercontent.com/riscvarchive/riscv-code-size-reduction/3e958ca838da2ae438d1ec3a84b8fae2edc97fd7/existing_extensions/Huawei%20Custom%20Extension/riscv_ldst_bh_extension.rst)

文件称四条指令已包含在 Huawei custom RISC-V extension 中、由内部 HCC GCC 支持，并已在 HiMiDeer SV100/V200 silicon 中实现。更早的 [CARRV 2020 材料](https://github.com/riscvarchive/riscv-code-size-reduction/blob/main/CARRV2020_final.pdf) 也公开讨论了 HCC 的 compressed byte/halfword load/store，但完整逐位表以 2020-09-04 的提交为清晰锚点。

这里的公开日期不是设计开始日期。材料自身声称此前已经有编译器和硅片实现，所以实际内部设计必然更早。

### 3.2 与 WCH XW 的逐字段对照

| 维度 | Huawei/HCC 2020 | WCH XW 非 SP 四条 | 结论 |
|---|---|---|---|
| 助记符 | `c.lbu/c.lhu/c.sb/c.sh` | 完全相同 | 相同 |
| 语义 | unsigned byte/half load，byte/half store | 完全相同 | 相同 |
| signed forms | 未采用，理由是收益较低 | 没有 `c.lb/c.lh` | 相同取舍 |
| 寄存器窗口 | x8–x15 | x8–x15 | 相同 |
| byte offset | 0–31 | 0–31 | 相同 |
| halfword offset | 0–62，步长 2 | 0–62，步长 2 | 相同 |
| funct3/quadrant | 指定四个 D/C 槽 | 同四槽 | 相同 |
| 寄存器字段 | RVC 三位窗口 | 相同 | 相同 |
| 立即数字段 | 特定打散布局 | 逐位相同 | 相同 |

Huawei 表可以直接推出：

```text
c.lbu a0,0(a1) = 0x2188
```

这与 WCH 官方工具链实测值完全一致。

这种一致性不是“都想给 byte/halfword load/store 做压缩编码”就足以解释的。即使目标和助记符相同，设计者仍可选择不同的寄存器窗口、offset 宽度、编码槽和立即数排列；Huawei/HCC 与 WCH 在所有这些自由度上都作出了相同选择。

因此，“共享或复用了同一个具体 ISA 设计”是高置信分析。

### 3.3 SP 四条的 Huawei 线索较弱

Huawei 的 2020 编码提案不包含 `c.lbusp/c.lhusp/c.sbsp/c.shsp`。

Huawei 在 2021-06-21 提交的代码尺寸分析脚本中出现过这四个确切名称：

- [2021-06-21 分析脚本提交](https://github.com/riscvarchive/riscv-code-size-reduction/commit/a528fafba93e360ed8996cdc2f7477939353123a)

但该材料只有收益建模，没有位编码；脚本中的候选 offset 范围也比 WCH 实现更大。它不能证明 Huawei 已把这些形式加入 ISA，更不能证明已经有硅片实现。

所以对 SP 四条只能说：两边存在共同的命名和需求思路，但尚无逐位同源证据。

## 4. 与标准 RISC-V 压缩扩展的关系

### 4.1 原始 C 扩展

原始 C 扩展提供压缩 word、doubleword 和浮点访存，但没有 byte/halfword 压缩访存。XW 填补的是一个真实且普遍的代码密度缺口，同时借用了原有 RVC 编码模板和部分 D 槽。

这说明 C 是 XW 的设计背景，但不能解释 Huawei/HCC 与 WCH 的逐位身份。

### 4.2 Zcb

现行 Zcb 也提供 `c.lbu/c.lhu/c.sb/c.sh`，但只是解决相同问题，并非 XW 的直接编码来源：

| 维度 | WCH XW | 标准 Zcb |
|---|---|---|
| 四条同名指令 | 有 | 有 |
| 寄存器窗口 | x8–x15 | x8–x15 |
| byte offset | 0–31 | 0–3 |
| halfword offset | 0–62 | 0 或 2 |
| 编码槽 | 复用四个 D/C 槽 | quadrant 0、funct3=100 |
| `c.lbu a0,0(a1)` | `0x2188` | `0x8188` |
| SP 四条 | 有 | 没有 |

Zcb 的设计和批准时间也更晚：Huawei 的完整同码设计最迟在 2020 年公开；Zc 工作在 2021 年仍处于早期计划阶段，现行路线在 2022 年逐步稳定，并于 2023-04-27 ratified：

- [Zc v1.0 ratification commit](https://github.com/riscvarchive/riscv-code-size-reduction/commit/61891aa8e6f4f4bc43eb1beb190d63f45dab5651)

因此不能说 WCH XW 借鉴了已经批准的 Zcb。更合理的表述是：Huawei/WCH 的早期 vendor 路线和后来 Zcb 都在解决同一代码密度问题，而标准最终选择了不同编码。

### 4.3 Zcmb、Zcmp、Zcmt 和 Zce

- 早期 Zcmb 草案也探索过复用 D 槽实现 byte/halfword load/store，因此方向接近 Huawei/WCH 路线，但其命名、signed forms 和具体布局不完全相同；后来被删除。
- Zcmp/Zcmt 分别服务于 push/pop、寄存器操作和 table jump；与 XW 只有编码空间冲突，没有指令语义谱系上的相似性。
- Zce 是 Zca、Zcb、Zcmp、Zcmt 等扩展的 MCU 聚合名，不引入一套新的指令编码，因此不是独立的 XW 来源候选。

## 5. 其它厂商 IP 的对照

### 5.1 T-Head

T-Head 的公开 XTheadMemIdx 也覆盖 byte/halfword load/store，但它使用 32 位 custom-0 编码、全 GP 寄存器、indexed/post-increment 寻址，助记符例如 `th.lbuia`。这与 XW 的 16 位 RVC 窗口和立即数模型不是同形设计。

- [XTheadMemIdx 公开规格提交，2022-07-27](https://github.com/T-head-Semi/thead-extension-spec/commit/28c85e6ef86fd20e6444f7e5a336acec9a170189)

### 5.2 Andes

Andes CoDense 同样追求代码密度，但公开工具链中的核心机制是 `exec.it/nexec.it`；公开的 GP-relative byte/halfword 访存也是 32 位形式。当前未找到与 XW 八条在名称、窗口、立即数和编码上同形的公开设计。

### 5.3 SiFive 和 Nuclei

在本轮检索到的官方规格、开放工具链和 opcode 表中，没有找到与 XW 同时满足“同名、同寄存器窗口、同立即数范围、同槽位和逐位同编码”的公开形式。

这是有限公开资料上的阴性结果，只能写作“未找到公开证据”，不能断言绝对不存在内部或未公开方案。

## 6. WCH 与第三方 CPU IP 的公开证据

### 6.1 WCH 确实承认早期外购过内核

WCH 官方历史页面称，其早期针对安全类产品曾外购第三方 RISC-V 内核；由于当时 IP 尚未成熟，WCH 从 2017 年开始关注和研究，随后形成 QingKe 系列处理器，并在 2019 年推出基于 QingKe V3A 的 CH32V103。

- [WCH RISC-V MCU 官方历史页](https://special.wch.cn/zh_cn/RISCV_MCU_Index/)
- [该表述的 2020-09-23 网页归档](https://web.archive.org/web/20200923051729id_/http://special.wch.cn/zh_cn/RISCV_MCU_Index/)

这是“WCH 早期外购过某个第三方 RISC-V 核”的直接厂商证据，但只能用于其所述的早期安全类产品。页面没有给出供应商、具体芯片、许可证或技术继承关系。

### 6.2 没有证据把该早期内核等同于 QingKe 或 XW

当前没有公开证据能够回答：

- 早期供应商是谁；
- 交付的是完整 RTL、软核、硬核还是其它形式；
- 哪个具体产品使用过它；
- QingKe 是否继承其中任何微架构、RTL 或自定义 ISA；
- Huawei、Andes、Nuclei、T-Head、SiFive 中是否有任何一家是该供应商。

WCH 当前官方页面称“青稞处理器是沁恒微电子自研的 32 位微处理器”：

- [WCH QingKe 官方介绍 API](https://www.wch.cn/api/official/website/articles/getArticle?alias=QingKe.html)
- [2024-09-08 网页归档](https://web.archive.org/web/20240908033825id_/https://api3.wch.cn/api/official/website/articles/getArticle?alias=QingKe.html)

这是一方厂商声明，不是独立 RTL 审计；但在没有相反直接证据时，也不能仅凭 ISA 编码相同就否定 QingKe 的自研实现属性。

## 7. WCH XW 的可证时间线

### 7.1 不能用 GCC 版本号给 XW 定年

WCH 的旧工具链显示 GCC 8.2.0，但这是后来构建和重新打包的工具链基线，不能据此推断 XW 在 2018 或 2019 年已经存在。包内构建信息甚至同时出现 `riscv-gcc-10.2.0-1.1` 路径，说明版本号不是 XW 首发日期。

见 [旧工具链取证](analysis/toolchain/wch-gcc-toolchain-survey.md) 的 GCC8 部分。

### 7.2 当前本地语料最早的可靠日期

当前仓库里最早能够安全落到具体日期、且明确带有 XW multilib 的 WCH 分发元数据是：

```text
DISTRIBUTION_FILE_DATE="20230510-1207"
```

同一分发包的 multilib generator 明列：

- `rv32ecxw`
- `rv32imacxw`
- `rv32imafcxw`

证据：

- [`host-defs-source.sh`](ref/gcc/darwin-arm64/8.2.0/distro-info/scripts/host-defs-source.sh)，第 2 行；
- [`common-versions-source.sh`](ref/gcc/darwin-arm64/8.2.0/distro-info/scripts/common-versions-source.sh)，第 142 行附近。

准确口径是“当前本地语料最早带日期的 XW-capable 分发/构建元数据”。它不是 XW 的设计日期、WCH 首次公开日期或首颗支持芯片的生产日期。

### 7.3 2019 年 QingKe V3A 不能证明 XW 更早

WCH 称 2019 年的 CH32V103 使用 QingKe V3A，但当前处理器能力矩阵中 V3A 是不支持 XW 的例外。因此不能用 CH32V103/V3A 的 2019 年时间点证明 XW 早于 Huawei 2020 年公开材料。

当前手册显示：

- V2A/V2C 支持 XW；
- V3A 不支持，V3B/V3C/V3F/V3V 支持；
- V4A 不支持，V4B/V4C/V4F/V4J 支持；
- V5F 支持。

这些是当前手册快照的能力表，不是完整产品首发时间线。

### 7.4 版本标签不能当时间证据

WCH 工具链接受 `xw1p0/xw2p0/xw2p2/xw3p0` 等标签，但对 8,704 个合法组合产生相同编码。标签可以被 assembler 透传到 ELF attributes，不能单独证明对应版本存在不同指令语义或不同设计年代。

## 8. 事实、分析和未知项分级

### 8.1 直接事实

1. WCH 当前手册把 XW 定义为八个 16 位 byte/halfword 压缩访存形式。
2. WCH 官方工具链中，非 SP 四条的逐位编码已经由多版本工具链和交付库实测闭合。
3. Huawei/HCC 2020 公开材料中的非 SP 四条与 WCH 在名称、语义、操作数、立即数和逐位编码上全部相同。
4. Huawei 材料称其方案在公开前已经由 HCC GCC 支持并在 HiMiDeer SV100/V200 silicon 实现。
5. Huawei 2020 编码提案没有 WCH 的四条 SP 形式。
6. 标准 Zcb 的同名指令使用不同编码和更小 offset，且批准更晚。
7. WCH 官方承认早期安全类产品阶段外购过第三方 RISC-V 内核。
8. 没有公开材料识别该供应商，也没有材料把早期外购核直接连接到 QingKe/XW。
9. WCH 官方称 QingKe 是自研处理器。

### 8.2 高置信分析

1. **WCH XW 非 SP 四条与 Huawei/HCC 属于同一具体 ISA 设计谱系。**

   依据不是一般功能相似，而是在多项可自由设计的维度上逐位完全一致。

2. **“八条全部由 WCH clean-sheet 独立设计”不符合现有证据的最简解释。**

   理论上不能排除双方独立作出完全相同选择，但概率明显低于设计传播或共同来源。

3. **WCH 至少进行了自身的集成和产品化实现。**

   XW 被纳入 QingKe 能力矩阵、WCH `-march`/multilib、GAS 自动压缩、ELF attributes 和官方软件库。这些都是 WCH 工具链与产品集成事实。

4. **四条 SP 形式可能是 WCH 的扩展。**

   当前没有找到与其逐位相同的更早公开编码，但“未找到”不足以证明原创。

### 8.3 合理但未证实的假设

- WCH 直接参考 Huawei/HCC 2020 公开提案实现非 SP 四条；
- WCH 与 Huawei/HCC 使用了一个更早的共同 RISC-V code-size 草案；
- 人员流动或非公开技术交流传播了该设计；
- WCH 的早期第三方核供应商与 XW 设计来源有关；
- SP 四条由 WCH 从非 SP 路线自行扩展。

这些解释目前都缺少直接传播记录、提交历史、许可证或人员证据，不能选定其中之一作为事实。

### 8.4 当前不受证据支持的断言

- “QingKe 是 Huawei/Andes/Nuclei/T-Head/SiFive 核的改名版本”；
- “WCH 购买了 Huawei HiMiDeer IP”；
- “WCH 复制了 Huawei RTL 或 GCC 源码”；
- “XW 来自标准 Zcb”；
- “XW 八条全部由 WCH 独立原创”；
- “2023-05-10 是 XW 的发明或首发日期”。

## 9. 对‘借鉴还是自研’的最终回答

### ISA 设计层

非 SP 四条高度疑似复用或借鉴了 Huawei/HCC 同源设计，不能合理地称为完全独立原创。SP 四条的设计来源仍未知，可能包含 WCH 自行扩展。

### 工具链层

WCH 确实完成了自己的发行集成：XW march 状态、宏、multilib、GAS opcode/alias、自动压缩、attribute 和打包行为均出现在官方工具链中。是否直接复用了某份第三方工具链源码，当前没有源码谱系证据。

### CPU 实现层

没有证据证明 QingKe 的 XW 译码器、执行单元或 RTL 来自第三方 IP。采用相同 ISA 编码与自行设计微架构并不矛盾。因此，可以同时成立：

> XW 的部分 ISA 设计不是 WCH clean-sheet 原创；QingKe 对该 ISA 的硬件实现仍可能是 WCH 自研。

## 10. 若要进一步定案，需要什么证据

以下任一类材料都能显著提高结论强度：

- 2020 年以前带日期的 WCH XW 手册、芯片勘误、SDK、工具链或硅片资料；
- WCH 或 Huawei 的原始 patch/commit 历史及作者信息；
- 双方或第三方关于 ISA 授权、合作、移植的公告或合同线索；
- WCH 早期外购内核的供应商与产品映射；
- 四条 SP 形式更早的带编码规范；
- QingKe RTL、网表或可信的微架构审计。

在这些证据出现之前，本文采用的推荐措辞是：

> WCH XW 的 `c.lbu/c.lhu/c.sb/c.sh` 与 2020 年公开、并称已在 Huawei HCC/HiMiDeer silicon 中实现的压缩访存设计逐位相同；这高度支持二者共享或复用了同一 ISA 设计谱系，但不能证明具体传播渠道，也不能推出 WCH 使用了 Huawei 或其他厂商的 CPU IP。XW 的四条 SP 形式和 QingKe 的硬件实现来源仍未确定。
