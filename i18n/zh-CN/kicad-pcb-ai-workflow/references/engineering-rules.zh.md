# 电子产品工程规则——安全性、适用性与 25 项受控修复

**当前 R10 优先级顺序：**适用法律/安全要求 → 产品规格与厂商数据手册/勘误 → 已批准的 PCB/PCBA 制造与项目约束 → 通用工程经验法则 → 外观。若来源冲突，停下来做一次有记录的工程决策与 ECO。绝不悄悄放宽硬性约束。下表保留历史 R9.x 修复 ID 作为兼容参考；权威的 R10 阶段归属与 Konnect 单写入者策略见[当前 16 节点工作流](latest-complete-workflow.md)。

已实现的检查器或退出码为 0 **并不**意味着产品已获量产批准。有来源依据的 PCB 规则、真实的项目专属数据、独立 KiCad ERC/DRC、原生等价几何、CAM/工厂 EQ 与人工签核，各自都可能独立成为必要条件。

## 1. 25 项规则级修复及其验证边界

| ID | 风险 | 工程规则/变更 | 已实现的控制手段与仍缺证据 |
|---|---|---|---|
| **R01** | P0 | 网表变更并非一律禁止；区分严格保留与经授权的 ECO | `netlist_guard.py` 的 preserve/eco；ECO 哈希与精确的预期差异。真实 ECO 仍需审批 |
| **R02** | P0 | 违规数量变少不是通过判据 | `engineering_gate.py` 按违规身份比对；原生报错与未经审阅的排除项阻断；高风险项需要逐条证据 |
| **R03** | P0 | 不得一刀切抑制 unconnected 警告 | 原生已排除的报错仍阻断；焊盘位置或缺失的 pad-to-zone 报错都不能证明实际连通 |
| **R04** | P0 | 孔工艺、跨层与制造意图必须一致 | 需要叠层、钻孔层对与真实 CAM；盲埋孔中的矛盾不能靠一条方便的备注豁免 |
| **R05** | P0 | 不要从间距/焊盘长边或通用 45° 几何技巧推断铜箔短路 | `pad_audit.py` 支持旋转矩形与圆形；不支持的焊盘形状需要原生 DRC/焊盘图形检查 |
| **R06** | P0 | XML 为空或解析失败不得靠退出码 0 蒙混通过 | 严格校验元件/网络/引脚 XML，保留 singleton/unconnected 语义；FAIL=1, BLOCKED=2 |
| **R07** | P0 | 差分审计必须包含弧线并区分过孔 | `link_audit.py` 检查唯一端点路径、走线/弧线/过孔、ps 级延迟、跨度与换层；复杂板的原生校验仍须具体分析 |
| **R08** | P1 | 旧的项目探查工具只作诊断，不是放行关卡 | 缺失、未闭合或畸形的 courtyard 不算获批；需要项目专属的几何/档案 |
| **R09** | P1 | 缺失的工具不是有效的保护 | SHA-256 工具清单绑定构建、命令、版本与证据范围；被排除的旧辅助工具不会成为默认依赖 |
| **R10** | P1 | 固定的八层名称不是真实叠层 | 为每条信号路径记录物理顺序、相关频率下的介质/Dk/Df、铜厚、参考平面与制板批准 |
| **R11** | P1 | AGND/DGND 并非总是单点连接 | 依据芯片本身、隔离方案与实际回流电流；功能分区不意味着必须分割地平面 |
| **R12** | P1 | 不要默认在每个平面分割处跨接电容 | 避免跨分割，区分地对地与参考面切换，并保护安全隔离 |
| **R13** | P1 | 不要把同一条差分长度公差套用到所有协议 | 区分 USB2/USB3、D-PHY/C-PHY、HDMI 各模式、RGMII 单端时序与以太网 MDI，以及 DDR 专属 lane/时序；计入封装内延迟 |
| **R14** | P1 | 绝不通过重命名网络或全局调低阈值来掩盖偏斜 | 在串联元件两侧保持差分对身份；追踪残桩/分支与端点映射，阻断不支持的拓扑 |
| **R15** | P1 | 3W/20H/90° 是情境化经验法则，不是判定通过/失败的电气定律 | 明确实际线缘/中心距、叠层与串扰预算；45°/弧线不能证明 SI 达标 |
| **R16** | P1 | 不存在固定的 A/mm、内层铜厚减半或「每过孔 1 A」规则 | 计算稳态/峰值电流、IR 压降、I²R、温升与实际铜厚/电镀/散热环境；加厚焊料不是通用解法 |
| **R17** | P1 | 不要按数据率强制背钻，也不要随意使用盘中孔（via-in-pad） | 由残桩与信道模型决定；盖帽/填孔过孔的共面性须与板厂和贴装厂共同批准 |
| **R18** | P1 | 最小容量的电容并非一律放最近；也不要清除全部热隔离（thermal relief）警告 | 依据 PDN/DC 偏压/ESR/ESL/反谐振/负载瞬态证据；可焊性与电流路径决定焊盘连接方式 |
| **R19** | P1 | 不存在「2 mm 后强制换层」或通用的过孔到焊盘 0.8 mm 规则 | 方向只是偏好；扇出、回流路径、时序与制造工艺决定 dogbone/激光/微孔细节 |
| **R20** | P1 | 仅按 Value+Footprint 分组 BOM 无效 | `assembly_guard.py` 按全部必要的制造字段分组；DNP 与变体分开；核对 CPL 实装清单；极性/旋转需人工审阅 |
| **R21** | P1 | KiCad SVG 不是 Gerber 验收测试 | 校验真实 Gerber/Excellon 结构、完整哈希，以及绑定全部当前输出的独立 CAM；已有假文件/旧 CAM 检测 |
| **R22** | P1 | 最终源文件必须冻结、重新覆铜、保存并做原生复验 | R10 的 `freeze_candidate.py` 暂存一份独立副本，接受 **Konnect** 覆铜/保存凭据与原生 CLI DRC；不会用 pcbnew 悄悄写入活动板 |
| **R23** | P2 | 默认不强制每页 30 个器件、A4 或绝对布线比例 | 由功能可读性决定分页。若产品规范指定 A4 横向、三图架构或居中，该**明确的项目约定**具有约束力 |
| **R24** | P2 | 明确区分设计、CAM、制板 EQ 与放行权限 | 历史 0–7 + 叠层 2.5 与 G1–G6 记录为兼容背景；R10 现行设计主线 01–13、G1–G4，外部为 14–16 |
| **R25** | P1 | 不存在通用的电压、纹波、温度、可靠性或认证数值 | 按产品/市场适用性量化每条电源轨与用例；D2 制造候选不等于 D3 产品鉴定 |

第三列出现代码或 fixtures 并不意味着已对当前板卡完成实时 KiCad 校验、场几何校验、量产 CAM 或物理验证。任何相关的缺失证据都必须保持阻断或挂起。

## 2. 量化的产品级验收档案

使用 `assets/engineering-profile.template.json`。每项要求都必须标明其 **ID、来源文档与版本/定位符、设计规则、验收条件、方法、真实证据文件的 SHA-256 与处置结论**。`null` 表示未解决，不是默认值。`not_applicable` 需要真实理由、审阅人与证据。缺少厂商指引、制板极限或项目约束时，受影响阶段保持阻断。

### 叠层与阻抗

记录实际物理层顺序；介质材料、相关频率下的成品厚度与 Dk/Df；铜厚；连续参考平面；对称性/铜平衡；以及目标板厂确认。阻抗目标**不能**直接换算为线宽。归档求解器/阻抗测试条（coupon）假设、名义与极端工况公差结果、差分/叠层参考以及板厂批准。仅凭 NetClass 设置并不能证明所有规则都已生效并作用于目标网络。

### 高速与差分链路

每条链路须指明源/目的引脚；协议、比特率与最快信号边沿；串联器件的跨网络映射；分支/残桩；允许的层与回流参考；逐层延迟加上封装/连接器/过孔预算；偏斜、眼图/时序/损耗/串扰目标，以及所需的外部模型/测试。**USB 2/3、MIPI D-PHY/C-PHY、HDMI TMDS/FRL 与 RGMII** 各需独立档案。RGMII 按单端时序检查；其物理以太网 MDI 是差分的。DDR 必须使用实际控制器/存储器厂商的 lane/CK/CA/DQS 约束，而不是通用的毫米公差。

### 电源、热与安全

每路电源须记录连续、峰值与故障电流；允许的 IR 压降/I²R；负载瞬态与目标阻抗 ΔV/ΔI；电容 ESR/ESL/DC 偏压；实际散热与铜箔条件。安全间距需要工作电压、过压类别、污染等级、材料组、海拔、绝缘类别与适用标准——**不要**从一块无关的板子泛化出某个数值间距。

## 3. 遗留放行等级与 R10 工作流

历史 R9.x 阶段：需求（0）；原理图/G1（1）；封装/G2（2）；叠层（2.5）；布局/G3（3）；布线/G4（4）；制造/制板 EQ/G5（5）；样机（6）；ECO/G6（7）。R10 现行的 AI 设计范围是[节点 01–13](latest-complete-workflow.md)，涵盖 G1–G4 与**待审阅的设计包**；工厂授权与物理测试仍在外部。

- **D0：**内部未批准候选；不投产。
- **D1：**已验证设计加独立 CAM 仅可用于回答工厂工程问题，且以授权为前提；EQ 未解决即不得下达制造订单。
- **D2：**目标工厂的 EQ/叠层/钻孔/阻抗/装配文档已关闭，精确的源/输出哈希与生产授权对指定的板厂/订单有效。D2 字段本身并不构成上述检查的证据。
- **D3：**真实产品鉴定、适用的可靠性/认证、ECO 与产线/工艺证据；静态 Skill 脚本无法单独产出。

默认：仅预览；不自动向厂商上传或下单。创建 `build-manifest.json` 并不授予 ChatGPT 向第三方发送制造文件的权限。必须获得用户明确批准的交接。

## 4. 最终铜箔、制造证据与风险收口

使用受控候选流程：已批准源文件 → 带真实凭据的 Konnect 覆铜/保存 → 独立原生重载/DRC → 一致性/约束审阅 → 不可变导出与 CAM。绝不批准新旧铜箔状态混杂的板子、随后又悄悄删除旧铜箔并交付 Gerber。绝不覆写原始源文件，并保持失败可追溯。

```bash
python scripts/netlist_guard.py base.xml candidate.xml --mode preserve --topology
python scripts/netlist_guard.py base.xml candidate.xml --mode eco --eco approved-eco.json
python scripts/link_audit.py candidate.kicad_pcb --profile link-profile.json
python scripts/assembly_guard.py production-bom.csv --cpl cpl.csv --variant default
python scripts/freeze_candidate.py /project --board board.kicad_pcb --destination /new-candidate
# Preview above; --apply stages a new candidate and Konnect handoff, NOT automatic fill.
python scripts/validate_frozen_candidate.py /new-candidate --config /new-candidate/review-config.json --output-dir /new-final-evidence
```

路径图审计若出现不支持的焊盘边缘接入、分支或中层过孔端点，一律按 `BLOCKED` 处理，而不是「总走线长度大致可接受」。链路检查不能证明特性阻抗、回流平面连续性或信号眼图质量。

制造交接需要逐层 Gerber、包含 PTH/NPTH/槽孔/层对的 Excellon、制板与装配图纸、变体 BOM/CPL，以及适用的钢网/锡膏文件。**检查真实的 Gerber/Excellon，而不是从 PCB 导出的 SVG。**逐个核验合法的内部槽孔/孔位，而不是强加「只允许单一轮廓」的假设。不要手工镜像底面制造输出；与贴装厂一起复核摆放旋转、原点、极性、DNP 与 1 脚标识。

`build-manifest.json` 必须绑定 D2、当前源文件与输出哈希、真实的工具版本/命令/日志、最终状态、与**全部**当前铜箔/钻孔输出哈希匹配且经独立审阅的 CAM JSON、已关闭的 EQ，以及限定于工厂/订单的授权。仅凭文件结构标记只能做完整性抽查，不构成完整的 Gerber 解析器或 CAM 批准。

高风险发现需要**逐项、内容绑定**的批准（规则/位置/描述指纹）；不得整类豁免警告。原生报错与未经审阅的排除项始终阻断。绝不通过重命名网络、调低全局 skew/unconnected 规则、删除对象或修改报告来逃避失败的检查。

## 5. 厂商与官方技术依据

- [KiCad 10 CLI](https://docs.kicad.org/10.0/en/cli/cli.html) 与 [KiCad PCB 编辑器](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html)。
- [Analog Devices 混合信号板布局](https://www.analog.com/en/resources/analog-dialogue/articles/what-are-the-basic-guidelines-for-layout-design-of-mixed-signal-pcbs.html)。
- [Texas Instruments SLLA414](https://www.ti.com/lit/an/slla414/slla414.pdf)。
- [Espressif ESP32-S3 PCB 布局指引](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/pcb-layout-design.html)。

这些来源为工程方法与能力提供参考，并不为当前设计背书。对 IPC/IEC 标准与厂商/板厂规则，须绑定实际适用的版本与许可。绝不伪造来源核验或合规结论。
