# 06c CH32 芯片 revision / errata 专项复核

日期：2026-08-04

状态：完成复核；本文件是独立 revision 文档，并对 06b 的一项字段解释作正式修正

范围：本地 WCH EVT 源码/头文件、已提取库对象、代表性构建、126 份 PDF（98 个内容哈希组），以及受限的官方仓库复核

## 1. 结论

这次复核必须先回答“选择的是芯片型号，还是同一芯片的 silicon revision”。结论如下：

1. WCH SDK 把 `0x1FFFF704` 的 32 位字作为 CHIPID；低 16 位由 `DBGMCU_GetREVID()` 返回，高 16 位由 `DBGMCU_GetDEVID()` 返回。
2. V203/V317/H417 等 SDK 公布的 CHIPID 模式中，低半字的 `x/X` 位位于 full CHIPID[7:4]。V317、H417 源码真正用来区分同型号 revision 的也是这一 nibble。
3. WCHNET 库中的 `lhu 0x1FFFF706; andi 0xF0` 在小端 RISC-V 上读取高半字 DEVID，并选择 full CHIPID[23:20]。`0x30/0x80` 对应 V203/V303 与 V208 等不同型号家族，不是同一型号的 revision。
4. 因此，06b 将该 WCHNET 路径列作 ID/revision workaround candidate 的解释不成立。它应改为 `MODEL-SELECT`；二进制中的防御性 descriptor 路径确实存在，但不能作为同芯片 revision errata 证据。
5. 真正闭合的运行时 revision 选择集中在 V317 和 H417：共 12 个语义组。恢复、重置、重初始化类路径标为 `REVISION-WORKAROUND-CANDIDATE`；时序、能力或配置演进标为 `REVISION-COMPATIBILITY`。由于已查手册没有给出这些源码分支的缺陷原因，均不得提升为 `ERRATA-CONFIRMED`。
6. 官方手册中有明确的 CHIPID 条件和打印批号条件。V205 手册的“CHIPID 倒数第二位为 1”可结合该系列 CHIPID 表闭合到 full CHIPID[7:4]；H417 的早期批次 I3C 无数据 IBI `IBIF` 不生效并指向 EVT 处理，可列为 `DOCUMENTED-LOT-ERRATUM`。
7. 本地材料和本次检查的官方仓库都没有把封装上的打印批号位映射到 `DBGMCU_GetREVID()`。二者可能相关，但在证据闭合前，打印批号不得等同于运行时 REVID。

机器可读结论见 [chipid-layout.tsv](06c-chip-revision-evidence/chipid-layout.tsv)、[revision-findings.tsv](06c-chip-revision-evidence/revision-findings.tsv) 和 [selector-classification.tsv](06c-chip-revision-evidence/selector-classification.tsv)。

## 2. ID 字段模型

### 2.1 SDK 已闭合的字段

V203、V317、H417 等 SDK 的 `dbgmcu.c` 给出相同拆分：

```text
CHIPID = *(uint32_t *)0x1FFFF704
REVID  = CHIPID & 0x0000FFFF        // full CHIPID[15:0]
DEVID  = CHIPID >> 16               // full CHIPID[31:16]
```

SDK 注释明确把低半字称为 device revision identifier，把高半字称为 device identifier。宏名 `IDCODE_DEVID_MASK` 虽然容易误导，但其实际运算和函数注释一致。原始摘录见 [field-v203-dbgmcu.txt](06c-chip-revision-evidence/source-excerpts/field-v203-dbgmcu.txt)、[field-v317-dbgmcu.txt](06c-chip-revision-evidence/source-excerpts/field-v317-dbgmcu.txt) 和 [field-h417-dbgmcu.txt](06c-chip-revision-evidence/source-excerpts/field-h417-dbgmcu.txt)。

不能把整个低 16 位简单描述成一个单调递增的“rev 数字”。以 SDK 公布的模式为例：

```text
CH32V203...  0x203...5x0
CH32V303...  0x303...5x4
CH32V317...  0x317...5X8
CH32H417...  0x417...5xD
```

这里唯一的 wildcard `x/X` 位于 full CHIPID[7:4]。源码中的同芯片 revision 分支也正是 `CHIPID >> 4 & 0xF` 或 `CHIPID & 0xF0`。因此本报告使用以下严格术语：

- `REVID`：SDK 定义的 full CHIPID[15:0]；
- `revision nibble`：这些已审系列实际参与运行时分支的 full CHIPID[7:4]；
- `DEVID`：full CHIPID[31:16]；
- `model/package selector`：读取 DEVID、其他固定型号位，或先屏蔽 `[7:4]` 再选择；
- `lot selector`：手册依据封装印字的“批号第 N 位/倒数第 N 位”限定，未自动视为 REVID。

### 2.2 判断规则

只有满足以下条件，才列为同芯片 `REVISION-SELECT`：

1. 数据源闭合到 `REVID`，本批证据具体为 full CHIPID[7:4]；
2. 固定同一型号/封装的其余 CHIPID 位后，两个 revision 值仍可走不同路径；
3. 分支影响外设配置、恢复、时序或功能，而不只是打印 ID；
4. 分类保留因果强度：有恢复形状不等于有官方 erratum 原因。

读取 DEVID、屏蔽 revision 后 switch、编译期库变体、CPU `mimpid`、身份序列号或打印批号，均不能冒充这类证据。

## 3. 06b 结论修正

### 3.1 被修正的内容

[06b 报告](06b-chipid-errata-codex.md) 对 soft WCHNET 的二进制路径确认了以下事实：

- 从 `0x1FFFF706` 无符号读取半字；
- 与 `0x00F0`；
- 比较 `0x30`、`0x80`；
- 在 descriptor 长时间不可用或计数超过阈值时清 owner bit。

这些二进制事实不变。需要修正的是字段语义和上层分类：

| 项目 | 06b 旧解释 | 06c 修正 |
|---|---|---|
| 读取字段 | `0x1FFFF706` 半字语义未知 | 小端下等于 `DBGMCU_GetDEVID()`，即 full CHIPID[31:16] |
| mask 字段 | 未闭合的 ID field | full CHIPID[23:20]，DEVID 的型号家族 nibble |
| `0x30/0x80` | ID-select / workaround candidate | V203/V303 与 V208 等型号值；`MODEL-SELECT` |
| 对 errata 的意义 | 可作为同芯片 revision 候选 | 不能证明同一型号不同 revision 的 silicon errata |

反汇编见 [两个 GetChipID 对象](06c-chip-revision-evidence/wchnet-binary/)；字段闭合来自 SDK `DBGMCU_GetREVID/DEVID` 源码，而不是根据地址命名猜测。

### 3.2 五个物理 WCHNET 包的型号域

[wchnet-model-domain.tsv](06c-chip-revision-evidence/wchnet-model-domain.tsv) 将每个物理包与该包 SDK 公布的型号列表对齐：

| EVT 包 | 公布型号家族 | full CHIPID[23:20] | `0x30` | `0x80` |
|---|---|---:|---|---|
| V203 | V203、V208 | `0x30`,`0x80` | V203 | V208 |
| V20x | V203、V208 | `0x30`,`0x80` | V203 | V208 |
| V317 | V303、V305、V307、V317 | `0x30`,`0x50`,`0x70` | V303 | 不可达 |
| V407 | V407、V467 | `0x70` | 不可达 | 不可达 |
| H417 | H415、H416、H417 | `0x50`,`0x60`,`0x70` | 不可达 | 不可达 |

这解释了为什么同一个对象可出现在多个 EVT 包中：在 V203/V20x 包里两个特殊值都是目标型号；在 V317 包里只有 V303 命中；在 V407/H417 的公布目标域里两者都不命中。它更符合共享代码的跨型号兼容/恢复路径，而不是 revision errata。

本修正仅替代 06b 对 WCHNET 字段和分类的解释，不撤销 06b 的对象哈希、8 个 archive-member occurrence、分支顺序、阈值和 sink 证据，也不改动 06b 的其他审计结论。

## 4. 真正的运行时 revision 差异

### 4.1 V317 / V30x / V31x

| ID | revision nibble | 行为差异 | 分类 |
|---|---:|---|---|
| REV-WCH-001 | 4..7 | `CAN_Init` 在常规流程前执行额外 RCC/CAN 复位、进入/退出 init、过滤器/状态清理及总线状态序列 | `REVISION-WORKAROUND-CANDIDATE` |
| REV-WCH-002 | 4..8 | TIM1/8/9/10 初始化额外置 `CTLR1 bit13` | `REVISION-WORKAROUND-CANDIDATE` |
| REV-WCH-003 | 0..2 | RMII/MII/RGMII 重试零 PHY 状态、抑制重复状态；漏帧计数异常时重建 MAC 并恢复 DMA | `REVISION-WORKAROUND-CANDIDATE` |
| REV-WCH-004 | >=6 | RGMII 千兆链路 TXC delay 从 `(0,4)` 改为 `(1,2)` | `REVISION-COMPATIBILITY` |
| REV-WCH-005 | 2 | 内置 10M PHY 漏帧时重建 MAC，并在协商失败窗口切换 P/N 极性 | `REVISION-WORKAROUND-CANDIDATE` |
| REV-WCH-006 | 1 | 10M RBU 中断归还下一 Rx descriptor 的 OWN 并恢复 Rx DMA | `REVISION-WORKAROUND-CANDIDATE` |

CAN 和 TIM 源码摘录分别见 [v317-can-revision.txt](06c-chip-revision-evidence/source-excerpts/v317-can-revision.txt) 与 [v317-tim-revision.txt](06c-chip-revision-evidence/source-excerpts/v317-tim-revision.txt)。对应函数已由 WCH GCC 发射到对象，反汇编见 [disassembly/](06c-chip-revision-evidence/disassembly/)。

以太网共有 20 个物理源码副本：4 种接口模式乘以 NetLib、MAC_RAW 和 3 个 USB 网络适配器位置。报告按 RMII、MII、RGMII、10M 四个语义模式归组，避免把复制文件误算成 20 个独立 errata。代表性摘录见 [v317-eth-rmii-revision.txt](06c-chip-revision-evidence/source-excerpts/v317-eth-rmii-revision.txt)、[v317-eth-rgmii-revision.txt](06c-chip-revision-evidence/source-excerpts/v317-eth-rgmii-revision.txt) 和 [v317-eth-10m-revision.txt](06c-chip-revision-evidence/source-excerpts/v317-eth-10m-revision.txt)。

本次另行完整构建了 `QingkeV4F_CH32V317_EVT/EXAM/ETH/MAC_RAW`。WCH GCC 构建、链接和 ISA 检查均通过，10M 驱动的 `ETH_PHYLink`、`WCHNET_RecProcess`、`WCHNET_ETHIsr`、`ETH_Init` 与 `ChipId` 均进入最终 ELF。该构建证明路径不是仅存在于未编译文本中，但不能替代真芯片实验。

### 4.2 H417 / H416 / H415

| ID | revision nibble | 行为差异 | 分类 |
|---|---:|---|---|
| REV-WCH-007 | 0 | `CAN_Init` 执行额外三路 CAN/RCC 复位和状态/过滤器清理序列 | `REVISION-WORKAROUND-CANDIDATE` |
| REV-WCH-008 | 0 | `GPIO_IPD_Unused` 临时开启 SWPMI 并置 `OR bit0` | `REVISION-WORKAROUND-CANDIDATE` |
| REV-WCH-009 | 0 | 6 个 dual-ADC 例程在校准后执行 `ADC_HD_CalibrationCmd(ADC1, DISABLE)` | `REVISION-WORKAROUND-CANDIDATE` |
| REV-WCH-010 | 0 | 3 个 eMMC 例程在 GPIO 初始化前开启 SWPMI 并置 `OR bit0` | `REVISION-WORKAROUND-CANDIDATE` |
| REV-WCH-011 | 0/1/2 | Stop mode 选择不同低功耗稳压配置 | `REVISION-COMPATIBILITY` |
| REV-WCH-012 | <3 / >=3 | 新 revision 使能/处理中断 `RX_SET_FC`；旧 revision 软件处理 `SET_LINK_FUNC` 并更新 U1/U2 | `REVISION-COMPATIBILITY` |

H417 GPIO 是区分两类选择最清楚的反例：

```text
if ((CHIPID & 0xF0) == 0) { ... SWPMI ... }  // revision gate
chip = CHIPID & ~0xF0;
switch (chip) { ... }                         // revision-insensitive model/package gate
```

同一函数先做 full CHIPID[7:4] revision gate，再明确屏蔽该 nibble 做型号/封装 switch。把两者都叫“ChipID 分支”会丢掉 errata 审计最关键的语义。摘录见 [h417-gpio-revision-and-model.txt](06c-chip-revision-evidence/source-excerpts/h417-gpio-revision-and-model.txt)。

H417 CAN 代表工程已用 WCH GCC 成功构建并链接；最终 ELF 中存在 `CAN_Init` 和 `GPIO_IPD_Unused`。ADC、eMMC、PWR、USBSS/UHSIF 仍以源码证据为主，未据此声称硬件因果已经验证。

### 4.3 不能越级成“已确认 errata”的原因

这些分支中的 CAN 重置、MAC 重建、DMA 恢复、SWPMI bypass 和 ADC 校准形状都很像 silicon workaround，因此保留高价值候选。但本地手册没有把它们闭合成“缺陷现象 → 受影响 revision → 规避动作”，官方仓库复核也没有找到对应映射。

所以分类边界是：

- 恢复/重置/重初始化/alternate path：`REVISION-WORKAROUND-CANDIDATE`；
- 时序、参数、能力演进：`REVISION-COMPATIBILITY`；
- 只有官方材料同时给出失效、受影响范围和处理方式，才可称 `ERRATA-CONFIRMED` 或本报告中的 `DOCUMENTED-LOT-ERRATUM`。

## 5. 官方文档中的 revision 与 lot 条件

### 5.1 文档覆盖

冻结的 PDF 清单为 126 个物理文件、98 个内容哈希组，Poppler 文本提取失败数为 0。全文关键词筛查后，对关键页同时做了页面渲染和视觉复核，而不是仅凭抽取文本接受版面语义。五个提交的视觉页是：

- V205 RM V1.2 PDF p261（印刷页 256）；
- L103 RM V2.2 PDF p262（印刷页 257）；
- H417 RM V1.7 PDF p1；
- H417 RM V1.7 PDF p375（印刷页 371）；
- CH32F/V20x/V30x/V31x RM V2.5 PDF p148（印刷页 145）。

全部文档行、页码、哈希、条件和分类见 [document-review.tsv](06c-chip-revision-evidence/document-review.tsv)，视觉验收见 [visual-review.tsv](06c-chip-revision-evidence/visual-review.tsv)。

### 5.2 明确使用 CHIPID 的条件

V205 和 L103 手册都写明：CHIPID 倒数第二位为 1 的芯片作为 Type-C Source 使用时，CC 端口配置为上拉输入。

对 V205，SDK CHIPID 表列出 `0x205205x0`、`0x205105x0`、`0x205005x0` 等模式，倒数第二个十六进制位正是 full CHIPID[7:4]，因此 `DOC-REV-001` 可列为 `DOCUMENTED-REVISION-REQUIREMENT`。这是“手册文字＋SDK ID 模式”的跨证据闭合，报告明确标为推断；原始表见 [field-v205-dbgmcu.txt](06c-chip-revision-evidence/source-excerpts/field-v205-dbgmcu.txt)。

对 L103，本地材料没有进一步闭合该位与 `DBGMCU_GetREVID()` API 的关系，因此只列 `DOCUMENTED-CHIPID-REQUIREMENT`，不强行复用 V205 的字段定义。

### 5.3 文档化 lot erratum 与限制

H417 RM p375 的 I3C 条目是本次最强的官方 errata 证据：批号倒数第五位小于 3 的芯片，在主机接收从机发出的无数据 IBI 时，`IBIF` 不生效，手册明确要求参考官网 EVT 例程处理。它满足“失效现象＋受影响 lot＋处理入口”，列为 `DOCUMENTED-LOT-ERRATUM`。

其他重要 lot 条件包括：

- H417 早期 lot：I2S `FSPOL=0` 需要外部上拉；QSPI 内存映射只能数据访问、不能取指；GPHA 特定 mode 的 `PL` 不能为 0；
- CH32F/V20x/V30x/V31x 早期 lot：DMA1 不能跨 64K 边界，部分批次/通道改为 128K，其他通道仍是 64K；
- V407 lot0：进入 standby 前未用于唤醒的 GPIO 要设为模拟输入；后续 lot 增加 RVV/DMA 64 位访问等能力；
- V003 和 x103 早期 lot：SPI 高速读仅在时钟 2 分频有效；
- X315、H417 评估指南：部分时钟或下载能力按打印批号开放。

手册有时写“批号第五位”，有时写“批号倒数第五位/第六位”。证据表保留原文位置，不擅自归一化。更重要的是，这些都是 `LOT-GATED` 条件；在没有官方映射时，不得把它们改写成 `if (DBGMCU_GetREVID() == N)`。

### 5.4 官方仓库复核边界

本次还检查了官方 [openwch/ch32v20x](https://github.com/openwch/ch32v20x) 与 [openwch/ch32v307](https://github.com/openwch/ch32v307) 分发入口。它们能佐证 SDK/手册的官方来源，但在检查范围内没有找到“封装打印 lot 位 → 运行时 REVID”的映射，也没有找到覆盖上述源码候选的独立 errata sheet。

这是受限负结论，只覆盖记录的本地语料、查询形式和上述官方入口，不表示厂商内部或未公开版本绝对不存在映射。

## 6. 型号/封装选择与其他反例

以下命中都不能列入 same-chip revision errata：

- V407 ETH：`(DBGMCU_GetCHIPID() >> 16) & 0xF` 读取 full CHIPID[19:16]，值 2/5 选择 LED/PHY 引脚，是 DEVID 内的型号/封装 subcode；
- V407 GPIO：先 `CHIPID & ~0xF0`，再按完整型号/封装 switch；
- V006 SLTIM：反复用 `CHIPID & ~0xF0 == 0x00700800`，有意让所有 revision 走同一型号路径；
- X315 GPIO：`VCfg_Init() & ~0xF0` 后做型号 switch；
- `DBGMCU_GetCHIPID()` 的调试打印、函数声明和返回值本身不构成行为选择；
- `DBGMCU_GetREVID()`/`DBGMCU_GetDEVID()` 在整个 EVT C/H 语料中没有声明/定义之外的直接调用者；实际分支多直接读取完整 CHIPID；
- core revision CSR、编译期 float/soft 库变体、身份认证字节和封装 lot 都是不同维度。

全 EVT 搜索覆盖 23,988 个 `.c/.h` 文件；`DBGMCU_GetCHIPID` 文本出现 998 次、涉及 980 个文件。文本命中不等于行为命中，最终仅保留 [callsite-summary.json](06c-chip-revision-evidence/callsite-summary.json) 和分类表中完成 source→predicate→behavior 闭合的组。

## 7. 对移植和重写的要求

### 7.1 API 与命名

移植层至少要显式区分：

```c
chipid = read32(0x1FFFF704);
revid  = chipid & 0xFFFF;
devid  = chipid >> 16;
rev_nibble = (chipid >> 4) & 0xF;
```

不要用一个模糊的 `chip_id` helper 同时承载型号和 revision 判断。代码注释应写 full CHIPID bit range，避免地址偏移再次造成误判。

### 7.2 保持谓词边界

等价移植必须保留：

- V317 CAN 的闭区间 4..7、TIM 的 4..8；
- ETH 的 `<=2`、`==2`、`==1`、`>=6`，不能合并成一个“旧芯片”布尔值；
- H417 的 `==0`、0/1/2 switch、`<3`/`>=3`；
- 型号 selector 中对 `[7:4]` 的显式屏蔽；
- WCHNET 的 DEVID `0x30/0x80` 谓词，不能改名为 revision predicate。

未知 revision 在原源码中通常走 default/普通路径。新增 fail-closed、超时、reset 或安全回退属于工程策略变更，不是观测等价重写，应单独评审。

### 7.3 lot 条件

打印 lot 条件在运行时不可自动套用，除非后续取得厂商映射并验证。可选做法是：

- 板级/产品配置显式声明受影响 lot；
- 生产测试读取并保存封装批号；
- 对无法识别的批次采用文档允许的保守配置；
- 将“lot workaround”和“REVID workaround”保留为不同配置源和测试矩阵。

## 8. 验证、限制与复现

已完成的验证：

- 126/98 PDF 语料闭合、0 个文本提取失败；
- 5 个关键 PDF 页经 Poppler 渲染并人工视觉复核；
- V317 CAN/TIM 与 H417 CAN/GPIO 函数存在 WCH 编译对象反汇编；
- H417 CAN 代表工程中的 `CAN_Init`、`GPIO_IPD_Unused` 已链接；
- 新增 V317 ETH MAC_RAW 全量构建通过，10M revision 路径进入最终 ELF；
- 两个 WCHNET object hash 的 `GetChipID` 均确认 `lhu 0x1FFFF706` 与 `andi 0xF0`；
- 证据包 manifest 对所有文件做大小和 SHA-256 闭合，验收脚本独立重哈希输入。

限制：没有实体芯片矩阵，不能证明候选分支的真实缺陷现象、受影响 die revision 或 workaround 有效性；没有打印 lot 到 REVID 的官方映射；未检查未公开文档；文本全文搜索不能替代所有扫描页 OCR。由此，本报告可以指导 ID 分类和移植保真，但不能替代厂商 errata sheet 或硬件 qualification。

从仓库根目录复现：

```sh
python3 audit-report-f/followup/results/06c-chip-revision-evidence/scripts/generate_evidence.py
python3 audit-report-f/followup/results/06c-chip-revision-evidence/scripts/acceptance.py
git diff --check -- audit-report-f/followup/results/06c-chip-revision-errata.md audit-report-f/followup/results/06c-chip-revision-evidence
```

完整文件闭合见 [evidence-manifest.tsv](06c-chip-revision-evidence/evidence-manifest.tsv)，构建记录见 [build-evidence.tsv](06c-chip-revision-evidence/build-evidence.tsv)，输入哈希见 [source-hashes.tsv](06c-chip-revision-evidence/source-hashes.tsv)。
