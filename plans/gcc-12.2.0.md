# Prompt 骨干：GCC 12.2.0（riscv-wch-elf）零差异工作流

> 状态：Phase 4/4.1 已完成：darwin-arm64 active 与 pristine 两条验证链均为
> 274/274 gate 零差异，phase-4.1 上游回归相对 vanilla 零回归；最终交付为 GCC 9 条 + binutils 7 条补丁；取证事实来源
> `analysis/toolchain/wch-gcc-toolchain-survey.md` §9（下称“报告”）及
> `analysis/toolchain/phase4-baseline.md`。
> 依赖 15.2.0 工作流建立的共享基建（Makefile 生成、golden manifest、对比脚本），本工作流只做版本特有部分。

## 使命

从 xPack 系上游（GCC 12.2.0）出发，产出开源补丁，使自建 `riscv-wch-elf` 工具链对精选 EVT 工程的产物（`.o`/`.elf`/`.bin`）与 `ref/gcc/darwin-arm64/12.2.0` 逐字节一致。目标平台 darwin-arm64（`ref/` 中无 linux 12.2.0 参照物；linux 侧是否纳入待获得对应官方包后另行立项）。

## 硬约束

同 15.2.0 骨干第 1–5 条（补丁落盘 `patches/12.2.0/`，构建树 `tmp/toolchain_12.2.0/`），另加：

6. comment 量逐字复用：`.comment` 精确字节 `\0GCC: (xPack GNU RISC-V Embedded GCC arm64) 12.2.0\0`（报告 §9），pkgversion 传 `'xPack GNU RISC-V Embedded GCC arm64'`。
7. 基线 release tag 考据完成前不开始 vanilla 构建。
8. **字面量一致性（AGENTS.md 硬规则）**：本版本的构建路径字面量为 `/Users/mrs/Work/riscv-none-elf-gcc-xpack.git/`（报告 §9）；symlink 钉死方式与 `SOURCE_DATE_EPOCH` 取值沿用 phase-1/2 约定，具体在 phase-4 prompt 里裁定。

## 版本特有问题（先裁定再动工）

1. **基线锚点（已裁定）**：构建体系锚定 xPack `v12.2.0-3`
   （commit `1737182b…`），源基线为该 recipe 使用的 GNU GCC 12.2.0 与
   binutils 2.38 verified tarballs；WCH helper fork 不可得，因此以 xPack
   目录/版本/阶段定义为 provenance，以官方 `gcc -v` configure argv
   逐字复放为构建规格。完整依据见 `phase4-baseline.md`。
2. **triple 差异的连带面（已裁定）**：`riscv-wch-elf` 进入 install
   路径、specs、SEARCH_DIR 与工具查找；完整 dumpspecs、SEARCH_DIR、43 项
   multilib、版本流和最终 EVT gate 均现场对拍。未发现可归因于 triple
   rename 的额外隐藏行为；WCH 行为差异均由独立源码补丁说明。
3. **`.riscv.attributes` 陷阱（已取证）**：12.2.0 的裸 `xw` 规范化为 **`xw1p0`**（15.2.0 是 `xw2p0`），直写 `.riscv.attributes`——不可把 15.2.0 的 march 处理补丁原样移植。`xw`/`_xw` 两拼法在 12.2.0 均接受。
4. **与 15.2.0 的补丁面对比**：WCH 官方 12.2.0 已支持 `mcpy`/`mrsl`/`mrslu`/`wexti`，且编码与 WCH 官方 15.2.0 逐字节相同（报告 §9）——上游 vanilla 2.38 仍缺失这些指令；32 位自定义指令的 gas 补丁预期同源，但代码基相差 3 个大版本，仍以 12.2.0 自己的差异清单为准，不假设直接可移植。
5. **EVT 工程配置**：MRS 元数据 pin GCC12 的工程用原生配置；其余用 `--gcc-major 12` 覆盖。官方 12.2.0 无法构建的精选工程（如有）记录并从本版本 golden 集剔除，不算失败。

## 阶段

1. golden manifest：全部精选工程用 WCH 官方 12.2.0 构建 + 双跑自复现验证 → `analysis/golden/12.2.0-darwin-arm64.tsv`（复用共享脚本，传版本参数）。
2. 基线裁定：取证报告 + xPack release 考据，输出「上游源 + 构建方式」结论进前提登记。
3. vanilla 复刻构建（xPack 框架或直接 configure，以阶段 2 结论为准）→ 首份差异清单。
4. 差异驱动修补 → 全量 golden 回归 → darwin 验收。

## 验收标准

同 15.2.0 骨干（版本号替换；golden 集为本版本可构建工程的全集）。

最终验收结果：active 与 pristine compare 均 `rc=0`、274/274；两条验证链
各通过 33/33 诊断、20/20 行为、13/13 字面量、8/8 wchsoftlib 与
定向源码测试（7 组 patch-added GCC 用例共 423 PASS + GAS `riscv.exp`
全量 202 PASS）。phase-4.1 另在 vanilla 与 active GCC 上补跑无过滤
`gcc.target/riscv` 全量及受目标无关改动影响的三个 dg 集合：vanilla
PASS 2007/4/190/36，active PASS 2430/4/192/36，四组 PASS→FAIL/ERROR
均为 0；`riscv.exp` 两侧均保留相同的 62 个宿主执行环境既有 FAIL，故
结论口径是“相对 vanilla 零回归”，不是“全套件绝对零 unexpected”。
完整证据索引见 `tmp/prompts/phase-{4,4.1}.checklist.md`，T1 `.sum` 与差分见
`tmp/phase4.1-evidence/t1/results-final/`。

## 升级/中止条款

同 15.2.0 骨干，另加：xPack 12.2.0 各 release 均与 WCH 二进制特征不符（无法锚定基线）→ 报告证据，请求裁定是否接受"最接近 release + 差异驱动"的降级路线。

## 前提登记（premise register）

| 前提 | 证据 | 状态 |
|---|---|---|
| 构建体系为 xPack（路径 `/Users/mrs/Work/riscv-none-elf-gcc-xpack.git/`） | 报告 §9 strings | 已验证 |
| binutils 2.38 / newlib 4.2.0 / gdb 12.1 | 报告 §9 | 已验证 |
| 裸 `xw` → `xw1p0`（与 15.2.0 的 `xw2p0` 不同） | 报告 §9 | 已验证 |
| 32 位自定义指令编码与 15.2.0 逐字节相同 | 报告 §9 | 已验证 |
| 对应的 xPack release tag 可锚定 | `analysis/toolchain/phase4-baseline.md`：bundled v3 文件逐字相同，锚定 `v12.2.0-3` / `1737182b…` | 已验证（高置信） |
| triple 重命名之外无隐藏行为差异 | `phase4-literal-surface.md` 与最终诊断/行为/EVT gate；差异均有独立源码实现 | 已验证 |
| `.highcode` 参数语义 | 官方现场探针与 active/pristine `final-*-behavior-*`：参数仅接受 0/1、精确匹配 `.highcode`、总是禁止 inline，值 1 按源码声明名拆节 | 已验证 |
| M 与 Zmmul 接受面 | GCC 官方与自建均拒绝 M+Zmmul并逐字匹配诊断；GAS 两者均接受；独立 Zmmul 仅提供乘法能力 | 已验证 |
| vendor-X 接受面 | active/pristine 诊断矩阵：仅观测到的 `xw` 与 `x` 前缀被接受，`x` 接受任意版本后缀（`rv32ix`→`x1p0`、`rv32ix9p9`→`x9p9`、`rv32ix123`→`x123p0`，表项 `{"x",…,1,0,0}` 只提供未写版本时的默认），其他未知 X 扩展按官方诊断拒绝 | 已验证 |
| `wchsoftlib` ELF 标志 | active/pristine 8/8 对拍：`-wchsoftlib`/`--wchsoftlib` 幂等 OR `0x01000000`，与 relax 正交 | 已验证 |
