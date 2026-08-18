# Phase 2 字面量面对照（vanilla GCC 15.2.0）

测试日期：2026-08-13（Asia/Tokyo）。所有命令使用 `LC_ALL=C` 和
`SOURCE_DATE_EPOCH=1767225600`。WCH 根为
`ref/gcc/darwin-arm64/15.2.0`，我方 install 根为
`tmp/toolchain_15.2.0/riscv-gnu-toolchain/output`。完整原始证据位于
`tmp/phase2-evidence/t4/`；可重放命令为
`bash tmp/phase2-evidence/run-t4.sh`。

## 结论总表

| 项目 | 期望值 | 实测值 | 判定 |
|---|---|---|---|
| T4.1 `Configured with:` | 与 WCH 逐字节相同 | 两侧均 1303 bytes，SHA256 均为 `9e040762…a42e`，`cmp=0` | 一致 |
| T4.2 `-v` 其余行 | 核心版本面相同；其余差异分类 | Target/thread/LTO/version 四行 `cmp=0`；调用路径不同；vanilla 额外报 10 条 XW multilib 解析错误 | 允许遗留，已分类 |
| T4.3 `.comment`/DWARF | `.comment` 指定 MD5；producer/comp_dir 同条件相同 | 四个对象的 `.comment` 均为 `83a117f6276bc1e35530c55b1451e9b3`；两个 DWARF 字段逐字相同；含/不含 `-g` 的对象本身也分别 `cmp=0` | 一致 |
| T4.4 linker `SEARCH_DIR` | 与 WCH 原顺序逐字相同 | 两侧均为 `/Users/mrs/riscv-gnu-toolchain/output/riscv32-wch-elf/lib`，`cmp=0` | 一致 |
| T4.5 as/ld 首行 | 与 WCH 相同 | 均为 GNU Binutils 2.45，两个 `cmp=0` | 一致 |
| T4.6 multilib 表 | 22 项、顺序和空白与 WCH 相同 | stdout 均 22 行且 `cmp=0`；vanilla 另在 stderr 报 10 条 XW 解析错误 | 数据面一致；行为差异已分类 |
| T4.7 strings 命中集 | 列出仅一侧项 | cc1/as/ld 三组过滤集合完全相同，六个 one-sided 文件均为 0 bytes | 一致，无仅一侧项 |
| T4.8 dumpspecs | 保存逐字 diff，允许不同 | 两侧均 142 行；MD5 分别为 WCH `800ded…ac3`、vanilla `924cb9…577`；仅 1 个 hunk | 允许遗留，已分类 |

关键 gate 1/3/4/5/6 均满足任务书要求。T4.6 的 22 行数据面逐字一致；其额外 stderr 是运行行为差异，未被忽略或归一化。

## T4.1 `Configured with:`

两侧均只提取到一行。完整行（含末尾换行）为 1303 bytes，SHA256 均为：

```text
9e040762b36a5f2caae005d79088d658c880930150ede693a221a021c724a42e
```

`cmp` 退出 0，证明 configure 字面路径、参数顺序、引号解码后的再打印形式，以及 multilib/CFLAGS 参数内部不规则空白均一致。权威证据：

- `wch-configured-with.txt`
- `ours-configured-with.txt`
- `status.tsv` 的 `configured_with_cmp_rc=0`

## T4.2 `-v` 其余行

以下四行两侧逐字相同（`gcc_v_invariants_cmp_rc=0`）：

```text
Target: riscv32-wch-elf
Thread model: single
Supported LTO compression algorithms: zlib
gcc version 15.2.0 (g5115c7e44-dirty)
```

遗留差异有两类：

1. `COLLECT_GCC` 与 `COLLECT_LTO_WRAPPER` 指向实际调用的不同 install 根。
   这是调用入口路径造成的 invocation artifact，并非固有工具链差异；本项
   按任务书使用各自真实入口采集。配置内嵌根仍由 T4.1/T4.7 证明为同一
   `/Users/mrs/...`。
2. vanilla `-v` 在退出 0 前额外报告 10 条 `xw` multilib 候选解析错误。WCH driver 接受这些候选，pristine parser 不接受；这是待 phase-3 处理的 driver/march 接受面差异，不是空白、路径或 configure 复刻错误。

完整统一 diff 为 `gcc-v-without-configured.diff`，完整两侧流分别为
`wch-gcc-v.txt` 和 `ours-gcc-v.txt`。

## T4.3 `.comment` 与 DWARF

两侧在同一物理 cwd
`/Users/apple/Projects/openwch/tmp/phase2-evidence/t4/probe` 内，依次使用同一个
`probe.c`、同一个临时输出名 `probe.o` 和同一参数：

```text
-march=rv32imac_zaamo_zalrsc -mabi=ilp32 -O2 [-g] -c probe.c -o probe.o
```

选择该 canonical multilib 是为了让 pristine driver 在解析全部 XW 候选前命中一个精确条目；双方参数完全相同，且没有改变待测产物。四份 `.comment` 都是 32 bytes，MD5 均为任务书指定值：

```text
83a117f6276bc1e35530c55b1451e9b3
```

`-O2 -g` 两侧字段均为：

```text
DW_AT_producer: GNU C23 15.2.0 -mabi=ilp32 -misa-spec=2.2 -march=rv32imac_zmmul_zaamo_zalrsc_zca -g -O2
DW_AT_comp_dir: /Users/apple/Projects/openwch/tmp/phase2-evidence/t4/probe
```

字段提取 `cmp=0`；原始 `readelf --debug-dump=info` 完整保留。额外的原字节检查显示 WCH/vanilla 的 `-O2` 对象 `cmp=0`，`-O2 -g` 对象也 `cmp=0`。readelf 对两侧相同地提示当前工具不支持 relocation type 60/61；这不影响字段提取，且原始对象未修改。

## T4.4 linker 搜索目录

完整 `ld --verbose` 输出保存后，仅提取原顺序 `SEARCH_DIR` 行做字段比较。两侧唯一一行完全相同：

```text
SEARCH_DIR("/Users/mrs/riscv-gnu-toolchain/output/riscv32-wch-elf/lib");
```

`search_dir_cmp_rc=0`。

## T4.5 as/ld 版本

完整 `--version` 输出均已保留，验收首行为：

```text
GNU assembler (GNU Binutils) 2.45
GNU ld (GNU Binutils) 2.45
```

两项首行 `cmp` 均为 0。

## T4.6 multilib

WCH 现场输出与 vanilla stdout 均为 22 行，原顺序和原空白 `cmp=0`。完整数据在
`wch-multilib.stdout` / `ours-multilib.stdout`；两个命令退出码均为 0。

vanilla stderr 另有 10 条错误，分别对应表内 10 个 XW 候选。该现象并非 stdout 表差异：pristine `riscv_compute_multilib` 在未先精确命中条目时会解析全部候选，而上游 parser 拒绝未知 `xw`。完整错误保存在 `ours-multilib.stderr`；WCH stderr 为 0 bytes。此差异同时解释 T4.2 及 T5 的构建接受面结果。

## T4.7 strings 命中集

两侧统一用 macOS `/usr/bin/strings -a`，过滤模式为：

```text
(/Users/|/home/|--with-|5115c7e44)
```

再以 `LC_ALL=C sort -u` 得到完整集合。结果：

| 二进制 | WCH unique | vanilla unique | only WCH | only vanilla |
|---|---:|---:|---:|---:|
| cc1 | 13 行 / 2234 bytes | 13 行 / 2234 bytes | 0 | 0 |
| as | 61 行 / 3336 bytes | 61 行 / 3336 bytes | 0 | 0 |
| ld | 59 行 / 3200 bytes | 59 行 / 3200 bytes | 0 | 0 |

全部集合小于 8 KiB，无截断；其行数、字节数和 SHA256 在
`strings/summary.tsv`。没有 `/Users/apple` 或 `/home` 命中，内嵌构建根均为钉死的 `/Users/mrs/riscv-gnu-toolchain`。

## T4.8 dumpspecs

WCH 现场值复现报告：142 行，MD5
`800ded8813ca9c990ece27bbea501ac3`。vanilla 同为 142 行，MD5
`924cb9c686ce8d67821eb87365c06577`。`cmp=1`，完整 diff 只有下列 hunk：

```diff
--- WCH-dumpspecs
+++ vanilla-dumpspecs
@@ -13,7 +13,7 @@
        objcopy --strip-dwo 	 %{c:%{o*:%*}%{!o*:%w%b%O}}%{!c:%U%O}     }
 
 *asm_options:
-%{-target-help:%:print-asm-header()} %{v} %{w:-W} %{I*} %(asm_debug_option) %{gz|gz=zlib:--compress-debug-sections=zlib} %{gz=none:--compress-debug-sections=none} %{gz=zstd:--compress-debug-sections=zstd} %{gz=zlib-gnu:}%a %Y %{c:%W{o*}%{!o*:-o %w%b%O}}%{!c:-o %d%w%u%O}
+%{-target-help:%:print-asm-header()} %{v} %{w:-W} %{I*} %(asm_debug_option) %{gz|gz=zlib:--compress-debug-sections=zlib} %{gz=none:--compress-debug-sections=none} %{gz=zlib-gnu:}%a %Y %{c:%W{o*}%{!o*:-o %w%b%O}}%{!c:-o %d%w%u%O}
 
 *invoke_as:
 %{!fwpa*:   %{fcompare-debug=*|fdump-final-insns=*:%:compare-debug-dump-opt()}   %{!S:-o %|.s |
```

归类：该差异与 host/binutils capability probe 的结果一致。GCC configure
会实际探测所用 assembler 是否接受
`--compress-debug-sections=zstd`；官方 as 支持，当前 vanilla binutils 在
不安装额外全局依赖的构建中未发现 libzstd，故生成 specs 时缺少该
clause。现有证据足以说明生成机制，不足以排除 WCH 侧还有手工变更，因此
本文没有把它定性为已确认的 WCH driver 补丁。T4.8 按任务书为诊断项、
允许不同；完整 stdout、stderr、hash 和固定 label diff 均已保留。

## 原始证据索引

- `tmp/phase2-evidence/t4/status.tsv`：所有 cmp/命令退出码。
- `tmp/phase2-evidence/t4/context.txt`：路径、epoch、probe cwd/flags。
- `tmp/phase2-evidence/t4/probe/`：源文件、四个原始对象、`.comment`、DWARF dump。
- `tmp/phase2-evidence/t4/strings/`：完整 raw/unique/one-sided 集及摘要。
- `tmp/phase2-evidence/t4/dumpspecs.diff`：完整 T4.8 diff。
