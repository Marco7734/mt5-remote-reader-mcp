"""
server.py — MT5 Remote Reader MCP Server
Server MCP read-only per monitorare conti MetaTrader 5 su VPS Windows remote via SSH.
"""

from fastmcp import FastMCP
from .ssh import run, setup, DEFAULT_MT5_TOOL_PATH
from .vps_manager import save_vps as _save_vps, list_vps as _list_vps, delete_vps as _delete_vps, get_vps_credentials
import os

mcp = FastMCP(
    name="mt5-remote-reader",
    instructions=(
        "Read-only MCP server per monitorare conti MetaTrader 5 su VPS Windows remote via SSH. "
        "Le credenziali VPS sono salvate in una rubrica locale sicura (~/.mt5-reader/vps.json). "
        "Prima di tutto controlla le VPS disponibili con list_vps. "
        "Se non ce ne sono, chiedi all'utente le credenziali e usa save_vps per salvarle — "
        "non dovrà reinserirle mai più. "
        "Poi usa connect_vps per configurare la VPS se è la prima volta, "
        "list_terminals per scoprire i terminali disponibili, "
        "e infine i tool di monitoraggio con il nome corto del terminale. "
        "Questo server non esegue mai operazioni di trading — è esclusivamente in lettura."
    ),
)

MT5_TOOL_PATH = os.environ.get("MT5_TOOL_PATH", DEFAULT_MT5_TOOL_PATH)


# ─────────────────────────────────────────────
#  RUBRICA VPS
# ─────────────────────────────────────────────

@mcp.tool
async def save_vps(name: str, ip: str, username: str, password: str) -> dict:
    """
    Aggiunge o aggiorna una VPS nella rubrica locale sicura.
    Le credenziali sono salvate cifrate in ~/.mt5-reader/vps.json.
    Dopo questa chiamata non sarà mai più necessario inserire ip, username e password.

    Args:
        name:     Nome amichevole da assegnare alla VPS (es. "ftmo", "axi", "mia_vps")
        ip:       Indirizzo IP pubblico della VPS
        username: Username SSH della VPS (solitamente "Administrator")
        password: Password SSH della VPS
    """
    return _save_vps(name, ip, username, password)


@mcp.tool
async def list_vps() -> dict:
    """
    Elenca tutte le VPS salvate in rubrica.
    Mostra nome, IP e username — mai le password.
    Chiamare sempre questo tool per primo per vedere le VPS disponibili.
    """
    data = _list_vps()
    if not data:
        return {
            "status": "empty",
            "message": (
                "Nessuna VPS in rubrica. "
                "Usa save_vps per aggiungerne una — "
                "basterà farlo una volta sola."
            ),
        }
    return {"status": "ok", "vps": data}


@mcp.tool
async def delete_vps(name: str) -> dict:
    """
    Rimuove una VPS dalla rubrica.

    Args:
        name: Nome amichevole della VPS da rimuovere (es. "ftmo")
    """
    return _delete_vps(name)


# ─────────────────────────────────────────────
#  SETUP VPS
# ─────────────────────────────────────────────

@mcp.tool
async def connect_vps(vps: str) -> dict:
    """
    Configura una VPS Windows per l'uso con mt5-remote-reader.
    Va chiamato la prima volta che si usa una VPS nuova.

    Fa tutto automaticamente:
    - Verifica se Python è installato, altrimenti lo installa
    - Installa le librerie necessarie (MetaTrader5, psutil)
    - Copia mt5_tool.py sulla VPS
    - Testa la connessione con MT5 e ritorna i terminali trovati

    MetaTrader 5 deve essere già installato e loggato sulla VPS.

    Args:
        vps: Nome amichevole della VPS in rubrica (es. "ftmo"). Usa list_vps per vedere quelle disponibili.
    """
    creds = get_vps_credentials(vps)
    mt5_tool_path = MT5_TOOL_PATH.replace("Administrator", creds["username"])
    return await setup(creds["ip"], creds["username"], creds["password"], mt5_tool_path)


# ─────────────────────────────────────────────
#  TOOL DI MONITORAGGIO
# ─────────────────────────────────────────────

@mcp.tool
async def list_terminals(vps: str) -> dict:
    """
    Elenca tutti i terminali MetaTrader 5 attivi sulla VPS.
    Ritorna nome, login, broker, server e stato connessione per ogni terminale.
    Usare sempre questo tool prima degli altri per scoprire i nomi dei terminali disponibili.

    Args:
        vps: Nome amichevole della VPS in rubrica (es. "ftmo"). Usa list_vps per vedere quelle disponibili.
    """
    creds = get_vps_credentials(vps)
    mt5_tool_path = MT5_TOOL_PATH.replace("Administrator", creds["username"])
    return await run(creds["ip"], creds["username"], creds["password"], "list_terminals", mt5_tool_path=mt5_tool_path)


@mcp.tool
async def get_open_positions(vps: str, terminal: str) -> list:
    """
    Ritorna le posizioni aperte sul terminale specificato.
    Ogni posizione include: ticket, symbol, type (buy/sell), volume,
    open_price, current_price, sl, tp, profit, swap, open_time, comment, magic.

    Args:
        vps:      Nome amichevole della VPS in rubrica (es. "ftmo")
        terminal: Nome corto del terminale (es. "mt5_5"), ottenuto da list_terminals
    """
    creds = get_vps_credentials(vps)
    mt5_tool_path = MT5_TOOL_PATH.replace("Administrator", creds["username"])
    return await run(creds["ip"], creds["username"], creds["password"], "get_open_positions", terminal=terminal, mt5_tool_path=mt5_tool_path)


@mcp.tool
async def get_account_info(vps: str, terminal: str) -> dict:
    """
    Ritorna le informazioni del conto MT5: balance, equity, margin, free margin,
    margin level, profit flottante, valuta, leva, login, broker.

    Args:
        vps:      Nome amichevole della VPS in rubrica (es. "ftmo")
        terminal: Nome corto del terminale, ottenuto da list_terminals
    """
    creds = get_vps_credentials(vps)
    mt5_tool_path = MT5_TOOL_PATH.replace("Administrator", creds["username"])
    return await run(creds["ip"], creds["username"], creds["password"],
                     "get_account_info", terminal=terminal, mt5_tool_path=mt5_tool_path)


@mcp.tool
async def get_trade_history(vps: str, terminal: str, days: int = 30) -> list:
    """
    Ritorna lo storico dei trade chiusi negli ultimi N giorni.
    Ogni trade include: symbol, type, volume, open_price, close_price,
    open_time, close_time, profit, swap, commission, net_profit.

    Args:
        vps:      Nome amichevole della VPS in rubrica (es. "ftmo")
        terminal: Nome corto del terminale, ottenuto da list_terminals
        days:     Numero di giorni di storico (default: 30)
    """
    creds = get_vps_credentials(vps)
    mt5_tool_path = MT5_TOOL_PATH.replace("Administrator", creds["username"])
    return await run(creds["ip"], creds["username"], creds["password"], "get_trade_history", terminal=terminal, days=days, mt5_tool_path=mt5_tool_path)


@mcp.tool
async def get_expert_log(vps: str, terminal: str, lines: int = 100) -> dict:
    """
    Ritorna le ultime N righe del log dell'Expert Advisor del terminale.
    Utile per diagnosticare problemi o verificare l'attività dell'EA.

    Args:
        vps:      Nome amichevole della VPS in rubrica (es. "ftmo")
        terminal: Nome corto del terminale, ottenuto da list_terminals
        lines:    Numero di righe di log da ritornare (default: 100)
    """
    creds = get_vps_credentials(vps)
    mt5_tool_path = MT5_TOOL_PATH.replace("Administrator", creds["username"])
    return await run(creds["ip"], creds["username"], creds["password"], "get_expert_log", terminal=terminal, lines=lines, mt5_tool_path=mt5_tool_path)


@mcp.tool
async def get_symbols(vps: str, terminal: str) -> list:
    """
    Ritorna tutti gli strumenti di trading disponibili sul terminale.

    Args:
        vps:      Nome amichevole della VPS in rubrica (es. "ftmo")
        terminal: Nome corto del terminale, ottenuto da list_terminals
    """
    creds = get_vps_credentials(vps)
    mt5_tool_path = MT5_TOOL_PATH.replace("Administrator", creds["username"])
    return await run(creds["ip"], creds["username"], creds["password"], "get_symbols", terminal=terminal, mt5_tool_path=mt5_tool_path)


@mcp.tool
async def get_symbol_info(vps: str, terminal: str, symbol: str) -> dict:
    """
    Ritorna i dettagli completi di uno strumento specifico.
    Include: contract_size, volume_min/max/step, swap_long/short, bid, ask, spread.

    Args:
        vps:      Nome amichevole della VPS in rubrica (es. "ftmo")
        terminal: Nome corto del terminale, ottenuto da list_terminals
        symbol:   Nome dello strumento (es. "EURUSD", "XAUUSD")
    """
    creds = get_vps_credentials(vps)
    mt5_tool_path = MT5_TOOL_PATH.replace("Administrator", creds["username"])
    return await run(creds["ip"], creds["username"], creds["password"], "get_symbol_info", terminal=terminal, symbol=symbol, mt5_tool_path=mt5_tool_path)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
