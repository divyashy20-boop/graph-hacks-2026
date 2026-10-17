/* Non-invasive UI adapter: keeps the collaborator's 2D/3D renderer unmodified. */
(() => {
  "use strict";
  const el = (name) => document.getElementById(name);
  let receipt = null;
  let ownerDataset = null;

  function resetReceipt() {
    receipt = null;
    ownerDataset = null;
    el("refreshreceipt").disabled = true;
    el("guidedverdict").hidden = true;
    el("guidedverdict").textContent = "";
    el("guidedresult").textContent = "";
    el("receiptreport").textContent = "";
  }

  async function withProgress(button, action) {
    const target = el(button);
    const status = el("guidedstatus");
    target.disabled = true;
    status.classList.remove("error");
    status.textContent = "Checking graph evidence…";
    try {
      const message = await action();
      status.textContent = message;
    } catch (err) {
      status.classList.add("error");
      status.textContent = err.message || "Request failed";
    } finally {
      target.disabled = button === "refreshreceipt" && !receipt;
    }
  }

  function showVerdict(message, safe) {
    const verdict = el("guidedverdict");
    verdict.hidden = false;
    verdict.textContent = message;
    verdict.style.borderLeft = `3px solid ${safe ? "var(--signal)" : "var(--amber)"}`;
  }

  async function runGuided() {
    resetReceipt();
    const query = el("guidedquestion").value.trim();
    if (query.length < 5) throw Error("Enter a question with at least five characters.");
    const dataset = el("dataset").value.trim();
    const key = el("access").value;
    const response = await api("/api/agent/guided", {query});
    el("guidedresult").textContent = JSON.stringify(response.result || response, null, 2);
    receipt = response.receipt_id || null;
    ownerDataset = {dataset, key};
    el("refreshreceipt").disabled = !receipt;
    const verdict = response.result?.verdict || response.status || "UNKNOWN";
    const freshness = response.freshness || "not available";
    showVerdict(`Graph verdict: ${verdict} · Receipt: ${freshness}${response.reason ? " · " + response.reason : ""}`, verdict !== "UNKNOWN" && freshness === "VALID");
    // Highlight exactly verified claim IDs, not hypotheses, if the renderer supports it.
    if (Array.isArray(response.result?.verified_claim_ids) && response.result.verified_claim_ids.length) {
      queryHighlights = new Set(response.result.verified_claim_ids);
      render(false);
    }
    return receipt ? "Guided answer recorded; recheck freshness before reuse." : "No reusable receipt recorded.";
  }

  async function checkReceipt() {
    if (!receipt || !ownerDataset) throw Error("No saved receipt for this selection.");
    if (ownerDataset.dataset !== el("dataset").value.trim() || ownerDataset.key !== el("access").value) {
      resetReceipt();
      throw Error("Dataset or access key changed; run a fresh graph question.");
    }
    const response = await api("/api/agent/receipts/" + encodeURIComponent(receipt) + "/freshness");
    el("receiptreport").textContent = JSON.stringify(response, null, 2);
    const reusable = response.safe_to_reuse === true;
    showVerdict(`Receipt ${response.freshness || "UNKNOWN"}. ${reusable ? "Safe at time of check." : "Do not reuse this answer; investigate again."}`, reusable);
    return reusable ? "Fresh evidence checked; valid now." : "Receipt not reusable. Obtain a fresh answer.";
  }

  el("guidedrun").addEventListener("click", () => withProgress("guidedrun", runGuided));
  el("refreshreceipt").addEventListener("click", () => withProgress("refreshreceipt", checkReceipt));
  for (const id of ["dataset", "access", "preset"]) {
    el(id).addEventListener("change", resetReceipt);
  }
  el("guidedquestion").addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      el("guidedrun").click();
    }
  });
  api("/health").then((health) => {
    el("guidedpanel").hidden = !(health.guided_agent_enabled && health.memory_enabled);
  }).catch(() => { el("guidedpanel").hidden = true; });
})();
