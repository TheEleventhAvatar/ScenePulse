/**
 * Performance instrumentation for the viewport.
 *
 * Tracks FPS, frame time, draw calls, triangle count and object count with
 * zero per-frame allocations. DOM updates are throttled to ~4 Hz so the
 * status bar never causes layout thrash inside the render loop.
 */

export class PerfStats {
  constructor({ fpsEl, frameTimeEl, drawCallsEl, trianglesEl, objectsEl } = {}) {
    this.els = { fpsEl, frameTimeEl, drawCallsEl, trianglesEl, objectsEl };

    // Exponential moving averages — no arrays, no allocation per frame.
    this.fps = 0;
    this.frameTimeMs = 0;
    this._emaAlpha = 0.08; // smoothing factor (~half-second window at 60fps)

    this.drawCalls = 0;
    this.triangles = 0;
    this.objectCount = 0;

    this._lastDomUpdate = 0;
    this._domIntervalMs = 250;
  }

  /** Called once per rendered frame. `delta` in seconds. */
  update(renderer, delta) {
    const instantFps = delta > 0 ? 1 / delta : 0;
    // Clamp away tab-switch spikes before they poison the average.
    if (instantFps > 0 && instantFps <= 240) {
      this.fps += (instantFps - this.fps) * this._emaAlpha;
      this.frameTimeMs += (delta * 1000 - this.frameTimeMs) * this._emaAlpha;
    }

    // renderer.info reflects the *last* render call — free to read.
    const info = renderer.info.render;
    this.drawCalls = info.calls;
    this.triangles = info.triangles;

    const now = performance.now();
    if (now - this._lastDomUpdate >= this._domIntervalMs) {
      this._lastDomUpdate = now;
      this._updateDom();
    }
  }

  /** Recount scene objects; call only when the scene changes, not per frame. */
  setObjectCount(count) {
    this.objectCount = count;
  }

  _updateDom() {
    const { fpsEl, frameTimeEl, drawCallsEl, trianglesEl, objectsEl } = this.els;
    const fps = Math.round(this.fps);
    if (fpsEl) {
      fpsEl.textContent = String(fps);
      const statEl = fpsEl.closest('.stat');
      if (statEl) {
        statEl.classList.toggle('fps-good', fps >= 50);
        statEl.classList.toggle('fps-mid', fps >= 30 && fps < 50);
        statEl.classList.toggle('fps-bad', fps < 30);
      }
    }
    if (frameTimeEl) frameTimeEl.textContent = `${this.frameTimeMs.toFixed(1)} ms`;
    if (drawCallsEl) drawCallsEl.textContent = String(this.drawCalls);
    if (trianglesEl) trianglesEl.textContent = formatCount(this.triangles);
    if (objectsEl) objectsEl.textContent = String(this.objectCount);
  }
}

function formatCount(n) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return String(n);
}