# Phase 3b — GCC 15.2.0 全 EVT 逐字节扩展验收

## Verdict

**INVALID**（形式 verdict）。Stage A 本身已封口并在其运行内完整恢复 EVT，但 Stage B 准备时误删了三个既存 `.pyc`；其中两个已按 Stage-A SHA-256 逐字节恢复，`tools/__pycache__/fetch_wch_toolchain.cpython-314.pyc` 的 17,166 个原字节无法从现存源码重建。最终 EVT 因这一项不等于 Stage-A pre-state；最终复核还发现未归因的 repository immutable-scope 漂移。任一项都足以按 prompt 规则判 `INVALID`。

若只看工具链技术结果，本次完整覆盖明确为 **FAIL**：项目 byte gate 为 **1219/1298**，gate artifact 原字节为 **46891/47797**；79 个非绿项目全部完成四跑和 disposition，未发现 canonical nondeterminism 或 Stage-A 瞬态。

## 1. Scope 与受控方法

- Stage-A run ID：`20260812T184054.547562Z-22930-ledger-repair4`；marker schema/state/prompt/summary/handoff/inventory 均有效，marker 引用的 **418/418** 个文件 hash 独立复算通过。
- 现场 inventory：1298 个唯一 `.wvproj` 路径，九个 EVT 根、metadata/native-major/march/ABI 锚点全部闭合；未去重。
- canonical 与 ours 对同一项目始终轮流使用 Stage-A 原 `tmp/phase3b-work/projects/<id>/work` 绝对路径。项目私有 `toolchain-current` symlink 只切换真实工具链根。
- 固定环境：`LC_ALL=C`、`SOURCE_DATE_EPOCH=1767225600`、`TMPDIR=$PWD/tmp/phase3b-work/tmp`、`PYTHONDONTWRITEBYTECODE=1`；Stage B 串行 `WVPROJ_WORKERS=1`、`MAKE_JOBS=1`，并清除 prompt 指定的编译/SDK/DYLD 污染变量。
- converter 固定调用 `python3 -B tools/wvproj_to_make.py <wvproj> --output <same-work> --compiler-path <private-neutral-gcc> --gcc-major 15 --quiet`。
- build 固定调用 `make -f Makefile -f harness.mk -j1 COMPILER_PATH=<neutral-gcc> TOOLCHAIN_BIN=<neutral-bin> CROSS_PREFIX=riscv32-wch-elf- DEBUG_PREFIX_FROM=<real-root> DEBUG_PREFIX_TO=<neutral> all`；harness 只追加两条既有 debug-prefix-map 语义。
- 每次 build 后固定由该侧 `objcopy -O binary <elf> <same-basename>.bin` 生成 BIN；gate 原始文件未经 normalize。
- 对 Stage-A 79 个非绿项目依次执行 canonical run1/run2、ours run1/run2，共 316 轮；完整 argv/cwd/退出码在 `stage-b-command-ledger.tsv`。

### 工具身份

| side | real root | version | target | gcc SHA-256 |
|---|---|---|---|---|
| canonical | /Users/apple/Projects/openwch/ref/gcc/darwin-arm64/15.2.0 | riscv32-wch-elf-gcc (g5115c7e44-dirty) 15.2.0 | riscv32-wch-elf | 339104dfa2792244e90a3f44bd1f1ff3435917a7668ab83f33241d5d9c2c2829 |
| ours | /Users/apple/Projects/openwch/tmp/toolchain_15.2.0/riscv-gnu-toolchain/output | riscv32-wch-elf-gcc (g5115c7e44-dirty) 15.2.0 | riscv32-wch-elf | bb5f0f7752157e4919483756084278d63fdce19fc58fee51f9b55b5ede50c22e |

两侧 `gcc/g++/cpp/as/ld/objcopy/objdump` 及 `cc1/cc1plus/collect2/lto1`、libgcc/newlib/crt 的 wiring 均解析在各自 real root 内；Stage-A audit 的 `identity_errors=[]`。

## 2. 项目级结果

- canonical：1298/1298 conversion/build/bin PASS。
- ours：1289/1298 conversion/build/bin PASS；9 个稳定 build fail。
- 双侧 build pass：1289/1298；其中 1219 byte MATCH、70 byte DIFF。
- 79 个非绿项目四跑：canonical 79/79 PASS 且双跑确定；ours 70/79 PASS 且双跑确定，9/79 两次稳定失败；跨侧 79/79 仍 DIFF。`RECOVERED/FLAKY=0`，canonical/ours nondeterminism 均为 0。

### 按 EVT 根

| value | total | canonical_build_pass | ours_build_pass | both_build_pass | build_fail | byte_match | byte_diff |
|---|---|---|---|---|---|---|---|
| QingkeV2AC_CH32V00x | 71 | 71 | 71 | 71 | 0 | 70 | 1 |
| QingkeV3A_CH32V103 | 87 | 87 | 87 | 87 | 0 | 87 | 0 |
| QingkeV3B_CH32V205 | 135 | 135 | 135 | 135 | 0 | 133 | 2 |
| QingkeV3C_CH587_EVT | 95 | 95 | 91 | 91 | 4 | 41 | 50 |
| QingkeV3F_CH32X315 | 88 | 88 | 87 | 87 | 1 | 84 | 3 |
| QingkeV3F_CH32X315_EVT | 88 | 88 | 87 | 87 | 1 | 84 | 3 |
| QingkeV4BC_CH32V20x | 176 | 176 | 176 | 176 | 0 | 171 | 5 |
| QingkeV4F_CH32V30x | 168 | 168 | 167 | 167 | 1 | 165 | 2 |
| QingkeV5F_CH32H417EVT | 390 | 390 | 388 | 388 | 2 | 384 | 4 |

### 按 metadata format

| value | total | canonical_build_pass | ours_build_pass | both_build_pass | build_fail | byte_match | byte_diff |
|---|---|---|---|---|---|---|---|
| cproject-fallback | 480 | 480 | 479 | 479 | 1 | 475 | 4 |
| json | 818 | 818 | 810 | 810 | 8 | 744 | 66 |

### 按 native GCC major

| value | total | canonical_build_pass | ours_build_pass | both_build_pass | build_fail | byte_match | byte_diff |
|---|---|---|---|---|---|---|---|
| 8 | 430 | 430 | 429 | 429 | 1 | 424 | 5 |
| 12 | 707 | 707 | 699 | 699 | 8 | 641 | 58 |
| 15 | 161 | 161 | 161 | 161 | 0 | 154 | 7 |

### 按 march

| value | total | canonical_build_pass | ours_build_pass | both_build_pass | build_fail | byte_match | byte_diff |
|---|---|---|---|---|---|---|---|
| rv32ec_xw | 5 | 5 | 5 | 5 | 0 | 4 | 1 |
| rv32ec_zmmul_xw | 78 | 78 | 78 | 78 | 0 | 78 | 0 |
| rv32imac | 100 | 100 | 100 | 100 | 0 | 96 | 4 |
| rv32imac_xw | 331 | 331 | 330 | 330 | 1 | 327 | 3 |
| rv32imac_zba_zbb_zbc_zbs_xw | 531 | 531 | 527 | 527 | 4 | 521 | 6 |
| rv32imac_zba_zbb_zbc_zbs_xw_zve64x_zvl64b_zvbb | 16 | 16 | 16 | 16 | 0 | 12 | 4 |
| rv32imafc_xw | 2 | 2 | 2 | 2 | 0 | 2 | 0 |
| rv32imafc_zba_zbb_zbc_zbs_xw | 7 | 7 | 7 | 7 | 0 | 7 | 0 |
| rv32imc | 1 | 1 | 1 | 1 | 0 | 1 | 0 |
| rv32imc_zba_zbb_zbc_zbs | 16 | 16 | 16 | 16 | 0 | 15 | 1 |
| rv32imc_zba_zbb_zbc_zbs_xw | 211 | 211 | 207 | 207 | 4 | 156 | 51 |

### 按 ABI

| value | total | canonical_build_pass | ours_build_pass | both_build_pass | build_fail | byte_match | byte_diff |
|---|---|---|---|---|---|---|---|
| ilp32 | 1206 | 1206 | 1197 | 1197 | 9 | 1128 | 69 |
| ilp32e | 83 | 83 | 83 | 83 | 0 | 82 | 1 |
| ilp32f | 9 | 9 | 9 | 9 | 0 | 9 | 0 |

这里 `build_fail = total - both_build_pass`；`byte_diff` 只计双侧均成功但 gate 不同的项目，9 个 build fail 不被重复冒充 byte diff。

## 3. Artifact gate 与 aux

Gate path union 为 **47797**：intersection **47192**、canonical-only/MISSING **605**、ours-only/EXTRA **0**。项目 gate 文件集合相同 **1289/1298**；集合不同 9 项就是 ours build fail。

| class | union total | raw MATCH | raw DIFF | MISSING | EXTRA | raw-match rate |
|---|---|---|---|---|---|---|
| gate (.o/.elf/.bin) | 47797 | 46891 | 301 | 605 | 0 | 98.1045% |
| aux | 48603 | 47049 | 946 | 608 | 0 | 96.8027% |

Gate 的 301 个内容 DIFF 可复算为 165 个 `.o`、68 个 `.elf`、68 个 `.bin`；MISSING 来自 9 个 ours build fail。两个 BLE JumpIAP 工程虽各有 3 个 `.o` DIFF，但链接后的 ELF/BIN 原字节相同；其余 68 个双侧成功非绿工程的 ELF/BIN 均不同。aux 只作诊断，不改变 verdict。

Phase 3 的既有 9 工程 274/274 gate 结论未被改写；Stage-A 新 runner 的 canonical→ours representative self-check 亦为 raw MATCH。本阶段扩大后的 denominator 与工程集合不同，不能用 274/274 替代上述 47,797 项 gate。

## 4. 首分歧与根因簇

70 个双侧 build-pass 非绿工程共有 165 个 `.o` DIFF。每个对象均以记录中的真实 compile argv、同一 cwd、对应 neutral toolchain 重放 `-S`：**165/165 `.s` 原字节 DIFF，0 MATCH**，所以首分歧在 GCC 输出汇编之前。再统一用 canonical binutils 诊断 165 对对象：

- disassembly：165 DIFF；section header：165 DIFF；section path set：162 MATCH、3 DIFF；
- relocation：3 MATCH、162 DIFF；symbol：165 DIFF；
- `.riscv.attributes` 文本与原 section bytes：165/165 MATCH；`.comment` 原 bytes：165/165 MATCH。

这排除了统一的 GAS encoding、ELF attribute 或 comment 根因；原 gate 仍以未修改对象为准。

| cluster | classification | projects | direct .o | member-project gate nonmatch* | first divergence |
|---|---|---|---|---|---|
| RC01 | GCC-FRONTEND/DRIVER | 4 | 0 | 188 | canonical accepts --param=highcode-gen-section-name=1; ours exits 1 with an unrecognized-option error |
| RC02 | GCC-FRONTEND/DRIVER | 5 | 0 | 417 | ours treats an implicit function declaration as an error while canonical continues the same command |
| RC03 | GCC-CODEGEN | 45 | 90 | 225 | ours inlines RFIP_ReadRssi/BB_DevSetTxPower and eliminates tmos_proces_system_time; canonical retains calls/functions |
| RC04 | GCC-CODEGEN | 59 | 61 | 267 | canonical emits mret where ours emits ret for WCH-Interrupt-fast functions |
| RC05 | GCC-CODEGEN | 4 | 4 | 12 | ours emits vlenb plus v0-v31 spill/reload sequences that canonical omits |
| RC06 | GCC-CODEGEN | 3 | 3 | 14 | canonical and ours emit different .highcode section/function counts after different inlining/placement decisions |
| RC07 | GCC-CODEGEN | 5 | 5 | 15 | canonical uses a5 for the final address while ours reserves/uses t0 in the same non-returning handler |
| RC08 | GCC-CODEGEN | 1 | 1 | 4 | canonical begins with KEY_AND_LEDIO_Init while ours begins with Motor_Operation_Process |
| RC09 | GCC-CODEGEN | 1 | 1 | 7 | canonical first emits hw_sub_from.constprop.0 while ours first emits hw_reduce_mod_p |

`*` member-project gate nonmatch 对重叠簇是非加和指标；直接 `.o` 分配互斥且合计 165。完整 membership、根分布、最小复现、排除项与 follow-up 在 `root-cause-clusters.tsv`。每个非绿项目的逐项 disposition 在 `project-dispositions.tsv`，79/79 无遗漏。

### Build-fail 与 byte-diff 分离

- RC01：4 项由 ours driver 在首个 compile action 拒绝 `--param=highcode-gen-section-name=1`。
- RC02：5 项由 ours 的 implicit-function-declaration 严重度策略阻断；canonical 同命令继续并完成。
- RC03–RC09：70 个双侧成功项目的差异均已证明从 `.s` 开始，归 `GCC-CODEGEN`；不把后续 ELF/BIN 扩散误算成 linker/objcopy 独立根因。
- canonical 自身：1298/1298 Stage A build pass；79 个目标四跑均确定，无 canonical failure/nondeterminism。

## 5. 未决问题

机器表 `unresolved.tsv` 有 3 项：

1. U01：一份 sealed `.pyc` 原字节无法恢复，直接导致形式 verdict `INVALID`。
2. U02：RC03/RC06/RC08/RC09 的精确 canonical GCC pass/cost 源码差异尚未定位；流水线阶段与机械行为已高置信确定，但后续补丁前仍需缩减 testcase 和 pass dump。
3. U03：最终 immutable-scope 复核发现仓库 HEAD 漂移、两份 harness script hash 漂移和 20 个 root `patches/12.2.0/` 文件新增；事实明确，但现有证据不能归因其写入者。

## 6. 边界与恢复审计

- Stage A 自身 EVT pre/post/restored manifest 均为 `c11d4a0cf010cd62bfad9708a1c33897414b250caebb1a71802434b1cbc33d10`，其运行恢复成立。
- 四跑 Stage B pre/post manifest 均为 `cb21ca622dc4f4d83e0b97f98a3dbc9fd34283ddf64321b26f62fd0efc6d7d25`；assembly 诊断 pre/post 亦相同。两轮的 EVT git status/diff 原字节也各自前后相同。
- Stage-A raw artifact/config/log 共 214,933 个文件只改为 readonly，前后内容 hash 0 差异；Stage B 未覆盖 sealed raw evidence。
- EVT patch allowlist 仍精确为 `0001-pmp-select-ch32v20x-d8w.patch`、`0002-fix-eight-wvproj-builds.patch`、`apply.sh`，组合 hash `32fd538c307b2ef27b7d1908fe50e707a11ec8c37251ec5dd32c48ade82d1ddf`；锚定的 `patches/15.2.0/` 字节亦未漂移，Stage-B 分析没有生成 patch。root `patches/` 的未归因 `12.2.0/` 新增另列于下。
- Stage B 准备脚本误删 3 个 Stage-A pre-existing `.pyc`。`test_wvproj_to_make` 与 `wvproj_to_make` 两份已按原 SHA-256 精确恢复；`fetch_wch_toolchain` 一份仍缺失，且这是当前 EVT 相对 Stage-A pre-state 的唯一 delta。它不是 EVT source/metadata/patch，也未改变 1298 项 inventory 或有效 build baseline，但严格恢复 gate 不允许豁免。
- 最终全仓库复核还观察到**未归因的并发漂移**：root HEAD 从 `9930eb90043c53f5cd5ec6419b083a4e74ffb4a3` 变为 `db9bed6d6beb253dd7bea7cdd4fa8b0e51eb77f7`；`scripts/evt-golden.sh` 与 `scripts/evt-compare.sh` 当前 hash 不再等于 Stage-A post hash；root `patches/` 比 Stage-A post 多 20 个 `12.2.0/` 文件。EVT patch allowlist、converter、现有 harness、active GCC 15.2/binutils source 则仍与相应锚点一致。该漂移不被吸收为 Stage-B 输出，也进一步阻止严格边界 PASS。

两份脚本的 hash 漂移为：`{"scripts/evt-compare.sh":{"current":"601a334ab1bb0103d5634f6eed1ca636664473091df011d15db760c3c47aea2e","stage_a":"2a05dab22e842d9f18da5e82d39ac1012e2d71de58174d3fc1ef770386d97140"},"scripts/evt-golden.sh":{"current":"c77e8ac5ec98d38c129a566a8d0fdebb6ef455c2be603c0eaee6aec381336eb1","stage_a":"7b27377d1d137970b379e235fdcc20309464475974a32ff78fd883f9b8639ea7"}}`。root patch extra 清单与逐项 current-state 对账保存在 `final-audit.json`。

关于 prompt 要求的固定陈述：测试确实临时应用了 allowlist 中两个既有 EVT patch，每轮结束后也把所有 patch target 恢复到该轮测试前原字节；Stage-B 分析没有生成补丁。由于上述独立 `.pyc` 删除残差和未归因 workspace 漂移，不能无条件宣称“未留下 EVT 改动；没有创建或修改任何 patch”，这正是形式 verdict 必须为 `INVALID` 的边界原因。

## 7. 证据索引

- sealed Stage A：`tmp/phase3b-evidence/stage-a/STAGE_A_COMPLETE.json`
- handoff 独立审计：`tmp/phase3b-evidence/stage-b/stage-a-audit.json`
- 四跑：`repro-results.tsv`、`repro-artifacts.tsv`、`repro-comparisons.tsv`、`repro-summary.json`
- `.s` 定位：`assembly-diagnostics.tsv`、`assembly-diagnostics-summary.json`
- canonical-binutils 对象定位：`object-diagnostics.tsv`、`object-diagnostics-summary.json`
- 逐项目结论：`project-dispositions.tsv`
- 根因簇：`root-cause-clusters.tsv`
- 未决：`unresolved.tsv`
- 边界缺陷：`boundary-prepare.json`、`cache-recovery.json`、`stage-a-pre-drift.json`
- 最终需求/边界审计：`final-audit.json`、`completion-matrix.tsv`
