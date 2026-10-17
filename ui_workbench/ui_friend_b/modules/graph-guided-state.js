/*
  UI-011 integration reference.
  Exposes presentation helpers only; it does not create graph physics, call an
  endpoint, or attach click/keyboard handlers. During UI-012, call these helpers
  from the existing app.js/guided.js state transitions exactly once.
*/
(function registerUGIBGraphGuidedState(global) {
  "use strict";

  const ugiBModeCopy = {
    "2d": {
      title: "2D evidence map",
      detail: "Select a record to trace direct source-backed context."
    },
    "3d": {
      title: "3D evidence orbit",
      detail: "Orbit changes perspective only; it does not change graph evidence."
    }
  };

  const ugiBReceiptCopy = {
    VALID: {
      title: "Evidence is current at this check",
      detail: "Reusable at the time of this check. Recheck after dataset or access changes."
    },
    STALE: {
      title: "Evidence changed after this answer",
      detail: "Do not reuse this answer. Run a fresh guided graph question."
    },
    UNKNOWN: {
      title: "Receipt cannot be reused",
      detail: "Evidence conflict or unavailable evidence requires investigation."
    }
  };

  function ugiBText(target, value) {
    if (target) target.textContent = value;
  }

  function ugiBSetMapReadout(root, mode, mapState, detail) {
    if (!root) return;
    const ugiBNormalizedMode = mode === "3d" ? "3d" : "2d";
    const ugiBCopy = ugiBModeCopy[ugiBNormalizedMode];
    root.dataset.mode = ugiBNormalizedMode;
    root.dataset.mapState = mapState || "ready";
    ugiBText(root.querySelector(".ugi-b-map-readout__title"), ugiBCopy.title);
    ugiBText(root.querySelector(".ugi-b-map-readout__detail"), detail || ugiBCopy.detail);
  }

  function ugiBSetReceipt(root, freshness, safeToReuse, reason) {
    if (!root) return;
    const ugiBState = ugiBReceiptCopy[freshness] ? freshness : "UNKNOWN";
    const ugiBCopy = ugiBReceiptCopy[ugiBState];
    root.dataset.receiptState = ugiBState;
    ugiBText(root.querySelector(".ugi-b-receipt__title"), ugiBCopy.title);
    ugiBText(root.querySelector(".ugi-b-receipt__state"), ugiBState);
    ugiBText(
      root.querySelector(".ugi-b-receipt__copy"),
      safeToReuse === true && ugiBState === "VALID" ? ugiBCopy.detail : (reason || ugiBCopy.detail)
    );
  }

  function ugiBSetOrbitFallback(root, active) {
    if (!root) return;
    root.hidden = !active;
  }

  global.ugiB = Object.freeze({
    setMapReadout: ugiBSetMapReadout,
    setReceipt: ugiBSetReceipt,
    setOrbitFallback: ugiBSetOrbitFallback
  });
})(window);
