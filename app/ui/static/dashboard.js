const state = {
  currentRunId: "",
};

const text = (id, value) => {
  document.getElementById(id).textContent = value ?? "";
};

const apiJson = async (url, options = {}) => {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
};

const yesNo = (value) => (value ? "yes" : "no");

async function loadStatus() {
  const [health, config, readiness] = await Promise.all([
    apiJson("/health"),
    apiJson("/g2b/config"),
    apiJson("/g2b/real-readiness"),
  ]);
  text("status-health", health.status);
  text("status-real-api", yesNo(config.real_api_enabled));
  text("status-service-key", yesNo(config.service_key_configured));
  text("status-endpoint", yesNo(config.endpoint_path_configured));
  text("status-fixture", yesNo(config.fixture_mode));
  text("status-readiness", readiness.ready ? "ready" : "not ready");
}

function requestFromForm(form) {
  const data = new FormData(form);
  const payload = {
    mode: data.get("mode"),
    keyword: data.get("keyword") || "AI",
    page_no: Number(data.get("page_no") || 1),
    num_rows: Number(data.get("num_rows") || 5),
    include_reports: data.get("include_reports") === "on",
    include_document_analysis: data.get("include_document_analysis") === "on",
    document_text: data.get("document_text") || null,
    confirm_real_api_call: data.get("confirm_real_api_call") === "on",
  };
  const startDate = data.get("start_date");
  const endDate = data.get("end_date");
  if (startDate) payload.start_date = startDate;
  if (endDate) payload.end_date = endDate;
  return payload;
}

async function runRecommendation(event) {
  event.preventDefault();
  const form = event.currentTarget;
  text("run-state", "Running");
  const payload = requestFromForm(form);
  const result = await apiJson("/ops/run-recommendations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  document.getElementById("run-result").textContent = JSON.stringify(result, null, 2);
  text("run-state", "Done");
  state.currentRunId = result.run_id || "";
  await Promise.all([loadRuns(), loadRecommendations()]);
  if (state.currentRunId) await loadRunDetail(state.currentRunId);
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function loadRuns() {
  const payload = await apiJson("/ops/runs?limit=20");
  const body = document.getElementById("runs-body");
  body.innerHTML = "";
  for (const run of payload.runs || []) {
    const row = document.createElement("tr");
    for (const value of [
      run.created_at,
      run.run_id,
      run.mode,
      run.keyword,
      run.source_count,
      run.status,
      run.error_code || "",
    ]) {
      const cell = document.createElement("td");
      cell.textContent = value ?? "";
      row.appendChild(cell);
    }
    const action = document.createElement("td");
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = "View";
    button.addEventListener("click", () => loadRunDetail(run.run_id));
    action.appendChild(button);
    row.appendChild(action);
    body.appendChild(row);
  }
}

async function loadRecommendations(extraParams = {}) {
  const params = new URLSearchParams({ limit: "20", ...extraParams });
  const payload = await apiJson(`/ops/recommendations?${params.toString()}`);
  const body = document.getElementById("recommendations-body");
  body.innerHTML = "";
  for (const rec of payload.recommendations || []) {
    const row = document.createElement("tr");
    const cells = [
      rec.rank,
      rec.title,
      rec.agency,
      rec.budget_amount || "",
      rec.deadline || "",
      rec.total_score,
      rec.recommendation_label,
      rec.risk_count,
    ];
    for (const value of cells) {
      const cell = document.createElement("td");
      cell.textContent = value ?? "";
      row.appendChild(cell);
    }
    const action = document.createElement("td");
    if (rec.report_path) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = "Open";
      button.dataset.run = rec.run_id;
      button.dataset.notice = rec.notice_id;
      button.addEventListener("click", () => loadReportContent(rec.run_id, rec.notice_id));
      action.appendChild(button);
    }
    row.appendChild(action);
    body.appendChild(row);
  }
}

async function applyRecommendationFilters() {
  const extra = {};
  const minScore = document.getElementById("filter-min-score").value;
  const label = document.getElementById("filter-label").value;
  if (minScore) extra.min_score = minScore;
  if (label) extra.label = label;
  await loadRecommendations(extra);
}

async function loadRunDetail(runId) {
  state.currentRunId = runId;
  const [detail, reports] = await Promise.all([
    apiJson(`/ops/runs/${encodeURIComponent(runId)}`),
    apiJson(`/ops/reports/${encodeURIComponent(runId)}`),
  ]);
  const run = detail.run || {};
  document.getElementById("run-detail").textContent =
    `Run ${run.run_id || runId}: ${run.status || "unknown"} / ${run.source_count || 0} source notices`;
  await loadRecommendations({ run_id: runId, limit: "100" });
  const reportList = document.getElementById("report-list");
  reportList.innerHTML = "";
  for (const report of reports.reports || []) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = report.notice_id;
    button.addEventListener("click", () => loadReportContent(runId, report.notice_id));
    reportList.appendChild(button);
  }
}

async function loadReportContent(runId, noticeId) {
  const payload = await apiJson(
    `/ops/report-content/${encodeURIComponent(runId)}/${encodeURIComponent(noticeId)}`,
  );
  document.getElementById("report-viewer").textContent = payload.markdown || "";
}

document.addEventListener("DOMContentLoaded", async () => {
  document.getElementById("refresh-status").addEventListener("click", loadStatus);
  document.getElementById("refresh-runs").addEventListener("click", loadRuns);
  document.getElementById("run-form").addEventListener("submit", runRecommendation);
  document
    .getElementById("apply-rec-filters")
    .addEventListener("click", applyRecommendationFilters);
  await Promise.all([loadStatus(), loadRuns(), loadRecommendations()]);
});
