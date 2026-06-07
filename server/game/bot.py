"""Bot AI controller — state machine with platform awareness.

Uses edge detection to avoid walking off platforms.
Navigates between platforms to chase enemies.
"""

import random
from server.config import BOT_SHOOT_RANGE, PLAYER_WIDTH, PLAYER_HEIGHT


class BotState:
    IDLE = "idle"
    SEEK_ENEMY = "seek_enemy"
    ATTACK = "attack"
    FLEE = "flee"


class BotController:
    """State machine AI for bot players with platform awareness."""

    def __init__(self):
        self.state = BotState.SEEK_ENEMY
        self.wander_dir = random.choice([-1, 1])
        self.wander_timer = 0.0
        self.stuck_timer = 0.0
        self.prev_x = 0.0

    def think(self, player: "Player", engine: "GameEngine") -> dict:
        """Generate input keys for a bot player."""
        keys = {
            "left": False,
            "right": False,
            "up": False,
            "attack": False,
            "special": False,
            "reload": False,
        }

        # Detect if stuck (not moving horizontally)
        if abs(player.x - self.prev_x) < 2 and abs(player.vx) < 10:
            self.stuck_timer += 0.05
        else:
            self.stuck_timer = 0.0
        self.prev_x = player.x

        # Find nearest enemy
        nearest = self._find_nearest_enemy(player, engine)

        if nearest:
            self.state = BotState.SEEK_ENEMY
            dx = nearest.x - player.x
            dy = nearest.y - player.y
            dist = abs(dx)

            # Determine movement direction toward enemy
            move_right = dx > 0

            # Edge safety: don't walk off platform
            safe_right = not self._would_fall(player, engine, 1)
            safe_left = not self._would_fall(player, engine, -1)

            # Face the enemy
            if move_right:
                if safe_right:
                    keys["right"] = True
                elif safe_left:
                    keys["left"] = True  # can't go right, go left instead
                player.facing_right = True
            else:
                if safe_left:
                    keys["left"] = True
                elif safe_right:
                    keys["right"] = True
                player.facing_right = False

            # If stuck, try jumping
            if self.stuck_timer > 1.0:
                keys["up"] = True
                self.stuck_timer = 0

            # Jump if enemy is above
            if dy < -50 and player.on_ground:
                keys["up"] = True

            # Jump if walking toward a wall/edge and need to reach a higher platform
            if not player.on_ground and abs(player.vy) < 5:
                # Falling without being on ground — try to move toward nearest platform
                pass

            # Attack if in range and roughly same level
            abs_dy = abs(dy)
            if dist < BOT_SHOOT_RANGE and abs_dy < 100:
                keys["attack"] = True

            # Reload if mag is low
            active = player.get_active_weapon()
            if active and active.current_mag <= 2:
                keys["reload"] = True

        else:
            # No enemies — wander safely
            self._wander(player, engine, keys)

        return keys

    def _wander(self, player: "Player", engine: "GameEngine", keys: dict) -> None:
        """Safely wander around the platform."""
        # Choose direction
        if random.random() < 0.02 or self.stuck_timer > 1.5:
            self.wander_dir *= -1
            self.stuck_timer = 0

        # Check if we'd fall in the wander direction
        would_fall = self._would_fall(player, engine, self.wander_dir)

        if would_fall:
            # Turn around or jump
            if player.on_ground and random.random() < 0.5:
                keys["up"] = True  # try jumping to another platform
            self.wander_dir *= -1
            # Move in opposite direction
            if self.wander_dir > 0:
                keys["right"] = True
            else:
                keys["left"] = True
        else:
            if self.wander_dir > 0:
                keys["right"] = True
            else:
                keys["left"] = True

        # Random jumps while wandering
        if player.on_ground and random.random() < 0.015:
            keys["up"] = True

    def _would_fall(self, player: "Player", engine: "GameEngine", direction: int) -> bool:
        """Check if moving in `direction` (1=right, -1=left) would cause the bot
        to walk off the edge of a platform. Returns True if there's no platform below
        within a safe distance.
        """
        platforms = engine.map.platforms

        # Check a point slightly ahead and below the player
        check_x = player.x + direction * 40  # look ahead
        check_y_bottom = player.y + PLAYER_HEIGHT + 10  # just below feet

        # Check if there's any platform under the check point
        for plat in platforms:
            if (
                plat.left < check_x + PLAYER_WIDTH / 2
                and plat.right > check_x - PLAYER_WIDTH / 2
                and plat.top >= player.y + PLAYER_HEIGHT - 5
                and plat.top <= check_y_bottom + 30
            ):
                return False  # platform found, safe to walk

        # Also check directly below current position (might be mid-air)
        for plat in platforms:
            if (
                plat.left < check_x + PLAYER_WIDTH / 2
                and plat.right > check_x - PLAYER_WIDTH / 2
                and abs(plat.top - (player.y + PLAYER_HEIGHT)) < 15
            ):
                return False  # standing on this platform, but edge ahead

        return True  # would fall!

    def _find_nearest_enemy(
        self, bot: "Player", engine: "GameEngine"
    ) -> "Player | None":
        """Find the nearest alive enemy player."""
        best = None
        best_dist = float("inf")
        bot_x, bot_y = bot.x, bot.y

        for player in engine.players.values():
            if player.id == bot.id or not player.is_alive():
                continue
            if player.team == bot.team:
                continue
            dist = ((player.x - bot_x) ** 2 + (player.y - bot_y) ** 2) ** 0.5
            if dist < best_dist:
                best_dist = dist
                best = player

        return best
