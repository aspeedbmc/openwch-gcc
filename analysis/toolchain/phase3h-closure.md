# phase-3h 收口报告

对象：15.2.0 / darwin-arm64 + linux-amd64。binutils series 由 6 补丁改为 7 补丁，
GCC series 9 补丁不变。冻结基线 main `f9fc735`（进场 HEAD `31c5d8d`，为其衍生态）。
证据根 `tmp/phase3h-evidence/`。

## 1. 本阶段交付

| 单元 | 内容 | 终态位 |
| --- | --- | --- |
| 0004 改造 | vendor `strcmp` 特判 → 运行期标志 + 隐藏长选项 `--w_priv_spec`，门 `w_priv_spec && (arch_attr \|\| explicit_attr)` | 0004 |
| REWORK-0005 | 旧 0005 并入 0001（xw 直接注册 2.2），补丁位删除、后续顺延 | 0001 |
| wchsoftlib | 隐藏长选项 `--wchsoftlib`，OR `EF_RISCV_WCH_SOFTLIB 0x01000000` | 0006 |
| objdump `-M xw` | 选项注册 + 解码门 + XW 操作数打印 + opcode 表序前移 | 0007 |

四项都不改变 EVT 产物字节：双平台全量 EVT 与 phase-3g 基线**逐字段相同**（§6）。
它们关闭的是「我方工具链与官方工具链**行为面**」的最后四个缺口。

## 2. 进场冻结态核验（S1）

`tmp/phase3h-evidence/s1-s3-checks.tsv`。HEAD `31c5d8d` 确为 `f9fc735` 衍生态；
`patches/` 干净；无 harness 写者；GCC 镜像树 `0785aaf0…` = series 复放 = phase-3d sealed。

**必须记录的一处**：binutils 活动镜像树为 `918ab266`(V3.0)，与 `patches/15.2.0/binutils`
复放出的 `9848f254` 不一致。这**不是**冻结态异常——`handoff-token-transfer.tsv` 明确
记载「权威基线是 series 复放出的 staged tree，不是活动镜像树……活动镜像 binutils
index tree 仍为 V3.0 的 918ab266…，勿照抄」，且 `gate-prepare_linux_v31.sh` 内的
`binutils_tree=9848f254…` 独立佐证。差异实体 = phase-3g 的 norvc 修复（repo `ff21464`）：
第一道 XW 门由三因子 `INSN_CLASS_XW && !xw_enabled && !riscv_opts.rvc` 改为二因子
`INSN_CLASS_XW && !riscv_opts.rvc`。本阶段已把镜像同步到权威态（`c643c8e9` → `9848f254`）。

## 3. quick comparator 16-worker 迁移（S2）

迁移 diff `tmp/phase3h/evt-compare-16w.diff`（136 行）。改动**仅**并发结构：worker 把
per-slug 行与四个计数器写入 per-slug 文件，父进程按 manifest 顺序拼接求和；**比较、分类、
extra 检测与两条要害退出码路径（成功 0 / gate 失败 1）逐字未动**。slug→工程解析上提到
并发之前——它是 harness 配置错误，必须整跑中止，而后台子 shell 无法中止父进程。
bash 3.2 无 `wait -n`，满池时等待最旧成员；工程数少于 workers 时全部并发
（DECISIONS 2026-08-15 口径）。

**一处必须如实记录的语义变化（异常路径）**：worker 改为后台子 shell 后，
`wait "${running_pids[0]}" || true` 不再让工程内部的失败以该命令自身的状态终止整跑；
该情形现在统一由 `[ -f "$temporary_dir/$slug.counts" ] || die` 收敛为 exit 2。
即**成功与 gate 失败两条路径不变，异常路径的退出码由「工程失败的原状态」变成 2**。
守卫位置是正确的——`.counts` 是 worker 的最后一次写，写不出来就一定被 `die` 抓住，
失败不会被静默吞掉。早先「退出码逻辑逐字未动」的表述对要害路径为真、对异常路径为假，
此处更正。

**语义不变的证明不是断言而是测量**：同一官方工具链下，串行原版与 16-worker 迁移版
的输出**逐字节相同**（`diff` 为空），rc 均 0。两侧 `meta.txt` 各自记录了被执行脚本的
sha256（原版 `d465d384…`、迁移版 `cd179ec8…`），故 artifact 自身即可证明跑的确实是两个
不同脚本，而不只是目录标签。官方自证 `274/274 / fail=0 / aux 277/0`。耗时 14s → 3s。

## 4. 草稿 rebase 与逐片落树（S3）

三个 delta 对**修正后**的 series（含 norvc 修复）`git apply --check` 全 clean、无 fuzz。
norvc 逐 hunk 四项核对：①第一道 XW 门保持二因子 ②reset 后 XW/ZCD 门原样
③`bfd/elfxx-riscv.c` 的 `INSN_CLASS_ZCD` 保持 0006 回退后的形态
④0006 注释所载不变式「同助记符 XW 行在非 XW 行之前」在表序前移后仍成立（8/8）。
我方 hunk（477 / 4580–4685 / 5852 行区）与 norvc hunk（`riscv_ip`，2865 行区）**函数级不相交**。

四次构建，`staged_tree` 与事前声明的期望值**全部 match=YES**：

| 片 | 落树位 → 终态位 | staged tree | build | quick | aux_diff | 探针 |
| --- | --- | --- | --- | --- | --- | --- |
| A | 0004 → 0004 | `838310b9` | EXIT=2（DEV-01） | **274/274** fail=0 | 4 | p1+p2 145/145 |
| B | 0007 → 0006 | `6f31f936` | EXIT=0 | **274/274** fail=0 | 4 | p1+p2+p3 199/199 |
| C | 0008 → 0007 | `bda204ba` | EXIT=0 | **274/274** fail=0 | 4 | 全量 **321/321** |
| final | 七补丁重编号 | `bda204ba` | EXIT=0 | **274/274** fail=0 | 4 | 全量 **321/321** |

**终态 series 的 staged tree 与片 C 完全相同** ⇒ REWORK-0005 的删位重编号是
**tree-neutral** 的：它只重发补丁文件与编号，不动源码。`aux_diff=4` 四条全是 `.map`
（`v3b-pioc`/`v3f-gpio`/`v3f2-gpio`/`v5f-fpu`），与 V3.1 基线逐项相同，非本批次引入。

### 4.1 S3 断言

| 断言 | 结果 |
| --- | --- |
| SR-01 锚点串 `internal: bad RISC-V privileged spec (%s)` | WCH=1 / V3.1=**0** / **`ours-v3h-final-frozen`=1**（片 C 树上同为 1） |
| `as --help`（路径归一后）与 WCH | **逐字节相同** |
| `objdump --help` 的 RISC-V 选项块与 WCH | **逐字节相同**（含 `xw` 条目与两个 TAB 续行） |
| 探针回放（6 组 / 321 项） | **321 comparisons, 0 mismatches — PASS**，运行 artifact `tmp/phase3h-evidence/probe-replay/`（`verify-draft.stdout`、`verify-draft.rc=0`、六份 `*.expected.tsv`、`replay-provenance.txt` 内含 verifier 与六个 runner 的 sha256） |

### 4.2 patch-id 完整性——series 重构无副作用的直接证据

| 终态位 | 补丁 | stable patch-id | 与旧 series |
| --- | --- | --- | --- |
| 0001 | accept bare XW arch attributes | `b4ff5f6caf91c251…` | **改**（旧 `e16f33df`；旧 0005 并入） |
| 0002 | emit WCH XW compressed bytes | `103af56c9664b82c…` | **不变** |
| 0003 | assemble custom opcodes | `9deb1d9431daf76a…` | **不变** |
| 0004 | make attribute write-out opt-in | `284978628685fdc7…` | **改**（旧 `41caa103`） |
| 0005 | match WCH XW gate diagnostic bytes | `a6c730fcbd8b95ae…` | **不变**（原 0006 顺延，id 保持） |
| 0006 | mark objects built against WCH softlib | `7155b5919b2aeec4…` | **新增** |
| 0007 | disassemble WCH XW encodings on request | `cc7ccf194c908dd7…` | **新增** |

旧 0005（XW mapping symbols，`9e42fee96a1a`）删位，内容并入 0001。
三个本批次未触碰的补丁 **patch-id 原封不动**；0002/0003 的文件级 diff 只有
`From <hash>`、`[PATCH n/6]→[PATCH n/7]` 与 blob index 三类元数据行。
## 5. 四项改动的行为规格与证据

### 5.1 0004：属性写出改为 opt-in

官方 15.2.0 汇编器有一个 `--help` 与 `--target-help` 都不列出的长选项 `--w_priv_spec`：
接受、拒绝带参、开启后写出属性节。上游条件保留在其下，故门为
`w_priv_spec && (riscv_opts.arch_attr || explicit_attr)`。四象限逐一可观测：

| `--w_priv_spec` | `arch_attr \|\| explicit_attr` | `.riscv.attributes` |
| --- | --- | --- |
| 否 | 任意 | 不存在；或恰好是 `.attribute` 指令写下的内容，**逐字未规范化** |
| 是 | 假 | 不存在 |
| 是 | 真 | 按上游合成 |

`-mno-arch-attr` 在门开时仍能关掉合成——这只有在 `DEFAULT_RISCV_ATTR` 仍为 1 时才可能；
而这也正是 `-march-attr` 看着像 no-op 的原因：它设的位早已被设上。
**默认值取无条件 0 而非 target 条件化**的完整理由写在 0004 的 commit message 里
（可观测行为面一致、configure 需重生成的风险、不写预防性跨 target 代码），供上游可解释性审查。

因为决定权从 target 移到了标志，被排除在本 target 之外的上游用例可以重新执行：
30 处 `#notarget: riscv*-wch-elf`（其中 28 处是上游用例，2 处是我方 0001 自建的
`attribute-xw.d` / `attribute-xw-version.d`）改为在 `#as:` 行加 `--w_priv_spec`，并因此**回退**了
三处为绕开缺失属性节而做的削弱（`csr-insns-pseudo*` 手工补 `-Mpriv-spec`、`imply`/
`option-norvc` 的可选属性节符号、整份 `section2.e-riscv-wch` 分叉期望文件）。

### 5.2 REWORK-0005：并入 0001

旧 0005 的全部语义就是「xw 的版本是 2.2」的四个面（表项、`attribute-xw.d` 期望、
`march-help.l` 期望、三个 mapping 用例），不含独立于该事实的行为。留着它意味着 0001
声称 2.0 并带一个立刻被推翻的 `xw2p0` 期望——那是开发轨迹，不是能向上游 reviewer
解释的补丁序列。并入后 0001 直接注册 2.2，四个面全部有用例，期望值取自官方二进制。

### 5.3 wchsoftlib

`--wchsoftlib` 的**全部**效果是把 `0x01000000` OR 进 `e_flags`：基线与开启的对象
**仅 1 字节不同**（偏移 `0x27`）；给两次产出逐字节相同的对象；与 `-mrelax`/`-mno-relax`
正交。它拒绝带参；不是 `.option` 指令；readelf 不给该位命名（只印 `0x1000001, RVC,
soft-float ABI`）；`ld` 的普通 `e_flags` 合并会把它带进链接产物，混链亦然且无告警。
故实现就是 `elf_flags |= EF_RISCV_WCH_SOFTLIB`，无 bfd、无 readelf 改动。

**官方 gcc driver 不传该选项**：6 组 `-###` 探针各产生 1 次 `as` 调用，无一命中；
`gcc`/`cc1`/`cc1plus`/`collect2`/`lto1` 与全部 `*.specs` 中两串计数均为 0 ⇒ **无 gcc 侧连带**。

### 5.4 objdump `-M xw` 与 opcode 表序

`-M xw` 不是接受面问题而是解码行为面：官方在含 XW 编码的对象上，无该选项时印 `.insn`，
有该选项时印 `lbu`（`-Mno-aliases` 下印 `c.lbu`）。且**只有该选项决定**——ELF 属性里
已有 `xw2p2` 也不启用，`-Mmax` 也不启用（`-Mmax` 反而把这些半字解成它们撞车的标准
`c.fld`）。故 XW 类从架构测试中豁免、改由该选项门控。四处改动：选项注册、解码门、
架构测试豁免、以及此前只有汇编侧存在的四个 XW 地址修饰符的操作数打印。

**表序**是 ERR-04 的实体。XW 的 alias 行本就按助记符与 Zcb 行交错排列、位置正确；
但 XW 的 canonical 行排在 `c.fldsp` 与 Zcb canonical 之后。aliases 模式看不见（alias 行先命中），
`-Mno-aliases` 把 alias 行滤掉后就暴露：65,536 半字穷举实测在 `rv32imafdc_xw` 上 **8,192 词**、
`rv32imac_zcb` 上再 **512 词** 与官方不符。修法是把四个 XW sp 形式与 XW/Zcb 共享助记符的
四组（连同各自 Zcb 兄弟行整组）前移到 `c.fldsp` 之前，共 12 行；三条约束：同名行必须连续
（`riscv-opc.c` 第 433 行明载，gas `riscv_ip` 按 `strcmp` 向后遍历）、组内 XW 行仍在 Zcb 行之前
（保住 0006 的汇编器不变式）、随行前移的 Zcb 行与 Zcd 行编码区间不相交（`0x8000-0x8FFF`
vs `0x2000-0x3FFF`/`0xA000-0xBFFF`），故不引入新的 Zcb↔Zcd 优先级变化。

**曾走过一次弯路并已废弃**：先按「`-M xw` 时 XW 恒优先」实现成两趟扫描，结果把
`zcb`/`xw`（aliases）从 0 打成 320 失配——官方在 `0x8020/0x8040/0x8060/0x8440` 选的是
**Zcb** alias，在 `0x8000/0x8400` 才选 XW。单一线性表序能同时解释这两组，「XW 恒优先」不能。
## 6. gate 结果

### 6.1 S4 DCXW 穷举（正式跑）——**VERDICT: PASS**

fixtures 按 HA annex：冻结 runner `tmp/phase3c-gas/{halfword_objdump,xw_matrix}.py`，
参照 `tmp/phase3f-evidence/matrix/gas/`，对应 feature 行 `L3-FEAT-DCXW-PRIORITY` 与
`L3-FEAT-OBJDUMP-HALFWORD`。halfword runner 用 phase-3h 副本（唯一改动 = `MODES` 增加
`-M xw` 与 `-M xw,no-aliases`）；生产者 runner 逐字使用。三侧：WCH / OURS-V31 / OURS-3H。

| 判据 | 期望 | 实测 |
| --- | --- | --- |
| halfword cell / word / missing | 48 / 3,145,728 / 0 | **48 / 3,145,728 / 0** |
| 16 个 `WCH-OURS3H` 比较 | 全零 | **全零** |
| 8 个 3f 基线 cell（default/no-aliases） | 双向零 | 三方向全零 |
| XW 生产者 accepted | 每 side×label 8704 | **全 8704** |
| `encoding_mismatches` | 0 | **0** |
| `expected_stream_sha256` | 与 3f 冻结同 | `a6ac473136e61f5f…` **逐字相同** |

`xw`/`xw-no-aliases` cell 上 `V31-OURS3H`=8704 不是回归，而是**被闭合的缺口本身**：
V3.1 不识别 `-M xw`，退回 `.insn`。

### 6.2 S5 常设回归

**SR-01**：`verdict=PASS`、**TIER-A=0**（改造前为 1）、**TIER-B1=3**、**TIER-B2=4**
——判据逐项命中、B 类**无漂移**。B1 = `gcc/0002` 的 unknown-X 诊断一条 + `gcc/0005`
的 implicit-declaration 两条；B2 = 2 条 zstd capability + 2 条 libctf `arc_mmap_writeout`。

**SR-02**：288 行 decoder×producer 矩阵。**WCH↔OURS-3H 互解码 0 不一致**；24 条上下游
分歧行上，与 WCH 同值的解码器集合恒为 `{OURS, OURS-3H, WCH}` —— OURS-3H **从不与
upstream 同侧**。3g 的 runner 依赖预先产出的 LTO 制品，故先跑了同源 producer 步
（`tmp/phase3h/sr02-lto-run.py`，仅改输出根与新增一侧）。

**SR-03**：138 probe × 6 side。WCH vs OURS-3H 在 `rc`/`stdout`/`stderr`/`object` 四个
哈希上**全零失配**；OURS-V3.1 vs OURS-3H 亦全零 ⇒ opcode 表序前移**未扰动** norvc 诊断面。

### 6.3 S6 双平台

| 面 | darwin-arm64 | linux-amd64 |
| --- | --- | --- |
| 全量 EVT | **1298 工程 / 47797 gate 行**，diff·missing·extra = 0/0/0 | **1298 / 47797**，0/0/0 |
| aux | 47784 / 819 | 47784 / 819 |
| 与 phase-3g 基线 | **逐字段相同** | **逐字段相同** |
| 并发契约 | 16 workers × `make -j2`，normalization=NONE | 同 |
| 快速回归 | 274/274 fail=0（aux_diff=4） | 274/274 fail=0（aux_diff=4） |
| XW+LTO | 100 命令 / 192 产物 / 492 比较 / **0 失败**，SEALED | 同左 |

**gcc driver `--wchsoftlib` 探测：否。** 6 组 `-###` 各产生 1 次 `as` 调用，无一含
`--wchsoftlib` 或 `--w_priv_spec`；`gcc`/`cc1`/`cc1plus`/`collect2`/`lto1` 与全部 `*.specs`
两串计数均 0 ⇒ **无 gcc specs 连带**。证据：`tmp/phase3h-evidence/driver/gcc-driver-invocations.tsv`
（`-###` 调用表，权威）与 `gcc-driver-static-scan.tsv`（静态扫描）。早先同目录下另有一份把调用表
复制进静态扫描文件的 artifact，因在 zsh 下未发生词分裂而把六行记成 `as_invocations=0`（空跑），
与权威表自相矛盾，已删除。

### 6.4 testsuite 对 pristine 的零回归

对照基线：同一 base（`2bc7af1f`）的 pristine 2.45 构建。**两侧 configure 并不相同**
——pristine 未带 `--with-zstd`，我方带（其余选项一致）。这一点对下面两栏的读法是决定性的。

| 项 | pristine | phase-3h | 说明 |
| --- | --- | --- | --- |
| gas expected passes | 619 | **650** | +31，账目严格闭合，见下 |
| gas unexpected | 0 | **0** | **零回归** |
| gas xfail / unsupported | 23 / 9 | 23 / 9 | 相同 |
| binutils expected passes | 227 | 234 | +7，**环境差异，与补丁无关**，见下 |
| binutils unexpected | 2 | 2 | 逐条归因见下 |

**gas 的 +31 是机械可核的账目闭合。** 七个补丁的 `create mode … .d` 逐个数：
`5 + 8 + 3 + 5 + 2 + 4 + 4 = 31`，**恰等于 619 → 650 的差**，且 `xfail 23=23`、
`unsupported 9=9`。**这比「零回归」更强：它证明无一条上游 gas 用例丢失**——若有丢失，
新增 31 与净增 31 不可能同时成立。旁证：片 A 的树（新增 `.d` 共 23 条）实测 gas 恰为
`642 = 619 + 23`。

需要更正一处早先的归因：`#notarget` 恢复执行对 **pristine** 基线的贡献恰为 **0**
——那 30 行 `#notarget` 是我方旧 0004 自己加的，pristine 从来没有它们。它相对的是
**V3.1**，不是 pristine。两个基线的相对量不能混用。

**binutils 的 +7 与补丁无关，是 configure 与用例执行面的环境差异。** 其中
`objcopy` 的 zstd 压缩/解压两条在 pristine 日志中**完全不存在**（未执行），由
`--with-zstd` 造成；其余数条（`pr25662`、`consecutive same-name`、
`multiple --disassemble` 一类）同样在 pristine 侧缺席或 UNTESTED。本项目的补丁面
（`gas/`、`opcodes/`、`bfd/elfxx-riscv.c`、`include/elf/riscv.h`）不含这些用例覆盖的代码。

binutils 两条 unexpected 的归因：

- `replacing non-deterministic member` —— **两侧都失败**（pristine 期望 776、我方 624）
  ⇒ 非回归。该用例断言宿主编译产物 `bintest.o` 的归档成员大小，随宿主 clang/SDK 变化；
  本 series 从不触及 `ar`。
- `Check if efi app format is recognized` —— 仅 pristine 失败，我方通过 ⇒ 非回归。
- `binutils-all/riscv/unknown` —— **仅我方失败，但不是缺陷**：该用例断言 custom 空间编码
  `0x0052018b` 必须打印为 `.insn`；补丁 0003 注册了 WCH 的四条 custom32 opcode，故解码为
  `wexti`。**官方 WCH objdump 对同一对象输出逐字相同**（`wexti gp,tp,t0,0`），V3.1 亦相同
  ⇒ 该失败早于 phase-3h，且是「与官方一致」的必然结果——让它通过反而会破坏字节 gate。

## 7. series 重导与 pristine 复放（S7）

终态 7 补丁已落 `patches/15.2.0/binutils/`，`series` 与 `patch-id.tsv`（17 行 = 9 GCC + 7 binutils）
同步重导，README 表格与说明章节改写（0004 的「已知缺陷」节替换为「vendor 特判已移除」，
新增 phase-3h 段，补记 GAS 侧注册版本已由 0001 自身携带 2.2）。

**pristine 复放不是额外一步，而是构建方式本身**：`tmp/phase3h/build-v3h.sh`（由 3g
`build-v3.sh` 逐字改写，全部守卫保留）每次都从 pristine base（gcc `5115c7e44`、
binutils `2bc7af1f`）克隆、`git apply --cached --check` 全量校验、再 `--index` 落定，
记录 staged tree 与 patch-series 台账，构建前后比对 protected-inputs。终态构建
`v3h-final` 的 staged tree 为 `bda204ba`，与声明期望一致（match=YES），两平台的全量 EVT
即是该复放产物的验证。linux 侧同样从 pristine 源 + `patches/` 复放
（`gate-prepare_linux.sh`，staged tree 同为 `bda204ba`）。
## 8. 台账登记

### 8.1 REWORK-0005（立项 → 闭合）

| 字段 | 内容 |
| --- | --- |
| 立项 | phase-3d 承接方（会话 b28c0730）勘查 0004 改造面时发现，Main 于 DECISIONS 2026-08-16 采纳 |
| 现象 | binutils 0005「match XW mapping symbols」的全部语义只是把 0001 注册的 `xw 2,0,0` 改成 `2,2,0`，并同步两处期望、加三个 mapping 用例；不含独立于「xw 是 2.2」的行为。0001 的 commit message 声称「observed default version 2.0」并带一个断言 `xw2p0` 的用例，被 0005 立刻推翻 |
| 依据 | 补丁全文比对（0005 的非 testsuite 面只有 `bfd/elfxx-riscv.c` 一行表项）；实测 series 净效果在 mapping / `-march=help` / 属性三面与 WCH 逐字节一致 |
| 处置 | 0005 并入 0001，删除该补丁位，后续顺延（原 0006→0005，新增 0006/0007） |
| 验证面 | mapping 三用例 + `attribute-xw{,-version}.d`（改造后真正执行）+ `wch-attribute-w-priv-spec-explicit.d`（规范化面）+ `march-help.l`，期望值全部取自官方二进制 |
| 闭合证据 | 终态 series staged tree `bda204ba` 与并入前的片 C 完全相同（tree-neutral）；patch-id 表显示未触碰的三个补丁 id 原封；双平台全量 EVT 与 3g 基线逐字段相同 |
| 状态 | **CLOSED** |

### 8.2 ERR-01..04 权威证据（本批次为权威归属方）

phase-3g handoff annex 的勘误节（HA-12）把四条勘误的权威证据归给本批次台账。正文登记如下。

**ERR-01 —— `-march-attr` 读法**。phase-3g 由「`-march-attr` 是 no-op」推广为
「arch-attr 一对全被架空」。**更正成立但推广错误**：`-march-attr` no-op 成立
（`C0`=`C1`、`C3`=`C4` 产物哈希级相等，两个门态都成立）；但 `-mno-arch-attr` 在门开时
**不是** no-op（`C5` 无属性节、`C3` 有）。门是双因子，`arch_attr` 可被 `-mno-arch-attr` 关闭。
权威证据：`tmp/prep-0004-rework/probes/p2-march-attr.expected.tsv`（本批次 321 项回放的一部分）。
**影响**：若照原推广读法实现成单因子门，四象限中的两个会错。

**ERR-02 —— XWVER-01 的性质**。phase-3g 记为「我方注册 2,0、测试期望 `xw2p0`，且改造使
属性路径可达后**必须同批修**，否则该串进入产物即破坏字节一致」。**改判：现树无在线缺陷**
——0005 已把注册改为 2.2，V3.1 与 WCH 在 mapping / `-march=help` / 属性三面逐字节相同
（`p4-xw-version.expected.tsv`：裸 `xw`、`rv32imacxw`、显式 `xw2p0/2p2/9p9` 五种输入，
两侧产物 sha256 全同；`-march=help` 两侧均列 2.2）。真正存在的是 series 内部自相矛盾，
处置为 REWORK-0005。**故「同批硬依赖」一说撤回**。

**ERR-03 —— `-M xw` 的结论范围**。phase-3g 记为「选项面缺口」，结论**偏小**：原探针对象
不含 XW 编码。含 XW 编码的对象实测 `-M xw` **改变解码**（`.insn` → `lbu`/`c.lbu`），且解码
**仅由该选项决定**（XW 属性不启用、`-Mmax` 不启用）。这是解码行为面差异，实现需 4 处
而非 1 处。权威证据：`p5-objdump-M-xw.expected.tsv` 与 §6 的 DCXW 穷举。

**ERR-04 —— `-M xw` 的解码优先级机制**。phase-3g（及本批次自己的第一版草稿）曾读作
「`-M xw` 时 XW 恒优先」。**不成立**：官方是普通单趟线性表序——`0x8020/0x8040/0x8060/0x8440`
选 Zcb alias，`0x8000/0x8400` 才选 XW；单一表序可同时解释两组，两趟扫描/XW 优先不能
（实测会把前一组也判成 XW，`zcb`/`xw` cell 由 0 变 320 失配）。真正的实体是 opcode 表中
XW canonical 行的位置。权威证据：`tmp/phase3h-evidence/dcxw/s4-official/`（48 cell 穷举）
与 §5.4 的弯路记录。

## 9. 偏差登记

`tmp/phase3h-evidence/deviations.tsv`。五条，均为执行过程/文档问题而非产物问题：

| id | 摘要 | 状态 |
| --- | --- | --- |
| DEV-01 | 片 A 收尾 protected-inputs 守卫因执行者并发改 `series` 而 EXIT=2 | **已闭合**：v3h-a2 SEALED |
| DEV-02 | `scripts/build-toolchain-15.2.0-linux.sh` 的未提交改动系 3g BLOCKER 解除物，需推进到七补丁口径 | 已处理，独立提交 |
| DEV-03 | 同一脚本与 prepare 脚本各残留一处硬编码补丁总数 15（其一是硬 die） | 已修为 16 |
| DEV-04 | `/Users/mrs` 别名自 DEV-01 起停留在 v3h-a 树，导致首轮 testsuite 用错测试源、8 条新用例未执行 | 已重跑并复位别名 |
| DEV-05 | linux 全量首跑 formal_pass=false（执行者 gate 运行期间改了 linux 构建脚本 + 运行中生成 `.pyc`）；字节 gate 本身全绿 | 已闭合：attempt2 formal_pass=True |

DEV-04 值得单独一句：它是 DEV-01 的**二阶后果**——`die` 发生在显式 `restore_links` 之前，
此后每次构建都把「进入时的值」当作原值保存并还原，于是错误值一路传递。三份
`users-mrs-link-before.txt` 记录的正是这条传播链。**构建本身不受影响**（每次构建都先把
别名指向自己的树），受影响的只有以 `srcdir=/Users/mrs/...` 配置的 testsuite。
## 10. 需求回归

逐条对照 `tmp/prompts/phase-3h.md` 与 `tmp/prep-0004-rework/notes.md` §7。

| 任务书条目 | 落点 | 结论 |
| --- | --- | --- |
| 硬约束 1 可解释性/诊断保真/缺陷保真 | §5 四项均为上游惯用形态；`--w_priv_spec`/`--wchsoftlib` 用 `md_longopts` + 不进 `md_show_usage` 的既有隐藏机制；`xw` 帮助串逐字复用官方原文（CLAUDE.md 允许的 comment 量）；无裸汇编、无搬运查找表、无工程特判 | 满足 |
| 硬约束 1 单补丁单验证 | §4 四次构建，每片 274/274 | 满足 |
| 硬约束 1 commit message 理由段 | 0004 含「无条件默认 0、不做 target 条件化」完整三条理由；0007 含表序三条约束 | 满足 |
| 硬约束 1 `SOURCE_DATE_EPOCH` / byte-cap / 不改 `ref/` | 全程导出 `1767225600`；大输出一律截断；`ref/` 无本工作流的内容改动。如实陈述：`ref/wch-evt/` 下 9 个 tracked 文件处于 modified 态，与 `ref/wch-evt/patches/*.patch` 完全一致（同为 50 行改动），是 harness 按设计施加的**既定态**而非漂移；另有运行中生成的 `__pycache__`（见 DEV-05） | 满足 |
| 硬约束 2 进场冻结态核验 | §2，含镜像漂移的记录与同步 | 满足 |
| 硬约束 3 并发契约 | comparator 迁 16 workers 且证明输出逐字节不变；全量 EVT 两平台均 16×j2 | 满足 |
| 硬约束 4 rebase 逐 hunk 核对 | §4 四项核对 + 函数级不相交 | 满足 |
| 硬约束 5 中途不 commit | 全程未在仓库根执行 commit；仅工作树写入 | 满足 |
| 任务 1 冻结态核验 | §2 | 完成 |
| 任务 2 comparator 迁移 + 官方自证 | §3 | 完成 |
| 任务 3 rebase + 逐片落树 + SR-01 锚点/help/321 探针 | §4、§4.1 | 完成 |
| 任务 4 DCXW 穷举 | §6.1 | 完成，PASS |
| 任务 5 SR-01 A=0/B1=3/B2=4 + SR-02/03 | §6.2 | 完成，判据命中 |
| 任务 6 双平台全量 + XW+LTO + testsuite + driver 探测 | §6.3、§6.4 | 完成 |
| 任务 7 series 重导 + pristine 复放 | §7 | 完成 |
| 台账义务 REWORK-0005 + ERR-01..04 | §8 | 完成 |

## 11. 设计回归

对照 AGENTS.md 硬规则与 DECISIONS 2026-08-15/16。

| 规则 | 核对 |
| --- | --- |
| 可解释性（每处改动可溯源到一个有证据的行为） | 四项改动各自的行为规格都由官方二进制现场探测得出（§5），期望值取自官方输出而非推断；曾经的「XW 恒优先」假说被穷举证伪并回退（§5.4） |
| 缺陷保真 | `-march-attr` 的 no-op、`-mno-arch-attr` 的非 no-op、`-M xw` 不被属性/`-Mmax` 启用、`--wchsoftlib` 只置位不被读回——四处「反直觉」行为均照实实现，未做「合理化」 |
| 比较语义未变 | comparator 迁移的输出对同一工具链**逐字节相同**（§3）；DCXW/SR 系列全部使用冻结 runner 的逐字副本，改动仅限输出根与新增一侧 |
| 并发契约 | 16 workers × `make -j2`，两平台全量与 quick 均记录在 summary 内 |
| 单写者 token | 全程本工作流独占；`/Users/mrs` 与 `tmp/golden/toolchain-current` 两个别名在每次使用后复位并核验（DEV-04 是一次失守，已修复并复核） |
| 中途不 commit | 满足；本报告与补丁重导按逻辑单元交由验收后提交 |
| 五轮规则 | 未触发：唯一反复的是 objdump 表序，第 1 轮定位、第 2 轮（两趟扫描）被穷举证伪、第 3 轮（表序前移）通过，共 3 轮且每轮都有新证据 |

## 12. 未决问题

**无。** 五条偏差（DEV-01..05）全部闭合，处置与证据见
`tmp/phase3h-evidence/deviations.tsv`：

- DEV-01 由 v3h-a2 以冻结 `patches/` 重跑补齐（staged tree `838310b9` match=YES、
  protected-inputs 前后一致、`summary.txt` 完整、quick 274/274），**SEALED**；跑完
  终态 series 已按快照逐字节还原。
- DEV-05 由 linux 全量 attempt2 补齐（`formal_pass=True`、`immutable_pre_post_equal=True`、
  `evt_exact_restored=True`、inner rc=0），counts 与 attempt1 逐字段相同；attempt1 的
  证据保留为 `full-stage-a.attempt1-immutable-drift`。

本批次未发现需要 gcc 侧连带的项（driver 探测为否）。

## 13. 提交建议（逻辑单元）

按验收后入库，建议四个独立单元：

1. **binutils series 重导**：`patches/15.2.0/binutils/*`、`series`、`patch-id.tsv`、
   `README.md`。这是本阶段的主交付。
2. **linux 构建脚本推进**：`scripts/build-toolchain-15.2.0-linux.sh`（diff 见附录 A）。
   它同时承载 DECISIONS 2026-08-16 路由给本工作流的 R-53 遗留改动（3g linux BLOCKER
   的解除物）与本批次的七补丁口径推进，**与 series 重导分开提交**。
3. **harness 并发迁移**：`scripts/evt-compare.sh`（16 workers，语义不变已证）。
4. **收口报告**：`analysis/toolchain/phase3h-closure.md`。

## 附录 A：`scripts/build-toolchain-15.2.0-linux.sh` 改动

`git diff` 共 124 行，由**两部分**构成，提交时一并带入，故两部分都在此描述。

**第一部分：3g 遗留（DECISIONS 2026-08-16 路由给本工作流）。** 这是 3g linux 腿 BLOCKER
的解除物，本阶段未改其机制，只承接：

| 位置 | 内容 |
| --- | --- |
| 抬头注释 | `all nine patches` → `all fifteen patches`（本阶段再推进为 sixteen） |
| 新增常量 | `gcc_frozen_patch_tree=0785aaf0…` |
| 新增常量 | `binutils_frozen_patch_tree=918ab266…(V3.0)` → `9848f254…(V3.1)` |
| `verify_patched_worktree` 的 gcc 计数 | `3` → `9` |
| 新增 | `patch-id.tsv` 存在性与**账本形状**校验（表头、三列、component 取值、40 位十六进制 id、键唯一、计数） |
| 新增 | 整块**逐补丁** `git patch-id --stable` 校验，与账本逐条比对 |
| 改造 | `verify_patched_worktree` 增加第 5 参数（该组件的冻结树），并在其内做 `write-tree` 比对 |

（该遗留态可从 `tmp/phase3g-evidence/.../state/openwch-diff.bin` 复原，可独立核验。）

**第二部分：phase-3h 增量。** 把上述机制推进到七补丁口径。

共六处：

| 位置 | 旧 | 新 |
| --- | --- | --- |
| 抬头注释 | `all fifteen patches` | `all sixteen patches` |
| `binutils_frozen_patch_tree` | `9848f254…` | `bda204ba…` |
| 账本形状校验 | `NR != 16 \|\| gcc != 9 \|\| binutils != 6` | `NR != 17 \|\| gcc != 9 \|\| binutils != 7` |
| `verify_patched_worktree` 的 binutils 计数 | `6` | `7` |
| 内部总数硬校验 | `-eq 15` | `-eq 16` |
| `patch_series=PASS` 打印 | `total=15` 硬编码 | `total=%s`，取 gcc+binutils 之和 |

前五处中的第三、四、五处是**硬 die**；第五处正是 linux 腿在 16 条 patch-id 全部 PASS
之后仍被拦下的原因（DEV-03）。第六处只影响打印，但会写进 provenance，
故一并参数化——注意 linux 构建在该修复之前完成，`gate/s6-linux/build/build.stdout`
内那一行仍写 `total=15`（同行 `gcc=9 binutils=7` 正确，真正 gate 的 `-eq 16` 已通过），
该字段为已知不实字段，入库脚本为正确形态。

## 14. 独立审计后的修正轮

独立对抗性审计（`analysis/toolchain/phase3h-review.md`，F1–F17）判定**有条件放行、
代码面零返工**，四片可解释性全部合格；全部发现为文档/证据链准确性问题。本轮逐项修正
如下，**除 F10 外不动任何补丁代码**。

| 发现 | 处置 |
| --- | --- |
| F1 pristine 对照并非同一 configure | §6.4 重写：删「同一 configure」，binutils +7 明确标为 `--with-zstd` 与 pristine 侧未执行用例造成的**环境差异** |
| F2 gas +31 归因把 V3.1 相对量安到 pristine 上 | §6.4 改述为账目严格闭合 `5+8+3+5+2+4+4=31`，并指出 `#notarget` 恢复对 pristine 的贡献为 0；该账目**比原说法更强**——证明无一条上游 gas 用例丢失 |
| F3 `deviations.tsv` 状态字段过期 | 五条状态字段全部更新为闭合态并附证据指针；§9 正文「四条」改「五条」 |
| F4 checklist S7 证据行写「待落盘与复放」 | 改为实际完成态（落盘件与导出件逐个 `cmp` byte-identical + 四项复放证据） |
| F5 README「every patch id is re-issued」误述 | 改为「7 中 4 个换 id、3 个原封」，并点明这正是未触碰补丁确未被触碰的直接证据 |
| F6 附录 A 只覆盖 diff 的一半 | 补齐 3g 遗留部分（gcc 计数 3→9、`gcc_frozen_patch_tree`、逐补丁 patch-id 校验块、抬头注释、`verify_patched_worktree` 第 5 参数），现为「遗留 7 项 + 增量 6 项」两部分 |
| F7 driver 两份 artifact 互相矛盾 | 删除错误的那份（zsh 下未词分裂导致记成空跑），保留 `gcc-driver-invocations.tsv` 为权威，静态扫描独立为 `gcc-driver-static-scan.tsv`；§5.3/§6.3 加指针与说明 |
| F8 异常路径退出码语义确有变化 | §3 如实记录：成功/gate 失败两条要害路径不变，异常路径由「工程失败的原状态」收敛为 exit 2；原「逐字未动」表述更正 |
| F9 「27 处 `#notarget`」计数偏差 | 改为 **30 处**（28 上游 + 2 我方自建的 `attribute-xw{,-version}.d`） |
| F10 0004 message 写 "Four new cases" | **唯一 message 改动**：改为五个并点名 `wch-attribute-w-priv-spec-off.d` 的第二因子证明作用；四元组见下 |
| F11 SR-01 锚点测量对象标注不一致 | 统一标注为 `ours-v3h-final-frozen`（并注明片 C 树上同为 1） |
| F12 XW 生产者 cell 数记述错误 | 18 → **15**（3 side × 5 label） |
| F13 321 项回放无运行记录 | 对终态冻结树重跑并落 artifact：`tmp/phase3h-evidence/probe-replay/`，**321 comparisons, 0 mismatches — PASS**，`rc=0` |
| F14 apply-check 措辞会被误读 | 照 `notes.md` §3.3(7) 改述为「按 series 顺序累积检查」 |
| F15 串行侧缺少脚本自证 | 两侧 wrapper 改为在 `meta.txt` 记录被执行脚本的 sha256，并重跑两侧：输出仍逐字节相同，14s vs 3s |
| F16 「`ref/` 未改」可被 `git status` 证伪 | §10 改为如实陈述：9 个 tracked 文件的 modified 态与 `ref/wch-evt/patches/*.patch` 完全一致（同 50 行），是 harness 既定态而非漂移 |
| F17 `EF_RISCV_WCH_SOFTLIB` 占 psABI 未分配位 | 信息性记录，无需改动：与 RVC 0x1 / float-ABI 0x6 / RVE 0x8 / TSO 0x10 无冲突，是 WCH 定义位，字节一致要求如此 |

### 14.1 F10 的四元组（照 phase-4.1 勘误先例）

message-only amend，源码树不得变：

| 量 | 修正前 | 修正后 | 结论 |
| --- | --- | --- | --- |
| head commit | `59643f803cea75090bdaa914caa0ce5f4663c112` | `e0ab4cf846397160aae4fe231f37736c254aba7f` | **变** |
| source tree | `0722e8e194719da172e5cbd8d7053f8f60d31f36` | `0722e8e194719da172e5cbd8d7053f8f60d31f36` | **不变** |
| 邮件 sha256 | `a67e9484da7428155c1e62d78353f31c8928685857cee992408d66991c41835c` | `5d7fa34d5ed99d277ce17b77f52caa736fb9974ec3833bfc4ba1d3eb34044710` | **变** |
| stable patch-id | `284978628685fdc70acbd6f25c704e61fda8d2d5` | `284978628685fdc70acbd6f25c704e61fda8d2d5` | **不变** |

两项独立佐证：补丁文件从 `diff --git` 起的部分**逐字节相同**；重导后 series 复放仍得
`bda204bac05cb5e1e2c77c6213aac71c0e110527`，与修正前一致。故 `patch-id.tsv` 中该行不变，
其余六个补丁文件一字未动。
