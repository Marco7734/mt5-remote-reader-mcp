"""
ssh.py — Modulo SSH per mt5-remote-reader-mcp
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


def _exec(client: paramiko.SSHClient, cmd: str) -> tuple:
    _, stdout, stderr = client.exec_command(cmd)
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
            steps.append("Python non trovato — installazione in corso...")
            # Imposta TLS 1.2 e scarica Python
            _exec(client, '[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12')
            _exec(client, (
                f'powershell -Command "Invoke-WebRequest -Uri {PYTHON_INSTALLER_URL} '
                f'-OutFile {PYTHON_INSTALLER_PATH}"'
            ))
            # Installa silenziosamente
            _exec(client, f'{PYTHON_INSTALLER_PATH} /quiet InstallAllUsers=1 PrependPath=1 Include_test=0')
            # Verifica
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
        # mt5_tool.py è dentro il package stesso
        local_mt5_tool = os.path.join(os.path.dirname(__file__), "mt5_tool.py")
        if not os.path.exists(local_mt5_tool):
            raise RuntimeError(
                f"mt5_tool.py non trovato in {local_mt5_tool}. "
                "Reinstalla il pacchetto con: pip install --force-reinstall mt5-remote-reader-mcp"
            )
        sftp = client.open_sftp()
        remote_path = mt5_tool_path.replace("\\", "/")
        # Assicura che la cartella esista
        remote_dir = "/".join(remote_path.split("/")[:-1])
        try:
            sftp.mkdir(remote_dir)
        except Exception:
            pass
        sftp.put(local_mt5_tool, remote_path)
        sftp.close()
        steps.append(f"mt5_tool.py copiato in {mt5_tool_path}")

        # 4. Test
        steps.append("Test connessione MT5...")
        out, err = _exec(client, f"python {mt5_tool_path} --function list_terminals")

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
