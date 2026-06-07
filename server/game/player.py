"""Player entity and state management."""

from enum import Enum
from server.config import (
    MAX_HP,
    MOVE_SPEED,
    JUMP_VELOCITY,
    PLAYER_WIDTH,
    PLAYER_HEIGHT,
    INVINCIBILITY_TIME,
    RESPAWN_TIME,
    KNOCKBACK_FACTOR,
    PISTOL,
    MAX_WEAPON_SLOTS,
    Ability,
)
from server.game.weapon import WeaponDef, WeaponState


class PlayerState(Enum):
    ALIVE = "alive"
    DEAD = "dead"
    RESPWAWNING = "respawning"


class Player:
    def __init__(
        self,
        player_id: str,
        name: str,
        x: float,
        y: float,
        lives: int = 3,
        is_bot: bool = False,
        appearance: str = "scout",
        team: str = "red",
        initial_weapon: str = PISTOL,
    ):
        self.id = player_id
        self.name = name
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.hp = MAX_HP
        self.lives = lives
        self.state = PlayerState.ALIVE
        self.on_ground = False
        self.facing_right = True
        self.is_bot = is_bot
        self.appearance = appearance
        self.team = team
        self.initial_weapon = initial_weapon

        # Weapon inventory: slot 0 = pistol (permanent), slots 1-3 = extra weapons
        self.weapons: list[WeaponState | None] = [None] * MAX_WEAPON_SLOTS
        self.weapons[0] = WeaponState(WeaponDef.from_name(self.initial_weapon))
        self.active_weapon_slot = 0

        # Special ability
        self.ability: Ability = Ability.NONE
        self.has_double_jumped: bool = False  # track if double jump used in current airtime
        self.has_left_ground_since_jump: bool = False
        self.air_jumps_used: int = 0
        self.jump_pressed_last_tick: bool = False
        self.special_pressed_last_tick: bool = False

        # Drop-through state (for one-way platforms)
        self.drop_through_platform: object | None = None  # reference to Platform
        self.drop_through_timer: float = 0.0

        # Timers
        self.respawn_timer = 0.0
        self.invincibility_timer = 0.0

        # Kill tracking
        self.kills = 0

    # ── Weapon Management ──────────────────────────────

    def get_active_weapon(self) -> WeaponState | None:
        """Get the currently selected weapon."""
        if 0 <= self.active_weapon_slot < len(self.weapons):
            return self.weapons[self.active_weapon_slot]
        return None

    def switch_weapon(self, slot: int) -> None:
        """Switch to weapon in given slot (0-3)."""
        if 0 <= slot < len(self.weapons) and self.weapons[slot] is not None:
            self.active_weapon_slot = slot

    def equip_weapon(self, weapon_name: str) -> bool:
        """Pick up a weapon from a crate. Places it in the first empty slot (1-3).
        If all slots are full, replaces the current special weapon slot.
        Returns True if weapon was equipped."""
        weapon = WeaponState(WeaponDef.from_name(weapon_name))

        # Find first empty slot (skip slot 0 which is pistol)
        for i in range(1, MAX_WEAPON_SLOTS):
            if self.weapons[i] is None:
                self.weapons[i] = weapon
                self.active_weapon_slot = i
                return True

        # All slots full — replace current slot if it's special (1-3)
        if self.active_weapon_slot >= 1:
            self.weapons[self.active_weapon_slot] = weapon
            return True

        # Current is pistol — replace slot 1
        self.weapons[1] = weapon
        self.active_weapon_slot = 1
        return True

    def fire_active(self) -> dict | None:
        """Try to fire the active weapon. Returns attack info dict or None."""
        weapon = self.get_active_weapon()
        if weapon is None:
            return None

        if not weapon.can_fire():
            # Auto-reload if mag empty
            if (
                weapon.current_mag <= 0
                and not weapon.is_reloading
            ):
                weapon.start_reload()
            return None

        no_consume = (
            self.ability == Ability.NO_RELOAD
            and weapon.weapon_def.key == PISTOL
        )
        weapon.fire(no_consume=no_consume)
        if weapon.weapon_def.kind == "melee":
            return {"kind": "melee", "weapon": weapon.weapon_def}
        return self._bullet_info(weapon.weapon_def)

    def use_active_special(self) -> dict | None:
        """Try to use the active weapon special attack."""
        weapon = self.get_active_weapon()
        if weapon is None or not weapon.use_special():
            return None
        return {"kind": "melee_special", "weapon": weapon.weapon_def}

    def reload_active(self) -> bool:
        """Reload the active weapon. Returns True if reloading started."""
        weapon = self.get_active_weapon()
        if weapon:
            was_reloading = weapon.is_reloading
            weapon.start_reload()
            return weapon.is_reloading and not was_reloading
        return False

    # ── Damage & Death ─────────────────────────────────

    def take_damage(self, damage: int, knockback_dx: float, knockback_dy: float) -> bool:
        """Apply damage and knockback. Returns True if player died."""
        if self.invincibility_timer > 0:
            return False

        self.hp -= damage
        self.vx += knockback_dx * KNOCKBACK_FACTOR
        self.vy += knockback_dy * KNOCKBACK_FACTOR

        if self.hp <= 0:
            self.hp = 0
            self.die()
            return True
        return False

    def die(self) -> None:
        """Handle player death."""
        self.lives -= 1
        self.state = PlayerState.DEAD
        self.vx = 0
        self.vy = 0
        # Drop all special weapons
        for i in range(1, MAX_WEAPON_SLOTS):
            self.weapons[i] = None
        self.active_weapon_slot = 0
        self.drop_through_platform = None
        self.has_double_jumped = False
        self.has_left_ground_since_jump = False
        self.air_jumps_used = 0
        self.jump_pressed_last_tick = False
        self.special_pressed_last_tick = False

        if self.lives > 0:
            self.respawn_timer = RESPAWN_TIME

    def start_respawn(self, x: float, y: float) -> None:
        """Respawn player at given position."""
        self.x = x
        self.y = y
        self.vx = 0
        self.vy = 0
        self.hp = MAX_HP
        self.state = PlayerState.ALIVE
        self.invincibility_timer = INVINCIBILITY_TIME
        self.has_double_jumped = False
        self.has_left_ground_since_jump = False
        self.air_jumps_used = 0
        self.jump_pressed_last_tick = False
        self.special_pressed_last_tick = False
        # Reset weapons
        self.weapons = [None] * MAX_WEAPON_SLOTS
        self.weapons[0] = WeaponState(WeaponDef.from_name(self.initial_weapon))
        self.active_weapon_slot = 0
        self.drop_through_platform = None
        self.drop_through_timer = 0.0

    # ── Timers ──────────────────────────────────────────

    def update_timers(self, dt: float) -> None:
        """Update cooldowns and state timers."""
        # Weapon timers
        for w in self.weapons:
            if w is not None:
                w.update(dt)
                # Discard empty special weapons (not pistol at slot 0)
                idx = self.weapons.index(w)
                if idx >= 1 and w.is_empty():
                    self.weapons[idx] = None
                    if self.active_weapon_slot == idx:
                        self.active_weapon_slot = 0

        # Drop-through timer
        if self.drop_through_timer > 0:
            self.drop_through_timer -= dt

        # Invincibility
        if self.invincibility_timer > 0:
            self.invincibility_timer -= dt

        # Respawn
        if self.state == PlayerState.DEAD and self.lives > 0:
            self.respawn_timer -= dt

    # ── State Checks ────────────────────────────────────

    def is_alive(self) -> bool:
        return self.state == PlayerState.ALIVE

    def is_dead(self) -> bool:
        return self.state == PlayerState.DEAD

    def needs_respawn(self) -> bool:
        """Check if player is dead but has lives and respawn timer elapsed."""
        return (
            self.state == PlayerState.DEAD
            and self.lives > 0
            and self.respawn_timer <= 0
        )

    def is_out(self) -> bool:
        """Player is out of the game entirely (no lives left)."""
        return self.state == PlayerState.DEAD and self.lives <= 0

    # ── Helpers ─────────────────────────────────────────

    def _bullet_info(self, wdef: WeaponDef) -> dict:
        """Create bullet spawn info from weapon definition."""
        dir_x = 1 if self.facing_right else -1
        return {
            "x": self.x + PLAYER_WIDTH / 2 + dir_x * (PLAYER_WIDTH / 2 + 5),
            "y": self.y + PLAYER_HEIGHT / 2 - 5,
            "vx": wdef.bullet_speed * dir_x,
            "vy": 0.0,
            "damage": wdef.damage,
            "knockback": wdef.knockback,
            "weapon": wdef.key,
        }

    def to_dict(self) -> dict:
        """Serialize player state for network transmission."""
        return {
            "id": self.id,
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "vx": self.vx,
            "vy": self.vy,
            "hp": self.hp,
            "max_hp": MAX_HP,
            "lives": self.lives,
            "state": self.state.value,
            "facing_right": self.facing_right,
            "on_ground": self.on_ground,
            "invincible": self.invincibility_timer > 0,
            "is_bot": self.is_bot,
            "appearance": self.appearance,
            "team": self.team,
            "initial_weapon": self.initial_weapon,
            "kills": self.kills,
            "weapons": [w.to_dict() if w else None for w in self.weapons],
            "active_weapon_slot": self.active_weapon_slot,
            "ability": self.ability.value,
        }
