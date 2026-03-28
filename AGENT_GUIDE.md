# Agent Guide — mt5-remote-reader-mcp

This document is intended for AI agents using the `mt5-remote-reader-mcp` skill.

---

## What this skill does

This skill connects to a remote Windows VPS via SSH and queries MetaTrader 5 trading terminals.  
It is **read-only** — it can never place, modify or close trades.

---

## Required information from the user

Before using any tool, you need:
- **ip**: the public IP address of the VPS (e.g. `107.189.25.91`)
- **password**: the SSH password for the `Administrator` user on the VPS

The user will provide these in the prompt. Never hardcode or assume credentials.

---

## Recommended workflow

### Step 1 — Always start with list_terminals
```
list_terminals(ip="...", password="...")
```
This returns the names of all active MT5 terminals. You need these names for all subsequent calls.

Example response:
```json
{
  "axi_mt5_5_terminal": {
    "login": 60231008,
    "broker": "AxiCorp Financial Services Pty Ltd",
    "server": "Axi-US52-Live",
    "connected": true
  },
  "mt5_5": {
    "login": 531160951,
    "broker": "FTMO Global Markets Ltd",
    "server": "FTMO-Server3",
    "connected": true
  }
}
```

Use the dictionary key (e.g. `"mt5_5"`) as the `terminal` parameter in all other tools.

### Step 2 — Query what the user asked for

**Open positions:**
```
get_open_positions(ip="...", password="...", terminal="mt5_5")
```

**Trade history (last N days):**
```
get_trade_history(ip="...", password="...", terminal="mt5_5", days=7)
```

**Expert Advisor log:**
```
get_expert_log(ip="...", password="...", terminal="mt5_5", lines=50)
```

**Symbol details:**
```
get_symbol_info(ip="...", password="...", terminal="mt5_5", symbol="XAUUSD")
```

---

## Interpreting the data

### Open positions
- `type`: `"buy"` or `"sell"`
- `profit`: current floating P&L in account currency
- `sl` / `tp`: stop loss / take profit price, `null` if not set
- `magic`: the EA's identifier number

### Trade history
- `net_profit`: profit after swap and commission — the real P&L
- `open_time` / `close_time`: ISO 8601 format
- Sorted by `open_time` descending (most recent first)

### Expert log
- `entries`: array of log line strings
- Look for keywords like `error`, `warning`, `failed` to spot issues

---

## Example prompts and how to handle them

**"What positions are open on my FTMO account?"**
1. Call `list_terminals` → identify the FTMO terminal (e.g. `mt5_5`)
2. Call `get_open_positions` with `terminal="mt5_5"`
3. Summarize: symbol, direction, size, current P&L

**"How much did I make this week?"**
1. Call `list_terminals`
2. Call `get_trade_history` with `days=7` for each terminal
3. Sum `net_profit` across all closed trades
4. Report total P&L, number of trades, win rate

**"Is the EA running correctly?"**
1. Call `list_terminals` → check `connected: true`
2. Call `get_expert_log` with `lines=100`
3. Scan for errors or warnings in recent entries
4. Report status

**"What's the spread on EURUSD right now?"**
1. Call `list_terminals`
2. Call `get_symbol_info` with `symbol="EURUSD"`
3. Report `spread`, `bid`, `ask`

---

## Error handling

If a tool returns an error, common causes are:
- VPS not reachable → wrong IP or SSH not running
- Authentication failed → wrong password
- MT5 not found → MetaTrader 5 is not open on the VPS
- Terminal not found → wrong terminal name, use `list_terminals` first

Always tell the user clearly what went wrong and what they can do to fix it.

---

## What this skill cannot do

- Place, modify or cancel orders
- Change account settings
- Access account equity/balance directly (use `list_terminals` which includes basic account info)
- Stream real-time data (each call is a snapshot)
