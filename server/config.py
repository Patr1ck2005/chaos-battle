"""Game configuration and constants."""

from dataclasses import dataclass, field

# ── Server ──────────────────────────────────────────
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8080
TICK_RATE = 20  # server ticks per second
TICK_DURATION = 1.0 / TICK_RATE  # seconds per tick

# ── Map ─────────────────────────────────────────────
MAP_WIDTH = 2000
MAP_HEIGHT = 1200
DEATH_Y = MAP_HEIGHT + 50  # fall below this = death

# ── Physics ─────────────────────────────────────────
GRAVITY = 1050.0  # px/s²
PLAYER_WIDTH = 30
PLAYER_HEIGHT = 50

# ── Player ──────────────────────────────────────────
MOVE_SPEED = 360.0  # px/s
HORIZONTAL_ACCELERATION = 3200.0  # px/s²
GROUND_FRICTION = 0.72
AIR_FRICTION = 0.94
MAX_FALL_SPEED = 980.0
JUMP_VELOCITY = -660.0  # px/s
MAX_HP = 100
DEFAULT_LIVES = 3
INVINCIBILITY_TIME = 2.0  # seconds after respawn
RESPAWN_TIME = 1.5  # seconds before appearing
KNOCKBACK_FACTOR = 1.0  # multiplier for knockback velocity
MAX_WEAPON_SLOTS = 4  # slot 0 = pistol, slots 1-3 = extra weapons
DROP_THROUGH_TIME = 0.3  # seconds to ignore platform when dropping through

# ── Abilities ───────────────────────────────────────
from enum import StrEnum

class Ability(StrEnum):
    NONE = "none"
    DOUBLE_JUMP = "double_jump"
    NO_RELOAD = "no_reload"


APPEARANCES = ("scout", "vanguard", "ghost", "medic", "engineer", "raider")
TEAMS = ("red", "blue", "green", "yellow")
DEFAULT_APPEARANCE = APPEARANCES[0]
DEFAULT_TEAM = TEAMS[0]

# ── Weapons ─────────────────────────────────────────
PISTOL = "pistol"
SNIPER = "sniper"
KATANA = "katana"
INITIAL_WEAPONS = (PISTOL, KATANA)

WEAPON_DEFS: dict[str, dict] = {
    PISTOL: {
        "name": "手枪",
        "damage": 15,
        "knockback": 150,    # target knockback (medium)
        "recoil": 80,        # self recoil (small)
        "fire_rate": 0.4,   # seconds between shots
        "mag_size": 10,
        "reload_time": 1.5,
        "bullet_speed": 800,
        "ammo": None,       # None = infinite reserve ammo
    },
    SNIPER: {
        "name": "狙击枪",
        "damage": 60,
        "knockback": 500,    # target knockback (very strong)
        "recoil": 250,       # self recoil (medium)
        "fire_rate": 1.2,
        "mag_size": 5,
        "reload_time": 2.0,
        "bullet_speed": 1200,
        "ammo": 5,          # total ammo, after used up weapon is discarded
    },
}

# ── Pickups (Weapon Crates) ─────────────────────────
CRATE_SPAWN_INTERVAL_MIN = 10.0  # seconds
CRATE_SPAWN_INTERVAL_MAX = 15.0
MAX_CRATES_ON_MAP = 3
CRATE_WIDTH = 24
CRATE_HEIGHT = 24
WEAPON_DEFS[KATANA] = {
    "name": "Katana",
    "kind": "melee",
    "damage": 24,
    "knockback": 260,
    "recoil": 0,
    "fire_rate": 0.28,
    "mag_size": 1,
    "reload_time": 0.0,
    "bullet_speed": 0,
    "ammo": None,
    "melee_range": 66,
    "melee_height": 66,
    "special_damage": 32,
    "special_knockback": 340,
    "special_lift": -420,
    "special_target_lift": -680,
    "special_cooldown": 0.75,
    "special_range": 78,
    "special_height": 82,
}

CRATE_WEAPON_POOL = [SNIPER, KATANA]  # weapons that can appear in crates

# ── Projectiles ─────────────────────────────────────
PROJECTILE_RADIUS = 4
PROJECTILE_LIFETIME = 3.0  # seconds before auto-despawn

# ── Bot ─────────────────────────────────────────────
BOT_REACTION_TIME = 0.2  # seconds of "thinking" delay
BOT_SHOOT_RANGE = 500  # px
BOT_WANDER_INTERVAL = 2.0


@dataclass
class RoomSettings:
    max_players: int = 10
    bot_count: int = 0
    lives: int = DEFAULT_LIVES
    weapon_crates: bool = True


def validate_settings(settings: dict) -> RoomSettings:
    """Validate and create RoomSettings from client input."""
    s = RoomSettings()
    if "max_players" in settings:
        s.max_players = max(1, min(10, int(settings["max_players"])))
    if "bot_count" in settings:
        s.bot_count = max(0, min(9, int(settings["bot_count"])))
    if "lives" in settings:
        s.lives = max(1, int(settings["lives"]))
    if "weapon_crates" in settings:
        s.weapon_crates = bool(settings["weapon_crates"])
    return s


def validate_appearance(appearance: str | None) -> str:
    """Return a known appearance id."""
    return appearance if appearance in APPEARANCES else DEFAULT_APPEARANCE


def validate_team(team: str | None) -> str:
    """Return a known team id."""
    return team if team in TEAMS else DEFAULT_TEAM


def validate_initial_weapon(weapon: str | None) -> str:
    """Return a known starting weapon id."""
    return weapon if weapon in INITIAL_WEAPONS else PISTOL
