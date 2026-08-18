# WCH EVT PDF 指令集/寄存器定位索引

扫描范围：`tmp/wch-evt/evt/` 下全部 PDF（11 棵 EVT 树，109 份文件，按 sha256 去重后 81 个内容组）。**不含** `tmp/wch-evt/application_notes/` 下的 13 份（另一路处理）。

方法：`pdftotext -layout` 逐组抽取一次（代表路径任选其一），产物存于 `tmp/wch-evt/eval/evt-pdf-text/<sha256前8位>.txt`；版本号取自 `pdftotext -f 1 -l 2 -layout "<pdf>" - | grep -iE '版本|Version'`（部分文档需翻到正文/页脚才能确认，已在表中注明）。**抽取产物 `.txt` 不是一手件，不作为出处；出处一律指向原始 PDF 及其 sha256。** 引用格式：`文档名 vX.Y (sha256:前16位) 第 N 页`。

---

## 0. 交付前置：PIOC 版本对应关系核查（协调者要求项）

协调者提供的四份优先目标基线：

| 文件 | 版本 | sha256(前16) |
|---|---|---|
| `CHRISC8B.PDF` | 版本:2B | `38231bec89ea50ab` |
| `CHRISC8B-EN.pdf` | Version: 2B | `a3b0ac3fa84387ee` |
| `PIOC.PDF` | 版本:1 | `61e543eb2dcdf538` |
| `PIOC User Manual-EN.pdf` | Version: V1.0 | `62b3ed245b6a43b2` |

**核查结论 1（CHRISC8B 中英文）：内容 1:1 对应，无实质差异。** 逐节核对：两者章节结构完全一致（1 概述/Overview、2 指令集/Instruction Set、3 指令周期/Instruction Cycle、4 等效和重新定义指令、5 寻址方式、6 汇编程序 6.1-6.6、7 指令详细说明[两版均为空/"暂无"·"(Not yet)"]、8 常见问题 8.1-8.6）；66 条指令的二进制码、HEX 码、助记符、操作数、执行操作、影响状态逐条比对一致（控制类18/字节类16/常数类16/位操作类9/转移类7 = 66，两版计数相同）。两版仅版本号书写形式不同（中文"版本：2B" vs 英文"Version: 2B"），本质是同一版本号，无需存疑。

**核查结论 2（PIOC.PDF 中文 vs "PIOC User Manual-EN.pdf"）：这是重要事实——两者根本不是同一份文档的中英文版本，是协调者基线表里的一处配对错配。**

实际读取内容后发现，EVT 树里 PIOC 相关英文文件的**文件名与内容不对应**：

- 文件名为 `PIOC-EN.pdf`（sha256:`d8b62cd7359d53c1`）的文件，首页标题实际是 **"PIOC User Manual" / "Manual" / "Version: V1"**（页脚打"V1.0"），内文是完整技术手册——概述、特点、指令/程序空间/堆栈、49 个 SFR 寄存器全表、逐寄存器位域说明、应用——**章节结构与寄存器表逐项对应 `PIOC.PDF`（中文，版本1）**：同样 21 个已用地址（00H-0CH、1CH-3FH）、同样的 SFR 名称（`SFR_INDIR_PORT`…`SFR_DATA_REG31`）、同样的 R/W/U/S 读写属性字母、同样的复位默认值（如 `SFR_BIT_CONFIG` 复位值均为 `00010000`）。**这才是 `PIOC.PDF` 真正的英文对应版本。**
- 文件名为 `PIOC User Manual-EN.pdf`（sha256:`62b3ed245b6a43b2`，协调者基线表里的那份）标题却是 **"User Guide for PIOC" Version: V1.0**，内容只有 2 页——是"以 CH32H417 为例，用 MounRiver 编译 PIOC_1_Wire 汇编示例并下载"的**5 步快速上手指南**（截图为主，无寄存器信息），其真正的中文对应版本是 `PIOC 使用说明.pdf`（sha256:`a1b0149616442cfa`／`2515e76f0c2841b2`，版本：V1.0，内容同样是 5 步编译下载 1-Wire 示例的快速指南）。

即：WCH 在 EVT 树里对 PIOC 文档的中英文命名规则不一致——中文把"完整手册"叫`PIOC.PDF`、"快速指南"叫`PIOC 使用说明.pdf`；英文把"完整手册"叫`PIOC-EN.pdf`、"快速指南"却叫`PIOC User Manual-EN.pdf`（字面像"用户手册"，实际是快速指南）。**协调者基线表中 `PIOC User Manual-EN.pdf` 一行如果用于与 `PIOC.PDF` 做内容对照，会找错文档**——真正该对照的是 `PIOC-EN.pdf`。版本号形式差异（中文"版本：1"／英文"Version: V1"／页脚"V1.0"）本身不构成实质版本冲突，是同一版本的中英文书写惯例差异；**真正的问题是文件配对，不是版本号**。下文第 2、3 节的 PIOC 内容统一以 `PIOC.PDF` + `PIOC-EN.pdf` 为准。

---

## 1. 文档清单

列说明：sha256 前16位 | 真实文档名（首页标题）| 版本 | 出现的树（路径省略仓库根 `tmp/wch-evt/evt/`）| 页数 | 抽取

### 1.1 RISC8B / PIOC 子系统

| sha16 | 真实文档名 | 版本 | 出现的树/路径 | 页数 | 抽取 |
|---|---|---|---|---|---|
| `38231bec89ea50ab` | WCH-RISC8B 内核指令集与汇编工具 | 版本：2B | V006、V205、H417（3份逐字节相同）`.../EXAM/PIOC/Tool_Manual/Manual/CHRISC8B.PDF` | 10 | 成功，表格完整可读 |
| `a3b0ac3fa84387ee` | RISC8B Core MCU Instruction Set and Assembly Tool | Version: 2B | 仅 H417 `.../CHRISC8B-EN.pdf` | 14 | 成功，表格完整可读 |
| `61e543eb2dcdf538` | 可编程协议 I/O 微控制器 PIOC 手册 | 版本：1 | V006、V205、H417（3份逐字节相同）`.../EXAM/PIOC/Tool_Manual/Manual/PIOC.PDF` | 9 | 成功，SFR 全表完整可读 |
| `d8b62cd7359d53c1` | WCH PIOC manual / PIOC User Manual | Version: V1（页脚 V1.0） | 仅 H417 `.../EXAM/PIOC/Tool_Manual/Manual/PIOC-EN.pdf` | 12 | 成功，SFR 全表完整可读，与上条逐节对应 |
| `a1b0149616442cfa` | PIOC 使用说明（1-Wire 示例快速指南） | 版本：V1.0 | V006、V205 `.../EXAM/PIOC/Tool_Manual/Manual/PIOC 使用说明.pdf` | 2 | 成功 |
| `2515e76f0c2841b2` | PIOC 使用说明（1-Wire 示例快速指南，H417 版，路径含 V3F/V5F 双工程） | 版本：V1.0 | 仅 H417 | 2 | 成功 |
| `62b3ed245b6a43b2` | User Guide for PIOC（1-Wire 示例快速指南英文版；**文件名`PIOC User Manual-EN.pdf`具误导性**，见第0节） | Version: V1.0 | 仅 H417 `.../PIOC User Manual-EN.pdf` | 2 | 成功 |

### 1.2 高速接口 / 总线（优先目标）

| sha16 | 真实文档名 | 版本 | 出现的树/路径 | 页数 | 抽取 |
|---|---|---|---|---|---|
| `a115a26443ee206d` | CH32H417 UHSIF Development Reference Manual | Version: V1.0 | 仅 H417 `.../EXAM/UHSIF/CH32H417 UHSIF Development Reference Manual-EN.pdf` | 13 | 成功 |
| `c4c31b260db2987f` | CH32H417 通用高速接口（UHSIF）开发参考手册 | 版本：1.0 | 仅 H417 `.../EXAM/UHSIF/CH32H417通用高速接口（UHSIF）开发参考指南.pdf` | 11 | 成功，与上条内容 1:1 对应（含同一处"详见 CH32H417DS0.PDF"的外部引用缺口） |
| `df41d54ffde33467` | I2C 接口使用指南 | 版本：1B | 仅 CH587 `.../EXAM/I2C/I2C接口使用指南.PDF` | 7 | 成功 |

### 1.3 网络协议栈（WCHNET，优先目标）

| sha16 | 真实文档名 | 版本 | 出现的树/路径 | 页数 | 抽取 |
|---|---|---|---|---|---|
| `1e1bf85517182dc3` | WCHNET Protocol Stack Library Application Note | Version: 1D | V203、V20x、V317（3份逐字节相同）`.../EXAM/ETH/WCHNET Protocol Stack Library Application Note.pdf` | 26 | 成功 |
| `09e3fa9f6069321b` | WCHNET 协议栈库说明 | 版本：1D | V203、V20x、V317（3份逐字节相同）`.../EXAM/ETH/WCHNET使用文档.pdf` | 27 | 成功，与上条内容对应（中英文版本号一致，均 1D） |
| `52c2105f0c584f05` | WCHNET WEB 配置程序说明 | 未标注 | V203、V20x、V317（3份逐字节相同）`.../EXAM/ETH/1_Tool_Doc/WCHNET WEB配置说明.PDF` | 3 | 成功，无相关内容 |
| `bb149c4ad066fdf2` | WCHNET IAP 升级方案使用教程 | 未标注 | V203、V20x、V317（3份逐字节相同）`.../EXAM/ETH/1_Tool_Doc/WCHNET IAP升级方案使用教程.PDF` | 4 | 成功，无相关内容 |
| `dbfc5c115ea72be2` | 以太网例程使用注意事项 | 版本：1.0 | 仅 V317 `.../EXAM/ETH/以太网例程使用注意事项.pdf` | 6 | 成功 |

### 1.4 蓝牙 / MESH

| sha16 | 真实文档名 | 版本 | 出现的树/路径 | 页数 | 抽取 |
|---|---|---|---|---|---|
| `14b38c55cd737852` | 沁恒低功耗蓝牙软件开发参考手册（V203/V20x 版） | V1.9（2025/7/17） | V203、V20x（2份逐字节相同）`.../EXAM/BLE/沁恒低功耗蓝牙软件开发参考手册.PDF` | 70 | 成功 |
| `197ec7ccbc510aae` | 沁恒低功耗蓝牙软件开发参考手册（CH587 版） | V1.9（2025/7/17） | 仅 CH587 | 70 | 成功，与上条版本号相同但内容 hash 不同（不同芯片家族分别定制） |
| `c7584f7adf38d33f` | 沁恒低功耗蓝牙 MESH 软件开发参考手册（CH587 版） | V1.1（2022/7/14） | 仅 CH587 `.../EXAM/BLE/MESH/沁恒低功耗蓝牙MESH软件开发参考手册.pdf` | 40 | 成功 |
| `ea4e426ded77b290` | 沁恒低功耗蓝牙 MESH 软件开发参考手册（V203/V20x 版） | V1.1（2022/7/14） | V203、V20x（2份逐字节相同） | 42 | 成功 |
| `a9beeac42aea281f` | 沁恒 MESH APP 管理配网应用手册（CH587 版） | V1.1（2022/7/14） | 仅 CH587 `.../EXAM/BLE/MESH/沁恒MESH APP管理配网应用说明.pdf` | 19 | 成功，无寄存器/指令内容 |
| `b5975bbb393e6cb5` | 沁恒 MESH APP 管理配网应用手册（V203/V20x 版） | V1.1（2022/7/14） | V203、V20x（2份逐字节相同） | 19 | 成功，无寄存器/指令内容 |
| `50755cdd3412262d` | 蓝牙芯片的电路及 PCB 设计的重要注意事项（V203/V20x 版） | 1E | V203、V20x（2份逐字节相同）`.../EXAM/BLE/蓝牙芯片的电路及PCB设计的重要注意事项.pdf` | 3 | 成功，硬件设计类，无寄存器表 |
| `fa38487e29d9cf77` | 蓝牙芯片的电路及 PCB 设计的重要注意事项（CH587 版） | 2B | 仅 CH587 `.../PUB/蓝牙芯片的电路及PCB设计的重要注意事项.pdf` | 4 | 成功，无寄存器表 |
| `02489bbaf1cd268b` | WCH CH32V208 蓝牙空中升级（BLE OTA） | v1.2 | V203、V20x（2份逐字节相同）`.../EXAM/BLE/WCH CH32V208 蓝牙空中升级（BLE OTA）.PDF` | 4 | 成功 |
| `f0ec07ed115cba1d` | WCH 蓝牙空中升级（BLE OTA）（CH587 版） | V1.2 | 仅 CH587 `.../EXAM/BLE/WCH蓝牙空中升级（BLE OTA）.PDF` | 4 | 成功 |

### 1.5 IAP / Bootloader 使用说明（均为同一模板，逐芯片定制）

| sha16 | 真实文档名 | 版本 | 出现的树 | 页数 | 抽取 |
|---|---|---|---|---|---|
| `ab08fe3e2195cb74` | CH32V003_IAP 使用说明 | V1.1 | V003 | 2 | 成功，无寄存器内容，仅提及 IAP 装载地址 `0x1FFFF000` |
| `28cedd1734c8047a` | CH32V00X_IAP 使用说明 | V1.1 | V006 | 2 | 成功，无寄存器内容 |
| `cf7ea9f355104b36` | CH32V10x_IAP使用说明 | 未标注 | V103 | 2 | 成功，无寄存器内容 |
| `63f10c5a8d1c0ac2` | CH32V205_IAP 使用说明 | 未标注 | V006、V205（2份逐字节相同） | 3 | 成功，无寄存器内容 |
| `2c928d4b2358043b` | CH32V20x_IAP 使用说明 | V1.1 | V203、V20x（2份逐字节相同） | 3 | 成功，无寄存器内容 |
| `a61909e8b9d937e2` | CH32V30x_IAP 使用说明 | V1.1 | V317 | 3 | 成功，无寄存器内容 |
| `094d0abdcf4b7a43` | CH32V4x7_IAP 使用说明 | V1.1 | V407 | 5 | 成功，无寄存器内容 |
| `8a10df8fc6f78255` | CH32X3x5_IAP 使用说明 | V1.0 | X315 | 5 | 成功，无寄存器内容 |
| `12d5ea086020bc01` | CH32H417_IAP 使用说明 | V1.2 | H417 | 5 | 成功，无寄存器内容 |
| `d0f94305e9e3fba2` | BOOT 区域作为用户区使用说明（V003 树版，示例含 CH641） | V1.3 | V003 | 4 | 成功，含 Flash 地址 `0x1FFF0000`，大小 3328 字节 |
| `ff1657e67e091473` | BOOT 区域作为用户区使用说明（V006 树版，示例仅 CH32V006） | V1.1 | V006 | 4 | 成功，内容与上条同主题但版本号不同（**同名文档跨树版本号不同，非同一内容组，未合并**）|

### 1.6 评估板参考手册（Evaluation Board Reference / 评估板说明书，各芯片家族一份，内容高度模板化）

| sha16 | 真实文档名 | 版本 | 出现的树 | 页数 | 抽取 |
|---|---|---|---|---|---|
| `c565840f62a98b79` | CH32V00x Evaluation Board Reference-EN | V1.3 | V003 | 10 | 成功，无寄存器/ISA内容（"指令集"=IDE反汇编单步调试功能名，非核心ISA文档） |
| `f348f5aa73057fbe` | CH32V00X Evaluation Board Reference（英文内容，文件名无"-EN"后缀） | V1.1 | V006 | 10 | 成功，同上 |
| `9929232c12a338f7` | CH32V00x评估板说明书 | V1.3 | V003 | 8 | 成功，中文版对应上两条 |
| `ad3b1f8c8f3d1e31` | CH32V00X评估板说明书 | V1.1 | V006 | 8 | 成功 |
| `dfed1b54b3e458f3` | CH32V103 Evaluation Board Reference-EN | V1.6 | V103 | 12 | 成功 |
| `7de7955ca3468ef1` | CH32V103评估板说明书 | V1.6 | V103 | 11 | 成功 |
| `30f9c20ea56a2051` | CH32V205 Evaluation Board Reference-EN | V1.1 | V006、V205（2份逐字节相同） | 9 | 成功 |
| `6a00add95cdeae61` | CH32V205评估板说明书 | V1.1 | V006、V205（2份逐字节相同） | 7 | 成功 |
| `3452f99482c656a4` | CH32V20x Evaluation Board Reference-EN | V1.5 | V203、V20x（2份逐字节相同） | 19 | 成功 |
| `889c4b22776f9760` | CH32V20x评估板说明书 | V1.5 | V203、V20x（2份逐字节相同） | 18 | 成功 |
| `9808e0981caaebe0` | CH32V30x Evaluation Board Reference-EN | V1.9 | V317 | 21 | 成功 |
| `d094012331a4f960` | CH32V30x评估板说明书 | V1.9 | V317 | 19 | 成功 |
| `3030dd04bac675b5` | CH32V4x7 Evaluation Board Reference-EN | V1.1 | V407 | 11 | 成功 |
| `e083020931f004cf` | CH32V4x7评估板说明书 | V1.1 | V407 | 9 | 成功 |
| `64115f9ea04b5f5c` | CH32X3x5 Evaluation Board Reference-EN | V1.0 | X315 | 11 | 成功 |
| `bb45de97592f9a55` | CH32X3x5评估板说明书 | V1.0 | X315 | 9 | 成功 |
| `78dc8d46f5e4da89` | CH32H417 Evaluation Board Reference-EN | V1.4 | H417 | 15 | 成功 |
| `14ea6def0bf92882` | CH32H417评估板说明书 | V1.4 | H417 | 12 | 成功 |
| `82c60716f886b595` | CH587 Evaluation Board Reference（英文内容，文件名无"-EN"后缀） | Version: 1 | CH587 | 13 | 成功 |
| `e524224396a0c9fc` | CH587评估板说明书 | 版本：1 | CH587 | 10 | 成功 |

以上 20 份 Evaluation Board Reference / 评估板说明书**内容高度模板化**：均为 MounRiver IDE 使用教程（工程建立、编译、下载、调试），其"指令集单步模式"/"Instruction set single-step mode"一节讲的是 **IDE 调试器的反汇编单步查看功能**，不是 CPU 指令集架构文档；未发现寄存器地址/位域/器件标识内容。

### 1.7 触摸

| sha16 | 真实文档名 | 版本 | 出现的树 | 页数 | 抽取 |
|---|---|---|---|---|---|
| `9c0f28254428f039` | WCH 触摸应用指南 | 未标注（全文未见版本号） | V006 `.../EXAM/TOUCHKEY/DOC_SCH_PCB/WCH触摸应用指南.pdf` | 11 | 成功，设计方法论文档，无寄存器 |
| `1d55728072da8f86` | WCH_touch_lite 库使用说明 | 未标注（仅"查询当前库版本"函数说明，非文档版本） | V006 `.../WCH_touchkey_lite库使用说明.pdf` | 10 | 成功 |
| `bf50109705ef8acb` | WCH_touch_V3 库使用说明 | V1.1（页脚标注，标题页未单独列版本行） | CH587 `.../EXAM/TOUCH/WCH_touch_V3库使用说明.pdf` | 18 | 成功 |
| `9693ef4c83762e3e` | CH32V00x_Touch_Kit（原理图） | 未标注 | V006 | 1 | 抽取以网表/网络标签为主；未见寄存器/指令正文，图形关系需看原 PDF |
| `6544e5b72df170db` | WCH_TOUCH_Kit_EX001（原理图） | 未标注 | V006 | 1 | 同上 |
| `2c860b1092ea0cd3` | WCH_TOUCH_Kit_EX002（原理图） | 未标注 | V006 | 1 | 同上 |

### 1.8 电机（BLDC/FOC 硬件说明，非 RISC-V 核心相关）

| sha16 | 真实文档名 | 版本 | 出现的树 | 页数 | 抽取 |
|---|---|---|---|---|---|
| `1fbfd86bb4ae445b` | CH32M007单电机BLDC评估板硬件说明 | V1.0 | V006 | 5 | 成功，硬件电路说明，无寄存器表 |
| `7b7878d7b889e753` | CH32M007双电机FOC评估板硬件说明 | V1.0 | V006 | 6 | 成功，同上 |
| `951e89a317fd38ee` | LV_hairDrier（原理图） | 未标注 | V006 | 1 | 未见寄存器/指令正文；网络与连线信息需看原 PDF |
| `dfa7c38bcb252af7` | PMSM_M007R_Fan（原理图） | 未标注 | V006 | 1 | 同上 |
| `f75b4d5cd0f31209` | PMSM_M007U_Fan（原理图） | 未标注 | V006 | 1 | 同上 |

### 1.9 USB PD Demo / USBSS

| sha16 | 真实文档名 | 版本 | 出现的树 | 页数 | 抽取 |
|---|---|---|---|---|---|
| `09fc67561c146ad6` | CH233 Demo Board Reference-EN | V1.1 | V203、V20x（2份逐字节相同） | 3 | 成功，无寄存器内容（另一颗 USB PD 芯片的演示板说明，非本仓库核心 MCU） |
| `47421352c2eb61da` | CH223 Demo板使用说明 | V1.1 | V203、V20x（2份逐字节相同） | 3 | 成功，无相关内容 |
| `6cb3dc7df54e15cd` | CH32H417 USB3.0模拟CH372测试说明 | V1.1（2025/09/15） | H417 | 6 | 成功，测速/校验为应用层数据比对，非硬件寄存器 |

### 1.10 原理图 / PCB 版图（pin/mux 文本可用，寄存器阴性结论受限）

| sha16 | 文件名 | 出现的树 | 页数 | 说明 |
|---|---|---|---|---|
| `17689742601852f0` | CH32V205SCH.pdf | V006、V205 | 4 | 可抽 pin/mux 与网络标签；限定寄存器/地址查询 0 命中 |
| `326f627e19cc307b` | CH32V30xSCH.pdf | V317 | 13 | 同上；文本量大，含大量元件/网络标签 |
| `5506439d08953413` | CH32H417SCH.pdf | H417 | 7 | 同上 |
| `7e8e8b99ea7a58aa` | CH32V20xSCH.pdf | V203、V20x | 16 | 同上 |
| `80ddd7b42f3ce04a` | CH32H417QEU-R1.pdf | H417 | 15 | 可抽 `PIOC_IO0/1` 等 pin/mux 标签；限定查询 0 命中 |
| `9e63334179d88222` | CH32V103SCH.pdf | V103 | 4 | 可抽 pin/mux 与网络标签；限定查询 0 命中 |
| `b4eb523bda7884f3` | CH32X3x5SCH.pdf | X315 | 4 | 同上 |
| `b7ee4a2d12170c06` | CH32V00XSCH.pdf | V006 | 11 | 同上 |
| `c05d96a7790f760f` | CH32V00xSCH.pdf | V003 | 1 | 同上 |
| `ec32c5f5576ad51e` | CH587SCH.pdf | CH587 | 1 | 可抽 PA/PB 复用标签；限定查询 0 命中 |
| `fe2cf67a94ff4dcd` | CH32V4x7SCH.pdf | V407 | 8 | 可抽 `PA4/ADC4/DAC0`、`PA13/SWDIO` 等标签；限定查询 0 命中 |

精确选择规则为“文件名以 `SCH.pdf` 结尾，或位于 `SCHPCB/` 目录下”，共得 **13 个物理文件、11 个 SHA-256 内容组**。全部页面经 `pdftotext -layout` 后，每组可识别 18–125 个不同 pin/mux token；CH587、V407、H417QEU 三张代表页的视觉抽查也确认这些标签可读。只有限定查询 `CSR|SFR_|register|寄存器|0x...` 为 0 命中；这不证明每页图形中绝无寄存器信息，也未做全页 OCR/人工阴性证明。

**文档清单合计：81 个内容组，109 份物理文件，覆盖 11 棵 EVT 树；81 组全部抽取成功（pdftotext 均返回 0 退出码）。原理图内容组可用于 pin/mux/网络标签核对，但当前限定查询未发现寄存器表；不能把该查询扩大成“原理图无可用文本”或全页阴性结论。**

---

## 2. RISC8B 指令集（核心，逐字转录）

来源：`WCH-RISC8B 内核指令集与汇编工具 v2B (sha256:38231bec89ea50ab)` 第1-10页（中文）／`RISC8B Core MCU Instruction Set and Assembly Tool v2B (sha256:a3b0ac3fa84387ee)` 第1-14页（英文，内容 1:1 对应，已核实见第0节）。

### 2.1 概述

WCH-RISC8B 是 8 位数据宽度的精简指令集单片机内核（RISC8B 基于 RISC8A 新增了一些位传送指令）。所有指令宽度均为 16 位，指令由操作码和操作数组成。RISC8B 共 66 条指令，按操作对象分五类：控制类(18)、面向字节操作类(16)、常数操作类(16)、面向位操作类(9)、转移类(7)。指令周期由系统时钟 SCLK 决定，单周期为主，跳转/查表/程序空间读写等为双周期或多周期（个别特殊工艺芯片"目前仅 CH537X"可能超过两周期）。（第1、5页）

### 2.2 操作数符号约定（第1页 / 2.2节原文）

| 符号 | 含义 |
|---|---|
| `f` | SFR 或 RAM 寄存器，有效值 0x00-0xFF |
| `F` | 扩展地址 SFR 或 RAM 寄存器，有效值 0x000-0x1FF |
| `A` | 工作寄存器；`C` 进位标志；`Z` 零标志 |
| `d` | 目的寄存器，有效值 0、1、A、F、空；d=0 或 A 时结果入 A，d=1 或 F 或空时结果入 f |
| `b` | 位选择，有效值 0-7 |
| `a` | 独立位选择，有效值 0-3，0 对应 C，1-3 对应自定义独立位 |
| `k2` | 2位常数，0-3 |
| `k`/`k8` | 8位常数，0x00-0xFF |
| `K7` | 7位常数，0x00-0x7F |
| `k9` | 9位常数，0x000-0x1FF |
| `k10` | 10位常数，0x000-0x3FF |
| `k12` | 12位常数，0x000-0xFFF |
| `TOS` | Top Of Stack，当前堆栈单元 |
| `1#ff`、`2#ff` | 自定义的 1#、2# 快速 SFR 寄存器 |
| `1#bf`、`2#bf` | 自定义的 1#、2# 位操作 SFR 寄存器 |
| `{*,*}` | 集合；`f[b]` 表示 f 的 b 位；`[@a]` 表示地址 a 指向的寄存器；`(k)` 表示执行时带参数 k |

底纹标灰的指令为 RISC8B 新增或重新定义，RISC8A 内核可能不支持。

### 2.3 完整指令表（66条，第1-4页）

**控制类（18条，第1-2页）**

| 二进制指令码 | HEX | 说明 | 助记符 | 操作数 | 执行操作 | 影响状态 |
|---|---|---|---|---|---|---|
| 00000000 000000xx | 0000 | 空操作 | NOP | 无 | 无 | 无 |
| 00000000 000010xx | 0008 | 清除看门狗计时器 | CLRWDT | 无 | 0→WatchDogTimer | 无 |
| 00000000 00001100 | 000C | 睡眠 | SLEEP | 无 | clock stop | 无 |
| 00000000 000011kk | 000C | 进入指定睡眠模式 | SLEEPX | k2 | k2→SleepMode, clock stop(k2) | 无 |
| 00000000 00010bbb | 0010 | 等待 b 选择的位为1 | WAITB | b | wait bit[b]==1 | 无 |
| 00000000 00010000 | 0010 | 等待从并口读出 | WAITRD | 无 | wait SB_IF_READ==1 | 无 |
| 00000000 00010100 | 0014 | 等待从并口写入/等待SPI中断 | WAITWR/WAITSPI | 无 | wait SB_IF_WRITE==1 / wait SB_IF_SPI==1 | 无 |
| 00000000 00011000 | 0018 | 从程序空间读取代码 | RDCODE | 无 | ROM_CODE→{SFR,A} | 无 |
| 00000000 000110kk | 0018 | 从程序空间读取代码(带参数) | RCODE | k2 | ROM_CODE(k2)→{SFR,A} | 无 |
| 00000000 00011100 | 001C | 将代码写入程序空间 | WRCODE | 无 | {SFR}→ROM_CODE | 短时暂停 |
| 00000000 000111kk | 001C | 带参数的自定义操作 | EXEC | k2 | custom operation(k2) | 自定义 |
| 00000000 001000xx | 0020 | 保存状态到堆栈 | PUSHAS | 无 | {A,Z,C,..}→TOS | 无 |
| 00000000 001001xx | 0024 | 从堆栈恢复状态 | POPAS | 无 | TOS→{A,Z,C,..} | Z,C |
| 00000000 001010xx | 0028 | 保存间接寻址寄存器2和页面位到堆栈 | PUSHA2 | 无 | {SFR_INDIR_ADDR2,INDIR_RAM_PAGE}→TOS | 无 |
| 00000000 001011xx | 002C | 从堆栈恢复间接寻址寄存器2和页面位 | POPA2 | 无 | TOS→{INDIR_RAM_PAGE,INDIR_RAM_SFR_INDIR_ADDR2} | 无 |
| 00000000 001100xx | 0030 | 子程序返回 | RET | 无 | TOS→PC | 无 |
| 00000000 001101xx | 0034 | 子程序置零状态返回 | RETZ | 无 | TOS→PC,1→Z | Z |
| 00000000 001110xx | 0038 | 中断返回 | RETIE | 无 | TOS→PC,1→IE_global | 无 |

**面向字节操作类（16条，第2-3页）**

| 二进制指令码 | HEX | 说明 | 助记符 | 操作数 | 执行操作 | 影响状态 |
|---|---|---|---|---|---|---|
| 00000000 000001xx | 0004 | A 清零 | CLRA | 无 | 0x00→A,1→Z | Z |
| 00000001 ffffffff | 01ff | f 清零 | CLR | f | 0x00→f,1→Z | Z |
| 0001000F FFFFFFFF | 10FF | A 传送到 F（位9指定扩展地址页面位） | MOVA | F | A→F | 无 |
| 000d001F FFFFFFFF | d2FF | 传送 F 到 d（位9指定扩展地址页面位） | MOV | F,d | F→d | Z |
| 000d0100 ffffffff | d4ff | f 递增 | INC | f,d | f+1→d | Z |
| 000d0101 ffffffff | d5ff | f 递减 | DEC | f,d | f-1→d | Z |
| 000d0110 ffffffff | d6ff | f 递增，为零则跳 | INCSZ | f,d | f+1→d, skip if Z==1 | 无 |
| 000d0111 ffffffff | d7ff | f 递减，为零则跳 | DECSZ | f,d | f-1→d, skip if Z==1 | 无 |
| 000d1000 ffffffff | d8ff | f 高低半字节交换 | SWAP | f,d | f[0:3]<>f[4:7]→d | 无 |
| 000d1001 ffffffff | d9ff | A 和 f 做与运算 | AND | f,d | A&f→d | Z |
| 000d1010 ffffffff | dAff | A 和 f 做或运算 | IOR | f,d | A\|f→d | Z |
| 000d1011 ffffffff | dBff | A 和 f 做异或运算 | XOR | f,d | A^f→d | Z |
| 000d1100 ffffffff | dCff | A 加 f | ADD | f,d | A+f→d | Z,C |
| 000d1101 ffffffff | dDff | f 减去 A | SUB | f,d | f-A→d | Z,C |
| 000d1110 ffffffff | dEff | f 带 C 循环左移 | RCL | f,d | {f,C}<<1→d,f[7]→C | C |
| 000d1111 ffffffff | dFff | f 带 C 循环右移 | RCR | f,d | {C,f}>>1→d,f[0]→C | C |

**常数类（16条，第3页）**

| 二进制指令码 | HEX | 说明 | 助记符 | 操作数 | 执行操作 | 影响状态 |
|---|---|---|---|---|---|---|
| 00100000 kkkkkkkk | 20kk | 子程序带参数返回 | RETL | k | k→A,TOS→PC | 无 |
| 00100001 kkkkkkkk | 21kk | 子程序带参数且置非零状态返回 | RETLN | k | k→A,0→Z,TOS→PC | Z |
| 0010001k kkkkkkkk | 22kk | 常数置入间接地址寄存器1和专用页面位 | MOVIP | k9 | k9→{INDIR_RAM_PAGE,INDIR_RAM_SFR_INDIR_ADDR} | 无 |
| 001001kk kkkkkkkk | 24kk | 常数置入间接寻址寄存器2 | MOVIA | k10 | k10→SFR_INDIR_ADDR2 | 无 |
| 00100011 kkkkkkkk | 23kk | 常数置入1#快速寄存器 | MOVA1F | k | k→1#ff | 无 |
| 00100101 kkkkkkkk | 25kk | 常数置入2#快速寄存器 | MOVA2F | k | k→2#ff | 无 |
| 00100110 kkkkkkkk | 26kk | 常数置入间接地址寄存器2指向的寄存器 | MOVA2P | k | k→[@SFR_INDIR_ADDR2] | 无 |
| 00100111 kkkkkkkk | 27kk | 常数置入间接地址寄存器1指向的寄存器 | MOVA1P | k | k→[@SFR_INDIR_ADDR] | 无 |
| 00101000 kkkkkkkk | 28kk | 常数置入 A | MOVL | k | k→A | 无 |
| 00101001 kkkkkkkk | 29kk | 常数和 A 做与运算 | ANDL | k | k&A→A | Z |
| 00101010 kkkkkkkk | 2Akk | 常数和 A 做或运算 | IORL | k | k\|A→A | Z |
| 00101011 kkkkkkkk | 2Bkk | 常数和 A 做异或运算 | XORL | k | k^A→A | Z |
| 00101100 kkkkkkkk | 2Ckk | 常数加 A | ADDL | k | k+A→A | Z,C |
| 00101101 kkkkkkkk | 2Dkk | 常数减去 A | SUBL | k | k-A→A | Z,C |
| 00101110 kkkkkkkk | 2Ekk | 常数加 A 做比较 | CMPLN | k | k+A | Z,C |
| 00101111 kkkkkkkk | 2Fkk | 常数减去 A 做比较 | CMPL | k | k-A | Z,C |

**面向位操作类（9条，第4页）**

| 二进制指令码 | HEX | 说明 | 助记符 | 操作数 | 执行操作 | 影响状态 |
|---|---|---|---|---|---|---|
| 01000bbb ffffffff | 40ff | 清除 f 的位 b | BC | f,b | 0→f[b] | 无 |
| 01001bbb ffffffff | 48ff | 设置 f 的位 b | BS | f,b | 1→f[b] | 无 |
| 01010bbb ffffffff | 50ff | f 的位 b 为0则跳 | BTSC | f,b | skip if f[b]==0 | 无 |
| 01011bbb ffffffff | 58ff | f 的位 b 为1则跳 | BTSS | f,b | skip if f[b]==1 | 无 |
| 00000000 000111aa | 001C | 传送 a 选择的位到 C | BCTC | a | bit[a]→C | C |
| 00000000 100aabbb | 008b | 传送1#位寄存器的位b到a选择的位 | BP1F | a,b | 1#bf[b]→bit[a] | C if a==0 |
| 00000000 101aabbb | 00Ab | 传送2#位寄存器的位b到a选择的位 | BP2F | a,b | 2#bf[b]→bit[a] | C if a==0 |
| 00000000 110aabbb | 00Cb | 传送a选择的位到1#位寄存器的位b | BG1F | a,b | bit[a]→1#bf[b] | 无 |
| 00000000 111aabbb | 00Eb | 传送a选择的位到2#位寄存器的位b | BG2F | a,b | bit[a]→2#bf[b] | 无 |

**转移类（7条，第4页）**

| 二进制指令码 | HEX | 说明 | 助记符 | 操作数 | 执行操作 | 影响状态 |
|---|---|---|---|---|---|---|
| 0110kkkk kkkkkkkk | 6kkk | 跳转 | JMP | k12 | k12→PC | 无 |
| 0111kkkk kkkkkkkk | 7kkk | 调用子程序 | CALL | k12 | PC+1→TOS,k12→PC | 无 |
| 001100kk kkkkkkkk | 3kkk | Z=0则跳转 | JNZ | k10 | k10→PC[9:0] if Z==0 | 无 |
| 001101kk kkkkkkkk | 3kkk | Z=1则跳转 | JZ | k10 | k10→PC[9:0] if Z==1 | 无 |
| 001110kk kkkkkkkk | 3kkk | C=0则跳转 | JNC | k10 | k10→PC[9:0] if C==0 | 无 |
| 001111kk kkkkkkkk | 3kkk | C=1则跳转 | JC | k10 | k10→PC[9:0] if C==1 | 无 |
| 1KKKKKKK kkkkkkkk | 8Kkk | 常数与A做比较，相等则跳转 | CMPZ | K7,k | k→PC[7:0] if A==K7 | 无 |

（合计 18+16+16+9+7 = 66 条，与文档第1页声明的"共66条"一致）

### 2.4 指令周期（第5页）

单周期为主。双周期/多周期：`JMP、CALL`（总是多周期）；`RET/RETZ/RETIE/RETL/RETLN`（总是多周期）；`JNZ/JZ/JNC/JC`、`CMPZ`（跳转成立时多周期，否则单周期）；`BTSC/BTSS`（跳转成立时双周期，否则单周期）；所有字节操作类指令中目标寄存器为 `SFR_PRG_COUNT` 的指令为多周期（如 `ADD SFR_PRG_COUNT,A` 是读操作例外，仍为单周期）。特殊多周期：`RDCODE` 通常3周期；`WRCODE` 最少4周期，最多数百毫秒；`EXEC` 自定义。

### 2.5 等效指令助记符与重新定义指令码（第5-6页）

等效别名（WASM53B 汇编器支持）：`CLRWDT`=`WDT`、`SLEEP`=`HALT`、`WAITSPI`=`WAITWR`、`PUSHAS`=`PUSH`、`POPAS`=`POP`、`RET`=`RETURN`、`RETZ`=`RETOK`、`RETIE`=`RETI`、`RETL`=`DB`、`RETLN`=`RETER`、`JMP`=`GOTO`；字节操作类指令（除 CLRA/INCSZ/DECSZ）原助记符后加 F 得等效名（如 `INC`→`INCF`）；位操作类指令（除 BTSC/BTSS）同理（如 `BC`→`BCF`）；`INCSZ`=`INCFSZ`、`DECSZ`=`DECFSZ`、`RCL`=`RCLF`/`RLF`、`RCR`=`RCRF`/`RRF`、`BTSC`=`BTFSC`、`BTSS`=`BTFSS`；`DW` 用于定义双字节数据（新指令，操作数为新指令码）。

重新定义指令码（不同芯片/应用中复用）：`SLEEP`(00001100)↔`SLEEPX k2`(000011kk)；`WAITRD`(00010000)↔`WAITB b`(00010bbb)；`WAITSPI`(00010100)↔`WAITB b`(00010bbb)；`RDCODE`(00011000)↔`RCODE k2`(000110kk)；`WRCODE`(00011100)↔`EXEC k2`(000111kk) 或 `BCTC a`(000111aa)；`MOVIP k9`(0010001k)↔`MOVIP k8`(00100010) 或 `MOVA1F k`(00100011)；`MOVIA k10`(001001kk)↔`MOVIA k8`(00100100)／`MOVA2F k`(00100101)／`MOVA2P k`(00100110)／`MOVA1P k`(00100111)。

### 2.6 寻址方式（第6-7页）

六种：立即数寻址、立即数快速寻址、普通直接寻址（0x000-0x0FF，8位地址）、扩展直接寻址（0x000-0x1FF，9位地址，仅限 `MOV register,A/F` 与 `MOVA register`）、间接寻址（0x000-0x3FF，覆盖全部寄存器，两组间接寻址寄存器 `SFR_INDIR_ADDR`/`SFR_INDIR_PORT` 与 `SFR_INDIR_ADDR2`/`SFR_INDIR_PORT2`）、位寻址（3位位地址+普通或间接寻址）。示例与语义见原文 5.1-5.6 节（第6-7页）。

### 2.7 汇编工具 WASM53B（第7-10页）

`WASM53B.EXE`：命令行 `WASM53B 源程序文件名`，源文件默认扩展名 `.ASM`；两遍扫描；产出同名 `.LST`（列表：源码+目标码+标号+常量+错误/警告计数）与 `.BIN`（目标数据，每指令2字节，小端；程序空间 4096 条指令，故 `.BIN` 恒 ≤8KB）。字符集：标号不超过20字符，数字/字母/`_`/`$`/`#`/`@`；保留字 `END`、`ORG`、`INCLUDE` 不可作标号。数值进制：二进制`0B`/`B'..'`、十六进制`0X`/`H'..'`、十进制直接或`0D`/`D'..'`、字符`'..'`。表达式支持 `+ - * / % & | ^ ~ << >>`，从右向左结合，`~`/`<<`/`>>` 结果限制在 0-255。语句格式 `LABEL INSTRUCTION PARAM1,PARAM2 ;REMARK`；单行≤249字符，单文件≤9999行。伪指令：`EQU`(标号赋值)、`ORG`(起始地址，默认0x0000，向前定义触发"go back by ORG"警告)、`INCLUDE`(最多8级嵌套)、`END`(源程序结束，未出现则警告"END not found")。第7节"指令详细说明"两版原文均为空（中文"暂无"／英文"(Not yet)"，第9页），**不是抽取失败，是文档本身未撰写该节**。

### 2.8 常见问题（第10页）

1）单字节查表短跳转页面 256 字节，用 `ADD SFR_PRG_COUNT`+`RETL` 查表时不可跨 `0xXXFF`；2）双字节查表用 `RDCODE`+`DW`，需注意跨页；3）长表达式建议人工核对 `.LST`；4）程序长跳转页面 4K，跨页调用需手工设置页面（V006 无额外跳转延时，见1.5节 BOOT 文档的类似表述）；5）可提供子程序库范例（32位加减、单/双字节查表、串口/SPI、24CXX/25FXX读写、USB/CH341兼容框架）；6）OTP 工艺 ROM 只能烧录一次（0→1，1保持1），建议关键模块前预留 NOP 便于后续替换为跳转指令。

---

## 3. PIOC 协处理器

来源：`可编程协议 I/O 微控制器 PIOC 手册 v版本1 (sha256:61e543eb2dcdf538)` 第1-9页（中文）／`PIOC User Manual v"Version: V1" (sha256:d8b62cd7359d53c1)` 第1-12页（英文，即文件名`PIOC-EN.pdf`，内容与中文版逐节对应，见第0节核查结论）。

### 3.1 定位与关系（第1页）

部分 WCH 芯片内嵌一个可编程协议 I/O 微控制器 PIOC，即 **eMCU**：基于单时钟周期的精简指令集 **RISC8B** 内核，**运行于系统主频**（与主 CPU 同频，非独立时钟域），具有 **2K 指令的程序 ROM** 及 **49 个 SFR 寄存器**，另有 PWM 定时/计数器，支持 2 个 I/O 引脚的协议控制。指令集本身即第2节 RISC8B（"更多介绍请参考 CHRISC8B.PDF"，第2页 3.1节原文引用）。

### 3.2 代码装载机制（第2页，3.2节）

eMCU 程序 ROM **复用 4K 字节系统 SRAM**：`RB_MST_CLK_GATE`=0 时该 4K SRAM 归主机侧使用（可供主机为 eMCU 动态加载新程序）；`RB_MST_CLK_GATE`=1 时归 eMCU 侧使用，作为 2048 字（0x0000-0x07FF）程序 ROM。0 地址指令具特殊用途、不会被执行。eMCU 支持对程序空间**只读**（先写目标地址低8位到 `SFR_INDIR_ADDR`、高3位到 A，执行 `RDCODE` 一次读出16位数据，用于双字节查表），**不支持写**。控制该复用切换的位是系统配置寄存器 `SFR_SYS_CFG` 的 `SB_MST_CLK_GATE`（位0，第7-8页，见3.5节）。

### 3.3 堆栈与睡眠/唤醒（第2页，3.3-3.4节）

6级深度堆栈，数据宽度11位，用于子程序返回地址及 `PUSHAS`/`POPAS` 保存变量状态。`RB_MST_CLK_GATE`=0 时程序暂停；执行 `SLEEP`/`SLEEPX` 进入睡眠（全静态设计，暂停与睡眠等效）。两种唤醒方式：电平变化检测唤醒、`SB_MST_CLK_GATE` 从0到1唤醒。

### 3.4 事件等待与位传送指令的硬件绑定（第2-3页，3.5-3.6节）

`WAITB` 支持8种事件：`WB_DATA_SW_MR_0`(等 `SB_DATA_SW_MR`=0)、`WB_BIT_CYC_TAIL_1`(等 `SB_BIT_CYC_TAIL`=1)、`WB_PORT_I0_FALL`/`WB_PORT_I0_RISE`(等 `SB_PORT_IN0` 下降/上升沿)、`WB_DATA_MW_SR_1`(等 `SB_DATA_MW_SR`=1)、`WB_PORT_XOR1_1`、`WB_PORT_XOR0_0`、`WB_PORT_XOR0_1`。位传送指令 `BP1F`/`BG1F` 对应 `SFR_INDIR_ADDR`，`BP2F`/`BG2F` 对应 `SFR_DATA_EXCH`；4个独立位：0#=`SB_FLAG_C`，1#=`SB_BIT_TX_O0`/`SB_BIT_RX_I0`，2#=`SB_PORT_OUT0`/`SB_PORT_IN0`，3#=`SB_PORT_OUT1`/`SB_PORT_IN1`；`BCTC` 的0#参数为 `SB_FLAG_C` 与 `SB_PORT_IN0` 异或结果。

### 3.5 与主核的接口（共享内存 + 握手位，第2、7-8页）

eMCU 数据空间 = 49 个 SFR，8位地址寻址（0x00-0x3F），全部1字节宽。**主机侧对部分 SFR 可读写或只读，支持8/16/32位宽访问；主机侧写优先——eMCU 与主机同时写同一寄存器时，eMCU 写操作被自动丢弃**（第3页）。握手机制（`SFR_SYS_CFG` 第0-7位，见3.6表）：`SB_INT_REQ`（eMCU 向主机请求中断，主机通过假写 `SFR_CTRL_RD` 清0）；`SB_DATA_SW_MR`（eMCU 写 `SFR_CTRL_RD` 后自动置1，主机读后自动清0）；`SB_DATA_MW_SR`（主机写 `SFR_CTRL_WR` 后自动置1，eMCU 读后自动清0）；`SB_MST_IO_EN1`/`SB_MST_IO_EN0`（IO1/IO0 引脚归主机或 eMCU 控制）；`SB_MST_RESET`（主机强制单独复位 eMCU）；`SB_MST_CLK_GATE`（eMCU 全局时钟开关，即代码装载复用切换位）。

### 3.6 SFR 全表（49个地址空间，21个已用地址，第3-4页原文表格）

| 地址 | SFR 名称 | 说明 | 主机侧读写 | 复位默认值 |
|---|---|---|---|---|
| 00H | SFR_INDIR_PORT | 间接寻址的数据读写端口 | UUUUUUUU | XXXXXXXX |
| 01H | SFR_INDIR_PORT2 | 间接寻址2的数据读写端口 | UUUUUUUU | XXXXXXXX |
| 02H | SFR_PRG_COUNT | 程序计数器PC的低字节 | UUUUUUUU | 00000000 |
| 03H | SFR_STATUS_REG | 状态寄存器 | UUUUSUSU | 0000-0-0 |
| 04H | SFR_INDIR_ADDR | 间接寻址的地址寄存器 | RRRRRRRR | XXXXXXXX |
| 05H | SFR_TMR0_COUNT | 定时器0的计数寄存器 | RRSSRRRR | 00000000 |
| 06H | SFR_TIMER_CTRL | 定时器的控制寄存器 | RRRRRRRR | 00000000 |
| 07H | SFR_TMR0_INIT | 定时器0的初值寄存器 | RRRRRRRR | 00000000 |
| 08H | SFR_BIT_CYCLE | 编码位周期寄存器 | WWWWWWWW | 00000000 |
| 09H | SFR_INDIR_ADDR2 | 间接寻址2的地址寄存器 | RRRRRRRR | 00000000 |
| 0AH | SFR_PORT_DIR | 端口方向设置寄存器 | RRRRRRRR | 00000000 |
| 0BH | SFR_PORT_IO | 端口输入输出寄存器 | RRRRRRRR | XXXXXX00 |
| 0CH | SFR_BIT_CONFIG | 编码位配置寄存器 | WWWRRRRR | 00010000 |
| 1CH | SFR_SYS_CFG | 系统配置寄存器 | RRRWWWWW | 00000000 |
| 1DH | SFR_CTRL_RD | eMCU读写且主机只读寄存器 | RRRRRRRR | 00000000 |
| 1EH | SFR_CTRL_WR | 主机读写且eMCU只读寄存器 | WWWWWWWW | 00000000 |
| 1FH | SFR_DATA_EXCH | 数据交换寄存器 | WWWWWWWW | 00000000 |
| 20H-3FH | SFR_DATA_REG0…REG31（32个） | 数据寄存器0-31 | WWWWWWWW | 00000000 |

字母含义：复位值 `0`=总是0，`1`=总是1，`X`=不确定，`-`=仅上电复位清0（系统/主机复位不影响）；读写属性 `W`=可读写，`R`=只读，`U`=不可读写（不可见），`S`=只读交换位（主机侧看到的 `SFR_TIMER_CTRL` 与 eMCU 侧不同：`SB_TMR0_ENABLE`/`SB_TMR0_OUT_EN` 分别被 `SB_GP_BIT_Y`/`SB_GP_BIT_X` 替代）。

### 3.7 关键寄存器位域详解（第4-9页）

- **`SFR_STATUS_REG`**（第4-5页）：位7-6保留=0；位5 `SB_STACK_USED`(堆栈使用标志)；位4 `SB_EN_TOUT_RST`(定时器超时复位使能)；位3 `SB_GP_BIT_Y`(通用位变量，上电清0，系统/主机复位不影响)；位2 `SB_FLAG_Z`(ALU零标志)；位1 `SB_GP_BIT_X`(通用位变量，同Y)；位0 `SB_FLAG_C`(ALU进位标志)。
- **`SFR_PORT_DIR`**（第5页）：位7-4 `SB_PORT_MOD3..0`(引脚模式，主机侧定义)；位3 `SB_PORT_PU1`(IO1上拉使能)；位2 `SB_PORT_PU0`(IO0上拉使能)；位1 `SB_PORT_DIR1`；位0 `SB_PORT_DIR0`(方向，0输入1输出)。
- **`SFR_PORT_IO`**（第5-6页）：位7 `SB_PORT_IN_XOR`；位6 `SB_BIT_RX_I0`(位解码接收数据)；位5 `SB_PORT_IN1`；位4 `SB_PORT_IN0`；位3 `SB_PORT_XOR1`；位2 `SB_PORT_XOR0`(电平变化检测)；位1 `SB_PORT_OUT1`；位0 `SB_PORT_OUT0`(定时器输出信号优先，`SB_TMR0_OUT_EN`=1时输出`SB_TMR0_CYCLE`或其二分频信号)。
- **`SFR_TIMER_CTRL`**（第6-7页）：位7 `SB_EN_LEVEL1`；位6 `SB_EN_LEVEL0`(电平变化激活中断/唤醒使能)；位5 `SB_TMR0_ENABLE`；位4 `SB_TMR0_OUT_EN`；位3 `SB_TMR0_MODE`(0定时器/1PWM)；位2-0 `SB_TMR0_FREQ`(时钟分频：000=1024X,001=256X,010=64X,011=16X,100=8X,101=4X,110=2X,111=1X)。定时器0为8位自动重载计数器，模式细节（计数溢出、`SB_TMR0_CYCLE` 占空比公式）见第6页正文。
- **`SFR_SYS_CFG`**（第7-8页）：位7 `SB_INT_REQ`；位6 `SB_DATA_SW_MR`；位5 `SB_DATA_MW_SR`；位4 `SB_MST_CFG_B4`(软件自定义)；位3 `SB_MST_IO_EN1`；位2 `SB_MST_IO_EN0`；位1 `SB_MST_RESET`；位0 `SB_MST_CLK_GATE`。全部见3.5节。
- **`SFR_BIT_CYCLE`**（第8页）：位7 `SB_BIT_TX_O0`(双缓冲，待发送编码位原始数据)；位6-0 `SB_BIT_CYCLE`(编码位宽度，时钟数-1；高5位为0关闭编解码)。
- **`SFR_BIT_CONFIG`**（第8页）：位7 `SB_BIT_TX_EN`；位6 `SB_BIT_CODE_MOD`(0=PWM占空比调制25%/75%，1=Manchester调制)；位5 `SB_PORT_IN_EDGE`(采样时点)；位4 `SB_BIT_CYC_TAIL`；位3-0 `SB_BIT_CYC_CNT6..3`(7位周期计数器的位6-3)。eMCU 支持 PWM 占空比调制与 Manchester 调制两种硬件位编解码方式（第8页正文，是 PIOC 面向低速通讯协议的核心硬件加速点）。
- **`SFR_DATA_REG0-31`／`SFR_DATA_EXCH`**：双侧可读可写，主机写优先，软件自定义用途；`SFR_DATA_EXCH` 另支持单周期位传送指令（第9页）。

### 3.8 时序与并行执行约束（第2、9页）

- eMCU 与主机**同主频**，无独立时钟域，二者是紧耦合的协处理关系而非异步核；
- 主机对共享 SFR 有**写优先权**（3.5节），避免总线仲裁但要求应用层自行避让写冲突窗口；
- 程序 ROM 复用同一块 4K SRAM，**装载新代码与 eMCU 运行互斥**（`RB_MST_CLK_GATE` 二选一，不能同时用于两侧）；
- 应用场景（第9页原文）：单周期设置/采集 I/O、单周期位复制、硬件编解码 PWM/Manchester 位数据，"适用于各种中低速通讯协议的 I/O 实现，以及需要精确定时的 I/O 控制"。

### 3.9 PIOC 快速上手指南（与技术手册为不同文档，见第0节）

`PIOC 使用说明 v版本V1.0 (sha256:a1b0149616442cfa` /`2515e76f0c2841b2)` 与 `User Guide for PIOC v"Version: V1.0" (sha256:62b3ed245b6a43b2`，**文件名`PIOC User Manual-EN.pdf`但非技术手册**，见第0节）：以 CH32V205/CH32H417 为例，MounRiver IDE + WCH-Link，5步流程——①打开 `PIOC_1_Wire\Asm\RGB1W.ASM` 编辑；②双击 `RGB1W.BAT` 编译；③复制 `RGB1W_inc.h` 内容；④粘贴替换 `RGB1W.C` 中 `PIOC_1W_CODE` 数组；⑤编译工程并下载。无寄存器信息，纯工具链操作指南。

---

## 4. 按四类分节的索引

### 4.1 指令集/汇编

| 文档 | 页码 | 摘录 | 说明 |
|---|---|---|---|
| WCH-RISC8B内核指令集与汇编工具 v2B (sha256:38231bec89ea50ab) | 第1-10页 | 见第2节完整转录 | RISC8B 66条指令全表、寻址方式、汇编器 WASM53B 用法、伪指令 |
| RISC8B Core MCU Instruction Set... v2B (sha256:a3b0ac3fa84387ee) | 第1-14页 | 同上英文版 | 内容与中文版逐指令对应 |
| 可编程协议I/O微控制器PIOC手册 v版本1 (sha256:61e543eb2dcdf538) | 第2页 | "eMCU 采用精简指令集 RISC8B 内核...共 66 条指令，除了跳转指令是双时钟周期、程序空间读写指令是双周期之外，其余指令都是单时钟周期。更多介绍请参考 RISC8B 内核指令集和汇编工具文档 CHRISC8B.PDF" | PIOC 复用 RISC8B 指令集，文档间显式互相引用 |
| CH32V00x Evaluation Board Reference-EN v1.3 (sha256:c565840f62a98b79) 等20份评估板手册（第1.6节全部列出） | 各文档第4-15页不等 | "Instruction set single-step mode: click to enter instruction set debugging" | **非 ISA 文档**——"指令集"指 IDE 反汇编单步调试功能名，属误报排除项，特此记录避免后续分析误用 |
| CH32M007单电机BLDC评估板硬件说明 v1.0 (sha256:1fbfd86bb4ae445b) | 第3页 | "由3片N+P双MOS管组成逆变电路，用于执行MCU的指令，从而控制电机" | 泛指"MCU执行指令控制电机"，非ISA文档，误报排除 |

### 4.2 加速功能及其寄存器

| 文档 | 页码 | 摘录 | 说明 |
|---|---|---|---|
| PIOC 手册 v版本1 (sha256:61e543eb2dcdf538) | 第8页 | "eMCU 支持两种位调制方式：PWM 占空比调制和 Manchester 曼彻斯特调制...设置 SB_BIT_CYCLE 大于3，则开启编解码" | **硬件位编解码加速**：`SFR_BIT_CYCLE`/`SFR_BIT_CONFIG` 寄存器控制的专用编解码硬件，见第3.7节 |
| WCHNET Protocol Stack Library Application Note v1D (sha256:1e1bf85517182dc3) | 第2页 | "HARDWARE_CHECKSUM_CONFIG [bit26] Hardware checksum checking and insertion configuration, 1: Enabled. 0: Disabled." | **以太网硬件校验和卸载**：`MiscConfig1` 位26，通过 `WCHNET_ConfigLIB` 配置；是库级配置字段而非直接给出寄存器地址（地址级定义应在 wchnet.h /芯片参考手册中，本文档未展开） |
| WCHNET 协议栈库说明 v1D (sha256:09e3fa9f6069321b) | 第2页 | "HARDWARE_CHECKSUM_CONFIG  26  硬件校验和检验和插入配置 1：启用，0：禁用" | 同上中文版 |
| CH32H417 UHSIF Development Reference Manual v1.0 (sha256:a115a26443ee206d) | 第10页 | "UHSIF_Reg_Change...The UHSIF has a total of 76 registers that can be modified; the offset address reg_addr ranges from 0 to 75" | **高速并行接口加速通道**：UHSIF 最高125MHz时钟、理论500MB/s，4条传输线路(Line)×8缓冲区(Buffer)硬件FIFO；提供API级76个寄存器改写接口(`UHSIF_Reg_Change`/`UHSIF_GPIO_Init`/`UHSIF_Line_Cfg`)，但**具体76个寄存器各自的地址/位域未在本文档展开**，文档明示"详细内容请参考 CH32H417DS0.PDF"（该数据手册不在本EVT树范围内，属外部引用缺口，见第5节） |
| CH32H417通用高速接口（UHSIF）开发参考手册 v1.0 (sha256:c4c31b260db2987f) | 第8页 | 同上中文版，"UHSIF 共有 76 个寄存器可被修改...详细的内容请参考 CH32H417DS0.PDF 手册" | 同一处外部引用缺口 |
| 以太网例程使用注意事项 v1.0 (sha256:dbfc5c115ea72be2) | 第4页 | "2、硬件浮点库使用 当工程中开启硬件浮点功能，需要将以太网浮点库添加至工程中" | **FPU 硬件加速**：确认 CH32V317 具备可选硬件浮点单元，链接期需选用浮点版协议栈库；文档仅涉及 IDE 工程配置，无 FPU 寄存器/CSR 地址信息 |
| 沁恒低功耗蓝牙软件开发参考手册 v1.9 (sha256:14b38c55cd737852 / 197ec7ccbc510aae) | 第38-39页 | "rfConfig.CRCInit = 0x555555;"，第67-68页 "CRCInit CRC 初始值" | **2.4GHz 无线物理层硬件CRC**：`rfConfig_t` 结构体的 `CRCInit` 字段配置射频硬件包校验初始值；是软件配置结构体字段，非直接内存映射寄存器地址 |
| WCH_touch_V3库使用说明 v1.1 (sha256:bf50109705ef8acb) / WCH_touchkey_lite库使用说明 (sha256:1d55728072da8f86) | 第7页 | "baseUpRefreshDouble：基线向上更新的倍数参数...该参数范围0～255，设置为0或1时不加速" | 触摸基线刷新的**软件滤波参数**"加速/不加速"，非硬件寄存器；触摸通道本身走 ADC（"channelNum：触摸通道索引，通常也是 ADC 通道编号"），未发现专用触摸硬件加速寄存器 |

### 4.3 特殊功能寄存器（SFR）/自定义 CSR

| 文档 | 页码 | 摘录 | 说明 |
|---|---|---|---|
| PIOC 手册 v版本1 (sha256:61e543eb2dcdf538) | 第3-9页 | 见第3.6-3.7节全表 | RISC8B/PIOC 自定义 SFR 空间（0x00-0x3F，49个地址，21个已用），本索引已完整转录 |
| WCH-RISC8B内核指令集 v2B (sha256:38231bec89ea50ab) | 第6-7页 | "读写间接寻址的数据读写端口 SFR_INDIR_PORT...SFR_INDIR_ADDR 及其页面位 SB_INDIR_RAM_PAGE" | RISC8B 通用内核层面的间接寻址 SFR（`SFR_INDIR_ADDR`/`SFR_INDIR_ADDR2`/`SFR_INDIR_PORT`/`SFR_INDIR_PORT2`），PIOC 是其具体实例化 |
| I2C接口使用指南 v1B (sha256:df41d54ffde33467) | 第1-7页 | "EV5：SB=1，读 STAR1 然后将地址写入 DATAR 寄存器将清除该事件"等 | I2C 外设 SFR 位事件编程模型：`STAR1`/`STAR2`(状态)、`DATAR`(数据)、`CTRL1`/`CTRL2`(控制)，标准 EVx 事件表（EV5/EV6/EV8/EV8_1/EV8_2/EV9 主模式；EV6_1/EV7/EV7_1 主接收；EV1/EV3/EV3_1/EV3_2 从发送；EV1/EV2/EV4 从接收），四种模式（主发送/主接收/从发送/从接收）时序图与库函数逐步对照 |
| WCHNET Protocol Stack Library Application Note v1D (sha256:1e1bf85517182dc3) | 第21页 | 全局中断状态表：位4 `GINT_STAT_SOCKET`、位2 `GINT_STAT_PHY_CHANGE`、位0 `GINT_STAT_UNREACH`；第22页 socket 中断状态表：位6 `SINT_STAT_TIM_OUT`、位4 `SINT_STAT_DISCONNECT`、位3 `SINT_STAT_CONNECT`、位2 `SINT_STAT_RECV` | 库级"中断"状态位（文档明确注明"实际上只是变量标志，并非 WCH 芯片产生的硬件中断"，第21页原文），非芯片硬件中断寄存器 |

### 4.4 器件标识类

**未发现。** 全部81个内容组关键词扫描（电子签名/唯一ID/唯一标识/器件ID/器件编号/芯片ID/芯片编号/选项字节/唯一识别码/UID/signature/unique id/device id/revision）+人工复核，**没有任何一份文档包含芯片电子签名区、唯一识别码寄存器、Flash容量寄存器、选项字节或器件ID/版本号寄存器的地址与位域说明**。命中的"版本号"关键词全部是软件库版本查询函数（`WCHNET_GetVer`、触摸库版本、`UHSIF_Get_Ver`）或 WCH-Link 下载工具版本要求，与芯片硬件标识寄存器无关。

与器件标识/Flash布局相关、值得记录但不构成"寄存器"的两处地址线索：
- BOOT区域作为用户区使用说明 v1.3 (sha256:d0f94305e9e3fba2) 第2页："新增内存段'BFLASH'，起始地址0x1fff0000，大小3328Byte" —— CH32V003/CH641/CH32V002/4/5/6/7 的 BOOT 区 Flash 地址与容量
- CH32V003_IAP使用说明 v1.1 (sha256:ab08fe3e2195cb74) 第1页："将 IAP 程序通过 WCH-LinkUtility 下载到 0x1FFFF000" —— 系统 Flash 启动区地址

**结论：器件标识类寄存器信息大概率存在于各芯片独立的《参考手册》/《数据手册》（Reference Manual/Datasheet）中，不在本次 EVT 树扫描范围内**（与 UHSIF 文档明确将寄存器细节外部引用到 `CH32H417DS0.PDF` 的模式一致，见4.2节）。

---

## 5. 抽取失败/需人工复核清单

**本次扫描的81个内容组中，pdftotext 均以退出码0完成抽取（无程序性失败）。** 但存在以下"抽取成功、内容不可靠或有已知缺口"的情况，如实记录：

1. **13 个物理原理图/PCB 文件、11 个内容组**（第1.10节所列）——`pdftotext -layout` 可抽出元件、网络以及可用的 pin/mux 标签；三张代表页已视觉复核。限定寄存器/地址正则为 0，但未逐页 OCR 或人工证明图形中完全没有寄存器信息。若需要完整引脚复用或图形连线关系，仍须查看原 PDF。
2. **CH32H417 UHSIF 开发参考手册（中英文）明确声明 76 个寄存器的地址/位域细节在本文档之外**（"详细的内容请参考 CH32H417DS0.PDF"，中英文版本第8/10页），该数据手册不在 `tmp/wch-evt/evt/` 范围内，本索引无法覆盖，需要单独定位 `CH32H417DS0.PDF` 后补充。
3. **未见明显寄存器表格被 pdftotext 错行/抽坏的情况**——PIOC/CHRISC8B/I2C/UHSIF/WCHNET 等含表格的核心文档经 `-layout` 抽取后表格结构清晰可读，未发现"有表但结果不可读"的页面。
4. 版本号确认为"未标注"的文档（已逐份翻页/关键词复核确认全文无版本声明，非抽取遗漏）：`WCHNET WEB配置程序说明`(52c2105f)、`WCHNET IAP升级方案使用教程`(bb149c4a)、`WCH触摸应用指南`(9c0f28254428f039)、`WCH_touch_lite库使用说明`(1d55728072da8f86)、`CH32V205_IAP使用说明`(63f10c5a8d1c0ac2)、`CH32V10x_IAP使用说明`(cf7ea9f355104b36)，以及全部原理图文件。

---

## 6. 其他值得记录的发现

- **CH533X/CH537X 芯片提示**：CHRISC8B 手册第10页提到"程序 ROM 为 OTP 工艺"及第5页"多周期...对于个别采用特殊工艺的芯片（目前仅 CH537X 芯片）则有可能超过两个周期"——CH533/CH537 系列芯片型号未见于本 EVT 树的11个顶层目录，是 RISC8B 内核应用范围比本仓库覆盖的 QingKe RISC-V 系列更广的旁证。
- **文件名≠文档标题的错配不止 PIOC 一处**：`CH32V00X Evaluation Board Reference.pdf`（V006树，无"-EN"后缀但内容是英文）与 `CH32V00x Evaluation Board Reference-EN.pdf`（V003树，有"-EN"后缀）说明 WCH 对"-EN"后缀的使用并不统一，不能仅凭文件名判断语言/内容归属，需要首页读取确认（本索引"真实文档名"列已按此原则填写）。
- **同名文档跨树版本不同**：`BOOT区域作为用户区使用说明.pdf` 在 V003 树是 V1.3（示例含 CH641），V006 树是 V1.1（示例仅 CH32V006）——sha256 不同，未被误合并为同一内容组。

---

**产出文件**：`/Users/apple/Projects/gccriscv-wch/wch-evt-pdf-instr-reg-index.md`（本文件）；抽取文本：`/Users/apple/Projects/gccriscv-wch/tmp/wch-evt/eval/evt-pdf-text/*.txt`（81份，文件名=sha256前8位）+ `manifest.json`（去重清单）+ `extract_log.json`（抽取日志）+ `keyword_hits.json`（关键词扫描原始命中）+ `version_scan.json`（版本行扫描原始结果）。
