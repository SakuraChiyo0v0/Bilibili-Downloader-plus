# Bilibili Downloader Plus

**在 Bili23 Downloader 基础上，增加持续同步、音频整理与 WebDAV 存储。**

[![Release](https://img.shields.io/github/v/release/SakuraChiyo0v0/Bilibili-Downloader-plus?style=flat-square)](https://github.com/SakuraChiyo0v0/Bilibili-Downloader-plus/releases)
[![Quality](https://github.com/SakuraChiyo0v0/Bilibili-Downloader-plus/actions/workflows/quality.yml/badge.svg)](https://github.com/SakuraChiyo0v0/Bilibili-Downloader-plus/actions/workflows/quality.yml)
[![License](https://img.shields.io/github/license/SakuraChiyo0v0/Bilibili-Downloader-plus?style=flat-square)](LICENSE)

**简体中文** · [English](README_en.md) · [下载增强版](https://github.com/SakuraChiyo0v0/Bilibili-Downloader-plus/releases) · [反馈问题](https://github.com/SakuraChiyo0v0/Bilibili-Downloader-plus/issues) · [更新记录](CHANGELOG.md)

## 致谢与项目定位

本项目 fork 自 **[ScottSloan / Bili23-Downloader](https://github.com/ScottSloan/Bili23-Downloader)**。视频解析、下载引擎、桌面界面及大部分基础能力来自 Scott Sloan 和上游贡献者。感谢他们持续维护这款开源工具。

Plus 的定位是**增强上游能力**：跟随上游版本与设计，在现有下载流程之上补充功能。遇到实现重叠或冲突，优先采用上游方案，再适配增强功能。这里主要介绍 Plus 增加了什么；登录、画质、字幕、命名规则等通用操作请查阅[上游文档](https://bili23.scott-sloan.cn/)。

当前源码基于上游 **2.20.0**，增强版标识为 **`2.20.0+plus.1`**。本文介绍当前源码，安装包实际包含的能力请以对应 Release 说明为准。

## Plus 增加了什么

| 能力 | 具体用途 |
| --- | --- |
| **持续同步下载** | 将收藏夹、合集或番剧保存为同步源，定期检查新增条目，并按该源保存的选项创建下载任务。 |
| **音频封面与标签** | 为纯音频文件嵌入封面，写入标题、UP 主和原视频链接，便于播放器识别与后续查找来源。 |
| **音频转 MP3** | 在上游音频处理流程上扩展 M4A／FLAC 转 MP3，保留启用的封面与标签。 |
| **WebDAV 存储** | 先在本地下载并完成媒体处理，再上传成品及选定的附加文件；支持远程目录、同名处理和上传成功后的本地清理。 |
| **按源保存下载选项** | 同步源可独立保存画质、音频、附加内容、命名选择和本地路径，后台任务使用创建时确定的选项。 |

多线程下载、断点续传、网络错误重试、多类型解析、章节、字幕、命名编辑器等基础能力继续沿用上游。音频标签、音频封面和远程存储需要自行启用；默认使用本地存储。

## 下载与更新

**[前往本仓库 Releases 下载增强版 →](https://github.com/SakuraChiyo0v0/Bilibili-Downloader-plus/releases)**

- 按自己的操作系统选择该次发布提供的安装包或便携包；平台覆盖以 Release 附件为准。
- 新增强版使用 `上游版本+plus.修订号`，例如 `2.20.0+plus.1`；历史发布可能尚未采用后缀。
- 应用内“检查更新”检查本仓库的增强版发布，支持同一上游版本下的 Plus 修订更新。
- 上游安装包请从[上游 Releases](https://github.com/ScottSloan/Bili23-Downloader/releases)获取；它们不包含本仓库的全部增强功能。

| 示例 | 含义 |
| --- | --- |
| `2.20.0+plus.1` | 基于上游 2.20.0 的第 1 次 Plus 修订 |
| `2.20.0+plus.2` | 仍基于 2.20.0，更新 Plus 功能或修复 |
| `2.21.0+plus.1` | 跟随上游 2.21.0 后重新开始 Plus 修订编号；仅为命名示例 |

升级遵循上游配置迁移逻辑：**从旧版本升级至 2.20.0 时，命名规则会重置，需要重新设置。** 升级前建议保留重要配置；已有下载文件不属于命名规则重置范围。

## 使用增强功能

### 持续同步

有两种入口，首次行为不同：

1. **下载并同步**：先解析收藏夹、合集或番剧，选择需要下载的条目，再选择“下载并同步”。所选内容会先创建下载任务，并保存同步源。
2. **手动添加同步源**：在“同步”页面添加链接并编辑下载选项。当前内容会作为已知基线保存，**不会立即下载已有全部内容**；后续检查再处理新增条目。

程序运行期间每 **30 分钟**检查一次已启用的同步源，也可在同步页面立即检查、停用、删除或修改选项。程序关闭后不会继续执行同步。创建失败的条目保留重试机会，不会因为一次错误而被当作已经处理。

同步是新增内容的下载，不会把远端删除操作映射为本地删除。

### 音频整理

1. 在下载选项中选择只下载音频，需要时开启“音频转 MP3”。
2. 在设置的封面区域开启“下载封面”，选择 JPG／PNG 等支持嵌入的格式，再开启“嵌入音频封面”；标题和 UP 主标签、视频链接标签可分别在元数据区域开启。
3. 按需要选择嵌入后是否删除原封面文件。

输出格式决定标签的保存方式：**MP4／M4A 同时嵌入封面时，来源链接写入标准 `comment` 标签**，以保留封面；其他支持的路径使用 `video_url`。标签和封面的展示方式取决于播放器。

### WebDAV

1. 在“设置 → 下载”的存储区域选择 **WebDAV**。
2. 配置服务器地址、账号、密码和远程根路径，使用“测试连接”检查访问情况。
3. 选择本地缓存目录、同名文件处理方式，以及是否在上传成功后清理本地文件。
4. 正常创建下载任务；媒体处理完成后会显示上传进度，上传成功才记为完成。

WebDAV 仍需要本地空间完成下载与媒体处理。上传失败会保留本地成品，重试时直接上传；程序在上传中退出后，下次启动等待手动重试。

**已知限制：** 一项任务包含多个文件时，如果部分文件已上传、其余失败，整任务重试可能在“自动重命名”策略下生成远端重复文件。当前不提供逐文件断点续传。

## 问题反馈与贡献

请优先在[本仓库 Issues](https://github.com/SakuraChiyo0v0/Bilibili-Downloader-plus/issues)反馈 Plus 使用问题。涉及上游共性问题时，先确认是否能在相同基础版本的上游复现，再向上游提供精简复现步骤。

反馈时请附上：

- 完整版本号，例如 `2.20.0+plus.1`，以及操作系统；源码运行还请提供 commit。
- 相关选项、复现步骤、预期结果与实际结果。
- 必要的日志片段或截图；删除 Cookie、令牌、密码及私有服务器地址后再上传。

欢迎修复、测试与文档改进。提交增强功能时，请说明与上游行为的关系，并尽量复用上游已有流程。开发环境、测试和打包方式见 [BUILD.md](BUILD.md)。

## 开源许可与使用范围

项目代码遵循 [GNU GPL v3](LICENSE)。下载内容仅限个人学习、研究和非商业使用，请遵守内容授权与平台规则；程序不会绕过账号本身的访问权限或付费限制。使用者需自行承担使用产生的风险。

保留并感谢以下项目的贡献与来源说明：

- **[Bili23-Downloader](https://github.com/ScottSloan/Bili23-Downloader)** — 上游项目与主要作者 Scott Sloan。欢迎为上游点亮 Star，或通过[上游支持入口](https://bili23.scott-sloan.cn/doc/about.html)支持作者。
- **[bilibili-API-collect](https://github.com/SocialSisterYi/bilibili-API-collect)** — B 站接口与签名相关参考。
- **[PyStand](https://github.com/skywind3000/PyStand)** — Windows 启动器来源，遵循其 MIT 许可；上游定制说明见 [launcher/README.md](launcher/README.md)。
