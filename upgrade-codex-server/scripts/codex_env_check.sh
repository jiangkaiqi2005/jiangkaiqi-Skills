#!/usr/bin/env bash
# codex_env_check.sh — 体检：本机 Codex CLI standalone 安装 + 代理隧道 + app-server 状态
# 输出面向 LLM 的事实行；[FAIL] 行代表需要处理的问题。
set -u
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
WRAPPER="${WRAPPER:-$HOME/.local/bin/codex}"
STANDALONE="$CODEX_HOME/packages/standalone"
FAIL=0
ok()  { echo "[ OK ] $*"; }
bad() { echo "[FAIL] $*"; FAIL=1; }
warn(){ echo "[WARN] $*"; }

# 1. 启动脚本（含代理端口来源）
if [ -x "$WRAPPER" ]; then
  ok "launcher: $WRAPPER"
else
  bad "launcher missing: $WRAPPER"
fi
PROXY_PORT=$(grep -oE '127\.0\.0\.1:[0-9]+' "$WRAPPER" 2>/dev/null | head -1 | cut -d: -f2)
PROXY_PORT=${PROXY_PORT:-17898}
export https_proxy="http://127.0.0.1:$PROXY_PORT" http_proxy="http://127.0.0.1:$PROXY_PORT"
echo "       wrapper proxy port: $PROXY_PORT"

# 2. current 软链与版本、code-mode-host
cur=$(readlink -f "$STANDALONE/current" 2>/dev/null || true)
if [ -n "$cur" ] && [ -x "$cur/bin/codex" ]; then
  ver=$("$cur/bin/codex" --version 2>/dev/null || echo unknown)
  ok "current -> $cur ($ver)"
  if [ -x "$cur/bin/codex-code-mode-host" ]; then
    ok "code-mode-host present"
  else
    bad "code-mode-host MISSING in $cur/bin — 桌面端终端命令将无法启动（用 install_codex_from_npm.sh 补全）"
  fi
else
  bad "current symlink broken: $STANDALONE/current"
fi
[ -d "$STANDALONE/releases" ] && ls -1 "$STANDALONE/releases" | sed 's/^/       release: /'

# 3. 代理端口监听（隧道由 Windows 端 SSH RemoteForward 建立）
if ss -tln 2>/dev/null | grep -q ":$PROXY_PORT "; then
  ok "proxy port $PROXY_PORT listening"
else
  bad "proxy port $PROXY_PORT NOT listening — 让用户在 Windows 重连 SSH（config 条目需含 RemoteForward $PROXY_PORT 127.0.0.1:7897）"
fi
if ss -tln 2>/dev/null | grep -q ":17897 "; then
  warn "port 17897 also listening — 本服务器为多人共用，可能被他人 RemoteForward 占用，勿再使用该端口"
fi

# 4. 隧道连通性（SOCKS5 + TLS）
python3 - "$PROXY_PORT" <<'EOF'
import socket, ssl, sys
port = int(sys.argv[1])
def test(host):
    try:
        s = socket.create_connection(('127.0.0.1', port), timeout=8)
        s.sendall(b'\x05\x01\x00'); r = s.recv(2)
        if r[:2] != b'\x05\x00': return 'not SOCKS5'
        a = host.encode()
        s.sendall(b'\x05\x01\x00\x03' + bytes([len(a)]) + a + (443).to_bytes(2, 'big'))
        r = s.recv(1024)
        if r[1] != 0: return f'SOCKS fail {r[1]}'
        t = ssl.create_default_context().wrap_socket(s, server_hostname=host)
        t.close(); return 'TLS OK'
    except Exception as e:
        return f'FAIL {type(e).__name__}'
for h in ('chatgpt.com', 'www.baidu.com'):
    print(f'       tunnel {h}: {test(h)}')
EOF
echo "       解读: chatgpt TLS OK = 健康; baidu OK 而 chatgpt FAIL = 隧道活着但境外路由坏（节点失效或端口被他人占用）"

# 5. 最新版本（npm registry 的 latest 端点不限流；GitHub API 匿名 60 次/小时常被代理出口 IP 打满，只作备用）
tag=$(wget -qO- --timeout=20 "https://registry.npmjs.org/@openai/codex/latest" 2>/dev/null | grep -m1 -oE '"version":"[0-9.]+"' | cut -d'"' -f4 || true)
if [ -z "$tag" ]; then
  tag=$(wget -q --max-redirect=0 -S -O /dev/null "https://github.com/openai/codex/releases/latest" 2>&1 | grep -m1 -oE 'rust-v[0-9.]+' | cut -dv -f2 || true)
fi
if [ -n "$tag" ]; then
  echo "       latest upstream: $tag"
else
  warn "无法获取最新版本（隧道不通或 GitHub 不可达）"
fi

# 6. 残留 app-server（桌面端旧版本识别的元凶）
if [ -n "$cur" ]; then
  dir_age=$(( $(date +%s) - $(stat -c %Y "$cur" 2>/dev/null || date +%s) ))
  while read -r pid et cmd; do
    if [ "${et:-0}" -gt "$dir_age" ]; then
      bad "stale app-server: pid=$pid running ${et}s, older than current install (${dir_age}s) — kill 后让桌面端重连"
      echo "       $cmd"
    else
      ok "app-server pid=$pid newer than install — 正常"
    fi
  done < <(ps -eo pid,etimes,cmd 2>/dev/null | awk -v u="$USER" '$2==u && /codex/ && /app-server/ {print $1, $2, substr($0, index($0,$3))}')
fi
[ -S "$CODEX_HOME/app-server-control/app-server-control.sock" ] && warn "control socket 存在（若刚 kill 进程需 rm 掉它）"

[ "$FAIL" -eq 0 ] && echo "RESULT: ALL OK" || echo "RESULT: $FAIL 类问题，见上方 [FAIL] 行"
exit "$FAIL"
