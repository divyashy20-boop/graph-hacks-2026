/**
 * UGI Friend B — Guided Agent and Receipt Presentation Module
 * UI-011: Graph and guided-state interaction module
 *
 * Implements feature-gated guided-agent controls and honest receipt
 * freshness verification according to UI_CONTRACT.md.
 *
 * Rules:
 * - Prefixed with `ugiB`
 * - Shows guided panel only when health API confirms both `guided_agent_enabled`
 *   and `memory_enabled` are true.
 * - Honestly renders VALID, STALE, and UNKNOWN receipt states:
 *   - VALID: Reusable at the time of the recheck.
 *   - STALE: Do not reuse; underlying graph or evidence changed.
 *   - UNKNOWN: Do not reuse; receipt cannot be verified.
 * - Never presents receipt freshness as a guarantee of safe external action.
 */

(function (global) {
  "use strict";

  /**
   * Determine whether the guided-agent panel should be displayed.
   * Both guided_agent_enabled and memory_enabled must be strictly true.
   *
   * @param {Object} healthResponse - Response from GET /health.
   * @returns {boolean} True if both flags are enabled.
   */
  function ugiBIsGuidedEnabled(healthResponse) {
    if (!healthResponse) return false;
    return Boolean(
      healthResponse.guided_agent_enabled === true &&
      healthResponse.memory_enabled === true
    );
  }

  /**
   * Update the visibility of the guided agent panel based on health status.
   *
   * @param {Element} panelElement - The #guidedpanel DOM element.
   * @param {Object} healthResponse - Data from GET /health.
   * @returns {boolean} Whether the panel is visible.
   */
  function ugiBUpdateGuidedVisibility(panelElement, healthResponse) {
    if (!panelElement) return false;
    const isEnabled = ugiBIsGuidedEnabled(healthResponse);
    panelElement.hidden = !isEnabled;
    if (isEnabled) {
      panelElement.classList.add("ugi-b-guided-active");
    } else {
      panelElement.classList.remove("ugi-b-guided-active");
    }
    return isEnabled;
  }

  /**
   * Format the receipt freshness status into an honest, structured verdict.
   *
   * Invariants (from UI_CONTRACT.md & TICKETS_new.md):
   * - Only VALID can be described as reusable at the time of the check.
   * - STALE and UNKNOWN explicitly mandate not reusing the answer.
   * - Receipt freshness is NOT a guarantee of external action safety.
   *
   * @param {Object} freshnessResponse - Response from GET /api/agent/receipts/{id}/freshness.
   * @returns {{
   *   freshness: "VALID"|"STALE"|"UNKNOWN",
   *   safeToReuse: boolean,
   *   tone: string,
   *   headline: string,
   *   guidance: string,
   *   className: string
   * }}
   */
  function ugiBFormatReceiptVerdict(freshnessResponse) {
    const rawFreshness = freshnessResponse?.freshness?.toUpperCase() || "UNKNOWN";
    const safeToReuse = freshnessResponse?.safe_to_reuse === true;

    // Strict validation: safeToReuse can only be true if freshness is literally VALID
    if (rawFreshness === "VALID" && safeToReuse) {
      return {
        freshness: "VALID",
        safeToReuse: true,
        tone: "var(--signal, #cf664c)",
        headline: "Receipt VALID: Safe at time of check.",
        guidance: "Fresh evidence verified against active graph state. Answer is reusable now.",
        className: "ugi-b-receipt-valid",
      };
    }

    if (rawFreshness === "STALE") {
      return {
        freshness: "STALE",
        safeToReuse: false,
        tone: "var(--amber, #d5a861)",
        headline: "Receipt STALE: Do not reuse this answer.",
        guidance: "Underlying graph evidence or source records have changed since receipt was created. Run a fresh question.",
        className: "ugi-b-receipt-stale",
      };
    }

    // Default: UNKNOWN or unverified
    return {
      freshness: "UNKNOWN",
      safeToReuse: false,
      tone: "var(--red, #df7a70)",
      headline: "Receipt UNKNOWN: Do not reuse.",
      guidance: "Receipt status could not be proven valid. Investigate directly before relying on this conclusion.",
      className: "ugi-b-receipt-unknown",
    };
  }

  /**
   * Safely extract and filter verified claim IDs for graph highlighting.
   * Ensures hypotheses and unverified edges are excluded.
   *
   * @param {Object} guidedResponse - Response from POST /api/agent/guided.
   * @returns {Array<string>} Array of verified claim IDs.
   */
  function ugiBExtractVerifiedClaimIds(guidedResponse) {
    if (!guidedResponse) return [];
    const result = guidedResponse.result || guidedResponse;
    const verified = result?.verified_claim_ids;
    if (Array.isArray(verified)) {
      return verified.filter((id) => typeof id === "string" && id.trim().length > 0);
    }
    return [];
  }

  /**
   * Reset receipt session state when dataset or credentials change.
   *
   * @param {Object} state - The receipt state store.
   * @param {Object} elements - UI elements to clear.
   */
  function ugiBResetReceiptState(state, elements) {
    if (state) {
      state.receiptId = null;
      state.ownerDataset = null;
    }
    if (elements?.refreshreceipt) {
      elements.refreshreceipt.disabled = true;
    }
    if (elements?.guidedverdict) {
      elements.guidedverdict.hidden = true;
      elements.guidedverdict.textContent = "";
      elements.guidedverdict.className = "answer";
    }
    if (elements?.guidedresult) {
      elements.guidedresult.textContent = "";
    }
    if (elements?.receiptreport) {
      elements.receiptreport.textContent = "";
    }
    if (elements?.guidedstatus) {
      elements.guidedstatus.textContent = "";
      elements.guidedstatus.classList.remove("error");
    }
  }

  /**
   * Display receipt verdict in the UI with appropriate styling and ARIA notification.
   *
   * @param {Element} verdictEl - The #guidedverdict element.
   * @param {Object} verdictInfo - Output of ugiBFormatReceiptVerdict.
   */
  function ugiBRenderReceiptVerdict(verdictEl, verdictInfo) {
    if (!verdictEl || !verdictInfo) return;

    verdictEl.hidden = false;
    verdictEl.className = `answer ugi-b-verdict-card ${verdictInfo.className}`;
    verdictEl.style.borderLeft = `3px solid ${verdictInfo.tone}`;

    // Clean DOM structure without innerHTML
    verdictEl.replaceChildren();

    const titleEl = document.createElement("strong");
    titleEl.textContent = verdictInfo.headline;
    titleEl.className = "ugi-b-verdict-title";

    const descEl = document.createElement("p");
    descEl.textContent = verdictInfo.guidance;
    descEl.className = "ugi-b-verdict-desc";

    verdictEl.append(titleEl, descEl);
  }

  // Export API
  const ugiBGuidedPresentation = {
    ugiBIsGuidedEnabled,
    ugiBUpdateGuidedVisibility,
    ugiBFormatReceiptVerdict,
    ugiBExtractVerifiedClaimIds,
    ugiBResetReceiptState,
    ugiBRenderReceiptVerdict,
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = ugiBGuidedPresentation;
  } else {
    global.ugiBGuidedPresentation = ugiBGuidedPresentation;
    Object.assign(global, ugiBGuidedPresentation);
  }
})(typeof window !== "undefined" ? window : globalThis);
