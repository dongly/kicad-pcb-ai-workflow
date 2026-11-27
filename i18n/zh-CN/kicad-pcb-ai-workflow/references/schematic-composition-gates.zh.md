# 原理图构图：标题栏净空、电源符号与自适应图纸

本文是[拓扑优先规则](schematic-ai-layout-rules.md)与[原理图风格](schematic-style.md)的机器强制扩展。当前 `schematic_style.py` 检查**声明的、与当前文件绑定的几何**、原生电源符号的使用情况以及实际的图纸层次。它还提供**只读的预检页面建议**。它**不是**完整的自动符号/标签布线器、渲染文本几何提取器、标题栏解析器或通用 KiCad 布局优化器。任何检查都不能替代原生 XML/ERC 或 G1 人工视觉审查。

## 新绘制原理图的强制流程

1. 从当前器件卡与产品接口契约独立推导预期的组件/引脚/网络图。在放置符号前检查供电域一致性、NC 与变体。
2. 规划功能模块并估算渲染宽度/高度、文本、布线走廊与标题栏/注释预留区。调用只读的页面预检（`--plan-input`）。只要模块数大于一（或超出密度/连接数上限），**默认建议层次化根图加功能子图**；**单页加模块边框**仅在一模块设计或显式 `prefer_hierarchy=false` 时返回。该决定只是建议，不是修改原理图的指令。
3. 在放置任何符号之前，从**当前 KiCad 图框**预留页面边框、标题栏与文档区域，而不是硬编码的屏幕像素矩形。对于自定义 `.kicad_wks`，使用实际图框几何与页面渲染。截图右上角的坐标不是可靠的 KiCad 毫米坐标。
4. 按真实引脚拓扑与信号流放置，然后使用短正交局部导线。**每一条电源与地/回流网络都用原生 KiCad `power:` 库符号绘制——绝不用全局标签（也不用任何其他标签）。** 把 `VIN_RAW` 与 `VIN`、开关电源轨、PGND、AGND 以及各独立电源域保留为不同的电源符号。绝不把 `PWR_FLAG` 等同于正电源或地网络符号。对**每一条**非电源的跨图接口使用项目作用域的图纸引脚与层次标签。不要把全局标签当作默认的跨图连接方式：只有真正全板通用的网络且已列入 `composition.labels.allow_global_labels` 时才允许，其余情况门禁都会报告 `LABEL_POLICY.GLOBAL`。
5. 保存权威的 `01_WORKING/` 原理图，导出**实际的** KiCad PDF/SVG 与 XML 网表，并按下文创建与源绑定、按对象绑定的清单。必须包含全部可见字段与注释边界；保留其原生对象 UUID 清单。清单与视图通过 SHA-256 绑定到当前原理图版本。
6. 以选择加入的构图策略运行 `schematic_style.py`。任何检测到的标题栏或注释重叠、缺失符号、非法边框、缺失子页、过期证据或不安全几何都会阻断完成。其输出是**需要视觉审查的实测几何筛查**，绝不是自动完成全部渲染几何验收的声明。
6b. 运行 `python scripts/schematic_overlap.py /project --schematic root.kicad_sch`，对整个层次执行一次（每张图可加 `--layout SHEET=layout.json`，内容取自 Konnect `get_schematic_layout`，以启用符号对部分）。任何发现即阻断：KiCad ERC 不检查文本或图形重叠。重叠本身完全由脚本判定（`STROKE` 从 SVG 测试真实墨迹接触）；页面图像只用于可读性检查。
7. 运行既有的 G1 `static_review.py` 路径、独立的原生网表/ERC、有依据可溯的 AI 审查以及真正的工程师批准。拓扑失败回到 L0；外观重排不得改变原有网络。

## 只读的图纸规划

创建项目本地的 JSON 请求（示例如下），内容包括 KiCad 纸张类型、当前图框的受保护矩形（毫米）、各模块*估算的*包围尺寸，以及模块间连接数：

```json
{
  "schema_version": 1,
  "paper": "A4",
  "portrait": false,
  "protected_regions": [{"id": "title", "bbox_mm": [220, 165, 292, 207]}],
  "modules": [
    {"id": "input", "estimated_box_mm": [55, 40]},
    {"id": "controller", "estimated_box_mm": [80, 60]},
    {"id": "output", "estimated_box_mm": [60, 45]}
  ],
  "cross_module_connections": 5,
  "max_single_sheet_cross_connections": 12,
  "max_occupancy": 0.72,
  "routing_text_allowance": 1.35
}
```

运行 `python scripts/schematic_style.py /project --plan-input page-plan.json`。该命令**绝不编辑或创建 KiCad 项目**。`recommended_mode=hierarchical`（在 `prefer_hierarchy` 为 true——即默认值——且模块数大于一时为默认输出）表示在同一 KiCad 项目内建立根总览图与真实的子 `.kicad_sch` 文件，通过层次标签与作用域正确的图纸引脚连接——绝不通过全局标签。`recommended_mode=single` 表示单页加显式功能边框，仅预期用于单模块设计或已记录的 `prefer_hierarchy=false`。不存在「N 个元件就必须新开一页」的固定规则：即使选择了不用层次结构，密度与跨模块连接上限仍可能强制拆分。实测的视觉质量与层次结构仍必须在实际渲染输出上验证。

## 构图策略与证据清单

`schematic-style.json` 可以通过这个**项目专属**小节选择加入新的可执行检查：

```json
{
  "schema_version": 1,
  "pages": {},
  "composition": {
    "schema_version": 1,
    "required": true,
    "geometry": {
      "file": "03_REPORTS/g1-current/geometry.json",
      "sha256": "<sha256-of-exact-manifest>",
      "evidence_file": "03_REPORTS/g1-current/current-render.svg",
      "evidence_sha256": "<sha256-of-exact-current-render>",
      "locator": "Sheet 1 / entire current rendered page"
    },
    "power": {"rails": ["+24V", "+12V", "GND"], "allow_rail_labels": []},
    "labels": {
      "schema_version": 1,
      "prefer_hierarchy": true,
      "allow_global_labels": []
    },
    "partition": {
      "mode": "auto",
      "modules": [
        {"id": "input", "page": "01_WORKING/main.kicad_sch", "frame_uuid": "<actual-polyline-uuid>"},
        {"id": "core", "page": "01_WORKING/main.kicad_sch", "frame_uuid": "<actual-polyline-uuid>"}
      ],
      "max_occupancy": 0.75
    }
  }
}
```

**电源网络只用电源符号——绝不用标签。** 所有路径相对于项目根目录；电源轨列表必须从**实际的**供电图选出且必须完整（每一条电源与地/回流网络，包括 PGND/AGND 与开关电源轨）。如果 `+24V` 或 `+12V` 并非真实电源轨，不要照抄。列出的每条电源轨都必须以原生 `power:` 符号出现，并且**不得**用任何形式的标签接线——局部、层次或**全局**；`allow_rail_labels` 必须为空列表，非空列表会被拒绝。电源网络上的全局标签会报告为 `POWER_SYMBOL_POLICY.LABEL` 并阻断 G1。未列出的信号与 SW 网络仍遵循其常规的局部/层次标签规则。`PWR_FLAG` 必须依据 ERC 电源驱动语义添加，而不是作为装饰性替代。

**标签作用域（`composition.labels`）：** `prefer_hierarchy=true` 配合 `allow_global_labels` 列表，即项目声明层次结构是默认、全局标签是例外。该小节存在时，门禁会对每一条网络不在允许列表内的 `global_label` 报告 `LABEL_POLICY.GLOBAL`；检查记录还会列出每张图的 `global_label`/`hierarchical_label` 数量与图纸引脚数量，便于审查者确认跨图接口是否真的以端口形式建立。允许列表条目必须是真正全板通用的网络（每张图都需要、又不是电源符号的网络）；不要为了避免添加图纸引脚而把某个网络塞进列表。缺少 `labels` 小节的策略保持旧有行为，且不能声称该筛查已运行。

`geometry.json` 文件必须包含**所有可达的原理图图纸**，每张图都有当前 KiCad 文件 SHA、真实图纸尺寸、标题栏受保护矩形、其他预留区域，以及源文件可见对象 UUID 的完整清单。示例结构：

```json
{
  "schema_version": 1,
  "pages": {
    "01_WORKING/main.kicad_sch": {
      "schematic_sha256": "<sha256-of-current-schematic>",
      "sheet_mm": [297, 210],
      "complete_object_inventory": true,
      "visible_fields_included": true,
      "protected_regions": [
        {"id": "title", "kind": "title_block", "bbox_mm": [220, 165, 292, 207]},
        {"id": "notes", "kind": "notes", "bbox_mm": [5, 166, 120, 205]}
      ],
      "objects": [
        {"uuid": "<native-symbol-uuid>", "kind": "symbol", "bbox_mm": [35, 35, 68, 58]},
        {"uuid": "<native-wire-uuid>", "kind": "wire", "bbox_mm": [71, 42, 85, 44]},
        {"uuid": "<native-frame-uuid>", "kind": "polyline", "bbox_mm": [18, 16, 130, 102]}
      ]
    }
  }
}
```

示例中的对象清单是**故意不完整的**，不能当作验收工件。实际检查中它必须与当前原理图中每个相关对象的 UUID 一致，包括标签、文本、导线与边框实例；每个符号报告的包围盒必须覆盖可见的位号/值字段，而不只是图形本体。这些边界是**来自实际审查过的 KiCad 视图的测量值**，不是随意生成的元数据。文件哈希证明提交证据的一致性，**不**证明报告的框经过准确测量。渲染图像/PDF 仍需视觉审查。

`schematic_style.py` 在需要时返回 `TITLE_BLOCK_CLEAR`、`NOTES_REGION_CLEAR`、`SHEET_BORDER_CLEAR`、`POWER_SYMBOL_POLICY.MISSING`、`POWER_SYMBOL_POLICY.LABEL`、`LABEL_POLICY.GLOBAL`、`SHEET_PARTITION_POLICY.FRAME`、`SHEET_PARTITION_POLICY.MODE`、`SHEET_PARTITION_POLICY.CAPACITY` 或 `COMPOSITION.*` 发现。证据缺失绝不转化为 PASS。缺少 `composition` 的旧策略对既有项目仍可读取，但会报告 `NOT_CONFIGURED_LEGACY_REVIEW_REQUIRED`。新项目必须提供 composition 小节才能声称这些自动筛查已执行。

## 本次升级不实现的内容

- 不把任意自定义 `.kicad_wks` 标题栏提取为已验证的多边形或完整的原生字体包围盒。**当前必须提供独立的几何清单与视图。** 缺失/不确定的图框必须阻断自动视觉验收。
- 不自动生成层次图纸、原生符号、放置坐标或导线。Konnect 仍是**唯一的活动 EDA 写入者**；所有真实写入都需要已接受的能力与当前项目验证。
- 不推断 `power:` 符号的存在意味着电气拓扑正确。检查实际的 KiCad 导出网络与 ERC；审查真实的电源域与稳压器关系。
- 不声称布局筛查通过即代表原理图视觉精良或 G1 已批准。审查者必须检查页面与相关细节。

## 验证与升级兼容性

`schematic_style.audit()` 入口在绑定原理图风格策略时，于既有 G1 `static_review.prepare()` 路径下运行。静态审查包会把构图策略、几何清单与渲染视图连同哈希一起冻结进其证据基线。新项目策略选择加入完整构图检查；旧策略保持可用但不能声称执行过这些检查。这种分阶段采用避免了破坏旧项目或削弱既有批准门禁。

## 原生几何迁移边界

`geometry_mode=native_auto` 现在在预放置阶段推导真实的 KiCad 符号图形/引脚与当前已放置实例的几何，而不是要求手工编写的逐组件矩形。文本范围是保守的，不是字体精确值；G1 `schematic_style.py` 审计仍要求单独审查过的渲染视图/图框几何清单。仅靠预放置筛查不会授予 G1 批准。参见[原生符号几何](schematic-native-geometry.md)。


## 重叠与标签放置筛查（`schematic_overlap.py`）

只读。用法：`python scripts/schematic_overlap.py /project --schematic root.kicad_sch [--kicad-cli PATH] [--layout child.kicad_sch=layout.json ...] [--min-entry 2.54] [--output-dir DIR] [--png [--dpi 200]]`。传入顶层 `.kicad_sch`，而不是 `.kicad_pro`（项目导出可能以 "加载原理图失败" 失败）。退出码 `0` = 未发现任何问题，`2` = 有发现或 BLOCKED，绝不是批准。JSON 报告（`overlap-report.json`）列出各页的导线/标签/文本计数。

文本与图形分开检查，因为它们的证据不同。

| 部分 | 证据 | 发现 |
|---|---|---|
| `SHEET_FRAME` | `.kicad_sch` 图纸位置/尺寸 | `SHEET_FRAME.OVERLAP` 图纸边框相交；`SHEET_FRAME.OUTSIDE` 图纸超出页面 |
| `OUT_OF_FRAME` | `.kicad_sch` 坐标与纸张尺寸对比 | `OUT_OF_FRAME` 符号/标签/文本/结点/不连接标记的锚点及导线端点落在纸外 |
| `TEXT_PAIR` | `kicad-cli sch export svg` 不可见文本记录（x, y, textLength, font-size, anchor, rotate） | `TEXT_PAIR` 两个文本框重叠（两轴均 >0.15 mm）：标签压标签、位号压值、标签压引脚名 |
| `WIRE_TEXT` | SVG 文本框与导线段对比 | `WIRE_TEXT` 导线穿过文本（进入框内 >0.3 mm） |
| `SYMBOL_PAIR` | `--layout` 文件（Konnect `get_schematic_layout` 变换后的边界） | `SYMBOL_PAIR.OVERLAP` 组件本体相交；`SYMBOL_PAIR.WIRE` 导线穿过另一符号（>0.5 mm）。未提供 `--layout` 时该部分报告为未运行 |
| `STROKE` | SVG 矢量路径：字形折线、导线路径、未填充符号轮廓 | `STROKE.TEXT_LINE` 导线或符号轮廓描边穿过文本字形；`STROKE.TEXT_TEXT` 两个文本的字形相触；`STROKE.WIRE_SYMBOL` 导线穿过符号轮廓。终止于轮廓上的导线属于引脚连接，交给 ERC 处理 |
| `LABEL` | `.kicad_sch` 标签/导线/总线加 SVG 文本长度 | `LABEL.OFF_WIRE` 标签不在导线或总线上（落在裸引脚或悬空）；`LABEL.WIRE_END` 网络标签位于导线端点；`LABEL.TEXT_PAST_WIRE` 网络标签文字长于其前方导线；`LABEL.ENTRY_SHORT` 层次/全局标签的进入导线短于 `--min-entry`；`LABEL.DUPLICATE_NET` 同一张图纸上同一网络名出现两个及以上层次/全局标签（多出的标签会把导线段静默合并成一个网络，且 ERC 不告警） |

标签文字方向取自 SVG 导出：基线在 0°/180° 时向右延伸，90°/270° 时向上延伸，且 `justify right` 使文字终止于锚点。层次与全局标签在其锚点处连接，因此 `LABEL.WIRE_END` 只适用于网络标签。普通网络标签必须落在导线内部；层次与全局标签锚定在导线末端，且同一网络在每张图纸上只允许有一个（`LABEL.DUPLICATE_NET`）。

`TEXT_PAIR` 与 `WIRE_TEXT` 使用文本框，因此也会报告临界情况（文本框重叠、字形并未相触）；`STROKE` 回答的是确切问题——「画出的墨迹是否接触画出的墨迹」，判断导线穿文本应以它为准。填充区域（符号本体填充、结点圆点）不是描边，不参与比较。

剩余的人工工作：**可读性**。拥挤、长绕行与混乱布线不由任何脚本评判。**视觉兜底：** 加上 `--png --output-dir NEW_DIR`（需要 `python -m pip install pypdfium2`，Apache-2.0/BSD-3 许可，无系统依赖）。脚本用 kicad-cli 导出 PDF，并把每一页按 `--dpi` 栅格化为 `<stem>-page<N>.png`；打开每个 PNG 仅做可读性检查。肉眼审查对小文本不可靠，因此永远不能替代脚本各部分。
