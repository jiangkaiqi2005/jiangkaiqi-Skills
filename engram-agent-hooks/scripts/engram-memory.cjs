// One stateless write guard; it never creates or saves a memory.
const path = require('path');
const os = require('os');
const nativeRoots = /^(?:\.codex\/memories(?:\/|$)|\.claude\/projects\/[^/]+\/memory(?:\/|$)|\.qoder-cn\/(?:memory(?:\/|$)|projects\/[^/]+\/memory(?:\/|$))|\.zcode\/cli\/memories\/projects\/[^/]+\/memory(?:\/|$)|\.codebuddy\/memories(?:\/|$))/i;
const reason = 'Use Engram MCP for durable memory. If this information no longer merits remembering, skip it; saving is optional.';

function check(event) {
  const antigravity = !!event.toolCall;
  const tool = event.tool_name || event.toolCall?.name || '';
  let args = event.tool_input || event.toolCall?.args || {};
  if (typeof args === 'string') {
    try { args = JSON.parse(args); } catch { args = {command: args}; }
  }
  const cwd = event.cwd || event.workspacePaths?.[0] || process.cwd();
  let files = [];
  if (/^(?:Write|Edit|MultiEdit|write|edit|write_to_file|replace_file_content|multi_replace_file_content)$/i.test(tool)) {
    files = [args.file_path, args.TargetFile, args.path];
    if (Array.isArray(args.edits)) files.push(...args.edits.map(edit => edit.file_path || edit.path));
  } else if (tool === 'str_replace_editor' && ['create','str_replace','insert'].includes(args.command)) {
    files = [args.path];
  } else if (/apply_patch$/i.test(tool)) {
    const patch = args.command || args.patch || args.input || '';
    files = [...patch.matchAll(/^\*\*\* (?:Add File|Update File|Delete File|Move to):\s*(.+)$/gm)].map(match => match[1].trim());
  }
  const deny = files.some(file => {
    if (typeof file !== 'string') return false;
    const target = path.resolve(cwd, file.replace(/^~(?=[\\/])/, os.homedir()));
    const relative = path.relative(os.homedir(), target).replaceAll('\\', '/');
    return nativeRoots.test(relative);
  });
  if (antigravity) return deny ? {decision:'deny',reason} : {decision:'allow'};
  return deny ? {hookSpecificOutput:{hookEventName:'PreToolUse',permissionDecision:'deny',permissionDecisionReason:reason}} : {};
}

module.exports = {check};
if (require.main === module) {
  let raw = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', chunk => {raw += chunk;});
  process.stdin.on('end', () => {
    try {process.stdout.write(JSON.stringify(check(JSON.parse(raw))) + '\n');}
    catch {process.stderr.write('Engram memory guard received invalid hook input.\n');process.exitCode=1;}
  });
}
