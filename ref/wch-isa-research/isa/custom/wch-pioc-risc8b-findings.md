# WCH PIOC / RISC8B 子系统:实物清点与已验证事实

本文件是**工作输入**(供后续两份正式文档取用),不是最终文档。所有内容均为本轮亲手实测,命令可复现。

**引用的一手件与版本**(完整账本见 `wch-doc-provenance.md`):`CHRISC8B.PDF` 版本 2B(sha256 `38231bec89ea50ab`,V006/V205/H417 三份逐字节相同)· `CHRISC8B-EN.pdf` Version 2B(`a3b0ac3fa84387ee`)· `PIOC.PDF` 版本 1(`61e543eb2dcdf538`,三份逐字节相同)· `PIOC-EN.pdf` Version V1(`d8b62cd7359d53c1`)· `PIOC User Manual-EN.pdf` V1.0(`62b3ed245b6a43b2`)· `PIOC_INC.ASM` V1.0(`4407b61b208a48ed`)· `RGB1W.ASM`(`754262d76a010c8c`,未标版本)· `RGB1W_inc.h`(`b23125ee811a1078`,未标版本)。

## 1. 这是什么

WCH 部分芯片内含 **PIOC(可编程 I/O 协处理器)**,它有**独立于 RISC-V 的自有指令集 RISC8B**。这与 RISC-V 侧的 XW 压缩扩展是**两套互不相干的指令体系**,文档中必须分开处理。

关键差异:RISC-V 侧大量证据来自闭源二进制库;PIOC/RISC8B 侧则随包提供指令集手册、汇编器、汇编源码和编译产物。手册定义 66 个格式,但当前随包样本只实际覆盖 39 个,不能把“材料齐全”写成“66 个格式均已动态验证”。

## 2. 实物清单(均已确认存在)

### 2.1 文档

| 文件 | 首页标题 | 所在树 |
|---|---|---|
| `CHRISC8B.PDF` | 《RISC8B 内核单片机指令集与汇编工具》版本 2B | V006 / V205 / H417 |
| `CHRISC8B-EN.pdf` | 同上英文版 | H417 |
| `PIOC.PDF` | 中文完整 PIOC 手册,版本 1 | V006 / V205 / H417 |
| `PIOC-EN.pdf` | 完整英文对应版,Version V1 | H417 |
| `PIOC User Manual-EN.pdf` | 2 页 1-Wire 快速入门,并非 `PIOC.PDF` 英文版 | H417 |

手册开篇原文(`CHRISC8B.PDF` 第 1 页):

> WCH-RISC8B 是 8 位数据宽度的精简指令集单片机内核,RISC8B 基于 RISC8A 新增了一些位传送指令。所有指令宽度均为 16 位,指令由操作码和操作数组成。**RISC8B 共有 66 条指令**,根据操作对象分为:控制类,面向字节操作类,常数操作类,面向位操作类,转移类。

操作数符号约定(同页):`f` = SFR 或 RAM 寄存器(0x00–0xFF);`F` = 扩展地址 SFR/RAM(0x000–0x1FF);`A` = 工作寄存器;`C` = 进位;`Z` = 零标志;`d` = 目的寄存器(0/A → 结果入 A,1/F/空 → 结果入 f);`b` = 位选择 0–7;`a` = 独立位选择 0–3(0 对应 C,1–3 为自定义独立位);`k2`/`k8`/`K7`/`k9`/`k10`/`k12` = 各宽度常数;`TOS` = 栈顶;`1#ff`/`2#ff` = 自定义快速 SFR。

### 2.2 工具链(随包发布)

`EXAM/PIOC/Tool_Manual/Tool/` 下:

- `WASM53B.EXE` —— RISC8B 汇编器
- `BIN_HEX.EXE` —— 把 `.BIN` 转成 C 数组头文件

编译脚本(`RGB1W.BAT`)原文:

```
..\..\Tool_Manual\Tool\WASM53B  RGB1W
..\..\Tool_Manual\Tool\BIN_HEX  RGB1W.BIN  RGB1W_inc.h  /C
```

(Windows 可执行文件;本机未运行,仅记录其存在与调用方式。)

### 2.3 源码与编译产物

- **87 个 PIOC 目录**、**30 份 `.ASM` 文件**:15 个程序源+15 个 EQU-only `PIOC_INC.ASM`,覆盖 1-Wire、Single-Wire、NEC 红外、IIC、UART 等外设模拟场景;
- `PIOC_INC.ASM` —— SFR 定义包含文件;
- `*_inc.h` —— 编译生成的 C 数组;
- `PIOC_*_CODE` 数组嵌在示例 C 代码中(见 V205 的 `PIOC_1_Wire/User/RGB1W.c`、各 `main.c`)。

## 3. SFR 寄存器映射(抄自 `PIOC_INC.ASM`,原文注释:`include file for PIOC/eMCU, V1.0, by W.ch @2022.08`)

| 地址 | 名称 | 地址 | 名称 |
|---|---|---|---|
| 0x00 | `SFR_INDIR_PORT` | 0x0A | `SFR_PORT_DIR` |
| 0x01 | `SFR_INDIR_PORT2` | 0x0B | `SFR_PORT_IO` |
| 0x02 | `SFR_PRG_COUNT` | 0x0C | `SFR_BIT_CONFIG` |
| 0x03 | `SFR_STATUS_REG` | 0x1C | `SFR_SYS_CFG` |
| 0x04 | `SFR_INDIR_ADDR` | 0x1D | `SFR_CTRL_RD` |
| 0x05 | `SFR_TMR0_COUNT` | 0x1E | `SFR_CTRL_WR` |
| 0x06 | `SFR_TIMER_CTRL` | 0x1F | `SFR_DATA_EXCH` |
| 0x07 | `SFR_TMR0_INIT` | 0x20–0x3F | `SFR_DATA_REG0` … `SFR_DATA_REG31` |
| 0x08 | `SFR_BIT_CYCLE` | | |
| 0x09 | `SFR_INDIR_ADDR2` | | |

`SFR_CTRL_RD` / `SFR_CTRL_WR` / `SFR_DATA_EXCH` 是主核↔PIOC 的交互寄存器,`SFR_DATA_REG0..31` 是双方共享的数据寄存器组——示例里用 `EQU` 把它们重命名为业务变量。【手册】`PIOC-EN.pdf` V1 (`d8b62cd7359d53c1`) PDF p3/p10/p12 已确认同址写时 host 优先、CTRL 状态位的置位/消费清零和 `SFR_DATA_EXCH` 单周期位传送;多字节原子性与精确端到端时序仍未给出。

## 4. 已验证的编码事实(源码 ↔ 编译产物逐字对照)

样本:`QingkeV2C_CH32V006_EVT/EXAM/PIOC/PIOC_1_Wire/Asm/` 的 `RGB1W.ASM` 与 `RGB1W_inc.h`。

`RGB1W_inc.h` = **1,358 字节 = 679 条 16 位指令,小端序**。与源码对照:

| 源码 | 字地址 | 编码 | 结论 |
|---|---|---|---|
| `ORG 0x0000` + `DW 0x0000` ×2 | 0–1 | `0000 0000` | 复位向量处两个保留字(RESERVED INFO / RESERVED ID) |
| `MCU_START: NOP` ×2 | 2–3 | `0000 0000` | **`NOP` 编码为 `0x0000`** |
| `JMP WAIT_COMMAND` | 4 | `6025` | **`JMP` = opcode `0x6` + 12 位字地址**;`0x025` = 37 |
| `WAIT_COMMAND:` 首条 | 37 | `5E1C` | 跳转目标落点与上式一致,**互相印证** |
| `ORG 0x0008` 后 5 条 `NOP` | 8–12 | `0000` ×5 | 地址是**字地址**(word-addressed),非字节地址 |

由此确立三条可直接用于后续解码的事实:**指令定长 16 位;C 数组按小端存放;`ORG`/`JMP` 的地址单位是字**。

### 4.1 与手册编码表的独立互证(两条路径吻合)

上表是从**二进制编译产物**解出的;`CHRISC8B.PDF` v2B 的指令表则由文档扫描单元**独立抽取**。两者对撞:

| 指令 | 手册编码表(`CHRISC8B.PDF` v2B,sha256 `38231bec89ea50ab`) | 本文件的二进制实测 | 结论 |
|---|---|---|---|
| `NOP` | `00000000 000000xx` → `0000` | word 2–3 = `0000` | ✔ 一致 |
| `JMP k12` | `0110kkkk kkkkkkkk` → `6kkk`,`k12→PC` | word 4 = `6025`,目标 word 37 落点吻合 | ✔ 一致,且 12 位字段语义得证 |

**手册文本抽取与二进制解码是两条完全独立的路径,结论相同** —— 这是 RISC8B 侧编码事实目前最强的证据形态(RISC-V 侧的 XW 拿不到这种互证,因为手册根本没给编码表)。

### 4.2 源码里那两条 NOP 的用途(手册给出了解释)

`RGB1W.ASM` 的 `MCU_START` 处有两条看似多余的 `NOP`。【手册】`CHRISC8B.PDF` v2B (`38231bec89ea50ab`) PDF p10 对采用 OTP 程序 ROM 的目标说明位只能 0→1,并建议在关键模块前预留 `NOP`,以便后续改为跳转。该物理限制只对手册所述 OTP 目标成立,不能外推到所有 PIOC 实现。

这条对等价重写有直接意义:**源码中的 NOP 不一定是延时或对齐,可能是刻意保留的补丁位**,重写时不可随意优化掉。

复现命令:

```sh
python3 - <<'EOF'
import re
h=open('tmp/wch-evt/evt/QingkeV2C_CH32V006_EVT/EXAM/PIOC/PIOC_1_Wire/Asm/RGB1W_inc.h','rb').read().decode('latin-1')
by=[int(x,16) for x in re.findall(r'0x([0-9A-Fa-f]{2})',h)]
w=[by[i]|(by[i+1]<<8) for i in range(0,len(by)-1,2)]
print(len(by),'bytes =',len(w),'insns'); print([f"{x:04X}" for x in w[:5]], f"{w[37]:04X}")
EOF
```

## 5. 对两份正式文档的意义

- **指令文档**:RISC8B 必须单列一章,与 RISC-V 侧的 XW/custom-0 分开。它的权威来源是 `CHRISC8B.PDF` 的 66 条指令表(正由文档扫描单元整理)。
- **库中如何使用的文档**:PIOC 侧有源码级 ground truth。第二轮静态闭环为 15 个程序的 ASM→LST→BIN/C-array 全部一致;7,307 条非 `DW` 行匹配手册 mask,实际覆盖 39/66 格式。它能给出这些样本的完整实例,不能替代未出现 27 格式的动态验证。

## 6. 尚未确认

- 手册已给 66 个格式的完整位表;当前随包样本只出现 39 个,其余 27 个是否被 WASM53B v3.1 接受仍未确认;
- PIOC 单寄存器写优先级和握手已从手册确认;多字节原子性、精确 cycle 相位和端到端延迟仍未确认;
- PIOC 是否存在于本项目关注的全部芯片,还是仅 V006/V205/H417 等型号;
- `WASM53B.EXE` 未运行(Windows 可执行),故未做"重新汇编比对"这类验证。
