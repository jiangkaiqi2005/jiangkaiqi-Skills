const assert = require('node:assert/strict');
const test = require('node:test');
const path = require('node:path');
const os = require('node:os');
const {check} = require('./engram-memory.cjs');

const home = os.homedir();
const cwd = path.join(home, 'WorkBuddy', 'example-session');
const memory = path.join(cwd, '.workbuddy', 'memory', 'note.md');
const otherWorkspace = process.platform === 'win32'
  ? `${path.parse(home).root[0].toUpperCase() === 'E' ? 'F' : 'E'}:/Example`
  : '/var/tmp/engram-example';

function write(file, directory = cwd) {
  return {cwd:directory,tool_name:'Write',tool_input:{file_path:file}};
}

const cases = [
  ['WorkBuddy user memory', write(path.join(home, '.workbuddy', 'memory', 'example_memory.md')), true],
  ['WorkBuddy workspace memory', write(memory), true],
  ['relative workspace memory', write('.workbuddy/memory/note.md'), true],
  ['other-drive workspace memory', write(path.join(otherWorkspace, '.workbuddy', 'memory', 'note.md'), otherWorkspace), true],
  ['other-drive relative memory', write('.workbuddy/memory/note.md', otherWorkspace), true],
  ['normalized memory path', write('.workbuddy/memory/sub/../note.md'), true],
  ['ordinary project memory file', write('src/memory/note.md'), false],
  ['neighboring directory', write('.workbuddy/memory-backup/note.md'), false],
  ['WorkBuddy settings', write('.workbuddy/settings.json'), false],
  ['reserved memory directory under another root', write('fixtures/.workbuddy/memory/note.md'), true],
  ['path escaping memory', write('.workbuddy/memory/../notes/note.md'), false],
  ['existing Codex guard', write(path.join(home, '.codex', 'memories', 'note.md')), true],
  ['existing Claude guard', write(path.join(home, '.claude', 'projects', 'demo', 'memory', 'note.md')), true],
  ['existing CodeBuddy guard', write(path.join(home, '.codebuddy', 'memories', 'note.md')), true],
  ['WorkBuddy Edit', {cwd,tool_name:'Edit',tool_input:{file_path:memory}}, true],
  ['WorkBuddy apply_patch', {cwd,tool_name:'apply_patch',tool_input:{input:'*** Begin Patch\n*** Add File: '+memory+'\n+test\n*** End Patch'}}, true],
  ['read-only view', {cwd,tool_name:'str_replace_editor',tool_input:{command:'view',path:memory}}, false],
  ['Engram tool', {cwd,tool_name:'mcp__engram__mem_save',tool_input:{file_path:memory}}, false],
  ['absolute memory path with wrong cwd', write(memory, os.tmpdir()), true],
  ['Bash heredoc append', {cwd,tool_name:'Bash',tool_input:{command:`mkdir -p "${cwd}/.workbuddy/memory" && cat >> "${memory}" <<'EOF'\nexample\nEOF`}}, true],
  ['Bash append with wrong cwd', {cwd:os.tmpdir(),tool_name:'Bash',tool_input:{command:`cat >> "${memory}" <<'EOF'\nexample\nEOF`}}, true],
  ['Bash relative append', {cwd,tool_name:'Bash',tool_input:{command:'echo example >> .workbuddy/memory/note.md'}}, true],
  ['PowerShell redirect', {cwd,tool_name:'PowerShell',tool_input:{command:`'example' >> '${memory}'`}}, true],
  ['PowerShell Add-Content', {cwd,tool_name:'PowerShell',tool_input:{command:`Add-Content -LiteralPath '${memory}' -Value 'example'`}}, true],
  ['PowerShell Set-Content', {cwd,tool_name:'PowerShell',tool_input:{command:`Set-Content '${memory}' 'example'`}}, true],
  ['PowerShell Out-File', {cwd,tool_name:'PowerShell',tool_input:{command:`'example' | Out-File -FilePath '${memory}'`}}, true],
  ['Bash ordinary output', {cwd,tool_name:'Bash',tool_input:{command:'echo example > notes.md'}}, false],
  ['Bash memory read', {cwd,tool_name:'Bash',tool_input:{command:`cat "${memory}"`}}, false],
  ['PowerShell memory read', {cwd,tool_name:'PowerShell',tool_input:{command:`Get-Content '${memory}'`}}, false],
  ['path only mentioned in quoted text', {cwd,tool_name:'Bash',tool_input:{command:`echo 'cat >> "${memory}"'`}}, false],
  ['path only mentioned in heredoc body', {cwd,tool_name:'Bash',tool_input:{command:`cat > notes.md <<'EOF'\ncat >> "${memory}"\nEOF`}}, false],
  ['path only mentioned in tool description', {cwd,tool_name:'Bash',tool_input:{command:'echo example',description:`write ${memory}`}}, false],
];

for (const [name,event,expected] of cases) {
  test(name, () => {
    const result = check(event);
    assert.equal(result.hookSpecificOutput?.permissionDecision === 'deny', expected);
    if (!expected) assert.deepEqual(result, {});
  });
}
