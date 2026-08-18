# wch-evt

本目录收集 WCH 不同处理器代际的 EVT 文件夹。每个 EVT 文件夹包含多个示范项目，文件夹名采用“处理器代际_处理器型号”的形式，例如 `QingkeV2AC_CH32V00x`、`QingkeV3B_CH32V205`。

其中 `V2AC` 表示同一目录同时收集 QingKe V2A 和 V2C 的资料；`V4BC` 同理表示 V4B 和 V4C 的合并目录。目录中的 `PUB`、启动文件、芯片型号列表和工程配置共同用于确认平台；微架构及指令集以 QingKe 处理器手册和 [`../wch-isa-research`](../wch-isa-research) 的研究结果为准。

## 架构介绍

| 文件夹 | 平台 | 微架构 | 备注 |
|---|---|---|---|
| `QingkeV2AC_CH32V00x` | CH32V00x | QingKe V2A / V2C | V2A 为 `RV32EC`，V2C 为 `RV32E` 加乘法子集 `Zmmul`；两者使用 WCH `XW` 扩展和 16 个整数寄存器，运行在 M 模式。当前目录中的 GPIO 工程配置更接近 V2C。 |
| `QingkeV3A_CH32V103` | CH32V103 | QingKe V3A | `RV32IMAC`；V3A 不提供 `XW`。手册中的 A 子集对 `LR/SC` 有简化实现，不能仅凭 `A` 字母推断为完整通用原子操作能力。 |
| `QingkeV3B_CH32V205` | CH32V205 | QingKe V3B | `RV32I[M]C[B]` 加 `XW`；部分型号的 M 支持有差异。V3B 的 MRS、延时类指令和 PIOC/RISC8B 属于 WCH 专有/配套能力，不能简单等同于标准 RISC-V 扩展。 |
| `QingkeV3C_CH587_EVT` | CH587 | QingKe V3C | `RV32IMCB` 加 `XW`；不含 F 和 A。目录还包含 BLE/ROM 资料，选用 LED 工程作为最小整数冒烟测试。 |
| `QingkeV3F_CH32X315` | CH32X315 | QingKe V3F | `RV32IMAFCB` 加 `XW`；核心具备 F 浮点能力，但当前选定的 GPIO 工程使用软浮点 ABI，因此不覆盖 F 指令。 |
| `QingkeV3F_CH32X315_EVT` | CH32X315 | QingKe V3F | 与上一个 V3F 文件夹是两份近乎相同的 CH32X315 EVT 内容；工程源码和配置相同，主要差异在个别说明书文件名，故分别计入覆盖范围。 |
| `QingkeV4BC_CH32V20x` | CH32V20x | QingKe V4B / V4C | `RV32IMAC` 加 `XW`；V4B 和 V4C 的资料在此合并。V4B 的 PMP 实现区域数为 0，V4C 为 4，具体芯片仍需结合型号确认。 |
| `QingkeV4F_CH32V30x` | CH32V30x | QingKe V4F | `RV32IMACF` 加 `XW`；F 为单精度浮点，工程可使用 `ilp32f`。V4F 的 PMP 和异常嵌套能力也不同于 V4B/V4C。 |
| `QingkeV5F_CH32H417EVT` | CH32H417 | QingKe V5F | 手册记为 `RV32IMABCFX`，其中 `X` 对应 WCH 自定义指令空间/XW；具备 A、B、F 和单精度硬浮点，另有 ITCM/DTCM、Cache 等 V5 特性。 |

这里的 ISA 记法说明如下：

- `C` 是标准压缩指令；`XW` 是 WCH 的自定义压缩字节/半字加载、存储指令，V2 中包括 `c.lbu`、`c.lhu`、`c.sb`、`c.sh` 及其栈相对形式。
- `M`、`A`、`B`、`F` 按工程或手册中的标准扩展字母记录；V2C 的乘法能力应写成 `Zmmul`，不能把它写成完整 `M`。
- 工程中的 `-march`/扩展勾选项表示该工程请求的编译目标，不单独证明所有列出的指令在每一颗同系列芯片上都可执行。尤其是 `XW`、MRS、PMP 和 WCH 中断 ABI 都需要与实际芯片、启动文件及工具链配套。

## 编译项目

EVT 工程主要是 MounRiver Studio 的托管工程，工程根目录中的 `.cproject` 或 `.wvproj` 是 ISA 配置的直接证据。可以先用下面的命令查看 `EXAM` 下的项目类别：

```sh
cd ref/wch-evt
find . | grep EXAM | cut -f4 -d/ | sort -u
```

下面每个 EVT 根目录至少选择一个项目。扩展指令列以所选工程的 `.cproject/.wvproj` 配置为准；`PMP` 是特权 CSR/硬件能力而不是一个 RISC-V 字母扩展，`F(single)` 表示单精度 F 扩展及 `ilp32f` ABI。

| 项目名 | 平台 | 微架构 | 覆盖扩展指令（如有） | 备注 | 目录 |
|---|---|---|---|---|---|
| `GPIO_Toggle` | CH32V00x | QingKe V2A / V2C | `C`、`XW`、`Zmmul`（工程配置） | `.cproject` 请求 `RV32E/ilp32e`；这是 V2C 风格配置，V2A 测试时应去掉 `Zmmul`；源码同时覆盖 WCH 快速中断入口。 | `./QingkeV2AC_CH32V00x/EXAM/GPIO/GPIO_Toggle` |
| `GPIO_Toggle` | CH32V103 | QingKe V3A | `M`、`A`、`C` | `.cproject` 请求 `RV32I`、`ilp32`、M/A/C，未启用 `XW`；A 的简化 `LR/SC` 语义见架构表。 | `./QingkeV3A_CH32V103/EXAM/GPIO/GPIO_Toggle` |
| `PIOC_1_Wire` | CH32V205 | QingKe V3B | `M`、`B`、`C`、`XW`（RISC-V 工程配置） | 工程还包含独立的 PIOC/RISC8B 程序（`Asm/RGB1W.ASM`、`RGB1W.BIN`、`RGB1W.LST`）；它不是 RISC-V 的 XW 扩展。RISC-V 主控工程可导入构建，PIOC 汇编批处理文件是 Windows 工具链流程。 | `./QingkeV3B_CH32V205/EXAM/PIOC/PIOC_1_Wire` |
| `LED` | CH587 | QingKe V3C | `M`、`B`、`C`、`XW` | `.cproject` 请求 `RV32I`、M/B/C/XW；该工程是最小整数冒烟测试，目录内已有 `obj/LED.hex`，但该文件是随 EVT 包提供的既有产物，不作为本次主机重新编译结果。 | `./QingkeV3C_CH587_EVT/EXAM/LED` |
| `GPIO_Toggle` | CH32X315 | QingKe V3F | `M`、`A`、`B`、`C`、`XW` | `.cproject/.wvproj` 启用整数 M/A/B/C/XW，未启用 F ABI；因此验证的是 V3F 的整数路径，不是 F 浮点指令。 | `./QingkeV3F_CH32X315/EXAM/GPIO/GPIO_Toggle` |
| `GPIO_Toggle` | CH32X315 | QingKe V3F | `M`、`A`、`B`、`C`、`XW` | 与上一行对应的第二份 EVT 根目录；工程配置和源码相同，保留独立行以证明两个文件夹都已覆盖。 | `./QingkeV3F_CH32X315_EVT/EXAM/GPIO/GPIO_Toggle` |
| `PMP` | CH32V20x | QingKe V4B / V4C | `M`、`A`、`C`、`XW`（工程配置）；PMP | `User/main.c` 实际写入 `pmpaddr0..3` 和 `pmpcfg0`。由于目录合并了 V4B/V4C，PMP 区域数要按实际芯片确认；V4B 可能没有可用 PMP 区域。 | `./QingkeV4BC_CH32V20x/EXAM/PMP/PMP` |
| `FPU` | CH32V30x | QingKe V4F | `M`、`A`、`C`、`F(single)`、`XW` | `.cproject` 使用单精度 F 和 `ilp32f`，源码包含硬件浮点计算；启动文件、FS 状态和实际芯片必须与硬浮点 ABI 一致。 | `./QingkeV4F_CH32V30x/EXAM/FPU/FPU` |
| `FPU_V5F` | CH32H417 | QingKe V5F | `M`、`A`、`B`、`C`、`F(single)`、`XW` | `.wvproj` 明确选择 `CH32H417` 的 `V5F` kernel，使用单精度硬浮点；不要误选同目录下的 V3F 兄弟工程。该行也覆盖 V5 的 B 和 V5 工程配置。 | `./QingkeV5F_CH32H417EVT/EXAM/CPU/FPU/FPU/V5F` |

### 编译和验证口径

1. 对普通 RISC-V 示例，在 MounRiver Studio 中导入表内目录，使用工程自带的启动文件、链接脚本和 `.cproject/.wvproj` 目标配置后执行 Build。此类工程不是统一的顶层 `Makefile` 工程，不能用一个通用的 `make` 命令替代所有项目。
2. `PIOC_1_Wire` 的 RISC-V 主控部分和 PIOC/RISC8B 部分是两条构建链；`RGB1W.BIN/.LST` 是 EVT 包中的 PIOC 产物，不能把它们算作主机 GCC 已编译的 RISC-V 指令。
3. V5F 工程位于多级 `EXAM/CPU/FPU/FPU/V5F` 路径，工程名和 `kernelName` 都要确认是 `V5F`；V3F 和 V5F 的源码布局相似，但 ISA/启动支持不同。
4. 选择工程是为了让每个 EVT 根目录都有最小可复现覆盖，并不意味着一个 GPIO、LED 或 FPU 示例能覆盖该微架构的全部指令。需要验证某条自定义指令时，应再选择包含该指令源码或汇编测试的专门项目。

### `.wvproj` 转换为 Makefile

仓库提供 [`tools/wvproj_to_make.py`](tools/wvproj_to_make.py)，把单个 `.wvproj` 转换成独立输出目录中的 `Makefile` 和 `config.json`。转换器不会改写 EVT 源码或工程目录；它会读取 `.wvproj` 中的目标 ISA、ABI、优化/警告/调试、汇编器、头文件路径、宏定义、链接脚本、库、specs、map/list/hex 配置，并收集 `.project` 的链接目录及 `.cproject` 的源文件排除项。

部分 EVT 的 `.wvproj` 是 MRS 加密的短文件，转换器会明确回退到同目录的 `.cproject`；没有可读 `.cproject` 时会报错，而不会猜测配置。默认工具链根目录是 `../gcc`，并按主机自动选择 `darwin-arm64` 或 `linux-amd64`；可用 `--gcc-root`、`--platform`、`--gcc-major` 覆盖默认选择。也可以直接传入具体 GCC 可执行文件的路径；`--compiler-path`（或别名 `--compiler`）优先级高于 `--platform` 和自动平台选择，生成的 Makefile 会直接使用该编译器及其所在目录的配套工具。工程元数据声明的 GCC 主版本不认识 WCH `XW` 和 Zb/Zmmul 的 `-march` 字符串时，自动平台选择会升级到当前平台中最低的兼容版本；显式给出 `--gcc-major` 或 `--compiler-path` 时不做这种替换，完全按指定的工具链执行。

生成的 `-march` 拼法跟随选中工具链的主版本，与 MounRiver 自身的拼装规则一致：GCC 12/15 追加 `_zba_zbb_zbc_zbs`、`_zmmul`、`_xw`（GCC 15 另加向量密码分量）；GCC 8 只追加裸 `xw`（8.2.0 拒绝任何带 `_` 的写法），并且直接丢弃工程勾选的 B 与 Zmmul——GCC 8 对这两者没有任何可被接受的拼法。

「与 MounRiver 自身的拼装规则一致」的一手证据是 MRS 2 的 `ref/MounRiver Studio 2.app/Contents/Resources/app/extensions/mrs-team.mrs-vscode/out/extension.js`（3478019 字节）偏移 **1953620** 处的 `-march` 拼装逻辑：`isWCHToolchain(...)` 之后先判 `WCH_Toolchain_GCC12 || WCH_Toolchain_GCC15`，**只有那一支**才追加 `_zba_zbb_zbc_zbs`（B）、`_zmmul` 与带下划线的 `_xw`；其 `else` 支（即 GCC 8）**只有** `extra_compressed_extension === true && (t += "xw")`，B 与 Zmmul 在该支中根本不出现。逐字节摘录另存于 `tmp/toolchain_8.2.0/evidence/s1/buildability/mrs-march-builder.txt` L5–L6（该目录 gitignored，属工具链工作流证据）。

`-mabi` 与基串两侧一致。因此 `--gcc-major 8` 确实调用 8.2.0，但对请求了 B/Zmmul 的工程，产物的 ISA 面窄于工程配置所请求的范围。

先应用随目录提供的可重复补丁，再转换和编译：

```sh
cd ref/wch-evt
./patches/apply.sh
python3 tools/wvproj_to_make.py \
  ./QingkeV2AC_CH32V00x/EXAM/GPIO/GPIO_Toggle/GPIO_Toggle.wvproj \
  --output .build/gpio-v2
make -C .build/gpio-v2 -j2 all
```

例如强制使用 MRS2 提取的 GCC 15 编译器时：

```sh
python3 tools/wvproj_to_make.py \
  ./QingkeV2AC_CH32V00x/EXAM/GPIO/GPIO_Toggle/GPIO_Toggle.wvproj \
  --compiler-path ../gcc/darwin-arm64/15.2.0/bin/riscv32-wch-elf-gcc \
  --platform linux-amd64 \
  --output .build/gpio-v2-gcc15
```

上例中 `--platform linux-amd64` 不会改变显式编译器；Makefile 的 `CC` 使用传入的 `riscv32-wch-elf-gcc`。

`PIOC_1_Wire` 的 `.ASM` 是独立 PIOC/RISC8B 汇编，转换器不会把它误交给 RISC-V GCC；同一工程中的 RISC-V C/启动文件仍会正常编译。V4BC 的 `PMP` 示例原始 `.cproject` 缺少 `CH32V20x_D8W` 定义，补丁 [`patches/0001-pmp-select-ch32v20x-d8w.patch`](patches/0001-pmp-select-ch32v20x-d8w.patch) 只修正工程配置；补丁 [`patches/0002-fix-eight-wvproj-builds.patch`](patches/0002-fix-eight-wvproj-builds.patch) 修复全量校验中发现的 8 个 EVT 工程问题。两个补丁都由 [`patches/apply.sh`](patches/apply.sh) 自动、可重复地应用。

本次在 Darwin arm64 主机上按同一流程实际编译了表中的全部项目，均生成 ELF 并通过 Makefile 的 `size` 目标：

| 项目 | 输出目录 | 选用工具链 | `-march` / `-mabi` |
|---|---|---|---|
| V2AC `GPIO_Toggle` | `.build/readme-v2` | GCC 12.2 `riscv-wch-elf-` | `rv32ec_zmmul_xw` / `ilp32e` |
| V3A `GPIO_Toggle` | `.build/readme-v3a` | GCC 8.2 `riscv-none-embed-` | `rv32imac` / `ilp32` |
| V3B `PIOC_1_Wire` | `.build/readme-v3b` | GCC 12.2 `riscv-wch-elf-` | `rv32imc_zba_zbb_zbc_zbs_xw` / `ilp32` |
| V3C `LED` | `.build/readme-v3c` | GCC 12.2 `riscv-wch-elf-` | `rv32imc_zba_zbb_zbc_zbs_xw` / `ilp32` |
| V3F `GPIO_Toggle` | `.build/readme-v3f` | GCC 15.2 `riscv32-wch-elf-` | `rv32imac_zba_zbb_zbc_zbs_xw` / `ilp32` |
| V3F EVT `GPIO_Toggle` | `.build/readme-v3f-evt` | GCC 15.2 `riscv32-wch-elf-` | `rv32imac_zba_zbb_zbc_zbs_xw` / `ilp32` |
| V4BC `PMP` | `.build/readme-v4bc` | GCC 12.2 `riscv-wch-elf-` | `rv32imac_xw` / `ilp32` |
| V4F `FPU` | `.build/readme-v4f` | GCC 12.2 `riscv-wch-elf-` | `rv32imafc_xw` / `ilp32f` |
| V5F `FPU_V5F` | `.build/readme-v5f` | GCC 12.2 `riscv-wch-elf-` | `rv32imafc_zba_zbb_zbc_zbs_xw` / `ilp32f` |

### 全量 `.wvproj` 编译校验

转换器支持传入具体编译器可执行文件：

```sh
python3 tools/wvproj_to_make.py PROJECT.wvproj \
  --compiler-path ../gcc/darwin-arm64/15.2.0/bin/riscv32-wch-elf-gcc \
  --platform linux-amd64 --output /tmp/wvproj-build
```

`--compiler-path`（或 `--compiler`）优先于 `--platform` 和自动平台选择；传入的 GCC 所在目录中的 `g++`、`as`、`objcopy`、`objdump` 等配套工具也会被优先使用。上面的命令即使指定了 `--platform linux-amd64`，仍会使用 Darwin arm64 的显式 GCC。

本次用该显式编译器遍历了所有 EVT 工程：

```sh
find Qingke*/EXAM -name '*.wvproj' -print
```

每个工程都先转换到独立的临时输出目录，再执行 `make -j2 all`；成功生成 ELF 后执行 `make clean`，并确认输出目录中不再有 `obj` 目录。EVT 源码目录没有被转换器写入。

初始全量校验发现 8 个 EVT 工程问题：

| 项目总数 | 转换失败 | 编译成功并清理 | 编译失败 | 清理失败 |
|---:|---:|---:|---:|---:|
| 1298 | 0 | 1290 | 8 | 0 |

应用 `0002-fix-eight-wvproj-builds.patch` 后，对这 8 个项目重新转换、编译并清理，结果为：

| 重试项目数 | 转换失败 | 编译成功并清理 | 编译失败 | 清理失败 |
|---:|---:|---:|---:|---:|
| 8 | 0 | 8 | 0 | 0 |

该补丁的修复内容如下：

- 两个 `ADC_ScanOut` 工程从 `.wvproj` 和 `.cproject` 的排除列表中移除 `Peripheral/src/ch32x3x5_dma.c`，恢复 `User/main.c` 所需的 DMA 实现。
- 两个 V5F 双核链接脚本移除对未生成的 `../../V3F/obj/User/shared.o` 的强制输入，并在 `RAM_SHARED` 中显式保留 `Buffer_Sharing[4]` 与 `Data_Sharing` 的共享布局；V3F 端仍可使用同一共享 RAM 地址。
- 四个 SDRAM 工程在 `hardware.c` 中补上缺失的 `bank1`（值为 0）定义；带空格的 `_DMA` 路径也已验证可正常传递给编译器。

因此，初始全量校验的 1290 个成功项和补丁后的 8 个定向成功项合计覆盖全部 1298 个 `.wvproj`；所有成功项的临时中间产物均已清理，EVT 源码目录没有被转换器写入。

### 自动化测试和 GitHub Actions

[`tests/test_wvproj_to_make.py`](tests/test_wvproj_to_make.py) 默认读取 `MODE=fast`，只编译本 README 代表性项目表中的 9 个工程，并检查每个 EVT 文件夹至少覆盖一个项目；设置 `MODE=full` 时会遍历全部 `.wvproj`。两种模式都会把输出写入临时目录、检查显式 `COMPILER_PATH` 是否传递到 Makefile、生成 ELF、执行 `make clean`，并在结束时恢复测试期间临时应用的补丁和 EVT 文件字节。

```sh
cd ref/wch-evt
COMPILER_PATH=../gcc/darwin-arm64/15.2.0/bin/riscv32-wch-elf-gcc \
  python3 tests/test_wvproj_to_make.py
MODE=full COMPILER_PATH=../gcc/darwin-arm64/15.2.0/bin/riscv32-wch-elf-gcc \
  python3 tests/test_wvproj_to_make.py
```

根目录的 [`.github/workflows/wvproj.yml`](../../.github/workflows/wvproj.yml) 在 push 和 pull request 中默认运行 `fast`；手动 dispatch 可以选择 `full`。GitHub Linux runner 没有预置 `COMPILER_PATH` 时，workflow 通过 [`tools/fetch_wch_toolchain.py`](tools/fetch_wch_toolchain.py) 按 `gccriscv-wch` 的 canonical package 约定解析 MounRiver 下载地址，并校验 MRS 2.5.0 归档大小、SHA-256 及 GCC15 可执行文件 SHA-256。`COMPILER_PATH` 可用于本地 `act`，例如将本机 Linux 工具链只读挂载到容器：

```sh
cd openwch
act push -W .github/workflows/wvproj.yml -j wvproj --bind \
  --container-architecture linux/amd64 \
  -P ubuntu-24.04=catthehacker/ubuntu:act-24.04 \
  --container-options "-v $PWD/ref/gcc/linux-amd64/15.2.0:/opt/wch-gcc:ro" \
  --env COMPILER_PATH=/opt/wch-gcc/bin/riscv32-wch-elf-gcc
```

## 指令集和备注更新

- **V2AC**：V2A 是 `RV32EC`，V2C 的 `m` 仅表示 `Zmmul`，不是硬件除法和完整 `M`；V2 使用 RV32E 的 x0–x15 寄存器集合。`GPIO_Toggle` 的 `Zmmul` 是工程配置证据，因此备注中明确标为 V2C 风格。
- **V3A/V3B/V3C/V3F**：V3A 为 `RV32IMAC` 且没有 XW；V3B/V3C 包含 B，V3B 的 M 为可选、V3C 固定包含 M，V3F 进一步包含 F。手册将 AMO 能力列在 V3A/V3F，不能把 B/C 工程中的选项或名称误读成通用 A/AMO 支持。研究资料中的 MRS、延时类指令以及 CH587 资料中出现的 `mcpy`，存在型号或资料范围差异，故没有把它们写成所有 V3 工程都覆盖的扩展。
- **V4BC/V4F**：V4A/B/C/J/F 的基础整数 ISA 以 `RV32IMAC` 为主，F 只属于 V4F；XW 也不是所有 V4 变体都具备。V4 的 A 实现同样有简化的 LR/SC 说明，PMP 区域数必须按 V4B/V4C/F 变体区分。
- **V5F**：V5F 在标准 `IMABCF` 基础上保留 WCH 自定义指令空间，并增加 TCM、Cache 和中断嵌套等平台特性；当前目录没有据此宣称存在向量扩展。
- **PIOC/RISC8B**：PIOC 是独立的 8 位协处理器/指令集。`PIOC_1_Wire` 的 `.ASM`、`.BIN` 和 `.LST` 只能说明该示例携带 PIOC 程序，不能把 PIOC 指令计入 RISC-V 的 `M/B/C/XW` 覆盖统计。

## 核对依据

- [QingKe 处理器代际与 ISA 研究](../wch-isa-research/isa/qingke_processor.md)
- [QingKe 自定义 ISA 参考](../wch-isa-research/isa/custom/qingke-custom-isa.md)
- [WCH 自定义指令参考](../wch-isa-research/isa/custom/wch-custom-isa-reference.md)
- [PIOC/RISC8B 研究记录](../wch-isa-research/isa/custom/wch-pioc-risc8b-findings.md)
- [QingKe V2 处理器手册](../wch-manuals/manual/QingKeV2_Processor_Manual.PDF)、[QingKe V3 处理器手册](../wch-manuals/manual/QingKeV3_Processor_Manual.PDF)
- [QingKe V4 处理器手册](../wch-manuals/manual/QingKeV4_Processor_Manual.PDF)、[QingKe V5 处理器手册](../wch-manuals/manual/QingKeV5_Processor_Manual.PDF)
