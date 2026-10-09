## Why

用户要求在仓库根目录建立 AGENTS.md，集中保存已确认的开发理念和规范，供后续开发持续遵循。此前定位分散在 README 和会话记录中，缺少面向开发工作的统一入口。

## What Changes

- 新增根目录 AGENTS.md，适用于本仓库开发工作。
- 固化独立维护、不向上游发起 PR、上游基础能力优先以及稳定性／完整性／效率原则。
- 整理任务范围、版本、同步与媒体安全、验证、文档维护和 Git 授权边界。
- 通过相对链接引用现有 README、BUILD 和工具入口，不复制易变的版本与测试结果。

## Capabilities

### New Capabilities
- `project-guidelines`: 开发理念、工程约束和授权边界的统一入口。

### Modified Capabilities

无。

## Impact

仅新增开发规范及本次 OpenSpec 文档，不修改运行行为、全局工具设置、Git 身份或发布配置。不提交、推送或发布。
