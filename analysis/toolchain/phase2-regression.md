# Phase 2 需求与设计回归

回归日期：2026-08-13（Asia/Tokyo）。本表对照
`tmp/prompts/phase-2.md`、`plans/gcc-15.2.0.md` 硬约束 6/7 与阶段 2；
状态只依据可复核证据，不把预期失败写成通过。

## 需求回归

| 范围 | 判定 | 证据 |
|---|---|---|
| 前置：manifest/compare 可用 | 满足 | `analysis/golden/15.2.0-darwin-arm64.tsv`；`bash -n scripts/evt-compare.sh` |
| 前置：固定 symlink | 满足 | `readlink /Users/mrs/riscv-gnu-toolchain` 精确为仓库内 `tmp/toolchain_15.2.0/riscv-gnu-toolchain` |
| T1 依赖判定 | 满足 | `tmp/toolchain_15.2.0/t1-otool.txt`；cc1/cc1plus 无 gmp/mpfr/mpc/isl/zlib dylib |
| T2 GCC 源码 | 满足 | HEAD `5115c7e447fc07457443df874bf57840e8316d5f`、exact tag `releases/gcc-15.2.0`、tracked tree clean |
| T2 binutils 源码/布局 | 满足 | HEAD `2bc7af1ff7732451b6a7b09462a815c3284f9613`、tag `binutils-2_45`；`build-gcc/.././gcc` 解析正确 |
| T3 可重入 build 脚本 | 满足 | 先有保留源码的第二次完整构建；再记录整棵 `tmp/toolchain_15.2.0/` 空目录 checkpoint，重跑 T2 fresh bootstrap 后原样执行 T3，退出 0 |
| T3 只构建 compiler | 满足 | 仅 `all-gcc/install-gcc`；第二轮日志无 `*-target-*` goal，`build-gcc` 无 target build dir；`reentrant/run2/source-and-scope.txt` |
| T3 官方库/sysroot 注入 | 满足 | 三棵 full `diff -qr` 均空；第二轮 2920 文件；`reentrant/run2/injection-full.diff` 0 bytes |
| T4 字面量面 | 满足 | `analysis/toolchain/phase2-literal-surface.md`；关键 1/3/4/5/6 全绿，2/7/8 完整分类 |
| T5 golden 稳定性 | 满足 | 官方全量复验 274/274 gate、277/277 aux；`t5-evidence/golden-stability.*` |
| T5 vanilla 全量 compare | 满足 | 9/9 BUILD-FAIL，0/274 gate；`analysis/toolchain/phase2-diff-inventory.md` |
| T5 XW 代表首分歧 | 满足 | full pipeline 在 driver 拒绝 `rv32imac_xw`；日志与空对象快照完整保留 |
| T5 代表工程 3 个指令差异 | 满足 | project as 有效参数为 WCH=0/vanilla=1；仅在两侧将 `xw` 显式为 `xw2p0` 后，同一真实 v4bc `.s` 隔离得到对象顺序前三个 site 的 3/3（`0x239c`、`0x239c`、`0x2bdc`）；WCH 三个重组对象逐字等于 golden |
| 五类差异分类 | 满足 | driver/march、assembler XW encoding、attributes 已观察到；codegen/link/debug 给出“未观察到”及隔离依据 |
| 大输出/原字节/范围边界 | 满足 | 大构建输出落 `tmp` 日志；manifest 用 SHA 原字节比较；未 normalize；没有 Phase 3 行为补丁 |

## 设计回归

| 设计约束 | 判定 | 证据/说明 |
|---|---|---|
| 硬约束 6：comment 字面量 | 满足 | 四份 `.comment` MD5 均为 `83a117f6276bc1e35530c55b1451e9b3`；DWARF producer 两侧同条件一致 |
| 硬约束 7：configure 字面路径/argv | 满足 | argv 每轮从官方 `gcc -v` 现场提取；Configured 行 1303 bytes、SHA256 `9e040762…a42e`、cmp 0 |
| 硬约束 7：固定时间 | 满足 | build 与 EVT harness 均 export `SOURCE_DATE_EPOCH=1767225600` |
| 硬约束 7：SEARCH_DIR/版本面 | 满足 | SEARCH_DIR、as/ld 首行、Target/thread/LTO/GCC version 均逐字一致 |
| 阶段 2：只测量、不打行为补丁 | 满足 | GCC/binutils tracked tree 均 clean；安装后 driver 仍复现 pristine XW failure |
| 阶段 2：只建 compiler、不建 target 库 | 满足 | `all-gcc/install-gcc` + full binutils；target libraries 由 WCH 原树注入 |
| 阶段 2：官方库/sysroot 原字节复用 | 满足 | `lib/gcc/.../15.2.0`、target include、target lib 三棵全树 diff 为空 |
| 阶段 2：差异清单覆盖工程范围 | 满足 | 9 工程全部执行并保留日志；主 compare 的共同 driver blocker与真实 v4bc `.s` 下游 assembler 隔离分开记录 |
| 工具链整体字节一致 | 不作为 gate | 两次 host Mach-O hash 不同；设计明确排除 host 编译器整体字节、SDK/签名戳 |

T4.6 按命令的数据输出通道 stdout 验收：22 行逐字一致且两侧命令均退出 0。
vanilla 在 stderr 的 10 条 XW 诊断没有被丢弃，而是完整保存并纳入 T4.2/T5
行为差异；诊断流不冒充 22-row multilib 数据面。

构建期 canonical `TFLAGS` 覆盖的是所有临时 xgcc probes，不进入 host
CFLAGS、configure argv、multilib 表或安装后 driver；可能影响的临时
include-fixed/macro 输出随后被官方 `lib/gcc/.../15.2.0` 整棵替换。它是让
pristine 22 项配置完成 `all-gcc/install-gcc` 的构建手段，不是 Phase 3
行为补丁。host zlib 的 `CPPFLAGS=-UTARGET_OS_MAC` 同样只处理当前 Apple
Clang 与 bundled zlib 1.2.11 的宿主构建冲突。

## 可重入性解释

先完成了保留 T2 pristine source/prerequisites、由脚本精确清空
`build-gcc`、`build-binutils`、`output` 与 `logs` 的第二次完整构建；2920
文件集合与第一轮相同，T4 run1/run2 的 71 个证据文件 `diff -qr` 为空。

随后按验收字面再作更强证明：把原 `tmp/toolchain_15.2.0/` 同卷 rename 到
quarantine（不删除），新建空目录并记录 0-byte `empty-state.entries`；重跑
T2 fresh shallow clone、五包 SHA512 验证与 prerequisites/layout，再原样调用
T3 build 脚本。构建退出 0，install 普通文件仍为 2920 且集合相同，三棵
注入树 full diff 为 0，T4 与最初 run1 的完整 71-file diff 为 0。T2 与 T3
职责仍分离，build 脚本接口未改。证据：
`tmp/phase2-evidence/literal-clean/{summary.txt,empty-state.entries,`
`fresh-sources.txt,output-files.txt,injection-full.diff,`
`t4-run1-literal-clean.diff,t4/}`。旧树保存在其 `quarantine-...` 目录，便于
审计与恢复；历史 T1/T5 小证据已复制回稳定顶层路径。
