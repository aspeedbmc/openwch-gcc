# WCH 官方 GCC 工具链取证报告

目的：为「用开源 GCC 复刻 WCH 官方工具链、输出逐字节一致」提供事实基线。

- 主对象：`ref/gcc/darwin-arm64/15.2.0/`，triple `riscv32-wch-elf`
- 次对象：`ref/gcc/darwin-arm64/12.2.0/`、`ref/gcc/darwin-arm64/8.2.0/`、`ref/gcc/linux-amd64/15.2.0/`
- 维度约定：目录中的 `darwin-arm64` / `linux-amd64` 描述宿主分发平台；`riscv32-wch-elf` / `arm-none-eabi` 等 compiler triple 描述 target。二者正交。
- 试编译产物目录：`/private/tmp/claude-501/-Users-apple-Projects-openwch/b28c0730-f239-4670-bbaf-cd987694f5f7/scratchpad/tcprobe/`
- 证据标注：【实测】= 本机命令输出；【网查】= 互联网核查；【推断】= 由前述推导，未直接验证。
- 下文 `$B` = `/Users/apple/Projects/openwch/ref/gcc/darwin-arm64/15.2.0/bin`，`$R` = 该工具链根目录。

---

## 1. 四件套版本与构建身份

【实测】命令与输出：

| 组件 | 版本串（逐字符） | 命令 |
|---|---|---|
| GCC | `riscv32-wch-elf-gcc (g5115c7e44-dirty) 15.2.0` | `$B/riscv32-wch-elf-gcc --version` |
| binutils (as) | `GNU assembler (GNU Binutils) 2.45` | `$B/riscv32-wch-elf-as --version` |
| binutils (ld) | `GNU ld (GNU Binutils) 2.45` | `$B/riscv32-wch-elf-ld --version` |
| binutils (objdump) | `GNU objdump (GNU Binutils) 2.45` | `$B/riscv32-wch-elf-objdump --version` |
| newlib | `4.5.0` | `grep _NEWLIB_VERSION $R/riscv32-wch-elf/include/_newlib_version.h` |
| gdb | `GNU gdb (GDB) 17.1` | `$B/riscv32-wch-elf-gdb --version` |

关键点：**只有 GCC 带 pkgversion**。binutils 与 gdb 的版本串是上游默认形态（`(GNU Binutils) 2.45`、`(GDB) 17.1`），说明二者构建时**没有**传 `--with-pkgversion`。复刻时必须同样只给 GCC 传该选项，否则 binutils/gdb 的 `--version` 输出会多出括号内容。

其他构建身份【实测】`$B/riscv32-wch-elf-gcc -v`：

- `Target: riscv32-wch-elf`
- `Thread model: single`
- `Supported LTO compression algorithms: zlib`
- `gcc version 15.2.0 (g5115c7e44-dirty)`

### 1.1 configure 全行（GCC，逐字符）

【实测】`$B/riscv32-wch-elf-gcc -v` 的 `Configured with:` 行：

```
/Users/mrs/riscv-gnu-toolchain/gcc/configure --target=riscv32-wch-elf --prefix=/Users/mrs/riscv-gnu-toolchain/output --disable-shared --disable-threads --enable-languages=c,c++ --with-pkgversion=g5115c7e44-dirty --without-system-zlib --enable-tls --with-newlib --with-sysroot=/Users/mrs/riscv-gnu-toolchain/output/riscv32-wch-elf --with-native-system-header-dir=/include --disable-libmudflap --disable-libssp --disable-libquadmath --disable-libgomp --disable-nls --disable-tm-clone-registry --src=.././gcc --enable-multilib --with-multilib-generator='rv32e-ilp32e-- rv32ec-ilp32e-- rv32ecxw-ilp32e-- rv32ec_zmmul-ilp32e-- rv32ecxw_zmmul-ilp32e-- rv32imac_zba_zbb_zbc_zbs-ilp32--    rv32imacxw_zba_zbb_zbc_zbs-ilp32-- rv32imacxw-ilp32-- rv32imac-ilp32-- rv32imcxw_zba_zbb_zbc_zbs-ilp32-- rv32imc_zba_zbb_zbc_zbs-ilp32--   rv32imafc-ilp32f--  rv32imafc_zba_zbb_zbc_zbs-ilp32f-- rv32imafcxw-ilp32f-- rv32imafcxw_zba_zbb_zbc_zbs-ilp32f-- rv32imc-ilp32-- rv32imcxw-ilp32--  rv32imac_zve64x_zvl64b-ilp32--  rv32imacxw_zve64x_zvl64b-ilp32--  rv32imac_zba_zbb_zbc_zbs_zve64x_zvl64b_zvbb-ilp32-- rv32imacxw_zba_zbb_zbc_zbs_zve64x_zvl64b_zvbb-ilp32--' --with-abi=ilp32 --with-arch=rv32gc --with-isa-spec=2.2 'CFLAGS_FOR_TARGET=-Os    -mcmodel=medlow' 'CXXFLAGS_FOR_TARGET=-Os    -mcmodel=medlow'
```

注意事项（复刻时逐条对齐）：

1. `--with-multilib-generator` 内部含**不规则空白**（多处连续 2–4 个空格）。该串会原样进入二进制，`-v` 输出与 `strings` 命中都带这些空格。
2. `CFLAGS_FOR_TARGET=-Os    -mcmodel=medlow` 同样含 4 个连续空格。目标库（libgcc/newlib）以 `-Os` 构建，非 `-O2`。
3. `--with-arch=rv32gc --with-abi=ilp32`：默认 arch 含 F/D，默认 ABI 却是软浮点 `ilp32`。这是有意配置，不是笔误（详见 §4.1）。
4. `--src=.././gcc` 是 riscv-gnu-toolchain 构建脚本的产物，非标准 GCC configure 选项形态。
5. 构建路径 `/Users/mrs/riscv-gnu-toolchain/` 会被编译进二进制（详见 §6）。

---

## 2. 上游基线定位

### 2.1 GCC：`5115c7e44` 是上游 commit，且正是 15.2.0 发布点

【网查】`https://api.github.com/repos/gcc-mirror/gcc/commits/5115c7e44`：

- 存在，完整 SHA `5115c7e447fc07457443df874bf57840e8316d5f`
- 作者 Richard Biener (rguenther@suse.de)，日期 `2025-08-08T06:52:36Z`
- 提交信息首行：`Update ChangeLog and version files for release`

【网查】标签解引用链：
`https://api.github.com/repos/gcc-mirror/gcc/git/ref/tags/releases/gcc-15.2.0` → annotated tag object `dcd428f94ffb464418f996ffb70dfa398f5caa3f` → `https://api.github.com/repos/gcc-mirror/gcc/git/tags/dcd428f94ffb464418f996ffb70dfa398f5caa3f` → tag name `releases/gcc-15.2.0`，指向 commit `5115c7e447fc07457443df874bf57840e8316d5f`。

**结论（对复刻决策最重要的一条）**：WCH 的 GCC 源码树基线 = 上游 `releases/gcc-15.2.0` 标签所指的那个 commit，**不是** WCH 私有仓库的 commit。pkgversion 尾部的 `-dirty` 表示构建时工作区**存在未提交修改** —— 即 WCH 的 XW/中断等改动是以未入库补丁的形式打在该 release 上的。

【推断】`g` 前缀 + 9 位缩写 + `-dirty` 的形态，符合 `git describe --always --dirty` 在**无可达标签**（如浅克隆）情况下的输出再由构建脚本加 `g` 前缀。因此复刻时 pkgversion 应直接硬编码为字面量 `g5115c7e44-dirty`，不要依赖本地 git describe 重新生成。

【网查】`https://api.github.com/repos/riscv-collab/riscv-gnu-toolchain/commits/5115c7e447fc07457443df874bf57840e8316d5f` 返回 HTTP 422，未能在该仓库解析到此对象。因 §2.1 已在 gcc-mirror 得到确定性正解，此项不再深究。

### 2.2 binutils / gdb：无 git 串

【实测】`as`/`ld` 版本串为纯 `2.45`，`gdb` 为纯 `17.1`，均无 `g<hash>`。
【实测】`strings -a $B/riscv32-wch-elf-as | grep -aoE 'g[0-9a-f]{9}(-dirty)?'` 无命中；仅 `2.45` 命中。

【实测】排除误报：在 `cc1` 与 `gdb` 中另外出现的 `gffeddcbba`、`g000000000` 经取上下文核对，分别来自一张降序 ASCII 数据表（`~~}|{zyyxwvvutsrrqpoonmmlkjjihhgffeddcbba``_^^]\\[...`）和一段数字表（`:ANX000b00g00000000000000000000000000000`），**不是** git hash。全树唯一真实 git 串是 `g5115c7e44-dirty`。

---

## 3. `.comment` 与 DWARF producer 精确取样

样本源文件 `probe.c`：`int add(int a, int b) { return a + b; }`

### 3.1 `.comment` 逐字节

【实测】`$B/riscv32-wch-elf-gcc -O2 -c probe.c -o probe_O2.o` 与 `-O2 -g` 两次编译，`.comment` **完全相同**，长度 **32 字节**：

```
$B/riscv32-wch-elf-objdump -s -j .comment probe_O2.o
 0000 00474343 3a202867 35313135 63376534  .GCC: (g5115c7e4
 0010 342d6469 72747929 2031352e 322e3000  4-dirty) 15.2.0.
```

【实测】`$B/riscv32-wch-elf-objcopy --dump-section .comment=comment.bin probe_O2.o /dev/null` 后：

- 字节数 `32`
- md5 `83a117f6276bc1e35530c55b1451e9b3`
- 内容（`@` 代表 NUL）：`@GCC: (g5115c7e44-dirty) 15.2.0@`

即精确构成为：`0x00` + ASCII `GCC: (g5115c7e44-dirty) 15.2.0`（30 字符）+ `0x00`。

注：`objcopy -O binary --only-section=.comment` 对本节输出 0 字节（`.comment` 非 SHF_ALLOC），必须用 `--dump-section` 或 `readelf -x` 取字节，否则会误判为空。

### 3.2 DWARF

【实测】`$B/riscv32-wch-elf-objdump --dwarf=info probe_O2g.o`：

- `Version: 5`（DWARF 5）
- `DW_AT_producer` = `GNU C23 15.2.0 -mabi=ilp32 -misa-spec=2.2 -march=rv32imafdc_zmmul_zaamo_zalrsc_zca_zcd_zcf -g -O2`
- `DW_AT_comp_dir` = 编译时 cwd（本次为 scratchpad 路径）
- `DW_AT_language` = `29 (C11)`

**关键结论**：`DW_AT_producer` **不含** pkgversion，只含裸版本号 `15.2.0` 加展开后的命令行开关。因此：

- pkgversion 的唯一逐字节落点是 `.comment`（以及 `--version`/`-v` 的终端输出）；
- producer 随 `-march`/`-mabi`/优化级别变化，复刻一致性取决于**命令行与默认 arch 展开结果**一致，而非 pkgversion；
- `DW_AT_comp_dir` 是编译目录，与工具链身份无关，逐字节比对时须统一编译目录或使用 `-fdebug-prefix-map`。

---

## 4. specs 与 multilib

### 4.1 默认目标

【实测】`$B/riscv32-wch-elf-gcc -Q --help=target`（存档 `help_target.txt`，3313 字节）关键行：

```
-mabi=            ilp32
-march=           rv32imafdc_zmmul_zaamo_zalrsc_zca_zcd_zcf
-mcmodel=         medlow
-misa-spec=       2.2
-mstrict-align    [enabled]
-mriscv-attribute [enabled]
```

即 `--with-arch=rv32gc` 在 `-misa-spec=2.2` 下展开为 `rv32imafdc_zmmul_zaamo_zalrsc_zca_zcd_zcf`。默认 arch 含 F/D 而默认 ABI 为软浮点 `ilp32`。

【实测】`grep -ic xw help_target.txt` = `0` —— **XW 在 `--help=target` 中完全不出现**，没有任何 `-mxw` 类专用开关，XW 只能经 `-march` 进入。

【实测】`-mcpu=` 可选值仅上游条目（sifive-*、thead-c906、tt-ascalon-d8、xiangshan-nanhu），`-mtune=` 同理；**没有** QingKe/WCH 型号。即 WCH 未添加自定义 cpu/tune 表。

### 4.2 `-dumpspecs`

【实测】`$B/riscv32-wch-elf-gcc -dumpspecs > dumpspecs.txt`：142 行，md5 `800ded8813ca9c990ece27bbea501ac3`。

【实测】对 `wch|xw|qingke|mrs|nano|isa-spec|zmmul` 的过滤命中仅两处：

1. 第 2 行 `*asm:` 尾部 `%{misa-spec=*}` —— 这是 riscv-gnu-toolchain 常规内容，非 WCH 私货。
2. 第 77 行 `*multilib_reuse:`/multilib 选择串 —— 含全部 `march=...xw...` 分支，是 `--with-multilib-generator` 的机械展开结果。

**结论**：`-dumpspecs` 中**没有** WCH 手写的自定义 specs 片段。XW 在 specs 层面的全部痕迹都来自 multilib 表的自动生成，复刻时只要 multilib generator 串一致即自动一致。

### 4.3 `-print-multi-lib` 全表（22 项）

【实测】`$B/riscv32-wch-elf-gcc -print-multi-lib`：

| # | 目录 | march | abi |
|---:|---|---|---|
| 1 | `.` | (默认 rv32gc) | ilp32 |
| 2 | `rv32e/ilp32e` | rv32e | ilp32e |
| 3 | `rv32ec/ilp32e` | rv32ec | ilp32e |
| 4 | `rv32ec_xw/ilp32e` | rv32ec_xw | ilp32e |
| 5 | `rv32ec_zmmul/ilp32e` | rv32ec_zmmul | ilp32e |
| 6 | `rv32ec_zmmul_xw/ilp32e` | rv32ec_zmmul_xw | ilp32e |
| 7 | `rv32imac_zaamo_zalrsc_zba_zbb_zbc_zbs/ilp32` | 同名 | ilp32 |
| 8 | `rv32imac_zaamo_zalrsc_zba_zbb_zbc_zbs_xw/ilp32` | 同名 | ilp32 |
| 9 | `rv32imac_zaamo_zalrsc_xw/ilp32` | 同名 | ilp32 |
| 10 | `rv32imac_zaamo_zalrsc/ilp32` | 同名 | ilp32 |
| 11 | `rv32imc_zba_zbb_zbc_zbs_xw/ilp32` | 同名 | ilp32 |
| 12 | `rv32imc_zba_zbb_zbc_zbs/ilp32` | 同名 | ilp32 |
| 13 | `rv32imafc_zaamo_zalrsc/ilp32f` | 同名 | ilp32f |
| 14 | `rv32imafc_zaamo_zalrsc_zba_zbb_zbc_zbs/ilp32f` | 同名 | ilp32f |
| 15 | `rv32imafc_zaamo_zalrsc_xw/ilp32f` | 同名 | ilp32f |
| 16 | `rv32imafc_zaamo_zalrsc_zba_zbb_zbc_zbs_xw/ilp32f` | 同名 | ilp32f |
| 17 | `rv32imc/ilp32` | rv32imc | ilp32 |
| 18 | `rv32imc_xw/ilp32` | rv32imc_xw | ilp32 |
| 19 | `rv32imac_zaamo_zalrsc_zve32x_zve64x_zvl32b_zvl64b/ilp32` | 同名 | ilp32 |
| 20 | `rv32imac_zaamo_zalrsc_zve32x_zve64x_zvl32b_zvl64b_xw/ilp32` | 同名 | ilp32 |
| 21 | `rv32imac_zaamo_zalrsc_zba_zbb_zbc_zbs_zvbb_zve32x_zve64x_zvkb_zvl32b_zvl64b/ilp32` | 同名 | ilp32 |
| 22 | `rv32imac_zaamo_zalrsc_zba_zbb_zbc_zbs_zvbb_zve32x_zve64x_zvkb_zvl32b_zvl64b_xw/ilp32` | 同名 | ilp32 |

其中 10 项带 `_xw`（#4、6、8、9、11、15、16、18、20、22）。

**规范化陷阱**：configure 里写的是**无下划线**形态（`rv32ecxw`、`rv32imacxw`、`rv32imcxw`、`rv32imafcxw`），GCC 规范化后目录名一律是**带下划线**的 `_xw`，并且补齐了 `zaamo/zalrsc/zca` 等 2.2 spec 下的隐含子扩展。复刻时 configure 必须原样使用无下划线形态，目录名会自动变成带下划线形态。

### 4.4 multilib 目录树（一层）

【实测】`ls $R/lib/gcc/riscv32-wch-elf/15.2.0/`：`crtbegin.o` `crtend.o` `crti.o` `crtn.o` `libgcc.a` `libgcov.a` `include` `include-fixed` `install-tools` `plugin`，外加与 §4.3 表 #2–#22 同名的 21 个 multilib 目录。

【实测】`ls $R/riscv32-wch-elf/lib/`：`crt0.o`、`ldscripts/`、newlib 系列 `.a`、4 个 `.specs`，外加同样的 21 个 multilib 目录。

### 4.5 随包 `.specs` 文件

【实测】`find $R -name "*.specs"`：每个 multilib 目录各 4 个（`nano.specs`、`nosys.specs`、`semihost.specs`、`sim.specs`），加顶层 `$R/riscv32-wch-elf/lib/` 下 4 个。

【实测】逐个 `cat` 顶层 4 个文件：内容与上游 newlib / riscv-gnu-toolchain 标准版本一致 —— `nano.specs` 做 `-lc_nano/-lg_nano/-lm_nano` 替换并加 `-isystem =/include/newlib-nano`，`nosys.specs`/`semihost.specs`/`sim.specs` 分别接 `-lnosys`/`-lsemihost`/`-lsim`。`nano.specs` 末尾甚至保留了上游原样的注释 `# ??? Maybe put --gc-sections option in here?`。

**结论**：**无任何 WCH 自定义 specs 文件**。

---

## 5. XW / WCH 选项与助记符接受面

### 5.1 `-march` 接受矩阵

【实测】统一命令形式：`$B/riscv32-wch-elf-gcc -march=<M> -mabi=<A> -O2 -c probe.c -o /dev/null`，并配 `-print-multi-directory`。

| `-march` | abi | 结果 | 落到的 multilib 目录 |
|---|---|---|---|
| `rv32imac_xw` | ilp32 | 接受 | `rv32imac_zaamo_zalrsc_xw/ilp32` |
| `rv32imacxw` | ilp32 | 接受 | `rv32imac_zaamo_zalrsc_xw/ilp32` |
| `rv32ecxw` | ilp32e | 接受 | `rv32ec_xw/ilp32e` |
| `rv32ec_xw` | ilp32e | 接受 | `rv32ec_xw/ilp32e` |
| `rv32imcxw` | ilp32 | 接受 | `rv32imc_xw/ilp32` |
| `rv32imafcxw` | ilp32f | 接受 | `rv32imafc_zaamo_zalrsc_xw/ilp32f` |
| `rv32imac_xw1p0` | ilp32 | 接受 | `rv32imac_zaamo_zalrsc_xw/ilp32` |
| `rv32imac_xw2p0` | ilp32 | 接受 | 同上 |
| `rv32imac_xw2p2` | ilp32 | 接受 | 同上 |
| `rv32imac_xw3p0` | ilp32 | 接受 | 同上 |
| `rv32imacxw_zba_zbb_zbc_zbs` | ilp32 | 接受 | `rv32imac_zaamo_zalrsc_zba_zbb_zbc_zbs_xw/ilp32` |
| `rv32ecxw_zmmul` | ilp32e | 接受 | `rv32ec_zmmul_xw/ilp32e` |
| `rv32imac` | ilp32 | 接受 | `rv32imac_zaamo_zalrsc/ilp32` |
| `rv32gcxw` | ilp32 | 接受 | **`.`（默认库，非 XW 库）** |
| `rv32imafdcxw` | ilp32 | 接受 | **`.`（同上）** |

要点：

1. **带/不带下划线两种拼法在 15.2.0 上等价**，都落到同一 multilib。
2. **XW 版本号是 passthrough**：`xw1p0`/`xw2p0`/`xw2p2`/`xw3p0` 全部接受且落到同一个 multilib 目录（与 `wch-custom-isa-reference.md` §4.1 的结论一致）。
3. **含 D 的组合（`rv32gcxw`/`rv32imafdcxw`）虽被接受，但退回默认 multilib `.`**，即链接到**不含 XW 的**默认库。这与 ISA 文档 §3.2「D+C+XW 不能作为完整扩展组合使用」相呼应：工具链没有为含 D 的 XW 组合构建任何库。

【实测】负向对照（证明解析器确实在校验，不是照单全收）：

| `-march` | 结果 |
|---|---|
| `rv32imac_xq` | 拒绝：`extension 'xq' starts with 'x' but is unsupported non-standard111 extension` |
| `rv32imac_zzz` | 拒绝：`extension 'zzz' starts with 'z' but is unsupported standard extension` |
| `rv32imacqq` | 拒绝：`extension 'q' is unsupported standard single letter extension` |
| `rv32imac_xw9p9` | **接受** |

`xw9p9` 被接受再次印证版本号不校验（passthrough）。

### 5.2 `.riscv.attributes` 里的规范 XW 版本（复刻的逐字节关键）

【实测】`$B/riscv32-wch-elf-readelf -A a.o | grep Tag_RISCV_arch`：

| `-march` 输入 | 15.2.0 的 `Tag_RISCV_arch` |
|---|---|
| `rv32imac_xw` | `rv32i2p0_m2p0_a2p0_c2p0_zmmul1p0_zaamo1p0_zalrsc1p0_zca1p0_xw2p0` |
| `rv32imacxw` | 同上（与带下划线写法逐字节相同） |
| `rv32imac_xw2p2` | `..._zca1p0_xw2p2` |
| `rv32imac_xw3p0` | `..._zca1p0_xw3p0` |
| `rv32ecxw` | `rv32e2p0_c2p0_zca1p0_xw2p0` |
| `rv32imac`（对照） | `rv32i2p0_m2p0_a2p0_c2p0_zmmul1p0_zaamo1p0_zalrsc1p0_zca1p0` |

【实测】12.2.0 同项对照：`rv32imac_xw` → `rv32i2p0_m2p0_a2p0_c2p0_zmmul1p0_xw1p0`；`rv32imac_xw2p2` → `..._zmmul1p0_xw2p2`。

**重要差异**：裸 `xw`（不写版本）的默认展开，**12.2.0 是 `xw1p0`，15.2.0 是 `xw2p0`**。该串直接写进 `.riscv.attributes` 节，是逐字节比对必然暴露的差异点。复刻 15.2.0 必须让裸 `xw` 默认解析为 `2p0`。

### 5.3 汇编器助记符接受面与编码

【实测】命令形式：`printf '.text\n.option rvc\n<INSN>\n' | $B/riscv32-wch-elf-as -march=rv32imac_xw -mabi=ilp32`，回读用同工具链 `objdump -s -j .text` 与 `objdump -d`。

XW 16 位压缩形式（8 条，全部接受）：

| 助记符 | 测试语句 | 节内字节 | 半字 |
|---|---|---|---|
| `c.lbu` | `c.lbu a0,0(a1)` | `88 21` | `0x2188` |
| `c.lhu` | `c.lhu a0,0(a1)` | `8a 21` | `0x218a` |
| `c.sb` | `c.sb a0,0(a1)` | `88 a1` | `0xa188` |
| `c.sh` | `c.sh a0,0(a1)` | `8a a1` | `0xa18a` |
| `c.lbusp` | `c.lbusp a0,0(sp)` | `08 80` | `0x8008` |
| `c.lhusp` | `c.lhusp a0,0(sp)` | `28 80` | `0x8028` |
| `c.sbsp` | `c.sbsp a0,0(sp)` | `48 80` | `0x8048` |
| `c.shsp` | `c.shsp a0,0(sp)` | `68 80` | `0x8068` |

32 位自定义形式：

| 助记符 | 测试语句 | 节内字节 | 字 | 结果 |
|---|---|---|---|---|
| `mcpy` | `mcpy a0,a1,a2` | `0f 70 b5 60` | `0x60b5700f` | 接受 |
| `mrsl` | `mrsl a0,a1,a2,3` | `0b 85 c5 1e` | `0x1ec5850b` | 接受 |
| `mrslu` | `mrslu a0,a1,a2,3` | `0b 85 c5 1c` | `0x1cc5850b` | 接受 |
| `wexti` | `wexti a0,a1,a2,3` | `0b 85 c5 18` | `0x18c5850b` | 接受 |

**方法交叉验证**：ISA 文档给出的两个锚点 —— `c.lbu a0,0(a1)` 应为 `0x2188`、`mcpy a0,a1,a2` 应为 `0x60b5700f` —— 本次实测**逐字节复现**，说明探针方法与工具链一致，上表其余数据可信。

`wexti` 操作数形式修正：本次先试 `wexti a0,a1,3,5` 被拒（`Error: illegal operands`），逐一试探后确定正确形式为 `rd,rs1,rs2,imm`（`wexti a0,a1,a2,3`）。
【实测】`strings -a $B/riscv32-wch-elf-as` 的操作码表印证：`mcpy` 的操作数格式串是 `s,t,r`（三个源寄存器、**无 rd**），`mrslu`/`mrsl`/`wexti` 共用 `d,s,t,F5`。

### 5.4 门控关系（哪些需要 march 里带 xw）

【实测】以 `-march=rv32imac`（**不带** xw）重测：

| 助记符 | 无 xw 时 |
|---|---|
| `c.lbu`（及其余 7 条压缩形式） | **拒绝** |
| `mcpy` | **接受**，编码同为 `0x60b5700f` |

**结论**：XW 的 8 条 16 位压缩形式受 `xw` 扩展门控；`mcpy`/`mrsl`/`mrslu`/`wexti` 这 4 条 32 位自定义指令**不受 `xw` 门控**，在任意 RV32 march 下恒可汇编。复刻时二者是两套独立补丁点。

### 5.5 WCH 中断属性

【实测】先确定实际拼法：`grep -rhoE '__attribute__\s*\(\(\s*interrupt[^)]*\)\)' ref/wch-evt` 统计 —— `__attribute__((interrupt("WCH-Interrupt-fast"))` 出现 3263 次，`__attribute__((interrupt())` 87 次，带空格变体 7 次。全树字符串形式**只有** `"WCH-Interrupt-fast"` 一种（3278 次）。

【实测】以 `void __attribute__((<ATTR>)) h(void){g++;}` 编译（`-march=rv32imac_xw -mabi=ilp32 -O2`）并反汇编：

| 属性 | 序言/尾声 | 终止指令 | 默认告警 |
|---|---|---|---|
| `interrupt` | `addi sp,sp,-16` + `sw a4,12(sp)` + `sw a5,8(sp)`（保存 2 个寄存器），尾声还原 | `mret` | 无 |
| `interrupt("machine")` | 同上（与裸 `interrupt` 逐字节同形） | `mret` | 无 |
| `interrupt("WCH-Interrupt-fast")` | **无栈帧、无寄存器保存**，函数体直接开始 | `mret` | 无 |
| `interrupt("user")` | 同 `machine`，保存 2 个寄存器（a4/a5） | `uret` | 无 |
| `interrupt("supervisor")` | 同 `machine`，保存 2 个寄存器（a4/a5） | `sret` | 无 |

【实测】`user`/`supervisor`/`machine` 三者的序言与尾声**逐字节相同**，差异仅在最后一条返回指令（`00200073` / `10200073` / `30200073`）。本样本中被保存的是 a4、a5 两个寄存器；反汇编里第三条 `sw` 是 `sw a5,0(a4)`，属于对全局变量 `g` 的数据写回，不是寄存器保存 —— 用 `grep -c sw` 计数会把它误计入。
| `interrupt("wch-interrupt-fast")` | 退化为普通函数 | **`ret`** | 有 |
| `interrupt("WCH-Interrupt-Fast")` | 退化为普通函数 | **`ret`** | 有 |
| `interrupt("WCH-Interrupt")` | 退化为普通函数 | **`ret`** | 有 |

`WCH-Interrupt-fast` 的实测反汇编（全部 5 条指令）：

```
0: 00000737  lui  a4,0x0
4: 00072783  lw   a5,0(a4)
8: 0785      addi a5,a5,1
a: 00f72023  sw   a5,0(a4)
e: 30200073  mret
```

要点：

1. `WCH-Interrupt-fast` 生成 **HPE 快速中断序言** —— 完全不保存整型寄存器（硬件压栈），以 `mret` 返回。与 ISA 文档 §6.3 描述一致。
2. **字符串大小写敏感、必须逐字符精确**。任何近似拼写会被降级为普通函数并生成 `ret` —— 这是一个静默性很强的坑：ISR 会以 `ret` 返回，中断永不正确退出。
3. 近似拼写**确实会告警**（`warning: argument to 'interrupt' attribute is not '"user"', '"supervisor"', or '"machine"' [-Wattributes]`），且 `-Wattributes` 默认开启，无需 `-Wall`。但该告警文案**没有把 `WCH-Interrupt-fast` 列进合法值**，说明 WCH 只在接受逻辑里加了分支，未同步更新诊断串 —— 又一个本地补丁指纹。
4. 【实测】`WCH-Interrupt-fast` 在 `-march=rv32imac`（无 xw）下同样生效，**不受 XW 门控**。

---

## 6. 二进制 strings 侦察

### 6.1 构建路径泄漏

【实测】`strings -a $L/cc1 | grep -aE '^/(Users|home)/'`（`$L` = `$R/libexec/gcc/riscv32-wch-elf/15.2.0`）：

- 完整 configure 行（同 §1.1）
- `/Users/mrs/riscv-gnu-toolchain/output`
- `/Users/mrs/riscv-gnu-toolchain/output/lib/gcc/`
- `/Users/mrs/riscv-gnu-toolchain/output/lib/gcc/riscv32-wch-elf/15.2.0/include`、`include-fixed`
- `/Users/mrs/riscv-gnu-toolchain/output/lib/gcc/riscv32-wch-elf/15.2.0/../../../../riscv32-wch-elf/include`（及 `c++/15.2.0`、`backward`、`riscv32-wch-elf`、`c++/v1` 各子路径）
- `/Users/mrs/riscv-gnu-toolchain/output/riscv32-wch-elf`

【实测】`as`/`ld`：泄漏的是 **binutils 源码树逐文件路径**，形如 `/Users/mrs/riscv-gnu-toolchain/binutils/bfd/*.c`（`archive.c`、`bfd.c`、`elfnn-riscv.c`、`elfxx-riscv.c`、`elflink.c` 等数十个），来自断言宏中的 `__FILE__`。

【实测】`ld` 另含运行期搜索路径：
`SEARCH_DIR("/Users/mrs/riscv-gnu-toolchain/output/riscv32-wch-elf/lib");`
以及 `/Users/mrs/riscv-gnu-toolchain/output/riscv32-wch-elf/bin`、`.../lib`。

**对复刻的影响**：这些路径是编译期常量，逐字节一致要求复刻构建使用**完全相同的源码树路径与 prefix**（macOS 侧为 `/Users/mrs/riscv-gnu-toolchain`，Linux 侧为 `/home/wch/riscv-gnu-toolchain`，见 §7）。否则 `cc1`/`as`/`ld` 二进制无法逐字节相同，且 `ld` 的默认搜索路径行为也会不同。

### 6.2 WCH 私有痕迹

【实测】`strings -a $L/cc1 | grep -aiE 'mrs|wch|qingke'` 去除 `wchar`/`Wchar-*` 等噪声后，真实命中：

- `WCH-Interrupt-fast`（中断属性字符串，位于 cc1）
- `riscv32-wch-elf`（triple）
- configure 行与 `/Users/mrs/...` 路径

**未命中**：`qingke` 全树零命中；`as`/`ld` 中除 triple 与构建路径外无 WCH 私有标识。

【实测】`strings -a $L/cc1 | grep -a "non-standard"` 发现一条**拼写错误的格式串**：

```
%<-march=%s%>: extension %qs starts with 'x' but is unsupported non-standard111 extension
```

上游 GCC 该串为 `... unsupported non-standard extension`，此处多出 `111`。这是 WCH 本地未提交补丁留下的最硬指纹之一，与 pkgversion 的 `-dirty` 后缀相互印证。复刻若以纯净上游构建，此错误信息将不同。

【实测】`as` 的操作数格式字符表中出现 `Ct,Wcb(Cs)`、`Ct,Wch(Cs)` —— `W` 前缀是 WCH 为 XW 访存形式新增的操作数类型字符，属于 `riscv-opc.c`/`tc-riscv.c` 层面的本地改动。

---

## 7. 库存清单

### 7.1 `lib/gcc/riscv32-wch-elf/15.2.0/`

【实测】`ls`：`crtbegin.o`、`crtend.o`、`crti.o`、`crtn.o`、`libgcc.a`、`libgcov.a`，目录 `include/`、`include-fixed/`、`install-tools/`、`plugin/`，外加 21 个 multilib 子目录（名称见 §4.3）。

### 7.2 sysroot `riscv32-wch-elf/lib/`

【实测】`ls`：

- 启动件：`crt0.o`
- newlib 常规：`libc.a`、`libg.a`、`libm.a`、`libnosys.a`、`libgloss.a`、`libsim.a`、`libsemihost.a`
- nano 变体：`libc_nano.a`、`libg_nano.a`、`libm_nano.a`、`libgloss_nano.a`
- C++：`libstdc++.a`、`libstdc++exp.a`、`libsupc++.a`、`libstdc++.a-gdb.py`、`libstdc++.la`、`libsupc++.la`、`libstdc++exp.la`、`libstdc++.modules.json`
- specs：`nano.specs`、`nosys.specs`、`semihost.specs`、`sim.specs`
- `ldscripts/`
- 21 个 multilib 子目录

### 7.3 WCH 专有库（非上游 newlib/GCC 组件）

【实测】`find $R -name "*.a" | xargs -n1 basename | sort -u` 后逐个定位份数：

| 库 | 份数 | 说明 |
|---|---:|---|
| `libIQmath_RV32.a` | 10 | WCH 定点数学库，配套头 `IQmath_RV32.h` |
| `libwchriscvnn.a` | 8 | WCH RISC-V 神经网络库 |
| `libprintf.a` | 16 | printf 变体 |
| `libprintfloat.a` | 16 | 带浮点 printf 变体 |
| `libshlib.a` | 16 | 份数与 printf 变体一致 |
| `libshflib.a` | 16 | 同上 |

份数少于 multilib 总数（22）说明这些库**并非对所有 multilib 都构建**（例如 `libIQmath_RV32.a` 仅 10 份，`libwchriscvnn.a` 仅 8 份）。

另有 `$R/lib/libriscv32-wch-elf-sim.a`（gdb 模拟器库，上游组件）。

**未发现** `libisr` 或其他以中断为名的专有库。

### 7.4 头文件

【实测】`grep -rla "wch.cn" $R/riscv32-wch-elf/include` 唯一命中：`riscv32-wch-elf/include/IQmath_RV32.h`。

其头部（【实测】`head -20`）：

```
/* 2021.09.10
*****************************************
**   Copyright  (C)  WCH  2001-2021    **
**   Web:      http://wch.cn           **
*****************************************
**  Fixed Point Math lib for RISC-V    **
**  IDE: MounRiver Studio              **
*****************************************
```

（文件内另有一行 GBK 编码中文注释，在 UTF-8 环境下显示为乱码。）

**结论**：sysroot 头目录中**唯一**的 WCH 专有头文件是 `IQmath_RV32.h`；其余均为 newlib / libstdc++ 上游头。（注：直接 `grep -ril "wch"` 会因 `wchar` 产生大量假阳性，须用 `wch.cn`/`MounRiver` 等特征串过滤。）

### 7.5 打包异常：`lib.zip`

【实测】`$R/riscv32-wch-elf/lib.zip` 存在。`unzip -l` 显示其内是一份 `lib/` 树的**部分副本**（含 `libc_nano.a`、`libm.a`、`libm_nano.a`、`libsupc++.a`、`libstdc++exp.a`、`libgloss.a`、`libnosys.a`、`libsim.a`、4 个 `.specs`、若干 `.la`/`.json`，以及一批**空的** multilib 目录条目）。

时间戳异常：zip 内条目日期为 `02-09-2026`，而 `bin/` 下主要二进制为 `Jun 30 19:03`。【推断】这是早期构建残留的打包产物被一并发布，非当前构建的一部分；复刻时不必复现，但比对文件清单时需要意识到它的存在。

---

## 8. 源码与许可随包情况

【实测】`find $R -iname "*licen*" -o -iname "COPYING*" -o -iname "*.tar*" -o -iname "*GPL*" -o -iname "*source*offer*"`：

- 唯一命中：`share/man/man7/gpl.7`

【实测】`ls -R $R/share`：`gcc-15.2.0/python/libstdcxx/`（GDB pretty-printer）、`gdb/syscalls/`、`gdb/system-gdbinit/`、`info/`（18 个 `.info`）、`man/man1|man3|man5|man7`。

即：**无** `licenses/` 目录、**无** COPYING/COPYING3、**无** 书面 source offer 文件、**无** 任何 `.tar*` 或源码目录。仅有 GCC 自带 man 页形式的 `gpl.7`。

（依任务约定，此节只记录存在性，不作评述。）

---

## 9. 次对象对比表

| 项 | darwin-arm64 15.2.0（主） | darwin-arm64 12.2.0 | darwin-arm64 8.2.0 | linux-amd64 15.2.0 |
|---|---|---|---|---|
| 可执行性 | 原生 arm64 | 原生 arm64 | x86_64，经 Rosetta 可运行 | ELF x86-64；阶段 5 在 linux/amd64 容器实机运行 |
| GCC 版本串 | `(g5115c7e44-dirty) 15.2.0` | `(xPack GNU RISC-V Embedded GCC arm64) 12.2.0` | `(xPack GNU RISC-V Embedded GCC x86_64) 8.2.0` | 同主对象（容器实测） |
| triple | `riscv32-wch-elf` | `riscv-wch-elf` | `riscv-none-embed` | `riscv32-wch-elf` |
| binutils | 2.45 | 2.38 | 2.32 | 2.45（容器实测） |
| newlib | 4.5.0 | 4.2.0 | 3.0.0 | 4.5.0（读 `_newlib_version.h`） |
| gdb | 17.1 | 12.1 | 8.3 | 17.1（版本身份；gdb 行为不在范围） |
| 构建体系 | riscv-gnu-toolchain | xPack (`riscv-none-elf-gcc-xpack.git`) | xPack (`riscv-none-embed-gcc-...`，源自 sifive/freedom-tools) | riscv-gnu-toolchain |
| 构建用户/路径 | `/Users/mrs/riscv-gnu-toolchain/` | `/Users/mrs/Work/riscv-none-elf-gcc-xpack.git/` | `/Users/wch/Work/riscv-none-embed-gcc-10.2.0-1.2/` | `/home/wch/riscv-gnu-toolchain/` |
| `--with-arch` | `rv32gc` | `rv32imac` | `rv32imac` | `rv32gc` |
| `--with-abi` | `ilp32` | `ilp32` | `ilp32` | `ilp32` |
| `--with-isa-spec` | `2.2` | `2.2` | （未给） | `2.2` |
| `--with-pkgversion` | `g5115c7e44-dirty` | `'xPack GNU RISC-V Embedded GCC arm64'` | `'xPack GNU RISC-V Embedded GCC x86_64'` | `g5115c7e44-dirty` |
| multilib 条数 | 22 | 43 | 23 | 22（文件系统实测 21 个 multilib 目录 + 默认 `.`） |
| `_xw`（带下划线） | 接受 | 接受 | **拒绝**（`unsupported ISA substring '_xw'`） | 接受（阶段 5 实测） |
| `xw`（无下划线） | 接受 | 接受 | 接受 | 接受（阶段 5 实测） |
| 裸 `xw` 默认版本 | `xw2p0` | `xw1p0` | 未测 | `xw2p0`（阶段 5 实测） |
| `c.lbu` 编码 | `0x2188` | `0x2188` | `0x2188` | `0x2188`（阶段 5 实测） |
| `mcpy`/`mrsl`/`mrslu`/`wexti` | 全部支持 | 全部支持，编码与 15.2.0 **逐字节相同** | **不支持**（`unrecognized opcode`） | 全部支持，定向编码与主对象逐字节相同 |
| `.comment` | `\0GCC: (g5115c7e44-dirty) 15.2.0\0` | `\0GCC: (xPack GNU RISC-V Embedded GCC arm64) 12.2.0\0` | `\0GCC: (xPack GNU RISC-V Embedded GCC x86_64) 8.2.0\0` | 同主对象【实测】 |

补充说明：

- 【实测】8.2.0 的 configure 中源码目录名为 `riscv-gcc-10.2.0-1.1`，而 GCC 版本是 8.2.0 —— 前者是 xPack 打包版本号，二者不矛盾但易误读。
- 【实测】8.2.0 虽不识别 `mcpy` 等 32 位自定义指令，但 XW 压缩形式已支持且 `c.lbu` 编码与新版一致 → XW 压缩指令的引入早于 32 位自定义指令；后者在 8.2.0 与 12.2.0 之间加入。
- 【实测】linux-amd64 15.2.0 与 darwin-arm64 15.2.0 的 configure 行，在把构建前缀 `/home/wch/` 与 `/Users/mrs/` 都归一为 `@PREFIX@` 后，`diff` 结果为**完全一致**（归一后各 1280 字节）。两者 `--with-pkgversion` 同为 `g5115c7e44-dirty`。
  阶段 5 已在 linux/amd64 容器实机补验：两平台 `.comment` 均为同一 32 字节串，march/8+4 编码/独立 GAS mapping/缺陷与 35-case GAS 诊断定向矩阵逐字节一致；证据见 `analysis/toolchain/phase5-linux.md` §4。
- 【实测】`darwin-arm64/9.3.1/` 是当前从 WCH macOS/Apple Silicon 平台包抽出的工具链；其宿主可执行体是 x86_64 Mach-O（在 Apple Silicon 上经 Rosetta 运行），`bin/arm-none-eabi-gcc --version` 为 `arm-none-eabi-gcc (xPack GNU Arm Embedded GCC, 64-bit) 9.3.1 20200408 (release)`，target 为 `arm-none-eabi`。宿主平台与 target 是正交维度：WCH 的 Linux 平台也有对应的 `arm-none-eabi` target 工具链；当前仓库给定的 Linux V250 参考输入只含 `RISC-V Embedded GCC15`，因此本报告没有盘点 Linux-host 的 ARM 工具链，绝不能把该 target 解释为 Mac 独有。

---

## 10. 未决问题

1. **`-dirty` 补丁集不可得**。pkgversion 明示 WCH 的 GCC 源码树含未提交修改，公开产物中无源码、无补丁、无 source offer（§8）。已确认的本地改动指纹至少包括：XW 扩展注册、`WCH-Interrupt-fast` 属性、`as` 的 `W*` 操作数类型、`non-standard111` 拼写错误。**要做到逐字节一致，必须先把这批补丁逆向重建**；本报告只界定了它们的可观测边界，未做重建。
2. **构建路径硬编码**。`cc1`/`as`/`ld` 内嵌 `/Users/mrs/riscv-gnu-toolchain`（Linux 版为 `/home/wch/...`）。逐字节复刻要求在完全相同的绝对路径下构建。此外二进制是否可复现还取决于宿主编译器版本、`-frandom-seed`、时间戳等因素 —— **本次未验证宿主侧可复现性**。
3. **`libIQmath_RV32.a` / `libwchriscvnn.a` / `libprintf*.a` / `libsh*lib.a` 的来源未知**。它们不是 newlib 或 GCC 组件，随包无源码。若复刻目标包含这些库，属于独立工作项。`libshlib.a`/`libshflib.a` 的功能本次未探查。
4. **XW 版本默认值变更的动因未知**。裸 `xw` 从 12.2.0 的 `xw1p0` 变为 15.2.0 的 `xw2p0`（§5.2）。该差异直接影响 `.riscv.attributes` 字节，但变更依据（是否对应硅片能力变化）无从判断。
5. **`rv32gcxw`/`rv32imafdcxw` 被接受却退回默认 multilib**（§5.1）。工具链未为含 D 的 XW 组合构建库，也未给出任何诊断。这是静默行为，实际影响（链接到不含 XW 的库）需要在具体工程中评估。
6. **`lib.zip` 的用途未确认**（§7.5）。时间戳早于主二进制，疑似历史残留。
7. **linux-amd64 15.2.0 的静态分析缺口已在阶段 5 关闭**。linux/amd64 容器实机确认 `.comment` 精确 32 字节，并完成 march 接受面、8+4 助记符编码、独立 GAS 默认 ISA spec/mapping symbol、缺陷四探针和 GAS 门控诊断对 Darwin 官方的逐字节定向对拍；见 `analysis/toolchain/phase5-linux.md` §4。该结论限定于已列探针面。
8. **当前只盘点了 macOS-host 的 `arm-none-eabi` 9.3.1，未盘点 Linux-host 的对应工具链**。`darwin-arm64`/`linux-amd64` 描述宿主，`arm-none-eabi` 描述 target；WCH 两个平台均可提供该 target。当前 Linux V250 参考输入只含 RISC-V GCC15，不能据此声称 Linux 没有 ARM target。ARM target 不在本次 RISC-V 复刻范围；如后续覆盖，需按宿主平台分别取官方包作为 gate。
9. **`riscv32-wch-elf-run`（模拟器）与 `gdb` 的 WCH 定制程度未评估**。本次只取版本串，未测其对 XW 指令的执行/反汇编支持。

---

## 附录：产物与复现命令

试编译产物目录：`/private/tmp/claude-501/-Users-apple-Projects-openwch/b28c0730-f239-4670-bbaf-cd987694f5f7/scratchpad/tcprobe/`

| 文件 | 内容 |
|---|---|
| `probe.c` | `int add(int a, int b) { return a + b; }` |
| `probe_O2.o` / `probe_O2g.o` | `-O2` / `-O2 -g` 编译产物 |
| `comment.bin` | `.comment` 精确 32 字节，md5 `83a117f6276bc1e35530c55b1451e9b3` |
| `dumpspecs.txt` | `-dumpspecs` 存档，142 行，md5 `800ded8813ca9c990ece27bbea501ac3` |
| `multilib.txt` | `-print-multi-lib` 全表，22 行 |
| `help_target.txt` | `-Q --help=target` 存档，3313 字节 |
| `darwin_cfg.txt` / `linux_cfg.txt` | 两平台 configure 行；`d.norm`/`l.norm` 为归一化后版本（各 1280 字节，内容相同） |

核心复现命令：

```sh
B=/Users/apple/Projects/openwch/ref/gcc/darwin-arm64/15.2.0/bin

# 版本与配置
$B/riscv32-wch-elf-gcc -v
$B/riscv32-wch-elf-as --version

# .comment 精确字节
$B/riscv32-wch-elf-gcc -O2 -c probe.c -o probe_O2.o
$B/riscv32-wch-elf-objcopy --dump-section .comment=comment.bin probe_O2.o /dev/null
xxd comment.bin

# multilib 与 XW 归属
$B/riscv32-wch-elf-gcc -print-multi-lib
$B/riscv32-wch-elf-gcc -march=rv32imacxw -mabi=ilp32 -print-multi-directory

# XW 编码回读（锚点：应为 0x2188）
printf '.text\n.option rvc\nc.lbu a0,0(a1)\n' > t.s
$B/riscv32-wch-elf-as -march=rv32imac_xw -mabi=ilp32 -o t.o t.s
$B/riscv32-wch-elf-objdump -s -j .text t.o

# 规范 XW 版本
$B/riscv32-wch-elf-readelf -A probe_O2.o | grep Tag_RISCV_arch
```
