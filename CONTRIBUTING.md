# Contributing to FIFA 16 Revival

Thanks for helping keep FIFA 16 Ultimate Team alive.

## License promise (share-alike)

This project is licensed under the **GNU GPL v3** (see `LICENSE`).

In plain terms:

1. You may use, study, modify, and redistribute this software for free.
2. **If you modify it, you must publish your modified source** — push your
   updates back (a fork, a branch, or a pull request to this repository).
   Keeping changes private violates the license.
3. Contributions submitted to this repository are licensed under the same
   GPLv3 terms.

We enforce this so the community always owns the full server stack and no
one can ship closed-source "premium" forks of community work.

## How to contribute

1. Fork the repository and create a feature branch:
   `git checkout -b feature/my-improvement`
2. Follow the existing code style (Python: PEP 8, 4-space indent).
3. Run the smoke tests before pushing:
   `python tests\test_smoke.py`
4. Document protocol discoveries in `docs/CLIENT_FINDINGS.md` — every
   packet capture, endpoint, and setting counts.
5. Open a pull request with a clear description of what changed and why.

## Priority areas

- Real client packet captures against the local server (Phase 1)
- Correct Blaze redirector responses (`winter15.gosredirector.ea.com`)
- FUT RS4 API payloads (`X-UT-SID` flow — see `docs/CLIENT_FINDINGS.md`)
- EASFC POW services (`X-POW-SID` flow)
- 2026 squad/database updates

## Legal ground rules

- Do **not** commit any EA game files, big archives, player photos, or
  server binaries. This repo contains only our original code and docs.
- Do not add paid gates, telemetry, or account requirements to core
  server functionality.
