/**
 * Comprehensive Audit and Verification Suite for UI-011 (UI Friend B)
 * Tests all modules against edge cases, null handling, contract adherence,
 * and failure handling.
 */

const assert = require("assert");

// Load Friend B modules
const graphInteraction = require("../modules/graph_interaction.js");
const orbitInteraction = require("../modules/orbit_interaction.js");
const graphStatus = require("../modules/graph_status.js");
const guidedPresentation = require("../modules/guided_presentation.js");

console.log("=== STARTING UI-011 AUDIT & VERIFICATION ===");

let passed = 0;
let total = 0;

function test(description, fn) {
  total++;
  try {
    fn();
    console.log(`  ✓ PASS: ${description}`);
    passed++;
  } catch (err) {
    console.error(`  ✗ FAIL: ${description}`);
    console.error(err);
    process.exitCode = 1;
  }
}

// -------------------------------------------------------------
// Suite 1: graph_interaction.js
// -------------------------------------------------------------
console.log("\n[Suite 1: Graph Interaction]");

test("ugiBBuildSelectionContext handles null/empty inputs gracefully", () => {
  const ctx1 = graphInteraction.ugiBBuildSelectionContext(null, null);
  assert.strictEqual(ctx1.entities.size, 0);
  assert.strictEqual(ctx1.claims.size, 0);
  assert.strictEqual(ctx1.events.size, 0);

  const ctx2 = graphInteraction.ugiBBuildSelectionContext("unknown-id", { entities: [], claims: [], events: [] });
  assert.strictEqual(ctx2.entities.size, 0);
});

test("ugiBBuildSelectionContext resolves binary Claim correctly", () => {
  const data = {
    entities: [{ id: "e1", name: "Checkout" }, { id: "e2", name: "Cache" }],
    claims: [{ id: "c1", kind: "Claim", subject_id: "e1", object_id: "e2", predicate: "DEPENDS_ON" }],
    events: []
  };
  const ctx = graphInteraction.ugiBBuildSelectionContext("c1", data);
  assert(ctx.claims.has("c1"));
  assert(ctx.entities.has("e1"));
  assert(ctx.entities.has("e2"));
  assert.strictEqual(ctx.events.size, 0);
});

test("ugiBBuildSelectionContext resolves whole RelationEvent participants", () => {
  const data = {
    entities: [{ id: "e1", name: "Lina" }, { id: "e2", name: "Noor" }, { id: "e3", name: "Lab" }],
    claims: [],
    events: [
      {
        id: "ev1",
        kind: "RelationEvent",
        relation_type: "RESEARCH_COLLABORATION",
        participants: [
          { entity_id: "e1", role: "lead" },
          { entity_id: "e2", role: "co-author" }
        ]
      }
    ]
  };
  const ctx = graphInteraction.ugiBBuildSelectionContext("ev1", data);
  assert(ctx.events.has("ev1"));
  assert(ctx.entities.has("e1"));
  assert(ctx.entities.has("e2"));
  assert(!ctx.entities.has("e3")); // e3 is not a participant
});

test("ugiBBuildSelectionContext resolves Entity and connected claims/events", () => {
  const data = {
    entities: [{ id: "e1", name: "Checkout" }, { id: "e2", name: "Cache" }],
    claims: [{ id: "c1", kind: "Claim", subject_id: "e1", object_id: "e2", predicate: "DEPENDS_ON" }],
    events: [
      {
        id: "ev1",
        kind: "RelationEvent",
        participants: [{ entity_id: "e1", role: "affected" }]
      }
    ]
  };
  const ctx = graphInteraction.ugiBBuildSelectionContext("e1", data);
  assert(ctx.entities.has("e1"));
  assert(ctx.entities.has("e2"));
  assert(ctx.claims.has("c1"));
  assert(ctx.events.has("ev1"));
});

test("ugiBFocusOpacity dims unselected elements correctly", () => {
  const emptyCtx = { entities: new Set(), claims: new Set(), events: new Set() };
  assert.strictEqual(graphInteraction.ugiBFocusOpacity(emptyCtx, "entities", "e1"), 1);

  const activeCtx = { entities: new Set(["e1"]), claims: new Set(), events: new Set() };
  assert.strictEqual(graphInteraction.ugiBFocusOpacity(activeCtx, "entities", "e1"), 1);
  assert.strictEqual(graphInteraction.ugiBFocusOpacity(activeCtx, "entities", "e2"), 0.15);
});

test("ugiBSelectRecord isolates inspector error without crashing", () => {
  let inspectCalled = false;
  let renderCalled = false;
  let orbitCalled = false;
  let errorCaught = null;

  graphInteraction.ugiBSelectRecord({ id: "e1" }, {
    onInspect: () => {
      inspectCalled = true;
      throw new Error("Simulated inspector network error");
    },
    onRender: () => { renderCalled = true; },
    onOrbitSync: () => { orbitCalled = true; },
    onError: (err) => { errorCaught = err; }
  });

  assert(inspectCalled);
  assert(renderCalled);
  assert(orbitCalled);
  assert(errorCaught !== null);
  assert.strictEqual(errorCaught.message, "Simulated inspector network error");
});

test("ugiBFilterAsOf filters valid time intervals correctly", () => {
  const records = [
    { id: "r1", valid_from: "2020-01-01", valid_to: "2022-01-01" },
    { id: "r2", valid_from: "2023-01-01", valid_to: "2024-01-01" },
    { id: "r3" } // unbounded
  ];

  const filtered = graphInteraction.ugiBFilterAsOf(records, "2021-06-01");
  assert.strictEqual(filtered.length, 2);
  assert.strictEqual(filtered[0].id, "r1");
  assert.strictEqual(filtered[1].id, "r3"); // unbounded remains valid
});

// -------------------------------------------------------------
// Suite 2: orbit_interaction.js
// -------------------------------------------------------------
console.log("\n[Suite 2: Orbit Interaction & WebGL Fallback]");

test("ugiBCheckWebGLSupport handles environments without WebGL context safely", () => {
  const result = orbitInteraction.ugiBCheckWebGLSupport(null);
  assert.strictEqual(result.supported, false);
  assert(result.reason.length > 0);
});

test("ugiBOrbitFallbackHandler reveals fallback and binds 2D return", () => {
  let fallbackClassAdded = false;
  let viewModeChangedTo = null;

  const mockFallbackEl = {
    hidden: true,
    classList: {
      add: (cls) => { if (cls === "ugi-b-fallback-active") fallbackClassAdded = true; }
    }
  };
  const mockButton = { onclick: null };

  orbitInteraction.ugiBOrbitFallbackHandler(mockFallbackEl, mockButton, (mode) => {
    viewModeChangedTo = mode;
  });

  assert.strictEqual(mockFallbackEl.hidden, false);
  assert(fallbackClassAdded);
  assert(typeof mockButton.onclick === "function");
  mockButton.onclick();
  assert.strictEqual(viewModeChangedTo, "2d");
});

test("ugiBPick3DRecord returns closest projected record within tolerance", () => {
  const canvas = {
    width: 1000,
    getBoundingClientRect: () => ({ left: 0, top: 0, width: 1000, height: 500 })
  };
  const screenRecords = [
    { x: 100, y: 100, depth: 0.5, item: { record: { id: "n1", name: "Node 1" } } },
    { x: 500, y: 500, depth: 0.2, item: { record: { id: "n2", name: "Node 2" } } }
  ];

  // Pick near (102, 101) -> within tolerance of n1
  const picked = orbitInteraction.ugiBPick3DRecord(102, 101, canvas, screenRecords, 24);
  assert(picked !== null);
  assert.strictEqual(picked.id, "n1");

  // Pick far away (900, 900) -> outside tolerance
  const missed = orbitInteraction.ugiBPick3DRecord(900, 900, canvas, screenRecords, 24);
  assert.strictEqual(missed, null);
});

test("ugiBSetViewMode coordinates 2D and 3D states with accessible ARIA", () => {
  const elements = {
    graph2d: { hidden: false },
    graph3d: { hidden: true },
    view2d: {
      setAttribute: (k, v) => { elements.view2d[k] = v; },
      tabIndex: 0
    },
    view3d: {
      setAttribute: (k, v) => { elements.view3d[k] = v; },
      tabIndex: -1
    },
    autoRotate: { hidden: true },
    zoomIn: { hidden: false },
    zoomOut: { hidden: false },
    resetview: { hidden: false },
    mapcaption: { textContent: "" }
  };

  let activated3D = false;
  orbitInteraction.ugiBSetViewMode("3d", elements, {
    onActivate3D: () => { activated3D = true; }
  });

  assert.strictEqual(elements.graph2d.hidden, true);
  assert.strictEqual(elements.graph3d.hidden, false);
  assert.strictEqual(elements.view3d["aria-selected"], "true");
  assert.strictEqual(elements.view2d["aria-selected"], "false");
  assert.strictEqual(elements.autoRotate.hidden, false);
  assert.strictEqual(elements.zoomIn.hidden, true);
  assert(activated3D);
});

test("ugiBGetVolumetricShaderSources provides valid volumetric 3D shaders with diffuse, specular, and selection corona", () => {
  const shaders = orbitInteraction.ugiBGetVolumetricShaderSources();
  assert(shaders.vertex.includes("attribute vec3 p;"));
  assert(shaders.vertex.includes("attribute float diamond;"));
  assert(shaders.fragment.includes("vec3 normal = normalize"));
  assert(shaders.fragment.includes("float spec = pow"));
  assert(shaders.fragment.includes("float fresnel = pow"));
  assert(shaders.fragment.includes("isSelected"));
  assert(shaders.fragment.includes("isDiamond"));
  assert(shaders.fragment.includes("isPhoton"));
});

test("ugiBFormatOrbitBadge computes HUD pill metrics, category colors, and selection flags faithfully", () => {
  assert.strictEqual(orbitInteraction.ugiBFormatOrbitBadge(null, null), null);

  const candidateService = {
    x: 100, y: 150, depth: 0.2,
    item: { record: { id: "svc-1", name: "Checkout Service Very Long Name", entity_type: "Service" }, event: false }
  };
  const badge1 = orbitInteraction.ugiBFormatOrbitBadge(candidateService, "svc-1", 1000);
  assert.strictEqual(badge1.isSelected, true);
  assert.strictEqual(badge1.catColor, "#ff523d");
  assert(badge1.shortName.endsWith("…"));
  assert.strictEqual(badge1.depthOpacity, 1);
  assert.strictEqual(badge1.pillX, 120);

  const candidateEvent = {
    x: 950, y: 200, depth: 0.8,
    item: { record: { id: "ev-1", relation_type: "OUTAGE" }, event: true }
  };
  const badge2 = orbitInteraction.ugiBFormatOrbitBadge(candidateEvent, null, 1000);
  assert.strictEqual(badge2.isSelected, false);
  assert.strictEqual(badge2.catColor, "#e879f9");
  assert.strictEqual(badge2.shortName, "OUTAGE");
  assert(badge2.depthOpacity < 1 && badge2.depthOpacity >= 0.45);
  // Flipped because close to right canvas edge:
  assert(badge2.pillX < 950);
});

// -------------------------------------------------------------
// Suite 3: graph_status.js
// -------------------------------------------------------------
console.log("\n[Suite 3: Graph Status & Legend]");

test("ugiBStatusTone matches UI_CONTRACT.md verdict semantics", () => {
  assert(graphStatus.ugiBStatusTone("SOURCE_ASSERTED").includes("signal"));
  assert(graphStatus.ugiBStatusTone("RULE_DERIVED").includes("signal"));
  assert(graphStatus.ugiBStatusTone("CONNECTED_ONLY").includes("amber"));
  assert(graphStatus.ugiBStatusTone("HYPOTHESIS").includes("amber"));
  assert(graphStatus.ugiBStatusTone("UNKNOWN").includes("amber"));
  assert(graphStatus.ugiBStatusTone("CONTRADICTED").includes("red"));
  assert(graphStatus.ugiBStatusTone("SOURCE_NEGATED").includes("red"));
});

test("ugiBTypeColor maps entity categories faithfully", () => {
  assert.strictEqual(graphStatus.ugiBTypeColor({ entity_type: "Service" }), "#cf664c");
  assert.strictEqual(graphStatus.ugiBTypeColor({ entity_type: "Component" }), "#cf664c");
  assert.strictEqual(graphStatus.ugiBTypeColor({ entity_type: "Person" }), "#8d82b4");
  assert.strictEqual(graphStatus.ugiBTypeColor({ entity_type: "Database" }), "#67a7c8");
});

test("ugiBUpdateTruncationNotice displays honest warning when capped", () => {
  const noticeEl = { hidden: true, textContent: "", className: "" };
  graphStatus.ugiBUpdateTruncationNotice(noticeEl, { Entity: 120, truncated: true }, 60);

  assert.strictEqual(noticeEl.hidden, false);
  assert(noticeEl.textContent.includes("capped at 60 entities"));
  assert(noticeEl.textContent.includes("All 120"));

  // Not truncated
  graphStatus.ugiBUpdateTruncationNotice(noticeEl, { Entity: 30, truncated: false }, 60);
  assert.strictEqual(noticeEl.hidden, true);
});

// -------------------------------------------------------------
// Suite 4: guided_presentation.js
// -------------------------------------------------------------
console.log("\n[Suite 4: Guided Presentation & Receipt Freshness]");

test("ugiBIsGuidedEnabled strictly requires BOTH flags true", () => {
  assert.strictEqual(guidedPresentation.ugiBIsGuidedEnabled(null), false);
  assert.strictEqual(guidedPresentation.ugiBIsGuidedEnabled({ guided_agent_enabled: true, memory_enabled: false }), false);
  assert.strictEqual(guidedPresentation.ugiBIsGuidedEnabled({ guided_agent_enabled: false, memory_enabled: true }), false);
  assert.strictEqual(guidedPresentation.ugiBIsGuidedEnabled({ guided_agent_enabled: true, memory_enabled: true }), true);
});

test("ugiBFormatReceiptVerdict handles VALID strictly and honestly", () => {
  const validResp = { freshness: "VALID", safe_to_reuse: true };
  const verdict = guidedPresentation.ugiBFormatReceiptVerdict(validResp);
  assert.strictEqual(verdict.freshness, "VALID");
  assert.strictEqual(verdict.safeToReuse, true);
  assert(verdict.headline.includes("Safe at time of check"));
  assert.strictEqual(verdict.className, "ugi-b-receipt-valid");
});

test("ugiBFormatReceiptVerdict forbids reuse of STALE receipts", () => {
  const staleResp = { freshness: "STALE", safe_to_reuse: false };
  const verdict = guidedPresentation.ugiBFormatReceiptVerdict(staleResp);
  assert.strictEqual(verdict.freshness, "STALE");
  assert.strictEqual(verdict.safeToReuse, false);
  assert(verdict.headline.includes("Do not reuse"));
  assert.strictEqual(verdict.className, "ugi-b-receipt-stale");
});

test("ugiBFormatReceiptVerdict forbids reuse of UNKNOWN receipts", () => {
  const unknownResp = { freshness: "UNKNOWN", safe_to_reuse: false };
  const verdict = guidedPresentation.ugiBFormatReceiptVerdict(unknownResp);
  assert.strictEqual(verdict.freshness, "UNKNOWN");
  assert.strictEqual(verdict.safeToReuse, false);
  assert(verdict.headline.includes("Do not reuse"));
  assert.strictEqual(verdict.className, "ugi-b-receipt-unknown");
});

test("ugiBFormatReceiptVerdict refuses reuse if freshness is not VALID even if safe_to_reuse was true", () => {
  // Defensive guard against corrupted backend payload
  const suspiciousResp = { freshness: "STALE", safe_to_reuse: true };
  const verdict = guidedPresentation.ugiBFormatReceiptVerdict(suspiciousResp);
  assert.strictEqual(verdict.safeToReuse, false);
});

test("ugiBExtractVerifiedClaimIds filters empty or invalid IDs", () => {
  const guidedResponse = {
    result: {
      verified_claim_ids: ["claim-1", "", null, "claim-2", 42]
    }
  };
  const verified = guidedPresentation.ugiBExtractVerifiedClaimIds(guidedResponse);
  assert.deepStrictEqual(verified, ["claim-1", "claim-2"]);
});

console.log(`\n=== AUDIT COMPLETE: ${passed}/${total} TESTS PASSED ===\n`);
if (passed === total) {
  process.exit(0);
} else {
  process.exit(1);
}
