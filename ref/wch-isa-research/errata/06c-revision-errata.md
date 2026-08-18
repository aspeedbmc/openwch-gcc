# 06c Revision / Errata

日期：2026-08-04

状态：规范入口。06c 专门记录同一芯片型号内的 silicon revision 行为差异、封装打印批号条件和 errata 证据；芯片 ID 来源及型号/封装选择见 [06b ChipID](06b-chipid.md)。

## 1. 判定规则

| 类别 | 判定条件 | 是否属于 06c errata 审计 |
|---|---|---|
| `MODEL-SELECT` | 读取 DEVID 或其他固定型号/封装位，命中不同芯片型号 | 否，归 06b |
| `REVISION-SELECT` | 固定同一型号后，REVID 中的 revision 值仍选择不同行为 | 是 |
| `REVISION-WORKAROUND-CANDIDATE` | revision 分支执行恢复、重置、重初始化或替代路径，但缺少官方缺陷因果说明 | 是，候选而非已确认 erratum |
| `REVISION-COMPATIBILITY` | revision 分支反映时序、参数或能力演进，没有闭合到缺陷 | 是，但不称为 erratum |
| `DOCUMENTED-LOT-ERRATUM` | 官方材料同时给出失效现象、受影响打印批号范围和处理入口 | 是，批号与运行时 REVID 仍分开记录 |

在已审 V203/V317/H417 等系列中，SDK 将 full CHIPID `[15:0]` 称为 `REVID`；真正参与已闭合运行时分支的是 full CHIPID `[7:4]`。打印在封装上的“批号第 N 位”没有被本地或已查官方材料映射到 `DBGMCU_GetREVID()`，因此不得把 lot 条件自动等同于 runtime revision。

## 2. 专项结论

1. 共闭合 12 个同芯片运行时 revision 语义组：9 个 `REVISION-WORKAROUND-CANDIDATE`，3 个 `REVISION-COMPATIBILITY`。
2. V317/V30x/V31x 覆盖 CAN、TIM 和四种以太网语义模式；H415/H416/H417 覆盖 CAN、GPIO、ADC、eMMC、Stop mode 和 USBSS/UHSIF。
3. 候选路径包含 CAN/RCC 复位、MAC 重建、DMA 恢复、SWPMI 旁路和 ADC 校准等明显的恢复形状，但已查手册没有给出“缺陷现象 → 受影响 revision → 规避动作”的完整映射。因此 12 个运行时发现中没有 `ERRATA-CONFIRMED`。
4. 文档复核形成 14 个条件发现。最强的一项是 H417 早期批次 I3C 无数据 IBI：`IBIF` 不生效，手册限定受影响打印批号并指向 EVT 处理，分类为 `DOCUMENTED-LOT-ERRATUM`。
5. WCHNET 的 `lhu 0x1FFFF706; andi 0xF0` 读取 full CHIPID `[23:20]`，比较 `0x30/0x80` 实际区分型号家族。它修正为 `MODEL-SELECT`，不能再作为 revision errata 证据。

## 3. 运行时 revision 总表

| 范围 | finding | revision 条件 | 行为类型 | 分类 |
|---|---|---|---|---|
| V317/V30x/V31x | `REV-WCH-001..003` | `[7:4] = 4..7`、`4..8`、`0..2` | CAN/TIM 额外初始化；以太网状态与 MAC/DMA 恢复 | workaround candidate |
| V317/V30x/V31x | `REV-WCH-004` | `[7:4] >= 6` | RGMII TXC delay 参数变化 | compatibility |
| V317/V30x/V31x | `REV-WCH-005..006` | `[7:4] = 2`、`1` | 10M PHY 极性/MAC 恢复；RBU descriptor/DMA 恢复 | workaround candidate |
| H415/H416/H417 | `REV-WCH-007..010` | `[7:4] = 0` | CAN、GPIO、ADC、eMMC 的额外复位/旁路/校准路径 | workaround candidate |
| H415/H416/H417 | `REV-WCH-011..012` | `0/1/2`、`<3 / >=3` | Stop mode 稳压配置；USBSS/UHSIF 功能处理演进 | compatibility |

逐项器件范围、源码锚点、证据强度和 errata 状态以 [revision-findings.tsv](06c-chip-revision-evidence/revision-findings.tsv) 为准。

## 4. 文档、实验与结论强度

- 126 份本地 PDF、98 个内容哈希组完成文本检查；关键条件页中有 5 页同时完成渲染与视觉复核。
- 14 个文档条件分别记录为 revision requirement、ChipID requirement、lot erratum、lot limitation、lot requirement 或 lot-gated capability，不把所有批号差异统称为 errata。
- V317 MAC_RAW、V317 CAN 和 H417 CAN 三个代表工程已用 WCH GCC 构建并链接，证明相关路径可进入发射对象或最终 ELF；这不替代真芯片故障复现。
- 源码中的恢复形状只支持“高价值 workaround 候选”。没有官方因果说明或硬件实验时，不提升为已确认 silicon erratum。

## 5. 交付与可追溯性

本文件是后续引用 06c 时使用的规范入口。完整论证和冻结证据继续保留在原提交路径，以维持证据清单与验收脚本的哈希闭合：

- [完整 revision / errata 专项报告](06c-chip-revision-errata.md)
- [证据说明](06c-chip-revision-evidence/README.md)
- [CHIPID 字段表](06c-chip-revision-evidence/chipid-layout.tsv)
- [selector 分类表](06c-chip-revision-evidence/selector-classification.tsv)
- [12 个运行时 revision 发现](06c-chip-revision-evidence/revision-findings.tsv)
- [14 个文档条件发现](06c-chip-revision-evidence/document-review.tsv)
- [证据清单](06c-chip-revision-evidence/evidence-manifest.tsv)

历史路径 `06c-chip-revision-errata.md` 是冻结的详细报告；规范名称和职责是本文件所定义的 `06c revision-errata`。
