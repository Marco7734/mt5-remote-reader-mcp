# Changelog

All notable changes to this project will be documented in this file.

---

## [0.1.0] — 2026-03-28

### Initial release

- MCP server in stdio mode using FastMCP 3.x
- SSH connection via paramiko (no pre-configured keys needed)
- 6 read-only tools: `list_terminals`, `get_open_positions`, `get_trade_history`, `get_expert_log`, `get_symbols`, `get_symbol_info`
- Async tool execution (non-blocking event loop)
- Configurable `MT5_TOOL_PATH` and `VPS_USER` via environment variables
- `setup_vps.py` for automated VPS configuration from Mac/Linux
- Published on PyPI as `mt5-remote-reader-mcp`
