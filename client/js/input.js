/**
 * Keyboard input manager.
 * Maps physical keys to logical game actions based on key bindings.
 */
class InputManager {
    constructor(keyBindings) {
        this.keyBindings = keyBindings;

        // Currently pressed physical keys
        this._pressed = new Set();

        // One-shot actions (fire once per keypress, not continuously)
        this._oneShotActions = {};

        this._onKeyDown = this._onKeyDown.bind(this);
        this._onKeyUp = this._onKeyUp.bind(this);

        window.addEventListener('keydown', this._onKeyDown);
        window.addEventListener('keyup', this._onKeyUp);
    }

    setBindings(keyBindings) {
        this.keyBindings = { ...this.keyBindings, ...keyBindings };
    }

    /**
     * Get current logical key state.
     * Returns object with boolean for each action, plus one-shot weapon_slot.
     * One-shot values are consumed (returned once then cleared).
     */
    getKeys() {
        const keys = {
            left: false,
            right: false,
            up: false,
            down: false,
            attack: false,
            special: false,
            reload: false,
            weapon_slot: null,  // one-shot: set to slot index when number key pressed
            attack_pressed: false,
            jump_pressed: false,
            special_pressed: false,
        };

        for (const [action, key] of Object.entries(this.keyBindings)) {
            keys[action] = this._pressed.has(key.toLowerCase());
        }

        if (this._oneShotActions.up) {
            keys.jump_pressed = true;
            this._oneShotActions.up = false;
        }

        if (this._oneShotActions.attack) {
            keys.attack_pressed = true;
            this._oneShotActions.attack = false;
        }

        if (this._oneShotActions.special) {
            keys.special_pressed = true;
            this._oneShotActions.special = false;
        }

        // Consume one-shot weapon slot changes
        if (this._oneShotActions.weapon_slot !== undefined) {
            keys.weapon_slot = this._oneShotActions.weapon_slot;
            this._oneShotActions.weapon_slot = undefined;
        }

        return keys;
    }

    /**
     * Start sending input to the server at regular intervals.
     */
    startSendingInput(intervalMs = 50) {
        if (this._sendInterval) return;
        this._sendInterval = setInterval(() => {
            if (App.network && App.network.connected) {
                App.network.send({
                    type: 'input',
                    keys: this.getKeys(),
                });
            }
        }, intervalMs);
    }

    /**
     * Stop sending input.
     */
    stopSendingInput() {
        if (this._sendInterval) {
            clearInterval(this._sendInterval);
            this._sendInterval = null;
        }
    }

    _onKeyDown(e) {
        // Ignore if typing in an input field
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') {
            return;
        }

        const key = e.key.toLowerCase();
        const wasPressed = this._pressed.has(key);
        this._pressed.add(key);
        if (typeof AudioManager !== 'undefined') {
            AudioManager.unlock();
        }

        if (!wasPressed && key === this.keyBindings.attack.toLowerCase()) {
            this._oneShotActions.attack = true;
            this._previewAttack('attack');
        }
        if (!wasPressed && key === this.keyBindings.up.toLowerCase()) {
            this._oneShotActions.up = true;
        }
        if (!wasPressed && key === this.keyBindings.special.toLowerCase()) {
            this._oneShotActions.special = true;
            this._previewAttack('special');
        }

        // Handle number keys for weapon switching (1-4)
        if (key === '1') this._oneShotActions.weapon_slot = 0;
        else if (key === '2') this._oneShotActions.weapon_slot = 1;
        else if (key === '3') this._oneShotActions.weapon_slot = 2;
        else if (key === '4') this._oneShotActions.weapon_slot = 3;

        e.preventDefault();
    }

    _previewAttack(action) {
        if (typeof App === 'undefined' || App.screen !== 'game' || !App.game?.currentState) return;
        const player = App.game.currentState.players?.find(p => p.id === App.game.localPlayerId);
        if (!player || player.state !== 'alive') return;
        const weapon = (player.weapons || [])[player.active_weapon_slot || 0];
        if (!weapon) return;
        const weaponKey = weapon.key || String(weapon.name || '').toLowerCase();
        if (weaponKey.includes('katana')) {
            App.game.renderer.previewLocalAttack(action === 'special' ? 'uppercut' : 'slash', 'katana');
        } else if (action === 'attack') {
            App.game.renderer.previewLocalAttack('shoot', weaponKey);
        }
    }

    _onKeyUp(e) {
        this._pressed.delete(e.key.toLowerCase());
        e.preventDefault();
    }

    destroy() {
        window.removeEventListener('keydown', this._onKeyDown);
        window.removeEventListener('keyup', this._onKeyUp);
        this.stopSendingInput();
    }
}
