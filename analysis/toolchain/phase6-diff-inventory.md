# phase-6 S2 首份差异清单：vanilla 8.2.0 vs 官方 golden（darwin-arm64）

> 测量态：vanilla = gcc 树 830ea0167（tag v8.2.0-3.1 + multilib 基础设施 1abae7a36 + host 830ea0167，**零行为补丁**）、binutils 树 82b51c7b（纯净 tag）。golden = `analysis/golden/8.2.0-darwin-arm64.tsv`（8 工程 / 242 gate 产物 / v3c-led EXCLUDED）。比较：`evt-compare.sh 8.2.0`（转换器 delta 修复后，双侧 GCC8 拼法对称，证据 `evidence/s2/converter-gcc8/dialect-symmetry.txt`）。原始输出：`evidence/s2/evt-compare-vanilla-r2.stdout`。

## 0. 总量

`gate_pass=28 / gate_total=242 / gate_fail=214`。

- **v3a-gpio（rv32imac，全集唯一非 XW 工程）：28/28 gate 全 PASS + 28 aux 全 MATCH——非 XW 行为面在零行为补丁下已逐字节闭合**（宿主路线、官方库注入、链接行为、字面量环境全部就地验证；含 probe `.o` sha 命中 019c42bf…）。
- 其余 7 工程（v2ac/v3b/v3f/v3f2/v4bc/v4f/v5f）：214 gate 全 FAIL，形态一致——vanilla gcc 拒绝 GCC8 拼法 march（`unsupported ISA substring 'xw'`），无产物生成。首个错误样本：`tmp/golden/8.2.0/{v2ac-gpio,v4f-fpu}/logs/compare-build.log`（`-march=rv32ecxw` / `rv32imafcxw`）。

## 1. 差异簇清单（S3 工作项，按依赖序）

| 簇 | 面 | 现象（vanilla vs 官方） | 规格来源 | 预计落点 |
| --- | --- | --- | --- | --- |
| D1 | gcc `-march` XW 接受 | vanilla 拒 `rv32imacxw` 系（residual `'xw'`）；官方接受贴写、拒 `_xw`（residual `'_xw'`）、`rv32imacx` 可通过 | optsweep §4 + probes §1 + D1 spec-probe 21 条（【勘误】吃 `x[w]` 为无条件步骤、仅一次、rv32/64 共路，非「`c` 后」） | **【落点勘误 2026-08-17】实际 `gcc/common/config/riscv/riscv-common.c`（`riscv_parse_arch_string`）**，`patches/8.2.0/gcc/0003-…`；本列原写 `gcc/config/riscv/riscv.c`（预计值，旧值保留） |
| D2 | gas XW 助记符 | vanilla as 接受 `rv32imacxw` march（上游 x* passthrough 已有）但 8 条压缩助记符 `unrecognized opcode`；官方 8 条编码全（`c.lbu`=0x2188 系），门控 `xw`∧`c` | probes §5 + gating-correction + `ref/wch-isa-research` 编码事实 | `include/opcode/riscv-opc.h`、`opcodes/riscv-opc.c`、`gas/config/tc-riscv.c`（subset 门控），`patches/8.2.0/binutils/` |
| D3 | objdump `-M xw` | vanilla 无该子选项（`-M` 面={no-aliases,numeric}）；官方 ={no-aliases,numeric,xw}，内联 strcmp 链实现、大小写敏感，`--help` 78–79 行 WCH 自撰串逐字节面 | optsweep §2 + probes §5 反汇编行 | `opcodes/riscv-dis.c` + `binutils/objdump`(--help 文本)，`patches/8.2.0/binutils/` |
| D4 | gcc C 侧 WCH 面 | ①`WCH-Interrupt-fast` interrupt 属性（无栈帧 HPE 序言 + mret，不受 xw 门控）；②私有 param `highcode-gen-section-name`（207=206+1，=1 时 `.highcode`→`.highcode.<fn>`）——vanilla 两者皆无；当前被 D1 遮蔽，D1 落地后如 EVT 源用到即显形 | probes §7 + optsweep §3 | **【落点勘误 2026-08-17】实际 D4a = `gcc/config/riscv/riscv.c`（interrupt 属性，`patches/8.2.0/gcc/0004-…`）；D4b = `gcc/params.def` **加** `gcc/c-family/c-attribs.c`（`patches/8.2.0/gcc/0005-…`）**；本列原写 `riscv.c + params.def`，遗漏 `c-attribs.c`（旧值保留） |
| D5 | 诊断字节面 | `_xw` 拒绝文案 `unsupported ISA substring '_xw'`、`illegal operands`/`unrecognized opcode` 分野（xw∧c）、`-march=help`? （8.2.0 无）等——补丁落地后逐条与官方对拍 | probes 原始 stderr 全集 | 随 D1/D2 自然携带，验收对拍 |

> **【「预计落点」列的口径与勘误，2026-08-17；审计 P3】** 本表落盘于 S2，最后一列当时是**预测**，
> S3/S4 落地后从未回改。现按 `patches/8.2.0/` 的实际 `+++ b/` 目标逐条订正（旧值保留在各单元格内）。
> D2 的实际落点在预计之外多一个 `include/opcode/riscv.h`（并附 gas testsuite 用例）：
> `include/opcode/riscv-opc.h` + `include/opcode/riscv.h` + `opcodes/riscv-opc.c` + `gas/config/tc-riscv.c`。
> D3 的实际落点**只有** `opcodes/riscv-dis.c`（并附 5 个 `.d` 用例）——预计里的
> 「`binutils/objdump`（`--help` 文本）」不成立：`-M` 子选项的 `--help` 文本由
> `opcodes/riscv-dis.c` 的 `print_riscv_disassembler_options` 打印，不在 `binutils/` 下。
> D5「诊断字节面」无独立落点（随 D1/D2 携带），维持原样。

依赖：D1 先行（解锁 7 工程进入编译）→ D2（.o 级差异显形）→ D4（若 EVT 源触发）→ D3（不影响 gate 产物，影响 .lst 辅助面与工具面完备性）。multilib 面已在 S2 基础设施 commit 闭合（`-print-multi-lib` 23 行 IDENTICAL）。

## 2. 已消除的候选差异面（S2 就地关闭）

- 字面量面 9/9 IDENTICAL（configure 行/版本串/.comment/multilib/dumpspecs/SEARCH_DIR，`phase6-literal-surface.md`）。
- host 依赖版本疑虑（FP 常量折叠）：v3a 28 gate + probe `.o` 逐字节命中官方 → 就地消除。
- 转换器方言不对称：delta 修复 + 五 lane 对称证据（converter-gcc8/report.md §5）。
- 15.2.0 代隐藏选项机制（--w_priv_spec/--wchsoftlib）：8.2.0 官方本就不存在（optsweep 全量枚举=0），无需实现——**代差警觉成立，勿从新版移植**。

## 3. 方法学注记

- 失败路径 stderr 在 make -j2 下行序抖动（buildability §4）：诊断字节对拍一律单调用采集，构建日志不作字节 gate。
- `.riscv.attributes`：8.2.0 默认双侧均不产生（probes §3），EVT gate 产物无该节，不构成差异面；显式 `-march-attr` 行为对拍归 D2 验收探针。
