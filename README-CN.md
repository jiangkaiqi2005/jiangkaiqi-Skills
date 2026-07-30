# Skills

[English](README.md) | 中文

这个仓库用于存放个人 AI Skills。根目录 README 只说明如何下载和安装；每个 Skill 文件夹内部会包含自己的 `SKILL.md`，必要时也会包含单独说明文档。

## 下载

任选一种方式即可。

### 方式一：使用 Git 克隆

```bash
git clone https://github.com/jiangkaiqi2005/jiangkaiqi-Skills.git
```

### 方式二：下载 ZIP

1. 打开 GitHub 仓库页面。
2. 点击 **Code**。
3. 点击 **Download ZIP**。
4. 将 ZIP 文件解压到本地。

## 安装

你可以安装整个仓库里的所有 Skill，也可以只安装需要的 Skill 文件夹。

### 安装到 Codex

将一个或多个 Skill 文件夹复制到 Codex 的 skills 目录：

```text
%USERPROFILE%\.codex\skills\
```

安装后的结构应该类似这样：

```text
%USERPROFILE%\.codex\skills\
└── skill-folder-name\
    └── SKILL.md
```

复制完成后，重启 Codex 或刷新 skills 列表。

### 安装到其他支持 Skill 的助手

将需要的 Skill 文件夹复制到该助手支持的 skills 目录即可。关键要求是：每个 Skill 都应保持为一个完整文件夹，并且文件夹内包含自己的 `SKILL.md`。

## 更新

如果你是用 Git 克隆的仓库：

```bash
git pull
```

如果你的助手不是直接读取这个仓库目录，请在拉取更新后，再把更新后的 Skill 文件夹复制到对应的 skills 目录。

如果你是下载 ZIP 安装的，请重新下载最新 ZIP，并替换旧的本地副本。

## 注意事项

- 尽量保持每个 Skill 为完整文件夹；除非你的助手明确支持，否则不要只复制单独的 `SKILL.md`。
- 添加或替换 Skill 后，如果新 Skill 没有出现，请重启或刷新助手。
- 具体 Skill 的使用方式，请查看对应 Skill 文件夹里的 README。
