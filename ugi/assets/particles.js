/* particles.js -- cursor-reactive dot field background */
(function () {
  'use strict';
  var reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduced) return;
  var canvas = document.createElement('canvas');
  canvas.id = 'particle-bg';
  canvas.setAttribute('aria-hidden', 'true');
  document.body.prepend(canvas);
  var ctx = canvas.getContext('2d');
  var CFG = { count: 160, baseRadius: 1.4, baseOpacity: 0.18, speed: 0.22,
    rippleRadius: 130, rippleForce: 0.055, returnSpeed: 0.032,
    colorA: { r: 103, g: 167, b: 200 },
    colorB: { r: 141, g: 130, b: 180 },
    colorC: { r: 207, g: 102, b: 76 } };
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
    this.radius  = CFG.baseRadius * (0.6 + Math.random() * 0.8);
    this.opacity = CFG.baseOpacity * (0.5 + Math.random() * 0.8);
    var angle = Math.random() * Math.PI * 2;
    var spd   = CFG.speed * (0.3 + Math.random());
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
      var force = (CFG.rippleRadius - dist) / CFG.rippleRadius;
      this.dx += (cdx / dist) * force * force * CFG.rippleForce * 18;
      this.dy += (cdy / dist) * force * force * CFG.rippleForce * 18;
    }
    this.dx *= (1 - CFG.returnSpeed); this.dy *= (1 - CFG.returnSpeed);
    var dlen = Math.sqrt(this.dx * this.dx + this.dy * this.dy);
    if (dlen > 50) { this.dx = (this.dx / dlen) * 50; this.dy = (this.dy / dlen) * 50; }
    this.x = this.ox + this.dx; this.y = this.oy + this.dy;
  };
  Particle.prototype.draw = function() {
    ctx.beginPath();
    ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(' + this.r + ',' + this.g + ',' + this.b + ',' + this.opacity + ')';
    ctx.fill();
  };
  var W = 0, H = 0, particles = [];
  function resize() {
    W = canvas.width  = window.innerWidth;
    H = canvas.height = window.innerHeight;
    particles = [];
    for (var i = 0; i < CFG.count; i++) particles.push(new Particle(W, H));
  }
  window.addEventListener('resize', resize, { passive: true });
  resize();
  function loop() {
    ctx.clearRect(0, 0, W, H);
    for (var i = 0; i < particles.length; i++) { particles[i].update(W, H); particles[i].draw(); }
    requestAnimationFrame(loop);
  }
  loop();
})();
