# phase-6 S1 基线考据：WCH GCC 8.2.0（riscv-none-embed，darwin-arm64 平台包）

> 执行会话：phase-6 工作流（转录 a592d307）。日期 2026-08-16。
> 证据根：`tmp/toolchain_8.2.0/evidence/s1/`（下文相对指针均以此为根）。四条并行轨道各有独立执行 agent，本文为编排会话综合，未复述的细节以各轨道原始交付物为准。

## 0. 结论摘要

1. **谱系锚定成功**：WCH 8.2.0 = xPack `riscv-none-embed-gcc-xpack` **v10.2.0-1.2 构建框架** + **v8.2.0-3.1 代组件源**（gcc 8.2.0 / binutils 2.32 / newlib 3.0.0 / gdb 8.3，SiFive freedom-tools v2019.05.0 组件四元组唯一命中）。「打包 10.2.0-1.2 vs GCC 8.2.0」之谜的解 = 新框架换旧源；源目录名 `riscv-gcc-10.2.0-1.1` 是框架钉死的 `GH_RELEASE` 所致，非笔误。
2. **一手证据就在随包内**：`ref/gcc/darwin-arm64/8.2.0/distro-info/` 是 WCH 原样发布的 xPack 构建目录，`scripts/host-defs-source.sh` 记录构建现场（`RELEASE_VERSION="10.2.0-1.2"`、`USER_NAME="wch"`、`TARGET_MACHINE="x86_64"`、构建机 macOS 10.13.6）。
3. **WCH 在构建配置层的唯一语义改动 = `GCC_MULTILIB`**：8.2.0-3.1 代的 19 条 + 3 条 XW（`rv32ecxw`/`rv32imacxw`/`rv32imafcxw`）= 官方 `-print-multi-lib` 23 行，逐项同序。
4. **XW 补丁面画像（对 S3 决定性）**：gcc 侧改动 = `-march` 解析器（吃 `x[w]`；【勘误 2026-08-16】原稿「`c` 后吃」已被 D1 的 21 条增补官方探针证伪并唯一化为「**无条件、仅执行一次、rv32/rv64 共路**」——`rv32imaxw`/`rv32ixw`/`rv32gxw`/`rv32exw` 官方全接受、`xx`→残余 `'x'`、`xww`→`'w'`；证据 `evidence/s3/d1/spec-probe/`，实现 commit 5ed9a2ca3）+ 私有 param `highcode-gen-section-name` + multilib 配置；**gcc 不生成任何 XW 指令，16 位压缩全部由 gas 完成**（同 RVC 机制，`riscv.md` 无 XW pattern）。as/objdump 各 3 个 WCH 符号（`wch_rvc_extension` 系）；**ld 零 WCH 痕迹**；as/ld/objdump 的 WCH 新增长选项数 = **0**（全量枚举，非候选否定）；objdump `-M` 面 = `{no-aliases, numeric, xw}`。
5. **可构建性普查**：转换器现行 flags 下官方 8.2.0 仅 1/9 可构建；按 MRS 原生 GCC8 拼装规则（一手证据 MRS2 extension.js：GCC8 只追加裸 `xw`，丢弃 B/Zmmul）达 **8/9**；唯一恒定剔除 **V3C LED**（`core_riscv.h:645` 内联汇编 `mcpy`，8.2.0 无此指令）。产物双跑 100% 逐字节稳定。
6. **两项需 Main 裁定**：golden 集口径（推荐 8/9）；`wvproj_to_make.py` 补 GCC8 分支的授权（`ref/wch-evt/` 超出本工作流单写者范围）。

## 1. 谱系锚定（轨道 A：`lineage/lineage-research.md`，205 行，全部 [已核] 带 URL）

- configure 全行 **36/36 token 与 v10.2.0-1.2 框架 `common-apps-functions-source.sh` L838–882 模板同序一致**（机械比对 `lineage/argv-compare.txt`）；v8.2.0-3.1 那代脚本被 4 个判别子证伪（bugurl 尾斜杠、`, 64-bit` 后缀、缺 `--with-native-system-header-dir`、多 `--disable-rpath`）。
- `--with-pkgversion` 的 `x86_64` 后缀 = xPack 自 v10.1.0-1.2（2021-11-04）起的 `${TARGET_MACHINE}` 命名；此前代次一律 `, ${TARGET_BITS}-bit` ⇒ 版本串本身即锁定框架代次。
- 随包 `distro-info` vs 上游 tag 全树比对：`patches/` 零差异；`scripts/` 仅 3 文件差异（1 个属上游 tag 后演进）；语义差异仅 `GCC_MULTILIB`（见摘要 3）。
- 组件源：`github.com/xpack-dev-tools/{riscv-gcc,riscv-binutils-gdb,riscv-newlib}` tag `v8.2.0-3.1`（tag object SHA 已落盘，GitHub tarball 无官方校验和）；newlib 树身份由 `licenses/newlib-4.1.0/COPYING.NEWLIB` 哈希落证。binutils 具体 fork tag 为反推，S2 vanilla 产物比对落证。
- S2 直接可用：源码必须置于 `sources/riscv-gcc-10.2.0-1.1`；`--build/--host` 逐字 `x86_64-apple-darwin17.7.0`；`MULTILIB_FLAGS` 空、`t-elf-multilib` 由 multilib-generator 生成（22-token 列表）；上游 `gcc-10.2.0.patch`/`binutils-2.35.patch` 不适用本代源。

## 2. 字面量面现场提取（编排会话直采，`gcc-v.txt`/`as-version.txt`/`ld-version.txt`/`ld-verbose.txt`/`multilib.txt`/`dumpspecs.txt`/`comment.bin`，shasum 见 `SHA256SUMS.s1-literals`；官方二进制锚 `SHA256SUMS.official-bins`）

- configure 全行逐字节存档（构建路径 `/Users/wch/Work/riscv-none-embed-gcc-10.2.0-1.2/darwin-x64/...`）。
- `.comment` = 51 字节 `\0GCC: (xPack GNU RISC-V Embedded GCC x86_64) 8.2.0\0`（`comment.bin` 原样）。
- as/ld 版本串 `GNU assembler/ld (xPack GNU RISC-V Embedded GCC x86_64) 2.32`。
- `ld --verbose` SEARCH_DIR 单行 4 目录（install 树 lib + `/usr/local/lib` + `/lib` + `/usr/lib`）。
- multilib 23 行；dumpspecs 已存档。环境钉法与 harness 相同（`LC_ALL=C`、`SOURCE_DATE_EPOCH=1767225600`）。

## 3. 行为探针面（轨道 B：`probes/README.md`，9 组脚本 + 2500 项清单，双跑稳定；一处门控表述已由编排会话依 optsweep + 现场裁定更正，见 §7）

代差要点（相对 15.2.0/12.2.0，全部 8.2.0 现场实测）：

| 面 | 8.2.0 实测 | 备注 |
| --- | --- | --- |
| gcc march | 仅收贴写 `rv32imacxw` 系；拒 `_xw`/版本后缀/`_zba`/`_zicsr`/大写 | 与 as 分叉（15.2.0 无此现象） |
| as march | 宽松 passthrough：`_xw`、`xw1p0/2p0/9p9`、`_xq` 全收 | x* 子集不校验名/版本 |
| 属性节 | **默认双侧均不产生 `.riscv.attributes`**；驱动不传 `-march-attr`；显式开启后裸 `xw`→`xw2p0`（同 15.2.0，异于 12.2.0 的 `xw1p0`），E 基座 `rv32e1p9` | survey §9「未测」项已补 |
| mapping symbols | 无 `$x`/`$d` | 2.32 早于引入 |
| XW 编码 | 8 条 16 位形式与 15.2.0 逐字节同（`c.lbu`=0x2188 锚点）；立即数边界真解析 | `mcpy`/`mrsl`/`mrslu`/`wexti` 完全不存在 |
| XW 门控 | `xw` ∧ `c` 双因子：缺 `c` → `unrecognized opcode`；有 `c` 缺 `xw` → `illegal operands` | 更正后结论，证据 `probes/raw/05-xw-encodings/gating-correction/` |
| 反汇编 | 默认按 D 槽解码；WCH 私有 `-M xw` 开启后 8 条正确；`--help` 第 78–79 行 WCH 自撰串（第 79 行 = 2 空格+7 TAB+助记符表）| 逐字节复刻面 |
| 隐藏选项 | `--w_priv_spec`/`--wchsoftlib`/`--whighcode` 三侧全无 | 15.2.0 机制在 8.2.0 不存在 |
| interrupt | `WCH-Interrupt-fast`：无栈帧 + `mret`，不受 xw 门控；错拼降级 `ret`，告警 `unrecognized argument to 'interrupt' attribute [-Wattributes]`（上游文案，见 optsweep §6） | 与 15.2.0 枚举式文案代差属上游演进 |
| highcode | 汇编层零特殊处理；gcc `--param highcode-gen-section-name=1` 把恰为 `.highcode` 的函数段改名 `.highcode.<fn>` | 下游用途待 EVT 侧证据 |
| D+C+XW | march 带 `xw` 时 `c.fld`/`c.fsd`/`c.fldsp`/`c.fsdsp` 禁用（`c.flw`/`c.fswsp` 保留）；`rv32imafdcxw` 全 ABI 退默认 multilib；无 D+xw 库 | 与 15.2.0 同形但需独立保真 |
| as 默认 | 无 `-march` 默认 arch=rv32imafd 行为（默认串 `rv32i2p0_m2p0_a2p0_f2p0_d2p0`） | |

## 4. 选项面与 WCH 标记全量取证（轨道 D：`optsweep/optsweep.md`）

- as/ld/objdump 长选项表全量枚举（270 具名项 + ld emulation 22 项）对照 fork `v8.2.0-3.1` 源码：WCH 新增 = **0**；「表内有而 --help 不列」12 项全部为上游本有。表边界用符号地址区间 + `md_longopts_size` 交叉 + 无符号通用扫描（19 段游程零 UNCOVERED）钉死。
- objdump `-M` 为内联 strcmp 链 `{no-aliases, numeric, xw}`，`xw` 以 `'x','w','\0'` 内联比较实现（纯 strings 必漏），大小写敏感。
- WCH 符号：as/objdump 各 3（`match_with_wch_rvc_extension`/`match_without_wch_rvc_extension`/`wch_rvc_extension`）；ld 零；cc1 系被 strip（字符串证据 + 行为反推，见未决）。
- gcc param 计数 207 = 上游 206 + `highcode-gen-section-name`；`-m` 选项 14 个与 fork `riscv.opt` 逐项一致（无 `-mxw`）。
- **计划外关键发现**：①WCH 改 gcc `-march` 解析器——上游 `riscv_parse_arch_string` 在扩展串解析完后遇残余即报错，WCH 插入「吃一个 `x`、可选吃一个 `w`」（判据：`rv32imacxq`→残余 `'q'`、`rv32imacxwz`→`'z'`、**`rv32imacx` 直接通过**、`rv32imac_xw`→`'_xw'`；诊断文案是上游串，纯文案 diff 不可见）。【勘误 2026-08-16】本轮「`c` 后插入」的定位随后被 D1 增补探针细化为**无条件步骤**（与 `c` 无关、仅一次、rv32/64 共路），见 §0.4 勘误与 `evidence/s3/d1/spec-probe/`。②gcc 不生成 XW 指令：同源 `-Os` 下 `rv32imac` 与 `rv32imacxw` 的 `-S` 输出 md5 相同，差异只在 `.o`（gas 压缩）。
- 15.2.0 的 `non-standard111` 类拼写错误串在 8.2.0 不存在。

## 5. 可构建性普查与 golden 集裁剪（轨道 C：`buildability/buildability.md`）

- 三种口径：转换器现行 flags **1/9**（仅 v3a；其余 8 个全部 `unsupported ISA substring`，未进编译阶段）；MRS 原生 GCC8 归一 **8/9**；仅「MRS 声明 GCC8」**3**（v3a/v4bc/v4f）。
- MRS 原生规则一手证据：MRS2 `extension.js`（`buildability/mrs-march-builder.txt`）——march 拼装按 component_toolchain 分岔，GCC12/15 追加 `_zba_zbb_zbc_zbs`/`_zmmul`/`_xw`，GCC8 只追加裸 `xw`，B/Zmmul 由 MRS 自行丢弃。8.2.0 对 B/Zb/Zmmul 无任何可接受拼法（`march-probe.tsv` 穷举）。
- **8/9 不可读成「按工程原样请求可构建 8 个」**（buildability §0 警示原文）：8 个中 5 个（v2ac/v3b/v3f/v3f-evt/v5f）以丢弃工程明确请求的 B/Zmmul 为语义代价——真实能力缺失，非拼写问题；纯拼法归一、语义逐项一致的只有 v4bc/v4f（v3a 无需归一）。
- 恒定剔除：**v3c-led**（`core_riscv.h:645` 内联 `mcpy`，gas 2.32 `unrecognized opcode`，证据 `logs/v3c-led.probe-r1.err`）。
- `wvproj_to_make.py` 只实现 GCC12/15 分支（L632–645）；`--gcc-major 8` 触发 `minimum_major=12` 静默升级（L886–909）⇒ **`--compiler-path` 是 8.2.0 唯一入口**，「--gcc-major 8 与 MRS 原生一致」在现状下不成立（需补 GCC8 分支，见未决）。基串与 `-mabi` 在 9/9 与工程元数据一致，偏差仅在扩展后缀。
- 双跑：产物（283 文件，两口径合计）100% 逐字节稳定 ⇒ S2 golden 双跑口径直接沿用。失败路径 stderr 受 `make -j2` 交错影响不逐字节稳定（行集合相同）⇒ 诊断类比较须单调用采集，构建日志不入字节 gate。
- 附带：xw 在 8.2.0 真实生效（lbu/sb/lhu 压 2 字节）；8.2.0 `.o` 无属性节；随包 objdump 默认不解 XW，`.lst` 显示 fld/fsd 形态。

## 6. 前提登记（premise register）

| 前提 | 证据 | 状态 |
| --- | --- | --- |
| 框架 = xPack v10.2.0-1.2；组件源 = v8.2.0-3.1 代（freedom-tools v2019.05.0 系） | `lineage/`（36/36 argv、distro-info 一手、四元组唯一命中） | 已验证 |
| binutils fork 精确 tag = v8.2.0-3.1 | licenses 无判别力，属反推 | 待 S2 vanilla 产物比对 |
| WCH 构建配置层唯一语义改动 = GCC_MULTILIB 19+3 | `lineage/`（distro-info 全树 diff） | 已验证 |
| gcc 拒 `_xw`、仅贴写；as passthrough；无 mcpy 系 | `probes/raw/01,02,05` | 已验证 |
| 默认无属性节；显式开启裸 `xw`→`xw2p0` | `probes/raw/03` | 已验证 |
| XW 压缩由 gas 完成，gcc 无 XW 代码生成 | `optsweep/`（-S md5 相同 + .o 差异） | 已验证 |
| as/ld/objdump WCH 新增长选项 = 0；`-M` 面完备 | `optsweep/`（全量枚举） | 已验证 |
| golden 集 = 9 工程中 8 个（剔 v3c-led），MRS-GCC8 march 口径 | `buildability/` | 已测量，口径待 Main 裁定 |
| 产物双跑逐字节稳定 | `buildability/` §4 | 已验证 |
| arm64 宿主构建产物与官方（x86_64 编译器产出）逐字节可达 | — | 待 S2/S3 实测 |
| 老代码基（gcc8/binutils2.32）可在现代 macOS arm64 完成构建 | — | 待 S2 实测（host/ 补丁面） |

## 7. 过程偏差登记（S1）

| # | 偏差 | 处置 |
| --- | --- | --- |
| DEV-P6-01 | 轨道 A agent 对其自建 scratch（`lineage/downloads/tagtree/.../tests`，本次自解可再生内容）误用一次 `rm -rf`，违反「破坏性操作先问」硬规则 | 从保留 tarball 原样重解恢复，diff 复验结论不变，无证据损失；agent 已自报 |
| DEV-P6-02 | 轨道 B `probes/README.md` 门控行原稿（「恒在 opcode 表内、无 xw 一律 illegal operands」）对无 `c` 基座不成立 | 轨道 D 反汇编证据 + 编排会话 8-march 现场裁定探针（stderr 哈希三聚类）更正原文，更正标注在行内，证据 `probes/raw/05-xw-encodings/gating-correction/` |
| DEV-P6-03 | 编排会话一次裁定探针误用残留相对 cwd，将证据目录嵌套建到 `probes/work/` 下；另有一个临时文件短暂落于 `/tmp` | 目录已搬正并原地复跑复验（SHA256SUMS.gating-correction 全 OK），`/tmp` 文件已删；嵌套空目录已清 |
| DEV-P6-04 | Main 身份冲突（两会话均自称 Main） | 转录指纹核验 + 用户原话指定 + openwch-05 关闭，地址固化 openwch-f4；全程 `main-identity-log.md` |

## 8. 未决问题（S1 → S2/S3 路由）

**Main 裁定结果（2026-08-16 回执，DECISIONS 已录 81fefdb）**：宿主路线批准 x86_64/Rosetta（任务书 arm64 默认为自身矛盾，按执行方案修正，plans/gcc-8.2.0.md 已由 Main 同步）；R1 取 C=8（归一规则=MRS 自身行为，6 个反事实工程与 5 个丢 B/Zmmul 语义代价在 golden manifest 头与本文档如实登记——即本文件 §5）；R2 授权限定修改转换器+README（四约束：附加性字节自证、消除显式 8 的静默升级、diff 单列、独立逻辑单元）；/Users/wch 布局推迟 ack；偏差 01–04 登记接受（-01 附纪律提醒：rm -rf 前先在日志声明目标与理由）。
**跨版本事实（Main 补录）**：裸 `xw` 规范化版本三代三样——8.2.0=`xw2p0`、12.2.0=`xw1p0`、15.2.0=GCC 侧 `xw2p0`/GAS mapping `xw2p2`。

**原裁定请求存档（已由上述回执关闭）**：
1. **golden 集口径**：A=1（转换器现行 flags）/ B=3（仅 MRS 声明 GCC8 工程）/ C=8（9 工程按 MRS-GCC8 march 归一的可构建子集）。推荐 **C**：与任务书「golden 集 = 可构建子集」及 15.2.0 先例（9 工程含 12.2 声明工程照建）同构；march 用 MRS 自身的 GCC8 拼装规则，非我方发明。集合 C 中 6 个工程系「MRS 声明 GCC12/15」的反事实构造，如实登记。
2. **`wvproj_to_make.py` GCC8 分支**：补分支（复刻 extension.js GCC8 规则 + 停用静默升级路径于显式 8 场景）需写 `ref/wch-evt/`，超出本工作流单写者范围。请 Main 仲裁：授权本工作流限定文件写入，或由 Main/其他持权方执行。S2 golden 与 S3 全量普查都依赖该入口（临时替代：`--compiler-path` + 后处理 march，重复劳动且易漂移）。

**S2 自答**：binutils fork tag 落证；源树进入 `sources/` 的机制（预置目录 vs URL 覆盖，含规避 multilib-generator 重跑与 `gcc-10.2.0.patch` 误套的口径——lineage 已给出可执行方案）；8.2.0 与 15.2.0 `.o` 属性节可比口径（是否有 EVT 工程显式 `-march-attr`）。
**S3 素材**：`WCH-Interrupt-fast` gcc 接入点定位（cc1 被 strip，源码层面在补丁开发时自然落证）；`highcode-gen-section-name=1` 下游用途（EVT 链接脚本侧）；社区分析 8 条 URL（全部 [待核]，仅作对照不采信）。
