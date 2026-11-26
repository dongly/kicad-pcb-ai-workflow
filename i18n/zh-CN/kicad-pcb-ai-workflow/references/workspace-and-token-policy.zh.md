# R10 工作区生命周期与上下文预算策略

## 目的与限制

保持一个可识别的 KiCad 工作项目，并减少重复摄取上下文，同时不削弱 G1–G4 或最终制造控制。`workspace_manager.py` 会索引项目文件与不可变证据；它不会静默创建电路、调用 Konnect、运行 KiCad CLI、移动历史目录、清理文件或授予任何工程审批。

## 规范项目布局

```text
PROJECT_ROOT/
  01_WORKING/                 One actively edited KiCad project
    main.kicad_pro
    main.kicad_sch
    main.kicad_pcb             Optional during schematic-only work
  02_CHECKPOINTS/             Explicit immutable milestone copies
  03_REPORTS/                 Immutable ERC/DRC and G1-G4 evidence
    index/                    References and hashes, not report duplicates
  04_RELEASE/                 Immutable manufacturing candidates
  CURRENT_PROJECT.json        Authoritative project location and revision
```

对于现有项目，首先创建独立备份，并确认选定的完整 KiCad 项目及其引用的全部库。明确地将其放到 `01_WORKING` 下，然后运行工作区初始化。绝不要根据最新修改时间推断权威项目。遵循此约定之外的历史项目继续受原有的禁止覆盖保护；新索引绝不授权盲目替换。

## 何时创建候选项目

仅在首次生成、显式分支、不可逆/高风险夹具工作、具名工程检查点或制造冻结时创建候选项目。在已授权的工作会话中，常规器件移动、布线和元件编辑都应在同一个 KiCad 项目上进行。核实目标路径、UUID/网络/封装身份以及前后哈希；采用适当的 Konnect 风险接受流程并读取回验。构建一个配置包，并在其来源、工具和规则指纹仍然有效时重复使用。新的审查数据包在 `03_REPORTS` 下不可变保存；在索引中记录报告哈希和项目修订。

制造冻结时不得递归复制 `02_CHECKPOINTS`、`03_REPORTS`、`04_RELEASE`、先前候选项目、代码仓库或其他历史树。确认复制后的源原理图、PCB、项目设置和所需相对库资源仍完整。保留所有历史文件；绝不自动删除或移动它们。

## CLI

```bash
python scripts/workflow.py workspace /project --action init --project-file 01_WORKING/main.kicad_pro --apply
python scripts/workflow.py workspace /project --action status
python scripts/workflow.py workspace /project --action checkpoint --label G1-approved --apply
python scripts/workflow.py workspace /project --action register --stage G1 --artifact 03_REPORTS/G1-r1/packet.json --apply
python scripts/workflow.py workspace /project --action index --stage G1
python scripts/workflow.py workspace /project --action inventory --limit 20
python scripts/workflow.py status /project --bundle control-r1 --format compact
```

## AI 上下文规则与度量

1. 阅读 `SKILL.md` 和一个选定模块。仅在任务需要时才阅读完整工作流、DFX、高速和制造参考资料。简单操作不要加载所有工具集。
2. 将原始源 PDF、网表、原生 ERC/DRC 输出及完整审查数据包保存在磁盘上。首先向 AI 提供有界的 `checks_summary`、工件路径、选定的当前阶段器件卡摘录及哈希。对于确切受影响的网络、引脚、来源页面、高风险发现或例外，再读取完整证据。
3. Konnect 能力发现必须保持动态完整；任务只应加载必要的工具集。重复使用仍有效且绑定构建/schema 的能力记录。
4. `workflow status --format compact` 显示计数与优先级最高的缺失项。完整调试时切换到 JSON 输出。
5. `token_budget.py --input REPORT --limit 6` 会优先显示失败/阻塞发现，并显示省略项总数；绝不能把隐藏的失败重新标记为 PASS。门禁始终处理完整原始证据。
6. 只有模型宿主的实际用量统计才能证明输入/输出 token 节省。文件字节/字符数只是代理指标，不能普遍可靠地换算；对每种 tokenizer 来说，英文也不一定总是更省。

## 验收与回滚

连续十次小型编辑应始终使用一个工作项目；创建检查点必须显式执行。失败、来源身份不明确或 GUI 中存在未保存的冲突状态时，必须阻止后续写入。新指令或规则修订可能使旧配置包哈希失效；应重建受影响的快照，而不是替换已签名记录。保留完整审计轨迹；只有在进行真实 KiCad/Konnect 端到端测试后，才能声称已完成实时编辑。
