# 可选的 Freerouting v2.5.0 适配器（实验性）

Freerouting 是单独安装的外部布线程序，不是强制捆绑的 Skill 依赖。适配器可以在明确的
工具/版本/规则验收下准备或验证有边界的 DSN→SES 交换；它不保证布线器的 SES 已被导入、
转换为真实 PCB 铜皮、保存并通过独立验证。在获认可的 Konnect 后端写入真实铜皮之前，
替代性的原生/脚本布线规划路径同样**只是提案**。

只有在核实所选板卡准确的源文件与工厂规则、受保护几何、差分/大电流/高速约束、层映射、
过孔余量以及实际外部可执行文件/构建之后，才可使用该适配器。在单独的候选板上验证布线
与掩膜规则的保真度。布线器不可用时，设计保持不变，并要求一份明确的、获认可的替代执行
计划；不得静默降级为未经验证的手工写入或 `pcbnew` 写入。

支持的命令细节请查看 `scripts/freerouting_adapter.py --help` 与
[布线契约](constraint-routing.md)。原生导入/保存/重载/DRC、G4 与工程师批准仍是独立
步骤。失败/部分布线/不支持的拓扑必须如实申报，绝不能计为已完成布线。

## R10 严格的候选板输入防护

v2.5.0 适配器额外支持 `--expected-dsn-sha256`、`--exclude-netclasses`、`--rules-file`
与 `--expected-rules-sha256`。使用 `--apply` 时，必须提供已审阅的 DSN SHA 以及非空的
受保护 NetClass 排除项。适配器会阻止静默自动发现的相邻 `<board>.rules`（除非显式
选中），并阻止规则哈希漂移。排除项使用官方的 `-inc` **NetClass** 机制，而不是裸网络
名；仅凭 DSN 中声明的类名存在，无法证明受保护网络的成员关系。实际的 KiCad NetClass
分配必须独立核实。调用此路径之前，请先审阅
[Freerouting-primary 布线契约](freerouting-primary-routing.md)；旧的预览与手工回退
不构成 G4 验收。
