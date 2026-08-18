# MRS 2.4.0 / 2.5.0 工具链与 runtime 差异研究

研究日期：2026-08-03；第二轮独立复核：2026-08-04（Asia/Tokyo）
仓库根：`/Users/apple/Projects/gccriscv-wch`
主提示：[research-mrs-version-diff-prompt.md](/Users/apple/Projects/gccriscv-wch/research-mrs-version-diff-prompt.md)
第二轮审计与需求—证据矩阵：[round2-review.md](/Users/apple/Projects/gccriscv-wch/mrs-version-diff/round2-review.md)

## 1. 执行摘要

### 1.1 A/B/C 计数口径

这里的“N 条”按带稳定 ID 的差异事项计，不把每一个 SHA 行都当成一条结论；文件级数量另列。第二轮已修正第一轮候选归因，每条结论均受本报告范围限制。

| 类别 | 条数 | 事项 |
|---|---:|---|
| A：两侧组件都存在且内容不同 | 3 | A1：492 个 Toolchain 文件重新签名；A2：GCC15 GDB 真内容/依赖变化；A3：OpenOCD package/binary 更新 |
| B：单侧出现、由抽取范围造成 | 5 | B1–B5：`manifest.json`、`SDK/default`、`Others/CommunicationLib`、`Others/Firmware_Link`、`Others/IQMath` |
| C：证据不足或无法归因 | 3 | C1：8 个 app-only `libwchriscvnn.a`；C2：3 个 `.DS_Store`；C3：GDB/OpenOCD 已观测变化之外的源码级差异缺构建材料 |

【实测】文件级核对数字仍为：Toolchain `same=18842,different=493,only_24=1,only_25=8`；仓库 2.5 抽取与 app 对应子集为 `same=11033,different=0,only_25=8310`；OpenOCD 为 `same=1795,different=3,only_24=2`。[tree-compare-counts.json](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/tree-compare-counts.json) 第二轮逐个复核 493 个 raw-SHA 差异：492 个 CodeDirectory 哈希相同而签名时间不同，唯一 signed content 真正不同的是 GCC15 `gdb`。[codesign summary](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/codesign-all-toolchain-differences-summary.json)

### 1.2 最重要的三条

1. 【实测】493 个共同 Toolchain raw-SHA 差异并非 493 个功能变化：492 个是相同 signed content 的重新签名；唯一真 binary 变化是 GCC15 GDB。两侧都内嵌 GDB 17.1，但 2.4 硬编码两个不存在的 `/Users/mrs/...` GMP/MPFR 依赖，2.5 去掉它们并可运行。[逐文件签名表](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/codesign-all-toolchain-differences.tsv)、[GDB static](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/behavior/gcc15-gdb-static-summary.tsv)
2. 【实测】四套 GCC 的 40 对默认配置输出相同；真实 compile+link fixture 都拉入 `libgcc`，成对 object、ELF、raw binary 逐字节相同，map/trace/symbols 也相同。[reported behavior](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/behavior/reported-behavior-summary.tsv)、[full link](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/behavior/full-link-summary.tsv)
3. 【实测】OpenOCD 是确认的版本与可搬移依赖更新：包版本 `v2.8 → v2.10`，内嵌 build 日期 2026-02-28 → 2026-06-17，`hidapi` 从 Homebrew 绝对路径改为 app 内 loader-relative 路径；`wch-riscv.cfg` 等配置脚本仍相同。[OpenOCD static](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/behavior/openocd-static-summary.tsv)、[文件比较](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/openocd-24-vs-25app.tsv)

【XW 单独结论】三套 assembler 的 CodeDirectory 内容相同；第二轮每套各汇编 8,704 条合法交互组合（总计每侧 26,112 条），对象和 17,408-byte `.text` 成对逐字节相同。在“随包 assembler + 第一轮语料 + 第二轮交叉乘积”范围内未发现 2.5 XW parser/编码支持变化；不外推为硬件语义或所有可能名称的无界证明。[xw cross-product](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/behavior/xw-cross-product-summary.tsv)

## 2. 范围与对等性说明（先于逐问结论）

### 2.1 三份实物

【文档】研究提示明确要求将三份材料视为不对等：

| 标签 | 实物 | 本次实际核对到的范围 |
|---|---|---|
| `mrs24` | `MRS_Toolchain_MAC_V240/` | `Toolchain`、`OpenOCD`；没有本机可用的完整 2.4 app/package |
| `mrs25_app` | `"/Users/apple/Projects/MounRiver Studio 2.app/Contents/Resources/app/resources/darwin/components/WCH/"` | `manifest.json`、ARM/GCC8/GCC12/GCC15、OpenOCD、SDK/default、Others 三个组件 |
| `mrs25_extract` | `tmp/mrs-2.5/WCH/Toolchain/` | 只有 GCC8/GCC12；没有 GCC15、ARM、OpenOCD、SDK/Others |

【实测】组件文件数与字节数见 [component-summary.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/component-summary.tsv)。核心摘要如下：

| 组件 | 2.4 仓库材料 | 2.5 app |
|---|---:|---:|
| Toolchain | 19336 files / 3123998432 bytes | 19343 / 3127382180 |
| OpenOCD | 1800 / 8899782 | 1798 / 8904551 |
| `manifest.json` | 0 | 1 / 677 bytes |
| `SDK/default` | 0 | 323 / 80556842 |
| `Others/CommunicationLib` | 0 | 8 / 455202 |
| `Others/Firmware_Link` | 0 | 13 / 669658 |
| `Others/IQMath` | 0 | 3 / 408737 |

【实测】原始 2.5 包 `/Users/apple/Projects/MounRiver_Studio_MacOS_ARM64_V2.5.0.tar` 存在。第二轮直接流式读取 tar，与安装 app 的 WCH 根核对：21,466 个普通文件、1,971 个目录、24 个 symlink 的内容、mode、link text 和路径均对应；忽略 11,627 个 macOS AppleDouble `._*` 元数据条目后，missing/content/link/mode/app-only 计数全部为 0。[tar-app-summary.json](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/tar-app-summary.json)、[空 mismatch 表](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/tar-app-mismatches.tsv)

【实测】第二轮以 `find -maxdepth 5` 再次检索 `/Users/apple/Projects` 与 `/Applications`；在该路径/深度/名称模式范围内只找到 2.4 抽取与既有 TSV，没有完整 2.4 app/package。[source-search-v24.txt](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/source-search-v24.txt) 因此 2.5 app 独有组件只能归 B，不能写成“2.5 新增”。

### 2.2 仓库 2.5 抽取与 app 的一致性

【实测】对 `mrs25_extract` 与 `mrs25_app` 的 GCC8/GCC12 对应目录做逐个普通文件/符号链接 SHA-256 比较，11033 个共同路径均为 `same`，没有 `different`、`only_24`；差异计数中的 8310 个 `only_25` 来自抽取缺少 GCC15/ARM 等范围，不是共同子集的内容差异。[tree-compare-counts.json](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/tree-compare-counts.json)

【实测】第二轮不复用上述 Python 哈希器，另以 `/usr/bin/diff -rq` 比 GCC8/GCC12 对应目录，两个比较均 return code 0、0 differ/only，独立复现共同子集一致性。[external-diff-summary.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/external-diff-summary.tsv)

【推断】因此此前基于仓库 2.5 GCC8/GCC12 副本作出的分析，在这两个对应 app 子集内仍可复现；它不能外推到 app 才有的 GCC15、ARM、OpenOCD、SDK 或 Others。

## 3. 问题 1：工具链二进制

### 3.1 全树与重点二进制计数

【实测】第一轮普通文件/符号链接清单记录 493 个共同 Toolchain 普通文件 raw SHA 不同；第二轮对这 493 个文件逐个读取 Mach-O CodeDirectory：

| 工具链 | 同 signed content、异签名 blob | signed content 真不同 |
|---|---:|---:|
| GCC8 | 139 | 0 |
| GCC12 | 147 | 0 |
| GCC15 | 54 | 1 |
| ARM | 152 | 0 |
| 合计 | 492 | 1 |

【实测】492 个文件的 `CandidateCDHashFull` 成对相同，2.4/2.5 签名时间成对不同；代表性 `as`/dylib 复制件执行 `codesign --remove-signature` 后 SHA 相同。唯一真内容差异是 `RISC-V Embedded GCC15/bin/riscv32-wch-elf-gdb`。[逐文件签名表](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/codesign-all-toolchain-differences.tsv)、[剥签样本](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/signature-strip-samples.tsv)

【实测】外部 `diff -rq` 显示 514 条 differ，是因为它解引用并重复报告 21 个 link text 相同的 symlink 目标；扣除 1+7+3+10 个 alias 后，四工具链恰为 139+147+55+152=493。[symlink reconciliation](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/external-diff-symlink-reconciliation.tsv)

【结论，A1】不能再把 raw-SHA 不同的 92 个 compiler/binutils 路径描述成 92 个未解释的工具功能变化；它们属于上述 492 个重新签名文件的子集。签名 blob 是实际包装字节差异，但 CodeDirectory 所覆盖的 executable code/data 未变。

### 3.2 版本与内建配置

【实测】重新执行两侧版本命令后，三个 RISC-V GCC 版本串分别为：

| 工具链 | 2.4 / 2.5 app 实测版本 |
|---|---|
| GCC8 | `riscv-none-embed-gcc ... x86_64 8.2.0` |
| GCC12 | `riscv-wch-elf-gcc ... arm64 12.2.0` |
| GCC15 | `riscv32-wch-elf-gcc (g5115c7e44-dirty) 15.2.0` |

【实测】GCC8/12/15 的 `gcc -v` 输出在替换两侧安装根路径后，完整输出及 `Target`、`Configured with`、`Thread model`、`gcc version` 关键行均相同；`as --version`/`ld --version` 的版本也在成对工具中相同：GCC8 binutils 2.32、GCC12 2.38、GCC15 2.45。[normalized-gcc-v.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/normalized-gcc-v.tsv)、各版本原始 [gcc-v 输出](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/)

【实测】第二轮进一步比较四套 GCC 的 built-in specs、target options、默认 driver、search dirs/sysroot/library resolution、assembler target help 和默认 linker script，共 40 对命令；规范化安装根及路径引号后全部 return code 0 且输出相同。[reported-behavior-summary.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/behavior/reported-behavior-summary.tsv)

【结论】GCC/assembler/linker 的 raw SHA 差异已归因为签名层，不再保留“可能是编译器优化或源码提交”的开放归因；GCC15 GDB 例外并单列 A2。

### 3.3 GCC15 的单独核对

【实测】GCC15 在 2.4 与 2.5 app 中均存在，不能与 `mrs25_extract` 缺 GCC15 混为版本差异。其 compiler/assembler/linker signed content 与行为保持一致；但 GDB 大小由 8,118,912 变为 8,473,840 bytes，CodeDirectory/UUID 不同。两侧静态版本 token 都是 17.1；2.4 GDB 依赖不存在的 `/Users/mrs/needlib/outm/lib/libmpfr.6.dylib` 与 `/Users/mrs/needlib/outg/lib/libgmp.10.dylib`，2.5 不再依赖它们并可输出 `GNU gdb (GDB) 17.1`。[GDB static](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/behavior/gcc15-gdb-static-summary.tsv)、[dependencies](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/behavior/gcc15-gdb-dependencies-v24.txt)、[2.5 runtime](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/behavior/gcc15-gdb-version-app.txt)

【结论，A2】这是确认的宿主调试器包装/内容修复；它不参与目标编译和链接，不能用来声称 GCC15 目标代码生成改变。缺源码/build log，依赖修复以外的内部变化保留 C3。

## 4. 问题 2：multilib 集合

【实测】两侧 `gcc -print-multi-lib` 的行数如下，且对应集合差文件为空（只有表头）：

| 工具链 | 2.4 | 2.5 app | 其中含 xw 的行 |
|---|---:|---:|---:|
| GCC8 | 23 | 23 | 3 |
| GCC12 | 43 | 43 | 7 |
| GCC15 | 22 | 22 | 10 |
| ARM | 22 | 22 | 未作为 XW 统计 |

【实测】GCC8 使用 `rv32imacxw` 一类无下划线拼写；GCC12 使用 `rv32imac_xw` 一类拼写；GCC15 的集合同时包含 `_xw` 变体与 4 个包含 `zve`/向量相关扩展的行。上述每一行在 2.4 与 2.5 app 的选项字符串相同；本次输出中没有出现 Zc multilib 行。[multilib.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/multilib.tsv)、[multilib-diff.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/multilib-diff.tsv)

【实测】为避免阴性只依赖同一个 `-print-multi-lib` 接口，第二轮直接从四套工具链文件系统枚举 `libgcc.a`、`libc.a`、`libg.a`、`libm.a`、`libnosys.a`、`libstdc++.a` 和 `crt0.o`。605 个选定相对路径的文件内容与 mode 成对相同，0 different/only；这独立支持已安装 multilib runtime 没有增删。[runtime-filesystem-summary.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/behavior/runtime-filesystem-summary.tsv)

【结论，A 类范围内未发现】在四套共同可比工具链的 `-print-multi-lib` 集合中，未发现 2.5 新增/删除的 XW、向量或其他标准扩展变体；这是受限于该命令输出的阴性结论，不覆盖工具链未列为 multilib 的手工 `-march` 组合。

## 5. 问题 3：XW 与自定义指令

### 5.1 已知八条 XW 指令

【实测】对 GCC8/GCC12/GCC15 的两侧 assembler 分别汇编：`c.lbu`、`c.lhu`、`c.sb`、`c.sh` 与四条 SP 形式。8 条均接受，编码两侧逐字节相同：

| 助记符 | 编码 |
|---|---|
| `c.lbu` | `2188` |
| `c.lhu` | `218a` |
| `c.sb` | `a188` |
| `c.sh` | `a18a` |
| `c.lbusp` | `8008` |
| `c.lhusp` | `8028` |
| `c.sbsp` | `8048` |
| `c.shsp` | `8068` |

`objdump` 对这些对象显示为 `.2byte`，不是命名别名；因此证据是 assembler 接受与对象字节相同，不是反汇编器提供助记符打印。[xw-known.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/xw-known.tsv)

### 5.2 操作数边界、版本标签和助记符扫描

【实测】边界语料覆盖紧凑寄存器、SP 寄存器、字节/半字立即数边界；2.4 与 2.5 app 在 GCC8/12/15 的每个测试形式接受/拒绝结果相同。[xw-operand-boundaries.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/xw-operand-boundaries.tsv)

【实测】第二轮新增交叉乘积语料，不只逐维测边界：`c.lbu/c.sb` 覆盖 8×8×32，`c.lhu/c.sh` 覆盖 8×8×32 个合法偶数 offset，四个 SP form 覆盖各 8×16，共每套 assembler 8,704 条。GCC8/GCC12/GCC15 两侧全部汇编成功，每份 `.text` 恰 17,408 bytes，对象与 raw `.text` 成对逐字节相同。[xw-cross-product-summary.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/behavior/xw-cross-product-summary.tsv)

【实测】测试的 `rv32imacxw`、`rv32imac_xw`、`xw1p0`、`xw2p0`、`xw2p2`、`xw3p0` 拼写（有/无下划线的适用形式）在两侧均被接受。[xw-profile-acceptance.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/xw-profile-acceptance.tsv)

【推断】这支持“版本号在本测试中是可接受的架构标签/透传标签”这一局部判断；它不证明某个硬件实现了 `xw2p2` 的全部语义，也不证明未测试的版本标签或拼写。

【实测】对 assembler 字符串的兴趣词扫描、已知 XW 相关错误输出和有限助记符探测，没有发现 2.5 app 相对 2.4 新增的 XW 命名指令；完整字符串摘录见 [assembler-interesting-strings.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/assembler-interesting-strings.tsv)。

### 5.3 五个 XW 压缩槽位的码点扫描

【实测】按提示指定的五个槽位（象限 0 的 funct3=001/100/101，象限 2 的 funct3=001/101）逐一生成全部 11-bit 可变字段，共每个工具链/材料侧 10240 个 16-bit 码点；两侧 GCC8/GCC12/GCC15 的 `.2byte` 汇编均返回 0，规范化 objdump 输出在每个槽位均相同。[xw-slot-scan.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/xw-slot-scan.tsv)、[xw-slot-scan-comparison.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/xw-slot-scan-comparison.tsv)

【实测】GCC8 每个槽位输出 2048 行，GCC12/GCC15 每个槽位输出 1024 行，是 objdump 将相邻 16-bit 数据组合为 32-bit `.word` 的显示差异；不是输入码点数量差异。每侧每个槽位的原始 assembler/objdump 命令和输出分别保存在 `tmp/mrs-diff/raw/xw-slot-*-as.txt` 与 `xw-slot-*-objdump.txt`。

【限制】`.2byte` 是原始数据伪指令，会绕过命名 opcode parser；因此槽位扫描只能解释为解码显示比较，不能把每个码点的 `.2byte` 接受解释成命名助记符。第二轮不再试图证明无界的“所有可能名称都不存在”，而以三套 `as` 的 CodeDirectory 内容成对相同、`as --target-help` 相同、第一轮命名语料相同和 8,704 条交叉乘积相同回答版本比较问题。[codesign table](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/codesign-all-toolchain-differences.tsv)、[reported behavior](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/behavior/reported-behavior-summary.tsv)

### 5.4 32 位自定义指令与 custom opcode 空间

【实测】两侧结果一致，但代际不同：

| 工具链 | `mcpy`/`wexti`/`mrslu`/`mrsl` | `dly`/`delay` |
|---|---|---|
| GCC8 | 全部不识别 | 不识别 |
| GCC12 | 四条均接受，编码分别为 `60b5700f`、`00c5850b`、`04c5850b`、`06c5850b` | 不识别 |
| GCC15 | 四条均接受，编码与 GCC12 相同 | 不识别 |

这里的 GCC8 与 GCC12/15 差异在 2.4 和 2.5 两侧都存在，不能归为 MRS 2.5 改动。[custom-instructions.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/custom-instructions.tsv)

【实测】generic `.insn r` 语料对 `0x0b/0x2b/0x5b/0x7b/0x0f` 五个 custom opcode 空间、各 `funct3=0..7`，两侧均返回成功；这是机器码编码入口测试，不是命名指令或硬件语义证明。[custom-opcode-space-mrs24-GCC12.summary](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/custom-opcode-space-mrs24-GCC12.summary)、[custom-opcode-space-mrs25_app-GCC12.summary](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/custom-opcode-space-mrs25_app-GCC12.summary)

【结论，受限命题】在“随包 GCC8/GCC12/GCC15 assembler 本体、8 条已知 XW、边界与交叉乘积、测试过的架构标签、4 条命名自定义指令、5 个 generic custom opcode 空间”范围内，未发现 2.5 XW parser 或编码支持变化。该比较阴性不再单列 C；仍未覆盖硬件语义或未交付的其他 assembler/plugin。

## 6. 问题 4：runtime 库

### 6.1 Newlib/Picolibc、libgcc/libstdc++

【实测】共同可比工具链的版本头文件和 SHA 如下；2.4/2.5 app 成对值相同：

| 工具链 | 头文件中观测版本 |
|---|---|
| GCC8 | Newlib `3.0.0` |
| GCC12 | Newlib `4.2.0`；Picolibc `1.8.6`（头文件同时带 `_NEWLIB_VERSION 4.1.0`） |
| GCC15 | Newlib `4.5.0` |
| ARM | Newlib `3.3.0` |

逐文件的 SHA 和相关宏见 [runtime-version-headers.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/runtime-version-headers.tsv)。

【实测】在 2.4 与 2.5 app 的共同 multilib 路径中，`libgcc/libstdc++` 181 个对象全部 `same`；WCH 专有筛选（`libIQMath*`、`libprintf*`、`libshlib`、`libshflib`）147 个全部 `same`；没有该筛选集合的 `different` 或 `only_24/only_25`。[runtime-library-comparisons.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/runtime-library-comparisons.tsv)

【实测】第二轮另用外部 `/usr/bin/cmp -s` 检查筛选到的 416 个共同 `libgcc/libstdc++`、libc 与 WCH archive，结果同样是 416 same、0 different/only；避免只依赖第一轮 SHA 实现。[runtime-external-cmp-summary.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/runtime-external-cmp-summary.tsv)

### 6.2 GCC15 的 `libwchriscvnn.a` 边界

【实测】Toolchain 全树中有 8 个 `libwchriscvnn.a` 只在 2.5 app 展开目录出现；其完整路径、大小和 SHA 在 [runtime-library-comparisons.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/runtime-library-comparisons.tsv)。进一步检查显示两侧 GCC15 `riscv32-wch-elf/lib.zip` SHA 都是 `87315e2f2849f9d469cd9474cd23f98bfbf1d942c37fb850f58a11ae69160aeb`，均有 625 个成员、成员元数据相同，且两份 zip 都没有 `libwchriscvnn` 成员。[followup-gcc15-libzip.txt](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/followup-gcc15-libzip.txt)

【实测】第二轮外部 `diff -rq` 独立列出恰好 8 条 app-only，且八条文件名均为 `libwchriscvnn.a`。[diff-rq-v24-vs-app-GCC15.txt](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/diff-rq-v24-vs-app-GCC15.txt)

【推断】这 8 个文件更像是某一侧的额外展开/打包阶段产物；因为没有 2.4 完整应用与同路径的对照，不能将其写成 2.5 的功能新增，列为 C。

### 6.3 `Others/IQMath` 与 Toolchain 内库

【实测】2.5 app 的 `Others/IQMath/default/IQmath_RV32.zip` 包含 header 和 EC/ECXW/IMAC/IMACXW 四个库。四个库与 GCC8 Toolchain 内对应 multilib 库 SHA 完全对应（IMAC 仅文件名大小写不同）：

| zip 变体 | Toolchain 相对路径 | 关系 |
|---|---|---|
| EC | `rv32ec/ilp32e/libIQMath_RV32.a` | SHA 相同 |
| ECXW | `rv32ecxw/ilp32e/libIQMath_RV32.a` | SHA 相同 |
| IMAC | `rv32imac/ilp32/libIQMath_RV32.a` | SHA 相同 |
| IMACXW | `rv32imacxw/ilp32/libIQMath_RV32.a` | SHA 相同 |

证据表：[iqmath-relationship.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/iqmath-relationship.tsv)；中间解包、`ar -t`、`objdump -dr` 输出保存在 `tmp/mrs-diff/probes/iqmath-other/` 与 [iqmath-other-objdump.txt](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/iqmath-other-objdump.txt)。

【结论，B 类】`Others/IQMath` 是独立打包组件，但本次可抽出的四个库不是一套新 SHA 的独立实现；2.4 侧没有对应路径，不能判断它是否在完整 2.4 产品中存在。

## 7. 问题 5：头文件、specs、链接脚本

【实测】2.4 与 2.5 app 的共同路径比较结果为：

| 分类 | 共同路径且相同 | 不同 |
|---|---:|---:|
| `include/header` | 8172 | 0 |
| `*.specs` | 478 | 0 |
| 默认链接脚本/`ldscripts` | 183 | 0 |

完整逐文件 SHA 在 [headers-specs-scripts.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/headers-specs-scripts.tsv)。

【结论】在这三个共同文件集合中没有观测到会直接改变 include、specs 或链接脚本选择的 2.5 差异；不扩展到 2.4 缺失的 SDK/Others 或未比较的完整安装包。

## 8. 问题 6：OpenOCD 与其余组件

### 8.1 OpenOCD（A 类）

【实测】两侧 OpenOCD 树有 1795 个相同文件、3 个共同路径内容不同、2 个只在 2.4 出现的 `.DS_Store`。3 个共同差异是 `OpenOCD/bin/openocd`、`OpenOCD/version.txt`、`OpenOCD/sub_manifest.json`；`OpenOCD/bin/wch-riscv.cfg` 及其他配置脚本在本次比较中相同。[openocd-24-vs-25app.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/openocd-24-vs-25app.tsv)

【实测】2.4 `openocd --version` 在当前 macOS 上因缺少 `/opt/homebrew/opt/hidapi/lib/libhidapi.0.dylib` 以 return code `-6` 退出；2.5 app binary 成功运行。第二轮不执行失败 binary，改由 `strings` 静态确认两侧内嵌 banner 分别为 `Open On-Chip Debugger 0.11.0+dev-snapshot (2026-02-28-11:34)` 与 `(2026-06-17-15:30)`，内嵌 build roots 分别为 `mrs2.4`/`mrs2.5`。[openocd-static-summary.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/behavior/openocd-static-summary.tsv)

【实测】文本 package 版本为 2.4 `v2.8`、2.5 `v2.10`。`otool -L` 还显示 2.5 将 `hidapi` 改为 `@loader_path/../../../Others/CommunicationLib/default/libhidapi.0.dylib`；这是相对 app 的可搬移依赖，而 2.4 是 Homebrew 绝对路径。[2.4 dependencies](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/behavior/openocd-v24-dependencies.txt)、[2.5 dependencies](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/behavior/openocd-app-dependencies.txt)

【结论，A3】OpenOCD package/binary 与 host dependency 是确认的版本更新；共同 cfg/scripts 没变，因此在这些配置文件范围内未观察到新增目标。缺对应源码/build log，binary 内部除已观测 metadata/dependency 外的变化保留 C3。

### 8.2 SDK 与 Others（B 类）

【实测】2.5 app 的 `SDK/default` 是 323 个文件，含 `.json`、`.png`、`.svd`、`.tflite`、`.txt`、`.zip`；`CommunicationLib` 含 8 个文件且含 dylib，`Firmware_Link` 含 13 个文件且含 `.bin`，`IQMath` 含 3 个文件且含 zip/manifest/version。[component-summary.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/component-summary.tsv)、[manifest-25-app.json](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/manifest-25-app.json)

【结论，B 类】由于 2.4 实物是只含 Toolchain/OpenOCD 的抽取，不能把这些 app-only 组件写成 2.5 相对完整 2.4 的新增或回归；它们只能说明当前 2.5 app 材料提供了这些可选资源。

## 9. 问题 7：对使用者的意义

### 9.1 同一源码的产物

【实测】用成对工具链、同一 `mrs_fixture.c`、相同 `-march`/`-mabi` 和编译选项做 compile-only 测试，GCC8/GCC12/GCC15 三组两侧均返回 0；对象 SHA 与汇编 SHA 均相同。GCC8/GCC12 的 `mrs25_extract` 与 app 也相同。[compile-fixture.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/compile-fixture.tsv)、[mrs_fixture.c](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/probes/compile/mrs_fixture.c)

【实测】第二轮补做完整 compile+link：GCC8/GCC12/GCC15/ARM 使用固定 freestanding 源码、相同 target flags、默认 linker script/默认库组并强制 64-bit 除法拉入 `libgcc`。四组两侧都成功，分别出现 `__udivdi3`/`__udivmoddi4`；成对 object、ELF、objcopy raw binary 全部逐字节相同，规范化 map、`-Wl,-t` trace 和 symbols 也相同。[full-link-summary.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/behavior/full-link-summary.tsv)

【结论，受限命题】在第一轮 compile-only fixture，以及第二轮这个真实链接 fixture、四套工具链、给定 flags 与默认 runtime/linker script 范围内，未观测到 2.4/2.5 最终目标产物差异。由于样本仍有限，不能升级成任意源码、优化/LTO/debug 选项或链接布局的全称保证。

【推断】结合 compiler/assembler/linker CodeDirectory 相同、40 对默认配置相同、已安装 runtime 相同和本轮最终产物相同，当前证据支持“共同配置下目标侧产物保持一致”；确认的功能差异位于宿主 GDB/OpenOCD 和 app 包装，而不是本次目标代码生成链。

### 9.2 只在 2.5 可用的能力与回归

【实测】本次比较范围内没有发现 2.5 独有的 GCC8/GCC12/GCC15 multilib、XW 已知/交叉乘积指令、测试过的 custom named instruction 或 common WCH runtime library；也没有发现 2.4 有而 2.5 缺失的这些目标侧项目。[multilib-diff.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/multilib-diff.tsv)、[xw-cross-product-summary.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/behavior/xw-cross-product-summary.tsv)、[custom-instructions.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/custom-instructions.tsv)、[runtime-external-cmp-summary.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/runtime-external-cmp-summary.tsv)

【实测】宿主侧可以确认 2.5 可用而当前 2.4 包装不可用的能力是 GCC15 GDB 启动，以及 OpenOCD 的 app-relative `hidapi` 解析；这是 A2/A3。app-only 资源因 2.4 抽取不完整属于 B，不能命名为 2.5 新能力；8 个展开 `libwchriscvnn.a` 属于 C1。

### 9.3 对“重写 WCH 库为等价实现”的影响

【结论，受限命题】在已核对的共同 `libIQMath*`、`libprintf*`、`libshlib`、`libshflib`、libgcc/libstdc++、头文件/specs/链接脚本和 XW 语料范围内，换用 2.5 没有改变现有“库内容/编码支持”的观察结论；`Others/IQMath` 的四个库还与 GCC8 Toolchain 内相应库逐一 SHA 对应。[runtime-library-comparisons.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/runtime-library-comparisons.tsv)、[iqmath-relationship.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/iqmath-relationship.tsv)

【推断】因此仅为复现已有 WCH 库行为而切换到 2.5，不应预期获得本次测试未显示的新 XW 命名指令；如果目标是使用 SDK/Communication/Firmware/IQMath 的分发资源，则需把它们作为独立组件处理，并先补齐 2.4 完整物料来做真正的产品级差异判断。

## 10. 未覆盖、失败命令与未能确认事项

1. 【实测】2.4 OpenOCD 与 GCC15 GDB 的 host 依赖不完整，不能在当前机器成功执行；其 build/version 由静态 strings、manifest 与 dependency table 确认，不冒充成功运行证据。
2. 【实测】完整链接强验证仍是一个 freestanding C fixture；未覆盖 C++ exceptions、LTO、debug info、所有优化级别、所有 multilib、用户 linker script、startup code 或真实 firmware 全集。
3. 【实测】492 个 Toolchain 差异已确认是同 CodeDirectory/异签名 blob，GDB 是唯一真 signed-content 差异；但缺上游构建输入，不能继续穷尽 GDB 与 OpenOCD 的源码级内部变化，保留 C3。
4. 【实测】XW 比较覆盖三个随包 `as`、已知/边界/交叉乘积/custom 语料；不证明 CPU 硬件语义，也不覆盖未交付 assembler/plugin。这里作版本间受限阴性，不作所有潜在名称的全称阴性。
5. 【实测】GCC15 `libwchriscvnn.a` 的 8 个展开路径只在 app 目录出现，但两侧相应 `lib.zip` 完全一致且都不含这些成员；缺完整 2.4 产品，无法判断是版本、解包流程还是历史残留，保留 C1。
6. 【范围】2.4 完整 app/package 未纳入，所有 app-only manifest/SDK/Others 结论严格保留为 B；原始 2.5 tar 与安装 app 的 WCH 树已核实一致，但这不能补足 2.4。
7. 【过程】第二轮发生过两项写范围偏差：一个仅含路径的 `/tmp` 临时文件已删除；首次误执行依赖缺失的 2.4 GDB 后，macOS 自动写了两个 DiagnosticReports，未再越权删除。完整披露与修正见 [process-log.md](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/process-log.md)。

## 11. 复现命令清单

从仓库根执行；脚本内部对含空格路径使用参数级引用，原始命令和返回码也写入 raw。

```sh
python3 -m py_compile "tmp/mrs-diff/run_research.py"
python3 "tmp/mrs-diff/run_research.py"
python3 -m py_compile "tmp/mrs-diff/capture_followup.py"
python3 "tmp/mrs-diff/capture_followup.py"
python3 -B "tmp/mrs-diff/probe_xw_slots.py"
python3 -B "tmp/mrs-diff/round2/verify_files_and_signatures.py"
python3 -B "tmp/mrs-diff/round2/verify_behavior.py"
python3 -B "tmp/mrs-diff/round2/audit_round2.py"
```

关键直接检查（路径保持引号）：

```sh
"/Users/apple/Projects/gccriscv-wch/MRS_Toolchain_MAC_V240/Toolchain/RISC-V Embedded GCC/bin/riscv-none-embed-gcc" --version
"/Users/apple/Projects/MounRiver Studio 2.app/Contents/Resources/app/resources/darwin/components/WCH/Toolchain/RISC-V Embedded GCC/bin/riscv-none-embed-gcc" --version
"/Users/apple/Projects/gccriscv-wch/MRS_Toolchain_MAC_V240/Toolchain/RISC-V Embedded GCC12/bin/riscv-wch-elf-gcc" -print-multi-lib
"/Users/apple/Projects/MounRiver Studio 2.app/Contents/Resources/app/resources/darwin/components/WCH/Toolchain/RISC-V Embedded GCC12/bin/riscv-wch-elf-gcc" -print-multi-lib
/usr/bin/otool -L "/Users/apple/Projects/gccriscv-wch/MRS_Toolchain_MAC_V240/OpenOCD/OpenOCD/bin/openocd"
/usr/bin/otool -L "/Users/apple/Projects/MounRiver Studio 2.app/Contents/Resources/app/resources/darwin/components/WCH/OpenOCD/OpenOCD/bin/openocd"
```

第一轮采集过程与 return code 在 [run.log](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/run.log)。第二轮的无效首跑解释、修正和最终 run marker 记录在 [process-log.md](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/process-log.md)、[run-files-and-signatures.txt](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/run-files-and-signatures.txt)、[run-behavior.json](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/run-behavior.json)。不要直接运行已知缺依赖的 2.4 OpenOCD/GDB；第二轮脚本对 GDB 先做 dependency preflight。

## 12. 证据与中间产物索引

- 树与完整 hash： [tree-compare-counts.json](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/tree-compare-counts.json)、[toolchain-24-vs-25app.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/toolchain-24-vs-25app.tsv)、[toolchain-extract-vs-25app.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/toolchain-extract-vs-25app.tsv)、[hashes-mrs24.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/hashes-mrs24.tsv)
- 二进制与配置： [binary-comparisons.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/binary-comparisons.tsv)、[normalized-gcc-v.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/normalized-gcc-v.tsv)、[followup-macho-dependencies.txt](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/followup-macho-dependencies.txt)、[multilib.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/multilib.tsv)、[multilib-diff.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/multilib-diff.tsv)
- XW/custom： [xw-known.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/xw-known.tsv)、[xw-profile-acceptance.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/xw-profile-acceptance.tsv)、[xw-operand-boundaries.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/xw-operand-boundaries.tsv)、[custom-instructions.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/custom-instructions.tsv)、[assembler-interesting-strings.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/assembler-interesting-strings.tsv)
- XW 槽位补充： [probe_xw_slots.py](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/probe_xw_slots.py)、[xw-slot-scan.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/xw-slot-scan.tsv)、[xw-slot-scan-comparison.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/xw-slot-scan-comparison.tsv)
- runtime/组件： [runtime-version-headers.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/runtime-version-headers.tsv)、[runtime-library-comparisons.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/runtime-library-comparisons.tsv)、[headers-specs-scripts.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/headers-specs-scripts.tsv)、[iqmath-relationship.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/iqmath-relationship.tsv)、[component-summary.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/component-summary.tsv)
- OpenOCD/命令失败证据： [openocd-24-vs-25app.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/openocd-24-vs-25app.tsv)、[mrs24-openocd-version.txt](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/mrs24-openocd-version.txt)、[mrs25-app-openocd-version.txt](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/mrs25-app-openocd-version.txt)、[followup-openocd-metadata.txt](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/followup-openocd-metadata.txt)
- 强验证与日志： [compile-fixture.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/compile-fixture.tsv)、[run.log](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/run.log)、[followup-gcc15-libzip.txt](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/raw/followup-gcc15-libzip.txt)
- 第二轮范围/签名： [tar-app-summary.json](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/tar-app-summary.json)、[external-diff-symlink-reconciliation.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/external-diff-symlink-reconciliation.tsv)、[codesign-all-toolchain-differences.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/codesign-all-toolchain-differences.tsv)
- 第二轮行为/强验证： [reported-behavior-summary.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/behavior/reported-behavior-summary.tsv)、[runtime-filesystem-summary.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/behavior/runtime-filesystem-summary.tsv)、[xw-cross-product-summary.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/behavior/xw-cross-product-summary.tsv)、[full-link-summary.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/behavior/full-link-summary.tsv)
- 第二轮审计： [round2-review.md](/Users/apple/Projects/gccriscv-wch/mrs-version-diff/round2-review.md)、[process-log.md](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/process-log.md)
- 最终机器断言： [audit_round2.py](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/audit_round2.py)、[final-audit.json](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/final-audit.json)（40/40 passed）

本任务未修改工具链源材料、原始 tar 或 `.app` 内容，未执行 `git commit`。有两项写范围偏差已在过程日志完整披露：已清理的 `/tmp` path-list，以及一次 dyld 失败触发且未越权删除的两份 macOS crash report。Git index 保留第一轮候选，worktree 保留第二轮 delta，便于独立审查。
