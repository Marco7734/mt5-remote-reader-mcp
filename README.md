# mt5-remote-reader-mcp

[![PyPI version](https://badge.fury.io/py/mt5-remote-reader-mcp.svg)](https://pypi.org/project/mt5-remote-reader-mcp/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-compatible-green.svg)](https://modelcontextprotocol.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Read-only** MCP server to monitor MetaTrader 5 accounts on remote Windows VPS via SSH.  
> Never executes trading operations — pure monitoring only.

---

## What it does

`mt5-remote-reader-mcp` lets any MCP-compatible AI agent (Claude, Cursor, Windsurf, etc.) connect to a Windows VPS running MetaTrader 5 and answer questions about your trading accounts — all via SSH, with no permanent connection and no risk of accidental trades.

**Example prompt:**
> "Use mt5-remote-reader-mcp, connect to VPS 107.x.x.x with password XXXX and tell me what positions are currently open"

The AI will:
1. Connect to your VPS via SSH
2. Query MetaTrader 5
3. Return the data in natural language

---

## Installation

```bash
pip install mt5-remote-reader-mcp
```

---

## Quick Start

### 1. Set up your VPS (one time only)

On your Mac/Linux, run:

```bash
python setup_vps.py YOUR_VPS_IP YOUR_VPS_PASSWORD
```

This installs Python, required libraries, and `mt5_tool.py` on the VPS automatically.

### 2. Configure your MCP client

Add to your MCP client config (e.g. `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "mt5-remote-reader": {
      "command": "mt5-remote-reader-mcp"
    }
  }
}
```

### 3. Talk to your AI

```
"Connect to my VPS at 1.2.3.4 with password XXXX and show me open positions"
"What trades did mt5_5 close in the last 7 days?"
"Is the expert advisor on axi_mt5_5_terminal logging any errors?"
```

---

## Available Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `list_terminals` | List all active MT5 terminals on the VPS | `ip`, `password` |
| `get_open_positions` | Get currently open positions | `ip`, `password`, `terminal` |
| `get_trade_history` | Get closed trades history | `ip`, `password`, `terminal`, `days` (default: 30) |
| `get_expert_log` | Get Expert Advisor log entries | `ip`, `password`, `terminal`, `lines` (default: 100) |
| `get_symbols` | List all available trading symbols | `ip`, `password`, `terminal` |
| `get_symbol_info` | Get detailed info for a specific symbol | `ip`, `password`, `terminal`, `symbol` |

### Recommended flow

Always start with `list_terminals` to discover what terminals are available, then use the short terminal name (e.g. `mt5_5`) for all subsequent calls.

---

## Environment Variables (optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `MT5_TOOL_PATH` | `C:\Users\Administrator\Desktop\mt5_tool.py` | Path to mt5_tool.py on the VPS |
| `VPS_USER` | `Administrator` | SSH username for the VPS |

Example with custom path:
```bash
MT5_TOOL_PATH="C:\trade_monitor\mt5_tool.py" mt5-remote-reader-mcp
```

---

## VPS Requirements

- Windows Server 2012 R2 or later
- MetaTrader 5 installed and logged in
- Python 3.8+ installed and in PATH
- OpenSSH Server active with password authentication
- `mt5_tool.py` deployed on the VPS (handled by `setup_vps.py`)

---

## Architecture

```
AI Agent
    ↓
mt5-remote-reader-mcp  (MCP stdio, runs on your local machine)
    ↓
SSH + password  (paramiko, no pre-configured keys needed)
    ↓
Windows VPS
    ↓
mt5_tool.py + MetaTrader5 Python library
    ↓
JSON  →  natural language response
```

**Why stdio?**  
No background process needed. The MCP server launches on demand, completes the request, and exits. SSH is fast and stateless — there's nothing to keep alive between calls.

**Why paramiko?**  
Pure Python SSH library — works on any Mac, Linux, or Windows without system-level SSH dependencies.

---

## Security

- **Read-only by design** — no trading operations are ever executed
- Credentials are passed per-call and never stored to disk
- SSH connection opens and closes for each request
- Works over standard SSH port 22 — no custom firewall rules needed

---

## Troubleshooting

**"Authentication failed"**  
→ Check the IP and password. Make sure OpenSSH is running on the VPS (`net start sshd`).

**"No output from VPS"**  
→ Make sure `mt5_tool.py` is at the expected path. Run `setup_vps.py` again to redeploy it.

**"MT5 terminal not found"**  
→ Make sure MetaTrader 5 is open and logged in on the VPS before querying.

**"Module MetaTrader5 not found"**  
→ Run `setup_vps.py` again — it will reinstall the required Python libraries.

---

## License

MIT — see [LICENSE](LICENSE)

---

## Related Projects

- [mt5_tool.py](mt5_tool.py) — the core VPS-side script
- [setup_vps.py](setup_vps.py) — automated VPS setup from your local machine
