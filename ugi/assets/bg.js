/* === UGI HERO VISUAL GRAPH & TRACER bg.js === */
/* Bound to .hero-art, local coordinate system, ResizeObserver & IntersectionObserver */
(function ugiHeroVisual() {
  'use strict';
  window.ugiBgLoaded = true;

  var CFG = {
    nodeCount: 22,
    nodeRadiusMin: 1.6,
    nodeRadiusMax: 3.2,
    edgeOpacity: 0.12,
    nodeOpacity: 0.16,
    nodeBrightOpacity: 0.36,
    brightNodeCount: 4,
    tracerCycleSecs: 11,
    tracerGlow: 0.50,
    driftPx: 2.5,
    driftSpeedSecs: 20,
    blue: '103,167,200',
    copper: '207,102,76',
    fps: 40
  };

  var wrapper = document.querySelector('.hero-visual');
  var art = document.querySelector('.hero-art') || document.querySelector('.hero-visual-stage');
  var canvas = document.getElementById('hero-graph-canvas');
  if (!canvas || !wrapper || !art) return;

  var ctx = canvas.getContext('2d');
  var hidden = document.hidden;
  var isIntersecting = true;
  var rafId = null;
  var lastTs = 0;
  var tStart = null;
  var mql = window.matchMedia('(prefers-reduced-motion: reduce)');
  var PRM = mql.matches;

  var dim = { w: 0, h: 0 };
  var nodes = [];
  var edges = [];
  var tracer = [];

  function resize() {
    var dpr = window.devicePixelRatio || 1;
    var w = art.offsetWidth || wrapper.clientWidth || 540;
    var h = art.offsetHeight || wrapper.clientHeight || 320;

    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return { w: w, h: h };
  }

  function buildNodes(w, h) {
    var nodeList = [];
    var cx = w * 0.50;
    var cy = h * 0.46;

    var core = art.querySelector('.sculpture-core');
    var artRect = art.getBoundingClientRect();
    var currentScale = artRect.width / (art.offsetWidth || w || 1);
    if (currentScale <= 0) currentScale = 1;

    if (core) {
      var coreRect = core.getBoundingClientRect();
      cx = (coreRect.left + coreRect.width / 2 - artRect.left) / currentScale;
      cy = (coreRect.top + coreRect.height / 2 - artRect.top) / currentScale;
    }

    // Anchor node for "CLAIM → ENTITY" leader line (scaled to match unscaled text screen pos)
    var line = document.querySelector('.sculpture-ann--rel .ann-line');
    var anchorX = w * 0.28;
    var anchorY = h * 0.25;
    if (line) {
      var lineRect = line.getBoundingClientRect();
      anchorX = (lineRect.right - artRect.left) / currentScale;
      anchorY = (lineRect.top + lineRect.height / 2 - artRect.top) / currentScale;
    }

    // Node 0: precisely anchored to leader line tip, no drift
    nodeList.push({
      bx: anchorX, by: anchorY, x: anchorX, y: anchorY,
      r: 3.2, bright: true, driftAngle: 0, driftSpeed: 0
    });

    // Close perimeter nodes around the sphere
    nodeList.push({ bx: cx + 30, by: cy - 22, x: cx + 30, y: cy - 22, r: 2.6, bright: false, driftAngle: 1.2, driftSpeed: 0.035 });
    nodeList.push({ bx: cx + 36, by: cy + 16, x: cx + 36, y: cy + 16, r: 2.8, bright: true,  driftAngle: 2.5, driftSpeed: 0.03 });
    nodeList.push({ bx: cx - 32, by: cy - 16, x: cx - 32, y: cy - 16, r: 2.4, bright: false, driftAngle: 3.1, driftSpeed: 0.04 });

    // Radiate 360° around sphere
    var minX = w * 0.06;
    var maxX = w * 0.94;
    var minY = h * 0.06;
    var maxY = h * 0.90;

    var directionalAngles = [
      -Math.PI * 0.85, -Math.PI * 0.68, -Math.PI * 0.50, -Math.PI * 0.35, -Math.PI * 0.18,
      0, Math.PI * 0.14, Math.PI * 0.28, Math.PI * 0.45, Math.PI * 0.58,
      Math.PI * 0.85, -Math.PI * 0.95, -Math.PI * 0.55, -Math.PI * 0.25, 0.08,
      Math.PI * 0.22, -Math.PI * 0.42, -Math.PI * 0.72
    ];

    for (var i = 0; i < directionalAngles.length && nodeList.length < CFG.nodeCount; i++) {
      var baseAng = directionalAngles[i];
      var ang = baseAng + (Math.random() - 0.5) * 0.22;
      var dist = 40 + Math.pow(Math.random(), 1.2) * (Math.min(w, h) * 0.46);
      var nx = cx + Math.cos(ang) * dist;
      var ny = cy + Math.sin(ang) * (dist * 0.70);

      nx = Math.max(minX, Math.min(maxX, nx));
      ny = Math.max(minY, Math.min(maxY, ny));

      var isBright = nodeList.length < (1 + CFG.brightNodeCount);
      var r = CFG.nodeRadiusMin + Math.random() * (CFG.nodeRadiusMax - CFG.nodeRadiusMin);
      nodeList.push({
        bx: nx, by: ny, x: nx, y: ny, r: r,
        bright: isBright,
        driftAngle: Math.random() * Math.PI * 2,
        driftSpeed: (0.4 + Math.random() * 0.7) / CFG.driftSpeedSecs
      });
    }

    return nodeList;
  }

  function buildEdges(nodeList, maxDist) {
    var edgeList = [];
    for (var i = 0; i < nodeList.length; i++) {
      for (var j = i + 1; j < nodeList.length; j++) {
        var dx = nodeList[i].bx - nodeList[j].bx;
        var dy = nodeList[i].by - nodeList[j].by;
        var d = Math.sqrt(dx * dx + dy * dy);
        if (d < maxDist) {
          edgeList.push({ a: i, b: j, len: d });
        }
      }
    }
    edgeList.sort(function(a, b) { return a.len - b.len; });
    return edgeList.slice(0, 32);
  }

  function buildTracer(nodeList, edgeList) {
    if (!edgeList.length) return [];
    var path = [0];
    var used = { 0: true };
    for (var step = 0; step < nodeList.length; step++) {
      var cur = path[path.length - 1];
      var best = -1;
      var bestLen = Infinity;
      for (var e = 0; e < edgeList.length; e++) {
        var other = -1;
        if (edgeList[e].a === cur && !used[edgeList[e].b]) other = edgeList[e].b;
        if (edgeList[e].b === cur && !used[edgeList[e].a]) other = edgeList[e].a;
        if (other >= 0 && edgeList[e].len < bestLen) {
          bestLen = edgeList[e].len;
          best = other;
        }
      }
      if (best < 0) break;
      path.push(best);
      used[best] = true;
    }
    return path.length >= 3 ? path.slice(0, Math.min(10, path.length)) : path;
  }

  function init() {
    dim = resize();
    nodes = buildNodes(dim.w, dim.h);
    edges = buildEdges(nodes, Math.min(dim.w * 0.36, 135));
    tracer = buildTracer(nodes, edges);
  }

  function draw(ts) {
    if (tStart === null) tStart = ts;
    var elapsed = (ts - tStart) / 1000;
    ctx.clearRect(0, 0, dim.w, dim.h);

    if (!PRM) {
      for (var i = 0; i < nodes.length; i++) {
        var n = nodes[i];
        if (n.driftSpeed > 0) {
          var phase = elapsed * n.driftSpeed * Math.PI * 2;
          n.x = n.bx + Math.cos(n.driftAngle + phase) * CFG.driftPx;
          n.y = n.by + Math.sin(n.driftAngle + phase * 0.7) * CFG.driftPx;
        }
      }
    }

    ctx.lineWidth = 0.85;
    for (var e = 0; e < edges.length; e++) {
      var na = nodes[edges[e].a];
      var nb = nodes[edges[e].b];
      ctx.strokeStyle = 'rgba(' + CFG.blue + ',' + CFG.edgeOpacity + ')';
      ctx.beginPath();
      ctx.moveTo(na.x, na.y);
      ctx.lineTo(nb.x, nb.y);
      ctx.stroke();
    }

    for (var ni = 0; ni < nodes.length; ni++) {
      var nd = nodes[ni];
      ctx.beginPath();
      ctx.arc(nd.x, nd.y, nd.r, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(' + (nd.bright ? CFG.copper : CFG.blue) + ',' + (nd.bright ? CFG.nodeBrightOpacity : CFG.nodeOpacity) + ')';
      ctx.fill();
    }

    if (tracer.length >= 2) {
      var t = PRM ? 0.35 : (elapsed % CFG.tracerCycleSecs) / CFG.tracerCycleSecs;
      var segCount = tracer.length - 1;
      var segTime = t * segCount;
      var segIdx = Math.min(Math.floor(segTime), segCount - 1);
      var segFrac = segTime - segIdx;

      var nodeA = nodes[tracer[segIdx]];
      var nodeB = nodes[tracer[segIdx + 1]];
      var tx = nodeA.x + (nodeB.x - nodeA.x) * segFrac;
      var ty = nodeA.y + (nodeB.y - nodeA.y) * segFrac;

      var glowGrad = ctx.createRadialGradient(tx, ty, 0, tx, ty, 11);
      glowGrad.addColorStop(0, 'rgba(' + CFG.copper + ',' + CFG.tracerGlow + ')');
      glowGrad.addColorStop(1, 'rgba(' + CFG.copper + ',0)');
      ctx.beginPath();
      ctx.arc(tx, ty, 11, 0, Math.PI * 2);
      ctx.fillStyle = glowGrad;
      ctx.fill();

      ctx.beginPath();
      ctx.arc(tx, ty, 2.6, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(' + CFG.copper + ',0.95)';
      ctx.fill();
    }
  }

  function loop(ts) {
    if (hidden || !isIntersecting || PRM) {
      rafId = null;
      return;
    }
    rafId = requestAnimationFrame(loop);
    if (ts - lastTs < 25) return;
    lastTs = ts;
    draw(ts);
  }

  function startAnimation() {
    if (rafId) return;
    if (!hidden && isIntersecting && !PRM) {
      tStart = null;
      rafId = requestAnimationFrame(loop);
    }
  }

  function stopAnimation() {
    if (rafId) {
      cancelAnimationFrame(rafId);
      rafId = null;
    }
  }

  function onMotionChange(e) {
    PRM = e.matches;
    stopAnimation();
    if (PRM) {
      draw(0);
    } else {
      startAnimation();
    }
  }

  if (mql.addEventListener) {
    mql.addEventListener('change', onMotionChange);
  }

  document.addEventListener('visibilitychange', function() {
    hidden = document.hidden;
    if (hidden) {
      stopAnimation();
    } else {
      startAnimation();
    }
  });

  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function(entries) {
      for (var i = 0; i < entries.length; i++) {
        if (entries[i].target === wrapper) {
          isIntersecting = entries[i].isIntersecting;
          if (isIntersecting) {
            startAnimation();
          } else {
            stopAnimation();
          }
        }
      }
    }, { threshold: 0.05 });
    io.observe(wrapper);
  }

  var resizeTimeout;
  function handleResize() {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(function() {
      stopAnimation();
      init();
      if (PRM) {
        draw(0);
      } else {
        startAnimation();
      }
    }, 120);
  }

  if ('ResizeObserver' in window) {
    var ro = new ResizeObserver(handleResize);
    ro.observe(wrapper);
  } else {
    window.addEventListener('resize', handleResize);
  }

  init();
  if (PRM) {
    draw(0);
  } else {
    startAnimation();
  }
})();