# Client adapters

These layouts capture the working Windows setup from October 2026. Rolling documentation and installed versions can diverge. Resolve the actual configuration home and preserve existing entries. CLI and desktop sharing an entrypoint does not prove both have loaded it.

## Template values

Render all placeholders before writing configuration:

- `NODE`: actual absolute Node executable, with forward slashes on Windows.
- `HOOKS`: stable absolute directory containing the two bundled scripts.
- `WRITE_MATCHER`: tool-name regex from SKILL.md.

Command-string examples below assume NODE has no spaces. For an executable with spaces, use the client's documented shell invocation and quote for that shell. Process handlers with separate command/args avoid shell parsing.

## Claude Code, Qoder, CodeBuddy

| Client | User hook configuration |
|---|---|
| Claude Code CLI / desktop Code sessions | `~/.claude/settings.json` |
| Qoder CN CLI | `~/.qoder-cn/settings.json`; check `QODERCN_CONFIG_DIR` |
| Qoder standalone desktop | `~/.qoder/settings.json` in the referenced desktop docs; confirm the edition's active config |
| CodeBuddy CLI | `~/.codebuddy/settings.json` |

Append these groups to the existing event arrays:

```json
{
  "hooks": {
    "SessionStart": [
      {"hooks": [{"type": "command", "command": "NODE \"HOOKS/engram-start.cjs\"", "timeout": 3}]}
    ],
    "PreToolUse": [
      {"matcher": "WRITE_MATCHER", "hooks": [{"type": "command", "command": "NODE \"HOOKS/engram-memory.cjs\"", "timeout": 3}]}
    ]
  }
}
```

The standard scripts emit `hookSpecificOutput` with `additionalContext` for SessionStart or `permissionDecision: deny` for a matched PreToolUse. An unmatched standard event returns `{}`, leaving the client's permission system in control.

Qoder CLI CN and standalone desktop have different documented config directories. Old IDE/Lingma documentation describes another product entrypoint; do not mix it into standalone desktop setup.

Sources: [Claude hooks](https://code.claude.com/docs/en/hooks), [Qoder CLI hooks](https://docs.qoder.cn/cli/hooks-reference), [Qoder desktop hooks](https://docs.qoder.cn/qoder/hooks), [CodeBuddy hooks](https://www.codebuddy.cn/docs/cli/hooks).

## Codex CLI / desktop

The existing deployment uses inline TOML in `~/.codex/config.toml`. Preserve its representation instead of also adding a hooks.json copy in the same layer:

```toml
[[hooks.SessionStart]]
matcher = "startup|resume|clear|compact"

[[hooks.SessionStart.hooks]]
type = "command"
command = 'NODE "HOOKS/engram-start.cjs"'
timeout = 3

[[hooks.PreToolUse]]
matcher = "WRITE_MATCHER"

[[hooks.PreToolUse.hooks]]
type = "command"
command = 'NODE "HOOKS/engram-memory.cjs"'
timeout = 3
```

For versions that require trust review, use the official `/hooks` interface to review the changed definitions. Preserve existing trusted hooks; let Codex maintain its trust state rather than synthesizing hashes or disabling review. Check local-only versus remote/cloud execution support for the actual session.

Sources: [OpenAI Hooks](https://learn.chatgpt.com/docs/hooks), [advanced configuration](https://learn.chatgpt.com/docs/config-file/config-advanced).

## ZCode

User configuration is `~/.zcode/cli/config.json`. This adapter uses direct process handlers; command is the executable path alone, without shell quotes:

```json
{
  "hooks": {
    "enabled": true,
    "events": {
      "SessionStart": [
        {"hooks": [{"type": "process", "command": "NODE", "args": ["HOOKS/engram-start.cjs"], "timeoutMs": 3000}]}
      ],
      "PreToolUse": [
        {"matcher": "WRITE_MATCHER", "hooks": [{"type": "process", "command": "NODE", "args": ["HOOKS/engram-memory.cjs"], "timeoutMs": 3000}]}
      ]
    }
  }
}
```

Use a new session after editing. The native-memory path targeted by the guard is `~/.zcode/cli/memories/projects/<project>/memory/`. Background extraction is not proven to traverse the same visible tool hooks.

Source: [ZCode hooks](https://zcode.z.ai/cn/docs/hooks).

## Antigravity desktop / CLI

User configuration is `~/.gemini/config/hooks.json`. Top-level keys are named hook bundles. SessionStart handlers are directly inside its array; PreToolUse has matcher groups:

```json
{
  "engram-memory-start": {
    "SessionStart": [
      {"type": "command", "command": "NODE \"HOOKS/engram-start.cjs\" --antigravity", "timeout": 3}
    ]
  },
  "engram-memory-guard": {
    "PreToolUse": [
      {"matcher": "WRITE_MATCHER", "hooks": [{"type": "command", "command": "NODE \"HOOKS/engram-memory.cjs\"", "timeout": 3}]}
    ]
  }
}
```

The startup flag selects `injectSteps`. The guard recognizes Antigravity's `toolCall.name`, `toolCall.args`, `workspacePaths`, and `TargetFile`, returning `decision: allow/deny`.

Its registration adds no Antigravity-specific memory root. Rules, skills, and user-approved `/learn` changes remain ordinary customization, not interception targets.

Source: [Antigravity hooks](https://antigravity.google/docs/hooks).

## DeepSeek Harness desktop

The original adapter targets `0.2.1-rc.2` with the official `@deepseek-ai/dsh-hooks-claude-code` bridge. Match the installed runtime's bridge/protocol versions; the example version is historical, not a latest-version recommendation.

1. Locate the desktop-bundled `dsh` command. Use it to manage the initialized desktop profile; an unrelated npm CLI may manage a different runtime. Follow that version's documented exit/restart requirements.
2. Ensure the matching `@deepseek-ai/dsh-hooks-claude-code` and its required protocol dependency resolve inside the target profile. The known rc.2 operation is `dsh plugin --profile desktop add @deepseek-ai/dsh-hooks-claude-code@0.2.1-rc.2` using the bundled command.
3. Create `HOOKS/dsh-memory-pre.json` using the standard JSON template above, containing both SessionStart and PreToolUse despite the historical filename.
4. Merge one profile-local entry into `~/.dsh/profiles/desktop/cordis.patch.yml`:

```yaml
- insert:
    - id: shared-memory-guard
      name: '@deepseek-ai/dsh-hooks-claude-code'
      config:
        configPath: 'HOOKS/dsh-memory-pre.json'
```

Profile-local installation keeps unrelated web/CLI profiles unchanged. A home-level overlay is appropriate only when all affected profiles are intentionally covered and can resolve the bridge.

The rc.2 Claude bridge documents best-effort SessionStart delivery, which may miss the first request. Its Codex bridge drops non-shell tool arguments in that version, making it unsuitable for this path-based guard. No native DSH memory directory is assumed.

Sources: [rc.2 Claude bridge](https://github.com/deepseek-ai/deepseek-harness/blob/dsh-v0.2.1-rc.2/packages/experimental/hooks-claude-code/README.md), [desktop bundled runtime](https://github.com/deepseek-ai/deepseek-harness/blob/dsh-v0.2.1-rc.2/apps/desktop/README.md).

## WorkBuddy desktop

Use a local hook plugin rather than assuming an undocumented `settings.json` hook entrypoint. The working package layout is:

```text
shared-memory-local/
  .codebuddy-plugin/marketplace.json
  plugins/shared-memory-guard/
    .codebuddy-plugin/plugin.json
    hooks/hooks.json
```

The marketplace declares `name: shared-memory-local`, an owner, and a plugin with `name: shared-memory-guard`, `source: ./plugins/shared-memory-guard`, and matching version. The plugin manifest declares its name, version, and description. Its hooks/hooks.json uses the standard template with rendered absolute paths to the shared scripts.

Install/enable through the supported marketplace/plugin flow for the actual WorkBuddy version. The original machine used CodeBuddy's plugin command with a process-local `CODEBUDDY_CONFIG_DIR` pointing at the WorkBuddy home. Treat that as a version-specific observed route: verify it before reuse, restore the environment, and let the plugin manager write its own registry.

Inspect the installed plugin's hook definition as well as its source. Editing source alone may leave a cached installed copy unchanged; use the supported update/reinstall route to refresh it. Existing wrappers that import the guard must invoke its exported `check(event)` and handle stdin/stdout; merely requiring the file does not run its CLI branch.

WorkBuddy's overnight memory extraction is a separate mechanism with no established native path in this guard. A loaded plugin does not prove interception of that background process.

Sources: [WorkBuddy plugins](https://www.codebuddy.cn/docs/workbuddy/Plugins), [plugin reference](https://www.codebuddy.cn/docs/cli/plugins-reference), [plugin marketplaces](https://www.codebuddy.cn/docs/cli/plugin-marketplaces).

## Troubleshooting

| Symptom | Focused check |
|---|---|
| Hook exits with code 1 on Windows | Reproduce the exact command in the actual shell with synthetic stdin. A quoted executable by itself is an expression in PowerShell. If its actual path has no spaces, `D:/Node.js/node.exe "C:/path/engram-start.cjs"` works in the previously checked PowerShell, CMD, and Git Bash shells. Paths with spaces need shell-specific handling. |
| Script works directly, fails inside client | Compare command-string execution versus separate executable/args, PATH, shell choice, stdin closure, and the installed plugin copy. |
| SessionStart succeeded but no memory search | Confirm injected context, task relevance, and tool availability. Reminder delivery is guidance, not an executed search. |
| Desktop search resolves project to a version directory | Pass the actual session workspace to `mem_current_project`, then pass the returned project explicitly. Keep the shared server workspace-independent. |
| Claude seems unaffected | Read relevant transcript records such as `hook_success` and `hook_additional_context`; then look separately for actual Engram calls. |
| Codex hook is installed but inactive | Inspect `/hooks`, version support, relevant managed policy, and execution host. Review changes through the supported trust UI. |
| Native memory still appears | Identify the actual writer and path. The guard handles only recognized file tools and roots; shell and internal background writes can bypass it. |

When verification is requested, use synthetic payloads for a matched native path, an ordinary project file, an `apply_patch` target, and a read-only `str_replace_editor` view. Expect denial only for recognized writes to native roots; standard nonmatches return `{}`, Antigravity nonmatches return `decision: allow`. Startup output must parse as the appropriate context-injection JSON. Keep stdout JSON-only and diagnostics on stderr.
