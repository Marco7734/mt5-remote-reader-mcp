"""
vps_manager.py — Rubrica VPS per mt5-remote-reader-mcp

Salva le credenziali VPS in:
    ~/.mt5-reader/vps.json  (cifrato con Fernet)

La chiave di cifratura è salvata nel keychain del sistema operativo
(macOS Keychain / Windows Credential Manager / Linux Secret Service)
tramite la libreria `keyring`.

Se keyring non è disponibile, cade back su una chiave derivata
da un file locale ~/.mt5-reader/.key (permessi 600).
"""

import json
import os
import base64
from pathlib import Path
from cryptography.fernet import Fernet

# --- Percorsi ---
CONFIG_DIR = Path.home() / ".mt5-reader"
VPS_FILE = CONFIG_DIR / "vps.json"
KEY_FILE = CONFIG_DIR / ".key"

KEYRING_SERVICE = "mt5-remote-reader"
KEYRING_KEY_NAME = "fernet-key"


# --- Gestione chiave di cifratura ---

def _get_or_create_key() -> bytes:
    """
    Recupera la chiave Fernet dal keychain di sistema.
    Se non esiste la crea e la salva.
    Fallback: file locale ~/.mt5-reader/.key con permessi 600.
    """
    # Prova keyring
    try:
        import keyring
        existing = keyring.get_password(KEYRING_SERVICE, KEYRING_KEY_NAME)
        if existing:
            return base64.urlsafe_b64decode(existing.encode())
        # Crea nuova chiave
        key = Fernet.generate_key()
        keyring.set_password(KEYRING_SERVICE, KEYRING_KEY_NAME, base64.urlsafe_b64encode(key).decode())
        return key
    except Exception:
        pass

    # Fallback: file locale
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if KEY_FILE.exists():
        return KEY_FILE.read_bytes()
    key = Fernet.generate_key()
    KEY_FILE.write_bytes(key)
    try:
        os.chmod(KEY_FILE, 0o600)
    except Exception:
        pass
    return key


def _fernet() -> Fernet:
    return Fernet(_get_or_create_key())


# --- Lettura / scrittura rubrica ---

def _load_raw() -> dict:
    """Legge e decifra il file vps.json. Ritorna dict vuoto se non esiste."""
    if not VPS_FILE.exists():
        return {}
    try:
        encrypted = VPS_FILE.read_bytes()
        decrypted = _fernet().decrypt(encrypted)
        return json.loads(decrypted.decode())
    except Exception:
        return {}


def _save_raw(data: dict) -> None:
    """Cifra e salva il file vps.json."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    encrypted = _fernet().encrypt(json.dumps(data, indent=2).encode())
    VPS_FILE.write_bytes(encrypted)
    try:
        os.chmod(VPS_FILE, 0o600)
    except Exception:
        pass


# --- API pubblica ---

def save_vps(name: str, ip: str, username: str, password: str) -> dict:
    """
    Aggiunge o aggiorna una VPS nella rubrica.
    
    Args:
        name:     Nome amichevole (es. "ftmo", "axi")
        ip:       Indirizzo IP pubblico della VPS
        username: Username SSH (solitamente "Administrator")
        password: Password SSH
    
    Returns:
        {"status": "ok", "name": name, "ip": ip}
    """
    data = _load_raw()
    data[name.lower()] = {
        "ip": ip,
        "username": username,
        "password": password,
    }
    _save_raw(data)
    return {
        "status": "ok",
        "message": f"VPS '{name}' salvata correttamente.",
        "name": name.lower(),
        "ip": ip,
        "username": username,
    }


def list_vps() -> dict:
    """
    Elenca le VPS in rubrica senza mostrare le password.
    
    Returns:
        Dict con nome → {ip, username} per ogni VPS salvata.
    """
    data = _load_raw()
    return {
        name: {"ip": info["ip"], "username": info["username"]}
        for name, info in data.items()
    }


def delete_vps(name: str) -> dict:
    """
    Rimuove una VPS dalla rubrica.
    
    Args:
        name: Nome amichevole della VPS da rimuovere
    
    Returns:
        {"status": "ok"} oppure {"status": "not_found"}
    """
    data = _load_raw()
    key = name.lower()
    if key not in data:
        return {"status": "not_found", "message": f"VPS '{name}' non trovata in rubrica."}
    del data[key]
    _save_raw(data)
    return {"status": "ok", "message": f"VPS '{name}' rimossa."}


def get_vps_credentials(name: str) -> dict:
    """
    Recupera le credenziali complete di una VPS (uso interno del server).
    
    Args:
        name: Nome amichevole della VPS
    
    Returns:
        {"ip": ..., "username": ..., "password": ...}
    
    Raises:
        KeyError: se la VPS non esiste in rubrica
    """
    data = _load_raw()
    key = name.lower()
    if key not in data:
        available = list(data.keys())
        raise KeyError(
            f"VPS '{name}' non trovata in rubrica. "
            f"VPS disponibili: {available}. "
            f"Usa save_vps per aggiungerne una nuova."
        )
    return data[key]
