/**
 * UGI Friend B — 3D Orbit Interaction and WebGL Fallback Module
 * UI-011: Graph and guided-state interaction module
 *
 * Implements native WebGL 3D orbit controls, camera projection, picking,
 * and graceful fallback to the 2D evidence map when WebGL is unavailable.
 *
 * Rules:
 * - Prefixed with `ugiB`
 * - No external dependencies (three.js, CDN, packages)
 * - Safe return-to-2D fallback that never obscures the empty graph state
 */

(function (global) {
  "use strict";

  /**
   * Check whether WebGL is supported and functional on the given canvas element.
   *
   * @param {HTMLCanvasElement} [canvas] - Optional canvas to probe.
   * @returns {{supported: boolean, gl: WebGLRenderingContext|null, reason: string|null}}
   */
  function ugiBCheckWebGLSupport(canvas) {
    const target = canvas || (typeof document !== "undefined" ? document.createElement("canvas") : null);
    if (!target || typeof target.getContext !== "function") {
      return { supported: false, gl: null, reason: "Canvas API not available" };
    }

    try {
      const gl = target.getContext("webgl", {
        alpha: true,
        antialias: true,
        preserveDrawingBuffer: false,
      }) || target.getContext("experimental-webgl");

      if (!gl) {
        return { supported: false, gl: null, reason: "WebGL context creation failed" };
      }

      // Check shader compiler support
      const vShader = gl.createShader(gl.VERTEX_SHADER);
      gl.shaderSource(vShader, "void main(){gl_Position=vec4(0.0);}");
      gl.compileShader(vShader);
      const ok = gl.getShaderParameter(vShader, gl.COMPILE_STATUS);
      gl.deleteShader(vShader);

      if (!ok) {
        return { supported: false, gl: null, reason: "Shader compilation not supported" };
      }

      return { supported: true, gl, reason: null };
    } catch (err) {
      return { supported: false, gl: null, reason: err.message || "WebGL initialization error" };
    }
  }

  /**
   * Setup and handle the WebGL fallback UI.
   * When WebGL fails, ensures the fallback notice is shown and binds
   * the return-to-2D button.
   *
   * @param {Element} fallbackEl - The #orbitFallback container.
   * @param {Element} returnButton - The #fallback2d button.
   * @param {Function} onViewModeChange - Callback to switch mode back to "2d".
   */
  function ugiBOrbitFallbackHandler(fallbackEl, returnButton, onViewModeChange) {
    if (!fallbackEl) return;

    fallbackEl.hidden = false;
    fallbackEl.classList.add("ugi-b-fallback-active");

    if (returnButton && typeof onViewModeChange === "function") {
      returnButton.onclick = (e) => {
        if (e) e.preventDefault();
        onViewModeChange("2d");
      };
    }
  }

  /**
   * Pick closest screen-projected 3D node or event record based on pointer coordinates.
   *
   * @param {number} clientX - Pointer clientX.
   * @param {number} clientY - Pointer clientY.
   * @param {HTMLCanvasElement} canvas - The WebGL canvas.
   * @param {Array<Object>} screenRecords - Array of projected objects {x, y, depth, item}.
   * @param {number} [tolerance=24] - Maximum distance in CSS pixels.
   * @returns {Object|null} The matched record or null.
   */
  function ugiBPick3DRecord(clientX, clientY, canvas, screenRecords, tolerance = 24) {
    if (!canvas || !Array.isArray(screenRecords) || !screenRecords.length) {
      return null;
    }

    const bounds = canvas.getBoundingClientRect();
    if (bounds.width <= 0 || bounds.height <= 0) return null;

    const ratio = canvas.width / bounds.width;
    const x = (clientX - bounds.left) * ratio;
    const y = (clientY - bounds.top) * ratio;

    const dpr = typeof window !== "undefined" && window.devicePixelRatio ? window.devicePixelRatio : 1;
    const matches = screenRecords
      .map((entry) => ({
        entry,
        distance: Math.hypot(entry.x - x, entry.y - y),
      }))
      .filter((m) => m.distance < tolerance * dpr)
      .sort((a, b) => a.distance - b.distance || a.entry.depth - b.entry.depth);

    return matches.length > 0 ? matches[0].entry.item.record : null;
  }

  /**
   * Coordinate view mode switching between "2d" and "3d".
   *
   * @param {"2d"|"3d"} mode - Desired mode.
   * @param {Object} elements - Map of UI elements (graph2d, graph3d, view2d, view3d, etc.).
   * @param {Object} callbacks - Hooks for orbit initialization and sync.
   * @returns {string} The active view mode.
   */
  function ugiBSetViewMode(mode, elements, callbacks) {
    const orbitView = mode === "3d";
    const graph2d = elements?.graph2d;
    const graph3d = elements?.graph3d;
    const view2d = elements?.view2d;
    const view3d = elements?.view3d;
    const autoRotate = elements?.autoRotate;
    const zoomIn = elements?.zoomIn;
    const zoomOut = elements?.zoomOut;
    const resetview = elements?.resetview;
    const mapcaption = elements?.mapcaption;

    if (graph2d) graph2d.hidden = orbitView;
    if (graph3d) graph3d.hidden = !orbitView;

    if (view2d) {
      view2d.setAttribute("aria-selected", String(!orbitView));
      view2d.tabIndex = orbitView ? -1 : 0;
    }
    if (view3d) {
      view3d.setAttribute("aria-selected", String(orbitView));
      view3d.tabIndex = orbitView ? 0 : -1;
    }

    if (autoRotate) autoRotate.hidden = !orbitView;
    if (zoomIn) zoomIn.hidden = orbitView;
    if (zoomOut) zoomOut.hidden = orbitView;
    if (resetview) resetview.hidden = orbitView;

    if (mapcaption) {
      mapcaption.textContent = orbitView
        ? "Orbit the same source-backed evidence in three dimensions. Directional particles show claim flow; selection always resolves to the stored record."
        : "Drag nodes to inspect their shape. Drag open space to pan. A selected node, claim, or event always resolves back to its stored record.";
    }

    if (orbitView && typeof callbacks?.onActivate3D === "function") {
      callbacks.onActivate3D();
    }

    return mode;
  }

  /**
   * Manage camera key navigation in 3D orbit view.
   * Accessible keyboard controls:
   * - Arrow keys: rotate yaw/pitch
   * - + / -: zoom in / out
   * - 0: reset camera to default
   * - Escape: clear selection
   *
   * @param {KeyboardEvent} event
   * @param {Object} orbitState - The camera state object {yaw, pitch, distance, target}.
   * @param {Object} callbacks - Hooks for clearSelection, reset, render.
   */
  function ugiBHandleOrbitKeyboard(event, orbitState, callbacks) {
    if (!event || !orbitState) return;

    const keys = {
      ArrowLeft: () => { orbitState.yaw -= 0.13; },
      ArrowRight: () => { orbitState.yaw += 0.13; },
      ArrowUp: () => { orbitState.pitch = Math.max(-1.25, orbitState.pitch - 0.1); },
      ArrowDown: () => { orbitState.pitch = Math.min(1.25, orbitState.pitch + 0.1); },
      "+": () => { orbitState.distance = Math.max(4, orbitState.distance * 0.88); },
      "=": () => { orbitState.distance = Math.max(4, orbitState.distance * 0.88); },
      "-": () => { orbitState.distance = Math.min(28, orbitState.distance * 1.14); },
      "0": () => {
        orbitState.yaw = 0.68;
        orbitState.pitch = 0.24;
        orbitState.distance = 13;
        orbitState.target = [0, 0, 0];
      },
      Escape: () => {
        if (typeof callbacks?.onClearSelection === "function") {
          callbacks.onClearSelection();
        }
      },
    };

    if (keys[event.key]) {
      event.preventDefault();
      keys[event.key]();
      if (typeof callbacks?.onUpdate === "function") {
        callbacks.onUpdate();
      }
    }
  }

  // Export API
  const ugiBOrbitInteraction = {
    ugiBCheckWebGLSupport,
    ugiBOrbitFallbackHandler,
    ugiBPick3DRecord,
    ugiBSetViewMode,
    ugiBHandleOrbitKeyboard,
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = ugiBOrbitInteraction;
  } else {
    global.ugiBOrbitInteraction = ugiBOrbitInteraction;
    Object.assign(global, ugiBOrbitInteraction);
  }
})(typeof window !== "undefined" ? window : globalThis);
