# Bilibili Downloader Plus

**Continuous sync, audio library features, and WebDAV storage built on Bili23 Downloader.**

[![Release](https://img.shields.io/github/v/release/SakuraChiyo0v0/Bilibili-Downloader-plus?style=flat-square)](https://github.com/SakuraChiyo0v0/Bilibili-Downloader-plus/releases)
[![Quality](https://github.com/SakuraChiyo0v0/Bilibili-Downloader-plus/actions/workflows/quality.yml/badge.svg)](https://github.com/SakuraChiyo0v0/Bilibili-Downloader-plus/actions/workflows/quality.yml)
[![License](https://img.shields.io/github/license/SakuraChiyo0v0/Bilibili-Downloader-plus?style=flat-square)](LICENSE)

[简体中文](README.md) · **English** · [Download Plus](https://github.com/SakuraChiyo0v0/Bilibili-Downloader-plus/releases) · [Report an issue](https://github.com/SakuraChiyo0v0/Bilibili-Downloader-plus/issues) · [Changelog](CHANGELOG.md)

## Upstream and project scope

This project is a fork of **[ScottSloan / Bili23-Downloader](https://github.com/ScottSloan/Bili23-Downloader)**. Video parsing, the download engine, the desktop interface, and most core features come from Scott Sloan and the upstream contributors. Thank you for maintaining this open-source tool.

Plus is an **independently maintained fork for specific workflows**. It grows from the maintainer’s personal needs for media organization, continuous sync, and remote storage. These needs may not suit a general-purpose downloader and do not represent upstream’s direction.

We continue to follow upstream releases and core design decisions, prefer upstream implementations when changes overlap, and adapt our additions accordingly. **Changes from this repository are reviewed, merged, and released here; we do not open pull requests against upstream.** Upstream attribution and synchronization remain part of this independent maintenance model.

For login, quality selection, subtitles, naming rules, and other core features, see the [upstream documentation](https://bili23.scott-sloan.cn/). This README focuses on the Plus additions and how to use them.

The current source is based on upstream **2.20.0**, identified as **`2.20.0+plus.1`**. This document describes the source branch; check each Release for features included in published packages.

## Maintenance priorities

- **Stability first:** protect existing download and data-handling behavior, with attention to recovery and regression tests for critical paths.
- **Complete workflows:** address a concrete need through configuration, execution, status reporting, and retries, so an added feature is usable end to end.
- **Efficiency as a constraint:** consider runtime performance, resource use, and maintenance cost. Feature count is not a growth target.

Specialized workflows may require additional options and more complex processing. We accept complexity that serves a clear purpose and aim to contain it within explicitly enabled enhancements. Users who only need general downloading capabilities can choose upstream directly.

## What Plus adds

| Feature | What it does |
| --- | --- |
| **Continuous sync** | Save a favorites list, collection, or series as a sync source. Check for new entries and create downloads using that source’s saved options. |
| **Audio covers and tags** | Embed cover art in audio-only files and write the title, uploader, and source video URL for playback and source tracking. |
| **Audio to MP3** | Extend upstream processing to convert M4A/FLAC audio to MP3 while retaining enabled cover art and tags. |
| **WebDAV storage** | Download and process files locally, then upload finished media and selected sidecar files. Configure the remote directory, filename conflicts, and optional local cleanup after upload. |
| **Per-source download options** | Keep quality, audio, sidecar, naming, and local path choices for each sync source. Queued tasks use options captured at creation. |

Core capabilities—including multithreaded downloads, resume, network retries, parsing, chapters, subtitles, and the naming editor—remain upstream implementations. Audio tags, audio covers, and remote storage are opt-in. Storage defaults to local.

## Downloads and updates

**[Download the enhanced edition from this repository’s Releases →](https://github.com/SakuraChiyo0v0/Bilibili-Downloader-plus/releases)**

- Choose a package for your operating system from the assets provided by that release. Available platforms depend on the release.
- New enhanced builds use `upstream-version+plus.revision`, such as `2.20.0+plus.1`. Older releases may predate this convention.
- In-app update checks use this repository’s enhanced releases, including Plus revisions on the same upstream base.
- Original packages are available from [upstream Releases](https://github.com/ScottSloan/Bili23-Downloader/releases); they do not contain all additions from this fork.

| Example | Meaning |
| --- | --- |
| `2.20.0+plus.1` | First Plus revision based on upstream 2.20.0 |
| `2.20.0+plus.2` | Further Plus changes on the same upstream base |
| `2.21.0+plus.1` | Plus numbering restarts after adopting upstream 2.21.0; naming example only |

We follow upstream configuration migrations. **Upgrading an older installation to 2.20.0 resets naming rules; configure them again after upgrading.** Keep a copy of important settings before upgrading. Resetting naming rules does not remove previously downloaded files.

## Using the additions

### Continuous sync

The two entry points have different initial behavior:

1. **Download and Sync:** parse a supported source, select entries, and choose this action. Selected entries are queued for download and the source is saved.
2. **Add a sync source manually:** enter its link on the Sync page and edit its download options. Current entries become the known baseline; **existing content is not downloaded immediately**. Later checks handle new entries.

Enabled sources are checked every **30 minutes while the application is running**. The Sync page also provides immediate checks, enable/disable controls, deletion, and option editing. Sync does not run after the application exits. Entries whose download tasks could not be created remain eligible for retry.

Sync downloads new content. It does not mirror remote deletions to local files.

### Audio library features

1. Select audio-only downloading and enable audio-to-MP3 conversion if needed.
2. Enable **Download Cover**, select an embeddable format such as JPG/PNG, then enable **Embed Audio Cover**. Media tags and source URL tags have separate switches under metadata settings.
3. Choose whether the original cover image should be removed after successful embedding.

Tag storage depends on the output format: **MP4/M4A with embedded cover art stores the source URL in the standard `comment` tag** to preserve the cover. Other supported paths use `video_url`. How covers and tags are displayed depends on your player.

### WebDAV

1. Choose **WebDAV** in the storage section of download settings.
2. Enter the server URL, credentials, and remote base path, then use **Test Connection**.
3. Select a local cache folder, filename conflict policy, and whether local files should be cleaned up after upload.
4. Create downloads normally. Upload progress appears after media processing, and a task completes only after a successful upload.

Local disk space is still required for downloading and processing. Upload failures retain local outputs; retries upload those outputs directly. If the application exits during an upload, it waits for a manual retry on the next launch.

**Known limitation:** when some files in a task have uploaded successfully and a later file fails, retrying the whole task with automatic renaming may create duplicate remote files. Per-file upload checkpoints are not currently supported.

## Feedback and contributions

Please report Plus issues and feature requests in [this repository’s Issues](https://github.com/SakuraChiyo0v0/Bilibili-Downloader-plus/issues); they are handled independently here. If you also tested the corresponding upstream version, include that comparison to help identify the source of the issue.

Include the full version, operating system, relevant settings, reproduction steps, expected and actual behavior, and useful log excerpts or screenshots. Source users should include the commit. Remove cookies, tokens, passwords, and private server addresses before posting.

Fixes, tests, and documentation contributions to this repository are welcome. Describe the specific workflow, its relationship to upstream behavior, and the implications for stability and resource use. Reuse existing workflows where possible. Plus-specific needs evolve here without asking upstream to take on their complexity or maintenance cost. See [BUILD.md](BUILD.md) for development, testing, and packaging instructions.

## License and attribution

The code is distributed under the [GNU GPL v3](LICENSE). Downloaded content is intended for personal learning, research, and non-commercial use. Respect content permissions and platform rules; the application does not bypass account access restrictions or paywalls. Users are responsible for risks arising from their use.

We retain and acknowledge these project credits:

- **[Bili23-Downloader](https://github.com/ScottSloan/Bili23-Downloader)** — upstream project by Scott Sloan. Consider starring upstream or visiting its [support page](https://bili23.scott-sloan.cn/doc/about.html).
- **[bilibili-API-collect](https://github.com/SocialSisterYi/bilibili-API-collect)** — API and signing references.
- **[PyStand](https://github.com/skywind3000/PyStand)** — Windows launcher origin, under its MIT license. See [launcher/README.md](launcher/README.md) for upstream customizations.
