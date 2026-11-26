# R10 Konnect MCP 迁移：动态发现与唯一的活动 EDA 写入者

## 策略

不要硬编码 228 或 235 个工具名的永久白名单。用 `list_toolboxes`、`load_toolset` 与
MCP `tools/list` 发现所安装 Konnect 版本实际暴露的工具；默认使用任务聚焦式发现，
仅在盘点时显式使用 `--all-toolsets`。**发现不等于验收。**能力按指定构建、输入
schema、项目范围、KiCad 版本与已验证对象类型进行验收，之后只能在这些确切条件下复用。

Konnect MCP 是唯一的活动 KiCad **写入者**。实验性的 `kicad_bridge` 插件、服务器与
请求写入路径已被禁用；原生 `pcbnew` 的填铜/保存不是自动回退。Python 仍负责计算、
缓存知识、确定性审计与隔离的离线生成；KiCad CLI 是独立的 ERC/DRC/检查路径。过渡
期间，少量 `pcbnew` **只读**几何/NetClass 审计在已验证的前提下仍然可用；缺少原生
等价信息时，阻断相关制造断言。

## 风险与可复用验收

| 风险 | 示例 | 验收边界 |
|---|---|---|
| L0 | 版本、list/read/get、板卡元数据 | 核实身份与预期目标；不写项目源文件 |
| L1 | 单对象移动/旋转、简单字段或丝印修改 | 显式授权下的首次有界使用，保存并回读；没有一刀切的夹具前置要求 |
| L2 | 成组放置、布线、过孔、填铜、网络变更 | 在受保护工作候选板上的首次授权小批量；保存、回读并审查真实状态 |
| L3 | 删除/重建、整板自动布线、高风险重构 | 隔离候选板，外加专门的故障/恢复与工程证据；按需人工授权 |

将验收登记表持久化在公开 Skill、候选板与项目**之外**（例如私有工作站位置）。每条
验收记录绑定：可执行文件 SHA-256；后端发布/服务器版本与构建 commit；KiCad 版本；
实际 MCP 工具名与输入 schema SHA；已测试的参数/几何/对象范围；源夹具与所得候选板
哈希；独立原生 DRC 证明；以及失败/恢复条件。新的可执行构建或输入 schema 变更都需要
新的相关验收。项目编辑仍需要独立的、针对该项目的结果与门禁审查。

## 操作序列

```bash
# Read-only inventory. Use --all-toolsets only when full audit is requested.
python scripts/konnect_capabilities.py discover --executable /real/konnect --config /real/config.json --all-toolsets --output-dir /new/reports/discovery
# Inspect a specific capability's identity and scope before performing writes.
python scripts/konnect_capabilities.py assess --help
# Use a *separate*, genuine KiCad fixture for first acceptance.
python scripts/konnect_capabilities.py fixture --help
# Only after actual scope acceptance, invoke a candidate operation with --apply.
python scripts/konnect_capabilities.py invoke --help
```

在启用尚未登记的版本之前，核实实际安装包来源与合法授权；在本地登记其可执行构建与
允许的 KiCad 目标。不得把 0.13.0 的测试结果当作商业版 0.14.1 或未来版本行为一致的
证明。不得仅因帮助文本存在就假定每个新发现的工具都是安全的。

## 候选板操作与冻结交接

1. 核实唯一的当前目标项目与候选源哈希，检查对象 UUID、受保护几何与既有的已验收
   工具范围。
2. 普通 L1/L2 操作直接进行有界的首次使用执行；L3 或专门验收预留独立夹具。`fixture`
   目前对指定的封装定位与填铜变更具有有界验收检查器；未知操作类别需要自己的确定性
   验证器，而非自动 PASS。
3. 通过 Konnect 执行小批量并回读真实变更；超时会留下不确定状态，直到回读为止。
   按要求在获认可操作之后保存，并把回执绑定到确切的源/候选哈希。
4. 冻结时，仅用 `freeze_candidate.py` 暂存独立副本；打开*候选板*，执行获认可的
   Konnect 填铜并保存；调用 `freeze_candidate.py --finalize --operation-report ...`
   验证回执、已填铜皮与独立 KiCad CLI 原生重载/DRC。源项目必须保持不变。
5. 将操作回执与原生输出存储在相互独立、不可变的报告目录中。原生 DRC 与人工 PCB
   审查仍使用当前已保存的候选板；仅有成功的 MCP 响应并不足够。

## 迁移局限

`konnect_backend.py` 验证后端身份与板卡/资源保护。其他脚本仍然要求通过 MCP 尚未
证明等价的原生几何、规则与制造语义；保留只读适配器，缺失时阻断。不得声称完全替代
`pcbnew` 读取、完整的自动布局/布线、EMC/PI 验证或最终生产批准。
`manufacturing_export.py` 用 KiCad CLI 生成独立输出；DFX/NPI 与来源追溯门禁仍是
强制的。

相关：[后端安装](konnect-backend.md)、[工作流程](latest-complete-workflow.md)、
[独立静态审查](static-ai-review.md)。

## 当前首次使用策略

可用 Konnect 工具列表不做人为裁剪。在完成当前可执行文件、工具 schema 与目标检查后，
L0 读取正常进行。L1/L2 可以在受保护工作候选板上尝试一次授权操作，而无需事先存在
夹具登记条目；该工具必须保存并立即被检查。已知封装放置与填铜有可选的精确已保存
状态验证器；陌生操作返回 `OPERATION_EXECUTED_NEEDS_POSTCHECK`，不能自动通过后续
工程门禁。no-op 操作返回 `NO_SAVED_CHANGE_REVIEW_REQUIRED`。超时、保存失败或意外
变更必须停止；重试前先检查真实编辑器。L3 删除、重建与脚本执行仍仅限隔离夹具。该
后端的通用 `invoke` 仍是**面向 PCB 文件**的；尚未验证其可作为通用原理图 GUI 调度器。
KiCad ERC/DRC 与工程师审查保持独立。
