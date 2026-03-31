"""
ssh.py — Modulo SSH per mt5-remote-reader-mcp
"""

import json
import asyncio
import http.client
import os
import time
import threading
import urllib.parse
import paramiko
from typing import Any

DEFAULT_MT5_TOOL_PATH = r"C:\Users\Administrator\Desktop\mt5_tool.py"
DEFAULT_VPS_USER = "Administrator"
PYTHON_INSTALLER_URL = "https://www.python.org/ftp/python/3.8.10/python-3.8.10-amd64.exe"
PYTHON_INSTALLER_PATH = r"C:\Windows\Temp\python-3.8.10-amd64.exe"

# ─── SSH Connection Pool ─────────────────────────────────────────────────────
_ssh_pool: dict[str, paramiko.SSHClient] = {}
_ssh_pool_lock = threading.Lock()

# ─── Daemon alive cache ───────────────────────────────────────────────────────
# Evita di riverificare il daemon ad ogni chiamata.
# Struttura: {ip: timestamp_ultima_verifica_ok}
_daemon_cache: dict[str, float] = {}
_daemon_cache_lock = threading.Lock()
_DAEMON_CACHE_TTL = 30.0  # secondi

# ─── Result cache ────────────────────────────────────────────────────────────
# Cache Mac-side delle risposte del daemon per evitare round trip SSH ripetuti.
# Struttura: {(ip, function, terminal, days, lines, symbol): (timestamp, data)}
_result_cache: dict[tuple, tuple[float, Any]] = {}
_result_cache_lock = threading.Lock()

_CACHE_TTL: dict[str, float] = {
    "get_open_positions":  5.0,
    "get_account_info":    5.0,
    "get_all_positions":   5.0,
    "list_terminals":     15.0,
    "get_trade_history":  60.0,
    "get_expert_log":     10.0,
    "get_symbols":       300.0,
    "get_symbol_info":    30.0,
}


def _ssh_connect(ip: str, username: str, password: str) -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(ip, username=username, password=password, timeout=15)
    except (ConnectionRefusedError, TimeoutError, OSError) as e:
        raise RuntimeError(
            f"SSH non raggiungibile su {ip}: {e}. "
            "Se la VPS è vergine, usa il tool get_vps_installer per ottenere "
            "il file di setup da eseguire sulla VPS prima di procedere."
        ) from e
    return client


def _get_ssh_client(ip: str, username: str, password: str) -> paramiko.SSHClient:
    """Restituisce una connessione SSH dal pool, riconnettendo se necessario."""
    with _ssh_pool_lock:
        client = _ssh_pool.get(ip)
        if client is not None:
            transport = client.get_transport()
            if transport is not None and transport.is_active():
                return client
            try:
                client.close()
            except Exception:
                pass
        client = _ssh_connect(ip, username, password)
        _ssh_pool[ip] = client
        return client


def _exec(client: paramiko.SSHClient, cmd: str) -> tuple:
    _, stdout, stderr = client.exec_command(cmd)
    return stdout.read().decode("utf-8").strip(), stderr.read().decode("utf-8").strip()


# ─── Daemon management ───────────────────────────────────────────────────────

def _check_daemon(client: paramiko.SSHClient) -> bool:
    """Verifica se il daemon MT5 è in ascolto su 127.0.0.1:9999 via SSH tunnel diretto."""
    try:
        transport = client.get_transport()
        channel = transport.open_channel("direct-tcpip", ("127.0.0.1", 9999), ("127.0.0.1", 0))
        channel.close()
        return True
    except Exception:
        return False


def _ensure_daemon_running(client: paramiko.SSHClient, mt5_tool_path: str) -> bool:
    """Verifica che il daemon MT5 sia attivo; se no, lo avvia. Ritorna True se attivo."""
    ip = client.get_transport().getpeername()[0] if client.get_transport() else ""
    with _daemon_cache_lock:
        last_ok = _daemon_cache.get(ip, 0.0)
        if time.time() - last_ok < _DAEMON_CACHE_TTL:
            return True  # verificato di recente, skip check

    if _check_daemon(client):
        with _daemon_cache_lock:
            _daemon_cache[ip] = time.time()
        return True

    # Avvia daemon come processo detached (creationflags=8 = DETACHED_PROCESS su Windows)
    path_repr = repr(mt5_tool_path)  # gestisce correttamente i backslash Windows
    start_cmd = (
        f"python -c \"import subprocess; "
        f"subprocess.Popen(['python', {path_repr}, '--daemon'], creationflags=8)\""
    )
    _exec(client, start_cmd)

    # Attende fino a 10 secondi (5 tentativi × 2s)
    for _ in range(5):
        time.sleep(2)
        if _check_daemon(client):
            with _daemon_cache_lock:
                _daemon_cache[ip] = time.time()
            return True

    return False


def _query_daemon(
    client: paramiko.SSHClient,
    function: str,
    terminal: str | None,
    days: int,
    lines: int,
    symbol: str | None,
) -> dict | list:
    """Interroga il daemon HTTP sulla VPS via SSH tunnel diretto.
    Nessun processo Python avviato sulla VPS — il Mac parla direttamente col daemon.
    """
    params: dict[str, str] = {"function": function}
    if terminal:
        params["terminal"] = terminal
    if days != 30:
        params["days"] = str(days)
    if lines != 100:
        params["lines"] = str(lines)
    if symbol:
        params["symbol"] = urllib.parse.quote(symbol, safe="")

    qs = "&".join(f"{k}={v}" for k, v in params.items())

    transport = client.get_transport()
    channel = transport.open_channel("direct-tcpip", ("127.0.0.1", 9999), ("127.0.0.1", 0))
    try:
        conn = http.client.HTTPConnection("127.0.0.1", 9999, timeout=10)
        conn.sock = channel  # bypassa connect(), usa il tunnel SSH
        conn.request("GET", f"/?{qs}")
        response = conn.getresponse()
        data = response.read().decode("utf-8")
    finally:
        channel.close()

    if not data:
        raise RuntimeError("Daemon non ha risposto.")

    return json.loads(data)


def _query_daemon_cached(
    client: paramiko.SSHClient,
    function: str,
    terminal: str | None,
    days: int,
    lines: int,
    symbol: str | None,
) -> dict | list:
    """Come _query_daemon ma con cache Mac-side a TTL per evitare round trip ripetuti."""
    ip = client.get_transport().getpeername()[0]
    key = (ip, function, terminal, days, lines, symbol)
    ttl = _CACHE_TTL.get(function, 10.0)

    with _result_cache_lock:
        entry = _result_cache.get(key)
        if entry is not None:
            ts, cached_data = entry
            if time.time() - ts < ttl:
                return cached_data  # cache hit: <1ms

    result = _query_daemon(client, function, terminal, days, lines, symbol)

    with _result_cache_lock:
        _result_cache[key] = (time.time(), result)

    return result


# ─── Run via SSH ─────────────────────────────────────────────────────────────

def _run_ssh(
    ip: str,
    username: str,
    password: str,
    cmd: str,
    mt5_tool_path: str | None = None,
    function: str | None = None,
    terminal: str | None = None,
    days: int = 30,
    lines: int = 100,
    symbol: str | None = None,
) -> dict | list:
    # Step 1: ottieni connessione SSH dal pool (riusa se possibile)
    client = _get_ssh_client(ip, username, password)
    _ip = ip  # alias per uso nel blocco except sotto

    # Step 2: tenta via daemon (path veloce)
    if mt5_tool_path and function:
        try:
            if _ensure_daemon_running(client, mt5_tool_path):
                result = _query_daemon_cached(client, function, terminal, days, lines, symbol)
                if not (isinstance(result, dict) and result.get("error") == "terminal_reconnecting"):
                    return result
        except Exception:
            # Invalida cache così la prossima chiamata riverifica il daemon
            with _daemon_cache_lock:
                _daemon_cache.pop(_ip, None)
            pass  # fallback al metodo classico

    # Step 3: fallback — esecuzione diretta di mt5_tool.py via SSH
    try:
        out, err = _exec(client, cmd)
    except (EOFError, paramiko.SSHException):
        # Connessione stantia: rimuovi dal pool e riprova una volta
        with _ssh_pool_lock:
            _ssh_pool.pop(ip, None)
        client = _get_ssh_client(ip, username, password)
        out, err = _exec(client, cmd)

    if not out:
        raise RuntimeError(f"Nessun output dalla VPS. Stderr: {err}")

    try:
        return json.loads(out)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Output non valido dalla VPS: {out[:200]}") from e


def _setup_vps_sync(ip: str, username: str, password: str, mt5_tool_path: str) -> dict:
    steps = []
    client = _ssh_connect(ip, username, password)
    with _ssh_pool_lock:
        _ssh_pool[ip] = client  # salva nel pool per riuso
    try:
        # 1. Controlla Python
        out, err = _exec(client, "python --version")
        python_version = out or err
        if python_version and "Python" in python_version:
            steps.append(f"Python trovato: {python_version}")
        else:
            steps.append("Python non trovato — installazione in corso...")
            _exec(client, '[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12')
            _exec(client, (
                f'powershell -Command "Invoke-WebRequest -Uri {PYTHON_INSTALLER_URL} '
                f'-OutFile {PYTHON_INSTALLER_PATH}"'
            ))
            _exec(client, f'{PYTHON_INSTALLER_PATH} /quiet InstallAllUsers=1 PrependPath=1 Include_test=0')
            out, err = _exec(client, "python --version")
            python_version = out or err
            if "Python" in (python_version or ""):
                steps.append(f"Python installato: {python_version}")
            else:
                raise RuntimeError(
                    "Installazione Python fallita. "
                    "Installa Python 3.8+ manualmente dalla VPS (python.org) "
                    "e spunta 'Add Python to PATH' durante l'installazione."
                )

        # 2. Installa librerie
        steps.append("Installazione MetaTrader5 e psutil...")
        _exec(client, "python -m pip install MetaTrader5 psutil --quiet")
        steps.append("Librerie installate.")

        # 3. Copia mt5_tool.py via SFTP
        steps.append("Copia mt5_tool.py sulla VPS...")
        local_mt5_tool = os.path.join(os.path.dirname(__file__), "mt5_tool.py")
        if not os.path.exists(local_mt5_tool):
            raise RuntimeError(
                f"mt5_tool.py non trovato in {local_mt5_tool}. "
                "Reinstalla il pacchetto con: pip install --force-reinstall mt5-remote-reader-mcp"
            )
        sftp = client.open_sftp()
        remote_path = mt5_tool_path.replace("\\", "/")
        remote_dir = "/".join(remote_path.split("/")[:-1])
        try:
            sftp.mkdir(remote_dir)
        except Exception:
            pass
        sftp.put(local_mt5_tool, remote_path)
        sftp.close()
        steps.append(f"mt5_tool.py copiato in {mt5_tool_path}")

        # 4. Avvia daemon
        steps.append("Avvio daemon MT5 (porta 9999)...")
        daemon_ok = _ensure_daemon_running(client, mt5_tool_path)
        if daemon_ok:
            steps.append("Daemon attivo su 127.0.0.1:9999.")
        else:
            steps.append("Daemon non avviato — verrà avviato automaticamente alla prima query.")

        # 5. Test
        steps.append("Test connessione MT5...")
        out, err = _exec(client, f"python {mt5_tool_path} --function list_terminals")

    finally:
        pass  # connessione resta nel pool, non si chiude

    if not out:
        return {
            "status": "warning",
            "steps": steps,
            "message": "Setup completato ma MT5 non risponde. Verifica che MetaTrader 5 sia aperto e loggato sulla VPS.",
            "terminals": {}
        }

    try:
        terminals = json.loads(out)
        steps.append(f"MT5 risponde — {len(terminals)} terminale/i trovato/i.")
        return {
            "status": "ok",
            "steps": steps,
            "message": "VPS configurata e pronta.",
            "terminals": terminals
        }
    except json.JSONDecodeError:
        return {
            "status": "warning",
            "steps": steps,
            "message": "Setup completato ma risposta MT5 non valida. Verifica che MetaTrader 5 sia aperto.",
            "terminals": {}
        }


async def setup(ip: str, username: str, password: str, mt5_tool_path: str = DEFAULT_MT5_TOOL_PATH) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _setup_vps_sync, ip, username, password, mt5_tool_path)


async def run(
    ip: str,
    username: str,
    password: str,
    function: str,
    terminal: str | None = None,
    days: int = 30,
    lines: int = 100,
    symbol: str | None = None,
    mt5_tool_path: str = DEFAULT_MT5_TOOL_PATH,
) -> dict | list:
    cmd = f"python {mt5_tool_path} --function {function}"
    if terminal:
        cmd += f" --terminal {terminal}"
    if days != 30:
        cmd += f" --days {days}"
    if lines != 100:
        cmd += f" --lines {lines}"
    if symbol:
        cmd += f" --symbol {symbol}"

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: _run_ssh(ip, username, password, cmd, mt5_tool_path, function, terminal, days, lines, symbol)
    )
