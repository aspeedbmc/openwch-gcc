# WCH ISA / Errata Research

本目录整理自 `/Users/apple/Projects/gccriscv-wch` 当前工作树，收录 WCH QingKe 自定义 ISA、工具链行为、ISA 普查，以及 ChipID / silicon revision / errata 分析成果。文档中的源路径仍以原仓库为准；本目录只整理交付物，不复制完整 EVT 原始资料库。

## 先读

| 主题 | 入口 |
| --- | --- |
| QingKe V2–V5 架构、EVT 映射和编译器含义 | [isa/qingke_processor.md](isa/qingke_processor.md) |
| 自定义指令、XW、CSR、PFIC/HPE/VTF | [isa/custom/wch-custom-isa-reference.md](isa/custom/wch-custom-isa-reference.md)、[isa/custom/qingke-custom-isa.md](isa/custom/qingke-custom-isa.md) |
| ISA 第二轮独立复核 | [isa/custom/codex-findings.md](isa/custom/codex-findings.md)、[isa/custom/review-codex-r2.md](isa/custom/review-codex-r2.md) |
| ChipID / 型号与身份流 | [errata/06b-chipid.md](errata/06b-chipid.md) |
| 同型号 revision、批号条件和 errata | [errata/06c-revision-errata.md](errata/06c-revision-errata.md) |

## ISA 材料

- `isa/custom/`：Claude 成稿与素材、Codex 独立复核，以及两轮交叉评审。
- `isa/census/`：[普查说明](isa/census/isa-census-notes.md)、[完整统计表](isa/census/isa-census.tsv)、[unknown 表](isa/census/isa-census-unknown.tsv)和[复算脚本](isa/census/isa_census.py)。
- `isa/toolchain/`：[MRS 2.4/2.5 差异研究](isa/toolchain/mrs-version-diff.md)及[第二轮评审](isa/toolchain/mrs-version-diff-round2-review.md)。

`isa/custom/` 文件索引：

| 文件 | 侧重点 |
| --- | --- |
| [qingke-custom-isa.md](isa/custom/qingke-custom-isa.md) | QingKe 各代 XW、32 位自定义指令、CSR、中断架构和手册冲突 |
| [wch-custom-isa-reference.md](isa/custom/wch-custom-isa-reference.md) | 可验证的 WCH 指令参考、证据规则和未确认项 |
| [wch-doc-instr-reg-findings.md](isa/custom/wch-doc-instr-reg-findings.md) | 手册指令/寄存器逐项发现 |
| [wch-doc-provenance.md](isa/custom/wch-doc-provenance.md) | 手册与一手材料来源账本 |
| [wch-evt-pdf-instr-reg-index.md](isa/custom/wch-evt-pdf-instr-reg-index.md) | EVT PDF 指令/寄存器索引 |
| [wch-isa-usage-in-libraries.md](isa/custom/wch-isa-usage-in-libraries.md) | 闭源库中的 ISA 使用情况 |
| [wch-pioc-risc8b-findings.md](isa/custom/wch-pioc-risc8b-findings.md) | PIOC/RISC8B 格式与边界 |
| [codex-findings.md](isa/custom/codex-findings.md) | 第二轮独立复核新增发现与修正 |
| [codex-round2-review.md](isa/custom/codex-round2-review.md) | 第二轮审查矩阵 |
| [review-claude.md](isa/custom/review-claude.md)、[review-codex.md](isa/custom/review-codex.md) | 首轮交叉评审 |
| [review-codex-followup.md](isa/custom/review-codex-followup.md)、[review-codex-r2.md](isa/custom/review-codex-r2.md) | 后续裁定与 R2 复核 |

当前结论应特别注意：XW 标签不能单独证明硬件能力；`mcpy` 在 CH587 ROM 中有阳性现场，但 V407 手册与 SDK/ROM 对操作数角色存在冲突，属于文档勘误候选；“库中没有命中”不能外推到 ROM 或未覆盖的运行时语义。

## Errata 材料

- [06b 规范入口](errata/06b-chipid.md)区分 ID 来源、型号/封装选择、身份流和 revision 分支。
- [06b 详细审计](errata/06b-chipid-errata-codex.md)、[发现表](errata/06b-chipid-errata-findings.tsv)和[物理输入清单](errata/06b-chipid-errata-inventory.tsv)记录完整范围与证据边界。
- [06b compact evidence](errata/06b-chipid-errata-evidence/evidence-manifest.tsv)保留哈希绑定的控制、脚本、正负控制、ROM/XW 和文档证据。
- [06c 规范入口](errata/06c-revision-errata.md)与[详细报告](errata/06c-chip-revision-errata.md)记录 12 组同型号 revision 行为和 14 个文档条件；[06c evidence README](errata/06c-chip-revision-evidence/README.md)是复现入口。

结论口径：目前没有 `ERRATA-CONFIRMED` 的 silicon 因果链。12 个运行时 revision 发现中，9 个是缺少官方因果说明的 workaround candidate，3 个是 compatibility；H417 I3C 早期批次条件是已记录的文档型 lot erratum。WCHNET 的 `0x1FFFF706 & 0xf0` 路径最终归为 DEVID/model select，不是同型号 revision errata。

## 范围说明

本次未复制以下过程型或超大原始数据：

- `audit-report-f/followup/results/06b-chipid-errata-object-scan.tsv`（约 7.9 GiB 的逐 occurrence 扫描账本）；
- `tmp/chipid-errata-06b/`、`tmp/chipid-revision-06c/` 下的完整运行树；
- `tmp/wch-evt/` 中的原始 SDK、PDF、工具链和 archive 输入。

它们不是索引入口所需的精简交付物；需要逐 occurrence 或重新生成证据时，应回到上述源仓库路径。已复制的 06b/06c evidence bundle 保持原目录结构和 `evidence-manifest.tsv`，便于独立验收。

整理日期：2026-08-12。源仓库存在其他未提交修改，本目录复制的是当时工作树内容，未修改源仓库。
