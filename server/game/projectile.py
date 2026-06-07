"""Projectile (bullet) management."""

from dataclasses import dataclass


@dataclass
class Projectile:
    owner_id: str
    x: float
    y: float
    vx: float
    vy: float
    damage: int
    knockback: float
    lifetime: float  # remaining seconds
    radius: float = 4
    weapon: str = "projectile"
    prev_x: float | None = None
    prev_y: float | None = None

    def update(self, dt: float) -> None:
        """Move projectile and reduce lifetime."""
        self.prev_x = self.x
        self.prev_y = self.y
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.lifetime -= dt

    def is_expired(self) -> bool:
        return self.lifetime <= 0

    def to_dict(self) -> dict:
        return {
            "id": id(self),  # unique identifier
            "owner_id": self.owner_id,
            "x": self.x,
            "y": self.y,
            "vx": self.vx,
            "vy": self.vy,
            "damage": self.damage,
            "knockback": self.knockback,
            "weapon": self.weapon,
        }
