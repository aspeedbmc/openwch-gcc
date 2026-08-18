# phase-6 独立对抗性审计报告（终稿）
## GCC 8.2.0 / riscv-none-embed / darwin-arm64

> 审计者上下文未持有作者工作。所有结论均为现场复算或独立重建，凡采信作者文件之处已标注。
> 本稿为初稿与修订件的合并终稿，除排版合并外未改动任何结论内容。
> 审计环境禁写 `.md`，全文由 Main（会话 b28c0730）逐字转写至本文件（仅还原传输转义字符）。

---

## 一、覆盖矩阵

| # | 审计项 | 手段 | 覆盖 |
| --- | --- | --- | --- |
| 1 | 7 片补丁逐 hunk 可解释性 | 全文通读 + 源树复核 + multilib 生成器独立重跑 + 上游 GCC 15 对照 + 官方二进制现场对拍 | **完整** |
| 2 | 构建脚本 6 件宿主适配 | 529 行通读 + 行号指针逐条核 + bfd-plugins 59B 现场 sha 对拍 | **完整** |
| 3 | golden/census 完整性 | 从 raw artifact 表独立重算全部计数 + 分区算术 + run_id/时序 + exclusions 三类抽验（各 1 例现场复现）+ **官方工具链在独立 cwd 下重建 2 工程逐产物 SHA256 对拍** + quick/full 两 lane 交叉验证 | **完整** |
| 4 | pristine 复放链 | 独立 clone → tag → 按 series `git am` → write-tree 比对；patch-id 双向重算 | **完整** |
| 5 | 行为抽验 | 90+ 例三方对拍（march 26 字母扫描、XW 8 编码、中断 14 变体、param 5 取值、objdump 5 模式、字面量 9 项） | **完整** |
| 6 | 探针集 804 口径 | probes.tsv 全量重算 + 41 条 EXCLUDED 逐条掩码 diff + R4c 替身组重算 + 全轮次台账 | **完整** |
| 7 | 豁免与偏差 | DEV 表逐条溯源 + amend-quad 四元组 + .map/.lst 归因证据 + 287→296 传播 | **完整** |
| 8 | 边界 | tree hash 对数 + git log + 转换器 18 组独立附加性复验 + harness 11 hunk 逐条语义审 | **完整** |

**七面全覆盖，无未闭合审计子项。**

---

## 二、发现

### P1 —— 入库前须处置

#### [P1-1][severity 3][confidence high] D1 补丁实现与其自身 commit message 声明的规格相反，造成对官方的真实行为分歧

`patches/8.2.0/gcc/0003-riscv-accept-the-WCH-QingKe-xw-march-spelling.patch:68-74`：

```c
+  if (*p == 'x')
+    {
+      p++;
+
+      if (*p == 'w')      /* ← 嵌套 */
+	p++;
+    }
```

同一文件 `:27-28` 的规格陈述写的是「`'x'` and `'w'` are **two independent single-character steps**, not a strcmp against "xw"」——**文字写对了，代码写反了**。

现场实测（独立复现，两侧同 argv 同 cwd）：

| `-march=` | 官方 | 我方 |
| --- | --- | --- |
| `rv32imacw` | **rc=0（接受）** | **rc=1 `unsupported ISA substring 'w'`** |
| `rv32iw` | rc=0 | rc=1 `'w'` |
| `rv32imacww` | rc=1 残串 `'w'` | rc=1 残串 `'ww'` |
| `rv32imacwx` | rc=1 残串 `'x'` | rc=1 残串 `'wx'` |
| `rv32imacxw` / `rv32imacx` | rc=0 | rc=0（一致） |

26 字母全扫描定位到唯一分歧字母 `w`；按「独立步骤 vs 嵌套」模型预注册 5 项预测，5/5 命中——是已证明的机制，不是推测。

**证据链缺陷（更值得记一笔）**：`evidence/s3/d1/spec-probe/` 的 25 个探测串**全部含 `x`**，而两种实现在含 `x` 的输入上产出完全相同 ⇒ 证据集在唯一能判别的轴上是盲的。commit message 由 `rv32imacxq→'q'`、`rv32imacxwz→'z'` 推出「两个独立步骤」，这两例只能排除 `strcmp(p,"xw")`，**不能**区分嵌套与并列。结论恰好写对了，证据不支持它，代码实现了被证据排除不掉的另一支。

**修法**：内层 `if` 反缩进为并列语句。**该修改可证明对 gate 中性**——从 `stage-a/effective-project-inventory.tsv` 提取全部 1298 工程的 march 取值，只有 6 种（`rv32imacxw` 878 / `rv32imcxw` 211 / `rv32imac` 100 / `rv32ecxw` 83 / `rv32imc` 17 / `rv32imafcxw` 9），**每个 `w` 都紧跟 `x`，无一例落在分歧面上**；且该 hunk 不触碰 `*flags`、不注册 subset，对所有当前被接受的串产出逐字节相同。故 Main 可按「重建 + quick 242/242 + 探针集 + 新增一条 `rv32imacw` 对拍」定向复验，不必然重跑 42285（但树哈希与 patch-id 会变，四项不变式需重签）。

#### [P1-2][severity 3][confidence high] `tmp/golden/toolchain-current` 未复位，checklist 的对应打勾为假

```
readlink tmp/golden/toolchain-current
→ .../tmp/toolchain_8.2.0/work/darwin-x64/install/riscv-none-embed-gcc   （mtime Aug 17 02:05）
进场值 / S2 归档 before==after → .../tmp/phase3g-evidence/ours-v3.0-frozen
```

`tmp/prompts/phase-6.checklist.md:63` 声称「toolchain-current 每用必复位（**当前=进场值**）」——**当前值 ≠ 进场值**。S2 那次复位确有其事（15:23 归档为证），但其后至少还有一次运行重新指向 8.2.0 且再未复位。机制：`evt-compare.sh:95`/`evt-golden.sh:83` 用 `ln -sfn` 抢占，两者的 `cleanup()` 只删临时目录、**不还原 symlink**，复位是纯人工协议。

**具体危害（不是理论）**：quick golden manifest 头部把 `toolchain_invocation_root=/…/tmp/golden/toolchain-current` 与 `debug_prefix_map` 写死为复现契约。任何人按该 manifest 复现 golden，若不先把 symlink 指回 `ref/gcc/darwin-arm64/8.2.0`，就会**拿我方编译器和它自己比**并得到全绿假通过。同理，并发的 15.2.0 比对会被中途抢走该链接。该项与 P2-20 耦合：quick lane 的 neutral 根就是这条 symlink。

**修法**：立即复位；结构性修法是在两脚本 `cleanup()` 中记录并还原原值，或对该路径加 flock。

---

### P2 —— 证据链/前提缺陷（不阻塞 gate 结论，但须修正措辞或补证）

#### [P2-1][severity 3][confidence high] 探针集「每条 EXCLUDED 都有 in-gate 替身」不成立，4 条有缺口；其中 2 条的排除理由本身不成立

对全部 41 条做独立掩码 diff（只把两侧安装前缀替换为同一占位符，其余一字不动）：39 条掩码后 diff 全空，判据成立；2 条不成立。

- `03-attributes/driver-v` 与 `08-defaults/v-default`：掩码后仍有两处**非路径**差异——现场复核确认：
  ```
  官方: compiled by GNU C version 11.2.0, GMP version 6.1.2, MPFR version 3.1.6, MPC version 1.0.3, isl version isl-0.18-GMP
  我方: compiled by GNU C version Apple LLVM 21.0.0 (clang-2100.1.1.101), GMP version 6.2.1, MPFR version 4.1.0, MPC version 1.2.1, isl version isl-0.18-GMP
  ```
  `gcc -v` 被 AGENTS.md 硬规则**明列**为可观测字面量面。该面现无任何 gate 探针覆盖，S2 的 9 项表只钉 `Configured with` 行。（`Compiler executable checksum` 属硬规则已豁免的宿主二进制面，但也应在排除理由里点名而非默认吞掉。）
- `08-defaults/print-search-dirs` / `print-sysroot`：`report.md:83-84` 称「属 S2 字面量面，不重复守」——实测 `phase6-literal-surface.md` 的 9 项表里**没有这两项**（只有 `ld --verbose` 的 SEARCH_DIR，与驱动的 `-print-search-dirs` 是不同的面）。转嫁对象不存在。

#### [P2-2][severity 3][confidence high] 前提 P-12「WCH 原始 XBB 环境版本不可观测」被官方二进制自身证伪

`phase6-literal-surface.md:36` 与 closure §14 P-12 据此把 host 依赖钉成 gmp 6.2.1 / mpfr 4.1.0 / mpc 1.2.1。但官方 `gcc -v` 编译期横幅**明写** GMP 6.1.2 / MPFR 3.1.6 / MPC 1.0.3 / 宿主 GCC 11.2.0（isl 0.18 恰好钉对）。这正是「继承而未测量的前提」的教科书案例，且该可观测面恰好落在被排除的那 2 条探针里。

产物无扰动的结论未必错（probe `.o` 与 v3a 全工程逐字节命中是独立佐证），但前提陈述必须改为「**可观测，实测为 GMP 6.1.2 / MPFR 3.1.6 / MPC 1.0.3 / GCC 11.2.0；我方另选一组，其无扰动性由产物字节反证**」。是否改钉为官方那组由 Main 定（改则需重测）。

#### [P2-3][severity 3][confidence high] 唯一一条 `lib:missing` 排除，其判据是事实错误，且分类结论亦须重裁

`analysis/golden/8.2.0-darwin-arm64-full-exclusions.tsv` 的 `ruling-note` 写：「`-lprintfloat` 不在官方包库存清单——区分测试：`ref/gcc/darwin-arm64/8.2.0` 树内**无该库文件**」。现场：

```
find ref/gcc/darwin-arm64/8.2.0 -name '*printfloat*'   → 6 个命中
  riscv-none-embed/lib/{rv32ec/ilp32e, rv32ecxw/ilp32e, rv32imac/ilp32,
                        rv32imacxw/ilp32, rv32imafc/ilp32f, rv32imafcxw/ilp32f}/libprintfloat.a
```

**决定性反证实验**：

```
把 CoreMark 的 -march=rv32imcxw 改成 rv32imacxw → 官方工具链 LINK OK
```

完整机理：CoreMark 的 `.cproject` 把 atomic 置 false → 转换器给出 `rv32imcxw` → 该串**不在 23 项 multilib 表内** → `-print-multi-directory` 返回 `.` → 落到 `riscv-none-embed/lib/`（只有 libc/libg/libm/libgloss/libnosys/libsim，无 libprintfloat）。

**后果超出措辞层**：按 ruling 自身的定义（config = 工程/环境层可修），该行属**工程层一改即通**，更应判 `EXCLUDED-config`，分区随之变为 capability 126 / config 2。反向论据也成立且必须一并呈给 Main：MRS 自身若同样从 atomic=false 推出 `rv32imcxw`，则该工程「按发布配置官方永远链不成」，capability 亦可辩。**要点是：Main 当初的裁定建立在一个已被证伪的区分测试之上，须以正确机理重裁**，而不是由审计者代裁。

同一错误另见 `census-report.md §4.1` 表格「8.2.0 包内不含该库」。失败场景：任何按该「区分测试」复核分类的人，一条 `find` 即得相反结论，随即怀疑整张分类表。gate 面 42285 两种判法均不受影响（该工程都出局）。

#### [P2-4][severity 3][confidence med-high] GCC8 `-march` dialect 是 golden 与候选的共模输入，字节 gate 原理上无法证伪它，而其一手证据指针缺失

`evt-golden.sh`（官方侧）与 `evt-compare.sh`（我方侧）用**同一个转换器**生成 Makefile ⇒ dialect 拼错会同向平移两侧，42285/42285 全绿对 dialect 正确性**零证据力**。新增分支的规则（只追加裸 `xw`、直接丢弃 B 与 Zmmul）在 diff 注释里给的是能力性论证；`ref/wch-evt/README.md` 进一步断言「与 MounRiver 自身拼装规则一致」，但**档案里没有该断言的一手证据指针**。

Main 裁定 ② 提到归一规则的一手证据是 MRS2 `extension.js`，`buildability/mrs-march-builder.txt` 亦在；若同一份 `extension.js` 同时锁定了 dialect，本前提即可消解——**需要把那个指针补进 premise register**，否则退一步登记为「规则由 GCC 8 接受面反推，gate 对其不敏感」。

与此耦合的一条收窄通路：EXCLUDED 判据是「官方侧构建失败」（读码确认，见正面确认 8），而喂给那次官方构建的 Makefile 正是新 dialect 的产出 ⇒ 若 dialect 吐出官方 gcc-8 拒绝的 march，工程会被静默归入 EXCLUDED-capability 而非暴露为转换器缺陷。8.2.0 与 12.2.0 不同之处正在于 dialect 分支与 EXCLUDED 扩权**在同一相里落地**。该风险面因正面确认 23/24（两条 lane 独立产出同一批哈希、官方侧可在异 cwd 重建）而**显著收窄**，但共模不可证伪的原理性问题仍在，一手证据指针仍需补。

#### [P2-5][severity 3][confidence high] 12.2.0 / 15.2.0 源码树「未被触碰」在现存档案里不可复推

`entry-baseline.txt` 对这两棵树只记了「no git repo」，**未记任何内容哈希**。补丁面与 golden TSV 已逐项对数确认（见正面确认 6），源码树则无对数基准。

**修法**：Main 入库前对两树取一次汇总哈希写进 SESSION-STATE，作为今后基准。（Main 已办：DECISIONS 2026-08-17 取录四树 HEAD/tree，dirty=0。）

#### [P2-6][severity 3][confidence high]「归档腿 `official-abs` 与 S1/S3 归档逐字节全同」表述过宽

`lib/compare.py:166` 对 `EXCLUDED` **短路返回**，归档腿对那 41 条根本没评。全量复算 1871 个归档文件有 3 个不同（`driver-v.stderr`、`v-default.{stderr,as-line.txt}`，差异为 gcc 驱动的随机 `ccXXXXXX.s` 名，性质与排除理由一致）。`archive_leg_mismatch=0` 的准确含义是「**741 个被评估的行里 0 失配**」（覆盖 2281/2476 文件），不是「全同」。

结论本身站得住（另 38 条 EXCLUDED 的归档对照经复算全部命中），但 closure §5 的措辞须改。另两条机制层假绿通道：归档侧缺文件是静默 `continue`（`compare.py:189`）；探针枚举以 official 侧目录为准（`:157`），我方多吐的文件永不被发现。

#### [P2-7][severity 2][confidence high] D4b（highcode）的 `param=1` 分支在 42285 gate 上零覆盖，而 closure 声称其已由 gate 闭合

closure §15 第 1 条写「D4b 的编译器侧行为已由 42285/42285 与 params.exp +2 闭合」。实测：

- EVT 树中把 `mrs.highcode` 选项置 `value="true"` 的工程共 **68 个，全部落在 EXCLUDED**（CH587 mcpy 类），PASS 集里 **0 个**；
- `wvproj_to_make.py` 对 `highcode` **零处理**（`grep highcode` 无命中），即便有 PASS 工程开启该选项也不会传到编译器。

⇒ 42285 只覆盖 `.highcode` 的 `DECL_UNINLINABLE` 半边（V2AC/V3B/V4BC 家族源码确用 `.highcode`，这半边确有 gate 覆盖）；`param=1` 的改名半边**完全靠官方探针 + 新增 9 个 testsuite 用例**。该实现本身经现场对拍确认与官方一致（`=1` 两侧同样拆成 `.highcode.<fn>`、`.o` 逐字节同），所以是**措辞过宽**而非实现缺陷。相应地，「未决 #2 highcode 下游用途仍开放」比 closure 暗示的稍更 load-bearing。

#### [P2-8][severity 2][confidence high] R3–R6 全部裁定未进 `DECISIONS.md`

（Main 已办：DECISIONS 2026-08-17 追录批次，commit cb66c29。）原发现：closure 反复援引 R3/R4/R4b/R4c/R5/R6、`lib:missing`、S4-02/S4-03，其唯一记录在被审计方自撰文件里；`SESSION-STATE.md:36` 明写「DECISIONS 由 Main 维护」，故这是 Main 的未完成动作，不是执行者违规。

#### [P2-9][severity 2][confidence high] 导出封存清单已对 README 失效

`evidence/s4/patches-export/final-SHA256SUMS.txt` 的 `shasum -c`：series、patch-id.tsv、7 片 `.patch` 全 OK，**`README.md` FAILED**（封存 `b61b0d64…` vs 当前 `05f09f47…`）。

成因可识别且合法：7 片补丁 mtime 23:46，README mtime 01:05——即 Main R3 明令的「把 `ac_cv_lib_dl_dlopen=no` 与 `inject_bfd_plugins` 写入宿主适配节」那次更新（已确认当前 README 确含这两节），封存后未重签。**核心交付面（补丁字节）未漂移**，但清单整体不可再用作 gate。修法：重签并注明原因。

#### [P2-10][severity 2][confidence high] 复放记录未钉死构建脚本身份

`replay-build.log` 记了源码树 HEAD、epoch、jobs、`install_files`，但**没有构建脚本自身的 sha256**；脚本本身 untracked、无 git 历史可比。源码面因脚本内建的 clean/baseline-tree 断言不受影响，受影响的是 configure 参数、注入面清单、host deps 这些非源码输入。修法：在脚本收尾输出块加一行 `script_sha256`。

#### [P2-11][severity 2][confidence high] `defect-fidelity/report.md` §三 覆盖表表体从未更新

`report.md:66` 合计行仍写 `788 | 728 I / 35 X / 25 M`，`:52` 的 D 行、`:57` 的 F 行 verdict 仍标 `MISMATCH`；只有文末增量修订节用文字说明「应改成什么」。单读 §三 会得到「25 条 MISMATCH、未通过」的过时结论。同节 `:132/:138/:155` 的 9632/9630/9665 与「3 条天生不可复现」（实为 2 条）均为 runC/runD 时代旧数。

#### [P2-12][severity 2][confidence high] 最后 6 条探针是靠改判据转绿，头条口径未加限定

台账：runA–D `788/728/35/25` → runE（**行为修正已全部落地**）`788/747/35/6` → runF/G/H `804/763/41/0`。runE→runF 的唯一变化是 `lib/compare.py:103-105` 把这 6 条加入 `EXCLUDE` + 新增 `lib/17-nm-plugin-samepath.sh`。

**这不是造假**——判据变更经独立复算成立（6 条掩码后 diff 全空；替身组 36 产物 diff=0 且脚本零 normalize）。但 closure §5 与 `report.md` §一 的头条「804 = 763/41/0」未在同处点明「其中 6 条本轮由 MISMATCH 转入 EXCLUDED」，只在增量修订节说了，披露密度不对等。另：runE 是唯一「行为已定型、判据未改」的关键快照，却只留了 console、未存 `probes.tsv`。

#### [P2-13][severity 2][confidence high] 转换器附加性自证不覆盖真实 harness 路径（已由独立复验补上）

`additivity/{diff.txt,diff.delta.txt}` 确为 0 字节、54 文件核对无误；但 `gen-additivity.sh` 的三个 lane **全部不传 `--compiler-path`**，走 `select_toolchain()`；而新增的 `probe_compiler_major()` 与 `probed_major` 键**全在 `select_explicit_compiler()` 里**——恰是 harness 唯一实际使用的路径（两个脚本都以 `--compiler-path` 调用）。

独立复验已补：9 工程 × {12.2.0, 15.2.0} 经 `--compiler-path` 强制触发探测分支，old/new 的 `Makefile`+`config.json` **18 组逐字节相同** ⇒ 附加性成立、未被证伪。属自证覆盖面缺陷，非结论错误。

附带措辞观察：该改动**并非结构上的「附加」**（`select_toolchain()` 的选择门与 `config_flags()` 都是改写共享代码），附加性是被验证出来的行为属性而非天然属性。

#### [P2-14][severity 2][confidence high]「六件宿主适配」枚举不完整

closure §4 的六行表遗漏两项落在同一脚本里的宿主 workaround：`-UTARGET_OS_MAC`（`:310`，clang 在现代 Darwin 预定义 `TARGET_OS_MAC`，zlib 1.2.12 误判为经典 Mac OS 而屏蔽 `fdopen`）与 zlib 的**非 VPATH 就地拷贝**（`:304-309`）。另，表中第 1 项只列四个 `-Wno-`，实际 `host_cflags` 同时把 `CFLAGS/CXXFLAGS` 整体设为 `-O2 -mmacosx-version-min=10.13 …`（上游默认为 `-g -O2`）。均不可观测于 gate，但「六件」是完整性声称。

#### [P2-15][severity 2][confidence high] 不注入 `ldscripts` 是一项写在脚本里的设计决定，只以「gate 外观察」形式披露

`build-toolchain-8.2.0.sh:389` `[ "$base" = ldscripts ] && continue` 使 44 个 ldscripts 中 **40 个与官方不同**（现场复核：官方内嵌 `/Host/home/wch/Work/riscv-none-embed-gcc-8.2.0-3.1/linux-x32/…`，我方内嵌自身前缀）。这与「完全逐字复用 WCH 随包库」的库策略构成一处**有意偏离**，理由（官方那 40 个来自另一次更早构建、EVT 一律 `-T` 指定脚本故 gate 不受影响）成立且已在 closure §11.1 观察 1 中说明，但它登记为「观察」而非偏差或裁定项。（Main 已追认：DECISIONS 2026-08-17。）

#### [P2-16][severity 2][confidence high] quick lane 的 EXCLUDED 记录不能自证

manifest 头 `# excluded[v3c-led]=… last_error=make: *** Waiting for unfinished jobs....` ——记的是 `-j2` 的包装行而非真实诊断。真实诊断（`core_riscv.h:645: Error: unrecognized opcode 'mcpy'`）在 S1 `buildability/logs/v3c-led.probe-r1.err` 中确实存在且被文档广泛引用，故非覆盖漏洞；但 full-exclusions.tsv 已做到每条附真实诊断，quick lane 未跟上。修法：`last_error_line()` 对 `make: ***` 前缀回退到上一条非 make 行。

#### [P2-17][severity 2][confidence med] 并发迁移的「与串行一致」措辞覆盖不全

`show_failure_excerpt`（含 `head -c 65536` 日志摘录）、`NONDETERMINISTIC` 行、`missing required gate artifacts` 的 FAIL 行**都绕过 per-slug 文件、由 16 个 worker 并发直写 stderr**。manifest 与 status 流确实按表序拼接（已验），但多工程同时失败时 stderr 上的摘录会交织，人工归因失据。另：9 个 slug < 16 workers，**满池等待分支在实际运行中从未执行过**。

#### [P2-18][severity 2][confidence med] 已入库的 12.2.0/15.2.0 darwin golden，其生成环境与现存档案不一致且未登记

BSD-awk 三目修复不是美化而是**硬解析错误**（本机 `/usr/bin/awk` 对原式报 `syntax error`，在 `set -euo pipefail` 下会直接终止 `evt-golden.sh`）；该未加括号写法自最初的 harness commit 起就在。但已入库的 `analysis/golden/{12.2.0,15.2.0}-darwin-arm64.tsv` 却带有填好的 `# debug_flags[...]=-gdwarf-4` 值 ⇒ 那两份 golden 是在 `awk` 解析为非 BSD awk 的 PATH 下生成的。不影响 gate（比较不读该字段），但那两份 golden 的生成环境按现存档案不可复现。属既有问题，非 phase-6 引入。

#### [P2-19][severity 2][confidence high] full-lane 生成器不在版本控制内

收口 gate 是全量口径，但 `scripts/` 下只有 quick 的 `evt-golden.sh`（且硬钉 `project_count -eq 9`）；full lane 的 `ours_runner.py` / census 工具在 untracked 的 `tmp/` 里。既有问题（15.2.0 同样如此），但 gate 的生成手段不在版本控制内值得单列。

#### [P2-20][severity 2][confidence high] gate 口径实为「模工具链安装前缀」的逐字节一致，与「比较前不做任何 normalize」的表述冲突

两条 lane 在**编译期**都加了 `-fdebug-prefix-map=<真实工具链根>=<neutral 根>`（quick 用 `tmp/golden/toolchain-current`，full 用 `<project_root>/toolchain-current`）。

这**不是**事后 normalize，是双侧对称的编译期开关，且已在 manifest 头与 `census-report §2/§7d` 披露、经用户裁定——**程序上干净**。但它有一个必须记账的后果：**任何仅表现为工具链路径字符串的真实差异，对 gate 不可见。**

AGENTS.md 硬规则写的是「比较前不做任何 normalize——差异本身是信息」，closure 亦沿用该措辞。**终报应改为带限定的表述**：「在双侧对称的 `-fdebug-prefix-map` 工具链前缀归一下逐字节一致；该开关经用户裁定，比较阶段零 normalize」。

此项与 **P1-2 耦合**：quick lane 的 neutral 根就是 `tmp/golden/toolchain-current`，复现前必须先复位——正面确认 23 的活体重建之所以能换 cwd 成功，是因为选样两工程 `debug_flags=none`；带 `-g` 的工程（如 v3f/v3f2）不具此自由度。

#### [P2-21][severity 2][confidence high] 33 个工程仅在链接阶段失败，却按工程粒度整体出局，丢弃约 900 个可对拍 `.o`（≈gate 面 2%）

z-subset 31 + lib:missing 1 + link:region-overflow 1 = 33 个工程，其 `.o` 在两侧都能正常产出（实测：z-subset 样本 25 个 `.o`、CoreMark 33 个 `.o` 全部编译成功），失败点纯在 `collect2`/`ld`。现行 harness 按工程粒度剔除，这批 `.o` 全部不入 gate。

**不是正确性缺陷**（已比的全部命中），是覆盖完整性缺口。收紧手段明确：改为**产物级剔除**（编译成功的 `.o` 入 gate，只剔 `.elf`/`.bin`）。已登记为已知口径（DECISIONS 2026-08-17），是否收紧待用户裁定。

---

### P3 —— 文档漂移与未测边界

- **[severity 2][confidence high]** `wch_rvc_extension` 在 gas 侧**只置位不清零**（`tc-riscv.c:155` 唯一赋值，无复位路径）。`.attribute arch` 允许在首条指令前出现多次，故 `.attribute arch,"rv32imac_xw"` 后跟 `.attribute arch,"rv32imafdc"` 会让 `c.fld` 继续报 `illegal operands`。官方是否同样单调未探（其导出符号形态相同，很可能同样单调）。EVT 不可达；建议补一条探针。
- **[severity 2][confidence high]** D4a 的早返回（`riscv_save_reg_p` 开头）同时绕过上游的 `calls_eh_return` 分支。已确认 `ra` 判据必要非冗余；`__builtin_eh_return` + WCH 快中断组合未探。嵌入式无异常路径，实际不可达。
- **[severity 2][confidence high]** `.map` 698 条残差的归因**只对 3 个工程逐行做过**，其余约 695 个文件靠机制外推。机制干净（317×38=12046 / 324×38=12312 与尺寸差精确相等已复核）且 `.map` 不入 gate、已有 P2-1 类豁免。一次全 698 文件的「尺寸差 = 出现次数 × 38」机械核对可把结论升为全覆盖。
- **[severity 2][confidence med]** 全仓所有 commit 的 author/committer 均为同一身份，**git 元数据无法区分 Main 与执行者**。
- **[severity 1][confidence high]** closure §10(b) 字段定位写偏：`gate_artifacts` 字段在 `full-census/stage-a/summary.json:12`，不在 `stage-replay/summary.json`；实质结论正确且三方哈希相等（census 85257 = aux 42972 + gate 42285）。
- **[severity 1][confidence high]** closure §9 的「三处均记 287」已过时（三处现均为 296 并附勘误注）。
- **[severity 1][confidence high]** `patches/8.2.0/README.md:25-27` 称编号裁定「matches the 12.2.0 precedent」，与执行者自己的 open-question.txt/closure §2.2「两个先例都不具判别力」不一致，README 措辞比其证据强。
- **[severity 1][confidence high]** `phase6-diff-inventory.md` 的「预计落点」从未回改（D1 实际在 riscv-common.c；D4 还有 c-attribs.c）。
- **[severity 1][confidence high]** `phase6-literal-surface.md` 回改策略不一致（§4 已勘误、§2 未改）。
- **[severity 1][confidence high]** `host/0002` 未同步上游注释措辞（代码已上游形态、注释仍旧）。
- **[severity 1][confidence high]** `scripts/evt-golden.sh:4` 头注释未加 8.2.0（usage 已加）。属 en-route fix。
- **[severity 1][confidence high]** closure §3 复放树归档路径少一层（实际 `tmp/toolchain_8.2.0/scratch-s4-applycheck/…`）。
- **[severity 1][confidence high]** closure §5 引用 `runs/runG-*.console` glob 不匹配（实名 `runG.console`；终态 runH，三份 console 逐字节相同）。
- **[severity 1][confidence high]** 全量认证 run 实体在 `evidence/s3/full-ours/stage-replay/`、叙述在 `evidence/s4/replay/`，按 s4 枚举会漏。
- **[severity 1][confidence high]** `git patch-id --stable` 对 `gcc/0003` 的第二字段被 message 里行首 64 位 sha256 污染（patch-id 本体不受影响；`awk '{print $2}'` 类脚本会在此片误报）。
- **[severity 1][confidence high]** 「143 行」是 `--stat` churn、「296 行」是 raw diff 行数，同报告两种口径未标注；建议统一 `123+/20−` 与 `113+/51−`。

### 已消解的疑虑

- census 转换器不传 `--gcc-major`：`wvproj_to_make.py:1287-1290` 给了 `--compiler-path` 即走 `select_explicit_compiler` 并忽略 `--gcc-major`；与 quick/full 交叉哈希相等两路确认，非问题。
- z-subset 摘录中的 `rv32e1p9_…_xw2p2` 串：来自工程链接的预编译厂商目标文件属性节（15.2.0 代 GAS mapping 形态），由 ld 属性合并报出，非转换器 `-march` 产出。见正面确认 27。

---

## 三、正面确认（独立复算命中，非采信；28 项）

1. **复放链闭合**：从上游 GitHub 实时核对的 pristine tag `v8.2.0-3.1` 出发，独立 clone 按 `series` 应用 7 片，零 reject/fuzz/warning，得 gcc tree `a6782d2562…`、binutils tree `8d0d7da3c3…` 与声称逐字相等；6 棵归档树 HEAD/tree/clean 全对。
2. **patch-id 7/7 双向全等**；series↔文件↔tsv 1:1；`From:` 统一；trailer 扫描（10 关键词）0 命中；`[PATCH n/5]`/`[n/2]` 编号自洽。
3. **42285 从 raw 表独立重算命中**：85257 数据行 = gate 42285（全 MATCH）+ aux 42972（42273 M/699 D）；gate 分项 `.o` 39945/`.elf` 1170/`.bin` 1170；project-results 逐行求和吻合；`gate-mismatches.tsv` 仅表头。
4. **分区算术全对**：1170+127+1+0=1298；exclusions 128 行=127+1；quick 242=226+8+8、8 工程。
5. **认证跑在复放构建上**：构建 01:22:56 < 认证 01:23:38 < 封存 01:31:51；`pre_hash==post_hash`；`install_files=2261` 重数吻合；复放 cc1 与 preserved cc1 哈希相同。
6. **边界未破**：`patches/15.2.0` tree `c3f61178…`、`patches/12.2.0` tree `16b35748…` 与进场记录相同；6 个他版 golden TSV shasum 全中；phase-6 产物全 untracked；进场即脏的 9 个 EVT 文件经双重证据判定内容未变。
7. **harness 三项全对**：296 行/113+51/11 hunk 归档件与活树逐字节同；四类改动恰覆盖 11 hunk；evt-compare 仅 2 处 case 路由。
8. **EXCLUDED 语义未放宽 gate**：evt-golden 两 run 均用官方编译器，官方失败即剔除；我方侧无 EXCLUDED 通路（build_ok!=yes ⇒ gate FAIL + exit 1）。
9. **gcc/0001 确为生成器输出**：树内 multilib-generator 以补丁注释的 22-token 命令重跑，除 argv[0] 注释行外逐字节同；22-token 在官方 `distro-info/scripts/common-versions-source.sh:142/144` 原文命中。
10. **host/0002 是上游回移**：与 GCC 15 `system.h:197-239` 同序；嵌套核对正确。
11. **行为面 90+ 例三方对拍全同**（除 P1-1 的 `w`）：`.comment` 51B 双侧 sha 同、multilib 23 行、`Configured with:` 1519B 逐字节、`gcc version` 行句末孤立空格逐字、`ld --verbose` 整份同、XW 8 编码与 ISA 文档槽位吻合（`c.lbu`=0x2188）、objdump `-M` 面与 help 畸形缩进原样。
12. **中断属性缺陷保真做对了**：14 个近似变体两侧 rc+诊断+`.s` 全逐字节同——官方对任何偏差静默降级普通 `ret`，我方未擅自"修正"。
13. **207=206+1 用 vanilla 独立验证成立**；`--help=params` 29645B 逐字节；`param=1` 确有可观测行为。
14. **D3 全空间扫描方法学干净**：三只 objdump 同 symlink 消 argv[0] 噪声；49152×5 三侧对比，我方 vs 官方 5/5 SAME、vanilla 三 xw 模式各 8749 DIFF（仪器有区分力）。
15. **`.lst` 闪烁是测量非断言**：16 路×200 轮×2 二进制原始件在位；双向交叉复现件正文 sha 同（`f01030fd…`）。
16. **DEV-P6-06 补救可验证**：amend-quad 中 old/new 的 tree 与 stable patch-id 逐一相同，message-only 成立；旧记录块显式作废——诚实。
17. **R4c 替身组经得起复算**：36 产物两腿 diff=0；替身脚本零 normalize；路径可比性靠同 scratch 绝对路径+统一相对 argv[0] 物理达成；DOWNGRADED.txt 在位。
18. **34 项 stable 筛除无掩盖通道**：过滤正则为 4 个显式路径片段精确匹配；两份 SHA256SUMS 全过；终态 runH，runF/G/H 三份逐字节相同，无 cherry-pick。
19. **gas 套件独立重算命中**：183P/0F/3XF/7U；`Running *.exp`=130；18 条 `xw-*` 全 PASS。
20. **两个功能面确为 gate load-bearing**：EVT 树 1651 源文件用 `WCH-Interrupt-fast`、49 个用 `.highcode`，V2AC/V3B/V4BC 家族在 PASS 集。
21. **zmmul 交叉核对无不自洽**（见已消解与 27）。
22. **转换器去静默升级实测复现**：old 8 条升级 warning、8/9 被换 12.2.0；new warning 0、9/9 选中 8.2.0；两处范围外变化确认无现存影响（EVT 元数据无 GCC9；16 个非空向量密码工程无一 GCC8）。
23. **[决定性] golden 在独立 cwd 下被官方重新产出**：v2ac-gpio 24/24、v3a-gpio 28/28 gate 产物 SHA256 逐条命中，差异仅 aux `.lst` 路径头行——比作者原口径更强（换 cwd 仍复现）。限定：两工程 `debug_flags=none`；带 `-g` 工程仍受路径约束。
24. **quick 与 full 两张 golden 互证**：两条独立 harness、不同 cwd、不同转换器调用，3 个共有工程 86 个 gate 哈希全等。作者未做此交叉验证。
25. **复放认证四路独立闭合**：两轮 install manifest 实差 59 行（全为 binutils 系可执行体）；active install 全树 2261 文件 0 mismatch/missing/extra（preserved 与 install inode 不同，真实两份拷贝）；复放树逐 commit patch-id 7/7 合 series；两轮 `input_hashes` 七项全等，换的只有 install 树；`aux-mismatches.tsv` 两轮 sha 相同（`dd23b669…`，699=698 `.map`+1 `.lst`）。
26. **集合级相等三组**：census FAIL(128)==exclusions、census PASS(1170)==full manifest、replay 集(1170)==PASS，setdiff 均 0；golden/exclusions/census marker 哈希三方一致。
27. **z-subset 归因升为实证**：`zmmul` 来自 EVT 随工程库 `Tag_RISCV_arch`（三例逐字对应）；`rv32ecxw` 工程 `.o` 与随包 crt0/libc/libgcc 均无属性节；失败确在链接段（25 `.o` 全部编译成功后 collect2 报错）。机理=WCH 用新工具链编的随工程库、官方 ld 2.32 读不懂——官方包自身内部矛盾；我方 ld 若接受 `z` 子集反而「我方出 ELF、官方出不了」⇒ capability 成立，非我方可修面。
28. **mcpy 类边界核实**：CH587 根 95 工程 95/95 FAIL，与计数精确重合；样本实建错误与表内注记逐字一致。

---

## 四、七片可解释性判定

| 片 | 面 | 判定 | 依据 / 保留 |
| --- | --- | --- | --- |
| `gcc/0001` multilib | 基建 | **合格** | 生成器独立重跑逐字节复现；22-token 在官方 distro-info 原文命中；py3/py2 等价性如实披露；基建归属三处一致 |
| `host/0002` system.h | 宿主 | **合格** | 上游 GCC 15 同序回移；嵌套核对正确；零行为改动。瑕疵：注释未同步上游措辞 |
| `gcc/0003` D1 march | 行为 | **存疑（须修）** | 形态合格（12 行、不触 `*flags`、无特判）；但实现与自身 message 相反，`rv32imacw` 类真实分歧，证据集判别轴全盲（P1-1）；修法一行反缩进，gate 可证中性 |
| `gcc/0004` D4a 中断 | 行为 | **合格** | 挂上游 interrupt 机制、减法式保存集；`ra` 判据必要性经核；8 新测试；14 变体缺陷保真全同。保留：`calls_eh_return` 边界未探（实际不可达） |
| `gcc/0005` D4b highcode | 行为 | **合格（覆盖须重述）** | 落点证据链扎实；先置改写有实测；help 串逐字。保留：`param=1` 零 gate 覆盖，closure 措辞收窄（P2-7） |
| `binutils/0001` D2 XW | 行为 | **合格** | 互补 match 对由官方导出符号实证；操作数串取官方 __cstring；xlen=0 有 rv64 实测；双诊断分野实测；13 测试；位账完整。保留：`wch_rvc_extension` 单调置位 |
| `binutils/0002` D3 objdump | 行为 | **合格** | 49152×5 三方零分歧；打印器有据；「官方内联 strcmp 无 xw 字面量」如实划界；help 逐字复刻 |

---

## 五、验收建议

**有条件放行。** 无 P0。核心 gate 结论达到本次审计能给到的最强证据等级；扣分集中在一处真实行为分歧、一处协议未履行、若干把证据支撑范围写宽的措辞与前提——是表述与覆盖缺口，不是数据造假。

**入库前必办（2 项）**：1) 修 D1 嵌套 + 补 `rv32imacw` 类对拍探针 + 重签四项不变式（定向复验或全量复验由 Main 定）；2) 复位 `tmp/golden/toolchain-current` + 撤回 checklist L63 表述 + 两脚本 cleanup() 加还原逻辑。

**入库同批办（Main 侧 5 项）**：3) R3–R6 等裁定批次入 DECISIONS（已办 cb66c29）；4) 12/15 源码树基线哈希（已办，四树取录）；5) final-SHA256SUMS 重签 + script_sha256；6) ldscripts 不注入追认（已办）；7) lib:missing 以正确机理重裁（已办：改判 config，126/2）。

**报告修订（8–17 项）**：P-12 前提改写；lib:missing 判据重写（含 census-report §4.1）；归档腿口径改 741/2281；4 条无替身与 param=1 零覆盖如实登记；dialect 补 extension.js 一手指针；「六件」补 zlib 两项；gate 口径加 -fdebug-prefix-map 限定；P2-21 登记；defect-fidelity §三 表体更新；closure §10(b)/§9/§3/§5、README 先例措辞、diff-inventory 落点等逐项订正。

**审计未覆盖项（如实登记）**：全量 42285 与 census 未重跑（按约束）；mcpy 与 z-subset 各抽验 1 例；补丁运行期正确性仅在被测面验证；未验证 xPack 仓库 tip 与 FSF pristine 的关系（本项目 upstream 定义即 xPack fork，自洽）。
