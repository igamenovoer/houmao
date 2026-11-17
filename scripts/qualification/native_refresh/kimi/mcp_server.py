"""Expose one deterministic MCP tool for isolated native refresh qualification."""

from __future__ import annotations

import json
import sys


def main() -> None:
    """Serve initialization and tool discovery without external side effects."""

    revision = sys.argv[1]
    for line in sys.stdin:
        message = json.loads(line)
        if "id" not in message:
            continue
        method = message["method"]
        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "refresh-probe", "version": revision},
            }
        elif method == "tools/list":
            result = {
                "tools": [
                    {
                        "name": "probe_" + revision,
                        "description": "Native refresh probe " + revision,
                        "inputSchema": {"type": "object", "properties": {}},
                    }
                ]
            }
        elif method == "tools/call":
            result = {"content": [{"type": "text", "text": revision}]}
        else:
            result = {}
        print(json.dumps({"jsonrpc": "2.0", "id": message["id"], "result": result}), flush=True)


if __name__ == "__main__":
    main()
