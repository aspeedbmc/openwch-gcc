# phase-6 S2 字面量清点：vanilla 8.2.0 vs 官方（darwin-arm64，x86_64/Rosetta 宿主路线）

> 证据根：`tmp/toolchain_8.2.0/evidence/`（下称 E）。vanilla = `scripts/build-toolchain-8.2.0.sh` 产物（gcc 树 @ 830ea0167 = tag v8.2.0-3.1 + multilib 基础设施 commit 1abae7a36 + host commit 830ea0167；binutils 树 @ 82b51c7b 纯净 tag），官方库字节注入后安装于 `/Users/wch/Work/riscv-none-embed-gcc-10.2.0-1.2/darwin-x64/install/riscv-none-embed-gcc`。对比基线：E/s1 官方现场提取件。

## 1. 结论：可观测字面量面全绿（9/9 项逐字节一致）

| 项 | 官方 | vanilla | 结果 | 证据 |
| --- | --- | --- | --- | --- |
| `gcc -v` Configured with 行 | sha256 35d6177c…（E/s1/gcc-v.txt） | 同左 | **IDENTICAL**（构建时以官方 -v 现场提取 argv 复放，脚本内 sha 钉死） | E/s2/vanilla-literals/gcc-v.txt |
| `gcc version` 行 | `gcc version 8.2.0 (xPack GNU RISC-V Embedded GCC x86_64) ` | 同左 | IDENTICAL | 同上 |
| `as --version` 首行 | `GNU assembler (xPack GNU RISC-V Embedded GCC x86_64) 2.32` | 同左 | IDENTICAL | E/s2/vanilla-literals/as-version.txt |
| `ld --version` 首行 | `GNU ld (xPack GNU RISC-V Embedded GCC x86_64) 2.32` | 同左 | IDENTICAL | E/s2/vanilla-literals/ld-version.txt |
| `-print-multi-lib` | 23 行 | 23 行 | **IDENTICAL**（python3 跑 multilib-generator 的输出与 WCH（python2 时代）构建等价性由此闭合） | E/s2/vanilla-literals/multilib.txt |
| `-dumpspecs` | E/s1/dumpspecs.txt | 同 | IDENTICAL（diff 0 行） | E/s2/vanilla-literals/dumpspecs.{txt,diff} |
| `ld --verbose` SEARCH_DIR | 单行 4 目录（install 树 + /usr/local/lib + /lib + /usr/lib） | 同左 | IDENTICAL | E/s2/vanilla-literals/ld-verbose.txt |
| `.comment` 51 字节 | `\0GCC: (xPack GNU RISC-V Embedded GCC x86_64) 8.2.0\0` | 同左 | IDENTICAL（cmp） | E/s2/vanilla-literals/work/comment.bin |
| 探针 `.o`（probe.c -O2） | sha256 019c42bf… | **同值** | **IDENTICAL——vanilla 在非 XW 面首个产物已逐字节命中官方** | E/s2/vanilla-literals/work/probe_O2.o |

## 2. 构建路线与字面量钉死手段

- **宿主路线 = x86_64/Rosetta（Main 裁定）**：configure 行内嵌 `--build/--host=x86_64-apple-darwin17.7.0` 属字面量面，argv 逐字复放必然产出 x86_64 宿主二进制；`arch -x86_64` 下 clang 仍默认 arm64（实测），故 CC/CXX 显式 `-arch x86_64`。
- 布局：`/Users/wch/Work/riscv-none-embed-gcc-10.2.0-1.2` symlink → `tmp/toolchain_8.2.0/work`；`darwin-x64/{sources,build,install}`；gcc 源目录名 `riscv-gcc-10.2.0-1.1`（谱系钉死）。
- 环境：`LC_ALL=C`、`TZ=UTC`、`SOURCE_DATE_EPOCH=1767225600`、`ZERO_AR_DATE=1`、PATH 最小化、`MAKEINFO=/usr/bin/true`。
- gcc configure argv：构建脚本运行时从官方 `gcc -v` 提取、sha256 钉死（35d6177c…）、shlex 拆分后逐字复放（`work/darwin-x64/logs/openwch-phase6/gcc-configure-argv.json`）。
- binutils configure：v10.2.0-1.2 框架模板 + 官方观测字面量（binutils 不内嵌 argv，验收挂可观测字面量与产物字节）。
- 官方库字节注入：sysroot include/lib（ldscripts 除外）+ lib/gcc payload（rv*/crt*/libgcc/libgcov），7 组抽样对 `verify_pair` 全 PASS（`logs/openwch-phase6/injection-samples.tsv`）。
  - **【勘误 2026-08-17，与 §4 同风格】** 本行的「7 组」是本文件落盘于 S2 那个时点的值，**旧值保留**；
    终态为 **8 组**——第 8 组 `bfd-plugins-lto-stub` 是 Main R4b 裁定（2026-08-17）之后加的注入项，
    `injection-samples.tsv` 现为 8 行、两侧 sha 逐行相等。两个数字各自对应各自的时点，
    以 `phase6-closure.md` §4 的 8 组为终态。
  - **【同处补一条 §2 未回改项】** 本节「ldscripts 除外」是一项**写在脚本里的设计决定**
    （`build-toolchain-8.2.0.sh:389`），后果是 44 个已安装 ldscripts 中 **40 个与官方不同**
    （官方包内嵌 `/Host/home/wch/Work/…/linux-x32/…`，我方内嵌自身前缀）。
    EVT 工程一律 `-T` 指定链接脚本，gate 不受影响；Main 已于 2026-08-17 追认（DECISIONS）。
    详见 `phase6-closure.md` §11.1 观察 1。

## 3. host 适配面（与目标行为无关，全部单列）

| # | 问题 | 处置 | 形态 |
| --- | --- | --- | --- |
| H1 | clang 16+ 把隐式函数声明/隐式 int/int-ptr 转换/函数指针失配升为硬错误（binutils readline `ioctl` 等） | host CFLAGS 加 4 个 `-Wno-*` | 构建旗标，零源码补丁 |
| H2 | isl 0.24 删除了 GCC 8.2 graphite 用的老 API（`isl_space_get_tuple_id` 等） | host 依赖换 isl 0.18（gcc.gnu.org infrastructure，sha256 6b8b0fd7…） | 依赖钉版，零源码补丁 |
| H3 | safe-ctype.h 宏毒化 vs 现代 libc++ 头图（`__locale` 的 `toupper` 成员声明炸） | gcc/system.h 把 C++ 标准头块移到 safe-ctype.h 之前（上游后续版本同构序） | **源码补丁**，gcc 树 commit 830ea0167 → `patches/8.2.0/host/` |

host 依赖：gmp 6.2.1 / mpfr 4.1.0 / mpc 1.2.1 / isl 0.18 / zlib 1.2.12 静态钉版（前提登记：WCH 原始 XBB 环境版本不可观测；probe `.o` 与 v3a 全工程逐字节命中官方，证明该组合对产物字节无扰动——FP 常量折叠疑虑就地消除）。

> **【前提勘误 2026-08-17，审计 P2-2；旧句保留在上一行】** 「WCH 原始 XBB 环境版本**不可观测**」被官方二进制自身证伪：
> 官方 `gcc -v` 的编译期横幅明写
> `compiled by GNU C version 11.2.0, GMP version 6.1.2, MPFR version 3.1.6, MPC version 1.0.3, isl version isl-0.18-GMP`
> （本轮现场重推确认；我方同一行为
> `Apple LLVM 21.0.0 (clang-2100.1.1.101), GMP 6.2.1, MPFR 4.1.0, MPC 1.2.1, isl-0.18-GMP`）。
> 正确表述：**可观测，实测官方为 GMP 6.1.2 / MPFR 3.1.6 / MPC 1.0.3 / 宿主 GCC 11.2.0（isl 0.18 恰好钉对）；
> 我方另选一组（上一行枚举的现值），其无扰动性由产物字节反证**。
> 是否改钉为官方那组由 Main 定（改则需重测）。前提登记原件见 `phase6-closure.md` §14 P-12。

## 4. 双跑与 harness

- 官方 golden：`analysis/golden/8.2.0-darwin-arm64.tsv`——8 工程双跑确定性 PASS、242 gate 产物、v3c-led EXCLUDED（`core_riscv.h:645` 内联 `mcpy`）。16 项目级 workers × make -j2（DECISIONS 并发契约）。
- harness 8.2.0 路由 + evt-golden 16-worker 迁移 + BSD-awk 三目可移植性修复：diff 单列 `E/s2/harness/harness-8.2.0-routing.diff`（**勘误 2026-08-17**：实测 296 行（113 插入/51 删除，11 hunk），归档件与活树 `git diff` 逐字节相同；本行原记 287 不可由现存档案复推，勘误详情见 phase6-closure.md §9。evt-compare 仅 2 处 case 路由；evt-golden 为 worker 池迁移，镜像 phase-3h 已审计的 evt-compare 模式，输出装配按表序、与串行逐字节同构）。
