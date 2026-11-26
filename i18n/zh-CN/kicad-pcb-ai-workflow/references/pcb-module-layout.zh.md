# 规则优先的 PCB 模块布局规划器 — R10 预览

## 必需的工程顺序

1. 先完成原生原理图/ERC 与 G2 符号引脚 → 封装焊盘核对。KiCad 10 的 Update PCB from Schematic（F8）负责同步封装与网络；XML 网表用于独立的焊盘/网络一致性核对，并非强制的中间导入步骤。
2. 在 G3 放置之前，先就制造约束、真实物理叠层、板框/连接器/孔位几何、RF 禁布区与固定锚点达成一致。按 KiCad Board Setup 设置走线/铜层间距、过孔直径/钻孔、孔环、铜到板边/孔间距、NetClass 以及设计专属的电源、高速、RF 与自定义规则的最小值。焊盘几何来自已核准的封装，而不是笼统的全局限制。
3. 以 pre_route 模式运行现有的 design_intent_audit.py 原生生效规则检查。规划器把七项有出处的制造最小值与实际 .kicad_pro 设置（毫米）逐项比较，并核对当前原生 PCB 与原理图 XML 的焊盘/网络标识是否一致。仅有一份 JSON 策略并不能证明规则已经激活。
4. 先确定整板的固定区域，再使用真实的正面 Courtyard 多边形和有界的网络邻近启发式，放置每个来源定义的功能模块中的关键成员与普通成员；最后测试有界的整模块平移，以协调模块之间的关系。
5. 规划器是只读的。通过唯一的 Konnect 写入者分小批写入精确的当前版本坐标，保存并回读，然后运行 `pcb.placement_pre`（`placement_review.py --phase pre_route`）作为 **仅布局的 G3 审查，不包含整板 DRC，也不要求零未连接**。G3 之后完成布线并重新填充铜区，再运行完整的原生 DRC 与 G4 审查。

## 输入契约与命令

用真实的、项目专属数据填写 assets/pcb-module-layout.template.json、assets/pcb-fab-placement-rules.template.json 和既有的 assets/placement-plan.template.json。fab 的 minimums_mm 取值必须包含 min_clearance_mm、min_track_width_mm、min_via_diameter_mm、min_via_drill_mm、min_annular_width_mm、min_copper_edge_clearance_mm 与 min_hole_to_hole_mm，外加 courtyard_clearance_mm。对应的 KiCad 序列化规则键包括 min_through_hole_diameter 和 min_via_annular_width。绝不允许凭空编造板厂最小值。

    python scripts/workflow.py run /project --task pcb.layout_preflight --layout-request 03_REPORTS/layout/request.json --layout-receipt /project/03_REPORTS/layout/rules-r1.json
    python scripts/workflow.py run /project --task pcb.layout_plan --layout-request 03_REPORTS/layout/request.json --layout-receipt /project/03_REPORTS/layout/rules-r1.json

RULES_VERIFIED_FOR_LAYOUT_PLANNING 是绑定来源的规划关卡，不是制造审批。BOUNDED_MODULAR_PLACEMENT_PROPOSAL 是只读候选，不是已放置的铜线，也不是 DRC 证据。只有在原生项目、板厂来源、网表、焊盘标识、叠层、板边与 RF/禁布区锚点都保持不变时，已保存的放置变更才复用规则预检。规则/封装/网络发生变更时必须重新执行原生预检。

## 限制

本预览支持矩形的原生 Edge.Cuts（gr_rect 或四段闭合正交 gr_line 线段），以及 placement_review.metadata() 返回的既有受支持的正交顶部 F.CrtYd 多边形。不受支持的多边形/圆弧/底层/曲线或 3D 几何必须提供真实的原生/人工证据；绝不允许推断虚构的包围盒。这一有界启发式保持封装朝向固定，不旋转完整模块，也不能证明可布线性、信号/回流完整性、热/RF 行为、装配安全性或制造适用性。未知几何、缺失规则证据或未同步的网络都会让规划器停止；搜索耗尽意味着需要重新规划，而不是 PCB 无法实现。KiCad 10/Konnect 的端到端实机执行仍有待验证。


## 任何 G3 布局规划之前必须获得用户对 JLCPCB 的明确批准

对常规 FR-4 2/4/6/8 层板，先用 `pcb.fab_preview` 预览保守的、来自工厂的参考值。把实际层数与全部建议尺寸**连同**制造商能力极限一并列出。等待用户明确批准后，`pcb.fab_confirm --apply` 会创建两个不可变的项目报告文件：`fab_approval` 和配套的 `fab_rules`。只有获得授权的 Konnect 写入者才能落实实际的 KiCad Board Setup 与叠层。布局请求必须引用该批准（`fab_approval`）及对应的 `fab_rules`；`pcb.layout_preflight` 会在昂贵的原生 NetClass 审计**之前**拒绝缺失、过期或已变更的人工批准。Konnect 保存之后，先回读真实叠层（含正确的成品铜厚）与生效规则，再规划模块放置；仅移动类规划可复用当前验收结果。来源、层数或建议规则发生变化即令授权失效。参见 [JLCPCB 确认流程](jlcpcb-fab-confirmation.md)。

## 原生 Courtyard 碰撞与放置安全的 DRC 预筛

当前规划器现在使用受支持的真实 Courtyard 多边形，而不再只用其轴对齐包围矩形。它保守地取「用户核准的 Courtyard 间隙」与已识别的 KiCad 自定义 `courtyard_clearance` 最小值两者中的较大者，并筛查禁止放置封装的 Keepout 区域、固定的 NPTH 安装孔、锁定件/连接器/RF 锚点、来源声明的固定/走廊约束，以及受支持的引脚级去耦与邻近规则。候选网格按需惰性生成并设有搜索上限，既有的合法封装位置优先保留。不受支持的几何与未知硬规则会导致阻断，而不是凭猜测继续。这仍然只是**只读预筛**，不能替代原生 KiCad DRC；真实的 Konnect 批量执行/保存/位置回读以及仅布局的 G3 审查仍然必需。整板 KiCad DRC 推迟到 G4 的布线与铜区重新填充之后。参见 [Courtyard 优先的几何与 DRC 语义](pcb-courtyard-hard-rules.md)。

## 强制阶段边界 — G3 不运行整板 DRC

- **布局：** `pcb.layout_preflight`（生效规则/网络标识，不是 DRC）→ `pcb.layout_plan`（仅坐标）→ 经授权的 Konnect 放置移动 → 保存并回读实际封装位置 → `pcb.placement_pre`（`placement_review.py --phase pre_route`）。G3 检查 Courtyard、装配/机械禁布区、模块边界、来源绑定的引脚级去耦/邻近关系以及预期的布线通道。此阶段的未连接网络/飞线属于正常现象，**不得当作 G3 布局错误**。
- **布线与铺铜：** G3 之后，对关键/普通网络、电源与 GND 布线；填充/重新填充铜区并验证保存状态的连通性。
- **G4：** 只有在布线与铜区重新填充之后，才使用 `pcb.prepare` / `pcb.gate` 执行独立的原生整板 KiCad DRC（包括未连接项）以及 AI/工程师审查。`pcb.placement_final` 是布线后单独进行的放置复查，不能替代完整 DRC。
- **不得**在 G3 中调用 `pcb.prepare`、`pcb.gate` 或 `kicad-cli pcb drc`，不得降低制造规则、压制违规项或伪造原生 DRC PASS。Konnect 的通用批量放置回滚仍是待实现能力，不是已实现的引擎。
