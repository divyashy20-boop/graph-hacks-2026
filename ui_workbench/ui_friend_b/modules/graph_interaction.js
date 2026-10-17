/**
 * UGI Friend B — 2D Evidence Map Interaction Module
 * UI-011: Graph and guided-state interaction module
 *
 * Provides resilient, accessible 2D selection, highlighting, focus dimming,
 * and routing back to the source inspector path.
 *
 * Rules:
 * - All identifiers prefixed with `ugiB`
 * - Preserves existing graph semantics (never converts uncertain edges into facts)
 * - Safe for browser and test environments
 */

(function (global) {
  "use strict";

  /**
   * Build the active selection context containing sets of highlighted entities,
   * claims, and whole relation events.
   *
   * @param {string|null} selectedRecordId - ID of the currently selected record.
   * @param {Object} graphData - Object with entities, claims, and events arrays.
   * @returns {{entities: Set<string>, claims: Set<string>, events: Set<string>}}
   */
  function ugiBBuildSelectionContext(selectedRecordId, graphData) {
    const context = {
      entities: new Set(),
      claims: new Set(),
      events: new Set(),
    };

    if (!selectedRecordId || !graphData) {
      return context;
    }

    const entities = Array.isArray(graphData.entities) ? graphData.entities : [];
    const claims = Array.isArray(graphData.claims) ? graphData.claims : [];
    const events = Array.isArray(graphData.events) ? graphData.events : [];

    // Find the record by ID across entities, claims, and events
    let selected = null;
    for (const record of entities) {
      if (record && record.id === selectedRecordId) {
        selected = record;
        break;
      }
    }
    if (!selected) {
      for (const record of claims) {
        if (record && record.id === selectedRecordId) {
          selected = record;
          break;
        }
      }
    }
    if (!selected) {
      for (const record of events) {
        if (record && record.id === selectedRecordId) {
          selected = record;
          break;
        }
      }
    }

    if (!selected) {
      return context;
    }

    // Case 1: Binary Claim selected
    if (selected.kind === "Claim") {
      context.claims.add(selected.id);
      if (selected.subject_id) context.entities.add(selected.subject_id);
      if (selected.object_id) context.entities.add(selected.object_id);
      return context;
    }

    // Case 2: Whole RelationEvent selected
    if (selected.kind === "RelationEvent") {
      context.events.add(selected.id);
      if (Array.isArray(selected.participants)) {
        for (const participant of selected.participants) {
          if (participant && participant.entity_id) {
            context.entities.add(participant.entity_id);
          }
        }
      }
      return context;
    }

    // Case 3: Entity selected -> highlight connected claims and events
    context.entities.add(selected.id);

    for (const claim of claims) {
      if (!claim) continue;
      if (claim.subject_id === selected.id || claim.object_id === selected.id) {
        context.claims.add(claim.id);
        if (claim.subject_id) context.entities.add(claim.subject_id);
        if (claim.object_id) context.entities.add(claim.object_id);
      }
    }

    for (const event of events) {
      if (!event) continue;
      const participants = Array.isArray(event.participants) ? event.participants : [];
      const isParticipant = participants.some(
        (p) => p && p.entity_id === selected.id
      );
      if (isParticipant) {
        context.events.add(event.id);
        for (const p of participants) {
          if (p && p.entity_id) context.entities.add(p.entity_id);
        }
      }
    }

    return context;
  }

  /**
   * Determine the visual opacity of an element based on selection context.
   *
   * @param {Object} context - Context object returned from ugiBBuildSelectionContext.
   * @param {"entities"|"claims"|"events"} kind - The record collection type.
   * @param {string} id - The ID of the item.
   * @param {number} [baseOpacity=1] - Full opacity when item is active or no selection.
   * @param {number} [dimmedOpacity=0.15] - Dimmed opacity when another item is selected.
   * @returns {number}
   */
  function ugiBFocusOpacity(context, kind, id, baseOpacity = 1, dimmedOpacity = 0.15) {
    if (!context) return baseOpacity;
    const hasSelection =
      context.entities.size > 0 ||
      context.claims.size > 0 ||
      context.events.size > 0;
    if (!hasSelection) return baseOpacity;

    const set = context[kind];
    return set && set.has(id) ? baseOpacity : dimmedOpacity;
  }

  /**
   * Select a record and trigger inspector and renderer updates.
   *
   * @param {Object} record - The graph record to select.
   * @param {Object} callbacks - Handler hooks.
   * @param {Function} callbacks.onInspect - Async or sync callback to inspect record.
   * @param {Function} [callbacks.onRender] - Render refresh callback.
   * @param {Function} [callbacks.onOrbitSync] - 3D orbit sync callback.
   * @param {Function} [callbacks.onError] - Error notification callback.
   */
  function ugiBSelectRecord(record, callbacks) {
    if (!record || !record.id) return;

    if (typeof callbacks?.onInspect === "function") {
      try {
        const result = callbacks.onInspect(record);
        if (result && typeof result.catch === "function") {
          result.catch((error) => {
            if (typeof callbacks?.onError === "function") {
              callbacks.onError(error);
            }
          });
        }
      } catch (error) {
        if (typeof callbacks?.onError === "function") {
          callbacks.onError(error);
        }
      }
    }

    if (typeof callbacks?.onRender === "function") {
      callbacks.onRender(false);
    }

    if (typeof callbacks?.onOrbitSync === "function") {
      callbacks.onOrbitSync(true);
    }
  }

  /**
   * Clear the active selection and reset inspector to initial state.
   *
   * @param {Object} callbacks - Handler hooks.
   * @param {Function} [callbacks.onClearInspector] - Callback to reset inspector.
   * @param {Function} [callbacks.onRender] - Render refresh callback.
   * @param {Function} [callbacks.onOrbitSync] - 3D orbit sync callback.
   */
  function ugiBClearSelection(callbacks) {
    if (typeof callbacks?.onClearInspector === "function") {
      callbacks.onClearInspector();
    }
    if (typeof callbacks?.onRender === "function") {
      callbacks.onRender(false);
    }
    if (typeof callbacks?.onOrbitSync === "function") {
      callbacks.onOrbitSync(false);
    }
  }

  /**
   * Bind accessible keyboard and click pick handling to an SVG/HTML node.
   *
   * @param {Element} node - DOM/SVG element to bind.
   * @param {Object} record - The associated record.
   * @param {Function} onSelect - Selection callback receiving the record.
   */
  function ugiBBindPick(node, record, onSelect) {
    if (!node || !record) return;

    const label =
      record.name ||
      record.predicate ||
      record.relation_type ||
      record.kind ||
      "Stored record";

    node.setAttribute("tabindex", "0");
    node.setAttribute("role", "button");
    node.setAttribute("aria-label", `Inspect ${label}`);
    node.classList.add("ugi-b-pickable");

    const handler = (event) => {
      if (event) {
        event.stopPropagation();
      }
      if (typeof onSelect === "function") {
        onSelect(record);
      }
    };

    node.addEventListener("click", handler);
    node.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        handler(event);
      }
    });
  }

  /**
   * Filter claims or events against an `as_of` date parameter.
   * If `asOfDate` is empty/null, returns all records.
   *
   * @param {Array<Object>} records - List of claims or events.
   * @param {string|null} asOfDate - ISO date string (e.g. "2021-06-01").
   * @returns {Array<Object>}
   */
  function ugiBFilterAsOf(records, asOfDate) {
    if (!asOfDate || !Array.isArray(records)) return records || [];

    const targetDate = new Date(asOfDate).getTime();
    if (isNaN(targetDate)) return records;

    return records.filter((record) => {
      if (!record) return false;
      const validFrom = record.valid_from ? new Date(record.valid_from).getTime() : -Infinity;
      const validTo = record.valid_to ? new Date(record.valid_to).getTime() : Infinity;
      return targetDate >= validFrom && targetDate <= validTo;
    });
  }

  // Export API
  const ugiBGraphInteraction = {
    ugiBBuildSelectionContext,
    ugiBFocusOpacity,
    ugiBSelectRecord,
    ugiBClearSelection,
    ugiBBindPick,
    ugiBFilterAsOf,
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = ugiBGraphInteraction;
  } else {
    global.ugiBGraphInteraction = ugiBGraphInteraction;
    Object.assign(global, ugiBGraphInteraction);
  }
})(typeof window !== "undefined" ? window : globalThis);
