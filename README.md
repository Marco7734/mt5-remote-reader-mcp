# mt5-remote-reader-mcp

> **Read-only** MCP server per monitorare conti MetaTrader 5 su VPS Windows remote via SSH.  
> Non esegue mai operazioni di trading.

## Installazione

```bash
pip install trading-skill
```

## Utilizzo con un agente AI

Una volta installata, puoi dire a qualsiasi agente AI compatibile MCP:

> "Usa la skill trading-skill, connettiti alla VPS 1.2.3.4 con password XXXX e dimmi i trade aperti"

Il comando da passare all'agente per configurare il server MCP è:

```
trading-skill
```

## Tool disponibili

| Tool | Descrizione | Parametri |
|------|-------------|-----------|
| `list_terminals` | Elenca i terminali MT5 attivi sulla VPS | `ip`, `password` |
| `get_open_positions` | Posizioni aperte | `ip`, `password`, `terminal` |
| `get_trade_history` | Storico trade chiusi | `ip`, `password`, `terminal`, `days` (default 30) |
| `get_expert_log` | Log dell'Expert Advisor | `ip`, `password`, `terminal`, `lines` (default 100) |
| `get_symbols` | Strumenti disponibili | `ip`, `password`, `terminal` |
| `get_symbol_info` | Dettagli di uno strumento | `ip`, `password`, `terminal`, `symbol` |

## Prerequisiti sulla VPS

- Windows Server 2012 R2 o superiore
- MetaTrader 5 installato e loggato
- Python 3.8+ installato
- OpenSSH attivo con autenticazione tramite password
- `mt5_tool.py` copiato in `C:\Users\Administrator\Desktop\mt5_tool.py`

## Setup VPS

Per configurare una VPS nuova dal tuo Mac:

```bash
python setup_vps.py 1.2.3.4 password
```

Questo copia automaticamente `mt5_tool.py` sulla VPS e verifica che tutto funzioni.

## Flusso tecnico

```
Agente AI → trading-skill (MCP stdio) → SSH → VPS Windows → mt5_tool.py → JSON
```

## Sicurezza

- La skill è **read-only** — non esegue nessuna operazione di trading
- Le credenziali vengono passate per ogni chiamata e non vengono salvate
