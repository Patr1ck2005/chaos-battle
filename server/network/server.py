"""HTTP + WebSocket server using aiohttp."""

import asyncio
import json
import pathlib
import time
import weakref

import aiohttp
from aiohttp import web, WSMsgType

from server.config import SERVER_HOST, SERVER_PORT, TICK_RATE
from server.game.bot import BotController
from server.network.lobby import LobbyManager, Room, RoomState
from server.network.protocol import (
    MessageType,
    make_message,
    parse_message,
    validate_message,
)

# Find the client directory (relative to this file)
CLIENT_DIR = pathlib.Path(__file__).parent.parent.parent / "client"


class GameServer:
    def __init__(self):
        self.lobby = LobbyManager()
        # Map: WebSocket → client_id
        self.clients: dict[aiohttp.web.WebSocketResponse, str] = {}
        # Map: client_id → WebSocket (using weakref-compatible approach)
        self.client_sockets: dict[str, aiohttp.web.WebSocketResponse] = {}
        self.game_loops: dict[str, asyncio.Task] = {}
        self.bot_controllers: dict[str, dict[str, BotController]] = {}
        self.last_pong: dict[str, float] = {}  # client_id → last pong timestamp
        self._heartbeat_task: asyncio.Task | None = None

    async def handle_ws(self, request: web.Request) -> web.WebSocketResponse:
        """Handle a WebSocket connection."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        client_id = None
        nickname = "Player"

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    data = parse_message(msg.data)
                    if not data or not validate_message(data):
                        await ws.send_str(
                            make_message(MessageType.ERROR, message="无效的消息格式")
                        )
                        continue

                    msg_type = data.get("type")

                    if msg_type == MessageType.JOIN_LOBBY:
                        client_id = str(id(ws))
                        nickname = data.get("nickname", "Player")
                        self.clients[ws] = client_id
                        self.client_sockets[client_id] = ws
                        self.last_pong[client_id] = time.time()
                        await ws.send_str(
                            make_message(
                                MessageType.LOBBY_STATE,
                                rooms=self.lobby.get_lobby_state(),
                                client_id=client_id,
                                nickname=nickname,
                            )
                        )

                    elif msg_type == MessageType.CREATE_ROOM:
                        if not client_id:
                            continue
                        room = self.lobby.create_room(
                            host_id=client_id,
                            host_name=nickname,
                            name=data.get("name", "Room"),
                            settings=data.get("settings"),
                        )
                        # Broadcast lobby update to all clients
                        await self._broadcast_lobby()
                        # Notify room members
                        await self._broadcast_room(room)

                    elif msg_type == MessageType.JOIN_ROOM:
                        if not client_id:
                            continue
                        room_id = data.get("room_id")
                        room, error = self.lobby.join_room(
                            room_id, client_id, nickname
                        )
                        if error:
                            await ws.send_str(
                                make_message(MessageType.ERROR, message=error)
                            )
                        else:
                            await self._broadcast_lobby()
                            await self._broadcast_room(room)

                    elif msg_type == MessageType.LEAVE_ROOM:
                        if not client_id:
                            continue
                        room = self.lobby.leave_room(client_id)
                        await self._broadcast_lobby()
                        if room:
                            await self._broadcast_room(room)

                    elif msg_type == MessageType.START_GAME:
                        if not client_id:
                            continue
                        room = self.lobby.get_client_room(client_id)
                        if room and room.can_start(client_id):
                            await self._start_game(room)

                    elif msg_type == MessageType.PLAYER_INPUT:
                        if not client_id:
                            continue
                        room = self.lobby.get_client_room(client_id)
                        if room and room.engine and room.state == RoomState.PLAYING:
                            room.engine.process_input(client_id, data.get("keys", {}))

                    elif msg_type == MessageType.SET_ABILITY:
                        if not client_id:
                            continue
                        room = self.lobby.get_client_room(client_id)
                        if room and room.state == RoomState.WAITING:
                            target_id = data.get("target_player_id", client_id)
                            ability = data.get("ability", "none")
                            # Host can set anyone's ability; normal players can only set their own
                            if client_id == room.host_id or target_id == client_id:
                                room.set_player_loadout(target_id, ability=ability)
                                await self._broadcast_room(room)

                    elif msg_type == MessageType.SET_LOADOUT:
                        if not client_id:
                            continue
                        room = self.lobby.get_client_room(client_id)
                        if room and room.state == RoomState.WAITING:
                            target_id = data.get("target_player_id", client_id)
                            is_host = client_id == room.host_id
                            target = next(
                                (p for p in room.players if p["id"] == target_id),
                                None,
                            )
                            if not target:
                                continue
                            can_edit = is_host or (
                                target_id == client_id and not target.get("is_bot", False)
                            )
                            if not can_edit:
                                continue
                            room.set_player_loadout(
                                target_id,
                                ability=data.get("ability"),
                                appearance=data.get("appearance"),
                                team=data.get("team"),
                                initial_weapon=data.get("initial_weapon"),
                            )
                            await self._broadcast_room(room)

                    elif msg_type == MessageType.ADD_BOT:
                        if not client_id:
                            continue
                        room = self.lobby.get_client_room(client_id)
                        if room and client_id == room.host_id and room.state == RoomState.WAITING:
                            if room.settings.bot_count < 9:
                                room.settings.bot_count += 1
                                room.add_bot()
                            await self._broadcast_room(room)
                            await self._broadcast_lobby()

                    elif msg_type == MessageType.REMOVE_BOT:
                        if not client_id:
                            continue
                        room = self.lobby.get_client_room(client_id)
                        if room and client_id == room.host_id and room.state == RoomState.WAITING:
                            if room.remove_bot(data.get("bot_id", "")):
                                await self._broadcast_room(room)
                                await self._broadcast_lobby()

                    elif msg_type == MessageType.PING:
                        await ws.send_str(make_message(MessageType.PONG))
                        if client_id:
                            self.last_pong[client_id] = time.time()

                    elif msg_type == MessageType.PONG:
                        if client_id:
                            self.last_pong[client_id] = time.time()

                    elif msg_type == MessageType.UPDATE_SETTINGS:
                        if not client_id:
                            continue
                        room = self.lobby.get_client_room(client_id)
                        if room and client_id == room.host_id and room.state == RoomState.WAITING:
                            settings = data.get("settings", {})
                            if "lives" in settings:
                                try:
                                    room.settings.lives = max(1, int(settings["lives"]))
                                except (TypeError, ValueError):
                                    room.settings.lives = 1
                            if "weapon_crates" in settings:
                                room.settings.weapon_crates = bool(settings["weapon_crates"])
                            await self._broadcast_room(room)

                elif msg.type == WSMsgType.ERROR:
                    pass

        except Exception as e:
            print(f"WebSocket error: {e}")
        finally:
            # Cleanup on disconnect
            if client_id:
                room = self.lobby.get_client_room(client_id)
                if room:
                    # If in game, kill the player's character
                    if room.engine and room.state == RoomState.PLAYING:
                        player = room.engine.players.get(client_id)
                        if player and player.is_alive():
                            player.die()
                # Leave room (this also handles cleaning up room player list)
                room = self.lobby.leave_room(client_id)
                self.client_sockets.pop(client_id, None)
                self.last_pong.pop(client_id, None)
                if room:
                    await self._broadcast_room(room)
                    await self._broadcast_lobby()
            self.clients.pop(ws, None)

        return ws

    async def _broadcast_lobby(self) -> None:
        """Send updated lobby state to all clients not in a room."""
        state = self.lobby.get_lobby_state()
        for client_id, ws in self.client_sockets.items():
            if not self.lobby.client_rooms.get(client_id):
                try:
                    await ws.send_str(
                        make_message(MessageType.LOBBY_STATE, rooms=state)
                    )
                except Exception:
                    pass

    async def _broadcast_room(self, room: Room) -> None:
        """Send room update to all players in the room."""
        try:
            data = make_message(MessageType.ROOM_UPDATE, room=room.to_dict())
        except Exception as e:
            print(f"ERROR _broadcast_room: make_message failed: {e}")
            return
        for pdata in room.human_players:
            pid = pdata["id"]
            ws = self.client_sockets.get(pid)
            if ws is not None:
                try:
                    await ws.send_str(data)
                except Exception as e:
                    print(f"ERROR _broadcast_room: send failed: {e}")

    async def _start_game(self, room: Room) -> None:
        """Start a game in the given room."""
        engine = room.start_game()

        # Set up bot controllers
        self.bot_controllers[room.id] = {}
        for pid, player in engine.players.items():
            if player.is_bot:
                self.bot_controllers[room.id][pid] = BotController()

        # Send game start + map data to all players
        map_data = engine.get_map_data()
        for pdata in room.human_players:
            ws = self.client_sockets.get(pdata["id"])
            if ws is not None:
                try:
                    await ws.send_str(
                        make_message(
                            MessageType.GAME_START,
                            map=map_data,
                            client_id=pdata["id"],
                        )
                    )
                except Exception:
                    pass

        # Start game loop
        loop = asyncio.get_event_loop()
        room.game_task = loop.create_task(self._run_game_loop(room))

    async def _run_game_loop(self, room: Room) -> None:
        """Run the game loop for a room."""
        tick_duration = 1.0 / TICK_RATE

        try:
            while room.engine and not room.engine.game_over:
                await asyncio.sleep(tick_duration)

                events = room.engine.tick(self.bot_controllers.get(room.id, {}))

                # Broadcast game state
                state = room.engine.get_state()
                state_data = make_message(MessageType.GAME_STATE, **state)
                for pdata in room.human_players:
                    ws = self.client_sockets.get(pdata["id"])
                    if ws is not None:
                        try:
                            await ws.send_str(state_data)
                        except Exception:
                            pass

                # Broadcast events
                if events:
                    events_data = make_message(MessageType.GAME_EVENTS, events=events)
                    for pdata in room.human_players:
                        ws = self.client_sockets.get(pdata["id"])
                        if ws is not None:
                            try:
                                await ws.send_str(events_data)
                            except Exception:
                                pass

            # Game over — send final state
            if room.engine:
                final_state = room.engine.get_state()
                for pdata in room.human_players:
                    ws = self.client_sockets.get(pdata["id"])
                    if ws is not None:
                        try:
                            await ws.send_str(
                                make_message(MessageType.GAME_STATE, **final_state)
                            )
                            await ws.send_str(
                                make_message(
                                    MessageType.GAME_OVER,
                                    winner_id=room.engine.winner_id,
                                    winner_team=final_state.get("winner_team"),
                                )
                            )
                        except Exception:
                            pass

                # Reset room after a delay
                await asyncio.sleep(5)
                room.reset()
                await self._broadcast_room(room)
                await self._broadcast_lobby()

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Game loop error: {e}")
            room.reset()

    async def handle_index(self, request: web.Request) -> web.FileResponse:
        """Serve index.html."""
        return web.FileResponse(CLIENT_DIR / "index.html")

    def create_app(self) -> web.Application:
        """Create the aiohttp application."""
        app = web.Application()

        # WebSocket route for game
        app.router.add_get("/ws", self.handle_ws)

        # Serve static files
        app.router.add_get("/", self.handle_index)
        # Add static routes for client subdirectories
        for subdir in ["css", "js", "assets"]:
            subdir_path = CLIENT_DIR / subdir
            if subdir_path.exists():
                app.router.add_static(
                    f"/{subdir}/", path=str(subdir_path), show_index=False
                )

        return app


    async def _run_heartbeat(self) -> None:
        """Send PING to all clients every 5s; disconnect clients silent for 15s+."""
        HEARTBEAT_INTERVAL = 5
        HEARTBEAT_TIMEOUT = 15
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            now = time.time()
            # Send PING to all connected clients
            for ws, client_id in list(self.clients.items()):
                try:
                    await ws.send_str(make_message(MessageType.PING))
                except Exception:
                    pass
            # Disconnect clients that haven't responded
            for client_id, last in list(self.last_pong.items()):
                if now - last > HEARTBEAT_TIMEOUT:
                    ws = self.client_sockets.get(client_id)
                    if ws is not None and not ws.closed:
                        print(f"Heartbeat timeout for client {client_id}, disconnecting.")
                        await ws.close()


async def run_server() -> None:
    """Run the game server."""
    server = GameServer()
    app = server.create_app()

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, SERVER_HOST, SERVER_PORT)

    print(f"Chaos Battle server running at http://localhost:{SERVER_PORT}")
    print(f"Client files served from: {CLIENT_DIR}")

    await site.start()

    # Start heartbeat task
    heartbeat = asyncio.create_task(server._run_heartbeat())

    # Keep running
    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        pass
    finally:
        heartbeat.cancel()
        try:
            await heartbeat
        except asyncio.CancelledError:
            pass
