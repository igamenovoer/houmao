"""Serve a credential-free MCP tool whose marker is read at process startup."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


def main() -> int:
    """Run the local stdio MCP fixture without model or network access."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--marker", required=True, type=Path)
    args = parser.parse_args()
    marker = args.marker.read_text(encoding="utf-8").strip()
    for line in sys.stdin:
        request = json.loads(line)
        if "id" not in request:
            continue
        method = request.get("method")
        result: dict[str, Any]
        if method == "initialize":
            result = {
                "protocolVersion": request.get("params", {}).get("protocolVersion", "2024-11-05"),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "houmao-native-refresh-probe", "version": marker},
            }
        elif method == "tools/list":
            result = {
                "tools": [
                    {
                        "name": "probe_" + marker,
                        "description": "Local refresh marker " + marker,
                        "inputSchema": {"type": "object", "properties": {}},
                    }
                ]
            }
        elif method == "tools/call":
            result = {"content": [{"type": "text", "text": marker}]}
        elif method == "resources/list":
            result = {"resources": []}
        elif method == "resources/templates/list":
            result = {"resourceTemplates": []}
        elif method == "prompts/list":
            result = {"prompts": []}
        else:
            print(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": request["id"],
                        "error": {"code": -32601, "message": "Unsupported fixture method"},
                    }
                ),
                flush=True,
            )
            continue
        print(json.dumps({"jsonrpc": "2.0", "id": request["id"], "result": result}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
