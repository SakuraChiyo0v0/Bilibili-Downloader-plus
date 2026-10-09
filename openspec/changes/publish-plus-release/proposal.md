## Why

用户明确要求构建并上传最新增强版 Release。当前源码版本为 2.20.0+plus.1，尚未发布。继承的 Windows 流程依赖上游签名凭据，本 fork 没有配置，需要兼容未签名构建并真实验证发行产物。

## What Changes

- 将已确认的 AGENTS.md 开发规范纳入发行源码。
- 签名凭据存在时保留签名流程，缺失时构建未签名 Windows 包并明确标注。
- 使用现有平台矩阵构建 Windows、Linux、macOS 产物，生成 SHA256 校验文件和增强版发布说明。
- 全部构建成功后准备草稿 Release，核对产物后正式发布为最新版。
- 修复本次构建和验证发现的必要发布问题，不改变业务功能定位。

## Capabilities

### New Capabilities
- `plus-release-delivery`: 具备产物验证和明确签名状态的增强版发布流程。

### Modified Capabilities

无。

## Impact

涉及发布工作流、构建验证、变更记录和发布操作。只向本 fork 提交和发布，不向上游创建 PR；不上传个人配置、账号数据或本地知识库。
