# phase-6 收口报告（GCC 8.2.0 / riscv-none-embed / darwin-arm64）

对象：WCH GCC 8.2.0 平台包（target `riscv-none-embed`，宿主可执行体 x86_64、经 Rosetta 运行）。
宿主路线 = x86_64/Rosetta（Main 裁定，`analysis/toolchain/phase6-baseline.md` §8）。
证据根 `tmp/toolchain_8.2.0/evidence/`（下称 **E**）；交付物根 `analysis/`。
本报告只引用已落盘证据，不重跑任何构建、套件或探针；引用到的每个数字都给出可独立重推的指针
（文件路径 + 行号或字段名）。

---

## 1. 终局摘要

### 1.1 交付栈

| 组件 | 基线 tag | 补丁栈（自下而上） | 终态 HEAD / tree |
| --- | --- | --- | --- |
| gcc | `v8.2.0-3.1`（`0c7a874f0…`） | `1abae7a36` multilib 基建 → `830ea0167` host `system.h` → **`bd000fc87` D1′ march** → **`f5d1f2b66` D4a 中断属性** → **`96943e02e` D4b highcode param** | HEAD `96943e02e327d9108493a27569908a2592f2ef81` / tree `3260ccd8722ba1dc938ad188fa2cafd2b61b5423` |
| binutils | `v8.2.0-3.1`（`82b51c7b5…`） | `236b362bc` D2 XW 压缩访存 → `1b4136adc` D3 objdump `-M xw` | HEAD `1b4136adc30d689d0ae12d862945406e48b3bb1c` / tree `8d0d7da3c3b3376d07ef0f76f0f00b6b913dcf40` |

证据：`E/s4/patches-export/{entry,exit}-state-v2.txt`（gcc HEAD/tree 与栈位六元组、
`entry_vs_exit: IDENTICAL`、两树 status clean）；`patches/8.2.0/patch-id.tsv` 的 `source_commit`
列七行与上表逐一吻合；`E/s4/testsuite-final/report.txt` L22–25/L29–32 记的是**修正前**的栈
（`f4d855414` / tree `a6782d2562…`），属 P1-1 修正轮之前的时点，见下方勘误块。

> **【P1-1 修正轮勘误，2026-08-17】** 本表原记 gcc 栈 `5ed9a2ca3` D1 → `80444ac97` D4a → `f4d855414` D4b、
> tree `a6782d2562d72d9f30246421814f09631b9aec1c`——**旧值保留于此**。
> 独立对抗性审计 P1-1 发现 D1 的实现与其自身 commit message 的规格陈述相反（详见 §2.4），
> D1 重做为 D1′ 后 gcc 栈自第三位起全部换号，终树 tree 随之变为 `3260ccd872…`。
> binutils 两片、gcc 前两片（`1abae7a36`/`830ea0167`）不受影响，patch-id 与文件字节均未变。

行为补丁面终形（`E/s4/transcript-recovery/reports-outbound.md` L177 原文）：
gcc 3 片（D1 march 解析 +12 行、D4a 中断属性 +35/−3、D4b highcode param +28/−4）
+ binutils 2 片（D2 XW 压缩 +163/−8、D3 `-M xw` +25）+ host 1 片 + 基建 1 片（multilib）。

### 1.2 gate 数字（终局）

| 面 | 数字 | 证据 |
| --- | --- | --- |
| 快速回归（README 精选集，8 工程 / `v3c-led` EXCLUDED），**复放构建** | **242/242 gate PASS、gate_fail=0、aux_diff=4** | `E/s4/replay/evt-compare-replay.stdout` 末行 `SUMMARY gate_pass=242 gate_total=242 gate_fail=0 aux_match=241 aux_diff=4` |
| 快速回归，**P1-1 修正构建**（D1′ 栈重建后） | **242/242 gate PASS、gate_fail=0、aux_diff=4** | `E/s4/replay/evt-compare-p11.stdout` 末行同上；重建 rc=0 见 `E/s4/replay/rebuild-p11.log`（`gcc_head=96943e02e`、`install_files=2261`） |
| **全量收口认证（复放构建）** | **42285/42285 gate MATCH、DIFF/MISSING/EXTRA = 0、1170/1170 工程** | `E/s3/full-ours/stage-replay/summary.json` 的 `counts`：`{"project_match":1170,"gate_match":42285,"gate_diff":0,"gate_missing":0,"gate_extra":0,...}`；`run_id 20260816T162338.762949Z-96569`、`ours_install_stable=true`。**该跑发生在 D1 栈上（tree `a6782d2562…`），未在 D1′ 栈上重跑**——D1′ 的认证接力见 §3.2 |
| aux 面（不入 gate） | 比较 42972 行、match 42273、**diff 699**（698 `.map` + 1 `.lst`） | 同 `summary.json`（`aux_total_compared` / `counts.aux_*`）；扩展名分布由 `stage-replay/aux-mismatches.tsv` 第 3 列可重推；698 条 `.map` 的**全覆盖**机械核对见 §6.1 |
| 缺陷保真探针集 | **834 条 = 793 IDENTICAL / 41 EXCLUDED / 0 MISMATCH，`run-probes.sh` rc=0** | `E/s4/defect-fidelity/probes.tsv`（834 数据行，末列 verdict）；`summary.txt` 首行与末行 `archive_leg_mismatch=0`；`runs/runJ.console` 末尾 `manifest_files=10203 stable_files=10169`；双跑判据对 = `runs/run{I,J}.{console,probes.tsv,stable.sums}` |
| testsuite | 六个验收面全部闭合 + pinned objdir 附录闭合 | `E/s4/testsuite-final/report.txt` §0/§2；`E/s4/testsuite-final/addendum-pinned-objdir-gas.txt` |

**认证口径（本报告写死，供审计者对数）**：修正后（R3 getopt + R4b 注入面补项）唯一一次
全量认证跑在**复放构建**上——即「pristine 上游 + `patches/8.2.0` series（v1 栈）+ 修正后构建脚本」
所产出的那棵 install 树。活动树上的 quick 242/242 是辅助证据，不是认证本身
（`E/s4/replay/replay-record.md` §「目的与地位」）。
**P1-1 修正轮之后，交付栈 = D1′ 栈**；42285 那一跑**留在原复放树上不重跑**（Main 裁定定向复验），
D1′ 的认证由「审计 gate 中性论证 + 定向复验接力」承担，逐项列在 §3.2。

> **gate 口径的准确表述（审计 P2-20）**：本报告全文所称「逐字节一致」，其准确含义是
> **「在双侧对称的 `-fdebug-prefix-map` 工具链前缀归一下的逐字节一致；该开关经用户裁定，
> 比较阶段零 normalize」**。两条 lane 在**编译期**都加了
> `-fdebug-prefix-map=<各自真实工具链根>=<neutral 根>`（quick 用 `tmp/golden/toolchain-current`，
> full 用逐工程 `<project_root>/toolchain-current`），这是双侧对称的编译期开关、不是事后 normalize，
> 且已在 manifest 头与 `census-report §2/§7d` 披露。**必须记账的后果**：任何仅表现为
> 工具链路径字符串的真实差异，对 gate 不可见。AGENTS.md 硬规则「比较前不做任何 normalize——
> 差异本身是信息」在**比较阶段**成立且本项目严格遵守（比较器零 normalize），
> 但**编译阶段**存在这一条经裁定的对称开关，故终报一律用上面的带限定表述。
> （本限定只适用于 gate 口径，即 42285 与 quick 242；`E/s4/defect-fidelity` 探针集不加该开关，
> 其「三侧同跑、比较前零 normalize」是字面为真的无限定陈述。）

### 1.3 分母的来历

全量分母 1298（canonical EVT 枚举，与 phase-3b 同构）拆为
PASS 1170 + EXCLUDED-capability 127 + EXCLUDED-config 1 + UNRESOLVED 0，
分区校验 1170+127+1+0 = 1298（`E/s3/full-census/census-report.md` §1）。
gate 产物 42285 = `.o` 39945 + `.elf` 1170 + `.bin` 1170（同 §1）。

**勘误（2026-08-17，P2-21 裁定，DECISIONS 4f5dedb）——分母口径扩展。**
上面三行是普查腿当时的账，逐字保留。用户裁定把排除粒度由工程级收紧为**产物级**：
仅在 `collect2`/`ld` 阶段失败的工程，其编译成功的 `.o` 进入收口 gate，只剔 `.elf`/`.bin`。

| 项 | 旧 | 新 |
| --- | --- | --- |
| 分母口径 | 工程级 1170 全绿 | **工程级 1170 全绿 + link-only 33 工程的 `.o` 面 1684 只** |
| gate 总数 | 42285 | **43969 = 42285 + 1684** |
| capability / config | 127 / 1 | 126 / 2（`lib:missing` 于同日另一次审计改判，与本次扩展无关） |

link-only 33 = `isa-attr:z-subset` 31（1349 只 `.o`）+ `lib:missing` 1（33 只）+ `link:region-overflow` 1（302 只）；
「约 900」是 P2-21 登记时的审计外推值，**实测 1684**（差额主体是 index 938 LTDC_LVGL 的 302 只）。
官方侧在同一 cwd 契约下 same-path 双跑（`official-r1`/`official-r2`）33/33 逐产物 sha256 相同后才固化；
我方侧同契约对拍 **1684/1684 MATCH、DIFF=0、MISSING=0、EXTRA=0**，两侧链接失败诊断 `<TC>` 归一后逐字相同 33/33。
落盘在 `analysis/golden/8.2.0-darwin-arm64-full.tsv` 的 P2-21 追加块（`class=gate-link-only`，原 42285 行逐字节未动，
新 sha256 `6e09fc44…d908a`）与 exclusions 表的 `link-only:` keyword 前缀（`class` 列不动，126/2 仍可推，
新 sha256 `466f37ac…fd530`）。证据 `E/s4/linkonly-extension/`，runner `tools/full-census/linkonly_runner.py`
（原样复用 `census_runner.build_side`，census/ours 两腿封存工具零改动）。
**复放口径**：全量重放 = `ours_runner.py`（42285）+ `linkonly_runner.py`（1684），两个封存工具都不改。
本次扩展只增加覆盖面，§1.2 的 42285/42285 认证行与其载体裁定（§2.4 第 4 段、§3.2）不受影响。

---

## 2. 补丁面终形与导出

### 2.1 七片布局

`patches/8.2.0/`：`gcc/` 4 片 + `host/` 1 片 + `binutils/` 2 片 + `series` + `patch-id.tsv` + `README.md`（英文）。

| series 位 | 文件 | stable patch-id | source_commit |
| --- | --- | --- | --- |
| 1 | `gcc/0001-riscv-regenerate-t-elf-multilib-from-the-WCH-GCC_MUL.patch` | `2eeed4290e44ec41…` | `1abae7a3652537ce…` |
| 2 | `host/0002-host-move-C-standard-header-includes-before-safe-cty.patch` | `3176631c1c02c8c1…` | `830ea01678dab982…` |
| 3 | `gcc/0003-riscv-accept-the-WCH-QingKe-xw-march-spelling.patch` | **`7f03544f9db27f5d…`** | **`bd000fc8747dc6ce…`** |
| 4 | `gcc/0004-riscv-accept-the-WCH-QingKe-WCH-Interrupt-fast-inter.patch` | `4ced28afaacd89a1…` | **`f5d1f2b6669c4c97…`** |
| 5 | `gcc/0005-c-family-add-the-WCH-highcode-gen-section-name-param.patch` | `e5d66a082d18b432…` | **`96943e02e327d910…`** |
| 6 | `binutils/0001-RISC-V-add-the-WCH-XW-compressed-byte-and-halfword-a.patch` | `49e28a5907f169cb…` | `236b362bc95ff1e5…` |
| 7 | `binutils/0002-RISC-V-decode-the-WCH-XW-compressed-accesses-under-o.patch` | `5228dfb0e554a732…` | `1b4136adc30d689d…` |

来源：`patches/8.2.0/{series,patch-id.tsv}`（`series` 7 行即上表顺序；`patch-id.tsv` 8 行 = 表头 + 7 行）。

### 2.2 编号裁定（B）与其理由

导出执行者在此处**停下并把问题作为交付物回传**（不自决），原件
`E/s4/patches-export/open-question.txt`：gcc 源树只有**一条**五提交栈，其中第二个提交要落 `host/`，
「编号 = 栈位」与「每个目录自 0001 连续」在此首次分叉——15.2.0 是一目录一源树、12.2.0 的同类
host 补丁留在 `gcc/` 的栈位上，两个先例都不具判别力。

编排会话裁定 **B：编号 = 栈位，只搬文件不重编号**（同文件末 `RESOLUTION` 段）。
后果是 `gcc/` 在 `0002` 处留一个可见的空位，而那正是被搬进 `host/` 的那一片；
文件名、`series`、`Subject: [PATCH n/5]` 三者因此保持互洽。理由已写进
`patches/8.2.0/README.md` 的 “Numbering and the `host/` split” 节。

### 2.3 四项不变式（导出无副作用的直接证据）

**四项不变式在 P1-1 修正轮后已全部重签（v2 轮）**，下表为终态；v1 轮的同名文件保留为被取代轮的记录
（`E/s4/patches-export/README-evidence-index.txt` 逐条说明哪份是 CURRENT、哪份是 SUPERSEDED）。

| 不变式 | 结果 | 证据（v2 = 终态） |
| --- | --- | --- |
| patch-id 7/7 全等（源提交 ↔ 导出文件，From 改写后） | **7/7 YES** | `E/s4/patches-export/patch-id-final-v2.tsv`（含 `vs_v1` 列：`gcc/0003` = CHANGED，其余六片 same）；与 `patches/8.2.0/patch-id.tsv` 逐行同 |
| 干净克隆 → base tag → 按 series `git am` → 终树 tree 断言 | **双断言 PASS**：gcc **`3260ccd872…`**、binutils `8d0d7da3c3…` | `E/s4/patches-export/apply-check-final-v2.log`（7 步逐步 tree 全列，`applied count gcc=5 binutils=2`） |
| 源树进出场 | `entry_vs_exit: IDENTICAL`，两树 status clean | `E/s4/patches-export/{entry,exit}-state-v2.txt` |
| trailer 扫描 | **0 命中**（无 co-authored-by / claude / anthropic / generated-with / signed-off-by） | `open-question.txt` 末段；裁定原文见 §11.3 |

**v1 → v2 的字节级差额（`v1-vs-v2-bytes.tsv`）**：`gcc/0003` 内容变（D1′ 重做）；
`gcc/0004`/`gcc/0005` **仅 mbox `From <sha>` 行**变（diff 正文逐字节相同 ⇒ patch-id 不变）；
`gcc/0001`、`host/0002`、`binutils/0001`、`binutils/0002` **四片逐字节不变**。
`patches/8.2.0/README.md` 另因终树哈希更新而变。
终清单见 `E/s4/patches-export/final-SHA256SUMS-v3.txt`（重签原因见 §2.5）。

**author 元数据统一**：七片的 `From:` 统一为 `OpenWCH Phase 6 <phase6@openwch.local>`（仅邮件头第 2 行；
mbox `From <sha>` 行与全部 `Date:` 保留源值）。这一项 **discharge 了 DEV-P6-06 留下的唯一遗留事项**
（该偏差原文：「author 身份差异记录留待 S4 元数据统一」，`E/deviations.tsv` DEV-P6-06 行）。

**无 trailer 裁定**：Main 在里程碑 #4 回信中就地确认「源码树补丁 commit 不加 Claude trailer，正确……S4 复核时按此口径」
（`E/s4/transcript-recovery/index.md` L19 逐字摘录；compact 后重定向信 L1361 重申其为不得回退项，见同文件 L26）。

### 2.4 P1-1 修正轮：D1 → D1′（审计发现 → 修法 → 复验口径）

独立对抗性审计（`analysis/toolchain/phase6-review.md` P1-1，severity 3 / confidence high）
在 gcc/0003 上发现**实现与其自身 commit message 的规格陈述相反**，本节按「发现 → 复证 → 修法 →
复验面 → 裁定及其依据」五段全量记录，不做压缩。

**1) 审计发现（原文要点）**：commit message `:27-28` 写的是「`'x'` 与 `'w'` 是**两个独立的单字符步骤**，
不是对 `"xw"` 的 strcmp」——文字写对了，**代码把内层 `if (*p == 'w')` 嵌进了 `if (*p == 'x')` 分支里**。
两种实现在**含 `x`** 的输入上产出完全相同，故 `E/s3/d1/spec-probe/` 的 25 个探测串（**全部含 `x`**）
**在唯一能判别的轴上是盲的**；commit message 引以为据的 `rv32imacxq→'q'`、`rv32imacxwz→'z'`
两例只能排除 `strcmp(p,"xw")`，**不能**区分嵌套与并列。

**2) 编排会话现场复证（五轴 × 2 模式，预注册后实测）**：按「独立步骤 vs 嵌套」模型预注册预测再测，
5/5 命中——分歧唯一落在字母 `w` 上：

| `-march=` | 官方 | 修正前我方 | 分歧 |
| --- | --- | --- | --- |
| `rv32imacw` | rc=0（cc1 放行，as 拒绝） | rc=1 `unsupported ISA substring 'w'` | **是** |
| `rv32iw` | rc=0 | rc=1 `'w'` | **是** |
| `rv32imacww` | 残余 `'w'` | 残余 `'ww'` | **是** |
| `rv32imacwx` | 残余 `'x'` | 残余 `'wx'` | **是** |
| `rv32imacxw` / `rv32imacx` / `rv64imacxw` / `rv32imacxq` | rc 与残余串同 | 同 | 否（不变对照） |

**3) 修法**：内层 `if` 反缩进为并列语句（一处缩进 + 注释更正），即
`patches/8.2.0/gcc/0003-…` 现文的 `if (*p == 'x') p++;` 与 `if (*p == 'w') p++;` 两条独立语句，
落点 `gcc/common/config/riscv/riscv-common.c`（`riscv_parse_arch_string`）。
栈重建：`bd000fc87`（D1′）→ `f5d1f2b66`（D4a′）→ `96943e02e`（D4b′）；
**D4a/D4b 的 stable patch-id 不变**（`4ced28af…` / `e5d66a08…`，`patch-id-final-v2.tsv` 的 `vs_v1` 列为 `same`），
终树 tree 不变式由 `apply-check-final-v2.log` 双断言 PASS 复验（gcc `3260ccd872…`、binutils `8d0d7da3c3…`）。

**4) 定向复验（Main 裁定不重跑 42285）与其依据**：

- **gate 中性论证（审计给出，本报告复核采信）**：从
  `E/s3/full-census/stage-a/effective-project-inventory.tsv` 提取全部 1298 工程的 march 取值，
  **只有 6 种**——`rv32imacxw` 878 / `rv32imcxw` 211 / `rv32imac` 100 / `rv32ecxw` 83 /
  `rv32imc` 17 / `rv32imafcxw` 9——**每个 `w` 都紧跟 `x`，无一例落在分歧面上**；
  且该 hunk 不触碰 `*flags`、不注册 subset，对所有当前被接受的串产出逐字节相同。
- **复验面（实跑，全部落盘）**：① 重建 rc=0（`E/s4/replay/rebuild-p11.log`，`gcc_head=96943e02e`、
  `install_files=2261`）；② quick **242/242、gate_fail=0、aux_diff=4**（`E/s4/replay/evt-compare-p11.stdout`）；
  ③ 缺陷保真探针集全量重放 **834/834 rc=0**（含新增 w 判别轴组，见下）；
  ④ 四项不变式 v2 全签（§2.3）。
- **判别轴已升为常设探针**：`E/s4/defect-fidelity/lib/18-march-w-axis.sh`
  —— 8 个 march 串 × `-S`/`-c` 两模式 = 16 条探针 + 1 张派生表，**17/17 全 IDENTICAL、双跑稳定**。
  该组同时给出 D1′ 「对 gate 中性」的**可观测字节证据**：`rv32imacw`、`rv32imacxw`、`rv32imacx`
  三者的 `-S` 产物 sha256 同为 `cf7667b994…`，`rv32imacxw`/`rv32imacx` 的 `.o` 同为 `6d7d5596f6…`
  （`E/s4/defect-fidelity/report.md` 增量修订二 §二之二）。
- **Main 裁定**：按上述面定向复验，**不重跑 42285**。理由是分歧面与 gate 面**证明不相交**
  （6 种 march 全部落在两种实现同解的区域），而 hunk 的中性由字节面独立佐证。
  该裁定的代价如实登记：**42285 那一跑的载体仍是 D1 栈的复放树**（tree `a6782d2562…`），
  D1′ 栈上没有 42285 的直接测量——这是一条**论证 + 定向测量**的接力，不是一次新的全量测量。

**5) 偏差登记**：DEV-P6-07（本项）、DEV-P6-08（栈重建时重演 `git cherry-pick -q` 无效旗标）
已入 `E/deviations.tsv`，见 §8。

### 2.5 导出清单重签（审计 P2-9）

`final-SHA256SUMS.txt`（v1 轮）对当前交付文件已失效，成因可识别且合法：
Main R3 明令的「把 `ac_cv_lib_dl_dlopen=no` 与 `inject_bfd_plugins` 写入宿主适配节」那次
`patches/8.2.0/README.md` 更新发生在封存之后。P1-1 修正轮又改了三片 gcc 补丁与 README。
按审计修法「**重签并注明原因**」，本轮产出 `E/s4/patches-export/final-SHA256SUMS-v3.txt`：
覆盖 `series` + `patch-id.tsv` + `README.md` + 7 片 `.patch`，v1/v2 两份原样保留作历史轮次记录
（`README-evidence-index.txt` 标注哪份 CURRENT、哪份 SUPERSEDED）。
同批补上审计 P2-10 要求的**构建/harness 脚本身份**：`E/s4/audit-sweep/script-sha256.txt`
逐脚本记录 `path + sha256 + 采集时点`（`replay-build.log` 属既落盘证据，不回改）。

---

## 3. pristine 复放认证链

复放不是收尾的一道额外手续，而是**认证对象本身**：交付栈的全量数字全部取自复放构建。
全程记录 `E/s4/replay/replay-record.md`。

| 环节 | 内容 | 结果 |
| --- | --- | --- |
| 输入 | gcc replay 树 `7ba6a31c6`（tree `a6782d2562…` == 开发树 tree）、binutils replay 树 `2dc53d2aa`（tree `8d0d7da3c3…` == 开发树 tree） | tree 相等已验（replay-record §输入） |
| 换入/换出 | `sources/` 两棵开发树 `mv` 为 `*.dev-preserved`、replay 树 `cp -R` 入原名；`install`/`build` 各 `mv` 为 `*.pre-replay-preserved`（可逆重命名，非删除） | replay-record §换入/换出 |
| 构建 | 修正后脚本 + host deps 全新重建 | **rc=0**（replay-record §结果第 1 条）；`replay-build.log` 记 `install_files=2261`、`gcc_head=7ba6a31c6`、`binutils_head=2dc53d2aa`、`build_jobs=16`、`SOURCE_DATE_EPOCH=1767225600`；injection **8 组全 PASS**（含 `bfd-plugins-lto-stub`）——`work/darwin-x64/logs/openwch-phase6/injection-samples.tsv` 8 行、两侧 sha 逐行相等（`verify_pair` 不等即 `die`，故 8 行存在即 8 组 PASS） |
| 终点抽查 | `as` 选项错误前缀与官方逐字节同、getopt 导入 0 | replay-record §结果第 2 条 |
| quick | **242/242、gate_fail=0、aux_diff=4** | `evt-compare-replay.stdout` 末行 |
| **全量认证** | **42285/42285、DIFF/MISSING/EXTRA=0、1170/1170** | `stage-replay/summary.json`；封存件 `stage-replay/STAGE_COMPLETE.json` |
| aux 面 | **699 行与 S3 轮 `stage-ours` 逐行逐 sha 全同** | 本报告现场复核：`cmp E/s3/full-ours/stage-{ours,replay}/aux-mismatches.tsv` ⇒ **两文件逐字节相同**（700 行 = 表头 + 699），比「逐行逐 sha」更强 |
| 复放 objdir gas 套件 | 183P/0F/3XF/7U/1W、`Running` .exp 行 130 | `E/s4/replay/check-gas/`，见 §7.2 |
| 布局定案（复放轮当时） | 复放 install 留任 active；`sources/` 复位开发树（当时为 `f4d855414`/`1b4136adc`）；复放树归档 `tmp/toolchain_8.2.0/scratch-s4-applycheck/{gcc,binutils}-replay-as-built` + `REPLAY-TREES.txt` 指针 | replay-record §结果末两条。**归档路径原文少一层**（写作 `scratch-s4-applycheck/…`），此处补全为仓库相对全路径 |

**闪烁预登记已兑现**：复放前按 R5 预登记「全量 aux 面可能出现别的工程 `.lst` 同址择名翻转
（或 955 恰好一致），出现时按闪烁类登记、不按新发现分诊」（replay-record §预登记）。
实测**未触发新增**——699 行分布与 S3 轮字节相同，仍是 698 `.map` + 1 `.lst`（index 955）。
预登记因此没有被用来事后合理化任何东西，这一点值得单独记一笔。

### 3.1 全量认证 run 的实体与叙述（两条路径，互引）

审计 P3 点名过一处易漏项：**全量认证 run 的实体与叙述分居两处**，只按 `E/s4/` 枚举会漏掉实体。
两条路径在此互引，任取其一都能走到对方：

| 面 | 位置 | 内容 |
| --- | --- | --- |
| **实体（机器件）** | `E/s3/full-ours/stage-replay/` | `summary.json`、`STAGE_COMPLETE.json`、`ours-{artifact,project}-results.tsv`、`gate-mismatches.tsv`（仅表头）、`aux-mismatches.tsv`（700 行 = 表头 + 699）、`run-id.txt`、`command-ledger.tsv`、`identity/`、`selfcheck/`、`triage/` |
| **叙述（过程记录）** | `E/s4/replay/` | `replay-record.md`（换入/换出、预登记、结果）、`replay-build.log`、`full-replay-run.log`、`evt-compare-replay.stdout`、`check-gas/`；P1-1 修正轮另加 `rebuild-p11.log`、`evt-compare-p11.stdout` |

### 3.2 D1′ 栈的认证接力（P1-1 修正轮后的终态口径）

**终布局（本轮实测）**：

| 项 | 终值 |
| --- | --- |
| active install | **P1-1 修正构建**（D1′ 栈，`E/s4/replay/rebuild-p11.log` 记 `gcc_head=96943e02e`、`install_files=2261`、rc=0） |
| `sources/` 两棵开发树 | gcc HEAD `96943e02e` / tree `3260ccd872…`；binutils HEAD `1b4136adc` / tree `8d0d7da3c3…`（本轮进出场零 git 写操作，现场 `rev-parse` 复验） |
| 42285 全量认证的载体 | **原复放轮的构建**（D1 栈，tree `a6782d2562…`）；未在 D1′ 栈上重跑，见 §2.4 第 4 段 |
| D1′ 的认证 | **审计 gate 中性论证**（1298 工程仅 6 种 march，全部落在两实现同解区）**+ 定向复验接力**（重建 rc=0、quick 242/242、探针集 834/834、四不变式 v2） |
| 复放树归档 | `tmp/toolchain_8.2.0/scratch-s4-applycheck/{gcc,binutils}-replay-as-built`（v1 轮）与 `{gcc,binutils}-replay2`（v2 轮 `git am` 保留克隆，`apply-check-final-v2.log` 末行记路径） |
| `install.pre-replay-preserved` / `build.pre-replay-preserved` | 仍在 `work/darwin-x64/`，处置待 Main（§15 第 3 条） |

**这条接力的性质如实写明**：它是「**论证 + 定向测量**」，不是「一次新的全量测量」。
若 Main 改判要求 D1′ 栈上的 42285 重跑，本报告的其余账目均不受影响，只需替换 §1.2 的认证行与本节。

---

## 4. 构建脚本宿主适配面（非补丁，**八件**）

老代码基（gcc 8.2 / binutils 2.32，2018–2019 年源）在现代 macOS 上的适配，
除 `host/0002` 一片源码补丁外全部落在 `scripts/build-toolchain-8.2.0.sh`，
理由是「它们是构建旗标与依赖钉版，不是源码改动，且无一在 gate 产物上可观测」
（`patches/8.2.0/README.md` “Host adaptations that are not patches”）。

> **【枚举补全，2026-08-17；审计 P2-14】** 本节原写「六件」，遗漏两项落在同一脚本里的 zlib 宿主
> workaround（第 7、8 项），且第 1 项只列了四个 `-Wno-`、未提 `host_cflags` 同时把整体优化/部署目标
> 设成 `-O2 -mmacosx-version-min=10.13`（上游默认为 `-g -O2`）。「六件」是完整性声称，故就地补全为**八件**；
> 旧计数保留在本注记里。八项**无一在 gate 产物上可观测**这一性质不变。

| # | 件 | 落点 | 性质 |
| --- | --- | --- | --- |
| 1 | `host_cflags` 整体：`-O2 -mmacosx-version-min=10.13` **加**四个 `-Wno-`（`-Wno-implicit-function-declaration` / `-Wno-implicit-int` / `-Wno-int-conversion` / `-Wno-incompatible-function-pointer-types`） | 脚本 L90 | 降回 clang 16 之前的诊断级别 + 显式钉死宿主优化/部署目标（上游默认 `-g -O2`），源码保持 pristine |
| 2 | ISL 钉 0.18 | 脚本 L147/L171/L289 | GCC 8.2 graphite 依赖的 API 在 isl 0.24 已删（`phase6-literal-surface.md` §3 H2） |
| 3 | `arch -x86_64` 自 re-exec + `CC/CXX` 显式 `-arch x86_64` | 脚本 L28–30（re-exec）、L36–37（`CC`/`CXX`） | configure 字面量内嵌 `--build/--host=x86_64-apple-darwin17.7.0`，逐字复放必然产出 x86_64 宿主；`arch -x86_64` 下 clang 仍默认 arm64（实测） |
| 4 | `LC_ALL=C` / `TZ=UTC` / `SOURCE_DATE_EPOCH=1767225600` / `ZERO_AR_DATE=1` / `MACOSX_DEPLOYMENT_TARGET=10.13` / `PATH` 最小化 / `MAKEINFO=/usr/bin/true` | 脚本 L32–40 | 字面量与时间戳钉死面 |
| 5 | **`export ac_cv_lib_dl_dlopen=no`（R3）** | 脚本 L344 export、L378 unset（段后立即解除，不波及 gcc 段） | 见 §5.1 |
| 6 | **`inject_bfd_plugins`（R4b）** | 脚本 L410–418 定义、L473 调用 | 见 §5.2 |
| 7 | **zlib 1.2.12 的非 VPATH 就地拷贝**：`/bin/cp -cR "$sources/zlib-1.2.12/." .` 后再 `./configure` | 脚本 L303–309 | zlib 1.2.12 的 Darwin configure 不是可靠的 VPATH 构建（xPack helper 同款布局），纯宿主依赖构建方式，与目标工具链无关 |
| 8 | **`-UTARGET_OS_MAC`（zlib CFLAGS）** | 脚本 L310 | 现代 Darwin 的 clang 预定义 `TARGET_OS_MAC`，zlib 1.2.12 误判为经典 Mac OS 而屏蔽 `fdopen`；只作用于 host zlib 这一个依赖的编译 |

**注入面核对现为 8 组**：`verify_pair` 在脚本 L490–511 调用八次（`target-stdio` / `target-libc` /
`xw-libc` / `nano-specs` / `target-libgcc` / `xw-libgcc` / `target-crt0` / `bfd-plugins-lto-stub`），
落 `logs/openwch-phase6/injection-samples.tsv` 8 行、两侧 sha 逐行相等。

> **时序口径（供审计者对数）**：`analysis/toolchain/phase6-literal-surface.md` §2 记「7 组 verify_pair 全 PASS」。
> 该报告落盘于 S2，而第 8 组 `bfd-plugins-lto-stub` 是 R4b 裁定（2026-08-17）之后加的；
> 两个数字都对，各自对应各自的时点。以本节的 8 组为终态。

---

## 5. 缺陷保真探针集与两簇史

探针集 = 对 S1/S3 已归档探针脚本的**重放**（`lib/01-*.sh`…`lib/09-*.sh` 是 `E/s1/probes/` 同名脚本的
逐字节副本，本单元不重写探针语义），三侧同跑、比较前零 normalize
（`E/s4/defect-fidelity/report.md` §二）。

**终态（P1-1 修正轮后）**：**834 条 = 793 IDENTICAL / 41 EXCLUDED / 0 MISMATCH**，`run-probes.sh` rc=0；
双跑判据对 **runI/runJ**（`probes.tsv` 与 `SHA256SUMS.stable` 两轮逐字节相同，两次 rc=0）；
`SHA256SUMS` 10203 项 / `SHA256SUMS.stable` 10169 项。
834 = 原 804 + 新增两组：**组 18 `march-w-axis` 17 行**（审计 P1-1 判别轴，§2.4）
与**组 19 `attr-arch-monotonic` 13 行**（审计 P3 第 1 条，见下）。
（`report.md` §三终态表 + 增量修订二；`probes.tsv` 834 数据行）

**转绿性质必须与头条同处披露（审计 P2-12）**：41 条 EXCLUDED 里，**19 条（簇 1 `as` 前缀）是真的修好了**
（R3 getopt 修正，runE 实测由 MISMATCH 转 IDENTICAL），而**6 条（簇 2 nm 插件）是 runE→runF 之间
由判据变更转入 EXCLUDED 的**——不是行为面自己变绿。该判据变更经审计独立复算成立
（6 条掩码后 diff 全空；替身组 36 产物 diff=0 且脚本零 normalize），但两者性质不同，不可混读。
全轮次台账：runA–D `788 / 728 I / 35 X / 25 M` → runE `788 / 747 / 35 / 6` →
runF/G/H `804 / 763 / 41 / 0` → **runI/J `834 / 793 / 41 / 0`**。
**runF/G/H 三份 console 逐字节相同**（本轮现场重推：`runs/{runF.console,runG.console,runH-replay.console}`
sha256 同为 `bbb3ad4ae15811f4…`，故当初终态取 runH 无 cherry-pick 之嫌）；
本轮的 `runs/{runI,runJ}.console` 同理逐字节相同（sha256 `d2b611a2d22f3b18…`）。
文件名口径一并更正：`runs/` 下是 **`runG.console` 实名**（原文引用的 `runs/runG-*.console` glob 不匹配任何文件），
runH 的实名是 `runH-replay.console`。
**runE 快照缺口如实登记**：runE 是唯一「行为已定型、判据未改」的关键快照，当时只留了 console、
未存 `probes.tsv` / `SHA256SUMS.stable`（`runs/` 目录可自证），该缺口不可事后补；
本轮 runI/runJ 三件齐全，不重演。

**归档腿的准确口径（审计 P2-6）**：`archive_leg_mismatch=0` 的含义是「**741 个被评估的行里 0 失配**，
覆盖 2281 个文件」，**不是**「与 S1/S3 归档逐字节全同」——`lib/compare.py:166` 对 EXCLUDED 行短路返回，
归档腿对那 41 条根本没评。终态现场重推：归档可比宇宙 783 行 / 2427 文件 =
741 行已评估（2281 文件全部命中）+ 41 行 EXCLUDED 短路（124 文件）+ 1 行归档侧无同名件；
另有 21 个文件落在已评估行内但归档侧无同名件而被 `compare.py:189` 静默 `continue`。
两条机制层假绿通道一并登记：归档侧缺文件静默 `continue`（`:189`）；探针枚举以 official 侧目录为准（`:157`），
我方多吐的文件永不被发现。（`report.md` §一勘误块 + 增量修订二 §归档腿口径）

**排除判据与替身的准确表述（审计 P2-1）**：**主判据**是「输出内嵌各自安装前缀的绝对路径，
跨侧必然不同且不携带行为信息」；审计对全部 41 条做独立掩码 diff，**39 条掩码后 diff 全空、判据成立**，
`03-attributes/driver-v` 与 `08-defaults/v-default` **两条判据不成立**（掩码后还剩 compiled-by 字面量行
与 `Compiler executable checksum` 行）。**「每条被排除的探针都有仍在 gate 内的替身」这一通则不成立**：
`driver-v`、`v-default`、`08-defaults/print-search-dirs`、`08-defaults/print-sysroot` **四条无有效替身**
——原文把后两条转嫁给「S2 字面量面」，而 `phase6-literal-surface.md` §1 的 9 项表里**没有**这两项
（只有 `ld --verbose` 的 SEARCH_DIR，是另一个面）。逐条订正后的判据表见 `report.md` §五。
按 Main 的 P-12 裁定，compiled-by 字面量面**在排除理由里如实点名、不新增 gate 探针**；
`Compiler executable checksum` 归类为项目硬规则已明文豁免的「工具链二进制整体字节面」。
EXCLUDED 41 = 原 35（libgcc/libc/sysroot/search-dirs 一类绝对路径输出 + 2 条 `gcc -v` 项）
+ 新增 6（簇 2，见 §5.2）。

**新增组 19：`wch_rvc_extension` 单调置位（审计 P3 第 1 条，从推测升为双侧实测）**——
gas 侧 `wch_rvc_extension` 只有唯一一处赋值、无复位路径，而 `.attribute arch` 允许在首条指令前多次出现。
探针以 4 个源文件 × 3 个命令行 `-march` = 12 条 + 1 派生表覆盖，**13/13 全 IDENTICAL、两侧同为单调**。
判别力由对照组保证：只写 `.attribute arch,"rv32imafdc"` 时 `c.fld` **两侧均 rc=0**（证明该指示符确实重配 subset），
而先写 `.attribute arch,"rv32imac_xw"` 再写同一条时 `c.fld` **两侧均 rc=1 `illegal operands`**
（诊断从 `unrecognized opcode` 变为 `illegal operands`，说明 arch 串已更新、只有 `wch_rvc_extension` 没清零）。
**EVT 不可达**：转换器只经 `-march` 命令行传 ISA，EVT 源无一使用 `.attribute arch`，gate 面不受影响。
（`report.md` 增量修订二 §二之三）

> **计数口径**（引用处写明一次，免得审计者重复踩）：§三 覆盖表的类小计**含**组内派生表行。
> 例如 `D-mapping-symbol缺席` 表内记 16，`probes.tsv` 拆为明细 15 + 派生表 1；增量修订节写的
> 「15 条改为 9 IDENTICAL + 6 EXCLUDED」是明细口径。两者不矛盾。
> 现场复核：`awk -F'\t' 'NR>1{print $2}' probes.tsv | sort | uniq -c` 给出全部类小计。

### 5.1 簇 1：`as` 选项错误前缀（19 条）——**已修，机制在宿主构建环境面**

- **现象**：同 argv、同 cwd 下，官方 `as` 的未识别选项诊断打 `argv[0]` **原文**，我方打 **basename**；
  两侧 rc 均 1，「被拒绝」这一语义完全一致（`report.md` §六簇 1 最小复现块）。
- **机制（读源腿 + 测量腿双落证）**：根因不在 libiberty，而在**链接行次序**——
  bfd 的 libtool 依赖串把 `-ldl` 排在 `../libiberty/libiberty.a` 之前
  （`bfd/Makefile.am:59` `LIBDL = @lt_cv_dlopen_libs@`、`:748` `libbfd_la_LIBADD`、
  `libtool.m4:1741-1749` darwin 分支）；现代 macOS SDK 的 `libdl.tbd` 是 `libSystem.tbd` 的符号链接
  （install-name `/usr/lib/libSystem.B.dylib`），于是 `_getopt_long_only`/`_optind`/`_optarg`
  在归档被扫描之前已由 dylib 解析，libiberty 的 `getopt.o`/`getopt1.o` 永不入选。
  翻转变量 = autoconf 缓存量 `ac_cv_lib_dl_dlopen`。（`E/s4/getopt-rootcause/report.txt` §一/§二）
- **同一次构建内的天然对照（决定性）**：`readelf`/`elfedit` 不链 `libbfd.la`，链行无 `-ldl`，
  这两个工具的 getopt 导入数 = 0，与官方一致 ⇒ 同源码、同宿主、同 linker、同一次 make 内，
  唯一自变量就是 `-ldl` 的位置（同报告 §三）。
- **假设台账**：Hx（归档里没有 getopt.o）**证伪**；Hy（`HAVE_DECL_GETOPT=1` 导致不入选）**证伪**；
  Hz（linker 世代差异）**证伪**（`-Wl,-ld_classic` 结果相同）；H-core（次序假说）P1–P4 四组最小复现**成立**（同报告 §四）。
- **装置自证（字节级）**：H0 的 scratch 构建产出的 `gas/as-new` 与 S2 基线构建树的
  `as-new` **SHA256 完全相同**（`b1529aef295d54a4…`）⇒ H1 与 H0 的一切差异只能归因于那一个被翻转的缓存量（同报告 §四 H0）。
- **失败一轮如实记录**：H1-round1 把变量只加在顶层 configure ⇒ 未翻转，因为 binutils 由顶层 make
  递归 configure 各子目录、每个子目录有独立 `./config.cache`。**该量必须 export 且对 configure 与 make 两阶段可见**
  ——这是落点写法的硬约束（同报告 §四 H1-round1）。
- **终点判据**（Main R3 给定）：`as` stderr 前缀为 `argv[0]` 原文且与官方逐字节同 + `nm -mu` 无 getopt 导入。
  **达成**：`E/s4/getopt-rootcause/{endpoint-check.sh,endpoint-check.out}`；
  命令行解析面 10 例三方对照 `argv-surface.out`：候选 vs 官方 **10/10 逐字节相同**，
  S2 基线 vs 官方 4 例不同且差异**全部且仅仅**是前缀形态。
  全工具波及：单一变量一次性把 13 个偏差工具的 getopt 导入数从 3–4 打到 0，无残留、无反向劣化（同报告 §五）。
- **零扰动抽验**：`as --version`/`--help`、汇编诊断、34 个 `.o`、一组 `.o`/`.elf`/`.bin`、
  `ld --version`/`--verbose`/SEARCH_DIR、`objdump -dr`、`nm` 文本输出——全部逐字节相同（同报告 §五）。
- **对补丁布局零影响**：不产生任何源码补丁，不改编号、顺序或复放输入集（同报告 §六.4，实测复放已证）。
- **划界（如实）**：「官方 2018 年该检测为 no」是从产物 + 机制**反推**的结论，不是对 macOS 10.13 SDK 的直接观测
  （同报告 §七.5）。交叉佐证：官方 12.2.0 与 15.2.0 包（更晚宿主环境构建）与我方 S2 基线同病，
  即这确为随宿主 SDK 漂移的环境量。

### 5.2 簇 2：`nm` 的 LTO 插件 dlopen 诊断（6 条）——**characterization-corrected**

这一簇的价值不在数字，而在**一次被取证反转的定性**。四段史如实登记：

1. **旧定性（保留不改，`report.md` §六簇 2 原文）**：`ref/gcc/darwin-arm64/8.2.0/lib/bfd-plugins/liblto_plugin.so`
   是 59 字节 ASCII 文本，内容恰是符号链接目标串；判为 `extract-wch-toolchain.sh` 把符号链接压平的**抽取失真**，
   并据此断言「S1 归档在这 6 条上记的不是 WCH 真实行为」，建议修脚本 + 重抽 `ref/`。
2. **Main 2026-08-17 取证反转（R4）**：该 59 字节文本与**源 app bundle 内同路径文件逐字节相同**（`cmp` IDENTICAL）
   ——抽取脚本忠实，无失真。真相是 **WCH darwin 8.2.0 包自身把一类 symlink 扁平化成了文本文件**，
   全类共 **7 个条目**（均 2023-09 时间戳）：`lib/bfd-plugins/liblto_plugin.so`、`lib/libcc1.so`、
   `libexec/lib{readline,expat,z}.dylib`、`plugin/lib{cc1,cp1}plugin.so`。
   对照面：12.2.0 同名文件是真 Mach-O、linux 15.2.0 是真 ELF ⇒ 纯 8.2.0 darwin 包装缺陷。
   （`E/s4/defect-fidelity/characterization-correction.txt`）
3. **处置**：a) 不修 extract 脚本、不重抽 `ref/`（参考物保持 as-shipped，差异即信息）；
   b) 我方 install 把同一份 59 字节文本**原样纳入注入面**——缺陷保真：官方 `nm` 对文本文件 dlopen 报错，
   我方必须同样报错（`inject_bfd_plugins`，`verify_pair` sha `0e1f88e299fe0fce…`，两侧 `cmp` IDENTICAL）；
   c) 这 6 条探针的**基线 = as-shipped 行为**，S1 归档是正确记录。
   `cluster2-probe/`（原「布局修正」实验）降级为机制证据存档，落 `DOWNGRADED.txt`，不参与 gate 判定。
4. **重跑与转类**：注入面补齐 + 簇 1 修正落地后重跑（runE），MISMATCH 25 → 6，簇 1 的 19 条全转 IDENTICAL。
   剩余 6 条**两侧都产生 dlopen 报错、报错结构完全同类**（同样 6 次尝试、4 次 `slice is not valid mach-o file` + 2 次 `no such file`），
   只差各自安装前缀那一段路径。此处 **Main「逐字节同」的预测字面不成立、行为保真已达成**：
   报错文本内嵌的是 `bindir/../lib/bfd-plugins` 绝对路径，由各侧真实安装位置推出，跨侧必然不同。
   按既有安装前缀判据整条转 **EXCLUDED**，并补**同路径顺序对照替身** `17-nm-plugin-samepath`：
   两侧先后占用同一个 scratch 绝对路径 `P`，按 `bindir/../lib` 相对布局摆放该侧 `nm` 与该侧那份 59 字节文本，
   于是 dlopen 诊断变成路径无关的可比面（EXCLUDED 是分类，不是 normalize）。
   **结果：36 个产物逐字节比较 diff = 0，16 条探针行全 IDENTICAL；rc/stdout/stderr 三项全部回到 gate，覆盖零损失。**
   as-shipped 断言留痕 `as-shipped-assert.tsv` 两侧同（6 行、`rc=0`、`stderr_bytes=1225`、`dlopen_hits=1`）
   ——证明这是「两侧都报错且报错同类」，不是「两侧同时静默」这种假绿。
   （`report.md` 增量修订节 §五新增行、§六簇 2 更新、§六之二）

### 5.3 与 gate 的关系

两簇自始至终**不触碰任何 `.o`/`.elf`/`.bin` 字节**，收口 gate 的 42285/42285 不受影响；
但它们落在硬约束 1 点名的「诊断文本保真面」内，故当初按**升级**处理而非自行豁免——
探针执行者两次都把问题原样回传、不自裁（`report.md` §六两处「建议路由（不自决）」），
两次裁定都由 Main 作出。这条路径本身是本阶段可复用的做法。

---

## 6. `.map` / `.lst` 归因与 R5 豁免

aux 面 699 条残差 = 698 `.map` + 1 `.lst`，两类都已归因关闭、且都不入 gate。

### 6.1 `.map`（698 条，S3 归因）

`E/s3/map-attribution/map-attribution.md`，三个代表工程逐行对齐分类，**「其他/未归因」恒 0**：

| 类别 | v3b-pioc | v3f-gpio | v3f2-gpio |
| --- | --- | --- | --- |
| 工具链根路径前缀长度差（每处 +38 B） | 274 | 324 | 324 |
| 符号/段真实尺寸差 | 1 | 0 | 0 |
| 级联地址位移（全部 delta = −2） | 205 | 0 | 0 |
| fill 补偿行 | 1 | 0 | 0 |
| 其他 / 未归因 | **0** | **0** | **0** |
| Σ | 481 | 324 | 324 |

文件级尺寸差 100% 由根路径串解释：出现次数 317/324/324，317×38 = 12046、324×38 = 12312，
与三文件字节尺寸差**精确相等**。

**全覆盖机械核对（审计 P3 第 3 条，本轮补做）**——上表的逐行归因只做过 3 个工程，
其余约 695 个文件此前靠机制外推。本轮把结论升为**全覆盖实测**：
`E/s4/audit-sweep/map-full-sweep/`（脚本 `map_full_sweep.py`、明细 `map-full-sweep.tsv`、`summary.txt`）
对 `stage-replay/aux-mismatches.tsv` 里**全部 698 个 `.map`** 逐文件断言

```
ours_size − canonical_size == count(官方包根绝对路径串) × 38
```

其中 38 = `len(我方安装根)` − `len(官方包根)`（脚本内现算，不写死：
官方根 `/Users/apple/Projects/openwch/ref/gcc/darwin-arm64/8.2.0` 长 56，
我方根 `/Users/apple/Projects/openwch/tmp/toolchain_8.2.0/work/darwin-x64/install/riscv-none-embed-gcc` 长 94）。

**结果：698/698 全部成立，残余恒 0。** 分项：磁盘缺件 0、
**两侧文件 sha256 与 `aux-mismatches.tsv` 记录值不符 0**（输入未漂移的自证：核对的就是认证那轮的字节）、
两侧出现次数不等 0、`(尺寸差 − 次数×38) ≠ 0` 的文件 **0**。
出现次数的实测分布 min 33 / max 753 / Σ 227293，三个 S3 锚点在本表内复现
（`QingkeV3B_CH32V205/EXAM/PIOC/*` 系 317 次 → 12046 字节；
`QingkeV5F_CH32H417EVT/EXAM/GPIO/GPIO_Toggle/V3F` 324 次 → 12312 字节）。
⇒ **`.map` 面从「3 个工程逐行 + 695 个机制外推」升为「698 个文件全覆盖机械核对」**，
「其他/未归因」在文件级尺寸维度上恒 0。（S3 的逐行分类仍只有 3 个工程，那是更细的粒度，未扩展。）v3b 唯一真实内容差在 `.text.PIOC_IRQHandler`（官方 0x16 vs 我方 0x14），
与 D4（官方 `mret` 4 B vs 当时我方 `ret` 压缩 2 B）算术闭合——D4 落地后该内容差归零，
留下的仍是路径前缀类（同文件 §对 gate 的意义）。

### 6.2 `.lst`（1 条，S4 归因，**闪烁类**）

对象 = 全量 index 955（`QingkeV5F_CH32H417EVT/…/HSEM_DataSharing_V3F`）的 `obj/*.lst`，
`E/s4/lst-attribution/lst-attribution.md`：

- **差异 = 5 行，全部是同一地址上多个符号之间的择名不同，合计 +6 字节，残余未归因 = 0**
  （`0x20110100` `HBPrescTB`↔`_data_vma` 等长 ×2 行、`0x20178000` `_eusrstack`↔`Data_Sharing` 每行 +2 B ×3 行，
  0×2 + 2×3 = +6，与文件尺寸差 197855→197861 精确相等）。
- **被反汇编的 `.elf` 两侧逐字节相同**（`70bab86e…6b6da`，golden manifest 与 `stage-ours/ours-artifact-results.tsv` 同值，
  `.bin` 亦 MATCH）⇒ 差异不可能来自生成代码。
- **铁证 = 双向交叉复现**：剥掉 objdump 回显 argv 的第 2 行后，正文 `f01030fd…` = 归档官方件 = 我方 objdump 的稀有分支；
  `b9d2a121…` = 归档我方件 = 官方 objdump 的多数分支。**两只 objdump 都能产出两种结果。**
- **机制**：binutils 2.32 `objdump.c:793-796` 在符号值相等后比较两个 `asection` 结构体的**运行期指针**，
  两符号段不同 ⇒ 必然在此返回，其后六级判据一条都不参与；`asection` 由段名哈希表经 `objalloc` 分配，
  chunk 直接来自 `malloc`（`libiberty/objalloc.c:159`，`CHUNK_SIZE = 4096-32`），跨 chunk 地址高低由宿主 malloc 决定——**每进程抽签**。
- **翻转率同分布**：16 路 × 200 轮 = 3200 次/每只二进制，官方 **8/3200**、我方 **4/3200**，
  6400 次里只出现两种结果、两对符号永远同时翻转从无混合；宿主 malloc 最小实验（mode 1 交错分配）倒挂率 2/1600，同数量级。
- **`.lst` 逐字节一致不是可达成目标**：同一只二进制、同一输入、同一 argv **复跑本身就会翻**。
- 类别账目含显式零项：路径前缀类 **0**（objdump 只回显 argv 里的 elf 路径，而两条 lane 的 objdump argv 逐字相同）
  ——与 `.map` 的性质正好相反。

**R5 裁定：`.lst` 闪烁类豁免成立**（Main 2026-08-17）。本报告按裁定把两侧翻转率
（官方 8/3200、我方 4/3200）与「复跑亦翻」写入前提登记（§14 P-08）。

---

## 7. testsuite 账目

### 7.1 六个验收面（终栈双 objdir 上采集）

`E/s4/testsuite-final/report.txt` §2，逐面「基线 → 逐簇增量 → 预期 → 实测 → 判定」：

| 面 | 基线 | 增量 | 实测终值 | 对基线 |
| --- | --- | --- | --- | --- |
| A gas 全量 | pristine 165P/0F/3XF/7U/1W | D2 +13、D3 +5 | **183P / 0F / 3XF / 7U / 1W，TOTAL 194** | removed=0 / added=18 / removed_PASS=0 / added_non_PASS=0；18 元组与 D2 的 13 + D3 的 5 集合**逐字相同** |
| B objdump `.d` 面（gas 子集） | 0 | D3 +5 | 5 例全 PASS，`xw-*` 全族非 PASS 计数 0 | 闭合（`xw-dis`/`-imm`/`-no-aliases`/`-numeric`/`-off`） |
| C gcc.target/riscv | pristine 59 元组（48P/2F/2UR/6U/1W） | D4 +67 | **126 元组：115/2/2/6/1** | removed=0 / added=67；67 元组与 D4 存档集合**逐字相同**（`diff/added-set-identity.diff` 为空）；既有 2F/2UR 原样保留（`pr84660.c`、`save-restore-1.c`，pristine 即如此） |
| D gcc.dg/dg.exp | vanilla 22143 元组 | 0 | 22143 元组，11 个状态计数逐一相等 | removed=0 / added=0（663 FAIL 是 vanilla 基线自带：老代码基 + 交叉目标无模拟器） |
| E g++ attrib | vanilla 369 元组 | 0 | 369 元组，计数逐一相等 | removed=0 / added=0 |
| G params.exp | vanilla 261 元组 | D4 +2 | **263 元组：262P / 1W** | added=2，恰为 `blocksort-part.c -O3 --param highcode-gen-section-name={0,1}`（params.exp 对每个 param 取 min/max 各跑一次，新增 1 个 param 理应恰好 +2） |

**D4-02 防护与 `Running` 断言**（同 objdir 串行、跨 objdir 并行）：六个 slot 的断言逐个命中；
gas 的 `Running` 行总数 **130**，与 pristine/D2/D3 同值 ⇒ 遍历的 `.exp` 集合未变；
四个 gcc slot 的 `Running` 行总数各为 1，直接证明三个共用 `testsuite/gcc/gcc.sum` 的 `check-gcc`
调用没有互相覆盖（report.txt §3）。

### 7.2 附加对照面 F（check-binutils）与其归因

**非验收项、无 pristine 基线。** 参考值取 D3 的附加跑（67 元组：50P/1F/12UNTESTED/3U/1W），
终树实测 67 元组：53P/1F/9UNTESTED/3U/1W，差额 removed=3 / added=3，且 `removed_PASS=0`、`added_non_PASS=0`
——三例 `strip` 系由 UNTESTED 转 PASS。

**归因已实验复现、非推断**：这三例在 `objcopy.exp` 里以 `target_compile testprog.c` 为前置（`objcopy.exp:414`），
D3 那次是临时 shell 的 ad-hoc 运行（其 `binutils-make.log` 首行是 Xcode 里的 make，`binutils.log` 内 `testprog` 出现 0 次）。
**单变量对照实验**：在同一个终树 objdir 上只把 PATH 换成不含工具链 bin 的版本重跑，得到 50P/1F/12UNTESTED/3U，
与 D3 存档 `binutils.sum` **元组逐条相同**（removed=0/added=0），连 `UNTESTED: strip` 在 log 中的行号位置都一致。
⇒ 差额 100% 由「目标 C 编译器是否在 PATH 上」决定，与任何补丁无关，方向是覆盖增加。
唯一 FAIL 仍是 `nm --size-sort`，D3 已三侧对照判定为既有现象（`E/s3/d3/nm-sizesort-triage/`）。

### 7.3 pinned objdir 附录（补一个口径缺口）

面 A 的 183P/0F 测在 `dev-build-s4-suites` 的 objdir 上，该 objdir configure 时**未带**
`ac_cv_lib_dl_dlopen=no`（getopt 修正晚于其配置），即被测 `as-new` 链的是 libSystem getopt，
而**交付配置**链的是 libiberty getopt。`argv-surface` 10 例论证了可迁移性，
但按本工作流「测量优先于论证」的口径补了一次实测：在**复放构建的 binutils objdir**
（tree `8d0d7da3c…` == 开发树，configure 含该缓存钉子）上 `cd gas && make check`——
**183P / 0F / 3XF / 7U / 1W，TOTAL 194，`Running` .exp 行 = 130，riscv.exp 断言命中**，
与面 A 账目逐项相等。gcc 面不受影响（脚本在 gcc 段前 `unset` 该变量）。
（`E/s4/testsuite-final/addendum-pinned-objdir-gas.txt`；原始件 `E/s4/replay/check-gas/{gas.sum,gas.log,make-check.log}`）

### 7.4 两项编排裁定与一处如实缺口

`E/s4/testsuite-final/orchestrator-rulings.txt`：
- **S4-03**（「binutils/objdump `.d` 面」的解读）：裁定 = 执行者解读正确。D3 的 5 个 `.d` 用例落在 gas 套件，
  故「`.d` 面」= gas 套件内由 objdump 驱动的用例；check-binutils 作为另一解读的覆盖跑保留为附加对照面，不升为验收项。零返工。
- **S4-02**（面 F 无 pristine 基线）：裁定 = **不补**。验收账目立在六个有基线的面上；面 F 的 3 元组差额已由
  单变量对照实验逐条闭合且方向为覆盖增加。**该缺口如实登记**（见 §15）。
- 验收：SHA256SUMS **140/140 编排独立复验 0 失败**；`report.txt` 为耐久副本（DEV-P6-05 同款回退）。

---

## 8. 偏差登记表（DEV-P6-01…09 全量）

原件 `E/deviations.tsv`（表头 + **9 行**）。全部为执行过程/文档问题，无一为产物问题；**九条全部 closed**。
（原文写「01…06 全量 / 表头 + 6 行 / 六条」，为审计修正轮之前的时点，旧值保留在本句里；
07–09 三条产生于独立审计与其修正轮，逐条列在本表末。）

| id | 阶段 | 偏差 | 处置 | 状态 |
| --- | --- | --- | --- | --- |
| DEV-P6-01 | S1 | 谱系 agent 对自建可再生 scratch（`lineage/downloads/tagtree/.../tests`）误用一次 `rm -rf`，违反「破坏性操作先问」硬规则 | 从保留 tarball 原样重解恢复，diff 复验结论不变，无证据损失；agent 自报。Main 登记接受并附纪律提醒：`rm -rf` 前先在日志声明目标与理由（后续 prompt 已注入该要求） | **closed** |
| DEV-P6-02 | S1 | `probes/README.md` 门控行原稿（「恒在 opcode 表内、无 `xw` 一律 `illegal operands`」）对无 `c` 基座不成立 | 以 optsweep 反汇编证据 + 编排会话 8-march 裁定探针（stderr 哈希三聚类）行内标注更正；证据 `probes/raw/05-xw-encodings/gating-correction/` | **closed** |
| DEV-P6-03 | S1 | 编排会话一次裁定探针误用残留相对 cwd，证据目录被嵌套建到 `probes/work/` 下；另有一个临时文件短暂落 `/tmp` | 目录搬正并原地复跑复验（`SHA256SUMS.gating-correction` 全 OK）；`/tmp` 文件删除；后续命令一律绝对路径 | **closed** |
| DEV-P6-04 | S1 | Main 身份冲突（`openwch-05` 与 `openwch-f4` 均自称 Main） | 转录指纹核验 + 用户原话指定 + `openwch-05` 关闭，地址固化 `openwch-f4`；全程 `main-identity-log.md`；Main 回执确认分阶段口径解释 | **closed** |
| DEV-P6-05 | S2 | 转换器执行者环境被 harness 禁写 `.md`，`report.md` 无法由执行者落盘 | 编排会话按执行者回传原文逐字持久化 `E/s2/converter-gcc8/report.md`，并抽验 0 字节证明（`additivity/diff.txt`、`parity.diff`）与 logs 计数；机器证据本身未受影响。此后成为本阶段惯例（census / map-attribution / defect-fidelity 同款） | **closed** |
| DEV-P6-06 | S3 | 编排会话执行 Main 批准的 message 修正时误用 `git cherry-pick -q`（无效旗标）致 cherry-pick 未执行、短暂产生缺第二 commit 的 HEAD，且首份 after 记录块无效 | 立即补 cherry-pick（`f4d855414`）；`amend-quad.txt` 以更正块为准（旧块标注失效）；四元组验证新 B/C 的 tree 与 stable patch-id 与旧值逐一相同 ⇒ 按 phase-3d message-only 先例，既有 quick 242/242 证据继续适用；author 身份差异留待 S4 元数据统一 | **closed**（遗留项已由 §2.3 的导出单元 discharge） |
| DEV-P6-07 | S4 审计 | D1 补丁把「吃 `w`」嵌进「吃 `x`」分支，与官方「顺序独立两步」语义相反（`rv32imacw`/`wx`/`ww` 三判别轴反向；25 条 spec-probe 全含 `x` 致判别轴全盲）；commit message 文字正确、代码相反 | 审计 P1-1 发现；编排会话五轴亲测复证（官方 cc1 放行 `rv32imacw`、由 as 拒绝）；修正 = 一行反缩进 + 注释更正，折入 D1′ 重建栈（`bd000fc87`，patch-id `7f03544f9`；D4a′/D4b′ patch-id 不变；终树 tree 不变式 `3260ccd87` 验证）；同批把判别轴补成常设探针组 18；复验口径见 §2.4 | **closed** |
| DEV-P6-08 | S4 修正轮 | 编排会话重演 DEV-P6-06 同款 `git cherry-pick -q`（无效旗标）致栈重建序列在 D1′ 后中断、`$TIP` 空值下 `branch -f` 短暂把 master 指到不完整栈 | 即时发现（输出可见 usage 错误），`--quit` 清序列后补 cherry-pick D4a/D4b，树不变式与 patch-id 全部复验通过；教训：`cherry-pick` 无 `-q` 旗标，本条为该教训第二次登记 | **closed** |
| DEV-P6-09 | S4 审计 | `tmp/golden/toolchain-current` 复位依赖编排会话手工操作而非脚本保证，Main 复测后悬置于我方 install；checklist「每用必复位」表述过强 | 审计 P1-2；已复位进场值；两 harness 脚本 `cleanup()` 加原值捕获 + 还原（单列 diff 44 行，`E/s4/p1-2-harness/cleanup-restore.diff`，另存改动前副本 `p1-2-harness/pre/`）；checklist 表述已撤改 | **closed** |

---

## 9. harness 改动单列

原件 `E/s2/harness/harness-8.2.0-routing.diff`。触及**两个文件**：`scripts/evt-compare.sh`（2 处）、
`scripts/evt-golden.sh`（其余）。四类改动：

| 类 | 内容 | 位置 |
| --- | --- | --- |
| ① 版本路由 | `evt-compare.sh` 两处 `case` 加 `8.2.0`（version 表与 version/platform 表）；`evt-golden.sh` 三处（usage 串、version `case`、platform `case`） | hunk @L5、@L14（compare）；@L27、@L36、@L45（golden） |
| ② EXCLUDED 语义 | `evt-golden.sh` 的 run1 构建失败分支由 `[ "$version" = 12.2.0 ]` 扩为再或上 `[ "$version" = 8.2.0 ]`，即 8.2.0 沿用 12.2.0 的「构建失败 ⇒ EXCLUDED 而非 FAIL」语义（对应 `v3c-led` 的 `mcpy`） | hunk @L75 内 `run1 build failed` 段 |
| ③ 16-worker 迁移 | 循环体提取为 `process_slug()`（全部局部变量 `local` 化），worker 把 body/meta/status 与四个计数器写 per-slug 文件，父进程**按项目表序**拼接求和 ⇒ **manifest 与 stdout 的状态流**与串行一致（**保证范围见下方 P2-17 注**）；slug→`.wvproj` 解析与 `[ "$project_count" -eq 9 ]` 表校验**上提到并发之前**（表错误是 harness 配置错误、必须中止整跑，而后台子 shell 无法中止父进程）；bash 3.2 无 `wait -n`，满池时等待最旧成员；`workers=${EVT_GOLDEN_WORKERS:-16}` | hunk @L63、@L75、@L168、@L204、@L240 |
| ④ BSD-awk 可移植性 | `END { print flags == "" ? "none" : flags }` → `END { print (flags == "" ? "none" : flags) }` | hunk @L54（`debug_flags_from_makefile`） |

> **【「与串行一致」的保证范围，2026-08-17；审计 P2-17】** 该保证覆盖的**恰好是走 per-slug 文件的那部分**：
> manifest 正文/元数据/状态流与四个计数器。**不覆盖** worker 直写 stderr 的三类诊断——
> `show_failure_excerpt`（含 `head -c 65536` 的日志摘录）、`NONDETERMINISTIC` 行、
> `missing required gate artifacts` 的 FAIL 行——多工程同时失败时这些摘录会在终端上交织，人工归因应改看 manifest。
> 已在 `evt-golden.sh` 的并发段注释里就地写明（单列 diff `E/s4/p1-2-harness/audit-p2-16-17-golden.diff`）。
> 同处登记一条覆盖事实：**精选集只有 9 个 slug < 16 workers，满池等待分支在实际运行中从未执行过**。
> 另按 P2-16 修正了 `last_error_line()`：`make -jN` 下失败日志的末行是
> `make: *** [target] Error 1` / `make: *** Waiting for unfinished jobs....` 这类包装行，
> 记进 manifest 的 `# excluded[...]` 头等于没记诊断；现改为「末行是 make 包装行 ⇒ 回退到最后一条真实诊断
> （`file:line: Error:` / `fatal error:` / `undefined reference`），再回退到最后一条非 make 行」。
> **实测复验**：对 `tmp/golden/8.2.0/v3c-led/logs/run1-build.log` 与 S1 的
> `buildability/logs/v3c-led.probe-r1.err` 两份真实日志，新逻辑均取到
> `…/core_riscv.h:645: Error: unrecognized opcode \`mcpy a2,a1,a5'`（旧逻辑取到 `make: *** Waiting…`）。
> **注意**：该修正只对**今后重生成**的 manifest 生效；已入库的
> `analysis/golden/8.2.0-darwin-arm64.tsv` 头部仍是旧串，本轮**不重生成** golden（重生成需重跑官方侧、
> 会动 `toolchain-current`，属口径外动作）。

**装配守卫**：拼接阶段以 `[ -f "$temporary_dir/$slug.counts" ] || die` 收敛——`.counts` 是 worker 的最后一次写，
写不出来必被 `die`（`evt-golden.sh:15-18`，退出码 **2**），失败不会被静默吞掉。
这与 phase-3h 对 `evt-compare.sh` 做同类迁移时的守卫位置一致（`analysis/toolchain/phase3h-closure.md` §3）。

**规模复核（口径写死；两种数不能混读）**——同一份改动有两种常见计法，本报告一律成对给出：

| 时点 | 归档件 / 命令 | **raw diff 行数**（含 `---`/`+++`/`@@`/上下文） | **`--stat` churn**（纯增删） | hunk |
| --- | --- | ---: | --- | ---: |
| S2 归档态 | `E/s2/harness/harness-8.2.0-routing.diff` | **296** | `113 insertions(+), 51 deletions(-)` | 11 |
| 终态（含 P1-2 与 P2-16/17 修正） | `git diff -- scripts/evt-{compare,golden}.sh` | **377** | `148 insertions(+), 53 deletions(-)` | 17 |

终态 = S2 归档态 + 两笔审计修正：**P1-2**（两脚本 `cleanup()` 加原值捕获 + 还原，单列 diff 44 行，
`E/s4/p1-2-harness/cleanup-restore.diff`）与 **P2-16/17**（`evt-golden.sh` 三处，单列 diff 54 行，
`E/s4/p1-2-harness/audit-p2-16-17-golden.diff`，改动前副本 `p1-2-harness/pre-audit-fixes/evt-golden.sh`）。

> **登记一处对不上的数（已闭合）**：`E/SESSION-STATE.md` L38 一带、`tmp/prompts/phase-6.checklist.md` L30
> 与 `analysis/toolchain/phase6-literal-surface.md` §4 曾记该 diff 为「287 行」，该值**无法由现存档案复推**。
> **现状：三处均已勘误为 296 并附勘误注**（现场复核逐处确认），Main 侧台账亦已按 296 下达
> （SESSION-STATE 终态回执第 ① 项）。287 的来历不作猜测，仅作旧值留痕。

> **另一处口径混读（审计 P3；本轮统一）**：本报告 §15 提到的转换器 GCC8 分支「143 行」是
> **`--stat` churn**（`1 file changed, 123 insertions(+), 20 deletions(-)`，123+20=143），
> 而 harness 的「296 行」是 **raw diff 行数**——两者不是同一种计法。
> 统一写法：转换器 = **`123+/20−`（raw diff 264 行）**；harness S2 归档态 = **`113+/51−`（raw diff 296 行）**。

---

## 10. 全量普查（census）第 7 节：偏差与未决五条

`E/s3/full-census/census-report.md` §7 逐条转录（**a–e**）：

- **(a) `lib:missing` 归类——已由 Main 于 2026-08-17 重裁为 `config`，分区 capability 126 / config 2。**
  > **【重裁记录，审计 P2-3】** 原判 capability 所依据的**区分测试是事实错误**：
  > `full-exclusions.tsv` 的 `ruling-note` 曾写「`ref/gcc/darwin-arm64/8.2.0` 树内**无** `libprintfloat.a`」，
  > 而一条 `find` 即得相反结论——包内实有 **6 份** `libprintfloat.a`（`rv32ec/ilp32e`、`rv32ecxw/ilp32e`、
  > `rv32imac/ilp32`、`rv32imacxw/ilp32`、`rv32imafc/ilp32f`、`rv32imafcxw/ilp32f` 六个 multilib 子目录）。
  > **正确机理**：CoreMark 的 `.cproject` 把 atomic 置 false ⇒ 转换器给出 `-march=rv32imcxw` ⇒
  > 该串**不在 23 项 multilib 表内** ⇒ `-print-multi-directory` 回落 `.` ⇒ 落到只有
  > libc/libg/libm/libgloss/libnosys/libsim 的默认库目录，故 `ld` 找不到 `-lprintfloat`。
  > 决定性反证实验：把 `-march` 改成 `rv32imacxw` 后**官方工具链 LINK OK**。
  > 按 ruling 自身的定义（config = 工程/环境层可修）该行属**工程层一改即通** ⇒ 判 **config**。
  > **Main 已按此机理重裁**（commit `cb66c29`，`analysis/golden/8.2.0-darwin-arm64-full-exclusions.tsv`
  > 的 `# ruling-note(改判 2026-08-17, 审计 cb66c29)` 行；原判据行保留于历史）。
  > 同一错误的另一处 `census-report.md §4.1` 表格「8.2.0 包内不含该库」亦已随之重写（§4.1/§4.2/§7(a)）。
  > **gate 面 42285 两种判法均不受影响**（该工程在两种判法下都出局）。
  > 旧值留痕：本条原文「Main 已裁定 `lib:missing = capability`，分类维持 127 / 1」。
- **(b) `summary.json` 的 `gate_artifacts` 字段名不准**：其值 85257 实为 PASS 工程全部产物行（含 `.d` 等 aux），
  真实 gate 数 **42285** 以 manifest 与 `render-audit.json` 为准。未回改 runner 源文件——
  marker 内 `input_hashes.runner` 记录实跑版本哈希，回改会使证据自相矛盾。
  > **【字段定位勘误 2026-08-17，审计 P3】** 该字段在 **`E/s3/full-census/stage-a/summary.json:12`**
  > （`"gate_artifacts": 85257`，现场复核行号），**不在** `stage-replay/summary.json`；本条原文的定位写偏，旧指针留痕。
  > 实质结论不变，且三方哈希相等：census 85257 = gate 42285 + aux 42972。

**Main 侧同批已办四项（本报告引用，非本工作流动作）**——commit `cb66c29`：
① R3–R6 等裁定批次入 `DECISIONS.md`（审计 P2-8）；② 12.2.0 / 15.2.0 源码树基线哈希取录（四树 HEAD/tree、dirty=0，审计 P2-5）；
③ 不注入 `ldscripts` 追认为设计决定（审计 P2-15，见 §11.1 观察 1）；④ `lib:missing` 以正确机理重裁（上条 (a)）。
- **(c) `effective-project-inventory.tsv` 的 `march`/`abi` 两列恒为 UNKNOWN**：phase-3b 继承代码读
  `resolved_flags["march"]`，转换器实存 `resolved_flags["target"]`。信息未丢（`debug_flags` 列逐字带 `-march=`），
  继承缺陷，沿用不改。
- **(d) quick lane 与 full lane 中性根不同**：quick golden 用 `tmp/golden/toolchain-current`（编排会话独管，本轮零触碰，
  命令账本 0 处引用），full lane 用逐工程 `<project_root>/toolchain-current`。带 `-g` 工程的 `.o` 因
  `-fdebug-prefix-map` 目标不同**不可跨 lane 比哈希**；PASS/FAIL 面一致（§5：精选 9 工程 index 15/87/201/352/417/505/667/792/950，判定 9/9 与 quick golden 一致）。
- **(e) 并发会话观察**：运行期间仓库有其他会话改动（`scripts/evt-golden.sh`、`scripts/evt-compare.sh`、
  `toolchain-current` 重指向——均为编排会话已知操作）。对本轮无影响：`summary.json` 的 immutable pre/post
  证明转换器、`patches/`、EVT patches、tests harness 整轮 715 s 内哈希未变；`evt_exact_restored=true`。

（同报告 §3 另记一条不属 §7 但对读数关键的政策：**全量只跑一趟**，另做「一个 `-g` 工程 + 一个非 `-g` 工程」各两趟的
同路径自检，以及 smoke 轮与全量轮相隔约 10 分钟的 107/107 跨轮独立复核；失败工程的 `-j1` 串行重跑触发 **0** 次。）

---

## 11. gate 外观察

### 11.1 三条（原文出处：`E/s4/transcript-recovery/reports-outbound.md` L177 里程碑 #4 块）

> 「gate 外观察三条留档（官方包 ldscripts 旧构建路径残留、我方 lib/gcc 少 6 个无关文件、`--version`/configure 行逐字同）。」

细节原件 `E/s3/full-ours/run-record.txt` §9（L88–101）：

1. **官方包 ldscripts 旧构建路径残留**：`riscv-none-embed/lib/ldscripts` 下 **40 个**已安装脚本文件两侧不同——
   官方包里的脚本写的是 `/Host/home/wch/Work/riscv-none-embed-gcc-8.2.0-3.1/linux-x32/…`，
   而**同一个包自己的 `ld` 与 gcc configure 行**写的都是 `/Users/wch/Work/riscv-none-embed-gcc-10.2.0-1.2/darwin-x64/…`
   ⇒ 官方包发的是另一次更早构建留下的 ldscripts。我方这 40 个与自身前缀自洽。
   EVT 工程一律用 `-T` 指定链接脚本、内建脚本不参与，gate 不受影响（本轮已证）。
   **【定性升级 2026-08-17，审计 P2-15】** 不注入 `ldscripts` 是一项**写在脚本里的设计决定**
   （`build-toolchain-8.2.0.sh:389` 的 `[ "$base" = ldscripts ] && continue`），与「完全逐字复用 WCH 随包库」
   的库策略构成一处**有意偏离**；此前只以「gate 外观察」形式披露。**Main 已于 2026-08-17 追认为裁定项**
   （DECISIONS，commit `cb66c29`），本条自此按「已追认的有意偏离」读，不再只是观察。
2. **我方 `lib/gcc` 树少 6 个官方文件**：`include/gcov.h`、`include/unwind.h` 与 4 个 `plugin/libcc1*.so`；
   1170 个工程无一需要它们。随包库本身逐字节相同（`libc.a`、`libm.a`、`libgcc.a`、`crt0.o`、全部 multilib、全部目标头文件）。
3. **`--version` 与完整 “Configured with:” 行逐字节相同**；`ld --verbose` 的 SEARCH_DIR 亦逐字节相同。

### 11.2 第四条：7 条目 symlink 扁平化全类（R4）

按 Main R4 裁定并入 gate 外观察（`characterization-correction.txt` 末段）：
WCH darwin 8.2.0 包自身把一类 symlink 扁平化成了文本文件，全类 **7 个条目**（均 2023-09 时间戳）：
`lib/bfd-plugins/liblto_plugin.so`、`lib/libcc1.so`、`libexec/lib{readline,expat,z}.dylib`、
`plugin/lib{cc1,cp1}plugin.so`。12.2.0 darwin 同名文件是真 Mach-O、linux 15.2.0 是真 ELF ⇒ 纯 8.2.0 darwin 包装缺陷。
取证证据（源包 `cmp`、7 条目清单、跨版本对照）由 Main 持有。

**与第 2 条的交集值得点一句**：观察 2 里「少的 4 个 `plugin/libcc1*.so`」与本条 7 条目中的
`plugin/lib{cc1,cp1}plugin.so` 指向同一批打包产物。我方通过 `inject_bfd_plugins` 补回的**只有
`lib/bfd-plugins/liblto_plugin.so` 一项**——那是 R4b 明令的注入项，因为 `nm` 的插件查找路径上正需要它
（§5.2）。其余 6 个条目未补：它们不落在任何被测行为面上（既不在 gate 产物路径上，也不在探针集覆盖的
调用路径上），故本阶段无补入依据。
（注意读数边界：run-record §9 关于「1170 个工程无一需要」的证据只覆盖 `lib/gcc` 树少的那 6 个文件，
**不覆盖** `lib/libcc1.so` 与 `libexec/lib{readline,expat,z}.dylib`——后者的「未补」理由是上一句的行为面判据，不是那条证据。）

### 11.3 Main 里程碑 #4 回信的其余两点

- 「就地裁定确认：源码树补丁 commit 不加 Claude trailer，正确……S4 复核时按此口径。」
- 「S4 序列照报文批准，两点要求：① `.lst` 有界归因按 `.map` 同标准；② closure 报告按 phase-3h 模式含偏差登记表全量……」
  （逐字摘录 `E/s4/transcript-recovery/index.md` L19–20；两项要求分别落在本报告 §6.2 与 §8。）

---

## 12. 三版本反汇编面对照（D3 全空间扫描 vs 15.2.0 的表序问题）

Main 里程碑 #4 回信第 1 点原文（`E/s4/transcript-recovery/main-inbound.md` L355，同信三阶段重复于 L371/L387）：

> 「D3 的 49152 半字全空间扫描把「8.2.0 无表序问题」从断言升为实测、并反向确认 15.2.0 0007 表序改动的版本特异性——这条跨版本事实写进 closure（三版本反汇编面对照）。EXCLUDED 抽样同失败 + 首诊断逐字同官方的"零超集信号"验证做得对。」

### 12.1 8.2.0 侧：实测

`E/s3/d3/sweep.sh` 枚举全部 **49152** 个低两位 ≠ 3 的 16 位半字（整个 16 位压缩解码面），
以 `-b binary -m riscv:rv32` 直接喂反汇编器（**绕开汇编器**），五种模式下三侧对比（`sweep.tsv`）：

| 模式 | mine vs official | vanilla vs official | mine 差异行 | vanilla 差异行 |
| --- | --- | --- | ---: | ---: |
| `default` | SAME | SAME | 0 | 0 |
| `no-aliases` | SAME | SAME | 0 | 0 |
| `xw` | **SAME** | DIFF | 0 | 8749 |
| `xw,no-aliases` | **SAME** | DIFF | 0 | 8749 |
| `xw,numeric` | **SAME** | DIFF | 0 | 8749 |

两条结论同时成立：默认面三侧一致 ⇒ D3 未动默认解码；`xw` 三模式我方与官方**零分歧**，
而 vanilla 与官方差 8749 行 ⇒ 比较仪器对这一簇改动有区分力。
（`sweep.sha256` 记 15 份 stdout 的哈希；该扫描在 S4 探针集里以 **100% 全空间重放**再跑一次，
`probes.tsv` 的 K2 类 5 明细 + 1 派生表全 IDENTICAL，`rvc.bin` sha `515345edcbce69f0…`。）

### 12.2 为什么 8.2.0 不需要 15.2.0 的表序搬移

机制差在**两族表项的匹配函数形态**（`E/s3/d3/acceptance.txt` 附加诊断段 + 同文件「与 D2 门的衔接」段）：

- **8.2.0**：D2 引入的 `match_with_wch_rvc_extension` / `match_without_wch_rvc_extension` 是**互补**的一对，
  XW 表项与 `c.f{ld,sd}{,sp}` 表项分别挂这两个函数 ⇒ 同一码字在任一旗标取值下**只有一族能命中**，
  表序根本不参与判定。D3 因此只做「让 `-M xw` 置位同一个全局、并让默认选项路径把它清零」，不新增 match 函数、不改表序。
- **15.2.0**：两族靠 `INSN_CLASS` + 单向 `pd->xw` 判定，同一码字可能被两族**同时**匹配，于是表序成为实体。
  phase-3h 的 65,536 半字穷举实测：`-Mno-aliases` 下 `rv32imafdc_xw` 上 **8,192 词**、`rv32imac_zcb` 上再 **512 词**
  与官方不符，修法是把 12 行（四个 XW sp 形式 + 四组 XW/Zcb 共享助记符行，连同各自 Zcb 兄弟行整组）
  前移到 `c.fldsp` 之前——即 15.2.0 补丁 0007 的表序前移。
  （`analysis/toolchain/phase3h-closure.md` §5.4 L150–157；§1 表 L14 记 0007 的四个组成部分。）

**跨版本读法**：15.2.0 patch 0007 的表序改动是**版本特异**的，8.2.0 不需要它；
而「8.2.0 无表序问题」现在是一条**实测**（49152 码字 × 5 模式 × 三侧全覆盖），不再是从代码形态推出的断言。
两次穷举的分母不同（15.2.0 取 65,536 全 16 位空间、8.2.0 取 49152 即低两位 ≠ 3 的压缩面），
读数时不能互相当作同一口径的数。

---

## 13. 转换器（R2 授权单元）的两处范围外行为变化

`E/s2/converter-gcc8/report.md` 第 11 条逐字口径（不阻塞，closure 需单列）：

1. **显式 `--gcc-major 9`** 现按请求选 9.3.1（arm target）并**干净报错**，不再静默换 12.2.0。
2. **假想「元数据 major 8 + 向量密码」工程**在默认路径下会丢弃向量分量（改前会拼出 8.2.0 必拒的 `_zve…` 串）。

两处都是「消除静默升级 / 让方言跟随实际编译器」这一改动的边缘效应，不在 R2 授权目标之内，故如实单列。
同单元的四项授权约束均已闭合：**附加性**（三 lane 54 文件对改前基线 `diff -r` = 0 字节，
`additivity/diff.txt` 与 `additivity/diff.delta.txt` 均 0 字节）；**去静默升级**（升级 warning 8 → 0，9/9 真正选中 8.2.0）；
**diff 单列**（`diff.s2-scope.txt`，仅两个授权文件）；**独立逻辑单元**（未 commit）。
双侧拼法对称由五 lane 矩阵 `dialect-symmetry.txt` 复证（GCC 8 三侧 9/9 march 一致；四 flag 组 × 9 工程 = 36 项 0 差异）。

---

## 14. 前提登记（premise register）

**P-01…P-11 逐条继承** `analysis/toolchain/phase6-baseline.md` §6（原表 11 行，顺序不变），状态按本阶段证据更新；
**P-12…P-16 为本阶段新增**。

| # | 前提 | 证据 | 状态 |
| --- | --- | --- | --- |
| P-01 | 框架 = xPack v10.2.0-1.2；组件源 = v8.2.0-3.1 代（freedom-tools v2019.05.0 系） | `E/s1/lineage/`（36/36 argv 与框架模板同序、distro-info 一手、组件四元组唯一命中） | 已验证 |
| P-02 | binutils fork 精确 tag = v8.2.0-3.1 | S1 时属反推（licenses 无判别力） | **已由 S2/S3 落证**：从该 tag 起的 vanilla 构建在字面量面 9/9 IDENTICAL 且非 XW 工程 28 gate 全 PASS（`phase6-literal-surface.md` §1、`phase6-diff-inventory.md` §0） |
| P-03 | WCH 在构建配置层的唯一语义改动 = `GCC_MULTILIB`（19+3） | `E/s1/lineage/` distro-info 全树 diff | 已验证；由 `-print-multi-lib` 23 行 IDENTICAL 闭合 |
| P-04 | gcc 拒 `_xw`、仅收贴写；as 侧 `x*` passthrough 更宽；`mcpy`/`mrsl`/`mrslu`/`wexti` 完全不存在 | `E/s1/probes/raw/{01,02,05}` | 已验证；**由 S4 探针集对最终安装树重放复证**（§5 覆盖表 A/A2/B 类 41+5+20 条、E 类 154 条全 IDENTICAL） |
| P-05 | 默认双侧均不产生 `.riscv.attributes`；显式开启后裸 `xw` → `xw2p0`、E 基座 `rv32e1p9` | `E/s1/probes/raw/03` | 已验证；同上复证（§5 覆盖表 C 类 86 条全 IDENTICAL） |
| P-06 | XW 压缩由 gas 完成，gcc 无 XW 代码生成 | `E/s1/optsweep/`（同源 `-Os` 下 `-S` md5 相同、差异只在 `.o`） | 已验证；D1/D2 的分工即建立在此前提上 |
| P-07 | as/ld/objdump 的 WCH 新增长选项 = 0；objdump `-M` 面完备 = `{no-aliases, numeric, xw}` | `E/s1/optsweep/`（全量枚举，非候选否定） | 已验证；同上复证（§5 覆盖表 F 类 64 条、K/K2 类 89+6 条全 IDENTICAL）。**推论**：15.2.0 代的隐藏选项机制在 8.2.0 无需实现 |
| P-08 | golden 集 = 精选 9 工程中 8 个（剔 `v3c-led`），march 取 MRS 原生 GCC 8 口径 | `E/s1/buildability/` | 已验证；口径由 Main R1 裁定为该项（`phase6-baseline.md` §8） |
| P-09 | 产物双跑逐字节稳定 | `E/s1/buildability/` §4（283 文件 100% 稳定） | 已验证。**附注（load-bearing，复现者必读）**：失败路径 stderr 在 `make -j2` 下行序抖动、**不**逐字节稳定（行集合相同）⇒ 诊断类比较一律**单调用采集**，构建日志不入字节 gate（同 §4；`phase6-diff-inventory.md` §3 复述）。全量普查对此另有硬保障：任何「无编译器/汇编器诊断」或 TIMEOUT/ERROR 的工程会被单独串行 `-j1` 重跑后再分类，本轮触发 **0** 次（`census-report.md` §3） |
| P-10 | ~~arm64 原生宿主构建产物与官方（x86_64 编译器产出）逐字节可达~~ | — | **已被取代（superseded）**：Main 裁定宿主路线 = x86_64/Rosetta（configure 字面量与 arm64 宿主互斥）；该前提不再成立也不再需要 |
| P-11 | 老代码基（gcc 8.2 / binutils 2.32）可在现代 macOS 完成构建 | 构建 rc=0 + 复放构建 rc=0 | **已验证**（`E/s2/build-run{1..4}.log`、`E/s4/replay/replay-build.log`）；代价 = §4 的六件宿主适配 |
| P-12 | host 依赖组合对产物字节无扰动。**官方那组可观测，实测为 GMP 6.1.2 / MPFR 3.1.6 / MPC 1.0.3 / 宿主 GCC 11.2.0（isl `isl-0.18-GMP`）；我方另选一组——GMP 6.2.1 / MPFR 4.1.0 / MPC 1.2.1 / isl 0.18 / zlib 1.2.12，宿主编译器 Apple LLVM 21.0.0 (clang-2100.1.1.101)——其无扰动性由产物字节反证** | **一手观测**：两侧 `gcc -v` 的 `compiled by GNU C version …` 行（本轮现场重推，逐字见 `E/s4/defect-fidelity/report.md` §五「两条不成立项的完整判据」第 2 条）。**反证**：probe `.o` sha 命中官方 `019c42bf…` + v3a 全工程 28 gate 逐字节命中 ⇒ FP 常量折叠疑虑就地消除 | 已验证（前提陈述已更正，见下方勘误） |
| P-13 | `ac_cv_lib_dl_dlopen=no` 复刻的是官方当年宿主的探测结果 | 「官方 2018 年该检测为 no」系从产物 + 机制**反推**，非对 10.13 SDK 的直接观测（`getopt-rootcause/report.txt` §七.5）；实测已证该量把 15 个链接单元一次性拉回官方状态；交叉佐证：官方 12.2.0/15.2.0 包与我方修正前同病 | 已验证（机制），**成因划界如实** |
| P-14 | `.lst` 同址符号择名属**闪烁类**：同一二进制、同一输入、同一 argv 复跑亦会翻 | 16 路 × 200 轮 = 3200 次/二进制，官方 **8/3200**、我方 **4/3200**；6400 次只出现两种结果、两对符号永不混合；宿主 malloc 最小实验 mode 1 倒挂 2/1600（`E/s4/lst-attribution/`） | 已验证；R5 裁定豁免成立 |
| P-15 | 我方 install 注入的 `bfd-plugins` 59 字节文本 = as-shipped 基线（不是修复对象） | `verify_pair` sha `0e1f88e299fe0fce…` 两侧 `cmp` IDENTICAL；`tree-fingerprint.txt` 记 `plugin_bytes=59`、`plugin_is_macho=0` | 已验证（R4b） |
| P-16 | 全量普查产物在同一批绝对路径上跨轮稳定 | 单趟 + 两工程双跑自检（49/48 产物逐字节同）+ smoke↔全量相隔约 10 分钟的 **107/107** 跨轮独立复核 | 已验证；**未做全量双跑**（如实登记，`census-report.md` §3） |
| **P-17** | 转换器的 GCC 8 `-march` 拼法（只追加**裸** `xw`、直接丢弃 B 与 Zmmul）与 MounRiver Studio 自身的拼装规则一致 | **一手指针（本轮补入）**：`E/s1/buildability/mrs-march-builder.txt` **L5–L6**（`== [A] GCC 命令行 -march 拼装`，逐字节摘录），源文件 `ref/MounRiver Studio 2.app/Contents/Resources/app/extensions/mrs-team.mrs-vscode/out/extension.js`（3478019 字节）**偏移 1953620**。该片段的判定链是：`isWCHToolchain(...)` 之后先分 `WCH_Toolchain_GCC12` 或 `WCH_Toolchain_GCC15` 一支——那一支里才追加 `_zba_zbb_zbc_zbs`（B）、`_zmmul`、`_xw`（GCC15 另加向量密码分量）；**`else` 支（即 GCC 8）只有 `extra_compressed_extension === true && (t += "xw")`**，B 与 Zmmul 在 GCC8 支**根本不出现**。⇒ 「裸 `xw` + 丢弃 B/Zmmul」两条规则在 MRS 源里逐字对应 | **已验证（一手）**。此前登记为「能力性论证」，审计 P2-4 指出一手指针缺失，现补齐 |
| **P-18** | `.map` 面 698 条 aux 残差的文件级尺寸差 100% 由工具链根路径串解释 | `E/s4/audit-sweep/map-full-sweep/`：698/698 逐文件断言 `ours_size − canonical_size == count(官方根) × 38` 全部成立，残余恒 0；输入自证 = 每个被读文件的 sha256 与 `aux-mismatches.tsv` 记录值相等（0 例不符）。见 §6.1 | 已验证（**全覆盖实测**，此前为「3 工程逐行 + 机制外推」） |

> **【P-12 前提勘误，2026-08-17；审计 P2-2】** 本前提原文写「**WCH 原始 XBB 环境版本不可观测**，属钉版假设」
> ——**旧句保留于此**，该断言被**官方二进制自身证伪**：官方 `gcc -v` 的编译期横幅明写
> GMP 6.1.2 / MPFR 3.1.6 / MPC 1.0.3 / 宿主 GCC 11.2.0（isl 0.18 恰好钉对）。
> 这是「继承而未测量的前提」的教科书案例，且该可观测面**恰好落在被排除的那 2 条探针里**
> （`03-attributes/driver-v`、`08-defaults/v-default`，见 §5 与 `report.md` §五）。
> **产物无扰动的结论未必错**（probe `.o` 与 v3a 全工程逐字节命中是独立佐证），改的是前提陈述本身。
> **是否把 host 依赖改钉为官方那组由 Main 定**（改则需重测全部字节面）；本轮不改钉、不新增 gate 探针。

> **【P-17 的共模不可证伪性，如实登记；审计 P2-4】** `evt-golden.sh`（官方侧）与 `evt-compare.sh`（我方侧）
> 用**同一个转换器**生成 Makefile ⇒ dialect 拼错会**同向平移两侧**，42285/42285 全绿对 dialect 正确性**零证据力**。
> P-17 的一手指针（extension.js 偏移 1953620）解决的是「规则是否与 MRS 一致」，
> **不解决**「字节 gate 原理上无法证伪共模输入」这一结构性问题——后者靠三条独立面显著收窄：
> ① 官方工具链在**独立 cwd** 下重建 2 个工程、gate 产物 SHA256 逐条命中（审计正面确认 23）；
> ② quick 与 full **两条独立 harness、不同 cwd、不同转换器调用**，3 个共有工程 86 个 gate 哈希全等（同 24）；
> ③ 五 lane 对称矩阵 `dialect-symmetry.txt`（GCC 8 三侧 9/9 march 一致）。
> 与此耦合的收窄通路一并登记：EXCLUDED 的判据是「官方侧构建失败」，而喂给那次官方构建的 Makefile
> 正是新 dialect 的产出 ⇒ 若 dialect 吐出官方 gcc-8 拒绝的 march，工程会被**静默归入 EXCLUDED-capability**
> 而非暴露为转换器缺陷。该通路未被触发的证据是 128 条 EXCLUDED 的 `first_error_excerpt` 逐条有真实诊断
> （无一条形如 `unsupported ISA substring`），但**原理性缺口仍在**，如实留档。

---

## 15. 未决与移交

1. **S1 `probes/README.md` 的三条未决**（`E/s1/probes/README.md` L29–31，任务书点名保留，逐条标注现状）：
   - #1「`-M xw` 之外，objdump/ld 是否还有未在 `--help` 暴露的 WCH 私有开关」——
     **本报告判读：已由 S1 轨道 D 关闭**。`E/s1/optsweep/optsweep.md` 做的正是该条要求的「选项表全量提取」
     （as/ld/objdump 270 具名项 + ld emulation 22 项，符号地址区间 + `md_longopts_size` 交叉 + 无符号通用扫描 19 段游程零 UNCOVERED），
     结论 **WCH 新增长选项 = 0**，`-M` 面 = `{no-aliases, numeric, xw}`（内联 strcmp 链，纯 strings 必漏）。
   - #2「`highcode-gen-section-name=1` 的下游用途（配套链接脚本/段搬运约定）」——**仍开放**，
     且**比原文暗示的更 load-bearing**。
     > **【覆盖声称收窄，2026-08-17；审计 P2-7】** 原文写「D4b 的编译器侧行为已由 42285/42285 与
     > params.exp +2 闭合」——**措辞过宽，旧句保留**。实测（本轮现场重推）：
     > EVT 树中把 `mrs.highcode` 置 `value="true"` 的工程共 **68 个，68/68 全部落在 EXCLUDED**，
     > PASS 集里 **0 个**；且 `ref/wch-evt/tools/wvproj_to_make.py` 对 `highcode` **零处理**
     > （`grep -c highcode` = 0），即便有 PASS 工程开启该选项也传不到编译器。
     > ⇒ 42285 只覆盖 `.highcode` 的 **`DECL_UNINLINABLE` 半边**（V2AC/V3B/V4BC 家族源码确用
     > `.highcode`，这半边确有 gate 覆盖）；**`param=1` 的改名半边在 42285 上零覆盖**。
     > 该半边的闭合口径是**定向矩阵**：官方对拍探针（`=1` 时两侧同样拆成 `.highcode.<fn>`、`.o` 逐字节同，
     > 探针集 G/G2 类）＋ `params.exp` 的 **+2**（`blocksort-part.c -O3 --param highcode-gen-section-name={0,1}`）
     > ＋ D4b 新增的 9 个 testsuite 用例。**实现本身经现场对拍确认与官方一致**，这是措辞问题、不是实现缺陷。
   - #3「8.2.0 与 15.2.0 对 `xw` 归一同为 `xw2p0`，两者在 `.o` 字节面的可比口径」——
     **本报告判读：已由 S2 关闭**。8.2.0 默认双侧均不产生 `.riscv.attributes`，EVT gate 产物无该节，不构成差异面
     （`analysis/toolchain/phase6-diff-inventory.md` §3）。
   （#1/#3 的关闭是本报告依所引证据作出的判读，供 Main 追认；未改动 `probes/README.md` 原件。）
2. **S4-02：面 F（check-binutils）无 pristine 基线**——编排裁定「不补」（§7.4），如实登记为口径缺口。
   若日后要补，需另建 vanilla binutils objdir；不改变六个验收面的任何结论。
3. **`install.pre-replay-preserved` / `build.pre-replay-preserved` 的处置待 Main**：
   两者是复放换出时的可逆重命名保全件，现存于 `tmp/toolchain_8.2.0/work/darwin-x64/`，
   实测占用 **422 MB / 319 MB**。它们是修正前活动树的最后快照；删除或长期保留由 Main 定，本报告不自决。
4. **未提交单元**（验收后由 Main 入库，本工作流全程未在仓库根 commit）：
   转换器 GCC 8 分支（`ref/wch-evt/tools/wvproj_to_make.py`，R2 授权、未 commit，**`123+/20−`，raw diff 264 行**）、
   harness 路由 + 16-worker 迁移 + 两笔审计修正（`scripts/evt-{compare,golden}.sh`，
   **终态 `148+/53−`，raw diff 377 行、17 hunk**；S2 归档态为 `113+/51−` / 296 行 / 11 hunk，见 §9 口径表）、
   `scripts/build-toolchain-8.2.0.sh`（新文件）、`patches/8.2.0/`、
   `analysis/golden/8.2.0-darwin-arm64{,-full,-full-exclusions}.tsv`、
   本报告与 `analysis/toolchain/phase6-{baseline,literal-surface,diff-inventory}.md`。
5. **随包库合规**属另一团队职责，本项目不涉。

### 15.1 审计 P2 项的登记（本轮不改动、只如实入账）

以下四条来自独立审计，本轮按其性质**登记而不处置**，逐条写明理由与归属：

| 项 | 内容 | 本轮处置 |
| --- | --- | --- |
| **P2-18** | 已入库的 `analysis/golden/{12.2.0,15.2.0}-darwin-arm64.tsv` 带有填好的 `# debug_flags[...]=-gdwarf-4` 值，说明那两份 golden 生成于「`awk` 不是 BSD awk」的 PATH 下——而本机 `/usr/bin/awk` 对未加括号的三目式报 `syntax error`，在 `set -euo pipefail` 下会直接终止 `evt-golden.sh`。**属既有问题，非 phase-6 引入**（该写法自最初的 harness commit 起就在）。**不影响 gate**（比较不读该字段） | **登记**。本工作流已修 BSD-awk 可移植性（§9 类 ④），但**不重生成那两份他版 golden**——重生成属他版本工作流的范围，且会改动硬约束 2 的边界面 |
| **P2-19** | 收口 gate 是全量口径，但 `scripts/` 下只有 quick 的 `evt-golden.sh`（且硬钉 `project_count -eq 9`）；full lane 的 `ours_runner.py` / census 工具在 untracked 的 `tmp/` 里，**gate 的生成手段不在版本控制内**。既有问题（15.2.0 同样如此） | **登记**，移交 Main。把 full-lane 生成器纳入 `scripts/` 是跨版本的仓库结构决定，不由本单元自决 |
| **P2-20** | gate 口径实为「模工具链安装前缀」的逐字节一致，与「比较前不做任何 normalize」的无限定表述冲突 | **已处置**：§1.2 的带限定表述已写死并全文适用，见该处的口径块 |
| **P2-21** | 33 个工程（z-subset 31 + `lib:missing` 1 + `link:region-overflow` 1）仅在**链接阶段**失败，其 `.o` 两侧都能正常产出（实测：z-subset 样本 25 个 `.o`、CoreMark 33 个 `.o` 全部编译成功），现行 harness 按**工程粒度**整体剔除，丢弃约 900 个可对拍 `.o`（≈gate 面 2%）。**不是正确性缺陷**（已比的全部命中），是覆盖完整性缺口；收紧手段明确 = 改为**产物级剔除**（编译成功的 `.o` 入 gate，只剔 `.elf`/`.bin`） | **登记，待用户裁定，本轮不实施**。已入 `DECISIONS.md`（2026-08-17）作为已知口径。实施会改变 gate 分母与 golden manifest，属口径变更、须先有裁定 |

### 15.2 审计 P3 项中「登记不改」的四条（附裁定与理由）

| 项 | 内容 | 裁定 |
| --- | --- | --- |
| `host/0002` 注释未同步上游措辞 | 代码已是上游 GCC 15 `system.h:197-239` 的同序回移形态，**注释仍是旧措辞**（零行为差） | **编排会话裁定：登记不改码。** 理由：改注释要重写 `host/0002` 这一片，进而重签整条 gcc 栈的 patch-id 与 tree 不变式（本轮刚因 P1-1 做过一次），代价是全栈重签、收益是零行为改进。**Main 可改判**——若改判，动作是「重写 `830ea0167` 的 message/注释 → 重建 D1′/D4a′/D4b′ 三片 → 四不变式 v4 重签」，其余账目不受影响 |
| D4a 早返回同时绕过上游 `calls_eh_return` 分支 | 已确认 `ra` 判据必要非冗余；`__builtin_eh_return` + WCH 快中断的组合**未探** | **登记不补探针**：嵌入式无异常路径，EVT 树内实际不可达；补探针需构造上游 eh_return 用例，属超出 WCH 行为面的上游语义测试 |
| 全仓 commit 的 author/committer 同一身份，**git 元数据无法区分 Main 与执行者** | 审计观察 | **登记**。角色区分由会话地址簿与转录（`E/s4/transcript-recovery/`）承担，不由 git 元数据承担；改动 commit 身份属仓库策略，移交 Main |
| `git patch-id --stable` 对 `gcc/0003` 的**第二字段**被 message 里行首 64 位 sha256 污染 | 本轮现场复验：`git patch-id --stable < gcc/0003-….patch` 输出 `7f03544f9db27f5d…  9d693fae19e3c9aa…`——**第二字段是官方 gcc 二进制的 sha256 前 40 位**，不是源提交号（对比 `gcc/0004` 的第二字段正是其源提交 `f5d1f2b66…`） | **登记**。**patch-id 本体（第一字段）不受影响**，本报告与 `patch-id.tsv` 的全部结论只用第一字段；风险面是他人写 `awk '{print $2}'` 类脚本时会在这一片上误报，故显式留档 |
