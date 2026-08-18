# Phase 2 首份差异清单（vanilla GCC 15.2.0）

测试日期：2026-08-13（Asia/Tokyo）。两侧均使用 Phase 1 的固定工程路径、
`SOURCE_DATE_EPOCH=1767225600` 和真实工具链根到
`tmp/golden/toolchain-current` 的 `-fdebug-prefix-map`。WCH 基准根为
`ref/gcc/darwin-arm64/15.2.0`，vanilla install 根为
`tmp/toolchain_15.2.0/riscv-gnu-toolchain/output`。原始 T5 证据位于
`tmp/toolchain_15.2.0/t5-evidence/`。

## 结论

官方工具链稳定性复验全绿：9 个工程、274/274 个 gate 和 277/277 个 aux
均与 Phase 1 manifest 相同。vanilla 工具链的全量 compare 则是 9/9
工程在生成首个对象前失败，汇总为 0/274 gate PASS、274 gate FAIL 和
277 个 aux missing。

首分歧不是代码生成或指令编码，而是 driver/multilib 接受面：现场复刻的
22 项 WCH multilib 表含 10 项 `xw`，pristine GCC 15.2.0 在选择 multilib
时解析全部候选并拒绝 `xw`。因此 XW 代表 `v4bc-pmp` 的用户
`-march=rv32imac_xw` 直接失败；甚至不含 XW 的 `v3a-gpio` 使用短写
`-march=rv32imac` 时，也会因遍历表中的 XW 候选失败。

完整流水线的首分歧止于 driver，但同一代表工程仍可作受控的下游隔离：
用 WCH GCC 按工程原始 flags 生成真实 EVT `.s`，再把这份未修改的同一输入
交给两侧 assembler。原始 `xw` 拼写先在 vanilla GAS 复现失败；随后只把
两侧 assembler 的该拼写显式化为 `xw2p0`。WCH 重组的三个对象仍逐字节
等于 Phase 1 golden；vanilla assembler 此时也成功消费输入，但没有把
3 条标准 load/store mnemonic
压缩成 XW 16-bit encoding。这样既保留主 compare 的真实 BUILD-FAIL，也
得到 3/3 个可复核的汇编器编码样例，没有把隔离结果冒充 full-pipeline PASS。

## Golden 稳定性复验

执行：

```text
scripts/evt-compare.sh 15.2.0 ref/gcc/darwin-arm64/15.2.0
```

退出码为 0，最终行为：

```text
SUMMARY gate_pass=274 gate_total=274 gate_fail=0 aux_match=277 aux_diff=0
```

这比“重建一个含 `-g` 的样本”更强：全量 9 工程均重建并逐 manifest
比较。其中含 `-gdwarf-4` 的 `v3f-gpio` 为 25/25 gate PASS。证据：
`golden-stability.stdout.tsv`、`golden-stability.stderr.log`（0 bytes）和
`golden-stability.status`。

## 全量 compare

执行：

```text
scripts/evt-compare.sh 15.2.0 tmp/toolchain_15.2.0/riscv-gnu-toolchain/output
```

退出码为 1，最终行为：

```text
SUMMARY gate_pass=0 gate_total=274 gate_fail=274 aux_match=0 aux_diff=277
```

下表的 274 个 gate FAIL 与 277 个 aux missing 是 9 次工程构建阻断按
manifest 展开后的结果，不代表发现了 551 个彼此独立的字节差异。compare
脚本在工程构建失败时把该工程实际产物集合视为空，并继续运行后续工程。

| 工程 | 状态 | gate PASS | manifest gate | gate FAIL | aux non-match | 首分歧 |
|---|---|---:|---:|---:|---:|---|
| `v2ac-gpio` | BUILD-FAIL | 0 | 24 | 24 | 24 | 用户 `rv32ec_zmmul_xw` 被拒绝 |
| `v3a-gpio` | BUILD-FAIL | 0 | 28 | 28 | 28 | 短写 `rv32imac` 触发 XW 候选解析 |
| `v3b-pioc` | BUILD-FAIL | 0 | 31 | 31 | 32 | 用户 `rv32imc_zba_zbb_zbc_zbs_xw` 被拒绝 |
| `v3c-led` | BUILD-FAIL | 0 | 32 | 32 | 32 | 用户 `rv32imc_zba_zbb_zbc_zbs_xw` 被拒绝 |
| `v3f-gpio` | BUILD-FAIL | 0 | 25 | 25 | 26 | 用户 `rv32imac_zba_zbb_zbc_zbs_xw` 被拒绝 |
| `v3f2-gpio` | BUILD-FAIL | 0 | 25 | 25 | 26 | 用户 `rv32imac_zba_zbb_zbc_zbs_xw` 被拒绝 |
| `v4bc-pmp` | BUILD-FAIL | 0 | 28 | 28 | 28 | 用户 `rv32imac_xw` 被拒绝 |
| `v4f-fpu` | BUILD-FAIL | 0 | 34 | 34 | 34 | 用户 `rv32imafc_xw` 被拒绝 |
| `v5f-fpu` | BUILD-FAIL | 0 | 47 | 47 | 47 | 用户 `rv32imafc_zba_zbb_zbc_zbs_xw` 被拒绝 |

逐工程完整快照在 `ours-state/<slug>/{work,logs}`；解析表为
`ours-project-summary.tsv`，其中 `failure_log` 是 compare 当时的 live 路径，
最终权威日志以冻结的 `ours-state/<slug>/logs/compare-build.log` 为准。每个
快照中的 `work/obj` 均为 0 个文件，证明不是在已有对象上挑选差异。

## XW 代表：`v4bc-pmp`

首条构建命令使用工程原始参数：

```text
-march=rv32imac_xw -mabi=ilp32 -msave-restore
```

driver 的第一条主诊断为：

```text
riscv32-wch-elf-gcc: error: '-march=rv32imac_xw': extension 'xw' starts with 'x' but is unsupported non-standard extension
```

随后还报告 multilib 表中其余 XW 候选，`make` 在
`obj/0000_ch32v20x_it.c.o` 与 `obj/0001_main.c.o` 退出 1。日志未出现
`cc1` 或 assembler 命令，快照中也没有任何对象；这与 driver 在子工具前
终止的控制流一致。因此完整流水线的首分歧止于 driver/march 接受面。
权威证据：
`ours-state/v4bc-pmp/logs/compare-build.log`。

### 指令级样例

主 compare 在对象前终止，故以下是明确标注的**下游 assembler 隔离**，不计作
golden gate。WCH GCC 使用工程原始
`-march=rv32imac_xw -mabi=ilp32 -msave-restore` 和相同 include/C flags，
从 `main.c`、`system_ch32v20x.c`、`ch32v20x_adc.c` 生成三份真实 `.s`；
每份输入只有一份，未按 assembler 改写。WCH project driver 的 `-v`
现场命令包含：

```text
--traditional-format
-march=rv32imac_xw
-march=rv32imac_zmmul_zaamo_zalrsc_zca_xw
-mabi=ilp32 -misa-spec=2.2
```

WCH GAS 对原始 argv 退出 0，vanilla GAS 则报 `x ISA extension 'xw' must be
set with the versions` 并退出 1。为越过这个已记录的拼写/接受面 blocker，
隔离实验在**两侧同时**只把上述两处 `xw` 改成 `xw2p0`，其余 argv 与 `.s`
原字节不变。此时六次（3 输入 × 2 assembler）汇编均退出 0。WCH 重组的
`main.o`、`system.o`、`adc.o` 与 Phase 1 golden 对象逐字节相同，证明输入
和重组路径对应真实工程产物。按生成 Makefile 的对象顺序扫描：`0000` 无
XW halfword，`0001` 与 `0002` 各一处，`0003`/`0004` 无，`0005` 的第一处
因而是第三处。下表严格列这**前三个 site**：

| # | 真实输入位置 / 函数 | 语义指令 | WCH encoding | vanilla encoding | 初步归因 |
|---:|---|---|---|---|---|
| 1 | `main.wch.s:412` / `main` | `lbu a5,0(a5)` | `.text.main+0xb0`: `0x239c`（16-bit `c.lbu x15,0(x15)`） | 同址 `0x0007c783`（32-bit `lbu`） | assembler XW 压缩编码 |
| 2 | `system.wch.s:220` / `SystemCoreClockUpdate` | `lbu a5,0(a5)` | `.text.SystemCoreClockUpdate+0x1b6`: `0x239c`（16-bit `c.lbu x15,0(x15)`） | 同址 `0x0007c783`（32-bit `lbu`） | assembler XW 压缩编码 |
| 3 | `adc.wch.s:117` / `ADC_Init` | `lbu a5,20(a5)` | `.text.ADC_Init+0xce`: `0x2bdc`（16-bit `c.lbu x15,20(x15)`） | 同址 `0x0147c783`（32-bit `lbu`） | assembler XW 压缩编码 |

三处 halfword（两种编码）的 XW mnemonic/operand 解码还逐项命中既有穷举映射
`ref/wch-isa-research/errata/06b-chipid-errata-evidence/controls/xw/`
`xw-source-encoding-map.tsv`。完整复现脚本为
`tmp/phase2-evidence/run-v4bc-two-as.sh`；状态、输入/对象 SHA256、完整
反汇编 diff 和样例表位于 `t5-evidence/drilldown/v4bc-pmp/`。因此结果是
**3/3**，同时仍明确保留 full pipeline 的首分歧是 march 解析失败。
`project-object-prefix-insn2.txt` 保存了上述对象前缀扫描，证明这里采用的是
26 个工程对象顺序中的前三个 site；第 1/2 处机器码相同但属于两个不同真实
函数位置，因此按任务书的“3 处”分别计数。

## 非 XW 诊断：`v3a-gpio`

### 原始工程参数

原始 `-march=rv32imac -mabi=ilp32` 仍在生成首个对象前失败。这里用户
march 本身没有 XW；失败来自 WCH multilib 表的 10 个 XW 候选。证据：
`ours-state/v3a-gpio/logs/compare-build.log`。这闭合了“不是只让 XW 工程
失败”的因果链。

### Canonical march 隔离诊断

为了越过该前置 blocker、观察其后的差异，诊断性地在**两侧同时**把短写
march 改为表内精确项：

```text
-march=rv32imac_zaamo_zalrsc -mabi=ilp32
```

这不是 golden gate，也没有被计入全量 compare 的 PASS。首先对
`ch32v10x_it.c` 做 `-S`，两侧汇编逐字相同；vanilla 额外警告两处
`interrupt("WCH-Interrupt-fast")` 参数不是上游支持的 user/supervisor/
machine，说明 frontend 属性接受面有差异，但该样本没有产生代码差异。

随后在同一固定 work 路径完整构建两次。产物集合相同，共 56 个文件：
51 MATCH、5 DIFF。不同项只有：

| 产物 | 结果 | 隔离结论 |
|---|---|---|
| `0003_core_riscv.c.o` | DIFF | 所有指令/重定位相同；vanilla 多 `priv_spec=1.11` 属性 |
| `0016_ch32v10x_pwr.c.o` | DIFF | 所有指令/重定位相同；vanilla 多 `priv_spec=1.11` 属性 |
| `0025_startup_ch32v10x.s.o` | DIFF | `.init/.vector/.text*` 相同；WCH 无 attributes 节，vanilla 有 |
| `GPIO_Toggle.elf` | DIFF | loadable 地址与机器码相同；attributes segment 大 4 bytes |
| `GPIO_Toggle.lst` | DIFF | 由 ELF attributes/container 差异传播 |

`GPIO_Toggle.bin` 与 `GPIO_Toggle.hex` 均逐字相同；bin 的 SHA256 为
`e4a993740741fc0fea01f6bb13d5772d1966b1f8fe2fd487ccbfa8375e773019`，
hex 的 SHA256 为
`4f64b08860ed2f40ba443bc25caf3ac41fc2e12f62af729697ec807fd87186ec`。
ELF 的 `.text/.init/.vector/.data` 以及全部 `.debug_*` 节原始字节也分别
相同；差异仅令后续非装载节的文件 offset 移动 4 bytes。

三份对象均用同一个官方 `riscv32-wch-elf-objdump/readelf` 下钻。去掉
objdump 的输入文件标题后，反汇编 diff 为空；重定位的语义字段 diff 为空；
所有 allocatable PROGBITS section 的 SHA256 两侧相同。完整小型证据集在
`tmp/phase2-evidence/agent-v3a-diff/`，构建汇总在
`t5-evidence/drilldown/v3a-gpio/canonical-summary.txt` 与
`canonical-artifacts.tsv`。

额外的 assembler 隔离复现实验把同一份汇编输入分别交给两侧 `as`，参数均为
`-misa-spec=2.2 -march=rv32imac_zaamo_zalrsc -mabi=ilp32`。WCH `as`
重组对象逐字节等于原 WCH 对象，vanilla `as` 重组对象逐字节等于原 vanilla
对象，三组均 MATCH。因此属性差异可归到 GAS 输出策略，而非 GCC 产生了
不同的 `.s`。证据为 `gas-isolation-summary.tsv` 和
`gas-reassembly-cmp.tsv`。三条可抽查的**相同编码**是
`30002573 csrr a0,mstatus`、`10500073 wfi`、
`30029073 csrw mstatus,t0`；它们用于证明没有把相同指令误报为差异，
不计入任务书要求的分歧样例。

## 差异分类

| 类别 | 判定 | 实例或未观察到的依据 |
|---|---|---|
| driver/march/multilib 接受面 | **已观察到，主阻断** | 9/9 工程在产物前失败；`v4bc-pmp` 直接拒绝 `rv32imac_xw`，`v3a-gpio` 因遍历 XW 候选失败 |
| 编译器代码生成 | 未观察到 | 主 compare 没有进入 cc1；canonical v3a 可比较的全部 `.text` 与 `-S` 样本相同 |
| 汇编器指令编码 | **已观察到** | 真实 v4bc `.s` 双 assembler 隔离中，按对象顺序的前三个 `lbu` site 被 WCH 压为 XW 16-bit，vanilla 保持标准 32-bit；3/3 样例见上 |
| `.riscv.attributes` | **已观察到** | vanilla C 对象/ELF 多 `Tag_RISCV_priv_spec=1`、minor `11`；startup 对象仅 vanilla 生成 attributes 节 |
| 链接布局 | 未观察到独立差异 | canonical v3a 的 loadable section 地址、LOAD headers 和内存镜像相同；RISCV_ATTRIBUTES header 的 FileSiz 如预期不同，且 attributes 大小造成非装载文件 offset 后移 |
| debug 路径来源 | 未观察到 | 主 compare 在 DWARF 前阻断；canonical v3a 的 `.debug_*` 原始节字节相同，Phase 1 的双侧 prefix-map 已生效 |

另有一项 frontend 属性诊断差异：vanilla 对
`WCH-Interrupt-fast` 给出两条 warning；当前选中的 handler 生成汇编相同，
故没有把 warning 误归为代码生成差异。

## 因果与边界

pristine 源码的关键链路为：driver 在 `gcc.cc` 调用
`set_multilib_dir()`；RISC-V `riscv_compute_multilib` 遍历配置生成的
multilib candidates，并由 `riscv_subset_list::parse` 解析各候选；未知
`xw` 在 `riscv-common.cc` 被报告为 unsupported。删除 XW candidates 会
破坏现场 `Configured with:` 与 22 行 multilib 表；提前修改 parser 则
违反 Phase 2“只测量、不打补丁”。构建脚本只给构建期临时 xgcc probes
传 canonical `TFLAGS` 以完成 `all-gcc/install-gcc`；安装后的 driver 仍
保持上述 pristine 行为，T5 已实证该 flags 未固化。

## 证据索引

- `tmp/toolchain_15.2.0/t5-evidence/context.txt`：manifest、epoch、symlink 与 compiler hash。
- `golden-stability.*`：官方全量稳定性复验。
- `ours-compare.*`、`ours-project-summary.tsv`：vanilla 全量 compare 与 9 工程汇总。
- `ours-state/<slug>/`：compare 后立即保存的每工程 work/log 快照。
- `drilldown/v4bc-pmp/`：真实 EVT `.s` 的双 assembler 状态、hash、golden 重组校验、完整反汇编 diff与 3 条编码样例。
- `tmp/phase2-evidence/run-v4bc-two-as.sh`：v4bc 双 assembler 隔离的可重放脚本。
- `drilldown/v3a-gpio/`：canonical 诊断的双侧原始产物、日志、hash 和集合比较。
- `tmp/phase2-evidence/agent-v3a-diff/`：三份差异对象的 section、attribute、relocation 与 disassembly 隔离证据。
- `tmp/toolchain_15.2.0/driver-blocker/`：最小 driver/multilib 复现。

## 边界说明

3 条指令样例来自同一 XW 代表的真实工程 `.s` 和双 assembler 隔离；它们
回答“march blocker 之后按工程对象顺序前三处指令的编码差异”。它们不改变、也不掩盖主
compare 的 9/9 BUILD-FAIL。canonical v3a 隔离仍只有 attributes 差异，
用于证明非 XW 路径没有被重复计作 XW 指令样例。
