"""Message protocol definitions and helpers."""

import json
from enum import StrEnum


class MessageType(StrEnum):
    # Client → Server
    JOIN_LOBBY = "join_lobby"
    CREATE_ROOM = "create_room"
    JOIN_ROOM = "join_room"
    LEAVE_ROOM = "leave_room"
    START_GAME = "start_game"
    PLAYER_INPUT = "input"
    UPDATE_SETTINGS = "update_settings"
    SET_ABILITY = "set_ability"
    SET_LOADOUT = "set_loadout"
    ADD_BOT = "add_bot"
    REMOVE_BOT = "remove_bot"
    # Server → Client
    LOBBY_STATE = "lobby_state"
    ROOM_UPDATE = "room_update"
    GAME_STATE = "game_state"
    GAME_START = "game_start"
    GAME_EVENTS = "game_events"
    GAME_OVER = "game_over"
    ERROR = "error"
    # Bidirectional
    PING = "ping"
    PONG = "pong"


def make_message(msg_type: str | MessageType, **kwargs) -> str:
    """Create a JSON message string."""
    msg = {"type": str(msg_type)}
    msg.update(kwargs)
    return json.dumps(msg, ensure_ascii=False)


def parse_message(raw: str) -> dict | None:
    """Parse a JSON message string. Returns None on parse error."""
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


def validate_message(msg: dict) -> bool:
    """Basic validation: message must have a 'type' field."""
    return isinstance(msg, dict) and "type" in msg
