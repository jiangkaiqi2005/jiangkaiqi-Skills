---
name: engram-agent-hooks
description: Install, repair, or audit shared Engram memory hooks across ZCode, Qoder, Codex, Claude Code, Antigravity, DeepSeek Harness, WorkBuddy, and CodeBuddy. Use for selective session-start recall and redirecting visible native-memory writes to Engram.
---

# Engram Agent Hooks

Connect coding agents to one Engram store with two small, stateless hooks. Keep the harness's judgment about what deserves durable memory.

## Behavior

- `SessionStart`: remind the agent to retrieve relevant Engram memories selectively. The script injects guidance; it does not query the database.
- `PreToolUse`: deny recognized file writes inside known native-memory roots. Ask the agent to save to Engram only if the information still merits remembering.
- Keep saving optional. This workflow has no Stop hook, forced summary, pending queue, or automatic transfer of rejected content.

Registration covers only events the client exposes. Shell interception handles the literal output forms documented in the WorkBuddy adapter; dynamic commands, dedicated memory tools, and background internal persistence are not universally intercepted.

## Install or repair

1. Identify the requested clients, editions, versions, configuration homes, and execution hosts. A remote agent needs hooks on its execution host. Read only relevant hook/MCP fields; avoid printing whole credential-bearing configs.
2. Confirm Engram MCP is available to each requested client and points to the intended store. Preserve working MCP entries. Resolve project scope using `mem_current_project(directory=<actual workspace>)`, then pass `project` explicitly to searches and saves. Desktop installation directories are not workspaces.
3. Read only the relevant sections of [client adapters](references/clients.md). Treat the documented configuration layouts as starting points; check the installed version and current official docs before editing. If evidence establishes support, do not require a model conversation merely to prove it again.
4. Deploy [engram-start.cjs](scripts/engram-start.cjs) and [engram-memory.cjs](scripts/engram-memory.cjs) to a stable directory such as `~/.agents/hooks/`. Resolve the actual Node executable and absolute script paths. Both scripts use only Node built-ins.
5. Back up the exact files being changed. Merge owned hook groups into existing event arrays; preserve unrelated hooks, settings, JSONC comments, and TOML/YAML structure. Identify owned handlers by their script path, so rerunning updates rather than duplicates them. For a mixed group, edit only the owned handler.
6. Complete client-specific installation or trust review, then report whether a new session or restart is needed. A configured hook, a trusted hook, an injected reminder, and an actual Engram operation are different evidence levels.

Use this write matcher where the client accepts a tool-name regex, adjusting only for documented or observed names:

```text
Write|Edit|MultiEdit|write|edit|apply_patch|str_replace_editor|write_to_file|replace_file_content|multi_replace_file_content
```

The guard resolves targets against the event workspace and matches these home-relative roots:

```text
.codex/memories/
.claude/projects/<project>/memory/
.qoder-cn/memory/
.qoder-cn/projects/<project>/memory/
.zcode/cli/memories/projects/<project>/memory/
.codebuddy/memories/
```

WorkBuddy additionally reserves the `.workbuddy/memory/` directory namespace in normalized target paths, including home and workspace memory on any drive. Absolute targets are recognized even when the event cwd is an application directory. Neighboring names such as `.workbuddy/memory-backup/` remain unaffected.

These are narrow path checks, not a ban on files named `memory`. Antigravity and DSH have no independent native-memory root in this implementation. Add a target only when its real path and tool input are established.

## Existing global instructions

When aligning shared rules is part of the request, maintain one canonical `~/.agents/AGENTS.md` and preserve the user's existing content. Link a client's documented instruction entrypoint to it where appropriate; inspect an existing destination before replacing it. Prefer existing AGENTS.md/CLAUDE.md integration over creating duplicate instruction files. Hook support does not prove that a client automatically reads `~/.agents/AGENTS.md`.

Keep the memory section short and in English:

```markdown
## Shared Memory

At the start of every session, selectively retrieve Engram MCP memories relevant to the current project and task; skip unrelated memories.

Keep the harness's memory-writing criteria, but use Engram MCP as the sole destination for durable memory.

Organize memories by project. Resolve it with `mem_current_project(directory=<actual workspace>)` and pass `project` explicitly to Engram searches and saves.

Keep confirmed, reusable knowledge, avoid duplicates, and exclude secrets.
```

## Verify proportionately

Parse changed configs and run `node --check` on deployed scripts. Check that unrelated configuration survived and each owned event is registered once.

For guard changes, run `node --test scripts/engram-memory.test.cjs` from this skill directory. The synthetic cases cover WorkBuddy paths, wrong cwd, another drive, literal shell writes, read-only commands, existing guards, and unaffected tools without writing memory files.

When diagnosing execution failures, pipe synthetic JSON through the exact configured command in the client's actual shell. Check a native-memory write is denied, an ordinary project file is unaffected, and startup returns the client's expected JSON. These checks do not write the target files or call a model.

Use existing logs to distinguish hook success, context injection, and actual Engram calls. Report only the evidence obtained; a reminder can succeed even when the agent decides no recall or save is needed. For known failure patterns, see [troubleshooting](references/clients.md#troubleshooting).
