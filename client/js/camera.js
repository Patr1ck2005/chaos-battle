/**
 * Camera — translates world coordinates to screen coordinates.
 * Follows the local player, clamped to map bounds.
 */
class Camera {
    constructor() {
        this.x = 0;
        this.y = 0;
        this.viewWidth = 0;
        this.viewHeight = 0;
        this.mapWidth = 2000;
        this.mapHeight = 1200;
    }

    /**
     * Set the viewport size (canvas dimensions).
     */
    setViewport(width, height) {
        this.viewWidth = width;
        this.viewHeight = height;
    }

    /**
     * Set map bounds.
     */
    setMapBounds(width, height) {
        this.mapWidth = width;
        this.mapHeight = height;
    }

    /**
     * Center camera on a world position, clamped to map edges.
     */
    follow(worldX, worldY) {
        this.x = worldX - this.viewWidth / 2;
        this.y = worldY - this.viewHeight / 2;

        // Clamp to map bounds
        if (this.x < 0) this.x = 0;
        if (this.y < 0) this.y = 0;
        if (this.x + this.viewWidth > this.mapWidth) {
            this.x = this.mapWidth - this.viewWidth;
        }
        if (this.y + this.viewHeight > this.mapHeight) {
            this.y = this.mapHeight - this.viewHeight;
        }

        // If view is larger than map, center it
        if (this.viewWidth >= this.mapWidth) {
            this.x = (this.mapWidth - this.viewWidth) / 2;
        }
        if (this.viewHeight >= this.mapHeight) {
            this.y = (this.mapHeight - this.viewHeight) / 2;
        }
    }

    /**
     * Convert world coordinates to screen coordinates.
     */
    worldToScreen(worldX, worldY) {
        return {
            x: worldX - this.x,
            y: worldY - this.y,
        };
    }
}
