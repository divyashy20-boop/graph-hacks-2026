/**
 * UGI Friend B — Graph Status and Legend Display Module
 * UI-011: Graph and guided-state interaction module
 *
 * Implements truthful, accessible display of visible graph states:
 * loading, ready, empty, error/retry, truncation, and legend color cues.
 *
 * Rules:
 * - Prefixed with `ugiB`
 * - Exact alignment with UI_CONTRACT.md status types:
 *   SOURCE_ASSERTED, SOURCE_NEGATED, RULE_DERIVED, CONNECTED_ONLY,
 *   CONTRADICTED, HYPOTHESIS, UNKNOWN
 */

(function (global) {
  "use strict";

  /**
   * Determine the visual color tone for relationship and evidence verdicts.
   *
   * @param {string} status - Verdict status code.
   * @returns {string} CSS variable or hex color.
   */
  function ugiBStatusTone(status) {
    switch (status) {
      case "CONTRADICTED":
      case "SOURCE_NEGATED":
        return "var(--red, #df7a70)";
      case "UNKNOWN":
      case "HYPOTHESIS":
      case "CONNECTED_ONLY":
        return "var(--amber, #d5a861)";
      case "SOURCE_ASSERTED":
      case "RULE_DERIVED":
      default:
        return "var(--signal, #cf664c)";
    }
  }

  /**
   * Map status codes to human-readable descriptive titles.
   *
   * @param {string} status
   * @returns {string}
   */
  function ugiBStatusTitle(status) {
    const titles = {
      SOURCE_ASSERTED: "Direct source assertion",
      RULE_DERIVED: "Rule-derived conclusion",
      CONNECTED_ONLY: "Connection is not enough",
      SOURCE_NEGATED: "Source negates the relation",
      CONTRADICTED: "Source evidence conflicts",
      HYPOTHESIS: "Stored risk hypothesis",
      UNKNOWN: "No supported conclusion",
    };
    return titles[status] || (status ? status.replace(/_/g, " ") : "Unknown status");
  }

  /**
   * Return color mapping for graph entities according to type.
   *
   * @param {Object} entity
   * @returns {string} Hex color
   */
  function ugiBTypeColor(entity) {
    const type = entity?.entity_type || "";
    if (/service|component/i.test(type)) return "#cf664c"; // Warm signal red/rust
    if (/person/i.test(type)) return "#8d82b4";            // Violet
    return "#67a7c8";                                      // Blue / Other entity
  }

  /**
   * Set and manage the visible graph state panel (loading, error, retry).
   *
   * @param {Element} stateEl - The #graphstate element.
   * @param {Element} kickerEl - The #graphstatekicker element.
   * @param {Element} textEl - The #graphstatetext element.
   * @param {Element} retryBtn - The #retrygraph element.
   * @param {"loading"|"error"|null} kind - State kind, or null to hide.
   * @param {string} [message=""] - Detailed message for the user.
   */
  function ugiBSetGraphState(stateEl, kickerEl, textEl, retryBtn, kind, message = "") {
    if (!stateEl) return;

    if (!kind) {
      stateEl.hidden = true;
      stateEl.classList.remove("ugi-b-state-active");
      return;
    }

    stateEl.hidden = false;
    stateEl.classList.add("ugi-b-state-active");

    const isError = kind === "error";
    if (kickerEl) {
      kickerEl.textContent = isError
        ? "Unable to load evidence map"
        : "Loading evidence map";
    }

    if (textEl) {
      textEl.textContent =
        message ||
        (isError
          ? "Check the connection or dataset, then try again."
          : "Retrieving graph-backed records.");
    }

    if (retryBtn) {
      retryBtn.hidden = !isError;
    }
  }

  /**
   * Update the truncation notice when record count exceeds visible display limits.
   *
   * @param {Element} noticeEl - The #graphnotice banner element.
   * @param {Object} counts - Object containing entity, claim, event counts and truncated boolean.
   * @param {number} [entityLimit=60] - Visible entity display cap.
   */
  function ugiBUpdateTruncationNotice(noticeEl, counts, entityLimit = 60) {
    if (!noticeEl) return;

    const isTruncated =
      counts?.truncated === true || (counts?.Entity && counts.Entity > entityLimit);

    if (isTruncated) {
      noticeEl.hidden = false;
      noticeEl.className = "notice ugi-b-truncation-notice";
      noticeEl.textContent = `Display capped at ${entityLimit} entities for interactive map clarity. All ${counts.Entity || "stored"} entities and evidence remain preserved in persistent storage and accessible via inspector/search.`;
    } else {
      noticeEl.hidden = true;
      noticeEl.textContent = "";
    }
  }

  /**
   * Toggle the empty graph state placeholder.
   *
   * @param {Element} emptyEl - The #empty element.
   * @param {boolean} isEmpty - True if graph has zero records.
   * @param {"2d"|"3d"} viewMode - Active view mode.
   */
  function ugiBUpdateEmptyState(emptyEl, isEmpty, viewMode) {
    if (!emptyEl) return;

    // In 3D mode, the empty state must never overlap or conflict with canvas
    if (viewMode === "3d" || !isEmpty) {
      emptyEl.hidden = true;
    } else {
      emptyEl.hidden = false;
    }
  }

  // Export API
  const ugiBGraphStatus = {
    ugiBStatusTone,
    ugiBStatusTitle,
    ugiBTypeColor,
    ugiBSetGraphState,
    ugiBUpdateTruncationNotice,
    ugiBUpdateEmptyState,
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = ugiBGraphStatus;
  } else {
    global.ugiBGraphStatus = ugiBGraphStatus;
    Object.assign(global, ugiBGraphStatus);
  }
})(typeof window !== "undefined" ? window : globalThis);
