# 原理图预布局：拓扑 → 空间预留 → 试布线 → 门禁

**范围：**在既有 KiCad 图纸页上为新元件做只读的候选位置规划，锚定于当前不可变的原生文件哈希。本模块实现一种保守且*有界*的预布局可行性筛查。使用 `geometry_mode=native_auto` 时，在任何新元件放置之前，直接从 `.kicad_sch` / `.kicad_sym` 提取原生 KiCad 符号图形、引脚、已放置的符号实例与当前图纸页实体。像素级精确的字体字形与自定义图框标题栏不会自动测量；KiCad 渲染复核保持独立。参见[原生几何](schematic-native-geometry.md)。

## 任何新符号放置之前必须遵循的顺序

**首选原生路径：**设置 `geometry_mode: "native_auto"`，并提供真实的 `lib_id`、值、位号与独立的引脚/网络图。以 KiCad 符号源原语取代手工编写的元件 `body_bbox_mm` 与引脚位置；图框保护区域策略每个项目声明一次。旧式手工测量的几何数据为兼容起见仍然可用。

1. 依据已批准的需求与厂商指南，独立建立**预期的精确引脚-网络图**。提供设计依据文件、SHA-256 与精确定位符；不得从生成的原理图推导预期连接。
2. 选定当前权威的 `01_WORKING/` 原理图与目标层级图纸页。先运行既有的图纸页规划器（`schematic_style.py --plan-input`），在尝试放置之前把过度拥挤的模块拆分到一条真实可达的子图纸页。
3. 把*当前*原理图的 UUID 清单与可视对象边界提取并核查到一份 `geometry.json` 清单文件中，并与已保存的 `.kicad_sch` 及导出的渲染视图绑定。内容包括所有可见符号字段、标签、既有导线、标注、真实的页面/图框禁布区与标题栏。**源文件哈希并不能证明几何测量正确。**自定义 `.kicad_wks` 与字体需要经独立核实的边界；缺少可信测量时，禁止自主放置。
4. 为每个新符号提供真实的库体边界、可见的 `Reference`/`Value` 字段边界、引脚挂接坐标与变换后的引出方向，并附一份以 SHA 锁定的几何来源文档。列出每个合法候选锚点，或给出可采纳的放置区域网格。为每个所需端点预留字段框、标签框与引脚引出走廊。电源/GND 连接需要规划原生电源符号，而非任意的文字替代。
5. 为所有新的非 NC 引脚提供完整显式的 `connections`（预期网络 + 源/目标 `[ref,pin]`）与标签预留。既有端点必须声明为 `fixed_ports`，并绑定到*当前*原理图中某个对象的 UUID。引脚/网络不匹配或缺少连接/标签时应予拒绝。
6. 运行有界的碰撞/间距预检与正交 A* **试布线**。它检查既有对象、字段/标签碰撞、标题栏/注释禁布区、逐引脚引出与预留布线走廊。候选搜索在显式预算处停止。它还检查保守的页面占用率以及可选的最大试布线长度/折弯限制，防止客观上过于拥挤或过于分散的候选布局。返回 `BLOCKED` 表示**所声明的这组候选尚未被证明可行**，而不是说有效的原理图不可能实现。
7. 当几何已验证且状态为 `PREPLACEMENT_FEASIBLE_FOR_DECLARED_GEOMETRY` 或 `PREPLACEMENT_GEOMETRY_READY_ROUTE_REVIEW_REQUIRED` 时，把不可变回执保存到既有的 **`03_REPORTS/`** 目录或工作项目之外，并在 Konnect 写入前立即重新校验 SHA 绑定的输入（无需重跑 A*）。已验证的布线路径只是*计划*，不是电气导线。宿主必须把实际的 Konnect 调用参数与精确的计划坐标和连接逐一比对；若所选工具无法兑现，则不得执行。**本 Skill 无法拦截来自其他 agent 的任意直接 MCP 工具调用。**
8. 通过经授权的 Konnect 后端**小批量**执行；立即回读实际的 UUID、引脚/网络、字段与已保存几何；运行原生 XML/ERC 与既有的 G1 几何/视觉复核。每个成功批次都会改变原理图 SHA 并使先前的回执失效。从最新的原生文件与渲染边界重新规划下一批次。未查明状态之前，不得重放失败/结果未知的写入。禁止静默回退到 pcbnew。

## 只读 CLI / 工作流命令

```bash
# Request, bound evidence, and receipt are inside the existing project reports area.
python scripts/workflow.py run /project --task schematic.preplacement_plan \
  --preplacement-request 03_REPORTS/preplacement/batch-01.json \
  --preplacement-receipt /project/03_REPORTS/preplacement/batch-01.receipt.json
# Run again just before the MCP call; catches stale geometry, plan or topology.
python scripts/workflow.py run /project --task schematic.preplacement_check \
  --preplacement-request 03_REPORTS/preplacement/batch-01.json \
  --preplacement-receipt /project/03_REPORTS/preplacement/batch-01.receipt.json
```

预检不得以 `--apply` 运行；它**不做任何 EDA 修改**。原始请求与被引用的源文件均为只读。回执文件必须尚不存在，且其父目录必须已经存在。若试布线失败或预算耗尽，规划器可能报告 `PREPLACEMENT_GEOMETRY_READY_ROUTE_REVIEW_REQUIRED`：此时仅允许有界的符号放置，绝不允许未经核实的布线。先尝试更换锚点/旋转，再考虑拆分图纸页；搜索耗尽并不能证明页面已满。

## Request v1 契约（节选，仅作示意）

```json
{
  "schema_version": 1,
  "schematic": "01_WORKING/main.kicad_sch",
  "schematic_sha256": "<current SHA-256>",
  "page": "01_WORKING/main.kicad_sch",
  "geometry_manifest": "03_REPORTS/current/geometry.json",
  "geometry_sha256": "<SHA-256>",
  "render_file": "03_REPORTS/current/schematic.svg",
  "render_sha256": "<SHA-256>",
  "topology_file": "03_REPORTS/expected/pin-net.json",
  "topology_sha256": "<SHA-256>",
  "grid_mm": 2.54,
  "clearance_mm": 1,
  "pin_escape_mm": 5.08,
  "wire_corridor_width_mm": 1,
  "max_candidate_positions": 120,
  "search_budget": 1000,
  "max_occupancy": 0.75,
  "max_trial_wire_length_mm": 100,
  "max_trial_wire_bends": 4,
  "power_rails": ["+3V3", "GND"],
  "symbols": [{
    "ref": "R1",
    "candidate_positions_mm": [[40.64, 53.34], [45.72, 53.34]],
    "rotations_deg": [0, 90],
    "geometry": {
      "source": {"file":"03_REPORTS/symbol-source.txt","sha256":"<SHA-256>","locator":"symbol reference & verified measurement"},
      "body_bbox_mm": [-4, -2, 4, 2],
      "fields": [{"name":"Reference","bbox_mm":[-2,-9,5,-6]}, {"name":"Value","bbox_mm":[-2,6,5,9]}],
      "pins": [{"number":"1","xy_mm":[-5,0],"outward":[-1,0],"net":"GND"},
               {"number":"2","xy_mm":[5,0],"outward":[1,0],"net":"SIG"}],
      "labels": [{"pin":"1","net":"GND","text":"GND","kind":"power","anchor_local_mm":[-10.08,0],"bbox_mm":[-23,-3,-10.08,3]}]
    }
  }],
  "fixed_ports": [{"id":"U1.3","net":"SIG","at_mm":[100,53.34],"source_uuid":"<current native UUID>"}],
  "connections": [{"net":"SIG","from":["R1","2"],"to":["@fixed","U1.3"]}]
}
```

`topology_file` 是一份独立编写的 JSON，包含 `schema_version:1`、`pins` 条目 `{"ref":"R1","pin":"1","net":"GND"}`，以及 `source:{"file":"...","sha256":"...","locator":"..."}`。每个新符号引脚必须**恰好出现一次**。每个电气引脚要么有显式连接，要么为局部/层级/全局/电源标签预留了空间；按 局部 → 层级（当网络离开本图纸页时）→ 全局（仅限白名单内的整板网络）的顺序选择 `kind`，使预布局计划永远不会把全局标签当成偷懒的跨图纸页默认手段；`NC` 必须经过刻意声明。非电源类标签的文字必须等于网络标识。其他图纸页保持不变；任意直接的 EDA 写入仍在本规划工具的触及范围之外。

## 工程局限与验收

- **无自动字体度量 / 图框解析器：**必须提供经核实的完整测量清单。算法基于已声明且已哈希的几何数据工作，而不是仅依赖原始 KiCad 绘图语义。
- **不提供虚假的布线证明：**本 A* 计划仅限单张图纸页内的正交路径；对交叉、总线语义与同网络共享结点采取保守处理。复杂层级、多单元符号、真正的 net-tie、引脚堆叠、部分布线与任意镜像文本需要专门验收或人工工程决策。
- **不隐藏 MCU 引脚变更：**旋转符号只改变其已声明的几何，从不改变源引脚编号或预期网络。应用后必须核实所有经过变换的引脚与实际电气连接。
- **禁止多写者并发：**继续使用同一个已注册的 `01_WORKING` 项目；每个当前修订版本只有一条 Konnect 写入路径。回执与完整检查分开保存；不要为每次放置新建一个 KiCad 项目。
- **必须完成的后端工作：**真实可信的符号与图框几何提取、逐工具的 Konnect `args ↔ planned placements` 实际强制比对，以及实机批次/回滚验收，均**未**由本只读规划器实现。在宣称完全自主的预布局与编辑之前，必须先在 Windows 上实现并验证这些能力。

[既有的构图/视觉门禁](schematic-composition-gates.md) · [拓扑优先规则](schematic-ai-layout-rules.md) · [原理图模块](module-schematic.md)。

## 两阶段更新：硬约束 vs. 软目标

硬约束：独立的引脚-网络契约、真实的标题栏/边框、经核实的符号与文本碰撞、合法的引脚引出、正确的电源/标签锚点。有界求解器现在会尝试全部四种正交旋转，除非符号限制了 `rotations_deg`；它会比较多个结果（默认 `max_scored_solutions=12`）。项目里的 `role=vertical_branch|decoupling|pullup|pulldown` 与 `preferred_rotations_deg` 可为有用的朝向设置优先级。软目标：占用率、试布线的存在性/长度/折弯数、求解器预算与留白。占用率按已声明占用矩形的并集估算，而不是会把预留标签重复计入的求和。当只有布线尚未证明时，允许一批有界的符号放置，但**绝不**自动接受布线。回执检查只对当前输入重新哈希；写入后的原生 XML/ERC 与视觉复核为强制项。可信的图框/文本几何仍由外部提供，而非自主提取。
