# openwch

WCH QingKe RISC-V GCC 工具链的开源重建：从 pristine 上游源码出发，把 WCH 的全部修改重建为
可审阅的补丁集，并只认一条验收标准——与官方 WCH 包逐字节一致。

[English README](README.md)

## 这是什么

WCH 在 MounRiver Studio 里为其 QingKe RISC-V 单片机分发三套 GCC 工具链。本仓库从 pristine
上游 GCC 与 binutils 重建这三套工具链，并以产物比对证明重建成立：同一个 EVT 工程、同一套编译
配置下，我方产出的 `.o`、`.elf`、`.bin` 与官方工具链的产物逐字节相同。

| 版本 | target triple | binutils | 补丁片数（GCC + binutils） | 宿主平台 |
| --- | --- | --- | --- | --- |
| GCC 15.2.0 | `riscv32-wch-elf` | 2.45 | 9 + 7 | darwin-arm64、linux-amd64 |
| GCC 12.2.0 | `riscv-wch-elf` | 2.38 | 9 + 7 | darwin-arm64 |
| GCC 8.2.0 | `riscv-none-embed` | 2.32 | 4 + 2，另有 1 片宿主构建补丁 | darwin（x86_64 构建，Apple Silicon 上走 Rosetta） |

比对**按平台分别进行**：darwin 构建对 darwin 官方包，linux 构建对 linux 官方包。WCH 官方两个
平台包自身在链接级就互有差异，因此跨平台产物一致既非事实也不是本项目的目标。另外，本仓库只交付
编译器本身——GCC 与 binutils 补丁、构建脚本与比对 harness；目标库（libgcc、newlib、crt、specs、
sysroot）逐字节复用官方包，由构建脚本注入，不重新构建。

## 背景与动机

WCH 分发了修改过的 GCC / binutils 二进制，却没有按要求开放对应的修改源码。本项目从 pristine
上游发行版出发，把每一处修改重建为有序、可解释的补丁集——为了 GPL 合规，也为了让 QingKe 自定义
ISA 的研究可以公开进行。

## 我们做了什么

**39 片补丁**，以 `git format-patch` 邮件形式导出，每个版本各带一份稳定 patch-ID 台账
（`patch-id.tsv`）：

| 版本 | GCC | binutils | 其他 | 合计 | 系列 README |
| --- | --- | --- | --- | --- | --- |
| 15.2.0 | 9 | 7 | — | 16 | [patches/15.2.0/README.md](patches/15.2.0/README.md) |
| 12.2.0 | 9 | 7 | — | 16 | [patches/12.2.0/README.md](patches/12.2.0/README.md) |
| 8.2.0 | 4 | 2 | 1（`host/`，只影响宿主构建） | 7 | [patches/8.2.0/README.md](patches/8.2.0/README.md) |

补丁全是上游惯用形态的源码改动——MD 模式、opcode 表项、`-march` 解析与 ELF 属性逻辑、选项注册、
诊断文本——每一处都能溯源到一个实测到的行为差异；三份系列 README 逐片列出「这片补丁对应哪一处
观测差异」。

**自定义 ISA 支持。** 面最大的是 WCH `XW` 压缩字节/半字访存扩展（八个形式，寄存器形式与 SP
相对形式各四个），覆盖汇编器、反汇编器与 ELF 属性三侧；此外还有 WCH 快速中断 ABI、`.highcode`
段语义、四条 32 位自定义 opcode，以及 `--w_priv_spec`、`--wchsoftlib`、`objdump -M xw` 这几个
官方隐藏选项面。XW 是什么、其设计来源见 [wch-xw.md](wch-xw.md)，ISA 事实本身见
[ref/wch-isa-research/](ref/wch-isa-research/)——本仓库不重新发现编码，只验证工具链的接受面与
产出字节。

**验收是字节 gate**，分两层：

| 层 | 语料 | 15.2.0 | 12.2.0 | 8.2.0 |
| --- | --- | --- | --- | --- |
| quick（每轮回归） | 精选 9 个 EVT 工程 | 每平台 274 / 274 | 274 / 274 | 242 / 242（8 个工程） |
| full（收口 gate） | 全量可构建 EVT 树 | darwin-arm64 与 linux-amd64 各 47,797 项产物（覆盖 1,298 个工程） | — | 43,969 项产物（覆盖 1,203 个工程） |

这里的「逐字节一致」有精确含义：在双侧对称 `-fdebug-prefix-map` 工具链前缀归一下的逐字节一致，
比较阶段零 normalize；`.map`/`.lst` 只作诊断辅助，不作 gate 产物。全过程每一轮都由未参与撰写该
工作的独立审计者对抗复审，每一条裁定都有台账——报告在 [analysis/](analysis/)，决策记录在
[DECISIONS.md](DECISIONS.md)。

## 获取输入

有两类外部输入需要自行就位，两者都不在仓库跟踪面内。

### 官方参照包

比对基线。两者都落在 `ref/gcc/<platform>/<version>/`，该目录被 gitignore。

* **darwin** —— 从 mounriver.com 下载 MounRiver Studio 2，放为 `ref/MounRiver Studio 2.app`，
  然后运行 [`scripts/extract-wch-toolchain.sh`](scripts/extract-wch-toolchain.sh)，把包内各套
  工具链抽取到 `ref/gcc/darwin-arm64/<version>/`。
* **linux** —— [`ref/wch-evt/tools/fetch_wch_toolchain.py`](ref/wch-evt/tools/fetch_wch_toolchain.py)
  通过官方 MounRiver API 解析当前签名 URL，并且只在体积与 SHA-256 双双命中时才接受该归档。CI 侧
  由 [`scripts/ci/provision-official.sh`](scripts/ci/provision-official.sh) 驱动。

### EVT 测试语料

`ref/wch-evt/` 的小件保留在仓库内——`tools/`、`patches/`、`tests/`、`README.md`、
`download-evt.sh`。真正作为测试语料的九个 `Qingke*/` 示例工程目录不入库，需要自行就位：

```sh
scripts/fetch-evt.sh --url "$EVT_PACK_URL" --apply   # 分发 URL，随发布公布
scripts/fetch-evt.sh --file <本地包> --apply          # 同一个包的本地副本
```

语料包的 SHA-256 在解包前校验，且没有放宽开关——语料是逐字节 gate 的输入。也可以自 WCH 官网逐包
下载重建：[`ref/wch-evt/download-evt.sh`](ref/wch-evt/download-evt.sh) 从 Chrome 下载历史里查出
各 EVT 归档的 URL，下载后把其中的 `EVT/` 目录解包并改名为对应的 `Qingke*` 目录。

**`--apply` 就是替你跑 [`ref/wch-evt/patches/apply.sh`](ref/wch-evt/patches/apply.sh)；用别的
方式让语料就位的话，这一步得自己跑**，而且不是可选项。不跑它，`v4bc-pmp` 等工程根本构建不起来；
更麻烦的是 `evt-golden.sh` 会**静默**把它们剔除——manifest 只剩 246 条 gate 行而不是 274，全程没有
任何非零退出，随后拿这份缩水的 manifest 去对拍还会报「全过」。这是新鲜克隆实验实证过的坑，见
[phase10-opensource-readiness.md](analysis/toolchain/phase10-opensource-readiness.md) §3.1-B6。

## 构建与验证

### 宿主前提

darwin 各腿需要 Apple Silicon 上的 macOS（darwin-arm64）；15.2.0 的 linux 腿跑在钉死的
`debian:bookworm` 容器里。字面构建根 `/Users/mrs` 与 `/Users/wch` 必须存在且可写，第一次需要一次
`sudo` 创建：官方二进制把这些构建路径作为字面量内嵌其中（configure 行、`DW_AT_comp_dir`、
`SEARCH_DIR`），要逐字节一致就只能复刻它们，而不是把它们归一掉。构建脚本会把这两个路径 symlink
到 `tmp/` 下的源码树；CI 侧的对应物是
[`scripts/ci/setup-literal-paths.sh`](scripts/ci/setup-literal-paths.sh)。

### 构建

```sh
scripts/ci/prepare-sources.sh 15.2.0     # 取上游源码、验证钉死值、按序打补丁
BUILD_JOBS=16 scripts/build-toolchain-15.2.0.sh <源码树>
```

`12.2.0` 与 `8.2.0` 同形。`BUILD_JOBS=16` 是本项目惯例——脚本缺省是 8，而全部已记录的墙钟数据都
取自 16。15.2.0 另有一条 linux 腿
[`scripts/build-toolchain-15.2.0-linux.sh`](scripts/build-toolchain-15.2.0-linux.sh)，在上述容器
内运行。每个构建脚本装上自己刚构建出的宿主可执行体后，再逐字节注入冻结的官方目标库。

### 验证

推荐流程是在你自己的 checkout 内现生成 manifest：

```sh
scripts/evt-golden.sh 15.2.0                    # 官方包 -> manifest
scripts/evt-compare.sh 15.2.0 <我方 gcc 或工具链路径>   # 我方构建 -> 对拍
```

理由是机制性的。带 `-g` 编译会把绝对工作目录写进 `DW_AT_comp_dir`，因此在 A 路径下构建的产物永远
不可能等于在 B 路径下构建的产物。随仓入库的 [analysis/golden/](analysis/golden/) 各 manifest 因此
内嵌了它们生成时的绝对 cwd，换一台机器就只是 raw drift 的诊断参照而非判据；在同一次运行、同一个
目录里先生成 golden 再对拍，这个变量就被彻底消掉了。

## CI

[`.github/workflows/toolchain-ci.yml`](.github/workflows/toolchain-ci.yml) 在 push 与 pull
request 上跑 quick 字节 gate，共四条腿——`linux-15-2-0`、`darwin-15-2-0`、`darwin-12-2-0`、
`darwin-8-2-0`——每条腿都在同一次运行内完成取官方包、备源、构建、现生成 manifest、对拍。不携带 EVT 语料的 checkout 会经 `scripts/fetch-evt.sh` 取语料包——需把仓库变量 `EVT_PACK_URL`（Settings → Secrets and variables → Actions → Variables）设为已发布的包 URL。由于对拍
器的期望总数是从它即将校验的那份 manifest 自己数出来的，每条腿还会在对拍**之前**断言与该 manifest
无关的绝对常数（274/274/274/242 条 gate 行、9/9/9/8 个工程）——正是这一步让静默缩水的语料判红而
不是判绿。全量 EVT 树刻意不进托管 CI（候选 runner 一律 14 GB 整盘磁盘，单 job 6 小时被杀），仍留
作本地 operator 驱动的收口 gate。

[`.github/workflows/release.yml`](.github/workflows/release.yml) 由 `v*` tag 触发，重跑同一套构建
与 gate，只有 gate 通过才发布可复现 tarball——内容是完整的安装树，含逐字节注入的官方目标库。
workflow 在本地用 `act` 验证，入口是
[`scripts/ci/act-verify.sh`](scripts/ci/act-verify.sh)：它跑在一份一次性工作副本上，并自证宿主
未被改动。设计要点与容量实测见
[analysis/toolchain/phase7-ci-cd.md](analysis/toolchain/phase7-ci-cd.md)。

## 仓库地图

| 路径 | 内容 |
| --- | --- |
| [patches/](patches/) | 交付物本体：三套有序补丁集、`series` 文件、稳定 patch-ID 台账、逐版本 README |
| [scripts/](scripts/) | 构建、抽取、golden/对拍 harness、补丁导出；[`scripts/ci/`](scripts/ci/) 是 CI 入口 |
| [analysis/](analysis/) | 取证、审计与收口报告，以及 golden manifests |
| [tests/](tests/) | 版本化的跨平台套件，例如 XW+LTO gate |
| [plans/](plans/) | 阶段路线图与各版本工作流任务书 |
| [ref/](ref/) | 参照输入：EVT 工程、ISA 研究、WCH 手册 |
| `tmp/` | 上游 clone、构建树与阶段证据——gitignored，不随仓库分发 |

**证据指针约定。** 补丁 message 里引用的 `tmp/...` 路径是开发机上的证据坐标，不随仓库分发：它们
记录的是「这次测量在哪里做的」，而不是你能在克隆里打开的文件。它们支撑的结论在 `analysis/` 报告
里；rv64 规格测量已复制进跟踪面，见
[phase9-rv64-spec-15.2.0.md](analysis/toolchain/phase9-rv64-spec-15.2.0.md) 与
[phase9-rv64-spec-12.2.0.md](analysis/toolchain/phase9-rv64-spec-12.2.0.md)。

## 术语表

* **EVT** —— WCH 按 QingKe 代际组织的示例工程树，本项目的测试语料：真实的厂商工程、真实的厂商
  编译配置。
* **golden manifest** —— 官方工具链在一次运行、一个目录下对某语料产出的全部产物的 SHA-256 表
  （[analysis/golden/](analysis/golden/)）。
* **quick gate / full gate** —— 前者是每次改动后必须保持全绿的 9 工程回归集，后者是给一个版本
  收口的全量 EVT 树。
* **phase-N** —— 本项目路线图上的一个工作单元，各有一份 [plans/](plans/) 任务书与一份
  `analysis/toolchain/` 下的收口或审计报告。
* **RC0x** —— phase-3d 内部的修复轮代号（RC01 = `.highcode` 轮、RC02 = 隐式声明轮、
  RC04 = `mret` 轮）。

## 关键文档

* [AGENTS.md](AGENTS.md) —— 项目规则、验收语义、范围决策
* [plans/roadmap.md](plans/roadmap.md) —— 每个阶段的输入与判定
* [analysis/toolchain/phase8-closure.md](analysis/toolchain/phase8-closure.md) —— 三版本 gate
  终签数字
* [ref/wch-evt/README.md](ref/wch-evt/README.md) —— 语料本身与精选 9 工程的覆盖面

## 状态

三个版本均已对各自平台的官方包达成零差异（2026-08）：15.2.0 覆盖 darwin-arm64 与 linux-amd64，
12.2.0 与 8.2.0 为 darwin。
