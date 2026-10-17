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
  const data = await response.json();
  if (!response.ok) {
    throw Error(typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail || "Request failed"));
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
  const [graph, cases, tasks] = await Promise.all([api(`/api/graph${query}`), api("/api/investigations"), api("/api/tasks")]);
  if (epoch !== loadEpoch) return;
  graphData = graph;
  if (!recordById(selectedRecordId)) selectedRecordId = null;
  for (const [id, value] of [["kentities", graph.counts.Entity || 0], ["kclaims", graph.counts.Claim || 0], ["kevents", graph.counts.RelationEvent || 0], ["kcases", cases.length], ["kreviews", tasks.filter((task) => task.status === "open").length]]) {
    $(id).textContent = value;
  }
  render();
  setGraphState();

  const notices = [];
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
  return `Loaded dataset ${$("dataset").value} · graph-backed records`;
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

// UI-004: a deliberately small, native WebGL view. It only projects records
// already supplied to the 2D map; graph meaning stays entirely in the API.
function orbitHex(hex, alpha = 1) {
  const value = hex.replace("#", "");
  return [parseInt(value.slice(0, 2), 16) / 255, parseInt(value.slice(2, 4), 16) / 255, parseInt(value.slice(4, 6), 16) / 255, alpha];
}

function orbitSubtract(a, b) { return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]; }
function orbitCross(a, b) { return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]; }
function orbitNormalize(vector) {
  const length = Math.hypot(...vector) || 1;
  return vector.map((item) => item / length);
}
function orbitDot(a, b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
function orbitMultiply(a, b) {
  const out = new Float32Array(16);
  for (let column = 0; column < 4; column += 1) for (let row = 0; row < 4; row += 1) {
    out[column * 4 + row] = a[row] * b[column * 4] + a[4 + row] * b[column * 4 + 1]
      + a[8 + row] * b[column * 4 + 2] + a[12 + row] * b[column * 4 + 3];
  }
  return out;
}
function orbitPerspective(aspect) {
  const f = 1 / Math.tan((48 * Math.PI) / 360);
  const near = .1;
  const far = 100;
  return new Float32Array([f / aspect, 0, 0, 0, 0, f, 0, 0, 0, 0, (far + near) / (near - far), -1, 0, 0, (2 * far * near) / (near - far), 0]);
}
function orbitLookAt(eye, centre) {
  const forward = orbitNormalize(orbitSubtract(eye, centre));
  const right = orbitNormalize(orbitCross([0, 1, 0], forward));
  const up = orbitCross(forward, right);
  return new Float32Array([
    right[0], up[0], forward[0], 0,
    right[1], up[1], forward[1], 0,
    right[2], up[2], forward[2], 0,
    -orbitDot(right, eye), -orbitDot(up, eye), -orbitDot(forward, eye), 1,
  ]);
}
function orbitProject(matrix, point, width, height) {
  const x = point[0], y = point[1], z = point[2];
  const w = matrix[3] * x + matrix[7] * y + matrix[11] * z + matrix[15];
  if (w <= 0) return null;
  const clipX = (matrix[0] * x + matrix[4] * y + matrix[8] * z + matrix[12]) / w;
  const clipY = (matrix[1] * x + matrix[5] * y + matrix[9] * z + matrix[13]) / w;
  const clipZ = (matrix[2] * x + matrix[6] * y + matrix[10] * z + matrix[14]) / w;
  return {x: (clipX * .5 + .5) * width, y: (-clipY * .5 + .5) * height, depth: clipZ, scale: 1 / w};
}

function createOrbitRenderer() {
  const canvas = $("orbitCanvas");
  const labels = $("orbitLabels");
  const fallback = $("orbitFallback");
  const gl = canvas.getContext("webgl", {alpha: true, antialias: true, preserveDrawingBuffer: false});
  if (!gl) {
    fallback.hidden = false;
    fallback.classList.add("ugi-b-fallback-active");
    return {failed: true, sync() {}, start() {}, setAutoRotate() {}, get autoRotate() { return false; }};
  }

  const compile = (kind, source) => {
    const shader = gl.createShader(kind);
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) throw Error(gl.getShaderInfoLog(shader));
    return shader;
  };
  const program = (vertex, fragment) => {
    const result = gl.createProgram();
    gl.attachShader(result, compile(gl.VERTEX_SHADER, vertex));
    gl.attachShader(result, compile(gl.FRAGMENT_SHADER, fragment));
    gl.linkProgram(result);
    if (!gl.getProgramParameter(result, gl.LINK_STATUS)) throw Error(gl.getProgramInfoLog(result));
    return result;
  };
  let pointProgram;
  let lineProgram;
  try {
    pointProgram = program(
      "attribute vec3 p; attribute vec4 c; attribute float s; attribute float diamond; uniform mat4 m; varying vec4 color; varying float shape; void main(){ gl_Position=m*vec4(p,1.0); float size = diamond < -0.5 ? max(10.0, (s * 5.0) / max(0.5, gl_Position.w)) : max(14.0, (s * 7.5)/max(0.5, gl_Position.w)); gl_PointSize=size; color=c; shape=diamond; }",
      `precision mediump float;
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
}`
    );
    lineProgram = program(
      "attribute vec3 p; attribute vec4 c; uniform mat4 m; varying vec4 color; void main(){ gl_Position=m*vec4(p,1.0); color=c; }",
      "precision mediump float; varying vec4 color; void main(){ gl_FragColor=color; }",
    );
  } catch (error) {
    fallback.hidden = false;
    fallback.classList.add("ugi-b-fallback-active");
    return {failed: true, sync() {}, start() {}, setAutoRotate() {}, get autoRotate() { return false; }};
  }

  const pointBuffer = gl.createBuffer();
  const lineBuffer = gl.createBuffer();
  const state = {
    yaw: .68, pitch: .24, distance: 7.0, target: [0, 0, 0],
    autoRotate: false,
    records: [], links: [], pointById: new Map(), screenRecords: [], running: false,
  };

  function positionFor(entity, index) {
    const angle = index * 2.399963229728653;
    const radius = 2.5 + Math.sqrt(index) * 0.65;
    return [Math.cos(angle) * radius, ((index % 5) - 2) * 0.85 + Math.sin(angle * 1.8) * 0.6, Math.sin(angle) * radius];
  }
  function rebuild() {
    const entities = graphData.entities.slice(0, 60);
    const ids = new Set(entities.map((entity) => entity.id));
    const events = (graphData.events || []).filter((event) => event.participants.every((participant) => ids.has(participant.entity_id))).slice(0, 8);
    state.records = entities.map((entity, index) => ({record: entity, point: positionFor(entity, index), event: false}));
    state.pointById = new Map(state.records.map((item) => [item.record.id, item.point]));
    for (const [index, event] of events.entries()) {
      const participants = event.participants.map((participant) => state.pointById.get(participant.entity_id)).filter(Boolean);
      if (!participants.length) continue;
      const point = participants.reduce((sum, item) => [sum[0] + item[0], sum[1] + item[1], sum[2] + item[2]], [0, 0, 0]).map((item) => item / participants.length);
      point[1] += 1.15 + (index % 2) * .3;
      state.records.push({record: event, point, event: true});
      state.pointById.set(event.id, point);
    }
    state.links = [];
    for (const claim of graphData.claims) {
      const from = state.pointById.get(claim.subject_id);
      const to = state.pointById.get(claim.object_id);
      if (from && to) state.links.push({record: claim, from, to, event: false});
    }
    for (const event of events) {
      const from = state.pointById.get(event.id);
      for (const participant of event.participants) {
        const to = state.pointById.get(participant.entity_id);
        if (from && to) state.links.push({record: event, from, to, event: true});
      }
    }
  }
  function orbitTypeColor(entity) {
    const type = entity?.entity_type || "";
    if (/service|component/i.test(type)) return "#ff523d";
    if (/person/i.test(type)) return "#b388ff";
    return "#38bdf8";
  }
  function claimColor(record, selected) {
    if (selected || queryHighlights.has(record.id)) return orbitHex("#67e8f9", 0.95);
    if (record.polarity === "negative") return orbitHex("#f87171", .75);
    if (record.modality && record.modality !== "asserted") return orbitHex("#fbbf24", .75);
    return orbitHex(record.kind === "RelationEvent" ? "#c084fc" : "#38bdf8", .42);
  }
  function nodeColor(item, selected) {
    if (selected) return orbitHex("#ffffff", 1);
    if (item.event) return claimColor(item.record, false);
    return orbitHex(orbitTypeColor(item.record), 1);
  }
  function matrix() {
    const cosPitch = Math.cos(state.pitch);
    const eye = [
      state.target[0] + state.distance * cosPitch * Math.sin(state.yaw),
      state.target[1] + state.distance * Math.sin(state.pitch),
      state.target[2] + state.distance * cosPitch * Math.cos(state.yaw),
    ];
    return orbitMultiply(orbitPerspective(canvas.width / canvas.height), orbitLookAt(eye, state.target));
  }
  function resize() {
    const bounds = canvas.getBoundingClientRect();
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    const width = Math.max(1, Math.round(bounds.width * ratio));
    const height = Math.max(1, Math.round(bounds.height * ratio));
    if (canvas.width !== width || canvas.height !== height) { canvas.width = width; canvas.height = height; }
    labels.setAttribute("viewBox", `0 0 ${width} ${height}`);
  }
  function draw(now = performance.now()) {
    if (viewMode !== "3d" || orbit?.failed) { state.running = false; return; }
    resize();
    if (state.autoRotate) state.yaw += .0018;
    const m = matrix();
    const focus = selectionContext();
    gl.viewport(0, 0, canvas.width, canvas.height);
    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    gl.enable(gl.DEPTH_TEST);
    gl.depthMask(false);

    const lines = [];
    const particles = [];
    for (const [index, link] of state.links.entries()) {
      const isIncident = focus[link.event ? "events" : "claims"].has(link.record.id);
      const opacity = focusOpacity(focus, link.event ? "events" : "claims", link.record.id);
      const color = claimColor(link.record, isIncident);
      color[3] *= opacity;
      lines.push(...link.from, ...color, ...link.to, ...color);

      // Streaming glowing energy pulses
      if (!link.event) {
        const speed = isIncident ? 0.00032 : 0.00018;
        const pSize = isIncident ? 11 : 7.5;
        const pColor = isIncident ? [0.95, 0.99, 1.0, 1.0] : [...color.slice(0, 3), opacity * 0.9];

        const t1 = ((now * speed) + index * 0.173) % 1.0;
        const pt1 = link.from.map((v, i) => v + (link.to[i] - v) * t1);
        particles.push(...pt1, ...pColor, pSize, -1.0);

        const t2 = (t1 + 0.5) % 1.0;
        const pt2 = link.from.map((v, i) => v + (link.to[i] - v) * t2);
        particles.push(...pt2, ...pColor, pSize * 0.85, -1.0);
      } else {
        const speed = isIncident ? 0.00028 : 0.00016;
        const t = ((now * speed) + index * 0.23) % 1.0;
        const pt = link.from.map((v, i) => v + (link.to[i] - v) * t);
        const pColor = isIncident ? [1.0, 0.95, 1.0, 1.0] : [0.91, 0.47, 0.98, opacity * 0.85];
        particles.push(...pt, ...pColor, isIncident ? 10 : 7, -1.0);
      }
    }
    gl.useProgram(lineProgram);
    gl.bindBuffer(gl.ARRAY_BUFFER, lineBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(lines), gl.DYNAMIC_DRAW);
    const lineStride = 7 * 4;
    const linePosition = gl.getAttribLocation(lineProgram, "p");
    const lineColor = gl.getAttribLocation(lineProgram, "c");
    gl.enableVertexAttribArray(linePosition); gl.vertexAttribPointer(linePosition, 3, gl.FLOAT, false, lineStride, 0);
    gl.enableVertexAttribArray(lineColor); gl.vertexAttribPointer(lineColor, 4, gl.FLOAT, false, lineStride, 12);
    gl.uniformMatrix4fv(gl.getUniformLocation(lineProgram, "m"), false, m);
    gl.drawArrays(gl.LINES, 0, lines.length / 7);

    const points = [];
    state.screenRecords = [];
    for (const item of state.records) {
      const selected = focus[item.event ? "events" : "entities"].has(item.record.id);
      const opacity = focusOpacity(focus, item.event ? "events" : "entities", item.record.id);
      const color = nodeColor(item, selected); color[3] *= opacity;
      const pointSize = selected ? 42 : item.event ? 30 : 24;
      const shapeCode = item.event ? (selected ? 3 : 1) : (selected ? 2 : 0);
      points.push(...item.point, ...color, pointSize, shapeCode);
      const projected = orbitProject(m, item.point, canvas.width, canvas.height);
      if (projected && projected.depth < 1) state.screenRecords.push({...projected, item});
    }
    points.push(...particles);
    gl.useProgram(pointProgram);
    gl.bindBuffer(gl.ARRAY_BUFFER, pointBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(points), gl.DYNAMIC_DRAW);
    const pointStride = 9 * 4;
    const pointPosition = gl.getAttribLocation(pointProgram, "p");
    const pointColor = gl.getAttribLocation(pointProgram, "c");
    const pointSize = gl.getAttribLocation(pointProgram, "s");
    const pointShape = gl.getAttribLocation(pointProgram, "diamond");
    gl.enableVertexAttribArray(pointPosition); gl.vertexAttribPointer(pointPosition, 3, gl.FLOAT, false, pointStride, 0);
    gl.enableVertexAttribArray(pointColor); gl.vertexAttribPointer(pointColor, 4, gl.FLOAT, false, pointStride, 12);
    gl.enableVertexAttribArray(pointSize); gl.vertexAttribPointer(pointSize, 1, gl.FLOAT, false, pointStride, 28);
    gl.enableVertexAttribArray(pointShape); gl.vertexAttribPointer(pointShape, 1, gl.FLOAT, false, pointStride, 32);
    gl.uniformMatrix4fv(gl.getUniformLocation(pointProgram, "m"), false, m);
    gl.drawArrays(gl.POINTS, 0, points.length / 9);
    gl.depthMask(true);
    renderLabels();
    requestAnimationFrame(draw);
  }
  function renderLabels() {
    labels.replaceChildren();
    if (viewMode !== "3d") return;
    const focus = selectionContext();
    const candidates = state.screenRecords
      .filter(({item}) => selectedRecordId ? focus[item.event ? "events" : "entities"].has(item.record.id) : true)
      .sort((a, b) => a.depth - b.depth).slice(0, selectedRecordId ? 12 : 10);
    for (const candidate of candidates) {
      const isSelected = Boolean(selectedRecordId && candidate.item.record.id === selectedRecordId);
      const rec = candidate.item.record;
      const isEvent = candidate.item.event;
      const name = rec.name || rec.relation_type || "Event";
      const catColor = isEvent ? "#e879f9" : orbitTypeColor(rec);
      const shortName = name.length > 24 ? `${name.slice(0, 21)}…` : name;
      const pillW = Math.max(68, Math.round(shortName.length * 7.5 + 28));
      const pillH = 22;
      const pillX = (candidate.x + 20 + pillW > canvas.width - 12)
        ? Math.round(candidate.x - pillW - 20)
        : Math.round(candidate.x + 20);
      const pillY = Math.round(candidate.y - 11);
      const depthOpacity = isSelected ? 1 : Math.max(0.45, Number((1 - candidate.depth * 0.55).toFixed(2)));

      if (isSelected) {
        const cx = Math.round(candidate.x);
        const cy = Math.round(candidate.y);
        const reticle = svg("g", {class: "orbit-reticle"});
        reticle.append(
          svg("circle", {cx, cy, r: 28, fill: "none", stroke: catColor, "stroke-width": 1.5, "stroke-dasharray": "5 3", opacity: "0.95"}),
          svg("circle", {cx, cy, r: 36, fill: "none", stroke: catColor, "stroke-width": 1, opacity: "0.38"})
        );
        labels.append(reticle);
      }

      const badgeGroup = svg("g", {
        class: isSelected ? "orbit-badge orbit-badge-selected" : "orbit-badge",
        opacity: depthOpacity,
      });
      const rect = svg("rect", {
        x: pillX, y: pillY, width: pillW, height: pillH, rx: 6,
        fill: isSelected ? "rgba(10, 24, 40, 0.92)" : "rgba(11, 17, 26, 0.82)",
        stroke: isSelected ? catColor : "rgba(255, 255, 255, 0.16)",
        "stroke-width": isSelected ? 1.5 : 1,
      });
      const dot = svg("circle", {
        cx: pillX + 10, cy: pillY + 11, r: 3.5,
        fill: catColor,
      });
      const text = svg("text", {
        x: pillX + 20, y: pillY + 15,
        fill: isSelected ? "#ffffff" : "#f1f5f9",
        "font-size": "11",
        "font-weight": isSelected ? "700" : "500",
      }, shortName);

      badgeGroup.append(rect, dot, text);
      labels.append(badgeGroup);
    }
  }
  function focus(record) {
    const point = state.pointById.get(record.id);
    if (point) state.target = [...point];
  }
  function pick(clientX, clientY) {
    const bounds = canvas.getBoundingClientRect();
    const ratio = canvas.width / bounds.width;
    const x = (clientX - bounds.left) * ratio;
    const y = (clientY - bounds.top) * ratio;
    const dpr = window.devicePixelRatio || 1;
    const match = state.screenRecords
      .map((item) => ({item, distance: Math.hypot(item.x - x, item.y - y)}))
      .filter((item) => item.distance < 28 * dpr)
      .sort((a, b) => a.distance - b.distance || a.item.depth - b.item.depth)[0];
    if (match) { focus(match.item.item.record); selectRecord(match.item.item.record); }
    else clearSelection();
  }
  let drag = null;
  const orbitPointers = new Map();

  function getOrbitPinchDist() {
    const pts = Array.from(orbitPointers.values());
    if (pts.length < 2) return null;
    return Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y);
  }

  canvas.oncontextmenu = (event) => event.preventDefault();
  canvas.onpointerdown = (event) => {
    orbitPointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    drag = {
      x: event.clientX, y: event.clientY,
      yaw: state.yaw, pitch: state.pitch,
      target: [...state.target],
      orbit: event.button === 2 || event.shiftKey,
      moved: false,
      initialPinchDist: orbitPointers.size === 2 ? getOrbitPinchDist() : null,
      initialDist: state.distance,
    };
    try { canvas.setPointerCapture(event.pointerId); } catch (_) {}
  };
  canvas.onpointermove = (event) => {
    if (orbitPointers.has(event.pointerId)) {
      orbitPointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    }
    if (!drag) return;

    // 2-finger touch pinch zoom
    if (orbitPointers.size === 2 && drag.initialPinchDist) {
      const currentDist = getOrbitPinchDist();
      if (currentDist && currentDist > 10) {
        const factor = drag.initialPinchDist / currentDist;
        state.distance = Math.max(2.5, Math.min(22, drag.initialDist * factor));
        drag.moved = true;
        return;
      }
    }

    // 3-finger drag or left-click drag: PAN the graph directly according to drag
    const dx = event.clientX - drag.x;
    const dy = event.clientY - drag.y;
    drag.moved ||= Math.abs(dx) + Math.abs(dy) > 3;
    if (!drag.moved) return;

    if (drag.orbit) {
      state.yaw = drag.yaw + dx * 0.007;
      state.pitch = Math.max(-1.25, Math.min(1.25, drag.pitch + dy * 0.007));
    } else {
      // Calculate camera right and up vectors in world space
      const cosPitch = Math.cos(state.pitch);
      const eye = [
        state.target[0] + state.distance * cosPitch * Math.sin(state.yaw),
        state.target[1] + state.distance * Math.sin(state.pitch),
        state.target[2] + state.distance * cosPitch * Math.cos(state.yaw),
      ];
      const forward = orbitNormalize(orbitSubtract(eye, state.target));
      const right = orbitNormalize(orbitCross([0, 1, 0], forward));
      const up = orbitCross(forward, right);

      // Exact screen-to-world scaling at focal plane (48 deg FOV)
      const unitsPerPixel = (2.0 * state.distance * 0.445228685) / Math.max(1, canvas.height);
      const moveX = dx * unitsPerPixel;
      const moveY = dy * unitsPerPixel;

      // Pan camera target directly according to screen drag (moves graph with cursor)
      state.target = [
        drag.target[0] - right[0] * moveX + up[0] * moveY,
        drag.target[1] - right[1] * moveX + up[1] * moveY,
        drag.target[2] - right[2] * moveX + up[2] * moveY,
      ];
    }
  };
  canvas.onpointerup = (event) => {
    orbitPointers.delete(event.pointerId);
    try { canvas.releasePointerCapture(event.pointerId); } catch (_) {}
    if (drag && !drag.moved) pick(event.clientX, event.clientY);
    if (orbitPointers.size === 0) drag = null;
  };
  canvas.onpointercancel = (event) => {
    orbitPointers.delete(event.pointerId);
    if (orbitPointers.size === 0) drag = null;
  };
  canvas.onwheel = (event) => {
    event.preventDefault();
    if (event.ctrlKey) {
      // 2-finger pinch on trackpad
      const zoomFactor = Math.exp(event.deltaY * 0.01);
      state.distance = Math.max(2.5, Math.min(22, state.distance * zoomFactor));
    } else {
      // Regular scroll wheel / 2-finger scroll
      const factor = event.deltaY > 0 ? 1.08 : 0.92;
      state.distance = Math.max(2.5, Math.min(22, state.distance * factor));
    }
  };
  canvas.onkeydown = (event) => {
    const keys = {ArrowLeft: () => { state.yaw -= .13; }, ArrowRight: () => { state.yaw += .13; }, ArrowUp: () => { state.pitch = Math.max(-1.25, state.pitch - .1); }, ArrowDown: () => { state.pitch = Math.min(1.25, state.pitch + .1); }, "+": () => { state.distance = Math.max(2.5, state.distance * .88); }, "-": () => { state.distance = Math.min(18, state.distance * 1.14); }, "0": () => { state.yaw = .68; state.pitch = .24; state.distance = 7.0; state.target = [0, 0, 0]; }, Escape: () => clearSelection()};
    if (!keys[event.key]) return;
    event.preventDefault();
    keys[event.key]();
  };
  if (window.ResizeObserver) new ResizeObserver(resize).observe(canvas);
  else window.addEventListener("resize", resize);
  return {
    failed: false,
    sync(focusRecord = false) { rebuild(); if (focusRecord && selectedRecordId) focus(recordById(selectedRecordId)); },
    start() { if (!state.running) { state.running = true; requestAnimationFrame(draw); } },
    reset() { state.yaw = .68; state.pitch = .24; state.distance = 7.0; state.target = [0, 0, 0]; },
    setAutoRotate(value) { state.autoRotate = value; },
    get autoRotate() { return state.autoRotate; },
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
    ? "3D Graph: left-click / 3-finger drag to pan, 2-finger pinch to zoom. Selection resolves to stored record."
    : "2D Graph: left-click / 3-finger drag to pan, 2-finger pinch to zoom, drag nodes to reposition. Selection resolves to stored record.";
  if (orbitView) {
    orbit ||= createOrbitRenderer();
    $("autoRotate").setAttribute("aria-pressed", String(orbit.autoRotate));
    orbit.sync(true);
    orbit.start();
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
