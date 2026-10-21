# FIFA 16 Revival - Development Roadmap

## Overview

Estimated timeline for a small team (2-3 people) or dedicated solo developer
with reverse engineering experience.

## Phase 0: Setup & Recon (Week 1-2)

- [x] Project structure created
- [x] Blaze protocol foundation written
- [x] FUT HTTP API skeleton created
- [x] Database schema defined
- [ ] Install FIFA 16, run recon tools
- [ ] Capture initial network traffic
- [ ] Document FIFA 16's specific endpoints
- [ ] Compare with FIFA 15's known protocol

**Deliverable:** Network traffic map of FIFA 16's connection flow

## Phase 1: Local FUT (Week 3-6)

- [ ] Get Blaze login flow working
- [ ] Get FUT menus loading
- [ ] Implement player catalog (import from FIFA 16 database)
- [ ] Implement pack opening
- [ ] Implement squad management
- [ ] Implement club persistence
- [ ] Transfer market (local only)

**Deliverable:** FIFA 16 loads into FUT offline against local server

### Key Milestones
- Client connects to Blaze redirector
- Client authenticates successfully
- FUT hub screen loads
- Can open packs
- Can create/edit squads
- Data persists across restarts

## Phase 2: Client Connection (Week 4-8, overlaps Phase 1)

- [ ] Bypass license check gate (Frida hooking or binary patch)
- [ ] Handle TLS certificate verification
- [ ] DNS redirect working
- [ ] Client reliably connects to local server

**Deliverable:** Unmodified FIFA 16 connects to local server via DNS redirect

### Key Challenges
- The license check gate (learned from FIFA 15)
- TLS certificate pinning
- Possibly encrypted configuration files

## Phase 3: Online Features (Week 8-14)

- [ ] Implement matchmaking (GameManager component)
- [ ] UDP relay for P2P gameplay
- [ ] Two clients can find each other
- [ ] Two clients can reach kit select screen
- [ ] Solve MatchReady/kickoff handshake (coordinate with FIFA 17 team)
- [ ] Match result reporting

**Deliverable:** Two players can matchmake and play a full match

### Known Issues (from FIFA 17 revival)
- MatchReady deadlock: clients hang on kit select
- Solution may involve NotifyPlayerJoining, NotifyJoiningPlayerInitiateConnections,
  NotifyPlatformHostInitialized, NotifyGameReportingIdChange notifications

## Phase 4: Polish & 2026 Squads (Week 12-16)

- [ ] Update player database to 2025-26 season
- [ ] Update team kits and badges
- [ ] Transfer market with AI buyers
- [ ] Seasons/divisions
- [ ] Draft mode
- [ ] Leaderboards
- [ ] Bug fixes and stability

**Deliverable:** Feature-complete FIFA 16 with current squads

## Phase 5: Community (Week 16+)

- [ ] Create Discord server
- [ ] Build launcher/installer
- [ ] Beta testing program
- [ ] Public release

---

## Technical Debt / Known Issues

- TDF decoder's struct-end finding is approximate (may need refinement)
- Error handling needs hardening
- No rate limiting on any endpoints
- Transfer market has no anti-cheat
- Pack opening doesn't validate pack ownership

## Resources

- **Aurora 15 Discord:** discord.gg/aurorafut
- **SoccerGaming Forums:** soccergaming.com
- **FIFA Modding Community:** FIFA Infinity, ModdingWay

## Estimated Effort

| Phase | Solo Dev | Small Team (2-3) |
|-------|----------|------------------|
| Phase 0 | 2 weeks | 1 week |
| Phase 1 | 4-6 weeks | 2-3 weeks |
| Phase 2 | 4-6 weeks | 2-4 weeks |
| Phase 3 | 6-8 weeks | 3-4 weeks |
| Phase 4 | 2-4 weeks | 1-2 weeks |
| **Total** | **18-26 weeks** | **9-14 weeks** |
