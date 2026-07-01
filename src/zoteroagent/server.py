"""ZoteroAgent MCP server."""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Literal

import httpx
from fastmcp.exceptions import ToolError
from fastmcp.server import FastMCP
from fastmcp.tools.tool import TextContent, ToolResult
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

logger = logging.getLogger("ZoteroAgent")

API_TARGETS: dict[str, str] = {
    "zotero": "https://api.zotero.org"
}
ALLOWED_COMMANDS: set[str] = {}
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class ZoteroagentConfig(BaseModel):
    """Runtime configuration for ZoteroAgent."""

    log_level: str = Field(default_factory=lambda: os.getenv("ZOTERO_LOG_LEVEL", "INFO"))


def _result(payload: Any) -> ToolResult:
    return ToolResult(content=[TextContent(type="text", text=json.dumps(payload, indent=2, sort_keys=True))])


def _headers(target: str) -> dict[str, str]:
    headers = {"Accept": "application/json", "User-Agent": "BioRouter-zoteroagent/0.1"}
    for key in ['ZOTERO_API_KEY']:
        value = os.getenv(key)
        if value:
            headers.setdefault("Authorization", f"Bearer {value}")
    return headers


def _join(base_url: str, path: str) -> str:
    if path.startswith(("http://", "https://")):
        return path
    return base_url.rstrip("/") + "/" + path.lstrip("/")


def create_server(config: ZoteroagentConfig) -> FastMCP:
    logging.basicConfig(level=getattr(logging, config.log_level.upper(), logging.INFO))
    mcp = FastMCP("ZoteroAgent")

    @mcp.tool(name="get_zoteroagent_status", annotations=ToolAnnotations(title="Get ZoteroAgent status", readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True))
    def get_status() -> ToolResult:
        """Report configuration, API targets, and local command availability."""
        command_status = {cmd: bool(shutil.which(cmd)) for cmd in sorted(ALLOWED_COMMANDS)}
        return _result({
            "service": "Zotero citation library",
            "api_targets": API_TARGETS,
            "allowed_commands": sorted(ALLOWED_COMMANDS),
            "command_available": command_status,
            "configured_env": {key: bool(os.getenv(key)) for key in ['ZOTERO_API_KEY', 'ZOTERO_USER_ID', 'ZOTERO_GROUP_ID', 'ZOTERO_LOG_LEVEL']},
            "license": "Apache-2.0",
        })

    @mcp.tool(name="list_zoteroagent_api_targets", annotations=ToolAnnotations(title="List ZoteroAgent API targets", readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True))
    def list_api_targets() -> ToolResult:
        """List named API targets supported by this extension."""
        return _result({"targets": API_TARGETS})

    @mcp.tool(name="call_zoteroagent_api", annotations=ToolAnnotations(title="Call a guarded Zotero citation library API endpoint", readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True))
    def call_api(
        target: str = Field(description="Named API target from the list tool, or 'custom' for a full URL in path."),
        path: str = Field(description="Relative API path, or full URL when target='custom'."),
        method: Literal["GET", "HEAD", "OPTIONS", "POST", "PUT", "PATCH", "DELETE"] = Field(default="GET"),
        query: dict[str, Any] | None = Field(default=None),
        json_body: dict[str, Any] | None = Field(default=None),
        allow_mutation: bool = Field(default=False, description="Must be true for POST/PUT/PATCH/DELETE."),
        timeout_s: float = Field(default=30.0, ge=1.0, le=120.0),
    ) -> ToolResult:
        """Call a platform API with write methods blocked by default."""
        method_upper = method.upper()
        if method_upper in WRITE_METHODS and not allow_mutation:
            raise ToolError("Mutation-capable HTTP methods require explicit user approval and allow_mutation=true.")
        if target == "custom":
            if not path.startswith(("https://", "http://")):
                raise ToolError("target='custom' requires a full URL in path.")
            url = path
        else:
            if target not in API_TARGETS:
                raise ToolError(f"Unknown API target '{target}'. Call list_zoteroagent_api_targets first.")
            base = os.getenv(f"{target.upper()}_BASE_URL") or API_TARGETS[target]
            url = _join(base, path)
        try:
            with httpx.Client(timeout=timeout_s, follow_redirects=True) as client:
                response = client.request(method_upper, url, params=query, json=json_body, headers=_headers(target))
            ctype = response.headers.get("content-type", "")
            if "json" in ctype.lower():
                body: Any = response.json()
            else:
                text = response.text
                body = text[:20000] + ("...(truncated)" if len(text) > 20000 else "")
            return _result({"url": str(response.url), "status_code": response.status_code, "ok": response.is_success, "content_type": ctype, "body": body})
        except httpx.HTTPError as exc:
            raise ToolError(f"API request failed: {exc}") from exc

    @mcp.tool(name="plan_zoteroagent_command", annotations=ToolAnnotations(title="Plan a guarded local command", readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False))
    def plan_command(command: str = Field(description="Command name to evaluate."), args: list[str] | None = Field(default=None)) -> ToolResult:
        """Explain whether a local command is allowed and what approval is needed."""
        args = args or []
        return _result({"command": command, "args": args, "allowed": command in ALLOWED_COMMANDS, "requires_allow_execute": True})

    @mcp.tool(name="run_zoteroagent_command", annotations=ToolAnnotations(title="Run a guarded local command", readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False))
    def run_command(command: str, args: list[str] = Field(default_factory=list), cwd: str | None = None, allow_execute: bool = False, timeout_s: float = Field(default=60.0, ge=1.0, le=3600.0)) -> ToolResult:
        """Run an allowlisted local command without a shell."""
        if command not in ALLOWED_COMMANDS:
            raise ToolError(f"Command '{command}' is not in this extension's allowlist.")
        if not allow_execute:
            raise ToolError("Local command execution requires explicit approval and allow_execute=true.")
        workdir = Path(cwd).expanduser() if cwd else None
        if workdir and not workdir.exists():
            raise ToolError(f"Working directory does not exist: {workdir}")
        try:
            proc = subprocess.run([command, *args], cwd=str(workdir) if workdir else None, text=True, capture_output=True, timeout=timeout_s, check=False)
            return _result({"command": [command, *args], "cwd": str(workdir) if workdir else None, "returncode": proc.returncode, "stdout": proc.stdout[-20000:], "stderr": proc.stderr[-20000:]})
        except subprocess.TimeoutExpired as exc:
            raise ToolError(f"Command timed out after {timeout_s} seconds: {exc}") from exc

    @mcp.tool(name="summarize_zoteroagent_resource", annotations=ToolAnnotations(title="Summarize a Zotero citation library payload", readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True))
    def summarize_resource(payload: dict[str, Any] = Field(description="JSON payload or exported metadata.")) -> ToolResult:
        """Summarize a JSON payload without making network calls."""
        keys = list(payload.keys())
        provenance = [k for k in keys if k.lower() in {"id", "identifier", "accession", "doi", "pmid", "version", "created_at", "updated_at", "url", "name", "title", "collection", "dataset", "run_id", "item_id"}]
        return _result({"service": "Zotero citation library", "top_level_keys": keys, "provenance_fields_present": provenance, "preview": {k: payload[k] for k in keys[:20]}})

    return mcp


def main(transport: Literal["stdio", "sse", "http"] = "stdio", log_level: str | None = None) -> None:
    config = ZoteroagentConfig(log_level=log_level or os.getenv("ZOTERO_LOG_LEVEL", "INFO"))
    logger.info("Starting ZoteroAgent")
    create_server(config).run()


if __name__ == "__main__":
    main()
