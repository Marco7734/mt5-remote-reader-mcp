"""
setup_vps.py — Configura una VPS Windows per trading-skill

Uso:
    python setup_vps.py <ip> <password>

Esempio:
    python setup_vps.py 107.189.25.91 29a3MxVyqUydF5

Cosa fa:
    1. Si connette alla VPS via SSH con password
    2. Verifica che Python sia installato
    3. Installa MetaTrader5 e psutil via pip
    4. Copia mt5_tool.py sulla VPS
    5. Esegue un test (list_terminals) per verificare che tutto funzioni
    6. Stampa il risultato
"""

import sys
import os
import paramiko


VPS_USER = "Administrator"
MT5_TOOL_REMOTE_PATH = "C:\\Users\\Administrator\\Desktop\\mt5_tool.py"
MT5_TOOL_LOCAL_PATH = os.path.join(os.path.dirname(__file__), "mt5_tool.py")


def log(msg):
    print(f"  → {msg}")


def run_cmd(ssh, cmd):
    _, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode("utf-8").strip()
    err = stderr.read().decode("utf-8").strip()
    return out, err


def setup(ip, password):
    print()
    print("=" * 50)
    print("  trading-skill — Setup VPS")
    print("=" * 50)
    print(f"  IP:   {ip}")
    print(f"  User: {VPS_USER}")
    print()

    # 1. Connessione SSH
    log("Connessione SSH alla VPS...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(ip, username=VPS_USER, password=password, timeout=15)
    except Exception as e:
        print(f"\n  ERRORE: impossibile connettersi alla VPS: {e}")
        sys.exit(1)
    log("Connesso.")

    # 2. Verifica Python
    log("Verifica Python...")
    out, err = run_cmd(ssh, "python --version")
    if not out and not err:
        print("\n  ERRORE: Python non trovato sulla VPS.")
        print("  Installa Python 3.8+ sulla VPS e riprova.")
        sys.exit(1)
    version = out or err  # python --version scrive su stderr in alcune versioni
    log(f"Python trovato: {version}")

    # 3. Installa librerie
    log("Installazione MetaTrader5...")
    out, err = run_cmd(ssh, "python -m pip install MetaTrader5 --quiet")
    log("Installazione psutil...")
    out, err = run_cmd(ssh, "python -m pip install psutil --quiet")
    log("Librerie installate.")

    # 4. Copia mt5_tool.py
    log("Copia mt5_tool.py sulla VPS...")
    if not os.path.exists(MT5_TOOL_LOCAL_PATH):
        print(f"\n  ERRORE: mt5_tool.py non trovato in {MT5_TOOL_LOCAL_PATH}")
        sys.exit(1)
    sftp = ssh.open_sftp()
    sftp.put(MT5_TOOL_LOCAL_PATH, MT5_TOOL_REMOTE_PATH.replace("\\", "/"))
    sftp.close()
    log(f"Copiato in {MT5_TOOL_REMOTE_PATH}")

    # 5. Test
    log("Test connessione MT5...")
    out, err = run_cmd(ssh, f"python {MT5_TOOL_REMOTE_PATH} --function list_terminals")

    ssh.close()

    print()
    if out and out.startswith("{"):
        print("=" * 50)
        print("  Setup completato con successo!")
        print("=" * 50)
        print()
        print("  Terminali MT5 rilevati:")
        import json
        try:
            terminals = json.loads(out)
            for name, info in terminals.items():
                login = info.get("login", "?")
                broker = info.get("broker", "?")
                connected = "✓" if info.get("connected") else "✗"
                print(f"    [{connected}] {name} — login {login} ({broker})")
        except Exception:
            print(out)
        print()
        print("  La VPS è pronta. Puoi usare trading-skill con:")
        print(f"    ip: {ip}")
        print(f"    password: {password}")
        print()
    else:
        print("  ATTENZIONE: il setup è completato ma il test MT5 non ha risposto.")
        print("  Verifica che MetaTrader 5 sia installato e loggato sulla VPS.")
        if err:
            print(f"  Errore: {err}")
        print()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python setup_vps.py <ip> <password>")
        sys.exit(1)

    ip = sys.argv[1]
    password = sys.argv[2]
    setup(ip, password)
