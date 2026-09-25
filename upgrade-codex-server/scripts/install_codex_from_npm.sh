#!/usr/bin/env bash
# install_codex_from_npm.sh — 从官方 npm 平台包安装/升级 Codex CLI（standalone 布局，完整组件）
# 用法: install_codex_from_npm.sh [版本号]     缺省 = GitHub 最新 release
# 为什么用 npm 包而不是 GitHub release tar.gz：后者只含主程序，缺 bin/codex-code-mode-host，
# 而桌面端固定传 -c features.code_mode_host=true，缺宿主会导致所有终端命令无法启动。
set -euo pipefail
VER="${1:-}"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
WRAPPER="${WRAPPER:-$HOME/.local/bin/codex}"
STANDALONE="$CODEX_HOME/packages/standalone"
TARGET="x86_64-unknown-linux-musl"

# 代理端口取自启动脚本（端口换过也能自适应）
PROXY_PORT=$(grep -oE '127\.0\.0\.1:[0-9]+' "$WRAPPER" 2>/dev/null | head -1 | cut -d: -f2 || true)
PROXY_PORT=${PROXY_PORT:-17898}
export https_proxy="http://127.0.0.1:$PROXY_PORT" http_proxy="http://127.0.0.1:$PROXY_PORT"

if [ -z "$VER" ]; then
  VER=$(wget -qO- --timeout=20 "https://registry.npmjs.org/@openai/codex/latest" 2>/dev/null \
        | grep -m1 -oE '"version":"[0-9.]+"' | cut -d'"' -f4 || true)
  if [ -z "$VER" ]; then
    VER=$(wget -q --max-redirect=0 -S -O /dev/null "https://github.com/openai/codex/releases/latest" 2>&1 \
          | grep -m1 -oE 'rust-v[0-9.]+' | cut -dv -f2 || true)
  fi
  [ -n "$VER" ] || { echo "error: 无法确定最新版本（隧道不通？先跑 codex_env_check.sh）"; exit 1; }
  echo "latest upstream: $VER"
fi
VER="${VER#rust-v}"
[[ "$VER" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "error: 版本号格式不对: '$VER'"; exit 1; }

REL="$STANDALONE/releases/$VER-$TARGET"
URL="https://registry.npmjs.org/@openai/codex/-/codex-$VER-linux-x64.tgz"
echo "installing codex $VER ($TARGET) -> $REL"

tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
wget -q --timeout=300 -O "$tmp/codex.tgz" "$URL" || { echo "error: 下载失败（检查隧道）"; exit 1; }
tar -xzf "$tmp/codex.tgz" -C "$tmp"
payload="$tmp/package/vendor/$TARGET"
[ -f "$payload/bin/codex" ] || { echo "error: 包结构异常（vendor/$TARGET/bin/codex 不存在）"; exit 1; }

rm -rf "$REL"
mkdir -p "$REL"
cp -a "$payload/." "$REL/"
ln -sfn bin/codex "$REL/codex"
chmod 755 "$REL/bin/codex" "$REL/bin/codex-code-mode-host" 2>/dev/null || true
ln -sfn "$REL" "$STANDALONE/current"

echo "installed: $("$WRAPPER" --version)"
[ -x "$REL/bin/codex-code-mode-host" ] && echo "code-mode-host: OK" || { echo "code-mode-host: MISSING"; exit 1; }

# 清掉残留 app-server + socket，桌面端重连后才会用上新二进制
pids=$(ps -eo pid,user,cmd 2>/dev/null | awk -v u="$USER" '$2==u && /codex/ && /app-server/ {print $1}')
if [ -n "$pids" ]; then
  kill $pids 2>/dev/null || true
  echo "killed stale app-server: $(echo $pids | tr '\n' ' ')"
fi
rm -f "$CODEX_HOME/app-server-control/app-server-control.sock"
echo "done — 让用户重连桌面端；旧版本保留在 $STANDALONE/releases/ 下可回滚（current 软链指回即可）"
