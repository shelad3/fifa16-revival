# FIFA 16 Network Protocol Notes

## Overview

FIFA 16 (PC) uses EA's proprietary **Blaze** protocol for online services.
The Blaze protocol is a binary TCP protocol using **TDF (Tag Data Format)**
for payload encoding, with optional TLS encryption.

## Connection Flow

```
1. Client resolves EA domain via DNS
   └── www.ea.com → EA's DNS servers

2. Client connects to Blaze Redirector (port 42127)
   └── Redirector returns auth server address

3. Client connects to Auth Server (port 42133/42230)
   ├── PreAuth (component 0x00, cmd 0x00)
   ├── Authentication (component 0x00, cmd 0x01)
   └── PostAuth (component 0x00, cmd 0x02)

4. Client connects to FUT HTTP API (port 443)
   └── REST endpoints for Ultimate Team data
```

## Blaze Packet Structure

Each packet has a 12-byte header:

```
Offset  Size  Field
0x00    2     Packet type (big-endian)
0x02    1     Component ID
0x03    1     Command ID
0x04    2     Error code (big-endian)
0x06    2     Message ID (big-endian)
0x08    4     Payload length (big-endian)
0x0C    N     Payload (TDF-encoded)
```

## Component IDs

| ID | Name | Description |
|----|------|-------------|
| 0x00 | Authentication | Login, session tokens |
| 0x01 | GameManager | Matchmaking, game sessions |
| 0x02 | UserSessions | Session management |
| 0x03 | Presence | Online status |
| 0x04 | Friends | Friends list |
| 0x05 | Gameplay | In-game data |
| 0x06 | Stats | Player statistics |
| 0x07 | Messaging | Messaging service |
| 0x08 | Gameroom | Custom game rooms |
| 0x09 | GameReporting | Match results |
| 0x0A | Util | Ping, config, network info |
| 0x0B | Clubs | Club/team management |
| 0x0C | Channels | Chat channels |

## TDF (Tag Data Format)

TDF values have a 7-byte header followed by data:

```
Offset  Size  Field
0x00    3     Name (ASCII, null-padded)
0x03    4     Type code (ASCII, null-padded)
0x07    N     Type-specific data
```

### Type Codes

| Code | Type | Data Format |
|------|------|-------------|
| STR | String | 2-byte length + UTF-8 data |
| I32 | Int32 | 4 bytes, little-endian, signed |
| UI32 | UInt32 | 4 bytes, little-endian, unsigned |
| I64 | Int64 | 8 bytes, little-endian, signed |
| UI64 | UInt64 | 8 bytes, little-endian, unsigned |
| BOOL | Boolean | 1 byte (0x00=false, 0x01=true) |
| BLOB | Binary | 2-byte length + raw data |
| STRC | Struct | Nested TDF values |
| LIST | List | Element type (4 bytes) + count (2 bytes) + elements |
| MAP | Map | Key type + value type + count + entries |
| PAIR | Pair | First value + second value |

## Known Authentication Flow

### 1. PreAuth (cmd 0x00)
Client sends initial handshake with platform info.
Server responds with session ID and auth token.

### 2. Authentication (cmd 0x01)  
Client sends credentials/token.
Server responds with user ID, persona ID, and session key.

### 3. PostAuth (cmd 0x02)
Client confirms session.
Server sends FUT API endpoint configuration.

## FUT HTTP API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| /fut/auth | GET | Authenticate, get session token |
| /fut/claim | GET | Initial claim/setup |
| /fut/user/accountinfo | GET | Account info, clubs |
| /fut/squad | GET/POST | Squad management |
| /fut/club | GET | Club information |
| /fut/store/packs | GET | Available packs |
| /fut/pack/purchase | POST | Buy a pack |
| /fut/pack/open | GET | Open purchased pack |
| /fut/transfer/market | GET | Transfer listings |
| /fut/transfer/item | POST | List item for sale |
| /fut/transfer/bid | POST | Place bid |
| /fut/playercatalog | GET | Player database |
| /fut/competition | GET | Competition info |

## Reverse Engineering Notes

### Tools Needed
- **Wireshark** — Packet capture
- **x64dbg** — Dynamic analysis (Windows)
- **Ghidra** — Static analysis / decompilation
- **Frida** — Runtime instrumentation

### Key Files
- `fifa16.exe` — Main game executable
- `CardsDLL.dll` — FUT client logic (if present)
- Game data files in `data/` directory

### DNS Redirect
FIFA 16 resolves EA servers via DNS. Redirecting DNS to localhost
allows us to intercept connections:

```
127.0.0.1 www.ea.com
127.0.0.1 ff-nrt-r3.fifa16.ea.com
127.0.0.1 utas.fut.ea.com
```

### TLS Considerations
FIFA 16 may use TLS with certificate pinning. Options:
1. Patch the certificate store in the binary
2. Install a custom CA certificate
3. Use a TLS-terminating proxy

### The License Check Gate (from FIFA 15 research)
FIFA 15's client checks for an authenticated EA session before
connecting to Blaze. If no valid session exists, the Blaze connection
is never initiated. This is upstream of the network stack.

FIFA 16 likely has similar logic. Solutions:
1. Runtime hooking (Frida) to force connection
2. Binary patching to skip the check
3. Providing a fake EA session token

This is the primary challenge for FIFA 16 revival.

## Protocol Differences from FIFA 15

FIFA 16 was released one year after FIFA 15 on the same engine
(Ignite on PC). Key similarities:
- Same Blaze protocol version
- Similar component structure  
- Same TDF encoding
- Similar FUT HTTP API

Expected differences:
- Updated player catalog format
- Possible new TDF fields
- Different server domain names
- Updated authentication tokens

## Sources

- KyroGeorge2/FIFA-15-Local-FUT — FUT HTTP API reference
- openBlase — TDF encoding reference
- grid-leak/blaze — Blaze protocol in Rust
- Horizzon1/fifa15-local-fut — Blaze server implementation
- Loopizzle/FIFA-14-Ultimate-Team — Protocol documentation
