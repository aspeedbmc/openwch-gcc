# phase-8 收口报告：三版本补丁集清理（每行可解释 / gate 不破 / 可读性·可维护性·最小化）

对象：`patches/{15.2.0,12.2.0,8.2.0}` 三套交付补丁集（15.2.0 = gcc 9 + binutils 7、12.2.0 = gcc 9 + binutils 7、
8.2.0 = gcc 4 + host 1 + binutils 2，共 39 片）及其台账、README、series、patch-id 台账。

本报告为**纯综合单元**：不跑构建、EVT 对比或任何工具链二进制，不改既有交付文件。所引每个数字与结论都给出
可独立重推的指针（文件路径 + 节/行）。唯一的自测量是 §2.4 三件封存件的自身 sha256（`shasum -a 256` 只读复算）。
凡两处来源不一致或无法落指针者，一律在原地标注，不作调和。

**指针缩写**（全部相对仓库根 `/Users/apple/Projects/openwch`）：

| 缩写 | 文件 |
| --- | --- |
| **TS** | `tmp/prompts/phase-8.md`（任务书） |
| **CL** | `tmp/prompts/phase-8.checklist.md` |
| **DEC:n** | `DECISIONS.md` 第 n 行 |
| **HO** | `tmp/prompts/main-handoff-p7p8.md`（Main 交接件） |
| **RR8 / RR12 / RR15** | `tmp/phase8-evidence/8.2.0/round-report.md` / `…/12.2.0/s3/round-report.md` / `…/15.2.0/round-report.md` |
| **LG8 / LG12 / LG15** | 三份 `tmp/phase8-evidence/<版本>/ledger.tsv`，一律引**现文的文件行号**（三份台账在 P8-R 中都增过表头注释行：LG8 的偏移注记经审计 P2-4 更正为「S1 编号 N = 文件行 N+4」并自记原错；LG12 增 3 行表头，其**现文行号比 RR12 §3 所引的多 3**，见 §10.3-4） |
| **E8 / E12 / E15** | `tmp/phase8-evidence/<版本>/`（证据根） |
| **RV** | `analysis/toolchain/phase8-review.md`（终局独立对抗审计报告） |
| **P8R** | `E15/p8r/`（15.2.0 修复轮证据根）；12.2.0 修复面证据在 `E12/{s3,scratch,probes}/`，8.2.0 在 `E8/{s3,obligations.md}` |

**修订记录**：本报告初稿（658 行）于 DEC:78 ② 被协调器通读接受；随后终局独立对抗审计（RV）判有条件放行、
P8-R 修复轮执行并验收（DEC:79、DEC:80）。**本版按 P8-R 终态重写受影响各节**，凡结论反转处保留原判与反转依据，
不做静默改写。受影响节：§2、§3.3、§5.2、§6.1、§6.4、§7（新增第五项）、§8、§9、§10。

---

## 1. 使命与验收面

### 1.1 用户使命原文与三要素

> 清理补丁，确保补丁的每一行代码都可解释；在不破坏 gate 的情况下优化代码的可读性、可维护性、最小化。

原文出处两处逐字一致：TS:7（任务书「使命（用户原话）」）与 HO:45（Main 交接件 §5 第一条）。三要素据此拆分：

| # | 要素 | 验收含义 |
| --- | --- | --- |
| 甲 | **每行可解释** | 每片补丁的每处改动可溯源到一个有证据的行为；且「代码与其自述一致」（TS:30 硬约束 9） |
| 乙 | **gate 不破** | 该版本全量口径 gate + 探针 + testsuite 零回归 + pristine 复放 tree 相等（TS:32 硬约束 11） |
| 丙 | **可读性 / 可维护性 / 最小化** | 上游惯用形态、去演化痕迹、去死代码——但让位于零差异与缺陷保真（TS:18-19 硬约束 1、2） |

### 1.2 任务书不变量清单（TS:18-33 硬约束 1–12）

| # | 不变量（一句话） |
| --- | --- |
| 1 | 缺陷保真行为不是可清理的冗余：删改前必须对官方探测该分支是否承载保真（行为面+诊断面），探不出判别输入 ⇒ KEEP-UNPROBED 不动代码 |
| 2 | 最小化让位于零差异：与 gate 面或保真面风险冲突时一律保守 |
| 3 | 改动分级 M/C/B 决定回归深度，预注册不得事后降级；C/B 的重建验证可按版本轮合批（协调器 2026-08-17 修订） |
| 4 | 单补丁单单元：镜像历史重写先声明后执行 → 重导 → pristine 复放 tree 相等 + patch-id 台账 → 按级回归；禁止攒片再验证 |
| 5 | 单写者守卫可执行化：protected 集基线（三 patches tree、各镜像 HEAD/tree、三组 readlink）每单元进出复核，非本单元漂移即 abort |
| 6 | B 级行为探针至少三侧（官方 / 改前我方 / 改后我方），同 cwd 同 argv、零 normalize；需区分 WCH 特性与我方回归时补 vanilla 第四侧 |
| 7 | 验证器独立性：计数机器派生自证据文件，判据不得由产出被验数据的同一段脚本硬编码，断言测量前预注册 |
| 8 | 探针必须对**重建后的最终 install 树**重放，不接受 dev 中间构建 |
| 9 | 「代码与其自述一致」是验收面：每片 message 的每个技术声称逐一对补丁内容核对 |
| 10 | 范围：patches/ 三版本 + 必要的 plans 回填 + tmp/phase8-evidence/；不改 harness 比较语义、不改 analysis 历史报告正文、不触 ref/、不动私有笔记、不 commit 仓库根 |
| 11 | 轮末该版本全量全绿（12.2.0 quick 274；8.2.0 quick 242 + 全量 43969；15.2.0 quick 274×2 + 全量 47797×2 + XW+LTO + SR-01/02/03 + DCXW）+ 探针集 + testsuite 对 pristine 零回归 + 复放 tree 相等；未触碰版本以不变性证据替代重跑；S4 三版本各终签一次 |
| 12 | 环境钉死：`SOURCE_DATE_EPOCH=1767225600`、16 项目级 workers × `make -j2`、toolchain/testsuite 16 jobs、byte-cap、`shasum -a 256`、比较零 normalize（双侧对称 `-fdebug-prefix-map` 工具链前缀归一为既定语义） |

组织面：编排与验收 = p8 协调器会话；执行 = 一版本一长驻 Opus 执行者，版本 token 制并行（TS:3、DEC:57、DEC:64）。
交付面定义见 TS:59（checklist 全勾 + 三版本台账终态 + 轮报告×3 + 本报告 + 摘要）。

---

## 2. 三版本清理面汇总

### 2.1 片数与 M/C/B 计数

| 版本 | 片数 | M（message/README/series/tsv） | C（源码注释/空白） | B（代码结构） | 指针 |
| --- | --- | --- | --- | --- | --- |
| 8.2.0 | 7（gcc 4 + host 1 + binutils 2） | **8 项**，落 5 片 + README + patch-id.tsv | **1 项**（host/0002） | **0 项**（全部候选评估后 KEEP） | RR8 §1 |
| 12.2.0 | 16（gcc 9 + binutils 7） | **9 + 6 + 3**（gcc 9 片 message-only；binutils 6 项 message 修正；README×2 段 + `plans/gcc-12.2.0.md` row9） | **5 + 7 + 2**（gcc 5 项；binutils 7 项；F2 两处门注释） | **6 项** | RR12 §1 |
| 15.2.0 | 16（gcc 9 + binutils 7） | 16 片 message 终稿：清理轮为 **8 MSG-ONLY / 2 HDR-ONLY / 6 CODE**（归一化口径见下） | riscv.cc 注释归属与语义更正、`xw_enabled` 注释改述、两处续行对齐、三个 `.d` 的 `##` 理由注释 | 两对折叠 + 两处不可达 `case INSN_CLASS_XW` 删除（−5 行）+ 一处析取项删除，**该删除已由 P8-R 回退**（§6.4） | RR15 §1、E15/impl/byte-classification.tsv、RR15 §9 |

15.2.0 的 patch-id 增量：**相对入库前（phase-3h 终态）10/16 不变**——`patches/15.2.0/README.md:281-283`
「Ten of the sixteen patch ids are unchanged」；16 个补丁文件名全部不变。P8-R 轮内再次变更的只有 gcc `0003`/`0007`
（DEC:80），两片本就在清理轮已变的 6 片之内，故相对入库前的「6 变 / 10 不变」总账不变。
（备稿曾预测 5/11，因 row23 取分支 B 多出 U-C2 单元而前进一格，E15/drafts/README.md:54-59。）

byte-classification 的**归一化口径**（审计 P3-14 要求补记）：8/2/6 是剥去 `index <hash>..<hash>` 行后的比较结果，
裸字节口径为 6/0/10；RR15 §1 已补该注，终态分类以 `E15/impl/byte-classification.tsv` 为准。

### 2.2 代表性改动（逐版本）

**8.2.0**（RR8 §1、§2；LG8 文件行 14/24-27/30/48/62-63）
- M 批：`gcc/0003` 四项——首段措辞由「x 必需、w 可选」的嵌套语义改为「两个独立可选步骤」（与代码 `:70-74` 的平级 `if` 一致）；
  补判别轴证据（`18-march-w-axis` 16 探针：`rv32imacw` 接受且 `.s` 与 `rv32imacxw`/`rv32imacx` 基线同 sha、`rv32imacwx`/`rv32imacww` 拒收）；
  补汇编器拒绝裸 `w` 的原文指针；把行首 64 位 sha256 缩进两格，使 `git patch-id --stable` 第二字段从被污染值回归为自身 `From <sha>`。
  另：全片证据指针根统一为 `tmp/toolchain_8.2.0/…` 完整前缀；`binutils/0001` 增单调置位缺陷保真注；README 断句；
  en-route 去掉 `gcc/0005` message 里硬编码的 `host/0002` commit sha。
- C 批：`host/0002` 增一 hunk，把 `gcc/system.h:197-198` 注释同步到上游 `releases/gcc-15` 逐字措辞。
  **整轮相对进场态的源码差异只有这两行注释**：`git diff --stat 3260ccd8…97b81fa8` = `gcc/system.h | 4 ++--`，语义 token 变动量 = 0（RR8 §1 末段）。
- B 批 0 项：五处「看似冗余」候选（multilib 续行、单点调用谓词函数、`section_name` 头部声明、四块 RVC 立即数 case 重复、四个 print case 重复）经评估全部 KEEP，理由均为「上游惯用形态」或「生成器原样输出」（RR8 §3）。

**12.2.0**（RR12 §1、E12/unit-records/U3-record.md:55-81）
- M：gcc 9 片补 `gcc/ChangeLog:` 段（以 stdlib 驱动上游 `contrib/gcc-changelog` 校验 **9/9** 通过，DEC:66）；`gcc/0004` 补 ICE 落证指针；
  binutils 0003/0004/0005/0006 六项 message 修正（含把 isa-research 引用从 §4.2 更正为 §3.1、补「因 rv32ix 在 WCH 侧被接受故删除上游用例」的理由）。
- C：`riscv.cc:3328-3330` 续行恢复上游 GNU 对齐；`riscv.h:531-532` 宏注释补 XLEN 掩码语义；`c-attribs.cc` 目标无关落点补来源注释；
  binutils 侧 `zmmul.d` 字符类统一、`tc-riscv.c` case 'F' 缩进回上游形态、`riscv-opc.c` 表头注释上移一行（**四行 WCH 表项一步未动**，表序属行为面）。
- B 六项：`riscv_epilogue_uses` 死子表达式删除（局部恒真，见 §6.4）、`MASK_ZMMUL/TARGET_ZMMUL` 掩码迁位、
  **Q-01** `--w_priv_spec` 运行期化、**Q-02** `objdump -M xw` 移植、**Q-03** 表名合并（`riscv_supported_vendor_x_ext` → 终名 `riscv_supported_std_x_ext`，
  终态 `bfd/elfxx-riscv.c` 逐字节不变、全树旧名命中 0）、**P8-F2** 反汇编器 subset 绕行修复（见 §5.2）。

**15.2.0**（RR15 §1、E15/impl/stage-trees.tsv、E15/drafts/README.md）
- 折叠两对纯自消对：gcc `0003`↔`0008` 的 `riscv_hard_regno_rename_ok` 例外；binutils `0002`↔`0005` 的 Zcd `&& !xw` 收紧。
  折叠位点终态树**逐位命中折叠前冻结值**（gcc `0785aaf06ea2…`、binutils `bda204bac05c…`），即折叠不改终态源码。
- **不折叠**（承载证据的中间态）：binutils `0002`→`0005` 的 riscv_ip 门重写、`0002`→`0007` 的 12 行表序迁移——
  两者的 message 承载 3h 任务书强制内容（诊断状态表、65,536 半字表序穷举），折叠即销毁证据叙事（DEC:63 Q1）。
- B 级删除：`bfd/elfxx-riscv.c` 两处不可达 `case INSN_CLASS_XW`（−5 行，三调用点静态穷举）——**保留有效**；
  另一处删除（`riscv_wch_fast_interrupt_saved_reg_p` 的 `|| regno == RETURN_ADDR_REGNUM`）的「恒真」前提
  被终局审计实测证伪，**已按 DEC:63 预注册条款回退**，详见 §6.4 与 §8.3。
- C 级注释语义反转修复：`riscv.cc:7507` 的上游注释「Return true if the current function must save register REGNO.」
  被新函数抢占，而该函数返回 true 表示「硬件已保存 ⇒ 软件不保存」，语义正相反——注释还给 `riscv_save_reg_p`，新函数补写自己的语义行（LG15:13）。
- 16 片 message 终稿：指针根统一为仓库相对、RC0x 内部代号首现处加括注、binutils `0004` 改为上游父提交视角、
  `0008` 折叠后成纯测试片故改述为「钉住官方行为的回归守卫」；gcc 9 片 changelog 校验 0 error/0 warning。
- 文档：README E1–E6（两处旧编号清零、3g 覆盖面措辞按实测改写、新增 Phase 8 节与 **Known deviations** 节，表仍 16 行）。
- 副产品：binutils 系列对 BFD 的改动收敛为 `0001` 的一行表项（RR15 §1 末）。
- **P8-R 追加（R-1…R-5，P8R/DECLARATION.txt）**：R-1 回退析取项并重写注释（B 级）；R-2 文档修正
  （README 的 Phase 8 段改为记述该删除与回退、删两处错误断言 → 现文 `:243-283`；ledger、RR15 §9、deviations、
  byte-classification 同步）；R-3 message 小项——按审计 P3-9 恢复 binutils `0007` 被漏掉的第三条表序约束句
  （随迁 Zcb 行与 Zcd 区间不相交，正是 8192-word 损伤类的成因）；R-4 回归（§3.3）；R-5 重签（§2.4）。

### 2.3 六棵镜像的进场 → 终态

进场值取 E8… 的守卫基线 `tmp/phase8-evidence/guard-baseline.tsv`（与 DEC:51 现场取录值三方相同）；终态值取各轮报告与封存件。

| 版本·组件 | 进场 HEAD / tree | 终态 HEAD / tree | 指针 |
| --- | --- | --- | --- |
| 15.2.0 gcc | `dfe977da3066…` / `0785aaf06ea2…` | HEAD 见下注 / **`5bb6a45665c03f5f67eee83f7a7598d135a679e1`**（P8-R 终态） | P8R/replay.log:1-2、P8R/darwin-p8r-results.tsv（build/replay 行）、`patches/15.2.0/README.md:279-281` |
| 15.2.0 binutils | `a430a09e3f7c…` / `bda204bac05c…` | `3e20c0a44ccf…` / **`22849f4548da2e1055a71b95cd78ddef3cbb5625`** | RR15 §0、stage-trees.tsv:7 |
| 12.2.0 gcc | `419ca42a7bae…` / `37559608d0be…` | `9731e5ee7010…` / **`af74531c952c78bab9089ee93af50e3a7fe992ea`** | RR12 §0 |
| 12.2.0 binutils | `d879720d2b59…` / `f7e1a27f3edf…` | `dfb77909835d…` / **`cb7b9681acb401984e98a5e5172bbdfde09eb62e`** | RR12 §0、E12/unit-records/F2-record.md 判据 1 |
| 8.2.0 gcc | `96943e02e327…` / `3260ccd8722b…` | `02be7a6dd317…` / **`97b81fa8f52fa7037045f428f41e37099ba16fdf`** | guard-baseline.tsv、E8/s3/rebuild.log、RR8 §4 步骤 5 |
| 8.2.0 binutils | `1b4136adc30d…` / `8d0d7da3c3b3…` | `8a0da1b4237c…` / **`8d0d7da3c3b3376d07ef0f76f0f00b6b913dcf40`**（tree 与进场逐位相同） | 同上 |

四点值得单列：
- **8.2.0 binutils 的源码树进出场逐位相同**——该版本 binutils 侧只改了 commit message，HEAD 变而 tree 不变（RR8 §1「B=0」与 §4 步骤 5 互证）。
- **15.2.0 binutils 的源码树在 P8-R 中逐位未变**（`22849f4548da…`，P8R/replay.log:3-4）：修复轮只动 gcc 链与
  binutils 的 message（R-3 恢复 `0007` 第三条表序约束句，P8R/DECLARATION.txt `units` 行）。这是 SR-01/02/03、DCXW、
  gas/binutils 套件按 TS:32 不变性勾定、不重跑的直接依据（P8R/darwin-p8r-results.tsv `invariance` 行）。
- 15.2.0 gcc 的**清理轮终态**（P8-R 之前、含被回退的删除）是 `8fe2bd16714dcce1d0573ccb7efaf0189c889d8b`
  （RR15 §0、E15/impl/stage-trees.tsv:3；审计的 clean-room 复放当时命中的正是该值，RV §2.1），
  回退后前进为 `5bb6a45665c0…`。P8-R 终态 HEAD 未在修复轮证据件内记录；可核的等价把手是末片导出 `From` 行
  `d14602eb4df12e4660c69d88f389cce509bf7f56`（`patches/15.2.0/gcc/0009-…patch:1`；15.2.0 的 `From` 行为真实 sha，DEC:65）。
- 三版本均保留旧末态引用：`refs/openwch/phase8-pre-cleanup-15.2.0`（RR15 §0）、
  `refs/openwch/phase8-pre-repair-15.2.0`（P8R/DECLARATION.txt `backup_ref`）、
  `refs/openwch/phase8-12.2.0-pre-u3-{gcc,binutils}-*` 与 `…-pre-f2-binutils-*`（E12/unit-records/U3-record.md:20-21、F2-record.md:62）。

### 2.4 交付面封存件

P8-R 之后三版本各持有一份**交付面**封存件（DEC:62 Q3 形态），三件均带自述头并签在各自全部文档编辑之后。
自身指纹为本报告落稿时以 `shasum -a 256` 对三件只读复算所得（唯一一次只读复算，不涉任何构建或工具链二进制）：

| 版本 | 封存件 | 覆盖 / 自验 | 自身 sha256 | 指针 |
| --- | --- | --- | --- | --- |
| 8.2.0 | `E8/phase8-8.2.0-SHA256SUMS`（**v2**） | 10 项（series、patch-id.tsv、README.md、7 片），`generated_utc 2026-08-17T10:03:05Z`，自验 10/10 OK | **`9a265b1ff37cf5fc…`** | 件头 `:1-11`（含 v2 重签理由=审计 P1-2）、DEC:80 |
| 8.2.0 | `E8/phase8-8.2.0-SHA256SUMS.v1`（冻结留痕） | v1 原件，`generated_utc 2026-08-17T06:16:06Z` | `323025c762dc0180…` | 文件本体；v1→v2 仅 README.md 一项哈希变化（`23661604a2d2…` → `188c970e0d8b…`） |
| 12.2.0 | `E12/phase8-12.2.0-SHA256SUMS`（**新建**，审计 P1-5） | 20 项（README、patch-id.tsv、两 series、16 片），`generated_utc 2026-08-17T10:10:03Z`，自验 20/20 OK | **`c189dedebaf5d37f…`** | 件头 `:1-9`、RR12 §8「封存重签的细节」 |
| 12.2.0 | `E12/s3/sealed/{manifest.txt,run-files.sha256}`（**v2**） | run 件 **390/390 OK**（v1 为 389 OK / 1 FAILED） | — | RV §3 P1-5、RR12 §8 |
| 15.2.0 | `E15/phase8-15.2.0-SHA256SUMS`（**P8-R 重签**，带自述头，审计 P3-15） | 20 项，`generated_utc 2026-08-17T11:46:24Z`，头内记封存时两棵树（gcc `5bb6a456…`、binutils `22849f45…`）与自验 20/20 OK | **`f7a37b9b35a6a7ee…`** | 件头 `:1-7`、DEC:80 |

封存次序纪律的完整历史：P2-9「先签后改」在 phase-6 两次复发（v1 签于 23:51 → README 次日 01:05 被改；
v3 签于 03:38 → README 03:46 再被改），p8 用 `E8/s3/seal.sh` 的「一切文档编辑之后运行并当场自验」纪律处置（RR8 §8、DEC:62）。
**该纪律在 p8 内被证明只覆盖了一半问题**：12.2.0 的 run 件封存 v1 仍有两个同源缺陷，都出自
`s3/run-round-end.sh` 的写入次序——`:136` 先 `find | xargs shasum` 落封存、`:137` 才写 `toolchain-current.after`，
于是①把仍在增长的 `driver.log` 一并入账（`:65` 的 `exec > >(tee -a driver.log)` 使其在封存后继续写入 `ROUND-END: ALL PASS`）
⇒ 自指封存、自验必然 389/1；②漏掉 `:137` 之后才产生的 `toolchain-current.after`。
v2 两者都修正（`driver.log` 排除、其最终内容哈希 `fe598a7c17c5…` 单记进自述头，文件完整保留），自验 390/390 OK（RR12 §8）。

---

## 3. gate 终签数字

**口径**：三版本终签数字 = 各版本**轮末批**（打重建后的最终 install 树）的实测值——8.2.0 与 12.2.0 为清理轮轮末批，
**15.2.0 为 P8-R 修复轮**（§3.3）；均已由协调器现场复测通过（DEC:72 / DEC:76 / DEC:77 / DEC:80）。
数字逐条转录自轮报告与其引用的原始日志。

> **终签勾定（DEC:78 ①，初稿的待勾项已闭合）**：CL:71「三版本 gate 终签（全量口径各一次）」不另跑第四次运行，
> 按 TS:32「未触碰版本以不变性证据替代重跑」成立，证据四条：①封存件自验（8.2.0 10/10、15.2.0 20/20；
> 12.2.0 经 P8-R 补齐为 run 件 390/390 + 交付面件 20/20，DEC:79 P1-5）；②三个 `patches` 目录在各自封存时点后
> mtime 扫描零改动；③六镜像 tree 与各轮终态逐一相同（12.2.0 另有 patch-id 16/16 重算与 P7 官方脚本重导逐字节自证）；
> ④**install 树未动**这条腿由审计代测成立（15.2.0/12.2.0 各 0 新文件、8.2.0 活体 install 对清单 2261/2261 OK，
> RV P2-10；DEC:79 令补记）。另有我方侧 quick 独立锚定 3/3（§10.2 #7）。

### 3.1 8.2.0（宿主 x86_64/Rosetta）

重建参数：`host_arch=x86_64`、`build_jobs=16`、`SOURCE_DATE_EPOCH=1767225600`、`install_files=2261`、
`script_sha256=3c3ac48c508faa591c4fb17e7fbe6f2551945638c7eb70c49d32bdf785cbe640`（RR8 §4 头）。

| 步骤 | 预注册判据 | 实测 | 判定 |
| --- | --- | --- | --- |
| 1 探针 834 | 793I / 41X / 0M | `probes=834 gate_IDENTICAL=793 excluded=41 mismatched=0 diff_files=0 missing_files=0` | PASS |
| 2 quick | 242/242、fail 0 | `gate_pass=242 gate_total=242 gate_fail=0 aux_match=241 aux_diff=4` | PASS |
| 3a 全量主腿 | 1170 工程全 MATCH | `projects=1170 gate_match=42285 gate_diff=0 gate_missing=0 gate_extra=0` | PASS |
| 3b 扩展腿（link-only 工程的 .o） | 33 工程 / 1684 产物全 MATCH | `projects=33 objects=1684 gate_match=1684 gate_diff=0 gate_missing=0 gate_extra=0 halts=0` | PASS |
| 3c 独立分区判据 | 三条分区断言 + 两腿身份一致 | 12/12 断言全过，`PARTITION-PASS total=43969` | PASS |
| 4 gas 套件 | 183/3/7/0 | `183 expected passes / 3 expected failures / 7 unsupported / 0 unexpected`（193 结果行、18 个 `xw-` 用例） | PASS |
| 5 git 级复放 | 两树等于预注册值 | gcc `97b81fa8f52f…` / binutils `8d0d7da3c3b3…` | PASS |
| 6 symlink 复位 | 等于进场值 | `toolchain-current -> tmp/phase3g-evidence/ours-v3.0-frozen`，前后一致 | PASS |

**gate 合计 43969/43969 零差异**（42285 + 1684），且该 43969 是**首次**由单次运行、同一 golden、同一 install 树、
并带顶层「不重不漏」分区证明的端到端证据产生（见 §5.1）。原始行表：`E8/s3/regression-results.tsv`（末行 `ALL-REGRESSION-PASS`）。

比字节 gate 更强的一条旁证（RR8 §4b）：重建前后对 install 树 2261 个文件逐一取 sha256，**只有 1 个不同**——
被改注释头文件的安装副本 `lib/gcc/riscv-none-embed/8.2.0/plugin/include/system.h`；`cc1`/`cc1plus`/驱动/`as`/`ld`/`objdump`
全部 byte-identical（`cc1` 前后同为 `d57e7de2…`），清单 `E8/s3/install-manifest.{pre,post}-rebuild.txt`。
aux 面 699→701 的增量逐条归因为 R5 已裁定的 `.lst` 闪烁豁免类，`.map` 失配集合与 phase-6 逐一相同（RR8 §4c）。

### 3.2 12.2.0

权威 run：`E12/s3/run-20260817T065202Z/`（`ROUND-END: ALL PASS`、`DRIVER_EXIT=0`）；全程墙钟 4m45s（RR12 §2）。

| 判据 | 期望 | 实测 | 判定 |
| --- | --- | --- | --- |
| P0 守卫 | 四 HEAD/tree 命中、镜像 clean、harness 无漂移 | 全命中；`evt-compare.sh = 7ee93e19…` | PASS |
| P6a 复放（建前） | 两组件 tree 命中 | gcc `af74531c952c…`、binutils `cb7b9681acb4…`，MATCH + vs-active MATCH | PASS |
| P1 重建 | rc=0、16 jobs、`SOURCE_DATE_EPOCH=1767225600` | rc=0；清洁构建（build 目录无条件清空，gcc 973/973 + binutils 283/283 个 `.o` 当轮新编，无 ccache）；宿主依赖按 marker 钉死复用 | PASS |
| P2 quick | 274/274、`gate_fail=0` | `gate_pass=274 gate_total=274 gate_fail=0 aux_match=273 aux_diff=4`（4 项全 `.map`，DEC:17 裁定不入 gate） | PASS |
| P3 四测试集对 vanilla | 四集 raw PASS→FAIL/ERROR 全 0 | 四集 rc=0、无 now-fail 块；riscv 2007→**2430**（两侧同 62 个宿主既有 FAIL）、c-attr 4→4、c-params 190→**192**、cxx-attr 36→36 | PASS |
| P4 GAS `riscv.exp` | PASS=210（202 + 8 新增）、FAIL=0 | `PASS=210 FAIL=0 UNRESOLVED=0`，新增 8/8 命中 | PASS |
| P5 官方-我方全字扫描 | 全部逐字节相同 + 默认模式中性 | `compared=162 differing=0`，默认模式断言成立 | PASS |
| P6b 复放（建后） | 两组件 tree 命中 | 两侧 MATCH | PASS |
| P7 export 常量回填 | diff 仅四行常量；重导逐字节相同 | diff 8 行（`gcc_head`/`gcc_tree`/`binutils_head`/`binutils_tree`）；官方脚本重导与现状 `diff -r` 为空 | PASS |
| P8 封存 | manifest + 文件哈希 + symlink 复位 | 390 项哈希；`toolchain-current` 前后一致 | PASS |

### 3.3 15.2.0（双平台）

**终签口径**：15.2.0 的终签数字取 **P8-R 修复轮**（在清理轮之后、对回退后的终态树）的实测值。
清理轮的 SR/DCXW/套件三面在 P8-R 中不重跑，依据是 binutils 源码树逐位未变（§2.3），按 TS:32 不变性勾定；
其数值仍为清理轮实测（RR15 §2）。下表分列标注来源。

**darwin-arm64（P8-R 10/10 + 不变性勾定一组）**

| 段 | 判据 | 实测 | 来源 |
| --- | --- | --- | --- |
| build+freeze | staged tree 命中 | gcc `5bb6a45665c03f5f67eee83f7a7598d135a679e1` 命中 | P8R/darwin-p8r-results.tsv |
| quick | 274/274/0 | `gate_pass=274 gate_total=274 gate_fail=0 aux_match=273 aux_diff=4` | 同上；P8R/quick.console 末行 |
| full | 47797 全 MATCH | `FULL-ASSERT-PASS 47797/47797` gate、aux 47784/819、1298 工程 | 同上；P8R/full-assert.txt |
| 探针 | 321/0 | `321 comparisons / 0 mismatches` | 同上 |
| **ra-flags 矩阵（P8-R 新增常设项）** | 官方 == 回退后我方 == 清理前树；且探针须自证判别力 | **16 组（2 源 × 4 flag × 2 个 -O 档）A/B 失配 0；C 档判别力 4 格**——回退前的 p8 树在 `-fcall-saved-ra` × {fi_simple,fi_cond} × {-Os,-O2} 四格被判出（`sw ra` 官方 0 / p8 1）；`RA-FLAG-PROBE-PASS` | P8R/ra-flags.console 末四行、P8R/ra-flags/*.tsv |
| 复放 | 两树 + patch-id 16/16 | gcc `5bb6a45665c0…` / binutils `22849f4548da…`；`ASSERT patch-id 16/16 PASS` | P8R/replay.log:1-5 |
| dumpmatrix 确定性（审计 P2-1） | marker 列独立轮次零漂移 | `marker 列独立轮次 0 漂移` | P8R/darwin-p8r-results.tsv |
| 资源纪律 | 两条 symlink 复位 | `resource-record` / `resource-restore` 双 PASS | 同上 |
| SR-01/02/03、DCXW、gas·binutils 套件、XW+LTO | 按 TS:32 不变性勾定（binutils tree 逐位未变） | 清理轮实测值沿用：SR-01 A=0/B1=3/B2=4（47 项二进制比较）；SR-02 rows 392、`{WCH,OURS-P8}²` 0 失配、历史侧对 3h 封存 288 cell 0 不同；SR-03 138 probe 零失配、历史侧 828 行 0 不同；DCXW 48 cell / 3,145,728 word / 0 missing、`stream a6ac473136e61f5f…` **与预注册冻结值相同**（审计 P3-16：该串是驱动内预注册常量，控制台只打印布尔比较结果，非实测输出）；gas 650/0/23/9、binutils 234/2；XW+LTO 100/192/492/0 SEALED | RR15 §2；P8R/darwin-p8r-results.tsv `invariance` 行 |

**linux-amd64（P8-R，`LINUX-ALL-PASS`）**：preflight（linux/amd64、双挂载同树）→ prepare（series 复放命中两棵冻结树）→
build → quick `gate_pass=274 gate_total=274 gate_fail=0`、aux 273/4（**与 darwin 同值**）→
full `FULL-ASSERT-PASS 47797/47797`、aux 47784/819、1298 工程 → XW+LTO 100/192/492/0 SEALED → `toolchain-current` 复位
（P8R/linux-results.tsv）。

墙钟：P8-R darwin 全段 **15m37s**（DEC:80）。清理轮分段墙钟（build 7m02s、quick 3s——与 3h 的 16-worker 基线逐秒相同、
full 8m02s、探针 1s、DCXW 20s、SR-01 20s、testsuite 38s；darwin 合计约 17 分钟、linux 约 1h38m）见 RR15 §3。

---

## 4. 跨版本移植与移植原则

### 4.1 移植原则（协调器立，DEC:66 原文）

> p8 可把用户已批准的行为对齐设计跨版本移植（前提=官方该版本现场实测存在同一可观测面），
> 不得自行发起新的行为修复（xlen 类维持另立呈用户）。

该原则由 12.2.0 的 U1 探测「翻案两问」触发：两处原本登记为清理项/未决项的东西，经官方实测发现是**能力面缺口**而非冗余，
按 TS:31 硬约束 10 的范围定义本不属「清理」；协调器据此立原则并批准两项移植（DEC:66），同时把
xlen=32 类（无用户已批准的对齐设计在案）挡在 p8 之外（DEC:63 Q4）。

### 4.2 Q-01：`--w_priv_spec`（binutils/0005 的 vendor strcmp 运行期化）

**官方 12.2.0 现场实测**（E12/probes/U1-conclusion.md 结论 1，只调用 `ref/gcc/darwin-arm64/12.2.0/bin/riscv-wch-elf-{as,objdump,readelf}`）：

| 探针 | 结果 |
| --- | --- |
| `--w_priv_spec` | rc=0，生成 `Tag_RISCV_priv_spec: 1` + `Tag_RISCV_priv_spec_minor: 11` |
| `-w_priv_spec`（单横线）/ `--w_priv`（缩写） | rc=0，同上 ⇒ 走 `getopt_long_only` |
| `--w_priv_spec=0` | rc=1，`option '--w_priv_spec' doesn't allow an argument` ⇒ `no_argument` |
| `--w-priv-spec` | rc=1，`unrecognized option` ⇒ 选项名逐字为 `w_priv_spec` |
| `as --help`（5124 B） | `w_priv`/`wch` 0 命中 ⇒ **隐藏**，不入 `md_show_usage` |
| 幂等 | 给两次与给一次的 `.o` 逐字节相同 |
| 默认（不给选项） | CSR / `.attribute arch` / `-mpriv-spec=1.11` / `--wchsoftlib` 各组合下 `Tag_RISCV_priv_spec` 计数均为 0 |

门的因子分解与 15.2.0 phase-3h 的 `w_priv_spec && (arch_attr || explicit_attr)` 同构：`w_priv_spec` 是唯一 WCH 新增因子，
`arch_attr || explicit_attr`、`start_assemble`、`explicit_priv_attr` 都是上游自带守卫（同源探针对官方 15.2.0 `as` 行为一致）。
我方现形态 `strcmp (TARGET_VENDOR, "wch") == 0 → return` 等价于「该标志永远为关」：**默认行为与官方逐字相同、EVT gate 中性**，
差的是官方存在而我方没有的可观测选项面（U1-conclusion.md §「对 row5 / Q-01 的意义」）。

**实施**（E12/unit-records/U3-record.md:64-71，规格取自官方实测而非照搬 15.2.0 代码）：
`static bool w_priv_spec = false;` + `OPTION_W_PRIV_SPEC` + `{"w_priv_spec", no_argument, …}` + `md_parse_option` 分支；
`riscv_write_out_attrs` 的早返回由 `strcmp (TARGET_VENDOR, "wch") == 0` 改为 `!w_priv_spec`，**位置不动**
（arch 属性写出之后、上游 priv 合成之前），故显式 `.attribute priv_spec` 路径照常写出（官方实测同）；不入 `md_show_usage`；
单横线由 `getopt_long_only` 提供，`--w` 与 `--wchsoftlib` 共前缀会 ambiguous——与官方一致。

**验收**：轮末 P4 GAS `riscv.exp` 210/0/0（含新增 8 个 `.d`）、P5 官方-我方多模式全字扫描 162/0、P2 quick 274/274（RR12 §2）。
第四象限（`-mno-arch-attr` + 选项 + CSR ⇒ 零输出）一度被判「无法用 `.d` 表达」，经读 binutils 2.38
`binutils-common.exp:580-584` 源码推翻，落成空期望 `.d`（DEV-P8-12-03，RR12 §5、U3-record.md:84-96；官方侧零输出实测
`E12/probes/gas-gate/on-no-arch-attr.attr` 为 0 字节）。

### 4.3 Q-02：`objdump -M xw`（反汇编开关移植）

**官方 12.2.0 现场实测**（U1-conclusion.md 结论 2）：`objdump --help` 的 RISC-V 段逐字列出四个选项
`numeric` / `no-aliases` / **`xw`** / `priv-spec=SPEC`，`xw` 条目两行文本（第二行以两个 TAB 起始）与官方 **15.2.0**
对应段落 `diff` 为空、逐字相同。对含 XW 压缩编码的对象（`.text` 原始字节 `88218a2188a18aa10880288048806880`）：

| 命令 | 输出 |
| --- | --- |
| `objdump -d`（默认） | `2188 .2byte 0x2188` …八条全部不解码 |
| `objdump -d -M xw` | `lbu a0,0(a1)` / `lhu` / `sb` / `sh` / `lbu a0,0(sp)` / `lhu` / `sb` / `sh` |

两者 `cmp` DIFFER；官方以**普通助记符**而非 `c.` 形式打印、sp 形式也打印为 `lbu a0,0(sp)` ⇒ 首匹配落在 alias 行，
**表序是行为面**（与 15.2.0 phase-3h 的表序守卫同一约束）。`-M XW`/`-M no-xw`/`-M bogusopt` 均报
`unrecognized disassembler option: <首字符>`。我方原形态是 `riscv-dis.c:631` 的无条件
`if (op->insn_class == INSN_CLASS_XW) continue;`——只复现了「默认不解码」这一半。

**实施**（U3-record.md:73-81）：`static int xw_disassemble` + `set_default_riscv_dis_options` 复位 +
`parse_riscv_dis_option_without_args` 增 `xw` + 整类 skip 改 `&& !xw_disassemble` +
`riscv_options[]` 在 `no-aliases` 与 `priv-spec=` 之间插入条目（描述串内嵌 `\n\t\t`，逐字复刻官方 `--help` 两行）+
`print_insn_args` 新增 `case 'X'` 打印四类 XW 立即数（四组映射对官方实测边界 31/62/15/30 手工验算一致）。**表序未动**。

**验收**：全字扫描含 D+C 对象 2188 的 `fld`→`lbu` 翻转对照（DEC:70）、P5 162/0、P4 中两个 `-M xw` 新用例转绿（RR12 §2、§4b）。
此项移植同时暴露并修掉了一个真代码缺陷 P8-F2（§5.2）。

### 4.4 移植的边界（未移植项）

- **xlen=32 的 rv64 分歧**不纳入 p8：属行为修复而非清理，15.2.0 已在 README「Known deviations」如实登记，跨版本处置呈用户（DEC:63 Q4、DEC:69）→ §7 ①。
- 12.2.0 的 KEEP-NO-TOUCH 五项（P8-R 按 `final_status` 重列，RR12 §3）：GCC 侧不做 m→zmmul 隐含（LG12:27）、
  `can not use both …` 官方逐字诊断（`:29`）、`params.opt` 帮助串（`:34`）、`binutils/0004` 的 GAS 侧嵌套 if（`:42`）、
  `wch_softlib` 静态量不省（`:48`）。**`riscv-opc.c` 表序不在此列**——它是 LG12:38 提案里的一句约束
  （只上移注释、表序禁动），已随 U3 执行完毕（审计 P2-8 的更正）。

---

## 5. 发现与修复

### 5.1 P8-F1：phase-6 的 43969 曾是时间拼接，p8 首次取得统一分区证据

**现象**（RR8 §6b）：8.2.0 轮末 S3 步骤 3 首跑，主 runner 在**前置一致性检查**即抛异常，未进入任何编译或比较：

```
RuntimeError: golden/census baseline reconciliation failed:
{'golden_projects': 1203, 'census_gate_projects': 1170,
 'golden_gate_rows': 43969, 'census_gate_rows': 42285, 'identical': False}
```

**根因在时序里**（RR8 §6b mtime 时间线）：

| 时刻 | 事件 | 口径 |
| --- | --- | --- |
| 08-16 19:08 | `tools/full-census/ours_runner.py` 最后修改 | 硬断言 `golden_projects==1170 and golden_gate_rows==42285` |
| 08-17 01:31 | phase-6 主腿最后一次成功运行 | `gate_match=42285`，**扩展前** |
| 08-17 08:57 | `linkonly_runner.py` 落地 | 无同类硬断言 |
| 08-17 08:59 | 扩展腿运行 | `objects=1684` |
| 08-17 09:01 | `analysis/golden/8.2.0-darwin-arm64-full.tsv` 按 P2-21 重固化 | **1203 工程 / 43969 行**，主 runner 的常量未同步 |

即 phase-6 验收数字 43969 = 「扩展**前**的一次 42285 运行」+「扩展**后**的一次 1684 运行」的**时间拼接**：
两腿从未在同一时刻、同一 golden、同一 install 树下同时成立；主 runner 自 golden 扩展后从未被端到端跑过，
故断裂潜伏到 p8 轮末批首次执行该路径才暴露。**定性 = 过程证据缺口，不是行为缺陷**——两腿各自跑过且全绿，
旧 42285 行未被扩展改动（DEC:71 裁定原文同此定性）。

**修法（裁定：选项 a 强化版 = 分区化，DEC:71）**：
1. `ours_runner.py` 的对数块改为从**当前** golden 按其自带 `class` 标记派生主腿视图（`gate` → 1170/42285；
   `gate-link-only` → 33/1684），并新增两条分区穷尽断言，**去掉硬编码计数**——今后再扩展 manifest 不会重演静默过期。
   「用扩展前的旧 golden 跑主腿」的拼接口径被明确否决：那会把事故固化成方法。
2. 步骤 3 拆为 3a 主腿（1170 工程）/ 3b 扩展腿（33 工程）/ 3c **独立分区判据器**，两腿打同一最终 install 树。
3. 判据器 `E8/s3/partition-check.py` 不读任何一腿的自产 summary/stdout，只读当前 golden 与两腿的逐产物**原始行表**
   （`ours-artifact-results.tsv` / `compare-artifacts.tsv`）及各自 `identity/toolchains.json`，独立重算：
   ①行 42285+1684=43969 且与 golden 行集不重不漏；②工程 1170+33=1203 不重不漏；③两腿 install 树身份彼此一致且等于活体安装树；
   ④两腿全部 gate 行 status 均为 MATCH。

**结果**：12/12 断言全过，`PARTITION-PASS total=43969`；协调器现场复测另核「两腿同 gcc sha、同 install 路径、
legs-match-live-install 全 ok」（DEC:72）。本轮因此是 43969 这一数字**首次由单次、同一 golden、同一 install 树、
带顶层不重不漏证明的端到端证据链**产生的一次，证据强度高于 phase-6 验收时的拼接口径（RR8 §6b「强化结论」）。

判据器自身的两处解析缺陷（DEV-P8-04）在 v1 报 FAIL、v2 12/12 全过，两腿数据未重跑；`regression-results.tsv`
同时保留 v1 FAIL 与 v2 PASS 两行，不抹除失败历史（RR8 §7）。

### 5.2 P8-F2：`-M xw` 的 subset 绕行缺陷——唯一真代码缺陷，被本轮新增用例拦下

**现象**（RR12 §4b）：run `run-20260817T063207Z` 的 P4 报 PASS=208 / FAIL=2（期望 210），两个 FAIL 全是本轮新增的
`-M xw` 用例（`wch-xw-disassemble`、`wch-xw-disassemble-noalias`）；dejagnu 日志里我方 objdump 重复吐
`internal: unreachable INSN_CLASS_*`。**默认模式不受影响**——`-default` 用例通过、P2 quick 274/274 通过，
预注册的「默认模式 gate 中性」断言成立。

**根因链三步，每步都有本项目自己的记录佐证**：
1. **S1 就记到了**：LG12:41（S1 row38）写明 `riscv_multi_subset_supports` 没有 `INSN_CLASS_XW` case，其 `default:` 会报
   `internal: unreachable INSN_CLASS_*`，「仅靠两处守卫使其当前不可达」，判 KEEP-UNPROBED；LG12:42（S1 row39）同时记下
   GAS 侧嵌套结构是**承载性**的、禁止扁平化，理由正是要绕开该调用。
2. **U3 亲手拆掉了那个前提**：Q-02 把 `riscv-dis.c` 的整类 `continue` 改成 `&& !xw_disassemble`，于是 `-M xw` 打开后
   XW 行第一次真的走到那个调用；当时 row38 的裁定「注释固化不变式、不补 case」在守卫仍无条件时是对的，
   但 Q-02 改变了前提，而 row39 已写明的绕行结构没有被同步搬到反汇编器侧。
3. **新增用例把它捕获**：两个新 `-M xw` 用例 FAIL。

**修法（裁定 DEC:75）**：取 15.2.0 现行双门实现（经 49152×5 穷举对拍验证）的语义等价 2.38 适配形——
门 1 由 `-M xw` 标志控制 XW 行是否参与匹配（`riscv-dis.c:679`），门 2 让 XW 行豁免架构检查
（`:695` 加 `op->insn_class != INSN_CLASS_XW &&`）。15.2.0 多出的 `!pd->all_ext` 在 2.38 无对应物
（`-M max` 是 2.45 才有的选项；**作用域限定**：`grep -c all_ext opcodes/riscv-dis.c` = 0——对 binutils-2.38 全树
`grep -rn` 会得 2656 个子串命中，`grep -rnw` 才为 0，照抄不带作用域的命令会误判该语义等价论证不成立，审计 P3-4），
去掉后两侧语义逐条相等（E12/unit-records/F2-record.md:9-21）。
**否决**「给 `riscv_multi_subset_supports` 补 `case INSN_CLASS_XW`」：官方在 `-M xw` 下对**没有 xw 架构属性**的
纯 D+C 对象照样解码，补 case 会让解码依赖属性、与官方相悖。该实测的**出处**是 U3 时段的
`E12/probes/u3-spec-detail.log`，不是 U1——`U1-conclusion.md` 附带取证 2 自陈「本轮未取到官方侧 D+C 与 XW 的同槽对照对象」
（审计 P3-3 的署名更正；审计另自行实测该行为，两侧一致，RV §4.3）。修复折入 Q-02 移植片（binutils `0004`），未新开补丁位，表序未动；
连带 row38 注释按新前提改写（原不变式前提已被 Q-02 拆除）。修后 P4 210/0、P5 162 项全逐字节相同。

**两条教训（RR12 §4b 原文口径）**：
- **若无本轮新增的 8 个 dejagnu 用例，该缺陷会随交付出厂**——它对既有 gate（274/274）、对默认模式、
  对全部 202 个上游 GAS 用例都完全不可见，只在新增能力面被触发。能力面每加一条可观测开关，就必须同时加覆盖该开关的用例；
  「gate 全绿」不能替代「新能力有测试」。
- `KEEP-UNPROBED` 的不变式一旦被后续单元改动了前提，必须回台账重判，而不是沿用当初的裁定——row38 的裁定在 U3 之后就已失效。

---

## 6. 缺陷保真面处置

TS:18 把「缺陷保真行为不是可清理的冗余」列为 p8 最大陷阱，并要求诊断/保真面与 gate 产物同标准（DEC:18）。本阶段四类处置：

### 6.1 Q4：ICE 消息内嵌的编译器自身源码行号不入保真面

**探测**（RR8 §5、LG8 文件行 38，探针件 `E8/probes/{run-eh-return.sh,out/compare.tsv,FINDING.md}`）：
7 源 × {`-S`,`-c`} × 两侧，测 `interrupt("WCH-Interrupt-fast")` × `__builtin_eh_return`。

- **官方缺陷共享事实**：该组合在**官方与我方两侧都触发 ICE**——同一 pass（`split2`）、同一函数
  （`riscv_set_return_address`）、同一触发条件、同一用户源码位置，两侧 14/14 的 rc 与产物 sha256 逐条相同；
  三个对照组（`interrupt("machine")`+eh_return、普通函数+eh_return、fast 无 eh_return）的 stdout+stderr 亦逐字节相同。
  崩点是 `gcc_assert (BITSET_P (cfun->machine->frame.mask, RETURN_ADDR_REGNUM))`——WCH 快中断规则把 ra 移出保存掩码，
  而 `__builtin_eh_return` 必然走到该函数。**这不是我方引入的缺陷，是上游 riscv 后端与 WCH 特性叠加的既有缺陷，两边同样具备。**
  对照组 `interrupt("machine")` 不崩，正因 `calls_eh_return` 分支（我方树 `riscv.c:3400`）把 ra 强制留在掩码内——
  这同时证明该分支确实被走到，探针有区分力。
- **唯一差异**：ICE 文本内嵌的编译器自身坐标，官方 `config/riscv/riscv.c:3646` vs 我方 `:3651`。可对数：
  pristine 该断言在 3622，我方（`gcc/0004` 前五个 hunk 3+5+1+17+3，五个 hunk 起点均 < 3622）插入 29 行——
  **这一半可独立复算**（审计已复算成立，RV P3-2）；官方的「插入 24 行」则是由坐标差 `3646−3622` **反推出的定义式**，
  官方无源码、物理上不可独立验证。两者并列时须注明证据强度不同（审计 P3-2 的措辞要求）。

**裁定（DEC:65）**：该坐标与 `Compiler executable checksum` 同类，属宿主源码布局量，**不入诊断保真面**；
合法手段不可对齐（凑行数被可解释性硬规则明禁）。**推广范围 = 一切被我方补丁触及文件内的 ICE 坐标**；
坐标之外该 ICE 的 pass / 消息 / 触发条件两侧一致，照常作为官方缺陷共享登记。

**豁免的界定（审计 §5 提示，本报告补记）**：该豁免是对**「坐标差异」这一类差异**的处置规则，
不是「我方补丁触及文件内不存在其他 ICE 差异」的断言——它由 **n=1** 的探针（8.2.0 的 eh_return × fast-interrupt 组合）
外推而来，未对补丁触及文件内的其他可达 ICE 做扫描。12.2.0 在 P8-R 中补的 row23 探针是该规则的**第二个实例**
（两侧同 pass、同函数、同断言、同用户源码位置，唯一裸差异为 ICE 内嵌坐标 官方 `riscv.cc:4173` vs 我方 `:4169`，
窄口径下六项 stderr 全同；RR12 §3、`E12/probes/row23-eh-return.{sh,log}`），不构成穷举。

### 6.2 `eh_return`：从「边界未探」到 EXEMPTED

审计遗留项「`gcc/0004` 的 D4a 早返回绕过上游 `calls_eh_return` 分支，边界未探」在 S1 台账登记为 B 级 PROBE 项，
经 U3 探针探明后结案 **EXEMPTED**：行为面 14/14 零分歧、gate 影响 0（EVT 无 `__builtin_eh_return`，且该组合两侧均无产物），
唯一分歧即 §6.1 的行号 ⇒ **代码不动、message 不动（保持最小）**（LG8 文件行 38 与 64、DEC:65）。
该项也是 8.2.0 轮 `KEEP-UNPROBED = 0` 的最后一块（RR8 §3 末）。

### 6.3 `wch_rvc_extension` 单调置位：从「未探边界」升格为有官方对照的缺陷保真

phase-6 审计 P3 第 1 条指出 gas 侧 `wch_rvc_extension` 只置位、无复位路径。p8 补探针组 19（`19-attr-arch-monotonic`，
12 探针 + `monotonic.tsv`，四源 × 三 `-march`）：`mono-d.s` 以 `.attribute arch,"rv32imac_xw"` 后接
`.attribute arch,"rv32imafdc"` 再 `c.fld`，**官方与我方 d1/d2/d3 全 rc=1、两侧 IDENTICAL**；`mono-a/b/c` 三组同为两侧 IDENTICAL
（LG8 文件行 48）。据此把该项从「未探边界」升格为**有官方对照的缺陷保真面**，处置写进 `binutils/0001` message：
gas 内 `riscv_set_arch` 是该标志唯一写者且只置不清、与官方一致，并写明「**加复位路径是行为改动而非清理**」。
协调器同批钉死：「补复位路径」类提案一律驳回（DEC:62）。

### 6.4 `ra` 的三版本对照：一次被证伪的「恒真」与它的回退

**本节结论在 P8-R 中反转。** 原判（清理轮）：同形析取项 `|| regno == RETURN_ADDR_REGNUM` 在 15.2.0 上恒真可删、
在 12.2.0/8.2.0 上是活代码——即「同形不同判，且各自都对」。终局审计实测证伪了 15.2.0 的那一半，
删除按 DEC:63 的预注册条款回退。**现状：三版本同形同判，该析取项在三个版本上都是活代码、全部保留。**

#### 6.4.1 静态前提（三版本，仍然成立）

引用口径统一为「宏行 + 数据行」双引用；三行数值由各版本执行者在**各自源码树**现场复核（RR12 §4 括注、RR8 §6 末段），
审计另行独立实读并**加验了 `FIXED_REGISTERS`**（RV §4.3）：

| 版本 | 引用 | `CALL_USED_REGISTERS` ra | `FIXED_REGISTERS` ra | 现状判定 |
| --- | --- | --- | --- | --- |
| GCC 8.2.0 | `riscv.h:252` 宏，数据行 `:254`（FIXED 见 `:240`） | **0** | **0** | **保留**：若无该项，ra 会落进 `call_saved && might_clobber → true` 被软件保存，与官方 p01 实测（非叶处理函数既不存 ra 也不存临时寄存器）相反（RR8 §6） |
| GCC 12.2.0 | `riscv.h:312` 宏，数据行 `:314`（FIXED 见 `:300`） | **0** | **0** | **保留**（台账 `final_status = KEEP-VERIFIED`）：ra 属 call-saved ⇒ `call_used_or_fixed_reg_p (ra)` 为假 ⇒ 载荷有效（RR12 §3、§4） |
| GCC 15.2.0 | `riscv.h:338` 宏，数据行 `:340`（FIXED 见 `:322`） | **1** | **1** | **一度删除 → P8-R 回退保留**（台账 `ledger.tsv:14` 改判 `KEEP-VERIFIED`）：静态前提为真，但「恒真」结论不成立，见 6.4.2 |

审计对 `FIXED_REGISTERS` 的加验有独立价值：若 GCC 12 的 ra 是 fixed，12.2.0 的 KEEP 判定就会是错的；
实测排除了该证伪路径（RV §4.3）。

#### 6.4.2 「恒真」论证的失效机理

被删项的论证是：ra 同时在 `FIXED_REGISTERS` 与 `CALL_USED_REGISTERS` 内 ⇒ `call_used_or_fixed_reg_p(1)`
（= `fixed_regs[] || call_used_regs[]`，`hard-reg-set.h`）恒真 ⇒ 析取项恒被前项吸收。
**两条静态前提都被审计证实**，失效点在「恒真」这一步：它要求穷举所有能改写这两张表的位点，而该穷举没有做——
S1 只查了 `riscv_conditional_register_usage`，漏了命令行改写路径。`gcc/reginfo.cc:661` 的 `fix_register()`
只对 `STACK_POINTER_REGNUM` / `HARD_FRAME_POINTER_REGNUM` / `FRAME_POINTER_REGNUM` 设防（`:674-678`），
其余寄存器一律执行 `fixed_regs[i] = fixed`（`:720`）与 `call_used_regs[i] = call_used`（`:723/725`）——
**ra 不在设防名单内，`-fcall-saved-ra` 可把两位同时清零**（RV §3 P1-1；执行者独立读源复核，P8R/DECLARATION.txt `mechanism_read`）。

**实测分歧**（`-Os -march=rv32imac -mabi=ilp32 -fcall-saved-ra`，fast-interrupt 非叶处理函数调用 `sink()`）：
官方与清理前树输出 `call sink` / `mret`（ra **不**软件保存），p8 清理后树多出 `sw ra,12(sp)` / `lw ra,12(sp)`——
`sw ra,` 计数 **官方 0 / 清理前 0 / p8 1**，分歧由清理轮引入（RV §3 P1-1 的三侧表；执行者独立复现，P8R/DECLARATION.txt `independent_repro`）。
`-ffixed-ra` 与 `-fcall-used-ra` 两侧相同，只有 `-fcall-saved-ra` 触发。
跨版本控制组：12.2.0 与 8.2.0 保留该析取项，两版在同一 flag 下官方与我方**均为** `call sink` / `mret`、零分歧（RV §3 P1-1）——
即该析取项正是各版本在该 flag 下维持官方一致的那一行。

**gate 影响中性**（审计独立验证）：`grep -rl -- "-fcall-saved\|-fcall-used\|-ffixed-" ref/wch-evt scripts tests` = 0 命中，
故 274 / 47797 / 43969 与全部封存 gate 数字不受影响；但 EVT 树内有 **1654** 个文件使用 `WCH-Interrupt-fast`，
受影响的函数类别本身是主力路径（RV §3 P1-1）。

#### 6.4.3 回退与 ra-flags 矩阵

处置走 DEC:63 自己预注册的路径「异动即回退转 KEEP+注释」（DEC:79 裁定、DEC:80 验收）：
①恢复析取项，注释改写为**实际机理**（`fix_register()` 只设防栈/帧指针 ⇒ `-fcall-saved-ra` 可清 ra 两表位；
硬件保存集含 ra 故必须显式列出），**明令不得复述已被证伪的恒真论证**，并按审计 P3-13 去掉
"whole call-clobbered GPR set" 的不准确表述；②`patches/15.2.0/README.md` 删除 "It makes no behavioural change."
与恒真推理段，改写为记述该次删除与回退的段落（现文 `:262-272`）；③台账 `ledger.tsv:14` 改判 **KEEP-VERIFIED**，
`impl/deviations.tsv` 新增 **DEV-P8-15-08**（本阶段唯一真回归，已回退）。

新增常设回归项 `ra-flags` 矩阵（P8R/ra-flags.console、`ra-flags/*.tsv`）：2 形状 × 4 flag × 2 个 `-O` 档 = **16 组**，
四侧 = 官方 / 回退后我方 / 清理前树 / 回退前 p8 树，判据 = `.s` 与 `.o` 逐字节。结果：
**A/B（官方 == 回退后我方 == 清理前树）失配 0；C 档（回退前 p8 树）在 `-fcall-saved-ra` × 2 形状 × 2 档共 4 格被判出**
（`sw ra` 官方 0 / p8 1）——即该探针**自证具备判别力**，不是又一条零判别力的绿。

**结论（RR15 §9 的撤回声明）**：原先「同形不同判」的论断建立在被证伪的恒真前提上，现予撤回；
真正的跨版本事实是——该析取项在三个版本上都是活代码，三版本形态一致。
（残余：RR12 §4 的跨版本表仍留着「15.2.0 恒真冗余，可删」一行，未随 P8-R 同步，
见 §10.3-4 的登记；本报告以 RR15 §9 + DEC:79/80 为准，不代为改写他人轮报告。）

#### 6.4.4 仍然成立的两条辨析

**机制（让本段自含）**：表里 ra=0 并不违反 ABI——ra 的调用破坏建模在 **call RTL** 上，不在这张表里。上游注释就写在该宏正上方，
8.2.0 `riscv.h:249-250` / 12.2.0 `:309-310` / 15.2.0 `:335-336` 三处逐字相同：

```c
/* a0-a7, t0-t6, fa0-fa7, and ft0-ft11 are volatile across calls.
   The call RTLs themselves clobber ra.  */
```

**约束：该注释不是版本判别依据。** 它在 GCC 15 里原样保留，而同一宏的 ra 已改为 1——GCC 15 把 ra 的调用破坏一并写进了表、
却没有同步这段注释。因此判定某版本的 `|| regno == RETURN_ADDR_REGNUM` 是死是活，**不能读这段注释**（RR12 §4）。
**P8-R 给这条约束加了后半句**：读该版本的数据行是**必要而不充分**的——15.2.0 的数据行确实是 1，
而该析取项照样是活代码，因为数据行只是**默认值**，命令行 `-f{fixed,call-used,call-saved}-REG` 可在其后改写它（§6.4.2）。

**两种不同的死因不可互搬**：12.2.0 本轮实际删除的是**另一处**——`riscv_epilogue_uses` 内的同形析取项（S1 基准 `riscv.cc:4659`），
其死因与 ra 的调用约定无关：该函数在入口处已对 `RETURN_ADDR_REGNUM` 无条件 `return true`，属**局部**恒真
（审计独立复核该函数入口 `:4651-4652` 确为无条件 `return true`，RV §4.3）；同版本 `riscv_save_reg_p`（终态树 `:3909`）
与 `riscv_hard_regno_rename_ok`（`:5416`）两处保持不动，台账终态记 `KEEP-VERIFIED`（RR12 §3、LG12:24）。

---

## 7. 呈用户裁定项

以下五项均已在协调器层做完事实澄清，但处置权在用户；本报告只给背景与选项，不预设结论。
（第五项为终局审计 P2-2 提出、DEC:79 接受后新增。）

> **处置结果（2026-08-17 用户裁定，详见 DECISIONS 末段）**：①=另立 phase-9 工作流（选项 b）；②=统一为真实 sha + 四列 tsv（已落地）；③=收编 scripts/full-census/（已落地）；④=a 项核实早已闭合、b 项打保存引用 refs/openwch/phase4-s2-head、c 项并入 phase-9、d 项三 darwin 脚本补校验块、f 项补齐两版本导出脚本；⑤=**追认**，移植原则入档为评估框架但不授权自裁——今后新的能力面移植仍逐案呈用户。本节原文保留为裁定时点的输入材料。

### ① `xlen=32` 的 rv64 分歧（跨版本不一致 + 官方无此限制）

**背景**。三版本的 XW opcode 表项在 xlen 字段上不一致：12.2.0 与 15.2.0 写 **32**
（`patches/12.2.0/binutils/0004-…patch:492`、`patches/15.2.0/binutils/0002-…patch:536`），8.2.0 写 **0**
（`patches/8.2.0/binutils/0001-…patch:798-802`）。15.2.0 侧的官方对照已在 p8 内实测（Q4 轻量探针，
DEC:68 授权、DEC:69 落证，证据 `E15/impl/q4-probe/`）：**官方 15.2.0 的汇编与反汇编两面在 rv64 下均不设限**——`as -march=rv64imac_xw` 接受
`c.lbu` 并发出与 rv32 相同的编码 `8821`，官方 `objdump -d -Mxw` 把该对象解出 `lbu a0,0(a1)`；我方 rv64 侧拒收
（`unrecognized opcode … extension 'zcb' required`）且 `-Mxw` 打印 `.insn 2, 0x2188`。rv32 两面逐字相同。
已按裁定写入 `patches/15.2.0/README.md:278-292`「Known deviations」，**不改码**（DEC:63 Q4、DEC:69）。
gate 中性成立：全部 EVT 工程与全部 gate 产物均为 rv32。

**选项**：(a) 维持现状——README 登记已知偏离，跨版本不一致保留（p8 立场：这是行为修复而非清理）；
(b) 另立工作流，把三版本统一到官方无限制语义（需先对 12.2.0 官方 rv64 面补同款探测——p8 只探了 15.2.0），
按行为修复口径走完探测 → 实现 → 双平台 gate；(c) 只统一为「三版本内部一致」而不追官方（不推荐：与官方面仍分歧，收益仅剩一致性）。

### ② 补丁导出的 `From` 行约定差异（12.2.0 zero-commit vs 15/8.2.0 真实 sha）

**背景**。核实结论（DEC:65）：15.2.0 与 8.2.0 的补丁 `From` 行是真实 commit sha，12.2.0 是全零 commit——
现文可直接验：`patches/15.2.0/gcc/0001-*.patch:1` = `From f893b93cbfb0…`、`patches/8.2.0/gcc/0001-*.patch:1` = `From 1abae7a36525…`、
`patches/12.2.0/gcc/0001-*.patch:1` = `From 0000000000000000000000000000000000000000`。
各版本**内部自洽**（`patch-id.tsv` 的列形也不同：8.2.0 为 `component/patch/stable_patch_id/source_commit` 四列，
12.2.0 与 15.2.0 为前三列、不带来源列），协调器已裁定**不强行统一**、留用户知悉。
相关：8.2.0 的 `stable patch-id` 才是跨两次 message 改写的稳定把手（README 已补说明，LG8 文件行 63）。

**选项**：(a) 保持现状（各版本内自洽，导出脚本不动）；(b) 统一为真实 sha（需改 12.2.0 导出脚本并重导全部 16 片，
patch-id 第一字段不受影响，但文件字节与封存件需重签）。

### ③ full-lane 工具仍在 gitignored `tmp/` 未版本化（P2-19）

**背景**。8.2.0 全量腿的三个 runner（`census_runner.py`、`ours_runner.py`、`linkonly_runner.py` 及配套）位于
`tmp/toolchain_8.2.0/tools/full-census/`——gitignored，不随仓库走（`git ls-files` 无命中）。HO:30 记该项为审计 **P2-19**
并注「p7 可能要收编」；同族的既有注脚见 DEC:28 ①「机器证据在 gitignored tmp/ 下不随仓库走，可复算需另归档」。
**p8 使其更紧要**：P8-F1 的修法把「分区化对数块」写进了 `ours_runner.py`（DEC:71 授权的定点写权），
即**当前 43969 gate 的证据机器本身已经带有 p8 的修正，而这份修正没有版本化**；同类地
`E8/s3/partition-check.py` 也只存在于证据树内。

**归属的出处**：本报告初稿曾标注「未能在权威来源中找到『p7 已结束』的记录」（盘面最接近的只有 DEC:72
「下一槽让渡 p7 linux act 腿（协作方全阶段唯一剩余活、已久候）」）。DEC:78 ④ 与 DEC:79 补记其出处为
**用户 2026-08-17 的会话指令**（会话 transcript 为证，盘面无记录如实承认）。审计对此的判读是：
该补记未给可核指针，属「用无证据断言替换一个被诚实标注的缺口」（RV §5 表末行），故本项的**责任归属仍需用户裁定**；
DEC:79 亦已把 full-lane 工具归属正式列入呈用户清单。

**选项**：(a) 收编进仓库（`tools/` 或 `scripts/`），连同 partition 判据器一起版本化，并把 43969 的分区判据固化为可复算件；
(b) 归档为证据快照（打 tar + 内容哈希入 `analysis/`），不进 `scripts/` 主路径；(c) 维持现状（接受不可复算风险）。

### ④ 台账中其余标 OUT-OF-SCOPE 且指向用户层的项

三份台账内 `status=OUT-OF-SCOPE` 共五行，均为 p8 范围外（TS:31 硬约束 10）而非缺陷：

| 台账行 | 内容 | p8 处置 | 需用户/协调器决定的点 |
| --- | --- | --- | --- |
| LG12:14 | P3-5 `ref/Archive.zip` / `ref/dec.tar` 未 gitignore | 不处置——DEC:22 已裁「ref/*.zip、ref/*.tar 加入 gitignore」，且硬约束 10 明确不触 `ref/` | 已裁定项，仅需确认现状与裁定一致 |
| LG12:15 | P3-7 `analysis/toolchain/phase4-diff-inventory.md:4` 引用的 S2 commit 仅 reflog 可达 | 不处置——硬约束 10 不改 analysis 历史正文 | 是否另开一次「历史报告指针修复」小项（会改既有报告正文） |
| LG15:46 | P3-4 `scripts/build-toolchain-15.2.0.sh:59-63、305、317` 的 `gcc_build_tflags` 脚手架残留 | 仅登记——p8 范围为 `patches/` + plans 回填，harness 不改 | 是否立 harness 清理小项 |
| LG15:47 | darwin 构建脚本不做 series/patch-id 校验，linux 脚本做（`build-toolchain-15.2.0-linux.sh:84-85、171-248`） | 仅登记；但 S2 改补丁后必须同步 linux 脚本常量（已执行，DEC:69「各两行，diff 单列」） | 是否把 linux 脚本的逐片 patch-id + 冻结 tree 三重校验反向移植到 darwin 脚本（提高两平台对称性） |
| LG15:48 | `plans/roadmap.md` 存在未提交改动（非该单元造成） | 报协调器知悉 | 入库时如何处置该未提交改动（p8 不 commit 仓库根，TS:31） |

补正（审计 P3-11、P3-19）：LG15:48 只记了 `plans/roadmap.md`，**漏记 `plans/gcc-12.2.0.md` 同样有未提交改动**；
另 `plans/roadmap.md` 现文仍记 phase-7「执行中」、phase-8「S1 重基线进行中」，且严格说 `roadmap.md` 不在 TS:31
列举的 `plans/gcc-*.md` 回填范围内——入库时一并需要用户/协调器口径。

### ⑤ Q-01 / Q-02 跨版本移植的追认（审计 P2-2）

**背景**。DEC:66 的「移植原则」由**协调器自立**，据此给交付的 12.2.0 工具链新增了两个此前不存在的可观测选项面
（`--w_priv_spec`、`objdump -M xw`，见 §4）。审计的原文理由（RV §3 P2-2）三条：
①按用户使命的字面（「清理…优化可读性、可维护性、最小化」），这是**能力增补而非清理**；
②它直接产生了本阶段唯一的真代码缺陷 P8-F2（§5.2）；
③协调器把**结构同类**的 xlen=32 能力缺口升级给了用户（§7①，理由「行为修复非清理」），却自裁了 Q-01/Q-02——
区分标准（「有用户已批准的对齐设计在案」）本身自洽，但 TS:55 的升级条款包含「形态改造类设计歧义」，
而 closure 初稿只把四项呈用户，Q-01/Q-02 **仅以既成事实出现在 §4**、未作为决策项呈交。

**正方论据**（支持维持）：官方 12.2.0 现场实测确证两个面都是**官方已有、我方缺失**（§4.2/§4.3），
移植后默认模式 gate 中性、全模式全字扫描 162/0（RR12 §2 P5），审计独立复算四模式产物逐字节相同、
`objdump --help` RISC-V 段 diff 为空（RV §4.3）；移植使 12.2.0 与 15.2.0 形态一致，并消除了
`strcmp (TARGET_VENDOR, "wch")` 这一「用 triple 字符串当行为开关」的可解释性缺陷（DEC:66）。
**反方论据**（支持另立工作流）：使命字面只授权清理；能力面扩张会带入新缺陷（P8-F2 即实例，虽被新增用例当场拦下）；
与 xlen=32 的处置标准不一致，两者都是「官方有、我方无」的能力缺口。

**选项**：(a) 用户追认既成事实（保留移植，记为使命范围内的对齐）；
(b) 用户追认但要求把同类判断标准写成规则（何时自裁、何时升级），供后续阶段沿用；
(c) 回退移植、另立能力面工作流（须重跑 12.2.0 轮末全套：quick 274、四测试集、gas 210、全字扫描 162）。
指针：DEC:66（原则与两项批准）、DEC:70（Q-01/Q-02 探测闭合）、DEC:75（P8-F2 裁定）、DEC:79（P2-2 接受、列为本项）。

---

## 8. 偏差台账汇总

### 8.1 三版本 DEV 全表

**8.2.0（RR8 §7）**

| 编号 | 一句话 | 处置 |
| --- | --- | --- |
| DEV-P8-01 | 首次重建用 `nohup … &` 叠加工具后台化，工具按启动器 exit 0 收尾并回收进程组，构建在 `gcc-all-gcc` 阶段被 SIGKILL（阶段日志零编译错误、lock 残留即实证） | 执行者失误、非补丁面；改双 fork 完全脱离进程组重启，清理动作先声明后执行 |
| DEV-P8-02 | 守卫量选错：S1 用 `git rev-parse HEAD:patches/<v>`，只读已提交树，对未提交改动不敏感（改了 8 个文件该值仍不变） | 更正为工作树内容哈希；协调器采纳为三执行者标准（DEC:65） |
| DEV-P8-03 | S3-1 指令的「同步内嵌 tree/patch-id 常量」在该脚本上是空操作（脚本只锚定 base tag，无终态常量） | 如实登记、不虚构改动；穷举证据在 `E8/unit-records.md` S3-1 |
| DEV-P8-04 | 分区判据器 v1 两处**自身解析**缺陷（按 `gate-link-only` 读扩展腿行表读成空；`d["ours"]` 混合 dict 取值 `TypeError`） | gate 数据无涉；v2 下同一批两腿数据 12/12 全过、两腿未重跑；`regression-results.tsv` 保留 v1 FAIL + v2 PASS 两行 |
| **P8-R 重签（审计 P1-2）** | `patches/8.2.0/README.md:150` 的一键复现脚本断言 gcc 树 `3260ccd8…`（p8 **进场**值，已被 U2 的注释同步作废），任何正确复现者会被 `test` 判失败；`:155-159` 措辞亦为 phase-6 原样留存；错值随 v1 封存件交付 | 改为 phase-8 终态 `97b81fa8…` 并改写措辞；封存件重签 **v2**（v1 冻结留痕，见 §2.4）；README 断言经实测复放闭环（DEC:80）。**另按审计 P2-4 修正台账行号偏移注记**（原写 +2 且四个示例全错，实际 +4，注记自身也算在内） |
| **P2-3 义务销账** | `obligations.md` 两项 S3 义务（0004/0005 的 PASS tuple 复算、重建后复跑 U3 探针）从未实测执行，却被 RR8 §9 宣告「全部结案、无悬置」 | 按 TS:32 不变性口径**显式销账**而非沉默：重建前后 `cc1`（`d57e7de2…`）/`cc1plus` 逐字节相同，2261 个安装文件唯一差异是被改注释头文件的安装副本，两项重跑物理上不可能得出不同结果；销账落 `obligations.md:88/125/153`、RR8 §9 限定块 |

**12.2.0（RR12 §5、§8）**

| 编号 | 一句话 | 处置 |
| --- | --- | --- |
| DEV-P8-12-01 | export 脚本头值钉死旧 HEAD | P7 步骤闭合（四行常量回填 + 官方脚本重导逐字节验证） |
| DEV-P8-12-03 | Q-01 第四象限一度判为无法用 `.d` 表达 | **改判进 dejagnu**——2.38 `regexp_diff`（`binutils-common.exp:580-584`）与 2.45 语义相同，空期望 `.d` 即零输出断言 |
| DEV-P8-12-04 | `binutils/0005` 主题与文件名更名 | 协调器追认（旧主题与新代码不符即违反 message-vs-code 验收面，DEC:70） |
| DEV-P8-12-06 | P2 判据串假设空格分隔（实为 TAB）→ 274/274 下**假停** | 判据器修正、预注册值不变；假停 run 留痕（DEC:73 ①） |
| DEV-P8-12-07 | P3 v1 命令层级错 + `.sum` 未逐集快照 → 无有效测量 | 照抄 phase-4.1 权威命令重写，差分改用 `contrib/compare_tests` |
| DEV-P8-12-08 | P4 命令层级错（应为 `-C <build>/gas`） | 被「上岗前干跑」拦下，**未产生无效 run** |
| DEV-P8-12-09 | F2 预注册措辞未计上下文位移（写成「其余六片 identical」） | 措辞缺陷非数据问题；已双证 0005/0007 为纯上下文位移（逐 index 累积树对照 + `+/-` 行逐字比较） |
| OBS-P8-12-02 / -05 | 观察到 `patches/8.2.0`、`patches/15.2.0` 的并发写者 | 均在版本 token 授权内，协调器消解（DEC:66、DEC:70） |

**12.2.0 的 P8-R 五项**（RR12 §8，审计驱动）

| 审计项 | 内容 | 处置 |
| --- | --- | --- |
| P1-3 + P2-11 | README 的 Phase-8 终态指向**已废弃历史** binutils `d3236cae…`（F2 修复折入前的中间态，`merge-base --is-ancestor` 为否）；两段叙述时序倒置，线性读者会得出「最终 gcc HEAD = `0dcdfa56`」。按它复现会得到缺 F2 门 2、缺三个 priv-attr 用例的树，GAS 套件退回 `PASS=208 FAIL=2` | README `:98-129` 按实际时序重排（U2 在前、U3+F2 在后），末态只出现一次且为真值 `dfb77909…`/`cb7b9681…`，并补记 F2 修复的作用 |
| P1-4 + P2-5 | 台账**根本未回填终态**（24 行 STILL-PRESENT、5 个 QUESTION 留在纸面），且表头树等式失效导致全表行号系统性失准 | 统一到 15.2.0 **九列口径**：前 7 列 S1 判定逐字未改（`scratch/ledger.pre-P8R.tsv` 留痕 + diff 验证），追加 `final_status`/`final_evidence`；**49 行全部有终态、STILL-PRESENT/QUESTION 残留 0**；表头改写为「S1 行号属旧基准、终态行号属现基准（`af74531c…`/`cb7b9681…`）」并逐条重验（`scratch/reverify-lines.log`） |
| P2-6 | 「message 指针 55/55」不可复算且引用件过期（`scratch/evidence-pointers.tsv` 早于 U3/F2 的 message 重写） | 作废旧值，对现文 16 片重算：**61 行 / 56 unique / 61 EXISTS / 0 MISSING**，与审计独立计数一致 |
| P2-7 | RR12 §2 声称 P1 数字「全部取自权威 run 的原始日志」，而 973/283 与 ccache 结论实出自被假停取代的首个 run | 出处改署 `driver-changes.md` 的首 run 计数；清洁性对每次 run 成立的**静态**依据改引 `build-toolchain-12.2.0.sh:192-195` 的四条顶层无条件 `safe_remove` |
| P2-8 | KEEP 家族清单成员集与台账不符（总数 7=7 是巧合）；一条未探证的「不可达」断言（row23）从复核里滑过；row8 自陈 KEEP-UNPROBED 却两不靠 | §3 按 `final_status` 逐行重列并给台账行号；`riscv-opc.c` 表序移出（非 KEEP 行）；row8 正式列入 KEEP-UNPROBED；**row23 补探针后结案 EXEMPTED**（两侧同 ICE，坐标差异在 DEC:65 豁免内，§6.1） |
| P1-5 | 封存自验 389 OK / 1 FAILED（自指 `driver.log`），且从未产出 DEC:62 Q3 形态的交付面封存件 | run 件重签 v2 **390/390 OK**（另修复 v1 漏签 `toolchain-current.after` 的第二个同源缺陷）；新建交付面封存件 20/20 OK（§2.4） |

**15.2.0（RR15 §4、E15/impl/deviations.tsv）**

| 编号 | 一句话 | 处置 |
| --- | --- | --- |
| DEV-P8-15-01 | SR-01 判据器 `DEFAULT_SIDES["OURS"]` 硬编码改造前的 `ours-v3.1-frozen`，驱动未传 `--ours` ⇒ 量了历史树，误报 TIER-A=1 | 加 `--ours "$FROZEN"` 与独立 `--cache`；从 step 6 续跑 |
| DEV-P8-15-02 | `sr03-norvc-matrix.py` 的 `SIDES` 硬编码六棵历史树，无被测侧 ⇒ 该绿对本轮零判别力 | p8 副本加 `OURS-P8` 侧，runner diff 单列 |
| DEV-P8-15-03 | 同类硬编码侧；且该 runner 不写 `sr02-verdict.json`，断言读的是 3h 遗留文件（mtime 08-16 02:49） | 加侧 + 现算矩阵，遗留 json 作废 |
| DEV-P8-15-04 | 顶层 `make check` 在 binutils 子套件（按预注册本就有 2 条 unexpected）以 Error 2 中止，永远到不了 gas ⇒ 无 `gas.sum` | 分套件跑，退出码不作判据 |
| DEV-P8-15-05 | 断言把 `rc` 纳入 SR-02 cell 判据；实测同批产物连跑两次 **26/392** cell 的 rc 在 0/4 间翻转（对 3h 封存 15/288），而 `debug_begin_stmt` 连跑两次 **0/392**、对 3h 封存 **0/288** | 判据列改 `debug_begin_stmt`，rc 降为信息列 |
| DEV-P8-15-06 | p8 副本迁 WORK/TMPDIR 后，LTO 目标内嵌工作目录路径改变，字节不再与 3h 相同 | 无害：marker 口径下历史侧 0/288 差异 ⇒ 不改被测量，登记不回退 |
| DEV-P8-15-07 | 续跑切片含已封存的 XW+LTO，脚本以「证据根已存在」停机 | 切片起点改到最后一个真绿段之后；不可变守卫按设计正确 |
| （未编号，DEC:69 追认） | U-C2：row23 取分支 B 改三个 `.d` 使 binutils 终态树从判据值 `07d30337…` 前进到 `22849f4548da…`、patch-id 由 5/11 变 6/10 | 协调器追认；阶段树逐位可核（`E15/impl/stage-trees.tsv`、`E15/drafts/README.md:54-59`） |
| **DEV-P8-15-08** | **本阶段唯一的真回归**：删除 `\|\| regno == RETURN_ADDR_REGNUM` 后，`-fcall-saved-ra` 下 fast-interrupt 非叶处理函数与官方分歧（官方/清理前树 ra 不软件保存，p8 树保存）。根因=「恒真」只穷举了 `riscv_conditional_register_usage`、漏了 `-f{fixed,call-used,call-saved}-REG` 路径；321 项探针面不含任何 `-f*-REG` 输入，护栏零判别力 | 按 DEC:63 预注册条款**回退**：恢复析取项、注释改写为实际机理；`ledger.tsv:14` 改 `KEEP-VERIFIED`；README 删除两处错误断言；新增 ra-flags 三侧矩阵纳入常设回归（§6.4.3）。状态：已回退并复验（`E15/impl/deviations.tsv` DEV-P8-15-08、RV §3 P1-1、DEC:79/80） |
| **（P8-R 自纠，未编号）** | 新增的 ra-flags 探针**自身先出了一处假绿**：相对输出路径导致四侧编译全部失败，判据把「空 == 空」读成一致 | 由「探针必须自证判别力」这条新增强制步骤当场抓出，改为 fail-closed 后重跑（RR15 §9 第 4 条、DEC:80） |

### 8.2 停机统计：10 次仪器停机 + 1 次真缺陷停机（P8-F2）+ 1 次真回归（P1-1，审计发现）

标题按审计 P3-1 的要求如实框定：初稿写作「10 次停机，10/10 判据器/驱动缺陷，零真回归」，
把第 11 次停机（12.2.0 P4 208/2，唯一真代码缺陷 P8-F2 所致）排除在计数外——枚举本身可复算、§8.3 也已披露，
但**标题的框定弱化了唯一的实质事件**。P8-R 之后还须再加一类：终局审计发现的真回归 P1-1（§6.4、§8.3 末）。
三类分列如下。

**第一类：仪器停机 10 次。** 停机 = 使某个预注册判据段中断、或使该段产出无效测量的事件。
逐条枚举（不含被预检拦下、未产生无效 run 的 DEV-P8-12-08）：

| # | 版本 | 事件 | 类别 | 指针 |
| --- | --- | --- | --- | --- |
| 1 | 8.2.0 | DEV-P8-01 重建被 SIGKILL | 驱动 | RR8 §7 |
| 2 | 8.2.0 | DEV-P8-04 分区判据器 v1 解析缺陷（`REGRESSION-FAIL step=partition`） | 判据器 | RR8 §7、`E8/s3/regression-results.tsv` |
| 3 | 12.2.0 | DEV-P8-12-06 P2 判据串 TAB 假停 | 判据器 | RR12 §5、DEC:73 |
| 4 | 12.2.0 | DEV-P8-12-07 P3 v1 无有效测量 | 驱动 | RR12 §5 |
| 5–10 | 15.2.0 | DEV-P8-15-01/02/03/04/05/07 六次 | 判据器 ×4、驱动 ×2 | RR15 §4（该报告自记「6/6 全为判据器/驱动缺陷」）、DEC:77 |

这 10 次**全部指向仪器（判据器或驱动），无一指向被测工具链**。15.2.0 的六次由其轮报告与 DEC:77 直接如此定性；
8.2.0 与 12.2.0 的四次由各自轮报告的偏差表逐条判读得出（本报告的合并计数，按上述停机定义可复算）。
RR15 §4 的强化表述：「六次停机没有一次指向被测工具链。真绿判据在修正后逐条命中，且每条都能指认被测对象
（`ours_root`/`DRAFT_ROOT`/`--ours`/side 标签）。」

**第二类：真缺陷停机 1 次**——P8-F2（12.2.0 P4 208/2），本阶段唯一的真代码缺陷，由本轮新增用例当场捕获（§8.3）。
**第三类：真回归 1 次**——P1-1 / DEV-P8-15-08，由终局独立审计发现，**没有触发任何本项目的停机**：
它对所有既有判据面（gate 274/47797/43969、321 项探针、SR/DCXW/套件）都不可见（§8.3 末）。
第三类正是本阶段最该记住的一条：**「没有停机」不等于「没有回归」，只等于「现有判据面看不见它」**。

### 8.3 P8-F2 是本阶段唯一的真代码缺陷，且由本轮新增测试拦下

与上表 10 次仪器停机并列的另一类停机只有一次：12.2.0 run `run-20260817T063207Z` 的 P4（PASS=208/FAIL=2），
根因是 Q-02 移植带来的真代码缺陷 P8-F2（§5.2）。三个事实同时成立且互相独立：
①它对既有 gate（quick 274/274）、对默认模式、对全部 202 个上游 GAS 用例完全不可见（RR12 §4b）；
②捕获它的两个用例是本轮随移植一起新增的（RR12 §2 的 P4「8/8 命中」中的两条）；
③修后 P4 回到 210/0、P5 162/0（RR12 §2、F2-record.md 判据 6）。

#### 8.3b P1-1：本阶段唯一的真回归，由外部独立审计发现——发现 → 回退 → 矩阵验证的闭环

P8-F2 是「本轮新增能力面内的缺陷、被本轮新增用例拦下」；P1-1 则是**另一个类别**：清理动作本身引入的行为回归，
**本项目所有判据面都看不见它**，最终由终局独立对抗审计（RV §3 P1-1）实测发现。闭环三步：

1. **发现**（审计侧）。审计不接受「恒真」这一断言，转而穷举能改写寄存器表的位点，读到 `reginfo.cc` 的
   `fix_register()` 只设防栈/帧指针，据此构造 `-fcall-saved-ra` 输入并三侧实跑，得到
   `sw ra` 计数 官方 0 / 清理前 0 / p8 1 的分歧（§6.4.2）。同时自证 gate 中性
   （`-f*-ra` 类选项在 `ref/wch-evt`、`scripts`、`tests` 内 0 命中），故所有既有封存数字不受影响。
2. **回退**（执行侧）。执行者**先独立复现**审计结论（同样的三侧、同样的计数）并自行读源确认机理，
   再按 DEC:63 预注册的「异动即回退转 KEEP+注释」执行——回退不是听命于结论，而是复现之后的执行（P8R/DECLARATION.txt）。
3. **矩阵验证**（新护栏）。新增 ra-flags 常设回归项：16 组、四侧、`.s`/`.o` 逐字节，A/B 零失配、
   C 档 4 格判别出回退前树；且该探针在上岗前**被强制自证判别力**，当场抓出自身一处假绿（相对输出路径 ⇒ 四侧编译全败 ⇒
   「空 == 空」读作一致），改为 fail-closed 后重跑（§6.4.3、§8.1 15.2.0 表末两行）。

三条附带事实：①这条缺陷属「前提被断言而非被测量」族——与本阶段自记的 P8-F2 教训、任务书硬约束 1 同族（RV §3 P1-1）；
②它一度写进了**已封存的交付 README**（"It makes no behavioural change."），故修复必然连带重签封存件（§2.4）；
③预注册的回退条款起了作用：DEC:63 在批准该删除时就写了触发条件与处置，P8-R 只是执行它，无需重新裁定形态。

---

## 9. 仪器教训（两层版 + P8-R 升级的两层）

前两层按 DEC:77 的指定，从 RR15 §6 转述并保持原有深度，与 12.2.0 轮的四处驱动/预注册缺陷合并成立；
第三、四层是 P8-R 从 P1-1 事故中升级出来的（DEC:80 采纳）。四层是同一条线的四步：
**量的是谁 → 量的那一列稳不稳 → 删条件前有没有穷举它的判定输入 → 新护栏量不量得出差别。**

**第一层——判据器的默认值 / 硬编码侧 / 退出码语义，必须先对「被测对象」验证。**
15.2.0 本轮 4 次停机（DEV-01/02/03/04）与 12.2.0 轮的四缺陷同源：判据器默认指向历史树、runner 侧表写死、
`make` 退出码被当成判据。**判据器跑通不等于判据成立——先问「它量的是谁」。**
最恶劣的形态是「绿得毫无判别力」：DEV-15-02 的 SR-03 报「138 probe 全零失配」而被测侧根本不在矩阵里，
那个绿只证明了 3h 树 == WCH。

**第二层——判据取哪一列，必须先证明该列确定。**
DEV-15-05 是新的一类：`lto-dump` 的 `rc` 在同一批输入上连跑两次就有 **26/392** 翻转，
而同一行的 `debug_begin_stmt` 完全稳定（连跑两次 0/392、对 3h 封存 0/288）。
**把不确定列写进判据，等于给回归检测装了随机报警器。**

**「对封存件干跑」这道预检的盲区机理（本轮亲历）。** 进场时判据器确实对 3h 封存件干跑并命中——
但封存件恰恰**就是历史树的产物**，于是「侧选错」在预检里**必然通过**；封存件又**只有一份**，
无法暴露任何列的不确定性。也就是说，这道预检对本轮真正踩到的两类缺陷**结构性失明**。
（同源提醒：12.2.0 裁定 #3 的「上岗前对权威 artifact 干跑」确实拦下了 DEV-P8-12-08，
说明该预检对「命令层级错」有效——它的失明是**特定于**侧选与列确定性这两类，不是普遍无效。）

**两条内建 sanity（本轮新增，建议成为常规）**
1. **历史侧 cell 必须与封存值逐一相同**——抓「侧选错」「路径漂移」「加侧扰动既有测量」。
   本轮 SR-02 288 cell、SR-03 828 行均 0 差异（RR15 §2）。
2. **同输入连跑两次**——抓「判据列不确定」。任何进入判据的列都要先过这一关。

**对第二层的补注（审计 P2-1，本报告如实补记）**：SR-02 的 PASS 是**在测量之后更换判据列**取得的——
`s3/darwin-results.resume2.tsv` 记录它在预注册的 `rc` 列下 FAIL（历史侧 19 处不同、相对 OURS-3H 漂移 7 处），
换列后重判 PASS，这与 TS:28 硬约束 7「断言在测量前预注册」有张力。三点必须写明：
①**换列发生在测量之后**；②稳定性证据是**同一批 n=2**（选择效应：所选列之所以稳，是在同一对 run 上确立的）；
③不确定性**不止于 `rc`**——审计重算两次 run 的矩阵后得 `rc`、`stdout_sha256`、`stderr_sha256`、`stdout_size`
**各 26/392 且是同一批 cell**，`debug_begin_stmt` 0/392；即被观测对象在 6.6% 的 cell 上整体不确定，
所选判据列是对该不确定性取平均的粗粒度派生标记。RR15 §2 与本报告 §3.3 把「历史侧对 3h 封存 288 cell 0 不同」
作为内建 sanity 的通过项呈现时，须注明它**在原判据列下读作 19**。缓解已落地：P8-R 对 `debug_begin_stmt`
补做了**独立轮次**的确定性复验（0 漂移，§3.3 `dumpmatrix-determinism` 行），把 n=2 的选择效应降了一档。

**第三层（P8-R 新增，DEC:80 采纳）——删除一个条件之前，必须穷举它的判定输入的全部改写位点；
护栏面必须含能判别该条件的输入。** P1-1 的失败正是这两条同时缺失：「恒真」只查了一条改写路径
（`riscv_conditional_register_usage`），漏了命令行 `-f*-REG`；而 321 项探针面里没有任何一个 `-f*-REG` 输入，
于是「删条件」与「护栏能否判别该条件」被当成了一件事（RR15 §9）。**推论**：删除类改动的护栏不能沿用既有面，
必须**为被删条件专门构造**判别输入——若构造不出，该条件就不该被删（回到硬约束 1 的 KEEP-UNPROBED）。

**第四层（同批）——新探针上岗前必须自证判别力，且自证要 fail-closed。** ra-flags 矩阵的自证当场抓出探针自身
一处假绿（相对输出路径导致四侧编译全败，判据把「空 == 空」读成一致）。这与第一层的「它量的是谁」是同一问题的
下一步：**先证明它量的是谁，再证明它量得出差别**（RR15 §9 第 4 条、DEC:80）。

四处 12.2.0 驱动/预注册缺陷的共性（RR12 §5 末）：**判据或命令建立在未经验证的格式/结构假设上**
（空白分隔 vs TAB、`make` 子套件层级、「其余片 identical」未计上下文位移）。
本阶段三个 F/P1 级发现也落在同族：P8-F1 是「硬编码计数在数据源变更后静默过期」，
P8-F2 是「不变式前提被后续单元拆除后未回台账重判」，P1-1 是「前提被断言而非被穷举，且护栏对该前提零判别力」。

---

## 10. 需求回归与设计回归

### 10.1 需求回归：使命三要素逐条对照

**甲 · 每行可解释** —— 成立，证据链三段：
1. **逐声称核对已做完**：8.2.0 台账 52 行全部结案（`STILL-PRESENT=0 · PROBE-CANDIDATE=0 · QUESTION=0 · KEEP-UNPROBED=0`，
   RR8 §9 的八类结案态计数，另见其 P2-3 限定块）；12.2.0 的 message 指针可达性经 P8-R 重算为
   **61 行 / 56 unique / 61 EXISTS / 0 MISSING**（旧值 55/55 已作废，RR12 §8 P2-6；审计独立计数一致），
   16 片 patch-id 与台账逐条命中；15.2.0 的 16 片 message 终稿逐片重写并经 `contrib/gcc-changelog` 校验 0/0（RR15 §1）。
   外部锚定：审计对三份台账做了 **152/152（100%）** 抽验，pristine 复放 clean-room **6/6**、patch-id **39/39** 命中（RV §0、§2.1）。
2. **本阶段修掉的正是「代码与其自述不一致」**：8.2.0 三处（`gcc/0003` 首段嵌套语义 vs 并列代码、判别论证建立在对该轴全盲的证据上、
   汇编器拒绝声称无指针，RR8 §2）；12.2.0 六项 binutils message 修正 + `binutils/0005` 随语义改写更名（DEC:70）；
   15.2.0 的注释语义反转修复与 `0008` 定位改述（RR15 §1）。
3. **讲不清的一律不动**：KEEP 族清单成立且带理由——8.2.0 五处 KEEP（RR8 §3）；
   12.2.0 经 P8-R 按 `final_status` 重列为 **KEEP-UNPROBED 2 + KEEP-VERIFIED 1 + EXEMPTED 1 + KEEP-NO-TOUCH 5**
   （旧表述「1+6」的成员集与台账不符，审计 P2-8；RR12 §3）；15.2.0 两处承载证据的中间态不折叠（RR15 §1）。

**乙 · gate 不破** —— 成立，但**须带一条限定**：§3 三张表，三版本轮末批（15.2.0 为 P8-R 轮）全绿并经协调器现场复测
（DEC:72 / DEC:76 / DEC:77 / DEC:80）。8.2.0 的 C 级预注册断言「全部 gate 产物逐字节不变」不仅兑现，
还被更强的旁证前置保证（install 树 2261 文件仅 1 个不同、编译器二进制 byte-identical，RR8 §4b）。
**限定**：初稿在此写「零真回归」，P8-R 后不再成立——15.2.0 的一处 B 级删除确曾引入对官方的真实行为分歧（P1-1），
只是它**落在全部 gate 面之外**（`-f*-ra` 类选项在 EVT/scripts/tests 内 0 命中，故 274 / 47797 / 43969 与全部封存数字
不受影响），由外部独立审计发现、已按预注册条款回退并新增护栏（§6.4、§8.3b）。
正确的表述是：**gate 数字自始至终未破，且现已由 ra-flags 矩阵把该分歧面纳入常设护栏**；
「零真回归」只对 gate 面成立，不对全部行为面成立。
唯一真代码缺陷 P8-F2 是**本轮新增能力面**内的缺陷，其默认模式 gate 中性断言成立且修后全绿（§5.2）。

**丙 · 可读性 / 可维护性 / 最小化** —— 成立，且**最小化的正确表现包含「没有删代码」**：
8.2.0 B 级 0 项、代码语义 token 变动量 0，整轮源码 delta 仅两行注释（RR8 §1、§2）；
15.2.0 只折叠纯自消对、承载证据的中间态一律保留（RR15 §1、DEC:63）；
12.2.0 的六项 B 级里，四项是形态/结构改善（死子表达式、掩码迁位、表名合并、vendor strcmp 运行期化），
两项是移植与其缺陷修复——没有一项为了美观而动行为面（RR12 §1）。
可维护性的三处实质改善：证据指针根统一可解析（8.2.0）、message 硬编码 sha 去除（8.2.0 en-route）、
`ours_runner.py` 的硬编码计数改为从当前 golden 派生（P8-F1，DEC:71）。

### 10.2 设计回归：对照任务书硬约束 1–12

| # | 判定 | 依据 / 裁定指针 |
| --- | --- | --- |
| 1 缺陷保真优先 | **遵守（一处曾失守，已回退）** | §6 四类处置；8.2.0 `wch_rvc_extension` 升格保真面并驳回「补复位路径」（DEC:62）；12.2.0 经 P8-R 重列的 KEEP 族 9 行（RR12 §3）；15.2.0 保留 `non-standard111` 诊断字面量（LG15:10，SR-01 B1 追踪命中）。**失守点**：15.2.0 的 ra 析取项删除以「断言」代替「探测」通过了本条（硬约束 1 要求删前探官方，而探针面对该条件零判别力），审计实测证伪后按预注册条款回退（§6.4、§8.3b） |
| 2 最小化让位于零差异 | **遵守** | 8.2.0 B=0（RR8 §3）；15.2.0 不折叠承载证据的中间态、riscv_ip 门重写与表序迁移不动（RR15 §1）；xlen=32 不改码（DEC:63 Q4） |
| 3 分级决定回归深度 | **遵守（含协调器修订）** | 三版本 M/C/B 预注册与实测判据见 §2.1、§3；M 批不重建的判据（tree 不变 + stable patch-id 第一字段不变 + 字节分类表）由 DEC:65 判 4/4、DEC:66 判 6/6；C/B 合批重建为 TS:24 的协调器 2026-08-17 修订，未事后降级 |
| 4 单补丁单单元 | **偏离，经协调器逐单元下发与验收** | 12.2.0 的 U3 一个单元覆盖约 20 个台账行、15.2.0 以七个命名单元（U-F1…U-M1）一次链重建——单元粒度由协调器下发裁定（DEC:66 / DEC:68 「实施法定为 commit-tree 链重建」/ DEC:70），且单元内保留逐片 git 级验证（逐 index 累积树对照、逐片字节分类、复放 tree 相等）；与 TS:25 字面「单补丁单单元、禁止攒片再验证」存在偏离，记录在此供审计 |
| 5 单写者守卫 | **遵守，且守卫机制被改进** | 基线件 `tmp/phase8-evidence/guard-baseline.tsv`；DEV-P8-02 把守卫量从 HEAD 树改为工作树内容哈希并推广三执行者（DEC:65）；OBS-P8-12-02/-05 两次并发写者观察均在版本 token 内消解（DEC:66/70）；三版本 `toolchain-current` 前后一致（RR8 §4 步骤 6、RR12 §6、RR15 §7） |
| 6 三/四侧对照 | **遵守（形态各异；15.2.0 一处曾"侧齐而输入不齐"，已补）** | 12.2.0 B 级 = 官方-我方全模式全字扫描 162/0 + 四测试集对 **vanilla**（第四侧）零回归 + 默认模式中性断言（RR12 §2 P3/P5）；8.2.0 无 B 级，U3 探针为官方/我方两侧 14/14（RR8 §5）；15.2.0 的 ra 删除侧数齐备（官方/改前/改后）但**输入集不含能判别该条件的 flag**，P8-R 补 ra-flags 四侧 16 组矩阵后闭合（§6.4.3）——本条的教训是：三侧对照的判别力取决于输入集，不取决于侧数 |
| 7 验证器独立性 | **遵守，且是本阶段最大教训所在** | 最强正例：`E8/s3/partition-check.py` 不读任何一腿自产 summary，只读 golden 与逐产物原始行表（RR8 §6b）；P8-F1 的修法删除了 runner 内的硬编码计数（DEC:71）；反例与修正见 §8.1 的 DEV-15-01/02/03、DEV-12-06 与 §9。**P8-R 后新增两项外部锚定**：①终局审计（上下文从未持有 p8 执笔工作）自行复算 pristine 复放 6/6、patch-id 39/39、封存自验、Q-01/Q-02 行为面（RV §1.1 的 20 项）；②审计建议、DEC:79 批准的**我方侧 quick 独立锚定 3/3**——8.2.0 `242/242`（`E8/s3/quick.p8r.stdout` 末行、stderr 0 字节）、12.2.0 `274/274`（RR12 §9，与轮末 P2 含 aux 273/4 逐字相同、两次测量互相独立）、15.2.0 `274/274`（P8-R darwin 回归内）。**残余**：审计对 SR-02 换列时点的 P2-1 与 P2-7 的出处署名错，均属本条约束的形态问题（§9 补注、§8.1 12.2.0 P8-R 表） |
| 8 探针打最终 install 树 | **遵守** | 8.2.0 探针 834 打最终 install 树、`probes.p8.summary` 与 `runJ` 逐字节相同（DEC:72）；15.2.0 探针 321/0 明记「打最终 install 树」（RR15 §2） |
| 9 代码与其自述一致 | **遵守** | §10.1 甲第 2 段；另 DEV-P8-12-04（主题随语义改写更名）即该验收面的直接执行（DEC:70） |
| 10 范围 | **遵守（授权外扩均单列）** | harness 比较语义未改（`evt-compare.sh` = `7ee93e19…`，RR12 §2 P0）；`ref/` 未触；范围外的定点写权各有裁定并要求 diff 单列：export/replay/build 脚本常量（DEC:66、DEC:67）、linux 构建脚本与 `gate-prepare_linux.sh` 各两行（DEC:69）、`tools/full-census/ours_runner.py` 对数块（DEC:71）；仓库根未 commit（留协调器验收后做，TS:31） |
| 11 轮末不变量 + S4 终签 | **遵守（终签已勾定，陈述已补全）** | 三版本轮末全量口径全绿见 §3。初稿标的「待勾项」由 DEC:78 ① 勾定：终签按 TS:32「不变性证据替代重跑」成立——封存自验（8.2.0 10/10、15.2.0 20/20）、三 `patches` 目录封存时点后 mtime 零漂移、六镜像 tree 与各轮终态逐一相同。**审计补齐两处缺口**：①TS:32 的**第三条腿 install 树**原未列，审计代测成立（15.2.0/12.2.0 各 0 新文件，8.2.0 活体 install 对 `install-manifest.post-rebuild.txt` 2261/2261 OK，RV P2-10）；②12.2.0 的封存自验原既未列出也不成立（389/1），P8-R 重签后 run 件 390/390 + 交付面件 20/20（RV P1-5、§2.4）——两点均由 DEC:79 令补记进终签陈述。15.2.0 的终签面在 P8-R 后更新为 §3.3 的 P8-R 数字 |
| 12 环境钉死 | **遵守** | `SOURCE_DATE_EPOCH=1767225600` 三版本重建均记录（RR8 §4 头、RR12 §2 P1、RR15 §2）；16 项目级 workers × `make -j2` 与 `BUILD_JOBS=16`（RR8 §10 头、RR12 §2 P1）；`shasum -a 256` 用于全部封存件；比较零 normalize（`.map`/`.lst` 类 aux 豁免为既有裁定，DEC:17、DEC:48） |

### 10.3 交付面尚未闭合项（供协调器验收时处置）

1. **三版本台账均已终态回填**（初稿此条两个方向都写错，审计 P1-4 指出：当时 12.2.0 实为未回填、15.2.0 实已回填；
   初稿以 **mtime** 当作内容已回填的证据，而 12.2.0 那次编辑只改了一行）。P8-R 后的实态：
   - **8.2.0**：7 列、status 词表原地扩充，52 行全部结案（`STILL-PRESENT=0`；RR8 §9，另带 P2-3 的义务销账限定块）。
   - **12.2.0**：按 15.2.0 口径改为**九列**，前 7 列 S1 判定逐字未改（`scratch/ledger.pre-P8R.tsv` 留痕 + diff 验证），
     **49 行全部有 `final_status`，`STILL-PRESENT`/`QUESTION` 残留 0**（分布见 `E12/ledger.tsv`；RR12 §8）。
   - **15.2.0**：九列，**51 行全部有终态**、无空值（`E15/ledger.tsv`；审计计数 51/51，RV P1-4 表）。
   **判定词口径**：TS:59 的字面要求是 `EXPLAINED` / `KEEP-UNPROBED`，三版本实际使用的是
   `RESOLVED-U-*` / `KEEP` 族体系（`EXPLAINED` 一次都没出现，审计 P1-4 附带）；DEC:79 已明确**接受该体系语义等价**。
2. **CL 勾选**：`tmp/prompts/phase-8.checklist.md` 的 41 项在本报告落稿时**仍全部未勾**（`- [x]` 计数 0，审计 P2-9）——
   TS:3 把 checklist 定为在跑证据台账、TS:59 把「checklist 全勾带证据」列为交付物，证据实际落在轮报告与 unit-records 中。
   DEC:79 已把勾定列为协调器自办项（P2-9/P2-10），与「入库 commit」同批待办。
3. **§7 五项呈用户裁定项**未决，其中 ③（full-lane 工具版本化）涉及当前 43969 gate 的证据机器可复算性、
   ⑤（Q-01/Q-02 移植追认）涉及使命边界，建议优先。
4. **两处文档未随 P8-R 同步（本报告落稿时实测，登记而不代改）**：
   - `RR12 §4` 的跨版本表仍留「15.2.0 ⇒ 恒真冗余，可删」一行，与 RR15 §9 的撤回声明及 DEC:79/80 的回退裁定不一致；
     本报告 §6.4 以后者为准。
   - `RR12 §3` 的 KEEP 族清单自称给「台账文件行号」，实际比现文**少 3**（P8-R 给 12.2.0 台账表头加了 3 行注释）：
     其 `:8`/`:21`/`:23`/`:40` 对应现文 `:11`/`:24`/`:26`/`:43`。这与审计 P2-4 修掉的 8.2.0 行号偏移注记是**同一缺陷族**
     （表头增行后指针未重定位），本报告引用时一律用现文行号。

---

## 附：本报告的自检

- 全部数字与结论均带指针（文件路径 + 节/行）。**唯一的自测量**：§2.4 三件封存件的自身 sha256 为落稿时
  `shasum -a 256` 只读复算所得（不涉构建、EVT 对比或工具链二进制），三值与协调器交办值逐位相同。
- **发现的来源矛盾数 = 0**（另有 2 处**未同步的过期表述**，非矛盾，已按 §10.3-4 原地登记而不代改）。
  历史上的两处表观矛盾均已有裁定收口：S1 的 `ra` 跨执行者判定（DEC:63 仲裁 → P8-R 后统一为「三版本都是活代码」，§6.4）、
  初稿 §10.3-1 的台账回填断言（审计 P1-4 证伪 → 本版按实态重写）。
- **无法落指针的声称数 = 0**。初稿的唯一一条（「p7 已结束」）现有出处：DEC:78 ④ / DEC:79 记其为用户 2026-08-17 的
  会话指令，并如实承认盘面无记录；审计对该补记的保留意见（RV §5 末行）与由此产生的归属未决，已在 §7③ 原文照录。
- 结论反转处一律保留原判与反转依据（§6.4 的原判表、§8.2 的旧标题、§10.1 乙的初稿措辞、§10.3-1 的初稿错误），
  不做静默改写。
