"""Weapon definitions and weapon state management."""

from dataclasses import dataclass
from server.config import WEAPON_DEFS, TICK_DURATION


@dataclass
class WeaponDef:
    key: str
    name: str
    kind: str
    damage: int
    knockback: float
    recoil: float       # self-knockback when firing
    fire_rate: float    # seconds between shots
    mag_size: int
    reload_time: float  # seconds to reload
    bullet_speed: float
    ammo: int | None = None  # None = infinite reserve ammo
    melee_range: float = 0.0
    melee_height: float = 0.0
    special_damage: int = 0
    special_knockback: float = 0.0
    special_lift: float = 0.0
    special_target_lift: float = 0.0
    special_cooldown: float = 0.0
    special_range: float = 0.0
    special_height: float = 0.0

    @classmethod
    def from_name(cls, name: str) -> "WeaponDef":
        """Create WeaponDef from a weapon name key."""
        data = WEAPON_DEFS[name]
        return cls(
            key=name,
            name=data["name"],
            kind=data.get("kind", "ranged"),
            damage=data["damage"],
            knockback=data["knockback"],
            recoil=data.get("recoil", 100),
            fire_rate=data["fire_rate"],
            mag_size=data["mag_size"],
            reload_time=data["reload_time"],
            bullet_speed=data["bullet_speed"],
            ammo=data["ammo"],
            melee_range=data.get("melee_range", 0.0),
            melee_height=data.get("melee_height", 0.0),
            special_damage=data.get("special_damage", 0),
            special_knockback=data.get("special_knockback", 0.0),
            special_lift=data.get("special_lift", 0.0),
            special_target_lift=data.get("special_target_lift", 0.0),
            special_cooldown=data.get("special_cooldown", 0.0),
            special_range=data.get("special_range", 0.0),
            special_height=data.get("special_height", 0.0),
        )


class WeaponState:
    """Runtime state of a weapon held by a player."""

    def __init__(self, weapon_def: WeaponDef):
        self.weapon_def = weapon_def
        self.current_mag = weapon_def.mag_size
        self.reserve_ammo = weapon_def.ammo  # None = infinite
        self.total_ammo_capacity = (
            None if weapon_def.ammo is None else weapon_def.mag_size + weapon_def.ammo
        )
        self.cooldown_timer = 0.0  # time until next shot allowed
        self.special_cooldown_timer = 0.0
        self.reload_timer = 0.0  # time until reload complete
        self.is_reloading = False

    def update(self, dt: float) -> None:
        """Update timers by dt seconds."""
        if self.cooldown_timer > 0:
            self.cooldown_timer -= dt
        if self.special_cooldown_timer > 0:
            self.special_cooldown_timer -= dt
        if self.reload_timer > 0:
            self.reload_timer -= dt
            if self.reload_timer <= 0:
                self._finish_reload()

    def can_fire(self) -> bool:
        """Check if weapon can fire right now."""
        return (
            self.cooldown_timer <= 0
            and self.reload_timer <= 0
            and (self.weapon_def.kind == "melee" or self.current_mag > 0)
        )

    def can_special(self) -> bool:
        """Check if a weapon special attack can be used right now."""
        return (
            self.weapon_def.kind == "melee"
            and self.special_cooldown_timer <= 0
            and self.reload_timer <= 0
        )

    def fire(self, no_consume: bool = False) -> bool:
        """Attempt to fire. Returns True if successful.
        If no_consume is True, doesn't use ammo (for no_reload ability)."""
        if not self.can_fire():
            return False
        if not no_consume and self.weapon_def.kind != "melee":
            self.current_mag -= 1
        self.cooldown_timer = self.weapon_def.fire_rate
        # Auto-reload if mag empty
        if self.current_mag <= 0 and not no_consume and self.weapon_def.kind != "melee":
            self.start_reload()
        return True

    def use_special(self) -> bool:
        """Trigger this weapon's special attack cooldown."""
        if not self.can_special():
            return False
        self.cooldown_timer = max(self.cooldown_timer, self.weapon_def.fire_rate)
        self.special_cooldown_timer = self.weapon_def.special_cooldown
        return True

    def start_reload(self) -> None:
        """Begin reloading. No-op if reserve ammo is 0 or already reloading."""
        if self.is_reloading:
            return
        if self.reserve_ammo is not None and self.reserve_ammo <= 0:
            return
        if self.current_mag == self.weapon_def.mag_size:
            return  # already full
        self.is_reloading = True
        self.reload_timer = self.weapon_def.reload_time

    def _finish_reload(self) -> None:
        """Complete the reload."""
        self.is_reloading = False
        shots_needed = self.weapon_def.mag_size - self.current_mag
        if self.reserve_ammo is None:
            # Infinite ammo
            self.current_mag = self.weapon_def.mag_size
        else:
            # Limited ammo
            reload_amount = min(shots_needed, self.reserve_ammo)
            self.current_mag += reload_amount
            self.reserve_ammo -= reload_amount

    def is_empty(self) -> bool:
        """Check if weapon has no ammo left at all."""
        if self.reserve_ammo is None:
            return False  # infinite ammo
        return self.current_mag <= 0 and self.reserve_ammo <= 0

    def to_dict(self) -> dict:
        return {
            "key": self.weapon_def.key,
            "name": self.weapon_def.name,
            "kind": self.weapon_def.kind,
            "mag": self.current_mag,
            "mag_size": self.weapon_def.mag_size,
            "reserve": self.reserve_ammo,
            "total_ammo_capacity": self.total_ammo_capacity,
            "is_reloading": self.is_reloading,
            "cooldown": max(0.0, self.cooldown_timer),
            "special_cooldown": max(0.0, self.special_cooldown_timer),
        }
