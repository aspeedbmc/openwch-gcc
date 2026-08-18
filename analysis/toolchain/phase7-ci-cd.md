# phase-7：GitHub workflows 构建 CD 与本地 act 验证

> 状态：**骨架**（轮 2 落盘）。带「轮 3 填」「轮 4 填」标记的小节等实测数据到位后补全，其余小节的内容已由轮 1/轮 2 的实证结论确定。

## 1. 目标与验收面

phase-1..6 已让三个版本（15.2.0 双平台、12.2.0 darwin、8.2.0 darwin）达成产物逐字节一致。phase-7 把「pristine 上游 + 本仓库补丁集 → 重建工具链 → 字节 gate」这条链路固化成 GitHub Actions workflow，使补丁集的可复现性成为一条可持续运行的机器判据，并在 tag 触发时把通过 gate 的工具链打包发布。

验收面沿用既有两层口径：托管 CI 跑**快速回归集**（精选 9 工程）；全量 EVT 树仍是本地收口 gate，理由见 §5。

## 2. 交付物

| 路径 | 作用 |
|---|---|
| `.github/workflows/toolchain-ci.yml` | 四条腿的字节 gate（push / pull_request / workflow_dispatch） |
| `.github/workflows/release.yml` | tag `v*` 触发：同一构建+gate 序列 + 可复现 tarball 发布 |
| `scripts/ci/provision-official.sh` | 取得/校验 WCH 官方包并抽取到 `ref/gcc/<platform>/<version>/` |
| `scripts/ci/prepare-sources.sh` | 三版本各自的上游获取 + 校验 + 补丁应用 |
| `scripts/ci/setup-literal-paths.sh` | 容器/runner 内建字面构建路径符号链接（带拒绝守卫） |
| `scripts/ci/act-verify.sh` | 本地 act 验证入口（专用工作副本、宿主零污染、分段计时与磁盘采样） |

## 3. 设计要点

### 3.1 gate 必须同 run 现生成 manifest

已入库的 `analysis/golden/*.tsv` 头部内嵌生成时的绝对 cwd，而 `-g` 编译把 cwd 写进 `DW_AT_comp_dir`，换目录必然失配。因此每条腿先用官方包跑 `evt-golden.sh` 现生成 manifest，再用我方工具链跑 `evt-compare.sh`，同 run 同 cwd。已入库 manifest 只作 raw drift 诊断打印，**不作判据**。

### 3.2 三层绝对断言

`evt-compare.sh:182` 的期望 gate 总数是从它即将校验的 manifest 自己数出来的；CI 里那份 manifest 又是同 run 现生成的——验证器与被验数据同源。若某工程在 CI 环境下被 EXCLUDED，manifest 变短，对拍会在缩水的分母上报「全过」。对策是每条腿断言与该 manifest 无关的绝对常数，且层 1/2 跑在对拍**之前**：

| job | gate 产物数 | 工程数 |
|---|---|---|
| `linux-15-2-0` | 274 | 9 |
| `darwin-15-2-0` | 274 | 9 |
| `darwin-12-2-0` | 274 | 9 |
| `darwin-8-2-0` | 242 | 8 |

层 3 显式解析 `SUMMARY` 行（**TAB 分隔**）的 `gate_pass=` 与 `gate_fail=0` 字段，并同时校验 `evt-compare.sh` 的退出码，两个信号都必须成立。

8.2.0 的 8 个工程是既定 EXCLUDED 一个工程的结果，不是缺陷；`evt-golden.sh:263` 硬要求 `evt-projects.tsv` 恰好 9 行数据，CI 不得裁剪该表。

### 3.3 并发契约

16 项目级 workers × 项目内 `make -j2`（后者硬编码在 harness 里）、工具链构建 `BUILD_JOBS=16`。三个值即便与缺省相同也在 workflow `env` 里显式钉死。runner 核数不足时按 oversubscribe 处理，**不因 runner 规格下调**；每个 job 开头把实际核数打进日志。

第四个必须钉死的是 linux 腿的 `EVT_CONTAINER_IMAGE`：`evt-golden.sh:45-47` 在 linux 上该变量为空即 die，而这一步发生在数小时构建之后。它只写进 manifest 头作 provenance，不拉容器。

### 3.4 环境钉死

- `runs-on` 一律用明确版本标签，不用浮动标签。
- linux 腿 `container: debian:bookworm@sha256:9344f8b8…8185dc`。三者关系：该串是**多架构 OCI index digest**；其下 amd64 专用 manifest digest 为 `sha256:41a613df…8755ab`，GitHub `ubuntu-24.04`（x64）会自动解析到它；Apple Silicon 宿主默认拉 arm64 变体，所以本机 act 必须显式 `--container-architecture linux/amd64`，否则 `build-toolchain-15.2.0-linux.sh:31` 的 `uname -m = x86_64` 断言会 die。
- 每个 `uses:` 钉 40 位 commit sha，尾注 tag：`actions/checkout` v4.4.0、`actions/cache` v4.3.0、`actions/upload-artifact` v4.6.2、`softprops/action-gh-release` v3.0.2。三个 `actions/*` 均已有更高 major，升 major 属口径变更，本阶段登记为未决项转出。

### 3.5 容器 apt 层的可观测性

digest 钉死的是基础镜像，其上叠的 apt 层是可变的，「环境已钉死」这句话在容器之上会断。因此 linux 腿把 `dpkg-query -W` 的完整包集与版本打进日志。包集由 `build-toolchain-15.2.0-linux.sh:37-44` 自己 require 的命令表推导，加 `m4`（GMP 构建需要）、解包工具、`curl`，以及 `nodejs`。

**两项不在命令表里、靠实测补上的依赖**（命令表推导本身发现不了，两者都会让 linux 腿在真跑时失败）：

- `patch` —— `ref/wch-evt/patches/apply.sh` 直接调用 `patch(1)`，而 `debian:bookworm` 基础镜像**不带** `patch`（实测 `BASE-LACKS patch`）。该步骤排在构建之前，漏装即每次 linux run 早期硬失败。macOS 自带 `/usr/bin/patch`，只影响容器。
- `zlib1g-dev` —— binutils 的 configure 行含 `--with-system-zlib`（`build-toolchain-15.2.0-linux.sh:291`），需要系统 zlib 头文件；命令表是命令清单，结构上照不出库依赖。已在容器内以 `#include <zlib.h>` + `-lz` 实编实链验证。
  对照：官方 linux gcc 二进制内嵌的 configure argv 是 `--without-system-zlib` 且**不含 zstd**，故 gcc 侧无需 `zlib1g-dev`/`libzstd-dev`——这两个事实是从官方二进制里读出来的，不是推断的。

`nodejs` 的理由：`debian:bookworm` 无 node，`actions/cache` 与 `actions/upload-artifact` 都是 JS action，在 `container:` 内直接 exit 127 且 job 判失败（act 实测）。真 GitHub 会把 runner 自带的 node 挂进容器，所以那里是冗余的（约 27 s），但一条 apt 行两边都对，胜过两套实现。

**phase-5 包集不可复原**：其记录位于 p8 独占路径 `tmp/toolchain_15.2.0-linux/`，phase-7 的隔离约束禁止读取。可作对照的公开摘录见 `analysis/toolchain/phase5-linux.md:27-29`（GCC 12.2.0、make 4.3、Python 3.11.2、flex 2.6.4、bison 3.8.2），那是文档摘录、非完整包集。

本轮已在 `debian:bookworm@sha256:9344f8b8…`（`--platform linux/amd64`）内实测该 apt 行：32 项必需命令全部命中（missing=0），zlib 头文件实编实链通过，`/usr/bin/gcc` 解析到 GNU `gcc-12`（Debian 12.2.0-14+deb12u1）而非 clang，`uname -m=x86_64`，`/.dockerenv` 存在，完整包集已随日志落盘。证据：`tmp/p7-evidence/S2/scratch/container-deps-probe.log`。

### 3.6 上游归档的 URL 与 SHA256

仓库里原本没有任何上游 URL——`verify_archive` 只校验不下载，归档缺失即 die。CI 必须自己取，所以：SHA256 **从构建脚本的 `verify_archive` 调用参数解析派生**（不重抄，杜绝漂移），URL 在 `prepare-sources.sh` 的 `archive_url()` 里钉死，fail closed（校验不过即红，绝不回退到「下载最新版」）。

**归档的身份由哈希锚定：URL 可替换，版本不可替换。** 任何可达来源只要字节与钉死 SHA256 匹配即同一身份，所以某镜像失效时换一个来源是合法操作；换一个版本号则不是，即便它「看起来只是小版本差」。硬例证：`isl` 在 12.2.0 用 0.24、在 8.2.0 用 0.18，二者**不可互换**——GCC 8.2 的 graphite 依赖的 API 在 isl 0.24 已被删除（`analysis/toolchain/phase6-closure.md` 脚本适配表第 2 项）。另一个例证是 zstd：构建脚本钉的文件名是 `zstd-1.5.2-release.tar.gz`，而 GitHub 上同一个「1.5.2」有两份字节不同的归档——tag 归档 `v1.5.2.tar.gz` 实测 `f7de1346…`（**不匹配**），release 资产 `zstd-1.5.2.tar.gz` 实测 `7c42d56f…`（匹配）。靠哈希才把两个同名版本区分开，靠版本号区分不了。

九个 URL 已于 2026-08-17 逐个下载并与钉死 SHA256 比对通过（证据 `tmp/p7-evidence/S2/scratch/urlprobe/results.tsv`），并于同日再做串行 HTTP 存活复核，9/9 LIVE（`tmp/p7-evidence/S4/archive-availability.tsv`）。**零 BLOCKED**：

| 归档 | 上游 URL |
|---|---|
| `gcc-12.2.0.tar.xz` | `https://ftp.gnu.org/gnu/gcc/gcc-12.2.0/gcc-12.2.0.tar.xz` |
| `binutils-2.38.tar.xz` | `https://ftp.gnu.org/gnu/binutils/binutils-2.38.tar.xz` |
| `gmp-6.2.1.tar.xz` | `https://ftp.gnu.org/gnu/gmp/gmp-6.2.1.tar.xz` |
| `mpfr-4.1.0.tar.xz` | `https://ftp.gnu.org/gnu/mpfr/mpfr-4.1.0.tar.xz` |
| `mpc-1.2.1.tar.gz` | `https://ftp.gnu.org/gnu/mpc/mpc-1.2.1.tar.gz` |
| `isl-0.24.tar.xz`（12.2.0） | `https://libisl.sourceforge.io/isl-0.24.tar.xz` |
| `isl-0.18.tar.bz2`（8.2.0） | `https://gcc.gnu.org/pub/gcc/infrastructure/isl-0.18.tar.bz2` |
| `zlib-1.2.12.tar.gz` | `https://www.zlib.net/fossils/zlib-1.2.12.tar.gz` |
| `zstd-1.5.2-release.tar.gz` | `https://github.com/facebook/zstd/releases/download/v1.5.2/zstd-1.5.2.tar.gz` |

两处易错点：zstd 的钉死 digest 属于 GitHub **release 资产** `zstd-1.5.2.tar.gz`，tag 归档 `v1.5.2.tar.gz` 的字节不同（实测 `f7de1346…`）；下载后必须存成构建脚本查表用的名字 `zstd-1.5.2-release.tar.gz`。isl 版本两版不同：12.2.0 用 0.24，8.2.0 用 0.18。

**耦合方向：只自动跟随一半——看到这个红时请照下面处置。**
本表与上游构建脚本的耦合是单向的，且只有一半是自动的：**SHA256 由 `verify_archive` 解析派生、自动跟随**；**URL 表由 `prepare-sources.sh` 独立维护、不会自动跟随**。
于是若上游构建脚本把某个前置件**换了版本**（不只是改哈希），CI 的表现会是：派生出新哈希 → 用旧 URL 下到旧版本字节 → **哈希不匹配 → fail closed → 红**。

**这个红是正确的**，fail closed 正是设计意图。**正确修法是更新 URL 表使其指向新版本，绝不是放宽、跳过校验，或把校验值改成「实际下到的那个」。** 这与本节「换源合法、换版本非法」是同一原则的两面：自动跟随的那一半保证哈希永不漂移，不自动跟随的那一半保证版本变更必须由人显式确认。

该耦合已有活的验证场景：phase-7 收尾期间，并行工作流正在改动 `scripts/build-toolchain-{15.2.0-linux,8.2.0}.sh`。因为 SHA256 是派生的，我方自动跟随、不欠同步义务；而若当初把「打完补丁后的 tree hash」也写成相等断言（该断言已按裁定删除，见 §3.12），此刻就会开始误红。

### 3.7 前置件口径（三版本互不相同）

- **15.2.0**：走树内 `contrib/download_prerequisites --verify --sha512`。pristine `releases/gcc-15.2.0` 的清单与 README 手工拷入的五个逐字符命中，等价性成立。CI 把这五个归档缓存在 `tmp/ci-cache/prereq-15.2.0/`；该脚本对已存在的归档不再下载（`:233-234`）但仍逐个 sha512 校验，所以缓存不削弱校验。
- **12.2.0 与 8.2.0**：**绝不用** `download_prerequisites`。两者各自钉死独立的 host-deps 清单并自带 SHA256 gate。xPack `riscv-gcc` 树内的 `download_prerequisites` 列的是 gmp-6.1.0 / mpfr-3.1.4 / mpc-1.0.3 / isl-0.18——四个里三个与 8.2.0 构建脚本实际用的版本不同，套用会静默构建出另一个编译器，是 gate 假绿的隐蔽形态。

### 3.8 EVT 工程补丁必须在 CI 内应用

`ref/wch-evt/` 按设计以**未应用态**入库，开发机上那 9 个改动文件是 `ref/wch-evt/patches/apply.sh` 的已应用态。CI 是干净 checkout，所以四条腿都显式跑一次该脚本（幂等）。本地 act 验证走同一步，与 CI 同构。

**2026-08-18 合并更新**：语料树改为分发制——公开仓库不收录 `ref/wch-evt/Qingke*/`（25065 文件），由 `scripts/fetch-evt.sh` 按钉死的 SHA-256 取包还原。两个 workflow 的这一步因此换成双分支一步「Provision the EVT corpus and apply its patches」：语料在位（私有 checkout）只跑 `apply.sh`，不在位则先按仓库变量 `EVT_PACK_URL` 取包、校验、解包再 apply，包按其 SHA-256 做缓存键；八条腿逐字节同构。必要性有实测：U5 在公开树上跑 act，缺语料时该步直接失败（`cannot apply: 0001-pmp-select-ch32v20x-d8w.patch`，`Job failed`），证据 `tmp/publish/evidence/u5/12-act-result.txt`。apply 是第一道拦截；即使它侥幸通过，§3.2 的绝对分母断言（274 / 9）仍会在比对前拦下缩水的语料树——两道都不从 manifest 自身取分母。

### 3.9 runner 分配

| job | runner | 规格 | 说明 |
|---|---|---|---|
| `linux-15-2-0` | `ubuntu-24.04` + `container: debian:bookworm@…` | 4 CPU / 16 GB / 14 GB SSD | 公共仓库规格 |
| `darwin-15-2-0` | `macos-15`（arm64） | 3 (M1) CPU / 7 GB / 14 GB SSD | 官方 15.2.0 宿主体是 arm64 原生 |
| `darwin-12-2-0` | `macos-15`（arm64） | 同上 | 官方 12.2.0 宿主体是 arm64 原生 |
| `darwin-8-2-0` | `macos-15`（arm64） | 同上 | 见下 |

**`darwin-8-2-0` 为什么不用 `macos-15-intel`**：官方 8.2.0 宿主可执行体是 Mach-O x86_64，原生 Intel runner 看起来更贴近，且 `macos-15-intel` 确是标准托管标签（4 CPU / 14 GB / 14 GB SSD，公共仓库免费，可用至 2027-08，是 Actions 上最后一个 x86_64 镜像）。但**用不了**：gate harness 在 macOS 上只认 arm64——`evt-golden.sh:32-36` 与 `evt-compare.sh:32-38` 只把 `Darwin/arm64` 与 Linux x86_64 映射成 platform，其余一律 `die "unsupported host platform"`，在 Intel runner 上两个脚本连启动都做不到；且该 platform 串还是 manifest 的文件名，接受 Intel 等于把 gate 基线分叉。arm64 runner 恰好复现本机达成零差异时的形态：`build-toolchain-8.2.0.sh:27-30` 自己经 `arch -x86_64` 重入，编译器仍是 x86_64 宿主构建，只是跑在 Rosetta 2 上。

**Rosetta 2 的一手依据**：arm64 macOS 镜像的 packer 模板执行 `install-rosetta.sh`，镜像自测断言守护进程 `oahd` 在运行。**两份镜像 Readme 都没提 Rosetta**，只看 Readme 会误判为「未预装」——这是后来者会踩的同一个坑。workflow 仍按「先探测（`arch -x86_64 /usr/bin/true`）、失败再装」写，不假定任一侧。

### 3.10 CD 的「D」

`release.yml` 由 tag `v*` 触发，复用同一构建+gate 序列，gate 通过后打包发布：

- 资产名 `openwch-toolchain-<version>-<platform>.tar.gz` 与同名 `.sha256`，归档顶层目录同名。
- 内容是构建脚本装出来的**完整工具链树**（含逐字节注入的 WCH 随包库/sysroot/specs/libgcc），即字节 gate 校验的那棵树本身，原样打包，不做重新组装。
- 构建时间来源是各构建脚本钉死的 `SOURCE_DATE_EPOCH=1767225600`；打包让归档与它一致而不是与 runner 时钟一致。
- 可复现打包参数：`--sort=name`（成员顺序与 readdir 无关）、`--mtime=@$SOURCE_DATE_EPOCH`、`--owner=0 --group=0 --numeric-owner`（不带 runner 账号名/uid）、`gzip -n`（gzip 头不带时间戳与原文件名）。五者缺一，同一棵工具链两次打包就会得到不同字节，release 资产也就无法与重建结果对照。这些是 GNU tar 的参数，macOS 自带 bsdtar 没有，所以 darwin 腿先解析 `gtar`（缺失则 `brew install gnu-tar`）。

### 3.11 复用形态

两个 workflow 之间**步骤直接重复**，未用 `workflow_call`，也未用仓库内 local composite action。理由：act 对本地 reusable workflow 的支持历来不稳，而这条腿本阶段要在 act 上验证；composite action 的解析也不被 `act --list` 覆盖，用了等于把一处风险推到第一次真跑。证据见 `tmp/p7-evidence/S2/reuse-form-check.txt`（`act --list` 两个 workflow 全部解析通过；linux 两个 job 的 `act -n` dryrun 逐步骤 Success、`Job succeeded`、退出 0）。

### 3.12 补丁 provenance：断言什么、只记录什么

CI 里对补丁应用的**硬断言**只有两项：钉死的**上游 commit**（`rev-parse`，8.2.0 因 `git am` 之后 HEAD 前进，等价形式是「base commit 是 HEAD 的祖先」），以及**全片 series 干净应用**。加上字节 gate 绿，这三者构成完整的 provenance 链。

打完补丁的 **tree hash 只打印、不断言**。理由是方向性的：补丁一旦变更，正确行为是**重跑字节 gate 判定新补丁集是否仍零差异**；而钉死的 tree 常数会把一次合法改动直接判红。在上述三项齐全的前提下，tree 常数不增加任何鉴别力，只制造「改补丁的人必须同步改 CI 常数」的义务——它产生的是噪声，不是信号。

下表是 **eed1486 时点的观测值**，仅作 provenance 记录与人工诊断参照，**不是验收条件**；补丁集演进后这些值改变属预期，不构成缺陷。

| 版本 | 组件 | 上游 commit（硬断言） | 观测到的打完补丁 tree（仅记录） |
|---|---|---|---|
| 15.2.0 | gcc | `5115c7e447fc07457443df874bf57840e8316d5f` | `0785aaf06ea20bd0f44b5084007d05497bc35e80` |
| 15.2.0 | binutils | `2bc7af1ff7732451b6a7b09462a815c3284f9613` | `bda204bac05cb5e1e2c77c6213aac71c0e110527` |
| 12.2.0 | gcc | 无（从校验过的 release tarball 导入，上游不变量是归档 SHA256） | `37559608d0be1a87979d1beedff5c4f6cb286b4c` |
| 12.2.0 | binutils | 同上 | `f7e1a27f3edf9ef412d47119aacec37e2abeba5c` |
| 8.2.0 | gcc | `0c7a874f0b6f452eeafde57731646e5f460187e4` | `3260ccd8722ba1dc938ad188fa2cafd2b61b5423` |
| 8.2.0 | binutils | `82b51c7b5087ddb77988287cd7a2dd8921331bfd` | `8d0d7da3c3b3376d07ef0f76f0f00b6b913dcf40` |

12.2.0 的**导入树**（`e66ae753…` / `d66ce22b…`）同样不在 CI 里重复断言——`scripts/build-toolchain-12.2.0.sh` 的 `verify_source_base()` 本来就会验它，再钉一遍只是多一处要同步的地方。

**2026-08-18 合并更新（对 main 4d 校验块现状的口径对齐）**：eed1486 之后 main 的构建脚本增加了构建期补丁集校验块（020d43a）。
其初版把判据挂在**导出用的内部 commit**（`expected_head` + `merge-base --is-ancestor`）上，
而全新克隆里根本没有那些 commit 对象，于是切断了 12.2.0/8.2.0 的一切 fresh 复放路径（phase-10 的 P10-F1）。
P10-F1 修复后该块改为**内容锚**——导入树、冻结补丁树、stable patch ID、`From` 行 commit 串**逐项相等**，
commit 可达性只在对象确实存在时才作为工作镜像的附加护栏，缺失时打一行 `from_commit_unavailable=` 如实披露。
因此**构建脚本自己就能在 fresh 树上完成补丁 provenance 自证**，本节「CI 只硬断言上游 commit + 全片干净应用、
tree hash 只打印不断言」的理由**不变**：两层各自成立、方向不冲突，CI 侧再钉一遍 tree 常数仍然只增同步义务、不增鉴别力。

## 4. 本地 act 验证

`scripts/ci/act-verify.sh <job-id>`：

- 钉 act 版本下限 0.2.89；只允许 linux job（白名单）。
- 拒绝自身参数与**所有它会读到的 `actrc`** 里的 `-self-hosted` 字面量。该能力不在 `act --help` 里，只在官网文档，靠 `--help` 自查发现不了。
- 一律不加 `--bind`（实测 bind 模式会直接改宿主文件）；`--action-cache-path` / `--cache-server-path` / `--artifact-server-path` 三者全部重定向进 `tmp/p7-evidence/S4/`（缺省会写 `~/.cache/act`、`~/.cache/actcache`，落在 worktree 之外）。
- 显式 `-P ubuntu-24.04=<image>`（无映射时 act 会弹交互选单，非交互调用直接 fatal EOF）与 `--container-architecture linux/amd64`。
- 跑在**专用工作副本**上：`git archive HEAD | tar -x` + `git init` + 一个 commit（commit 不是可选的——unborn HEAD 会让 act 推导不出 `GITHUB_SHA`）。该副本天然等于 CI 看到的干净 checkout，所以这个选择同时提高了本地与线上的同构性。
- **交付物绑定**：跑前跑后各记一次工作副本内 `.github/workflows/*` 与 `scripts/ci/*` 的 sha256，与冻结 worktree 的交付版逐条比对，落 `deliverable-binding.txt`；不一致即非零退出。
- **宿主隔离回归**：跑前跑后各存一次冻结 worktree 的 `rev-parse HEAD` 与 `status --porcelain`，两者必须逐字节相同。
- **分段计时**：workflow 各步骤打 `P7_STAGE` 标记（provision / prepare / build / gate-golden / gate-compare 分别计时），脚本解析成 `timing.tsv`；同时记录宿主核数、容器内 `nproc`、`--container-architecture` 取值、以及同时段是否有其它重型 run（可填字段 `ACT_CONCURRENT_NOTE`）。
- **磁盘采样**：workflow 在 provision 后 / 源码就绪后 / 构建期间（30 s 间隔后台采样取极值）/ 对拍时打 `P7_DISK` 标记，脚本解析成 `disk.tsv`。
- 产物取出走 `--artifact-server-path` + `actions/upload-artifact@v4`（实测通，且完全不碰 workspace）。

## 5. 不进托管 CI 的边界

全量 EVT（1298 工程 × 双侧构建）不进托管 CI，两条硬上限各自独立成立：

- **磁盘**：三类候选 runner 一律 14 GB SSD，且这是含操作系统与全部预装软件的整盘规格值，不是空闲值。
- **时长**：单 job 6 小时硬上限，`timeout-minutes` 无法放宽（设置值超过 runner 上限时按后者取消）；macOS 并发上限 Free/Pro/Team 均为 5 且与 larger runner 共享，无法靠 matrix 横向摊薄。

替代路径：全量腿留作本地 operator 驱动的运行。其生成器尚未版本化（P2-19），本阶段不收编，登记为未决项转出。
**2026-08-18 合并更新**：P2-19 已闭合——`scripts/full-census` 已版本化（commit 4cb591e）；「不进托管 CI」的两条硬上限（磁盘、时长）不因此改变。

## 6. 容量可行性：墙钟、内存、磁盘

> 本节的数字状态：**act 端到端取证跑尚未执行**（等协调器放行）。凡标「待 act 补」的格子，
> 其采集手段已建进 workflow 本体与 `scripts/ci/act-verify.sh`，跑完即自动落表。
> 本节**不用推断填数**。
>
> **2026-08-18 合并更新**：act linux 腿取证跑已由 phase-10 执行完毕（`ACT_EXIT=0`，端到端全绿），
> 下文 linux 腿的「待 act 补」格已按实测回填，证据源
> `tmp/p7-worktree/tmp/p7-evidence/S4/linux-15-2-0-20260818T105514Z/{timing,timing-stages,memory,disk}.tsv`。
> **测量对象是冻结 worktree（eed1486 补丁集）**，不是合并后的 main；合并后须在 main 上重跑一轮刷新。
> 三条 darwin 腿仍「未判定」，其格子不变。

### 6.1 三条腿的判定形态

**结论是「未判定」，不是「可行」也不是「不可行」。** 这是一个合法且有价值的交付结论：
它把「交了一套跑不完的 workflow」换成「明确标注了托管边界 + 给出受支持的替代路径 + 首次真跑即自解」。
**不会**为了让各腿看起来可行而调低 gate 面或放松并发契约来凑——那才是失败。

### 6.2 墙钟

#### 6.2.1 缺锚（这本身是一条发现）

六个阶段、三个版本、双平台、全部零差异达成，**仓库里没有任何一处记录过工具链构建墙钟**。
12.2.0 与 15.2.0 至今没有实测锚，phase-7 做容量估算时无从挂靠。详见 §8 发现 1。

#### 6.2.2 必须一起引用的三个因子

| 因子 | 值 | 适用面 |
|---|---|---|
| 容器 qemu 仿真（amd64-on-arm64） | 1.67×（gcc `-O2`）／1.96×（mawk 整数循环） | **只**适用 linux 腿的本机 act 观测折算 |
| **Rosetta 2**（x86_64-on-arm64） | **1.15–1.25×** | **只**适用 8.2.0 腿 |
| `evt-golden.sh` **设计性双跑** | golden 段墙钟 ≈ 单趟 2 倍 | 四条腿的 gate 段都适用 |

**8.2.0 腿明确不套用 1.67×，理由是机制不同，已实测**（`S1/rosetta/verdict.md`）。
套用 1.67× 会把 8.2.0 的构建时长高估约 30–45%。Rosetta 区间的四条边界必须与数字同时出现：
①**代理测量**——测的是 macOS 自带 clang 的 x86_64 切片编一个小 TU，不是 8.2.0 构建本身；
②**只覆盖 CPU，不覆盖内存放大**，OOM 量化**不能**用它推；
③**单进程测量，未含并发**，16 workers × `make -j2` 在少核 runner 上是 oversubscribe，外推非线性；
④因子随负载漂移（两档已差 0.10），**给区间不给单点**。

单腿 gate 段的工程构建次数：`evt-golden.sh` 双跑 9 工程 ×2 + `evt-compare.sh` 再建 9 工程 = **27 次工程构建**。

#### 6.2.3 串行占比 `s`：单跑解不出，只给结构性近似

`T(n) = T₁·(s + (1−s)/n)` 有两个未知数，**一次测量只给一个方程**。真解需要两个不同核数各跑一次，
等于再花一个稀缺窗口——**本阶段不做**（协调器裁定不追加 `-j4` 第二点）。

替代是用构建脚本自己的阶段日志做**结构性近似**：`configure` 类基本串行、`make all-*` 类基本并行、
`install` 类居中，于是 `s ≈ (配置段 + 安装段) / 总墙钟`。采集已建入：workflow 给
`binutils-configure` / `binutils-build` / `binutils-install` / `gcc-configure` / `gcc-all-gcc` /
`gcc-install-gcc` 逐个打 `P7_SUBSTAGE` 时间戳，落 `S4/timing-stages.tsv`。

**引用时必须同时标三条**：①这是**结构性近似**，不是两点拟合解；②它测自**容器 qemu 仿真环境**，
**仿真对串行段与并行段的放大未必等比**，可迁移性有限；③**用于 darwin 外推时不得当作原生 `s`**
（darwin 是原生 arm64，8.2.0 另叠 Rosetta，机制不同），只能作参考区间。

**结论形式是区间稳健性，不是点估计。** 已算：`darwin-8.2.0` 在 `s∈[0.05,0.30]` 上**结论翻转**
（锚取 2.0 h 时构建段落在 3.10–6.70 h），故判**无法判定（需实测）**。翻转点对 `O`
（provision / prepare / golden / compare 四段墙钟）**比对 `s` 更敏感**，所以采集的重点是把 `O` 采全。

#### 6.2.4 每腿墙钟外推（linux 腿 2026-08-18 已实测回填，darwin 三腿仍待）

| job | 分段实测 | 外推墙钟 | `timeout-minutes` | 结论 |
|---|---|---|---|---|
| `linux-15-2-0` | **2026-08-18 实测**：provision 107 s · prepare 96 s · build 898 s（binutils 185 + gcc compiler-only 676 + 注入 2）· gate-golden 55 s · gate-compare 23 s | **act 全程 1299 s ≈ 22 min**（16 核宿主，linux/amd64 容器 + qemu） | 345 | **有实测支撑的可行**（见表下注） |
| `darwin-15-2-0` | 无锚 | 待判 | 345 | 未判定 |
| `darwin-12-2-0` | 无锚 | 待判 | 345 | 未判定 |
| `darwin-8-2-0` | 无锚（Rosetta 1.15–1.25×） | 3.10–6.70 h（`s∈[0.05,0.30]`） | 345 | **无法判定，需实测** |

`timeout-minutes` 一律 **345 而非 360**：设成等于平台上限等于放弃诊断——平台会**静默斩断**，
而那恰恰是最需要诊断的那次运行。15 分钟余量换一次**可诊断**的超时失败，且已采数据仍能吐完。

**2026-08-18 合并更新（linux 腿注）**：上表 linux 行是**本机 act 实测**（16 核 Apple Silicon 宿主上的
linux/amd64 qemu 容器），不是托管 runner 实测；托管 `ubuntu-24.04`（4 vCPU x86_64 原生）上按核数折算
约 1 h 量级，仍远低于 345 min，故判「有实测支撑的可行」。分段和 1179 s 与 act 全程 1299 s 差 120 s，
差额是镜像拉取与 act 自身开销（`timing.tsv` 自注）；子段 185+676+2=863 s 与 build 898 s 之差为两次
configure（13+14 s）与标记间隙。**测量对象是冻结 worktree（eed1486 补丁集）**，合并后须在 main 重跑刷新。

### 6.3 内存：`BUILD_JOBS=16` 对 7 GB

#### 6.3.1 主路径 = act 那一跑的聚合实测（不经任何换算链）

act 取证跑本身就是 `BUILD_JOBS=16` 真建一遍 GCC+binutils，容器内 cgroup v2 `memory.peak`
采到的正是**「16 路并行建 GCC 的系统级峰值」**——**那就是要量的量本身，不需要经过共享因子**。
该值**直接与 7 GB 并列**，如实标注**跨平台外推**（linux/amd64 容器 + qemu ⇒ darwin/arm64 原生）。

⇒ **那一跑的 `P7_MEM` 不是附带项，是 OOM 判定的主证据。** 待 act 补。

**2026-08-18 合并更新（实测回填）**：容器 cgroup 构建峰值 **8,780,759,040 B ≈ 8.78 GB**（10⁹ 口径；
8.18 GiB），条件 `BUILD_JOBS=16`、容器 16 CPU / 16 GB（`memory.tsv`：`container_meminfo_total_kb=16425308`、
`container_nproc=16`）。同一跑另有宿主侧 `docker stats` 轮询极值 **7.743 GiB**（口径不同、取值更低），
**两个口径都超过 darwin runner 的 7 GB，结论不依赖取哪一个**。同跑字节 gate
`gate_pass=274 gate_total=274 gate_fail=0`（分母断言 `manifest_gate_rows=274` / `manifest_projects=9` 命中）。
⇒ **§6.3 结论行：8.78 GB > 7 GB darwin runner——darwin 三条腿的主要风险轴是内存，不是墙钟**
（墙钟风险见 §6.2.4 的 linux 实测与 p8 darwin 构建锚）。
限制照 §6.3.3/§6.3.4/§6.3.5 不变：这是 **linux/amd64 + qemu 容器**的数，外推到 darwin/arm64 原生跨平台边界；
**测量对象是冻结 worktree（eed1486 补丁集）**，合并后须在 main 重跑刷新。
处置（降 `BUILD_JOBS` 属并发契约变更 / self-hosted）属 §7.4 的用户选项，本文不替用户选。

#### 6.3.2 辅路径 = 共享因子换算链（降为交叉校验）

`per-process 峰值 × N × f` 是三段推理，每段都有误差，故只作交叉校验。
**两者若不一致，那个不一致本身就是结论**——它量化了 `f` 的可迁移性有多差，比任一单独的数更有价值；
报告必须显式做这个比对，不许只报主路径。

本机实测（4 路并行 `clang++`，两个采集器各 60 次有界采样）：

| 指标 | 基线 | 峰值 | 增量 |
|---|---|---|---|
| `vm_stat` app 内存（active+wired+compressed） | 8.41 GB | 8.67 GB | **0.26 GB** |
| `ps -A -o rss=` 求和 | 42.87 GB | 43.94 GB | 1.07 GB |
| `/usr/bin/time -l` 单进程 max RSS | — | — | 116.1 MB |

由 `f = 0.560 @ N=4` 反解得等效参数 **`p/s ≈ 0.70`**。三档翻转点（对 7 GB）：

| `f` | 翻转点（单进程） | 性质 |
|---|---|---|
| 0.45（并发 4→16 摊薄后） | 996 MB | 偏保守方向的漂移 |
| 0.56（实测 @N=4） | 800 MB | 实测点 |
| **1.0** | **448 MB** | **保守上界** |

**决策取保守侧（`f→1`，448 MB），这是一个自觉的选择，不是因为只有一个效应存在。** 取保守只会
**强化**「无法判定」，不会削弱它。必须带的限制：**`p/s` 是单点拟合的等效参数，吸收了「共享页重复计数」
与「各进程峰值不同时发生」两种机制；两者随并发度的标度不同，故 N=16 的外推带模型风险，不只是参数风险。**
`f=1.0 → 448 MB` 的保守上界**免于此模型风险**（不假设共享收益、不假设峰值错开），
所以**决策挂在保守上界 + act 直接实测上，`f` 分档只作参考**。

#### 6.3.3 指标选型与偏置方向

| 指标 | 角色 | 偏置方向 |
|---|---|---|
| cgroup v2 `memory.peak`（linux 容器） | linux 腿主指标 | 累计高水位，**段内峰值只能由段间差**下界推断 |
| `vm_stat` active+wired+compressed（macOS） | darwin 腿主指标 | **偏低**（compressor 吸页；7 GB runner 上压缩/换页行为不同，表观占用会更高） |
| `/usr/bin/time -l` 单进程 max RSS | 辅助，对照翻转点 | **偏高** |
| ~~`ps -A -o rss=` 求和~~ | **弃用** | 绝对值比同时刻 app 内存高 **5.1×**（RSS 把共享 text 按进程重复计数） |
| ~~`vm_stat` "Pages free"~~ | **绝不使用** | 本机基线仅 85 MB——macOS 惯例把内存用满作缓存，据此推容量会得出「已经没内存了」的假结论 |

**一个不知道偏向哪边的数，在容量判定里是危险的**，所以两个方向都写明。

#### 6.3.4 三条局限（与数据同行）

①本机采样期间 p8 正在跑全量对拍，**系统级基线被污染**——增量与偏置比值不受影响，**绝对基线不可外推**；
②负载是 4 路 clang++ 编 116 MB TU，不是 16 路 GCC 编 GCC 自身，共享因子可迁移性有限；
③这是**冒烟级验证**（证明机制读得出数、量级合理、偏置已知），**不是满负载检验**。

#### 6.3.5 仪器自证链条断在哪里（务必读）

**darwin 侧的内存仪器大概率全程只经冒烟检验、未经满负载检验。** 本机跑要占 p8 的窗口且未必拿得到，
即使拿到也是 16 核 / 64 GB，不是 3 核 / 7 GB 的 runner。
⇒ **darwin 侧的可靠性不等同于 linux 侧**：将来第一次在托管 runner 上真跑的人，
**先核一眼内存数据是否合理，再采信它**。

### 6.4 磁盘（四腿分列）

| job | 峰值估算 | runner 磁盘 | 结论 |
|---|---|---|---|
| `linux-15-2-0` | **2026-08-18 实测（宿主 df 差分）**：provision→build 占用 7,319,304 KiB ≈ **6.98 GiB / 7.49 GB**；`P7_DISK build-peak`（`du -sk` 极值）**未采到，该格为空** | 14 GB（规格值，含 OS 与预装软件） | **仍待判**（df 差分只给净增量，14 GB 上叠加 OS 后偏紧） |
| `darwin-15-2-0` | 未量化 | 14 GB | 未判定 |
| `darwin-12-2-0` | 未量化（另需 6 个 host-deps 源码树） | 14 GB | 未判定 |
| `darwin-8-2-0` | 未量化 | 14 GB | 未判定 |

三条 darwin 腿另有一项固定开销：MounRiver 官方包 1.34 GiB + 解出的官方树。三腿共用一次下载与一份
`actions/cache`，但**每个 job 各自要解包一次**。

**2026-08-18 合并更新（linux 腿注）**：`disk.tsv` 的 `build-peak` 行值为空——后台 `du -sk` 采样在这一跑
从未成功落值，磁盘结论**只有 df 差分一条支撑**（`after-provision` 884217152 → `after-build` 876897848 KiB avail）。
这是仪器的一处实测缺口：下一次真跑前应先核 `P7_DISK build-peak` 采样是否真的产出，再采信该行。

## 7. darwin 的交付形态（定稿，四件）

### 7.1 托管可行性：**未判定**

见 §6.1–§6.4：三腿各自的翻转点、缺锚情况与判定所需测量都已写明。**不写成「不可行」，也不写成「可行」。**

### 7.2 受支持的替代路径：本地镜像跑

**`tmp/p7-evidence/S4/darwin-window-run.sh` 是正式交付物**，配套准备脚本 `darwin-prepare.sh`。
后来者有一条真能跑的 darwin 验证路径，而不是只有一句「托管跑不了」。

```sh
# 一次性准备（窗口之外，可重跑，幂等）
tmp/p7-evidence/S4/darwin-prepare.sh 15.2.0 12.2.0 8.2.0

# 窗口内（每次一条腿）
tmp/p7-evidence/S4/darwin-window-run.sh 15.2.0
```

- **前置条件**：darwin-arm64 宿主；15.2.0 腿需 Homebrew zstd；8.2.0 腿需 Rosetta 2；
  准备脚本已落 `.p7-window-ready.tsv` 就绪标记。窗口内**不做准备**，缺任何一项在碰 symlink **之前**中止。
- **复原语义**：只动该版本的**一条**字面 symlink；动手前 `readlink` 取前值，
  **取不到就 abort 并上报，绝不猜恢复目标**；`trap restore EXIT HUP INT TERM`；
  复原后 `readlink` 复核必须等于前值，不等则非零退出并大声报错；前值与后值都回报。
- **证据落点**：`S4/window-<version>-<run_id>/`（全量日志、SUMMARY、探针、symlink 前后值、
  worktree 前后状态），以及 `S4/timing-darwin-<version>.tsv`、`S4/disk-darwin-<version>.tsv`。
- **隔离**：跑在 `S4/darwin-workspace-<version>/` 工作副本上（理由见 §4 同一条）。

### 7.3 workflow 自带仪器，首次真跑即自解

容量仪器建在 **workflow 本体**里而不是只在本地驱动脚本里：`P7_STAGE`（分段墙钟）、
`P7_SUBSTAGE`（构建阶段细分）、`P7_DISK`、`P7_MEM`、`P7_SAMPLE`（流式采样）、`P7_FACT`、`P7_TOOLCHAIN`。
**流式**是硬要求：每个样本一产生就吐，不攒到最后——6 h 是硬杀，攒在最后一步输出的数据在被杀的那次全丢，
**而那正是最该诊断的一次**。目标：一次被斩断的运行仍能从日志还原「跑到哪一段、各段多久、峰值多少」。

⇒ 将来第一次在真 runner 上跑，容量问题作为**副产品自解**，不需要另起测量任务。

### 7.4 升级路径与各自代价（只列，**不替用户选**）

| 选项 | 代价与前提 |
|---|---|
| **self-hosted runner**（本项目的天然答案） | 用户这台 16 核 Apple Silicon **原生**跑：无 qemu 仿真、无 6 h 上限、无 14 GB 磁盘上限、内存 64 GB。代价：需要注册 runner 与远端仓库；机器被 CI 占用；安全面（公共仓库上 self-hosted 需谨慎）。 |
| 拆 job + 缓存中间产物 | 把构建与 gate 拆成前后 job，中间产物走 cache。代价：`actions/cache` 单仓总容量上限与跨 job 传输时间；工具链树体积大，缓存命中率与恢复耗时都要实测；拆开后**不再是「同 run 同 cwd」**，需重新论证 `DW_AT_comp_dir` 一致性。 |
| 付费大机型 macOS runner | `-large` / `-xlarge` 属 larger runners，仅 Team / Enterprise 计划可用，公共仓库免费额度不覆盖。代价：订阅层级 + 按分钟计费。 |
| **golden 单跑变体**（R9-4） | `evt-golden.sh` 的双跑正是其**确定性自证**；改成单跑可省下单腿 27 次工程构建里的 9 次。**需改 harness 语义、需用户裁定、p7 不做。绝不实现，也不许在 CI 里用任何方式绕过双跑。** |

## 8. 发现

1. **仓库从未记录过工具链构建墙钟。** 六个阶段、三版本、双平台全部零差异达成，却没有任何一处留下构建时长，
   以致 phase-7 做容量估算时无锚可用（12.2.0 / 15.2.0 至今无实测锚）。这是可复现性文档的真实缺口。
   严重度低，但对后续阶段有用。**建议**（只提议、不改既有构建脚本——那是另一条工作流的面）：
   `act-verify.sh` 的 `timing.tsv` 形态若通用，可作为后续构建脚本记录墙钟的范式。
   **2026-08-18 合并更新**：本条对**跟踪面**仍成立（版本库里依旧没有构建墙钟记录），但 p8 起
   **证据树已有实测锚**——`tmp/phase8-evidence/8.2.0/s3/timings.tsv` 等（8.2.0 probes 128 s、quick 5 s、
   full-main 517 s、full-linkonly 128 s；15.2.0 darwin build 7m02s；12.2.0 清洁构建 2m44s），
   phase-7 容量估算时的「无锚可用」在后续阶段已不再成立。注意这些证据树 **gitignored、未跟踪**，
   所以「缺口」的准确表述是「未进版本库」，不是「从未测过」。
2. **`scripts/ci/{provision-official,prepare-sources}.sh` 曾会在干净 checkout 上必然失败。**
   两者都 `mktemp` 到 `$repo_root/tmp/`，而 `tmp/` 是 gitignored 且 git 不跟踪空目录——
   **真 CI 第一次跑就会死在这里**。由本地真跑 darwin 准备时撞出，已加 `mkdir -p "$repo_root/tmp"`。
3. **act 用 `sh -e`（dash）执行 `container:` job 的 `run:` 步骤**，`set -o pipefail` 非法、`PIPESTATUS` 不存在。
   若无仪器冒烟测试，这个缺陷会在取证跑的**构建步骤**炸——即 apt、provision、prepare 都跑完之后。
   修法：workflow 顶层 `defaults: run: shell: bash`。
4. **`shell: bash` 隐含 `-eo pipefail`**，于是后台采样循环里任何一次 `du` 瞬时失败都会**静默打死采样器**。
   修法：采样循环内每处命令替换都加兜底。发现 3 与 4 都由冒烟测试揪出，是「仪器必须先自证」的直接例证。
5. **归档身份由哈希锚定**：同一个「zstd 1.5.2」在 GitHub 上有两份字节不同的归档，靠版本号区分不了，
   靠 SHA256 才分得开。详见 §3.6。
6. **两个容易踩的测量坑**（方法论）：①探针第一版 `heavy.cc` 漏 `#include <numeric>`，编译秒失败
   ⇒ **根本没有负载，采出来是空数据却看起来像数据**；②`vm_stat` 的 "Pages free" 本机基线仅 85 MB，
   拿它推容量会得出「已经没内存了」的假结论。

## 9. 已知边界与未决

- `git.sr.ht` 作为 binutils 上游的可用性未做长期性验证；一次 clone 成功不等于持续可用。
  归档身份由哈希锚定的原则同样适用：换镜像合法，换版本非法。
- macOS 并发上限 Free/Pro/Team 均为 5 且与 larger runner 共享；`release.yml` 一次触发三条 darwin 腿，
  会占满其中三席。
- 三个 `actions/*` 均已有更高 major（`checkout` v7、`cache` v6、`upload-artifact` v7），
  本阶段按任务书取 v4 系最新。升 major 属口径变更，转出为未决项。
- P2-19（全量腿生成器未版本化）本阶段不收编，转出登记。**2026-08-18 合并更新：已闭合——`scripts/full-census` 已版本化（commit 4cb591e）。**
- `macos-15-intel` 于 2027 年 8 月退役，是 Actions 上最后一个 x86_64 镜像；本项目三条 darwin 腿
  已统一在 arm64 上，不受该退役影响。
- **P2-B（2026-08-18 合并更新：已在合并副本修复）**：`act-verify.sh` 的 gate 判据块以 `>>` 追加
  `summary-line.txt`，而内层 awk 又以同一文件为输入，块首写入的 `# expected:` 注释行因此成为一条
  无 `gate_pass=` 字段的 awk 输入 ⇒ 产物**恒含一条伪 `verdict FAIL`**（冻结跑的 `summary-line.txt`
  即为 2 条 SUMMARY + 2 PASS + 1 伪 FAIL），真失败会淹没其中。修法：期望值改写独立文件
  `summary-expected.txt`（同时恢复 `-s` 空文件守卫的原意），并把该文件并入证据拷贝清单。
  自证（前后块 × 好坏样例）：`tmp/publish/evidence/u2/p2b-selftest/`。
  **注意**：冻结证据树里那一跑的 `summary-line.txt` 仍带这条伪 FAIL，读旧证据时按此解释。
