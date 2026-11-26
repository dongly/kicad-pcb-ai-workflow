# 模块化、引脚级与视觉 PCB 布局复核

## 执行顺序

先推导真实的板框轮廓、安装孔、连接器位置、机械禁布区与可制造性/courtyard 限制。然后划分功能模块并锚定关键位置：电源环路、振荡器、复位、模拟滤波器、RF 馈线/天线、高速连接器与引出路径。先解决物理布线走廊与引脚级电流回流，再追求美观对称。

模型基于真实的原理图网络拓扑、已核实的 G3 器件卡与板厂规则来规划元件布局。经采纳的 Konnect MCP 工具以有界批次对*当前授权的工作项目*施加真实的移动/旋转；Python `placement_review.py` 读取并评估所得几何。它不是已实现的自动布局优化器。必须核查实际的焊盘中心与引脚身份、封装朝向/所在面、courtyard BBox、模块占用、最短关键回流环路、天线/安装限制、散热气流与装配/测试可达性。

## 四类证据

1. **机械几何：**板框与安装约束、courtyard 封装、连接器配合间距、边缘/禁布区与装配高度限制。
2. **电气局部几何：**真实的去耦引脚到电容焊盘连接、振荡器/时钟环路几何、RF 匹配/天线位置、敏感模拟与电源环路的相互作用；焊盘中心距离并不等于完整回流路径。
3. **布线可行性：**进入/引出通道、真实窄间距几何、网络分类、受保护路径与电流/散热线宽。飞线数量的近似统计并不能证明布线已完成。
4. **人工视觉质量：**功能分组、位号/值可读性、丝印朝向、图纸易读性与维护可达性，且不得削弱硬性规则。

## G3 布线前仅布局检查 对比 G4 布线后 DRC

**G3：**`pcb.layout_plan` → Konnect 采纳的布局移动 → 保存/位置回读 → `pcb.placement_pre` / `placement_review.py --phase pre_route`。核查受支持的 courtyard/碰撞、机械禁布区、模块归属、以源为依据的引脚邻近/去耦、走廊以及预期布线可达性。**不运行全板 KiCad DRC，未连接网络永远不会构成 G3 失败。**G3 阶段不得调用 `pcb.prepare`/`pcb.gate`。

**G3 之后：**完成信号与电源/GND 布线 → 铺铜填充/重新填充 → 保存/重新加载。**G4：**`pcb.prepare` 调用原生全板 KiCad DRC（包括未连接项与原理图一致性）；`pcb.gate` 需要 AI 与工程师复核。`pcb.placement_final` 可以复查最终布局，但不能取代 G4 DRC。

布线前运行对应阶段的布局复核；每当相关布局发生变化，在保存最终铜皮/铺铜填充之后再次运行。按阶段保留报告，记录当前板卡 SHA、来源卡依据、实际元件 ID/坐标、发现的违规与独立的工程师决策。失败/未知/知识缺失不得为优化观感而转为 PASS。参见[原理图来源](module-schematic.md)、[G3/G4 工作流](latest-complete-workflow.md)、[PCB 规则](module-pcb.md)。

```bash
# Read-only G3 report, always into a new immutable report directory.
python scripts/placement_review.py /project --policy placement-plan.json --netlist actual-netlist.xml --board actual-board.kicad_pcb --phase pre_route --review-config /project/static-review.json --output-dir /project/03_REPORTS/layout-r1
```

## 精确的策略输入与实现边界

使用 `assets/placement-plan.template.json`（schema 版本 1），以项目内文件 SHA-256 与文档定位符绑定每个策略来源。每个实际 PCB 封装——包括 DNP、机械件与测试件——必须恰好归属一个模块；模块区域可以重叠，但元件归属不可以。指定锚点、成员、真实 `refs`、角色与允许的 `bounds_mm`。典型角色包括 controller、decoupling、clock、power、connector、protection、termination、filter、feedback、RF、analog、passive、test、mechanical、reserve 与 other。角色跟随引脚/网络的实际用途，绝不依据 C/R 前缀。仅存在于原理图的符号需要显式的 ref/理由/证据例外；机械封装可以不出现在原理图中。只有在审查电气适用性之后才可使用 `other`。

`critical_subcircuits` 必须显式列出 `id/type/reason/refs/check_ids/source`。类型包括 decoupling、power_loop、crystal、termination、protection、filter、feedback、rf、reserve 与 other。每个已知的去耦电容必须有专用的引脚级去耦规则；不得把任意邻近焊盘当作有效的去耦电路。

| 局部电路 | 相对于什么定位 | 几何不能证明什么 |
|---|---|---|
| 旁路电容 | 指定的 IC 电源引脚、电容电源/地焊盘与显式回流锚点 | 焊盘中心邻近无法确立回流环路电感或铜皮连续性 |
| 开关稳压器 | 厂商指明的高 di/dt 环路与安静采样/反馈点 | courtyard 外包络并不能定义实际电流环路 |
| 振荡器/时钟 | 指定引脚、负载电容路径与噪声敏感的邻近电路 | 不存在通用的铜皮挖空或一刀切的接地围栏规则 |
| 串/并联端接 | 拓扑所要求的实际驱动端或接收端 | 默认不要把每个电阻都放到 IC 旁边 |
| 接口保护/ESD | 连接器入口、上下游网络与低电感放电路径 | 到控制器的路径短并不等于 ESD 回流有效 |
| RF 馈电/匹配/天线 | 器件专属拓扑、参考平面与辐射禁布区 | 默认不要移除所有 RF 电路下方的铜皮 |
| 反馈/模拟滤波 | 具体采样点、源阻抗与回流/参考要求 | 仅凭走线长度并不能确立精度或稳定性 |
| 可选/DNP 分支 | 实际贴装变体与物理短桩/焊盘寄生 | 未贴装的焊盘仍可能影响 RF/高速拓扑 |

### 受支持的约束与核查限制

`placement_review.py` 是**只读**的，不是自动布局器。每条约束都有唯一的 `id`、`kind`、风险 `level` 与来源。物理单位与阈值必须来自当前设计或相关厂商/制板厂来源，绝不能是通用的硬编码距离。

- `fixed`：以 `position_mm`、`angle_deg`、`position_tolerance_mm` 与 `angle_tolerance_deg` 核对封装的真实参考位置与角度；不能证明 3D 适配。
- `pad_proximity`：精确的 `(ref,pad,net)` 端点、最大距离与可选的同面规则；与真实 XML 网表及实际焊盘身份交叉核对。
- `decoupling`：`ic_power`、`cap_power`、`cap_ground`、`return_anchor`、`max_power_mm`、`max_return_mm` 与同面规则。电容的电源端点与地端点必须可区分，并具有被指名的回流焊盘或经 UUID 验证。即便几何结果通过，也不能证明参考平面连续性。
- `corridor`：受保护矩形、边距与显式允许的封装 refs。只检查受支持情况下的保守 courtyard AABB 侵入；不计算布线容量。
- `alignment`、`uniform_spacing`（三个及以上 refs）与 `orientation`：仅属于美观约束，绝不能成为推翻电气或制造违规的理由。

courtyard/物理边界检查需要受支持的真实顶点，而不能只看封装中心。受支持的静态几何仅限简单的同面直角闭合轮廓；旋转、底面、曲线/多轮廓或缺少 courtyard 的情况可能需要原生或人工证据。若无法独立确立精确的焊盘变换，应返回 `manual_required` / 阻塞，而不是计算一个猜测的位置。对于 `manual_geometry[ref]`，要求提供当前板卡 SHA-256、理由与真实的原生/机械证据。这里记录的是人工提供的例外，而不是自动 PASS。

只有美观规则可以声明 `exception={reason,evidence:{file,sha256}}`；硬规则绝不继承此类豁免。丝印遮挡、极性、1 脚、3D 干涉、散热可达性、放置高度与可维修性需要超越基础几何检查器的真实设计/装配审查。

### 布线前复核、最终复核与失效

`reviews.pre_route` 必须绑定 `placement_sha256`、`netlist_sha256`、`policy_sha256`（排除复核记录本身）、复核人、日期、理由与证据。对**每一条**已声明的关键子电路复核可布线性/引出、回流路径、厂商参考布局与机械约束。它不能证明自动可布线性。`reviews.final` 必须对应同一实际布局与最终 `board_sha256`，并覆盖最终视觉质量以及布线/填充之后的所有 `moves_rechecked`。即使布线前布局未变，板卡变更也可能使最终复核失效；焊盘、约束、源数据或元件位置的变更要求重新进行受影响的布线前复核。绝不通过重构或倒填日期来补造缺失的早期复核。

对于 PCB 静态 AI 审查，设置 `require_placement_review=true`，绑定 `placement_review.policy`，并添加 `placement_quality` 语义任务。覆盖所有物理封装与关键网络；机械对象按封装观察，电气引脚按 `(ref,pin,net)` 观察。原生层视图与来源布局是相互独立的证据。缺少布线前/最终证据或硬约束失败会阻塞相关的 G3/G4 与制造门禁；**仅未布线网络永远不会阻塞 G3**。即使出图看起来整洁，也要求人工/AI 复核。

交付四类*只读*产物：`module-map.svg`、`local-N.svg` 局部电路视图、`placement-report.json/.md` 与 `visual-review.md`。它们是坐标示意，不是 KiCad 原生铜皮/CAM/3D 证明。在原生 PCB 提取不可用的场合，`--static-preview` 仅作初筛；不受支持的几何仍作为已上报的缺口。严格报告使用新的不可变报告目录；不要仅为另一份报告而克隆一个全新的 KiCad 工程项目。

## 布局前提：有效规则与模块分区

在生成新的候选位置之前，使用[规则优先的模块布局](pcb-module-layout.md)预检。它检查真实的 KiCad 源规则/生效规则以及有来源依据的制造最小值，而不是重复 G3 写入后的电气与机械复核。模块化启发式是只读的；任何提案都不是已放置的 PCB、已布线的铜皮、已验证的 SI/PI 或 G3 批准。回读当前的 Konnect 移动，并继续沿用原有 G3 复核者。
