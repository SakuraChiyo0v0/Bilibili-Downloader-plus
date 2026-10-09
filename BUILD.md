# 构建与验证

当前代码跟随上游 2.20.0。Windows 构建已改为将应用源码和完整性清单嵌入启动器，旧版“复制 src 到 script 目录”的 2.10.4 构建方式不再适用。

## 版本与发行标签

应用和 `pyproject.toml` 使用完整增强版版本，例如 `2.20.0+plus.1`。每次 Plus 修订递增后缀，跟随新的上游基础版本时从 `plus.1` 重新开始。标签使用 `v2.20.0+plus.1`；预览版可使用 `v2.21.0-rc1+plus.1`，并在 GitHub 标记为预览发布。

`+plus.N` 采用 [PyPA 的本地版本标识格式](https://packaging.python.org/en/latest/specifications/version-specifiers/#local-version-identifiers)，用于区分基于同一上游版本的下游改动。

发布工作流通过 `scripts/release_version.py` 校验标签与源码版本一致。`VERSION_NAME` 保留完整后缀供文件名使用，`VERSION` 为纯数字上游基础版本供平台元数据使用；RPM 将增强版修订写入 `Release`。Windows 启动器显示完整产品版本，数值资源与 manifest 使用四段数字。安装器的 `MyAppVersion` 为基础版本，`MyAppVersionName` 为完整版本。

Debian 包使用 `DEB_VERSION`：正式版仍为 `2.20.0+plus.1`，预览版转换为 `2.21.0~rc1+plus.1`，按 [Debian 版本排序规则](https://www.debian.org/doc/debian-policy/ch-controlfields.html#version)确保预览版先于正式版。

只检查元数据，不构建或发布：

```powershell
& ./.venv/Scripts/python.exe scripts/release_version.py 'v2.20.0+plus.1'
```

标签本身不会替代应用版本修改：先更新版本字段与变更记录，再由已获授权的发布流程创建发行。应用更新仅识别本仓库带 `+plus.N` 的发布，草稿和无后缀的历史版本不会成为增强版更新候选。

## 源码环境

项目最低要求 Python 3.11，上游质量检查使用 Python 3.11 和 3.13。请在仓库根目录建立独立环境，依赖版本以 `requirements.txt` 和 `pyproject.toml` 为准。

```powershell
python -m venv .venv
& ./.venv/Scripts/python.exe -m pip install -r requirements.txt pytest==9.1.1 ruff==0.16.7
```

正常启动会读取并升级当前用户配置，包括上游 2.20.0 的命名规则重置。开发验证请先运行隔离测试；不要用真实账号、同步源或 WebDAV 目录做自动化测试。

## 自动化验证

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
& ./.venv/Scripts/python.exe -m ruff check src test
& ./.venv/Scripts/python.exe -m pytest
```

`test/conftest.py` 在导入应用前启用 Qt 测试模式，使配置和数据库写入测试目录。该目录在每轮测试前清理，同一主机上的测试进程应串行运行。

## 翻译与资源

```powershell
$env:PATH = "$(Join-Path $PWD '.venv/Scripts');$env:PATH"
& ./.venv/Scripts/python.exe scripts/translate.py
& ./.venv/Scripts/pyside6-lrelease.exe src/res/i18n/bili23.zh_CN.ts
& ./.venv/Scripts/pyside6-lrelease.exe src/res/i18n/bili23.zh_TW.ts
& ./.venv/Scripts/pyside6-rcc.exe src/res/resources.qrc -o src/res/resources_rc.py
```

先翻译新增的 `.ts` 条目，再生成 `.qm` 和 `resources_rc.py`，三者应保持一致。

## Windows 启动器

构建入口为上游的 `scripts/build_release.ps1`，需要 Python、CMake、Windows C++ 编译工具，以及解压后的 Windows 静态运行时模板。当前发布流程使用 `ScottSloan/Python-Static` 的 `v0.1.9` 模板。

```powershell
.\scripts\build_release.ps1 -RuntimeDir <已解压的运行时模板目录> -OutputDir .\release
```

脚本先打包源码、生成清单，再编译 `launcher`，输出未签名的 `release/Bili23.exe`。`OutputDir` 会被重新创建，应只指定专用构建目录，不能指向源码、运行时输入或个人数据目录。

安装包使用 `assets/setup.iss`。版本替换、语言包、Windows 签名以及各平台打包步骤以 `.github/workflows/publish.yml` 为准。签名依赖仓库的 `signing` 环境与相应凭据，fork 不能默认复用上游凭据。本次同步只验证源码，不执行发布流程。
