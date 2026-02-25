"""MCP client for Award Travel Finder API."""

import json
import os
from typing import Any, Optional

import httpx
from dotenv import load_dotenv

from ..base import ProviderError

load_dotenv()

BASE_URL = "https://mcp.awardtravelfinder.com/mcp"


class ATFClient:
    """MCP JSON-RPC client for AwardTravelFinder."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ATF_API_KEY")
        if not self.api_key:
            raise ProviderError(
                "ATF_API_KEY not set. Add it to .env or set the environment variable."
            )
        self._session_id: Optional[str] = None
        self._request_id = 0
        self._http = httpx.Client(timeout=30.0)

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _headers(self, include_session: bool = True) -> dict[str, str]:
        h = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "X-API-Key": self.api_key,
        }
        if include_session and self._session_id:
            h["Mcp-Session-Id"] = self._session_id
        return h

    def _parse_sse(self, text: str) -> dict[str, Any]:
        """Parse SSE response and extract JSON-RPC result."""
        for line in text.strip().split("\n"):
            if line.startswith("data: "):
                data = json.loads(line[6:])
                if "error" in data:
                    err = data["error"]
                    raise ProviderError(
                        f"ATF API error: {err.get('message', str(err))}",
                        status_code=err.get("code"),
                    )
                if "result" in data:
                    return data["result"]
        raise ProviderError(f"No valid JSON-RPC result in SSE response: {text[:200]}")

    def _init_session(self) -> None:
        """Initialize MCP session."""
        resp = self._http.post(
            BASE_URL,
            json={
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "flight-buddy", "version": "0.1"},
                },
            },
            headers=self._headers(include_session=False),
        )
        resp.raise_for_status()
        self._session_id = resp.headers.get("mcp-session-id")
        if not self._session_id:
            raise ProviderError("No Mcp-Session-Id in initialize response")
        # Parse to validate
        self._parse_sse(resp.text)

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        """Call an MCP tool and return the parsed result."""
        if not self._session_id:
            self._init_session()

        resp = self._http.post(
            BASE_URL,
            json={
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "tools/call",
                "params": {
                    "name": name,
                    "arguments": arguments or {},
                },
            },
            headers=self._headers(),
        )
        resp.raise_for_status()
        result = self._parse_sse(resp.text)

        # MCP tool results have content blocks
        content = result.get("content", [])
        for block in content:
            if block.get("type") == "text":
                try:
                    return json.loads(block["text"])
                except (json.JSONDecodeError, KeyError):
                    return block.get("text", "")
        return content

    def close(self) -> None:
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
