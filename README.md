# FIFA 16 Revival Server

A community-run server revival project for FIFA 16 PC Ultimate Team,
inspired by the successful Aurora 15 (FIFA 15) and FIFA 17 revival projects.

## What is this?

FIFA 16's online servers were shut down by EA on February 14, 2023.
This project recreates the server infrastructure needed to bring back
Ultimate Team and online features on PC.

## Status

| Component | Status |
|-----------|--------|
| Project structure | Complete |
| Blaze protocol foundation | In Progress |
| FUT HTTP API | In Progress |
| Database layer | In Progress |
| Client connection | Not Started |
| Online matchmaking | Not Started |

## Requirements

- Windows 10/11
- Python 3.11+
- FIFA 16 PC (legitimate copy required)
- Run as Administrator (for DNS redirect)

## Quick Start

```bash
# 1. Install dependencies
setup.bat

# 2. Start the server
.venv\Scripts\activate
python run_server.py

# 3. In a separate admin terminal, setup DNS redirect
python recon\setup_dns_redirect.py install

# 4. Launch FIFA 16
```

## Project Structure

```
fifa16-revival/
├── run_server.py          # Main entry point
├── setup.bat              # Setup script
├── requirements.txt       # Python dependencies
├── config/
│   └── server_config.json # Server configuration
├── server/
│   ├── blaze/             # Blaze protocol server
│   │   ├── __init__.py    # TDF encoder/decoder, packet structures
│   │   ├── redirector.py  # Blaze redirector (port 42127)
│   │   └── auth_server.py # Authentication server
│   ├── fut_api/
│   │   └── app.py         # FUT HTTP API server
│   ├── database/
│   │   └── db.py          # SQLite database layer
│   └── logging_setup.py   # Logging configuration
├── recon/                 # Reverse engineering tools
│   ├── analyze_packets.py # Network journal analyzer
│   ├── analyze_client.py  # FIFA 16 client scanner
│   └── setup_dns_redirect.py # DNS redirect setup
├── tools/                 # Client modification tools
│   ├── backup_game.py     # Game file backup/restore
│   └── patch_client.py    # Binary patching utilities
├── data/                  # Database and game data
├── logs/                  # Server logs and network journal
└── docs/                  # Documentation
```

## Architecture

```
FIFA 16 Client
    │
    ├── DNS Redirect → 127.0.0.1
    │
    ├── Blaze Protocol (TCP)
    │   ├── Redirector (port 42127)
    │   ├── Auth Server (port 42230)
    │   └── GameManager, UserSessions, etc.
    │
    ├── FUT HTTP API (port 42129)
    │   ├── /fut/auth
    │   ├── /fut/club
    │   ├── /fut/squad
    │   ├── /fut/store/packs
    │   └── /fut/transfer/market
    │
    └── UDP Relay (port 3659) — for P2P match gameplay
```

## Related Projects

- **Aurora 15** — Working FIFA 15 online revival ([discord.gg/aurorafut](https://discord.gg/aurorafut))
- **KyroGeorge2/FIFA-15-Local-FUT** — FIFA 15 local FUT server
- **Impulsum** — FIFA 13/14/17 revival project
- **openBlase** — Open-source Blaze protocol implementation

## Key Findings (summary)

The retail client can be redirected **without binary patching**:

- Real Blaze redirector: `winter15.gosredirector.ea.com` (HTTP-based, plus sdev/stest/scert fallbacks)
- FUT API override: `FUT_TARGET_HOSTNAME` / `FUT_TARGET_PORT` settings (or `FUT_RS4_APIURL_<region>`)
- POW override: `FIFA_POW_URL` + `ONLINE/FORCE-NON-SECURE`
- Blaze override: `ONLINE/BLAZEIP` / `ONLINE/BLAZEPORT`
- `user.ini` in the game directory is the highest-priority settings override

Full details: [`docs/CLIENT_FINDINGS.md`](docs/CLIENT_FINDINGS.md)

## Website

A project landing page lives at [`docs/index.html`](docs/index.html) — enable it via
GitHub Pages (Settings → Pages → Deploy from branch → `main` / `docs`).

## License

**GNU GPL v3** — free to use, study, modify, and redistribute, but derivative works
must also be published under the same license. If you improve the server, push your
updates back (fork, branch, or PR). See [`LICENSE`](LICENSE) and
[`CONTRIBUTING.md`](CONTRIBUTING.md).

## Legal

This is an independent preservation project. It is not affiliated with,
endorsed by, or connected to Electronic Arts Inc., EA Sports, FIFA, or
any of their licensees. FIFA 16 is a trademark of Electronic Arts Inc.

This project does not distribute any EA game files, assets, or server
binaries. Users must own a legitimate copy of FIFA 16 PC.

## Contributing

Protocol discoveries go in `docs/CLIENT_FINDINGS.md`; see
[`CONTRIBUTING.md`](CONTRIBUTING.md) for workflow and the share-alike rules.
`docs/REVERSE_ENGINEERING.md` documents the Blaze protocol and FIFA 16's
network architecture.
