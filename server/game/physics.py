"""Physics simulation: gravity, one-way platform collision, ground detection."""

from server.config import (
    GRAVITY,
    TICK_DURATION,
    PLAYER_WIDTH,
    PLAYER_HEIGHT,
    DEATH_Y,
    MAP_WIDTH,
    MAX_FALL_SPEED,
)
from server.game.map import Map, Platform


def apply_physics(player: "Player") -> None:
    """Apply gravity and integrate velocity into position for one tick."""
    # Apply gravity
    player.vy += GRAVITY * TICK_DURATION
    if player.vy > MAX_FALL_SPEED:
        player.vy = MAX_FALL_SPEED

    # Integrate velocity
    player.x += player.vx * TICK_DURATION
    player.y += player.vy * TICK_DURATION

    # Keep players inside the horizontal arena. Falling below the map still kills.
    if player.x < 0:
        player.x = 0
        player.vx = max(0, player.vx * -0.2)
    elif player.x + PLAYER_WIDTH > MAP_WIDTH:
        player.x = MAP_WIDTH - PLAYER_WIDTH
        player.vx = min(0, player.vx * -0.2)


def check_platform_collision(player: "Player", platforms: list[Platform]) -> None:
    """Check and resolve one-way platform collisions.

    Platforms are ONE-WAY:
    - Player can jump up through platforms from below
    - Player lands on top of platforms when falling down
    - Player can press DOWN to drop through the platform they're standing on
    - Only the top surface is solid; sides and bottom are pass-through
    """
    player_left = player.x
    player_right = player.x + PLAYER_WIDTH
    player_top = player.y
    player_bottom = player.y + PLAYER_HEIGHT

    player.on_ground = False

    for plat in platforms:
        # Skip if player is dropping through this platform
        if player.drop_through_platform is plat:
            continue

        # Only check collision if player overlaps platform
        if not (
            player_right > plat.left
            and player_left < plat.right
            and player_bottom > plat.top
            and player_top < plat.bottom
        ):
            continue

        # Calculate overlap amounts
        overlap_top = player_bottom - plat.top    # how much player is below plat top
        overlap_bottom = plat.bottom - player_top  # how much player is above plat bottom
        overlap_left = player_right - plat.left
        overlap_right = plat.right - player_left

        # Check where the player was before movement
        prev_bottom = player_bottom - player.vy * TICK_DURATION
        was_above = prev_bottom <= plat.top + 2  # player's feet were at or above platform top

        # Landing on top (one-way): only if player was above and is moving down
        if was_above and overlap_top > 0 and overlap_top < PLAYER_HEIGHT + 10:
            # Snap player to top of platform
            player.y = plat.top - PLAYER_HEIGHT
            player.vy = 0
            player.on_ground = True
            player.drop_through_platform = None  # clear drop-through when landing
            return  # only collide with one platform per tick

        # Sides and bottoms are deliberately pass-through for floaty arena play.


def check_drop_through(player: "Player", platforms: list[Platform]) -> None:
    """If player presses down while on ground, allow dropping through
    the platform they're standing on."""
    if not player.on_ground:
        return

    # Find which platform the player is standing on
    player_left = player.x
    player_right = player.x + PLAYER_WIDTH
    player_bottom = player.y + PLAYER_HEIGHT

    for plat in platforms:
        if (
            player_right > plat.left
            and player_left < plat.right
            and abs(player_bottom - plat.top) < 5
        ):
            # Player is standing on this platform — initiate drop-through
            player.drop_through_platform = plat
            player.vy = 50  # small downward push to start falling
            player.on_ground = False
            player.drop_through_timer = 0.3  # seconds to ignore this platform
            break


def update_drop_through(player: "Player", dt: float) -> None:
    """Update drop-through timer. Clear it when expired or player is no longer
    near the platform."""
    if player.drop_through_platform is None:
        return

    if player.drop_through_timer > 0:
        player.drop_through_timer -= dt
        return

    # Timer expired — check if player is still overlapping the platform
    plat = player.drop_through_platform
    player_bottom = player.y + PLAYER_HEIGHT
    player_top = player.y
    player_left = player.x
    player_right = player.x + PLAYER_WIDTH

    if not (
        player_right > plat.left
        and player_left < plat.right
        and player_top < plat.bottom
        and player_bottom > plat.top
    ):
        # Player has moved past the platform, clear drop-through
        player.drop_through_platform = None
    # If still overlapping, keep the drop-through active a bit longer
    # (handled in next tick's collision check)


def is_on_ground(player: "Player", platforms: list[Platform]) -> bool:
    """Check if player is standing on a platform surface."""
    player_left = player.x
    player_right = player.x + PLAYER_WIDTH
    player_bottom = player.y + PLAYER_HEIGHT

    for plat in platforms:
        if player.drop_through_platform is plat:
            continue
        if (
            player_right > plat.left
            and player_left < plat.right
            and abs(player_bottom - plat.top) < 4
            and player.vy >= -1  # not moving up fast
        ):
            return True
    return False


def check_death_zone(player: "Player") -> bool:
    """Check if player has fallen below the map (no platforms below)."""
    return player.y > DEATH_Y
