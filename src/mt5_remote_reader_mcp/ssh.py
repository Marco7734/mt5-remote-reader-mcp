"""
ssh.py — Modulo SSH per mt5-remote-reader-mcp
Gestisce la connessione alla VPS e l'esecuzione di mt5_tool.py
"""

import json
import asyncio
import os
import paramiko

DEFAULT_MT5_TOOL_PATH = r"C:\Users\Administrator\Desktop\mt5_tool.py"
DEFAULT_VPS_USER = "Administrator"
PYTHON_INSTALLER_URL = "https://www.python.org/ftp/python/3.8.10/python-3.8.10-amd64.exe"
PYTHON_INSTALLER_PATH = r"C:\Windows\Temp\python-3.8.10-amd64.exe"


def _ssh_connect(ip: str, username: str, password: str) -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(ip, username=username, password=password, timeout=15)
    return client


def _exec(client: paramiko.SSHClient, cmd: str, timeout: int = 300) -> tuple:
    """Esegue un comando e aspetta il completamento. Ritorna (stdout, stderr)."""
    _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    # Aspetta che il comando finisca
    stdout.channel.recv_exit_status()
    return stdout.read().decode("utf-8").strip(), stderr.read().decode("utf-8").strip()


def _run_ssh(ip: str, username: str, password: str, cmd: str) -> dict:
    client = _ssh_connect(ip, username, password)
    try:
        out, err = _exec(client, cmd)
    finally:
        client.close()

    if not out:
        raise RuntimeError(f"Nessun output dalla VPS. Stderr: {err}")

    try:
        return json.loads(out)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Output non valido dalla VPS: {out[:200]}") from e


def _setup_vps_sync(ip: str, username: str, password: str, mt5_tool_path: str) -> dict:
    steps = []
    client = _ssh_connect(ip, username, password)
    try:
        # 1. Controlla Python
        out, err = _exec(client, "python --version")
        python_version = out or err
        if python_version and "Python" in python_version:
            steps.append(f"Python trovato: {python_version}")
        else:
            # Scarica installer (può richiedere qualche minuto)
            steps.append("Python non trovato — download installer in corso (attendere)...")
            out, err = _exec(client, (
                f'powershell -Command "Invoke-WebRequest -Uri \'{PYTHON_INSTALLER_URL}\' '
                f'-OutFile \'{PYTHON_INSTALLER_PATH}\' -UseBasicParsing"'
            ), timeout=300)

            # Installa silenziosamente
            steps.append("Installazione Python in corso (attendere)...")
            out, err = _exec(client, (
                f'"{PYTHON_INSTALLER_PATH}" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0'
            ), timeout=300)

            # Verifica installazione — serve aprire una nuova sessione per vedere il PATH aggiornato
            client.close()
            client = _ssh_connect(ip, username, password)
            out, err = _exec(client, "python --version")
            python_version = out or err
            if "Python" in (python_version or ""):
                steps.append(f"Python installato: {python_version}")
            else:
                raise RuntimeError("Installazione Python fallita. Installa Python 3.8+ manualmente sulla VPS.")

        # 2. Installa librerie
        steps.append("Installazione MetaTrader5 e psutil...")
        _exec(client, "python -m pip install MetaTrader5 psutil --quiet", timeout=180)
        steps.append("Librerie installate.")

        # 3. Copia mt5_tool.py via SFTP
        steps.append("Copia mt5_tool.py sulla VPS...")
        local_mt5_tool = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "mt5_tool.py")
        )
        if not os.path.exists(local_mt5_tool):
            raise RuntimeError(f"mt5_tool.py non trovato localmente: {local_mt5_tool}")
        sftp = client.open_sftp()
        remote_path = mt5_tool_path.replace("\\", "/")
        sftp.put(local_mt5_tool, remote_path)
        sftp.close()
        steps.append(f"mt5_tool.py copiato in {mt5_tool_path}")

        # 4. Test
        steps.append("Test connessione MT5...")
        out, err = _exec(client, f"python {mt5_tool_path} --function list_terminals", timeout=30)

    finally:
        client.close()

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
    return await loop.run_in_executor(None, _run_ssh, ip, username, password, cmd)
