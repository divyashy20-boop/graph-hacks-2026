/* particles.js -- cursor-reactive soft white dot matrix background
   - Soft white dots: rgba(255, 255, 255, alpha)
   - Visible resting opacity (0.35), brightens to 0.95 near cursor
   - Dense uniform 24px grid across viewport
   - Fluid interactive ripple radiating outward with cursor movement
   - Smooth elastic spring return to origin
   - Strictly excluded from evidence graph area
   - HiDPI / Retina crispness
   - Reduced-motion compliant
*/

(function () {
  'use strict';

  if (typeof window === 'undefined' || window.__ugiDotMatrixInitialized) return;
  window.__ugiDotMatrixInitialized = true;

  if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    return;
  }

  var canvas = document.getElementById('particle-bg');
  if (!canvas) {
    canvas = document.createElement('canvas');
    canvas.id = 'particle-bg';
    canvas.setAttribute('aria-hidden', 'true');
    document.body.prepend(canvas);
  }

  canvas.style.cssText = 'position:fixed!important;top:0!important;left:0!important;width:100vw!important;height:100vh!important;z-index:0!important;pointer-events:none!important;display:block!important;';

  var ctx = canvas.getContext('2d');
  if (!ctx) return;

  var SPACING = 24;          // 24px grid spacing
  var BASE_RADIUS = 1.25;    // Crisp, soft white dot radius
  var BASE_ALPHA = 0.35;     // Visible resting opacity
  var RIPPLE_RADIUS = 150;   // Cursor influence radius
  var RIPPLE_PUSH = 15;      // Ripple displacement distance
  var SPRING = 0.14;         // Return spring stiffness
  var DAMPING = 0.82;        // Motion damping

  var dpr = Math.min(window.devicePixelRatio || 1, 2);
  var width = window.innerWidth;
  var height = window.innerHeight;
  var dots = [];
  var graphRect = null;
  var lastRectCheck = 0;

  var mouse = { x: -9999, y: -9999 };

  function updateGraphBounds() {
    var el = document.querySelector('.panel--map') || document.querySelector('.graphwrap');
    if (el) {
      var r = el.getBoundingClientRect();
      graphRect = { left: r.left, top: r.top, right: r.right, bottom: r.bottom };
    } else {
      graphRect = null;
    }
  }

  function resize() {
    width = window.innerWidth;
    height = window.innerHeight;
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    dots = [];
    var cols = Math.ceil(width / SPACING) + 1;
    var rows = Math.ceil(height / SPACING) + 1;

    for (var r = 0; r < rows; r++) {
      for (var c = 0; c < cols; c++) {
        var ox = c * SPACING;
        var oy = r * SPACING;
        dots.push({
          ox: ox,
          oy: oy,
          x: ox,
          y: oy,
          vx: 0,
          vy: 0,
          alpha: BASE_ALPHA,
          radius: BASE_RADIUS
        });
      }
    }
    updateGraphBounds();
  }

  window.addEventListener('resize', resize, { passive: true });
  window.addEventListener('scroll', updateGraphBounds, { passive: true });

  window.addEventListener('mousemove', function (e) {
    mouse.x = e.clientX;
    mouse.y = e.clientY;
  }, { passive: true });

  window.addEventListener('touchmove', function (e) {
    if (e.touches && e.touches.length > 0) {
      mouse.x = e.touches[0].clientX;
      mouse.y = e.touches[0].clientY;
    }
  }, { passive: true });

  window.addEventListener('mouseleave', function () {
    mouse.x = -9999;
    mouse.y = -9999;
  });

  function render(time) {
    if (time - lastRectCheck > 1000) {
      updateGraphBounds();
      lastRectCheck = time;
    }

    ctx.clearRect(0, 0, width, height);

    var mx = mouse.x;
    var my = mouse.y;
    var len = dots.length;

    for (var i = 0; i < len; i++) {
      var d = dots[i];

      // Exclude dots inside evidence graph window
      if (graphRect &&
          d.ox >= graphRect.left && d.ox <= graphRect.right &&
          d.oy >= graphRect.top && d.oy <= graphRect.bottom) {
        continue;
      }

      var dx = d.ox - mx;
      var dy = d.oy - my;
      var dist = Math.sqrt(dx * dx + dy * dy);

      var targetX = d.ox;
      var targetY = d.oy;
      var targetAlpha = BASE_ALPHA;
      var targetRadius = BASE_RADIUS;

      // Subtle organic idle wave
      var idle = Math.sin(d.ox * 0.015 + time * 0.001) * Math.cos(d.oy * 0.015 + time * 0.001) * 0.7;
      targetX += idle;
      targetY += idle;

      if (dist < RIPPLE_RADIUS && dist > 0.1) {
        var norm = dist / RIPPLE_RADIUS;
        var wave = Math.sin(norm * Math.PI);
        var push = wave * RIPPLE_PUSH;
        targetX += (dx / dist) * push;
        targetY += (dy / dist) * push;

        var highlight = Math.pow(1 - norm, 1.4);
        targetAlpha = BASE_ALPHA + highlight * 0.62; // Up to ~0.97
        targetRadius = BASE_RADIUS + highlight * 1.1; // Up to ~2.35px
      }

      // Spring physics
      var ax = (targetX - d.x) * SPRING;
      var ay = (targetY - d.y) * SPRING;
      d.vx = (d.vx + ax) * DAMPING;
      d.vy = (d.vy + ay) * DAMPING;
      d.x += d.vx;
      d.y += d.vy;

      d.alpha += (targetAlpha - d.alpha) * 0.2;
      d.radius += (targetRadius - d.radius) * 0.2;

      // Draw soft white dot
      ctx.beginPath();
      ctx.arc(d.x, d.y, d.radius, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(255, 255, 255, ' + d.alpha.toFixed(3) + ')';
      ctx.fill();
    }

    requestAnimationFrame(render);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      resize();
      requestAnimationFrame(render);
    });
  } else {
    resize();
    requestAnimationFrame(render);
  }
})();
