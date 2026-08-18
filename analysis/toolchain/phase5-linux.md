# Phase 5：GCC 15.2.0 linux-amd64 复验

> 状态：**COMPLETE**。本阶段按 2026-08-13 裁定，以 Linux 官方工具链的
> Linux golden 为 gate；Darwin/Linux 官方包之间已知的 14 项链接差异不是 gate，
> 仅作有界归因。

## 1. 结论

冻结的 9 片 GCC/binutils 补丁在 `debian:bookworm` linux/amd64 容器中从
pristine 上游源码完整复放、构建成功。构建只安装 host 编译器，并逐字注入
Linux 官方包的 target 库和头文件。自建工具链与 Linux 官方工具链的关键字面量
逐字相同；精选 9 工程最终 compare 退出 0，**274/274 gate 全 PASS**。

Linux 官方的 XW 接受面、编码、独立 GAS、缺陷与诊断探针均与 Darwin 官方定向
对拍一致。两官方包的库树存在大量输入差异；14 项跨平台链接差异中按任务书选取
的 `v3a-gpio` 代表失配已归因到不同官方库输入，没有发现该取样中相同输入下
链接器行为不同的信号。本阶段未修改 `patches/15.2.0/`。

这里的“完成”只指 phase-5 任务书规定的 9 工程快速回归集。DECISIONS 另立的
1298 工程全量 EVT 收口仍属于 phase-3d，不在本阶段宣称完成。

## 2. 容器环境与工具链身份（T1）

- 构建容器：`debian:bookworm`，image ID
  `sha256:9344f8b8992482f80cba753f323adeaf17690076c095ccff6cc9536be98185dc`；
  OrbStack/Rosetta 下 `uname -m=x86_64`，Debian 12.15。
- 关键包版本见
  `tmp/toolchain_15.2.0-linux/evidence/t1/packages.txt`：GCC 12.2.0、make 4.3、
  Python 3.11.2、flex 2.6.4、bison 3.8.2。
- Linux 官方工具链为 GCC `(g5115c7e44-dirty) 15.2.0`、binutils 2.45。
- Linux/Darwin `Configured with:` 只把 `/home/wch/` 与 `/Users/mrs/` 归一为
  `@PREFIX@/` 后，1280 B payload 原字节 `cmp` 通过，与 survey §9 一致。
  证据：`tmp/toolchain_15.2.0-linux/evidence/t1/config-compare.txt`。

## 3. Linux golden（T2）

最终 golden 在 linux/amd64 容器中生成，仓库挂载为与 Darwin 相同的绝对路径
`/Users/apple/Projects/openwch`：

- 9/9 工程构建成功；`double_run=PASS deterministic=9 excluded=0 failures=0`；
- 551 个产物行：274 gate、277 aux；每工程均含 `.o`、`.elf`、`.bin`；
- manifest 头包含工具链、逐工程 converter argv、`SOURCE_DATE_EPOCH=1767225600`、
  双跑结论、生成时间和容器 image digest；
- 保存的 run1/run2 各 551 个文件重新逐行对 manifest 的 size/SHA256 审计，
  两跑均为 0 mismatch；run1 对 run2 也为 0 mismatch。

交付物为 `analysis/golden/15.2.0-linux-amd64.tsv`；运行证据为
`tmp/toolchain_15.2.0-linux/evidence/t2-golden-samepath.log`。

## 4. Linux 官方 XW 实机对拍（T3）

| 表面 | 覆盖 | 结果 |
|---|---|---|
| `.comment` | `-O2` C object | 32 B，MD5 `83a117f6276bc1e35530c55b1451e9b3`，两平台 BYTE-EXACT |
| march | `xw`、`_xw`、`xw2p2`、`xw9p9` | 接受面、multidir、对象与 attributes 全同；裸 XW 为 `xw2p0` |
| 编码 | 8 条 XW compressed + 4 条 custom32 | 对象和 `.text` 全同；`c.lbu=0x2188`，`mcpy=0x60b5700f` |
| 独立 GAS | omitted / 2.2 / 20190608 / 20191213 | 默认等同 2.2；mapping symbol 以 `_xw2p2` 结尾；两平台全同 |
| 缺陷保真 | a–d 四探针 | rc/stdout/stderr/产物逐字节相同 |
| GAS 门控诊断 | 35 case | rc/stdout/stderr 35/35 相同，并命中冻结 Darwin 结果 |

证据入口：
`tmp/toolchain_15.2.0-linux/evidence/t3-agent/comparison-matrix.tsv`、
`anchor-checks.txt`、`encoding-per-instruction.tsv`。该结论只覆盖任务书列出的
定向接受面、编码面和诊断面。

## 5. 官方跨平台链接差异的有界归因（T3b）

逐文件 SHA256 清单覆盖任务书指定的两棵库树：

| 库树 | Darwin 文件 | Linux 文件 | 同路径同哈希 | 同路径异哈希 | 仅 Darwin | 仅 Linux |
|---|---:|---:|---:|---:|---:|---:|
| `lib/gcc/riscv32-wch-elf/15.2.0` | 713 | 715 | 610 | 101 | 2 | 4 |
| `riscv32-wch-elf/lib` | 663 | 663 | 223 | 440 | 0 | 0 |

完整的四份 manifest 和 547 行差异清单位于
`tmp/toolchain_15.2.0-linux/evidence/t3b/`；生成器为同目录
`generate-library-evidence.sh`。这证明两个官方包随附的 target 库不是同一组输入。

按任务书选无 XW 干扰的 `v3a-gpio` 归因：

- Darwin ELF 为 22780 B、SHA256 `0daa6fe6…277e1`；Linux ELF 为 22776 B、
  SHA256 `0f490cc4…91632`；26 个显式工程 `.o` 全部 BYTE-SAME。
- `.init`、`.vector`、`.text`、`.data`、`.comment`、`.riscv.attributes` 等相同，
  最终 BIN 也相同（SHA256 `e4a99374…3019`）。仅 `.debug_line`、
  `.debug_line_str`、`.debug_info`、`.debug_str` 不同。
- 该 ELF 唯一 DWARF CU 是 `libgcc/config/riscv/save-restore.S`。所选 multilib
  `libgcc.a` 的 Darwin/Linux SHA256 分别为 `08eeb6dc…145fc`、
  `aac978f7…cb1e`；其中 `save-restore.o` 分别为 `2106d117…d7b9ba`、
  `ea70f42e…d9fcb`。
- 两个成员的 `.text` 逐字相同；差异是 `DW_AT_comp_dir`：Darwin 指向
  `/Users/mrs/.../build-gcc-newlib-stage2/.../libgcc`，Linux 指向
  `/home/wch/.../build-gcc-newlib-stage3/.../libgcc`。`nm -A` 也确认
  `__riscv_save_*`/`__riscv_restore_*` 由该 archive member 提供。

证据为同目录的 `v3a-section-hashes.tsv`、`v3a-project-objects.tsv`、
`v3a-*-dwarf-provenance.txt`、`*-save-restore.dwarf.txt`、
`*-save-restore-symbol-ownership.txt` 与 `v3a-attribution-summary.txt`；生成器为
`generate-v3a-attribution.sh`。因此本取样失配可归因到不同官方库输入，不是
相同输入下链接器行为差异。该结论不外推为任意输入下两平台链接器完全等价。

## 6. Pristine 复放、Linux 构建与库注入（T4）

- pristine release HEAD：GCC
  `5115c7e447fc07457443df874bf57840e8316d5f`、binutils
  `2bc7af1ff7732451b6a7b09462a815c3284f9613`。
- `patches/15.2.0/` 的 3+6 片按 series 在隔离 index 中 apply-check/apply 全过；
  实际构建树分别等于 tree `3686efe41d20…`、`918ab266a63d…`，`diff --check` 通过。
- `scripts/build-toolchain-15.2.0-linux.sh` 从 Linux 官方 `gcc -v` 现场提取并原样
  执行 configure argv，以 `/home/wch/riscv-gnu-toolchain` 字面 symlink 构建；
  binutils 明确带 `--with-isa-spec=2.2`；只执行 `all-gcc + install-gcc`。
- 构建退出 0，安装树 2921 个文件。Linux 官方三棵 target 数据树原字节注入，
  共 2829 个文件；stage/final 六份 `diff -qr --no-dereference` 输出均为 0 B，
  5 个指定样本 SHA256 全 PASS。

证据：`tmp/toolchain_15.2.0-linux/evidence/t4/build-success-summary.txt`、
`success/{binutils-configure,binutils-build,binutils-install,gcc-configure,gcc-all-gcc,gcc-install-gcc}.log`、
`success/injection-samples.tsv`、`success/injection-*.diff`。顶层 `build-driver.log` 和
`build-aborted.txt` 属此前资源中止轮，不是成功轮证据；最终成功轮由上述分阶段日志、
汇总、安装树、字面量核验和最终 compare 共同闭合。

## 7. 自建对 Linux 官方字面量清点（T4）

| 项目 | 结果 |
|---|---|
| `Configured with:` | 原字节 `cmp=0`；1300 B；SHA256 `dcf5ea99…9720da` |
| `.comment` | 原字节 `cmp=0`；32 B；MD5 `83a117f6276bc1e35530c55b1451e9b3` |
| `SEARCH_DIR` | 完整提取行 `cmp=0`；`/home/wch/riscv-gnu-toolchain/output/riscv32-wch-elf/lib` |
| `-print-multi-lib` | stdout/stderr 均 `cmp=0`；22 行；stderr 0 B |
| gcc/as/ld `--version` | 三份完整输出均 `cmp=0` |
| DWARF producer/comp_dir | 同 cwd、同 flags 的字段与完整 object 均 `cmp=0` |

`.comment` 完整 hex 为
`004743433a2028673531313563376534342d6469727479292031352e322e3000`。
证据：`tmp/toolchain_15.2.0-linux/evidence/t4/literals/summary.txt` 及同目录原始输出。

## 8. Linux golden compare（T4）

compare 在 linux/amd64 的 `openwch-p5-samepath` 容器中运行；仓库路径为
`/Users/apple/Projects/openwch`，并设置
`/home/wch/riscv-gnu-toolchain` 指向同一挂载树的 Linux 构建。结果：

```text
exit_code=0
SUMMARY gate_pass=274 gate_total=274 gate_fail=0 aux_match=273 aux_diff=4
```

全部 256 个 `.o`、9 个 `.elf`、9 个 `.bin` 均逐字命中 Linux golden。4 项
aux 差异均为 `.map`，按项目定义只作诊断、不进 gate。原始证据：
`tmp/toolchain_15.2.0-linux/evidence/t4/evt-compare.{stdout,stderr,status}`；stderr
为 0 B。此前一次误在 Darwin 宿主执行 Linux ELF 的 error 126 已单独保存为
`evt-compare-invalid-host.*` 并标注 `gate_round=no`，不属于行为差异轮次。

## 9. Harness 平台适配

`scripts/evt-golden.sh` 与 `scripts/evt-compare.sh` 只增加宿主平台选择、平台化
官方根/manifest、Linux manifest 镜像头和 `sha256sum` 等价后备。neutral root、
双侧 `-fdebug-prefix-map`、原始文件 size/SHA256、gate/aux 分类、extra gate 判定和
退出码语义未改。相关脚本 `bash -n` 与 phase-5 文件范围的
`git diff --check -- <phase-5-files>` 通过；最终 Linux golden 双跑及 274/274
compare 是实机覆盖。全工作树另有其他阶段已有的 CRLF/尾空白改动，未纳入本项、
也未擅自修改。

## 10. 前提登记回填

1. Darwin/Linux configure 行归一化前缀后一致：**已在 Linux 容器实机验证**。
2. Linux 侧 XW 行为与 Darwin 一致：**任务书列出的定向探针已验证**。
3. Darwin/Linux 官方精选集 gate 一致：**已证伪，但已裁定为非目标**；14 项均为
   链接产物差异。两包的随附库树已确认不是同一组输入，其中任务书指定的
   `v3a-gpio` 单样本已定位到不同 `libgcc.a` 成员的 DWARF；其余 13 项未逐项归因，
   不阻塞各平台对自身 golden 的 gate。
4. 同一冻结补丁集在 Linux 对 Linux 官方 golden：**已验证，274/274**。

## 11. 需求回归与设计回归

- 需求回归：T1、T2、T3、T3b、T4 均有当前证据；manifest 双跑、字面量和最终
  compare 均满足 phase-5 明文验收项。
- 设计回归：`git diff -- patches/15.2.0` 为空；构建只含 compiler-only 与 Linux
  官方原字节库注入；harness 比较未 normalize 的原产物，gate/退出码语义未变；
  官方跨平台差异按 DECISIONS 裁定只归因、不修复。

## 12. 未决问题

无。T3b 未发现需要单列的同输入链接器行为差异；Linux 对 Linux golden 也没有
未收敛的 gate 差异。
