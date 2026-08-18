# phase-2 / phase-3 独立对抗性审计报告

审计者上下文从未持有执行 agent 的工作。所有结论均为本次现场落证，不采信 checklist 声称。
审计时间：2026-08-13。对象：`patches/15.2.0/`（gcc 3 + binutils 5）、`scripts/` harness、
`analysis/golden/15.2.0-darwin-arm64.tsv`、phase-2/3 证据树。

---

## 1. 覆盖矩阵

| # | 审计项 | 结论 | 证据指针（本次实跑） |
|---|---|---|---|
| 1 | Golden manifest 完整性 | **通过（高）** | 用官方 `ref/gcc/darwin-arm64/15.2.0` 重建 v3a-gpio / v4bc-pmp(XW) / v3f-gpio(`-gdwarf-4`)：56/56、56/56、51/51 行逐一 SHA256 命中 manifest，且无 manifest 外多余产物；另全部 9 工程的 `run1`+`run2` 残留（551×2 行）全部命中 |
| 2 | Harness 未被弱化 | **通过，含 1 处已裁定偏离（高）** | 通读 `scripts/evt-compare.sh`、`evt-golden.sh`、`build-toolchain-15.2.0.sh`；gate 判定/退出码/多余产物处理无缺口。偏离＝双侧注入 `-fdebug-prefix-map`（见发现 P2-1） |
| 3 | 8 个补丁可解释性 | **8/8 合格，其中 1 个附存疑项（高）** | 全文通读 + 逐条行为对拍官方二进制，判定表见 §3 |
| 4 | 缺陷保真行为探针 | **4/4 通过，逐字节相同（高）** | 见 §2.1；含 `non-standard111`、fast-interrupt、`rv32gcxw`、裸 `xw`→`xw2p0`、GAS `xw2p2` |
| 5 | 字面量面抽查 | **通过（高）** | `Configured with:` 1303 B `cmp=0`；`.comment` md5 `83a117f6…e9b3`（`-O2`/`-O2 -g` 各 32 B）；`SEARCH_DIR` 一致且钉死 `/Users/mrs/...`；`-print-multi-lib` 22 行 stdout+stderr `cmp=0`；`as`/`ld --version` 一致 |
| 6 | pristine 复放声称 | **通过（高）** | 8/8 `git patch-id --stable` 与 active commit 一致；按 series 顺序 apply 到 pristine release tree 后 `write-tree` 与 active HEAD tree **逐字相同**（gcc `3686efe41d20…`、binutils `612325559103…`），且与 cleanroom 记录值一致 |
| 7 | 边界完整性 | **通过（高）** | `ref/` 修改文件集 == `ref/wch-evt/patches/*.patch` 目标集（9/9，无多无少）；仓库根 HEAD `9930eb9…` 未新增 commit；harness 四文件 mtime 停留在 phase-1/2 |
| 8 | 指令覆盖审计 | **无重大偏离，2 项待声明** | 见 §5 |

---

## 2. 关键实测

### 2.1 缺陷保真探针（ours vs 官方，同一 cwd、同 epoch，stdout/stderr/产物全比）

| 探针 | 结果 |
|---|---|
| (a) `-march=rv32imac_xq` 诊断 | stdout/stderr 逐字节相同；含 `unsupported non-standard111 extension` 原字节 |
| (b) `interrupt("WCH-Interrupt-fast")` | `.s` 全文相同；`good` → `mret`、拼错 `WCH-Interrupt-Fast` → `ret`；**两侧 stderr 逐字节相同** |
| (c) `-march=rv32gcxw` | 退出 0，stderr 0 字节（静默），`-print-multi-directory` 两侧均为 `.` |
| (d) 裸 `xw` 属性 | `Tag_RISCV_arch: …_zca1p0_xw2p0`；整个 `.o` SHA256 两侧相同 `e2367b09…` |
| (d′) GAS mapping symbol | 官方 `as -march=rv32imac_xw` 落 `$x…_xw2p2`；**`xw2p2` 在官方二进制上确实存在**，非实现借口 |

> **对 (b) 的更正**：任务书与 `plans/gcc-15.2.0.md` 阶段 3 的措辞「拼错静默降级 `ret` **且无 warning**」与
> 官方二进制不符——官方**确实告警**（`argument to 'interrupt' attribute is not '"user"'…`）。
> `wch-gcc-toolchain-survey.md` §5.5 要点 3 的描述才是准确的（缺陷在于告警文案未把
> `WCH-Interrupt-fast` 列为合法值），补丁 gcc/0003 与之一致。属**设计文档措辞失准，非实现偏离**。

### 2.2 `-fdebug-prefix-map` 的实际遮蔽面（实测，非推断）

关闭 harness 注入后用 ours 重建 v3f-gpio：**24 个 gate 产物（23 个 `.o` + `.elf`）失配**，`.bin` 不受影响。
逐字符核对差异源：仅 DWARF 内嵌 sysroot 头文件路径的**工具链根前缀**
（ours `…/tmp/toolchain_15.2.0/riscv-gnu-toolchain/output` vs golden `…/tmp/golden/toolchain-current`），
后缀完全一致。含 `-gdwarf-4` 的工程只有 v3f-gpio 与 v3f2-gpio，故该机制承载约 **48/274（17.5%）** 的 gate 判定。

### 2.3 4 项 `.map` aux 残差的性质（实测）

把 ours 的工具链根路径串替换为官方根路径后，v3b-pioc / v3f-gpio / v3f2-gpio / v5f-fpu 四个 `.map`
与 golden **逐字节相同**。即：**残差 100% 是安装路径前缀，链接器行为零残差**。这是比 checklist 「如实保留」更强的正面结论。

---

## 3. 8 补丁可解释性判定

判定标准：上游惯用形态、可向上游 reviewer 解释、无裸字节块/不透明搬运/EVT 特判。
补丁改动的**非 testsuite 源码文件仅 8 个**，全部为 riscv 目标相关文件；无 `configure`、无 libgcc/newlib、无 harness。

| 补丁 | 判定 | 依据 |
|---|---|---|
| gcc/0001 accept-XW-march | **合格** | `riscv_ext_version_table` 增 1 行 `{"xw", …, 2, 0}`，其余行为由既有解析器涌现；含 2 个 dg 测试 |
| gcc/0002 non-standard111 | **合格** | 单词级诊断串修改 + 同步 2 个上游 dg 期望；官方二进制对拍逐字节命中，commit message 写明是刻意保真缺陷 |
| gcc/0003 fast-interrupt | **合格** | `machine_function` 新增标志 + `riscv_save_reg_p` / frame / rename hook 的常规 target hook 改动，5 个 dg 测试；`.s` 与官方逐字节相同 |
| binutils/0001 XW arch 接受 | **合格** | `riscv_supported_vendor_x_ext` 增 1 行 + gas 属性测试 |
| binutils/0002 8 条压缩编码 | **合格（附存疑项）** | MATCH/MASK、ENCODE/EXTRACT/VALID 宏、`INSN_CLASS_XW`、opcode 表项、`Xw*` 操作数解析——全为上游惯用形态，无查找表搬运。对拍官方：8 条编码、ordinary alias、`.attribute` 粘性、Zcb 优先级、Zcd 冲突、rvc 循环产物**全部逐字节相同**。**存疑：错误诊断文本与官方不符**（见 P2-2），且新增 `.l` 期望文件固化了我方文本 |
| binutils/0003 4 条 custom32 | **合格** | `funct5` 操作数（`OP_MASK_FUNCT5`）+ 4 个 opcode 表项 + 反汇编 `F5` 打印。改写 4 个上游 `x-thead-*/x-cv-*/mips-insns` `.d` 期望**经官方证实**：官方 objdump 对 `0x0010000b` 同样打印 `wexti zero,zero,ra,0`，即遮蔽行为是 WCH 事实而非迁就补丁 |
| binutils/0004 属性合成抑制 | **合格** | 源码仅 2 行：`strcmp (TARGET_VENDOR, "wch")` 门控 `riscv_write_out_attrs`。`TARGET_VENDOR` 是 binutils configure 既有宏（`gas/configure.ac:937`，本树 `config.h` 值为 `"wch"`），属上游惯用的目标条件化，**不是** EVT 工程/文件名特判。官方对拍：默认无属性段、`-march-attr` 为 no-op、显式 `.attribute` 原样保留——三种情形产物均 OBJ-SAME |
| binutils/0005 mapping `xw2p2` | **合格** | vendor 扩展表默认版本 2.0→2.2 一行；官方对拍确认裸 XW 的 mapping symbol 为 `xw2p2`，且 GCC 侧 `xw2p0` 因驱动显式写全串而不受影响 |

无任何补丁命中禁止形态 (a) 裸汇编/字节块、(b) 不透明搬运、(c) EVT 特判、(d) 讲不清依据。
8 个 commit message 均含差异现象首行 + 规格来源节号（正文引用 survey/isa-research 章节）。

---

## 4. 发现列表

严重度：P0 阻断 / P1 需修后放行 / P2 建议在 phase-4 开工前处置 / P3 记录级。

### P2

**P2-1 `-fdebug-prefix-map` 是编译期归一化，承载 17.5% 的 gate 判定**（置信度：高）
harness 双侧注入 `-fdebug-prefix-map=<各自工具链根>=<中性 symlink>`（`scripts/evt-compare.sh:114-131`、
`evt-golden.sh:119-153`）。这是 `plans/gcc-15.2.0.md` 硬约束 3「比较前不做任何 normalize」的编译期变体。
性质澄清：双侧对称、只重写工具链根前缀、后缀仍参与比对（§2.2 实测），**不掩盖任何编译器行为差异**；
但其后果是——「我方工具链装在自身路径下、与 MRS 官方工具链装在其自身路径下产出同字节」这一命题
**未被 gate 覆盖**。phase-1 prompt T6 预先把该方案列为两个候选裁定之一，manifest 头记 `(user-selected)`，
phase-1 checklist 记「用户裁定方案 1」。**用户裁定本身我无法落证**（会话记录不在可访问范围）→ 标 UNVERIFIED。
建议：主会话确认该裁定成立即可，并把「gate 不覆盖工具链安装根前缀」写进前提登记表。

**P2-2 GAS 诊断文本与官方不一致，且补丁自带的期望文件固化了我方文本**（置信度：高）
实测（`as -misa-spec=2.2`，两侧同参）：

| 输入 | 官方 | ours |
|---|---|---|
| `-march=rv32imac` + `c.lbu a0,0(a1)` | `Error: illegal operands \`c.lbu a0,0(a1)', extension \`zcb' required` | `Error: unrecognized opcode …` |
| `.option arch,+xw` + `c.lbu` | 同上（`illegal operands`） | 同上（`unrecognized opcode`） |
| `-march=rv32imac` + `c.lbusp a0,0(sp)` | `Error: illegal operands \`c.lbusp a0,0(sp)'` | `Error: unrecognized opcode \`c.lbusp a0,0(sp)'` |
| `-march=rv32imafdc_xw` + `c.fld` | `Error: illegal operands \`c.fld fa0,0(a1)'` | `…unrecognized opcode …, extension \`d' and \`c', or \`zcd' required` |

我方机制可定位：binutils/0002 在 `riscv_ip` 中对 `INSN_CLASS_XW` 走 `continue`，跳过了其后
`error.msg = _("illegal operands")` 的重置（补丁 hunk `@@ -2872,13 +2891,18 @@`）。**官方的实现机制未知**（未逆向），
此处只报实测差异与我方成因。
为什么算问题：phase-3 硬约束 3 规定「行为以 WCH 二进制为规格，包括缺陷」，而本项目已用 gcc/0002
把诊断文本（`non-standard111`）当作必须逐字保真的对象——同一标准下 GAS 诊断不应例外。
更关键的是补丁新增的 `xw-compressed-option-fail.l`、`xw-compressed-zcd-fail.l` 把**我方的**文本写成期望值，
属「用实现自身语义写断言」，绿测无法发现该漂移；且这套补丁将作为 12.2.0/8.2.0 的模板复用。
gate 字节不受影响（诊断只走 stderr），故为 P2 而非 P1。
checklist T2 行「Zcb/D 冲突矩阵…与官方对象逐字相同」——**对象**部分属实，**诊断**部分不成立。

**P2-3 独立 `as` 的默认 isa-spec 与官方不同**（置信度：高）
`as -march=rv32imac_xw`（不带 `-misa-spec`）：官方 mapping symbol 为
`$xrv32i2p0_m2p0_a2p0_c2p0_…_xw2p2`，ours 为 `$xrv32i**2p1**_m2p0_a**2p1**_c2p0_…_xw2p2`，`.o` 相差 2 字节。
定位：官方 `as` 默认 isa-spec = 2.2，ours = 20191213（上游默认）。显式 `-misa-spec=2.2/20190608/20191213`
三档下两侧产物**完全相同**——即补丁本身正确，差异纯来自 binutils configure：本树
`build-binutils/gas/config.h` 为 `/* #undef DEFAULT_RISCV_ISA_SPEC */`，而 `gas/configure.ac:648` 提供
`--with-isa-spec=[2.2|20190608|20191213]`。
gate 不受影响（gcc 驱动两侧都显式传 `-misa-spec=2.2`，已实测 `-###` 对拍相同），但任何直接用
`as` 汇编 `.S` 的下游用法都会暴露。
根因关联：phase-2 硬约束 5「binutils 不复原 configure argv」把 configure 派生的行为面留在了验收之外。
修法：`scripts/build-toolchain-15.2.0.sh` 的 binutils configure 增 `--with-isa-spec=2.2`（harness 改动，非补丁）。

**P2-4 全部交付物未入 git，无防篡改证据**（置信度：高）
`patches/`、`analysis/`、`scripts/evt-*.sh`、`plans/` 均为 untracked。manifest 理论上可被事后改写这一风险，
目前只由本次独立重建（审计项 1）锚定。建议验收同时提交，使后续阶段有 diff 基线。

### P3

- **P3-1** phase-3 期间在两棵源码树用了 4 次 `git commit --amend`（gcc 1 次、binutils 3 次，另 1 次 `reset`；
  证据：两树 `git reflog`）。产物无害（最终 series 与 active tree 完全对应，见审计项 6），
  但 checklist 与 phase-3 prompt 中均无 `amend` 字样，未声明。全局规则「未询问不 amend」针对用户仓库历史，
  此处是 gitignored 的补丁管理树，性质较轻。
- **P3-2** XW 压缩指令表项标 `xlen=32`；实测 `-march=rv64imac_xw` 时官方接受 `c.lbu` 而 ours 报错。
  目标是 rv32，实际影响为零，但属未对齐的行为面。
- **P3-3** `riscv_multi_subset_supports_ext` 新增的 `INSN_CLASS_XW` 分支不可达（XW 的门控在 `riscv_ip` 里
  提前 `continue`，从不设置 `missing_ext`）——死代码，上游 reviewer 会指出。
- **P3-4** `scripts/build-toolchain-15.2.0.sh:61` 的 `gcc_build_tflags` 是为 pristine 驱动无法解析 XW multilib
  而设的 phase-2 权宜；打完补丁后已无必要，但复放构建仍在传。属残留脚手架（已在脚本注释与 phase-2 checklist 声明）。
- **P3-5** binutils/0004 用 `#notarget: riscv*-wch-elf` 关掉了 30 个上游属性回归用例，
  该目标上上游属性行为不再被覆盖（新增 3 个 wch 用例只覆盖新行为）。
- **P3-6** `plans/gcc-15.2.0.md` 的「裸 `xw` 规范化为 `xw2p0`」不完整：GCC 侧 2p0、独立 GAS 侧 2p2，
  两者都经官方证实。`patches/15.2.0/README.md` 已正确记载，建议回填设计文档以免 12.2.0 沿用错误前提。
- **P3-7** `ref/Archive.zip`（1.85 GB）与 `ref/dec.tar` untracked 且未被 `.gitignore` 覆盖（mtime 早于 phase-2，
  非本阶段产生）；一次 `git add .` 即会入库。

### 正面确认（同样是审计结论）

- manifest 由官方工具链可独立重建：3 工程 163 行 + 9 工程 run1/run2 共 1102 行，零失配、零多余产物。
- 4 项 `.map` 残差经路径归一后逐字节相同 → 链接器行为零残差（比 checklist 的声称更强）。
- 补丁集可重放性最强形式已成立：ordered apply 到 pristine release tree 得到的 tree 哈希与 active HEAD tree **相等**。
- binutils/0003 改写上游 vendor 反汇编期望，经官方 objdump 证实为 WCH 事实。
- binutils/0004 的目标条件化用的是 binutils 既有 configure 宏，不是路径/文件名特判。
- 9 轮修补每轮都有独立全量 compare 且单调递增（24→24→81→198→218→221→256→271→274），无「攒补丁再验证」。

---

## 5. 指令覆盖审计（phase-2 / phase-3 硬约束逐条）

| 约束 | 判定 | 依据 |
|---|---|---|
| phase-2「只测量不打补丁」 | **遵守** | 两棵源码树在 phase-2 末保持 pristine（phase-3 首个 commit 前 HEAD 即 release commit，reflog 佐证）；`TFLAGS` 是 make 变量而非源码/configure 改动，且在 checklist T3 显式声明 |
| phase-3「修改范围仅限两棵源码树，不改 configure/注入库/harness」 | **遵守** | 补丁触及的非 testsuite 文件仅 8 个 riscv 目标文件；harness 四文件 mtime 均停在 phase-1/2；`ref/` 修改集 == apply.sh 目标集 |
| phase-3「单补丁单验证，不允许攒补丁」 | **遵守** | 9 个 round 目录各有 `evt-compare.status` + `evt-compare.log`，PASS 数单调递增 |
| phase-3「五轮规则」 | **遵守（未触发）** | 9 轮对应 8 个逻辑补丁 + 1 次 epilogue 修正，无同一差异项反复 5 轮的痕迹；未决问题 0 |
| phase-3「行为裁定顺序：不得以上游合理做法替代 WCH 实测」 | **遵守** | 探针 (b)/(d) 证明：设计文档措辞与官方二进制冲突时，实现跟的是二进制（见 §2.1 更正）；`xw2p2`、vendor 反汇编遮蔽等均先有官方实测 |
| `SOURCE_DATE_EPOCH=1767225600` | **遵守** | 三个 harness 脚本头部 `export`，不依赖环境；manifest 头记录同值 |
| 「不在仓库根 commit」 | **遵守** | 根 HEAD `9930eb9…`（commit time 2026-08-12T22:09:56，早于 phase-1 起始），与 `final/root-head.txt` 一致 |
| 「大输出 byte-cap / 不整读大二进制」 | **无法验证** | 属过程约束，证据树中无可判定痕迹 |
| debug-prefix-map 的用户裁定 | **UNVERIFIED** | phase-1 prompt T6 预先把该方案列为候选之一，manifest 头与 phase-1 checklist 均记「用户裁定」；裁定原文不在可访问范围 |
| phase-3「harness 修 bug 需在 checklist 单列」 | **遵守（无触发）** | phase-3 期间 harness 无改动 |

---

## 6. 本次审计对仓库的临时改动（均已还原）

- `tmp/golden/15.2.0/{v3a-gpio,v4bc-pmp,v3f-gpio}/work` 曾被就地重建（官方工具链 / 无 map 对照实验），
  改动前已备份、改动后已原样恢复；恢复后复核：v3a 56/56、v4bc 56/56、v3f 50 命中 + 1 个已知 `.map` 差异
  ——与审计前状态完全一致。
- `tmp/golden/toolchain-current` 只读未改；`/Users/mrs/riscv-gnu-toolchain` 未触碰；未运行 `evt-golden.sh`
  （其结尾会覆写 manifest）。
- 其余全部探针产物在会话 scratchpad 内，未进仓库。

---

## 7. 验收建议

**有条件放行。**

理由：唯一 gate（274/274 逐字节）已被独立锚定——manifest 可由官方工具链重建，补丁集可从 pristine 精确重放，
8 个补丁全部是上游惯用形态且逐条对拍过官方二进制行为，边界与字面量面现场复验全绿。P0/P1 计数为 0。

phase-4 开工前建议处置（不构成 gate 阻断，但都是硬约束 3 明确划进范围、且会随补丁模板复制到 12.2.0/8.2.0 的项）：

1. **P2-2**：修正 XW 门控路径的诊断文本以对齐官方，并把 `xw-compressed-option-fail.l` /
   `xw-compressed-zcd-fail.l` 的期望改成官方文本；若决定不修，请在设计文档明确豁免「GAS 诊断不纳入保真面」，
   避免与 gcc/0002 的标准自相矛盾。
2. **P2-3**：binutils configure 补 `--with-isa-spec=2.2`，并重跑一次全量 compare 确认无回归。
3. **P2-4**：验收时把 `patches/`、`analysis/`、`scripts/` 提交入库，建立防篡改基线。
4. **P2-1**：主会话确认 debug-prefix-map 裁定，并把「gate 不覆盖工具链安装根前缀」登记进前提表。
5. **P3-6**：回填 `plans/gcc-15.2.0.md` 的 GCC `xw2p0` / GAS `xw2p2` 双面事实，防止 12.2.0 沿用不完整前提。
