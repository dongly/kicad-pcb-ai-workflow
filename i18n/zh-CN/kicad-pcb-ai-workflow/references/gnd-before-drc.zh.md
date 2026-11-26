# R10 — GND 先铺铜 → 获批缝合过孔 → 重填铜 → 完整原生 DRC / G4

**强制顺序。** GND 被有意排除在普通 Freerouting 走线布线之外，通常通过获批准的
铜区/平面几何连接。**绝不能在未填充的板卡上运行最终的整板连通性/DRC 门禁**，也不得
把预期的 GND 飞线当作最终布线失败。布局前的 Board Setup 规则检查、布局/courtyard
检查与源文件审计仍可更早运行；它们不是 G4 整板 DRC。

## KiCad 10 原生保存文件兼容性（R10 修复）

KiCad 10 的原生 SaveBoard / `kicad-cli pcb drc --refill-zones --save-board`
可以使用 `(net "GND")`、`(net "+3V3")` 名称式网络引用，且**没有**
旧版 `(net 2 "GND")` 的顶层数字网络表。不能仅因缺少该表就断言
GND 丢失。必须从真实焊盘网络名重建并核对每条铜线、过孔和 Zone
的实际网络身份；名称不匹配、无法由焊盘确认的网络、重复/冲突编号
仍然 **BLOCKED**，不能根据 `(net_name "GND")` 等装饰性标签猜测。

KiCad 10 保存还会添加空白属性、将 `.6` 规范化为 `0.6`，
并重排焊盘的 F.Mask/F.Paste 列表。前后板比较应采用**同一物理/电气语义**
（UUID、位置、旋转、焊盘尺寸与孔径、实际网络、层集合、已有线/孔几何），
而不是逐字比较不影响电气的序列化格式。未经批准的真实器件移动、
新 GND 走线、过孔改径或网络更改依然阻断。

## 实际执行（独立的 KiCad/Konnect 保存/回读快照）

1. **布线之后** — 完成并核验获允许的 P0–P3 非 GND 走线。保留已保存的
   `pre_ground_board` 检查点、全部受保护铜皮与网络成员关系。
2. **首次真实 GND 填充** — 使用获认可的 KiCad/Konnect 操作创建并填充真实 GND 铜区，
   **只能放在显式批准的承载地铜层上**（例如双层板的 F.Cu 与 B.Cu，或多层板中显式
   指定的 In*.Cu 地层）。检查平面优先级、禁布区、间距与热焊盘连接，并核对每层的铜区
   定义。当前未锚定的平面可能暂时**没有填充多边形**，因为 KiCad 会移除孤立铜岛；
   只有在随后执行获批缝合、且**最终**重填在每个必需层上都呈现真实 GND 铜皮时，这种
   情况才可接受。保存、重载并对板卡做哈希，记为 `first_filled_board`。铜区边框不等于
   填充。
3. **审查 GND 拓扑** — 检查焊盘、分割/孤立铜岛、参考回流连续性，以及预期层上实际
   存在地铜皮的位置。铜区填充可能移除悬浮铜岛。必须判定是否确实需要任何缝合过孔；
   仅凭外观开路状的补丁并不足够。获批准的过孔需要有接地端点、合法的过孔类型以及相关
   层上的真实铜皮。缝合过孔不会自动使每块铜皮区域连续；没有原生连通性与工程审查就
   没有证明。
4. **只允许必需且获批准的缝合过孔** — 过孔放置有界且显式（UUID、网络 GND、X/Y、
   实际过孔跨越层、获批 GND 接触层、直径、钻孔、用途）。检查铜皮到孔/过孔到焊盘的
   间距、钻孔/焊环（annular ring）/板边/禁布区、信号/回流间距、天线禁布、层跨越，
   以及适用时的电流/发热/EMC。使用获认可的唯一 KiCad/Konnect 写入者；保存/重载
   `stitched_board`。禁止任意批量放置过孔。
5. **缝合之后再填充** — 对所有修改过的 GND 铜区再次填充，保存、重载并对
   `final_refilled_board` 做哈希。凡对过孔、铜皮、铜区、器件位置、间距或板卡几何的
   任何编辑之后，都要重复此步骤。
6. **DRC 前的地平面门禁** — 对那四个以哈希绑定的实际 PCB 文件运行
   `routing_seven_stage.py audit-ground`。它检查每个预期层的 GND 铜区定义，显式记录
   首次填充时任何未锚定的层，并要求：每个获批 GND 层上都有**真实的最终填充多边形**、
   非地走线/封装保持不变，以及恰好获批且尺寸正确的 GND 缝合过孔。生成新的不可变
   `GROUND_FILLED_STITCHING_AUDITED_READY_FOR_NATIVE_DRC` JSON 报告。
   **这是一个只读的几何/快照门禁，不是连通性证明，也不是 G4 通过。**
7. **只有此时才运行完整 KiCad DRC** — 在隔离保存的候选板上运行：
   `kicad-cli pcb drc --refill-zones --save-board --format json --output reports/final-drc.json checkpoints/after-refill.kicad_pcb`
   KiCad 10 的 CLI 用 `--refill-zones` 在 DRC **之前**重新填充；只有同时指定
   `--save-board` 时才会持久化该填充。重新打开这份 DRC 后的板卡，连同 JSON 报告一起
   做哈希，包括 `violations` 与 `unconnected_items` 两部分。仅在未填充的布线候选上
   运行的 DRC 不算 G4。
8. **最终审计与 G4** — 运行 `audit-final`：`before_board` 绑定地平面门禁的最终重填
   板卡，`after_board` 绑定 DRC 后已保存的板卡，提供 `gnd_completion_report` 绑定、
   与 DRC 后板卡一致的 `native_drc_board_sha256`、`native_drc_json` 绑定以及
   `zone_refill_completed:true`。原生错误、仍存在的 GND 未连接项、无效平面铜岛或
   失败的工程回流路径都会阻断 G4。工程师分别签核 SI/PI、热、DFX 与制造。没有发布
   门禁时，Gerber 保持 `EXPORTED_NOT_RELEASED` 状态。

## GND 阶段配置示例

把所有占位哈希替换为**真实已保存项目文件**的 SHA-256。如果没有必要放置缝合过孔，
`approved_stitching_vias` 必须为 `[]`，且实际新增的 GND 过孔数量也必须为零。

~~~json
{
  "schema_version": 1,
  "stage": "ground",
  "pre_ground_board": {"file":"checkpoints/routed.kicad_pcb", "sha256":"<actual-sha>"},
  "first_filled_board": {"file":"checkpoints/first-fill.kicad_pcb", "sha256":"<actual-sha>"},
  "stitched_board": {"file":"checkpoints/stitched.kicad_pcb", "sha256":"<actual-sha>"},
  "final_refilled_board": {"file":"checkpoints/final-refilled.kicad_pcb", "sha256":"<actual-sha>"},
  "gnd_zone_layers": {"GND":["F.Cu","B.Cu"]},
  "copper_layer_stack": ["F.Cu","B.Cu"],
  "approved_stitching_vias": [
    {"uuid":"<actual-via-uuid>", "net":"GND",
     "at_mm":[12.0,8.0], "layers":["F.Cu","B.Cu"],
     "ground_contact_layers":["F.Cu","B.Cu"],
     "min_diameter_mm":0.6, "min_drill_mm":0.3,
     "purpose":"Bridge verified separate ground copper regions"}
  ]
}
~~~

## 命令

~~~bash
# After the accepted KiCad/Konnect writer has physically filled/stitched/refilled:
python scripts/routing_seven_stage.py audit-ground PROJECT \
  --config ground-config.json --output reports/ground-pre-drc.json
# BLOCKED means do not execute the following full-board DRC as final G4.
kicad-cli pcb drc --refill-zones --save-board --format json \
  --output reports/final-drc.json PROJECT/checkpoints/final-refilled.kicad_pcb
# Reopen saved post-DRC PCB and bind all source/output hashes in final config:
python scripts/routing_seven_stage.py audit-final PROJECT --config final-config.json
~~~

通过 `workflow.py` 使用任务 `pcb.ground_plane_audit`，附带
`--routing-stage-config ground-config.json --ground-audit-output reports/ground-pre-drc.json`；
之后再用最终配置运行 `pcb.routing_final_audit`。

**局限：** 只读快照审计器无法仅凭读取 JSON 回执来认证原生工具，也无法计算孔壁镀铜
接触、悬浮铜皮/铜岛邻接、热/EMC、特性阻抗或三维回流连续性。用户/工程师必须验证
获认可的原生调用，并检查实际的 KiCad DRC 与平面/回流路径结果。不包含完整 GND 铜区的
真实 KiCad/Freerouting *仅布线*夹具，不得运行或报告最终整板 DRC。

参考：KiCad 10 PCB Editor 铜区填充文档与 KiCad 10 CLI 的
`pcb drc --refill-zones --save-board` 命令。
