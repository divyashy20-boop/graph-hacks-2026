const $ = (id) => document.getElementById(id);

let graphData = {entities: [], claims: [], events: []};
let positions = new Map();
let view = [0, 0, 1100, 500];
let baseView = [0, 0, 1100, 500];
let selectedRecordId = null;
let queryHighlights = new Set();
let caseKey = null;
let loadEpoch = 0;

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
  } finally {
    $(button).disabled = false;
  }
}

function field(parent, label, value) {
  if (value === undefined || value === null || value === "") return;
  const row = element("div", undefined, "field");
  row.append(element("b", label), element("span", String(value)));
  parent.append(row);
}

function recordById(id) {
  return [...graphData.entities, ...graphData.claims, ...graphData.events].find((record) => record.id === id);
}

async function inspect(record) {
  $("inspectkind").textContent = record.kind || "Entity";
  const box = $("inspector");
  box.replaceChildren();
  field(box, "Name / relation", record.name || record.relation_type || record.predicate);
  field(box, "Entity type", record.entity_type);
  field(box, "Polarity / modality", [record.polarity, record.modality].filter(Boolean).join(" · "));
  if (record.kind !== "Entity") {
    field(box, "Valid interval", [record.valid_from || "unknown", record.valid_to || "unknown"].join(" → "));
  }
  field(box, "Event time", record.event_time);
  field(box, "Record ID", record.id);

  if (record.participants) {
    for (const participant of record.participants) field(box, participant.role, participant.name);
  }

  if (record.evidence_id) {
    try {
      const evidence = await api(`/api/records/${record.evidence_id}`);
      box.append(element("div", evidence.quote, "quote"));
      const source = await api(`/api/records/${evidence.source_id}`);
      field(box, "Source", source.filename);
      field(box, "Location", JSON.stringify(evidence.location));
      field(box, "Exact chunk offsets", `${evidence.start}–${evidence.end}`);
      field(box, "Verification", record.review_reason);
      field(box, "World verification", record.independently_verified ? "Independently verified" : "Source assertion only");
    } catch (error) {
      box.append(element("p", error.message, "error"));
    }
  } else if (record.kind === "Entity") {
    const matches = await api(`/api/entities?name=${encodeURIComponent(record.name)}`);
    field(box, "Matching name identities", matches.length);
    if (matches.length > 1) box.append(element("p", "Ambiguous name: select an exact ID when querying."));
    const events = await api(`/api/events?entity_id=${encodeURIComponent(record.id)}`);
    field(box, "Whole-event participation", events.events.length);
    for (const event of events.events) {
      const button = element("button", event.relation_type);
      button.onclick = () => selectRecord(event);
      box.append(button);
    }
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
  if (/service|component/i.test(entity.entity_type)) return "#d6ff4f";
  if (/person/i.test(entity.entity_type)) return "#c2a8ff";
  return "#8db7ff";
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
}

function clearSelection() {
  if (!selectedRecordId) return;
  selectedRecordId = null;
  $("inspectkind").textContent = "Select a record";
  $("inspector").replaceChildren(element("p", "Select a node, relation, or whole event to inspect its source record."));
  render(false);
}

function bindPick(node, record) {
  node.setAttribute("tabindex", "0");
  node.setAttribute("role", "button");
  node.setAttribute("aria-label", `Inspect ${record.name || record.predicate || record.relation_type || record.kind}`);
  node.setAttribute("aria-pressed", String(selectedRecordId === record.id));
  node.classList.add("pick");
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
  marker.append(svg("path", {d: "M0,-4L8,0L0,4Z", fill: "#607282"}));
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
    const color = selected || queryActive ? "#f0f3ee" : claim.polarity === "negative" || conflict ? "#ff9e9b"
      : claim.modality !== "asserted" ? "#ffd17d" : "#607282";
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
    const color = event.polarity === "negative" ? "#ff9e9b" : event.modality !== "asserted" ? "#ffd17d" : "#c2a8ff";
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
      fill: color, stroke: focus.events.has(event.id) ? "#f0f3ee" : "#0b1015", "stroke-width": 2, opacity,
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
      stroke: selected ? "#f0f3ee" : "#0b1015", "stroke-width": selected ? 3 : 2, opacity,
    });
    bindPick(node, entity);
    makeDraggable(node, entity);
    root.append(node);
    const label = svg("text", {x: x + 16, y: y + 4, opacity}, entity.name.length > 27 ? `${entity.name.slice(0, 24)}…` : entity.name);
    bindPick(label, entity);
    root.append(label);
  }
}

$("graph").onpointerdown = (event) => {
  if (event.target !== $("graph")) return;
  clearSelection();
  const original = [...view];
  const start = [event.clientX, event.clientY];
  const bounds = $("graph").getBoundingClientRect();
  $("graph").setPointerCapture(event.pointerId);
  $("graph").onpointermove = (pointerEvent) => {
    view = [
      original[0] - ((pointerEvent.clientX - start[0]) * original[2]) / bounds.width,
      original[1] - ((pointerEvent.clientY - start[1]) * original[3]) / bounds.height,
      original[2], original[3],
    ];
    setView();
  };
  $("graph").onpointerup = () => { $("graph").onpointermove = null; };
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
  const query = $("timeline").value ? `?as_of=${$("timeline").value}` : "";
  const [graph, cases, tasks] = await Promise.all([api(`/api/graph${query}`), api("/api/investigations"), api("/api/tasks")]);
  if (epoch !== loadEpoch) return;
  graphData = graph;
  if (!recordById(selectedRecordId)) selectedRecordId = null;
  for (const [id, value] of [["kentities", graph.counts.Entity || 0], ["kclaims", graph.counts.Claim || 0], ["kevents", graph.counts.RelationEvent || 0], ["kcases", cases.length], ["kreviews", tasks.filter((task) => task.status === "open").length]]) {
    $(id).textContent = value;
  }
  render();

  const notices = [];
  if (graph.truncated) notices.push("Bounded view: some records are outside this result.");
  if (graph.unknown_dates_excluded) notices.push("Historical view excludes claims without dated evidence; counts above show all stored records.");
  $("graphnotice").hidden = !notices.length;
  $("graphnotice").textContent = notices.join(" ");

  $("cases").replaceChildren();
  if (!cases.length) $("cases").append(element("p", "No saved investigations. Preview a target to begin."));
  for (const item of cases) {
    const entry = element("div", undefined, "entry");
    entry.append(element("strong", `${item.priority.toUpperCase()} · ${item.affected_entity_ids.length} exposed components`), element("p", `${item.status} · ${item.id.slice(0, 12)}`, "small"));
    const button = element("button", "Inspect saved case");
    button.onclick = () => { show("action", item); $("actionbrief").textContent = item.explanation; };
    entry.append(button);
    $("cases").append(entry);
  }

  $("tasks").replaceChildren();
  if (!tasks.length) $("tasks").append(element("p", "No review tasks."));
  for (const task of tasks.slice(0, 30)) {
    const entry = element("div", undefined, "entry");
    entry.append(element("span", task.status.toUpperCase(), "badge"), element("p", task.reason, "small"));
    if (task.status === "open") {
      for (const decision of ["accepted", "rejected"]) {
        const button = element("button", decision);
        button.onclick = () => busy("refresh", "globalstatus", async () => {
          const reason = prompt("Why? Enter at least 5 characters.");
          if (!reason) return "Decision cancelled";
          await api(`/api/tasks/${task.id}/decision`, {decision, reason});
          await refresh();
          return "Review decision persisted";
        });
        entry.append(button);
      }
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

$("query").onclick = () => busy("query", "querystatus", async () => {
  const result = await api("/api/relationships", {
    subject: $("subject").value, object: $("object").value, predicate: $("predicate").value,
    as_of: $("timeline").value || null, allow_hypothesis: $("hypothesis").checked,
  });
  show("answerjson", result);
  const box = $("answer");
  box.hidden = false;
  box.replaceChildren();
  const badge = element("span", result.status, "result-status");
  badge.style.color = result.status === "CONTRADICTED" || result.status === "SOURCE_NEGATED" ? "var(--red)"
    : result.status === "UNKNOWN" || result.status === "HYPOTHESIS" ? "var(--amber)" : "var(--signal)";
  box.append(badge, element("p", result.explanation));
  if (result.resolution) {
    for (const needed of result.resolution.missing_evidence || []) box.append(element("p", `Needed: ${needed}`, "small"));
  }
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
  $("actionbrief").textContent = result.executed ? `Saved investigation ${result.id} · ${result.priority} priority`
    : result.priority ? `Preview · ${result.affected_entity_ids.length} exposed components · ${result.priority} priority` : result.explanation;
  if (execute && result.executed) await refresh();
  return result.executed ? "Persistent investigation and review tasks stored" : "Preview complete; no new action created";
}

$("target").oninput = () => { caseKey = null; $("authorise").checked = false; };
$("preview").onclick = () => busy("preview", "actionstatus", () => investigate(false));
$("execute").onclick = () => busy("execute", "actionstatus", () => investigate(true));

api("/health").then((health) => { $("backend").textContent = `${health.backend} · ${health.provider}`; })
  .catch((error) => { $("backend").textContent = error.message; });
refresh().then((message) => { $("globalstatus").textContent = message; })
  .catch((error) => { $("globalstatus").textContent = error.message; $("globalstatus").classList.add("error"); });
