# DFX/NPI 与制造候选

当用户要求**工程导出**时，阅读 [导出经验教训](engineering-export-lessons.md)：核实当前的来源快照与实际文件，识别尚未解决的采购/工艺证据，并保留 `EXPORTED_NOT_RELEASED` 状态。这种有限的导出检查并不代表下文所述的正式冻结交接、工程师签字或工厂发布关卡已经通过。已完成的示例导出不得描述成一次完整的正式 NPI 运行。

在任何正式制造导出之前，独立验证当前的 G1–G4、网表/板版本、板厂叠层、生效规则、BOM/CPL 变体、焊盘/极性、测试点、机械轮廓、制造/装配工艺极限以及适用的 SI/PI 或安全结论。`mass_production_review.py` 与 `static_review_gate.py` 必须消费完整证据，即使 agent 看到的只是简短摘要。

用有据可查的 Konnect 铜区填充/保存回执以及独立的 KiCad CLI 重新加载/DRC，冻结一个**新的隔离候选**。只有在相关关卡通过之后，`manufacturing_export.py` 才能生成 Gerber、Excellon 钻孔、BOM、CPL 与图纸；哈希必须绑定到确切保存的来源候选。导出成功只意味着 `EXPORTED_NOT_RELEASED`，绝不等于自动获得工厂批准。真实的工厂 CAM、工程查询（EQ）、拼板/装配审查与生产授权需要实际的外部证据与人工签字。

参见 [DFX/NPI 细节](dfx-npi.md)、[最新工作流](latest-complete-workflow.md) 与 [阶段审批](stage-approvals.md)。
