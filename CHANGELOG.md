# Changelog

All notable changes to this project will be documented in this file.

---

## [0.3.0] — 2026-03-28

### Added — Rubrica VPS locale cifrata

- Nuovo modulo `vps_manager.py`: gestisce una rubrica VPS salvata in `~/.mt5-reader/vps.json`
- Le credenziali sono cifrate con Fernet (AES-128-CBC); la chiave è nel keychain del sistema operativo (macOS Keychain / Windows Credential Manager / Linux Secret Service) tramite `keyring`, con fallback su file locale `~/.mt5-reader/.key` (permessi 600)
- 3 nuovi tool MCP: `save_vps`, `list_vps`, `delete_vps`
- Tutti i tool di monitoraggio ora accettano `vps="nome"` invece di `ip + username + password`
- Le credenziali non appaiono mai più nei prompt dopo il primo inserimento
- Nuove dipendenze: `cryptography>=41.0.0`, `keyring>=24.0.0`

### Changed

- `connect_vps(vps)` — ora accetta solo il nome VPS in rubrica
- `list_terminals(vps)` — idem
- `get_open_positions(vps, terminal)` — idem
- `get_trade_history(vps, terminal, days)` — idem
- `get_expert_log(vps, terminal, lines)` — idem
- `get_symbols(vps, terminal)` — idem
- `get_symbol_info(vps, terminal, symbol)` — idem

---

## [0.2.1] — 2026-03-28

### Fixed

- `connect_vps` ora sostituisce correttamente il placeholder `Administrator` nel path quando si usa un username diverso

---

## [0.2.0] — 2026-03-28

### Added

- Tool `connect_vps` per configurare automaticamente una VPS vergine
- Installazione automatica di Python se non presente sulla VPS
- `username` come parametro esplicito in tutti i tool (rimosso default hardcoded)

---

## [0.1.1] — 2026-03-28

### Fixed

- Gestione encoding UTF-16 nei log MT5

---

## [0.1.0] — 2026-03-28

### Initial release

- MCP server in stdio mode usando FastMCP 3.x
- SSH via paramiko (no pre-configured keys needed)
- 6 tool read-only: `list_terminals`, `get_open_positions`, `get_trade_history`, `get_expert_log`, `get_symbols`, `get_symbol_info`
- Async tool execution
- `setup_vps.py` per configurazione VPS da Mac/Linux
- Pubblicato su PyPI come `mt5-remote-reader-mcp`
