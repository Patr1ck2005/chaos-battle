/**
 * UI Manager — handles all DOM screens (menu, lobby, room, settings).
 */
const UI = {
    init() {
        // ── Main Menu ──────────────────────────────
        document.getElementById('btn-single').addEventListener('click', () => {
            App.nickname = document.getElementById('input-nickname').value.trim() || 'Player';
            localStorage.setItem('chaos_battle_nickname', App.nickname);
            App.pendingSinglePlayer = false;
            this._sendWhenReady({
                type: 'create_room',
                name: '单人练习',
                settings: {
                    max_players: 1,
                    bot_count: 3,
                    lives: 3,
                    weapon_crates: true,
                },
            });
        });

        document.getElementById('btn-multi').addEventListener('click', () => {
            App.nickname = document.getElementById('input-nickname').value.trim() || 'Player';
            localStorage.setItem('chaos_battle_nickname', App.nickname);
            App.showScreen('lobby');
        });

        document.getElementById('btn-settings').addEventListener('click', () => {
            this._populateSettings();
            App.showScreen('settings');
        });

        // ── Lobby ──────────────────────────────────
        document.getElementById('btn-create-room').addEventListener('click', () => {
            const name = document.getElementById('input-room-name').value.trim() || '游戏房间';
            this._sendWhenReady({
                type: 'create_room',
                name: name,
                settings: {
                    max_players: 10,
                    bot_count: 0,
                    lives: 3,
                    weapon_crates: true,
                },
            });
        });

        document.getElementById('btn-refresh-lobby').addEventListener('click', () => {
            App.network.send({ type: 'join_lobby', nickname: App.nickname });
        });

        document.getElementById('btn-back-to-menu').addEventListener('click', () => {
            App.network.send({ type: 'leave_room' });
            App.showScreen('menu');
        });

        // ── Room ───────────────────────────────────
        document.getElementById('btn-start-game').addEventListener('click', () => {
            App.network.send({ type: 'start_game' });
        });

        document.getElementById('btn-leave-room').addEventListener('click', () => {
            App.network.send({ type: 'leave_room' });
            App.showScreen('menu');
        });

        // ── Settings ───────────────────────────────
        document.getElementById('btn-save-settings').addEventListener('click', () => {
            this._saveSettings();
            App.showScreen('menu');
        });

        document.getElementById('btn-back-settings').addEventListener('click', () => {
            App.showScreen('menu');
        });

        // ── Game Over ──────────────────────────────
        document.getElementById('btn-back-from-game').addEventListener('click', () => {
            App.game.stop();
            App.input.stopSendingInput();
            if (App.currentRoom && App.currentRoom.state === 'waiting') {
                document.getElementById('game-over-overlay').style.display = 'none';
                App.showScreen('room');
            } else {
                App.returnToRoomAfterGameOver = true;
                document.getElementById('game-over-text').textContent = '正在返回房间...';
                document.getElementById('game-over-winner').textContent = '请稍候，房间正在重置。';
            }
        });
    },

    // ── Send helper: queues if not connected yet ──────
    _sendWhenReady(msg) {
        if (App.lobbyReady && App.clientId) {
            App.network.send(msg);
        } else {
            // Queue the action, will be sent when lobby_state arrives
            App._pendingAction = () => App.network.send(msg);
            // Ensure we've requested registration
            App.network.send({ type: 'join_lobby', nickname: App.nickname });
        }
    },

    // ── Render Functions ──────────────────────────

    renderLobby(rooms) {
        if (App.screen !== 'lobby') return;
        const list = document.getElementById('room-list');
        if (!rooms || rooms.length === 0) {
            list.innerHTML = '<div class="room-list-empty">暂无房间，创建一个吧！</div>';
            return;
        }

        list.innerHTML = rooms.map(r => `
            <div class="room-list-item" data-room-id="${r.id}">
                <div>
                    <div class="room-name">${this._esc(r.name)}</div>
                    <div class="room-info">
                        玩家 ${r.player_count}/${r.max_players}
                        | 机器人 ${r.settings.bot_count}
                        | 生命 ×${r.settings.lives}
                        | 武器箱 ${r.settings.weapon_crates ? '开启' : '关闭'}
                    </div>
                </div>
            </div>
        `).join('');

        // Click to join room
        list.querySelectorAll('.room-list-item').forEach(item => {
            item.addEventListener('click', () => {
                const roomId = item.dataset.roomId;
                App.network.send({ type: 'join_room', room_id: roomId });
            });
        });
    },

    renderRoom(room, isHost) {
        // Update screen
        document.getElementById('room-title').textContent = room.name;
        document.getElementById('btn-start-game').style.display = isHost ? 'inline-block' : 'none';

        // Unified member table. Everyone sees the same rows; permissions only affect controls.
        const playerList = document.getElementById('room-players');
        playerList.innerHTML = `
            <div class="member-table">
                <div class="member-row member-row-head">
                    <div>成员</div>
                    <div>外观</div>
                    <div>能力</div>
                    <div>队伍</div>
                    <div>操作</div>
                </div>
                ${room.players.map(p => this._renderLoadoutRow(p, isHost)).join('')}
            </div>
        `;
        const headCells = playerList.querySelectorAll('.member-row-head > div');
        if (headCells.length === 5) {
            const startWeaponHead = document.createElement('div');
            startWeaponHead.textContent = '初始武器';
            headCells[2].after(startWeaponHead);
        }

        const settingsDisplay = document.getElementById('room-settings-display');
        settingsDisplay.innerHTML = `
            <div class="room-admin-panel">
                <div class="room-admin-title">房间管理</div>
                <div class="room-admin-controls">
                    <label class="room-admin-field">
                        <span>生命数</span>
                        <input id="room-lives-input" type="number" min="1" step="1" value="${room.settings.lives}" ${isHost ? '' : 'disabled'}>
                    </label>
                    <label class="room-admin-field room-admin-toggle">
                        <span>武器箱</span>
                        <input id="room-crates-input" type="checkbox" ${room.settings.weapon_crates ? 'checked' : ''} ${isHost ? '' : 'disabled'}>
                    </label>
                    <div class="room-admin-summary">真人 ${room.player_count}/${room.max_players} · AI ${room.bot_count ?? room.settings.bot_count}</div>
                    ${isHost ? '<button id="btn-add-bot" class="btn-secondary btn-compact" type="button">添加 AI</button>' : ''}
                </div>
            </div>
        `;

        const addBot = settingsDisplay.querySelector('#btn-add-bot');
        if (addBot) {
            addBot.addEventListener('click', () => {
                App.network.send({ type: 'add_bot' });
            });
        }

        playerList.querySelectorAll('.btn-remove-bot').forEach(btn => {
            btn.addEventListener('click', () => {
                App.network.send({ type: 'remove_bot', bot_id: btn.dataset.playerId });
            });
        });

        playerList.querySelectorAll('.loadout-select').forEach(sel => {
            sel.addEventListener('change', () => {
                const row = sel.closest('.ability-row');
                App.network.send({
                    type: 'set_loadout',
                    target_player_id: row.dataset.playerId,
                    appearance: row.querySelector('[data-field="appearance"]')?.value,
                    ability: row.querySelector('[data-field="ability"]')?.value,
                    initial_weapon: row.querySelector('[data-field="initial_weapon"]')?.value,
                    team: row.querySelector('[data-field="team"]')?.value,
                });
            });
        });

        const sendSettings = () => {
            if (!isHost) return;
            const livesInput = settingsDisplay.querySelector('#room-lives-input');
            const cratesInput = settingsDisplay.querySelector('#room-crates-input');
            const parsedLives = parseInt(livesInput.value || '1', 10);
            const lives = Number.isFinite(parsedLives) ? Math.max(1, parsedLives) : 1;
            livesInput.value = String(lives);
            App.network.send({
                type: 'update_settings',
                settings: {
                    lives,
                    weapon_crates: cratesInput.checked,
                },
            });
        };

        const livesInput = settingsDisplay.querySelector('#room-lives-input');
        const cratesInput = settingsDisplay.querySelector('#room-crates-input');
        if (livesInput && !livesInput.disabled) {
            livesInput.addEventListener('change', sendSettings);
            livesInput.addEventListener('blur', sendSettings);
        }
        if (cratesInput && !cratesInput.disabled) {
            cratesInput.addEventListener('change', sendSettings);
        }
    },

    _renderLoadoutRow(player, isHost) {
        const canEdit = isHost || (player.id === App.clientId && !player.is_bot);
        const disabled = canEdit ? '' : 'disabled';
        return `
            <div class="ability-row member-row" data-player-id="${player.id}">
                <div class="member-name">
                    <span class="team-dot team-${this._esc(player.team || 'red')}"></span>
                    ${this._esc(player.name)}
                    ${player.is_host ? '<span class="host-badge">[房主]</span>' : ''}
                    ${player.is_bot ? '<span class="bot-badge">[AI]</span>' : ''}
                </div>
                <div>
                    <select class="loadout-select" data-field="appearance" ${disabled}>
                        ${this._appearanceOptions(player.appearance)}
                    </select>
                </div>
                <div>
                    <select class="loadout-select" data-field="ability" ${disabled}>
                        ${this._abilityOptions(player.ability)}
                    </select>
                </div>
                <div>
                    <select class="loadout-select" data-field="initial_weapon" ${disabled}>
                        ${this._initialWeaponOptions(player.initial_weapon)}
                    </select>
                </div>
                <div>
                    <select class="loadout-select" data-field="team" ${disabled}>
                        ${this._teamOptions(player.team)}
                    </select>
                </div>
                <div class="member-actions">
                    ${isHost && player.is_bot ? `
                        <button class="btn-secondary btn-compact btn-remove-bot" type="button" data-player-id="${player.id}">移除</button>
                    ` : ''}
                </div>
            </div>
        `;
    },

    _abilityOptions(value = 'none') {
        const items = [
            ['none', '无能力'],
            ['double_jump', '二段跳'],
            ['no_reload', '手枪无需换弹'],
        ];
        return items.map(([id, label]) =>
            `<option value="${id}" ${value === id ? 'selected' : ''}>${label}</option>`
        ).join('');
    },

    _appearanceOptions(value = 'scout') {
        const items = [
            ['scout', '侦察兵'],
            ['vanguard', '先锋'],
            ['ghost', '幽灵'],
            ['medic', '医疗兵'],
            ['engineer', '工程师'],
            ['raider', '突击手'],
        ];
        return items.map(([id, label]) =>
            `<option value="${id}" ${value === id ? 'selected' : ''}>${label}</option>`
        ).join('');
    },

    _initialWeaponOptions(value = 'pistol') {
        const items = [
            ['pistol', '手枪'],
            ['katana', '武士刀'],
        ];
        return items.map(([id, label]) =>
            `<option value="${id}" ${value === id ? 'selected' : ''}>${label}</option>`
        ).join('');
    },

    _teamOptions(value = 'red') {
        const items = [
            ['red', '红队'],
            ['blue', '蓝队'],
            ['green', '绿队'],
            ['yellow', '黄队'],
        ];
        return items.map(([id, label]) =>
            `<option value="${id}" ${value === id ? 'selected' : ''}>${label}</option>`
        ).join('');
    },

    _abilityLabel(ability) {
        if (ability === 'double_jump') return '二段跳';
        if (ability === 'no_reload') return '手枪无需换弹';
        return '无';
    },

    _appearanceLabel(appearance) {
        const labels = {
            scout: '侦察兵',
            vanguard: '先锋',
            ghost: '幽灵',
            medic: '医疗兵',
            engineer: '工程师',
            raider: '突击手',
        };
        return labels[appearance] || labels.scout;
    },

    _teamLabel(team) {
        const labels = {
            red: '红队',
            blue: '蓝队',
            green: '绿队',
            yellow: '黄队',
        };
        return labels[team] || labels.red;
    },

    // ── Settings ──────────────────────────────────

    _populateSettings() {
        document.getElementById('bind-left').value = App.keyBindings.left.toUpperCase();
        document.getElementById('bind-right').value = App.keyBindings.right.toUpperCase();
        document.getElementById('bind-up').value = App.keyBindings.up.toUpperCase();
        document.getElementById('bind-down').value = App.keyBindings.down.toUpperCase();
        document.getElementById('bind-attack').value = App.keyBindings.attack.toUpperCase();
        document.getElementById('bind-special').value = App.keyBindings.special.toUpperCase();
        document.getElementById('bind-reload').value = App.keyBindings.reload.toUpperCase();
    },

    _saveSettings() {
        const newBindings = {
            left: document.getElementById('bind-left').value.toLowerCase() || 'a',
            right: document.getElementById('bind-right').value.toLowerCase() || 'd',
            up: document.getElementById('bind-up').value.toLowerCase() || 'w',
            down: document.getElementById('bind-down').value.toLowerCase() || 's',
            attack: document.getElementById('bind-attack').value.toLowerCase() || 'j',
            special: document.getElementById('bind-special').value.toLowerCase() || 'k',
            reload: document.getElementById('bind-reload').value.toLowerCase() || 'r',
        };
        App.keyBindings = newBindings;
        App.input.setBindings(newBindings);
        localStorage.setItem('chaos_battle_keybinds', JSON.stringify(newBindings));
    },

    // ── Helpers ───────────────────────────────────

    _esc(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    },
};
