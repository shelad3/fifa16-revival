"""
FUT HTTP API Server

FIFA 16's Ultimate Team mode uses a separate HTTP API alongside the
Blaze protocol. This server handles:
  - Authentication/session management
  - Club and squad management
  - Pack opening
  - Transfer market
  - Player catalog
  - Match result reporting
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, Optional

from aiohttp import web

log = logging.getLogger("fut_api")


class FUTApiServer:
    """FUT HTTP API server."""

    def __init__(self, config, db):
        self.name = "FUT HTTP API"
        self.config = config
        self.db = db
        self.app = web.Application()
        self.runner = None
        self.sessions: Dict[str, dict] = {}
        self._setup_routes()

    def _setup_routes(self):
        self.app.router.add_get("/fut/auth", self.handle_auth)
        self.app.router.add_get("/fut/claim", self.handle_claim)
        self.app.router.add_get("/fut/user/accountinfo", self.handle_account_info)
        self.app.router.add_get("/fut/iteminfo", self.handle_item_info)
        self.app.router.add_get("/fut/playercatalog", self.handle_player_catalog)
        self.app.router.add_get("/fut/squad", self.handle_get_squad)
        self.app.router.add_post("/fut/squad", self.handle_save_squad)
        self.app.router.add_get("/fut/club", self.handle_club)
        self.app.router.add_post("/fut/pack/purchase", self.handle_buy_pack)
        self.app.router.add_get("/fut/pack/open", self.handle_open_pack)
        self.app.router.add_get("/fut/store/packs", self.handle_get_packs)
        self.app.router.add_get("/fut/transfer/market", self.handle_transfer_market)
        self.app.router.add_post("/fut/transfer/item", self.handle_list_item)
        self.app.router.add_post("/fut/transfer/bid", self.handle_place_bid)
        self.app.router.add_get("/fut/competition", self.handle_competition)
        self.app.router.add_get("/fut/challenge", self.handle_challenge)
        self.app.router.add_get("/", self.handle_root)
        self.app.router.add_get("/health", self.handle_health)

    async def start(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(
            self.runner,
            self.config["host"],
            self.config["port"]
        )
        await site.start()
        log.info("FUT API listening on %s:%s",
                 self.config["host"], self.config["port"])

    async def stop(self):
        if self.runner:
            await self.runner.cleanup()

    def _get_session(self, request) -> Optional[dict]:
        session_token = request.headers.get("X-UT-SHARD-ID", "")
        auth_header = request.headers.get("Authorization", "")

        if auth_header.startswith("Bearer "):
            session_token = auth_header[7:]

        session = self.sessions.get(session_token)
        if session:
            session["last_seen"] = time.time()
        return session

    def _make_response(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        return web.Response(
            body=body,
            status=status,
            content_type="application/json"
        )

    async def handle_root(self, request):
        return self._make_response({
            "name": "FIFA 16 Revival FUT API",
            "version": "0.1.0",
            "status": "running"
        })

    async def handle_health(self, request):
        return self._make_response({"status": "ok"})

    async def handle_auth(self, request):
        """POST /fut/auth - Authenticate and get session token."""
        session_token = str(uuid.uuid4())
        user_id = request.query.get("userId", "1001")

        self.sessions[session_token] = {
            "token": session_token,
            "user_id": int(user_id),
            "created_at": time.time(),
            "last_seen": time.time()
        }

        log.info("FUT auth: user %s, token %s", user_id, session_token)

        return self._make_response({
            "userAccountInfo": {
                "userId": int(user_id),
                "personaId": int(user_id) * 1000 + 1,
                "displayName": "Player",
                "permissions": 0,
                "禁signOnType": 0,
                "country": "US",
                "locale": "en-US",
                "utQuestion": {
                    "assets": [],
                    "validActions": []
                }
            },
            "phishingToken": session_token,
            "sessionToken": session_token,
            "serverTime": int(time.time() * 1000)
        })

    async def handle_claim(self, request):
        """GET /fut/claim - Initial claim / setup."""
        session = self._get_session(request)
        if not session:
            return self._make_response({"error": "No session"}, 401)

        user_id = session["user_id"]
        club = await self.db.get_or_create_club(user_id)

        return self._make_response({
            "credits": club.get("credits", 10000),
            "tokens": 0,
            "rounds": 0,
            "unopenedPacks": 0,
            "contracts": 0,
            "vc": 0,
            "freeCoins": 0,
            "freeFIFAPoints": 0
        })

    async def handle_account_info(self, request):
        """GET /fut/user/accountinfo - Account information."""
        session = self._get_session(request)
        if not session:
            return self._make_response({"error": "No session"}, 401)

        user_id = session["user_id"]
        club = await self.db.get_or_create_club(user_id)

        return self._make_response({
            "userAccountInfo": {
                "userId": user_id,
                "personaId": user_id * 1000 + 1,
                "displayName": "Player",
                "permissions": 0,
                "clubList": [{
                    "clubName": club.get("name", "My Club"),
                    "clubAbbr": club.get("abbreviation", "CLB"),
                    "yearFounded": club.get("year_founded", 2015),
                    "regionId": 1,
                    "platform": "PC",
                    "credits": club.get("credits", 10000),
                    "contractBonus": 0,
                    "relegation": 0,
                    "division": 10,
                    "leagueId": 1,
                    "divisionMatchesPlayed": 0,
                    "divisionMatchesRemaining": 10,
                    "leagueMatchesPlayed": 0,
                    "leagueMatchesRemaining": 0,
                    "formations": [],
                    "kits": [],
                    "stadium": {},
                    "badges": [],
                    "leaderboardName": "Player",
                    "clubId": club.get("id", 1)
                }],
                "personaList": [{
                    "personaId": user_id * 1000 + 1,
                    "displayName": "Player",
                    "avatar": 0,
                    "roles": 0
                }]
            },
            "section": "FUT",
            "currency": "USD"
        })

    async def handle_item_info(self, request):
        """GET /fut/iteminfo - Player/item details."""
        item_id = request.query.get("itemId", "0")
        return self._make_response({
            "itemInfo": {
                "itemId": int(item_id),
                "definition": {},
                "team": {},
                "nation": {},
                "league": {}
            }
        })

    async def handle_player_catalog(self, request):
        """GET /fut/playercatalog - Available players."""
        players = await self.db.get_players(
            limit=int(request.query.get("limit", "50")),
            offset=int(request.query.get("offset", "0"))
        )

        return self._make_response({
            "players": players,
            "totalPlayers": len(players),
            "page": int(request.query.get("offset", "0")) // 50
        })

    async def handle_get_squad(self, request):
        """GET /fut/squad - Get active squad."""
        session = self._get_session(request)
        if not session:
            return self._make_response({"error": "No session"}, 401)

        user_id = session["user_id"]
        squad = await self.db.get_active_squad(user_id)

        if not squad:
            return self._make_response({
                "squad": {
                    "id": 0,
                    "name": "Active Squad",
                    "formation": "4-4-2",
                    "players": [],
                    "chemistry": 0,
                    "manager": {}
                }
            })

        return self._make_response({"squad": squad})

    async def handle_save_squad(self, request):
        """POST /fut/squad - Save/update a squad."""
        session = self._get_session(request)
        if not session:
            return self._make_response({"error": "No session"}, 401)

        user_id = session["user_id"]
        data = await request.json()

        squad = await self.db.save_squad(
            user_id=user_id,
            name=data.get("name", "Active Squad"),
            formation=data.get("formation", "4-4-2"),
            players=data.get("players", [])
        )

        return self._make_response({"squad": squad, "success": True})

    async def handle_club(self, request):
        """GET /fut/club - Club information."""
        session = self._get_session(request)
        if not session:
            return self._make_response({"error": "No session"}, 401)

        user_id = session["user_id"]
        club = await self.db.get_or_create_club(user_id)
        items = await self.db.get_user_items(user_id)

        return self._make_response({
            "club": club,
            "items": items,
            "totalItems": len(items)
        })

    async def handle_get_packs(self, request):
        """GET /fut/store/packs - Available packs."""
        packs = [
            {"id": 1, "name": "Bronze Pack", "price": 400, "currency": "coins",
             "contents": {"players": 3, "consumables": 3, "clubItems": 1}},
            {"id": 2, "name": "Silver Pack", "price": 1500, "currency": "coins",
             "contents": {"players": 3, "consumables": 3, "clubItems": 1}},
            {"id": 3, "name": "Gold Pack", "price": 7500, "currency": "coins",
             "contents": {"players": 3, "consumables": 3, "clubItems": 1}},
            {"id": 4, "name": "Premium Gold Pack", "price": 7500, "currency": "coins",
             "contents": {"players": 5, "consumables": 4, "clubItems": 2}},
            {"id": 5, "name": "Jumbo Premium Gold Pack", "price": 15000, "currency": "coins",
             "contents": {"players": 10, "consumables": 7, "clubItems": 3}},
            {"id": 6, "name": "Team of the Week Pack", "price": 100000, "currency": "coins",
             "contents": {"players": 12, "consumables": 0, "clubItems": 0}},
        ]

        return self._make_response({
            "packs": packs,
            "credits": (await self.db.get_or_create_club(
                self._get_session(request)["user_id"]
            )).get("credits", 10000) if self._get_session(request) else 0
        })

    async def handle_buy_pack(self, request):
        """POST /fut/pack/purchase - Buy a pack."""
        session = self._get_session(request)
        if not session:
            return self._make_response({"error": "No session"}, 401)

        user_id = session["user_id"]
        data = await request.json()
        pack_id = int(data.get("packId", 3))

        pack_prices = {1: 400, 2: 1500, 3: 7500, 4: 7500, 5: 15000, 6: 100000}
        price = pack_prices.get(pack_id, 7500)

        club = await self.db.get_or_create_club(user_id)
        if club.get("credits", 0) < price:
            return self._make_response({"error": "Insufficient credits"}, 400)

        await self.db.update_credits(user_id, -price)

        return self._make_response({
            "purchase": {
                "packId": pack_id,
                "credits": club.get("credits", 0) - price,
                "purchaseId": str(uuid.uuid4())
            },
            "success": True
        })

    async def handle_open_pack(self, request):
        """GET /fut/pack/open - Open a purchased pack."""
        session = self._get_session(request)
        if not session:
            return self._make_response({"error": "No session"}, 401)

        user_id = session["user_id"]
        items = await self.db.generate_pack_contents(user_id)

        return self._make_response({
            "itemList": items,
            "credits": (await self.db.get_or_create_club(user_id)).get("credits", 0),
            "packType": 3,
            "purchaseId": str(uuid.uuid4())
        })

    async def handle_transfer_market(self, request):
        """GET /fut/transfer/market - Transfer market listings."""
        items = await self.db.get_transfer_listings(
            limit=int(request.query.get("limit", "50"))
        )
        return self._make_response({
            "auctionInfo": items,
            "credits": 10000
        })

    async def handle_list_item(self, request):
        """POST /fut/transfer/item - List an item on the market."""
        session = self._get_session(request)
        if not session:
            return self._make_response({"error": "No session"}, 401)

        data = await request.json()
        listing = await self.db.create_transfer_listing(
            user_id=session["user_id"],
            item_id=int(data.get("itemId", 0)),
            start_price=int(data.get("startPrice", 0)),
            buy_now_price=int(data.get("buyNowPrice", 0)),
            duration=int(data.get("duration", 3600))
        )

        return self._make_response({
            "listing": listing,
            "success": True
        })

    async def handle_place_bid(self, request):
        """POST /fut/transfer/bid - Place a bid."""
        session = self._get_session(request)
        if not session:
            return self._make_response({"error": "No session"}, 401)

        data = await request.json()
        result = await self.db.place_bid(
            user_id=session["user_id"],
            listing_id=int(data.get("listingId", 0)),
            bid_amount=int(data.get("bid", 0))
        )

        return self._make_response(result)

    async def handle_competition(self, request):
        """GET /fut/competition - Competition/league info."""
        return self._make_response({
            "competitions": [
                {"id": 1, "name": "Ultimate Team", "type": "FUT"},
                {"id": 2, "name": "Division 1", "type": "SEASONS"},
                {"id": 3, "name": "FUT Draft", "type": "DRAFT"},
            ]
        })

    async def handle_challenge(self, request):
        """GET /fut/challenge - Squad building challenges."""
        return self._make_response({
            "challenges": [],
            "groups": []
        })
