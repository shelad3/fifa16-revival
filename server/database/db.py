"""
Database layer for FIFA 16 Revival Server.

Uses SQLite for persistence. Stores:
  - Users and personas
  - Clubs and credits
  - Player catalog
  - User items (packs, consumables)
  - Squads
  - Transfer market listings
"""

import asyncio
import json
import logging
import random
import time
import uuid
from pathlib import Path

import aiosqlite

log = logging.getLogger("database")


INITIAL_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    created_at REAL NOT NULL,
    last_login REAL
);

CREATE TABLE IF NOT EXISTS personas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    display_name TEXT NOT NULL,
    avatar INTEGER DEFAULT 0,
    roles INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS clubs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    name TEXT DEFAULT 'My Club',
    abbreviation TEXT DEFAULT 'CLB',
    year_founded INTEGER DEFAULT 2015,
    credits INTEGER DEFAULT 10000,
    fifa_points INTEGER DEFAULT 0,
    division INTEGER DEFAULT 10,
    league_id INTEGER DEFAULT 1,
    created_at REAL NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    definition_id INTEGER UNIQUE NOT NULL,
    first_name TEXT,
    last_name TEXT,
    common_name TEXT,
    rating INTEGER DEFAULT 75,
    position TEXT DEFAULT 'ST',
    nationality TEXT DEFAULT 'England',
    league TEXT DEFAULT 'Premier League',
    club TEXT DEFAULT 'Unknown',
    skill INTEGER DEFAULT 3,
    weak_foot INTEGER DEFAULT 3,
    work_rate TEXT DEFAULT 'Medium/Medium',
    pace INTEGER DEFAULT 75,
    shooting INTEGER DEFAULT 75,
    passing INTEGER DEFAULT 75,
    dribbling INTEGER DEFAULT 75,
    defending INTEGER DEFAULT 75,
    physical INTEGER DEFAULT 75,
    diving INTEGER DEFAULT 50,
    handling INTEGER DEFAULT 50,
    kicking INTEGER DEFAULT 50,
    reflexes INTEGER DEFAULT 50,
    speed INTEGER DEFAULT 50,
    positioning INTEGER DEFAULT 50,
    card_type TEXT DEFAULT 'gold'
);

CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT UNIQUE NOT NULL,
    user_id INTEGER NOT NULL,
    definition_id INTEGER NOT NULL,
    resource_id INTEGER DEFAULT 0,
    created_at REAL NOT NULL,
    contracts INTEGER DEFAULT 7,
    fitness INTEGER DEFAULT 99,
    chemistry INTEGER DEFAULT 0,
    is_tradeable INTEGER DEFAULT 1,
    unassigned INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS squads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    formation TEXT DEFAULT '4-4-2',
    is_active INTEGER DEFAULT 0,
    chemistry INTEGER DEFAULT 0,
    players_json TEXT DEFAULT '[]',
    created_at REAL NOT NULL,
    updated_at REAL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS transfer_listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_user_id INTEGER NOT NULL,
    item_id TEXT NOT NULL,
    definition_id INTEGER NOT NULL,
    start_price INTEGER NOT NULL,
    buy_now_price INTEGER NOT NULL,
    current_bid INTEGER DEFAULT 0,
    bid_user_id INTEGER,
    listed_at REAL NOT NULL,
    expires_at REAL NOT NULL,
    status TEXT DEFAULT 'active',
    FOREIGN KEY (seller_user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS match_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    home_user_id INTEGER NOT NULL,
    away_user_id INTEGER NOT NULL,
    home_score INTEGER,
    away_score INTEGER,
    played_at REAL NOT NULL,
    match_type TEXT DEFAULT 'friendly'
);

CREATE TABLE IF NOT EXISTS pack_openings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    pack_id INTEGER NOT NULL,
    opened_at REAL NOT NULL,
    items_json TEXT
);
"""

DEFAULT_PLAYERS = [
    {"definition_id": 1, "first_name": "Lionel", "last_name": "Messi", "common_name": "Messi",
     "rating": 94, "position": "RW", "nationality": "Argentina", "league": "La Liga",
     "club": "FC Barcelona", "skill": 4, "weak_foot": 4, "pace": 89, "shooting": 85,
     "passing": 86, "dribbling": 92, "defending": 32, "physical": 56},
    {"definition_id": 2, "first_name": "Cristiano", "last_name": "Ronaldo", "common_name": "Ronaldo",
     "rating": 93, "position": "LW", "nationality": "Portugal", "league": "La Liga",
     "club": "Real Madrid", "skill": 5, "weak_foot": 4, "pace": 90, "shooting": 92,
     "passing": 77, "dribbling": 90, "defending": 33, "physical": 78},
    {"definition_id": 3, "first_name": "Neymar", "last_name": "Jr", "common_name": "Neymar Jr",
     "rating": 88, "position": "LW", "nationality": "Brazil", "league": "Ligue 1",
     "club": "Paris Saint-Germain", "skill": 5, "weak_foot": 4, "pace": 90, "shooting": 77,
     "passing": 78, "dribbling": 91, "defending": 30, "physical": 58},
    {"definition_id": 4, "first_name": "Luis", "last_name": "Suarez", "common_name": "Suarez",
     "rating": 90, "position": "ST", "nationality": "Uruguay", "league": "La Liga",
     "club": "FC Barcelona", "skill": 4, "weak_foot": 4, "pace": 79, "shooting": 89,
     "passing": 78, "dribbling": 85, "defending": 45, "physical": 78},
    {"definition_id": 5, "first_name": "Manuel", "last_name": "Neuer", "common_name": "Neuer",
     "rating": 90, "position": "GK", "nationality": "Germany", "league": "Bundesliga",
     "club": "FC Bayern Munich", "skill": 1, "weak_foot": 5, "diving": 86, "handling": 84,
     "kicking": 78, "reflexes": 89, "speed": 60, "positioning": 85},
    {"definition_id": 6, "first_name": "Robert", "last_name": "Lewandowski", "common_name": "Lewandowski",
     "rating": 90, "position": "ST", "nationality": "Poland", "league": "Bundesliga",
     "club": "FC Bayern Munich", "skill": 4, "weak_foot": 4, "pace": 80, "shooting": 89,
     "passing": 71, "dribbling": 83, "defending": 32, "physical": 80},
    {"definition_id": 7, "first_name": "Eden", "last_name": "Hazard", "common_name": "Hazard",
     "rating": 89, "position": "LW", "nationality": "Belgium", "league": "Premier League",
     "club": "Chelsea", "skill": 4, "weak_foot": 4, "pace": 88, "shooting": 77,
     "passing": 82, "dribbling": 90, "defending": 35, "physical": 58},
    {"definition_id": 8, "first_name": "Alexis", "last_name": "Sanchez", "common_name": "Sanchez",
     "rating": 88, "position": "ST", "nationality": "Chile", "league": "Premier League",
     "club": "Arsenal", "skill": 4, "weak_foot": 3, "pace": 86, "shooting": 82,
     "passing": 79, "dribbling": 87, "defending": 42, "physical": 73},
    {"definition_id": 9, "first_name": "Zlatan", "last_name": "Ibrahimovic", "common_name": "Ibrahimovic",
     "rating": 89, "position": "ST", "nationality": "Sweden", "league": "Ligue 1",
     "club": "Paris Saint-Germain", "skill": 4, "weak_foot": 4, "pace": 74, "shooting": 88,
     "passing": 81, "dribbling": 84, "defending": 42, "physical": 80},
    {"definition_id": 10, "first_name": "Gareth", "last_name": "Bale", "common_name": "Bale",
     "rating": 87, "position": "RW", "nationality": "Wales", "league": "La Liga",
     "club": "Real Madrid", "skill": 3, "weak_foot": 3, "pace": 94, "shooting": 85,
     "passing": 75, "dribbling": 84, "defending": 35, "physical": 75},
    {"definition_id": 11, "first_name": "Christian", "last_name": "Pulisic", "common_name": "Pulisic",
     "rating": 78, "position": "LW", "nationality": "USA", "league": "Bundesliga",
     "club": "Borussia Dortmund", "skill": 3, "weak_foot": 3, "pace": 82, "shooting": 68,
     "passing": 72, "dribbling": 80, "defending": 35, "physical": 55},
    {"definition_id": 12, "first_name": "Dele", "last_name": "Alli", "common_name": "Alli",
     "rating": 82, "position": "CAM", "nationality": "England", "league": "Premier League",
     "club": "Tottenham Hotspur", "skill": 3, "weak_foot": 3, "pace": 76, "shooting": 76,
     "passing": 76, "dribbling": 78, "defending": 60, "physical": 72},
    {"definition_id": 13, "first_name": "Jurgen", "last_name": "Klopp", "common_name": "Klopp",
     "rating": 60, "position": "GK", "nationality": "Germany", "league": "Bundesliga",
     "club": "Free Agents", "skill": 1, "weak_foot": 2, "diving": 50, "handling": 48,
     "kicking": 45, "reflexes": 52, "speed": 30, "positioning": 50},
    {"definition_id": 14, "first_name": "Marcus", "last_name": "Rashford", "common_name": "Rashford",
     "rating": 83, "position": "LW", "nationality": "England", "league": "Premier League",
     "club": "Manchester United", "skill": 3, "weak_foot": 3, "pace": 91, "shooting": 76,
     "passing": 70, "dribbling": 82, "defending": 30, "physical": 65},
    {"definition_id": 15, "first_name": "Raheem", "last_name": "Sterling", "common_name": "Sterling",
     "rating": 84, "position": "LW", "nationality": "England", "league": "Premier League",
     "club": "Manchester City", "skill": 3, "weak_foot": 3, "pace": 88, "shooting": 73,
     "passing": 76, "dribbling": 84, "defending": 32, "physical": 58},
    {"definition_id": 16, "first_name": "Kevin", "last_name": "De Bruyne", "common_name": "De Bruyne",
     "rating": 89, "position": "CAM", "nationality": "Belgium", "league": "Premier League",
     "club": "Manchester City", "skill": 4, "weak_foot": 5, "pace": 76, "shooting": 80,
     "passing": 89, "dribbling": 85, "defending": 45, "physical": 70},
    {"definition_id": 17, "first_name": "Nemanja", "last_name": "Matic", "common_name": "Matic",
     "rating": 83, "position": "CDM", "nationality": "Serbia", "league": "Premier League",
     "club": "Manchester United", "skill": 2, "weak_foot": 3, "pace": 55, "shooting": 65,
     "passing": 75, "dribbling": 70, "defending": 82, "physical": 79},
    {"definition_id": 18, "first_name": "Jan", "last_name": "Oblak", "common_name": "Oblak",
     "rating": 86, "position": "GK", "nationality": "Slovenia", "league": "La Liga",
     "club": "Atletico Madrid", "skill": 1, "weak_foot": 3, "diving": 85, "handling": 82,
     "kicking": 70, "reflexes": 88, "speed": 55, "positioning": 84},
    {"definition_id": 19, "first_name": "Diego", "last_name": "Godin", "common_name": "Godin",
     "rating": 85, "position": "CB", "nationality": "Uruguay", "league": "La Liga",
     "club": "Atletico Madrid", "skill": 1, "weak_foot": 3, "pace": 58, "shooting": 45,
     "passing": 60, "dribbling": 50, "defending": 85, "physical": 80},
    {"definition_id": 20, "first_name": "Leon", "last_name": "Goretzka", "common_name": "Goretzka",
     "rating": 82, "position": "CM", "nationality": "Germany", "league": "Bundesliga",
     "club": "FC Bayern Munich", "skill": 3, "weak_foot": 3, "pace": 74, "shooting": 74,
     "passing": 76, "dribbling": 77, "defending": 70, "physical": 76},
    {"definition_id": 21, "first_name": "Callum", "last_name": "Wilson", "common_name": "Wilson",
     "rating": 76, "position": "ST", "nationality": "England", "league": "Premier League",
     "club": "Bournemouth", "skill": 2, "weak_foot": 2, "pace": 78, "shooting": 74,
     "passing": 60, "dribbling": 70, "defending": 30, "physical": 72},
    {"definition_id": 22, "first_name": "Andros", "last_name": "Townsend", "common_name": "Townsend",
     "rating": 75, "position": "RW", "nationality": "England", "league": "Premier League",
     "club": "Crystal Palace", "skill": 3, "weak_foot": 3, "pace": 78, "shooting": 68,
     "passing": 70, "dribbling": 74, "defending": 35, "physical": 55},
    {"definition_id": 23, "first_name": "Jonjo", "last_name": "Shelvey", "common_name": "Shelvey",
     "rating": 74, "position": "CM", "nationality": "England", "league": "Premier League",
     "club": "Newcastle United", "skill": 2, "weak_foot": 3, "pace": 50, "shooting": 70,
     "passing": 76, "dribbling": 65, "defending": 58, "physical": 65},
    {"definition_id": 24, "first_name": "Ahmed", "last_name": "Musa", "common_name": "Musa",
     "rating": 73, "position": "ST", "nationality": "Nigeria", "league": "Premier League",
     "club": "Leicester City", "skill": 3, "weak_foot": 2, "pace": 88, "shooting": 68,
     "passing": 58, "dribbling": 72, "defending": 28, "physical": 60},
    {"definition_id": 25, "first_name": "Sergio", "last_name": "Asenjo", "common_name": "Asenjo",
     "rating": 72, "position": "GK", "nationality": "Spain", "league": "La Liga",
     "club": "Villarreal", "skill": 1, "weak_foot": 2, "diving": 70, "handling": 68,
     "kicking": 55, "reflexes": 72, "speed": 40, "positioning": 68},
    {"definition_id": 26, "first_name": "Lewis", "last_name": "Dunk", "common_name": "Dunk",
     "rating": 71, "position": "CB", "nationality": "England", "league": "Premier League",
     "club": "Brighton", "skill": 1, "weak_foot": 2, "pace": 55, "shooting": 35,
     "passing": 55, "dribbling": 45, "defending": 72, "physical": 74},
    {"definition_id": 27, "first_name": "Joel", "last_name": "Matip", "common_name": "Matip",
     "rating": 80, "position": "CB", "nationality": "Cameroon", "league": "Premier League",
     "club": "Liverpool", "skill": 1, "weak_foot": 3, "pace": 68, "shooting": 40,
     "passing": 65, "dribbling": 52, "defending": 80, "physical": 75},
    {"definition_id": 28, "first_name": "Alex", "last_name": "Oxlade-Chamberlain", "common_name": "Oxlade-Chamberlain",
     "rating": 79, "position": "RM", "nationality": "England", "league": "Premier League",
     "club": "Liverpool", "skill": 3, "weak_foot": 3, "pace": 80, "shooting": 70,
     "passing": 74, "dribbling": 78, "defending": 45, "physical": 65},
    {"definition_id": 29, "first_name": "Kasper", "last_name": "Schmeichel", "common_name": "Schmeichel",
     "rating": 79, "position": "GK", "nationality": "Denmark", "league": "Premier League",
     "club": "Leicester City", "skill": 1, "weak_foot": 3, "diving": 78, "handling": 74,
     "kicking": 68, "reflexes": 80, "speed": 45, "positioning": 76},
    {"definition_id": 30, "first_name": "Ruben", "last_name": "Loftus-Cheek", "common_name": "Loftus-Cheek",
     "rating": 76, "position": "CM", "nationality": "England", "league": "Premier League",
     "club": "Chelsea", "skill": 3, "weak_foot": 3, "pace": 72, "shooting": 62,
     "passing": 70, "dribbling": 74, "defending": 55, "physical": 74},
]

PACK_POOL_RATINGS = {
    "bronze": (55, 64),
    "silver": (65, 74),
    "gold": (75, 100),
}


class Database:
    """Async SQLite database for the FIFA 16 revival server."""

    def __init__(self, config):
        self.config = config
        self.db_path = config["path"]
        self.conn: Optional[aiosqlite.Connection] = None

    async def initialize(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self.conn = await aiosqlite.connect(self.db_path)
        self.conn.row_factory = aiosqlite.Row

        await self.conn.executescript(INITIAL_SCHEMA)
        await self.conn.commit()

        count = await self._count_players()
        if count == 0:
            log.info("Seeding player catalog...")
            await self._seed_players()

        log.info("Database ready at %s", self.db_path)

    async def close(self):
        if self.conn:
            await self.conn.close()

    async def _count_players(self) -> int:
        async with self.conn.execute("SELECT COUNT(*) FROM players") as cur:
            row = await cur.fetchone()
            return row[0] if row else 0

    async def _seed_players(self):
        for p in DEFAULT_PLAYERS:
            await self.conn.execute(
                """INSERT OR IGNORE INTO players
                   (definition_id, first_name, last_name, common_name, rating, position,
                    nationality, league, club, skill, weak_foot, pace, shooting,
                    passing, dribbling, defending, physical, diving, handling,
                    kicking, reflexes, speed, positioning)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (p["definition_id"], p["first_name"], p["last_name"], p["common_name"],
                 p["rating"], p["position"], p["nationality"], p["league"], p["club"],
                 p.get("skill", 3), p.get("weak_foot", 3),
                 p.get("pace", 75), p.get("shooting", 75), p.get("passing", 75),
                 p.get("dribbling", 75), p.get("defending", 75), p.get("physical", 75),
                 p.get("diving", 50), p.get("handling", 50), p.get("kicking", 50),
                 p.get("reflexes", 50), p.get("speed", 50), p.get("positioning", 50))
            )
        await self.conn.commit()
        log.info("Seeded %d players", len(DEFAULT_PLAYERS))

    async def get_or_create_user(self, username: str) -> dict:
        async with self.conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ) as cur:
            row = await cur.fetchone()
            if row:
                await self.conn.execute(
                    "UPDATE users SET last_login = ? WHERE id = ?",
                    (time.time(), row["id"])
                )
                await self.conn.commit()
                return dict(row)

        now = time.time()
        cursor = await self.conn.execute(
            "INSERT INTO users (username, created_at, last_login) VALUES (?, ?, ?)",
            (username, now, now)
        )
        await self.conn.commit()
        return {"id": cursor.lastrowid, "username": username, "created_at": now}

    async def get_default_persona(self, user_id: int) -> dict:
        async with self.conn.execute(
            "SELECT * FROM personas WHERE user_id = ? ORDER BY id LIMIT 1", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            if row:
                return dict(row)

        cursor = await self.conn.execute(
            "INSERT INTO personas (user_id, display_name) VALUES (?, ?)",
            (user_id, f"Player_{user_id}")
        )
        await self.conn.commit()
        return {"id": cursor.lastrowid, "user_id": user_id, "display_name": f"Player_{user_id}"}

    async def get_or_create_club(self, user_id: int) -> dict:
        async with self.conn.execute(
            "SELECT * FROM clubs WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            if row:
                return dict(row)

        now = time.time()
        cursor = await self.conn.execute(
            "INSERT INTO clubs (user_id, created_at) VALUES (?, ?)", (user_id, now)
        )
        await self.conn.commit()
        return {"id": cursor.lastrowid, "user_id": user_id, "credits": 10000,
                "name": "My Club", "abbreviation": "CLB"}

    async def update_credits(self, user_id: int, amount: int):
        await self.conn.execute(
            "UPDATE clubs SET credits = credits + ? WHERE user_id = ?",
            (amount, user_id)
        )
        await self.conn.commit()

    async def get_players(self, limit=50, offset=0, min_rating=None, max_rating=None):
        query = "SELECT * FROM players"
        params = []
        conditions = []

        if min_rating is not None:
            conditions.append("rating >= ?")
            params.append(min_rating)
        if max_rating is not None:
            conditions.append("rating <= ?")
            params.append(max_rating)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY rating DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        async with self.conn.execute(query, params) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def get_player_by_definition(self, definition_id: int) -> Optional[dict]:
        async with self.conn.execute(
            "SELECT * FROM players WHERE definition_id = ?", (definition_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

    async def get_user_items(self, user_id: int) -> list:
        async with self.conn.execute(
            "SELECT i.*, p.first_name, p.last_name, p.common_name, p.rating, p.position, p.club, p.nationality "
            "FROM items i LEFT JOIN players p ON i.definition_id = p.definition_id "
            "WHERE i.user_id = ? ORDER BY i.created_at DESC",
            (user_id,)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def add_item(self, user_id: int, definition_id: int, unassigned=1) -> dict:
        item_id = str(uuid.uuid4())
        now = time.time()
        cursor = await self.conn.execute(
            "INSERT INTO items (item_id, user_id, definition_id, created_at, unassigned) "
            "VALUES (?, ?, ?, ?, ?)",
            (item_id, user_id, definition_id, now, unassigned)
        )
        await self.conn.commit()
        return {"id": cursor.lastrowid, "item_id": item_id, "definition_id": definition_id}

    async def generate_pack_contents(self, user_id: int) -> list:
        pack_type = random.choice(["bronze", "silver", "gold"])
        min_r, max_r = PACK_POOL_RATINGS[pack_type]

        async with self.conn.execute(
            "SELECT definition_id FROM players WHERE rating BETWEEN ? AND ? ORDER BY RANDOM() LIMIT 5",
            (min_r, max_r)
        ) as cur:
            rows = await cur.fetchall()

        if not rows:
            async with self.conn.execute(
                "SELECT definition_id FROM players ORDER BY RANDOM() LIMIT 5"
            ) as cur:
                rows = await cur.fetchall()

        items = []
        for row in rows:
            item = await self.add_item(user_id, row["definition_id"])
            player = await self.get_player_by_definition(row["definition_id"])
            item["player"] = player
            items.append(item)

        return items

    async def get_active_squad(self, user_id: int) -> Optional[dict]:
        async with self.conn.execute(
            "SELECT * FROM squads WHERE user_id = ? AND is_active = 1 LIMIT 1", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            if row:
                result = dict(row)
                result["players"] = json.loads(result.pop("players_json", "[]"))
                return result
        return None

    async def save_squad(self, user_id: int, name: str, formation: str, players: list) -> dict:
        now = time.time()
        players_json = json.dumps(players)

        await self.conn.execute(
            "UPDATE squads SET is_active = 0 WHERE user_id = ?", (user_id,)
        )

        cursor = await self.conn.execute(
            "INSERT INTO squads (user_id, name, formation, is_active, players_json, created_at, updated_at) "
            "VALUES (?, ?, ?, 1, ?, ?, ?)",
            (user_id, name, formation, players_json, now, now)
        )
        await self.conn.commit()

        return {"id": cursor.lastrowid, "name": name, "formation": formation,
                "players": players, "is_active": 1}

    async def get_transfer_listings(self, limit=50, offset=0) -> list:
        async with self.conn.execute(
            "SELECT t.*, p.first_name, p.last_name, p.common_name, p.rating, p.position, p.club "
            "FROM transfer_listings t LEFT JOIN players p ON t.definition_id = p.definition_id "
            "WHERE t.status = 'active' AND t.expires_at > ? "
            "ORDER BY t.listed_at DESC LIMIT ? OFFSET ?",
            (time.time(), limit, offset)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def create_transfer_listing(self, user_id: int, item_id: str,
                                       start_price: int, buy_now_price: int,
                                       duration: int) -> dict:
        item = await self.conn.execute(
            "SELECT * FROM items WHERE item_id = ? AND user_id = ?", (item_id, user_id)
        )
        row = await item.fetchone()
        if not row:
            return {"error": "Item not found"}

        now = time.time()
        cursor = await self.conn.execute(
            "INSERT INTO transfer_listings (seller_user_id, item_id, definition_id, "
            "start_price, buy_now_price, listed_at, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, item_id, row["definition_id"], start_price, buy_now_price,
             now, now + duration)
        )
        await self.conn.commit()

        return {"id": cursor.lastrowid, "item_id": item_id,
                "start_price": start_price, "buy_now_price": buy_now_price}

    async def place_bid(self, user_id: int, listing_id: int, bid_amount: int) -> dict:
        async with self.conn.execute(
            "SELECT * FROM transfer_listings WHERE id = ? AND status = 'active'",
            (listing_id,)
        ) as cur:
            listing = await cur.fetchone()

        if not listing:
            return {"error": "Listing not found or expired"}
        if bid_amount <= listing["current_bid"]:
            return {"error": "Bid too low"}
        if listing["seller_user_id"] == user_id:
            return {"error": "Cannot bid on your own listing"}

        if bid_amount >= listing["buy_now_price"]:
            await self.conn.execute(
                "UPDATE transfer_listings SET status = 'sold', current_bid = ?, "
                "bid_user_id = ? WHERE id = ?",
                (bid_amount, user_id, listing_id)
            )
            await self.conn.commit()
            return {"status": "sold", "price": bid_amount}

        await self.conn.execute(
            "UPDATE transfer_listings SET current_bid = ?, bid_user_id = ? WHERE id = ?",
            (bid_amount, user_id, listing_id)
        )
        await self.conn.commit()
        return {"status": "bid_placed", "bid": bid_amount}

    async def get_config(self) -> dict:
        return {}
