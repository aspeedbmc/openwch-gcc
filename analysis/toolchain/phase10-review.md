# phase-10 开源前检查报告 · 独立对抗审计（delta）

审计对象：`analysis/toolchain/phase10-opensource-readiness.md`（386 行）+ `tmp/phase10-evidence/` + DECISIONS 2026-08-18 phase-10 两条。审计者上下文从未持有 phase-10 执笔工作；p8/P8-R/phase-9 三轮审计的基线知识作为资产使用。可复算即自己复算；报告与简报作为**被审对象**。

审计日期 2026-08-18。

---

## 0. 结论摘要

| 项 | 值 |
| --- | --- |
| **verdict** | **有条件放行** —— 四个重点面中三个（act 实证、P10-F1、指针普查）证据链**完全成立且经我独立复算**；第四个（S2 实验）有一处**结论被自身数据反证**，须更正后放行 |
| P1 | **1** |
| P2 | **2** |
| P3 | **4** |
| 独立复算 | act 交付物绑定 7/7 自算命中、断言 274/274、指针普查 143 分类与双外锚全中、P10-F1 三版本机理逐条读源、S2 的 74 FAIL 逐行分类 |

**一句话**：这份报告的**方法与工程判断质量很高**（判据器自证、预注册、读源直证、呈用户不自决都做到了），但它在自己最醒目的一行里把**两个不同成因混成一个**，并据此写下一条**被自身证据文件反证**的技术结论。

---

## 1. 重点一：act linux 腿端到端全绿 —— **成立**，我逐项复算

| 核验点 | 我的独立结果 |
| --- | --- |
| 退出码 | `act-exit-code.txt` = **0**；`act-run.log` 尾 `🏁 Job succeeded`、`ACT_EXIT=0` |
| 分母绝对断言 | `assertions.txt`：`manifest_gate_rows=274 expected=274`、`manifest_projects=9 expected=9` —— 两条**绝对常数断言**在位并命中 |
| 字节 gate | `summary-line.txt` 两条 `SUMMARY gate_pass=274 gate_total=274 gate_fail=0 aux_match=273 aux_diff=4`；`raw-drift.txt` = `raw_drift_lines=328+328`（入库 manifest 仅作诊断，与 DEC:60 语义一致） |
| 墙钟 1299s | `timing.tsv`：provision 107 + prepare 96 + build 898 + gate-golden 55 + gate-compare 23 = **1179s**，`act-total 1299`（自述含镜像拉取与 act 开销）——**差 120s 有交代，自洽**。子段 `timing-stages.tsv` 再分解（binutils-build 185 + gcc-compiler-only 676 + inject 2）与 build 898 相容 |
| 内存 8.78 GB | `memory.tsv`：`build-peak-bytes 8780759040` = 8.78 GB，来源标注 **cgroup peak**；另有 `docker-stats-peak 7.743GiB`（宿主侧轮询）。两个口径都 > darwin runner 7 GB ⇒ **结论不依赖取哪一个**。文件头自带跨平台外推警告，报告 §4.4 如实转述 |
| worktree 隔离 | `worktree-status-{before,after}.txt` **逐字节相同**（4 M + 4 ??）；我现场再取一次 `git status --porcelain=v1`，与两者**仍逐字节相同**，HEAD 仍 `eed1486` |
| 交付物绑定 7/7 | **我自己重算了 7 个文件的 sha256**，与 `deliverable-binding.txt` 的 before/after 两栏**逐字符全等**（`release.yml 7f32aeaa…`、`toolchain-ci.yml b98d807e…`、四个 `scripts/ci/*`、`wvproj.yml c3603e9d…`）；文件内 before/after 各 `rows=7 status=0` |

**判定**：这是本项目 CI 的首次端到端实证，证据形态完整（自动落盘 timing/disk/memory/assertions/binding/worktree），**分量与报告的定性相称**。p7「仪器建在 workflow 本体、首次真跑即自解」的设计确实兑现。

---

## 2. 重点二：P10-F1 —— **成立**，分级 P1 恰当

**实测件真实**：`s2/replay2.log` 在 8 归档校验、**16 片 apply_check 全 PASS**、双组件 `tree_match PASS`（gcc `af74531c…`、binutils `0d01a497…`）之后，死于

```
fatal: failed to unpack tree object 3280576e992d8fcd57fabd4bb85944fcf2bfaddb
REPLAY_EXIT=128
```

即失败发生在补丁**全部成功应用之后**，正是报告描述的位置。

**机理三版本差分，我逐条读源**：

| 版本 | 锚形态 | fresh 兼容性 |
| --- | --- | --- |
| 12.2.0 | `:105 gcc_base=3280576e…`（**commit**）作 `read-tree` 锚（`:165`/`:203`）；`:187` `merge-base --is-ancestor` From 可达检查 | **原理上不可能通过**（实测证实） |
| 8.2.0 | `:235` 同款 From 可达检查（read-tree 锚为上游 tag commit） | 同类断点（报告标注**读源推导、未实跑**——标注准确） |
| 15.2.0 darwin/linux | `merge-base --is-ancestor` 命中数 **0/0** ⇒ 纯内容锚 | **fresh 兼容**（与报告一致） |

**「击穿 p7 两条 darwin 腿」传导链成立**：`prepare-sources.sh:21-23` 的 12.2.0 腿是「verified tarballs → git init/commit import → git am」、8.2.0 腿是「clone tag → git am」，两者都产生**新 commit**；而该脚本 `:301-306` 的注释**明写**其契约建立在「`verify_source_base()` falls back to the root commit of a fresh import」之上——正是 020d43a 改掉的行为。`toolchain-ci.yml:680`（darwin-12-2-0）与 `:921`（darwin-8-2-0）都直接调用对应构建脚本 ⇒ 两腿必红。

**分级 P1 恰当**：它切断 3 个版本中 2 个的**一切外部 fresh 复现路径**，并击穿 4 条 CI 腿中的 2 条；失败形态是裸 `git fatal` 无诊断文案（对外部使用者更不友好）。对一个「开源前检查」而言，「外部复现不可能」就是最高后果类。未升 P0 也正确——本阶段 analysis-only，既有内部流程未坏。

---

## 3. 重点三：S2 实验完整性 —— **一处结论被自身数据反证（P1）**

### 3.1 正面部分（我复算命中）

- 预注册 `s2/preregistration.md` 自述「写于任何数据产生之前」，三条预期 P-pred-1/2/3 **文本具体、可证伪**（含机理与预期数字），形态合规。
- **走通路径实证成立**：`golden-regen2.log` `double_run=PASS deterministic=9 excluded=0 failures=0`；`compare-fresh-manifest.log` `SUMMARY gate_pass=274 gate_total=274 gate_fail=0 aux_match=273 aux_diff=4` —— 与主仓正典 quick 数字逐一相同。**P-pred-3 命中，DEC:60 的异地实证成立**，这是本阶段最有价值的正面结果之一。
- B6 的「静默缩水」实证扎实：`golden-regen.log` 记 `v4bc-pmp EXCLUDED run1 build failed`，根因日志明写 `main.c:196:2: error: #error "This chip dosen's support pmp function"`，且首次重生成**无任何非零退出信号** ⇒ 「无声错数」定性成立，对 p7 三层绝对断言设计的实证正当性也成立。

### 3.2 **P1-A `[P1][置信度 高]` §3.1-A1 把两个成因混成一个，并据此写下被自身数据反证的结论**

**位置**：`analysis/toolchain/phase10-opensource-readiness.md:128`（A1 行）、`:120` 与 `:352`（三预期全中）

我把 `s2/compare-shipped-manifest.log` 的 74 条 FAIL **逐行分类**：

| 成因 | 行数 | 工程 |
| --- | --- | --- |
| **真字节差异**（`expected_size=… actual_size=…`） | **46** | v3f-gpio 23 + v3f2-gpio 23 |
| **`missing or build failed`** | **28** | v4bc-pmp（+1 条 `compare-build` 阶段失败记录） |

⇒ **两处错误**：

**① 数量与归因**：A1 声称「74 项失配全部落在三个 `-g` 工程」，把 A1（cwd/DWARF，**原理不可省**）的规模高估了 61%。真正体现该机制的是 **46 项 / 两个工程**；另 **28 项**是 v4bc-pmp 因未跑 `apply.sh` 而**编译失败**，成因是 **B6（文档缺口，完全可修）**。把可修缺口的后果计入「原理不可省」栏，方向上让问题显得比实际更不可修。

**② 结论被自身数据反证**：A1 括注称「**1 .bin**——后者说明 cwd 还能经 `__FILE__` 类字面量进入非调试产物」。实际：

- 唯一失配的 `.bin` 是 `v4bc-pmp obj/PMP.bin`，状态栏原文 **`missing or build failed`** —— **不是字节不同，是产物不存在**；
- 真正呈现 cwd 效应的两个工程 **v3f-gpio 与 v3f2-gpio 的 `.bin` 均 PASS**；
- 全部 9 个 `.bin` 行 = **8 PASS + 1 missing**。

**本实验没有任何证据支持「cwd 进入非调试产物」；其数据正面支持相反结论。** 连带地，P-pred-2 的子预期「无 DWARF 的产物（.bin）预计 MATCH」其实是**被证实**的，而报告把一次构建失败误读成了反向证据加新发现。

**为何是 P1**：本阶段交付物就是分析本身，对分析而言错误结论等价于代码缺陷。且这条结论出现在最高可见度的「原理不可省」行，会直接传导到对外推荐复现流程的措辞与「哪些缺口可修」的判断。
**修法**：A1 行改为「46 项 / 两个 `-g` 工程（70→46 .o/.elf）」，把 28 项 `missing` 明确移入 B6 后果；删除 `__FILE__` 那句括注（或改写为「本实验中 .bin 全部 MATCH，未观察到 cwd 进入非调试产物」）；§3.1 分栏比例随之更新。

### 3.3 **P2-A `[P2][置信度 高]` 「三条预期全部命中，无反向」与报告自身叙述冲突**

`:120` 写「三条预期**全部命中，无反向**」、`:352` 写「预注册三预期全中」；而 `:128` 同时把 `.bin` 当作一个**出乎预期**的发现来陈述。两处不能同时为真。经 3.2 澄清后实情是：**P-pred-2 完全命中（含 .bin 子预期）**，报告既误判了反向、又声称无反向——说明这条「无反向」是概括写下的，未逐条回到数据核对。
**修法**：把预期核对写成逐条对照表（预期文本 / 实测 / 判定），P-pred-2 标注「含 .bin 子预期，命中」。

---

## 4. 重点四：指针普查与分级 —— **判据器与总量全部成立**

### 4.1 判据器三关（我自己跑）

`python3 s1/pointer-census.py --selftest` 输出：

```
selftest PASS: ['tmp/phase8-evidence/a.log', 'analysis/toolchain/phase8-closure.md:12',
                'ref/gcc/darwin-arm64/15.2.0', 'DECISIONS.md:63']
diffstat 后内容未被计入: PASS
```

三关俱在：合成样例断言（`:114` `assert toks == exp`）、diffstat 边界（`:116`，防把补丁正文内容计入 message）、片数断言（`:57` `assert len(patches) == 39`）。**这是本项目判据器纪律的正确形态。**

### 4.2 143 指针分类（我从明细件复算）

| 类 | 我的复算 | 报告 |
| --- | --- | --- |
| TMP（对外悬空） | **108** | 108 ✓（75.5%） |
| TRACKED（可达） | **30** | 30 ✓ |
| REF-IGN（`ref/gcc`） | **5** | 5 ✓ |
| 合计 / 不存在路径 | **143 / 0** | 143 / 0 ✓ |

**双外锚我逐个复算命中**：15.2.0 `gcc/0004` = **5 指针全 TMP**（与我在 phase-8 审计 P3-12 记的 5 条一致）；12.2.0 合计 = **62**（= 我在 P8-R 复算的 61 + phase-9 新增 1）。**用我自己此前两轮的独立数字作外锚，是这个判据器最有说服力的一点。**

### 4.3 分级与 §6 完备性

- P1 四条我逐条核：P10-F1（§2 成立）、无入口文档（`git ls-files` 确认根无 README）、私有笔记无 ignore 防护（我实测 `git ls-files` = 0 未跟踪、`git check-ignore` 无输出 ⇒ **P1-3 成立**）、指针 75% 悬空（§4.2 成立）。**四条都够 P1，无该升未升。**
- P2-6 我实测 `git ls-files | grep -c .DS_Store` = **3** ✓。
- §6 八项覆盖了全部需要取舍的轴（体积、过程史、身份、指针、CI 路径、文档归属、发布形态），且与 P1/P2 的对应关系清楚；P10-F1 的处置虽未单列为 §6 项，但已并入 ⑥ 的「合并前必须重整清单」第 1 条 —— 它是待修缺陷而非待裁取舍，**归置正确**。
- 唯一可议：**P2-4**（`scripts/full-census/partition-check.py:20` 硬编码绝对 `REPO=`）是**已跟踪**文件，对任何异地使用者该工具直接不可用；考虑到它只是诊断工具、不在主复现路径，P2 可接受，但建议在 §6-⑦/入口文档任务里点名。

---

## 5. 其他发现

### P2-B `[P2][置信度 高]` `act-verify.sh` 的 gate 判据自读自写，产物恒含一条伪 `verdict FAIL`

`tmp/p7-worktree/scripts/ci/act-verify.sh:262-281`：该块以 `>> "$run_dir/summary-line.txt"` 追加，**同时**内层 awk 又以同一文件为输入（`:276`）。块首 `printf '# expected: …'` 写入的注释行因此成为 awk 的第三条输入行，其中无 `gate_pass=` 字段 ⇒ `pass/total/fail` 全 `absent` ⇒ 产出一条 `verdict FAIL`。

实测产物 15 行：2 条 SUMMARY + 1 条 `# expected:` 注释 + **PASS / PASS / FAIL** 三块。我用最小样例复现：注释行输入必得 `FAIL (pass=absent)`。

**后果**：只要日志里有 ≥1 条 SUMMARY，该文件**永远**含一条 FAIL ⇒ 该文件里的 FAIL 信号**零信息量**，真失败也会淹没其中。报告 §4.4 以「端到端全绿」概括，未提该 FAIL 行；协调器或外部复核者抽查 `summary-line.txt` 会读到 `verdict FAIL`。
**加重情节**：这是**待合并的 p7 CI 交付件本体**（`act-verify.sh` 在 7/7 绑定清单内），phase-10 的职责正是替合并做就绪检查。
**修法**：把 `# expected:` 行改为写入独立文件，或内层 awk 加 `$1 ~ /^SUMMARY/` 过滤；作为合并前重整清单第 6 条。

### P3 级

| # | 发现 |
| --- | --- |
| P3-1 | §2.1 per-version 表与明细件差 1：12.2.0 TMP 报 **53** 实为 **54**、15.2.0 报 **25** 实为 **24**（两处反向，合计 108 仍对）⇒ 该表不是从明细件生成的 |
| P3-2 | `disk.tsv` 的 `build-peak` 行**值为空**（「peak du -sk」从未采到），磁盘结论实际只有 df 差分支撑；报告 §4.4 称「约 7.2 GB」，按 df 差分我算得 7,319,304 KiB ≈ 6.98 GiB / 7.49 GB（口径未注明二进制还是十进制） |
| P3-3 | `memory.tsv` 有第二个测量 `docker-stats-peak 7.743GiB`，报告只引 cgroup 的 8.78 GB。结论不受影响（两者都 > 7 GB），但两测量并存且差 1 GB 值得一句说明 |
| P3-4 | 「三个 `-g` 工程」这一属性我**未能独立证实**：在三个工程的 `.wvproj` 里 grep `-g` 零命中（编译选项可能来自 `.cproject` 或转换器默认）。属性本身不影响 3.2 的结论（我的分类按状态列做，不依赖 -g），但报告用它作分类依据时应给出处 |

---

## 6. 正面确认（我自己复算的）

- act：退出码 0、断言 274/274 与 9/9、SUMMARY 两条、raw-drift 328+328、墙钟分段自洽、内存双口径、worktree before/after 与**我现场第三次取值**三者逐字节相同、**交付物 7 件 sha256 我自算全等**。
- P10-F1：实测件真实、三版本机理差分逐条读源成立、p7 两腿传导链由 `prepare-sources.sh` 自身注释坐实、分级恰当。
- 指针普查：判据器三关我实跑、143 分类全等、**双外锚用我自己前两轮的独立数字命中**。
- S2 正面结果：`274/274` 走通路径、`double_run=PASS deterministic=9 excluded=0`、B6 静默缩水实证（含根因 `#error` 原文）。
- 出场守卫：repo HEAD `6705cce` 与报告一致；三 patches 内容哈希 `30f8ba45…`/`dccdf8a5…`/`89876c5c…` 与 p9 出场值**逐字相同**；`toolchain-current`、`mrs` readlink 均为基线值。
- P1-3 / P2-6 我实测成立（私有笔记未跟踪且无 ignore；3 个 `.DS_Store` 已跟踪）。
- analysis-only 边界：主仓跟踪面零改动，唯一新增为报告与 `tmp/phase10-evidence/`。

---

## 7. 对协调器裁量条的独立意见（comparator 2 次超字面）

**我同意协调器的裁量接受，并认为理由可以写得更强。**

「每版本至多一次 quick」这条限额的立法目的是**限制审计者/执行者消耗独占的重型机时并扰动共享状态**。本例中两次 `evt-compare` 是同一实验的**对照对本身**——一次对随仓 manifest（预期失败，用于证 A1）、一次对自生成 golden（预期全绿，用于证 P-pred-3）；**去掉任何一次，实验就失去对照，结论不成立**。这不是超额消耗，而是「限额按次计、实验按对照计」两种计量口径的冲突。

三点支撑：①两次都跑在 `tmp/phase10-evidence/scratch/clone/` 内，**主仓 `toolchain-current` 全程未占用**（我复核终值为基线）；②执行者**主动如实登记并提请裁量**，未自行消化；③其中一次的结论（274/274 异地成立）是本阶段最有价值的正面产出之一。

建议把该裁量固化为一般规则：**限额约束的是「对共享/独占资源的占用次数」，不约束在隔离副本内构成单一实验对照组的重复调用**；隔离性由「未占用共享 symlink + 出场守卫零漂移」证明。这样下次不必逐案裁量。

---

## 8. verdict

**有条件放行。**

四个重点面里，act 实证、P10-F1、指针普查三项的证据链**完全成立**，且都经我用独立路径复算（其中指针普查的两个外锚正是我自己前两轮审计的数字，交叉验证成立）。方法面（判据器三关自证、预注册先于数据、读源直证、QUESTION 全部呈用户不自决、出场守卫零漂移）达到本项目迄今的高标准。

**放行前须闭合（P1）**：§3.1-A1 的 74 项拆分为 46（A1 真机制）+ 28（B6 后果），并删除/改写被自身数据反证的 `__FILE__` 结论。这处更正会**改善**结论——更多失败落在可修的文档缺口栏。

**建议同批**：P2-A（预期逐条对照表）、P2-B（`act-verify.sh` 自读自写判据，且列入 p7 合并前重整清单）、P3-1（per-version 表从明细件重生成）。

**给协调器的一句提醒**：本轮 P1 与 phase-9 的 P2-1、p8 的 P1-2/P1-3 属同一族——**报告里的数字/结论与其证据文件不一致**。三轮里这一族每次都出现，且每次都不是分析能力问题，而是**最后一步没有回到证据文件逐条核对**。建议把「报告数字 vs 产物机械对照」固化为收尾必做步骤（我在 phase-9 P2-4 已提过，本轮再次命中）。

---

## 附：审计脚手架与足迹

- 本次审计未修改任何 phase-10 交付文件；未占用 `tmp/golden/toolchain-current`（未跑 comparator）。
- 唯一写面：本报告 `tmp/phase10-evidence/review/phase10-review.md` 与 `/tmp/p10-selftest.txt`（P2-B 的最小复现样例）。
- 出场复核：repo HEAD `6705cce` 不变，三 patches 内容哈希与 p9 出场值逐字相同，两条 readlink 为基线值。
