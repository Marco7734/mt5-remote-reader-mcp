"""
server.py — MT5 Remote Reader MCP Server
Server MCP read-only per monitorare conti MetaTrader 5 su VPS Windows remote via SSH.
"""

from fastmcp import FastMCP
from .ssh import run, setup, DEFAULT_MT5_TOOL_PATH
from .vps_manager import save_vps as _save_vps, list_vps as _list_vps, delete_vps as _delete_vps, get_vps_credentials
from importlib.metadata import version as _pkg_version
import asyncio
import os
import shutil
import urllib.request

_VERSION = _pkg_version("mt5-remote-reader-mcp")

mcp = FastMCP(
    name="mt5-remote-reader",
    instructions=(
        "Read-only MCP server per monitorare conti MetaTrader 5 su VPS Windows remote via SSH. "
        "Le credenziali VPS sono salvate in una rubrica locale sicura (~/.mt5-reader/vps.json). "
        "Prima di tutto controlla le VPS disponibili con list_vps. "
        "Se non ce ne sono, chiedi all'utente le credenziali e usa save_vps per salvarle — "
        "non dovrà reinserirle mai più. "
        "Poi usa connect_vps per configurare la VPS se è la prima volta (installa Python, "
        "le librerie e copia mt5_tool.py sulla VPS via SSH). "
        "Se connect_vps fallisce perché SSH non è raggiungibile, la VPS è probabilmente "
        "vergine e va prima configurata: usa get_vps_installer per ottenere il file exe "
        "da far eseguire all'utente direttamente sulla VPS. "
        "Dopo il setup usa list_terminals per scoprire i terminali disponibili, "
        "e infine i tool di monitoraggio con il nome corto del terminale. "
        "Questo server non esegue mai operazioni di trading — è esclusivamente in lettura."
    ),
)

MT5_TOOL_PATH = os.environ.get("MT5_TOOL_PATH", DEFAULT_MT5_TOOL_PATH)


# ─────────────────────────────────────────────
#  VERSIONE
# ─────────────────────────────────────────────

@mcp.tool
async def get_version() -> dict:
    """
    Restituisce la versione installata di mt5-remote-reader-mcp.
    Utile per verificare che il package sia aggiornato.
    """
    return {"version": _VERSION, "package": "mt5-remote-reader-mcp"}


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

    Se SSH non è raggiungibile (VPS vergine), scarica automaticamente
    setup_mt5_vps.exe in ~/Downloads e fornisce le istruzioni per eseguirlo.

    MetaTrader 5 deve essere già installato e loggato sulla VPS.

    Args:
        vps: Nome amichevole della VPS in rubrica (es. "ftmo"). Usa list_vps per vedere quelle disponibili.
    """
    creds = get_vps_credentials(vps)
    mt5_tool_path = MT5_TOOL_PATH.replace("Administrator", creds["username"])
    try:
        return await setup(creds["ip"], creds["username"], creds["password"], mt5_tool_path)
    except RuntimeError as e:
        err_str = str(e).lower()
        if any(k in err_str for k in ("ssh non raggiungibile", "connection refused", "timed out", "timeout", "ssh")):
            # VPS vergine: SSH non ancora attivo — scarica l'installer automaticamente
            installer_result = await get_vps_installer()
            if installer_result.get("status") == "ok":
                return {
                    "status": "setup_required",
                    "message": (
                        "La VPS non ha SSH attivo: probabilmente è vergine e va preparata prima. "
                        "Ho già scaricato il file di setup sul tuo Mac."
                    ),
                    "installer_path": installer_result["file"],
                    "istruzioni": (
                        "PASSAGGI DA SEGUIRE:\n"
                        f"1. Vai in ~/Downloads e trovi il file: setup_mt5_vps.exe\n"
                        "2. Collegati alla VPS tramite RDP (Remote Desktop).\n"
                        "3. Copia setup_mt5_vps.exe dalla tua cartella Downloads alla VPS "
                        "(trascina il file nella finestra RDP, oppure usa copia-incolla).\n"
                        "4. Sulla VPS: tasto destro sul file → 'Esegui come amministratore'.\n"
                        "5. Attendi il completamento (2-5 minuti). "
                        "Vedrai una finestra nera con i progressi — non chiuderla.\n"
                        "6. Quando la finestra si chiude da sola, torna qui e dimmi 'fatto' "
                        "così riprovo la connessione."
                    ),
                }
            else:
                return {
                    "status": "setup_required",
                    "message": "La VPS non ha SSH attivo e non ho potuto scaricare l'installer automaticamente.",
                    "download_error": installer_result.get("message", ""),
                    "istruzioni": (
                        "Scarica manualmente setup_mt5_vps.exe da: "
                        "https://github.com/Marco7734/mt5-remote-reader-mcp/releases/latest "
                        "e seguila sulla VPS come amministratore."
                    ),
                }
        raise


_INSTALLER_FILENAME = f"MT5RemoteReader_Setup_{_VERSION}.exe"
_INSTALLER_URL = (
    "https://github.com/Marco7734/mt5-vps-installer"
    f"/releases/latest/download/MT5RemoteReader_Setup_{_VERSION}.exe"
)


@mcp.tool
async def get_vps_installer() -> dict:
    """
    Scarica setup_mt5_vps_{version}.exe in ~/Downloads e restituisce il percorso.

    Usare quando connect_vps fallisce perché SSH non è ancora attivo sulla VPS.
    L'exe va copiato sulla VPS Windows ed eseguito come amministratore:
    tasto destro → "Esegui come amministratore".

    L'exe installa automaticamente sulla VPS:
    - OpenSSH Server (abilita la connessione SSH)
    - Python 3.8
    - Librerie MetaTrader5 e psutil
    - mt5_tool.py sul Desktop della VPS

    Dopo aver eseguito l'exe, tornare qui e richiamare connect_vps.
    """
    downloads = os.path.join(os.path.expanduser("~"), "Downloads")
    os.makedirs(downloads, exist_ok=True)
    dest = os.path.join(downloads, _INSTALLER_FILENAME)

    try:
        urllib.request.urlretrieve(_INSTALLER_URL, dest)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {
                "status": "error",
                "message": (
                    "Nessuna release trovata su GitHub. "
                    "Scarica manualmente l'installer da: "
                    "https://github.com/Marco7734/mt5-remote-reader-mcp/releases"
                )
            }
        return {"status": "error", "message": f"Errore download ({e.code}): {e}"}
    except Exception as e:
        return {"status": "error", "message": f"Download fallito: {e}"}

    return {
        "status": "ok",
        "file": dest,
        "istruzioni": (
            "1. Copia il file sulla VPS Windows (via RDP → trascina il file). "
            "2. Tasto destro sul file → 'Esegui come amministratore'. "
            "3. Attendi il completamento (2-5 minuti). "
            "4. Torna qui e chiama connect_vps per completare la configurazione."
        )
    }


# ─────────────────────────────────────────────
#  TOOL DI MONITORAGGIO
# ─────────────────────────────────────────────

async def _fetch_vps_positions(vps_name: str) -> dict:
    """Interroga una singola VPS: legge terminali e posizioni di tutti in un'unica chiamata batch."""
    try:
        creds = get_vps_credentials(vps_name)
        mt5_tool_path = MT5_TOOL_PATH.replace("Administrator", creds["username"])
        ip, user, pwd = creds["ip"], creds["username"], creds["password"]

        result = await run(ip, user, pwd, "get_all_positions", mt5_tool_path=mt5_tool_path)

        if isinstance(result, dict) and "error" not in result:
            return {"status": "ok", "terminals": result}
        else:
            return {"status": "error", "detail": result}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@mcp.tool
async def get_all_open_positions() -> dict:
    """
    Legge le posizioni aperte su TUTTE le VPS in rubrica in parallelo.
    Non serve specificare nulla: recupera automaticamente tutte le VPS salvate
    e tutti i terminali MT5 attivi su ciascuna.

    Usare questo tool invece di get_open_positions quando si vuole
    una panoramica completa di tutti i conti monitorati.

    Ritorna: {nome_vps: {nome_terminale: [posizioni]}} per ogni VPS raggiungibile.
    Le VPS non raggiungibili compaiono con status "error" invece delle posizioni.
    """
    all_vps = _list_vps()
    if not all_vps:
        return {"status": "empty", "message": "Nessuna VPS in rubrica."}

    names = list(all_vps.keys())
    results = await asyncio.gather(
        *[_fetch_vps_positions(name) for name in names],
        return_exceptions=True
    )

    return {
        name: (res if not isinstance(res, Exception) else {"status": "error", "detail": str(res)})
        for name, res in zip(names, results)
    }



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
