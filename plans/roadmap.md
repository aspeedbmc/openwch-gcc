# 总体阶段路线图

阶段编号全局唯一，prompt 文件按 `tmp/prompts/phase-N{.md,.checklist.md}` 命名。执行 agent 逐项打勾（附证据指针），完成前必做需求回归 + 设计回归（对照本 plans 目录的对应骨干）。

| 阶段 | 内容 | 参照骨干 | prompt 状态 |
|---|---|---|---|
| phase-1 | 共享差异测试基建 + golden manifest（官方 15.2.0 与 12.2.0，darwin-arm64，含双跑自复现验证） | gcc-15.2.0.md 阶段 1 | 已切 |
| phase-2 | 15.2.0 vanilla 复刻构建（字面量钉死）+ 字面量面清点 + 首份差异清单 | gcc-15.2.0.md 阶段 2 | 已切 |
| phase-3 | 15.2.0 差异驱动修补至 darwin-arm64 全量零差异，补丁落 `patches/15.2.0/` | gcc-15.2.0.md 阶段 3–4 | 完成；审计有条件放行（analysis/toolchain/phase3-review.md） |
| phase-3.1 | 审计收尾：P2-2 GAS 诊断文本保真 + P2-3 binutils isa-spec 默认值，重导补丁 | 审计报告 §P2-2/P2-3 | 完成；主会话现场复测验收（274/274、探针全绿） |
| phase-3d | 15.2.0 全量 EVT 收口（双平台）：301 DIFF + 605 MISSING → 0（RC01/02 → RC04 → 策略簇），T6 linux 收口腿 | phase3b-full-evt-acceptance.md + DECISIONS 2026-08-13 | 完成；双平台行为 gate 全绿，corrected lineage 已闭合三项历史过程证据，checklist 未决 0 |
| phase-3e | gdb / riscv32-wch-elf-run 上游&WCH 修改深析（分析-only，非 gate） | tmp/prompts/phase-3e.md + phase-3e-fix.md | 完成；r2 重签 PASS（Main 裁定）：对照重建后「43 个 WCH-only sim 选项」撤回（BSD sed 构建缺陷），trace 23/23 收口、custom32 命名解码直证，unresolved 归零 |
| phase-3f | phase-3c 未定论项收尾（OURS-V2 重冻结 + 矩阵复裁 + 逐项裁决） | tmp/prompts/phase-3f.md | 完成（正式 INVALID：冻结后 phase-3d 并发落补丁）；测量可复现、636 义务全裁决，有效重跑并入 phase-3g |
| phase-3g | 15.2.0 darwin 终局裁决 + 能力面收口（zstd、elfedit-mmap、norvc 我方回归、slim-LTO 残留、T5 强度重裁） | tmp/prompts/phase-3g.md | 完成；verdict FAIL（gate 全绿、35-feature 0 GAP、10/10 mismatch 类闭合于 V3.1；义务未 100% 终局故不判 PASS）；合并 aee2cb4、交付入库 f9fc735；0004 形态改造移交 phase-3d 批次 |
| phase-3h | binutils 0004 改造（运行期 `--w_priv_spec`）+ REWORK-0005（0001+0005 合并删位）+ wchsoftlib 注册 + objdump `-M xw` + DCXW 表序守卫 | DECISIONS 2026-08-15/16 + tmp/prep-0004-rework/notes.md §7 | 完成；独立审计有条件放行且修正轮 F1–F17 全闭合（phase3h-review.md）；双平台 47797/47797、SR-01 A=0、series 6→7 |
| phase-4 | 12.2.0 全周期（xPack tag 考据 → vanilla → 修补至零差异） | gcc-12.2.0.md | 完成；审计有条件放行（phase4-review.md），交付已 checkpoint 入库 |
| phase-4.1 | 审计收尾：P2-1 上游 gcc.target/riscv 全量补跑（对拍 vanilla、零回归）+ P2-2 `.highcode` 落位证据写回与补丁重导 | phase4-review.md §P2 | 完成；主会话复核验收通过 |
| phase-5 | 15.2.0 linux-amd64 复验（容器实测，含 linux 侧 golden） | gcc-15.2.0.md 阶段 5 | 完成；Linux 274/274，T3b 归因完成，未决 0 |
| phase-6 | 8.2.0 全周期（考据 → golden → vanilla → 修补 → 复放；host/行为补丁分离） | gcc-8.2.0.md + tmp/prompts/phase-6.md | 完成；审计有条件放行修正轮全闭合（phase6-review.md）；quick 242/242、全量 43969/43969（含产物级扩展），补丁 7 片入库 |
| phase-7 | GitHub workflows 构建 CD，本地 act 验证 | tmp/prompts/phase-7.md + DECISIONS 2026-08-17 phase-7 两条 | 会话已结束；交付物冻结于 tmp/p7-worktree @ eed1486，**未合并**、linux act 端到端**未跑**（等 8.2.0 销账期间会话终止）；现状核查与合并路径评估归 phase-10 S3 |
| phase-8 | 补丁清理：每行可解释，不破坏 gate 前提下优化可读性/可维护性/最小化（三版本补丁集） | 四份审计报告判定表 + main-handoff-p7p8.md §5 | 完成；独立双审计放行（phase8-review.md delta 节）；三版本 gate 终签全绿（quick 242/274/274×2、全量 43969 与 47797×2）；收口报告 phase8-closure.md；五项呈用户裁定项见 closure §7 |
| phase-9 | XW 表项 rv64 面与官方对齐（15.2.0+12.2.0 行为修复；8.2.0 为参照系不动） | phase8-closure.md §7① + tmp/prompts/phase-9.md | 完成；rv64 四类分歧归零（含 16 项裸别名静默编码分歧）、rv32 双平台零扰动（对 P8-R 封存值逐一命中）、独立审计 delta 放行（phase9-review.md）；三版本 XW 表项现统一 xlen=0 |
| phase-10 | 开源前检查：发布面清点、补丁集外部可用性、新鲜克隆复现实验、CI 方法审查（analysis-only） | tmp/prompts/phase-10.md | 完成；报告 phase10-opensource-readiness.md，独立审计放行（phase10-review.md）；act linux 腿端到端全绿；P10-F1 等 P1×4 移交发布准备 |
| 发布准备 | 用户八项裁定落地：P10-F1 修复、p7 CI 合并、双语 README、EVT 语料分发、公开仓库组装与验证 | DECISIONS 2026-08-18/19 | 完成；aspeedbmc/openwch-gcc 已发布，toolchain-ci run 32166821541 四腿全绿（274/274/242/274）+ wvproj 绿；语料经 Release 资产分发（R2 待写权限令牌）；darwin 托管可行性以实测收口 |

依赖：phase-2/3 依赖 phase-1 的 harness 与 manifest；phase-4/5 复用 phase-1 基建与 phase-3 的补丁面经验；phase-4 与 phase-5 可并行。
