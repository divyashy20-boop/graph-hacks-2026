/* particles.js -- cursor-reactive dot matrix background
   Matches the subtle, high-density interactive dot matrix design
   seen on modern developer tools like the Antigravity IDE download page.
   - Dense uniform dot matrix across the viewport
   - Small, crisp, low-opacity dots (1px base radius)
   - Dynamic ripple effect radiating from cursor movement
   - Smooth spring dampening returning dots to resting state
   - Strictly excludes the evidence graph window
   - HiDPI/Retina display support
   - Respects prefers-reduced-motion
*/

(function () {
  'use strict';

  var reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduced) return;

  var canvas = document.createElement('canvas');
  canvas.id = 'particle-bg';
  canvas.setAttribute('aria-hidden', 'true');
  canvas.style.cssText = 'position:fixed;inset:0;z-index:0;pointer-events:none;width:100vw;height:100vh;display:block;';
  document.body.prepend(canvas);

  var ctx = canvas.getContext('2d');
  if (!ctx) return;

  var CONFIG = {
    spacing: 26,            // Distance between dot grid points (px)
    baseRadius: 1.0,        // Tiny, crisp dot radius
    baseAlpha: 0.16,        // Low resting opacity
    color: { r: 120, g: 170, b: 215 }, // Tech slate-cyan
    hoverColor: { r: 165, g: 220, b: 255 }, // Glowing cyan-white near cursor
    rippleRadius: 145,      // Influence radius around cursor
    ripplePush: 11,         // Maximum displacement distance (px)
    spring: 0.14,           // Return stiffness
    friction: 0.82          // Damping factor
  };

  var dpr = Math.min(window.devicePixelRatio || 1, 2);
  var width = 0;
  var height = 0;
  var dots = [];
  var graphRect = null;
  var lastRectCheck = 0;

  var mouse = {
    x: -9999,
    y: -9999,
    targetX: -9999,
    targetY: -9999,
    active: false
  };

  function updateGraphBounds() {
    var graphEl = document.querySelector('.panel--map') || document.querySelector('.graphwrap');
    if (graphEl) {
      var r = graphEl.getBoundingClientRect();
      graphRect = {
        left: r.left,
        top: r.top,
        right: r.right,
        bottom: r.bottom
      };
    } else {
      graphRect = null;
    }
  }

  function Dot(ox, oy) {
    this.ox = ox;
    this.oy = oy;
    this.x = ox;
    this.y = oy;
    this.vx = 0;
    this.vy = 0;
    this.alpha = CONFIG.baseAlpha;
    this.targetAlpha = CONFIG.baseAlpha;
    this.radius = CONFIG.baseRadius;
  }

  Dot.prototype.update = function (now) {
    var dx = this.ox - mouse.x;
    var dy = this.oy - mouse.y;
    var dist = Math.sqrt(dx * dx + dy * dy);

    var targetX = this.ox;
    var targetY = this.oy;
    this.targetAlpha = CONFIG.baseAlpha;

    // Gentle ambient idle wave
    var idle = Math.sin(this.ox * 0.012 + now * 0.0009) * Math.cos(this.oy * 0.012 + now * 0.0009) * 0.7;
    targetX += idle;
    targetY += idle;

    if (dist < CONFIG.rippleRadius && dist > 0.1) {
      var norm = dist / CONFIG.rippleRadius; // 0 (cursor) to 1 (outer edge)
      // Ripple wave profile
      var wave = Math.sin(norm * Math.PI);
      var push = wave * CONFIG.ripplePush;
      targetX += (dx / dist) * push;
      targetY += (dy / dist) * push;

      var highlight = Math.pow(1 - norm, 1.5);
      this.targetAlpha = CONFIG.baseAlpha + highlight * 0.58;
      this.radius = CONFIG.baseRadius + highlight * 0.75;
    } else {
      this.radius = CONFIG.baseRadius;
    }

    // Spring physics towards target
    var ax = (targetX - this.x) * CONFIG.spring;
    var ay = (targetY - this.y) * CONFIG.spring;
    this.vx = (this.vx + ax) * CONFIG.friction;
    this.vy = (this.vy + ay) * CONFIG.friction;
    this.x += this.vx;
    this.y += this.vy;

    // Smooth opacity transition
    this.alpha += (this.targetAlpha - this.alpha) * 0.18;
  };

  function initGrid() {
    width = window.innerWidth;
    height = window.innerHeight;
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    dots = [];
    var cols = Math.ceil(width / CONFIG.spacing) + 1;
    var rows = Math.ceil(height / CONFIG.spacing) + 1;

    for (var r = 0; r < rows; r++) {
      for (var c = 0; c < cols; c++) {
        var ox = c * CONFIG.spacing;
        var oy = r * CONFIG.spacing;
        dots.push(new Dot(ox, oy));
      }
    }
    updateGraphBounds();
  }

  window.addEventListener('resize', initGrid, { passive: true });
  window.addEventListener('scroll', updateGraphBounds, { passive: true });

  window.addEventListener('mousemove', function (e) {
    mouse.x = e.clientX;
    mouse.y = e.clientY;
    mouse.active = true;
  }, { passive: true });

  window.addEventListener('touchmove', function (e) {
    if (e.touches.length) {
      mouse.x = e.touches[0].clientX;
      mouse.y = e.touches[0].clientY;
      mouse.active = true;
    }
  }, { passive: true });

  window.addEventListener('mouseleave', function () {
    mouse.x = -9999;
    mouse.y = -9999;
    mouse.active = false;
  });

  function render(now) {
    // Periodically refresh graph bounds to handle resize / dynamic panels
    if (now - lastRectCheck > 1000) {
      updateGraphBounds();
      lastRectCheck = now;
    }

    ctx.clearRect(0, 0, width, height);

    var len = dots.length;
    var baseCol = CONFIG.color;
    var hovCol = CONFIG.hoverColor;

    for (var i = 0; i < len; i++) {
      var d = dots[i];
      d.update(now);

      // STRICT EXCLUSION: Never draw dots inside the graph window
      if (graphRect &&
          d.x >= graphRect.left && d.x <= graphRect.right &&
          d.y >= graphRect.top && d.y <= graphRect.bottom) {
        continue;
      }

      var a = d.alpha;
      if (a < 0.01) continue;

      var isHot = a > 0.32;
      var c = isHot ? hovCol : baseCol;

      ctx.beginPath();
      ctx.arc(d.x, d.y, d.radius, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(' + c.r + ',' + c.g + ',' + c.b + ',' + a.toFixed(3) + ')';
      ctx.fill();
    }

    requestAnimationFrame(render);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      initGrid();
      requestAnimationFrame(render);
    });
  } else {
    initGrid();
    requestAnimationFrame(render);
  }
})();
