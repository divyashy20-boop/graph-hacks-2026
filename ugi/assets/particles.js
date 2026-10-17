/* particles.js -- cursor-reactive dot field background v2 */
(function () {
  'use strict';
  var reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduced) return;

  /* canvas -- fixed, full viewport, pointer-events none */
  var canvas = document.createElement('canvas');
  canvas.id = 'particle-bg';
  canvas.setAttribute('aria-hidden', 'true');
  canvas.style.cssText = 'position:fixed;inset:0;z-index:0;pointer-events:none;width:100%;height:100%;display:block';
  document.body.prepend(canvas);
  var ctx = canvas.getContext('2d');

  var CFG = {
    count:        220,
    baseRadius:   2.2,
    baseOpacity:  0.55,
    speed:        0.28,
    rippleRadius: 150,
    rippleForce:  0.07,
    returnSpeed:  0.04,
    glow:         8,
    colorA: { r: 103, g: 167, b: 200 },
    colorB: { r: 141, g: 130, b: 180 },
    colorC: { r: 207, g: 102, b: 76 }
  };
  var COLORS = [CFG.colorA, CFG.colorB, CFG.colorC];

  var mx = -9999, my = -9999;
  window.addEventListener('mousemove', function(e) { mx = e.clientX; my = e.clientY; }, { passive: true });
  window.addEventListener('touchmove', function(e) { if (e.touches.length) { mx = e.touches[0].clientX; my = e.touches[0].clientY; } }, { passive: true });
  window.addEventListener('mouseleave', function() { mx = -9999; my = -9999; });

  function Particle(W, H) { this.reset(W, H); }
  Particle.prototype.reset = function(W, H) {
    this.ox = Math.random() * W; this.oy = Math.random() * H;
    this.x = this.ox; this.y = this.oy; this.dx = 0; this.dy = 0;
    var c = COLORS[Math.floor(Math.random() * COLORS.length)];
    this.r = c.r; this.g = c.g; this.b = c.b;
    this.radius  = CFG.baseRadius * (0.5 + Math.random() * 1.0);
    this.opacity = CFG.baseOpacity * (0.6 + Math.random() * 0.7);
    var angle = Math.random() * Math.PI * 2;
    var spd   = CFG.speed * (0.3 + Math.random() * 0.9);
    this.vx = Math.cos(angle) * spd; this.vy = Math.sin(angle) * spd;
  };
  Particle.prototype.update = function(W, H) {
    this.ox += this.vx; this.oy += this.vy;
    if (this.ox < -10) this.ox = W + 10;
    if (this.ox > W + 10) this.ox = -10;
    if (this.oy < -10) this.oy = H + 10;
    if (this.oy > H + 10) this.oy = -10;
    var cdx = this.ox - mx, cdy = this.oy - my;
    var dist = Math.sqrt(cdx * cdx + cdy * cdy);
    if (dist < CFG.rippleRadius && dist > 0.5) {
      var f = (CFG.rippleRadius - dist) / CFG.rippleRadius;
      this.dx += (cdx / dist) * f * f * CFG.rippleForce * 20;
      this.dy += (cdy / dist) * f * f * CFG.rippleForce * 20;
    }
    this.dx *= (1 - CFG.returnSpeed); this.dy *= (1 - CFG.returnSpeed);
    var dlen = Math.sqrt(this.dx * this.dx + this.dy * this.dy);
    if (dlen > 55) { this.dx = this.dx / dlen * 55; this.dy = this.dy / dlen * 55; }
    this.x = this.ox + this.dx; this.y = this.oy + this.dy;
  };
  Particle.prototype.draw = function() {
    var col = 'rgba(' + this.r + ',' + this.g + ',' + this.b + ',';
    ctx.shadowBlur  = CFG.glow;
    ctx.shadowColor = 'rgba(' + this.r + ',' + this.g + ',' + this.b + ',0.5)';
    ctx.beginPath();
    ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
    ctx.fillStyle = col + this.opacity + ')';
    ctx.fill();
    ctx.shadowBlur = 0;
  };

  var W = 0, H = 0, particles = [];
  function resize() {
    W = canvas.width  = window.innerWidth;
    H = canvas.height = window.innerHeight;
    particles = [];
    for (var i = 0; i < CFG.count; i++) particles.push(new Particle(W, H));
  }
  window.addEventListener('resize', resize, { passive: true });
  window.addEventListener('DOMContentLoaded', resize);
  resize();

  function loop() {
    ctx.clearRect(0, 0, W, H);
    for (var i = 0; i < particles.length; i++) {
      particles[i].update(W, H); particles[i].draw();
    }
    requestAnimationFrame(loop);
  }
  requestAnimationFrame(loop);
})();
