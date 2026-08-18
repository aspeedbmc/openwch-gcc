# MRS 2.4.0 / 2.5.0 第二轮独立复核

- 复核日期：2026-08-04（Asia/Tokyo）
- 主报告：[findings.md](/Users/apple/Projects/gccriscv-wch/mrs-version-diff/findings.md)
- 过程记录：[process-log.md](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/process-log.md)

本轮把第一轮已暂存内容当作候选基线，不直接采信其归因；改用 BSD `diff`/`cmp`、原始 tar 流、Mach-O CodeDirectory、文件系统 runtime 清单、真实完整链接和交叉乘积 XW 语料复核。以下结论已回写主报告。

## 1. 修正后的 A/B/C 口径

“条”是带稳定 ID 的差异事项，不是文件行数。

| ID | 类别 | 复核结论 |
|---|---|---|
| A1 | A | 493 个共同 Toolchain 普通文件的原始 SHA 不同；其中 492 个 CodeDirectory 内容哈希相同、签名时间不同，属于重新签名；不是 492 个编译器功能改动。 |
| A2 | A | 唯一 CodeDirectory 真正不同的 Toolchain 文件是 GCC15 `riscv32-wch-elf-gdb`。两侧都内嵌 17.1；2.4 硬编码两个本机不存在的 `/Users/mrs/...` GMP/MPFR 依赖，2.5 去掉这两个依赖并能运行。 |
| A3 | A | OpenOCD 的 binary、`version.txt`、`sub_manifest.json` 改变：包版本 `v2.8 → v2.10`，内嵌构建为 2026-02-28/mrs2.4 → 2026-06-17/mrs2.5；`hidapi` 从 Homebrew 绝对路径改为 app 内 loader-relative 路径。 |
| B1–B5 | B | `manifest.json`、`SDK/default`、`Others/CommunicationLib`、`Others/Firmware_Link`、`Others/IQMath` 只在完整 2.5 材料可见；缺完整 2.4，不能称为 2.5 新增。 |
| C1 | C | 8 个展开的 `libwchriscvnn.a` 只在 2.5 app 可见；第二轮外部 diff 复现八条，两侧 `lib.zip` 相同且均不含它们，来源仍不确定。 |
| C2 | C | 三个单侧 `.DS_Store`（Toolchain 根一个、OpenOCD 两个）是包装残留，不能归因成功能版本差异。 |
| C3 | C | 缺 GDB/OpenOCD 对应源码、构建日志和完整 changelog；已确认的依赖/版本变化之外，不能穷尽其内部源码差异。 |

计数：A=3、B=5、C=3。

## 2. 需求—证据矩阵

| 原提示要求 | 第二轮独立方法 | 结果 | 直接证据 | 剩余边界 |
|---|---|---|---|---|
| 先确认比较实物 | 流式读取 4.57 GB 原始 2.5 tar，对安装 app 的 WCH 树逐文件 SHA、mode、symlink、路径求差 | 21,466 普通文件、1,971 目录、24 symlink 全部对应；忽略 11,627 个 `._*` AppleDouble 条目后，所有 mismatch/only 计数为 0 | [tar-app-summary.json](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/tar-app-summary.json) | 仍缺完整 2.4 包 |
| 仓库 2.5 抽取是否可信 | 外部 `/usr/bin/diff -rq`，不复用第一轮哈希器 | GCC8/GCC12 各 0 differ/only | [external-diff-summary.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/external-diff-summary.tsv) | 只证明该两个子树 |
| Toolchain 哪些真变了 | 对 493 个原始 SHA 差异逐个取 `codesign -d --verbose=5` CodeDirectory 哈希；代表样本复制后剥签再 SHA | 492 同内容/异签名，1 个真内容差异（GCC15 GDB） | [codesign summary](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/codesign-all-toolchain-differences-summary.json)、[逐文件表](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/codesign-all-toolchain-differences.tsv)、[剥签样本](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/signature-strip-samples.tsv) | CodeDirectory 等同不解释签名服务为何重签 |
| 构建默认值是否改变 | 四套 GCC 各比较 dumpspecs、target options、默认 driver、search dirs、sysroot、库路径、assembler help、默认 linker script，共 40 对命令 | 规范化安装根和仅呈现用引号后 40/40 返回 0 且输出相同 | [reported-behavior-summary.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/behavior/reported-behavior-summary.tsv) | 不外推到全部可选 flags |
| multilib/runtime 是否改变 | 不依赖 `-print-multi-lib`，从文件系统枚举 `libgcc.a`、libc/libm/libg/libnosys/libstdc++、crt0 并逐 SHA；另用外部 `cmp` 复核共同 runtime | 605 个选定文件路径/内容/mode 相同；外部 `cmp` 的 416 个共同 runtime 也全同 | [filesystem summary](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/behavior/runtime-filesystem-summary.tsv)、[external cmp](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/runtime-external-cmp-summary.tsv) | 受列出的 basename/WCH 正则限制 |
| XW 支持是否改变 | 先确认三套 `as` CodeDirectory 相同；再对每套汇编 8,704 条合法寄存器×base×立即数组合并比较对象与 `.text` | GCC8/12/15 两侧均成功；每份 `.text` 恰 17,408 bytes，逐字节相同 | [xw-cross-product-summary.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/behavior/xw-cross-product-summary.tsv)、[签名逐文件表](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/codesign-all-toolchain-differences.tsv) | 不证明硬件语义，也不声称列举了宇宙中所有可能助记符名称 |
| 同源码最终产物是否改变 | 四套工具链用固定源码实际 compile+link；默认 linker script、默认库组，强制 64-bit 除法拉入 `libgcc`；比较 object、ELF、raw binary、map、trace、symbols | 四套均成功；所有成对 object/ELF/raw binary 逐字节相同，规范化 map/trace/symbols 也相同 | [full-link-summary.tsv](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/behavior/full-link-summary.tsv) | 单一 freestanding fixture，不是任意程序全称保证 |
| OpenOCD/GDB 宿主工具 | `strings` 静态取 build banner，`otool -L` 取依赖；先做依赖预检再决定是否执行 | OpenOCD 和 GDB 的真实包装/依赖差异均被定位 | [OpenOCD static](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/behavior/openocd-static-summary.tsv)、[GDB static](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/behavior/gcc15-gdb-static-summary.tsv) | 2.4 两个 binary 在当前机器不能成功运行 |

## 3. 对第一轮候选结论的修正

| 第一轮候选 | 第二轮处理 |
|---|---|
| “493 个差异原因不明，可能是源码/优化/时间戳/签名” | 收窄为 492 个相同 CodeDirectory 的重签名 + 1 个 GCC15 GDB 真变化；不再把 92 个 raw-SHA 不同的工具路径暗示为 92 个功能变化。 |
| “没有做完整链接” | 已关闭：GCC8/GCC12/GCC15/ARM 四组完整链接和最终 binary 均相同。 |
| “2.4 OpenOCD 运行失败，实际 build banner 未确认” | 动态执行仍失败，但静态二进制内嵌 banner 已确认；依赖路径变化也已定位。 |
| “XW 全量助记符阴性保留 C” | 不再作无界名称枚举；比较问题改由 assembler CodeDirectory 相同 + 26,112 条交互语料相同回答：在交付的三个 assembler 及这些输入范围内未发现 2.5 parser/编码变化。 |
| “2.5 app 是可信比较源”主要依赖安装目录 | 原始 tar 与安装 WCH 全量流式核对，补足来源链。 |
| 外部 `diff -rq` 显示 514 行，似与 493 冲突 | 其中 21 行是 `diff` 解引用相同 symlink 文本后重复报告目标差异；扣除后按工具链为 139+147+55+152=493 | [symlink reconciliation](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/raw/external-diff-symlink-reconciliation.tsv) |

## 4. 结论边界

- 【实测】可确认的编译产物结论只覆盖本轮固定 freestanding fixture、四套工具链和列出的 flags；不能写成任意源码、LTO、调试信息、语言前端或任意链接布局都相同。
- 【实测】XW 比较覆盖三个随包 assembler、第一轮已知/边界/custom 语料与第二轮 8,704 交互组合；不证明 CPU 硬件语义。
- 【实测】2.5 原始 tar 与当前 app 的 WCH 树一致；2.4 只有 Toolchain/OpenOCD 抽取，因此 B1–B5 仍不能升级为版本新增。
- 【推断】鉴于目标编译器、assembler、linker、默认配置、runtime 和本轮最终产物都一致，2.5 对“重写 WCH 库为等价实现”的已有目标侧结论没有显示出改变；宿主侧真正改善是 GCC15 GDB 与 OpenOCD 的可搬移依赖。

## 5. Git 追踪方式

第一轮候选内容保留在 index；第二轮修订保留为相对 index 的 worktree delta，未 commit。只看任务范围：

```sh
git diff --cached -- "mrs-version-diff" "tmp/mrs-diff"
git diff -- "mrs-version-diff" "tmp/mrs-diff"
git status --short --untracked-files=all -- "mrs-version-diff" "tmp/mrs-diff"
```

第二轮脚本：[verify_files_and_signatures.py](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/verify_files_and_signatures.py)、[verify_behavior.py](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/verify_behavior.py)、[audit_round2.py](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/audit_round2.py)。最终 40 项断言全部通过：[final-audit.json](/Users/apple/Projects/gccriscv-wch/tmp/mrs-diff/round2/final-audit.json)。
