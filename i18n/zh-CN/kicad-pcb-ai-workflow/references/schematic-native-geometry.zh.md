# 原生 KiCad 符号几何 — 预布局前必读

**主要来源：**KiCad 原生 `.kicad_sch` 内嵌的 `lib_symbols` 与 `.kicad_sym` 文件。其中包含真实的符号原语、引脚连接坐标/方向与字段位置。完整符号没有通用的宽/高存储属性：本 Skill 从库的图形原语计算包围矩形。它**绝不能凭空捏造符号尺寸**。

## 自动来源查找

1. **既有/内嵌：**从所选 `.kicad_sch` 的 `lib_symbols` 缓存加载确切的符号定义（遵循当前已保存的符号修订版本）。
2. **新的、尚未缓存：**解析匹配的项目 `sym-lib-table`；否则退回已安装的 `KICAD10_SYMBOL_DIR`/`KICAD9_SYMBOL_DIR`/`KICAD_SYMBOL_DIR`、本地项目库或标准 KiCad 安装目录。用户可以为自定义/私有库显式传入一个既有 `.kicad_sym`。无需网络、下载或测试板。
3. **继承/多单元：**解析 `(extends ...)`，选择所请求的 `(unit ...)` 与图形样式，并纳入共享的 unit-0 图形与引脚。若所需原生库或某种图形类型不可用，报告哪个符号缺数据，不得凭空捏造一个方框。

提取器计算矩形、圆、折线范围、三点圆弧（含极值点）、三次贝塞尔曲线极值点、引脚杆与引脚名称/编号。KiCad 原生库使用 **+Y 向上**；图纸页使用 **+Y 向下**。实例应用 0/90/180/270 度旋转与 `mirror x|y`；引脚端点与引出方向按同一映射变换。导线要使用精确的 KiCad 引脚端点，绝不使用近似中心点。

## 实用的只读命令

```bash
# Query dimensions and pins BEFORE placing Device:R. Looks up the embedded
# definition or the installed/project symbol library automatically.
python scripts/schematic_native_geometry.py symbol /project \
  --schematic 01_WORKING/main.kicad_sch --lib-id Device:R

# Optional offline geometry snapshot of already placed objects. Only the
# worksheet protected-region contract (not a per-symbol bounding list) is needed.
python scripts/schematic_native_geometry.py snapshot /project \
  --schematic 01_WORKING/main.kicad_sch \
  --protected 03_REPORTS/worksheet-regions.json \
  --output /project/03_REPORTS/native-geometry.json
```

一次性图框区域示例（取值必须来自实际项目图框或经审阅的 KiCad SVG；不要把任意坐标复制到生产项目）：

```json
{
  "*": [
    {"id":"project-title", "kind":"title_block", "bbox_mm":[220,165,292,207]}
  ]
}
```

对规划器，请使用 **`geometry_mode: "native_auto"`** 与 **`protected_regions_by_page`**，而不是 `geometry_manifest`、`geometry_sha256`、`render_file` 以及每个符号上由调用方编写的 `geometry` 字段：

```json
{
  "schema_version": 1,
  "geometry_mode": "native_auto",
  "schematic": "01_WORKING/main.kicad_sch",
  "schematic_sha256": "<sha256 of current schematic>",
  "page": "01_WORKING/main.kicad_sch",
  "protected_regions_by_page": {
    "*": [{"id":"project-title", "kind":"title_block", "bbox_mm":[220,165,292,207]}]
  },
  "topology_file": "03_REPORTS/expected-pin-nets.json",
  "topology_sha256": "<sha256 of independently approved topology>",
  "clearance_mm": 1,
  "symbols": [
    {"ref":"R1", "lib_id":"Device:R", "value":"10k", "unit":1,
     "candidate_positions_mm":[[50.8,63.5],[55.88,63.5]],
     "rotations_deg":[0,90,180,270],
     "labels":[{"pin":"1","kind":"local"}]}
  ]
}
```

这只是一个**示意性的部分请求**；规划之前仍需提供常规的独立引脚-网络契约、连接清单、布线/标签设置与真实的图纸页禁布区。每个元件所需的输入是 **KiCad 库标识、网络拓扑以及可选的实际显示 Value / 放置区域**——而不是猜测的体/引脚几何。未指定的 `value` 会继承原生符号库的 `Value` 属性；`lib_id` 本身始终是不参与渲染的查找元数据。

## 哪些精确、哪些不精确

| 量 | 证据/精度 |
|---|---|
| 受支持的符号绘图原语、坐标、引脚端点 | 源自原生源文件，经几何计算 |
| `lib_id`（如 `Device:R`） | **仅查找元数据；绝不是可见文本对象，也绝不是碰撞宽度的来源。**标识符长度变化不得改变放置边界。 |
| 实际显示的 `Reference`（`R1`）、`Value`（`10k`）与其他可见文本 | 占用估算计入其显示文本，并采用保守字体估计；隐藏属性不构成障碍。若预期实例未声明 `value`，则继承**原生 KiCad 库的 `Value` 字段**，绝不继承 `lib_id` 或其后缀。 |
| 实际放置实例的原点/旋转/镜像 | 原生 `.kicad_sch` |
| 既有 Reference/Value 文本位置、字号、可见/隐藏标志 | 原生 `.kicad_sch` 元数据 |
| KiCad 渲染字体的**精确字形轮廓**，尤其是复杂 Unicode | **不由文本尺寸元数据保证。**写入后复核时使用保守边界与真实的 KiCad SVG/PDF |
| 自定义图框标题栏范围 | 必须来自实际的 `.kicad_wks` / 渲染图框且只配置一次；**不得从符号库推断** |
| 电气正确性 | **不由几何决定。**仍须运行原生 XML 网表/ERC 与 G1 复核 |

### 执行契约

- 原生提取器与 `schematic.preplacement_plan` 是只读的。规划器在运行时解析真实的符号库来源，并对每个源文件做哈希。
- `schematic.preplacement_check` 校验请求、符号、源哈希与求解器代码哈希；对未变更的批次不重跑符号几何提取或 A*。
- 规划成功的锚点**不**等于已验证的 KiCad 编辑。Konnect 必须写入确切的库 ID、单元、朝向、引脚/网络身份、字段/标签位置与实际项目修订版本；推进之前，先将其保存后的回读与计划比对。
- 意外的 KiCad 字体/文本渲染、不受支持的图形原语、第三方库漂移、并发的未保存编辑器变更或缺失的图框证据，都**不能被静默批准**。真实编辑之后只重算受影响的模块/页面。未知的 A* 结果仍仅作建议，不得据此断言图纸页放不下。

本模块不能替代 KiCad 的原生渲染器、自定义图框解析器或集成的 Konnect 原理图事务性回写。在宣称原理图生成达到生产可用之前，必须在目标 Windows/KiCad/Konnect 栈上另行完成完整的实机端到端验收。
