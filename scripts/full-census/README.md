# full-census：8.2.0 全量 EVT gate 的生成与判据套件

本目录是 phase-8 closure §7③ 裁定的**收编件**：把此前只存在于 gitignored `tmp/` 下的全量腿
runner 套件纳入版本控制。收编的是**产生过 43969 证据的原件**，逐字节一致，不是改写版
（对照结果见文末「收编溯源」）。

## 1. 用途与 43969 gate 的关系

8.2.0 的收口 gate 是「canonical 能构建的全部 EVT 工程产物逐字节一致」，规模 **43969**，
由两条腿分工产生，两腿都打同一最终 install 树：

| 腿 | 脚本 | 面 | 规模 |
| --- | --- | --- | --- |
| 主腿 | `ours_runner.py` | census gate 面（官方侧可完整构建的工程） | 1170 工程 / **42285** 产物 |
| 扩展腿 | `linkonly_runner.py` | 仅链接阶段失败的工程，其编译成功的 `.o` | 33 工程 / **1684** 产物 |
| 合计 | — | — | 1203 工程 / **43969** |

扩展腿的存在源于 DECISIONS 2026-08-17 的 **P2-21 裁定**：排除粒度由工程级收紧为**产物级**——
仅链接失败的工程，其编译成功的 `.o` 仍入 gate，只剔 `.elf`/`.bin`。

配套件：`census_runner.py` 用官方工具链做全量普查并产出基线（同时**被两个 runner 以
`importlib` 当模块加载**，见 §4）；`render_manifest.py` 由 raw 表渲染 golden manifest；
`census_stats.py` 重算分区统计；`cross_checks.py` 做两 lane 交叉验证。

## 2. golden 的 `class` 列语义（重要）

`analysis/golden/8.2.0-darwin-arm64-full.tsv` 用 `class` 列在**同一个文件里**区分两个分区：

| class | 含义 | 行数 / 工程数 |
| --- | --- | --- |
| `gate` | census gate 面，主腿负责 | 42285 / 1170 |
| `gate-link-only` | P2-21 产物级扩展面，扩展腿负责 | 1684 / 33 |
| `aux` | 非 gate 辅助产物（`.map`/`.lst`/`.d` 等），不入 gate | — |

**易踩的坑**：`gate-link-only` 这个类名**只存在于 golden**，因为只有 golden 需要在一个文件里
区分两个分区。**每条腿在自己的结果表里一律把本面产物标为 `gate`**——扩展腿的
`compare-artifacts.tsv` 里 1684 行的 class 是 `gate`，不是 `gate-link-only`。
判据器按错误的类名过滤会读出空集（phase-8 DEV-P8-04 即栽在此处）。

## 3. 分区判据器 `partition-check.py`

用法：`python3 partition-check.py <ours_stage> <linkonly_stage>`
（例：`partition-check.py stage-p8s3 stage-p8s3`）

它是**独立于两条腿**的顶层判据：只读当前 golden、两腿的**逐产物原始行表**
（`ours-artifact-results.tsv` / `compare-artifacts.tsv`）与各自的 `identity/toolchains.json`，
**不读任何一腿自产的 summary 或 stdout**——这是验证器独立性要求（任务书硬约束 7）。

断言：

1. **行分区**：主腿 gate 行 + 扩展腿 gate 行 = 43969，且与当前 golden 行集**不重不漏**，
   两个子集分别等于 golden 的 `gate` 与 `gate-link-only` 分区。
2. **工程分区**：1170 + 33 = 1203，不重不漏。
3. **两腿身份一致**：两腿所用 install 树的工具哈希彼此相同，且等于活体安装树。
   （`identity/toolchains.json` 的 `ours` 是**混合 dict**——只有 `gcc`/`as`/`ld`/`objcopy`/`objdump`
   五项是含 `sha256` 的子 dict，其余是字符串；按形状筛选，勿逐项取值。）
4. **加强项**：两腿全部 gate 行 `status` 均为 `MATCH`，同样从原始行重算。

## 4. 路径假设与环境前提（**未改写，按裁定原样保留**）

收编时**没有**把内嵌路径参数化——改写就不再是「产生过 43969 证据的原件」。因此：

- `REPO` 由 `Path(__file__).resolve().parents[4]` 推出。该表达式是按**原位置**
  `tmp/toolchain_8.2.0/tools/full-census/` 的深度写的；从 `scripts/full-census/` 直接运行会推出错误的仓库根。
- `TOOLS`、`CENSUS_STAGE`、`EVIDENCE`、`STAGE` 一律硬钉 `tmp/toolchain_8.2.0/...`；
  两个 runner 通过 `importlib` 从 **`TOOLS/census_runner.py`**（即 tmp 下那份）加载共享模块，
  **不是**从本目录加载。
- `OURS_LINK` 硬钉字面量路径 `/Users/wch/Work/riscv-none-embed-gcc-10.2.0-1.2/darwin-x64/install/riscv-none-embed-gcc`
  （WCH 官方构建布局的复刻，字面量面要求）。
- 宿主前提：macOS + x86_64/Rosetta 工具链、`SOURCE_DATE_EPOCH=1767225600`、16 项目级 workers × `make -j2`。

**结论：本目录当前是「可版本化的权威副本 + 可读文档」，不是「就地可跑的可重定位工具」。**
要复跑，仍须在 `tmp/toolchain_8.2.0/tools/full-census/` 就位后从该处运行；
本目录的副本用于审计对照、代码审查与未来的参数化重构起点。
若日后要让它就地可跑，属独立改动，须重新取得 43969 证据后才可替换本副本。

环境变量：`OURS_STAGE` / `LINKONLY_STAGE` 指定 stage 子目录名；`OURS_LIMIT>0` 仅用于排练，
会缩小 gate 面，**不得用于验收跑**。

## 5. 收编溯源（逐字节一致对照）

来源：`tmp/toolchain_8.2.0/tools/full-census/`（六件）与
`tmp/phase8-evidence/8.2.0/s3/partition-check.py`（一件）。全部 `cmp` 判定 IDENTICAL。

| 文件 | sha256 |
| --- | --- |
| `census_runner.py` | `f04e653ff2a9e4b74743746dafbe85449d973e612cb0f0cdb3d22a4d3ade1848` |
| `ours_runner.py` | `95dd894200371779710a29f622b37f86362330a7ec83588e9b1185d1025fa689` |
| `linkonly_runner.py` | `bab18ba848ccaeba92d7878de91ddde3bd861c4c47ea0c3c00973344c83e02ff` |
| `render_manifest.py` | `57dd6cc080d61ebef16c0dc510865f598c12bceb441d1d6349494e888afb788e` |
| `census_stats.py` | `59f37f06f45226db53ff62e25e4ad4a1b6822181fa53b6863638bd9590e45370` |
| `cross_checks.py` | `32f68e88fe1e77ede24c96fb77ccf8399e22cfd8c8e8da3a6b84267fccd7f3eb` |
| `partition-check.py` | `49cb5a5462c4a907e3a7e57df4769293736a8b168b600604ce6f63e9755938f6` |

`ours_runner.py` 含 **phase-8 P8-F1 分区化修正**：其 pre-flight 对数块改为从**当前** golden 按
`class` 列派生主腿视图，并加两条分区穷尽断言，取代了原先硬编码的 `1170 / 42285`
（该硬编码在 P2-21 扩展 golden 后静默过期，导致主腿自扩展起从未成功跑过——
43969 一度是「扩展前 42285 + 扩展后 1684」的时间拼接）。时序可证收编的正是产生证据的那一版：
`ours_runner.py` mtime 12:03:29 早于 sealed run stage `stage-p8s3` 的 12:07:54；
`partition-check.py` v2 mtime 15:14:36 早于其 `PARTITION-PASS` 的 15:15。

对应证据：`tmp/phase8-evidence/8.2.0/s3/{regression-results.tsv,partition-check.out,timings.tsv}`、
轮报告 `round-report.md` §4 与 §6b。
