"""
ssh.py — Modulo SSH per mt5-remote-reader-mcp
Gestisce la connessione alla VPS e l'esecuzione di mt5_tool.py
"""

import json
import asyncio
import paramiko

DEFAULT_MT5_TOOL_PATH = r"C:\Users\Administrator\Desktop\mt5_tool.py"
DEFAULT_VPS_USER = "Administrator"


def _run_ssh(ip: str, password: str, cmd: str, user: str = DEFAULT_VPS_USER) -> dict:
    """Esegue un comando sulla VPS via SSH e ritorna il risultato parsato come dict/list."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(ip, username=user, password=password, timeout=15)
        _, stdout, stderr = client.exec_command(cmd)
        output = stdout.read().decode("utf-8").strip()
        error = stderr.read().decode("utf-8").strip()
    finally:
        client.close()

    if not output:
        raise RuntimeError(f"Nessun output dalla VPS. Stderr: {error}")

    try:
        return json.loads(output)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Output non valido dalla VPS: {output[:200]}") from e


async def run(
    ip: str,
    password: str,
    function: str,
    terminal: str | None = None,
    days: int = 30,
    lines: int = 100,
    symbol: str | None = None,
    mt5_tool_path: str = DEFAULT_MT5_TOOL_PATH,
    vps_user: str = DEFAULT_VPS_USER,
) -> dict | list:
    """
    Esegue una funzione di mt5_tool.py sulla VPS via SSH.
    Wrapper async attorno a _run_ssh (usa executor per non bloccare l'event loop).
    """
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
        None, _run_ssh, ip, password, cmd, vps_user
    )
