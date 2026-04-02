# Changelog

All notable changes to this project will be documented in this file.

---

## [0.6.1] — 2026-04-02

### Changed — Versione nel nome dei file

- `setup_mt5_vps.exe` → `setup_mt5_vps_0.6.1.exe` (e versioni successive portano sempre il numero)
- `build_exe.bat`: nome exe aggiornato con versione esplicita
- `server.py`: URL download e nome file locale costruiti dinamicamente da `_VERSION`

---

## [0.6.0] — 2026-04-02

### Added — SSH IP whitelist nel VPS installer

- `setup_vps_installer.py`: menu all'avvio con due opzioni (setup completo / gestione accessi SSH)
- Funzione `manage_whitelist()`: permette di aggiungere manualmente IP autorizzati a connettersi
  via SSH alla VPS, direttamente dall'exe sulla VPS
- Gli IP vengono accumulati (non sostituiti) nella regola Windows Firewall tramite `_add_ip_to_whitelist()`
- Al primo setup la porta 22 parte **bloccata per tutti** — nessun IP è autorizzato finché
  l'utente non ne aggiunge uno esplicitamente dall'exe
- Sezione "Sicurezza SSH" alla fine del setup: mostra gli IP autorizzati e permette di
  aggiungerne uno prima di uscire
- Messaggio finale esplicito: "Puoi chiudere questa finestra" — chiarisce che OpenSSH
  e il daemon MT5 girano come servizi Windows indipendenti

---

## [0.5.0] — 2026-03-30

### Added — VPS installer embedded + tool get_vps_installer

- `setup_vps_installer.py`: installer Windows incluso nel pacchetto — installa OpenSSH,
  Python, MetaTrader5, psutil e mt5_tool.py su una VPS vergine (gira sulla VPS, non via SSH)
- Nuovo tool MCP `get_vps_installer`: scarica `setup_mt5_vps.exe` da GitHub Releases
  in ~/Downloads e restituisce istruzioni per configurare una VPS vergine prima di usare connect_vps
- `build_exe.bat`: script per ricompilare l'exe su Windows dopo modifiche al sorgente
- `ssh.py`: errore SSH più descrittivo — suggerisce get_vps_installer se la connessione fallisce

### Changed

- `server.py` instructions: aggiornate per guidare l'agente all'uso di get_vps_installer
  quando connect_vps fallisce per SSH non disponibile

---

## [0.4.0] — 2026-03-29

### Added

- Tool `get_account_info(vps, terminal)`: ritorna balance, equity, margin, free margin,
  margin level, profit flottante, valuta, leva, login, broker del conto MT5
- Funzione `get_account_info(terminal_path)` in `mt5_tool.py` lato VPS

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
