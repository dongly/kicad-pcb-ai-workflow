# courtyard 优先的 PCB 摆放安全——原生几何预览

这个 R10 **只读布局规划器**不是 KiCad DRC，也不能证明 DRC 零报错。KiCad 封装的 F.CrtYd/B.CrtYd 边界是**装配 courtyard**，不是一揽子铜箔间距，也不保证电气连接正确。KiCad 原生 DRC 会独立检查 courtyard 重叠、自定义 `courtyard_clearance`、铜箔间距、孔约束、禁布区等。规划器不得为得到候选位置而削弱任何生效规则。请使用真实的 `.kicad_pro`、`.kicad_dru`、板卡、XML 网表、已批准的 fab 档案与绑定源文件的摆放策略。

## 顺序与检查

1. 使用 `pcb.fab_preview` / 明确的人工 `pcb.fab_confirm` **确认板厂档案**。通过已认可的 Konnect 写入端应用实际的 Board Setup、netclass、叠层与自定义 DRC 规则。运行 `pcb.layout_preflight` 回读真实规则与网表一致性。
2. 依据 KiCad `.kicad_pcb` 的 courtyard **读取原始原生几何**。对受支持的顶面直线闭合 courtyard，保留原始多边形，而不只是其 AABB。可用已认可的原生 `pcbnew` 只读快照验证旋转变换；未经验证的旋转/底层/多轮廓/曲线 courtyard 一律 **BLOCKED**，绝不以臆造的矩形替代。某个封装的 `F.CrtYd` 不一定是对称的轴对齐矩形。
3. **尊重占位**：检查真实的 courtyard 多边形间重叠与额外间隙；预留显式的原生封装禁布多边形；保护已锁定、连接器、RF 禁布区锚定与机械类封装。固定的圆形 NPTH 安装钻孔是独立的机械障碍物。不受支持或可移动的安装孔在自动化之前需要原生证据。
4. **搜索期间尊重电气约束**：使用源文件声明的 `fixed`、`corridor`、`pad_proximity` 与 `decoupling` 约束。焊盘规则须校验焊盘编号、当前网络与实际焊盘中心；经核验的原生焊盘偏移可支持旋转封装，否则只接受顶面零角度焊盘。具名的 GND 回流过孔会核对真实 UUID 与网络身份。评估某个距离**并不能**证明回流平面连续性、瞬态电感或成品铜厚。
5. **限定搜索并保留状态**：移动封装之前先尝试当前合法位置；以显式上限惰性生成候选网格位置，并把每个候选与当前已放置对象一起评估。贪心有界搜索失败表示 `REPLAN_REQUIRED`，不是板卡不可布的证明。后续全局环节只平移可移动模块；不宣称任何自动的模块/封装旋转。
6. **应用并独立验证**：`BOUNDED_MODULAR_PLACEMENT_PROPOSAL` 只包含坐标。经批准的确切移动仍须通过 Konnect 单独认可，并且必须保存/回读、与方案核对，随后进行**仅布局的 G3 审阅**（`pcb.placement_pre` / `placement_review.py --phase pre_route`），**不做全板 DRC**。未消完的飞线/unconnected 网络属预期情况，绝不构成 G3 阻断；**布线与覆铜重填之后**，原生 KiCad 全板 DRC 加连通性检查属于 G4。绝不宣称该规划器已消除未来所有 DRC 发现。

## courtyard 间距语义

Skill 的 `courtyard_clearance_mm` 是*已放大后的* courtyard 边界之间的**保守装配规划间隙**，不是铜箔间距，也不是新的全局 KiCad 最小值。另外还会读取显式的 `.kicad_dru` `courtyard_clearance` 最小值，单位包括 `mm`、`mil` 与 `in`。规划间隙取已确认的 Skill 建议值与所有可理解的自定义最小值中的最大者，不论自定义条件的适用范围。这是保守做法，未必等于 KiCad 精确的条件规则求值。无法识别的自定义表达式会阻断规划，并要求实际原生审阅。若生效的 courtyard 重叠 DRC 严重度被显式设为 `ignore`，预检拒绝将其解读为可接受。

## 当前限制与杜绝虚假批准

- 既有的 `placement_review.py` 仍是独立的 G3 审计者，在受支持处使用原生焊盘位置。其 `critical_subcircuits`/视觉/热/布线/审阅凭据要求不予豁免。其他关键子电路类型仍需要当前真实的 G3 知识与审阅。
- 原生轮廓支持目前限于矩形或严格的四边轴对齐矩形环。任意板框、内部槽孔、复杂 courtyard 与 3D 外壳碰撞需要更丰富的原生几何模型和/或机械验收。未知意味着停止，而不是忽略。
- 目前只筛查简单的多边形封装 Keepout 与固定的圆形 NPTH 钻孔。铜箔到焊盘/走线的间距、阻焊/丝印、其他几何形状的孔，以及真实布线拥塞，都需要**布线后的 G4** 原生 KiCad 检查。不要把全板 DRC 当作 G3 布局关卡。规划器使用**受支持的约束**，不是对 KiCad DRC 规则引擎的完整复刻。
- `pcb.layout_plan` 不编辑任何实际板卡。本预览中**不存在通用的、已获认可的 Konnect 自动摆放执行/回滚循环**。离线合成测试成功不等于真实的 Windows KiCad/Konnect 验证。

参考：KiCad 10 PCB 编辑器 DRC/courtyard 间距文档：https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html ; KiCad Library Conventions：https://klc.kicad.org/。
