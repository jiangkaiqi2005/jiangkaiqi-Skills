---
name: clash-chain-proxy
description: Clash Verge Rev 链式代理（机场节点做入口 + 静态住宅 SOCKS5/HTTP 做出口）的配置、验证与排障。Use when 用户提到 dialer-proxy、前置代理、链式代理、1024Proxy/静态住宅 IP 一直超时（Mainland China IP banned）、出口 IP 不是住宅 IP、Clash 重启后链条失效、或系统代理没接管浏览器流量。
---

# Clash Verge Rev 链式代理（机场入口 + 静态住宅出口）

## 拓扑与目的

```text
本机 → 机场节点(入口，运输通道) → 静态住宅代理(出口，网站看到的 IP) → 目标网站
```

为什么必须套链：住宅代理服务商封中国大陆来源 IP（1024Proxy 实测 HTTP 403，`errorMsg: Mainland China IP <本地IP> banned`）。让机场的非大陆服务器去连住宅代理，最后一跳出口固定为住宅 IP。

## 核心概念（改配置前先读，防止方向性错误）

1. **dialer-proxy 挂在出口节点上**，含义是"要连我这个节点，先经过 X"。X 用**分组名**最稳：机场节点名带国旗 emoji（🇺🇸 是两个 Unicode 区域指示符组成），手打必错，只能从节点列表整体复制。
2. 流量会不会从住宅 IP 出，只看一条：**规则命中的分组当前选中的是不是带 dialer-proxy 的节点**。入口节点怎么换（日/港/美）都不影响出口 IP——这正是链式的意义；反过来说，选中了别的普通节点就完全不经过住宅代理。
3. mihomo 已移除 relay 分组（日志原话 `with relay type was removed, please using dialer-proxy instead`），前置只能用 dialer-proxy。要求 Clash Verge Rev ≥ 2.4.5，实测 2.5.5 可用。
4. **孤儿节点**：定义了节点但没被任何分组引用 = 选不到 = 白配。prepend 之后必须确认节点进了分组（见第 3 步）。
5. UI 上的「链式代理」面板配置重启会掉，不要依赖面板，用增强文件。

## 文件地图（Windows）

根目录：`%APPDATA%\io.github.clash-verge-rev.clash-verge-rev\`

| 文件 | 作用 |
|---|---|
| `clash-verge.yaml` | mihomo 实际加载的运行时配置，**诊断以它为准** |
| `profiles.yaml` | 订阅注册表：`current`、各订阅的 `option.{proxies,groups,rules,merge,script}` 增强文件关联、分组选中记录 `selected` |
| `profiles/<订阅uid>.yaml` | 订阅缓存原文 |
| `profiles/<proxies uid>.yaml` | UI「编辑节点」= proxies prepend，**链式节点定义的落点** |
| `profiles/<groups uid>.yaml` | UI「编辑分组」= groups prepend（只能整组新增，不能往已有组塞成员） |
| `profiles/<script uid>.js` | UI「编辑脚本」，运行时改配置，适合按 server IP 动态补属性 |
| `verge.yaml` | 应用设置：`enable_system_proxy`、`enable_builtin_enhanced`、`verge_mixed_port` |
| `logs/` | 内核日志 |

对应 UI 入口：订阅页 → 右键订阅 → 编辑节点 / 编辑分组 / 编辑脚本。

## 配置步骤（已验证走通的方法）

### 第 1 步：拿住宅代理信息

1024Proxy 后台「获取代理 → 长效静态 ISP」导出 `socks5://<username>:<password>@<host>:<port>`。**凭据只贴进 Clash 自己的配置，不写进任何文档/脚本/仓库，也不发给别人。**

### 第 2 步：写「编辑节点」（proxies prepend）

```yaml
prepend:
  - type: socks5
    name: "SOCKS5 <host>:<port>"
    server: <host>
    port: <port>
    username: "<username>"
    password: "<password>"
    udp: true
    dialer-proxy: "自动选择"   # 入口分组名；若要钉死单个机场节点，名字必须从列表整体复制
```

替代方案（节点是通过 UI 导入 socks5:// 链接产生的）：用「编辑脚本」按 server IP 定位补 dialer-proxy，彻底避开 emoji 匹配问题：

```js
function main(config) {
  const p = (config.proxies || []).find(x => x.server === "<host>");
  if (p) { p["dialer-proxy"] = "自动选择"; p.udp = true; }
  return config;
}
```

### 第 3 步：确认节点进了出口分组（关键，别跳过）

订阅的分组常见是**静态成员列表**，本身不含新节点。本机实测：Verge 的内建增强（设置里「内建增强配置」，`enable_builtin_enhanced: true`）会把 prepend 的节点自动插进**第一个代理组**（select 类型）的成员列表头，url-test/fallback 组不受影响。版本不同行为可能变，所以每次都要确认：

- 运行时配置检查：`grep -A8 "name: <出口分组名>" clash-verge.yaml`，节点名应在 `proxies:` 里；
- 或 UI 代理页看该分组里有没有这个节点；
- 没进去 → 用「编辑脚本」把节点名 unshift 进目标组（编辑分组只能新增整组，塞不进已有组）：

```js
function main(config) {
  const g = (config["proxy-groups"] || []).find(g => g.name === "<出口分组名>");
  const n = "SOCKS5 <host>:<port>";
  if (g && Array.isArray(g.proxies) && !g.proxies.includes(n)) g.proxies.unshift(n);
  return config;
}
```

### 第 4 步：分组里选中出口节点

UI 代理页 → 出口分组（订阅规则流量指向的组，本机为「良心云」）→ 选中 `SOCKS5 <host>:<port>`。入口分组（自动选择）保持 url-test 自动挑即可。选中状态存于 `profiles.yaml` 的 `selected`，重启保持。

### 第 5 步：开系统代理

正常情况直接点 UI「系统代理」开关即可。若 UI 状态和实际不一致（如注册表 `ProxyEnable=0` 但 UI 显示开），用文件方式：

1. `taskkill //F //IM clash-verge.exe`（强杀，防止退出时把设置写回覆盖）
2. 改 `verge.yaml` → `enable_system_proxy: true`
3. 重新启动 Clash Verge
4. 验证注册表：`ProxyEnable=1`、`ProxyServer=127.0.0.1:<混合端口>`

不开系统代理也不开 TUN 的后果：链条修好了浏览器也不走，表现为"查 IP 还是本地宽带 IP"。

## 验证（分层）

```bash
# 1. 走内核（混合端口，默认 7897，以 verge.yaml verge_mixed_port 为准）
curl -s --max-time 30 -x http://127.0.0.1:7897 https://api.ipify.org

# 2. 走系统代理（等同浏览器视角，验证第 5 步）
powershell -NoProfile -Command "(Invoke-WebRequest -UseBasicParsing 'https://api.ipify.org' -TimeoutSec 30).Content"
```

结果判读：

| 显示的 IP | 结论 |
|---|---|
| 住宅代理 IP | ✅ 全链路通 |
| 机场节点 IP | dialer-proxy 没落地，回第 2/3 步 |
| 本地宽带 IP | Clash 没接管流量，回第 5 步（系统代理/TUN） |
| 打不开/超时 | 链条某环断了，走排错阶梯 |

配置落地检查：`grep -c dialer-proxy clash-verge.yaml` ≥ 1 且挂在出口节点上；出口节点在分组成员列表里且被选中。

## 排错阶梯（还是不通时按序查）

| 现象 | 结论 | 处理 |
|---|---|---|
| TCP 秒连但 SOCKS5 握手被静默关闭；HTTP 探测回 403 `Mainland China IP banned` | 链没套上，本机直连被服务商拉黑 | 本 skill 主题：补 dialer-proxy + 进组 + 选中 |
| 403 且来源 IP 是机场机房 IP | 服务商封机房段 | 换入口节点/线路 |
| SOCKS5 无响应，但 HTTP 探测活着（回 `Proxy-Authenticate: Basic`） | 该端口只有 HTTP 代理，没有 SOCKS5 | 节点 `type: socks5` 改 `type: http` |
| 日志出现 `with relay type was removed` | 用了已废弃的 relay 分组 | 改用 dialer-proxy |
| dialer-proxy 指向的名字找不到 | emoji 节点名手打错 | 指向分组名，或从节点列表整体复制 |
| 节点不在任何分组里 | 孤儿节点 | 第 3 步脚本 unshift |
| curl 通、浏览器不通 | 系统代理没开 | 第 5 步 |
| UI 链式面板配置重启后消失 | 面板不持久 | 改用增强文件（本 skill 方法） |

协议层探测命令（区分上表前几种情况；凭据只在命令行临时用，勿写进文档/历史）：

```bash
# TCP 是否活
curl -v --connect-timeout 5 telnet://<host>:<port>
# HTTP 代理探测（403 响应头会带服务商拒绝原因）
curl -v --connect-timeout 8 -x http://<host>:<port> --proxy-user '<user>:<pass>' https://api.ipify.org
# SOCKS5 直探
curl -v --socks5-hostname <host>:<port> --proxy-user '<user>:<pass>' https://api.ipify.org
```

## 本机部署快照（2026-09-28）

- 出口：1024Proxy 美国长效静态 ISP，`<住宅代理 IP:端口>`，socks5（IP 与账密见本机 Clash 配置，不记录于此）
- 入口：良心云「自动选择」（url-test）
- 落点：`profiles/pabOlrucbnvj.yaml`（良心云订阅的「编辑节点」prepend，节点带 `dialer-proxy: 自动选择`）
- 出口分组：「良心云」（select），选中该 SOCKS5 节点；规则模式，国内 DIRECT 直连
- 混合端口 7897，系统代理已开
- 验证基准：ipify 应返回住宅代理的出口 IP（具体值见本机 Clash 配置）

## 注意事项

- 机场中转住宅代理 = 入口、出口流量双倍计费，且部分机场条款禁止此用法。
- 首页「当前节点」卡片显示的是**所选分组**的节点（如自动选择=入口组），组里看不到 SOCKS5 不代表链断了，以 IP 实测为准；出口状态看出口分组。
- 订阅更新不会丢 prepend/脚本（它们是独立增强文件）；Verge 大版本升级后建议复查一遍运行时配置（内建增强行为可能变化）。
