"""Room and lobby management."""

import uuid
import asyncio
from enum import StrEnum

from server.config import (
    Ability,
    APPEARANCES,
    TEAMS,
    RoomSettings,
    validate_appearance,
    validate_initial_weapon,
    validate_settings,
    validate_team,
)
from server.game.engine import GameEngine
from server.game.map import Map
from server.game.player import Player


class RoomState(StrEnum):
    WAITING = "waiting"
    COUNTDOWN = "countdown"
    PLAYING = "playing"
    FINISHED = "finished"


class Room:
    def __init__(self, name: str, host_id: str, host_name: str, settings: RoomSettings):
        self.id = uuid.uuid4().hex[:8]
        self.name = name
        self.host_id = host_id
        self.settings = settings
        self.state = RoomState.WAITING
        self.players: list[dict] = []
        self._bot_seq = 0
        self.add_player(host_id, host_name, is_host=True)
        for _ in range(self.settings.bot_count):
            self.add_bot()
        self.engine: GameEngine | None = None
        self.game_task: asyncio.Task | None = None

    def add_player(self, player_id: str, name: str, is_host: bool = False) -> bool:
        """Add a player to the room. Returns False if room is full."""
        if self.human_count >= self.settings.max_players:
            return False
        # Don't add duplicate
        if any(p["id"] == player_id for p in self.players):
            return True
        team = "red" if is_host else TEAMS[self.human_count % len(TEAMS)]
        self.players.append(
            self._make_member(
                player_id=player_id,
                name=name,
                is_host=is_host,
                is_bot=False,
                team=team,
                appearance=APPEARANCES[self.human_count % len(APPEARANCES)],
            )
        )
        return True

    def remove_player(self, player_id: str) -> None:
        """Remove a player from the room."""
        self.players = [
            p for p in self.players if p["id"] != player_id or p.get("is_bot", False)
        ]
        # Reassign host if host left
        humans = self.human_players
        if humans and not any(p["is_host"] for p in humans):
            humans[0]["is_host"] = True
            self.host_id = humans[0]["id"]

    def get_player_ids(self) -> list[str]:
        return [p["id"] for p in self.human_players]

    @property
    def human_players(self) -> list[dict]:
        return [p for p in self.players if not p.get("is_bot", False)]

    @property
    def human_count(self) -> int:
        return len(self.human_players)

    @property
    def bot_players(self) -> list[dict]:
        return [p for p in self.players if p.get("is_bot", False)]

    def can_start(self, player_id: str) -> bool:
        """Check if the requesting player can start the game."""
        return (
            player_id == self.host_id
            and self.state == RoomState.WAITING
            and len(self.players) >= 1
        )

    def start_game(self) -> GameEngine:
        """Initialize and start a game for this room."""
        self.state = RoomState.PLAYING
        game_map = Map.default_map()
        self.engine = GameEngine(game_map, self.settings)

        # Add all room members, including AI.
        for pdata in self.players:
            player = Player(
                player_id=pdata["id"],
                name=pdata["name"],
                x=0,
                y=0,
                lives=self.settings.lives,
                is_bot=pdata.get("is_bot", False),
                appearance=pdata.get("appearance", "scout"),
                team=pdata.get("team", "red"),
                initial_weapon=validate_initial_weapon(pdata.get("initial_weapon")),
            )
            try:
                player.ability = Ability(pdata.get("ability", "none"))
            except ValueError:
                player.ability = Ability.NONE
            self.engine.add_player(player)

        return self.engine

    def reset(self) -> None:
        """Reset room back to waiting state after game ends."""
        self.state = RoomState.WAITING
        self.engine = None
        self.game_task = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "host_id": self.host_id,
            "state": self.state.value,
            "players": self.players,
            "settings": {
                "max_players": self.settings.max_players,
                "bot_count": self.settings.bot_count,
                "lives": self.settings.lives,
                "weapon_crates": self.settings.weapon_crates,
            },
            "player_count": self.human_count,
            "member_count": len(self.players),
            "bot_count": len(self.bot_players),
            "max_players": self.settings.max_players,
        }

    def set_player_loadout(
        self,
        player_id: str,
        ability: str | None = None,
        appearance: str | None = None,
        team: str | None = None,
        initial_weapon: str | None = None,
    ) -> None:
        """Set selectable room attributes for a member."""
        for p in self.players:
            if p["id"] == player_id:
                if ability is not None:
                    try:
                        p["ability"] = Ability(ability).value
                    except ValueError:
                        p["ability"] = Ability.NONE.value
                if appearance is not None:
                    p["appearance"] = validate_appearance(appearance)
                if team is not None:
                    p["team"] = validate_team(team)
                if initial_weapon is not None:
                    p["initial_weapon"] = validate_initial_weapon(initial_weapon)
                break

    def add_bot(self) -> dict:
        """Add an AI member to the room."""
        bot_id = f"bot_{self.id}_{self._bot_seq}"
        self._bot_seq += 1
        bot_count = len(self.bot_players)
        bot = self._make_member(
            player_id=bot_id,
            name=f"AI {bot_count + 1}",
            is_host=False,
            is_bot=True,
            team=TEAMS[self._bot_seq % len(TEAMS)],
            appearance=APPEARANCES[(bot_count + 1) % len(APPEARANCES)],
        )
        self.players.append(bot)
        self.settings.bot_count = len(self.bot_players)
        return bot

    def remove_bot(self, bot_id: str) -> bool:
        """Remove an AI member from the room."""
        before = len(self.players)
        self.players = [
            p for p in self.players if not (p["id"] == bot_id and p.get("is_bot", False))
        ]
        removed = len(self.players) != before
        if removed:
            self.settings.bot_count = len(self.bot_players)
        return removed

    def sync_bot_count(self) -> None:
        """Match bot members to settings.bot_count after settings updates."""
        target = self.settings.bot_count
        while len(self.bot_players) < target:
            self.add_bot()
        while len(self.bot_players) > target:
            self.remove_bot(self.bot_players[-1]["id"])

    def _make_member(
        self,
        player_id: str,
        name: str,
        is_host: bool,
        is_bot: bool,
        team: str,
        appearance: str,
    ) -> dict:
        return {
            "id": player_id,
            "name": name,
            "is_host": is_host,
            "is_bot": is_bot,
            "ability": Ability.NONE.value,
            "appearance": validate_appearance(appearance),
            "team": validate_team(team),
            "initial_weapon": "pistol",
        }


class LobbyManager:
    def __init__(self):
        self.rooms: dict[str, Room] = {}
        # Track which room each connected client is in
        self.client_rooms: dict[str, str] = {}  # client_id → room_id

    def create_room(
        self, host_id: str, host_name: str, name: str, settings: dict | None = None
    ) -> Room:
        """Create a new room."""
        room_settings = validate_settings(settings or {})
        room = Room(name=name, host_id=host_id, host_name=host_name, settings=room_settings)
        self.rooms[room.id] = room
        self.client_rooms[host_id] = room.id
        return room

    def join_room(self, room_id: str, player_id: str, name: str) -> tuple[Room | None, str]:
        """Join an existing room. Returns (room, error_message)."""
        room = self.rooms.get(room_id)
        if not room:
            return None, "房间不存在"
        if room.state != RoomState.WAITING:
            return None, "游戏已开始，无法加入"
        if not room.add_player(player_id, name):
            return None, "房间已满"
        self.client_rooms[player_id] = room_id
        return room, ""

    def leave_room(self, player_id: str) -> Room | None:
        """Leave current room. Returns the room if it still exists."""
        room_id = self.client_rooms.pop(player_id, None)
        if not room_id:
            return None
        room = self.rooms.get(room_id)
        if room:
            room.remove_player(player_id)
            # Clean up empty rooms
            if not room.human_players:
                self._cleanup_room(room_id)
                return None
        return room

    def get_client_room(self, client_id: str) -> Room | None:
        """Get the room a client is currently in."""
        room_id = self.client_rooms.get(client_id)
        if room_id:
            return self.rooms.get(room_id)
        return None

    def get_lobby_state(self) -> list[dict]:
        """Get list of joinable rooms."""
        return [
            r.to_dict()
            for r in self.rooms.values()
            if r.state == RoomState.WAITING
        ]

    def _cleanup_room(self, room_id: str) -> None:
        """Remove a room and its game task."""
        room = self.rooms.pop(room_id, None)
        if room and room.game_task:
            room.game_task.cancel()
