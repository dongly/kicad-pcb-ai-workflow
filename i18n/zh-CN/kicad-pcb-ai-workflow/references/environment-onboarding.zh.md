# 环境配置与日常操作

## 前置条件

使用真实的 KiCad 安装，以及与目标项目兼容的 `kicad-cli`；只有进行实时操作时，才需要单独许可并在本机注册的 Konnect MCP 可执行程序，以及可访问的 KiCad 编辑器。Python 标准库脚本可在隔离解释器中运行；提取源 PDF 文本可能需要 `pdftotext`。不要从 PyPI 安装来路不明的 `pcbnew` wheel 来替代与 KiCad 匹配的旧版 Python 绑定。在单写入者迁移期间，旧版 `pcbnew` 对某些只读审计可以是可选项，但不得用作授权的电路板写入器。

## 首次安装与冒烟测试

确认实际操作系统、安装路径、CLI 版本、KiCad 应用版本、可执行文件 SHA-256、Konnect 后端构建版本及许可证。对于稳定版 KiCad 10.x，应在真实、独立且非空的候选项目上运行原生冒烟测试，并按任务要求检查原理图 XML/PDF、ERC/DRC、PCB 重新加载以及制造命令的可用性。对于 KiCad 11+，不要假设旧版 SWIG `pcbnew` 可用：仅 CLI 冒烟测试或许允许范围受限的源代码任务，但不会自动授权 PCB 写入、冻结或制造审批。KiCad 9 的兼容性状态另有限制，除非经过独立验证。未来的版本号本身不能证明兼容性。

```bash
# Read-only environment diagnosis without creating an engineering project.
python scripts/workflow.py run /project --task environment.doctor
# Setup requires a real independent project and, for mutations, explicit --apply.
python scripts/workflow.py run /project --task environment.setup --cli-only
# See actual supported arguments for the installed version.
python scripts/environment_start.py --help
```

## 日常工作（仅进行必要调用）

对于常规 MCP 可用性检查，尝试一次受支持的协议 ping 或轻量级读取；若要确认真实 KiCad 项目连接，则使用预期的电路板路径执行一次 `open_project` 查询。成功后立即停止。不要为了连接 ping 自动重启软件、安装插件、打开新的测试板、发现全部 200 多个工具、截取桌面截图或运行 DRC。如果连接失败，检查返回的失败类别，然后先做一次有针对性的诊断，再考虑更改。

编辑时，读取工作区索引并确认 `01_WORKING` 是获授权的项目。Konnect 操作验收与环境冒烟测试分别记录；已保存的当前项目也需要单独进行原生验证。如果 CLI 可执行文件、服务构建版本、连接凭据/目标板、项目 schema 或规则发生变化，并使相关既有证据失效，则应重新运行设置流程。绝不能复制其他用户的启动状态文件或人工审批记录。

## 调试与跨平台说明

在 Windows PowerShell、Linux 或 macOS 上使用实际的本机 KiCad 与 Python 路径。不要臆造平台目录；应通过 `--version`/`--help` 和用户提供的安装信息检查已安装二进制文件。不同解释器、nightly/RC 版本以及混用的 KiCad 库都需要明确的独立测试。命令和导出/报告 schema 可能因版本而异。如果缺少所需能力，应准确说明受阻范围，不要把离线模拟误称为已通过真实原生验证。

相关内容：[环境模块](module-environment.md)、[Konnect 后端](konnect-backend.md)、[工作区策略](workspace-and-token-policy.md)、[KiCad 原生验证](static-ai-review.md)。
