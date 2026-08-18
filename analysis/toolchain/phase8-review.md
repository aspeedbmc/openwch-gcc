# phase-8 终局独立对抗审计报告

审计者上下文从未持有任何 p8 执笔工作。一切声称按「可复算即自己复算」处理：本报告的每条结论要么来自我自己跑的命令，要么标注为「未能核验」。被审对象包括 `analysis/toolchain/phase8-closure.md` 本身——它是被审件，不是可信来源。

审计日期 2026-08-17。工作目录 `/Users/apple/Projects/openwch`。

**验收建议：有条件放行。** 5 项 P1 必须先闭合；其中 1 项（P1-1）是对官方的真实行为分歧，由 p8 本轮引入，且触发了协调器自己预注册的回退条款。

---

## 0. 结论摘要

| 项 | 值 |
| --- | --- |
| P0 阻断 | **0** |
| P1 修后放行 | **5** |
| P2 建议 | **12** |
| P3 记录 | **19** |
| 台账抽验覆盖率 | 8.2.0 **52/52**、12.2.0 **49/49**、15.2.0 **51/51** = **152/152（100%）**（要求 ≥1/3） |
| 独立锚定 | pristine 复放 **6/6** 命中、patch-id **39/39** 命中、quick comparator **3/3** 命中（274/274/242）、封存件 **30/31 项 OK**（12.2.0 有 1 项失败） |
| 技术实体结论 | 三版本补丁的**技术内容**经得起独立复算；缺陷集中在**交付面元数据**（README/台账/封存）与**一处前提未穷举的 B 级删除** |

---

## 1. 覆盖矩阵

### 1.1 我亲自复算的项（未采信任何报告转述）

| # | 项 | 方法 | 结果 |
| --- | --- | --- | --- |
| 1 | 三版本 pristine 复放 | 全新 scratch：`git archive <root>` → `tar -x` → `git init` → `git apply --index` 逐片 → `write-tree`（不碰镜像） | **6/6 逐位命中**（见 §2.1） |
| 2 | patch-id 台账 | `git patch-id --stable` 重算 39 片 | **39/39** 与 `patch-id.tsv` 相同 |
| 3 | quick comparator | `scripts/evt-compare.sh <v> ref/gcc/darwin-arm64/<v>` ×3（对官方包） | 274/274、274/274、242/242，`gate_fail=0`；symlink 前后值均为基线 |
| 4 | 封存件自验 | `shasum -a 256 -c` ×3 | 8.2.0 **10/10 OK**、15.2.0 **20/20 OK**、12.2.0 **389 OK / 1 FAILED** |
| 5 | patches 内容哈希 | `run-round-end.sh:71-72` 同算法重算 ×3 | 三值与 `s3/sealed/manifest.txt` 全同 |
| 6 | 封存后 mtime 漂移扫描 | `stat` 全量 `patches/**` vs 各封存时点 | **零漂移**（8.2.0 seal 15:16:06 > README 15:15:59；12.2.0 15:56:40 > tsv 15:56:35；15.2.0 17:55:32 > README 11:39:57） |
| 7 | 守卫终态 | `readlink` ×3、六镜像 `rev-parse` + `status --porcelain` | 全部等于 `guard-baseline.tsv`；六镜像 dirty=0，HEAD tree = 各轮终态 |
| 8 | install 树不变性（TS:32 第三条腿） | mtime 扫描 + 清单重验 | 15.2.0 / 12.2.0 零新文件；8.2.0 活体 install 对 `install-manifest.post-rebuild.txt` **2261/2261 OK** |
| 9 | 12.2.0 Q-01 `--w_priv_spec` | 官方 vs 我方 install 树，4 模式 | 产物**逐字节相同**；`Tag_RISCV_priv_spec 1/minor 11`；`=0` 拒收；`--w-priv-spec` unrecognized；`--help` 差异仅 argv[0] |
| 10 | 12.2.0 Q-02 `objdump -M xw` | 官方 vs 我方，含 P8-F2 场景 | `--help` RISC-V 段 **diff 为空**；默认/`-M xw`/`-M xw,no-aliases` 三模式解码全同；纯 D+C 对象 `2188` 两侧同解为 `lbu a0,0(a1)`，`unreachable INSN_CLASS` **0 次** |
| 11 | 三版本 `riscv.h` 寄存器表前提 | 实读源码 | `CALL_USED_REGISTERS` ra = 0/0/**1**（:254/:314/:340）；`FIXED_REGISTERS` ra = 0/0/**1**（:240/:300/:322） |
| 12 | `-fcall-saved-ra` 三侧/五工具链对照 | 实跑（见 §3 P1-1） | **发现 15.2.0 对官方的真实分歧** |
| 13 | 8.2.0 探针集 | `probes.p8.tsv` 原始行表重数 | 834 = 793 IDENTICAL + 41 EXCLUDED；`probes.p8.summary` 与 `runJ` **逐字节相同** |
| 14 | 8.2.0 全量分区 | 独立解析 `analysis/golden/8.2.0-darwin-arm64-full.tsv` | 43969 行 = `gate` 42285/1170 工程 + `gate-link-only` 1684/33 工程，共 1203 工程 |
| 15 | 15.2.0 折叠位点树 | 镜像对象库 `rev-parse` | fold/gcc → `0785aaf0`（=折叠前冻结值）、fold/binutils → `bda204ba`（同）⇒ **折叠证明不改终态源码** |
| 16 | 15.2.0 byte-classification | 重数 | 8 MSG-ONLY / 2 HDR-ONLY / 6 CODE；patch-id 6 变 10 不变 |
| 17 | SR-02 判据列确定性 | 自写 Python 对 `sr02-run1-matrix.tsv` vs `sr02-lto/stream-diffs/lto-dump-matrix.tsv` 逐 cell 比 | `rc` 26/392、**`stdout_sha256`/`stderr_sha256`/`stdout_size` 各 26/392**、`debug_begin_stmt` 0/392 |
| 18 | DEC:74 [CORRECTION] 前提 | 实读 `build-toolchain-12.2.0.sh:192-195` | 四条顶层无条件 `safe_remove`；`grep -c ccache` = 0 ⇒ **该更正属实** |
| 19 | 15.2.0 双平台全量 gate | 读 `gate*/…/summary.json` 原始件 | 两平台各 `gate_match=47797, diff/missing/extra=0`，1298 工程，`normalization=NONE`，`ours=…ours-p8final-frozen` |
| 20 | 12.2.0 轮末原始件 | 读 `run-20260817T065202Z/` | `p2-summary` 274/274/0、`gas.sum` `# of expected passes 210`、`p5.log` `compared=162 differing=0` |

### 1.2 台账抽验覆盖

| 版本 | 数据行 | 抽验 | class=B | KEEP 族 / EXEMPTED / OUT-OF-SCOPE / QUESTION / STILL-PRESENT |
| --- | --- | --- | --- | --- |
| 8.2.0 | 52 | 52（100%） | 7/7 | 6/6（KEEP 5 + EXEMPTED 1；其余三类本表 0 行） |
| 12.2.0 | 49 | 49（100%） | 8/8 | 15/15（KEEP 族 7 + OUT-OF-SCOPE 2 + QUESTION 5 + …） |
| 15.2.0 | 51 | 51（100%） | 10/10 | 48/48（status 列 33 + final_status 列 15） |

---

## 2. 独立锚定结果

### 2.1 pristine 复放（clean-room，6/6）

不使用项目自带的任何复放脚本。方法：`git -C <mirror> archive <root-commit> | tar -x -C /tmp/...` → `git init` → `git add -A` → `write-tree`（先验证等于镜像 root tree）→ 按 `series` 顺序 `git apply --index` → `write-tree`。脚本存于 `/Users/apple/Projects/openwch/tmp/phase8-evidence/review-s4/replay.sh`。

| 版本·组件 | 基点（= README 自述基点） | 我算出的终态 | 期望值 | 判定 |
| --- | --- | --- | --- | --- |
| 8.2.0 gcc | `0c7a874f0b6f…` | `97b81fa8f52fa7037045f428f41e37099ba16fdf` | 同 | ✅ |
| 8.2.0 binutils | `82b51c7b5087…` | `8d0d7da3c3b3376d07ef0f76f0f00b6b913dcf40` | 同 | ✅ |
| 12.2.0 gcc | `3280576e992d…` | `af74531c952c78bab9089ee93af50e3a7fe992ea` | 同 | ✅ |
| 12.2.0 binutils | `dc5b5e8935f9…` | `cb7b9681acb401984e98a5e5172bbdfde09eb62e` | 同 | ✅ |
| 15.2.0 gcc | `5115c7e447fc…` | `8fe2bd16714dcce1d0573ccb7efaf0189c889d8b` | 同 | ✅ |
| 15.2.0 binutils | `2bc7af1ff773…` | `22849f4548da2e1055a71b95cd78ddef3cbb5625` | 同 | ✅ |

**这条锚定是本次审计最强的一条**：它同时证明了补丁集完整、series 顺序正确、三版本终态与镜像一致，且不依赖项目的任何机器。它也是 P1-2 的直接证伪工具（8.2.0 README 断言的 `3260ccd8…` 与此不符）。

### 2.2 quick comparator（3/3）

| 版本 | 命令 | 结果 | 墙钟 | `toolchain-current` 前 → 后 |
| --- | --- | --- | --- | --- |
| 15.2.0 | `evt-compare.sh 15.2.0 ref/gcc/darwin-arm64/15.2.0` | `gate_pass=274 gate_total=274 gate_fail=0 aux_diff=0` | 3.4s | `ours-v3.0-frozen` → `ours-v3.0-frozen` |
| 12.2.0 | 同式 | `gate_pass=274 gate_total=274 gate_fail=0 aux_diff=0` | 3.1s | 同上，已复位 |
| 8.2.0 | 同式 | `gate_pass=242 gate_total=242 gate_fail=0 aux_diff=0` | 7.4s | 同上，已复位 |

**口径限制（重要）**：按任务书要求对**官方包**跑。官方-vs-golden 只锚定 golden manifest + harness + EVT 源码树三者未漂移，**不构成对我方工具链 gate 的独立重测**。我方侧 gate 数字仍只有轮末批一次证据（见 §6 未能核验项 1）。

---

## 3. 发现列表（按严重度；不过滤）

### P1-1 `[P1][置信度 高]` 15.2.0 的 B 级删除引入了对官方的真实行为分歧，「恒真」前提被实测证伪

**位置**：`patches/15.2.0/gcc/0003-RISC-V-match-WCH-fast-interrupt-EVT-frames.patch:126-133`（终态树 `riscv.cc:7513-7519`）
**连带错误断言**：`analysis/toolchain/phase8-closure.md:414`、`tmp/phase8-evidence/15.2.0/round-report.md:3` 与 `:86`、`patches/15.2.0/README.md:247` 与 `:261-263`、`DECISIONS.md:63`

被审声称：15.2.0 中 ra 同时位于 `FIXED_REGISTERS` 与 `CALL_USED_REGISTERS` ⇒ `call_used_or_fixed_reg_p(1)` **恒真** ⇒ `|| regno == RETURN_ADDR_REGNUM` 恒被前项吸收 ⇒ 可删。

我先证实了两条静态前提（`riscv.h:322` FIXED ra=1、`:340` CALL_USED ra=1，`call_used_or_fixed_reg_p` = `fixed_regs[] || call_used_regs[]`，`hard-reg-set.h:523`）。**但「恒真」要求穷举所有能改写这两张表的位点，而该穷举没有做**：`gcc/reginfo.cc:661 fix_register()` 只对 `STACK_POINTER_REGNUM` / `HARD_FRAME_POINTER_REGNUM` / `FRAME_POINTER_REGNUM` 设防（`:674-678`），其余寄存器一律执行 `fixed_regs[i] = fixed`（`:720`）与 `call_used_regs[i] = call_used`（`:723/725`）。ra 不在设防名单内，故 `-fcall-saved-ra` 可把两者同时清零。

**实测复现**（我自己跑，非引用）。源码：`__attribute__((interrupt("WCH-Interrupt-fast")))` 的非叶处理函数调用 `sink()`；命令 `-Os -march=rv32imac -mabi=ilp32 -fcall-saved-ra -S`：

| 侧 | 生成体 |
| --- | --- |
| 官方 `ref/gcc/darwin-arm64/15.2.0` | `call sink` / `mret` — ra **不**软件保存 |
| **我方 p8 终态** `tmp/phase3h-evidence/ours-p8final-frozen` | `addi sp,sp,-16` / `sw ra,12(sp)` / `call sink` / `lw ra,12(sp)` / `addi sp,sp,16` / `mret` — **分歧** |
| 我方清理前 `tmp/phase3h-evidence/ours-v3h-final-frozen` | `call sink` / `mret` — 与官方相同 |

⇒ **分歧由 p8 本轮引入**。`-ffixed-ra` 与 `-fcall-used-ra` 两侧仍相同，只有 `-fcall-saved-ra` 触发。

**跨版本对照（我加做的控制组，反证该析取项并非死代码）**：12.2.0 与 8.2.0 保留了该析取项，两版在 `-fcall-saved-ra` 下官方与我方**均为** `call sink` / `mret`，零分歧。即：该析取项正是各版本在该 flag 下维持官方一致的那一行；12.2.0 的 KEEP 判定正确，15.2.0 的删除判定错误。

**为什么必须是 P1**：
1. `DECISIONS.md:63` 给这条删除挂的验收条件原文是「重建字节断言 + 三侧探针护栏，**异动即回退转 KEEP+注释**」。321 项探针面不含任何 `-f{call-saved,call-used,fixed}-*` 输入，护栏对该分歧**零判别力**；预注册的回退条款现已被触发。
2. 「零行为改动」「It makes no behavioural change.」是**已写入交付 README 并已封存**的错误断言（README 在 `phase8-15.2.0-SHA256SUMS` 内）。
3. 这属于「前提被断言而非被测量」的缺陷类——正是任务书硬约束 1 与本阶段自记教训（closure §5.2、§9）指向的同一族。

**gate 影响：中性（我已独立验证）**。`grep -rl -- "-fcall-saved\|-fcall-used\|-ffixed-" ref/wch-evt scripts tests` = **0 命中**，故 274/47797/43969 与全部封存 gate 数字不受影响。但 EVT 树内 **1654** 个文件使用 `WCH-Interrupt-fast`，受影响的函数类别本身是主力路径。

**修法（建议 ①）**：
1. **回退**：恢复 `|| regno == RETURN_ADDR_REGNUM`，台账 `ledger.tsv:14` 改判 `KEEP`，并在源码写明「不依赖 `call_used_or_fixed_reg_p` 恒真——`-fcall-saved-ra` 可清 `fixed_regs[1]`/`call_used_regs[1]`」。这正是 DEC:63 预注册的路径，且使三版本形态一致。
2. 保留删除，但把全部「恒真」表述改为有界表述，把该 flag 下的分歧写入 README「Known deviations」（与 xlen=32 并列），并删除 `README.md:247` 的 "makes no behavioural change"。
3. 把三侧探针面扩到 `-fcall-saved-ra` 后重跑——结果必然失配，等价于回到 ①。

---

### P1-2 `[P1][置信度 高]` `patches/8.2.0/README.md` 的一键复现脚本断言了错误的树，且与同一交付内的封存件头自相矛盾

**位置**：`patches/8.2.0/README.md:149-152`

该 README 的 Apply 段（`:141-147`）对**当前** `patches/8.2.0/series` 逐片 `git am`，随后断言：

```
test "$(git -C "$tree/gcc" rev-parse HEAD^{tree})" = \
  3260ccd8722ba1dc938ad188fa2cafd2b61b5423
```

**实测**：该脚本自述的基点（`:136-137` 的 gcc HEAD `0c7a874f0b6f…`）正是我复放所用的镜像 root commit；我从该基点应用当前 series 得到的 gcc 终态是 **`97b81fa8f52fa7037045f428f41e37099ba16fdf`**。`3260ccd8…` 是 **p8 进场值**（`guard-baseline.tsv`），已被 U2 的 `gcc/system.h` 注释同步作废。

同一交付内的三处自证它是错的：
- 封存件头 `tmp/phase8-evidence/8.2.0/phase8-8.2.0-SHA256SUMS:5` 写 `# gcc source tree at seal time: 97b81fa8f52fa7037045f428f41e37099ba16fdf`；
- 执行者自己的 `replay-check-u2.log` 与 `s3/replay.log` 两处 `ASSERT gcc 97b81fa8… PASS`，并注明 `delta vs pre-p8 gcc tree 3260ccd8… : only gcc/system.h blob f9f38c41 -> 33f78489`；
- README 自身 `:50-56` 承认 `host/0002` 的 diff「genuinely grew by those two comment lines」。

`README.md:155-156` 还把这两个值描述为「the trees the **phase-6** gate artifacts were built from」——即措辞本身就是从 phase-6 原样留下的。全文 `grep 97b81fa8` = **0 命中**。

**失败场景**：任何按交付 README 复现的人，在正确复现之后被 `test` 判为失败并中止。
**加重情节**：README 已被 `phase8-8.2.0-SHA256SUMS`（`23661604a2d2…`）封存，错值随封存件一起交付。
**修法**：`:150` 改为 `97b81fa8f52fa7037045f428f41e37099ba16fdf`；`:155-156` 措辞改为「phase-8 终态树」；重签封存件。

---

### P1-3 `[P1][置信度 高]` `patches/12.2.0/README.md` 记录的 binutils 终态指向**已废弃的历史**

**位置**：`patches/12.2.0/README.md:106-112`

README 记 Phase-8 终态为 gcc HEAD `9731e5ee…`（tree `af74531c…`，**正确**）与 binutils HEAD `d3236caead2f…`（tree `2c501e752f0b…`）。

**实测**：真正的终态是 binutils HEAD `dfb77909835d602e540ee245392d12fa16e80c81` / tree `cb7b9681acb401984e98a5e5172bbdfde09eb62e`（我 `rev-parse` 镜像；与 RR12 §0、`s3/sealed/manifest.txt`、closure §2.3 一致）。而

```
git merge-base --is-ancestor d3236caead2f… HEAD  →  NO — 已废弃历史
```

`d3236cae` 是 P8-F2 修复折入前的中间态，被 DEC:75 的历史重演取代。按 README 复现者会得到一棵**缺 F2 门 2、缺三个 priv-attr 用例**的树，其 GAS 套件退回 `PASS=208 FAIL=2`——正是 `run-20260817T063207Z` 的故障态。

**为什么没被拦下**：轮末 P7 只回填了 `scripts/export-patches-12.2.0.sh` 的四行常量（`p7.log` 的 diff 恰为 `gcc_head`/`gcc_tree`/`binutils_head`/`binutils_tree` 八行），**未触 README**。CL S3 对 12.2.0 明列「README/plans 回填与补丁终态一致」，RR12 §7 却写「未决：无」。该错值同样已进入 `s3/sealed/manifest.txt` 的内容哈希。
**修法**：`:108-110` 改为 `dfb77909…` / `cb7b9681…`，重算内容哈希并重签。

---

### P1-4 `[P1][置信度 高]` 12.2.0 台账根本未回填终态，而 closure 断言其「已回填」；同一句对 15.2.0 的断言又是过期的

**位置**：`analysis/toolchain/phase8-closure.md:642-645`

closure 写：「8.2.0（mtime 15:16）与 12.2.0（15:53）**已回填**，15.2.0 **待补**」。两半都不成立：

| 版本 | 表头 | 我数出的 status 分布 | 判定 |
| --- | --- | --- | --- |
| 8.2.0 | 7 列（status 列原地扩词表） | ALREADY-FIXED 28 / RESOLVED-U1 8 / RULED 6 / KEEP 5 / RESOLVED-S3 2 / RESOLVED-U2 1 / RESOLVED-U3 1 / EXEMPTED 1，**STILL-PRESENT = 0** | 已回填 ✅ |
| **12.2.0** | **7 列，无任何 final 列** | **STILL-PRESENT 24** / CONFIRMED-OK 7 / **QUESTION 5** / KEEP-NO-TOUCH 5 / OUT-OF-SCOPE 2 / ALREADY-FIXED 2 / REOPENED-FIXED 1 / N-A 1 / KEEP-UNPROBED 1 / KEEP 1 | **未回填** ❌ |
| 15.2.0 | **9 列**（新增 `final_status`/`final_evidence`） | 51/51 行**全部**有终态，无空值 | 已回填（18:17，晚于 closure 的 18:14）✅ |

closure 用 **mtime** 当作内容已回填的证据——而 12.2.0 那次 15:53 的编辑只改了 row38 一行。12.2.0 的 49 行里 23 行实际早已执行完毕（我逐条对现文核过），5 个 QUESTION 的 Q-01/Q-02/Q-03 均已裁定落地（DEC:66/70/75），只是台账没写回去。

**失败场景**：S4 终签按 TS:59/CL:72 核 12.2.0 交付面，依 closure 直接勾过；而台账原文读起来是「24 项未处置、5 项未裁定」，与 RR12 §1「M 9+6+3 / C 5+7+2 / B 6 全部落地」正面冲突。
**附带**：三份台账三种口径（原地扩词表 / 加两列 / 未办），互不可比；且 TS:59 原文要求的判定词是 `EXPLAINED` / `KEEP-UNPROBED`，15.2.0 用的是 `RESOLVED-U-*` 体系，**`EXPLAINED` 一次都没出现**——语义可论证等价，字面需协调器明确接受。
**修法**：12.2.0 台账补回填并统一三版本口径；closure §10.3-1 整条改写（15.2.0 已闭合、12.2.0 待补）。

---

### P1-5 `[P1][置信度 高]` 12.2.0 封存件自验失败 1/390，而 S4 终签的证据陈述把它整个略去

**位置**：`tmp/phase8-evidence/12.2.0/s3/sealed/run-files.sha256`；`DECISIONS.md:78` ①

我跑 `shasum -a 256 -c`：**389 OK / 1 FAILED**，失败项为 `run-20260817T065202Z/driver.log`。

根因我从源码证明，不是猜测：`s3/run-round-end.sh:65` 用 `exec > >(tee -a "$RUN/driver.log") 2>&1` 把驱动全部输出续写进该日志，而 `:136` 的 `find "$RUN" -type f | … | xargs shasum -a 256` 把**仍在增长的该日志**一并入账——自指封存。日志尾部确实还有封存步骤之后写入的 `ROUND-END: ALL PASS` 等行。

**问题不在这一个文件的完整性**（内容可读、差异可完全解释、与任何 gate 数据无关），**而在于 S4 终签的证据陈述**：`DECISIONS.md:78` ① 把终签建立在「8.2.0 封存自验 10/10 OK、15.2.0 封存自验 20/20 OK」上，**12.2.0 的封存自验既未列出也从未成立**。同时 DEC:62 Q3 裁定「p8 轮末自起封存件 `phase8-<版本>-SHA256SUMS`（含 README 终态）」——12.2.0 从未产出该形态的交付面封存件，只有 run 文件哈希 + 一个卷起的目录内容哈希。

这与阶段自记的 P2-9「先签后改」属同一族，而该族被 closure §2.4 宣布已由 8.2.0 的 `seal.sh` 次序纪律闭合。
**修法**：封存时排除 `driver.log`（或先落盘再哈希）；为 12.2.0 补一份 `phase8-12.2.0-SHA256SUMS` 交付面封存件；DEC:78 ① 补记 12.2.0 的实际证据形态。

---

### P2 级

**P2-1 `[P2][置信度 高]` SR-02 的 PASS 建立在**测量后**更换判据列之上，且不确定性范围比报告所述更大**
`s3/darwin-results.resume2.tsv` 记录 SR-02 在预注册的 `rc` 列下 **FAIL**（历史侧 19 处不同、相对 OURS-3H 漂移 7 处）；随后判据列改为 `debug_begin_stmt` 并重判 PASS。TS:28 硬约束 7 要求「断言在测量前预注册」。
缓解是实质性的：换列有确定性测量支撑（DEV-P8-15-05），且 DEV-05/06 与 closure §9 如实披露。**但我自己重算两次 run 的矩阵后发现不确定性不止于 `rc`**：`rc`、`stdout_sha256`、`stderr_sha256`、`stdout_size` **各 26/392 且是同一批 cell**，`debug_begin_stmt` 0/392。报告只陈述了 `rc` 不稳。即：被观测对象在 6.6% 的 cell 上整体不确定，所选判据列之所以稳定，是因为它是一个对该不确定性取平均的粗粒度派生标记，而它的稳定性又恰恰是在**同一批 n=2** 上确立的（选择效应）。RR15 §2 与 closure §3.3 把「历史侧对 3h 封存 288 cell 0 不同」作为内建 sanity 通过项呈现，未注明它在原判据列下读作 19。
**修法**：在 RR15/closure 注明列更换发生在测量之后、稳定性证据为 n=2；把 stdout/stderr 同步不确定的事实写入；对 `debug_begin_stmt` 补一次独立轮次的确定性验证。

**P2-2 `[P2][置信度 中]` Q-01/Q-02 跨版本移植是新增能力面，由协调器自裁而非升级用户，且与 xlen=32 的处置标准不一致**
DEC:66 的「移植原则」由协调器自立，据此给交付的 12.2.0 工具链**新增了两个此前不存在的可观测选项面**（`--w_priv_spec`、`objdump -M xw`）。按用户使命的字面（「清理…优化可读性、可维护性、最小化」），这是能力增补而非清理；它也直接产生了本阶段唯一的真代码缺陷 P8-F2。协调器把结构同类的 xlen=32 能力缺口升级给了用户（closure §7①，理由「行为修复非清理」），却自裁了 Q-01/Q-02。区分标准（「有用户已批准的对齐设计在案」）自洽，但 closure §7 只把四项呈用户，**Q-01/Q-02 仅以既成事实出现在 §4**，未作为决策项呈交。TS:55 的升级条款包含「形态改造类设计歧义」。
**修法**：把 Q-01/Q-02 的移植作为第五项列入 closure §7，请用户在验收时明确追认。

**P2-3 `[P2][置信度 高]` 8.2.0 有两项自陈归 S3 的义务从未执行，却被宣告「全部结案、无悬置」**
`obligations.md:86-87` 把「`gcc.target/riscv` 新增用例 PASS tuple 复算（0004 声称 30、0005 声称 37）」定为 C/B 级**必做**并注明「S3 须实测复算一次——本轮未复算」，`:121` 再列为补办项 #3；`:148-149` 把「重建后复跑 U3 探针确认 `riscv.c:3651`」列为轮末批新增项。`s3/regression-results.tsv` 的步骤集为 probes/quick/full-main/full-linkonly/partition/gas/replay/neutral，**两项均无记录**；`probes/` 全部文件 mtime 11:15–11:18，早于 15:15 的重建。而 RR8 §9 宣告「52 行全部结案，无悬置」，closure §10.1 甲第 1 点直接引用，closure §10.3 未列。
**风险实质为零**（我复核：`cc1` 前后同为 `d57e7de2…`、`cc1plus` 同为 `e0c4f35b…`，编译器二进制字节不变，testsuite 结果物理上不可能变），**但义务未销账且被表述为已结案**。
**修法**：或补跑记账，或在 closure §10.3 显式登记「以 cc1 字节不变替代重跑」（TS:32 不变性口径），二选一，不能沉默。

**P2-4 `[P2][置信度 高]` 8.2.0 台账的行号偏移注记自身错 2 行，四个示例全部指向错误的行**
`ledger.tsv:7-8` 称「S2 追加了上面两行 ⇒ S1 行号 N = 文件行 N+2」，并给出「旧 31 = 现 33、旧 41 = 现 43」。实际追加了 4 行（含该注记本身），正确偏移为 **N+4**。按注记打开「旧 row 31」得到的是普通 message 计数行（文件行 33），而 RR8 §5 与 closure §6.2 所指的 EXEMPTED 缺陷保真行在**文件行 35**；「旧 41」同理错到 43，真值在 45。该注记恰好制造了它声称要防止的张冠李戴，且错在最关键的两行上。（RR8 与 closure 一律用文件行，未受污染。）

**P2-5 `[P2][置信度 高]` 12.2.0 台账表头的树等式已失效，导致全表行号系统性失准**
`ledger.tsv:2` 称行号取自 gcc tree `37559608d0be…` / binutils `f7e1a27f3edf…`「与镜像 HEAD 逐字相同」；实际镜像终态为 `af74531c…`/`cb7b9681…`。抽验失准举例：row5 称 `tc-riscv.c:4411-4414` 为 `TARGET_VENDOR` 唯一命中（现文该符号全文件 **0 命中**，实际门在 `:4437`）；row6/row41 称 `riscv-dis.c:631`（实际 `:679`）；row20 称 `riscv.cc:4659` 为死子表达式（该处现为 `return true;`）；row25、row39、row40、row24/26 均位移。审计者按 row5 grep 得 0 命中时无法区分「已修好」与「台账错」。

**P2-6 `[P2][置信度 高]` 「message 指针可达性 55/55」不可复算，引用件亦已过期**
`ledger.tsv:47` 与 closure §10.1（`:601`）称 16 片 message 共 55 个仓库内指针、55/55 EXISTS。被引用的 `scratch/evidence-pointers.tsv` 实际 **57 行**（unique 53），且 mtime 11:19 **早于** U3（11:32–11:56）与 F2（15:50）的 message 重写——文件里仍带旧文件名 `0005-RISC-V-omit-WCH-finish-time-privilege-attributes.patch`。对现文 16 片重算得 **61 行 / 56 unique / 61 EXISTS / 0 MISSING**。**结论方向成立（0 悬空可独立复现），数字与引用件双错。**

**P2-7 `[P2][置信度 中]` RR12/closure 声称「全部取自权威 run 的原始日志」的 P1 数字，实际不在权威 run 里**
RR12 §2 表头明写数字全部取自权威 run；closure §3.2 逐条转录。但权威 run `run-20260817T065202Z` 的 `build.log`/`driver.log` 的 P1 段只有 `install_files`/`build_jobs`/`SOURCE_DATE_EPOCH`/`multilib_sha256`，**无** 973/283、**无** ccache 结论。该数字出自 `s3/driver-changes.md:27` 的 `-newermt` 计数，取自被判假停、后被三次重跑取代的首个 run。结论本身仍成立（我实读 `build-toolchain-12.2.0.sh:192-195` 四条顶层无条件 `safe_remove`，清洁构建对每次 run 都成立），但出处署名错——正是硬约束 7 要防的形态。

**P2-8 `[P2][置信度 中]` 12.2.0 的 KEEP 家族清单成员集与台账不符，一条未探证的「不可达」断言从复核里滑过**
台账 KEEP 家族 7 行 = KEEP-NO-TOUCH 5 + KEEP 1（row23）+ KEEP-UNPROBED 1。RR12 §3 与 closure §10.1 丙报「KEEP-UNPROBED 1 + KEEP-NO-TOUCH 6」，其枚举里的「`riscv-opc.c` 表序」在台账中并非 KEEP 行（是 row35 提案里的一句约束）；而真正 status=`KEEP` 的 **row23**（`gcc/0005` 新早返回抢占上游 `calls_eh_return` 分支）在 RR12 与 closure 中**都不出现**。总数 7=7 是巧合。row23 的保留理由是「中断处理程序不走 eh_return，实际不可达」——**只有源码位置、无任何探针落证**，对比 8.2.0 同类项有 14/14 三侧探针。closure §10.2 #1 的证据链按这份名单核时，row23 无名单、无理由承载。
另 `ledger.tsv:8`（highcode 守卫，自陈「归 KEEP-UNPROBED」）也未进任何清单，两不靠。

**P2-9 `[P2][置信度 高]` `tmp/prompts/phase-8.checklist.md` 41 项**全部未勾**
TS:3 把 checklist 定为逐单元的**在跑**证据台账（「无证据不得打勾」，S2 行「由执行者按台账扩充于此」），TS:59 把「checklist 全勾带证据」列为交付物。实测 `- [x]` 计数 = **0**，`- [ ]` = 41，S0–S3 各段均未维护，S2 单元行从未扩充。证据实际落在轮报告与 unit-records 中。已披露（closure §10.3-2、DEC:78 待办），但交付项未达成，且任务书设计的在跑纪律被事后重构取代。

**P2-10 `[P2][置信度 高]` DEC:78 ① 的不变性证据集漏了 TS:32 的第三条腿；我已代为测量，结论成立**
TS:32 的「不变性证据替代重跑」为三条腿：patches tree hash、镜像 tree hash、**install 树未动**。DEC:78 ① 只列了封存自验、mtime 扫描、六镜像 tree。我补测：15.2.0 `ours-p8final-frozen` 17:00 后 0 新文件；12.2.0 `application` 15:57 后 0 新文件；8.2.0 活体 install 对 `install-manifest.post-rebuild.txt` **2261/2261 OK**。**事实成立，记录不全。** S4 终签陈述应补引。

**P2-11 `[P2][置信度 高]` `patches/12.2.0/README.md` 两段 Phase-8 叙述时序倒置，末段停在过时的 gcc HEAD**
`:98-112` 叙述 U3（gcc → `9731e5ee`/`af74531c`，正确终态），`:114-124` 叙述 U2（gcc → `0dcdfa56eae7…`，tree 仍 `37559608`）。实际时序 U2（11:16）在前、U3（11:32–11:56）在后，README 顺序相反。线性阅读者会得出「最终 gcc HEAD = `0dcdfa56`」，与 P1-3 的 binutils 错值叠加后，整段 Phase-8 provenance 不可用。

**P2-12 `[P2][置信度 高]` `patches/15.2.0/README.md` 的两条断言随 P1-1 一并失效**
`:247` "It makes no behavioural change."；`:261-263` "This port marks ra both fixed and call-clobbered, so `call_used_or_fixed_reg_p` already returns true for it."。后者会诱导下游在别的版本/别的 flag 面照抄这个推理——正是 RR12 §4 与 RR15 §5 自己警告过的失败模式。修法随 P1-1。

---

### P3 级（记录）

| # | 发现 | 位置 |
| --- | --- | --- |
| P3-1 | closure §8.2 标题「10 次停机，10/10 判据器/驱动缺陷，零真回归」把第 11 次停机（12.2.0 P4 208/2，本阶段唯一真代码缺陷 P8-F2 所致）排除在计数外。枚举可复算且 §8.3 已披露，但标题框定弱化了唯一实质事件 | `phase8-closure.md:536` |
| P3-2 | closure §6.1「官方在断言前插入 24 行」是由 ICE 坐标 `3646−3622` 反推的定义式，官方无源码不可独立验证；同句的我方 `+29` 我已独立复算成立（`gcc/0004` 前五 hunk 净增 3+5+1+17+3，且五个 hunk 起点均 <3622）。两者并列会被读成各自落证 | `phase8-closure.md:382-383` |
| P3-3 | closure §5.2 把「官方对无 xw 属性的纯 D+C 对象照样解码」署名给 U1；`U1-conclusion.md` 附带取证 2 自陈「本轮未取到官方侧 D+C 与 XW 的同槽对照对象」，该测量实出自 `probes/u3-spec-detail.log`（U3 时段）。前提成立、证据存在，仅出处署名错。（我已独立实测该行为，两侧一致） | `phase8-closure.md:354` |
| P3-4 | closure/RR12 的「`grep -c all_ext` = 0」未写作用域；对 binutils-2.38 全树 `grep -rn` 得 2656（子串命中），`grep -rnw` 与 `grep -c … opcodes/riscv-dis.c` 才是 0。照抄命令会误判语义等价论证不成立 | `phase8-closure.md:353` |
| P3-5 | 15.2.0 台账 row7「16 片 message 重排至 ≤75 列」不成立：`gcc/0008:12` = 77 列、`:13` = 76 列、`binutils/0003:14` = 82 列 | `15.2.0/ledger.tsv:7` |
| P3-6 | 15.2.0 台账 row36 的门指针 `tc-riscv.c:5809` 不解析（该处为 `if (!start_assemble`），实际在 `:5869`；本轮对该文件净改动仅 ±1 行，说明 S1 取录时即错，回填时未重验 | `15.2.0/ledger.tsv:36` |
| P3-7 | 15.2.0 台账 row49 用**数据行序号**交叉引用（11/20/26/27/38），而 closure 的 `LG15:13`/`:46`/`:47`/`:48` 用**文件行号**；同一张表两套编号，按文件行打开会错位三处 | `15.2.0/ledger.tsv:49` |
| P3-8 | 15.2.0 台账 row44 终态无有效指针（S1 指针 `README.md:228-231` 已被本轮 E1–E6 打偏，该段现于 `:234-236`）；TS:59 要求终态带有效指针 | `15.2.0/ledger.tsv:44` |
| P3-9 | `binutils/0007` message 重写后只剩 2 条表序约束，第三条（随迁 Zcb 行与 Zcd 区间不相交）已不在文中，而 row40 的 KEEP 判据引的是三条。该条恰是 8192-word 损伤类的成因 | `15.2.0/ledger.tsv:40` |
| P3-10 | DEV-P8-15-05 的关键数字「26/392」无原始件：run2 逐 cell 矩阵未落盘，s3 下只有聚合值 `nonzero_rc 81/83`。该数字是「判据列须先证确定性」这一跨版本教训的唯一定量支撑。（我用 run1 矩阵与最终矩阵重算得 26/392，可复算——但那两份文件并非报告所引的 run1/run2 对） | `15.2.0/round-report.md:74` |
| P3-11 | 15.2.0 台账 row48 只记 `plans/roadmap.md` 有未提交改动，漏记 `plans/gcc-12.2.0.md`；closure §7④ 同 | `15.2.0/ledger.tsv:48` |
| P3-12 | 15.2.0 台账 row16 称「四条 tmp/ 指针」，现文 `gcc/0004` 有 5 条（`:34-37` 四条 + `:39` 一条），五条均存在 | `15.2.0/ledger.tsv:16` |
| P3-13 | 本轮新写的注释「That is the whole call-clobbered GPR set, ra included.」与谓词不完全对应：谓词含 `fixed_regs` ⇒ 也覆盖 x0/sp/gp/tp。行为无害，但属本轮 C 级新写、须可向上游 reviewer 解释的面；且该句是 P1-1 错误前提的载体 | `patches/15.2.0/gcc/0003-*.patch:126-128` |
| P3-14 | `impl/byte-classification.tsv` 的归一化口径未记录：裸字节比较得 6/0/10，忽略 `index <hash>..<hash>` 行后才得 8/2/6（我两种口径都算过，后者与表逐行全等）。应在表头或 RR15 §1 注明 | `15.2.0/impl/byte-classification.tsv` |
| P3-15 | 15.2.0 封存件无自述头（无 `generated_utc`、无自验行），不能凭件自证签在文档编辑之后；8.2.0 那份有。我实测 20/20 OK 且 mtime 序正确，事实无问题 | `15.2.0/phase8-15.2.0-SHA256SUMS` |
| P3-16 | DCXW 的 `stream a6ac473136e61f5f…` 在 RR15/closure 中读作实测输出，实为驱动脚本预注册常量（`resume-from-sr01.sh:41`），控制台只打印布尔 `== frozen 3f: True`。判据成立，表述应改为「与预注册冻结值相同」 | `15.2.0/round-report.md:33` |
| P3-17 | `patch-id.tsv` 列形三版本不一（8.2.0 四列含 `source_commit`，12/15 三列）。已在 closure §7② 披露。我实测 8.2.0 的 7 个 `source_commit` 全部解析且可从 HEAD 到达；另两版无等价 provenance 把手 | `patches/*/patch-id.tsv` |
| P3-18 | 轮报告位置不一：TS:47 规定 `tmp/phase8-evidence/<版本>/round-report.md`，12.2.0 的落在 `s3/` 下。closure 缩写表已如实记录 | `12.2.0/s3/round-report.md` |
| P3-19 | `impl/deviations.tsv` 中 DEV-P8-15-02/03/04 的 status 仍为「待协调器裁定」，而 DEC:77 已接受；`plans/roadmap.md` 仍记 phase-7「执行中」、phase-8「S1 重基线进行中」，且 roadmap.md 严格说不在 TS:31 的 `plans/gcc-*.md` 范围内。另 8.2.0 的 `export-patches-8.2.0.sh` / `replay-toolchain-8.2.0.sh`（`obligations.md:123` 列为「S2 开工前」补办项）至今不存在，15.2.0 亦无等价件 | 多处 |

---

## 4. 正面确认

以下为我**自己复算/实开命中**的项，构成本次放行建议的基础。

### 4.1 交付面完整性

- **pristine 复放 6/6 逐位命中**（clean-room，见 §2.1）——这同时证明补丁集完整、series 顺序正确、三版本终态与镜像一致。
- **patch-id 39/39** 与三份 `patch-id.tsv` 相同。8.2.0 的 7 个 `source_commit` 全部解析且可从 HEAD 到达。
- **封存件**：8.2.0 10/10 OK、15.2.0 20/20 OK（12.2.0 见 P1-5）。
- **封存后零 mtime 漂移**；三个 patches 目录内容哈希与 `s3/sealed/manifest.txt` 全同。
- **守卫终态干净**：`toolchain-current`、`/Users/mrs`、`/Users/wch` 三组均等于 `guard-baseline.tsv`；六镜像 dirty=0。
- **harness 未被改动**：`evt-compare.sh` = `7ee93e19…`，与 12.2.0 manifest 及 closure §10.2 #10 一致 ⇒ 比较语义未动（TS:31 范围约束成立）。
- **保留历史齐备**：`refs/openwch/phase8-pre-cleanup-15.2.0`（两组件均等于进场 HEAD）、12.2.0 的 pre-u2/pre-u3/pre-f2 系列均在。
- **声明纪律**：8.2.0 `unit-records.md` 有「先声明后执行」块（含混合态 install 树先移存、经批准后删除的完整序列，该树现已不存在）；15.2.0 `impl/DECLARATION.txt` 是带 UTC 时戳与七个命名单元的正式预声明。

### 4.2 gate 与回归数字（我落到原始件）

| 版本 | 项 | 我读到/算到的 |
| --- | --- | --- |
| 8.2.0 | 探针 | 由 `probes.p8.tsv` **重数** 834 = 793 IDENTICAL + 41 EXCLUDED；`probes.p8.summary` 与 `probes.runJ.summary` **逐字节相同** |
| 8.2.0 | 全量分区 | 独立解析 golden：43969 行 = `gate` 42285（1170 工程）+ `gate-link-only` 1684（33 工程），共 1203 工程；`partition-check.out` **12/12 PASS**，含 `legs-match-live-install` 与 `legs-same-toolchain` |
| 8.2.0 | C 级断言旁证 | install 清单 pre/post 各 **2261 行**，我自己 diff 得**恰好 1 个文件不同**（`plugin/include/system.h`）；`cc1`/`cc1plus`/`as`/`ld`/`objdump` **byte-identical** |
| 8.2.0 | 失败历史保留 | `regression-results.tsv` 同时保留 partition v1 `REGRESSION-FAIL` 行与 v2 PASS 行，末行 `ALL-REGRESSION-PASS` |
| 12.2.0 | 轮末 | `p2-summary` 274/274/0；`p4/gas.sum` `# of expected passes 210`；`p5.log` `compared=162 differing=0`；`replay-{pre,post}.log` 双 MATCH；`sealed/run-files.sha256` 390 行 |
| 15.2.0 | 双平台全量 | 两平台 `summary.json` 各 `gate_match=47797, gate_diff/missing/extra=0`, aux 47784/819, 1298 工程, `normalization=NONE`, `ours=…ours-p8final-frozen` ⇒ **被测对象确为 p8 终态树**（正面回应 DEV-15-01/02/03 那一族「量了谁」的缺陷） |
| 15.2.0 | 折叠位点 | fold/gcc → `0785aaf06ea2`（=折叠前冻结值）、fold/binutils → `bda204bac05c`（同）、full → `07d30337`（=协调器预注册判据值）、final → `22849f4548da` ⇒ **折叠可证不改终态源码** |
| 15.2.0 | 分类计数 | byte-classification 重数 8 MSG-ONLY / 2 HDR-ONLY / 6 CODE；patch-id 6 变 / 10 不变 |

### 4.3 关键行为面（我自己跑的探针）

- **Q-01 `--w_priv_spec`（12.2.0）**：官方与我方 install 树在四种模式（给选项 / 不给 / 单横线 / 缩写+重复）下产物**逐字节相同**；`--w_priv_spec` 产出 `Tag_RISCV_priv_spec: 1` + `minor: 11`，默认模式 0 计数；`--w_priv_spec=0` 两侧同报 `doesn't allow an argument`；`--w-priv-spec` 两侧同报 `unrecognized option`；`as --help` 两侧唯一差异是 argv[0] 路径，`w_priv` 命中 0 ⇒ **隐藏性成立**。closure §4.2 全部成立。
- **Q-02 `objdump -M xw`（12.2.0）**：`objdump --help` 的 RISC-V 段两侧 **diff 为空**，`xw` 条目确在 `no-aliases` 与 `priv-spec=SPEC` 之间，第二行以两个 TAB 起始；同一对象在默认 / `-M xw` / `-M xw,no-aliases` 三模式下解码**逐行相同**（`.2byte 0x2188` → `lbu a0,0(a1)` → `c.lbu a0,0(a1)`），`-M XW`/`no-xw`/`bogusopt` 三种拒绝也相同。closure §4.3 全部成立。
- **P8-F2 修复有效**：构造**无 xw 架构属性**的纯 D+C 对象（`c.fld` 编码 `2188`），`-M xw` 下官方与我方**同解为 `lbu a0,0(a1)`**，`unreachable INSN_CLASS` 命中 **0**。这同时印证 closure 否决「补 `riscv_multi_subset_supports` case」的理由成立——补 case 会让解码依赖 arch 属性，与官方相悖。
- **P8-F2 的捕获者确实存在**：`wch-xw-disassemble.d` / `-noalias.d` / `-default.d` 在位；DEV-P8-12-03 的空期望用例 `wch-priv-attr-no-arch-attr.d` 实为 104 字节、仅 3 行头，确是零输出断言。
- **`ra` 三版本前提**：`CALL_USED_REGISTERS` ra = 0/0/1（`riscv.h:254`/`:314`/`:340`），**且我加验了 `FIXED_REGISTERS` ra = 0/0/1**（`:240`/`:300`/`:322`）。这条加验很重要——若 GCC 12 的 ra 是 fixed，12.2.0 的 KEEP 判定就会是错的；实测排除了该证伪路径，**12.2.0 的 KEEP 正确**。`call_used_or_fixed_reg_p` = `fixed_regs[] || call_used_regs[]`（`hard-reg-set.h:523`）。
- **12.2.0 `riscv_epilogue_uses` 的「局部恒真」成立**：函数入口 `:4651-4652` 即 `if (regno == RETURN_ADDR_REGNUM) return true;`，故其内层同形析取项确为局部死码，死因与调用约定无关——closure §6.4「两种死因不可互搬」的论断正确。
- **15.2.0 B 级删除的代码面**：`bfd/elfxx-riscv.c` 的 `INSN_CLASS_XW` 命中 **0**（两处不可达 case 已消失）；`riscv-dis.c` 双门在 `:1056` 与 `:1074-1075`；12.2.0 对应门在 `:679` 与 `:695`，`all_ext` 在 2.38 确不存在。注释归属反转修复方向正确（`:7507-7510` 新函数自有语义行，`:7521` 上游注释归还 `riscv_save_reg_p`）。
- **DEC:74 [CORRECTION] 属实**：`build-toolchain-12.2.0.sh:192-195` 四条顶层无条件 `safe_remove`，`grep -c ccache` = 0。协调器在自己裁定的前提被执行者证伪后如实改记因果、保留处置——这是本次协调器行为审计中最正面的一条。

---

## 5. 协调器行为审计

| 审计点 | 结论 |
| --- | --- |
| **DEC 各裁定与证据一致性** | 大体一致。Q1–Q4、移植原则、分级修订、机时协议、token 分发均有可核证据链 |
| **[CORRECTION] 条（DEC:74）** | **正面**。裁定②的前提被执行者实证推翻后，协调器保留处置但改记因果并登记 DEV-P8-12-06。我实读脚本证实更正内容属实。这是「不用新证据粉饰旧裁定」的正确做法 |
| **Q4 ICE 行号豁免（DEC:65）** | 逻辑上安全：它豁免的是一**类差异**（坐标），并非断言不存在其他差异，且明文保留「坐标之外的 pass/消息/触发条件照常登记」。但推广至「一切被我方补丁触及文件内的 ICE 坐标」是由 **n=1** 探针外推，未对补丁触及文件内其他可达 ICE 做扫描。**P3 级前提提示** |
| **移植原则的边界（DEC:66）** | **见 P2-2**。原则自洽但由协调器自立，产出的是交付工具链的能力增补而非清理；与 xlen=32 的升级处置不一致；未作为决策项呈用户 |
| **硬约束 4 粒度偏离追认（DEC:78 ③）** | **证据充分**。closure §10.2 #4 如实记录偏离，我复核了替代证据确实存在：15.2.0 `impl/DECLARATION.txt`（七命名单元预声明）、`stage-trees.tsv`（6/6 阶段树可在镜像对象库复算）、`byte-classification.tsv`（逐片）、复放 tree 相等。单元内逐片 git 级验证确实保留 |
| **S4 终签不变性勾定（DEC:78 ①）** | **证据不足，须补**。①漏 TS:32 第三条腿 install 树（P2-10，我已代测且成立）；②只列 8.2.0/15.2.0 的封存自验，**12.2.0 的既未列出也不成立**（P1-5）。终签结论我认为仍可成立，但陈述必须补全 |
| **DEC:78 ④「p7 已结束」出处补记** | **P2 级**。closure 诚实标注「本报告未能在权威来源中找到该记录」（§7③、附）；DEC:78 ④ 以「用户 2026-08-17 会话指令」作答，**未给可核指针**——用无证据断言替换了一个被诚实标注的缺口。closure §7③ 的归属问题（承载 43969 证据机器且已含 p8 自身 P8-F1 修正的 full-lane 工具仍未版本化）因此仍无有据的责任人 |
| **closure §10.3 的自我披露质量** | 混合。§10.3-2（checklist 待办）、§3 口径待勾项属**诚实披露**；§10.3-1 则两个方向都错（P1-4） |
| **失败历史保留纪律** | **正面**。8.2.0 保留 partition v1 FAIL 行、15.2.0 保留四份 resume 表含 SR-01/testsuite/SR-02/切片四次 REGRESSION-FAIL、12.2.0 保留三个 run 目录。未见抹除失败历史的迹象 |

---

## 6. 我没能核验的项

1. **我方侧 gate 未独立重测。** 按任务书，quick comparator 每版本一次且对官方包。274/274、47797/47797、43969、gas、SR-01/02/03、DCXW、XW+LTO 全部只做到「与 `s3/` 原始件逐条对上」。鉴于 15.2.0 本轮 6 次停机 6/6 是判据器缺陷，这条链路的先验可靠性不高。**建议协调器补跑三次我方侧 quick**（各 3–8 秒，`ours-p8final-frozen` 等三棵树均在位且只读）。
2. **12.2.0 权威 run 的 973/283 计数**：构建目录已被覆盖，`-newermt` 计数未落盘，只读约束下不可重算（见 P2-7）。
3. **8.2.0 的 22-token `GCC_MULTILIB` 来源比对**与 **`strings` 复算（`.highcode` 1/1/0、param 名 1/1/1）**：均属对 WCH 官方二进制的深度取证面，按项目硬规则须派专门 agent，本次未做；这两个数字目前仍是 phase-6 遗留断言，未在 p8 内重新测量。
4. **官方侧 `riscv.c` 相对 pristine 的 `+24`**：官方无源码，物理上不可独立验证（P3-2）。
5. **binutils 侧折叠的 apply-and-diff 式重放**：镜像 pre-cleanup 链的 binutils 只有一个压缩提交，七片旧补丁不在历史里；改用「全补丁集字符串缺席 + 终态与上游逐字节相同」的静态穷举证明（对 rename_ok 与 ZCD 两项均成立）。
6. **`-fcall-saved-ra` 之外的其他可达面**：只穷举了 `-ffixed-ra` / `-fcall-used-ra` / `-fcall-saved-ra` 三个直接改写寄存器表的选项。`#pragma GCC target`、per-function optimization node、LTO 组合等未查，**P1-1 的分歧面可能更大**。
7. **`contrib/gcc-changelog` 校验的口径差**：本机无 GitPython/unidiff，只能用自写 stdlib 驱动加载上游 `git_commit.py`，9/9 通过 0 error，但 hunk 级校验未启用，与报告声称的「0 error / 0 warning」不完全同口径。
8. **P5「162 项全字扫描」的判据实现**：只核了汇总行 `compared=162 differing=0`，未展开 `p5/` 逐件产物，也未核该断言的判据实现。
9. **`impl/reexport-*`、`drafts/patches-final/` 与入库补丁「逐字节相同」**：未逐文件 diff，只做了 patch-id 与封存哈希两侧的一致性验证。
10. **`ref/wch-toolchain-private.md`**：按约束禁读。若其中载有官方对 ra / fast-interrupt 寄存器保存的口径，P1-1 的定性可能需按它复核。

---

## 7. 验收建议

**有条件放行。** 三版本补丁集的技术实体、gate 证据链主干、封存与复放纪律均经得起独立复算；缺陷高度集中在交付面元数据与一处前提未穷举的删除。

**放行前必须闭合（5 项）**

1. **P1-1** — 15.2.0 `-fcall-saved-ra` 行为分歧：按 DEC:63 自己的预注册条款回退为 KEEP+注释（建议），或改为有界表述并登记进 Known deviations 且删除两处「零行为改动」断言。
2. **P1-2** — `patches/8.2.0/README.md:150` 树值改 `97b81fa8…`，重签封存件。
3. **P1-3** — `patches/12.2.0/README.md:108-110` 改 `dfb77909…`/`cb7b9681…`，重算内容哈希并重签。
4. **P1-4** — 12.2.0 台账补回填；closure §10.3-1 整条改写。
5. **P1-5** — 12.2.0 封存排除自指的 `driver.log`，补交付面封存件；DEC:78 ① 补记 12.2.0 的实际证据形态与 install 树不变性腿。

**建议同批处理**：P2-2（把 Q-01/Q-02 移植列为第五项呈用户裁定）、P2-3（8.2.0 两项义务补跑或明确登记为不变性替代）、P2-9（checklist 勾定）、P2-10（终签陈述补全）。

**建议补做**：三版本我方侧 quick 各一次（§6 第 1 条），成本 3–8 秒/版本，可把 gate 面从「单次轮末批证据」提升为「带独立复现的证据」。

---

## 附：审计脚手架

- clean-room 复放脚本：`/Users/apple/Projects/openwch/tmp/phase8-evidence/review-s4/replay.sh`
- 行为探针与 SR-02 重算脚本：`/tmp/p8audit/`（`ra/fi.c`、`probes/`、`replay.sh`）
- 本次审计未修改任何 p8 交付文件；`tmp/golden/toolchain-current` 三次占用前后值均为 `/Users/apple/Projects/openwch/tmp/phase3g-evidence/ours-v3.0-frozen`，已复位。

---
---

# P8-R delta 复核

复核日期 2026-08-17（首轮报告之后）。同约束：可复算即自己复算；报告与 DECISIONS 仍按被审对象处理。

**delta verdict：放行。** 五项 P1 **全部闭合**，均由我独立复算确认；建议同批的 P2 四项中三项闭合、一项（P2-9）经裁定转为协调器自办。新发现 **3 P2 + 2 P3**，全部落在证据卫生与文档层，**无一触及 gate 数字、补丁语义或行为面**。

## R.1 delta 独立锚定

| 项 | 方法 | 结果 |
| --- | --- | --- |
| clean-room 复放 ×6 | 首轮同一脚本重跑 | **6/6 命中**：15.2.0 gcc **`5bb6a45665c03f5f67eee83f7a7598d135a679e1`**（新值）、binutils `22849f4548da…`（**逐位未变**）；12.2.0 与 8.2.0 四棵树与首轮**逐位相同** |
| patch-id | 39 片重算 | **39/39** 与三份 `patch-id.tsv` 相同 |
| 8.2.0 交付面封存 v2 | `shasum -c` | **10/10 OK**，自身 sha `9a265b1f…`；v1→v2 diff 仅「头部 + README.md 哈希」两处 ⇒ **只有 README 变化**，符合声称 |
| 15.2.0 交付面封存 | `shasum -c` | **20/20 OK** |
| 12.2.0 交付面封存（新增） | `shasum -c` | **20/20 OK**，自身 sha `c189dede…`；头记 seal-time 双树 = `af74531c…`/`cb7b9681…` |
| 12.2.0 run 封存 v2 | 在 run 目录内 `shasum -c` | **390/390 OK**（v2 改用相对路径，属改进）；`driver.log` 已移出清单、其终值记于头部 `fe598a7c…`，**与我首轮实测值逐字相同**；`toolchain-current.after` 已入签 |
| 守卫终态 | `readlink` + 六镜像 | `toolchain-current` = 基线；六镜像 dirty=0，HEAD tree 与各表一致 |

## R.2 五项 P1 逐项闭合判定

### P1-1 — **闭合（强证据）**

| 核验点 | 我的独立结果 |
| --- | --- |
| 析取项已恢复 | `riscv.cc:7519-7521` = `GP_REG_P (regno) && (call_used_or_fixed_reg_p (regno) \|\| regno == RETURN_ADDR_REGNUM)`；补丁现文 `gcc/0003-*.patch:138` 含该行 |
| 新注释形态 | `:7507-7514` **不复述「恒真」论证**，而是正面陈述机理：ra 单列是因为 `-fcall-saved-ra` 会清掉 `call_used_or_fixed_reg_p` 的两个输入、而 `fix_register()` 只回绝栈/帧指针，硬件则照存不误。**与我实证的机理逐点一致，且是可向上游 reviewer 解释的形态** |
| C 级注释归属未被破坏 | `:7527` 的上游注释仍正确归属 `riscv_save_reg_p` |
| **我自己的首轮 reproducer 重跑** | 四个 flag 档（无 / `-ffixed-ra` / `-fcall-used-ra` / `-fcall-saved-ra`）下 **官方 vs P8R 的 `.s` 逐字节相同**；同一批次里 **P8（回退前树）在 `-fcall-saved-ra` 档仍复现分歧** ⇒ 探针未钝化，「OFF==P8R」是有判别力的通过，不是空绿 |
| 新增常设探针 `s3/probe-ra-flags.sh` | 判据 A/B/C **写在脚本头部、测量前**；**fail-closed**（任一编译失败即判失败，杜绝「空==空 读成一致」）；**C 档强制**——若无任何档位能区分回退前树则 `exit 1`。这直接针对 DEV-15-02「绿得毫无判别力」那一族 |
| **我对 `ra-flags/results.tsv` 的独立重算** | 64 行 = 16 组 × 4 侧；**A/B 失配 0**；**C 判别力档位 4**（`fi_simple`/`fi_cond` × `-Os`/`-O2` × `-fcall-saved-ra`）；失败编译 0。与其 console 逐值相同。判据含 `o_sha256`，比我首轮的 `.s` 比较更强 |
| README | `makes no behavioural change` 与 `already returns true` **均已消失**；`:267` 改载 `-fcall-saved-ra` 机理 |
| 回归 | darwin `DARWIN-P8R-ALL-PASS`：quick 274/274/0、full 47797/47797（aux 47784/819、1298 工程）、探针 321/0、复放 + patch-id 16/16；linux `LINUX-ALL-PASS`：quick 274/274/0、full 47797/47797、XW+LTO 100/192/492/0 SEALED |

### P1-2 — **闭合**
`README.md:150` = `97b81fa8f52fa7037045f428f41e37099ba16fdf`（与我 clean-room 复放的 gcc 终态逐字相同）；`:155-159` 措辞已脱离 phase-6 口径并说明「gcc 值因 `gcc/system.h` 注释同步而移动、binutils 未受影响」。封存 v2 自验 10/10，且 v1→v2 只有 README 一处内容变化，头部明记重签理由与「签在编辑之后」的 P2-9 次序规则。

### P1-3 — **闭合**
`README.md:128-132` 给出正确终态（gcc `9731e5ee…`/`af74531c…`、binutils **`dfb77909…`/`cb7b9681…`**）；`:98-99` 明写「按执行顺序叙述，只有第二遍产生终态」，U2 在前、U3+F2 在后，时序倒置已消除；`:120-123` 补述了折入 `binutils/0004` 的 F2 修复；`:124-126` 同时列出 pre-u3 与 **pre-f2** 两组保留 ref。已废弃的 `d3236cae`/`2c501e75` 不再出现。

### P1-4 — **闭合**
`E12/ledger.tsv` 改为**九列**，49 行 **`final_status` 无空值**；前 7 列 S1 判定**逐字保留**（`status` 列仍为 24 STILL-PRESENT / 5 QUESTION 等原值，与我首轮计数逐一相同）——这正是「回填而不篡改历史判定」的正确做法。15.2.0 复核仍为 51/51 无空值。closure §10.3-1 已整条重写，如实记「初稿两个方向都写错、且以 mtime 当作内容证据」，并交代 `EXPLAINED` 字面与 `RESOLVED-U-*` 体系的等价由 DEC:79 明确接受。

### P1-5 — **闭合，且他们自查出我未发现的第二处同源缺陷**
run 封存 v2 **390/390 OK**；`driver.log` 移出清单并在头部单记终值，头部同时写明自指封存的机理（`run-round-end.sh:65` 的 `tee -a` vs `:136` 的 `find|xargs`）。**额外**：v2 补签了 v1 漏签的 `toolchain-current.after`（同源缺陷，我首轮未发现）。另新增交付面封存件 `phase8-12.2.0-SHA256SUMS`（20/20），补齐 DEC:62 Q3 要求的形态，三版本封存件口径至此一致。

## R.3 建议同批 P2 的处置

| 项 | 判定 | 依据 |
| --- | --- | --- |
| P2-2 Q-01/Q-02 呈用户 | **闭合** | closure `§7 ⑤ Q-01 / Q-02 跨版本移植的追认（审计 P2-2）` 已立节，并在 §10.3-3 标为建议优先 |
| P2-3 8.2.0 两项义务 | **闭合（走不变性口径，合规）** | RR8 §9 增限定块：「全部结案」限于台账裁决面，两项 S3 义务按 TS:32 **不变性销账而非执行**，依据是重建前后 `cc1` `d57e7de2…`/`cc1plus` 逐字节相同；销账落 `obligations.md:88/125/153`。这正是我首轮给的两条路径之一，且未沉默 |
| P2-9 checklist | **未闭合（经裁定转办）** | 实测仍 `- [x]` = 0 / `- [ ]` = 41；DEC:79 将其列为协调器自办、与入库 commit 同批。closure §10.3-2 如实记录 |
| P2-10 终签证据腿 | **闭合** | 新 DECISIONS 条目补记 install 树不变性腿（并注明「审计已代测三版本成立」）与 12.2.0 封存实态 |

## R.4 delta 新发现

### RV-1 `[P2][置信度 高]` SR-02 的 dumpmatrix 确定性复验**量的是回退前的树**——同族缺陷第 4 次复发

`run-darwin-p8r.sh:101` 无参调用 `s3/sr02-lto-dumpmatrix.p8.py`，而该脚本 `:38-46` 的 `SIDES` 是**硬编码**字典，`OURS-P8` 指向 `tmp/phase3h-evidence/ours-p8final-frozen`（**回退前**），**无 `ours-p8r-frozen` 侧，也无 argv 注入侧的接口**（全文 `argv` 仅用于 subprocess）。我核过：p8r 目录下没有任何 `.tsv`/`.json` 以 `ours-p8r-frozen` 为被测侧（只有 ra-flags 因取 `$1` install-root 而正确）。

后果两条：①我首轮 P2-1 要求的「对 `debug_begin_stmt` 补独立轮次确定性验证」，实际验证的是**旧二进制**的确定性，不是交付树的；②SR-02 的实质结论（WCH↔OURS 互解码 0 失配）被结转给一棵 `lto-dump` 二进制已改变的树，而无任何一侧测量它。

这正是 DEV-P8-15-02/03 的形态，也正是 closure §9 第一层教训（「判据器跑通不等于判据成立——先问『它量的是谁』」）所指——**第 4 次出现**。
**缓解（我已核实）**：LTO 面并非无覆盖——linux 腿在 P8-R 中**重跑了** XW+LTO（`100/192/492/0 SEALED`），而 linux 是从同一套 p8r 补丁重建的，故新 gcc 的 LTO 面实际被独立覆盖。因此本条是**证据卫生**问题，不是覆盖空洞。
**修法**：给 `sr02-lto-dumpmatrix.p8.py` 加 `--ours`/侧注入参数（照 DEV-15-02 当初对 `sr03-norvc-matrix.py` 的做法），以 p8r 侧重跑一次；或在 RR15/closure 明写该复验的被测对象是回退前树、并说明为何仍足以支撑结论。

### RV-2 `[P2][置信度 高]` 不变性豁免的前件是**源码树**，但豁免面里既有非 binutils 面、其二进制面也确实变了

`run-darwin-p8r.sh:96-99` 以「binutils 源码树与回退前逐位相同」勾定 **SR-01/02/03、DCXW、gas/binutils 套件**不重跑。两处不严：

1. **SR-02 根本不是 binutils 面**——它跑的是 `bin/riscv32-wch-elf-lto-dump`，**GCC 工具**；gcc 树本轮恰恰变了。把它放进「binutils 未变」的豁免范围属分类错误。
2. **源码相同 ≠ 二进制相同**：我实测 p8final 与 p8r 两棵 install 树的 **8 个 binutils 工具全部字节不同**（`as` 尺寸 1729168→1728704，`cmp -l` 33473 字节不同；两侧均无嵌入构建目录串，故非路径差）。而 SR-01 恰恰是**对二进制做字面量审计**的探针，用源码面前件豁免二进制面探针，逻辑上不闭合。

**我做的补偿测量**：同一输入下两棵树的 `as` 产出 `.o` **逐字节相同**、`objdump -d -M xw` 反汇编**逐字节相同** ⇒ 豁免的**结论**（行为不变）站得住。故本条是**论证链缺一环**，非结论错误。
**修法**：把豁免措辞改为「binutils 源码树逐位相同**且**同输入下 as/objdump 产物逐字节相同」并附该次测量；把 SR-02 移出该豁免、按 RV-1 处理。

### RV-3 `[P2][置信度 高]` 8.2.0 台账行号偏移注记**第三次算错**——被它自己的更正文字再次推翻

注记已从 `+2` 改为 `+4`（`ledger.tsv:7-8`），但更正本身又给表头加了行。实测：表头行在 `:13`，首个数据行 `:14`，而首个数据行 = S1 row 7 ⇒ **真实偏移 = +7**。注记 `:9` 的四个示例（`7→11`、`31→35`、`41→45`、`49→53`）**全部再次偏 3**，并且再次落到无关的 `ALREADY-FIXED` 行上：

| S1 row | 注记称 | 该行实际内容 | 真实行 | 真实内容 |
| --- | --- | --- | --- | --- |
| 31 | 35 | `gcc/0004` message 声称核对（ALREADY-FIXED） | **38** | `gcc/0004` D4a `calls_eh_return` — **EXEMPTED** |
| 41 | 45 | `binutils/0001` 立即数宽度（ALREADY-FIXED） | **48** | `binutils/0001` `wch_rvc_extension` 单调置位 — **RESOLVED-U1** |
| 49 | 53 | `binutils/0002` vendor 内联比较（ALREADY-FIXED） | **56** | 复放勘误 — RESOLVED-U3 |

**无下游损害**（closure 与 RR8 一律用文件行号，且本轮已同步到 `:38`/`:48`，我逐一验过命中）。但交付台账里的导航注记连续三版错误，且每次都恰好把读者从缺陷保真行引开。
**修法**：**直接删掉该注记**（所有消费者已改用文件行号，它已无用途且是纯风险），或改为自计算表述「表头 13 行，S1 row N = 文件行 N+7」。

### RV-4 `[P3][置信度 高]` 12.2.0 指针件的行数与「61/56/0」三元组对不上
`scratch/evidence-pointers.tsv` 实为 **60 行、全 EXISTS**；我对现文 16 片 message 独立重算得 **raw 61 / unique 56 / MISSING 0**。60 既非 61 也非 56，说明该件的计数规则（去重口径、是否含某类指针）未记录。**实质结论「0 悬空」我已独立复现，成立**；属首轮 P3-14「计数机器口径未记录」同族。

### RV-5 `[P3][置信度 高]` closure 自行登记了两处未随 P8-R 同步的文档，尚未处理
closure §10.3-4 主动记下：①`RR12 §4` 的跨版本表仍留「15.2.0 ⇒ 恒真冗余，可删」一行，与回退裁定冲突；②`RR12 §3` 的 KEEP 族清单自称用台账文件行号，实际比现文少 3（`:8/:21/:23/:40` 应为 `:11/:24/:26/:43`）——与 RV-3 同族。**登记而不代改是正确处置**，此处仅记为待办。

## R.5 首轮 P2/P3 的回归性抽查

- **P2-8（row23）闭合且做法优良**：新增 `E12/probes/row23-eh-return.{sh,log}` + `probes/row23/` 48 个产物，三组（fast+eh_return / machine+eh_return / 普通函数+eh_return）× `{-S,-c}` × 官方/我方，零 normalize 全比；随后做 DEC:65 **窄口径**复比，掩码仅 `sed -E 's|(config/riscv/riscv\.cc):[0-9]+|\1:<COORD>|'`——**只屏蔽 ICE 内嵌坐标本身**，pass/函数/断言/用户源码位置/rc/产物全比。台账 `final_status` 由 `KEEP` 改 `EXEMPTED`，并**明记 S1 的「实际不可达」措辞被证伪**（组合可达且崩，但崩点为官方共享缺陷）。这是我首轮指出的「无探针承载的 KEEP」被正确补证并如实翻案。
- **P3-1 闭合**：closure §8.2 标题改为「10 次仪器停机 + 1 次真缺陷停机（P8-F2）+ **1 次真回归（P1-1，审计发现）**」，并显式交代初稿框定问题。
- **§6.4 重写属实**：标题改为「一次被证伪的『恒真』与它的回退」，表格增列 `FIXED_REGISTERS`，明记「三版本同形同判、该析取项在三个版本上都是活代码」，并保留我加验 `FIXED_REGISTERS` 的独立价值说明。
- **指针抽查**（每新改节 ≥2 个，实开）：`gcc/reginfo.cc:661` → `fix_register (const char *name, int fixed, int call_used)` ✅；`riscv.cc:7519` → 谓词首行 ✅；`E15/ledger.tsv:14` → `status=STILL-PRESENT` / `final_status=KEEP-VERIFIED` ✅；`E12/ledger.tsv:26` → row23 `KEEP→EXEMPTED` ✅；closure 的 `LG8 文件行 38 / 48` → EXEMPTED 行、`wch_rvc_extension` 行 ✅。

## R.6 delta 最终 verdict

**放行。**

五项 P1 全部闭合，其中 P1-1 的闭合由**三条互相独立的证据**支撑：我自己的首轮 reproducer 在新树上转为与官方逐字节相同、该 reproducer 对旧树仍保持判别力、以及我对新增探针原始行表的独立重算（16 组 A/B 零失配 + 4 个判别力档位）。修法选的是 DEC:63 预注册的回退条款，代码形态与注释可向上游解释，双平台全量 gate 复跑全绿。

残留 3 P2 + 2 P3 全部位于证据卫生与文档层：RV-1/RV-2 是「判据器量了谁」与「豁免前件缺一环」，其结论已由我的补偿测量与 linux 腿 XW+LTO 重跑覆盖；RV-3/RV-5 是行号注记与两处未同步表述；RV-4 是计数口径未记。**无一影响 gate 数字、补丁语义或交付行为面。**

**入库前建议顺手做的三件（均非阻塞）**：①删除或改写 8.2.0 台账的行号偏移注记（RV-3）；②给 `sr02-lto-dumpmatrix.p8.py` 加侧注入并以 p8r 侧重跑一次，或在报告注明其被测对象（RV-1）；③把不变性豁免措辞补上二进制行为等价那一环并将 SR-02 移出该豁免（RV-2）。P2-9（checklist 勾定）按 DEC:79 与入库 commit 同批完成。

**首轮遗留的覆盖口径限制依旧成立**：我方侧 quick 仍未由我独立重跑（本轮三次 comparator 预算用于 clean-room 复放与行为探针）；15.2.0 我方侧的 274/47797 仍来自 p8r 轮的自测。若要把该腿也提升为带独立复现的证据，代价仍是每版本 3–8 秒。

## 附：delta 复核脚手架

- 复放脚本（与首轮同一份，未修改）：`/Users/apple/Projects/openwch/tmp/phase8-evidence/review-s4/replay.sh`
- `-fcall-saved-ra` reproducer：`/tmp/p8audit/ra/fi.c`（四 flag × 四侧 OFFICIAL/P8R/P8/PRECLEAN）
- 本次 delta 复核同样未修改任何 p8 交付文件；未占用 `tmp/golden/toolchain-current`（未跑 comparator），终值仍为 `…/tmp/phase3g-evidence/ours-v3.0-frozen`。
