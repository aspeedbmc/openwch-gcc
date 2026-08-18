# Prompt 骨干：GCC 15.2.0（riscv32-wch-elf）零差异工作流

> 状态：定稿（取证事实已并入，来源 `analysis/toolchain/wch-gcc-toolchain-survey.md`，下称"报告"）。
> 本工作流是三版本中的先导：差异测试基建（Makefile 生成、golden manifest、对比脚本）在此建立，12.2.0 / 8.2.0 工作流复用。

## 使命

从上游 GCC 15.2.0 + 对应 binutils 出发，产出一组开源补丁，使自建工具链对全部精选 EVT 工程的产物（`.o`/`.elf`/`.bin`）与 `ref/gcc/darwin-arm64/15.2.0` 逐字节一致。先 darwin-arm64，达标后同一补丁集在 linux-amd64 复验（对照 `ref/gcc/linux-amd64/15.2.0`）。

## 硬约束

1. 只修改 gcc/binutils 源码并以补丁形式落盘 `patches/15.2.0/{gcc,binutils}/`；**库与 sysroot 逐字复用 WCH 随包内容**（libgcc/newlib/crt/specs/头文件），不重建、不修改。
2. 上游源码 clone 与构建树只放 `tmp/toolchain_15.2.0/`（gitignored）；本仓库只进补丁、脚本、manifest、报告。
3. 比较前不对产物做任何 normalize；两条工具链在**相同绝对路径**下构建同一工程，产物换目录暂存后比较。
4. 深度逆向 WCH 二进制一律派 opus 级 agent；ISA 事实以 `ref/wch-isa-research` 为准，不重新发现。
5. 只访问本仓库目录与互联网。
6. comment 量逐字复用 WCH 官方定义：configure 传 `--with-pkgversion=g5115c7e44-dirty`；`.comment` 精确字节为 32 字节 `\0GCC: (g5115c7e44-dirty) 15.2.0\0`（报告 §3.1，md5 `83a117f6276bc1e35530c55b1451e9b3`，`-O2` 与 `-O2 -g` 相同）；`DW_AT_producer` 不含 pkgversion。
7. **字面量一致性（CLAUDE.md 硬规则）**：路径、时间、configure、版本类字面量逐字节对齐 WCH 值。具体手段：configure 经 `/Users/mrs/riscv-gnu-toolchain/gcc/configure` 字面路径调用（`Configured with:` 行记录的是 configure 的 `$0`——`/Users/mrs/riscv-gnu-toolchain` 做成指向 `tmp/toolchain_15.2.0/riscv-gnu-toolchain` 的 symlink，需一次性管理员操作，见 phase-2 前置条件）；configure 参数逐字符复刻（含 multilib-generator 与 CFLAGS_FOR_TARGET 的不规则空白）；harness 统一 export 钉死的 `SOURCE_DATE_EPOCH=1767225600`（2026-01-01T00:00:00Z，覆盖 EVT 源码中可能的 `__DATE__`/`__TIME__`）。验收（逐字节）：`Configured with:` 行 diff 为空；`.comment` md5 命中；`ld --verbose` 的 SEARCH_DIR 与 WCH 一致。边界：工具链二进制整体字节一致、宿主编译器代码生成、Mach-O SDK 戳、gdb 均不在要求内；binutils 无内嵌 configure 行，不做 argv 复原。

## 基线与输入（已取证）

- WCH 官方参照物：`ref/gcc/darwin-arm64/15.2.0/`（arm64 原生）、`ref/gcc/linux-amd64/15.2.0/`。两平台 configure 行归一化构建前缀后逐字符一致（报告 §9）。
- 上游基线：GCC 15.2.0 release——版本串中的 `5115c7e44` 即 `releases/gcc-15.2.0` tag 所指上游 commit（`5115c7e447fc07457443df874bf57840e8316d5f`）；`-dirty` 表示 WCH 补丁未提交，不存在可拉取的 WCH commit，补丁面只能差异驱动重建。配套：binutils 2.45、newlib 4.5.0、gdb 17.1（binutils/gdb 为上游裸版本串，无 pkgversion）。
- 构建体系：riscv-gnu-toolchain 框架，configure 全行逐字符记录于报告 §1.1——含 `--with-multilib-generator`（22 条 multilib）且串内有不规则空白、`CFLAGS_FOR_TARGET=-Os    -mcmodel=medlow`、`--with-arch=rv32gc --with-abi=ilp32 --with-isa-spec=2.2`。复刻时逐字符对齐；vanilla 构建走 riscv-gnu-toolchain 而非手工 configure。
- 构建前缀：WCH 在 `/Users/mrs/riscv-gnu-toolchain`（linux 为 `/home/wch/...`）构建，路径被编进 `cc1`/`as`/`ld` 与 `ld` 的 `SEARCH_DIR`。按硬约束 7 经 symlink 钉死为同一字面路径；副作用是 `.map` 的 SEARCH_DIR 行也应随之收敛（仍非 gate）。
- 测试用例：`ref/wch-evt/README.md`「编译项目」表全部精选工程，经 `tools/wvproj_to_make.py --gcc-major 15` 生成 Makefile；EVT 修补先跑 `ref/wch-evt/patches/apply.sh`。
- 目录约定：`tmp/toolchain_15.2.0/{gcc,binutils,build-gcc,build-binutils,install,evt-build}/`。

## 阶段

1. **golden manifest（共享基建）**：全部精选工程用 WCH 官方 15.2.0 构建通过；同一工程连续构建两次验证哈希自复现（清除 harness 级非确定性）；固化产物 SHA256 到 `analysis/golden/15.2.0-darwin-arm64.tsv`。构建/对比脚本进 `scripts/`，设计为版本参数化，供 12.2.0/8.2.0 复用。
2. **vanilla 复刻构建 + 字面量面清点**：按取证 configure 行（从 WCH 二进制现场提取，非转抄）在 darwin-arm64 构建未打补丁的上游工具链，字面量按硬约束 7 钉死；只构建编译器（`make all-gcc && make install-gcc` + binutils），**不构建任何 target 库**——install 树里除 `bin/`、`libexec/` 的可执行体外，编译/链接读到的一切（头文件、libgcc、sysroot 库、crt、specs）都是 WCH 原字节注入。构建前先 `otool -L` WCH 的 cc1 判定 gmp/mpfr/mpc 的 in-tree/系统链接方式。产出字面量对照表 + 首份差异清单（= WCH 补丁面的完整工程范围）。本阶段只测量，不打补丁。
3. **差异驱动修补**：逐工程、按 `-S` → `.o` → `.elf` → `.bin` 顺序定位。已取证的 WCH 补丁面锚点（报告 §5–6，复刻时逐条对齐行为，包括缺陷）：
   - march 解析：`xw` 与 `_xw` 拼法等价，版本号纯 passthrough（`xw9p9` 也接受，`xq` 拒绝）；裸 `xw` 在 **GCC 侧**规范化为 **`xw2p0`** 直写 `.riscv.attributes`（逐字节关键），**GAS 独立汇编路径**的 mapping symbol 则为 `xw2p2`（官方实测，2026-08-13 审计回填）——两面并存，勿混同；含 D 的组合（`rv32gcxw`）被静默接受但退回不含 XW 的默认 multilib——保持同样的静默行为。
   - gas：8 条 16 位 XW 压缩形式受 march `xw` 门控；`mcpy`/`mrsl`/`mrslu`/`wexti` 不受门控、任意 RV32 march 恒可汇编；锚点编码 `c.lbu`→`0x2188`、`mcpy`→`0x60b5700f`（报告已逐字节复现）。
   - gcc：`WCH-Interrupt-fast` 中断属性（正确值生成 `mret`；拼错的值**有告警**并降级 `ret`，缺陷在于告警文案未把 `WCH-Interrupt-fast` 列为合法值。2026-08-13 审计更正：此前「拼错静默无 warning」的措辞失准，官方确实告警，实现与二进制一致）；cc1 指纹串 `non-standard111 extension`（含拼写错误，逐字保留）。**诊断文本（gcc 与 GAS）纳入保真面**，与 gate 产物同标准。
   每个补丁附最小复现用例，每轮修补后全量 golden 回归。
4. **darwin 验收**（见验收标准）→ 冻结补丁集。
5. **linux-amd64 复验**：同一补丁集在 linux/amd64 容器构建，对照 `ref/gcc/linux-amd64/15.2.0` 的平台自身 golden manifest 重跑。阶段 5 已完成：精选集 274/274 gate；官方跨平台 14 项链接差异已裁定为非目标。T3b 确认两包随附库树输入不同，并把代表失配 v3a 归因到 `libgcc.a` 成员的 DWARF 构建路径。

## 验收标准

- 总体工作流的自动化目标（不作为 phase-5 单项完成条件）：`scripts/` 一键串联
  源码获取 → 打补丁 → 构建 → 注入随包库 → 全量 EVT 对比。当前 phase-5 交付的
  Linux 构建脚本覆盖 pristine 校验、打补丁、构建与库注入；精选集 compare 由
  `scripts/evt-compare.sh` 独立执行。1298 工程全量 EVT 收口仍属于 phase-3d。
- 全部精选工程 `.o`/`.elf`/`.bin` SHA256 与 golden manifest 完全一致（`.map`/`.lst` 差异仅记录不阻塞）。
- 补丁集干净应用于上游 pristine 树（`git apply --check` 通过），每个补丁有一行说明其对应的差异现象。
- 官方工具链双跑自复现前提已验证并记录在 manifest 头部。

## 升级/中止条款

- 出现无法用 gcc/binutils 补丁解释的产物差异（如疑似随包库版本错配、工程配置歧义）→ 停下向 Main 报告，不猜。
- 同一差异 5 轮未收敛 → 蒸馏 handoff 换新上下文。
- vanilla 构建在 darwin-arm64 无法完成（上游对 host 工具链不兼容）→ 报告阻塞点与候选方案，等待裁定。

## 前提登记（premise register）

| 前提 | 证据 | 状态 |
|---|---|---|
| 基线 = 上游 15.2.0 release；`5115c7e44` 即 release tag commit，`-dirty` 为未提交补丁 | 报告 §2.1 | 已验证 |
| binutils 2.45 / newlib 4.5.0 / gdb 17.1 | 报告 §1 | 已验证 |
| configure 全行（riscv-gnu-toolchain 形态，含不规则空白） | 报告 §1.1 | 已验证 |
| darwin 与 linux 的 configure 行归一化前缀后一致 | 报告 §9；阶段 5 报告 §2 容器实机复验（payload 1280 B，`cmp=0`） | 已验证（阶段 5 复验） |
| `.comment` 精确 32 字节；DW_AT_producer 不含 pkgversion | 报告 §3 | 已验证 |
| 官方工具链同路径双跑产物自复现 | 阶段 1 Darwin manifest；阶段 5 Linux manifest（9/9，`deterministic=9`） | 已验证 |
| 随包库逐字复用可使 `.elf` 一致性归约为 `.o` 一致性 | 阶段 2 实测 | 待验证 |
| symlink 路径下 configure `$0` 字面量与 WCH 一致（`Configured with:` diff 为空） | 阶段 2 实测 | 待验证 |
| riscv-gnu-toolchain 相对布局可复现 `--src=.././gcc` 等相对字面量 | 阶段 2 实测 | 待验证 |
| linux 侧 XW 行为与 darwin 一致 | 阶段 5 报告 §4：march/8+4 编码/独立 GAS/缺陷四探针/35-case 诊断逐字节对拍 | 已验证 |
| darwin 与 linux 官方完整快速 gate 跨平台一致 | 阶段 5 报告 §5：相同绝对工程路径下 260/274 相同，8 ELF + 6 BIN 不同；T3b 抽样归因到不同随包库输入 | 已证伪；已裁定为非目标，不阻塞平台自身 gate |
| 同一冻结补丁集在 linux 对 linux 官方 golden 一致 | 阶段 5 报告 §6–8：pristine 复放、Linux 构建/库注入、字面量与 compare | 已验证（精选集 274/274） |
| gate 不覆盖「工具链安装根前缀」：harness 双侧对称注入 `-fdebug-prefix-map`（根前缀→中性路径），承载 48/274 gate 判定，后缀仍全比、不掩盖行为差异 | 审计报告 §2.2 实测；P2-1 裁定豁免 | 已裁定 |
