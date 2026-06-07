/**
 * Canvas 2D Renderer — draws the game world.
 * Uses programmatic graphics (colored shapes) — no external sprites needed.
 */
class Renderer {
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.camera = new Camera();
        this.sprite = new Image();
        this.spriteLoaded = false;
        this.sprite.onload = () => { this.spriteLoaded = true; };
        this.sprite.src = '/assets/player-sprites.png';
        this.weaponSprite = new Image();
        this.weaponSpriteLoaded = false;
        this.weaponSprite.onload = () => { this.weaponSpriteLoaded = true; };
        this.weaponSprite.src = '/assets/weapon-sprites.png?v=katana-awm-2';
        this.spriteFrameW = 32;
        this.spriteFrameH = 48;
        this.spriteScale = 1.35;
        this.weaponFrameW = 48;
        this.weaponFrameH = 24;
        this.appearanceRows = {
            scout: 0,
            vanguard: 1,
            ghost: 2,
            medic: 3,
            engineer: 4,
            raider: 5,
        };
        this.weaponRows = {
            pistol: 0,
            sniper: 1,
            katana: 2,
        };
        this.attackEffects = {};
        this.localPlayerId = null;
    }

    handleGameEvent(evt) {
        const now = performance.now();
        if (evt.type === 'shoot') {
            this.attackEffects[evt.player_id] = {
                type: 'shoot',
                weapon: evt.weapon,
                start: now,
                duration: 140,
            };
        } else if (evt.type === 'melee_swing') {
            this.attackEffects[evt.player_id] = {
                type: evt.attack === 'uppercut' ? 'uppercut' : 'slash',
                weapon: evt.weapon,
                start: now,
                duration: evt.attack === 'uppercut' ? 260 : 220,
            };
        }
    }

    previewLocalAttack(type, weapon = null) {
        if (!this.localPlayerId) return;
        this.attackEffects[this.localPlayerId] = {
            type,
            weapon: weapon || (type === 'shoot' ? 'pistol' : 'katana'),
            start: performance.now(),
            duration: type === 'uppercut' ? 260 : type === 'slash' ? 220 : 140,
        };
    }

    /**
     * Resize canvas to fill window.
     */
    resize() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
        this.camera.setViewport(this.canvas.width, this.canvas.height);
    }

    /**
     * Draw one frame given the game state and local player id.
     * state: { players, projectiles, pickups }
     * prevState: previous state for interpolation (nullable)
     * alpha: interpolation factor 0-1
     */
    draw(state, prevState, localPlayerId) {
        const ctx = this.ctx;
        const cam = this.camera;
        const w = this.canvas.width;
        const h = this.canvas.height;
        this.localPlayerId = localPlayerId;

        // Clear
        ctx.fillStyle = '#0a0a1a';
        ctx.fillRect(0, 0, w, h);

        // Draw starfield background
        this._drawBackground(ctx, w, h);

        // Find local player to center camera
        let localPlayer = null;
        for (const p of state.players) {
            if (p.id === localPlayerId) {
                localPlayer = p;
                break;
            }
        }
        if (localPlayer && localPlayer.state === 'alive') {
            cam.follow(localPlayer.x + 15, localPlayer.y + 25);
        }

        // Save context for world-space drawing
        ctx.save();
        ctx.translate(-cam.x, -cam.y);

        // Draw map boundary
        ctx.strokeStyle = '#334';
        ctx.lineWidth = 3;
        ctx.strokeRect(0, 0, state.map?.width || 2000, state.map?.height || 1200);

        // Draw platforms
        this._drawPlatforms(ctx, state.map);

        // Draw pickups
        if (state.pickups) {
            for (const pk of state.pickups) {
                this._drawPickup(ctx, pk);
            }
        }

        // Draw projectiles
        if (state.projectiles) {
            for (const proj of state.projectiles) {
                this._drawProjectile(ctx, proj);
            }
        }

        // Draw players
        for (const p of state.players) {
            if (p.state === 'alive') {
                this._drawPlayer(ctx, p, localPlayerId);
            }
        }

        ctx.restore();

        // Draw HUD
        if (localPlayer) {
            this._drawHUD(localPlayer);
        }
    }

    // ── Background ──────────────────────────────
    _drawBackground(ctx, w, h) {
        // Simple gradient sky
        const grad = ctx.createLinearGradient(0, 0, 0, h);
        grad.addColorStop(0, '#0a0a2e');
        grad.addColorStop(0.5, '#101030');
        grad.addColorStop(1, '#1a1a3a');
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, w, h);

        // Stars
        ctx.fillStyle = '#ffffff';
        const starSeed = 42;
        for (let i = 0; i < 80; i++) {
            const sx = ((i * 173 + starSeed) % w);
            const sy = ((i * 311 + starSeed * 7) % h);
            const brightness = 0.3 + ((i * 97) % 100) / 140;
            ctx.globalAlpha = brightness;
            ctx.fillRect(sx, sy, 2, 2);
        }
        ctx.globalAlpha = 1;
    }

    // ── Platforms ───────────────────────────────
    _drawPlatforms(ctx, mapData) {
        if (!mapData || !mapData.platforms) return;

        for (const plat of mapData.platforms) {
            // Platform body
            const grad = ctx.createLinearGradient(plat.x, plat.y, plat.x, plat.y + plat.height);
            grad.addColorStop(0, '#5a7a5a');
            grad.addColorStop(0.5, '#4a6a4a');
            grad.addColorStop(1, '#3a5a3a');
            ctx.fillStyle = grad;
            ctx.fillRect(plat.x, plat.y, plat.width, plat.height);

            // Top edge highlight
            ctx.fillStyle = '#7aaa7a';
            ctx.fillRect(plat.x, plat.y, plat.width, 3);

            // Bottom shadow
            ctx.fillStyle = '#2a4a2a';
            ctx.fillRect(plat.x, plat.y + plat.height - 2, plat.width, 2);
        }
    }

    // ── Pickups ─────────────────────────────────
    _drawPickup(ctx, pk) {
        // Crate body
        ctx.fillStyle = '#cc8800';
        ctx.fillRect(pk.x, pk.y, pk.width, pk.height);

        // Crate cross (ammo box style)
        ctx.strokeStyle = '#ffee44';
        ctx.lineWidth = 2;
        const cx = pk.x + pk.width / 2;
        const cy = pk.y + pk.height / 2;
        ctx.beginPath();
        ctx.moveTo(cx, pk.y + 3);
        ctx.lineTo(cx, pk.y + pk.height - 3);
        ctx.moveTo(pk.x + 3, cy);
        ctx.lineTo(pk.x + pk.width - 3, cy);
        ctx.stroke();

        // Glow effect
        ctx.shadowColor = '#ffaa00';
        ctx.shadowBlur = 8;
        ctx.fillStyle = 'rgba(255, 170, 0, 0.3)';
        ctx.fillRect(pk.x - 2, pk.y - 2, pk.width + 4, pk.height + 4);
        ctx.shadowBlur = 0;

        ctx.fillStyle = '#2b1b08';
        ctx.fillRect(pk.x + 7, pk.y + 7, 10, 10);
        ctx.fillStyle = '#ffee66';
        ctx.fillRect(pk.x + 10, pk.y + 5, 4, 14);
    }

    // ── Projectiles ─────────────────────────────
    _drawProjectile(ctx, proj) {
        // Bullet trail
        ctx.fillStyle = '#ffdd44';
        ctx.shadowColor = '#ffaa00';
        ctx.shadowBlur = 4;
        ctx.beginPath();
        ctx.arc(proj.x, proj.y, proj.radius || 4, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 0;
    }

    // ── Players ─────────────────────────────────
    _drawPlayer(ctx, p, localPlayerId) {
        const isLocal = p.id === localPlayerId;
        const style = this._appearanceStyle(p.appearance);
        const teamColor = this._teamColor(p.team);

        // Shadow
        ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
        ctx.fillRect(p.x + 2, p.y + 2, 30, 50);

        let bodyColor = style.body;
        if (p.invincible) {
            // Blink effect for invincibility
            bodyColor = (Math.floor(Date.now() / 100) % 2 === 0) ? '#ffffff' : bodyColor;
        }

        // Team marker under the feet
        ctx.fillStyle = teamColor;
        ctx.globalAlpha = 0.75;
        ctx.fillRect(p.x - 3, p.y + 51, 36, 4);
        ctx.globalAlpha = 1;

        // Body
        const usingSprite = this.spriteLoaded && !p.invincible;
        if (usingSprite) {
            this._drawPlayerSprite(ctx, p);
        } else {
            this._drawFallbackPlayer(ctx, p, bodyColor, style);
        }
        this._drawHeldWeapon(ctx, p);

        // Team belt
        ctx.fillStyle = teamColor;
        ctx.fillRect(p.x, p.y + 28, 30, 5);

        // Bot antenna
        if (p.is_bot && !usingSprite) {
            ctx.strokeStyle = '#dce9ff';
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(p.x + 15, p.y - 8);
            ctx.lineTo(p.x + 15, p.y - 15);
            ctx.stroke();
            ctx.fillStyle = teamColor;
            ctx.fillRect(p.x + 13, p.y - 17, 4, 4);
        }

        if (!usingSprite) {
            // Eyes (direction indicator)
            ctx.fillStyle = '#000';
            const eyeX = p.facing_right ? p.x + 18 : p.x + 8;
            ctx.fillRect(eyeX, p.y - 3, 4, 4);

            // Weapon arm
            ctx.fillStyle = bodyColor;
            if (p.facing_right) {
                ctx.fillRect(p.x + 28, p.y + 15, 12, 6);
            } else {
                ctx.fillRect(p.x - 10, p.y + 15, 12, 6);
            }
        }

        // Name label
        ctx.fillStyle = '#ffffff';
        ctx.font = '11px Consolas, Microsoft YaHei, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(p.name || 'Player', p.x + 15, p.y - 12);

        // HP bar above player
        const hpRatio = p.hp / p.max_hp;
        const barWidth = 30;
        const barY = p.y - 6;
        ctx.fillStyle = '#333';
        ctx.fillRect(p.x, barY, barWidth, 3);
        ctx.fillStyle = hpRatio > 0.5 ? '#22cc22' : hpRatio > 0.25 ? '#cccc22' : '#cc2222';
        ctx.fillRect(p.x, barY, barWidth * hpRatio, 3);

        ctx.textAlign = 'start';
    }

    _drawPlayerSprite(ctx, p) {
        const row = this.appearanceRows[p.appearance] ?? 0;
        let frame = 0;
        if (!p.on_ground) {
            frame = 3;
        } else if (Math.abs(p.vx) > 35) {
            frame = Math.floor(Date.now() / 120) % 2 === 0 ? 1 : 2;
        }

        const drawW = this.spriteFrameW * this.spriteScale;
        const drawH = this.spriteFrameH * this.spriteScale;
        const dx = p.x + 15 - drawW / 2;
        const dy = p.y + 50 - drawH;

        ctx.save();
        ctx.imageSmoothingEnabled = false;
        if (!p.facing_right) {
            ctx.translate(dx + drawW, dy);
            ctx.scale(-1, 1);
            ctx.drawImage(
                this.sprite,
                frame * this.spriteFrameW,
                row * this.spriteFrameH,
                this.spriteFrameW,
                this.spriteFrameH,
                0,
                0,
                drawW,
                drawH
            );
        } else {
            ctx.drawImage(
                this.sprite,
                frame * this.spriteFrameW,
                row * this.spriteFrameH,
                this.spriteFrameW,
                this.spriteFrameH,
                dx,
                dy,
                drawW,
                drawH
            );
        }
        ctx.restore();
    }

    _drawFallbackPlayer(ctx, p, bodyColor, style) {
        ctx.fillStyle = bodyColor;
        ctx.fillRect(p.x, p.y, 30, 50);

        ctx.fillStyle = style.detail;
        if (p.appearance === 'ghost') {
            ctx.fillRect(p.x + 4, p.y + 8, 22, 5);
            ctx.fillRect(p.x + 2, p.y + 34, 26, 10);
        } else if (p.appearance === 'medic') {
            ctx.fillRect(p.x + 13, p.y + 8, 4, 18);
            ctx.fillRect(p.x + 8, p.y + 14, 14, 4);
        } else if (p.appearance === 'engineer') {
            ctx.fillRect(p.x + 4, p.y + 7, 22, 6);
            ctx.fillRect(p.x + 6, p.y + 31, 18, 5);
        } else if (p.appearance === 'raider') {
            ctx.fillRect(p.x + 5, p.y + 10, 20, 4);
            ctx.fillRect(p.x + 20, p.y + 20, 6, 22);
        } else if (p.appearance === 'vanguard') {
            ctx.fillRect(p.x + 3, p.y + 6, 24, 8);
            ctx.fillRect(p.x + 6, p.y + 22, 18, 8);
        } else {
            ctx.fillRect(p.x + 5, p.y + 10, 20, 4);
            ctx.fillRect(p.x + 12, p.y + 24, 6, 18);
        }

        ctx.fillStyle = '#ffcc99';
        ctx.fillRect(p.x + 7, p.y - 8, 16, 14);
    }

    _drawHeldWeapon(ctx, p) {
        const weapon = (p.weapons || [])[p.active_weapon_slot || 0];
        if (!weapon) return;

        const dir = p.facing_right ? 1 : -1;
        const weaponKey = weapon.key || this._weaponKeyFromName(weapon.name);
        const row = this.weaponRows[weaponKey] ?? 0;
        const scale = weaponKey === 'sniper' ? 1.25 : weaponKey === 'katana' ? 1.28 : 1.15;
        const drawW = this.weaponFrameW * scale;
        const drawH = this.weaponFrameH * scale;
        const explicitEffect = this._activeAttackEffect(p.id);
        const stateEffect = weaponKey === 'katana'
            ? this._weaponStateAttackEffect(weapon)
            : null;
        const effect = explicitEffect || stateEffect;
        const progress = effect ? effect.progress : 1;
        const recoil = effect && effect.type === 'shoot' ? (1 - progress) * 10 : 0;
        const slashLift = effect && effect.type === 'slash' ? Math.sin(progress * Math.PI) * 10 : 0;
        const upperLift = effect && effect.type === 'uppercut' ? Math.sin(progress * Math.PI) * 18 : 0;
        const gripX = p.facing_right ? p.x + 27 : p.x + 3;
        const destX = gripX - dir * recoil;
        const destY = p.y + 20 - slashLift - upperLift;
        let angle = 0;
        if (weaponKey === 'katana' && effect) {
            if (effect.type === 'slash') {
                angle = (-0.85 + progress * 2.15) * dir;
            } else if (effect.type === 'uppercut') {
                angle = (1.15 - progress * 2.45) * dir;
            }
        }

        if (this.weaponSpriteLoaded) {
            ctx.save();
            ctx.imageSmoothingEnabled = false;
            ctx.translate(destX, destY);
            ctx.rotate(angle);
            if (!p.facing_right) {
                ctx.scale(-1, 1);
                ctx.drawImage(
                    this.weaponSprite,
                    0,
                    row * this.weaponFrameH,
                    this.weaponFrameW,
                    this.weaponFrameH,
                    weaponKey === 'katana' ? -drawW * 0.18 : -drawW * 0.22,
                    -drawH / 2,
                    drawW,
                    drawH
                );
            } else {
                ctx.drawImage(
                    this.weaponSprite,
                    0,
                    row * this.weaponFrameH,
                    this.weaponFrameW,
                    this.weaponFrameH,
                    weaponKey === 'katana' ? -drawW * 0.18 : -drawW * 0.22,
                    -drawH / 2,
                    drawW,
                    drawH
                );
            }
            ctx.restore();
            if (weaponKey === 'katana' && effect) {
                this._drawAttackArc(ctx, p, effect);
            }
            return;
        }

        ctx.fillStyle = weaponKey === 'katana' ? '#e8f4ff' : '#242a36';
        ctx.fillRect(p.facing_right ? destX : destX - 18, destY - 3, weaponKey === 'katana' ? 22 : 18, 5);
        if (weaponKey === 'katana' && effect) {
            this._drawAttackArc(ctx, p, effect);
        }
    }

    _drawAttackArc(ctx, p, effect) {
        const dir = p.facing_right ? 1 : -1;
        const progress = Math.max(0, Math.min(1, effect.progress));
        const cx = p.x + 15 + dir * 28;
        const cy = p.y + 24;
        const alpha = Math.sin(progress * Math.PI);
        const radius = effect.type === 'uppercut' ? 48 : 44;

        ctx.save();
        ctx.globalAlpha = Math.max(0, alpha);
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';

        if (effect.type === 'uppercut') {
            const start = dir > 0 ? 0.72 * Math.PI : 0.28 * Math.PI;
            const end = dir > 0 ? -0.58 * Math.PI : 1.58 * Math.PI;
            const sweepStart = start + (end - start) * Math.max(0, progress - 0.28);
            const sweepEnd = start + (end - start) * Math.min(1, progress + 0.28);
            ctx.strokeStyle = 'rgba(180, 236, 255, 0.92)';
            ctx.lineWidth = 8;
            ctx.beginPath();
            ctx.arc(cx, cy + 8, radius, sweepStart, sweepEnd, dir < 0);
            ctx.stroke();
            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = 3;
            ctx.beginPath();
            ctx.arc(cx, cy + 8, radius - 2, sweepStart, sweepEnd, dir < 0);
            ctx.stroke();
        } else {
            const startX = cx + dir * (-18 + progress * 30);
            const startY = cy - 42 + progress * 10;
            const midX = cx + dir * 34;
            const midY = cy - 4;
            const endX = cx + dir * (54 - progress * 8);
            const endY = cy + 34 - progress * 5;
            ctx.fillStyle = 'rgba(255, 210, 82, 0.22)';
            ctx.beginPath();
            ctx.moveTo(startX, startY);
            ctx.quadraticCurveTo(midX, midY, endX, endY);
            ctx.lineTo(endX - dir * 14, endY + 12);
            ctx.quadraticCurveTo(midX - dir * 10, midY + 8, startX - dir * 10, startY + 10);
            ctx.closePath();
            ctx.fill();
            ctx.strokeStyle = 'rgba(255, 238, 168, 0.9)';
            ctx.lineWidth = 12;
            ctx.beginPath();
            ctx.moveTo(startX, startY);
            ctx.quadraticCurveTo(midX, midY, endX, endY);
            ctx.stroke();
            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = 4;
            ctx.beginPath();
            ctx.moveTo(startX, startY);
            ctx.quadraticCurveTo(midX, midY, endX, endY);
            ctx.stroke();
        }

        ctx.restore();
    }

    _weaponStateAttackEffect(weapon) {
        const special = Number(weapon.special_cooldown || 0);
        if (special > 0.49) {
            return {
                type: 'uppercut',
                progress: Math.max(0, Math.min(1, (0.75 - special) / 0.26)),
            };
        }

        const cooldown = Number(weapon.cooldown || 0);
        if (cooldown > 0) {
            return {
                type: 'slash',
                progress: Math.max(0, Math.min(1, (0.28 - cooldown) / 0.28)),
            };
        }
        return null;
    }

    _activeAttackEffect(playerId) {
        const effect = this.attackEffects[playerId];
        if (!effect) return null;
        const elapsed = performance.now() - effect.start;
        if (elapsed >= effect.duration) {
            delete this.attackEffects[playerId];
            return null;
        }
        return { ...effect, progress: elapsed / effect.duration };
    }

    _drawWeaponIcon(ctx, weaponKey, x, y, w, h) {
        const row = this.weaponRows[weaponKey] ?? 0;
        if (this.weaponSpriteLoaded) {
            ctx.save();
            ctx.imageSmoothingEnabled = false;
            ctx.drawImage(
                this.weaponSprite,
                0,
                row * this.weaponFrameH,
                this.weaponFrameW,
                this.weaponFrameH,
                x,
                y,
                w,
                h
            );
            ctx.restore();
            return;
        }
        ctx.fillStyle = weaponKey === 'katana' ? '#dbe9ff' : '#202735';
        ctx.fillRect(x + 3, y + h / 2 - 2, w - 6, 4);
    }

    _weaponKeyFromName(name) {
        if (!name) return 'pistol';
        const lower = String(name).toLowerCase();
        if (lower.includes('katana')) return 'katana';
        if (lower.includes('sniper')) return 'sniper';
        return 'pistol';
    }

    _appearanceStyle(appearance) {
        const styles = {
            scout: { body: '#45a7ff', detail: '#d8efff' },
            vanguard: { body: '#7b7f8d', detail: '#c8ccd8' },
            ghost: { body: '#5f5b91', detail: '#bfb8ff' },
            medic: { body: '#f4f1e8', detail: '#df3848' },
            engineer: { body: '#d49a38', detail: '#4b596a' },
            raider: { body: '#43b36a', detail: '#1e3328' },
        };
        return styles[appearance] || styles.scout;
    }

    _teamColor(team) {
        const colors = {
            red: '#e9474f',
            blue: '#3f8cff',
            green: '#35bf65',
            yellow: '#e2b93b',
        };
        return colors[team] || colors.red;
    }

    // ── HUD ─────────────────────────────────────
    _drawHUD(player) {
        this._drawModernHUD(player);
        return;

        // Update DOM HUD elements
        const hpBar = document.getElementById('hud-hp-bar');
        const hpText = document.getElementById('hud-hp-text');
        const weaponName = document.getElementById('hud-weapon-name');
        const weaponAmmo = document.getElementById('hud-weapon-ammo');
        const livesCount = document.getElementById('hud-lives-count');
        const killsCount = document.getElementById('hud-kills-count');

        const hpRatio = player.hp / player.max_hp;
        hpBar.style.width = (hpRatio * 100) + '%';
        hpBar.style.background = hpRatio > 0.5
            ? 'linear-gradient(90deg, #22cc22, #66ee66)'
            : hpRatio > 0.25
                ? 'linear-gradient(90deg, #cccc22, #eeee44)'
                : 'linear-gradient(90deg, #cc2222, #ee4444)';
        hpText.textContent = `${player.hp}/${player.max_hp}`;

        // Weapon inventory display
        const weapons = player.weapons || [];
        const activeSlot = player.active_weapon_slot || 0;
        const activeWeapon = weapons[activeSlot];
        if (activeWeapon) {
            weaponName.textContent = `[${activeSlot + 1}] ${activeWeapon.name}`;
            weaponAmmo.textContent = activeWeapon.is_reloading
                ? '换弹中...'
                : (activeWeapon.reserve === null
                    ? `${activeWeapon.mag}/∞`
                    : `${activeWeapon.mag}/${activeWeapon.mag_size}` +
                      (activeWeapon.reserve > 0 ? ` (${activeWeapon.reserve})` : ''));
        }

        // Update weapon slots in the special weapon area
        const specialEl = document.getElementById('hud-special');
        if (activeWeapon) {
            weaponAmmo.textContent = this._ammoText(activeWeapon, false);
        }

        specialEl.innerHTML = '';
        for (let i = 0; i < 4; i++) {
            const w = weapons[i];
            const div = document.createElement('div');
            div.className = 'weapon-slot' + (i === activeSlot ? ' active' : '');
            div.style.cssText = `
                padding: 7px 10px; font-size: 15px; font-weight: ${i === activeSlot ? '800' : '600'};
                color: ${i === activeSlot ? '#fff' : '#888'};
                background: ${i === activeSlot ? 'rgba(255,200,50,0.3)' : 'rgba(0,0,0,0.3)'};
                border: 1px solid ${i === activeSlot ? '#ffcc44' : '#444'};
                border-radius: 5px; margin-bottom: 0;
            `;
            if (w) {
                div.textContent = `${i + 1}. ${w.name} ${w.mag}/${w.mag_size}` +
                    (w.is_reloading ? ' R' : '');
            } else {
                div.textContent = `${i + 1}. ——`;
            }
            specialEl.appendChild(div);
        }

        livesCount.textContent = player.lives;
        killsCount.textContent = player.kills || 0;
    }

    // ── Kill Feed ───────────────────────────────
    _drawModernHUD(player) {
        const hpBar = document.getElementById('hud-hp-bar');
        const hpText = document.getElementById('hud-hp-text');
        const weaponName = document.getElementById('hud-weapon-name');
        const weaponAmmo = document.getElementById('hud-weapon-ammo');
        const livesCount = document.getElementById('hud-lives-count');
        const killsCount = document.getElementById('hud-kills-count');
        const specialEl = document.getElementById('hud-special');
        if (!hpBar || !hpText || !weaponName || !weaponAmmo || !specialEl) return;

        const hpRatio = Math.max(0, Math.min(1, player.hp / player.max_hp));
        hpBar.style.width = `${hpRatio * 100}%`;
        hpBar.style.background = hpRatio > 0.5
            ? 'linear-gradient(90deg, #22cc22, #66ee66)'
            : hpRatio > 0.25
                ? 'linear-gradient(90deg, #cccc22, #eeee44)'
                : 'linear-gradient(90deg, #cc2222, #ee4444)';
        hpText.textContent = `${player.hp}/${player.max_hp}`;

        const weapons = player.weapons || [];
        const activeSlot = player.active_weapon_slot || 0;
        const activeWeapon = weapons[activeSlot];
        if (activeWeapon) {
            weaponName.textContent = `[${activeSlot + 1}] ${activeWeapon.name}`;
            weaponAmmo.textContent = this._ammoText(activeWeapon, false);
        }

        specialEl.innerHTML = '';
        for (let i = 0; i < 4; i++) {
            const w = weapons[i];
            const div = document.createElement('div');
            div.className = 'weapon-slot' + (i === activeSlot ? ' active' : '');
            if (w) {
                const weaponKey = w.key || this._weaponKeyFromName(w.name);
                const ammoText = this._ammoText(w, true);
                div.innerHTML = `
                    <span class="weapon-slot-index">${i + 1}</span>
                    <span class="weapon-slot-icon" style="${this._weaponIconCss(weaponKey)}"></span>
                    <span class="weapon-slot-name">${w.name}</span>
                    <span class="weapon-slot-ammo">${ammoText}</span>
                `;
            } else {
                div.innerHTML = `
                    <span class="weapon-slot-index">${i + 1}</span>
                    <span class="weapon-slot-icon empty"></span>
                    <span class="weapon-slot-name">Empty</span>
                    <span class="weapon-slot-ammo"></span>
                `;
            }
            specialEl.appendChild(div);
        }

        if (livesCount) livesCount.textContent = player.lives;
        if (killsCount) killsCount.textContent = player.kills || 0;
    }

    _weaponIconCss(weaponKey) {
        const row = this.weaponRows[weaponKey] ?? 0;
        return [
            "background-image: url('/assets/weapon-sprites.png?v=katana-awm-2')",
            `background-position: 0 -${row * this.weaponFrameH}px`,
            `background-size: ${this.weaponFrameW}px ${Object.keys(this.weaponRows).length * this.weaponFrameH}px`,
        ].join(';');
    }

    _ammoText(weapon, compact = false) {
        if (!weapon) return '';
        if (weapon.kind === 'melee') {
            return weapon.special_cooldown > 0
                ? `SPECIAL ${weapon.special_cooldown.toFixed(1)}s`
                : (compact ? 'READY' : 'MELEE READY');
        }
        if (weapon.is_reloading) return compact ? 'R' : 'RELOADING';
        if (weapon.reserve === null) return `${weapon.mag}/∞`;
        const total = weapon.total_ammo_capacity ?? (weapon.mag_size + Math.max(0, weapon.reserve || 0));
        return `${weapon.mag}/${total}`;
    }

    showKillMessage(killerName, victimName) {
        const feed = document.getElementById('hud-killfeed');
        const el = document.createElement('div');
        el.className = 'killfeed-item';
        el.textContent = `${killerName || '环境'} 击杀了 ${victimName}`;
        feed.appendChild(el);

        // Auto-remove after animation
        setTimeout(() => {
            if (el.parentNode) el.parentNode.removeChild(el);
        }, 4000);
    }
}
