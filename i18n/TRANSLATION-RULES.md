# 翻译规则（kicad-pcb-ai-workflow 双语文档）

本文件约束 `i18n/zh-CN/` 下所有 `.zh.md` 翻译的生成与维护。
校验器：`python i18n/verify-pairing.py`（机制参考 deepseek-ai/deepseek-harness 的
verify-translation-pairing / CONTRIBUTING.i18n.yaml 约定）。

## 路径映射

英文原文保持原地不动（仓库内任意 `.md`，不含 `i18n/` 自身）。
中文译本放在 `i18n/zh-CN/` 下镜像同路径，后缀 `.zh.md`：

- `README.md` → `i18n/zh-CN/README.zh.md`
- `kicad-pcb-ai-workflow/SKILL.md` → `i18n/zh-CN/kicad-pcb-ai-workflow/SKILL.zh.md`
- `kicad-pcb-ai-workflow/references/x.md` → `i18n/zh-CN/kicad-pcb-ai-workflow/references/x.zh.md`
- `kicad-pcb-ai-workflow/references/high-speed/policy-format.md` → 同名 `.zh.md` 对应目录

## 翻译规则（校验器强制的部分）

1. **标题结构必须逐一对齐**：标题数量、层级、顺序与英文完全一致；标题文字译成中文。
2. **围栏代码块（``` 或 ~~~ 包裹）逐字节保持原样**，块内不翻译，块数量、顺序、内容
   与英文一致（含语言标注）。
3. `<!-- i18n:generated:start -->` … `<!-- i18n:generated:end -->` 之间的生成区域
   逐字节保持原样（一般不会遇到）。
4. YAML frontmatter：`name:` 的值保持英文原文不动；其余人类可读的值（如
   `description`）译成中文；YAML 键名不动。frontmatter 整体参与 preamble 哈希。

## 翻译规则（人工审校责任，校验器不查）

1. 简体中文，技术文档文风：简洁、准确、命令式指令保持祈使语气。
2. 术语保留英文：KiCad、Konnect、Freerouting、ERC、DRC、BOM、Gerber、SMD、THT、
   courtyard、SKILL.md、MCP、G1–G4、DSH、frontmatter、glob、git。silkscreen 译「丝印」。
3. 链接 URL 与锚点不改；链接文字可译。表格行数列数不变，单元格内文字可译。
4. 行内代码（反引号包裹）不翻译。
5. 数字、单位、路径、文件名、命令行、引号内的字符串字面量保持原样。

## 一致性跟踪（.i18n.yaml）

每个译本旁有同名 `.i18n.yaml` 账本：按英文标题的 slug 层级路径分节
（重复键加 `~2`），每节记录 en/zh 两侧 16 位 hex（sha256 前 64 位）哈希，
frontmatter 与代码块、生成区域之外的内容参与哈希。
改动任一侧后，重新生成账本：

```
python i18n/verify-pairing.py --write --all     # 全量重建账本
python i18n/verify-pairing.py                    # 只校验不写入
python i18n/verify-pairing.py --list             # 状态清单
```

校验器还会检查：两侧标题数一致；代码块逐字节一致；生成区域逐字节一致。

## 编码与换行

- 所有 md 文本统一 UTF-8；EOL 由根目录 `.gitattributes` 钉死为 LF
  （`*.md text eol=lf`、`i18n/** text eol=lf`），不受 core.autocrlf 影响。
- 校验器在哈希前先把 `\r\n` 归一为 `\n`，因此 CRLF 工作区副本不会产生假差异；
  `.gitattributes` 保证落盘与仓库层面一致，双保险。
- fixtures（development/fixtures/**）是字节级证据文件，`.gitattributes` 末尾的
  `-text` 例外行必须保持最后，任何新通配规则不得覆盖它。
