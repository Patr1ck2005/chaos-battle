/**
 * Chaos Battle — Main Application Controller
 * Manages app state, screen routing, and coordinates all subsystems.
 */

const App = {
    // ── State ──────────────────────────────────────
    screen: 'menu',       // menu | lobby | room | game | settings
    clientId: null,
    nickname: 'Player',
    currentRoom: null,     // room data from server
    isHost: false,
    pendingSinglePlayer: false,
    returnToRoomAfterGameOver: false,
    lobbyReady: false,
    _pendingAction: null,  // queued action when not yet connected

    // Key bindings (default: WASD, J/K/R)
    keyBindings: {
        left: 'a',
        right: 'd',
        up: 'w',
        down: 's',
        attack: 'j',
        special: 'k',
        reload: 'r',
    },

    // ── Subsystems ─────────────────────────────────
    network: null,       // Network instance
    input: null,         // InputManager instance
    game: null,          // ClientGame instance

    // ── Init ───────────────────────────────────────
    init() {
        // Load key bindings from localStorage
        const saved = localStorage.getItem('chaos_battle_keybinds');
        if (saved) {
            try {
                const parsed = JSON.parse(saved);
                Object.assign(this.keyBindings, parsed);
            } catch (e) { /* ignore */ }
        }

        // Load nickname
        const savedName = localStorage.getItem('chaos_battle_nickname');
        if (savedName) {
            this.nickname = savedName;
        }
        document.getElementById('input-nickname').value = this.nickname;

        // Init input manager
        this.input = new InputManager(this.keyBindings);
        AudioManager.init();

        // Init network
        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${location.host}/ws`;
        this.network = new Network(wsUrl);
        this.network.onMessage = (msg) => this._handleMessage(msg);
        this.network.connect();

        // Init game
        this.game = new ClientGame();

        // Init UI event handlers
        UI.init();

        // Show menu
        this.showScreen('menu');
    },

    // ── Screen Management ──────────────────────────
    showScreen(screen) {
        this.screen = screen;
        document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));

        const gameCanvas = document.getElementById('game-canvas');
        const gameOver = document.getElementById('game-over-overlay');
        const hud = document.getElementById('hud');

        if (screen === 'game') {
            document.getElementById('app').style.display = 'none';
            gameCanvas.style.display = 'block';
            hud.style.display = 'block';
            gameOver.style.display = 'none';
        } else {
            document.getElementById('app').style.display = 'flex';
            gameCanvas.style.display = 'none';
            hud.style.display = 'none';
            gameOver.style.display = 'none';

            const screenEl = document.getElementById(`screen-${screen}`);
            if (screenEl) screenEl.classList.add('active');

            if (screen === 'lobby') {
                this.network.send({ type: 'join_lobby', nickname: this.nickname });
            }
        }
    },

    // ── Message Handler ────────────────────────────
    _handleMessage(msg) {
        switch (msg.type) {
            case 'lobby_state':
                if (msg.client_id) {
                    this.clientId = msg.client_id;
                }
                if (msg.nickname) {
                    this.nickname = msg.nickname;
                }
                this.lobbyReady = true;
                if (this.screen === 'lobby') {
                    UI.renderLobby(msg.rooms);
                }
                // Execute pending action if any
                if (this._pendingAction) {
                    const action = this._pendingAction;
                    this._pendingAction = null;
                    action();
                }
                break;

            case 'room_update':
                this.currentRoom = msg.room;
                this.isHost = msg.room.host_id === this.clientId;
                UI.renderRoom(msg.room, this.isHost);
                if (this.returnToRoomAfterGameOver && this.screen === 'game') {
                    this.returnToRoomAfterGameOver = false;
                    document.getElementById('game-over-overlay').style.display = 'none';
                    this.showScreen('room');
                    break;
                }
                if (this.screen !== 'room' && this.screen !== 'game') {
                    this.showScreen('room');
                }
                break;

            case 'game_start':
                this.currentRoom = null;  // will be set when we return
                this.game.start(msg.map, msg.client_id);
                this.showScreen('game');
                break;

            case 'game_state':
                this.game.onGameState(msg);
                break;

            case 'game_events':
                this.game.onGameEvents(msg.events);
                break;

            case 'game_over':
                this.game.onGameOver(msg);
                // Show game over overlay
                const overlay = document.getElementById('game-over-overlay');
                const text = document.getElementById('game-over-winner');
                overlay.style.display = 'flex';
                if (msg.winner_id === this.clientId) {
                    document.getElementById('game-over-text').textContent = '你赢了！';
                    text.textContent = '恭喜！你是最后的幸存者。';
                } else if (msg.winner_id) {
                    document.getElementById('game-over-text').textContent = '游戏结束';
                    text.textContent = '胜者已决出。';
                } else {
                    document.getElementById('game-over-text').textContent = '游戏结束';
                    text.textContent = '没有胜者。';
                }
                // After 5 seconds, auto-return to room
                setTimeout(() => {
                    document.getElementById('game-over-overlay').style.display = 'none';
                    if (this.currentRoom && this.currentRoom.state === 'waiting') {
                        this.showScreen('room');
                    } else {
                        this.returnToRoomAfterGameOver = true;
                    }
                }, 5000);
                break;

            case 'error':
                alert('错误: ' + (msg.message || '未知错误'));
                break;

            case 'pong':
                break;
        }
    },
};

// ── Boot ───────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
    App.init();
});
