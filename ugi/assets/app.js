const $ = (id) => document.getElementById(id);

let graphData = {entities: [], claims: [], events: []};
let positions = new Map();
let view = [0, 0, 1100, 500];
let baseView = [0, 0, 1100, 500];
let selectedRecordId = null;
let queryHighlights = new Set();
let caseKey = null;
let loadEpoch = 0;
let viewMode = "2d";
let orbit = null;

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function show(id, value) {
  $(id).textContent = JSON.stringify(value, null, 2);
}

async function api(path, body) {
  const headers = {"X-Dataset": $("dataset").value.trim(), "X-API-Key": $("access").value};
  if (body && !(body instanceof FormData)) headers["Content-Type"] = "application/json";
  const response = await fetch(path, {
    method: body ? "POST" : "GET",
    headers,
    body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
  });
  // Gateways sometimes reply with HTML rather than API JSON.
  const raw = await response.text();
  let data;
  try {
    data = JSON.parse(raw);
  } catch (_) {
    throw Error(`Backend returned a non-JSON response (HTTP ${response.status}). Check gateway routing.`);
  }
  if (!response.ok) {
    throw Error(typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail || `HTTP ${response.status}`));
  }
  return data;
}

async function busy(button, status, work) {
  $(button).disabled = true;
  $(status).classList.remove("error");
  $(status).textContent = "Working…";
  try {
    const message = await work();
    $(status).textContent = message || "Complete";
  } catch (error) {
    $(status).textContent = error.message;
    $(status).classList.add("error");
    if (status === "globalstatus") setGraphState("error", error.message);
  } finally {
    $(button).disabled = false;
  }
}

function setGraphState(kind, message = "") {
  const state = $("graphstate");
  if (!kind) { state.hidden = true; return; }
  state.hidden = false;
  $("graphstatekicker").textContent = kind === "error" ? "Unable to load evidence map" : "Loading evidence map";
  $("graphstatetext").textContent = message || (kind === "error" ? "Check the connection or dataset, then try again." : "Retrieving graph-backed records.");
  $("retrygraph").hidden = kind !== "error";
}

function field(parent, label, value) {
  if (value === undefined || value === null || value === "") return;
  const row = element("div", undefined, "field");
  row.append(element("b", label), element("span", String(value)));
  parent.append(row);
}

function metric(label, value) {
  const item = element("div");
  item.append(element("b", label), element("span", value === undefined || value === null || value === "" ? "—" : String(value)));
  return item;
}

function storySection(title, detail) {
  const section = element("section", undefined, "story-section");
  const heading = element("div", undefined, "story-heading");
  heading.append(element("span", title));
  if (detail) heading.append(element("span", detail));
  section.append(heading);
  return section;
}

function statusTone(status) {
  if (status === "CONTRADICTED" || status === "SOURCE_NEGATED") return "var(--red)";
  if (status === "UNKNOWN" || status === "HYPOTHESIS" || status === "CONNECTED_ONLY") return "var(--amber)";
  return "var(--signal)";
}

function statusTitle(status) {
  return ({SOURCE_ASSERTED: "Direct source assertion", RULE_DERIVED: "Rule-derived conclusion", CONNECTED_ONLY: "Connection is not enough", SOURCE_NEGATED: "Source negates the relation", CONTRADICTED: "Source evidence conflicts", HYPOTHESIS: "Stored risk hypothesis", UNKNOWN: "No supported conclusion"})[status] || status.replaceAll("_", " ");
}

function recordById(id) {
  return [...graphData.entities, ...graphData.claims, ...graphData.events].find((record) => record.id === id);
}

async function inspect(record) {
  $("inspectkind").textContent = record.kind || "Entity";
  const box = $("inspector");
  box.replaceChildren();
  const lead = element("div", undefined, "inspector-lead");
  lead.append(element("strong", record.name || record.relation_type || record.predicate || "Stored record"));
  lead.append(element("p", record.kind === "Entity" ? "Identity record in the active dataset." : "Inspect the exact supporting source before treating this as a conclusion."));
  box.append(lead);
  const facts = element("div", undefined, "provenance-grid");
  facts.append(metric("Record type", record.kind || "Entity"), metric("Entity type", record.entity_type || "—"), metric("Polarity / modality", [record.polarity, record.modality].filter(Boolean).join(" · ") || "—"), metric("Event time", record.event_time || "—"));
  box.append(facts);
  if (record.kind !== "Entity") box.append(element("p", `Valid interval: ${record.valid_from || "unknown"} → ${record.valid_to || "unknown"}`, "small"));

  if (record.participants) {
    const participants = storySection("Whole-event participants", `${record.participants.length} roles`);
    const list = element("div", undefined, "provenance-grid");
    for (const participant of record.participants) list.append(metric(participant.role, participant.name));
    participants.append(list);
    box.append(participants);
  }

  if (record.evidence_id) {
    try {
      const evidence = await api(`/api/records/${record.evidence_id}`);
      const source = await api(`/api/records/${evidence.source_id}`);
      const sourceSection = storySection("Exact supporting source", source.filename || "Stored source");
      sourceSection.append(element("div", evidence.quote, "quote"));
      const provenance = element("div", undefined, "provenance-grid");
      provenance.append(metric("Source file", source.filename || "Unknown"), metric("Offsets", `${evidence.start}–${evidence.end}`), metric("Location", evidence.location ? JSON.stringify(evidence.location) : "—"), metric("Record check", record.review_reason || "Source-backed"));
      sourceSection.append(provenance);
      box.append(sourceSection);
      const limit = element("p", undefined, "limit-note");
      limit.append(element("strong", "Scope of this evidence"), document.createTextNode(record.independently_verified ? "Independently verified." : "This is a source assertion, not independent world verification."));
      box.append(limit);
    } catch (error) {
      box.append(element("p", error.message, "error"));
    }
  } else if (record.kind === "Entity") {
    const matches = await api(`/api/entities?name=${encodeURIComponent(record.name)}`);
    const events = await api(`/api/events?entity_id=${encodeURIComponent(record.id)}`);
    const identity = storySection("Identity and participation");
    const provenance = element("div", undefined, "provenance-grid");
    provenance.append(metric("Matching identities", matches.length), metric("Whole events", events.events.length));
    identity.append(provenance);
    if (matches.length > 1) identity.append(element("p", "Ambiguous name: select an exact ID when querying.", "limit-note"));
    for (const event of events.events) {
      const button = element("button", event.relation_type);
      button.onclick = () => selectRecord(event);
      identity.append(button);
    }
    box.append(identity);
  }

  const details = element("details");
  details.append(element("summary", "Stored record JSON"), element("pre", JSON.stringify(record, null, 2)));
  box.append(details);
}

function svg(tag, attributes, text) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [name, value] of Object.entries(attributes)) node.setAttribute(name, value);
  if (text !== undefined) node.textContent = text;
  return node;
}

function typeColor(entity) {
  if (/service|component/i.test(entity.entity_type)) return "#c64b32";
  if (/person/i.test(entity.entity_type)) return "#6b5b79";
  return "#28597c";
}

function setView() {
  $("graph").setAttribute("viewBox", view.join(" "));
}

function point(event) {
  const svgPoint = $("graph").createSVGPoint();
  svgPoint.x = event.clientX;
  svgPoint.y = event.clientY;
  return svgPoint.matrixTransform($("graph").getScreenCTM().inverse());
}

function selectionContext() {
  const context = {entities: new Set(), claims: new Set(), events: new Set()};
  const selected = recordById(selectedRecordId);
  if (!selected) return context;

  if (selected.kind === "Claim") {
    context.claims.add(selected.id);
    context.entities.add(selected.subject_id);
    context.entities.add(selected.object_id);
    return context;
  }

  if (selected.kind === "RelationEvent") {
    context.events.add(selected.id);
    for (const participant of selected.participants || []) context.entities.add(participant.entity_id);
    return context;
  }

  context.entities.add(selected.id);
  for (const claim of graphData.claims) {
    if (claim.subject_id === selected.id || claim.object_id === selected.id) {
      context.claims.add(claim.id);
      context.entities.add(claim.subject_id);
      context.entities.add(claim.object_id);
    }
  }
  for (const event of graphData.events) {
    if ((event.participants || []).some((participant) => participant.entity_id === selected.id)) {
      context.events.add(event.id);
      for (const participant of event.participants) context.entities.add(participant.entity_id);
    }
  }
  return context;
}

function focusOpacity(context, kind, id) {
  if (!selectedRecordId) return 1;
  return context[kind].has(id) ? 1 : 0.15;
}

function selectRecord(record) {
  selectedRecordId = record.id;
  inspect(record).catch((error) => {
    $("globalstatus").textContent = error.message;
    $("globalstatus").classList.add("error");
  });
  render(false);
  orbit?.sync(true);
}

function clearSelection() {
  if (!selectedRecordId) return;
  selectedRecordId = null;
  $("inspectkind").textContent = "Select a record";
  $("inspector").replaceChildren(element("p", "Select a node, relation, or whole event to inspect its source record."));
  render(false);
  orbit?.sync();
}

function bindPick(node, record) {
  node.setAttribute("tabindex", "0");
  node.setAttribute("role", "button");
  node.setAttribute("aria-label", `Inspect ${record.name || record.predicate || record.relation_type || record.kind}`);
  node.setAttribute("aria-pressed", String(selectedRecordId === record.id));
  node.classList.add("pick");
  node.classList.add("ugi-b-pickable");
  node.onclick = (event) => {
    event.stopPropagation();
    selectRecord(record);
  };
  node.onkeydown = (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      selectRecord(record);
    }
  };
}

function makeDraggable(shape, record) {
  shape.onpointerdown = (event) => {
    event.stopPropagation();
    const start = point(event);
    const initial = positions.get(record.id);
    let moved = false;

    const move = (pointerEvent) => {
      const current = point(pointerEvent);
      if (Math.abs(current.x - start.x) + Math.abs(current.y - start.y) > 3) moved = true;
      if (moved) {
        positions.set(record.id, [initial[0] + current.x - start.x, initial[1] + current.y - start.y]);
        render(false);
      }
    };
    const up = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      if (!moved) selectRecord(record);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up, {once: true});
  };
}

function layoutEntities(entities, events) {
  positions = new Map();
  if (!entities.length) return;

  const centre = [550, 270];
  let index = 0;
  let ring = 0;
  while (index < entities.length) {
    const capacity = ring === 0 ? 1 : 8 + ring * 8;
    const count = Math.min(capacity, entities.length - index);
    const radius = ring === 0 ? 0 : 108 + ring * 106;
    for (let slot = 0; slot < count; slot += 1) {
      const angle = ring === 0 ? 0 : ((Math.PI * 2 * slot) / count) - (Math.PI / 2) + ring * 0.23;
      positions.set(entities[index + slot].id, [
        centre[0] + Math.cos(angle) * radius,
        centre[1] + Math.sin(angle) * radius * 0.66,
      ]);
    }
    index += count;
    ring += 1;
  }

  events.forEach((event, index) => {
    const points = (event.participants || []).map((participant) => positions.get(participant.entity_id)).filter(Boolean);
    if (!points.length) return;
    const average = points.reduce((total, position) => [total[0] + position[0], total[1] + position[1]], [0, 0]);
    const offsetAngle = index * 2.4;
    positions.set(event.id, [
      average[0] / points.length + Math.cos(offsetAngle) * 36,
      average[1] / points.length + Math.sin(offsetAngle) * 30,
    ]);
  });
}

function markerDefinitions() {
  const defs = svg("defs", {});
  const marker = svg("marker", {
    id: "evidence-arrow", viewBox: "0 -4 8 8", refX: 14, refY: 0,
    markerWidth: 7, markerHeight: 7, orient: "auto", markerUnits: "strokeWidth",
  });
  marker.append(svg("path", {d: "M0,-4L8,0L0,4Z", fill: "#5d6b69"}));
  defs.append(marker);
  return defs;
}

function render(reset = true) {
  const root = $("graph");
  root.replaceChildren(markerDefinitions());
  const entities = graphData.entities.slice(0, 60);
  const ids = new Set(entities.map((entity) => entity.id));
  const events = (graphData.events || []).filter((event) => event.participants.every((participant) => ids.has(participant.entity_id))).slice(0, 8);
  if (reset) {
    layoutEntities(entities, events);
    baseView = [0, 0, 1100, Math.max(540, 540 + Math.max(0, Math.ceil(entities.length / 25) - 1) * 140)];
    view = [...baseView];
  }
  setView();
  $("empty").hidden = entities.length > 0;
  const focus = selectionContext();

  const groups = new Map();
  for (const claim of graphData.claims) {
    const key = [claim.subject_id, claim.predicate, claim.object_id].join("|");
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(claim);
  }

  for (const claim of graphData.claims) {
    if (!positions.has(claim.subject_id) || !positions.has(claim.object_id)) continue;
    const from = positions.get(claim.subject_id);
    const to = positions.get(claim.object_id);
    const peerClaims = groups.get([claim.subject_id, claim.predicate, claim.object_id].join("|")) || [];
    const conflict = peerClaims.some((peer) => peer.polarity !== claim.polarity && peer.modality === "asserted"
      && claim.modality === "asserted" && [peer.valid_from || "0000", claim.valid_from || "0000"].sort().at(-1)
      <= [peer.valid_to || "9999", claim.valid_to || "9999"].sort()[0]);
    const queryActive = queryHighlights.has(claim.id);
    const selected = focus.claims.has(claim.id);
    const color = selected || queryActive ? "#171715" : claim.polarity === "negative" || conflict ? "#a7352a"
      : claim.modality !== "asserted" ? "#9a691d" : "#5d6b69";
    const opacity = focusOpacity(focus, "claims", claim.id);
    const line = svg("line", {
      x1: from[0], y1: from[1], x2: to[0], y2: to[1], stroke: color,
      "stroke-width": selected || queryActive ? 3.4 : 1.6,
      "stroke-dasharray": claim.historical ? "5 4" : "none",
      "marker-end": "url(#evidence-arrow)", opacity,
    });
    bindPick(line, claim);
    root.append(line);
    const label = svg("text", {
      x: (from[0] + to[0]) / 2, y: (from[1] + to[1]) / 2 - 7,
      class: "edge-label", opacity,
    }, `${claim.predicate}${conflict ? " ⚑" : ""}`);
    bindPick(label, claim);
    root.append(label);
  }

  for (const event of events) {
    const [x, y] = positions.get(event.id);
    const opacity = focusOpacity(focus, "events", event.id);
    const color = event.polarity === "negative" ? "#a7352a" : event.modality !== "asserted" ? "#9a691d" : "#6b5b79";
    for (const participant of event.participants) {
      const [px, py] = positions.get(participant.entity_id);
      const connector = svg("line", {
        x1: x, y1: y, x2: px, y2: py, stroke: color, "stroke-width": 1.4,
        "stroke-dasharray": event.historical ? "5 4" : "none", opacity,
      });
      bindPick(connector, event);
      root.append(connector);
      const role = svg("text", {x: (x + px) / 2, y: (y + py) / 2 - 5, class: "edge-label", opacity}, participant.role);
      bindPick(role, event);
      root.append(role);
    }
    const diamond = svg("polygon", {
      points: `${x},${y - 14} ${x + 14},${y} ${x},${y + 14} ${x - 14},${y}`,
      fill: color, stroke: focus.events.has(event.id) ? "#171715" : "#eeebe4", "stroke-width": 2, opacity,
    });
    bindPick(diamond, event);
    makeDraggable(diamond, event);
    root.append(diamond);
    const label = svg("text", {x: x + 20, y: y + 5, opacity}, event.relation_type);
    bindPick(label, event);
    root.append(label);
  }

  for (const entity of entities) {
    const [x, y] = positions.get(entity.id);
    const selected = focus.entities.has(entity.id);
    const opacity = focusOpacity(focus, "entities", entity.id);
    const node = svg("circle", {
      cx: x, cy: y, r: selected ? 13 : 11, fill: typeColor(entity),
      stroke: selected ? "#171715" : "#eeebe4", "stroke-width": selected ? 3 : 2, opacity,
    });
    bindPick(node, entity);
    makeDraggable(node, entity);
    root.append(node);
    const label = svg("text", {x: x + 16, y: y + 4, opacity}, entity.name.length > 27 ? `${entity.name.slice(0, 24)}…` : entity.name);
    bindPick(label, entity);
    root.append(label);
  }
  orbit?.sync();
}

let graphDrag = null;
const graphPointers = new Map();

function getGraphPinchDist() {
  const pts = Array.from(graphPointers.values());
  if (pts.length < 2) return null;
  return Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y);
}

$("graph").onpointerdown = (event) => {
  if (event.button !== 0 && event.pointerType === "mouse") return;
  graphPointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
  const bounds = $("graph").getBoundingClientRect();
  graphDrag = {
    startX: event.clientX,
    startY: event.clientY,
    origView: [...view],
    bounds,
    moved: false,
    initialPinchDist: graphPointers.size === 2 ? getGraphPinchDist() : null,
    initialPinchView: [...view],
  };
  try { $("graph").setPointerCapture(event.pointerId); } catch (_) {}
};

$("graph").onpointermove = (event) => {
  if (graphPointers.has(event.pointerId)) {
    graphPointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
  }
  if (!graphDrag) return;

  // 2-finger pinch zoom on touch screens
  if (graphPointers.size === 2 && graphDrag.initialPinchDist) {
    const currentDist = getGraphPinchDist();
    if (currentDist && currentDist > 10) {
      const pinchFactor = graphDrag.initialPinchDist / currentDist;
      const factor = Math.max(0.65, Math.min(1.8, pinchFactor));
      const newW = Math.max(120, Math.min(6000, graphDrag.initialPinchView[2] * factor));
      const newH = Math.max(90, Math.min(4500, graphDrag.initialPinchView[3] * factor));
      view = [
        graphDrag.initialPinchView[0] + (graphDrag.initialPinchView[2] - newW) / 2,
        graphDrag.initialPinchView[1] + (graphDrag.initialPinchView[3] - newH) / 2,
        newW,
        newH,
      ];
      setView();
      graphDrag.moved = true;
      return;
    }
  }

  // 3-finger drag or left-click drag to move it around
  const dx = event.clientX - graphDrag.startX;
  const dy = event.clientY - graphDrag.startY;
  if (Math.abs(dx) + Math.abs(dy) > 3) {
    graphDrag.moved = true;
    const scaleX = graphDrag.origView[2] / graphDrag.bounds.width;
    const scaleY = graphDrag.origView[3] / graphDrag.bounds.height;
    view = [
      graphDrag.origView[0] - dx * scaleX,
      graphDrag.origView[1] - dy * scaleY,
      graphDrag.origView[2],
      graphDrag.origView[3],
    ];
    setView();
  }
};

$("graph").onpointerup = (event) => {
  graphPointers.delete(event.pointerId);
  try { $("graph").releasePointerCapture(event.pointerId); } catch (_) {}
  if (graphDrag && !graphDrag.moved) {
    clearSelection();
  }
  if (graphPointers.size === 0) graphDrag = null;
};

$("graph").onpointercancel = (event) => {
  graphPointers.delete(event.pointerId);
  if (graphPointers.size === 0) graphDrag = null;
};

// 2-finger pinch to zoom in & out (and mouse wheel) in 2D
$("graph").onwheel = (event) => {
  event.preventDefault();
  const bounds = $("graph").getBoundingClientRect();
  const mouseX = Math.max(0, Math.min(1, (event.clientX - bounds.left) / bounds.width));
  const mouseY = Math.max(0, Math.min(1, (event.clientY - bounds.top) / bounds.height));

  let factor;
  if (event.ctrlKey) {
    // 2-finger pinch on trackpad
    factor = Math.exp(event.deltaY * 0.012);
  } else {
    // Regular 2-finger scroll or wheel
    factor = event.deltaY > 0 ? 1.09 : 0.91;
  }
  factor = Math.max(0.65, Math.min(1.4, factor));

  const newW = Math.max(120, Math.min(6000, view[2] * factor));
  const newH = Math.max(90, Math.min(4500, view[3] * factor));
  view = [
    view[0] + (view[2] - newW) * mouseX,
    view[1] + (view[3] - newH) * mouseY,
    newW,
    newH,
  ];
  setView();
};

function zoom(factor) {
  view = [view[0] + view[2] * (1 - factor) / 2, view[1] + view[3] * (1 - factor) / 2, view[2] * factor, view[3] * factor];
  setView();
}

$("zoomIn").onclick = () => zoom(0.8);
$("zoomOut").onclick = () => zoom(1.25);
$("resetview").onclick = () => { view = [...baseView]; setView(); };

async function refresh() {
  const epoch = ++loadEpoch;
  $("globalstatus").textContent = "Loading graph and persistent state…";
  setGraphState("loading");
  const query = $("timeline").value ? `?as_of=${$("timeline").value}` : "";
  // Secondary read-only panels must never prevent a valid graph from rendering.
  const [graphResult, casesResult, tasksResult] = await Promise.allSettled([
    api(`/api/graph${query}`), api("/api/investigations"), api("/api/tasks")
  ]);
  if (epoch !== loadEpoch) return;
  if (graphResult.status !== "fulfilled") throw graphResult.reason;
  const graph = graphResult.value;
  if (!graph || !Array.isArray(graph.entities) || !Array.isArray(graph.claims) ||
      !Array.isArray(graph.events) || !graph.counts) {
    throw Error("The graph endpoint returned an invalid response.");
  }
  const cases = casesResult.status === "fulfilled" && Array.isArray(casesResult.value) ? casesResult.value : [];
  const tasks = tasksResult.status === "fulfilled" && Array.isArray(tasksResult.value) ? tasksResult.value : [];
  graphData = graph;
  if (!recordById(selectedRecordId)) selectedRecordId = null;
  for (const [id, value] of [["kentities", graph.counts.Entity || 0], ["kclaims", graph.counts.Claim || 0], ["kevents", graph.counts.RelationEvent || 0], ["kcases", cases.length], ["kreviews", tasks.filter((task) => task.status === "open").length]]) {
    $(id).textContent = value;
  }
  render();
  setGraphState();

  const notices = [];
  if (casesResult.status !== "fulfilled") notices.push("Saved investigations unavailable. Graph data is still shown.");
  if (tasksResult.status !== "fulfilled") notices.push("Review queue unavailable. Graph data is still shown.");
  if (graph.truncated) notices.push("Bounded view: some records are outside this result.");
  if (graph.unknown_dates_excluded) notices.push("Historical view excludes claims without dated evidence; counts above show all stored records.");
  $("graphnotice").hidden = !notices.length;
  $("graphnotice").textContent = notices.join(" ");
  if (notices.length) $("graphnotice").classList.add("ugi-b-truncation-notice");

  $("cases").replaceChildren();
  if (!cases.length) $("cases").append(element("p", "No saved investigations. Preview a target to begin."));
  for (const item of cases) {
    const entry = element("article", undefined, "case-card");
    const head = element("div", undefined, "case-card-head");
    const copy = element("div");
    copy.append(element("h3", `Investigation · ${item.priority || "unknown"} priority`), element("p", item.explanation || "Stored investigation", "small"));
    head.append(copy, element("span", item.status || "saved", "badge"));
    const metrics = element("div", undefined, "story-metrics");
    metrics.append(metric("Exposure", `${(item.affected_entity_ids || []).length} components`), metric("Claims", (item.supporting_claim_ids || []).length), metric("As of", item.as_of || "Current"), metric("Case ID", item.id.slice(0, 12)));
    const button = element("button", "Inspect saved case");
    button.onclick = () => { show("action", item); renderInvestigationBrief({...item, executed: true}); };
    entry.append(head, metrics, button);
    $("cases").append(entry);
  }

  $("tasks").replaceChildren();
  if (!tasks.length) $("tasks").append(element("p", "No review tasks."));
  for (const task of tasks.slice(0, 30)) {
    const entry = element("article", undefined, "task-card");
    const head = element("div", undefined, "task-card-head");
    const copy = element("div");
    copy.append(element("h3", task.status === "open" ? "Review required" : "Review resolved"), element("p", task.reason, "small"));
    head.append(copy, element("span", task.status.toUpperCase(), "badge"));
    entry.append(head);
    const meta = element("p", `Claim ${task.claim_id ? task.claim_id.slice(0, 12) : "impact assessment"} · Case ${task.investigation_id ? task.investigation_id.slice(0, 12) : "not linked"}`, "small muted");
    entry.append(meta);
    if (task.status === "open") {
      const actions = element("div", undefined, "task-actions");
      for (const decision of ["accepted", "rejected"]) {
        const button = element("button", decision);
        button.onclick = () => busy("refresh", "globalstatus", async () => {
          const reason = prompt("Why? Enter at least 5 characters.");
          if (!reason) return "Decision cancelled";
          await api(`/api/tasks/${task.id}/decision`, {decision, reason});
          await refresh();
          return "Review decision persisted";
        });
        actions.append(button);
      }
      entry.append(actions);
    }
    $("tasks").append(entry);
  }
  return graph.entities.length
    ? `Loaded dataset ${$("dataset").value} · graph-backed records`
    : `Dataset ${$("dataset").value} is empty. Upload a source to populate this graph.`;
}

function resetAction() {
  caseKey = null;
  selectedRecordId = null;
  queryHighlights.clear();
  $("authorise").checked = false;
  $("answer").hidden = true;
  show("answerjson", {});
  $("actionbrief").textContent = "";
  $("actionmode").textContent = "Preview is read only";
  show("action", {});
  $("inspectkind").textContent = "Select a record";
  $("inspector").replaceChildren(element("p", "Select a node, relation, or whole event to inspect its source record."));
}

function presetValues() {
  const domain = $("preset").value.split("-").at(-1);
  const values = domain === "supply" ? ["Harbor Factory", "TRANSITIVELY_DEPENDS_ON", "Nova Supply", "Nova Supply"]
    : domain === "research" ? ["Lina", "SHARES_EMPLOYER", "Noor", "Lina"]
      : ["Checkout", "TRANSITIVELY_DEPENDS_ON", "Cache", "Cache"];
  ["subject", "predicate", "object", "target"].forEach((id, index) => { $(id).value = values[index]; });
  $("timeline").value = domain === "research" ? "2021-06-01" : "";
}

$("refresh").onclick = () => { resetAction(); busy("refresh", "globalstatus", refresh); };
$("retrygraph").onclick = () => { resetAction(); busy("refresh", "globalstatus", refresh); };
$("dataset").onchange = () => { resetAction(); busy("refresh", "globalstatus", refresh); };
$("access").onchange = () => { resetAction(); busy("refresh", "globalstatus", refresh); };
$("preset").onchange = () => {
  if (!$("preset").value) return;
  $("dataset").value = $("preset").value;
  presetValues();
  resetAction();
  busy("refresh", "globalstatus", refresh);
};
$("timeline").onchange = resetAction;
$("applytime").onclick = () => { resetAction(); busy("applytime", "globalstatus", refresh); };
$("cleartime").onclick = () => { $("timeline").value = ""; resetAction(); busy("cleartime", "globalstatus", refresh); };

$("upload").onclick = () => busy("upload", "uploadstatus", async () => {
  if (!$("file").files.length) throw Error("Choose a source file first");
  const form = new FormData();
  form.append("file", $("file").files[0]);
  const report = await api(`/api/uploads?use_ai=${$("useai").checked}`, form);
  show("ingestion", report);
  await refresh();
  return `${report.duplicate ? "Already ingested" : "Stored"} · ${report.claims} claims · ${report.relation_events || 0} events · ${report.review_tasks} reviews`;
});

async function renderVerdict(result) {
  const box = $("answer");
  box.hidden = false;
  box.replaceChildren();
  const tone = statusTone(result.status);
  const verdict = element("div", undefined, "verdict-head");
  const copy = element("div");
  copy.append(element("span", "Completed relationship verdict", "panel-kicker"), element("h3", statusTitle(result.status)), element("p", result.explanation));
  const signal = element("div", undefined, "verdict-status");
  const badge = element("span", result.status, "result-status");
  badge.style.color = tone;
  signal.append(badge, element("small", result.resolution?.assessment || "Final assessment"));
  verdict.append(copy, signal);
  box.append(verdict);

  const request = element("div", undefined, "story-metrics");
  request.append(metric("Subject", $("subject").value), metric("Predicate", result.predicate || $("predicate").value), metric("Object", $("object").value), metric("As of", $("timeline").value || "Current view"));
  box.append(request);

  const trace = storySection("Reasoning trace", `${(result.rules || []).length} rule${(result.rules || []).length === 1 ? "" : "s"}`);
  const steps = element("ol", undefined, "trace-list");
  const traceRows = [];
  for (const rule of result.rules || []) traceRows.push(["Safe rule applied", rule]);
  for (const [index, path] of (result.paths || []).entries()) traceRows.push([`Graph path ${index + 1}`, `${path.claim_ids.length} source-backed claim${path.claim_ids.length === 1 ? "" : "s"} · ${path.directions.map((direction) => direction ? "forward" : "reverse").join(" → ")}`]);
  if (!traceRows.length) traceRows.push(["No inference trace", "The final assessment relies on the displayed direct-source or identity result."]);
  traceRows.slice(0, 5).forEach(([title, detail], index) => {
    const row = element("li", undefined, "trace-step");
    const copy = element("div");
    copy.append(element("strong", title), element("p", detail));
    row.append(element("span", String(index + 1), "trace-index"), copy);
    steps.append(row);
  });
  trace.append(steps);
  box.append(trace);

  const evidenceItems = result.evidence || [];
  if (evidenceItems.length) {
    const evidenceSection = storySection("Exact supporting evidence", `${evidenceItems.length} source span${evidenceItems.length === 1 ? "" : "s"}`);
    const sourceNames = new Map();
    const resolveSource = async (sourceId) => {
      if (!sourceId) return "Stored source";
      if (!sourceNames.has(sourceId)) sourceNames.set(sourceId, api(`/api/records/${sourceId}`).then((source) => source.filename || "Stored source").catch(() => "Source unavailable"));
      return sourceNames.get(sourceId);
    };
    const cards = await Promise.all(evidenceItems.slice(0, 6).map(async (item, index) => {
      const evidence = item.evidence || {};
      const card = element("article", undefined, "evidence-card");
      card.append(element("span", `Evidence ${index + 1}`, "badge"), element("div", evidence.quote || "No quote returned", "quote"));
      const data = element("div", undefined, "provenance-grid");
      data.append(metric("Source file", await resolveSource(evidence.source_id)), metric("Offsets", evidence.start === undefined ? "—" : `${evidence.start}–${evidence.end}`), metric("Claim", item.claim?.predicate || "Stored claim"), metric("Validity", [item.claim?.valid_from || "unknown", item.claim?.valid_to || "unknown"].join(" → ")));
      card.append(data);
      return card;
    }));
    evidenceSection.append(...cards);
    box.append(evidenceSection);
  }

  const resolution = result.resolution || {};
  const limits = storySection("Limits and next evidence");
  const limitList = [];
  if (result.confidence_note) limitList.push(result.confidence_note);
  if (resolution.safety_note) limitList.push(resolution.safety_note);
  if (resolution.recommended_action) limitList.push(`Next: ${resolution.recommended_action}`);
  for (const needed of resolution.missing_evidence || []) limitList.push(`Needed: ${needed}`);
  if (!limitList.length) limitList.push("This presentation reflects stored evidence and the final verdict; it is not an independent real-world verification.");
  for (const note of limitList.slice(0, 5)) limits.append(element("p", note, "limit-note"));
  box.append(limits);
}

function renderInvestigationBrief(result) {
  const box = $("actionbrief");
  const executed = Boolean(result.executed);
  $("actionmode").textContent = executed ? "Persistent action recorded" : "Preview is read only";
  box.replaceChildren();
  const brief = element("section", undefined, `action-brief action-brief--${executed ? "executed" : "preview"}`);
  const badge = element("span", executed ? "Written to graph" : "No write performed", "badge");
  badge.style.color = executed ? "var(--signal)" : "var(--blue)";
  brief.append(badge, element("h3", executed ? "Investigation saved" : "Investigation preview"), element("p", result.explanation || "No action was taken."));
  const metrics = element("div", undefined, "story-metrics");
  metrics.append(metric("Priority", result.priority || "—"), metric("Exposure", `${(result.affected_entity_ids || []).length} components`), metric("Supporting claims", (result.supporting_claim_ids || []).length), metric("Review tasks", (result.review_task_ids || []).length || (executed ? "Created" : "Pending authorization")));
  brief.append(metrics);
  const trace = storySection("Tool execution", `${(result.trace || []).length} steps`);
  const list = element("ol", undefined, "trace-list");
  (result.trace || []).forEach((step, index) => {
    const row = element("li", undefined, "trace-step");
    const copy = element("div");
    copy.append(element("strong", step.tool.replaceAll("_", " ")), element("p", step.read_only ? "Read-only inspection" : "Authorized persistent write"));
    row.append(element("span", String(index + 1), "trace-index"), copy);
    list.append(row);
  });
  if (!(result.trace || []).length) list.append(element("li", "No tool steps were completed.", "trace-step"));
  trace.append(list);
  brief.append(trace);
  if (!executed) brief.append(element("p", "Preview output is not saved. Persistence requires the authorization checkbox and the explicit execute control.", "limit-note"));
  box.append(brief);
}

$("query").onclick = () => busy("query", "querystatus", async () => {
  const result = await api("/api/relationships", {
    subject: $("subject").value, object: $("object").value, predicate: $("predicate").value,
    as_of: $("timeline").value || null, allow_hypothesis: $("hypothesis").checked,
  });
  show("answerjson", result);
  await renderVerdict(result);
  queryHighlights = new Set((result.evidence || []).map((item) => item.claim.id));
  render(false);
  return "Conclusion labelled; supporting graph paths highlighted";
});

async function investigate(execute) {
  if (execute && !$("authorise").checked) throw Error("Explicit action authorization is required");
  if (!caseKey) caseKey = crypto.randomUUID();
  const result = await api("/api/investigations", {
    target: $("target").value, idempotency_key: caseKey, authorise_action: execute, as_of: $("timeline").value || null,
  });
  show("action", result);
  renderInvestigationBrief(result);
  if (execute && result.executed) await refresh();
  return result.executed ? "Persistent investigation and review tasks stored" : "Preview complete; no new action created";
}

$("target").oninput = () => { caseKey = null; $("authorise").checked = false; };
$("preview").onclick = () => busy("preview", "actionstatus", () => investigate(false));
$("execute").onclick = () => busy("execute", "actionstatus", () => investigate(true));

api("/health").then((health) => { $("backend").textContent = `${health.backend} · ${health.provider}`; })
  .catch((error) => { $("backend").textContent = error.message; });
refresh().then((message) => { $("globalstatus").textContent = message; })
  .catch((error) => { $("globalstatus").textContent = error.message; $("globalstatus").classList.add("error"); setGraphState("error", error.message); });

// 3d-force-graph receives disposable display objects, never the source records.
// Force simulation changes positions only; proximity is not evidence of a claim.
function forceGraphData(data) {
  const entities = data.entities.slice(0, 60);
  const ids = new Set(entities.map((record) => record.id));
  const events = (data.events || []).filter((event) =>
    event.participants.every((participant) => ids.has(participant.entity_id))).slice(0, 8);
  const nodes = [...entities, ...events].map((record) => ({
    id: record.id, record, event: events.includes(record),
  }));
  const links = data.claims.filter((claim) => ids.has(claim.subject_id) && ids.has(claim.object_id))
    .map((record) => ({source: record.subject_id, target: record.object_id, record, event: false}));
  for (const record of events) {
    for (const participant of record.participants) {
      links.push({source: record.id, target: participant.entity_id, record, event: true, role: participant.role});
    }
  }
  return {nodes, links};
}

function createOrbitRenderer() {
  const host = $("orbitCanvas");
  const labels = $("orbitLabels");
  let graph;
  try {
    graph = new ForceGraph3D(host, {controlType: "orbit"})
      .backgroundColor("#070b10").showNavInfo(false)
      .nodeLabel((node) => element("span", `${node.event ? "Event: " : ""}${node.record.name || node.record.relation_type || node.id}`))
      .linkLabel((link) => element("span", link.event
        ? `HAS_PARTICIPANT · ${link.role}`
        : `${link.record.predicate || "Claim"} · ${link.record.polarity || ""} · ${link.record.modality || "asserted"}`))
      .nodeRelSize(5).nodeOpacity(0.95).linkOpacity(0.65)
      .linkDirectionalArrowLength((link) => link.event ? 0 : 3)
      .linkDirectionalArrowRelPos(0.85)
      .onNodeClick((node) => selectRecord(node.record))
      .onLinkClick((link) => selectRecord(link.record))
      .onBackgroundClick(clearSelection)
      .cooldownTicks(120);
  } catch (error) {
    graph?.pauseAnimation();
    $("orbitFallback").hidden = false;
    return {failed: true, sync() {}, start() {}, stop() {}, setAutoRotate() {}, get autoRotate() { return false; }};
  }
  const controls = graph.controls();
  controls.autoRotateSpeed = 0.6;
  let sourceData = null;
  let context = selectionContext();
  let fitPending = false;
  let labelFrame = null;
  const category = (item) => item.event ? "events" : "entities";
  const highlighted = (item, kind) => context[kind].has(item.record.id) || queryHighlights.has(item.record.id);
  function nodeColor(node) {
    if (highlighted(node, category(node))) return "#ffffff";
    if (selectedRecordId && !context[category(node)].has(node.id)) return "#344352";
    if (node.event) return "#c084fc";
    if (/service|component/i.test(node.record.entity_type || "")) return "#ff523d";
    return /person/i.test(node.record.entity_type || "") ? "#b388ff" : "#38bdf8";
  }
  function linkColor(link) {
    if (highlighted(link, link.event ? "events" : "claims")) return "#67e8f9";
    if (selectedRecordId) return "#26313d";
    if (link.record.polarity === "negative") return "#f87171";
    if (link.record.modality && link.record.modality !== "asserted") return "#fbbf24";
    return link.event ? "#c084fc" : "#38bdf8";
  }
  function resize() {
    if (viewMode !== "3d") return;
    const {width, height} = host.getBoundingClientRect();
    graph.width(Math.max(1, width)).height(Math.max(1, height));
    labels.setAttribute("viewBox", `0 0 ${Math.max(1, width)} ${Math.max(1, height)}`);
  }
  function renderLabels() {
    labels.replaceChildren();
    const camera = graph.camera();
    const direction = camera.getWorldDirection(camera.position.clone());
    const nodes = graph.graphData().nodes.filter((node) =>
      Number.isFinite(node.x) && (!selectedRecordId || context[category(node)].has(node.id))).slice(0, 12);
    for (const node of nodes) {
      const offset = camera.position.clone().set(node.x, node.y, node.z).sub(camera.position);
      if (offset.dot(direction) <= 0) continue;
      const {x, y} = graph.graph2ScreenCoords(node.x, node.y, node.z);
      if (x < 0 || y < 0 || x > graph.width() || y > graph.height()) continue;
      const name = `${node.event ? "◇ " : ""}${node.record.name || node.record.relation_type || "Event"}`;
      labels.append(svg("text", {x: x + 12, y: y + 4, "font-size": 11}, name.length > 28 ? `${name.slice(0, 25)}…` : name));
    }
    labelFrame = requestAnimationFrame(renderLabels);
  }
  function reset() { graph.zoomToFit(500, 55); }
  graph.onEngineStop(() => {
    if (fitPending && viewMode === "3d") { fitPending = false; reset(); }
  });
  host.onkeydown = (event) => {
    const camera = graph.camera();
    const offset = camera.position.clone().sub(controls.target);
    if (event.key === "Escape") clearSelection();
    else if (event.key === "0") reset();
    else if (["+", "=", "-"].includes(event.key)) {
      offset.multiplyScalar(event.key === "-" ? 1.15 : 0.87);
      camera.position.copy(controls.target).add(offset);
    } else if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)) {
      const axis = offset.clone().set(0, 1, 0);
      if (["ArrowUp", "ArrowDown"].includes(event.key)) axis.set(1, 0, 0).applyQuaternion(camera.quaternion);
      offset.applyAxisAngle(axis, ["ArrowLeft", "ArrowUp"].includes(event.key) ? 0.13 : -0.13);
      camera.position.copy(controls.target).add(offset);
    } else return;
    controls.update();
    event.preventDefault();
  };
  if (window.ResizeObserver) new ResizeObserver(resize).observe(host);
  else window.addEventListener("resize", resize);
  return {
    failed: false,
    sync(focusRecord = false) {
      context = selectionContext();
      if (sourceData !== graphData) {
        sourceData = graphData;
        graph.graphData(forceGraphData(graphData));
        fitPending = true;
      }
      graph.nodeColor(nodeColor).linkColor(linkColor)
        .nodeVal((node) => node.id === selectedRecordId ? 3 : node.event ? 1.8 : 1)
        .linkWidth((link) => highlighted(link, link.event ? "events" : "claims") ? 1.5 : 0.6);
      if (focusRecord) {
        const node = graph.graphData().nodes.find((item) => item.id === selectedRecordId);
        if (node && Number.isFinite(node.x)) {
          graph.cameraPosition({x: node.x + 80, y: node.y + 50, z: node.z + 120}, node, 500);
        }
      }
    },
    start() {
      resize();
      graph.resumeAnimation();
      if (labelFrame === null) renderLabels();
      if (fitPending) { reset(); }
    },
    stop() {
      graph.pauseAnimation();
      cancelAnimationFrame(labelFrame);
      labelFrame = null;
    },
    reset,
    setAutoRotate(value) { controls.autoRotate = value; },
    get autoRotate() { return controls.autoRotate; },
  };
}

function setViewMode(mode) {
  viewMode = mode;
  const orbitView = mode === "3d";
  $("graph2d").hidden = orbitView;
  $("graph3d").hidden = !orbitView;
  $("view2d").setAttribute("aria-selected", String(!orbitView));
  $("view3d").setAttribute("aria-selected", String(orbitView));
  $("view2d").tabIndex = orbitView ? -1 : 0;
  $("view3d").tabIndex = orbitView ? 0 : -1;
  $("autoRotate").hidden = !orbitView;
  $("zoomIn").hidden = orbitView; $("zoomOut").hidden = orbitView; $("resetview").hidden = orbitView;
  $("mapcaption").textContent = orbitView
    ? "3D force graph: drag to orbit, right-drag to pan, scroll / pinch to zoom. Select a node or link to inspect its stored record."
    : "2D Graph: left-click / 3-finger drag to pan, 2-finger pinch to zoom, drag nodes to reposition. Selection resolves to stored record.";
  if (orbitView) {
    orbit ||= createOrbitRenderer();
    $("autoRotate").setAttribute("aria-pressed", String(orbit.autoRotate));
    orbit.sync(true);
    orbit.start();
  } else {
    orbit?.stop();
  }
}

$("view2d").onclick = () => setViewMode("2d");
$("view3d").onclick = () => setViewMode("3d");
$("fallback2d").onclick = () => setViewMode("2d");
$("view2d").onkeydown = $("view3d").onkeydown = (event) => {
  if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
  event.preventDefault();
  const next = event.key === "ArrowLeft" || event.key === "Home" ? $("view2d") : $("view3d");
  setViewMode(next.id === "view3d" ? "3d" : "2d");
  next.focus();
};
$("autoRotate").onclick = () => {
  orbit?.setAutoRotate(!orbit.autoRotate);
  $("autoRotate").setAttribute("aria-pressed", String(orbit?.autoRotate));
};
