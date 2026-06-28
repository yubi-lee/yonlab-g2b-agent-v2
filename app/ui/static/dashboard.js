const state = {
  currentRunId: "",
  currentOpportunityMarkdown: "",
  currentOpportunityTitle: "yonlab-opportunity",
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
  const [health, config, readiness, packageInfo] = await Promise.all([
    apiJson("/health"),
    apiJson("/g2b/config"),
    apiJson("/g2b/real-readiness"),
    apiJson("/ops/package-info"),
  ]);
  text("status-health", health.status);
  text("status-package", packageInfo.package_version);
  text("status-real-api", yesNo(config.real_api_enabled));
  text("status-service-key", yesNo(config.service_key_configured));
  text("status-endpoint", yesNo(config.endpoint_path_configured));
  text("status-fixture", yesNo(config.fixture_mode));
  text("status-readiness", readiness.ready ? "ready" : "not ready");
  renderPackageInfo(packageInfo);
}

async function loadQualitySummary() {
  const summary = await apiJson("/ops/quality-summary");
  text("quality-total-runs", summary.total_runs);
  text("quality-summary-status", summary.summary_status || "unknown");
  text("quality-total-reports", summary.total_reports ?? 0);
  text("quality-real-reports", summary.real_report_count ?? 0);
  text("quality-total-recommendations", summary.total_recommendations);
  text("quality-average-score", summary.average_score);
  text("quality-strong", summary.strong_recommend_count);
  text("quality-recommend", summary.recommend_count);
  text("quality-consider", summary.consider_count);
  text("quality-not-recommended", summary.not_recommended_count);
  text("quality-latest-run", summary.latest_run_id || "none");
  text("quality-latest-status", summary.latest_run?.status || "none");
  text("quality-latest-at", summary.latest_run_created_at || "none");
  text("quality-latest-error", summary.latest_run?.error_code || "none");
  text("quality-real-runs", `${summary.real_run_count ?? 0} (${summary.real_mode_status || "empty"})`);
  text("quality-warnings", summary.warning_count ?? 0);
  text("quality-errors", summary.error_count ?? 0);
  text("opportunity-deployment-status", summary.summary_status === "failure" ? "review" : "ready");
  text("opportunity-latest-run", summary.latest_run_id || "none");
  text("opportunity-summary-status", summary.summary_status || "unknown");
  text("opportunity-real-reports", summary.real_report_count ?? 0);
  text("opportunity-service-key", yesNo(summary.service_key_exposed));
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
  if (payload.mode === "real" && !payload.confirm_real_api_call) {
    text("run-state", "Blocked: confirm real API call first");
    document.getElementById("run-result").textContent =
      "Real mode uses live G2B API quota. Check Confirm real API call before submitting.";
    return;
  }
  const result = await apiJson("/ops/run-recommendations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  document.getElementById("run-result").textContent = JSON.stringify(result, null, 2);
  text("run-state", "Done");
  state.currentRunId = result.run_id || "";
  await Promise.all([loadRuns(), loadRecommendations(), loadQualitySummary()]);
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


function opportunityQueryParams() {
  const params = new URLSearchParams({ limit: "20" });
  const keyword = document.getElementById("opportunity-keyword").value;
  const grade = document.getElementById("opportunity-grade").value;
  const risk = document.getElementById("opportunity-risk").value;
  const source = document.getElementById("opportunity-source").value;
  const sort = document.getElementById("opportunity-sort").value;
  if (keyword) params.set("keyword", keyword);
  if (grade) params.set("grade", grade);
  if (risk) params.set("risk_level", risk);
  if (source) params.set("source_type", source);
  if (sort) params.set("sort", sort);
  return params;
}

async function loadOpportunityInbox() {
  const payload = await apiJson("/ops/opportunity-inbox?" + opportunityQueryParams().toString());
  renderOpportunityInbox(payload);
}

function renderOpportunityInbox(payload) {
  const body = document.getElementById("opportunity-body");
  const empty = document.getElementById("opportunity-empty");
  body.innerHTML = "";
  const items = payload.items || [];
  empty.textContent = items.length
    ? `${items.length} opportunities loaded (${payload.source_mode || "unknown"}).`
    : payload.empty_state_message || "No opportunity data yet.";
  for (const item of items) {
    const row = document.createElement("tr");
    const values = [
      item.title,
      item.agency,
      item.deadline || "",
      formatBudget(item.budget),
      item.score,
      item.grade,
      item.risk_level,
      (item.source_badges || [item.source_type]).join(", "),
    ];
    for (const value of values) {
      const cell = document.createElement("td");
      cell.textContent = value ?? "";
      row.appendChild(cell);
    }
    const action = document.createElement("td");
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = "Review";
    button.addEventListener("click", () => loadOpportunityDetail(item.notice_id));
    action.appendChild(button);
    row.appendChild(action);
    body.appendChild(row);
  }
  if (!items.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 9;
    cell.textContent = "No opportunity data yet. Run a fixture job or controlled real run to populate this view.";
    row.appendChild(cell);
    body.appendChild(row);
  }
}

async function loadOpportunityDetail(noticeId) {
  const payload = await apiJson(`/ops/opportunity-inbox/${encodeURIComponent(noticeId)}`);
  const report = await apiJson(`/ops/opportunity-report/${encodeURIComponent(noticeId)}`);
  state.currentOpportunityMarkdown = report.markdown || "";
  state.currentOpportunityTitle = payload.title || noticeId;
  document.getElementById("opportunity-detail").textContent =
    `${payload.title} / ${payload.agency || "unknown agency"} / ${payload.source_type} / ${payload.score}??/ ${payload.risk_level}`;
  document.getElementById("opportunity-markdown").textContent = state.currentOpportunityMarkdown;
}

function downloadOpportunityMarkdown() {
  if (!state.currentOpportunityMarkdown) return;
  const blob = new Blob([state.currentOpportunityMarkdown], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${sanitizeFilename(state.currentOpportunityTitle)}.md`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function sanitizeFilename(value) {
  return (value || "yonlab-opportunity")
    .replace(/[^a-z0-9_-]+/gi, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80) || "yonlab-opportunity";
}
function formatBudget(value) {
  if (value === null || value === undefined || value === "") return "";
  const number = Number(value);
  if (Number.isNaN(number)) return value;
  return `${number.toLocaleString()}??;
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

function renderPackageInfo(packageInfo) {
  document.getElementById("package-summary").textContent =
    `${packageInfo.package_name} ${packageInfo.package_version} / default ${packageInfo.default_run_mode} / reports ${packageInfo.storage.report_dir}`;
  renderList("package-capabilities", packageInfo.capabilities || []);
  renderList("package-scripts", packageInfo.scripts || []);
}

function renderList(elementId, values) {
  const list = document.getElementById(elementId);
  list.innerHTML = "";
  for (const value of values) {
    const item = document.createElement("li");
    item.textContent = value;
    list.appendChild(item);
  }
}

function updateRunModeDefaults() {
  const mode = document.querySelector('[name="mode"]').value;
  const rowsInput = document.querySelector('[name="num_rows"]');
  const submitButton = document.querySelector('#run-form button[type="submit"]');
  if (mode === "real") {
    rowsInput.value = "3";
    submitButton.textContent = "Run controlled real job";
  } else {
    rowsInput.value = "5";
    submitButton.textContent = "Run fixture-safe job";
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  document.getElementById("refresh-status").addEventListener("click", loadStatus);
  document.getElementById("refresh-quality").addEventListener("click", loadQualitySummary);
  document.getElementById("refresh-runs").addEventListener("click", loadRuns);
  document.getElementById("refresh-opportunities").addEventListener("click", loadOpportunityInbox);
  document.getElementById("apply-opportunity-filters").addEventListener("click", loadOpportunityInbox);
  document.getElementById("download-opportunity-markdown").addEventListener("click", downloadOpportunityMarkdown);
  document.getElementById("run-form").addEventListener("submit", runRecommendation);
  document.querySelector('[name="mode"]').addEventListener("change", updateRunModeDefaults);
  document
    .getElementById("apply-rec-filters")
    .addEventListener("click", applyRecommendationFilters);
  updateRunModeDefaults();
  await Promise.all([loadStatus(), loadQualitySummary(), loadOpportunityInbox(), loadRuns(), loadRecommendations()]);
});
