# DFX/NPI：实施矩阵、证据与受控发布

本参考文档规定可制造性、装配、测试、可靠性与交接检查的**真实范围与限制**。它并不声称 KiCad 或本 Skill 能自动验证每一项机械、SI/PI、安全、CAM 或产品性能属性。**R10 优先：** Konnect MCP 是唯一被授权的活动 EDA 写入方；KiCad CLI 执行独立的原生检查；`pcbnew` 可继续作为只读兼容依赖保留。节点 13 产出带 `EXPORTED_NOT_RELEASED` 状态的候选包，而非自动的生产放行授权。实际的 CAM/EQ、样机与 ECO 是独立的外部步骤。任何暗示强制 `pcbnew` 编辑后端或自动执行 G5/G6 的旧 R9.x 指令均为历史内容，不构成 R10 权限。

## 1. 生命周期与责任归属映射

早期工程流程使用带独立叠层前置阶段的八阶段基线；部分较旧的 NPI 指南使用十个**管理检查点**。两者都不能替代当前的 [16 节点契约](latest-complete-workflow.md)。有效的 R10 主线在节点 13 设计包评审就绪后结束。

| 当前区段 | 工作内容 | 独立验收 |
|---|---|---|
| 节点 1–4 | 需求、AVL、MPN/制造商货源、防护选项、变体 | 货源有效性、明确的验收条件与约束 |
| 节点 5–7 | 原理图、ERC、完整的引脚/封装映射 | **G1** 原理图/语义/工程师，**G2** 符号-封装/制造商 |
| 节点 8–9 | 已批准的叠层、原生规则、布局 | 实际规则应用、**G3** 布局、回流与装配 |
| 节点 10–11 | 走线、覆铜区、关键网络、原生 DRC、设计评审 | 连通性、覆铜填充/回读、**G4** PCB/工程师 |
| 节点 12–13 | DFX/NPI 与不可变的制造候选包 | 源/证据哈希、变体一致性、Gerber/钻孔/BOM/CPL/图纸、`EXPORTED_NOT_RELEASED` |
| 节点 14–16 | CAM/EQ、实际的 EVT/DVT/PVT 与 ECO | **外部**工厂与工程师权限、实测量化结果 |

`pre_export` 报告检查设计输入；它**不**授权制造。历史 `release` 检查审验既有候选包的完整性与已授权处置。任何关卡都不会仅因文件存在而通过。

## 2. 全量工程检查矩阵

使用三种实施类别：**NATIVE**（真实的 KiCad CLI 结果或经专门认可的等效结果）、**SCREEN**（有界的 Python 几何/数据启发式检查）与 **EXTERNAL**（真实的工程师、工厂、实验室或专用工具）。当仅有 SCREEN 时，须记录其局限，且不得将其升级为 NATIVE 或最终制造验收。

| 领域/检查项 | 证据与实施方式 | 局限与强制升级 |
|---|---|---|
| ERC 及严重级别 | `kicad-cli sch erc --format json --severity-all --exit-code-violations`；解析原生报告 | 错误项阻断；警告项需要书面工程处置，不得静默忽略 |
| 层次结构、图纸命名与跨页电气同一性 | 原生 XML 网表、ERC、图纸解析器/图结构环路检测与 `netlist_guard.py` | 仅凭文本解析图纸无法证明电气拓扑或模块化正确性 |
| 变体识别 | 显式声明的 `variants`、变体 BOM 与已批准的变体基线 | 绝不推断缺失的变体；原生 ERC 未必提供 `--variant` 开关 |
| 位号、MPN、制造商、封装与字段完整性 | 实际 BOM CSV，含位号拆分、字段映射与重复项检查 | 缺失字段与重复位号将阻断；CSV 解析不等于货源批准 |
| 同 MPN 冲突与跨变体一致性 | 比对精确 MPN、制造商/封装/规格，以及已声明的各变体不变字段 | 已批准的替代料必须有书面 ECO 或变体策略 |
| 电源域与防护配置 | 已配置的电源域，以及反极性、TVS、保险丝、看门狗、复位等的角色 | 位号匹配绝不证明防护拓扑正确；必须人工评审原理图 |
| 爬电/电气间隙与安全绝缘 | 评审者提供实际电压、污染等级、材料组、海拔与工作绝缘类别 | 没有通用数值；缺少适用标准/批准时不得自动通过安全验收 |
| EOL/NRND 可获得性 | 导出候选 MPN 清单，状态标注为 `not_queried` 供外部查询 | 本 Skill 不会静默联络供应链服务 |
| 电气/热降额 | 制造商额定值，以及合格评审者或外部器件数据库 | 缺少相应器件参数与条件时不得计算通过/不通过 |
| PCB 几何数据来源 | 已保存的板卡数据、经认可的原生等效读取器、可选的只读 pcbnew | 静态文本回退**仅限预览**，不构成制造级几何权威 |
| NetClass 分配 | 实际 KiCad 项目规则与暴露的原生类数据 | 仅有存在性不能证明网络分配、规则优先级或适用性正确 |
| 热源、散热过孔与温度敏感器件 | 已声明的热源、邻近过孔候选与 2D 距离 | 不能确定热阻、铜连接或实际温度 |
| 功率环路面积 | 以封装中心包围盒估算 | 并非真实的功率或回流环路面积 |
| 测试点可达性 | 探针接触尺寸、邻近焊盘包络与预期可达性 | 2D 遮挡不等于实际治具/高度可达性；须检查真实外壳/治具 |
| JTAG/其他调试接口 | 在已声明连接器焊盘上的已声明 JTAG 网络 | 链路顺序、电平、连接器极性与可用性需实际评审 |
| 器件到板边与安装孔的铜距 | 焊盘几何与直边轮廓筛查 | 弧形边、3D 器件、螺钉/垫圈与精确铜距需原生/MCAD 评审 |
| 器件高度干涉 | 显式的机械评审者/模板或 3D/MCAD | 不得从 2D 封装推断 Z 向高度 |
| 去耦电容与 IC 供电引脚 | 显式位号与焊盘编号、已批准的最大距离、真实焊盘中心回读 | 直线距离不等于环路电感、回流路径或足够电容量 |
| 平面分割、回流连续性与 PI | 已批准的叠层、类、铜皮与基于源端接地的分析 | 没有隐式场求解器，也不会自动证明电流回流 |
| 差分对与关键链路路径 | 实际线段/弧线/过孔、端点唯一性、分层时延模型与链路审计 | 缺失路径/分支/重复铜皮/未知模型将阻断；不自动计算耦合阻抗或 S 参数 |
| 功能分区与噪声耦合 | 已声明的区域与中心位置；噪声网络与敏感网络间的 2D 间距 | 2D 距离不构成电磁耦合证明 |
| 线宽、间距、钻孔与环径 | 工厂批准的边界值、原生 DRC 加走线/焊盘/过孔预筛查 | 所有对象类型与自定义规则都需要原生完整 DRC；不得猜测限值 |
| 孔的厚径比 | 标称通孔板厚/孔径 | 盲孔/埋孔/微孔需要实际贯穿层厚度与工厂确认 |
| 阻抗预检 | 已批准的叠层、介质厚度、Er 与目标公差 | 缺少经验证的场计算器/coupon（阻抗测试条）流程时**不得声称阻抗已解算** |
| 锐角、走线细颈与阻焊桥 | 线段角度与焊盘包络、DRC 与工厂检查 | 精确的填充细颈几何与全部阻焊开窗无法完全自动化；需 CAM 评审 |
| 层铜平衡/板翘曲 | 对简单矩形做覆铜/走线/焊盘包络的稀疏网格估算 | 并非精确的 CAM 铜面积；无法预测翘曲或板材层压行为 |
| 覆铜区重叠、孤岛与实际填充 | 填充多边形存在性、原生 DRC 与目视检查 | 仅有区域轮廓不等于已填充铜皮；独立的精确孤岛检测可能不可用 |
| SMT 间距与 BGA 边缘风险 | 焊盘盒间距与板边筛查 | 必须检查器件本体、courtyard、返修与分板应力 |
| 拼板 V-Cut 与邮票孔 | 显式的工厂/装配评审 | 仅凭标注或图形不能证明拼板切割几何/铜皮间距 |
| 基准点（Fiducial） | 名称/封装与数量筛查 | 拼板级位置、非共线性、铜皮与阻焊禁布区需装配评审 |
| SPICE | 显式原理图导出与可选的独立 ngspice | 模型、激励与分析由工程师提供/批准；未运行的演示不构成测试 |
| 热仿真 | 将源坐标交接给外部求解器 | 没有外部结果时不得声称已完成热仿真 |
| EMC | 接地/滤波/屏蔽筛查并附外部测试证据 | 静态筛查不构成 EMC 合规或场解算 |
| 基线、版本与变体 | 覆盖原理图、层次结构、PCB、项目、BOM 与变体 BOM 的 SHA-256 | 缺失当前版本/批准人/变体集将阻断；哈希不可被改写以掩盖变更 |
| ECO | 变更 ID、原因、范围、受影响文件、验证、负责人与批准 | 输入变更使相关工程签名失效 |
| Gerber/钻孔/CPL/BOM/图纸 | 显式、无通配符的逐层/逐类输出清单并附文件哈希 | 仅凭文件非空绝不证明 CAM、装配或 D2 授权 |
| 作业集（jobset） | 受限且经验证的工具/命令配置 | 通用的 jobset 输出不能绕过逐文件导出与目的地契约校验 |
| EVT/DVT/PVT | 真实的数量/条件/验收/证据/负责人 | 静态评审不能声称已取得实验室与制造测量结果 |
| CCC/CE/产品法规 | 由负责工程师作出显式的产品/市场适用性决定 | 不隐含任何认证或法律结论 |

上述所有检查项保留其名称与失败语义。当工具无法获得原生等效几何数据时，保持 `BLOCKED` 或 `NEEDS_EVIDENCE`；不得为让报告变绿而将关卡降级为纯文本估算。

## 3. 依赖、配置与可选外部工具

- **按实际任务所需：** 受支持的 KiCad CLI 用于原生原理图/PCB 检查与导出；可访问的项目源文件；目标工厂批准的工艺限值；器件制造商文档与评审证据。在目标环境中实测当前的二进制版本与报告 schema。
- **Konnect：** 需要活动 EDA 写入时，须发现并接受当前二进制/构建/工具 schema 与操作范围；对旧公开版/商业版的接受不可迁移。本 Skill 包不捆绑 Konnect。
- **旧版只读兼容：** 在证明 Konnect 快照覆盖达到原生等效之前，某些精细几何检查可能仍需要安装特定的 pcbnew 读取器。这**不**授权 pcbnew 写入活动项目。
- **可选：** 带有效 SPICE 模型的独立 ngspice；仅在明确提供并获授权时使用的供应链 API；专用 SI/PI、热、EMC、3D/MCAD、工厂 CAM 与治具系统。
- **Python：** 核心工具的许多任务使用标准库；各工具的外部依赖必须核查而非猜测。不得从 pip 安装任意的 `pcbnew` 包来绕过版本兼容。

首先使用 [环境接入](environment-onboarding.md) 与实际 Skill 的 `doctor`/Konnect 能力检查。填写 `assets/review-config.template.json` 的实际项目副本、工程配置档案与工艺货源批准。未填写完整的模板永远不是已批准的设计。所有新报告输出都写入显式的新目录；**日常编辑始终只在一个已注册的工作项目中进行**。

## 4. 带防护的评审与发布工作流示例

```bash
# Read-only pre-export design review; source reports remain immutable.
python scripts/mass_production_review.py /project \
  --config /project/review-config.json --mode mass_production \
  --phase pre_export --output-dir /project/03_REPORTS/npi-pre-export-r1

# Candidate package must already exist and match the reviewed source.
python scripts/mass_production_review.py /project \
  --config /project/review-config.json --mode mass_production \
  --phase release --candidate-dir /separate/manufacturing-candidate \
  --output-dir /project/03_REPORTS/npi-release-check-r1

# Explicitly preview publication first; --apply only after real authorization.
python scripts/npi_release.py /project --config /project/review-config.json \
  --candidate-dir /separate/manufacturing-candidate --destination /separate/new-release
```

以上命令均为示意性的契约模式。请在已安装的构建中使用实际受支持的选项名、版本检查、相对文件路径与文件存在性检查。`--mode prototype` 是非生产诊断模式；它无法导出或发布生产包。

### 制造商参考与安全冻结交接（R10）

1. 评审真实的源数据与应用；确保 G1–G4 报告适用于**本**原理图与 PCB 哈希。
2. 通过**经治具认可的 Konnect** 操作，在受控候选中完成布线与当前覆铜填充状态；执行独立回读与 CLI DRC。不得让静态布线规划输出顶替实际已保存的铜皮。
3. `freeze_candidate.py` 创建隔离候选与 Konnect 交接。其显式 `--apply` 会暂存一份副本，且**不会自动重新填充**。`--finalize` 需要真实的 Konnect 操作回执与独立原生 DRC。返回 `FROZEN_NOT_VALIDATED` 后仍需通过其他项目关卡。
4. 不得在新候选中递归包含 `02_CHECKPOINTS/`、`03_REPORTS/`、`04_RELEASE/` 与历史快照。所有历史在外部妥善保存；不得删除。确保实际设计依赖文件仍然存在。
5. 将所得基线绑定到精确版本、授权评审者、装配变体、层次结构与源哈希。任何相关输入的变更都要求重新冻结与重新评估，而不是修改哈希。
6. 通过经验证的直接 KiCad CLI 命令，将 Gerber、钻孔、BOM、CPL 与所需装配层导出到新候选目录。记录 CLI 版本/构建、命令参数、日志、返回码、源/目标路径与输出哈希。PDF 或其他打印图纸仍需人工内容评审。
7. 在 CAM 中独立打开 Gerber/钻孔文件，完成工厂 EQ 的闭环，核验 D2 交付清单，并取得工厂/订单范围与人工授权。打包**完整**的已验证交付物，而非仅 Gerber 文件。
8. 实际的物理样机/可靠性批准与静态设计及制造候选就绪状态分开管理。

### 外部证据与评审契约

批准或不适用决定必须包含 `reviewer`、ISO 日期、`reason`，以及一个真实非空的 `evidence` 数组（含现存路径与 SHA-256）。手写的 JSON 评审声明不能核验个人签名；组织必须独立管理权限。人工评审不能推翻已被证实的原生/ERC/DRC 阻断项。

```json
{
  "baseline": {
    "revision": "R1",
    "approved_by": "engineer-name",
    "variants": ["default"],
    "sha256": {"board.kicad_pcb": "CURRENT_64_CHARACTER_SHA256_REQUIRED"}
  },
  "manual_reviews": {
    "SCH.CREEPAGE": {
      "status": "not_applicable",
      "reviewer": "responsible-engineer",
      "date": "2026-11-17",
      "reason": "Documented product-specific applicability decision",
      "evidence": [{"file": "reviews/safety.pdf", "sha256": "CURRENT_64_CHARACTER_SHA256_REQUIRED"}]
    }
  }
}
```

该 JSON 仅是说明性的**模板**，不是有效的生产证据，也不是供直接粘贴使用的批准。导出回执、外部测试结果与实际的当前板卡哈希在其适用阶段为必需项。除非明确授权，不得泄露机密或联络供应商 API。

### ECO 与样机可追溯性

ECO 需记录：ID、新旧版本、受影响的原理图/PCB/BOM/固件/治具、失败原因、风险、测试证据、负责人与实际批准日期。EVT：在量化计划下执行功能/电源/接口/DFT 测试；DVT：适用的热/湿度/振动/老化与安全项；PVT：良率、测试覆盖率、可追溯性与工艺稳健性。以上任何一项都不能仅凭本 Skill 的软件夹具获得批准。

## 5. 发布把关与失败恢复规则

- 只读评审期间不得变更源 EDA 数据，也不得覆盖既有报告目录或已签名证据。
- `--static-preview` 绝不授权生产，即使未发现其他违规。
- 发布决定会重新计算相关实际文件哈希与当前关卡；手改的历史报告不具权威性。
- 绝不覆盖既有源文件/候选包，绝不接受路径穿越/符号链接逃逸，绝不把通配符类别当作文件级证明。
- 强制执行 **设计预检 → 隔离制造候选 → 候选完整性/CAM/EQ → 显式发布**，避免在预检阶段循环要求验证尚未生成的文件。
- 若缺少源约束、原生几何、芯片应用要求或实际工具能力，报告 **BLOCKED/NEEDS_EVIDENCE**，而不是编造一个安全值。
- 工程与工厂标准按**实际产品与工艺适用性**应用。引用 IPC/IEC 不隐含通用数值或产品认证。

## 6. 交叉引用与权威关系

- [设计意图与 NetClass](design-intent.md)：PCB 布线之前基于源文件的差分、电流与 RF 约束。
- [G1/G4 静态 AI 评审](static-ai-review.md)：真实的图纸/网表/板卡与当前工程师评审。
- [预留与调试选项](reserve-options.md)：变体、0 Ω、DNP、测试点与不预留的理由。
- [布局质量](placement-quality.md)：G3 布线前与最终布局/回流路径证据。
- [工程规则](engineering-rules.md)：产品级安全、范围、量化验收与风险处置。
- [完整当前设计工作流](latest-complete-workflow.md)：优先于较旧的 R9.x 阶段编号。
- [KiCad 10 CLI](https://docs.kicad.org/10.0/en/cli/cli.html)、[KiCad PCB Editor](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html)、[KiCad IPC API](https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/for-addon-developers/)。

**边界：** 软件契约测试与原生示例工具链冒烟测试不等于制造发布、信号完整性或实际产品验证。显式记录每一项未实现的精确几何或专业分析检查；不得通过选择宽松模式将其隐藏。
