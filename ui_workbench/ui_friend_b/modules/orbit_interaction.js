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
        ? "3D Graph: left-click / 3-finger drag to pan, 2-finger pinch to zoom. Selection resolves to stored record."
        : "2D Graph: left-click / 3-finger drag to pan, 2-finger pinch to zoom, drag nodes to reposition. Selection resolves to stored record.";
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

  /**
   * Return the GLSL vertex and fragment shader sources for volumetric 3D spheres
   * and cut-crystal diamonds with emissive selection highlights.
   *
   * @returns {{vertex: string, fragment: string}}
   */
  function ugiBGetVolumetricShaderSources() {
    const vertex = "attribute vec3 p; attribute vec4 c; attribute float s; attribute float diamond; uniform mat4 m; varying vec4 color; varying float shape; void main(){ gl_Position=m*vec4(p,1.0); float size = diamond < -0.5 ? max(10.0, (s * 5.0) / max(0.5, gl_Position.w)) : max(14.0, (s * 7.5)/max(0.5, gl_Position.w)); gl_PointSize=size; color=c; shape=diamond; }";
    const fragment = `precision mediump float;
varying vec4 color;
varying float shape;
void main(){
  vec2 q = (gl_PointCoord - 0.5) * 2.0;
  bool isPhoton = shape < -0.5;
  bool isDiamond = (shape > 0.5 && shape < 1.5) || (shape > 2.5);
  bool isSelected = shape > 1.5;

  if (isPhoton) {
    float r = length(q);
    if (r > 1.0) discard;
    float glow = exp(-r * 2.5);
    float core = smoothstep(0.4, 0.0, r);
    vec3 photonColor = mix(color.rgb, vec3(1.0), core * 0.9);
    float alpha = color.a * (glow * 0.75 + core * 0.55);
    gl_FragColor = vec4(photonColor, alpha);
  } else if (isDiamond) {
    vec2 p = abs(q);
    float d = p.x + p.y;
    if (d > 1.0) discard;
    float facet = 0.65 + 0.35 * (gl_PointCoord.y < 0.5 ? 0.35 : -0.2) + 0.25 * (gl_PointCoord.x < 0.5 ? 0.2 : -0.2);
    float ridge = 1.0 - smoothstep(0.0, 0.35, abs(p.x - p.y));
    float rim = smoothstep(0.75, 0.98, d);
    vec3 base = color.rgb * facet + vec3(0.4) * ridge;
    if (isSelected) base = mix(base, vec3(1.0, 0.98, 0.95), 0.6) + color.rgb * 0.4;
    float alpha = color.a * smoothstep(1.0, 0.92, d);
    gl_FragColor = vec4(base + vec3(rim * 0.45), alpha);
  } else {
    float distSq = dot(q, q);
    if (distSq > 1.0) discard;
    float r = sqrt(distSq);
    float z = sqrt(max(0.0, 1.0 - distSq));
    vec3 normal = normalize(vec3(q.x, -q.y, z));
    vec3 keyLight = normalize(vec3(-0.45, 0.65, 0.75));
    float keyDiff = max(0.0, dot(normal, keyLight));
    vec3 fillLight = normalize(vec3(0.55, -0.45, 0.4));
    float fillDiff = max(0.0, dot(normal, fillLight)) * 0.35;
    vec3 viewDir = vec3(0.0, 0.0, 1.0);
    vec3 keyHalf = normalize(keyLight + viewDir);
    float spec = pow(max(0.0, dot(normal, keyHalf)), isSelected ? 40.0 : 28.0) * (isSelected ? 1.0 : 0.75);
    float sheen = pow(max(0.0, dot(normal, keyHalf)), 8.0) * 0.25;
    float fresnel = pow(1.0 - normal.z, 2.0);
    vec3 rimGlow = mix(color.rgb, vec3(1.0), 0.35) * (fresnel * 0.65);
    float core = 1.0 - smoothstep(0.0, 0.92, r);
    vec3 innerGlow = color.rgb * (core * 0.32);
    vec3 ambient = color.rgb * 0.30;
    vec3 diffuse = color.rgb * (keyDiff * 0.58 + fillDiff);
    vec3 shaded = ambient + diffuse + innerGlow + rimGlow + vec3(1.0) * (spec + sheen);
    if (isSelected) {
      float centerHotspot = smoothstep(0.75, 0.0, r);
      shaded = mix(shaded, vec3(1.0, 0.98, 0.94), 0.5) + vec3(1.0) * (centerHotspot * 0.5) + rimGlow * 0.7;
    }
    float alpha = color.a * smoothstep(1.0, 0.90, r);
    gl_FragColor = vec4(shaded, alpha);
  }
}`;
    return { vertex, fragment };
  }

  /**
   * Compute HUD badge parameters (pill dimensions, category color, depth opacity)
   * for 3D projected screen records.
   *
   * @param {Object} candidate - Screen record { x, y, depth, item }
   * @param {string|null} selectedRecordId - Currently selected record ID.
   * @param {number} [canvasWidth=1000] - Canvas width for bounds-checking.
   * @returns {Object|null}
   */
  function ugiBFormatOrbitBadge(candidate, selectedRecordId, canvasWidth = 1000) {
    if (!candidate || !candidate.item || !candidate.item.record) return null;
    const rec = candidate.item.record;
    const isEvent = Boolean(candidate.item.event);
    const isSelected = Boolean(selectedRecordId && rec.id === selectedRecordId);
    const name = rec.name || rec.relation_type || "Event";
    const shortName = name.length > 24 ? `${name.slice(0, 21)}…` : name;

    let catColor = "#38bdf8";
    if (isEvent) {
      catColor = "#e879f9";
    } else {
      const type = rec.entity_type || "";
      if (/service|component/i.test(type)) catColor = "#ff523d";
      else if (/person/i.test(type)) catColor = "#b388ff";
    }

    const pillW = Math.max(68, Math.round(shortName.length * 7.5 + 28));
    const pillH = 22;
    const rawX = candidate.x || 0;
    const rawY = candidate.y || 0;
    const pillX = (rawX + 20 + pillW > canvasWidth - 12)
      ? Math.round(rawX - pillW - 20)
      : Math.round(rawX + 20);
    const pillY = Math.round(rawY - 11);
    const depth = typeof candidate.depth === "number" ? candidate.depth : 0.5;
    const depthOpacity = isSelected ? 1 : Math.max(0.45, Number((1 - depth * 0.55).toFixed(2)));

    return {
      isSelected,
      catColor,
      shortName,
      pillX,
      pillY,
      pillW,
      pillH,
      depthOpacity,
      cx: Math.round(rawX),
      cy: Math.round(rawY),
    };
  }

  // Export API
  const ugiBOrbitInteraction = {
    ugiBCheckWebGLSupport,
    ugiBOrbitFallbackHandler,
    ugiBPick3DRecord,
    ugiBSetViewMode,
    ugiBHandleOrbitKeyboard,
    ugiBGetVolumetricShaderSources,
    ugiBFormatOrbitBadge,
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = ugiBOrbitInteraction;
  } else {
    global.ugiBOrbitInteraction = ugiBOrbitInteraction;
    Object.assign(global, ugiBOrbitInteraction);
  }
})(typeof window !== "undefined" ? window : globalThis);

