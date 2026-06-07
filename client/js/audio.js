/**
 * Audio manager — stub for sound effects.
 * Uses Web Audio API. Currently placeholder — sounds can be added later.
 */
const AudioManager = {
    ctx: null,
    unlocked: false,

    init() {
        try {
            this.ctx = new (window.AudioContext || window.webkitAudioContext)();
            window.addEventListener('pointerdown', () => this.unlock(), { once: true });
            window.addEventListener('keydown', () => this.unlock(), { once: true });
        } catch (e) {
            console.log('Web Audio API not available');
        }
    },

    unlock() {
        if (!this.ctx || this.unlocked) return;
        const resume = this.ctx.state === 'suspended'
            ? this.ctx.resume()
            : Promise.resolve();
        resume.then(() => {
            const gain = this.ctx.createGain();
            gain.gain.value = 0.0001;
            const osc = this.ctx.createOscillator();
            osc.frequency.value = 220;
            osc.connect(gain);
            gain.connect(this.ctx.destination);
            osc.start();
            osc.stop(this.ctx.currentTime + 0.02);
            this.unlocked = true;
        }).catch(() => {});
    },

    /**
     * Play a simple tone (placeholder for real sound effects).
     */
    playTone(freq, duration, type = 'square', volume = 0.1) {
        if (!this.ctx) return;
        if (this.ctx.state === 'suspended') {
            this.ctx.resume()
                .then(() => {
                    this.unlocked = true;
                    this.playTone(freq, duration, type, volume);
                })
                .catch(() => {});
            return;
        }
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = type;
        osc.frequency.value = freq;
        gain.gain.setValueAtTime(volume, this.ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + duration);
        osc.connect(gain);
        gain.connect(this.ctx.destination);
        osc.start(this.ctx.currentTime);
        osc.stop(this.ctx.currentTime + duration);
    },

    shoot() {
        this.playTone(820, 0.09, 'square', 0.09);
        setTimeout(() => this.playTone(180, 0.05, 'triangle', 0.035), 25);
    },

    hit() {
        this.playTone(190, 0.16, 'sawtooth', 0.12);
    },

    blade() {
        this.playTone(360, 0.10, 'triangle', 0.09);
        setTimeout(() => this.playTone(760, 0.08, 'triangle', 0.07), 35);
    },

    reload() {
        this.playTone(300, 0.07, 'square', 0.075);
        setTimeout(() => this.playTone(480, 0.07, 'square', 0.06), 95);
    },

    pickup() {
        this.playTone(620, 0.1, 'sine', 0.08);
    },

    death() {
        this.playTone(100, 0.3, 'sawtooth', 0.1);
    },
};
