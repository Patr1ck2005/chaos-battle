/**
 * Client-side game loop and state management.
 * Runs at 60fps via requestAnimationFrame.
 * Interpolates between server state snapshots for smooth rendering.
 */
class ClientGame {
    constructor() {
        this.canvas = document.getElementById('game-canvas');
        this.renderer = new Renderer(this.canvas);
        this.currentState = null;
        this.previousState = null;
        this.stateTime = 0;       // when currentState was received
        this.mapData = null;
        this.localPlayerId = null;
        this.running = false;
        this.animFrameId = null;

        window.addEventListener('resize', () => this.renderer.resize());
    }

    /**
     * Called when the game starts. Initializes the map and rendering.
     */
    start(mapData, localPlayerId) {
        this.mapData = mapData;
        this.localPlayerId = localPlayerId;

        this.renderer.resize();
        this.renderer.camera.setMapBounds(
            mapData.width || 2000,
            mapData.height || 1200
        );

        // Start input sending
        App.input.startSendingInput(50);

        this.running = true;
        this._loop();
    }

    /**
     * Called when we receive a game state update from the server.
     */
    onGameState(state) {
        // Attach map data reference (server doesn't resend map each tick)
        state.map = this.mapData;

        this.previousState = this.currentState;
        this.currentState = state;
        this.stateTime = performance.now();
    }

    /**
     * Called when we receive game events (kills, etc.).
     */
    onGameEvents(events) {
        for (const evt of events) {
            this.renderer.handleGameEvent(evt);
            if (evt.type === 'kill') {
                this.renderer.showKillMessage(evt.killer_name, evt.victim_name);
            }
            if (evt.type === 'shoot') {
                AudioManager.shoot();
            } else if (evt.type === 'melee_swing') {
                AudioManager.blade();
            } else if (evt.type === 'hit') {
                AudioManager.hit();
            } else if (evt.type === 'reload') {
                AudioManager.reload();
            } else if (evt.type === 'pickup') {
                AudioManager.pickup();
            } else if (evt.type === 'kill') {
                AudioManager.death();
            }
        }
    }

    /**
     * Called when the game ends.
     */
    onGameOver(msg) {
        this.running = false;
        App.input.stopSendingInput();
        if (this.animFrameId) {
            cancelAnimationFrame(this.animFrameId);
            this.animFrameId = null;
        }
    }

    /**
     * Stop the game (manual stop, e.g., leaving early).
     */
    stop() {
        this.running = false;
        App.input.stopSendingInput();
        if (this.animFrameId) {
            cancelAnimationFrame(this.animFrameId);
            this.animFrameId = null;
        }
    }

    // ── Render Loop ──────────────────────────────

    _loop() {
        if (!this.running) return;

        this.animFrameId = requestAnimationFrame(() => this._loop());

        if (!this.currentState) return;

        const now = performance.now();
        const tickDuration = 50; // ms (20 ticks/sec)
        const elapsed = now - this.stateTime;
        const alpha = Math.min(elapsed / tickDuration, 1.0);

        // Interpolate between previous and current state
        let renderState;
        if (this.previousState) {
            renderState = this._interpolate(this.currentState, this.previousState, alpha);
        } else {
            renderState = this.currentState;
        }
        renderState.map = this.mapData;

        this.renderer.draw(renderState, null, this.localPlayerId);
    }

    /**
     * Linear interpolation between two game states.
     * Interpolates player positions, projectile positions.
     */
    _interpolate(current, previous, alpha) {
        if (!previous || !current) return current;

        const state = {
            players: [],
            projectiles: current.projectiles,
            pickups: current.pickups,
            tick: current.tick,
            game_over: current.game_over,
            winner_id: current.winner_id,
        };

        // Build lookup for previous players
        const prevPlayers = {};
        for (const pp of previous.players) {
            prevPlayers[pp.id] = pp;
        }

        for (const cp of current.players) {
            const pp = prevPlayers[cp.id];
            if (pp) {
                state.players.push({
                    ...cp,
                    x: pp.x + (cp.x - pp.x) * alpha,
                    y: pp.y + (cp.y - pp.y) * alpha,
                    vx: pp.vx + (cp.vx - pp.vx) * alpha,
                    vy: pp.vy + (cp.vy - pp.vy) * alpha,
                });
            } else {
                state.players.push(cp);
            }
        }

        return state;
    }
}
