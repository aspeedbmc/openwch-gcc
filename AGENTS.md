# openwch — 开源 WCH RISC-V GCC 工具链

## 项目目标

WCH 的 GCC 工具链修改未按要求开源。本项目从上游 GCC/binutils 出发，实现支持 WCH QingKe 自定义 ISA 扩展（XW 等，事实以 `ref/wch-isa-research` 为准）的开源工具链。

**唯一验收 gate：逐字节一致。** 同一 EVT 工程、同一编译配置下，我们的工具链产物（`.o`、`.elf`、`.bin`）与 WCH 官方工具链产物逐字节相同；`.map`/`.lst` 作诊断辅助，不作 gate。零差异达成前，任何里程碑不得宣称完成。**gate 按平台分别对照该平台的官方工具链**（darwin↔darwin 官方、linux↔linux 官方）：WCH 官方两平台包自身在链接级互有差异（2026-08-13 实测 15.2.0：14 项 elf/bin 不同、全部 .o 相同，归因为随包 libgcc 成员的 DWARF 内嵌构建路径），跨平台产物一致既非事实也不可能，不是本项目目标。**双平台交付要求**：同一补丁集必须在 darwin-arm64 与 linux-amd64 两个宿主上都能构建出编译器，且各平台的行为与产物分别与该平台官方逐字节一致。

平台顺序：**先 darwin-arm64 做到零差异，再开发 linux-amd64**。在此之前不写任何跨平台预防性代码。

## WCH 授权边界（用户已确认）

- **已获 WCH 授权**：可自由分析、使用 WCH 工具链（含提取、逆向）。
- 发布产物用于 WCH 芯片即无授权问题。
- **无需法律意义上的 cleanroom（隔离重实现）流程**。术语澄清：工作流中的「pristine 补丁复放验证」（全新上游源码 + 补丁集 → 重建 → 全量比对）是补丁集完整性/可复现性的工程检查，继续保留，与授权无关。
- 版本串等 comment 量（`.comment`/`.ident`/`DW_AT_producer` 等）可直接提取并逐字复用 WCH 官方定义——这是逐字节一致的前提。
- 授权话题到此为止：本项目内不再讨论合规问题（随包库合规由另一团队负责的决策继续有效）。

## 硬规则

- **字面量一致性**：我们产出的工具链二进制与 gate 产物中，凡与 WCH 官方二进制对应的字面量——构建路径/前缀、configure 串（含其不规则空白）、版本串、时间类字面量——必须与 WCH 值逐字节一致。手段：configure 参数逐字符复刻、构建目录布局对齐（`/Users/mrs/...` 经 symlink 指向 `tmp/` 构建树）、`SOURCE_DATE_EPOCH` 钉死；绝不依赖环境默认值。**边界**：以可观测字面量面为准（`strings`、`gcc -v`、`--version`、`ld --verbose` 的 SEARCH_DIR、`.comment`、DWARF producer/comp_dir）；工具链二进制的整体字节一致（宿主编译器代码生成、Mach-O SDK 戳、签名）不在要求内；gdb 完全不在范围内。binutils 不内嵌 configure 行，其验收只挂可观测字面量与产物字节，不做 configure argv 复原。
- **代码可解释性（授权不豁免此项）**：补丁必须是上游惯用形态的源码实现——MD 模式、opcode 表项、解析/属性逻辑，每处改动可溯源到一个明确的、有证据的行为。**禁止**：大段裸汇编/二进制字节块"凑数"、从 WCH 二进制搬运的不透明代码或查找表（上游惯用的 opcode 编码表不在此列）、针对特定 EVT 工程/文件的特判、任何"能过 compare 但讲不清为什么"的实现。审查标准：每个补丁能向上游 reviewer 解释。
- **深度分析/逆向 WCH 工具链文件或二进制 → 一律派 opus 级 agent 执行**，只回传文字结论；不在主上下文直接阅读大二进制、大 dump 或 strings 全量输出。
- **只能访问本仓库目录和互联网**，不得读取本机其他目录里的文件。
- **字节一致性比较的环境控制**：两条工具链必须在相同绝对路径下构建同一工程（`-g` 时 `DW_AT_comp_dir` 内嵌 cwd），产物换目录暂存后比较；比较前不做任何 normalize——差异本身是信息。
- ISA/编码事实不重新发现：以 `ref/wch-isa-research` 的结论为准，工具链层面只验证"接受面"（哪些 march 串、助记符、属性被接受及其编码）。

## 目录地图

- `ref/gcc/<platform>/<version>/` — 从 MRS 抽取的 WCH 官方工具链（gitignored；用 `scripts/extract-wch-toolchain.sh` 从 `ref/MounRiver Studio 2.app`（darwin）与 `ref/MRS_Toolchain_Linux_X64_V250`（linux）重新生成）。`platform` 是**宿主分发平台**，target 由 compiler triple 单独描述；二者正交，绝不能把 `arm-none-eabi` 写成 Darwin 专属 target。
  - darwin-arm64（WCH 的 macOS/Apple Silicon 平台包）：`15.2.0`（target `riscv32-wch-elf`，arm64 原生，版本串 `(g5115c7e44-dirty) 15.2.0`）、`12.2.0`（target `riscv-wch-elf`，arm64，xPack 系）、`8.2.0`（target `riscv-none-embed`，x86_64/Rosetta，xPack 系）、`9.3.1`（target `arm-none-eabi`，宿主可执行体为 x86_64/Rosetta）。
  - linux-amd64：当前仓库给定的 `MRS_Toolchain_Linux_X64_V250` 输入只抽到 `15.2.0`（target `riscv32-wch-elf`）；WCH 的 Linux 平台也有对应的 `arm-none-eabi` target 工具链，当前目录缺失只代表参考输入尚未纳入该包，不代表平台没有该 target。本项目范围仍只含上述三个 RISC-V 版本。
- `ref/wch-evt/` — WCH EVT 示例工程库。README「编译项目」表是覆盖各微架构与 XW 的精选工程清单（差异测试用例来源）；`tools/wvproj_to_make.py` 将 `.wvproj`/`.cproject` 转为独立 Makefile（`--gcc-major`/`--compiler-path` 可指定工具链）；`patches/` 是让精选工程可构建的修补。
- `ref/wch-isa-research/` — QingKe 自定义 ISA / XW / CSR / errata 研究成果（先读其 README）。
- `ref/wch-manuals/` — WCH 官方手册。
- `analysis/` — 本仓库产出的研究交付物（工具链取证报告等）。
- `plans/` — 总体阶段路线图（`roadmap.md`）与各版本工作流的 prompt 骨干（任务书）。
- `patches/` — 本项目产出的 gcc/binutils 补丁（按版本分目录）。
- `scripts/` — 仓库脚本。
  - `scripts/ci/` — CI 专用脚本。只有 `setup-literal-paths.sh` 带执行环境守卫（它要在仓库外建符号链接）；其余三个在本机可直接跑（2026-08-18 合并更新：p7 阶段就是这么用的，但它当时依赖的两个 darwin 本地驱动脚本 `darwin-prepare.sh`/`darwin-window-run.sh` 至今未版本化，只存在于 p7 证据树 `tmp/p7-worktree/tmp/p7-evidence/S4/`）：
    - `provision-official.sh <版本>` — 取得并校验 WCH 官方包，抽取到 `ref/gcc/<platform>/<version>/`（这正是 `evt-golden.sh`/`evt-compare.sh` 硬编码的路径）。`COMPILER_PATH` 可覆盖，`OFFICIAL_ARCHIVE` 可指定本地归档。
    - `prepare-sources.sh <版本> [dest-root]` — 按各版本自己的口径取上游源码、校验、应用补丁 series（三版本口径互不相同）。缺省 dest-root 为 `tmp/ci-src`；8.2.0 忽略该参数（其构建脚本硬编码 `tmp/toolchain_8.2.0/work`）。
    - `setup-literal-paths.sh <版本> [源码树]` — 在容器/runner 内建 WCH 字面构建路径符号链接。**守卫**：仅当存在容器标记，或 `GITHUB_ACTIONS=true` 且 `ACT` 未设时才执行，否则非零退出。
    - `act-verify.sh <job-id>` — 本地 act 验证入口，只允许 linux job，禁用 `--bind` 与任何 `-self-hosted` 映射，在专用工作副本上跑，产出 `timing.tsv`/`disk.tsv`/`deliverable-binding.txt`。
- `.github/workflows/` — `toolchain-ci.yml`（四条腿的字节 gate）、`release.yml`（tag 触发的工具链 tarball 发布）、`wvproj.yml`（EVT 工程构建自检）。
- `tmp/` — **本地使用，不入 git**（gitignored，不随任何发布面分发）。布局：
  - `tmp/prompts/` — agent 级提示词（阶段任务书 `phase-N{.md,.checklist.md}`，执行 agent 逐项打勾并附证据指针）。
  - `tmp/<task>/` — 各任务的状态、提示词/交接文档与 evidence（如 `tmp/phase8-evidence/`、`tmp/publish/`）。上游源码 clone 与构建树按 `tmp/toolchain_<版本>/` 组织；CI 另用 `tmp/ci-src/`（上游源码）与 `tmp/ci-cache/`（官方包与前置件归档缓存）。
  - **tmp 外的文档/文件不得指向 tmp/**：进入版本库的交付物必须自含——证据要么摘要转写、要么复制入库（先例：`analysis/toolchain/phase9-rv64-spec-*.md`）。存量豁免：既有补丁 message 与历史 analysis/DECISIONS 条目中的 tmp/ 证据坐标按 2026-08-18 裁定⑤保留、由根 README「证据指针约定」解释；新增或修订内容一律不得新增 tmp/ 指向。

## 差异测试方法

0. 验收面分两层：README 精选 9 工程是**快速回归集**（每轮修补后必须保持全绿）；**收口 gate 是全量 EVT 树**（canonical 能构建的全部工程产物逐字节，15.2.0 起适用，phase-3b 口径）。
1. 用 `wvproj_to_make.py` 为每个精选 EVT 工程生成 Makefile，分别以 WCH 官方 gcc 与本项目 gcc 构建。
2. 以 WCH 官方各版本对全部精选工程的产物 SHA256 固化为 golden manifest，作为回归基线；每次编译器修补后重跑全量对比。
3. 差异定位顺序：`-S` 汇编文本 → `.o`（objdump -d / -r 定位段）→ `.elf` → `.bin`。

## 范围决策（用户已拍板）

- **版本范围**：8.2.0、12.2.0、15.2.0 三个版本都做；先做 12.2.0 和 15.2.0，8.2.0 靠后。每个版本一条独立工作流，prompt 骨干在 `plans/`。
- **库策略**：**完全逐字复用 WCH 随包库**（libgcc/newlib/crt/specs 等），本项目只产出编译器本身（gcc + binutils）的补丁。随包库合规性由另一团队负责，已确认无合规问题——本项目不再关注库合规话题。
- **仓库布局**：本仓库只存补丁（`patches/`）与构建/测试脚本，不进上游源码树。上游源码 clone 与全部构建产物放 `tmp/toolchain_{8.2.0,12.2.0,15.2.0}/{gcc,binutils,build,...}`（gitignored）。
- **CD**：三版本零差异达成后，增加 GitHub workflows 实现构建 CD，本地用 `act` 验证 workflow。
