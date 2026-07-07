# 构建文档

本文档说明如何在 Windows 本地从源码构建 Bili23 Downloader 安装包。流程与 `.github/workflows/publish.yml` 中的 Windows 发布任务保持一致：先准备静态 Python 运行时，再复制项目源码，最后用 Inno Setup 生成安装器。

## 构建产物

默认 Windows 10/11 x64 安装包：

```text
build/windows/Bili23-Downloader_<version>_windows_x64.exe
```

可选便携版：

```text
build/windows/Bili23-Downloader_<version>_windows_x64_portable.zip
```

可选 Windows 7 专用安装包：

```text
build/windows/Bili23-Downloader_<version>_windows_x64_for_win7.exe
```

## 环境要求

- Windows x64
- PowerShell 5 或更高版本
- 7-Zip，用于生成便携版 zip
- Inno Setup 6，用于生成安装器
- 可访问 GitHub，用于下载静态运行时和 Inno Setup 中文语言文件

如果使用 Scoop，可以这样安装工具：

```powershell
scoop bucket add extras
scoop install 7zip inno-setup
```

也可以从 Inno Setup 官网安装。只要命令行能找到 `iscc.exe` 即可验证成功：

```powershell
iscc.exe /?
```

## 准备 Inno Setup 中文语言文件

`assets/setup.iss` 中声明了 `zh_CN` 和 `zh_TW`，所以 Inno Setup 的 `Languages` 目录需要存在以下两个文件：

- `ChineseSimplified.isl`
- `ChineseTraditional.isl`

如果 Inno Setup 通过 Scoop 安装，可以执行：

```powershell
$InnoRoot = "$env:USERPROFILE\scoop\apps\inno-setup\current"
Invoke-WebRequest `
  -Uri "https://raw.githubusercontent.com/jrsoftware/issrc/refs/heads/main/Files/Languages/ChineseSimplified.isl" `
  -OutFile "$InnoRoot\Languages\ChineseSimplified.isl"
Invoke-WebRequest `
  -Uri "https://raw.githubusercontent.com/jrsoftware/issrc/refs/heads/main/Files/Languages/ChineseTraditional.isl" `
  -OutFile "$InnoRoot\Languages\ChineseTraditional.isl"
```

如果 Inno Setup 安装在 `C:\Program Files (x86)\Inno Setup 6`，请把 `$InnoRoot` 改为该目录。写入 `Program Files` 可能需要管理员权限。

## 构建 Windows 10/11 安装包

在仓库根目录执行以下脚本：

```powershell
$Version = "2.10.4"
$VersionName = "2.10.4"
$BuildDir = Join-Path (Get-Location) "build\windows"
$AppDir = Join-Path $BuildDir "Bili23-Downloader"
$RuntimeZip = Join-Path $BuildDir "windows_x64_runtime.zip"

New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null

Invoke-WebRequest `
  -Uri "https://github.com/ScottSloan/Python-Static/releases/download/v0.1.0/windows_x64_runtime.zip" `
  -OutFile $RuntimeZip

if (Test-Path $AppDir) {
  Remove-Item -Path $AppDir -Recurse -Force
}

Expand-Archive -Path $RuntimeZip -DestinationPath $AppDir -Force

New-Item -ItemType Directory -Force -Path "$AppDir\script" | Out-Null
Copy-Item -Path "src\*" -Destination "$AppDir\script" -Recurse -Force

Copy-Item -Path "LICENSE" -Destination "$BuildDir\LICENSE" -Force
Copy-Item -Path "assets\setup.iss" -Destination "$BuildDir\setup.iss" -Force

$SetupPath = Join-Path $BuildDir "setup.iss"
$Content = Get-Content $SetupPath -Raw
$Content = $Content -replace '(?m)^#define\s+MyAppVersion\s+".*?"', "#define MyAppVersion `"$Version`""
$Content = $Content -replace '(?m)^#define\s+MyAppVersionName\s+".*?"', "#define MyAppVersionName `"$VersionName`""
[System.IO.File]::WriteAllText((Resolve-Path $SetupPath), $Content, (New-Object System.Text.UTF8Encoding($false)))

& "$AppDir\runtime\python.exe" -m compileall $AppDir

Push-Location $BuildDir
iscc.exe setup.iss
Pop-Location
```

构建成功后，安装包会输出到：

```text
build/windows/Bili23-Downloader_2.10.4_windows_x64.exe
```

## 构建便携版 zip

安装包构建前后都可以生成便携版。确认 `build/windows/Bili23-Downloader` 已准备好后执行：

```powershell
$VersionName = "2.10.4"
Push-Location "build\windows"
7z a -tzip -mx=9 "Bili23-Downloader_${VersionName}_windows_x64_portable.zip" ".\Bili23-Downloader\*"
Pop-Location
```

## 构建 Windows 7 专用安装包

Windows 7 版使用单独的静态运行时。步骤与 Windows 10/11 版相同，只需要把运行时下载地址替换为：

```text
https://github.com/ScottSloan/Python-Static/releases/download/v0.1.0/windows_x64_runtime_for_win7.zip
```

`iscc.exe setup.iss` 生成的文件名仍然是 `Bili23-Downloader_<version>_windows_x64.exe`，构建完成后重命名：

```powershell
$VersionName = "2.10.4"
Rename-Item `
  -Path "build\windows\Bili23-Downloader_${VersionName}_windows_x64.exe" `
  -NewName "Bili23-Downloader_${VersionName}_windows_x64_for_win7.exe"
```

## 校验产物

生成安装包后建议记录文件大小和 SHA256：

```powershell
Get-Item "build\windows\Bili23-Downloader_2.10.4_windows_x64.exe" |
  Format-List FullName,Length,LastWriteTime

Get-FileHash "build\windows\Bili23-Downloader_2.10.4_windows_x64.exe" -Algorithm SHA256 |
  Format-List Algorithm,Hash,Path
```

## 常见问题

`iscc.exe` 找不到：

确认 Inno Setup 已安装，并且 `ISCC.exe` 或 Scoop shim 在 `PATH` 中。Scoop 安装后通常可以直接使用 `iscc.exe`。

提示 `ChineseSimplified.isl` 或 `ChineseTraditional.isl` 找不到：

按照“准备 Inno Setup 中文语言文件”下载语言文件到 Inno Setup 的 `Languages` 目录。

提示 `Source file ... not found`：

请确认 `iscc.exe setup.iss` 是在 `build/windows` 目录中执行。`setup.iss` 里的路径是相对当前目录的，需要同级存在 `Bili23-Downloader` 和 `LICENSE`。

本机 `python` 版本不一致：

构建发布包时不依赖系统 Python。请使用静态运行时自带的 `build/windows/Bili23-Downloader/runtime/python.exe` 执行 `compileall`。

安装后启动程序，只能看到 `C:`，看不到 `M:`、`Z:` 等映射盘：

这通常不是保存路径选择器的问题，而是 Windows 权限会话隔离导致的。安装器可能以管理员权限运行，如果安装完成后直接用管理员令牌启动 Bili23，程序就可能看不到普通用户会话里的盘符，例如 `subst M:`、rclone/FUSE 挂载的 `Z:` 或网络映射盘。

`assets/setup.iss` 的 `[Run]` 必须使用 `runasoriginaluser`，不要改回 `runascurrentuser`。这样安装完成后勾选“启动程序”时，会回到原始用户会话启动，才能看到用户态映射盘。验证时请先完全退出已经被管理员权限启动的 Bili23，再从开始菜单、桌面快捷方式或安装器的完成页重新启动。

## CI 发布流程

完整发布流程以 `.github/workflows/publish.yml` 为准。该 workflow 会同时构建：

- Windows 10/11 x64 安装版和便携版
- Windows 7 x64 专用安装版
- Linux amd64/arm64 便携版和 deb 包
- macOS x86_64/aarch64 dmg 包
