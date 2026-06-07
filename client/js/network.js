/**
 * WebSocket network client.
 */
class Network {
    constructor(url) {
        this.url = url;
        this.ws = null;
        this.onMessage = null;
        this.reconnectTimer = null;
        this.connected = false;
    }

    connect() {
        if (this.ws) {
            this.ws.close();
        }
        try {
            this.ws = new WebSocket(this.url);
        } catch (e) {
            console.error('WebSocket connection error:', e);
            this._scheduleReconnect();
            return;
        }

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.connected = true;
            if (this.reconnectTimer) {
                clearTimeout(this.reconnectTimer);
                this.reconnectTimer = null;
            }
            // Always register with the server on connect
            this.send({ type: 'join_lobby', nickname: App.nickname });
        };

        this.ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                if (this.onMessage) {
                    this.onMessage(msg);
                }
            } catch (e) {
                console.error('Failed to parse message:', e);
            }
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.connected = false;
            this._scheduleReconnect();
        };

        this.ws.onerror = (err) => {
            console.error('WebSocket error:', err);
        };
    }

    send(msg) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(msg));
        }
    }

    _scheduleReconnect() {
        if (this.reconnectTimer) return;
        this.reconnectTimer = setTimeout(() => {
            this.reconnectTimer = null;
            console.log('Attempting reconnect...');
            this.connect();
        }, 3000);
    }

    close() {
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
}
