# 环境、连接与工作区

**最小优先的检查：** 例行 MCP 健康检查使用受支持的协议 ping 或一个已经暴露出来的只读调用，例如 `get_active_toolsets`。KiCad 连通性检查使用一次 `open_project` 查询（如果提供了请求的板子路径就一并带上）。连接检查成功*不等于*操作能力验收，也不能证明原生文件正确。

解读返回的事实：`ipc_available=true` 且打开了匹配的板子表示 KiCad IPC 已连通；没有打开的板子只是普通的未打开状态；`ipc_available=false` 需要查看上报的 `ipc_failure`；板子路径不同则是目标不匹配。不要为了检查连接就自动启动应用、切换板子、截取桌面、创建测试板、运行 DRC 或安装插件。

如果某次调用失败，用其实际错误再选择**一个**有针对性的只读诊断。不要运行无界的重装/重连循环，也不要重复整套工具集的发现流程。首次安装、新的 Konnect 二进制、新的高危操作或原生来源验证可能需要文档化的 doctor/setup 流程与限定范围的能力夹具。

当前工作项目通过 `workflow.py workspace ...` 登记；增量编辑前务必先检查 `CURRENT_PROJECT.json`。完整的本地验收参见 [Konnect 后端](konnect-backend.md)、[动态能力](konnect-capability-migration.md) 与 [环境搭建](environment-onboarding.md)。`--apply` 只用于明确授权的写入；绝不从只读检查推断源文件写入权限。
