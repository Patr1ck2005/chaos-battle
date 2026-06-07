"""Map and platform definitions."""

from dataclasses import dataclass
import random

from server.config import MAP_WIDTH, MAP_HEIGHT


@dataclass
class Platform:
    x: float
    y: float
    width: float
    height: float

    @property
    def left(self) -> float:
        return self.x

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def top(self) -> float:
        return self.y

    @property
    def bottom(self) -> float:
        return self.y + self.height

    def to_dict(self) -> dict:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }


class Map:
    def __init__(self, platforms: list[Platform]):
        self.platforms = platforms

    def get_spawn_points(self, count: int = 1) -> list[tuple[float, float]]:
        """Generate random spawn points above platforms.
        Returns list of (x, y) positions in the sky above random platforms.
        """
        spawns = []
        for _ in range(count):
            plat = random.choice(self.platforms)
            # Spawn somewhere above the platform, within its horizontal bounds
            spawn_x = plat.x + random.uniform(50, plat.width - 50)
            spawn_y = plat.y - random.uniform(100, 200)
            spawns.append((spawn_x, spawn_y))
        return spawns

    def to_dict(self) -> dict:
        return {
            "width": MAP_WIDTH,
            "height": MAP_HEIGHT,
            "platforms": [p.to_dict() for p in self.platforms],
        }

    @staticmethod
    def default_map() -> "Map":
        """Create the default map with several floating platforms.
        Platform vertical spacing is ~150px — jumpable with one jump (max ~213px)."""
        platforms = [
            # Bottom-most platforms (just above death zone)
            Platform(0, MAP_HEIGHT - 60, 380, 20),
            Platform(750, MAP_HEIGHT - 60, 450, 20),
            Platform(1550, MAP_HEIGHT - 60, 400, 20),
            # Level 1: y ~ 990 (gap ~150 from bottom ~1140)
            Platform(80, 990, 400, 20),
            Platform(850, 970, 350, 20),
            Platform(1500, 990, 400, 20),
            # Level 2: y ~ 840
            Platform(300, 840, 300, 20),
            Platform(1000, 820, 350, 20),
            Platform(1550, 840, 300, 20),
            # Level 3: y ~ 690
            Platform(100, 690, 280, 20),
            Platform(700, 670, 300, 20),
            Platform(1300, 690, 250, 20),
            # Level 4: y ~ 540
            Platform(400, 540, 220, 20),
            Platform(950, 520, 250, 20),
            Platform(1500, 540, 200, 20),
            # Level 5: y ~ 390
            Platform(200, 390, 200, 20),
            Platform(800, 370, 220, 20),
            Platform(1400, 390, 200, 20),
            # Top: y ~ 240
            Platform(500, 240, 200, 20),
            Platform(1000, 220, 220, 20),
        ]
        return Map(platforms)
