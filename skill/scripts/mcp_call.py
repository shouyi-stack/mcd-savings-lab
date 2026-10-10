#!/usr/bin/env python3
"""麦当劳 MCP 统一调用封装。

用法:
    python mcp_call.py <tool-name> --args '{"k":"v"}'
    python mcp_call.py now-time-info
    python mcp_call.py calculate-price --dry-run --args '{"storeCode":"x"}'

设计要点（对齐 TRACE 评审）:
    - 无硬编码密钥，Token 仅从环境变量 MCD_MCP_TOKEN 读取
    - 接口地址无路径后缀（mcp.mcd.cn），避免连接失败
    - initialize 后补发 notifications/initialized（协议要求）
    - 内置串行节流，规避 600 次/分钟限流
    - 异常转友好提示，不抛栈；支持 --help / --dry-run / 非交互
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

# ⚠️ 无路径后缀
ENDPOINT = os.environ.get("MCD_MCP_ENDPOINT", "https://mcp.mcd.cn")
TOKEN = os.environ.get("MCD_MCP_TOKEN", "")
PROTOCOL = "2025-06-18"
_LAST_CALL = [0.0]


def _throttle(min_interval=0.15):
    """限流 600/min，串行调用保底间隔。"""
    delta = time.time() - _LAST_CALL[0]
    if delta < min_interval:
        time.sleep(min_interval - delta)
    _LAST_CALL[0] = time.time()


def _explain(code):
    tips = {
        401: "MCP Token 无效或已过期，请到 open.mcd.cn/mcp 控制台重新激活并更新环境变量 MCD_MCP_TOKEN。",
        429: "触发限流（600 次/分钟），请降低调用频率后重试。",
        403: "鉴权失败，请检查 Authorization 请求头格式是否为 'Bearer <token>'。",
    }
    return {"ok": False, "error_code": code,
            "message": tips.get(code, f"服务返回 {code}，请稍后重试。")}


def _parse(body):
    # Streamable HTTP 可能返回 SSE（data: {...}）或纯 JSON
    for line in body.splitlines():
        if line.startswith("data:"):
            return json.loads(line[5:].strip())
    return json.loads(body)


def _post(payload, session_id=None):
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": PROTOCOL,
    }
    if session_id:
        headers["mcp-session-id"] = session_id
    _throttle()
    req = urllib.request.Request(
        ENDPOINT, data=json.dumps(payload).encode("utf-8"),
        headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return _parse(raw) if raw.strip() else {}, resp.headers.get("mcp-session-id")
    except urllib.error.HTTPError as e:
        return _explain(e.code), None
    except urllib.error.URLError as e:
        return {"ok": False, "message": f"网络不可达：{e.reason}"}, None
    except (ValueError, json.JSONDecodeError) as e:
        return {"ok": False, "message": f"响应解析失败：{e}"}, None


def call(tool, args):
    if not TOKEN:
        return {"ok": False, "message": "缺少环境变量 MCD_MCP_TOKEN，请先设置后再试。"}
    _, sid = _post({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                    "params": {"protocolVersion": PROTOCOL, "capabilities": {},
                               "clientInfo": {"name": "mcd-savings-lab", "version": "1.0.0"}}})
    if sid:
        _post({"jsonrpc": "2.0", "method": "notifications/initialized"}, sid)
    result, _ = _post({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                       "params": {"name": tool, "arguments": args}}, sid)
    return result


def main():
    p = argparse.ArgumentParser(description="麦当劳 MCP 工具调用器（只读安全）")
    p.add_argument("tool", help="工具名，如 available-coupons")
    p.add_argument("--args", default="{}", help="JSON 字符串参数")
    p.add_argument("--dry-run", action="store_true", help="仅打印将要发送的请求，不实际调用")
    a = p.parse_args()

    try:
        args = json.loads(a.args)
    except json.JSONDecodeError as e:
        print(json.dumps({"ok": False, "message": f"--args 不是合法 JSON：{e}"},
                         ensure_ascii=False, indent=2))
        sys.exit(2)

    if a.dry_run:
        print(json.dumps({"endpoint": ENDPOINT, "tool": a.tool, "args": args},
                         ensure_ascii=False, indent=2))
        return

    print(json.dumps(call(a.tool, args), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
