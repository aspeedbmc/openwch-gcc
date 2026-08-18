# phase-4（GCC 12.2.0 / riscv-wch-elf）独立对抗性审计报告

审计者上下文从未持有执行 agent 的工作。所有结论均为本次现场落证，不采信 checklist 声称。
审计时间：2026-08-13。对象：`patches/12.2.0/`（gcc 9 + binutils 7）、
`analysis/golden/12.2.0-darwin-arm64.tsv`、`analysis/toolchain/phase4-{baseline,literal-surface,diff-inventory}.md`、
`tmp/phase4-evidence/` 证据树、`tmp/toolchain_12.2.0{,-pristine}` 构建树。

审计过程未修改任何既有文件。临时产物在
`/private/tmp/claude-501/-Users-apple-Projects-openwch/b28c0730-f239-4670-bbaf-cd987694f5f7/scratchpad/review-p4/`。
两次 EVT 全量重建前均确认 `pgrep -f evt-compare` 无命中；`tmp/golden/toolchain-current`
在审计开始时指向 active，结束后已回到同一目标。

---

## 1. 覆盖矩阵

| # | 审计项 | 结论 | 证据指针（本次实跑） |
|---|---|---|---|
| 1 | Golden 12.2.0 manifest 完整性 | **通过（高）** | 用官方 `ref/gcc/darwin-arm64/12.2.0` 跑 `scripts/evt-compare.sh 12.2.0`（与生成 manifest 的 `evt-golden.sh` 是两个脚本，构成交叉验证）：`rc=0`、`gate_pass=274 gate_total=274 gate_fail=0 aux_match=277 aux_diff=0`。9/9 工程全覆盖，非抽样 2 个 |
| 2 | manifest 剔除名单声称 | **通过（高）** | manifest 头 `double_run=PASS deterministic=9 excluded=0 failures=0`；`scripts/evt-projects.tsv` 9 行 == `ref/wch-evt/README.md`「编译项目」表 9 行 == manifest 内 9 个 slug。**剔除名单为空**，与 plans 的「如有」条款一致 |
| 3 | 16 片补丁可解释性 | **16/16 合格（高）** | 全文通读 16 个 patch；0 处裸字节块、0 处不透明搬运表、0 处 EVT 工程/文件特判。判定表见 §4。4 处形态类观察记为 P3 |
| 4 | 四个新特性面行为对拍 | **通过，逐字节相同（高）** | `.highcode`、`wchsoftlib`、M+Zmmul、vendor-X 共 40+ 组现场对拍，见 §3.1–§3.4 |
| 5 | 12.2.0 缺陷保真面（不假设同 15.2.0） | **通过（高）** | `non-standard111` 在 12.2.0 官方 cc1/cc1plus **不存在**（0 命中），未盲移植 15.2.0 补丁 = 正确；中断属性 typo 行为逐字节相同。见 §3.5 |
| 6 | 字面量面抽查 | **通过（高）** | `Configured with:` 1435 B `cmp=0`、SHA256 `3028beb3…aad4`；`.comment` 51 B 逐字节相同；`SEARCH_DIR` 钉死 `/Users/mrs/...` 且相同；`-print-multi-lib` 43 行 `cmp=0`；gcc/as/ld 版本串相同；`--help=params` 全量 `cmp=0` |
| 7 | pristine 复放声称 | **通过（高）** | 16/16 `git patch-id --stable` 三方一致（文件 / `patch-id.tsv` / active 仓库历史）；导出补丁按 series 顺序 apply 到 pristine base 后 `write-tree` 与 active HEAD tree **逐字相同**；8/8 tarball SHA256 命中 README |
| 8 | active 274/274 gate 声称 | **通过（高）** | 本次独立重跑 `rc=0`、`gate_pass=274 gate_total=274 gate_fail=0`、`aux_diff=4`；274 条 gate 行与作者 `final-active-compare-*/compare.stdout` **逐行相同** |
| 9 | 边界完整性 | **通过（高）** | `patches/15.2.0` git 无改动；`analysis/golden/15.2.0-darwin-arm64.tsv` 无改动；15.2.0 源码树 clean、最后 commit 早于 phase-4 起点、phase-4 起点后 0 个文件被改；`ref/` 改动集 == 9 个 EVT 工程文件；仓库根 HEAD 仍 `db9bed6`，无新 commit |
| 10 | 指令覆盖审计 | **1 项偏离（已裁定合理）、1 项缺口** | 见 §6；缺口 = GCC 回归测试被过滤（P2-1） |

---

## 2. 发现列表

### P2-1 GCC 上游回归测试从未跑过，只跑了本项目新增的 7 个用例 —— 置信度 高

`tmp/phase4-evidence/final-active-tests-20260813T003203Z/commands.txt` 显示 GCC 侧七条命令
全部带过滤器：

```
make ... check-gcc RUNTESTFLAGS='riscv.exp=wch-xw-*.c'
make ... check-gcc RUNTESTFLAGS='riscv.exp=zbs-load-single-bit.c'
... （共 7 条，合计 423 PASS）
```

GAS 侧是 `make ... check RUNTESTFLAGS=riscv.exp`（无过滤，202 PASS，含被本补丁集改写的
上游 `.d/.l` 期望文件）。也就是说 **`gcc.target/riscv` 上游全量套件一次都没跑过**，
checklist 与 plans 中的「625 项源码测试、零 unexpected」实际只覆盖新增用例。

这不是无关紧要的过滤，因为下列补丁改的是通用 RISC-V 后端 / 目标无关文件，作用于全部
multilib 与 RV64：

- `gcc/0004`：`gcc/config/riscv/predicates.md` `splittable_const_int_operand` 去掉 `TARGET_64BIT &&`
- `gcc/0006`：`gcc/config/riscv/riscv.md` 12 处乘法 pattern 条件、`riscv.cc` 代价模型
- `gcc/0007`：`gcc/config/riscv/riscv.h` 重定义 `SINGLE_BIT_MASK_OPERAND`、两个 predicate 换实现
- `gcc/0008`：`gcc/config/riscv/riscv.cc` `riscv_build_integer_1` 中间值截断
- `gcc/0009`：`gcc/c-family/c-attribs.cc`（目标无关）、`gcc/params.opt`（`Common`）

失败场景：例如 `gcc/0007` 把 `not_single_bit_mask_operand` 从 `pow2p_hwi (~INTVAL (op))`
改成 `SINGLE_BIT_MASK_OPERAND (~UINTVAL (op))`，在 RV32 下会把高 32 位掩掉；若某个
DImode 常量路径依赖旧语义，只有上游套件能发现——274 件 gate 产物来自 9 个工程、
少数几个 multilib，覆盖不到。

缓释证据（本次实跑，降低但不消除该风险）：我另跑了 21 组对抗矩阵——
`{-O0,-Os,-O1,-O2,-O3} × {rv32i_zbs, rv32imac_zba_zbb_zbc_zbs, rv32imac}` 共 15 组，
外加 `{-O0,-Os,-O2} × {rv64imac_zbs, rv64imafdc_zicsr}` 共 6 组，输入含
`0x80000000`/`0x7fffffff`/bit0/bit11/`0x100000000`/`0x8000000000000000` 等边界常量——
**ours 与官方的 `.s` 与 stderr 全部逐字节相同，无 ICE**。

因此 WCH 保真度风险低；缺口在**上游回归 / 未来 rebase 风险**，以及「可向上游 reviewer 解释」
所需的证据完整性。

修复：两条 lane 各补跑一次 `make check-gcc RUNTESTFLAGS=riscv.exp`（不带过滤），
落 `.sum` 到证据树；或由 Main 明示裁定「只对 WCH 行为面做回归」，并把这条写进 checklist，
不要让「625 PASS、零 unexpected」读起来像全量套件。

### P2-2 `.highcode` 落在目标无关代码里，但「为什么不是 riscv 后端」无证据链 —— 置信度 中

`patches/12.2.0/gcc/0009-gcc-implement-WCH-highcode-section-splitting.patch` 把行为实现在
`gcc/c-family/c-attribs.cc:2278` 的通用 `handle_section_attribute` 中，参数在
`gcc/params.opt` 声明为 `Common`。测试却放在 `gcc/testsuite/gcc.target/riscv/`。
commit message 只描述行为，未说明这个「目标无关」的选择本身是官方设计。

本次补证（结论是该设计正确，但证据是我补的，不在交付物里）：
官方 `riscv-wch-elf-gcc --help=params` 输出含
`--param=highcode-gen-section-name=<0,1> __attribute__((section(.highcode)))` /
`generate new section name.`，而 `--help=target` 中 0 命中 —— 说明官方也确实把它放在
Common 参数集。ours 的 `--help=params` 与官方全量 `cmp=0`。

失败场景：上游 reviewer（或半年后的自己）问「为何改 c-family 而不是 riscv 后端」，
交付物里答不上来。修复：把上面这条 `--help=params` vs `--help=target` 的探针结论
写进 commit message 或 `patches/12.2.0/README.md`。

### P3-1 `binutils/0005` 以 `TARGET_VENDOR` 字符串作为行为开关 —— 置信度 高

`gas/config/tc-riscv.c` `riscv_write_out_attrs()` 中：

```c
  if (strcmp (TARGET_VENDOR, "wch") == 0)
    return;
```

不是 EVT 特判（是 triple 级条件，非工程/文件级），因此不违反 AGENTS.md 硬规则；
但也不是上游惯用形态——上游抑制属性合成通常走 configure 选项或命令行开关。
无功能失败场景，属上游可接受性问题。修复：在 README 的已知偏离里记一笔，
或将来若真要上游化，改成 `-mno-priv-attr` 之类的显式开关。

### P3-2 `binutils/0004` 改了反汇编器但 commit message 未提 —— 置信度 高

`opcodes/riscv-dis.c` 新增 `if (op->insn_class == INSN_CLASS_XW) continue;`，
即反汇编时整类跳过。commit message 只说「shares the D+C encoding slot and diagnostics」，
没说为何要动 disassembler。

本次补证：**这是对的**。官方 `riscv-wch-elf-objdump -d` 对 XW 压缩编码同样打印
`.2byte 0x2188` 等原始半字（不解码），ours 与官方的反汇编输出逐字节相同
（唯一差异是 objdump 头里的输入文件名）。原因是 `MATCH_XW_C_LBU 0x2000/0xe003`
与 `c.fld` 编码槽重叠，不跳过就会污染所有 RV32 D+C 代码的反汇编。
修复：commit message 补一句。

### P3-3 `xw_enabled` 是不参与 `.option push/pop` 的文件级 sticky 全局 —— 置信度 高

`gas/config/tc-riscv.c` 的 `static bool xw_enabled;` 只在 `riscv_set_arch()` 里 `|=`，
从不复位，也不进 `struct riscv_option_stack`。commit message 称之为
「preserves initial-architecture sticky eligibility」，但没写明 push/pop 故意不还原它。

本次补证：**语义与官方逐字节一致**。四组边界用例 ours 与官方 obj+stderr 全同：
`.attribute arch,"rv32imac_xw"` 后 `.option arch,-xw` 仍可汇编 `c.lbu`（sticky 生效）；
单独 `.option arch,+xw` **不能**启用（官方同样报 `illegal operands`）；
`.attribute arch,"rv32imac"` 在 `-march=…_xw` 命令行下仍可汇编；
XW 启用后 `c.fld` 被拒。属文档问题，非行为问题。

### P3-4 `gcc/0009` 未保护 `DECL_NAME (decl)` 为 NULL 的情形 —— 置信度 高

```c
	  if (param_highcode_gen_section_name)
	    new_section_name = ACONCAT ((new_section_name, ".",
					IDENTIFIER_POINTER (DECL_NAME (decl)),
					NULL));
```

`DECL_NAME` 为 `NULL_TREE` 时 `IDENTIFIER_POINTER` 会解引用空指针。我未能构造出复现
——C/C++ 里带 `section` 属性的 decl 总是具名。记为理论缺陷，非实测缺陷。
修复：加一个 `DECL_NAME (decl) &&` 守卫，或在注释里注明不可达。

### P3-5 仓库里有 1.9 GB 未跟踪且未被 gitignore 覆盖的二进制 —— 置信度 高

`ref/Archive.zip`（1,849,942,658 B，`2b5402d5…6543`）与 `ref/dec.tar`
（65,427,456 B，`32ae5843…31ab`）为 untracked，且 `git check-ignore -v` 对两者均无命中。
两者 mtime 为 2026-08-12 22:28/22:38，**早于 phase-4 起点**，不是 phase-4 产生的，
但验收时若执行 `git add -A` 会把 1.9 GB blob 提交进仓库。
修复：加 `.gitignore` 规则或删除，然后再做验收提交。

### P3-6 `plans/gcc-12.2.0.md` 前提登记中 vendor-X 表述偏窄 —— 置信度 高

前提登记写「仅观测到的 `xw` 与裸 `x` 接受」。实测：裸 `x` 接受**任意版本后缀**——
官方 `-march=rv32ix9p9` → `x9p9`、`rv32ix123` → `x123p0`、`rv32ix` → `x1p0`，
ours 全同。补丁本身正确（表项 `{"x", ISA_SPEC_CLASS_DRAFT, 1, 0, 0}` 只是默认版本），
是登记文字读起来像「只接受无版本的 x」。修复：把「裸 `x`」改为「`x` 前缀（任意版本）」。

### P3-7 `analysis/toolchain/phase4-diff-inventory.md:4` 引用的 S2 commit 已不可达 —— 置信度 高

文中记 S2 GCC HEAD `65fe1a3a…`。该 commit 现仅通过 reflog 可达（`git cat-file -t` 仍返回
`commit`，`reflog` 1 命中），不在任何分支上，`git gc` 后会消失。
`tmp/phase4-evidence/s2-first-compare/` 里的 `SUMMARY gate_pass=1 gate_total=274
gate_fail=273 aux_match=27 aux_diff=250` 仍是权威记录，所以实际影响很小。

### P3-8（正面）4 处 `.map` 差异已被本次量化归因，不含行为信号 —— 置信度 高

checklist 称「aux 273 match / 4 `.map` differences，仅诊断」。表面上差异不小
（v3f-gpio：172,805 → 192,998 B，+11.7%），我做了归因：

- 我方工具链根 `/Users/apple/…/tmp/toolchain_12.2.0/riscv-none-elf-gcc-xpack.git/build/darwin-arm64/application` 长 110 字符
- 官方根 `/Users/apple/Projects/openwch/ref/gcc/darwin-arm64/12.2.0` 长 57 字符
- 该串在 map 中出现 381 次；`381 × (110 − 57) = 20,193`
- 实测尺寸差 `192,998 − 172,805 = 20,193` —— **精确相等**

即 `.map` 差异 100% 来自工具链安装根前缀长度，与 DECISIONS.md 中已裁定「工具链安装根前缀
不在 gate 覆盖面」（P2-1 裁定）一致，不含归档成员选择或链接决策差异。
未直接落证项：归一化前缀后两份 map 是否逐字节相同（官方 map 已被后续 compare 覆盖，
需再跑一次官方全量才能取回）——标 **UNVERIFIED**，但尺寸精确相等已使其他解释近乎不可能。

---

## 3. 关键实测（ours vs 官方，同 cwd、`SOURCE_DATE_EPOCH=1767225600`，stdout/stderr/产物全比、不 normalize）

### 3.1 `.highcode`

| 探针 | 官方结果 | ours |
|---|---|---|
| `--param=highcode-gen-section-name=0`，函数 `.highcode` | 段名保持 `.highcode`，callee 不被 inline（`-O2` 下符号仍在） | `.s` 逐字节相同 |
| `=1`，`int source_name(int) __asm__("assembler_name")` | `.section .highcode.source_name` + 标签 `assembler_name:` —— 用**源码声明名**而非汇编名 | `.s` 逐字节相同 |
| `=1`，变量 `highcode_object` | `.section .highcode.highcode_object,"aw"` —— 变量同样拆节 | 相同 |
| `=1`，`.highcode.extra` / `.highcode_init` / `.Highcode` | **均不改写**（精确、大小写敏感匹配） | 相同 |
| `=2`（越界） | `riscv-wch-elf-gcc: error: argument to '--param=highcode-gen-section-name=' is not between 0 and 1`，rc=1 | stderr 逐字节相同 |
| 函数+变量同放 `.highcode`（`=0`） | `error: 'highcode_object' causes a section type conflict with 'source_name'`，rc=1 | stderr 逐字节相同 |
| `--help=params` 全量 | 含该参数与 `generate new section name.` | 全文件 `cmp=0` |

补丁 testsuite 里 `wch-highcode-sections.c` 断言的每一条（源码名 vs 汇编名、三种近似拼写不改写、
变量拆节）本次都在**官方二进制上**独立复现，不是「合理推断」。

注：作者的 `tmp/phase4-evidence/highcode-12.2-official/assertions.tsv` 只列了 5 个 case
（param0/param1/noinline/invalid/gc-link），**未含大小写与近似拼写、以及源码名 vs 汇编名**这两条。
这两条的官方证据由本次审计补齐——原交付物在这两点上确实只有本项目自己的 testsuite 断言。

### 3.2 `-wchsoftlib` / `--wchsoftlib`

| 选项 | 官方 `e_flags` | obj cmp | stderr cmp |
|---|---|---|---|
| `--wchsoftlib` | `0x1000001, RVC, soft-float ABI` | 相同 | 相同 |
| `-wchsoftlib`（单横线） | `0x1000001` | 相同 | 相同 |
| `--wchsoftlib --wchsoftlib` | `0x1000001` | 相同；且与单次的 `.o` **逐字节相同**（幂等落证） | 相同 |
| `--wchsoftlib -mrelax` | `0x1000001` | 相同（与 relax 正交落证） | 相同 |
| 不带 | `0x1` | 相同 | 相同 |

`EF_RISCV_WCH_SOFTLIB 0x01000000` 与 `0x1`（RVC）OR 得 `0x1000001`，与实测一致。

### 3.3 M / Zmmul

| 探针 | 官方 | ours |
|---|---|---|
| GCC `-march=rv32imac_zmmul` | `cc1: error: can not use both the 'ZMMUL' and the 'M' extension`，rc=1 | stderr 逐字节相同 |
| GAS `-march=rv32imac_zmmul` + `mul` | 接受，rc=0 | `.o` 逐字节相同 |
| GAS `-march=rv32i_zmmul` 属性 | `rv32i2p0_zmmul1p0` | 相同 |
| GAS `-march=rv32i_zmmul` + `div` | `Error: unrecognized opcode 'div a0,a1,a2'`，rc=1 | stderr 逐字节相同 |
| GAS `-march=rv32im` 属性 | `rv32i2p0_m2p0_zmmul1p0`（M 隐含 Zmmul） | 相同 |

GAS 接受而 GCC 拒绝 M+Zmmul 这一非对称性，ours 完整复现。

### 3.4 vendor-X 接受面

| `-march=` | 官方 GAS `Tag_RISCV_arch` / 诊断 | ours |
|---|---|---|
| `rv32imacxw`（连写） | `rv32i2p0_m2p0_a2p0_c2p0_zmmul1p0_xw1p0` | `.o` 相同 |
| `rv32imac_xw`（下划线） | 同上（与连写产物逐字节相同） | `.o` 相同 |
| `rv32imac_xw1p0` | 同上 | `.o` 相同 |
| `rv32imacxw9p9` | `…_xw9p9`（显式版本保留） | `.o` 相同 |
| `rv32ix` | `rv32i2p0_x1p0` | `.o` 相同 |
| `rv32ix9p9` / `rv32ix123` | `x9p9` / `x123p0` | `.o` 相同 |
| `rv32imac_xq` | `Error: rv32imac_xq: unknown prefixed ISA extension 'xq'`，rc=1 | stderr 逐字节相同 |
| `rv32i_xargle2p0` / `rv32i_xargle` | `Error: …: unknown prefixed ISA extension 'xargle'` | stderr 逐字节相同 |

另：GCC driver 对 `rv32ix` 报
`error: '-march=rv32ix': name of non-standard extension must be more than 1 letter`（rc=1），
而 GAS 接受 `rv32ix` —— 这个 driver/GAS 不对称也逐字节复现。

`gas/testsuite/gas/riscv/wch-vendor-x-*.l` 中的期望文本与我在官方二进制上取到的
stderr 逐字相同（`unknown prefixed ISA extension 'xq'`、`'xargle'`），
符合「期望文件=官方文本」的硬约束。

### 3.5 12.2.0 自己的缺陷保真面（未假设与 15.2.0 相同）

| 面 | 15.2.0 情况 | 12.2.0 实测 | 处置 |
|---|---|---|---|
| `non-standard111` 诊断 | 15.2.0 官方有此拼写，`patches/15.2.0/gcc/0002` 专门保真 | 官方 `cc1`/`cc1plus` 中 `non-standard111` **0 命中**，`unsupported non-standard` 2 命中；ours 完全相同 | **正确未移植**，直接落证「禁止盲移植」被遵守 |
| 中断属性 | 15.2.0 有 fast-interrupt 帧补丁 | `interrupt("WCH-Interrupt-fast")` 静默 + `mret`；`"WCH-Interrupt-Fast"`（大小写 typo）与 `"bogus"` 发**同一条** `-Wattributes` 警告 + `ret` | ours 的 `.s` 与 stderr 与官方逐字节相同 |
| 未知 X 经 gcc→gas | — | `-march=rv32imac_xfoo`：driver 通过，GAS 两行诊断拒绝 | 归一化临时文件名后 stderr 逐字节相同 |
| 32 位自定义指令 | 与 15.2.0 编码同 | `mcpy/mrsl/mrslu/wexti` 在 `rv32i` 下即可汇编；`60b5700f/1ec5850b/1cc5850b/18c5850b` | `.o`、反汇编、错误流均逐字节相同 |
| XW 压缩编码 | — | 8 条压缩形式 + 4 条普通 alias；objdump 打印 `.2byte`（官方也不解码） | `.o` 与反汇编逐字节相同 |
| GAS mapping symbol | 15.2.0 为 `xw2p2` | 12.2.0 恒为 `$x`（baseline 记录，本次未复测符号名） | 未落证项标注见 §7 |

---

## 4. 16 片补丁可解释性判定

判定口径：上游惯用形态；每处改动可溯源到一个有证据的行为；无裸字节块 / 不透明搬运 /
EVT 特判 / 讲不清依据。

| # | 补丁 | 判定 | 依据与备注 |
|---|---|---|---|
| gcc 0001 | `riscv: configure WCH 12.2 multilib set` | **合格** | 纯 `t-elf-multilib` 生成结果（42 条 + default），multilib-generator 注释行保留可复算；43 行输出本次 `cmp=0` |
| gcc 0002 | `Backport safe-ctype include ordering…` | **合格** | 明确标注 backport 上游 `releases/gcc-12` commit `a995fded34fe…`（PR middle-end/111632）；宿主构建使能，与目标行为无关 |
| gcc 0003 | `test unversioned WCH XW march strings` | **合格** | 纯新增 2 个 testsuite 用例，无源码改动；正确地**不**在 GCC 侧加 XW 默认版本（默认由 GAS 提供），与 §3.4 实测一致 |
| gcc 0004 | `recognize RV32 Zbs single-bit constant moves` | **合格** | 1 行 predicate 条件；commit message 给出现象（`extract_insn` ICE）与规格来源（官方 `.s`） |
| gcc 0005 | `implement WCH hardware-saved fast interrupts` | **合格** | 惯用形态：`machine_function` 新字段 + 4 个 hook 分支；typo 警告行为被刻意保留并写进 testsuite；§3.5 实测相符 |
| gcc 0006 | `generate multiply instructions for Zmmul` | **合格** | 与上游 GCC 13 的 Zmmul 实现形态一致（`riscv_zmmul_subext`/`MASK_ZMMUL`/MD 条件）；冲突诊断保留官方的不合语法拼写 `can not`，属有意保真 |
| gcc 0007 | `recognize the RV32 sign bit in Zbs masks` | **合格** | `SINGLE_BIT_MASK_OPERAND` 按 XLEN 掩码，理由（HOST_WIDE_INT 符号扩展）写在 message 里，可解释 |
| gcc 0008 | `truncate RV32 integer-building intermediates` | **合格** | `trunc_int_for_mode` 3 行；O0/Os/O1/O2 官方 `.s` 作规格来源 |
| gcc 0009 | `implement WCH highcode section splitting` | **合格（附 P2-2、P3-4）** | 惯用形态（`params.opt` + 通用 section 属性 hook）；行为断言本次全部在官方二进制上复现。扣分项：目标无关落点无证据链、`DECL_NAME` 未守卫 |
| bu 0001 | `accept WCH XW 1.0 arch attributes` | **合格** | 标准 `riscv_supported_*_ext` 表项 + 默认版本查表分支 |
| bu 0002 | `add Zmmul 1.0 instruction subset` | **合格** | 与上游 binutils 2.39 的 Zmmul 实现形态一致（implicit subset `m→zmmul`、`INSN_CLASS_ZMMUL`、mul* 重分类、div* 留在 M）；改写的 8 个上游 `.d` 期望是 `zmmul1p0` 隐含项的必然结果 |
| bu 0003 | `assemble WCH custom 32-bit instructions` | **合格** | 4 条 opcode 表项 + `F5` 操作数类（parser/validator/printer 三处对称）；编码来源指向 `ref/wch-isa-research/…/wch-custom-isa-reference.md` §5，属「上游惯用 opcode 编码表」，不在禁令范围 |
| bu 0004 | `add WCH XW compressed load and store forms` | **合格（附 P3-2、P3-3）** | 8 条编码 + `ENCODE/EXTRACT/VALID` 宏三元组（上游标准形态）+ 操作数类；扣分项均为 message 缺说明，行为本次全部落证 |
| bu 0005 | `omit WCH finish-time privilege attributes` | **合格（附 P3-1）** | 5 行 early return；改写 7 个上游 `.d` 是该行为的必然结果 |
| bu 0006 | `restrict WCH vendor extensions to the observed set` | **合格** | 表驱动替代原来的 `strcmp(ext,"x")` 特例；改写 15 个上游 `xargle/xvendor` 用例为 `xw/x` 属必要（未知 X 已被拒），message 注明「Independent binary analysis confirmed the official table」；§3.4 逐条复现 |
| bu 0007 | `emit the WCH soft-library ELF flag` | **合格** | `md_longopts` + `EF_RISCV_WCH_SOFTLIB` 常量 + `riscv_elf_final_processing` 里一次 OR；隐藏（不进 `md_show_usage`）有注释说明；§3.2 逐条复现 |

**汇总：合格 16 / 存疑 0 / 违规 0。** `final-design-audit-*/{evt-special-case-hits,opaque-byte-hits}.txt`
均为 0 行，与我通读结论一致。全部 16 条 commit message 都含「差异现象 + 规格来源（evidence 路径或上游 commit）」。
证据指针可达性本次逐条抽验：16 条 message 正文共引用 53 个仓库内路径
（`tmp/phase4-evidence/…`、`ref/wch-isa-research/…`、`ref/wch-evt/…`、`analysis/…`），
**53/53 全部存在，0 悬空**。

---

## 5. 完整性与复放（本次独立复算）

| 项 | 声称 | 本次实测 |
|---|---|---|
| active GCC HEAD / tree | `9e5c14891…` / `37559608d0be…` | 一致，`status --porcelain` 空 |
| active binutils HEAD / tree | `d879720d2…` / `f7e1a27f3e…` | 一致，clean |
| pristine GCC / binutils HEAD | `e356b10c3…` / `7ed9b8e54…` | 一致（`tmp/toolchain_12.2.0/pristine-replay/…`），clean |
| pristine tree == active tree | 声称相等 | **相等**：`37559608d0be…` / `f7e1a27f3e…` 两侧完全相同 |
| base import tree 两 lane 一致 | — | GCC `e66ae7537f9a…`、binutils `d66ce22b2d9b…` 两 lane 相同 |
| 16 stable patch-id | `patch-id.tsv` | 文件重算 16/16 命中；与 active 仓库 `diff-tree \| patch-id --stable` 16/16 命中（三方一致） |
| 顺序 apply-check | 16/16 | 本次用 `read-tree` + `git apply --cached` 从 pristine base 顺序重放：16/16 OK，`write-tree` 得 `37559608d0be…` / `f7e1a27f3e…`，与 HEAD tree **逐字相同** |
| 8 个 tarball SHA256 | README 表 | 8/8 命中（`gcc/binutils/gmp/mpfr/mpc/isl/zlib/zstd`） |
| commit 数 | gcc 9 + binutils 7 | gcc `rev-list --count`=10（1 base + 9）、binutils=8（1 base + 7） |

补充观察（非发现）：`tmp/toolchain_12.2.0-pristine/`（gcc n=9、binutils n=6）与
`tmp/toolchain_12.2.0/replay-wrapper-smoke/`（同）是更早的中途复放树，tree 与最终值不同。
最终声称指向的是 `tmp/toolchain_12.2.0/pristine-replay/`，checklist 的路径写法正确，
但同目录下并存三棵 pristine 树容易误读，建议清理或加 README 说明。

---

## 6. 指令覆盖审计（对照 `tmp/prompts/phase-4.md` 硬约束）

| 硬约束 | 判定 | 依据 |
|---|---|---|
| 只改 gcc/binutils 源码、git 管理、单 commit 单逻辑、message 含现象+规格来源 | **遵守** | 16 commit 全部单逻辑、全部含现象与 evidence 指针（§4） |
| 库与 sysroot 从官方原字节注入，只建编译器不建 target 库 | **遵守** | `build-toolchain-12.2.0.sh` 仅建 host 工具；`s2-literals-final/injection-samples.tsv` 六项；本次 274/274 gate 通过间接确认注入正确 |
| 行为规格 = 官方二进制现场探测（含缺陷保真） | **遵守** | §3 全部 40+ 组对拍；缺陷面 §3.5 |
| **诊断文本从第一轮起纳入保真面（15.2.0 的 P2-2 教训）** | **遵守** | `s1-official/diagnostics.tsv`（33 case）产生于 S1（04:33），早于第一个行为补丁（binutils 06:30）；final 两 lane 各 33/33、`mismatch_rows=0` |
| **GAS 测试期望文件一律写官方文本** | **遵守** | 本次抽验 5 组：vendor-x（`xq`/`xargle`）、`zmmul-div`、`wch-custom32-fail`（funct5 三行）、highcode 越界、zmmul 冲突 —— 期望文本与官方 stderr 逐字相同 |
| 字面量钉死（`/Users/mrs/…`、configure 逐字节、`.comment`） | **遵守** | §1 第 6 行；`/Users/mrs/Work/riscv-none-elf-gcc-xpack.git` symlink 指向 active |
| 版本陷阱：裸 `xw` → `xw1p0`（非 `xw2p0`） | **遵守** | §3.4 实测 `xw1p0` |
| **15.2.0 补丁只作参照，禁止盲移植** | **遵守，且有反证** | `non-standard111` 在 12.2.0 不存在且未被移植（§3.5）；`phase4-diff-inventory.md` §「Explicitly excluded blind ports」逐条列出未移植项；bu 0001 用 `xw1p0` 而非 15.2 的 2p0 |
| **S2 只测量不修补** | **偏离（判定：合理，但需明示裁定）** | S2 期间落了 2 个 GCC commit：`41ea9f548`（04:49 multilib 配置）与 `b760fc139`（05:20 宿主 libc++ backport）。二者均非 WCH ISA 行为修补——前者是字面量面（43 行 multilib）、后者是宿主可构建性。commit 时间序确认第一个行为补丁是 binutils `9515ad91`（06:30），确在其后。checklist 自己也写明「S2 source 仅 multilib 配置与 upstream host backport」。**建议 Main 明示裁定**，不要留作隐性偏离 |
| 不 commit 仓库根 | **遵守** | HEAD 仍 `db9bed6`，无新 commit；交付物为工作区未跟踪状态 |
| 不修改 `ref/`、15.2.0 的补丁/构建树/harness 语义 | **遵守** | §1 第 9 行；`scripts/evt-{compare,golden}.sh` 的改动是 phase-5 的 linux 平台派生（`platform` 变量 + `sha256sum` 回退 + 容器镜像头），darwin/12.2.0 代码路径语义不变，且本次官方与 ours 两次运行均正常 |
| 未决问题写 checklist 后停下返回 | **遵守** | 未决问题数 0，与本次审计未发现阻断项一致 |

---

## 7. 未落证 / UNVERIFIED 项（如实记录）

1. **归一化前缀后的 `.map` 逐字节比较**（P3-8）：需再跑一次官方全量 compare 才能取回官方 map；
   尺寸差 381×53=20,193 精确相等已使其他解释近乎不可能，但严格意义上未直接比较。
2. **GAS mapping symbol 恒为 `$x`**：采信 `phase4-baseline.md` 与 `s1-official/`，本次未复测。
3. **pristine lane 的 EVT gate**：本次只独立重跑了 active lane（274/274 复现）与官方 lane（274/274）。
   pristine lane 的 274/274 **采信** `final-pristine-compare-20260813T012000Z/`。
   我独立落证的是**源码树逐字相同**（`37559608d0be…` / `f7e1a27f3e…`）；
   源码树相同并不蕴含二进制产物相同——同源不同环境产生不同字节正是本项目的立项前提。
   因此该项的实际证据强度是：树同一性（我复算）+ 作者记录的 pristine gate 274/274
   + 作者记录的 pristine 探针（13/13 literals、33/33 diagnostics、8/8 wchsoftlib），
   而非逻辑必然。若要消除该采信，需实跑一次 pristine lane 的全量 compare。
4. **625 项测试的 pristine lane 复跑**：未做，同样为采信。P2-1 指出的过滤问题对两条 lane 同等成立。
5. **xPack `v12.2.0-3` 基线锚定**：`phase4-baseline.md` 的公网核对（bundled 文件与公开 tag 逐字相同、
   commit `1737182b…`）本次未联网复核，采信其记录；该结论只影响 provenance 叙述，不影响字节 gate。
6. **`ref/Archive.zip` / `ref/dec.tar` 的来源**：未跟踪、未 gitignore、早于 phase-4；本次未打开检视其内容。

---

## 8. 验收建议

**有条件放行。** P0=0，P1=0，P2=2，P3=8（其中 1 条为正面归因）。

唯一 gate（`.o/.elf/.bin` 逐字节一致）本次由我独立复现：官方 lane 274/274 + 277/277 aux，
active lane 274/274 且 274 条 gate 行与作者证据逐行相同；16 片补丁全部可解释、
零 EVT 特判、零不透明字节块；四个新特性面的每一条行为断言都在官方二进制上现场复现，
不是推断；pristine 复放由我用独立方法（index 重放）确认 tree 逐字相同。

放行前建议完成（均不阻断 gate，按优先级）：

1. **P2-1**：两条 lane 各补跑一次不带过滤的 `make check-gcc RUNTESTFLAGS=riscv.exp`，
   把 `.sum` 落进证据树；或由 Main 裁定只做 WCH 面回归，并把 checklist 里
   「625 项源码测试」的口径改写清楚（现在读起来像全量套件）。
2. **P2-2**：把 `--help=params` vs `--help=target` 的官方探针结论写进 `gcc/0009`
   的 commit message 或 `patches/12.2.0/README.md`，补上「为何落在 c-family」的证据链。
3. **「S2 只测量不修补」的偏离**由 Main 明示裁定并记入 `DECISIONS.md`，
   与 phase-3 的 P2-1 裁定同格式。
4. **P3-5**：在验收提交前处理 `ref/Archive.zip` / `ref/dec.tar`（1.9 GB，未 gitignore）。
5. P3-2 / P3-3 / P3-6 / P3-7 为 message 与文档措辞修正，可随下一次导出一并处理。
