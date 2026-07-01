from __future__ import annotations

import argparse

from .server import main as server_main


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ZoteroAgent MCP server")
    parser.add_argument("--transport", choices=["stdio", "sse", "http"], default="stdio")
    parser.add_argument("--log-level", default=None)
    args = parser.parse_args()
    server_main(transport=args.transport, log_level=args.log_level)
