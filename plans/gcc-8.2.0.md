# Prompt 骨干：GCC 8.2.0（riscv-none-embed）零差异工作流

> 状态：骨干（取证事实已并入，来源 `analysis/toolchain/wch-gcc-toolchain-survey.md` §9，下称"报告"），排期在 12.2.0 / 15.2.0 之后。
> 依赖 15.2.0 工作流建立的共享基建。

## 使命

从 xPack 系上游（GNU MCU Eclipse / xPack riscv-none-embed-gcc 8.2.0）出发，产出开源补丁，使自建工具链对精选 EVT 工程产物（`.o`/`.elf`/`.bin`）与 `ref/gcc/darwin-arm64/8.2.0` 逐字节一致。

## 硬约束

同 15.2.0 骨干第 1–5 条（补丁落盘 `patches/8.2.0/`，构建树 `tmp/toolchain_8.2.0/`），另加：

6. comment 量逐字复用：`.comment` 精确字节 `\0GCC: (xPack GNU RISC-V Embedded GCC x86_64) 8.2.0\0`（报告 §9）。注意版本串含 `x86_64`——即使我们构建 arm64 宿主的编译器，pkgversion 也必须逐字保持该串（gate 是产物字节，不是宿主架构）。
7. **字面量一致性（CLAUDE.md 硬规则）**：本版本的构建路径字面量为 `/Users/wch/Work/riscv-none-embed-gcc-10.2.0-1.2/`、源码目录 `riscv-gcc-10.2.0-1.1`（报告 §9）；symlink 钉死方式沿用既有约定，具体在 phase-6 prompt 里裁定。

## 版本特有问题（先裁定再动工）

1. **宿主架构（2026-08-16 已裁定：x86_64/Rosetta 路线）**：官方 configure 行内嵌 `--build/--host=x86_64-apple-darwin17.7.0`（S1 现场提取），而 configure 行属逐字节复刻的字面量面——arm64 原生宿主与该 gate **原理性互斥**（先验不可满足，非实测差异；伪造 `-v` 输出属可解释性禁区）。故 S2 起直接 x86_64/Rosetta 宿主：configure triple 逐字复刻、宿主编译器 clang -arch x86_64、构建与运行均在 Rosetta 下，与官方 golden 的 Rosetta 运行对称。旁证：GCC 8.2 代码基无 aarch64-darwin 宿主支持。
2. **老代码基的现代宿主构建**：GCC 8.2 时代源码用现代 clang/macOS SDK 构建预期需要 host 侧适配补丁（与目标行为无关，单独归类 `patches/8.2.0/host/`，不计入"WCH 行为补丁面"）。
3. **基线锚点（部分已取证）**：构建体系为 xPack `riscv-none-embed-gcc`（源自 sifive/freedom-tools），配套 binutils 2.32、newlib 3.0.0、gdb 8.3，`--with-arch=rv32imac --with-abi=ilp32`（无 `--with-isa-spec`），multilib 23 条（报告 §9）。注意易误读点：构建路径为 `/Users/wch/Work/riscv-none-embed-gcc-10.2.0-1.2/`、源码目录名 `riscv-gcc-10.2.0-1.1`——`10.2.0-1.x` 是 xPack 打包版本号，GCC 实为 8.2.0。仍待考据：对应的 xPack release tag 及其与 WCH 构建的偏差。该版本是 MRS 初代 XW 工具链，社区已有对其 XW 补丁的部分公开分析，考据时优先核对而非重做。
4. **march 语法代差（已取证）**：8.2.0 **拒绝** `_xw` 拼法（`unsupported ISA substring '_xw'`），仅接受无下划线的 `xw`；`mcpy`/`mrsl`/`mrslu`/`wexti` 不支持（32 位自定义指令在 8.2.0→12.2.0 之间引入），XW 压缩形式已支持且 `c.lbu` 编码 `0x2188` 与新版一致（报告 §9）。确认 `wvproj_to_make.py --gcc-major 8` 生成的 flags 与 MRS 原生调用一致。
5. **golden 集裁剪**：精选工程中官方 8.2.0 无法构建的（B 扩展、V5F 等新特性工程预期在列）记录并剔除，golden 集为该版本可构建工程全集。

## 阶段

1. golden manifest：官方 8.2.0（Rosetta 运行）构建 + 双跑自复现 → `analysis/golden/8.2.0-darwin-arm64.tsv`。
2. 基线裁定（xPack release 考据 + 取证报告）。
3. vanilla 复刻构建（含 host 适配补丁）→ 首份差异清单。
4. 差异驱动修补 → 全量 golden 回归 → 验收。

## 验收标准

同 15.2.0 骨干，另加：host 适配补丁与行为补丁分目录，行为补丁单独可审计。

## 升级/中止条款

同 15.2.0 骨干。（原 arm64→x86_64 降级条款已被 2026-08-16 宿主路线裁定先验消耗：直接 x86_64/Rosetta。）

## 前提登记（premise register）

| 前提 | 证据 | 状态 |
|---|---|---|
| 构建体系 xPack riscv-none-embed（sifive/freedom-tools 系），打包版本 10.2.0-1.x、GCC 8.2.0 | 报告 §9 | 已验证 |
| binutils 2.32 / newlib 3.0.0 / gdb 8.3 | 报告 §9 | 已验证 |
| `_xw` 拒绝、仅 `xw`；无 `mcpy` 等 32 位自定义指令 | 报告 §9 | 已验证 |
| 对应 xPack release tag 可锚定 | phase-6 S1：v10.2.0-1.2 框架 + v8.2.0-3.1 代组件源（freedom-tools v2019.05.0），configure 36/36 token 命中，distro-info 一手现场 | 已验证 |
| arm64 宿主与 x86_64 宿主产物字节一致 | 2026-08-16 裁定路线合一（x86_64/Rosetta），无需验证 | 不适用 |
| 老代码基可在 Rosetta/x86_64 + 现代 clang/SDK 下完成构建（host/ 适配补丁面） | S2 实测 | 待验证 |
| golden 集裁剪清单 | phase-6 S1 普查：MRS-GCC8 归一口径 8/9，恒定剔除 v3c-led（core_riscv.h 内联 mcpy）；R1 裁定取 C=8 | 已验证 |
