# JLCPCB 刚性 FR-4：明确的厂商能力档案审核与用户确认

## 范围、来源与区别

本 Skill 附带 `references/jlcpcb-rigid-fr4-presets.json`：一份带日期的、**由 Skill 作者整理的保守建议**，依据 JLCPCB 公开的刚性板工艺能力与成品铜厚文档（核对日期为 2026-11-18）。它**不是 JLCPCB 官方的默认下单配置**，不得当作工厂报价、实际叠层、产能保证或制造授权来呈现。每个来源 URL 都收录在该参数目录中。实际下单时的工厂可得性、成本与确切层叠参数必须另行复核。

- 1 oz 铜厚：JLCPCB 公布的工艺能力下限约为 1–2 层刚性板线宽/间距 0.10/0.10 mm、多层板 0.09/0.09 mm。本 Skill 建议更保守的设计下限：2 层板 0.20/0.20 mm、4/6/8 层板 0.15/0.15 mm。针对实际电流、电压与散热条件仍须计算更宽的线宽；这些档案不是通用的电源线宽规则。
- 公布的微孔能力（孔 0.15 mm/盘 0.25 mm）属于**进阶、可能加收费用**的极限，并非 Skill 默认值。Skill 建议 0.30 mm 钻孔/0.70 mm 外径，名义径向环形铜环（annular ring）为 0.20 mm。同时建议 0.30 mm 的铜箔到铣板边缘间距、过孔孔到孔间距余量，以及 0.25 mm 的 courtyard 间距（最后一项是项目装配规划建议，不是通用的 JLCPCB 最小值）。
- JLCPCB 公布多层板常用默认成品内层铜厚为 0.5 oz；档案建议外层 1 oz / 内层 0.5 oz、整体板厚 1.6 mm。进入 G3 之前，实际 KiCad 叠层必须精确包含已批准的铜层数并匹配成品铜厚。**笼统的 4/6/8 层数或 1.6 mm 板厚都不代表叠层阻抗有效。**应选定具体的 JLCPCB 叠层方案，必要时使用厂商阻抗计算器。
- 对 6 层及以上的刚性 FR-4，JLCPCB 的能力表不含 HASL；档案建议采用兼容的非 HASL 表面处理，如 ENIG。实际下单的表面处理仍须独立确认。V-cut 边缘要求不同的铜箔间距（0.4 mm），半孔（castellated holes）、板边电镀与特殊拼板同理。
- 制板工艺下限不能批准任意的元件 courtyard/3D、PTH 焊盘孔径与焊盘直径、自定义封装中的环形铜环、阻焊桥、受控阻抗、RF 回流、SI/PI 或装配。请运行独立的 DRC 与工厂 DFM 检查。

## 人工介入流程（不得自动确认）

**步骤 A：侦测选定的板卡并展示一份提案**（不改动 KiCad）：

```bash
python scripts/workflow.py run /project --task pcb.fab_preview \
  --fab-board 01_WORKING/main.kicad_pcb --fab-layers 4 \
  --fab-proposal /project/03_REPORTS/pcb-fab/proposal-v1.json
```

Agent **必须向用户展示**：选定的厂商、铜层数、板厚、外层/内层铜厚、建议的最小线宽/间距、推荐的过孔钻孔径/外径/径向铜环、铜箔到板边间距、钻孔间距、courtyard、表面处理，以及工厂极限与设计建议之间的区别。对未知的实际叠层 ID、高速阻抗与特殊制造要求，须明确披露。状态为 `FAB_USER_CONFIRMATION_REQUIRED`。若用户更改层数或设置，须修订提案或改用另行取证的合适自定义档案；不得把旧凭据当作批准。

**步骤 B：停在这里，直到用户明确确认所展示的提案。**绝不从沉默或之前的聊天内容推断批准。只有确认之后，Agent 才可使用：

```bash
python scripts/workflow.py run /project --task pcb.fab_confirm --apply \
  --fab-proposal 03_REPORTS/pcb-fab/proposal-v1.json \
  --fab-decision CONFIRM --fab-confirmed-by '<actual approving user or engineer>' \
  --fab-approval 03_REPORTS/pcb-fab/approval-v1.json \
  --fab-rule-output 03_REPORTS/pcb-fab/fab-rules-v1.json
```

这些文件仅是**新增的、不可变的、限定于本项目的凭据（receipt）**。CLI 应答无法认证操作者身份：宿主必须保留真实的对话/用户操作。脚本本身不能点击、配置或保存 KiCad 编辑器。确认成功仅表示 `FAB_PROFILE_USER_CONFIRMED`，**并非**规则应用步骤或工程签核完成。重复调用会拒绝覆盖，而不是悄悄续期批准。

**步骤 C：在同一个受保护的工作项目中，通过已配置的 Konnect MCP 写入端应用实际规则**；配置板层数、1.6mm 名义整体板厚、实际的成品外层/内层铜厚叠层、Board Setup 约束、NetClasses 以及适用的特殊规则。保存后，独立回读当前 `.kicad_pro`、`.kicad_pcb` 的原生叠层与生效 NetClasses。凡涉及阻抗，必须显式选定厂商确切的层压/介质厚度与叠层 ID。不设第二个原生写入端回退。

**步骤 D：只有 C 成功之后，才运行原生布局预检与模块布局规划：**

```bash
# Request must include both approved `fab_rules` and immutable `fab_approval`.
python scripts/workflow.py run /project --task pcb.layout_preflight \
  --layout-request 03_REPORTS/pcb-layout/request.json \
  --layout-receipt /project/03_REPORTS/pcb-layout/rules-v1.json
python scripts/workflow.py run /project --task pcb.layout_plan \
  --layout-request 03_REPORTS/pcb-layout/request.json \
  --layout-receipt /project/03_REPORTS/pcb-layout/rules-v1.json
```

布局预检首先校验一份与板卡身份和层数匹配、经用户明确批准且哈希绑定的档案；同时核对当前确切的各铜层厚度（本参数目录中为外层 1 oz、内层 0.5 oz），以及生效的 KiCad 最小规则是否满足每一项已批准的设计下限；随后调用既有的**原生**生效 NetClass 审计与原理图到 PCB 的焊盘-网络一致性检查。若缺少批准，则在代价高昂的 KiCad 审计之前以 `FAB_USER_CONFIRMATION_REQUIRED` 阻断。两级规划器在后续仅移动式规划中复用已验证且不可变的预检结果，避免重复批准/审计。来源、层数、选型、叠层或规则的任何变更都会使对应的批准/回读失效，并视情况要求用户重新审阅。既有的 DRC、G3 与制造放行关卡保持独立。

## 硬性失败情形

- 向 2 层板套用 4 层选型、参数目录/档案变更、已存储的提案/fab JSON 变更、缺少批准或缺少真实用户确认：一律 **BLOCKED**。
- 实际 Board Setup 不包含所选铜层叠层，或成品铜厚不符：在 G3 之前 **BLOCKED**。
- 实际 KiCad 最小约束不如用户批准的建议下限保守，或原生 NetClass 数据无法回读：**BLOCKED**。
- 特殊需求（阻抗、RF、参数目录之外的铜厚、非常规板厚、盲埋孔、V-cut 等）不得被悄悄当作标准情形处理：必须取得另行取证并经审阅的规格说明；这四套预设并非通用。

本参数目录仅收录 2/4/6/8 层、1.6mm 名义板厚的刚性 FR4 档案；无关的板厂与特殊工艺必须使用另立范围的专用流程，绝不伪造 JLCPCB 证明。
