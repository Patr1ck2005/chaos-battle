"""Weapon crate pickups."""

import random
from dataclasses import dataclass, field
from server.config import CRATE_WIDTH, CRATE_HEIGHT, CRATE_WEAPON_POOL


_pickup_counter = 0


def _next_id() -> str:
    global _pickup_counter
    _pickup_counter += 1
    return f"pickup_{_pickup_counter}"


@dataclass
class Pickup:
    x: float
    y: float
    weapon_name: str
    id: str = field(default_factory=_next_id)

    @property
    def width(self) -> float:
        return CRATE_WIDTH

    @property
    def height(self) -> float:
        return CRATE_HEIGHT

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }


def spawn_crate(platforms: list) -> Pickup | None:
    """Attempt to spawn a weapon crate on a random platform.
    Returns None if no suitable spot found.
    """
    if not platforms:
        return None

    plat = random.choice(platforms)
    # Place on top of platform
    crate_x = plat.x + random.uniform(20, plat.width - CRATE_WIDTH - 20)
    crate_y = plat.y - CRATE_HEIGHT - 2  # just above platform surface

    weapon_name = random.choice(CRATE_WEAPON_POOL)
    return Pickup(x=crate_x, y=crate_y, weapon_name=weapon_name)


def check_crate_pickup(
    player_x: float, player_y: float, player_w: float, player_h: float, crate: Pickup
) -> bool:
    """Check if a player's hitbox overlaps a crate."""
    return (
        player_x + player_w > crate.x
        and player_x < crate.x + crate.width
        and player_y + player_h > crate.y
        and player_y < crate.y + crate.height
    )
