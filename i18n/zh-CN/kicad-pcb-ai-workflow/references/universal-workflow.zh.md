# R10 统一 CLI 与任务路由

## 从最小相关接口入手

不要为一个简单修改去读所有参考文档、编译所有配置或发现所有 Konnect 工具集。先确定当前项目身份，有效时复用其既有配置快照，并只选择一个已声明的任务。`workflow.py modules` 选择模块指引；`workflow.py plan` 预览操作；`workflow.py run` 派发经授权、绑定清单的工具；Konnect MCP 编辑是单独验收的真实 EDA 动作。

## 六个兼容分组与现行设计阶段

| 分组 | 节点与意图 | 主要检查 |
|---|---|---|
| 环境 | 节点 01：连接、工作区与工具身份 | 真实 KiCad/CLI/已验证 Konnect 目标 |
| 架构 | 节点 02–04：量化需求、缓存来源、备选项 | 精确器件证据与有来源依据的约束 |
| 原理图 | 节点 05–07：拓扑/网表、G1、G2 | 原生 ERC 与符号引脚/封装映射 |
| PCB | 节点 08–11：叠层/规则、G3、布线、G4 | 实际已保存板卡、完整原生 DRC 与 AI 评审 |
| 制造 | 节点 12–14：NPI、导出；工厂评审属外部 | `EXPORTED_NOT_RELEASED`、已验证产物 |
| 生命周期 | 节点 15–16：真实测试与 ECO，属外部授权 | 物理证据与工程师签名 |

## 核心命令

```bash
# Discover module-level task reading requirements without creating a new project.
python scripts/workflow.py modules --intent schematic
# Register a known working project ONCE. Do not create a second project for ordinary edits.
python scripts/workflow.py workspace /project --action status
# First-time master config only; an existing config must be reused or intentionally versioned.
python scripts/workflow.py init /project
python scripts/workflow.py init /project --apply
# Generate a new immutable configuration bundle only if the original source/rules changed.
python scripts/workflow.py build /project --bundle control-r1
python scripts/workflow.py build /project --bundle control-r1 --apply
# Use compact status, and obtain full JSON only for specific diagnosis.
python scripts/workflow.py status /project --bundle control-r1 --format compact
python scripts/workflow.py status /project --bundle control-r1 --format json
# Ordinary task: preview first, then run with required exact options.
python scripts/workflow.py plan /project --bundle control-r1 --task schematic.prepare --output-dir /project/03_REPORTS/G1-r1
python scripts/workflow.py run /project --bundle control-r1 --task schematic.prepare --output-dir /project/03_REPORTS/G1-r1
```

新安装时运行 `environment.doctor`；原生设置需要真实有效的输入，并在适当环节获得显式写授权。原理图 AI 评审使用节点 03 的项目器件卡片、真实网表/XML、原生 ERC 与 G1 工程师处置。PCB 在 G4 独立评审真实铜箔/DRC。制造输出必须使用隔离候选，不得仅因报告看起来干净就获得授权。某项已配置功能不适用并不会静默禁用强制闸门。

## 状态、安全与演进

配置包不可变，并与来源主档、工具及器件规则哈希绑定。工具、器件或来源变更可能需要*新的*配置包；不要为节省磁盘而覆盖旧的签核包。外部提供的脚本/命令不会自动可执行。Python 脚本路由使用经认可的工具清单与显式 argv。Konnect 动态 MCP 工具单独发现，并需通过构建/模式/范围验收；只有 Konnect 才能写入活动 EDA 项目。针对 10.x 样例的验收不会自动延伸到未来的 KiCad 11+、非基线安装或复杂制造场景。

参见 [入口](../SKILL.md)、[工作区策略](workspace-and-token-policy.md)、[最新 16 节点流程](latest-complete-workflow.md) 与 [Konnect 能力](konnect-capability-migration.md)。
