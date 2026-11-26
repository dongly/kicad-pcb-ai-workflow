---
name: kicad-pcb-ai-workflow
description: "KiCad PCB/原理图技能：G1–G4 知识复用、Konnect 单一写入者、KiCad CLI 验证、单一工作工程、紧凑上下文。"
---

# KiCad PCB AI 技能 R10 — 单一工作区，最小上下文

## 不可妥协的执行规则

1. **唯一权威工作工程。** 若存在 `CURRENT_PROJECT.json`，先运行 `workflow.py workspace ROOT --action status`。普通的符号创建、网络编辑、摆放、布线与丝印编辑继续在已登记的 `01_WORKING/` 工程内进行。**不要为每次增量编辑都运行 init/build 或生成新的原理图候选。** 只有初始创建、高风险测试、里程碑或最终冻结才创建独立候选。每批新原理图符号之前，必须执行绑定源数据的[预布局门禁](references/schematic-preplacement.md)：独立拓扑、占用/禁布/字段/标签/引脚空间预留、试布走线，以及按确切回执重新校验。可行方案不等于真实的原生 KiCad 编辑或已验证的 ERC。不要猜测旧工程的最新副本。参见[工作区与上下文策略](references/workspace-and-token-policy.md)。
2. **单一 EDA 写入者，带首次使用后置检查。** Konnect MCP 执行活动 EDA 写入，Python 负责规划/审计，KiCad CLI 校验已保存结果。动态发现工具；L0 读取与有界的 L1/L2 首次使用编辑不需要一揽子 fixture 验收，但需要当前目标/schema、明确授权、保存与立即回读。未经验证的未知改动保持未批准状态；L3 破坏性工具需要隔离验收。绝不静默重试或切换到 pcbnew。
3. **原厂数据缓存优先。** 节点 3 在抓取外部来源之前，先查找精确的制造商、MPN 与封装。在 G1/6、G2/7、G3/9 与 G4/11 复用已冻结的知识卡；仅在来源缺失/过期/冲突时重新核实。每个工程都独立核查。参见[器件知识](references/device-knowledge.md)。
4. **工程门禁相互独立。** 绝不编造电气、SI/PI 或板厂参数。核查每个实际设计与现行规则。原生 ERC/DRC、有来源依据的 AI 审查与工程师批准相互独立；输入变更会使受影响的证据失效。制造产物保持 `EXPORTED_NOT_RELEASED` 状态；CAM/工厂 EQ、样机测试与 ECO 需要单独的外部授权。不要删除历史工程或证据。
5. **上下文高效阅读，但不减少检查。** 只加载当前任务的模块。从 `status --format compact`、知识 `brief` 或 `report-brief` 开始；只展开相关异常与被引用的数据。完整保留磁盘证据；门禁校验完整文件，绝不基于摘要。
6. **现有原理图的最小改动。** 修改现有原理图时，默认仅在现有图纸上做局部微调。保留当前图纸结构以及现有器件摆放和布线；除非用户明确要求，否则不要重组设计、重画整块电路或把电路移到其他图纸。如果认为需要更大范围的改动，先说明原因并征求同意。

## 原理图构图检查（新设计）

摆放符号之前，先用 `schematic_style.py --plan-input page-plan.json` 选择单张带功能区块分区的图纸，或分层根图加子图纸。若多个功能电路放在同一张图纸上，用直线图形分隔线和/或矩形框进行视觉分组与分隔；这些图形要避开符号、导线、标签和文本，不能用电气导线充当边框。**分层结构是默认选择：** 功能模块多于一个时，规划器建议根总览图加真实子 `.kicad_sch` 文件；单页方案需要显式设置 `prefer_hierarchy=false` 并说明理由。**不要把全局标签当作连接区块或图纸的默认手段。** 跨图纸信号使用子图中的分层标签，并与父图中对应的图纸引脚绑定（`add_hierarchical_sheet` → `add_schematic_net_label label_type=hierarchical_label` → `import_sheet_pins` → `validate_sheet_pins`）；单张图纸内部使用本地标签；全局标签只保留给 `composition.labels.allow_global_labels` 中列出的少数真正贯穿整板的网络，G1 风格门禁强制执行这一点（`LABEL_POLICY.GLOBAL`）。**在每个简单电路和自包含单元电路内部，优先用真实导线直接连接引脚**；不要用标签替代短距离本地连接，标签只用于离开功能块或跨图纸的连接。**网络标签绝不能直接放在普通元件引脚或父图中的图纸符号引脚上，也不能放在导线端点上：** 先从引脚引出一段导线，再把标签锚点放在导线内部，并让整段文字覆盖在导线上方（Konnect `connect_to_net`：给出 `stub_length`）。每轮绘制之后都要对整个层次结构运行 `schematic_overlap.py --png --output-dir NEW_DIR`（需要 `pypdfium2`）；KiCad ERC 既不检查文字重叠也不检查图形重叠，该脚本的发现会阻断 G1。`STROKE` 段比较 SVG 导出中的绘制笔画，因此导线穿过文字、文字叠文字等重叠均以精确墨迹接触判定；PNG 仅用于判断可读性，没有任何脚本度量这一点。保留实际的工作表标题栏与注释区域。显式正电源/地电源轨使用原生 KiCad 电源库符号；**电源网络绝不能用全局标签（或任何其他标签）接线**——`composition.power.rails` 中的每条电源轨都必须以 `power:` 符号出现，`allow_rail_labels` 必须为空，否则门禁报告 `POWER_SYMBOL_POLICY.LABEL`。新原理图的 G1 风格策略必须显式启用 `composition.required=true`，并绑定实际渲染几何与完整的对象清单。`schematic_style.py` 门禁筛查禁布区、电源轨符号与图纸层次，但任何几何筛查都无法在没有真实页面审查的情况下证明视觉质量。不要生成未经核实的布局几何，也不要声称自动摆放。参见[构图检查](references/schematic-composition-gates.md)。

每个新的符号摆放批次之前，优先使用 `geometry_mode=native_auto`，并通过 [`schematic_native_geometry.py`](references/schematic-native-geometry.md) 提取真实的 KiCad 符号图形、引脚、字段与当前实例位置。不要凭空捏造每个符号的矩形。工作表标题栏区域需要针对具体工程的来源证据，保守的字体边界仍需 KiCad 渲染审查。第二次快速门禁复用几何/来源 SHA 哈希，无需重跑 A*。

## 强制 PCB 布线顺序（七阶段；范围限定 Freerouting 2.5.0）

G3 仅布局审查之后（G3 绝不运行全板 DRC），阅读[七阶段布线契约](references/freerouting-seven-stage.md)、[电源/颈缩与后端约束](references/constraint-routing.md)以及[PCB 模块](references/module-pcb.md)。

1. 盘点**全部实际**的原理图 XML/KiCad 网络与 (ref,pin)/(pad) 端点；对每条电源/关键/普通/GND 网络分类，并记录预期电流与优先级。未知网络 = BLOCKED。
2. 确认制造商、层数/铜厚、生效的 KiCad NetClass 与自定义规则，以及线宽/间距/过孔/叠层/角度策略。通过已验收的 Konnect 写入者应用，并**回读实际生效的规则状态**。仅有 JSON 规则请求并不等于规则已应用。
3. 先布线并保护关键网络（电源、RF、差分、时序、开关回路、Kelvin 与回流路径）。确认实际保存的几何与锁定/保护证据。
4. 仅对符合条件的普通网络使用已验证的 Freerouting **2.5.0 DSN->SES**，提供经审查的显式 DSN/规则哈希，并用 `-inc` 排除包括 GND 与关键网络在内的 **NetClass**。从 KiCad 侧核实类成员资格；DSN 中出现的类名不足以作为依据。绝不布普通 GND 走线。
5. 通过经授权的 Konnect/KiCad 将 SES 导入隔离的 PCB 候选。保存/回读并运行 `routing_seven_stage.py audit-import`，检查来源哈希、受保护铜对象、H/V/45°、最小线宽、层、过孔与网络一致性。导入失败或不完整按 BLOCKED 处理。
6. 只允许有界重试或经批准的局部原生修复，并生成新的绑定源检查点与明确的网络/拆线范围；绝不静默放宽制造商约束、电源干线宽度（+0.254 mm）、已批准的局部焊盘颈缩、RF/阻抗、间距或 GND 策略。
7. 重新填充已验证的 GND 铜区，确认实际回流/连接，保存/重载，在 G4 执行独立完整的 KiCad **原生 DRC**（含未连接项）、最终几何审计、适用时的 SI/PI/热分析，以及工程 G4 签核。证明失败或缺失 = BLOCKED；不存在隐含的制造放行。

`routing_seven_stage.py` 是**只读的阶段规划器与导入后板级审计器**，不是 Freerouting 调用引擎、KiCad 写入者、原生 DRC 运行器或 G4 批准。其运行成功不能替代 Konnect/KiCad 端到端实时证据。通过 `workflow.py run PROJECT --bundle BUNDLE --task pcb.routing_seven_plan --routing-stage-config CONFIG` 运行（另有 `pcb.routing_import_audit`、`pcb.routing_final_audit`）。

## 按任务的参考文档路由

**原生案例覆盖（2026-11-21）：** 仓库中的单铜层 8×8 LED 示例已完成 Windows/KiCad 10.0.8 的原理图/PCB 工作、零警告原生 ERC/DRC，以及经核查的 Gerber/BOM 工程导出。已摆放字段的修复需要单独构建的开源 Konnect 扩展；原版 0.13.0/0.14.1 缺少该接口。这是一个案例，不是全板型/全平台或完整 16 节点认证。相关警告见[丝印/字段修复](references/pcb-silkscreen-fields.md)，单铜层/job/BOM 陷阱见[工程导出检查](references/engineering-export-lessons.md)。工厂 CAM 与硬件测试仍属外部流程。

| 请求的任务 | 优先阅读 |
|---|---|
| 连接、环境、工作区 | [module-environment](references/module-environment.md) |
| 需求、架构、原厂参考 | [module-requirements](references/module-requirements.md) |
| 符号、引脚映射、封装 | [module-resources](references/module-resources.md) |
| 原理图编辑、实际网络、G1 | [module-schematic](references/module-schematic.md) |
| PCB 约束、布局、布线、铺铜 | [module-pcb](references/module-pcb.md) |
| 仅在适用时的高速/PI | [module-high-speed](references/module-high-speed.md) |
| DFX/NPI、评审、制造候选 | [module-manufacturing](references/module-manufacturing.md) |
| 外部样机/ECO，仅在单独提出时 | [module-lifecycle](references/module-lifecycle.md) |

仅在需要时使用 `python scripts/workflow.py modules --intent schematic`。进阶参考：[16 节点](references/latest-complete-workflow.md) · [Konnect 能力](references/konnect-capability-migration.md)。

## 工作区结构

```text
/project/
  01_WORKING/       Project.kicad_pro + .kicad_sch + .kicad_pcb
  02_CHECKPOINTS/   Immutable milestone/high-risk backups only
  03_REPORTS/       Full ERC, DRC, G1–G4 and other evidence
  04_RELEASE/       Isolated, never implicitly approved deliverables
  CURRENT_PROJECT.json  # Authoritative navigation index, never approval
```

```bash
# First place the complete project and relative library resources in 01_WORKING.
python scripts/workflow.py workspace /project --action init --project-file 01_WORKING/Project.kicad_pro --apply
python scripts/workflow.py workspace /project --action status
python scripts/workflow.py workspace /project --action inventory  # Classify only, preserve files
python scripts/workflow.py workspace /project --action checkpoint --label G1-approved --apply
python scripts/workflow.py status /project --bundle control-r1 --format compact
python scripts/workflow.py report-brief /project/03_REPORTS/G1/checks.json --limit 6
```

连接检查只执行一次足够充分的读取；不自动创建测试板。写入需要授权与目标校验。布线流程：板厂规则 → 网络类 → 关键网络 → Konnect 批量操作 → 保存回读 → 原生 DRC → G4。规划不等于执行。

制造阶段使用带防护的 `--mode mass_production` 与 [DFX/NPI](references/dfx-npi.md)；`--mode prototype` 不能授权放行。`npi_release.py` 需要现行 CAM/工厂证据与工程师签核；任何上下文优化都不能绕过放行门禁。

**原理图两阶段工作流：** 摆放前检查独立的引脚/网络契约、标题栏排除区、真实的对象/文字碰撞与有效的标签/引脚锚点。搜索已声明的合法正交旋转并比较有界候选评分。将密度、试布长度/拐弯与求解器预算视为*参考项*：布线不确定时只允许摆放符号，不代表接受布线。复查计划/来源 SHA 而不重复运行 A*，并在每次 Konnect 编辑之后核查实际保存的几何、原生网络表/ERC 与视觉证据。参见[预布局](references/schematic-preplacement.md)。

**规则先于 PCB 布局：** G2 之后，从原理图同步 PCB（KiCad F8）；在移动封装之前应用实际的板厂/叠层/网络类/Board Setup 约束。先运行 `pcb.layout_preflight`（原生生效规则、现行物理最小值与 PCB/XML 网络一致性），再运行 `pcb.layout_plan`（先局部模块布局，再全板协调）。计划只读：使用唯一的 Konnect 写入者，保存并回读实际封装位置，然后运行 `pcb.placement_pre` / `placement_review.py --phase pre_route` 完成**仅布局的 G3 门禁，不运行全板 DRC，也没有零未连接要求**。G3 之后布完所有需要的网络，完成电源/GND 并重新铺铜；然后才运行 `pcb.prepare`（完整原生 DRC）与 `pcb.gate` 进入 G4。参见[PCB 模块布局](references/pcb-module-layout.md)。

**PCB 布局前显式确认 JLCPCB 制造参数：** 对普通 2/4/6/8 层刚性 FR-4，先用 `pcb.fab_preview` 并排展示实际工程层数、依据制造商信息的保守设计规则与官方能力上限。在 `pcb.fab_confirm --apply` 之前停下，等待实际用户的明确批准。不要伪造用户同意，也不要把预览当作已应用的规则。Konnect 是唯一的 KiCad 写入者：应用选定的真实 Board Setup/叠层，然后在 `pcb.layout_plan` 之前要求 `pcb.layout_preflight` 中有原生回读与现行 `fab_approval`。参见[用户确认的制造基线](references/jlcpcb-fab-confirmation.md)。

**G3 的 courtyard 优先几何：** 只读的 `pcb.layout_plan` 现在会在提出布局位置之前，先筛查受支持的实际 courtyard 多边形（含已批准的额外 courtyard 间隙与被识别的 KiCad 自定义 `courtyard_clearance`）、固定的 NPTH 孔、封装禁布区、固定/连接器/RF 锚点，以及声明的引脚级去耦/邻近限制。受支持范围内的未知几何或强制性电气规则一律阻断，不做猜测。候选结果*不是* DRC PASS。Konnect 保存位置回读与 `pcb.placement_pre`（courtyard、机械、关键引脚邻近与布线走廊的**布局**筛查）共同决定 G3 就绪状态；**走线未完成时绝不运行全板 DRC**。完整原生 DRC（含未连接项）必须在 G4 于**布线与重新铺铜之后**强制执行。参见[courtyard 硬规则预筛查](references/pcb-courtyard-hard-rules.md)。

**布线边界（R10 预览）：** G3 之后，要求完成全部具名 XML 网络的分类。默认采用 GND 过孔/铜区回流，而不是把 GND 当作普通 A* 目标。普通实验性 A* 候选使用 H/V/45° 线段，连续转弯最大 45°；受支持的专用布线器可能需要其他经批准的几何形式。电源**主干**使用用户提供的电流表（仅 1/1.5/2 oz）+ 至少 0.254 mm 的**线宽余量**，并叠加有来源依据的温升/压降下限。细间距焊盘入口可能需要**短且经明确批准的颈缩**，但绝不能低于板厂真实绝对最小值；写明确切的焊盘/区域，限制长度/数量，核查真实热性能与原生生效的自定义规则，并尽早恢复加宽。当前离线 A* 求解器**未实现**此类混合线宽的布线铜皮；缺少验收依据时即停止。使用[布线约束](references/constraint-routing.md)，并在布线/重新铺铜之后保留 G4 全板 DRC。
