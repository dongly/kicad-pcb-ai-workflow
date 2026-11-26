# 独立的 G1 原理图与 G4 PCB AI 评审

## 职责与证据

`static_review.py` 从当前已保存的项目创建*全新的、不可变的证据包*。其中在可用时包含原生网表/导出、既有的文档/源哈希、项目输入、选定的 PDF/文本证据、评审任务、解析后的检查项与可视化视图。它不会静默修改原理图或 PCB。模型读取当前任务包、被引用的源文档段落与真实的网络/几何数据，然后写出明确的 `ai-review.json`，给出每个必需任务的状态与发现。`static_review_gate.py` 检查证据包完整性、原生就绪状态、风险、AI 报告、项目版本与实际工程师评审。AI 绝不能自我批准。

`AI_REQUIRED`、缺失的事实、不受支持的原生输出或源版本不一致均*不*算 PASS。即使模型最初只看到小型的有界摘要，关卡也必须处理**完整**的原始证据包与证据。所有额外发现的问题都必须记录在结构化的 `additional_findings` 中，而不能只写在叙述性文字里。工程师批准绑定到确切的证据包与当前项目哈希。

## G1 评审流程

1. 确认当前原理图 `.kicad_sch/.kicad_pro`、项目源文件集合、需求、真实的 KiCad 导出与 ERC。独立提供的 XML 预览不等价于原生当前网表导出。
2. 先读取 `packet.json` 与 `device_knowledge_brief`；选择与实际 MPN、封装及应用相匹配的电源、上电启动、时钟、复位、boot、接口与推荐电路。
3. 检查当前引脚-网络事实、供电树、未用/NC 引脚、参考电压、分压/容差与电流路径计算。将每条相关需求与原始制造商文档的引用定位符比对；必要时查阅插图/脚注。
4. 阅读真实的原理图页面/可视化导出。检查层次结构、离页标签、结点、布线歧义、符号值/位号/极性与模块可读性。原生 ERC 无法证明预期的电气功能。
5. 为每个强制任务记录一个 `PASS`、`FAIL`、`NEEDS_EVIDENCE` 或适用的报告值，并附实测的真实数值、源定位符与精确的修复/复测步骤。另行完成人工工程师确认。

## G4 评审流程

1. 要求**已保存、已布线、已完成覆铜填充的板卡**、与原理图的实际一致性、已批准的叠层/NetClass 以及原生 DRC。通过 `project_stage_brief` 获取 G4 专属的已核验卡片。
2. 检查每个真实铜层与相关视图。评估关键信号路径、差分配对/长度预算、过孔、参考平面跨越、RF 天线区域、功率/回流电流、滤波、去耦、连接器信号、结构、装配与测试可达性。
3. 追踪真实的 UUID/位号/网络/层/坐标；避免把未观察到的网络报告为已布线、把焊盘中心距离误当作回流环路面积，或仅凭 DRC 推断 SI/PI/EMC。
4. 产出结构化 AI 评审与独立的工程师处置。PCB 几何、规则、源卡片或证据哈希被修改后，受影响的旧 G4 证据包即失效。

## 阶段准备与按需模型上下文

```bash
# Always target distinct, explicit review directories; do not overwrite signed evidence.
python scripts/static_review.py /project --config /project/static-review.json --stage schematic --output-dir /project/03_REPORTS/G1-r1
python scripts/static_review.py /project --config /project/static-review.json --stage pcb --output-dir /project/03_REPORTS/G4-r1
# Show a bounded initial summary while preserving full report files.
python scripts/token_budget.py --input /project/03_REPORTS/G1-r1/checks.json --limit 6
```

准备阶段可以复制真实源文件并生成本地 PDF 文本，用于**审计留存**，而不是把全部字节注入模型上下文。若源文本的 SHA 与项目冻结缓存匹配，则直接复用。日常评审时，模型先读取简报与真实的当前检查项。仅展开解决差异所需的精确位置；高风险上下文需要时才展开完整源文件。

## 关卡安全与当前版本绑定

- 原始与被评审的源文件/板卡必须与证据包中记录的输入哈希一致。原生 CLI 环境与报告 schema 必须获得接受。未解决的硬风险项不能仅凭签名豁免。
- AI 评审内容与工程师确认相互独立。具体的评审者必须记录证据包标识、决定、日期、当前问题的处置与理由。模型不得伪造该记录。
- 项目变体、资源锁、预留选项、接口契约与 G3 布局在已配置时会被检查；缺少必需策略则证据包不完整。
- 静态评审不是硬件台架测试、阻抗场求解器、热分析、EMC 测试或工厂 CAM 验收。不受支持的主张应作为带有负责人与证明要求的外部测试上报。

参见[需求与风险类别](engineering-rules.md)、[阶段批准](stage-approvals.md)与[最新 16 节点工作流](latest-complete-workflow.md)。

## 强制的源与任务契约

`assets/static-review.template.json` 只是 schema 示例，不是有效的当前工程批准。每条已批准的 `documents` 条目都需要真实且本地冻结的文件、SHA-256、发布方、标题、版本、适用性与来源批准；`authority` 类别区分 `product_spec`、`datasheet`、`manufacturer_guide`、`industry_standard`、`factory_spec`。每个任务必须声明其 `id/category/requirement/strength/level/targets/source_refs/check`，其中 `strength` 区分强制约束、建议与典型示例。不得把典型图示或绝对最大额定值提升为无条件的设计限值。

`component_sources` 将每个关键器件绑定到精确匹配的制造商、MPN、封装与版本；`critical_nets` 显式覆盖电源/地、自举/跳线/复位、时钟、差分/高速、RF/模拟与外部接口。`support_files` 必须按实际使用绑定 BOM、叠层、库、计算、设计意图与相关图纸。原理图的层次子图与导入的原始文档都必须纳入评审基线；截图不能证明不可见的连线或跨图纸连通性。

| 检查类型 | 确定性覆盖范围 | 不足以覆盖的场景 |
|---|---|---|
| `pin_net`、`same_net`、`different_nets` | 实际 KiCad XML 引脚/网络归属 | 连接器语义、器件行为或未被网表关联的交叉走线 |
| `component_field` | 精确的值、封装、数据手册或已声明的器件字段 | 轻信相似的封装/MPN 描述 |
| `voltage_levels` | 显式的 VOH/VOL、VIH/VIL 与绝对工作边界 | 电流负载、掉电注入、上升/下降、时序与故障行为 |
| `resistor_divider` | 实际的三网络电路，以及容差范围内最坏情况的*空载*直流分压比 | 闭环稳定性、负载、漏电流、瞬态 |
| `track_geometry`、`via_count` | 具名的走线线段/弧线、层、线宽与过孔数量 | 特性阻抗、回流连续性或过孔残桩效应 |
| `pad_distance` | 真实的焊盘中心间距 | 电流环路几何/地电感 |
| `endpoint_path` | 已声明的点对点路径与受支持的时延模型 | 未声明的分支或完整通道 SI 分析 |
| `semantic` | AI 必须检查源文档、图形与真实视图 | Python 返回 `AI_REQUIRED`；绝不静默 PASS |

制造商 PDF 文本抽取（可用时使用 `pdftotext`）只是带索引的*文本来源*，不能证明已查看图示、表格布局、波形条件或图注。对于扫描版 PDF 或关键的制造商图纸，评审 Agent 必须查看原始图示（无法获得时须指出缺口）。在缓存优先路径下，先比对文件哈希并复用已冻结的器件卡片文本，而不是重复抽取每个 PDF 或重复搜索公共互联网。

## G1：原理图评审义务

1. 核验真实的源版本、MPN、封装、电压/温度/工作条件、原始制造商推荐电路与勘误；拒绝不恰当的参考板假设。
2. 查看真实的 KiCad 导出原理图 PDF 与原始制造商图纸；将所有具名引脚与实际导出的 XML 交叉核对。视觉上的线条交叉不是电气结点；在没有导出证据的情况下，两个层次标签也不能证明同一网络。
3. 按适用情况覆盖电源输入/输出/使能/反馈与上电启动、时钟源及其负载、复位/跳线行为、接口极性/逻辑电平、端接/交流耦合/ESD、电源故障处理、模拟输入/反馈、散热/裸露焊盘要求，以及每个适用的已贴装/未贴装 BOM 变体。并非每个产品都需要相同的看门狗、复位或防护架构；须书面记录适用性。
4. 区分真实的确定性 FAIL 与语义不确定性。AI 必须为预设任务未列出的风险记录 `additional_findings`，并为缺失图纸、不可读源或未经测试的动态行为记录 `NEEDS_EVIDENCE`。
5. 原生 ERC/网表一致性 + AI 基于源文档的推理 + 实际工程师批准是**三项相互独立**的批准。正确的网表不能证明视觉可读性或安全的电源行为。

## G4：PCB 评审义务

1. 阅读已保存的板卡与当前叠层、真实的封装/焊盘/网络几何、走线/弧线/过孔/覆铜区以及**所有铜层视图**，而不是单张好看的单个截图。SVG 视图不等于 Gerber CAM 检查。
2. 从真实端点出发追踪关键通道，尊重串联器件与参考/回流层；检查层切换、空洞、分割、差分布线、接地/回流与应用相关的时序。若阻抗或时延模型不可用，保持 `NEEDS_EVIDENCE`，而不是断言 SI 成功。
3. 检查供电主干、走线收窄段、电流与过孔/散热限值、开关环路、反馈路径、振荡器与 RF 馈电/天线净距、焊盘到器件的回流几何与制造商布局要求。欧氏距离短并不能证明低电感环路。
4. 检查工厂制造规则、板框、孔、courtyard、装配极性与变体、DNP 与测试可达性。原生 DRC、信号质量工程判断与工厂 CAM 评审保持相互独立。
5. 以正确的对象标识与来源位置记录全部所需的封装、关键网络与铜层观察结果。未展示某区域的图示不能作为该区域正确性的证据。

## AI 报告、处置与工程师证据

运行中的 Agent 必须读取 `packet.json`、`facts.json`、`checks.json`、G1/G4 各阶段专属的 `device-knowledge-brief.json`、相关源文档引用与真实视图，然后产出独立的 `ai-review.json` 与可读的工程报告。它不能把自己标记为真实的人类评审者。每个任务的 AI 状态为 `PASS|FAIL|NEEDS_EVIDENCE|NOT_APPLICABLE`；保留原有的工程严重级别，并记录真实观察结果（`ref/pin/net/layer/view` 或精确的 facts JSON 指针）、适用条件、简短的已核验源文档引用、推理过程与可执行的修复/验证计划。`additional_findings` 必须包含结构化的新发现问题，即使没有预设任务覆盖它们。器件、关键网络与铜层的完整 `coverage` 不能用一句 "all covered."（全部已覆盖）的断言来替代。

`not_applicable`/`accept_deviation` 之类的处置需要证据、理由，并绑定到每个当前条目的 SHA；它们不能使活跃的阻断项或缺失的源失效。人工的 `engineer-review.json` 绑定真实评审者、日期、范围、决定以及证据包/AI 的 SHA 哈希；不得有 AI 生成的签名或伪造的测试结果。关卡检查这一绑定与当前文件，但无法认证个人身份，也无法保证推理在技术上正确。`APPROVED_STATIC` 仅表示*静态评审通过*；它不授权生产。文件或源适用性的变更会使受影响的评审证据失效。修改 PCB 铜皮不必然使未变的原理图知识失效，但会使受影响的 PCB G4 及后续制造文件失效。

```bash
python scripts/static_review.py /project --config /project/static-review.json --stage schematic --output-dir /project/03_REPORTS/G1-r1
python scripts/static_review_gate.py /project --packet /project/03_REPORTS/G1-r1 --ai-review /project/03_REPORTS/G1-r1/ai-review.json
# After a real engineer review, supply an actual engineer-review.json for the same packet:
python scripts/static_review_gate.py /project --packet /project/03_REPORTS/G1-r1 --ai-review /project/03_REPORTS/G1-r1/ai-review.json --engineer-review /project/03_REPORTS/G1-r1/engineer-review.json
python scripts/static_review.py /project --config /project/static-review.json --stage pcb --output-dir /project/03_REPORTS/G4-r1
```

成功的 `prepare` 只证明证据包已创建；若没有独立有效的当前 KiCad CLI/网表/Drc 证据，它只是*预览*，不是已批准的板卡。关卡可以拒绝：缺失 ERC/DRC、未更新/损坏的证据、仅 AI 的批准或过期的人工评审。产品性能、热、EMC、眼图/USB 合规、仿真与样机测试仍需外部真实证据。在 R10 下，Konnect 是唯一的活动 EDA 写入方；可选的旧版 pcbnew 仅限于独立隔离的只读兼容，不是自动的保存/填充回退。
