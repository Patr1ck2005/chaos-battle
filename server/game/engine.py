"""Server-authoritative game engine. Runs the game loop at 20 ticks/sec."""

import random
import time
from collections import deque

from server.config import (
    TICK_DURATION,
    MOVE_SPEED,
    HORIZONTAL_ACCELERATION,
    GROUND_FRICTION,
    AIR_FRICTION,
    JUMP_VELOCITY,
    PLAYER_WIDTH,
    PLAYER_HEIGHT,
    PROJECTILE_LIFETIME,
    PROJECTILE_RADIUS,
    CRATE_SPAWN_INTERVAL_MIN,
    CRATE_SPAWN_INTERVAL_MAX,
    MAX_CRATES_ON_MAP,
    MAX_WEAPON_SLOTS,
    PISTOL,
    Ability,
)
from server.game.map import Map, Platform
from server.game.player import Player, PlayerState
from server.game.weapon import WeaponDef, WeaponState
from server.game.projectile import Projectile
from server.game.pickup import Pickup, spawn_crate, check_crate_pickup
from server.game.physics import apply_physics, check_platform_collision, check_death_zone


class GameEngine:
    def __init__(self, game_map: Map, settings: "RoomSettings"):
        self.map = game_map
        self.settings = settings
        self.players: dict[str, Player] = {}
        self.projectiles: list[Projectile] = []
        self.pickups: list[Pickup] = []
        self.tick_count = 0
        self.elapsed = 0.0
        self.crate_timer = random.uniform(
            CRATE_SPAWN_INTERVAL_MIN, CRATE_SPAWN_INTERVAL_MAX
        )
        self.events: list[dict] = []  # events generated this tick
        self.pending_events: list[dict] = []  # events generated between ticks
        self.in_tick = False
        self.game_over = False
        self.winner_id: str | None = None

    # ── Player Management ───────────────────────────────────

    def add_player(self, player: Player) -> None:
        """Add a player to the game at a spawn point."""
        spawns = self.map.get_spawn_points(1)
        if spawns:
            player.x, player.y = spawns[0]
        self.players[player.id] = player

    def remove_player(self, player_id: str) -> None:
        """Remove a player from the game."""
        if player_id in self.players:
            del self.players[player_id]

    # ── Input Processing ────────────────────────────────────

    def process_input(self, player_id: str, keys: dict) -> None:
        """Process input from a human player."""
        player = self.players.get(player_id)
        if not player or not player.is_alive():
            return

        # Horizontal movement
        accel = HORIZONTAL_ACCELERATION * TICK_DURATION
        if keys.get("left"):
            player.vx = max(-MOVE_SPEED, player.vx - accel)
            player.facing_right = False
        elif keys.get("right"):
            player.vx = min(MOVE_SPEED, player.vx + accel)
            player.facing_right = True
        else:
            # Apply friction/stop. Air friction is looser for that old Flash float.
            player.vx *= GROUND_FRICTION if player.on_ground else AIR_FRICTION
            if abs(player.vx) < 5:
                player.vx = 0

        jump_held = bool(keys.get("up"))
        jump_pressed = bool(keys.get("jump_pressed")) or (
            jump_held and not player.jump_pressed_last_tick
        )

        # Jump (normal or double jump). Use a press edge so holding jump cannot
        # consume both jumps, but a second tap in the air is always accepted.
        if jump_pressed:
            if player.on_ground:
                player.vy = JUMP_VELOCITY
                player.on_ground = False
                player.has_double_jumped = False
                player.has_left_ground_since_jump = False
                player.air_jumps_used = 0
            elif (player.ability == Ability.DOUBLE_JUMP
                  and player.air_jumps_used < 1):
                player.vy = JUMP_VELOCITY * 0.85  # slightly weaker second jump
                player.on_ground = False
                player.air_jumps_used += 1
                player.has_double_jumped = True
        player.jump_pressed_last_tick = jump_held

        # Drop through platform (press down while on ground)
        if keys.get("down") and player.on_ground:
            from server.game.physics import check_drop_through
            check_drop_through(player, self.map.platforms)

        # Attack (fires active weapon). The pressed edge keeps quick taps from
        # being lost between 20Hz server input packets.
        if keys.get("attack") or keys.get("attack_pressed"):
            attack_info = player.fire_active()
            if attack_info and attack_info.get("kind") == "melee":
                self._emit_event(
                    {
                        "type": "melee_swing",
                        "player_id": player.id,
                        "weapon": attack_info["weapon"].key,
                        "attack": "slash",
                    }
                )
                self._apply_melee_attack(player, attack_info["weapon"], special=False)
            elif attack_info:
                self._spawn_bullet(player, attack_info)
                weapon = player.get_active_weapon()
                self._emit_event(
                    {
                        "type": "shoot",
                        "player_id": player.id,
                        "weapon": weapon.weapon_def.key if weapon else "unknown",
                    }
                )
                # Apply recoil (self-knockback opposite to facing direction)
                if weapon:
                    recoil_force = weapon.weapon_def.recoil
                    dir_x = 1 if player.facing_right else -1
                    player.vx -= dir_x * recoil_force
                    if weapon.is_reloading:
                        self._emit_event(
                            {
                                "type": "reload",
                                "player_id": player.id,
                                "weapon": weapon.weapon_def.key,
                            }
                        )

        special_held = bool(keys.get("special"))
        special_pressed = bool(keys.get("special_pressed")) or (
            special_held and not player.special_pressed_last_tick
        )
        if special_pressed:
            special_info = player.use_active_special()
            if special_info and special_info.get("kind") == "melee_special":
                wdef = special_info["weapon"]
                player.vy = min(player.vy, wdef.special_lift)
                player.on_ground = False
                self._emit_event(
                    {
                        "type": "melee_swing",
                        "player_id": player.id,
                        "weapon": wdef.key,
                        "attack": "uppercut",
                    }
                )
                self._apply_melee_attack(player, wdef, special=True)
        player.special_pressed_last_tick = special_held

        # Reload
        if keys.get("reload"):
            if player.reload_active():
                weapon = player.get_active_weapon()
                self._emit_event(
                    {
                        "type": "reload",
                        "player_id": player.id,
                        "weapon": weapon.weapon_def.key if weapon else "unknown",
                    }
                )

        # Weapon switching (processed once per key press via "weapon_slot")
        slot = keys.get("weapon_slot")
        if slot is not None and 0 <= slot < MAX_WEAPON_SLOTS:
            player.switch_weapon(slot)

    # ── Bot Input ───────────────────────────────────────────

    def process_bot(self, player_id: str, bot_controller) -> None:
        """Let bot AI generate input for this player."""
        player = self.players.get(player_id)
        if not player or not player.is_alive() or not player.is_bot:
            return

        # Delegate to bot controller
        keys = bot_controller.think(player, self)
        self.process_input(player_id, keys)

    # ── Main Tick ───────────────────────────────────────────

    def tick(self, bot_controllers: dict[str, object] | None = None) -> list[dict]:
        """Advance game state by one tick. Returns list of events this tick."""
        self.tick_count += 1
        self.elapsed += TICK_DURATION
        self.events = self.pending_events
        self.pending_events = []
        self.in_tick = True

        bot_controllers = bot_controllers or {}

        # 1. Update all players
        for player in list(self.players.values()):
            # Always update timers (needed for respawn countdown)
            player.update_timers(TICK_DURATION)

            if player.is_alive():
                # Bot processing
                if player.is_bot and player.id in bot_controllers:
                    self.process_bot(player.id, bot_controllers[player.id])

                # Physics
                apply_physics(player)
                check_platform_collision(player, self.map.platforms)

                # Update drop-through state
                from server.game.physics import update_drop_through
                update_drop_through(player, TICK_DURATION)

                # Update ground state
                from server.game.physics import is_on_ground

                was_on_ground = player.on_ground
                player.on_ground = is_on_ground(player, self.map.platforms)

                # Reset double jump when landing
                if player.on_ground and not was_on_ground:
                    player.has_double_jumped = False
                    player.has_left_ground_since_jump = False
                    player.air_jumps_used = 0
                elif not player.on_ground:
                    player.has_left_ground_since_jump = True

                # Death zone check
                if check_death_zone(player):
                    self._kill_player(player, None)

            elif player.needs_respawn():
                # Respawn
                spawns = self.map.get_spawn_points(1)
                if spawns:
                    player.start_respawn(spawns[0][0], spawns[0][1])

        # 2. Update projectiles
        for proj in list(self.projectiles):
            proj.update(TICK_DURATION)
            if proj.is_expired():
                self.projectiles.remove(proj)
                continue

            owner = self.players.get(proj.owner_id)

            # Hit detection against alive players
            for player in self.players.values():
                if not player.is_alive():
                    continue
                if player.id == proj.owner_id:
                    continue  # can't hit self
                if owner and owner.team == player.team:
                    continue  # teammates cannot damage each other
                if player.invincibility_timer > 0:
                    continue

                # Circle vs AABB hit test
                if self._bullet_hits_player(proj, player):
                    died = player.take_damage(
                        proj.damage, proj.knockback * (1 if proj.vx > 0 else -1), -50
                    )
                    self._emit_event(
                        {
                            "type": "hit",
                            "attacker_id": proj.owner_id,
                            "victim_id": player.id,
                            "weapon": proj.weapon,
                            "hit_kind": "bullet",
                        }
                    )
                    self.projectiles.remove(proj)
                    if died:
                        killer = self.players.get(proj.owner_id)
                        self._kill_player(player, killer)
                    break

        # 3. Update pickups and crate spawning
        if self.settings.weapon_crates:
            self.crate_timer -= TICK_DURATION
            if self.crate_timer <= 0 and len(self.pickups) < MAX_CRATES_ON_MAP:
                crate = spawn_crate(self.map.platforms)
                if crate:
                    self.pickups.append(crate)
                self.crate_timer = random.uniform(
                    CRATE_SPAWN_INTERVAL_MIN, CRATE_SPAWN_INTERVAL_MAX
                )

        # 4. Check pickup collection
        for player in self.players.values():
            if not player.is_alive():
                continue
            for crate in list(self.pickups):
                if check_crate_pickup(
                    player.x, player.y, PLAYER_WIDTH, PLAYER_HEIGHT, crate
                ):
                    player.equip_weapon(crate.weapon_name)
                    self.pickups.remove(crate)
                    self._emit_event(
                        {
                            "type": "pickup",
                            "player_id": player.id,
                            "weapon": crate.weapon_name,
                        }
                    )

        # 5. Check game over
        self._check_game_over()

        self.in_tick = False
        return self.events

    # ── Internal Helpers ────────────────────────────────────

    def _spawn_bullet(self, player: Player, info: dict) -> None:
        """Create a projectile from bullet info."""
        proj = Projectile(
            owner_id=player.id,
            x=info["x"],
            y=info["y"],
            vx=info["vx"],
            vy=info["vy"],
            damage=info["damage"],
            knockback=info["knockback"],
            lifetime=PROJECTILE_LIFETIME,
            radius=PROJECTILE_RADIUS,
            weapon=info.get("weapon", "projectile"),
        )
        self.projectiles.append(proj)

    def _emit_event(self, event: dict) -> None:
        """Store an event whether it happened inside or between ticks."""
        if self.in_tick:
            self.events.append(event)
        else:
            self.pending_events.append(event)

    def _apply_melee_attack(
        self, attacker: Player, wdef: WeaponDef, special: bool = False
    ) -> None:
        """Apply a short forward melee hitbox for blade-style weapons."""
        direction = 1 if attacker.facing_right else -1
        attack_range = wdef.special_range if special else wdef.melee_range
        attack_height = wdef.special_height if special else wdef.melee_height
        hit_left = attacker.x + PLAYER_WIDTH if direction > 0 else attacker.x - attack_range
        hit_top = attacker.y + PLAYER_HEIGHT / 2 - attack_height / 2
        hit_right = hit_left + attack_range
        hit_bottom = hit_top + attack_height

        damage = wdef.special_damage if special else wdef.damage
        knockback = wdef.special_knockback if special else wdef.knockback
        knockback_y = wdef.special_target_lift if special else -130

        for target in self.players.values():
            if target.id == attacker.id or not target.is_alive():
                continue
            if target.team == attacker.team:
                continue
            if target.invincibility_timer > 0:
                continue

            target_left = target.x
            target_right = target.x + PLAYER_WIDTH
            target_top = target.y
            target_bottom = target.y + PLAYER_HEIGHT
            overlaps = (
                hit_right > target_left
                and hit_left < target_right
                and hit_bottom > target_top
                and hit_top < target_bottom
            )
            if not overlaps:
                continue

            died = target.take_damage(damage, knockback * direction, knockback_y)
            self._emit_event(
                {
                    "type": "hit",
                    "attacker_id": attacker.id,
                    "victim_id": target.id,
                    "weapon": wdef.key,
                    "hit_kind": "melee_special" if special else "melee",
                }
            )
            if died:
                self._kill_player(target, attacker)

    def _bullet_hits_player(self, proj: Projectile, player: Player) -> bool:
        """Swept bullet segment vs expanded player AABB.

        Server ticks are only 20Hz, while bullets are fast enough to cross a
        player-sized hitbox between two ticks. Treat the bullet as a line from
        its previous point to its current point so non-piercing bullets reliably
        disappear on impact.
        """
        x1 = proj.prev_x if proj.prev_x is not None else proj.x
        y1 = proj.prev_y if proj.prev_y is not None else proj.y
        x2 = proj.x
        y2 = proj.y
        left = player.x - proj.radius
        right = player.x + PLAYER_WIDTH + proj.radius
        top = player.y - proj.radius
        bottom = player.y + PLAYER_HEIGHT + proj.radius

        dx = x2 - x1
        dy = y2 - y1
        t_min = 0.0
        t_max = 1.0

        for start, delta, axis_min, axis_max in (
            (x1, dx, left, right),
            (y1, dy, top, bottom),
        ):
            if abs(delta) < 1e-9:
                if start < axis_min or start > axis_max:
                    return False
                continue
            inv_delta = 1.0 / delta
            t1 = (axis_min - start) * inv_delta
            t2 = (axis_max - start) * inv_delta
            if t1 > t2:
                t1, t2 = t2, t1
            t_min = max(t_min, t1)
            t_max = min(t_max, t2)
            if t_min > t_max:
                return False

        return True

    def _kill_player(self, victim: Player, killer: Player | None) -> None:
        """Handle a player death."""
        victim.die()
        if killer and killer.id != victim.id:
            killer.kills += 1
        self._emit_event(
            {
                "type": "kill",
                "victim_id": victim.id,
                "victim_name": victim.name,
                "killer_id": killer.id if killer else None,
                "killer_name": killer.name if killer else "环境",
            }
        )

    def _check_game_over(self) -> None:
        """Check if only one team (or fewer) remains with lives."""
        players_with_lives = [p for p in self.players.values() if not p.is_out()]
        teams_with_lives = {p.team for p in players_with_lives}
        if len(teams_with_lives) <= 1 and len(self.players) > 0:
            # Don't end game if the last player is just respawning
            actually_alive = [p for p in players_with_lives if p.is_alive()]
            if len(actually_alive) == 0 and len(teams_with_lives) == 1:
                return  # waiting for respawn
            self.game_over = True
            self.winner_id = players_with_lives[0].id if players_with_lives else None
            self.events.append(
                {
                    "type": "game_over",
                    "winner_id": self.winner_id,
                    "winner_team": players_with_lives[0].team if players_with_lives else None,
                    "winner_name": players_with_lives[0].name if players_with_lives else "无人",
                }
            )

    # ── State Snapshot ──────────────────────────────────────

    def get_state(self) -> dict:
        """Return full game state for network broadcast."""
        return {
            "tick": self.tick_count,
            "players": [p.to_dict() for p in self.players.values()],
            "projectiles": [p.to_dict() for p in self.projectiles],
            "pickups": [p.to_dict() for p in self.pickups],
            "game_over": self.game_over,
            "winner_id": self.winner_id,
            "winner_team": self.players[self.winner_id].team if self.winner_id in self.players else None,
        }

    def get_map_data(self) -> dict:
        """Return map data for initial client load."""
        return self.map.to_dict()
