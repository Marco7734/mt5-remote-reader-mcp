"""
server.py — MT5 Remote Reader MCP Server
Server MCP read-only per monitorare conti MetaTrader 5 su VPS Windows remote via SSH.
"""

import os
from fastmcp import FastMCP
from .ssh import run, setup, DEFAULT_MT5_TOOL_PATH, DEFAULT_VPS_USER

mcp = FastMCP(
    name="mt5-remote-reader",
    instructions=(
        "Read-only MCP server per monitorare conti MetaTrader 5 su VPS Windows remote via SSH. "
        "Ogni tool richiede ip, username e password della VPS. "
        "Se è la prima volta che usi una VPS, chiama prima connect_vps per configurarla. "
        "Poi usa list_terminals per scoprire i terminali disponibili, "
        "e infine usa il nome corto del terminale per le altre funzioni. "
        "Questo server non esegue mai operazioni di trading — è esclusivamente in lettura."
    ),
)

MT5_TOOL_PATH = os.environ.get("MT5_TOOL_PATH", DEFAULT_MT5_TOOL_PATH)


@mcp.tool
async def connect_vps(ip: str, username: str, password: str) -> dict:
    """
    Configura una VPS Windows per l'uso con mt5-remote-reader.
    Va chiamato la prima volta che si usa una VPS nuova.
    
    Fa tutto automaticamente:
    - Verifica se Python è installato, altrimenti lo installa silenziosamente
    - Installa le librerie necessarie (MetaTrader5, psutil)
    - Copia mt5_tool.py sulla VPS
    - Testa la connessione con MT5 e ritorna i terminali trovati
    
    Se la VPS è già configurata, verifica solo che tutto funzioni correttamente.
    MetaTrader 5 deve essere già installato e loggato sulla VPS prima di chiamare questo tool.

    Args:
        ip: Indirizzo IP pubblico della VPS
        username: Username SSH della VPS (solitamente "Administrator")
        password: Password SSH della VPS
    """
    mt5_tool_path = MT5_TOOL_PATH.replace("Administrator", username)
    return await setup(ip, username, password, mt5_tool_path)


@mcp.tool
async def list_terminals(ip: str, username: str, password: str) -> dict:
    """
    Elenca tutti i terminali MetaTrader 5 attivi sulla VPS.
    Ritorna un dizionario con nome, login, broker, server e stato connessione
    per ogni terminale trovato.
    Usa sempre questo tool prima degli altri per scoprire i nomi dei terminali disponibili.

    Args:
        ip: Indirizzo IP della VPS
        username: Username SSH della VPS (solitamente "Administrator")
        password: Password SSH della VPS
    """
    mt5_tool_path = MT5_TOOL_PATH.replace("Administrator", username)
    return await run(ip, username, password, "list_terminals", mt5_tool_path=mt5_tool_path)


@mcp.tool
async def get_open_positions(ip: str, username: str, password: str, terminal: str) -> list:
    """
    Ritorna le posizioni aperte sul terminale specificato.
    Ogni posizione include: ticket, symbol, type (buy/sell), volume,
    open_price, current_price, sl, tp, profit, swap, open_time, comment, magic.

    Args:
        ip: Indirizzo IP della VPS
        username: Username SSH della VPS (solitamente "Administrator")
        password: Password SSH della VPS
        terminal: Nome corto del terminale (es. "mt5_5"), ottenuto da list_terminals
    """
    mt5_tool_path = MT5_TOOL_PATH.replace("Administrator", username)
    return await run(ip, username, password, "get_open_positions", terminal=terminal, mt5_tool_path=mt5_tool_path)


@mcp.tool
async def get_trade_history(ip: str, username: str, password: str, terminal: str, days: int = 30) -> list:
    """
    Ritorna lo storico dei trade chiusi negli ultimi N giorni.
    Ogni trade include: symbol, type, volume, open_price, close_price,
    open_time, close_time, profit, swap, commission, net_profit.

    Args:
        ip: Indirizzo IP della VPS
        username: Username SSH della VPS (solitamente "Administrator")
        password: Password SSH della VPS
        terminal: Nome corto del terminale, ottenuto da list_terminals
        days: Numero di giorni di storico (default: 30)
    """
    mt5_tool_path = MT5_TOOL_PATH.replace("Administrator", username)
    return await run(ip, username, password, "get_trade_history", terminal=terminal, days=days, mt5_tool_path=mt5_tool_path)


@mcp.tool
async def get_expert_log(ip: str, username: str, password: str, terminal: str, lines: int = 100) -> dict:
    """
    Ritorna le ultime N righe del log dell'Expert Advisor del terminale.
    Utile per diagnosticare problemi o verificare l'attività dell'EA.

    Args:
        ip: Indirizzo IP della VPS
        username: Username SSH della VPS (solitamente "Administrator")
        password: Password SSH della VPS
        terminal: Nome corto del terminale, ottenuto da list_terminals
        lines: Numero di righe di log da ritornare (default: 100)
    """
    mt5_tool_path = MT5_TOOL_PATH.replace("Administrator", username)
    return await run(ip, username, password, "get_expert_log", terminal=terminal, lines=lines, mt5_tool_path=mt5_tool_path)


@mcp.tool
async def get_symbols(ip: str, username: str, password: str, terminal: str) -> list:
    """
    Ritorna tutti gli strumenti di trading disponibili sul terminale.

    Args:
        ip: Indirizzo IP della VPS
        username: Username SSH della VPS (solitamente "Administrator")
        password: Password SSH della VPS
        terminal: Nome corto del terminale, ottenuto da list_terminals
    """
    mt5_tool_path = MT5_TOOL_PATH.replace("Administrator", username)
    return await run(ip, username, password, "get_symbols", terminal=terminal, mt5_tool_path=mt5_tool_path)


@mcp.tool
async def get_symbol_info(ip: str, username: str, password: str, terminal: str, symbol: str) -> dict:
    """
    Ritorna i dettagli completi di uno strumento specifico.
    Include: contract_size, volume_min/max/step, swap_long/short, bid, ask, spread.

    Args:
        ip: Indirizzo IP della VPS
        username: Username SSH della VPS (solitamente "Administrator")
        password: Password SSH della VPS
        terminal: Nome corto del terminale, ottenuto da list_terminals
        symbol: Nome dello strumento (es. "EURUSD", "XAUUSD")
    """
    mt5_tool_path = MT5_TOOL_PATH.replace("Administrator", username)
    return await run(ip, username, password, "get_symbol_info", terminal=terminal, symbol=symbol, mt5_tool_path=mt5_tool_path)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
