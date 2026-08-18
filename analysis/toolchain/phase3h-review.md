# phase-3h 独立对抗性审计报告

> 转写说明：审计 agent 因环境约束无法直接落盘本文件，全文由主会话逐字转写；审计执行与结论出自独立 reviewer（上下文未持有作者工作）。审计对象：staged 的 binutils series 重导（7 补丁）、harness 迁移、closure 报告与全部 phase-3h 证据链。

**结论：有条件放行。** 无 P0/P1。四个补丁的代码形态、行为规格与设计冻结件三者一致，且核心事实审计者已用官方工具链现场对拍与 pristine 复放独立重推。全部发现集中在**文档与证据链准确性**，其中 F1/F2 是真实的前提缺陷（结论仍成立，但报告陈述的依据不成立）。

## 一、覆盖矩阵

| 审计项 | 手段 | 状态 |
| --- | --- | --- |
| 1 四片逐 hunk 可解释性 | 全文通读 + 与 notes.md §3.2 冻结设计逐字对照 + 旧 0004/0005 对比 | 完成 |
| 2 未动补丁完整性 | 独立重算 16 个 `git patch-id --stable` + 与 HEAD 账本对比 | 完成 |
| 3 行为抽验（官方 vs 我方现场） | 4 象限×6 组、softlib×5 组、objdump 24 编码点×7 模式、help 全文、锚点串 | 完成 |
| 4 DEV-01..05 闭合 | seal/provenance 目录 + testsuite 计数差 + linux attempt2 JSON | 完成 |
| 5 harness 迁移 | diff 通读 + 串并行输出实测比对 + linux 脚本 124 行通读 | 完成 |
| 6 pristine 复放/镜像 | 自行 clone 2bc7af1f 顺序复放 → write-tree | 完成 |
| 7 边界 | ref/、commit 时间线、别名状态 | 完成 |
| 重型 gate | 从 raw `artifact-results.tsv`（96,400 行×2）独立重算，未重跑 | 完成 |
| 321 项探针回放 | 无运行记录可落证（见 F13），已用自跑探针替代 | 部分 UNVERIFIED |

## 二、发现

### F1 `[3][high]` pristine 对照的 configure 不同，"同一 configure" 前提不成立
`analysis/toolchain/phase3h-closure.md:203`：「与同一 base（`2bc7af1f`）、**同一 configure** 的 pristine 2.45 构建对照」。实测：

- pristine：`../src/configure --target=riscv32-wch-elf --prefix=/tmp/p3h-pristine … --with-system-zlib`
- 我方：`… --with-system-zlib --with-zstd`

失败场景：binutils 侧 +7 的构成里，`objcopy (objcopy compress/decompress debug sections with zstd)` 两条在 pristine 日志中**完全不存在**（未执行），是 `--with-zstd` 造成的；另有 5 条（`pr25662`×2、`consecutive same-name`×2、`multiple --disassemble`）同样在 pristine 中缺席或 UNTESTED。即 8 条净增中 7 条与补丁无关，报告未作任何归因。修法：用 `--with-zstd` 重建 pristine 基线，或删去"同一 configure"并把 binutils 的 +7 明确标为环境差异。
**反证据（对结论有利）**：gas 侧账目严格闭合（见 F2），故 gas 零回归结论不受影响。

### F2 `[3][high]` gas +31 的归因把 V3.1 相对量安到了 pristine 相对量上
`phase3h-closure.md:207` / `tmp/phase3h-evidence/testsuite-vs-pristine.tsv`：「+31；本批次 12 条新用例全部 PASS，另加从 `#notarget` 恢复执行的上游 attribute 用例」。对 **pristine** 基线而言，`#notarget` 恢复贡献恰为 **0**——那些行是我方旧 0004 自己加的，pristine 从来没有。实测机械计数：七个补丁 `create mode … .d` 合计 **5+8+3+5+2+4+4 = 31**，恰等于 619→650 的差；`xfail 23=23`、`unsupported 9=9`。旁证：run1（v3h-a 树，新增 .d 共 23 条）gas 恰为 **642 = 619+23**。
另："12 条新用例"与任何口径都对不上——对 pristine 是 13 条，对 V3.1 是 10 条。
**副产品（正面）**：这条账目严格闭合，等于证明**无一条上游 gas 用例丢失**，比报告原本的说法更强。

### F3 `[2][high]` `deviations.tsv` 状态字段过期，与 closure 自相矛盾
`tmp/phase3h-evidence/deviations.tsv`：DEV-01 `status=待重跑`、DEV-02 `status=S7 处理`；而 closure §9/§12 与 checklist 均声称五条全闭合，且 §12 明确指认该 tsv 为权威处置记录。另 closure §9 正文写「四条」，其下表为五行。

### F4 `[2][high]` checklist S7 已打勾，证据行却写「待落盘与复放」
`tmp/prompts/phase-3h.checklist.md:45-46` 自相矛盾。**实际工作已完成**：`tmp/phase3h/export/final/0*.patch` 与 `patches/15.2.0/binutils/` 落盘件逐个 `cmp` byte-identical；审计另行复放验证（见正面确认 2）。

### F5 `[2][med]` README 新增段落 "every patch id is re-issued" 为误述
`patches/15.2.0/README.md`（staged）Phase 3h 节。实为 7 中 3 个 patch-id 原封不动——而这恰是"未触碰的补丁确实未被触碰"的直接证据（closure §4.2 与 `patch-id-delta.tsv` 说法正确）。README 这句会让后续读者失去该信号。

### F6 `[2][med]` closure 附录 A 只覆盖了 124 行 diff 的一半
`git diff scripts/build-toolchain-15.2.0-linux.sh` 共 124 行（与声称一致），但附录 A 的六项表只描述 phase-3h 增量；同一次提交还将带入未被描述的 3g 遗留：`verify_patched_worktree gcc … 3 → 9`、新增 `gcc_frozen_patch_tree`、整块逐补丁 `git patch-id --stable` 校验、抬头注释 `all nine → …`。附录 A 描述遗留的那一段只提了 binutils 冻结树常量与账本形状校验。（遗留态本身可在 `tmp/phase3g-evidence/.../state/openwch-diff.bin` 复原，不构成不可核验。）

### F7 `[2][med]` driver 探针两份 artifact 互相矛盾
`tmp/phase3h-evidence/driver/gcc-driver-wchsoftlib.tsv` 首块复制了 invocations 表但六行全为 `as_invocations=0`；`gcc-driver-invocations.tsv` 同六行为 `1` 并带完整 argv。若照前者，探针为空跑。结论不受影响（两串计数皆 0，且 47797 字节 gate 本身即覆盖该面），但其中一份 artifact 是错的。

### F8 `[2][med]` comparator 异常路径退出码语义确有变化
`scripts/evt-compare.sh`：worker 改为后台子 shell + `wait "${running_pids[0]}" || true`，原先 `set -e` 下工程内部失败会以该命令自身状态终止整跑，现统一由 `[ -f "$…/$slug.counts" ] || die` 转为 exit 2。成功(0)与 gate 失败(1)两条路径未变，故 closure §3「退出码逐字未动」对要害路径为真、对异常路径为假。
**正面**：`.counts` 是 worker 的最后一次写，守卫位置正确，失败不会被静默吞掉；`make -j2`、`set -euo pipefail` 保留；bash 3.2 空数组写法在本机实测安全。

### F9 `[1][high]` "27 处 `#notarget`" 计数偏差
`phase3h-closure.md:109` 与 `tmp/prep-0004-rework/notes.md` §1.1。旧 0004 实为 **30** 行 `+#notarget: riscv*-wch-elf`，其中 28 个是上游用例（`attribute-xw.d`/`attribute-xw-version.d` 是我方自建）。

### F10 `[1][high]` 0004 commit message 写 "Four new cases"，实际新增五个 `.d`
第五个 `wch-attribute-w-priv-spec-off.d`（选项开 + 门为假 ⇒ 无属性节）恰是唯一证明"第二因子在选项打开时仍然生效"的用例，反而未被 message 点名。

### F11 `[1][high]` SR-01 锚点断言的测量对象标注不一致
`tmp/phase3h-evidence/s3-assertions.tsv` 记为 `v3h-c=1`，closure §4.1 与 checklist 记为 `v3h-final=1`。（审计已在 `ours-v3h-final-frozen` 上重测 = 1，事实无误。）

### F12 `[1][med]` XW 生产者 cell 数记述错误
`s4-s5-results.tsv` 写「18 cell（6 side x 5 label 中的 3 side x 5）」；`dcxw-verdict.json` 实为 3 side × 5 label = **15**。

### F13 `[1][med]` 321 项探针回放无运行记录（UNVERIFIED）
`tmp/phase3h-evidence/` 下无任何 `verify-draft.py` 运行产物，仅 `s3-assertions.tsv`/`per-piece.tsv` 各一行手写摘要。复现把手存在（`tmp/prep-0004-rework/probes/p{1..6}*.expected.tsv` + `verify-draft.py`），但当前该数字无 artifact 支撑。缓解：审计已独立自跑等价探针（正面确认 3–7），覆盖 p1/p2/p3/p5 的核心断言。

### F14 `[1][med]` "7 补丁对 pristine apply-check 逐个 PASS" 措辞会被误读
按字面（每个补丁单独对裸 pristine 检查）只有 0001/0002 通过；正确含义是顺序累积检查——notes.md §3.3(7) 已明确指出这一点，closure/checklist 应照抄该措辞。

### F15 `[1][low]` 串行/并行等价性证明的一侧缺少脚本自证
`tmp/phase3h/quick/official-serial-orig/meta.txt` 记 `workers=16`（wrapper 无条件回显环境变量），故该 artifact 本身不能证明跑的是串行原版；provenance 仅靠目录标签与 13s vs 3s 耗时。建议 meta 内记录被执行脚本的 sha256。

### F16 `[1][low]` "`ref/` 未改"的表述可被 `git status` 直接证伪
closure §10。`ref/wch-evt/` 下 9 个 tracked 文件处于 modified 态，mtime 落在 phase-3h 窗口内。核验结论：文件清单与 `ref/wch-evt/patches/*.patch` 完全一致、改动行数同为 50 行，即 harness 按设计施加的既定态，**非漂移**——但报告应如此陈述，而非声称未改。

### F17 `[1][low]` `EF_RISCV_WCH_SOFTLIB 0x01000000` 占用 psABI 未分配位
与现有 RVC 0x1 / float-ABI 0x6 / RVE 0x8 / TSO 0x10 无冲突。仅作信息记录：这是 WCH 定义位，字节一致要求如此。

## 三、正面确认（均为审计独立重推，非继承）

1. **patch-id 账本**：重算全部 16 个 `git patch-id --stable`，与 `patches/15.2.0/patch-id.tsv` 逐条相同；binutils 0002/0003/0005 与 HEAD 账本值一字不差 ⇒ closure §4.2 成立。
2. **pristine 复放**：自行 clone binutils 至 `2bc7af1f`，按 series 顺序 apply 七补丁 → `git write-tree` = `bda204bac05cb5e1e2c77c6213aac71c0e110527`，与活动镜像 HEAD tree 相同；镜像 commit `a430a09e` 存在，binutils/gcc 两镜像工作树皆干净，gcc tree `0785aaf0`。
3. **四象限属性行为**：6 组组合官方与我方产物逐字节相同，且内容符合规格表（门关+显式 `.attribute` ⇒ `"rv32imac_xw"` 原样；门开 ⇒ 规范化 `…_xw2p2` + priv_spec 标签；门开+`-mno-arch-attr`+无显式 ⇒ 无节）；`-march-attr` 在门关时两侧同为 no-op。
4. **`--wchsoftlib`**：开/关仅偏移 `0x27` 一字节（0x00→0x01）；给两次产物完全相同；与 `-mrelax`/`-mno-relax` 正交；五种变体官方↔我方皆逐字节相同。两个隐藏选项带参时的拒绝诊断两侧逐字相同；`-w_priv_spec`、`--w_priv`、`--wchsoft` 缩写行为两侧一致。
5. **`objdump -M xw`**：构造含 24 个半字的对象（含 ERR-04 争议点 `0x8000/0x8020/0x8040/0x8060/0x8400/0x8440`、八个 XW 形式、撞车的 `c.fld/c.fsd/c.fldsp/c.fsdsp`），在 `-d`、`-Mxw`、`-Mno-aliases`、`-Mxw,no-aliases`、`-Mmax`、`-Mmax,no-aliases`、`-Mxw,max` 七种模式下与官方全部 IDENTICAL；默认与 `-Mmax` 均不解 XW；`0x8020` 处 Zcb alias 胜出的反直觉行为被忠实复现（缺陷保真）。
6. **帮助面**：`objdump --help` 与官方仅差三行程序自身路径 ⇒ 含 `xw` 条目的整份 `-M` 列表逐字节相同；`as --help` 路径归一后完全相同；`--help`/`--target-help` 均不列两个隐藏选项。
7. **SR-01 锚点串**：`internal: bad RISC-V privileged spec (%s)` 在官方与我方 `as` 中各出现 1 次。
8. **双平台 gate 独立重算**：不读 `summary.json`，直接对 `artifact-results.tsv`（两平台各 96,400 行）计数 ⇒ darwin/linux 均 `gate/MATCH=47797`、无 gate DIFF/MISSING/EXTRA、`aux 47784/819`；`gate-mismatches.tsv` 仅表头；两侧构建失败表皆空。
9. **comparator 等价性**：`official-serial-orig/evt-compare.log` 与 `official-selfcheck/evt-compare.log` 逐字节相同（各 65,167 字节），rc 均 0；磁盘上的迁移 diff 与当前工作树 diff 内容一致。
10. **设计回归**：notes.md §3.2 冻结的三段代码（门表达式、`md_longopts` 两条、反汇编器双门形状）在落盘补丁中逐字复现；§8 五条开放问题全部有裁决且可溯源——0004 message 内含三条理由段、0007 message 内含表序三条约束，均为任务书硬性要求，实测齐全。
11. **REWORK-0005 无丢失**：旧 0005 的四个面（表项 `2,2,0`、`attribute-xw.d` 的 `xw2p2`、`march-help.l` 的 2.2、三个 mapping `.d`）在合并后 0001 中全部存在。
12. **空期望 `.d` 非空断言**：`binutils/testsuite/lib/binutils-common.exp:578` 的 `regexp_diff` 在期望耗尽而实际仍有非空行时走 `end_2` 分支报 "extra lines" 并判 FAIL ⇒ `wch-attribute-{default-off,march-attr-off,w-priv-spec-off}.d` 确实在断言"无属性节"。
13. **边界**：`31c5d8d`（02:02 JST）之后无任何仓库根 commit，早于执行起点；staged 集合恰为 series 重导 + README + patch-id.tsv；`/Users/mrs/riscv-gnu-toolchain` 与 `tmp/golden/toolchain-current` 均已回到基线目标。
14. **DEV-04/DEV-05 定量闭合**：gas 642（run1，错误测试源）→ 650（重跑）= +8，与 DEV-04 所述被跳过的 8 条严格吻合；linux `full-outer-restore/summary.json` 的 `formal_pass`/`immutable_pre_post_equal`/`evt_exact_restored` 皆 True、`inner_returncode=0`。
15. **各 verdict 原始 JSON**：DCXW 48 cell / 3,145,728 word / missing 0 / `halfword_violations` 空 / 全部 `WCH-OURS-3H` cell 计数为 0 / 生产者 8704×15 / stream sha 与 3f 冻结同；SR-01 `tier_a=0, b1=3, b2=4, PASS`；XW+LTO 两平台 100/192/492/0、SEALED、`writable_entries_after_seal=0`。

## 四、四片可解释性判定

| 片 | 判定 | 依据与保留意见 |
| --- | --- | --- |
| **0001**（合并旧 0005） | **合格** | 非 testsuite 面仅一行上游表项；旧 0005 四个面无丢失；message 讲清 GAS 侧 `xw2p2` 与 GCC 侧显式 `xw2p0` 两个独立面并给出规格来源。无特判、无不透明块。 |
| **0004** | **合格** | `md_longopts` + `md_parse_option` + 条件改写，全部上游惯用形态；vendor `strcmp` 已彻底移除；隐藏机制就是"不进 `md_show_usage`"，无 hack。message 含要求的「无条件默认 0、不做 target 条件化」完整三条理由，逐字核对齐全。保留：F10 用例计数误述。 |
| **0006** | **合格** | 12 行代码 = 一个 `|=` + 一个 enum/longopt/case + 一个头文件 `#define`；三条声称行为（幂等、relax 正交、单字节）均经审计实测复现；无 bfd/readelf 改动符合"无人读回"的取证结论。 |
| **0007** | **合格** | message 含表序三条约束且逐条可核（③随迁 Zcb 行 `0x8000–0x8FFF`/op=00 与 Zcd `c.fld 0x2000–0x3FFF`、`c.fsd 0xA000–0xBFFF` 区间不相交已按 MATCH/MASK 复核成立）。移入 12 行 / 移出 12 行，无重复行；操作数打印沿用既有 `case 'X'` 厂商分支形态；"XW 恒优先"的弯路及其穷举证伪被如实记录。 |

## 五、验收建议

**有条件放行**。入库前修正（均为文档/账本，不涉及代码与补丁内容）：

1. **F1 + F2** — 改写 closure §6.4：删除"同一 configure"，把 binutils +7 标注为 `--with-zstd` 及 pristine 侧未执行用例造成的环境差异；把 gas +31 改述为"七补丁系列新增的 31 个 `.d` 全部通过，账目严格闭合、无上游用例丢失"（更强的结论）。
2. **F3 + F4** — 同步 `deviations.tsv` 的 DEV-01/DEV-02 状态字段与 §9 的"四条"，修正 checklist S7 的证据行。
3. **F5** — 删除 README 的 "every patch id is re-issued"，改为"7 中 4 个换 id、3 个原封"。
4. **F6** — 附录 A 补齐 3g 遗留部分（gcc 计数 3→9、`gcc_frozen_patch_tree`、逐补丁 patch-id 校验块）。
5. F7/F9/F11/F12/F14 数字与措辞更正；F13/F15 补记运行 artifact 与脚本哈希；F16 改为如实陈述。
