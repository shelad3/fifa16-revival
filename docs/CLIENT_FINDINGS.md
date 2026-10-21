# FIFA 16 Client Network Findings

Scanned from: `D:\FIFA-16-SteamRIP.com\FIFA 16` (deep binary scan of fifa16.exe, fifa16.bin, CardsDLLzf.dll, powdllzf.dll, origin_emu.dll, crash.dmp)

## Critical Discovery: The REAL Blaze Redirector Hostname

The production Blaze redirector is **NOT** plain `gosredirector.ea.com` — it is environment-prefixed:

```
winter15.gosredirector.ea.com        ← production Blaze redirector (THE key host)
winter15.gosredirector.sdev.ea.com   ← dev fallback
winter15.gosredirector.stest.ea.com  ← test fallback
winter15.gosredirector.scert.ea.com  ← certificate server (TLS validation)
```

`winter15` is EA's internal environment name for the FIFA 16 generation (shipped Fall 2015).
These four hostnames appear together in `fifa16.exe` in the HTTP redirector client block, next to:
- `X-BLAZE-ERRORCODE` HTTP response header parsing
- XML `<errorCode>` element parsing
- `compress` / `identity` Accept-Encoding negotiation

The redirector flow is **HTTP-based** (ProtoHttp user-agent: `ProtoHttp %d.%d/DS %d.%d.%d.%d.%d (Windows)`),
trying sdev → stest → scert → production.

## All EA Service Endpoints Found

### Blaze / GOS
| Domain | Purpose |
|--------|---------|
| `winter15.gosredirector.ea.com` | **Production Blaze redirector — main entry point** |
| `winter15.gosredirector.sdev.ea.com` | Dev redirector fallback |
| `winter15.gosredirector.stest.ea.com` | Test redirector fallback |
| `winter15.gosredirector.scert.ea.com` | Redirector certificate server |
| `gosredirector.scert.ea.com` | Certificate server (unprefixed variant) |
| `gosredirector.sdev.ea.com` | Dev (unprefixed variant) |
| `gosredirector.stest.ea.com` | Test (unprefixed variant) |
| `gosca.ea.com` | Blaze CA (certificate authority) |
| `gateway.ea.com` | Blaze gateway |
| `gateway.int.ea.com` | Blaze gateway (internal) |
| `demangler.ea.com` | C++ demangler (debug symbol service) |

### Authentication
| Domain | Purpose |
|--------|---------|
| `accounts.ea.com` | EA accounts |
| `signin.ea.com` | Sign-in service |
| `accounts.int.ea.com` | Accounts (internal) |
| `signin.int.ea.com` | Sign-in (internal) |

### FUT / EASFC Web Services (HTTP, separate from Blaze)
| Domain | Purpose |
|--------|---------|
| `content.lt.easfc.ea.com:8080` | FUT live content service (powdllzf.dll) |
| `pas.gt.easfc.ea.com:8094` | Player account service (powdllzf.dll) |
| `http://easw.easports.com:8099/` | EA Sports World (CardsDLLzf.dll) |
| `peach.online.ea.com` | Online service host (fifa16.exe) |
| `http://fifa.easports.com` | Main site |
| `http://www.easportsfootball.com` | Football site (powdllzf.dll) |

### Diagnostics / Telemetry
| Domain | Purpose |
|--------|---------|
| `http://elephant.online.ea.com/bugsentry` | BugSentry crash reporting |
| `https://gen4.reports.tools.gos.ea.com/bugsentry` | BugSentry (Gen4 = FIFA 16 engine gen) |
| `http://test.reports.tools.gos.ea.com/bugsentry` | BugSentry test |
| `https://pin-river.data.ea.com` / `river.data.ea.com` | PIN telemetry |
| `https://fifa15.service.easports.com/xmshd_collector/v1/file/doupload.json?` | Telemetry file upload (shared with FIFA 15) |
| `https://fifa.test.service.easports.com/xmshd_collector/v1/` | Telemetry test |

### Legacy Test (dead code, useful for URL patterns)
| Domain | Purpose |
|--------|---------|
| `pg.fifa12.test.easportsworld.ea.com:8309` | Legacy FUT (FIFA 12) |
| `pg.fifa13.test.easportsworld.ea.com:8306/fifa/fltOnlineAssets/2013/fut/leaderboard/images` | Legacy FUT (FIFA 13) |

## Client Override Mechanisms (HUGE)

The client has **built-in override settings** that can redirect it to a local server
**without any hosts-file or binary patching**. Setting keys found in the binaries:

### Blaze overrides (fifa16.exe — Aardvark settings system)
```
ONLINE/BLAZEIP          ← Blaze server IP
ONLINE/BLAZEPORT        ← Blaze server port
ONLINE/BLAZEENV         ← Environment name
ONLINE/ENABLE_GEOLOCATIONRULE
BLAZE_SERVICE_NAME_OVERRIDE
BLAZE_CONN_TIMEOUT / BLAZE_LOGGING / BLAZE_ID
```

### FUT API overrides (CardsDLLzf.dll)
```
FUT_TARGET_HOSTNAME     ← FUT API host (direct override)
FUT_TARGET_PORT         ← FUT API port
FUT_RS4_APIURL_<region> ← Full API base URL per region (RS4 = REST API gen)
FUT_RS4_URL_<region>
FUT/MODULE_BASEURL_<region>
FUT/SINGLE_BASEURL_<region>
FUT_DNS_TIMEOUT / FUT_PING_TIMEOUT / FUT_MAX_HOPS / FUT_PUMP_RATE_MILLSEC
FIFA_FUT_ALLOW_PING
FUT_STAT_TUNING / ONLINE/NO_AUTO_SQUAD / ONLINE/FUTDYNAMICMESSAGES_TUTORIAL_MSG_URL
```

### EASFC POW overrides (powdllzf.dll)
```
FIFA_POW_URL                    ← POW web API base URL (env var or setting)
FIFA_POW_CONTENT_SERVER_URL
FIFA_POW_NUCLEUS_PROXY_URL
FIFA_POW_MMM_URL
ONLINE/POW_CUSTOMURL            ← settings-path form of the same
ONLINE/POW_CUSTOMCONTENTURL
ONLINE/FORCE-NON-SECURE         ← disable TLS for POW traffic
POW/SKU, POW/GAMETITLE, POW/CATALOGUENAME, POW/SHARED_CATALOGUENAME
```

### OSDK / EASW overrides (fifa16.exe)
```
OSDK_EASW_REQ_URL               ← SportsWorld/EASW request base URL
OSDK_EASW_GF_FILE_URL           ← GameFace file download URL
```

Settings are loaded via the **Aardvark settings system** ("LoadAArdvarkFiles") from:
`product.ini` → `platform.ini` → `sku.ini` → `cl.ini` → ... → **`user.ini`** (highest priority,
initialized at boot: "Init user.ini") and `test.ini`. Command line is parsed via
`GetCommandLineW`/`CommandLineToArgvW`, so settings are likely also passable as
command-line switches. Environment variables named above are read directly.

## FUT HTTP API Surface (CardsDLLzf.dll — RS4 REST client)

Protocol: HTTPS/HTTP REST, JSON request/response, gzip.
Base URL composition: `game/<region>` + module paths; also `%s/pow/mm/` and `/fut/`.

### Headers
```
X-UT-SID: %s            ← session ID (from /auth)
X-UT-VALIDATE: true     ← validation flag
Accept: application/json
Content-Type: application/json
Hash: %s                ← HMAC signature (see Events.FUT.HMACFail)
Cache-Control / X-Cache-Control: max-age=...
Content-Encoding: gzip
```

### Endpoints (from binary strings)
```
/auth                    /security               /trustInfo
/captcha                 /captcha/               /phishing
/trusteddevice           /requestedPrivileges
/club                    /clubUser               /user /user/list /user/history
/squad                   /squad/mode
/auctionhouse            /transfermarket         /trade /tradePile /watchList
/relist                  /sold                   /pricelimits /pileSize
/item /items             /item/resource          /consumables/
/credits                 /fifapoints
/draft /draft/state      /draft/choose           /draft/autocomplete /draft/mode
/season /season/user     /season/user/history    /season/friendly     /division/
/tournament              /tournament/user        /match
/store                   /offer /offer/          /purchase/mode/      /purchased
/purchasegroup           /grant/award
/loan/player/            /loan/players           /loanPlayerReward
/totw                    /leaderboards           /leaderboards/options
/stats /stats/           /stats/staff
/keepalive               /status                 /reset /validate
/active /active/user/    /activeMessage          /livemessage
/managerquest            /tutorialpopups
/dreamsquad/dreamsquadpacklist.json
/icebreaker/icebreakerpacklist.json
/choices/captain /choices/difficulty /choices/formation /choices/manager /choices/player
/defid                   /marketdata             /teams /clientdata
/ini/fcc.ini
/g4/fut2dheads.big       /g4/single/
```

## EASFC POW Web API Surface (powdllzf.dll — RestClient::PowSession)

Protocol: REST JSON, gzip. Session header: `X-POW-SID: %s`.
Request fields: `clientVersion`, `nuc` (nucleus id), `nucleusPersonaId`,
`nucleusPersonaDisplayName`, `locale`, `priorityLevel`, `sku`, `regionCode`, `isReadOnly`.

### Endpoints
```
/auth  /security  /trustInfo  /requestedPrivileges  /healthcheck/system/all
/nucleus/entitlements
/bank/user/account        /bank/currency/
/inventory/item           /inventory/item/list
/store/game/              /store/catalog/          /store/gift/
/store/gift/catalog/      /store/gift/list
/catalog/                 /catalog/list            /assembly
/pfyc/                    /pfyc/user               /pfyc/user/club
/pfyc/user/prefs/shareinfo
/lvl/user/tiergp/         /lvl/weight/tiergp/      /users/info/tiergp/   /tiertp/
/user/friends
/communication/all        /communication/all/countUnread
/communication/attributes/type/   /communication/count   /communication/type/
/message /message/list /comment
/news/* /banners/ /activity/count /v2/activity
/chal/user/prog  /cap/info  /mm/game/  /matchday/
/gamechange/gamechangetype/
/attributes/type/  /type/tag/name/  /item/  /item/list
/pow/cacheresponse/{alertcache.json,catalogcache.txt,newscache.json,useritemscache.txt}
```

## OSDK EASW (SportsWorld) HTTP Headers (fifa16.exe)

```
EASW-Userid: %s
EASW-Session: %s
EASW-Token: %s
EASW-Request-Signature: %s
EASW-Content-Signature: %s
Content-Type: multipart/form-data; boundary=THIS_IS_THE_OSDK_V4_SPORTSWORLD_MIME_MULTIPART_BOUNDARY_TEXT
```

## Heat Protocol (Blaze over HTTP)

The RS4 REST decoder supports multiple content types (classes found: `HttpDecoder`,
`Heat2Decoder`, `Xml2Decoder`, `JsonDecoder`, `RestDecoder`):
```
Content-Type: application/heat          ← Blaze "Heat" binary over HTTP
Content-Type: application/json
Content-Type: application/xml
X-BLAZE-METHOD: <method>                ← Blaze method routing on HTTP requests
X-BLAZE-ERRORCODE: <code>               ← error channel from redirector
```

## Key Strings (fifa16.exe)

```
BLAZEIP  BLAZEPORT  BLAZEENV  BLAZE_ID  BLAZE_LOGGING
BLAZE_SERVICE_NAME  BLAZE_SERVICE_NAME_OVERRIDE
BLAZE_CONN_TIMEOUT  BLAZE_CONN_FAILED  BLAZESERVER_CONN_LOST
BLAZE_HUB_ALREADY_INITIALIZED  BLAZE_SERVER_ERROR
http://localhost:8000                                      ← built-in localhost fallback
http://%s:%d/getPeerAddress?myIP=%s&myPort=%d&version=1.0  ← P2P peer discovery
https://%s:%u/qos/qos | /qos/firewall | /qos/firetype     ← QoS probes
FE::FIFA::BlazeCustomMessage
```

FUT event telemetry keys (suggest error taxonomy for server):
`Events.FUT.Exception`, `Events.FUT.HMACFail`, `Events.FUT.CaptchaRequired`,
`Events.FUT.CaptchaFailed`, `Events.FUT.SportsWorldOperationFail`,
`Events.FUT.StoreService`, `Events.FUT.MatchEndFail`, `Events.FUT.ExtendGameSession`

## Identity Structure (from rune.ini)

```ini
[Settings]
UserName=STEAMRIP
Language=en_US
UserId=1144668899
PersonaId=1000200030000
```

## Crack / DRM Layer

- `fifa16.exe` loads **`DSN.dll`** (string table contains `DSN.dll` + tag `DELUSIONAL`).
- `DSN.dll` references **`origin_emu.dll`** — socket-level Origin emulator (SteamRIP crack).
- `fifa16.bin` and `fifa16.dsn` are same size (117,906,200) but different hashes; both are PE files
  containing identical EA string tables (packed/decoy variants).
- `install.ini`: `[STREAMINGINSTALL] LIMITED_MODE=1`, `[BUGSENTRY] ENABLE_REPORTING=1`
- The origin emulator may already satisfy the license-check gate that blocked FIFA 15 revivals.

## Crash Dump Analysis (crash.dmp, 53KB minidump — truncated)

- Build paths: `E:\s1\fifa16g4\buildsys\build\runtime\pc64\{sysdllzf,BCEnginezf,powdllzf}.pdb`
  → internal codename **fifa16g4** (Gen4 engine), built with VS2012 (msvcp110.amd64).
- Crash occurred on Intel HD Graphics (igd10iumd64.pdb) — driver-level, not network related.
- Exception stream truncated/corrupt (record pointers past EOF) — not usable for protocol info.
- No fifa16.pdb in dump; exe has no embedded PDB path (stripped retail build).

## Important DLLs

| DLL | Size | Purpose |
|-----|------|---------|
| `fifa16.exe` | 118MB | Main game, Blaze SDK + OSDK + Heat REST embedded |
| `CardsDLLzf.dll` | 2.3MB | **FUT client (RS4 REST, X-UT-SID, full UT API)** |
| `BCEnginezf.dll` | 1.4MB | Backend Connection Engine |
| `powdllzf.dll` | 954KB | **EASFC POW client (X-POW-SID, Football Club services)** |
| `FootballCompEngzf.dll` | 731KB | Competition engine (career/leagues) |
| `DSN.dll` | 177KB | Crack loader (loads origin_emu.dll) |
| `origin_emu.dll` | 530KB | Origin emulator (DRM bypass, socket hooks) |
| `dbdata.dll` | 2.6MB | Database engine |
| `Core/libeay32.dll` + `ssleay32.dll` | — | OpenSSL (TLS pinning risk: check cert validation) |

## Implications for Server

1. **Redirect `winter15.gosredirector.ea.com` → 127.0.0.1** (plus sdev/stest/scert) — NOT plain gosredirector.ea.com
2. **Better: set `ONLINE/BLAZEIP=127.0.0.1` + `ONLINE/BLAZEPORT`** (or env vars) — no hosts edit needed
3. **FUT API can be redirected via `FUT_TARGET_HOSTNAME`/`FUT_TARGET_PORT`** or `FUT_RS4_APIURL_<region>` — no patching needed
4. **POW API can be redirected via `FIFA_POW_URL`** + `ONLINE/FORCE-NON-SECURE` to skip TLS
5. **`user.ini` in the game dir** is the highest-priority settings override file — primary config vector
6. **FUT requests carry an HMAC `Hash:` header** — server must either verify with a known key or accept anything; `Events.FUT.HMACFail` confirms client-side check exists (may only log)
7. **Redirector protocol is HTTP + XML/JSON/Heat**, not raw TCP Blaze on first hop — our redirector should speak HTTP
8. **`fifa15.service.easports.com`** is shared — Aurora 15 (FIFA 15 revival) knowledge applies directly
9. **P2P peer discovery** (`getPeerAddress` HTTP) and **QoS probes** (`/qos/*`) are plain HTTP — easy to stub
10. **Two parallel web stacks** must be served: FUT RS4 (X-UT-SID) and EASFC POW (X-POW-SID), plus OSDK EASW (EASW-* headers)
