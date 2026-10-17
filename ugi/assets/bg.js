/* === UGI BACKGROUND SYSTEM bg.js === */
/* Vanilla JS canvas: sparse graph network with copper tracer, behind hero right side */
(function ugiBackground() {
  'use strict';
  window.ugiBgLoaded = true;

  var CFG = {
    nodeCount: 22,
    nodeRadiusMin: 1.5,
    nodeRadiusMax: 3.2,
    edgeOpacity: 0.10,
    nodeOpacity: 0.14,
    nodeBrightOpacity: 0.32,
    brightNodeCount: 4,
    tracerCycleSecs: 11,
    tracerGlow: 0.45,
    driftPx: 3.5,
    driftSpeedSecs: 20,
    blue: '103,167,200',
    copper: '207,102,76',
    fps: 40
  };

  var canvas = document.getElementById('ugi-bg-canvas');
  if (!canvas) return;
  var ctx = canvas.getContext('2d');
  var hidden = false;
  var rafId = null;
  var mql = window.matchMedia('(prefers-reduced-motion: reduce)');
  var PRM = mql.matches;

  function resize() {
    var dpr = window.devicePixelRatio || 1;
    var w = window.innerWidth;
    var h = window.innerHeight;
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return { w: w, h: h };
  }

  function buildNodes(w, h) {
    var nodes = [];
    var cx = Math.max(w * 0.65, Math.min(w * 0.82, w * 0.76));
    var cy = Math.max(120, Math.min(260, h * 0.25));

    // Anchor 2-3 nodes near the sphere perimeter so edges visibly connect into the sphere area
    nodes.push({ bx: cx - 24, by: cy - 14, x: cx - 24, y: cy - 14, r: 2.8, bright: true, driftAngle: 0.4, driftSpeed: 0.03 });
    nodes.push({ bx: cx + 28, by: cy + 18, x: cx + 28, y: cy + 18, r: 2.5, bright: false, driftAngle: 1.2, driftSpeed: 0.04 });
    nodes.push({ bx: cx - 8,  by: cy + 34, x: cx - 8,  by: cy + 34, r: 3.0, bright: true, driftAngle: 2.1, driftSpeed: 0.035 });

    for (var i = 3; i < CFG.nodeCount; i++) {
      var angle = Math.random() * Math.PI * 2;
      var dist = 45 + Math.random() * Math.min(w * 0.22, 230);
      var x = cx + Math.cos(angle) * dist * (0.6 + Math.random() * 0.8);
      var y = cy + Math.sin(angle) * dist * (0.5 + Math.random() * 0.7);

      x = Math.max(w * 0.48, Math.min(w * 0.96, x));
      y = Math.max(25, Math.min(Math.max(380, h * 0.55), y));

      var isBright = i < (3 + CFG.brightNodeCount);
      var r = CFG.nodeRadiusMin + Math.random() * (CFG.nodeRadiusMax - CFG.nodeRadiusMin);
      nodes.push({
        bx: x,
        by: y,
        x: x,
        y: y,
        r: r,
        bright: isBright,
        driftAngle: Math.random() * Math.PI * 2,
        driftSpeed: (0.5 + Math.random() * 0.8) / CFG.driftSpeedSecs
      });
    }
    return nodes;
  }

  function buildEdges(nodes, maxDist) {
    var edges = [];
    for (var i = 0; i < nodes.length; i++) {
      for (var j = i + 1; j < nodes.length; j++) {
        var dx = nodes[i].bx - nodes[j].bx;
        var dy = nodes[i].by - nodes[j].by;
        var d = Math.sqrt(dx * dx + dy * dy);
        if (d < maxDist) {
          edges.push({ a: i, b: j, len: d });
        }
      }
    }
    edges.sort(function(a, b) { return a.len - b.len; });
    return edges.slice(0, 32);
  }

  function buildTracer(nodes, edges) {
    if (!edges.length) return [];
    var path = [0];
    var used = { 0: true };
    for (var step = 0; step < nodes.length; step++) {
      var cur = path[path.length - 1];
      var best = -1;
      var bestLen = Infinity;
      for (var e = 0; e < edges.length; e++) {
        var other = -1;
        if (edges[e].a === cur && !used[edges[e].b]) other = edges[e].b;
        if (edges[e].b === cur && !used[edges[e].a]) other = edges[e].a;
        if (other >= 0 && edges[e].len < bestLen) {
          bestLen = edges[e].len;
          best = other;
        }
      }
      if (best < 0) break;
      path.push(best);
      used[best] = true;
    }
    return path.length >= 3 ? path.slice(0, Math.min(10, path.length)) : path;
  }

  var dim = { w: 0, h: 0 };
  var nodes = [];
  var edges = [];
  var tracer = [];
  var tStart = null;

  function init() {
    dim = resize();
    nodes = buildNodes(dim.w, dim.h);
    edges = buildEdges(nodes, Math.min(dim.w * 0.20, 185));
    tracer = buildTracer(nodes, edges);
  }

  function draw(ts) {
    if (tStart === null) tStart = ts;
    var elapsed = (ts - tStart) / 1000;
    ctx.clearRect(0, 0, dim.w, dim.h);

    if (!PRM) {
      for (var i = 0; i < nodes.length; i++) {
        var n = nodes[i];
        var phase = elapsed * n.driftSpeed * Math.PI * 2;
        n.x = n.bx + Math.cos(n.driftAngle + phase) * CFG.driftPx;
        n.y = n.by + Math.sin(n.driftAngle + phase * 0.7) * CFG.driftPx;
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

      var g = ctx.createRadialGradient(tx, ty, 0, tx, ty, 10);
      g.addColorStop(0, 'rgba(' + CFG.copper + ',' + CFG.tracerGlow + ')');
      g.addColorStop(1, 'rgba(' + CFG.copper + ',0)');
      ctx.beginPath();
      ctx.arc(tx, ty, 10, 0, Math.PI * 2);
      ctx.fillStyle = g;
      ctx.fill();

      ctx.beginPath();
      ctx.arc(tx, ty, 2.6, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(' + CFG.copper + ',0.92)';
      ctx.fill();
    }
  }

  var lastTs = 0;
  var minGap = 1000 / CFG.fps;
  function loop(ts) {
    if (hidden || PRM) return;
    rafId = requestAnimationFrame(loop);
    if (ts - lastTs < minGap) return;
    lastTs = ts;
    draw(ts);
  }

  function onMotionChange(e) {
    PRM = e.matches;
    if (rafId) {
      cancelAnimationFrame(rafId);
      rafId = null;
    }
    if (PRM) {
      draw(0);
    } else {
      tStart = null;
      rafId = requestAnimationFrame(loop);
    }
  }

  if (mql.addEventListener) {
    mql.addEventListener('change', onMotionChange);
  } else if (mql.addListener) {
    mql.addListener(onMotionChange);
  }

  document.addEventListener('visibilitychange', function() {
    hidden = document.hidden;
    if (!hidden && !PRM) {
      rafId = requestAnimationFrame(loop);
    }
  });

  var rTimer;
  window.addEventListener('resize', function() {
    clearTimeout(rTimer);
    rTimer = setTimeout(function() {
      if (rafId) cancelAnimationFrame(rafId);
      init();
      if (PRM) {
        draw(0);
      } else {
        tStart = null;
        rafId = requestAnimationFrame(loop);
      }
    }, 150);
  });

  init();
  if (PRM) {
    draw(0);
  } else {
    rafId = requestAnimationFrame(loop);
  }
})();