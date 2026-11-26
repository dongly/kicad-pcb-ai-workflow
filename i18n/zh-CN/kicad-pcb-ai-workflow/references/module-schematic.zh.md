# 原理图设计与 PCB 同步

按需使用 [拓扑优先的绘图契约](schematic-ai-layout-rules.md)、[原理图视觉风格](schematic-style.md) 与 [系统集成](system-integration.md)。在放置全部符号之前，先解决网络拓扑、全局布线走廊与跨页连接。**默认使用层次图页，而不是全局标签：** 把每个功能模块放进一个子图页，通过层次标签 + 图页引脚与父图页相连，图页内部使用局部标签；只有具备整板层面的理由并登记 `allow_global_labels` 条目时才允许全局标签。可见的线段交叉并不能证明 KiCad 电气连接存在。核实层次标签、引脚端点、位号、NC 行为、供电方向以及电气/ERC 语义。

首个候选方案由 `schematic_candidate.py` 接受显式的、绑定来源的设计与原生期望网络契约。此后的常规修改应在**同一个**已授权的工作区项目内、用限定作用域的 Konnect 工具完成。KiCad 10 的 PCB IPC 并不自动提供原理图 IPC 编辑；Konnect 的原理图工具可能采用基于文件的操作。绝不允许两个写入者同时编辑一份未保存的原理图。

在 G1，复用节点 03 的项目冻结器件卡片简报；`static_review.py --stage schematic` 准备原生 XML/网表、PDF/图形审查材料以及已验证的缓存源文本。先只读取与当前相关的卡片条目。按需检查原始资料中的图示、注释、极限工况与厂商推荐电路。原生 ERC、引脚级网表、图形判读、实际项目取值与工程师确认是各自独立的强制检查。

原理图到 PCB 的同步：使用经过验证的 `update_pcb_from_schematic` 等价操作。先 `dry_run` 并记录 `plan_revision`；检查锁定对象、封装出处、受保护铜线与确切的拟定动作；然后只应用同一个 `expected_plan_revision`。遇到不匹配、超时或回滚失败时，先检查状态再重试。事后核实 UUID/位号/焊盘-网络映射、已保存的原理图/PCB 对应关系以及当前 DRC。复杂的层次、多单元与替换场景需要超越小型夹具测试的独立验收。

完整关卡见 [静态 AI 审查](static-ai-review.md) 与 [设计意图](design-intent.md)；动态 MCP 工具不是额外的 `workflow.py` 命令。

## 可执行的构图筛查

对新建的原理图，先用 `schematic_style.py /project --plan-input page-plan.json` 取得只读的页面规划。只要存在多于一个功能模块，规划就会建议层次根图页加子图页；只有在记录了工程理由时才允许设置 `prefer_hierarchy=false`。只在已登记的工作项目内按该规划用 Konnect 写入：每个模块用 `add_hierarchical_sheet`，子图页内放层次标签，父图页内 `import_sheet_pins`/`validate_sheet_pins`，电源/地轨使用原生电源符号。简单电路与自包含单元电路要用真实导线实现引脚对引脚连接；只有离开方块或跨图页的连接才使用标签。Konnect 的 `connect_to_net`/`batch_connect_to_net` 在图页内网络保持 `label_type=net_label`；不要改用 `global_label`，并设置 `stub_length`，让标签落在导线内部而不是引脚端点上。保存后对整个层次运行 `schematic_overlap.py`；其发现具有阻断性。把真实的图框/注释禁布区、显式电源与地轨的原生电源符号，以及既有的功能单图页图框或已验证的层次子图页纳入约束。保存并导出后，在项目原理图风格策略中启用 `composition.required=true`，并运行既有的 G1 静态审查：其中会调用 `schematic_style.audit()`。缺失或过期的渲染边界清单会阻断构图筛查；视觉/原生 ERC 审查保持独立。详情：[原理图构图关卡](schematic-composition-gates.md)。


## 强制的新符号批量预放置（只读候选关卡）

在调用 Konnect 插入符号之前，通过 [预放置策略](schematic-preplacement.md) 核实独立的引脚到网络拓扑以及当前完整测量过的页面几何。运行 `workflow.py run /project --task schematic.preplacement_plan --preplacement-request REPORT_PATH --preplacement-receipt RECEIPT_PATH`，随后立即用同一请求与回执运行 `schematic.preplacement_check`。凡出现 `BLOCKED`、过期/被修改的回执、未预留的标签/电源符号、拥堵的引脚出口或试布失败的候选，一律拒绝。这些工具不执行任何 KiCad 写入；宿主必须把实际 MCP 操作映射到确切的计划批次，然后回读原生网表/ERC、字段与渲染页面。Skill 之外直接发起的 MCP 调用不受拦截，未测量的图框/字体几何禁止自动接受间距。

## 两阶段规划与执行

对硬性电气、图框、碰撞与引脚/标签约束做预检。自动测试声明合法的 0/90/180/270 度旋转并为候选布局评分。占用、试布线长/弯折与 A* 资源限制属于软约束：未解决的布线需要人工审查并禁止未经验证的连线，但不应阻断几何上安全的仅符号批次。校验既有规划回执的哈希，而不重跑 A*。L1/L2 Konnect 工具可以在受保护的候选上执行首次使用的有界写入，随后做保存状态检查；L3 破坏性操作需要隔离验收。结果未知时停下检查，绝不自动重试。常规编辑不要新建项目副本。

**原生预放置几何：** 用 `schematic_native_geometry.py` 与 `geometry_mode=native_auto` 读取真实的 KiCad 符号图形、引脚与既有实例变换。不要手工编写符号矩形。真实文字字形与图框标题区域仍需渲染/图框证据。参见 [原生几何](schematic-native-geometry.md)。

**不要为 `lib_id` 预留文本框。** 它是不参与渲染的 KiCad 库查找键。只预留原理图上实际显示的原生符号图形/引脚与属性：可见的 Reference、Value、其他可见字段、标签与注释。省略 `value` 时使用原生库的 Value 属性，而不是 `lib_id` 后缀。参见 [原生几何](schematic-native-geometry.md)。
