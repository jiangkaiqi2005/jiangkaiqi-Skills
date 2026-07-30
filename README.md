# Skills

English | [中文](README-CN.md)

This repository contains personal AI skills. The root README only explains how to download and install them. Each skill folder contains its own `SKILL.md` and, when needed, its own documentation.

## Download

Choose one method:

### Option 1: Clone with Git

```bash
git clone https://github.com/jiangkaiqi2005/jiangkaiqi-Skills.git
```

### Option 2: Download ZIP

1. Open the GitHub repository page.
2. Click **Code**.
3. Click **Download ZIP**.
4. Extract the ZIP file locally.

## Install

Install either the whole collection or only the skill folders you need.

### Install for Codex

Copy one or more skill folders into your Codex skills directory:

```text
%USERPROFILE%\.codex\skills\
```

Each installed skill should look like this:

```text
%USERPROFILE%\.codex\skills\
└── skill-folder-name\
    └── SKILL.md
```

Restart Codex or refresh the skills list after copying.

### Install for Other Skill-Compatible Assistants

Copy the desired skill folder into the assistant's supported skills directory. The important requirement is that each skill remains a complete folder containing its own `SKILL.md`.

## Update

If you cloned the repository with Git:

```bash
git pull
```

Then copy the updated skill folders into your skills directory again if your assistant does not read directly from this repository.

If you downloaded a ZIP file, download the latest ZIP and replace the old local copy.

## Notes

- Keep each skill as a full folder; do not copy only `SKILL.md` unless your assistant explicitly supports that.
- After adding or replacing skills, restart or refresh your assistant if the new skills do not appear.
- Read the README inside a skill folder for skill-specific usage notes.
