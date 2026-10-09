## Context

用户要求版本基础部分与上游一致、带增强版后缀，README 明确上游归属并以 fork 增量为主体；另确认应用内更新检查切换到本仓库发行。此前上游同步已在独立工作区准备好，尚未提交或发布。

## Goals / Non-Goals

目标：用户能识别增强版、找到对应安装包和反馈入口；同基础版本的 Plus 修订可正确更新；版本后缀不破坏平台打包。

不包含：创建 Release、推送标签、配置签名凭据、改动下载能力、迁移安装目录或重新设计上游界面。

## Decisions

- 使用 `2.20.0+plus.1`。`+plus.N` 符合 PyPA 本地版本标识形式；保留上游数字版本，Plus 修订按整数比较。预览版支持 `-rcN`，正式版优先于同基础版本的预览版。
- 版本解析在不依赖 Qt／配置的共用模块中实现，更新检查与发布脚本复用。配置格式版本仍为 2200，增强版修订不会额外触发命名规则迁移。
- 增强版查询固定仓库的 GitHub Releases；忽略草稿、无增强版后缀标签，并按现有预览开关过滤。跳过版本、手动检查、错误反馈仍使用上游交互。保留上游通道实现，但增强版网络失败不回落到上游。
- 应用显示、发行标签与文件名保留完整后缀；Windows／macOS 的数字字段使用基础版本。RPM Release 保存 Plus 修订，Debian 预览版使用 `~rcN` 以维持版本顺序。
- 发布预检验证标签与应用、pyproject 版本一致，防止文件名和实际程序版本不一致。
- README 中英文同步说明增量、首次同步行为、封面前置选项、WebDAV 本地空间和重试限制。上游作者、许可证、文档与支持入口保留，下载和反馈链接指向本仓库。

## References

- [PyPA 本地版本标识](https://packaging.python.org/en/latest/specifications/version-specifiers/#local-version-identifiers)
- [Debian 版本字段与排序](https://www.debian.org/doc/debian-policy/ch-controlfields.html#version)

## Validation

见同目录 validation.md。网络检查使用 httpx MockTransport，不创建真实发布，不调用签名服务。
