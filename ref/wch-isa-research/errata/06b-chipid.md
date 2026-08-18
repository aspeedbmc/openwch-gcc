# 06b ChipID

日期：2026-08-04

状态：规范入口。06b 只负责芯片 ID 的来源、字段、型号/封装选择和身份流；同一芯片的 silicon revision、批号条件及 errata 统一交给 [06c Revision / Errata](06c-revision-errata.md)。

## 1. 边界

06b 回答两个问题：代码或二进制从哪里取得 ID，以及该 ID 实际区分什么。它覆盖 CHIPID/DEVID/REVID 字段识别、型号或封装选择、身份认证数据流、编译期变体，以及对象库中的 ID 读取与消费路径。

仅仅读取 CHIPID、命中不同型号，或出现防御性代码，都不能据此称为 revision errata。只有在固定同一芯片型号后，revision 值仍选择不同行为，才进入 06c。

## 2. 字段模型

| 数据源或字段 | 已闭合语义 | 归属 |
|---|---|---|
| `*(uint32_t *)0x1FFFF704` | 完整 32 位 `CHIPID` | 06b 识别字段 |
| full CHIPID `[15:0]` | SDK `DBGMCU_GetREVID()` 返回的 `REVID` 半字 | 06b 识别字段；行为差异交 06c |
| full CHIPID `[7:4]` | 已审 V203/V317/H417 等系列 CHIPID 模式中的 revision nibble | 同型号行为选择交 06c |
| full CHIPID `[31:16]` | SDK `DBGMCU_GetDEVID()` 返回的 `DEVID` 半字 | 06b 型号/器件识别 |
| `lhu 0x1FFFF706; andi 0xF0` | 小端下读取 full CHIPID `[23:20]`，即 DEVID 内的型号家族位 | 06b `MODEL-SELECT` |
| `0x1FFFF7E0` 的 16 字节 | IoCHub 注册/认证所用的工厂身份数据流 | 06b `ID-FLOW`，不是 errata selector |
| `mvendorid`/`marchid`/`mimpid`/`mhartid` 等 CSR | 核心/实现身份；除非闭合到同芯片行为分支，否则不等于芯片 revision | 06b 候选发现 |

这里的 `REVID` 是 SDK 对低 16 位的命名，不能默认把整个半字当作单调递增的 revision 数字。当前闭合到运行时 revision 选择的是 full CHIPID `[7:4]`，且仍需证明固定型号后行为发生变化。

## 3. 06b 结论

1. 五个 soft-WCHNET 物理包中的八个 `eth_api.o` occurrence 确实包含 `0x1FFFF706` 读取、`0x30/0x80` 比较和 Tx descriptor 恢复路径；但该字段是 full CHIPID `[23:20]`，选择 V203/V303、V208 等型号家族。因此最终分类是 `ID-READ + MODEL-SELECT`，不是同芯片 revision errata。
2. V317 float WCHNET 对象没有运行时 `GetChipID` 路径，属于 `STATIC-VARIANT-SPECIALIZATION`。
3. 三个 IoCHub 对象读取工厂信息并进入注册/认证材料派生，属于 `ID-READ/ID-FLOW`，没有闭合到 workaround 选择。
4. 其余对象、归档、ROM、CSR、字面量和文档扫描的否定结论都受各自扫描域约束，不能外推为“仓库中不存在其他 ID 逻辑”。

06b 冻结报告曾把 WCHNET 路径描述为 model/revision selector candidate。其二进制事实、对象哈希、occurrence 数量、分支顺序、阈值和 sink 证据继续有效；字段语义和 revision 分类由 06c 正式修正为 `MODEL-SELECT`。

## 4. 交付与可追溯性

本文件是后续引用 06b 时使用的规范入口。为保证清单哈希、内部链接和验收脚本仍可复现，已经提交的证据文件保留历史文件名，不做搬移：

- [冻结的 06b 详细审计报告](06b-chipid-errata-codex.md)
- [物理输入清单](06b-chipid-errata-inventory.tsv)
- 对象扫描结果（约 7.9 GiB）未复制到本参考目录，保留在源仓库 `audit-report-f/followup/results/06b-chipid-errata-object-scan.tsv`
- [发现表](06b-chipid-errata-findings.tsv)
- [证据清单](06b-chipid-errata-evidence/evidence-manifest.tsv)
- [结论修正与 revision 专项](06c-revision-errata.md)

历史路径中的 `chipid-errata` 仅表示冻结运行的原始名称，不再表示 06b 的规范范围。
