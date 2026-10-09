# 2.20.0+plus.1 发布记录

发布时间：2026-10-09 12:37（UTC+8）。

- [正式 Release](https://github.com/SakuraChiyo0v0/Bilibili-Downloader-plus/releases/tag/v2.20.0%2Bplus.1)，已设为 Latest，非草稿、非预览版。
- 标签 `v2.20.0+plus.1` 指向 [a2e0eb7f](https://github.com/SakuraChiyo0v0/Bilibili-Downloader-plus/commit/a2e0eb7fccb74ece58d24e2289d44051071855d0)。后续提交仅完善发布保护和记录，不改动该标签或产物。
- [最终构建](https://github.com/SakuraChiyo0v0/Bilibili-Downloader-plus/actions/runs/37884153259) 全部成功。
- [源码质量检查](https://github.com/SakuraChiyo0v0/Bilibili-Downloader-plus/actions/runs/37884152433) 的 Lint 和四组 Windows/Linux × Python 3.11/3.13 均通过；每组 748 passed、3 skipped。跳过项包括 runner 未提供的媒体工具检查，不据此声称完成所有实媒体验证。

## 发行内容

共 13 个安装／便携产物和 1 个 SHA256 清单：

| 平台 | 产物 |
| --- | --- |
| Windows x64 | 安装包、便携 ZIP、Win7 兼容安装包 |
| Linux amd64／arm64 | 每种架构分别提供便携 tar.gz、DEB、RPM、AppImage |
| macOS Intel／Apple Silicon | 每种架构一个 DMG |
| 校验 | SHA256SUMS.txt，覆盖全部 13 个产物 |

核对了全部 GitHub 服务端资产摘要与清单内容，并计算本地下载的 Windows 安装包、便携包 SHA256 确认一致。资产状态均为 uploaded。

## 实包检查

Windows 便携包中的 249 个内嵌 Python 源码模块与发布提交逐个匹配，669 个完整性清单条目的实际文件哈希全部一致。启动器产品版本为 `2.20.0+plus.1`。

使用实际启动器执行 `--mcp-stdio --no-launch` 并显式指定测试端口和令牌，确认无界面入口与内嵌源码加载正常，不读取用户真实配置。

随后使用产物自带 Python 3.13.13、PySide6 6.10.2、QFluentWidgets 1.11.3，在 Qt 测试模式与 offscreen 环境中构造同步页、关于页、下载选项及主窗口延迟页面。GUI 探针仅验证构造，输出结果后直接终止隔离进程；正常交互与完整退出没有作为已通过项目。

首轮草稿实包检查发现 `gui.interface.sync` 仍从已取消聚合导出的 `gui.component.widget` 导入 ToolButton。新增构造回归测试先复现 ImportError，再修正为直接从 button 子模块导入；相关 7 项测试通过后重建全部平台产物。旧草稿从未公开，最终全部资产来自修复提交。

## 签名与范围

- 仓库没有签名凭据。Windows 启动器与安装包检查结果为 NotSigned，Release 已明确标注；没有生成或借用上游签名。
- macOS 本次未执行 Apple 签名或公证。
- 未使用真实账号下载视频或执行真实 WebDAV 写入；未完成全部目标系统的安装、交互与退出验收，也没有 Win7 真机验证。

## 重复触发保护

正式发布创建标签后，GitHub 又触发了 [重复构建](https://github.com/SakuraChiyo0v0/Bilibili-Downloader-plus/actions/runs/37884778951)。该运行已取消，发布任务没有执行，正式资产保持不变。

随后增加 `scripts/release_guard.py`：同名发行已公开时输出 SHOULD_BUILD=false，三类平台任务均受此条件限制；404 允许首次构建，其他查询错误停止流程。保护与资产准备相关 9 项测试通过，Ruff 与 YAML 检查通过；针对本次公开发行的只读查询实际返回 SHOULD_BUILD=false。
