# Freerouting 优先布线候选：分阶段工程契约（R10 预览）

**状态：**实现提案加部分 CLI fail-closed 防护；尚无端到端验收或默认晋升。**不要把当前分支当作具备生产资格的布线器。**

## 决策：确定性自动布线器、AI 规划器与独立的 KiCad 权威

对于普通网络，优先采用*合格的* Freerouting 2.5.0 DSN/SES 候选，而不是构建一个由 LLM 操作的多网络 A* 铜层引擎。保持 Konnect 作为唯一的活跃 KiCad 写入方与回读工具，并以原生 KiCad 检查作为最终权威。离线网格 A* 仍仅作为有界的研究/诊断候选；它**不是**生产回退手段。对于关键走线，由 Konnect 执行已批准的原生走线操作，或由用户手动布线并接受审查。

在存在同等的、与源绑定的 E2E 证据之前，Freerouting **DSN** 路线优先于实验性的 JSON/API 路线。存在插件或 SES 文件并不构成板卡合规的证据。

## 七阶段布线编排

1. **整板网络清单**：对每一条真实 XML/KiCad 网络分类；绑定网络名、引脚/焊盘端点、实际 NetClass 分配与受保护网络。未知名称即 BLOCKED。使用 `constraint-routing.md` 中的全网络请求闸门。
2. **规则与 GND 策略**：应用经确认的板厂叠层、铜宽/间距、钻孔/过孔几何、层限制、板边、keepout，以及实际生效的 KiCad 规则。为最终重新填充准备好连续的 GND 覆铜区；把专用 GND NetClass 从*走线*自动布线中排除，但不得抑制 GND 短回流/缝合或电气连接性验证。专用 NetClass 必须由 KiCad 与导出的 DSN 共同证明；名为 GND 的类别并不能证明 GND 网络属于它。
3. **关键优先几何**：保护固定封装、锁定的既有走线、天线/模拟/RF、高速差分、长度敏感、开关环路、Kelvin 与大电流分支。特殊信号在原生 KiCad/Konnect 中布线，并带各自的工程验收。NetClass `-inc` 排除对普通网络批次是强制性的，且必须对照实际 KiCad 网络成员关系进行审查。
4. **普通候选**：从真实、已保存的 KiCad PCB 将 DSN 导出到隔离检查点。绑定确切的 DSN SHA、可选的经审查 Freerouting `.rules` SHA 以及经验证的 2.5.0 JAR SHA。以有界的 `-mp`/超时运行，使用 `-inc` 排除类别，并使用全新的输出目录。适配器拒绝未批准的相邻 `.rules`；它自身绝不导入 SES。
5. **隔离导入与回读**：只使用已批准的 Konnect 能力/KiCad 编辑器把 `.ses` 导入一个单独的候选，保存、重载，并对比网络、封装、走线、过孔、覆铜区与受保护对象 UUID。仅凭成功退出码/SES 无法满足本阶段。保留源 SHA 与一个非覆盖式的证据目录。
6. **电气修复与覆铜**：用有界且已验收的原生工具修复剩余的普通飞线；不得悄悄放宽网络/制造规则。电源干线尺寸依据实际铜厚、压降、温升与用户参考线宽**外加 0.254 mm** 来确定，并*向上*取整。只有在具名网络/焊盘/区域/层、最大长度、经验证的热/电流/压降以及原生规则范围齐备时，才允许范围化的焊盘引出颈缩。Freerouting 2.5.0 的 `-inc`/DSN 规则**不能**证明它能自动强制执行这种分段局部颈缩。填充所有已授权的 GND 覆铜区；确认实际的焊盘到覆铜区连接性与回流连续性。
7. **G4 闸门与发布**：填充后完成原生 KiCad DRC、全部必需网络连接性、原生网表一致性、保存/重载几何、规则命中审计，以及按适用情况进行的受控阻抗/差分偏斜/时序/电源/热/爬电审查。**任何不受支持/过时/缺失的规则、铜层保护丢失或 DRC 阻塞项都意味着 BLOCKED**，而不是悄悄接受一份 SES。在单独要求的发布闸门通过之前，制造状态保持 EXPORTED_NOT_RELEASED。

## 规则放置与实际能力边界

| 要求 | 最佳强制执行点 | Freerouting 2.5.0 的处理方式 |
|---|---|---|
| 线宽/间距/NetClass/层限制/过孔 | KiCad Board Setup、已批准的原生生效规则、DSN、经审查的 `.rules` | 可消费受支持的 Specctra/FreeRouting 规则；须验证最终实际线宽/间距与层 |
| GND 平面与参考回流 | KiCad 覆铜区策略 + 受保护 NetClass + 填充后检查 | 用 `-inc` 排除走线布线的 GND NetClass；`-inc` 作用于**类别，而非名称** |
| H/V/45 一般信号形状 | 最终几何分析器与已批准的布线器专属选项 | 不要仅凭 DSN 声称严格的 45 度输出；须检查实际经 SES 导入的走线 |
| 电源干线 +0.254 mm | 外部电源线宽闸门、已批准的 netclass 与 KiCad 原生几何审计 | 不要假设 `.rules` 会应用任意的逐线段电气尺寸 |
| 细间距范围化颈缩 | KiCad 自定义规则 + 原生焊盘/走线几何与热审计 | 使用已批准的 Konnect 干预；没有自动的局部变线宽保证 |
| USB/MIPI/RF 受控阻抗与长度/偏斜 | KiCad 设计规则与专门的 SI/PI 审查 | 初期按受保护/关键对待；单独布线 |
| 元件 courtyard、keepout、锁定铜层 | KiCad 实际对象几何与受保护对象 diff | 并非每个装配/courtyard 或自定义规则条件都能在 DSN 转换中保留 |
| 完整的制造/热/信号完整性签核 | 原生 KiCad + 电气分析 + 工程师闸门 | 即使布线器 DRC 存在，也不交付此项 |

**版本区分：**在 Freerouting *v2.5.0* CLI 文档中，受支持的输入是 DSN/SES/FreeRouting `.rules`，`-inc` 排除 NetClass；后续的 **master** 分支文档还描述了直接输入 KiCad `.kicad_pro`/`.kicad_dru` 以及颈宽（neck-width）行为。**不要**把后续 master 特性当作已测试的 2.5.0 能力来宣称。

## 最小化的带闸门外部 CLI 示例（并非发布授权）

```bash
python scripts/freerouting_adapter.py \
  --dsn path/to/approved-board.dsn \
  --expected-dsn-sha256 <actual-reviewed-64-hex-sha256> \
  --exclude-netclasses GND,RF,DIFF,POWER_CRITICAL \
  --jar path/to/verified-freerouting-2.5.0.jar \
  --expected-jar-sha256 <trusted-jar-hash> \
  --output-dir path/to/new-candidate
# Inspect preview. Run same command with --apply only after source/protection review.
```

如果 DSN 中包含 `approved-board.rules`，必须显式传入 `--rules-file` 与 `--expected-rules-sha256`，或把这个不受控的伴生文件从干净、隔离的导出目录中移除。绝不为让哈希检查通过而改动原始导出。

## 晋升闸门

在多块经独立审查的板卡上运行版本固定的 Windows KiCad 10.0.8 + Konnect + Freerouting 2.5.0 集成测试（包括 2/4 层普通网络、既有锁定铜层、GND 平面、细间距焊盘引出、混合电源以及高速受保护组）。对比前后的未映射网络、布线完成度、DRC、保留的对象 UUID、线宽/间距、层使用、过孔、差分/热约束、耗时与人工干预。只把 Freerouting 晋升为**已验收范围**内的自动默认；对不受支持的设计保留明确的回退 BLOCKED。

**来源**：[Freerouting v2.5.0 CLI](https://github.com/freerouting/freerouting/blob/v2.5.0/docs/command_line_arguments.md)、[KiCad 集成](https://github.com/freerouting/freerouting/blob/master/integrations/KiCad/README.md)、[KiCad PCB 设计规则](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html)。
