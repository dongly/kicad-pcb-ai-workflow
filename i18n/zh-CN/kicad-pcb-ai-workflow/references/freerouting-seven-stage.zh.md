# 使用 Freerouting 2.5.0 的七阶段 KiCad PCB 布线（R10 预览）

> **执行状态：**七阶段布线策略与验证已集成进 Skill。Freerouting 是*合格普通网络的首选候选生成器*，不是普遍适用于生产的已验收布线器。原生 KiCad/Konnect 写入方、G4 与制造闸门保持权威地位。不宣称任何真实 GUI/复杂板卡的端到端验收。

## 不可变更的阶段与责任归属

| 阶段 | 责任方 | 强制证据 / 停止条件 |
|---|---|---|
| 1. 全网络清单 | Skill + `routing_policy.py` | 所有真实 XML/KiCad 网络完成分类、两端点连接、设计电流/关键性，NC 单独列出；未知名称或类别不完整 = BLOCKED |
| 2. 设计规则 | Skill + 经验证的 Konnect/KiCad | 已批准的板厂叠层；生效的层/铜、NetClass、线宽/间距、过孔直径/钻孔、板边、keepout、H/V/45 偏好、SI/PI；**回读实际原生值** |
| 3. 关键布线 | KiCad（经已验收的 Konnect 工具/工程师） | 完成 P0–P2 布线与保护记录；验证锁定/既有走线与实际保存的板卡哈希；电源干线 >= 电流/热/压降表 + 0.254 mm；仅允许明确的焊盘/层/区域/长度受限颈缩 |
| 4. 普通自动布线 | Freerouting **v2.5.0** 外部 CLI | 把已保存的板卡导出为经审查的 Specctra DSN；DSN、外部 `.rules` 与 JAR 均哈希锁定；`-inc` 必须排除独立的 **GND、关键电源、RF、差分、时钟及其他受保护 NetClass**；输出 SES 仅为**候选** |
| 5. 导入与几何审计 | Konnect/KiCad + `routing_seven_stage.py audit-import` | **隔离候选**导入；保存/重载；相同的网络清单；保留关键铜层/对象 UUID；新增普通 H/V/45 线段、逐网络线宽、合法层、过孔几何/数量 |
| 6. 有界修复 | 已验收的 KiCad/Konnect 布线工具或工程师 | 新检查点、显式标识的剩余连接、已批准的最大迭代/时间/过孔、拆线（ripup）白名单。任何源哈希漂移、失败或需要放宽约束 = BLOCKED |
| 7. GND 先填充 → 过孔缝合 → 最终重新填充 → G4 | 已验收的 KiCad/Konnect + `audit-ground` + 原生 KiCad DRC + 工程师 | 先填充所有已批准的 GND 层；检查铜岛/接地焊盘连续性，必要时只放置明确批准的 GND 缝合过孔，再次填充，保存/重载，并在运行完整原生 DRC 之前**通过与源绑定的 DRC 前 GND 闸门**。任何残留的实际 GND 未连接错误或 G4 阻塞项都需要修复并重新填充 |

**不要在 G3 摆放阶段要求零未连接或整板 DRC**。G3 在真实 Konnect 保存与位置回读之后仍仅限摆放。只有阶段 7 会调用最终的原生整板 DRC，且是在初次铺铜、可能的缝合与最终重新填充**之后**。

## 实际用法

1. 使用现有的 `pcb.fab_preview` / `pcb.fab_confirm`，随后通过实际已验收的 KiCad/Konnect 写入方应用已批准的设置，并回读生效规则。使用现有的 `pcb.routing_preflight` 与布线策略（以实际哈希绑定的板卡、XML 网表、叠层、规则、受保护对象输入做全网络清单）。
2. 把*已保存*的 KiCad PCB 导出为 DSN；创建经过独立审计的 `netclass-map.json`。一个名字看起来合理的 JSON 文件并不是实际 KiCad NetClass 成员关系的证明；操作者必须在调用 Freerouting 之前验证生效的原生分配。
3. 创建阶段规划配置并运行 `routing_seven_stage.py plan`。它复用现有的全网络约束校验器，并拒绝把受保护/GND 网络与普通网络混在同一 NetClass 中的做法。
4. 执行关键网络的原生布线；保存/重载并采集保护/哈希证据。在这些编辑**之后**重新导出 DSN，重新绑定全部哈希，并在 Freerouting 之前重新规划。
5. 以确切的源哈希、排除项、经验证的 JAR 和有界运行来调用 `freerouting_adapter.py`；适配器只生成 SES，不导入也不批准。
6. 通过已验收的 Konnect 命令把 SES 导入*另一个*已保存的 KiCad 候选，保存/重载。对实际的导入前后板卡哈希使用 `audit-import`；修复一切被阻塞的内容。绝不为让检查通过而覆写原始 PCB。
7. 重新填充 GND 并再次保存。运行完整的原生 KiCad DRC，采集机器可读的 JSON；对检查点/最终板卡与 DRC 使用 `audit-final`。**成功仍意味着等待 G4 工程师批准，而不是 Gerber 就绪。**

### 规划示例（`route-plan-config.json`）

```json
{
  "schema_version": 1,
  "stage": "plan",
  "routing_request": "routing-request.json",
  "dsn": {"file":"route/board.dsn","sha256":"<actual 64-hex source SHA>"},
  "netclass_map": {"file":"route/netclass-map.json","sha256":"<actual 64-hex map SHA>"}
}
```

所引用的原生映射为：

```json
{
  "schema_version": 1,
  "board_sha256": "<routing-request inputs.board.sha256>",
  "dsn_sha256": "<actual DSN SHA>",
  "net_to_class": {
    "GND": "GND",
    "USB_D+": "DIFF_CRITICAL",
    "GPIO1": "SIGNAL"
  }
}
```

`net_to_class` 必须包含该具体项目中**每一条**已分类网络与实际 NetClass。受保护网络与普通网络不得共用一个 Freerouting 类别。不得为生产布线手写一个未经验证的映射。

### 审查示例（`route-import-config.json`）

```json
{
  "schema_version": 1,
  "stage": "import",
  "before_board": {"file":"checkpoints/pre-freerouting.kicad_pcb","sha256":"<source hash>"},
  "after_board": {"file":"candidates/imported.kicad_pcb","sha256":"<candidate hash>"},
  "networks": {
    "GPIO1": {
      "minimum_width_mm": 0.20,
      "allowed_layers": ["F.Cu","B.Cu"],
      "min_via_diameter_mm": 0.30,
      "min_via_drill_mm": 0.20
    }
  },
  "protected_nets": ["GND","USB_D+"],
  "gnd_nets": ["GND"],
  "protected_object_uuids": ["<actual saved locked object UUID>"],
  "max_new_vias": 10
}
```

对于最终审计，使用 `"stage":"final"`，并添加实际的 DRC 前 `"gnd_completion_report":{"file":"reports/ground-pre-drc.json","sha256":"<actual gate report hash>"}`、`"native_drc_board_sha256":"<post-DRC saved board SHA>"`、`"zone_refill_completed":true` 与 `"native_drc_json":{"file":"reports/final-drc.json","sha256":"<actual DRC report hash>"}`。`before_board` 必须绑定最终 GND 重新填充之后保存的板卡。`after_board` 绑定 KiCad DRC 之后保存的板卡。仅凭布尔值**不能**授权 DRC/G4。最终板卡必须有真实填充的 GND 覆铜区，且报告必须包含 `violations` 与 `unconnected_items` 数组。这份只读审计本身不认证 DRC 工具，也不计算电流/热、差分时序、特性阻抗、回流路径或工程师验收。**绝不要把用户提供的布尔证据当作实际原生操作的替代品。**

### 命令

```bash
python scripts/routing_seven_stage.py plan PROJECT --config route-plan-config.json
python scripts/freerouting_adapter.py --dsn route/board.dsn \
  --expected-dsn-sha256 ACTUAL_DSN_SHA --jar approved/freerouting-2.5.0.jar \
  --expected-jar-sha256 APPROVED_JAR_SHA \
  --exclude-netclasses GND,DIFF_CRITICAL,RF_CRITICAL,POWER_CRITICAL \
  --netclass-map route/netclass-map.json \
  --expected-netclass-map-sha256 APPROVED_NATIVE_MAP_SHA \
  --output-dir NEW_CANDIDATE --passes 20
# After reviewing preview, repeat the same command with --apply.
# Import SES via accepted KiCad/Konnect operation into isolated candidate.
python scripts/routing_seven_stage.py audit-import PROJECT --config route-import-config.json
# After import/repairs, FIRST fill GND, review and add APPROVED vias only if needed,
# REFILL GND, save/reload four source-bound candidate PCB checkpoints.
python scripts/routing_seven_stage.py audit-ground PROJECT --config ground-config.json --output reports/ground-pre-drc.json
# Do not do full G4 DRC until audit-ground succeeds:
kicad-cli pcb drc --refill-zones --save-board --format json --output reports/final-drc.json PROJECT/checkpoints/final-refilled.kicad_pcb
python scripts/routing_seven_stage.py audit-final PROJECT --config route-final-config.json
```

如果存在已批准的 Freerouting `.rules`，则传入 `--rules-file FILE --expected-rules-sha256 HASH`；悄悄自动发现的相邻规则文件会被阻塞。使用实际可用的 NetClass 名称：示例**不是**自动类别。

[完整的 GND 先铺铜/缝合/重新填充/DRC 证据契约](gnd-before-drc.md)在完整 DRC 之前是强制性的。

同一套规划/审计接口还注册为 `workflow.py --task pcb.routing_seven_plan`、`pcb.routing_import_audit`、`pcb.ground_plane_audit` 与 `pcb.routing_final_audit`，并配合 `--routing-stage-config` 使用。`pcb.freerouting_candidate` 任务只调用离线 Freerouting 适配器；已验收的 Konnect 原生导入仍是单独发现并授权的操作。

## Freerouting 2.5.0 扇出（fanout）与优化安全性

原生 KiCad 10.0.8 + Freerouting 2.5.0 的回归测试表明：即使 GND 已正确分配到生效的 GND NetClass 并指定了 -inc GND，布线器初始的 SMD 扇出阶段仍可能添加 GND 铜。因此，已批准的 R10 普通网络 CLI 适配器显式设置 --router.fanout.enabled=false 与 --router.optimizer.enabled=false。只保留受限的普通自动布线批次。这可能会降低非常密集板卡上的布线完成度；在没有单独的版本固定原生受保护对象测试的情况下，绝不重新启用扇出或优化器。如果设计在这些保护下无法完成，则返回 BLOCKED/移交工程师，而不是悄悄布 GND。

真实的 KiCad SES 导入仍必须证明：在保存并重载后的板卡中没有新增/移除的 GND 走线/过孔或受保护铜层。

## 强制的原生 NetClass 成员关系证明（R10 受保护 GND 修复）

一份 DSN 文件可以声明一个名为 GND 的类别，却不把实际的 GND 网络放入该类别。特别是，无头 KiCad 10 的 SWIG LoadBoard() 只加载 PCB，不加载独立的 .kicad_pro 网络设置；朴素的 ExportSpecctraDSN() 可能发出 GND 声明却把 GND 放进 kicad_default。Freerouting 的 -inc GND 只作用于实际导入的生效类别。R10 现在检查真实 DSN network/class 块内部的直接成员关系，而不是仅对类别名做正则匹配。被分配到非排除类别的 GND 网络即 BLOCKED。

在配合 --apply 使用适配器之前，从具备项目感知的编辑器独立读取实际 KiCad NetClass 成员关系，并提供完整的与源/DSN 绑定的映射：

~~~json
{
  "schema_version": 1,
  "board_sha256": "actual saved KiCad board SHA-256",
  "dsn_sha256": "actual exported DSN SHA-256",
  "net_to_class": {"GND": "GND", "GPIO": "SIGNAL"}
}
~~~

通过 --netclass-map 与 --expected-netclass-map-sha256 传入该映射及其 SHA-256。每个 DSN 类别成员都必须与原生映射完全一致，且 DSN 哈希必须匹配；适配器不推断也不修复项目规则，必须拒绝不一致。使用原生的具备项目感知的 Konnect DSN 导出与独立回读。隔离的原生测试可以在其真正的 KiCad ExportSpecctraDSN() 调用之前，显式地把 .kicad_pro 设置恢复到一个一次性的无头板卡中，但这并不是通过 pcbnew 写用户活跃 PCB 的授权。

SES 导入之后，把保存板卡的走线、过孔与受保护铜层（包括 GND）与原始板卡对比。仅凭一份干净的 DSN 映射和一次成功的 SES 生成**本身**永远无法关闭 G4。

## 重要限制与测试闸门

- Freerouting 的 `-is prioritized` **不能**保证用户定义的 P0/P1/P2 固定网络顺序。先用单独的已验证操作给关键网络布线并保护其铜层，然后再导出仅含普通网络的 DSN。
- `-inc` 排除的是 **NetClass**，而不是原始网络名；类别仅存在并不保证网络成员关系。
- Freerouting 的 `automatic_neckdown` 与优化器行为不是已批准的替代方案，不能替代逐焊盘、有源可查、带受限长度/热检查的局部电源引出。
- `routing_seven_stage.py` 解析器检查新增的普通直线段线宽、H/V/45、允许层、过孔预算/直径、受保护网络与 UUID；其他原生/自定义/热/SI 规则仍需独立签核。
- 不要仅凭软件测试夹具宣称验收。只有在 Windows KiCad 10.0.8、已验收的 Konnect 工具、Freerouting 2.5.0 以及多样的代表性 2/4 层板卡全部通过实际的保存/重载/DRC 与几何审计之后，才将自动执行晋升为默认。
- 一份生成的 SES 或零违规 JSON 本身绝不授权制造，也不能绕过 G4。最终状态保持 `EXPORTED_NOT_RELEASED`，等待全部生产发布要求。

参考：[Freerouting 2.5.0 CLI](https://github.com/freerouting/freerouting/blob/v2.5.0/docs/command_line_arguments.md)、[Freerouting 2.5.0 设置](https://github.com/freerouting/freerouting/blob/v2.5.0/docs/settings.md)、[KiCad PCB 编辑器规则](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html)。
