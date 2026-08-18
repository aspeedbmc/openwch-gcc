# phase-10 开源前检查：补丁集、仓库发布面与 CI 方法（analysis-only）

执行日期 2026-08-18。仓库 HEAD `6705cce`。定性：纯分析阶段——不修文件、不重写补丁、不合并分支；
发现登记分级，处置属后续阶段。合规/授权话题按项目既定裁定不涉及，本报告全部按**工程卫生**口径。
证据根：`tmp/phase10-evidence/`（进出场守卫 `s0/`、发布面 `s1/`、克隆实验 `s2/`、CI 实证 `s3/`）。

**一句话结论**：三版本补丁集的技术实体与 gate 证据链已具发布质量，但仓库**现状不可直接开源**——
无入口文档、39 片 message 的证据指针 75% 对外悬空、外部复现路径在 12.2.0/8.2.0 上被
2026-08-18 的构建期校验块在原理上切断（P10-F1）、CI 交付物冻结在 17 个 commit 之前的未合并
worktree 上。全部缺口可修，分级清单见 §5，须用户拍板的取舍见 §6。

---

## 1. 发布面清点与敏感信息扫描

### 1.1 跟踪面构成

`git ls-files` = **25,442 文件 / 约 1.04 GB**（工作底稿 `s1/findings.md`）：

| 目录 | 文件数 | 说明 |
| --- | --- | --- |
| `ref/wch-evt/` | 25,018 | WCH EVT 工程树（差异测试输入）；工作树上 9 个文件为补丁已应用态（设计如此，见 §3 卡点 7） |
| `ref/wch-isa-research/` | 206 | ISA 研究成果；含**单文件 344 MB** 的 `errata/06b-…/machine/canonical-unit-domain-records.jsonl.gz` |
| `ref/wch-manuals/` | 17 | WCH 官方 PDF 手册 |
| `analysis/` | 55 | golden manifests ×9（四份 full 各 ~8 MB）+ 46 份阶段取证/审计/收口报告 |
| `patches/` | 50 | 39 片 + 三组 README/series/patch-id.tsv |
| `scripts/` | 20 | 构建/对比/导出/全量 census 工具 |
| `tests/` `plans/` 根文档 | 19 | XW+LTO 套件、路线图、AGENTS/DECISIONS/wch-xw |

- 根目录**无 README**；跟踪的根文档只有 AGENTS.md（内部 agent 工作规则）、DECISIONS.md
  （88 条内部裁定台账）、wch-xw.md、.gitignore。
- `ref/wch-toolchain-private.md`（用户私有笔记）：**未被跟踪——确认成立**；但也未被 .gitignore
  覆盖，`git add -A` 会误收（→ §5 P1-3）。
- 仓库 .gitignore 无 `.DS_Store` 行（目前仅靠本机全局 ignore 挡住），且 `ref/wch-evt/` 下已有
  **3 个 .DS_Store 被跟踪**（→ §5 P2-6）。
- gitignore 面核对：`ref/gcc`、两 MRS 包、`tmp/`、`ref/*.zip`、`ref/*.tar` 全部命中，与 DEC:22 一致。

### 1.2 敏感信息扫描（git grep 全跟踪内容）

| 模式 | 结果 | 定性 |
| --- | --- | --- |
| token / 私钥 / 内网 URL / IP | **0 命中** | — |
| `/Users/apple`（绝对仓库路径） | 42 文件 | 三类：golden manifest 表头与 analysis 证据（**字面量机制/证据 provenance，设计需要**，外部读者需要解释）；`scripts/full-census/partition-check.py:20` 硬编码 `REPO=`（工具缺陷，异地即断，→P2-4）；两份补丁 README 复现序列的 `repo=/Users/apple/Projects/openwch` 行（→P2-3） |
| `/Users/mrs`、`/Users/wch` | 27 / 14 文件 | 字面量一致性机制本体（设计需要）；须入口文档解释其含义与建法 |
| 主机名/个人标识 | 跟踪文件 0 命中；**git 历史 64 个 commit 作者恒为 `apple <apple@apples-MacBook-Pro.local>`** | 发布即公开个人机器名 → §6-④ 呈用户 |
| 会话 UUID | `b28c0730-…` 3 处（DECISIONS.md 等） | 内部残留，无害，P3 |
| 邮箱 | 39 片补丁作者=合成身份 `phase{3,4,6}@openwch.local`；一处上游引文邮箱 | 无问题 |

### 1.3 体积与形态

跟踪面 1.04 GB（EVT 树 + 344 MB 研究证据大档 + 33 MB golden manifests 为大头），克隆（含 .git）
约 1.6 GB + 检出 1.04 GB。是否照原样公开（EVT 树、344 MB 机器证据、46 份内部报告、DECISIONS
台账）是取舍问题 → §6-①②③。

---

## 2. 补丁集外部可用性（39 片外部视角复审）

p8 已完成可解释性审计（每行可解释，phase8-review 152/152 台账抽验），本节只审**外部可用性**。

### 2.1 message 证据指针普查

工具 `s1/pointer-census.py`（判据器三关自证：合成样例断言、diffstat 后内容零计入、两外锚命中——
15.2.0 gcc/0004 tmp=5 与 phase8-review P3-12 一致；12.2.0 合计 62 = P8-R 复算 61 + phase-9 新增 1）。
逐片明细 `s1/pointer-census{.tsv,-detail.tsv}`。

**总量：39 片 message 共 143 个仓库路径指针，其中 108 个（75%）指向 gitignored `tmp/`——
对任何外部克隆全部悬空**；30 个指向跟踪文件（可达）、5 个指向 gitignored `ref/gcc`（外部人重建
ref 后可达）、0 个指向不存在路径。

| 版本 | tmp 悬空 | 可达 | 特征 |
| --- | --- | --- | --- |
| 12.2.0（16 片） | 53 | 8 | 重灾区；指针根多为 `tmp/phase4-evidence/` |
| 8.2.0（7 片） | 30 | 2 | 指针根 `tmp/toolchain_8.2.0/evidence/`、`tmp/golden/` |
| 15.2.0（16 片） | 25 | 20 | binutils 侧多片 0 悬空（指向 isa-research/survey 等跟踪文件） |

其中 3 片（15.2.0 binutils 0002/0007、12.2.0 binutils 0004）的**规格来源**指针指向 gitignored
`tmp/phase9-evidence/<v>/spec.md`（phase9-review P3-20 已点名，与「可向上游 reviewer 解释」硬规则
有张力）。本机现存性 107/108（陈述性截断路径 1 例除外）——即证据本体都在，只是不随仓库走。

**处置选项（不自决，→ §6-⑤）**：
(a) 保留作历史 provenance，入口文档声明「tmp/ 指针为开发机证据坐标，不随仓库分发」；
(b) 为每版本补一页 analysis/ 摘要（把各片关键证据结论/哈希落成跟踪文件），message 不动；
(c) 改写 message 指针指向 (b) 的摘要页——代价：39 片重导、patch-id 不变但文件字节全变、封存件重签。

### 2.2 内部代号密度与解释入口

`patches/` 内：phase-N 11 次/6 文件、phase-3[a-h] 28 次/7 文件、RC0x 8 次/6 文件、SR-01 1 次、
EVT 45 次/23 文件；DEV-*/DCXW/XWVER/U-* 为 0（p8 清理干净）。message 内 RC0x 多数带随文注解
（"RC01 (.highcode repair round)"）；**15.2.0 README 首现 RC01/RC02/… 无注解**；全仓无术语表。
外部读者理解这些代号的唯一途径是通读 analysis/ 阶段报告。

### 2.3 三版本 README 外部可读性判定

| README | 判定 | 外部断点 |
| --- | --- | --- |
| 12.2.0（189 行） | **最接近外部可用**：上游输入 SHA256 表、一键 replay、From/patch-id 导出约定 | 源码包无 URL（URL 表在未合并的 p7 交付物 §3.6）；"as described by the root repository instructions" 指向不存在的根文档；replay 依赖 gitignored 活动镜像与 downloads/（§3 卡点 3/4）；MRS darwin 包获取零文档 |
| 8.2.0（163 行） | 叙事最自含（xpack 克隆 URL、host/ 拆分、宿主适配逐条讲清） | `repo=` 硬编码；/Users/wch 需 sudo 未提；From 可达性检查使 README 的 `git am` 复现流在原理上过不了构建脚本（P10-F1） |
| 15.2.0（322 行） | 信息最全但结构=阶段编年史 | `repo=` 硬编码；复现序列 `cp "$active/…"` 五行从 gitignored 活动树取前置件缓存，外部人 `set -e` 即死（`download_prerequisites` 本可下载）；证据指针指 gitignored `tmp/phase3d-evidence/…`、`tmp/prompts/phase-3d.checklist.md`；/Users/mrs 需 sudo 未提 |

三份都没有提 `ref/wch-evt/patches/apply.sh`（§3 卡点 7 的成因），也都没有解释 golden manifest 的
绝对 cwd 前提（§3 卡点 6）。

### 2.4 入口文档缺口清单（只列，不代写）

1. 根 README：项目是什么、三版本关系、验收 gate 语义（按平台逐字节、双侧对称 prefix-map 限定）、目录地图节选。
2. 官方参照物获取指南：MRS darwin 包渠道；linux 包已有 `fetch_wch_toolchain.py`（官方 API + 双 SHA256）可直接引用。
3. 复现指南：宿主前提（/Users/mrs、/Users/wch 的 sudo 建法与含义）、EVT 补丁应用步骤、
   「golden 自生成 → 对拍」推荐流程（S2 已实证可行，§3.3）。
4. 术语表/阅读地图：phase-N、RC0x、SR-0x、quick/full gate、golden 的一页式说明 + analysis/ 报告索引。
5. 贡献指南与 LICENSE 文件（工程口径登记：上游 GCC/binutils 补丁仓库的惯例配套缺失；不做合规论证）。
6. 上游源码包 URL 表（p7 交付物已备好，合并即得）。

---

## 3. S2 新鲜克隆复现实验（12.2.0 最小链）

方法：file:// 克隆 HEAD → 只依据克隆内文档走「源获取 → 打补丁 → 构建 → quick 对比」，每步登记
〔文档覆盖/克隆外依赖/卡点定性〕；实验者补给克隆外输入时如实登记为卡点数据。预注册
`s2/preregistration.md` 三条预期**全部命中，无反向**。步骤台账 `s2/steps.md`，日志 `s2/*.log`。

### 3.1 卡点清单（两栏分类）

**原理不可省（字节一致性机制的必然后果）**

| # | 卡点 | 实证 |
| --- | --- | --- |
| A1 | **随仓分发的 golden manifest 只在其生成 cwd 下可复用**：克隆内对拍 `gate_pass=200/274, gate_fail=74`。**〔2026-08-18 审计 P1-A 更正，对日志机械重取〕**74 条分解为两个成因：**46 条 = 真 cwd 差**——两个 `-g` 工程（v3f-gpio 与 v3f2-gpio，各 22 .o + 1 .elf），DWARF 内嵌 comp_dir；**28 条 = v4bc-pmp 全部 gate 产物**（26 .o + 1 .elf + 1 .bin），成因是 B6（克隆未应用 EVT 补丁、构建配置本身不同），与 cwd 无关。九个 .bin 八个 PASS、唯一 FAIL 属 B6 项目——「.bin 不受调试路径影响」的历轮结论继续成立；初稿「cwd 经 __FILE__ 进 .bin」说法被本表数据反证，**撤回**（预注册的「.bin 预计 MATCH」原判成立）。其余七个无 -g 工程中六个全 PASS、v4bc-pmp 因 B6 全 FAIL | `s2/compare-shipped-manifest.log`；审计 `tmp/phase10-evidence/review/phase10-review.md` P1-A；DEC:30/60 既有结论的克隆侧直证 |
| A2 | 宿主字面根 `/Users/mrs`、`/Users/wch` 必须存在（需 sudo）——官方 configure/DWARF 字面量的复刻前提 | 构建脚本硬编码；CI 侧已有 `setup-literal-paths.sh` 对应物 |

**文档缺口 / 工具形态缺陷（全部可修）**

| # | 卡点 | 定性 |
| --- | --- | --- |
| B1 | 无根 README，外部人靠 AGENTS.md 目录地图摸路 | 文档缺口 |
| B2 | 8 个上游源码包只有 SHA256 无 URL；replay 只校验不下载 | 文档缺口（p7 §3.6 已备 URL 表待合并） |
| B3 | MRS darwin 包获取渠道零文档；抽取脚本要求 darwin+linux 两包同时在位 | 文档缺口 + 工具形态小缺陷 |
| B4 | `replay-toolchain-12.2.0.sh` 要求 gitignored **活动镜像树**在位作「复放==活动」锚（其锚值本已内嵌于 patch-id.tsv/README，可改为常量锚） | 工具形态缺陷；p7 已知并以 `prepare-sources.sh` 替代（未合并） |
| B5 | **P10-F1**（详见 3.2）：构建期校验块锚定不可再生的内部 commit | **工具缺陷，P1** |
| B6 | `ref/wch-evt/patches/apply.sh` 一步在三份补丁 README 中零提及 → 克隆内 golden **静默**缩水（v4bc-pmp 被 EXCLUDED，manifest gate 行 246/274，第一次重生成无任何非零退出信号）。加重登记：比缺文档更糟的是无声错数——若无分母绝对断言，缩水 manifest 对拍会假全过；p7 CI 的「三层绝对断言」设计（每腿断言 274/242 常数）在本实验中获得实证正当性 | 文档缺口（加重）；CI 设计已防 |
| B7 | `BUILD_JOBS` 缺省 8，项目契约 16；12.2.0 README 未提 | 文档缺口（轻） |
| B8 | linux 腿复现驱动（容器编排 run-linux.sh / gate-prepare_linux.sh）在 gitignored `tmp/phase3h/`，未版本化；p7 workflow 合并可消解 | 发布面缺口 |

### 3.2 P10-F1：构建期补丁集校验块切断 fresh 复放（本检查最高级别发现）

**现象**：克隆内 replay 在 8 归档校验、16 片 apply_check、双组件 tree_match 全 PASS 之后，
死于 `fatal: failed to unpack tree object 3280576e…`、退出 128（原样 git fatal，无 die 文案）。

**机理（读源直证）**：`scripts/build-toolchain-12.2.0.sh` 的构建期校验块（DEC:83-4d，
commit 020d43a，2026-08-18）以**导入 commit** `3280576e…` 作 `read-tree` 锚，并要求每片 From 源
commit `merge-base --is-ancestor` 可达 HEAD。fresh 归档导入产生的 commit 必然不同
（克隆内实测 `2ae2464e…`，tree 相同 `e66ae753…`）；fresh `git am` 产生的 commit 也必然不是
From 值。故**任何 fresh 复放在原理上过不了该块**。8.2.0 脚本 `:235` 有同款 From 可达检查
（其 read-tree 锚是上游 tag commit，无此问题；该断点为读源推导，未实跑）；15.2.0 darwin/linux
两脚本为纯内容锚（read-tree 上游 commit + write-tree 对冻结树），fresh 兼容。

**为何此前未暴露**：4d 的验证重建（DEC:83「12.2.0/8.2.0 各做一次验证重建」）跑在**活动树**上，
那里被锚定的 commit 全部真实在历史里——改了校验、没对 fresh-clone 这个被测对象重跑消费路径，
P9-F1 同款教训。p8 协调器已认领该裁定责任面（跨会话信，2026-08-18）；分级维持 **P1**。

**连带后果**：p7 CI 的 `darwin-12-2-0` / `darwin-8-2-0` 两腿在 current main 上会死在同一处
（prepare-sources 产 fresh 树 → build 脚本 4d 块 fatal）——p7 交付时（eed1486）该块尚不存在，
prepare-sources.sh 的注释明确记载其契约建立在当时 `verify_source_base()` 的 fresh 导入回退上。

**修复方向（选项，不自决）**：把两个目标拆开——「本地活动树守卫」（commit 锚合法有效）与
「fresh 复放自证」（只能内容锚：导入 **tree** 值 + 冻结补丁 tree + stable patch-id，三者
现皆已内嵌）分属不同机制，混在一个检查里正是断因。可行形态：read-tree 锚从 `$gcc_base`(commit)
改为 `$gcc_base_tree`(tree)；From 可达检查降为「From == patch-id.tsv.source_commit 相等断言」
（该等式已在同块中检查）加「可达性仅在 commit 存在时执行」。

### 3.3 走通路径实证（正面结果）

供给克隆外输入并跨过 B4/B5 后：构建成功（`BUILD_EXIT=0`，install 3878 文件，16 核约 7 分钟）；
克隆内跑 `ref/wch-evt/patches/apply.sh` + `evt-golden.sh 12.2.0`（`deterministic=9 excluded=0`，
gate 行 274）→ `evt-compare.sh` 对自生成 golden：

```
SUMMARY  gate_pass=274  gate_total=274  gate_fail=0  aux_match=273  aux_diff=4
```

与主仓正典 quick 数字（含 4 项既裁定 .map aux 豁免）逐一相同——**「同 run 同 cwd 现生成
manifest → 对拍」这条路径在任意克隆位置完全成立**（DEC:60 CI 语义的异地实证）。
建议将其作为对外文档的**推荐复现流程**：官方包 → evt-golden 自生成 → 构建我方 → evt-compare；
随仓 manifest 明示「仅作 raw drift 诊断参照」。

### 3.4 15.2.0 / 8.2.0 差异点推演（文档面，未重复实验）

- **15.2.0 darwin**：README 内联序列用上游 git clone（URL 有）+ `git apply --index`（不产生
  commit）+ 构建脚本内容锚 → **无 P10-F1 断点**；断点=前置件 `cp "$active/…"` 五行（B 类，删行即
  由 `download_prerequisites --verify --sha512` 网络获取）、/Users/mrs 前提、Homebrew zstd 1.5.7
  前提（README 已写明）。
- **15.2.0 linux**：构建脚本 fresh 兼容，但容器编排驱动未版本化（B8）；p7 workflow 即其
  版本化形态（含 image digest 钉死、apt 包集、EVT_CONTAINER_IMAGE provenance）。
- **8.2.0**：克隆 URL/tag 齐全、宿主适配文档最全（Rosetta 重入、ac_cv 钉死、ISL 0.18）；
  断点=From 可达检查（P10-F1 半款）+ /Users/wch 前提 + `repo=` 硬编码。
  另：官方 darwin 8.2.0 包内 59 字节文本化 symlink 的缺陷保真已在 README 讲清（正面）。

---

## 4. CI 方法审查（p7 遗产的现实检验）

### 4.1 交付物清点与分叉状态

p7 交付物冻结于 worktree `tmp/p7-worktree`（eed1486，**从未合并**；会话已结束）：
4 个新件（`toolchain-ci.yml` 1001 行、`release.yml` 863 行、`scripts/ci/` 四脚本 1249 行、
`analysis/toolchain/phase7-ci-cd.md` 396 行）+ 4 个文档修改（AGENTS.md 目录地图、三 README 文末
「## CI」小节）+ 证据树 `tmp/p7-worktree/tmp/p7-evidence/`（S0–S5，含官方包同源实证、act 冒烟、
9 个上游 URL 存活复核、darwin 开窗申请三件——窗口至会话结束未获得，darwin 本地腿从未跑）。

main 自 eed1486 前进 **17 个 commit**（p8 三版本清理、From 统一、full-census 收编、导出脚本、
4d 校验块、phase-9 xlen、常量同步）。逐件过时程度：

| 交付物 | 判定 | 依据 |
| --- | --- | --- |
| `prepare-sources.sh` 的 SHA 派生 | **不过时** | 其 awk（含续行拼接）对 main 现行三脚本实测仍产出 8/5/0 针，与设计一致 |
| `prepare-sources.sh` 12.2.0/8.2.0 腿 | **被 main 侧 4d 块击穿** | P10-F1；其注释所依赖的「verify_source_base fresh 回退」契约已被 020d43a 改变 |
| workflow 绝对断言（274/274/274/242、9/9/9/8 工程） | **不过时** | 三版本 quick 分母未变；harness/evt-projects.tsv/golden quick manifests 自 eed1486 零改动（git diff 为空） |
| workflow 调用的 patches/series | **自动跟随** | CI 用 checkout 自带补丁；p8/p9 改动不需 CI 侧同步 |
| §3.12「tree 只打印不断言」叙事 | **与 main 现状有张力** | main 的 4d 块已在构建脚本内钉冻结树/patch-id（用户裁定），两层设计方向不冲突但文档须改写口径 |
| 文档修改 4 件 | **须重排** | main 侧同名文件已被 p8/p9 大改，直接合并必冲突；p7 增量为文末追加小节，重排成本低 |
| phase7-ci-cd.md 若干叙事 | 局部过时 | P2-19（full-census 未版本化）已被 main 4cb591e 收编闭合；「仓库无构建墙钟记录」对跟踪面仍成立，但 p8 证据树已有实测锚（见 4.3） |

### 4.2 设计复核（对照 DECISIONS 五条 CI 裁定）

| 裁定 | 实现 | 判定 |
| --- | --- | --- |
| DEC:59① 只写 workflow + 本地 act，不建远端 | 交付物全为文件 + act-verify 入口，无远端痕迹 | 忠实 |
| DEC:59② quick 作 push/PR gate（274/274/242），全量不进托管 CI 且显式标注 | 四腿常数断言 + workflow 头注/§5 边界声明 + 全量留本地 operator 路径 | 忠实；且分母断言设计被 S2 卡点 B6 实证为必要 |
| DEC:59③ tag 触发 release、tarball 含逐字节注入库 | `release.yml`：`v*` tag → 同构建+gate → gate 绿才打包（`--sort=name --mtime=@SOURCE_DATE_EPOCH --owner=0 --group=0 --numeric-owner` + `gzip -n` 可复现打包）→ 资产=构建脚本装出的完整树 | 忠实 |
| DEC:59④ p7 钉冻结 worktree、不写共享路径、act 容器自由、共享路径申请窗口 | 全程 worktree 内；darwin 三窗口申请件在 S4（未获窗）；act-verify 设计性拒绝 `--bind`/`-self-hosted` | 忠实 |
| DEC:60 同 run 同 cwd 现生成 manifest；入库 manifest 只作 raw drift 诊断；官方包同源实证为 gate 前提 | workflow 每腿先 evt-golden 后 evt-compare；同源实证已做（S0/gate0：API 侧 vs ref 侧 3032/3032 内容全等 + 338 目录 + 6 个 libcc1/libcp1 symlink-vs-普通文件差异，内容逐字节同，论证 gate 中性） | 忠实 |

### 4.3 runner 资源估算复核（以 p8/p9 实测 timings）

p7 判定「darwin 腿托管可行性未判定」，其时仓库无任何构建墙钟锚。p8 证据树现已提供实测锚
（16 核 M 系列本机）：15.2.0 darwin build 7m02s、quick 3s、full 8m02s；12.2.0 清洁构建 2m44s、
轮末批全程 4m45s；8.2.0（Rosetta）probes 128s、quick 5s、full-main 517s、full-linkonly 128s
（`tmp/phase8-evidence/8.2.0/s3/timings.tsv`）；15.2.0 linux 容器（qemu amd64-on-arm64）全程
约 1h38m。复核结论：
- **6h 墙钟上限对 quick 腿不再是主要风险**：即便按 16→3/4 核线性折算加 Rosetta 1.15–1.25×，
  三条 darwin quick 腿的构建+27 次工程构建都在个位小时内有宽裕余量；linux 腿见 4.4 act 实测。
- **未判定轴收敛为两条**：darwin runner 7 GB 内存（`BUILD_JOBS=16` 的峰值无满负载实测——p7
  已把 `P7_MEM` 流式仪器建进 workflow 本体，首次真跑自解）与 14 GB 磁盘（12.2.0 本地项目根
  7.6 GB + 官方包 1.1 GB + 归档 0.6 GB，紧但未证不可行）。
- p7「全量不进托管 CI」的结论**继续成立**（full 腿磁盘/时长两条独立上限未变）。

### 4.4 act linux 腿实证（p7 阶段内从未跑过的那一环——本检查补上，端到端全绿）

`scripts/ci/act-verify.sh linux-15-2-0`（act 0.2.89，冻结 worktree 内，未降级），
**Job succeeded / ACT_EXIT=0**。证据：`tmp/phase10-evidence/s3/act-run.log` 与
`tmp/p7-worktree/tmp/p7-evidence/S4/linux-15-2-0-20260818T105514Z/`（timing/disk/memory/
assertions/deliverable-binding/worktree-status 全套自动落盘——p7「仪器建在 workflow 本体、
首次真跑即自解」的设计如约兑现）。

| 项 | 实测 |
| --- | --- |
| 字节 gate | 分母断言 `manifest_gate_rows=274 / manifest_projects=9` 命中；`SUMMARY gate_pass=274 gate_total=274 gate_fail=0 aux_match=273 aux_diff=4`（同 run 容器内官方现生成 manifest 对拍；入库 manifest 仅打 raw drift 诊断 328+328 行——与 §3.1-A1 的 cwd 结论互证） |
| 分段墙钟 | provision 107s（官方包经 MounRiver API + 双 SHA256）· prepare 96s（上游浅克隆+16 片应用）· build 898s（binutils 185s + gcc compiler-only 676s + 注入 2s）· gate-golden 55s · gate-compare 23s；**act 全程 1299s ≈ 22 分钟**（16 核宿主，linux/amd64 容器） |
| 内存 | 容器 cgroup 构建峰值 **8.78 GB**（BUILD_JOBS=16、容器 16 CPU/16 GB）——p7 §6.3 悬置的 OOM 主证据就位：**8.78 GB > darwin runner 7 GB**，三条 darwin 腿按 16 jobs 契约在托管 runner 上有实证的内存风险（跨平台外推限定照 p7 自注） |
| 磁盘 | 宿主 df 差分 provision→build 约 7.2 GB（14 GB runner 上叠加 OS 后依旧偏紧，维持「待判」） |
| 宿主隔离 | worktree `status --porcelain` before/after 逐字节相同、HEAD 不变；act 三个写面全部重定向进证据目录 |
| 交付物绑定 | 工作副本 `.github/workflows/*` + `scripts/ci/*` 与冻结交付版 sha256 比对 **7/7 SAME** |

**外推**：GitHub `ubuntu-24.04`（4 vCPU x86_64 原生）上并行段按核数折算 ≈ 1h 量级，
远低于 345 分钟 timeout——**linux 腿托管可行性由「待 act 补」转为「有实测支撑的可行」**。
p7 文档的 1.67× qemu 折算口径与本机容器实测（build 898s vs p8 darwin 原生 422s，约 2.1×）
不一致，报告以实测墙钟为准、不细究容器实现机制。
darwin 三腿的新增结论：时长风险低（§4.3），**内存 8.78 GB@16 jobs 成为主要风险轴**——
处置属 p7 §7.4 升级路径的用户选项（self-hosted / 降 BUILD_JOBS 属并发契约变更需裁定），→ §6-⑥。

### 4.5 CI 现状结论与合并路径

**现状 =「设计已裁定、实现冻结于 eed1486、linux 腿端到端已由本检查验证全绿（4.4）、darwin 腿
从未本地验证且内存风险已被 4.4 量化、与 main 的 4d 块存在一处原理性冲突（P10-F1）」。**

合并前必须重整清单（无论选哪条路径）：
1. 解决 P10-F1：4d 块与 fresh 复放的机制拆分（§3.2 选项），否则 `darwin-12-2-0`/`darwin-8-2-0` 两腿必红；
2. 四件文档修改对 p8/p9 后的现文重排（文末小节，成本低）；
3. phase7-ci-cd.md 过时叙事更新（P2-19 已闭合、构建墙钟锚已存在、§3.12 口径对 4d 现状改写）;
4. `wvproj.yml` 与 `toolchain-ci.yml` 的官方包缓存 key 各自独立，合并后统一缓存策略可选（非必须）；
5. darwin 三腿至少各做一次 `darwin-window-run.sh` 本地窗口跑（p7 已备好就绪脚本与申请件，从未获窗）。

**路径选项（不自决，→ §6-⑥）**：
(a) 重整后合并：按上表 1–3 修后把 4 新件 + 4 文档增量落 main，act/窗口验证在 main 上重做一轮；
(b) 按现状归档另起：worktree 冻结为历史证据（打 ref 或 tar 归档），CI 在 main 上按 phase7-ci-cd.md
    的设计重新落地（设计文档质量足以支撑重写）；
(c) 部分合并：先合 `scripts/ci/` 四脚本与文档（它们同时修复 S2 卡点 B2/B4），workflow 两件
    待 P10-F1 解决后再合。

---

## 5. 分级发现列表

**P1（开源前必须处理）**

| # | 发现 | 指针 |
| --- | --- | --- |
| P1-1 | **P10-F1**：4d 构建期校验块锚定内部 commit，切断 12.2.0（实测）/8.2.0（读源）的一切 fresh 复放路径，连带击穿 p7 CI 两腿；且失败形态为原样 git fatal 无诊断文案 | §3.2；`s2/replay2.log`；`build-toolchain-12.2.0.sh:105,190+`、`build-toolchain-8.2.0.sh:235` |
| P1-2 | 无入口文档：根 README/复现指南/官方包获取/术语入口四缺；12.2.0 README 引用不存在的「root repository instructions」 | §2.4 |
| P1-3 | `ref/wch-toolchain-private.md` 未跟踪但无 ignore 防护，一次 `git add -A` 即混入公开仓库 | §1.1 |
| P1-4 | 39 片 message 证据指针 75% 对外悬空（含 3 片规格来源指针）——「每片能向上游 reviewer 解释」在克隆环境不成立，须按 §6-⑤ 选定处置 | §2.1 |

**P2（建议处理）**

| # | 发现 | 指针 |
| --- | --- | --- |
| P2-1 | EVT apply.sh 步骤零文档 → golden 静默缩水 246/274（无非零退出）；本地 `evt-golden.sh` 无分母断言（CI 侧有） | §3.1-B6 |
| P2-2 | replay 包装器依赖 gitignored 活动镜像树作锚（p7 的 prepare-sources 替代件未合并前，12.2.0 对外无一键路径） | §3.1-B4 |
| P2-3 | 两份 README 复现序列 `repo=` 硬编码 + 15.2.0 的 `cp "$active/…"` 五行对外必死 | §2.3 |
| P2-4 | `scripts/full-census/partition-check.py:20` 硬编码绝对 REPO 路径（收编件带着开发机坐标进了版本库） | §1.2 |
| P2-5 | linux 复现驱动未版本化（tmp/phase3h/），p7 合并前 linux 腿对外不可复现 | §3.1-B8 |
| P2-6 | 3 个 .DS_Store 已跟踪；仓库 .gitignore 无 .DS_Store 行 | §1.1 |
| P2-7 | p7 四件文档修改与 main 现文的合并冲突面（须重排后才能合并） | §4.1 |
| P2-8 | 抽取脚本要求 darwin+linux 两 MRS 包同时在位；单版本复现者被迫双包 | §3.1-B3 |
| P2-9 | 8.2.0 quick golden manifest 头残留旧 `last_error` 串（已裁定对今后重生成生效，发布前重生成可顺带消除） | §1.3 |

**P3（记录）**

| # | 发现 |
| --- | --- |
| P3-1 | BUILD_JOBS 缺省 8 vs 契约 16，12.2.0 README 未提 |
| P3-2 | 会话 UUID 3 处于 DECISIONS.md；代号密度§2.2；15.2.0 README 首现 RC0x 无注解 |
| P3-3 | phase7-ci-cd.md 局部叙事过时（P2-19 已闭合、墙钟锚已存在） |
| P3-4 | `ref/wch-evt/` 下 56 个含空格/特殊字符文件名（跨平台 checkout 兼容性提示，Windows 保留字未查） |
| P3-5 | 单文件 344 MB 研究证据大档使浅克隆亦不轻（LFS/拆分属 §6-② 取舍的子项） |

---

## 6. 呈用户裁定清单

| # | 事项 | 背景 | 选项 |
| --- | --- | --- | --- |
| ① | **EVT 树是否入公开仓库** | 25,018 文件 / 仓库体积主体；是 gate 的输入语料，`wvproj.yml` CI 依赖它；WCH 官方 EVT 本身公开可下载 | (a) 原样入库（现状，复现自含）；(b) 移出为独立仓库/下载步骤（主仓库瘦身，复现多一步获取+校验）；(c) 只保留 9+精选工程（全量 gate 语料另行分发） |
| ② | **ref/wch-isa-research 的 344 MB 机器证据大档** | errata 研究的机器域记录，非工具链复现必需 | (a) 原样；(b) 单独归档（analysis 指针留存哈希）；(c) git-lfs |
| ③ | **内部过程史的公开口径**（DECISIONS.md 88 条、46 份阶段报告、plans/ 任务书） | 完整 provenance 透明 vs 大量内部代号/会话坐标/绝对路径 | (a) 原样发布（透明最大化，配术语表）；(b) 保留 analysis/ 报告、DECISIONS 精简为对外决策记录；(c) 过程史整体移入独立 archive 分支/仓库 |
| ④ | **git 历史作者身份** | 64 commits 均为 `apple <apple@apples-MacBook-Pro.local>`（个人机器名） | (a) 接受公开；(b) 发布前一次性 filter-repo 改写为项目身份（历史 sha 全变，需在封存/引用体系定稿前做）；(c) 新仓库 squash 首发（丢历史granularity） |
| ⑤ | **39 片 tmp/ 指针处置** | §2.1 三选项 (a)保留+声明 / (b)补 analysis 摘要页 / (c)改写指针重导 | 见 §2.1；(c) 与 ④(b) 若都做应同批（都动补丁文件字节与封存） |
| ⑥ | **p7 CI 合并路径** | §4.5 现状与合并前清单 | (a) 重整后合并 / (b) 归档另起 / (c) 分批合并（脚本先行） |
| ⑦ | **入口文档由谁写** | §2.4 六项缺口 | (a) 立 phase-11 文档工作流；(b) 与 ⑥ 合并为一个「发布准备」阶段；(c) 用户自写核心 README、工作流补技术面 |
| ⑧ | **发布形态** | 现仓库直接 public vs 新建发布仓库 | 与 ①③④ 强耦合：若 ③(c)/④(b)/①(b) 任一成立，新仓库首发更省；若全走 (a)，现仓库直接 public 即可 |

---

## 7. 需求回归与设计回归

### 7.1 需求回归（使命「对补丁、项目 CI 方法进行分析，做开源前检查」逐句）

- **对补丁分析**：39 片外部视角复审完成——指针普查（143 指针全分类，判据器自证+双外锚）、
  代号密度、三 README 逐份判定（§2）；p8 的可解释性审计不重做，只审外部可用性。✔
- **对项目 CI 方法分析**：p7 交付物逐件清点与过时评估、五条裁定逐条设计复核、资源估算以 p8
  实测 timings 复核、act linux 腿实证（§4，4.4 待回填/已回填）。✔
- **开源前检查**：发布面全量清点+敏感扫描（§1）、新鲜克隆复现实验（§3，预注册三预期全中）、
  分级发现（§5）与呈用户清单（§6）。✔

### 7.2 设计回归（任务书边界 1–6 逐条）

1. **analysis-only**：未修任何仓库文件、未动 patches/scripts/三镜像；唯一写面 =
   `tmp/phase10-evidence/`（含 scratch 克隆）与本报告。声明两处授权内扩展：S3 act 按任务书
   在 p7-worktree 内运行，其证据按 act-verify 设计落 `tmp/p7-worktree/tmp/p7-evidence/S4/`
   （gitignored，宿主隔离由该脚本自证）；S2 实验中 /Users/mrs/Work symlink 两次占用并复原
   （`s2/links.log` 前后值，终值=进场值）。✔
2. **合规话题零涉及**：全部按工程卫生口径；LICENSE 缺失仅登记为惯例配套缺口。✔
3. **私有笔记未读**；其未跟踪状态已确认，防护缺口登记 P1-3。✔
4. **运行面**：quick comparator 主仓库侧 0 次；克隆内部 `evt-golden.sh` 两次（缩水态与修复态）、
   `evt-compare.sh` 两次（对随仓 manifest / 对自生成 golden）——按 S2 链条解读为实验内步骤；
   若按「每版本至多一次」字面计，12.2.0 对拍多出一次，如实登记供验收裁量。克隆实验一次；
   act 容器运行一次（重型段均先经跨会话机时通报，p8 协调器确认放行）；三镜像/patches/
   scripts 零改动（出场守卫 §7.3）；主仓 toolchain-current 全程未占用。✔
5. **判据器三关**：pointer-census 自证（合成样例 + 15.2.0 gcc/0004=5 外锚 + 12.2.0 合计 62 外锚）；
   S2 预注册先于数据；镜像基线首拍误判（用猜测目录布局当探针）当场按「量的是谁」教训重测并
   留痕更正（`s0/entry-baseline.txt` 更正 2）。✔
6. **汇报**：里程碑经跨会话信送 p8 协调器（openwch-3f）两次送达并获回执；QUESTION 类全部
   落 §6 呈用户清单，未自决。✔

### 7.3 出场守卫（`s0/exit-guard.txt` vs `s0/entry-baseline{-v2}.txt`，2026-08-18T11:19Z）

- 三 patches 工作树哈希：`30f8ba45…`/`dccdf8a5…`/`89876c5c…` — 与进场值及 p9 出场守卫**逐字相同**。
- 六镜像 HEAD/tree/dirty：与进场值逐项相同（15.2.0 `5bb6a456…`/`1321f9e2…`、12.2.0 `af74531c…`/
  `0d01a497…`、8.2.0 `97b81fa8…`/`8d0d7da3…`，dirty 全 0）。
- 四条 readlink（mrs×2、wch×1、toolchain-current）：与进场值逐条相同；/Users/mrs/Work 两次占用
  的前后值四行在 `s2/links.log`，终值=进场值。
- repo HEAD `6705cce` 不变；跟踪文件修改（进场既有 9 个 EVT 应用态之外）**0**；
  新增 untracked 仅本报告。p7 worktree HEAD/status 由 act-verify 自证 before/after 逐字节相同。
- 本阶段新增物 = `tmp/phase10-evidence/`（含 scratch 克隆约 12 GB，可整目录删除）、本报告、
  act 一次运行落在 `tmp/p7-worktree/tmp/p7-evidence/S4/` 的证据（该目录 gitignored；
  scratch 克隆的清理时点留验收方决定）。
