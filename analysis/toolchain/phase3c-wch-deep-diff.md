# Phase 3c — WCH canonical 15.2.0 工具链全差异深析

## 结论

**正式 verdict：`INVALID`。** Phase 3c 冻结输入之后，另一个并发工作流改变了本阶段规定为 immutable 的 root/binutils/patch/output/golden-link 状态，而且这些外部变化没有被恢复。`tmp/prompts/phase-3c.md` 明确定义“输入树被本阶段期间改变且未恢复”为 `INVALID`；本阶段没有权限回滚其他工作的修改，因此不能把这次运行提升为有效的 `FAIL` 或 `PASS`。

这不是“没有发现差异”。绑定到 T0 冻结身份的证据仍可复算；若只评价其技术结果而暂时忽略 immutable 失败，**反事实实质 verdict 是 `FAIL`**：35 个 canonical 功能中 12 个已覆盖、12 个 `GAP`、11 个 `UNRESOLVED`；冻结 OURS 的 172 个强制 probe 行中 97 行 exact/baseline、18 行 mismatch、57 行因 T0 原件丢失而不可运行。任一 GAP、UNRESOLVED、mismatch 或 NOT-RUN 都足以阻止 PASS。

本报告只做分析和报告，没有修改 GCC/binutils active source、既有 patch、`ref/`、EVT、converter、harness 或仓库根脚本，也没有创建补丁、commit、reset、checkout 或 clean。并发变更被保留并列为外部漂移，不被冒充为本阶段 OURS。

## 精确分母

| 分母 | 结果 | 闭合状态 |
|---|---:|---|
| WCH package paths | 3,234 | 3,234/3,234 inventory |
| acceptance-gate paths | 616 | 616/616 分配到 29 个 implementation groups |
| external frozen WCH runtime | 2,500 | 全部 path/hash/type/source 分类，不进入 compiler binary denominator |
| out-of-scope frozen | 32 | gdb/sim-owned 路径按规则冻结 |
| package-inventory-only | 86 | 已分类，不冒充功能 gate |
| acceptance path dispositions | 551 byte-exact + 46 byte-different + 1 mode-only + 2 missing-control + 16 directories | 合计 616 |
| WCH↔OURS byte-different Mach-O paths | 46 | 四侧 canonical obligation 共 184 = 46 × 4 |
| binary interval obligations | 184 | 184/184 从 0 到 EOF 连续、无洞、无重叠 |
| semantically classified obligations | 12 | GAS/objdump 的 12 个 WCH/P2/matched side-path obligations |
| semantic `UNRESOLVED` obligations | 172 | 结构覆盖 100%，但不得把整文件 tiling 冒充语义解释 |
| binary-region rows/file-sides | 1,818 / 190 | permitted enum、interval 和文件大小机械校验通过 |
| append-only feature candidates | 81 | 81/81 映射到唯一 canonical/nonfunctional target |
| canonical functional features | 35 | 12 covered / 12 GAP / 11 UNRESOLVED |
| probe rows | 1,284 | WCH 340、P2 336、matched 208、OURS 293、replay 107 |
| mandatory probe rows, all sides | 849 | 每行都有 `side_id/control_id` |
| exact frozen-T0 OURS mandatory rows | 172 | 97 exact、18 mismatch、57 unavailable |
| errata source rows | 50 | 12 runtime + 14 document + 24 research/06b leads |
| deduplicated semantic findings | 44 | 44/44 有结论 |
| unresolved ledger rows | 21 | 逐项给出阻塞原因、影响分母、已尝试证据和 next action |

机器复算来源是 `final-summary.json`、`mismatch-summary.tsv`、`binary-coverage-obligations.tsv` 和 `strict-feature-validation.txt`。异质单位没有相加：18/172 是 probe-row 计数；D+C+XW 的 16,384/131,072 是两个独立反汇编 mode 的 halfword-cell 计数；10/35 是至少一个适用目标产物 gate 为 `DIFF` 的 feature 计数。

## 身份与四侧控制

### WCH

Canonical 发布树是 `ref/gcc/darwin-arm64/15.2.0/`。GCC 可观察身份为 `riscv32-wch-elf-gcc (g5115c7e44-dirty) 15.2.0`。WCH binutils 二进制只证明版本 2.45；本报告没有声称复原 WCH 私有 parent commit 或 binutils configure argv。

### UPSTREAM-SOURCE / UPSTREAM-P2

- GCC exact base：`5115c7e447fc07457443df874bf57840e8316d5f`
- binutils release baseline：`2bc7af1ff7732451b6a7b09462a815c3284f9613`
- Phase 2 原版 executable control 来自保存的 quarantine manifest；它不具备 host zstd capability。
- P2 的 GCC driver 会在读取含 XW 的 pristine multilib generator 时产生 10 条错误。这是实际 upstream control 行为，不是 OURS 行为，也不是审计工具错误；backend lane 另用 direct-cc1 控制隔离了非 driver 代码生成。

### UPSTREAM-MATCHED

最终能力匹配控制位于 `tmp/phase3c-driver/upstream-matched-zstd-r3/output`。它使用完全相同的 GCC/binutils upstream source 和 zstd v1.5.7 `f8745da6ff1ad1e7bab384bd1f9d742439278e99`。安装 manifest 716 行，SHA-256 `b7b85ba5788d60bb0517c180edd425674cff12af994a2eb68eb2b58c18f114e9`。

关键 executable SHA-256：gcc `8adc83c82785da5127126bfb25f9a4dbf9ece8231bec878bbc341e1e6749f680`、as `ee61fb024382d826032679cc4bc36c0523e922b9b1fc2dc9b9966536ebca57e7`、ld `804c550cd96c6b25666b15f3a4c9f1f153db25b238fd1165ba3d852f0c941ca8`、objcopy `270e87512ffe2b98c3d6bbf4ee49a0871817cd954ae47e7f3ba2cfb0891cf0a6`、readelf `5c5717e52b9a222666f60b62fd61f36cab243cdd30b0eb7e6f6d899561432e4a`。`gcc_cv_as_compress_debug=2`、`gcc_cv_ld_compress_debug=2`；四个 BFD tools 均导入 `@loader_path/libzstd.1.dylib`。较早的 `upstream-matched/output` 只是 `UPSTREAM-MATCHED-CAPABILITY-PROBE-NO-ZSTD`，没有被当作最终 matched side。

### OURS 与冻结边界

T0 OURS 定义为 exact bases 加冻结的 GCC 3 + binutils 5 patch。冻结时 GCC source HEAD 为 `de9b62e3768877c5757eb5454dddd593145c5b2b`，binutils HEAD 为 `258634dda7ce7b529231c57474372ecc4aca3408`；安装 manifest 有 3,177 行。所有结论绑定到该 manifest 和每次 runner 捕获的 executable/input hash，而不是目录名或后来被覆盖的 active alias。

外部漂移后，当前树与冻结 OURS 的 3,177 行比较为 3,150 exact、27 drift、0 missing。五个 primary GCC driver hashes 仍与 T0 一致；27 个漂移项均位于被外部重建的 binutils 输出面。源一致的五补丁 cleanroom/replay 只标为 `OURS-PROVEN-REPLAY`，绝不替代消失的 T0 原始 Mach-O bytes。

## 组件与发布文件闭合

四个 lane 的互斥 primary ownership 是：

| Lane | 主要范围 | groups | paths | WCH↔OURS byte-diff paths |
|---|---|---:|---:|---:|
| L1 | GCC driver aliases、HOST-ZSTD | 2 | 7 | 5；另 2 个 WCH-only dylib |
| L2 | cc1、cc1plus、lto1 | 3 | 3 | 3 |
| L3 | GAS、objdump 及发布 aliases | 2 | 4 | 4 |
| L4 | ld、其余 binutils、GCC auxiliaries/plugins/SDK | 22 | 602 | 34 |
| 合计 | acceptance gate | 29 | 616 | 46 |

L4 的 602 路径细分为 551 byte-exact、34 byte-diff、16 directories、1 个 `.la` mode-only。HOST-ZSTD 的两个 dylib 在 WCH 存在而 P2/OURS 缺失，所以作为 missing-control package/capability 记录，而不是伪造零长度 interval。别名/hardlink/content duplicate 均保留独立发布路径行并指向 implementation group。

## 宿主 Mach-O 静态闭合边界

所有 46 个 WCH↔OURS byte-different acceptance paths 都有 WCH、P2、matched、OURS 四侧 obligation；共 184 条，均机械证明 `[0, EOF)` 连续覆盖。直接可得的 Mach-O 使用 load commands、segments/sections、signature/UUID、imports/exports/rpath、symbols/function-starts 等划分；T0 OURS 原件已消失的 L4 路径只以冻结 manifest 的 size/hash 建立 whole-file `UNRESOLVED` obligation，明确标为 manifest-bound，而不是从 post-T0 binary 推断。

Region ledger 的 1,818 行分类为：38 `FUNCTIONAL-CODE`、247 `FUNCTIONAL-DATA-TABLE`、340 `LINK-LAYOUT`、158 `PACKAGING/DEPENDENCY`、74 `PADDING/ALIGNMENT`、498 `SIGNATURE/UUID/BUILD-METADATA`、114 `STRIP/DEBUG/SYMBOL-LAYOUT`、349 `UNRESOLVED`。前七类只在相应 lane 有结构/source/control 证据时使用；没有把 stripped WCH 与不同 host build 的所有差异批量标成 noise。

结构 tiling 完整不等于语义闭合。184 obligations 中 172 保持 semantic `UNRESOLVED`，这本身阻止 PASS。尤其 L1 五个 driver、L2 三个 backend、L4 三十四个路径的 host code/data 不能由签名、符号数量或 raw 地址偏移直接解释。L3 的 12 个 WCH/P2/matched as/objdump obligation 有受限的 table/source/probe 分类；四个 T0 OURS side-path 原件不可恢复，仍为 unresolved。

## Canonical 功能与强制 probe

35 个 canonical feature 的最终状态为：

- `COVERED-BYTE-EXACT`：5
- `COVERED-BEHAVIOR-EXACT`：6
- `UPSTREAM-IDENTICAL`：1
- `GAP`：12
- `UNRESOLVED`：11

覆盖项合计 12/35。`COVERED-BEHAVIOR-EXACT` 只用于 `artifact_gate_applicable=false`；`COVERED-BYTE-EXACT` 的所有适用 `.s/.o/.elf/.bin` 字段均为 `EXACT`。独立复核后新增的严格 validator 把 feature candidate/alias 解析到 canonical ID，再检查每个 covered feature 的强制 OURS 行；结果是 0 个 mandatory mismatch/unavailable。

冻结 T0 OURS 的 172 个 mandatory rows 分解为：

| 类别 | 行数 | 说明 |
|---|---:|---|
| exact/baseline | 97 | bounded raw behavior 或 artifact 与 WCH 一致 |
| mismatch | 18 | 8 raw behavior + 8 target-artifact byte + 2 exhaustive decode-row |
| unavailable | 57 | L4 的 T0 OURS 原始 binutils/tool executable 消失后拒绝运行 |

两个 exhaustive decode-row 各为 8,192/65,536 mismatch，总计 16,384/131,072 isolated halfword-mode cells。`OURS-PROVEN-REPLAY` 是额外控制：100 个 mandatory rows 中 84 exact、16 mismatch、0 unavailable；它不改变 canonical T0 denominator。

## 十二个 GAP

下表每行都给出最小触发、四侧结果、静态归因和后续修补面。多个 GAS feature 共享同一“默认 ISA spec 版本导致 mapping/object bytes 不同”根因，但按照冻结的 canonical observable 分别保留；这不是把一个根因误写成多个独立缺陷数。

| Feature | 最小/有界复现 | WCH | UPSTREAM-P2 | UPSTREAM-MATCHED | OURS / replay | 静态根因、排除项与建议修补面 |
|---|---|---|---|---|---|---|
| `L1-FEAT-ZSTD` | `gcc -dumpspecs`; `gcc/as/ld/readelf/objcopy` 对有效 zstd DWARF corpus；两个 dylib | 两个 spec clause；生成/链接/解码/复制成功；dylib 存在 | as/ld/objcopy 失败；readelf 只 warning、无 DWARF decode | 同源构建两 probe=2；直接工具与 WCH exact；四工具 loader-relative import | T0 gcc rc0 但 debug 未压缩；工具缺 zstd；dylib 缺失 | `CONFIGURE/CAPABILITY + PACKAGING/DEPENDENCY`；matched 同源码排除 source patch；显式传播 `ZSTD_*`、链接 BFD consumers、重建 GCC、包装两份 runtime |
| `L3-FEAT-DEFAULT-ISA-SPEC` | 5 个 default profile object + 3 个 `-misa-spec=2.2` controls | 默认 i2p0/a2p0；RV32E e1p9 | 默认 i2p1/a2p1；显式 2.2 对齐 | 同 P2 | replay 默认 i2p1/a2p1；4/5 default object diff；3 controls exact | build/config default；显式 2.2 排除 opcode encoding patch；固定 WCH 的 assembler default ISA spec |
| `L3-FEAT-XW-MAPPING` | bare/explicit XW 与五标签 exhaustive mapping | bare suffix xw2p2，base i2p0/a2p0 | bare XW reject，explicit 使用 current base | 同 P2 | XW suffix 已匹配，完整 symbol 仍为 i2p1/a2p1 | patch 0005 只闭合 XW suffix；需与 default ISA spec 一起修正完整 mapping bytes |
| `L3-FEAT-XW-ASSEMBLY` | 8,704 legal cases × 5 labels | 43,520/43,520 接受，canonical `.text` | 43,520 全拒绝 | 43,520 全拒绝 | `.text` 43,520/43,520 exact；whole `.o` 因 mapping diff | encoding/table 实现已排除；修 default ISA spec 后重跑对象 gate |
| `L3-FEAT-XW-ARCH` | 五标签 × 8,704，加 bounded negatives | 五标签与所有 legal operands 接受 | 全拒绝 | 全拒绝 | 接受面 exact；default object diff | arch registration 正常，失败来自适用 artifact mapping；修 build default 并保持 negatives |
| `L3-FEAT-CUSTOM32` | 20,650 pairwise cases × 5 profiles | 103,250 有界决定；RV32E legal subset 7,162 | 全拒绝 | 全拒绝 | acceptance/text/decode exact；4/5 default objects diff | formula/opcode records 已交叉验证，排除 opaque table；修 base mapping default |
| `L3-FEAT-OPCODE-NAMESPACE` | XW + custom32 exhaustive 和 halfword namespace | 暴露 XW/四 custom32 names | standalone names absent | standalone names absent | namespace/text 基本闭合；对象 mapping 及另列 DCXW collision 失败 | 正常 upstream opcode tables；先修 default mapping 与 DCXW priority，不添加不明助记符 |
| `L3-FEAT-ATTRIBUTES` | default-off、march-attr、explicit literal、sticky controls | policy/acceptance 5/5 | current attributes 或 bare reject | 同 P2 | policy 5/5 exact，但成功对象受 mapping bytes 影响 | attribute rewrite patch 本身已闭合；artifact gate 要求连同 base mapping exact |
| `L3-FEAT-RELAXATION` | default relax 与 `.option norelax` | 2 vs 0 个 `R_RISCV_RELAX` | relocation semantics 同 | 同 P2 | semantics exact；default object mapping diff | 排除 relocation implementation；修 default ISA spec 后比较完整 object |
| `L3-FEAT-DCXW-PRIORITY` | D+C+XW × default/no-aliases × 65,536 halfwords | 两个范围解为 fld/fsd families | 在 collision words 与 WCH 相同，另有独立 custom32 66 words | 同 P2 | 每 mode 恰 8,192 mismatch，输出 `.insn` | OURS source 对 Zcd support 加 `&& !xw` 且 skip XW class；GAS 单独正确拒绝 c.fld，故只修 objdump decoder priority/gating |
| `L3-FEAT-XW-DIAGNOSTICS` | 7 个 missing-C/XW/bounds/norvc/option controls | 原始诊断冻结 | upstream namespace 差异 | content 同 P2；晚跑 raw path 不作 byte comparator | replay 4/7 exact；3 项 illegal operands vs unrecognized opcode | `riscv_ip` predicate/precedence 未闭合；排除单纯绝对路径；以三项最小 negatives 定位并修正常诊断顺序 |
| `L4-FEAT-ELFEDIT-MMAP` | `elfedit` help 与 minimal x86 GNU-property option | help 暴露且 option rc0 | option absent/reject | option absent/reject | T0 unavailable；五补丁 replay absent/reject | `HAVE_MMAP` host configure capability；排除 WCH source patch；匹配 mmap capability 后在 x86 ELF corpus 重测副作用 |

D+C+XW 两个精确 mismatch ranges 为 `0x2000..0x3ffe step 2` 和 `0xa000..0xbffe step 2`，每 mode 合计 8,192。独立 framing 证明每个 16-bit word 不会被相邻 halfword 吞成 32-bit 指令。

## 现有八个 patch 的双向证明

| Patch 面 | WCH↔upstream 差异 | OURS 机制与动态结果 | 负控制 / 最终状态 |
|---|---|---|---|
| GCC XW registration/version/multilib | upstream 不识别 XW，P2 multilib parser 报 10 错 | 正常 `riscv_ext_version_table` 表项；14 march + 22 multilib rows；bounded objects exact | malformed/unknown/XLEN/ABI negatives；canonical XW feature covered |
| GCC `non-standard111` diagnostic | upstream literal 不同 | `riscv_subset_list::add` 的一个诊断 literal；WCH/OURS stderr exact | unknown-X negative；covered |
| GCC `WCH-Interrupt-fast` | P2 warning 并按普通函数降低 | 正常 attribute/frame/save/FCSR/rename 机制；21/21 target artifacts exact | redeclare、近似拼写、不同 frame/优化；covered，但跨 HPE generation 硬件 ABI unresolved |
| GAS XW arch acceptance | P2/matched 全拒绝 exhaustive XW | 正常 arch parser/table；43,520 acceptance/text exact | missing C/XW、norvc、versions；完整 object 因 mapping gap，feature 为 GAP |
| 8 个 XW compressed forms/ordinary aliases | upstream namespace 缺失 | 正常 opcode table；8,704 × 5 encoding stream exact | D/Zcb/option/bounds controls；mapping、diagnostic、DCXW 分别 GAP |
| 4 个 custom32 | P2/matched 103,250 全拒绝 | 正常 opcode/operand formulas；103,250 acceptance/text/decode exact | RV32E/RV64/F5/bounds negatives；whole object mapping GAP |
| WCH attribute policy | upstream synthesis/rewrite 不同 | 正常 attribute policy；5/5 bounded behavior exact | default-off、explicit/sticky controls；whole object mapping GAP |
| bare-XW GAS mapping suffix xw2p2 | upstream bare XW reject/current base | patch 精确闭合 xw suffix | GCC bare-XW attribute xw2p0 与 GAS mapping xw2p2 是不同面；完整 mapping 因 base default GAP |

所有实现都是上游惯用的 MD、target hook、parser 或 opcode/attribute 表逻辑；没有大段裸字节、EVT 特判或不可解释的 binary lookup。

## Backend、LTO 与 ABI

L2 的 primary denominator 是 cc1/cc1plus/lto1 三组、三路径、三份 WCH↔OURS byte-different host Mach-O。最终 driver matrix 有 63 个命名 case、每运行侧 72 个 expected artifact states；WCH 与 OURS 各为 71 present + 1 expected-absent。非 LTO 的 60 个可比 target rows 全部 byte-exact。57 个 direct-cc1 supplementary cases进一步隔离了 P2 driver 的 XW multilib 启动失败；WCH/OURS 为 57/57 exact。

LTO 未闭合：六个 slim-LTO `.o` WCH↔OURS 不同；三个 final ELF 和三个在外部 objcopy 漂移之前生成的 BIN pairs 相同。差异位于 `.gnu.lto_.decls` payload，但尚未完成语义归因，所以 canonical LTO feature 是 `UNRESOLVED 6/13`，不能由相同 final ELF/BIN 抹掉 intermediate `.o` gate。

`WCH-Interrupt-fast` 的 21 个有界 target artifacts exact，覆盖 leaf/nonleaf、GPR/RA、frame、FPR/FCSR、call、属性拼写和多个优化/调试/relax 组合。研究资料同时说明 HPE V2 与 V3/V4/V5 hardware save/storage 不同，而 compiler 没有 QingKe/HPE generation selector；因此只能证明有界编译行为，不能宣称各代芯片 runtime ABI 安全。

## GAS/objdump exhaustive 分母

冻结 T0 的三套初始 executable set 加入 matched/replay controls 后，合并 observations 为：

- XW：4 sets × 5 labels × 8,704 = 174,080 cell-cases。
- custom32：4 sets × 5 profiles × 20,650 = 413,000 cell-cases。
- halfword objdump：4 sets × 4 profiles × 2 modes × 65,536 = 2,097,152 isolated word-cells。
- targeted surface：4 sets × 43 = 172 observations。

每个 exhaustive stream 都记录生成公式、profile/label、input ELF attributes、固定 framing stride、decoded/missing/duplicate counts。XW/custom32 的接受面和 target `.text` 已按公式交叉验证；失败来自完整 `.o` 的 mapping base version，而不是 encoding。硬件 delay 语义没有从 binary pattern 重新猜测：四侧可见行为都是 mnemonic reject、generic `.insn` accept，因此只标 `UPSTREAM-IDENTICAL`。

## Zstd 专项结论

Zstd 是确定的 gate GAP，但不是 WCH 私有 source patch：

1. WCH `-dumpspecs` 同时含 assembler/linker zstd clauses；P2/OURS 只有 linker-side clause。
2. WCH `gcc -g -gz=zstd` 生成 `SHF_COMPRESSED` zstd debug；OURS 返回 rc0 却静默生成未压缩 debug object。
3. WCH as/ld/readelf/objcopy 能生成、消费、解码、解压/重压有效 zstd DWARF；P2/OURS frozen behavior 缺 capability。
4. WCH 包含两份 `libzstd.1.dylib`，OURS 缺失。两份 WCH signed bytes 不同，但去签名 analysis-copy byte-exact，属于签名 metadata，而非两个实现。
5. exact pristine source 加显式 zstd configure/link/package controls 后，matched dumpspecs、direct-tool rc/stdout/stderr 和关键 artifacts 与 WCH 一致。完整 pristine GCC compile 仍被独立的 XW multilib parser 阻塞，所以没有伪造 matched GCC artifact。

因此后续修复面是 build/config/package：钉死 `ZSTD_CFLAGS/ZSTD_LIBS/PKG_CONFIG_*`，把 zstd 链接传播到所有静态-BFD consumers，重建 GCC 让 assembler capability probe 为 2，并以 loader-relative 方式包装两份 dylib。`Supported LTO compression algorithms: zlib` 在所有检查侧一致，它与 ELF debug zstd 是不同能力。

## Errata → GCC 专项

机械 source census 覆盖了 06c 的 12 个 runtime rows、14 个 document rows，以及 custom/processor/06b 路由出的 24 个相关 leads，共 50 source rows；去重为 44 个 semantic IDs。最终分类：

| 分类 | 数量 |
|---|---:|
| `NO-GCC-EVIDENCE` | 26 |
| `HARDWARE/DOCUMENT-ONLY` | 12 |
| `GCC-FEATURE-NOT-ERRATUM` | 3 |
| `BINUTILS-ONLY` | 2 |
| `UNRESOLVED` | 1 |
| 其他允许分类 | 0 |

没有一项达到 `GCC-ERRATUM-FIX-CONFIRMED` 或 `GCC-WORKAROUND-CANDIDATE` 的三重证据门槛。WCH/P2/OURS 在不手写 workaround 的 bounded clean-C O0/O2/Os 与 O2 GIMPLE/asm 中没有出现 finding-specific selector、barrier、delay、reset sequence、atomic lowering 或额外保存。06c 的实际动作位于 SDK source 或硬件文档；本地资料的原始强度仍是 9 个 workaround candidates + 3 个 compatibility rows，不能升级为已确认 silicon 因果。文档化 H417 lot 条件仍只分类为 hardware/document。

三项 `GCC-FEATURE-NOT-ERRATUM` 是 XW、fast interrupt 和普通 LR/SC lowering；两项 `BINUTILS-ONLY` 是 custom CSR/delay 的工具可见接受面。唯一 unresolved 是 vector nested-interrupt/calling ABI。结论是“当前 44 项有界证据中未确认 WCH GCC 自动 errata 修复”，不是“证明绝对不存在”。每个 finding 的 MCU/revision/lot、强度、workaround locus、static search、clean input、四侧行为、证据和未覆盖条件见机器表。

## Negative-space 与候选闭合

冻结 source census 初始 31 行，四 lane 追加 50 行，最终 81 个 stable candidates；81/81 映射到唯一 canonical feature 或明确 nonfunctional ledger ID，4 个跨 lane aliases 保留。静态候选表另有 36 个 bounded leads。搜索面包括 option/help、diagnostic、extension/attribute/spec/opcode/emulation、imports/dylibs/plugins、WCH↔upstream、OURS↔WCH 和标准 RV32 negatives。

新发现的功能差异没有被挤出分母：zstd、default ISA spec mapping、D+C+XW decoder priority 和 elfedit mmap capability 均成为 canonical GAP。host signature/UUID/build metadata、绝对安装路径和 package-only 文件只进入相应 nonfunctional/binary/component ledger。身份面在独立复核后降为 unresolved：`gcc -v` 的唯一 mandatory raw comparison 因 `COLLECT_GCC/COLLECT_LTO_WRAPPER` 嵌入各自 invocation/install root 而不同；规则禁止 normalize，且没有同一 absolute executable pathname 的顺序控制，所以不能继续声称 covered。

## Immutable pre/post 与正式 INVALID 原因

Pre/post 共 23 个 Git/symlink snapshot rows：12 exact、11 drift。GCC 七项全部 exact；`/Users/mrs/riscv-gnu-toolchain` link text 不变并指向仓库 `tmp/`。以下 immutable scopes 漂移：

- root HEAD `9930eb90043c53f5cd5ec6419b083a4e74ffb4a3` → `db9bed6d6beb253dd7bea7cdd4fa8b0e51eb77f7`，root index/worktree/status/tracked/untracked snapshots也变化；
- binutils HEAD `258634dda7ce7b529231c57474372ecc4aca3408` → `169c561ddd844aeab247940f49ada09c8e6d6f50`，index tree `61232555…` → `918ab266…`，series 从五项增长为六项且原五 patch/README 被改写；
- active binutils output 有 27/3,177 frozen manifest rows漂移；
- `tmp/golden/toolchain-current` 从 frozen Darwin OURS output 改指 `ref/gcc/linux-amd64/15.2.0`。

这些时间戳和 source/output变化来自另一个并发 Phase3b 工作流。Phase 3c 在发现后停止读取 active binutils aliases，没有把六补丁结果吸收为 OURS，也没有回滚他人的工作。原因归属不改变 prompt 的 immutable 判定，因此正式 verdict 必须是 `INVALID`。

## 独立终审与账本修正

四个主 lane 均由 `gpt-5.6-sol`、reasoning `ultra` 执行；runtime self-reported identity 为 `Codex/GPT-5 family`，deployment hash 未暴露，报告未虚构 hash。四份报告 SHA-256 分别为：driver `18b0cb85857c0bb17090ed5e7dec3b8a831e384808814b4144ab822c8b8cafea`、backend `701b4976b714c7a7fc5e7635a77fb6a37ebd0229b3ac5e7c6dccc60a6e269131`、gas `e9b72d03109af478bb8a7c0537535b7cd7bd277f11225467e4126a1ef2f6bde4`、ld-tools `980ba2d190f4477fe5ac18a1e981a2bd8d8b4162bf311ae7379d09dff54e5ff7`。

第一名独立 reviewer 在完成结构复算和原始抽查后耗尽运行额度，未能写正式报告，但发现三类 overclaim；协调层没有忽略它们：

1. `L1-FEAT-IDENTITY` 的 mandatory `gcc -v` 是 raw behavior diff，状态从 covered 5/5 降为 `UNRESOLVED 0/1`。
2. 四侧 `ID-DUMPSPECS` 从 covered routing 重新归到 zstd GAP，zstd denominator 从 11 改为 12。
3. 八个 D+C+XW halfword/profile rows 从 covered generic halfword feature 重新归到 dedicated DCXW GAP。

修正记录在 `reviewer-corrections.tsv`。修正后的 frozen-v2 manifest 有 33 个输入，manifest SHA-256 `1a1da2586df4e38bb20273d1fc0bcc4c04e727bdf8b4c4004f546f6f7d7c8f41`。一名未参与主分析的新 reviewer 对 v2 重新做 component、region、feature、errata、zstd、unresolved 和 raw-sample 复算；其最终结论、独立数字和任何残留 finding 以 `tmp/phase3c-evidence/agents/reviewer-final/REPORT.md` 为准。

终审给出的限定保留如下：81/81 指 76 个映射到 35 个 canonical features、5 个映射到 nonfunctional final targets，不是 81 个 canonical features；184 个 canonical obligations 对应 1,581 个 region rows，另有 237 rows/6 file-sides 是 supplemental controls；“covered feature 没有强制失败”严格指 52 个可直接解析到 covered canonical feature 的 OURS mandatory rows，另 29 个 `feature_candidate_id=-` 的 backend mandatory rows虽均 byte-equal，但不被静默算作 direct mapping。46 个 matched obligation 的正式 `manifest_size/manifest_sha256` 列为 `-`，值被编码在 `manifest_status`，可复算但 schema 不规整。L2 lane 报告早于 late-matched merge，其“matched 无 interval rows”已被最终三条 matched whole-file obligations取代；L1 的 24 primary sides 包含四个 zstd supplemental sides，canonical differing-Mach-O denominator 仍是 20。原 strict validator command 没有声明 input/output hash；新的 independent v2 复算恢复了数字可信度，但不消除原 provenance 弱点。

## 命令与证据质量

所有正式证据生成/变换通过 `tmp/phase3c-evidence/scripts/phase3c-run.sh`，command ledger 记录 argv、cwd、environment delta、input/output hashes、时间、rc 和完整 stdout/stderr 路径。非零命令没有删除：expected difference/negative search、control construction、caller quoting/path、preclosure 和 drift detections逐行进入 `command-quality.tsv`；被更正的命令只由后续明确 evidence ID 取代，不把失败当成功。

早期 lane 探索存在少量 wrapper 定位前的只读 session log；L1 曾误写 `/tmp/phase3c-driver-prewrapper.txt`，随后由 audited wrapper 精确 unlink，最终证明该路径不存在。没有递归删除或恢复用户数据。几个 stale wrapper prehash 和 optional disassembly process tree 在 PID/command/elapsed 审计后只对精确 PID 发 TERM；所有 required evidence 已先完成。

## 未解决项和后续顺序

21 个 unresolved ledger rows 的主要阻塞簇是：172 个 host-Mach-O semantic obligations；冻结 T0 binutils 原件消失导致 L4 57 个 mandatory probe unavailable；slim-LTO serialization；HPE generations 和 vector ABI；GCC implicit QingKe tuning negative-space；matched backend late/not-run；raw diagnostic/identity path comparability；以及 immutable external drift。

建议严格按下列顺序开启新阶段，而不是在本阶段修改 patch：

1. 建立单写者、不可变的五补丁 OURS snapshot，恢复/重新生成精确 provenance，并重新冻结 prestate。
2. 修 build/config/package 的 zstd 与 GAS default ISA spec；重建后先跑最小 GAP matrix。
3. 修 objdump D+C+XW priority 和三项 XW diagnostics，保持 GAS 的正确 c.fld reject 行为。
4. 匹配 elfedit mmap capability。
5. 在同一 absolute work/path 条件复测 identity；解析 slim-LTO stream；如 gate 仍要求，再做 feature-directed host function/table attribution。
6. 重跑 35-feature mandatory matrix、46-path four-side interval/semantic ledger 和全 EVT byte gate；在无 GAP、UNRESOLVED、NOT-RUN、mismatch 且 immutable PASS 前不得宣称完成。

## 交付物与证据入口

- 主报告：`analysis/toolchain/phase3c-wch-deep-diff.md`
- 功能表：`analysis/toolchain/phase3c-feature-coverage.tsv`
- binary region 表：`analysis/toolchain/phase3c-binary-difference-ledger.tsv`
- errata 表：`analysis/toolchain/phase3c-errata-gcc-audit.tsv`
- 组件 inventory：`analysis/toolchain/phase3c-component-inventory.tsv`
- 全量 raw/机器证据：`tmp/phase3c-evidence/`
- 四 lane 报告：`tmp/phase3c-evidence/agents/{driver,backend,gas,ld-tools}/REPORT.md`
- 独立终审：`tmp/phase3c-evidence/agents/reviewer-final/REPORT.md`
- 核心闭合表：`binary-coverage-obligations.tsv`、`feature-universe.tsv`、`probe-results.tsv`、`unresolved.tsv`、`mismatch-summary.tsv`、`poststate-verdict.tsv`

最终五件公开交付物的 SHA-256/size 由 `analysis/toolchain/phase3c-deliverables.sha256` 记录；报告自身不嵌入自引用 hash。
