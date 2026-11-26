# 只读 KiCad IPC 连接与板卡快照

IPC 是通往*正在运行*的 PCB 编辑器的技术性读取桥，不是对另一个写入后端的自动批准。
当前 Skill 可以在受支持的情况下探测 KiCad 编辑器可用性、所选板卡路径、板卡状态与
只读封装/焊盘。用户保存之前，磁盘上已保存的项目与内存中的活动板卡可能合法地不同；
要记录双方身份，不得用过期快照覆盖其中任何一方。

只有在明确请求活动诊断时，才使用具体的 `kicad_ipc_probe.py` 命令/帮助或 `workflow.py`
环境 IPC 任务。常规连接问题用一次轻量 Konnect 请求成本更低，无需抓取完整板卡转储。
如果 IPC 无法连接，记录返回的错误并做有限诊断；绝不静默安装实验性插件或创建测试板。

IPC 兼容性按版本限定范围；较旧的 KiCad SWIG 绑定可能已弃用/不存在。不得由可用的
只读 IPC 探测推断它授权 `pcbnew` 或自研桥接写入。在获批的单写入者策略下，所有活动
KiCad 修改都属于 Konnect MCP；最终原生验证使用已保存的项目与 KiCad CLI。

参见[历史受控编辑](controlled-editing.md)、[当前 Konnect 后端](konnect-backend.md)
与[环境搭建](environment-onboarding.md)。
