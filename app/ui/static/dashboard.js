const state = {
  currentRunId: "",
  currentOpportunityId: "",
  currentOpportunityMarkdown: "",
  currentOpportunityTitle: "yonlab-opportunity",
  currentDailyReviewMarkdown: "",
  currentDecisionMemoId: "",
  currentDecisionMemoMarkdown: "",
  currentManualDecision: "hold",
};

const safeValue = (value, fallback = "No data") => {
  if (value === null || value === undefined || value === "") return fallback;
  return value;
};

const safeText = (id, value, fallback = "No data") => {
  const element = document.getElementById(id);
  if (!element) return;
  element.textContent = safeValue(value, fallback);
};

const text = safeText;

const apiJson = async (url, options = {}) => {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
};

const yesNo = (value) => (value ? "yes" : "no");

function setSectionError(ids, message) {
  for (const id of ids) {
    safeText(id, message || "Error");
  }
}

async function loadSection(name, loader, errorIds = []) {
  try {
    await loader();
  } catch (error) {
    console.error(`${name} failed`, error);
    setSectionError(errorIds, "Error");
  }
}

async function loadStatus() {
  const [health, config, readiness, packageInfo] = await Promise.all([
    apiJson("/health"),
    apiJson("/g2b/config"),
    apiJson("/g2b/real-readiness"),
    apiJson("/ops/package-info"),
  ]);
  safeText("status-health", health.status);
  safeText("status-package", packageInfo.package_version);
  safeText("status-real-api", yesNo(config.real_api_enabled));
  safeText("status-service-key", yesNo(config.service_key_configured));
  safeText("status-endpoint", yesNo(config.endpoint_path_configured));
  safeText("status-fixture", yesNo(config.fixture_mode));
  safeText("status-readiness", readiness.ready ? "ready" : "not ready");
  renderPackageInfo(packageInfo);
}

async function loadQualitySummary() {
  const summary = await apiJson("/ops/quality-summary");
  safeText("quality-total-runs", summary.total_runs, 0);
  safeText("quality-summary-status", summary.summary_status || "unknown");
  safeText("quality-total-reports", summary.total_reports, 0);
  safeText("quality-real-reports", summary.real_report_count, 0);
  safeText("quality-total-recommendations", summary.total_recommendations, 0);
  safeText("quality-average-score", summary.average_score, 0);
  safeText("quality-strong", summary.strong_recommend_count, 0);
  safeText("quality-recommend", summary.recommend_count, 0);
  safeText("quality-consider", summary.consider_count, 0);
  safeText("quality-not-recommended", summary.not_recommended_count, 0);
  safeText("quality-latest-run", summary.latest_run_id || "none");
  safeText("quality-latest-status", summary.latest_run?.status || "none");
  safeText("quality-latest-at", summary.latest_run_created_at || "none");
  safeText("quality-latest-error", summary.latest_run?.error_code || "none");
  safeText("quality-real-runs", `${summary.real_run_count ?? 0} (${summary.real_mode_status || "empty"})`);
  safeText("quality-warnings", summary.warning_count, 0);
  safeText("quality-errors", summary.error_count, 0);
  safeText("opportunity-deployment-status", summary.summary_status === "failure" ? "review" : "ready");
  safeText("opportunity-latest-run", summary.latest_run_id || "none");
  safeText("opportunity-summary-status", summary.summary_status || "unknown");
  safeText("opportunity-real-reports", summary.real_report_count, 0);
  safeText("opportunity-service-key", yesNo(summary.service_key_exposed));
}

async function loadDailyReviewPack() {
  const pack = await apiJson("/ops/daily-review-pack");
  renderDailyReviewPack(pack || {});
  renderSourceModeBanner(pack || {});
  renderPriorityLegend(pack.priority_legend || {});
}

async function loadSafeDailyStatus() {
  const payload = await apiJson("/ops/safe-daily-status");
  renderSafeDailyStatus(payload || {});
}

async function loadReviewBoard() {
  const payload = await apiJson("/ops/review-board");
  renderReviewBoard(payload || {});
}

async function loadDecisionMemo(noticeId) {
  const safeNoticeId = String(noticeId || "").trim();
  if (!safeNoticeId) {
    state.currentDecisionMemoId = "";
    state.currentDecisionMemoMarkdown = "";
    renderDecisionMemo(emptyDecisionMemo());
    return;
  }
  const payload = await apiJson(`/ops/decision-memo/${encodeURIComponent(safeNoticeId)}`);
  state.currentDecisionMemoId = payload.notice_id || safeNoticeId;
  state.currentDecisionMemoMarkdown = payload.export_blocks?.markdown || "";
  const input = document.getElementById("decision-memo-notice-id");
  if (input) input.value = state.currentDecisionMemoId;
  renderDecisionMemo(payload || emptyDecisionMemo());
}

function renderDailyReviewPack(pack) {
  state.currentDailyReviewMarkdown = pack.markdown_report || "";
  safeText("daily-review-status", pack.status || "empty");
  safeText("daily-review-generated-at", pack.generated_at || "none");
  safeText("daily-review-latest-run", pack.latest_run_id || "none");
  safeText("daily-review-total-items", pack.total_items, 0);
  safeText("daily-review-p1", pack.p1_count, 0);
  safeText("daily-review-p2", pack.p2_count, 0);
  safeText("daily-review-p3", pack.p3_count, 0);
  safeText("daily-review-hold", pack.hold_count, 0);
  safeText("daily-review-no-go", pack.no_go_count, 0);
  renderExecutiveSummary(pack.executive_summary || {});
  renderList(
    "daily-review-top-items",
    (pack.top_items || []).map((item) =>
      `${item.bid_priority || "Hold"} / ${item.notice_id || ""} / ${item.title || "No title"} / ${item.score ?? 0}`,
    ),
    "No opportunity data",
  );
  renderList(
    "daily-review-today-actions",
    (pack.today_actions || []).map((item) =>
      `${item.bid_priority || "Hold"} / ${item.notice_id || ""}: ${item.today_action || "Review"}`,
    ),
    "No opportunity data",
  );
  renderList(
    "daily-review-document-actions",
    (pack.document_actions || []).map((item) =>
      `${item.notice_id || ""}: ${item.document_action || "Check documents"}${formatDocumentGroups(item.required_documents_grouped)}`,
    ),
    "No opportunity data",
  );
  const risk = pack.risk_summary || {};
  renderList(
    "daily-review-risk-summary",
    [
      `high: ${risk.high_risk_count ?? 0}`,
      `medium: ${risk.medium_risk_count ?? 0}`,
      `low: ${risk.low_risk_count ?? 0}`,
    ],
    "No opportunity data",
  );
  safeText(
    "daily-review-markdown",
    state.currentDailyReviewMarkdown || pack.empty_state_message || "No opportunity data",
  );
}

function renderExecutiveSummary(summary) {
  const element = document.getElementById("daily-review-executive-summary");
  if (!element) return;
  const lines = Array.isArray(summary.lines) ? summary.lines : [];
  element.textContent = lines.length
    ? lines.join(" ")
    : "No opportunity data yet. Run a fixture-safe job or approved controlled real run first.";
}

function renderSourceModeBanner(payload) {
  safeText("source-mode-current", payload.source_mode || "empty");
  safeText("source-mode-message", payload.source_mode_message || "Source mode empty: no searchable saved notices yet.");
  safeText("source-mode-latest-run", payload.latest_run_id || "none");
  safeText("source-mode-latest-at", payload.latest_run_created_at || "none");
  safeText("source-mode-real-reports", payload.real_report_count, 0);
  safeText("source-mode-total-items", payload.total_items, 0);
  renderList(
    "source-mode-next-actions",
    payload.empty_state_next_actions || [],
    "Saved runs are empty. Use the approved controlled real run script with explicit confirmation if real data is needed.",
  );
}

function renderPriorityLegend(legend) {
  const entries = Object.entries(legend || {});
  renderList(
    "priority-legend",
    entries.map(([priority, description]) => `${priority}: ${description}`),
    "P1: same-day priority review / P2: next candidate review / P3: spare capacity check / Hold: monitor/exclude candidate",
  );
}

function renderSafeDailyStatus(payload) {
  safeText("safe-daily-current-status", payload.status || "empty");
  safeText("safe-daily-latest-result", payload.latest_result || "none");
  safeText("safe-daily-latest-log", payload.latest_log_filename || "none");
  safeText("safe-daily-real-api", yesNo(payload.real_api_call_attempted));
  safeText("safe-daily-service-key", yesNo(payload.service_key_exposed));
  safeText("safe-daily-target", payload.scheduler_target_expected || "scripts/run_ops_safe_daily.ps1");
  safeText("safe-daily-note", payload.note || "Safe daily status is based on local log metadata only.");
}

function renderReviewBoard(payload) {
  const statusCounts = payload.status_counts || {};
  safeText("review-board-generated-at", payload.generated_at || "none");
  safeText("review-board-source", payload.source || "empty");
  safeText("review-board-total-count", payload.total_count, 0);
  safeText("review-board-active-count", payload.active_count, 0);
  safeText("review-board-go", statusCounts.go, 0);
  safeText("review-board-reviewing", statusCounts.reviewing, 0);
  safeText("review-board-shortlisted", statusCounts.shortlisted, 0);
  safeText("review-board-hold", statusCounts.hold, 0);

  const cards = Array.isArray(payload.cards) ? payload.cards : [];
  const nextActions = Array.isArray(payload.deadline_first_actions)
    ? payload.deadline_first_actions
    : [];
  const emptyMessage = cards.some((card) => (card.count || 0) > 0)
    ? "Click a review card to focus the Opportunity Inbox."
    : "No active review board items yet. Save local review status from Opportunity Detail to build the board.";
  safeText("review-board-empty", emptyMessage);

  const cardContainer = document.getElementById("review-board-cards");
  if (cardContainer) {
    cardContainer.innerHTML = "";
    for (const card of cards) {
      cardContainer.appendChild(renderReviewBoardCard(card));
    }
  }

  renderNextActionBoard(nextActions);
}

function renderReviewBoardCard(card) {
  const article = document.createElement("article");
  article.className = "review-board-card";

  const button = document.createElement("button");
  button.type = "button";
  button.textContent = `${safeValue(card.review_status_ko || card.review_status, "review")} (${card.count ?? 0})`;
  button.addEventListener("click", () => applyReviewBoardFilter(card.filter_payload || {}));
  article.appendChild(button);

  const meta = document.createElement("div");
  meta.className = "review-board-card-meta";
  meta.textContent = card.count ? "Active-state-first review slice" : "No active items";
  article.appendChild(meta);

  const list = document.createElement("ul");
  const items = Array.isArray(card.items) ? card.items : [];
  if (!items.length) {
    const item = document.createElement("li");
    item.textContent = "No active items";
    list.appendChild(item);
  } else {
    for (const boardItem of items) {
      const item = document.createElement("li");
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = [
        safeValue(boardItem.title, "No title"),
        safeValue(boardItem.deadline, "No deadline"),
        `${boardItem.score ?? 0}pt`,
        safeValue(boardItem.next_action, "Review"),
      ].join(" / ");
      button.addEventListener("click", () => openReviewBoardItem(boardItem));
      item.appendChild(button);
      list.appendChild(item);
    }
  }
  article.appendChild(list);
  return article;
}

function renderNextActionBoard(items) {
  const list = document.getElementById("review-board-next-actions");
  if (!list) return;
  list.innerHTML = "";
  const safeItems = Array.isArray(items) ? items : [];
  if (!safeItems.length) {
    const empty = document.createElement("li");
    empty.textContent = "No deadline-first next actions yet.";
    list.appendChild(empty);
    return;
  }
  for (const item of safeItems) {
    const entry = document.createElement("li");
    entry.className = "review-board-next-action";
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = safeValue(item.review_status, "review");
    button.addEventListener("click", () => openReviewBoardItem(item));
    const summary = document.createElement("span");
    summary.textContent = [
      safeValue(item.deadline, "No deadline"),
      safeValue(item.title, "No title"),
      safeValue(item.next_action, "Review"),
    ].join(" / ");
    entry.appendChild(button);
    entry.appendChild(summary);
    list.appendChild(entry);
  }
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
  safeText("run-state", "Running");
  const payload = requestFromForm(form);
  if (payload.mode === "real" && !payload.confirm_real_api_call) {
    safeText("run-state", "Blocked: confirm real API call first");
    const result = document.getElementById("run-result");
    if (result) {
      result.textContent =
        "Real mode uses live G2B API quota. Check Confirm real API call before submitting.";
    }
    return;
  }
  const result = await apiJson("/ops/run-recommendations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const resultBox = document.getElementById("run-result");
  if (resultBox) resultBox.textContent = JSON.stringify(result, null, 2);
  safeText("run-state", "Done");
  state.currentRunId = result.run_id || "";
  await Promise.allSettled([
    loadRuns(),
    loadRecommendations(),
    loadQualitySummary(),
    loadOpportunityInbox(),
    loadReviewBoard(),
    loadDailyReviewPack(),
  ]);
  if (state.currentRunId) await loadRunDetail(state.currentRunId);
}

function syncInboxDefaultFilters() {
  const hideArchivedNoGo = document.getElementById("opportunity-hide-archived-no-go");
  const sort = document.getElementById("opportunity-sort");
  if (hideArchivedNoGo && !hideArchivedNoGo.checked) {
    hideArchivedNoGo.checked = true;
  }
  if (sort && !sort.value) {
    sort.value = "score_desc";
  }
}

function opportunityQueryParams() {
  const params = new URLSearchParams({ limit: "20" });
  const keyword = document.getElementById("opportunity-keyword")?.value;
  const grade = document.getElementById("opportunity-grade")?.value;
  const risk = document.getElementById("opportunity-risk")?.value;
  const reviewStatus = document.getElementById("opportunity-review-filter")?.value;
  const source = document.getElementById("opportunity-source")?.value;
  const sort = document.getElementById("opportunity-sort")?.value;
  const shortlistedOnly = document.getElementById("opportunity-shortlisted-only")?.checked;
  const hideArchivedNoGo = document.getElementById("opportunity-hide-archived-no-go")?.checked;
  if (keyword) params.set("keyword", keyword);
  if (grade) params.set("grade", grade);
  if (risk) params.set("risk_level", risk);
  if (reviewStatus) params.set("review_status", reviewStatus);
  if (source) params.set("source_type", source);
  if (sort) params.set("sort", sort);
  if (shortlistedOnly) params.set("shortlisted_only", "true");
  if (hideArchivedNoGo) params.set("hide_archived_no_go", "true");
  return params;
}

async function applyReviewBoardFilter(filterPayload = {}) {
  const reviewStatus = document.getElementById("opportunity-review-filter");
  const shortlistedOnly = document.getElementById("opportunity-shortlisted-only");
  const hideArchivedNoGo = document.getElementById("opportunity-hide-archived-no-go");
  const sort = document.getElementById("opportunity-sort");

  if (reviewStatus) reviewStatus.value = filterPayload.review_status || "";
  if (shortlistedOnly) shortlistedOnly.checked = Boolean(filterPayload.shortlisted_only);
  if (hideArchivedNoGo) hideArchivedNoGo.checked = filterPayload.hide_archived_no_go !== false;
  if (sort) sort.value = filterPayload.sort || "score_desc";
  syncInboxDefaultFilters();
  await loadOpportunityInbox();
}

async function openReviewBoardItem(item = {}) {
  const noticeId = item.notice_id || "";
  await applyReviewBoardFilter(item.filter_payload || {});
  if (noticeId) {
    await loadDecisionMemo(noticeId);
  }
}

async function loadOpportunityInbox() {
  const payload = await apiJson("/ops/opportunity-inbox?" + opportunityQueryParams().toString());
  renderOpportunityInbox(payload || {});
}

function renderOpportunityInbox(payload) {
  const body = document.getElementById("opportunity-body");
  const empty = document.getElementById("opportunity-empty");
  if (!body) return;
  body.innerHTML = "";
  const items = Array.isArray(payload.items) ? payload.items : [];
  if (empty) {
    empty.textContent = items.length
      ? `${items.length} opportunities loaded (${payload.source_mode || "unknown"}).`
      : `${payload.empty_state_message || "No opportunity data yet."} ${(payload.empty_state_next_actions || []).join(" ")}`;
  }
  renderSourceModeBanner(payload || {});
  renderPriorityLegend(payload.priority_legend || {});
  for (const item of items) {
    const row = document.createElement("tr");
    const values = [
      item.title,
      item.agency,
      item.deadline || "",
      formatBudget(item.budget),
      item.score,
      item.grade,
      item.review_status_ko || item.review_status,
      item.decision_label_ko,
      item.bid_priority,
      item.risk_level,
      item.next_action || item.action_plan?.today_action,
      (item.source_badges || [item.source_type]).filter(Boolean).join(", "),
    ];
    for (const value of values) {
      const cell = document.createElement("td");
      cell.textContent = safeValue(value, "");
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
    cell.colSpan = 13;
    cell.textContent = "No opportunity data yet. Run a fixture job or use the approved controlled real run script with explicit confirmation to populate this view.";
    row.appendChild(cell);
    body.appendChild(row);
  }
}

async function loadOpportunityDetail(noticeId) {
  const payload = await apiJson(`/ops/opportunity-inbox/${encodeURIComponent(noticeId)}`);
  const report = await apiJson(`/ops/opportunity-report/${encodeURIComponent(noticeId)}`);
  state.currentOpportunityId = noticeId;
  state.currentOpportunityMarkdown = report.markdown || "";
  state.currentOpportunityTitle = payload.title || noticeId;
  renderOpportunityDetail(payload);
  renderOpportunityReviewStatus(payload);
  safeText("opportunity-markdown", state.currentOpportunityMarkdown || "No report content");
}

function renderOpportunityDetail(payload) {
  safeText(
    "opportunity-detail",
    `${payload.title || "No title"} / ${payload.agency || "unknown agency"} / ${payload.source_type || "unknown"} / ${payload.score ?? 0}점 / ${payload.decision_label_ko || "확인 필요"} / ${payload.bid_priority || "Hold"} / ${payload.go_no_go_recommendation_ko || "확인 필요"}`,
  );
  const detail = document.getElementById("opportunity-detail-fields");
  if (!detail) return;
  detail.innerHTML = "";
  detail.appendChild(renderFieldGroup("Decision Reasons", payload.decision_reasons || []));
  const actionPlan = payload.action_plan || {};
  detail.appendChild(renderFieldGroup("Action Plan", [
    actionPlan.today_action,
    actionPlan.document_action,
    actionPlan.business_action,
    actionPlan.go_no_go_action,
  ]));
  detail.appendChild(renderFieldGroup("Required Documents", requiredDocumentLines(payload)));
  detail.appendChild(renderFieldGroup(
    "Risk Categories",
    (payload.risk_categories || []).map((risk) => `${risk.category_ko || risk.category || "risk"}: ${risk.level || "unknown"}`),
  ));
}

function emptyDecisionMemo() {
  return {
    status: "empty",
    notice_id: "",
    notice: { title: "", agency: "", deadline: "" },
    yonlab_fit_summary: { fit_reasons: [], concern_reasons: [] },
    risk_summary: {
      eligibility_risks: [],
      document_risks: [],
      schedule_risks: [],
      commercial_risks: [],
    },
    deadline_next_action: {
      deadline: "",
      urgency: "unknown",
      next_action: "Select a Review Board item or enter a known notice id.",
    },
    recommended_decision: {
      value: "Hold",
      rationale: "No local-safe Decision Memo has been selected yet.",
    },
    preparation_actions: [],
    required_documents: [],
    export_blocks: {
      markdown: "",
      short_summary: "Select a Review Board item or enter a known notice id.",
    },
  };
}

function normalizeManualDecision(value) {
  const normalized = String(value || "").trim().toLowerCase();
  if (["prepare", "review", "hold", "reject"].includes(normalized)) return normalized;
  if (normalized === "go") return "prepare";
  if (normalized === "reviewing") return "review";
  if (normalized === "no_go" || normalized === "no-go") return "reject";
  return "hold";
}

function selectManualDecision(value) {
  const normalized = normalizeManualDecision(value);
  state.currentManualDecision = normalized;
  const manualOptions = {
    prepare: document.getElementById("decision-memo-manual-prepare"),
    review: document.getElementById("decision-memo-manual-review"),
    hold: document.getElementById("decision-memo-manual-hold"),
    reject: document.getElementById("decision-memo-manual-reject"),
  };
  for (const [optionValue, element] of Object.entries(manualOptions)) {
    if (element) element.checked = optionValue === normalized;
  }
}

function renderManualDecision(payload) {
  const memo = payload || {};
  const manualDecision = memo.manual_decision || {};
  const decisionValue = normalizeManualDecision(
    manualDecision.decision || memo.recommended_decision?.value || state.currentManualDecision,
  );
  const note = document.getElementById("decision-memo-manual-note");
  if (note) {
    note.value = manualDecision.note || "";
  }
  selectManualDecision(decisionValue);
  safeText(
    "decision-memo-manual-message",
    manualDecision.updated_at ? `Saved ${manualDecision.updated_at}` : "Local only.",
  );
}

function renderDecisionMemo(payload) {
  const memo = payload || emptyDecisionMemo();
  const notice = memo.notice || {};
  const fitSummary = memo.yonlab_fit_summary || {};
  const riskSummary = memo.risk_summary || {};
  const nextAction = memo.deadline_next_action || {};
  const decision = memo.recommended_decision || {};
  const input = document.getElementById("decision-memo-notice-id");
  if (input) {
    input.value = memo.notice_id || state.currentDecisionMemoId || "";
  }

  safeText("decision-memo-status", memo.status || "empty");
  safeText("decision-memo-decision", decision.value || "Hold");
  safeText(
    "decision-memo-rationale",
    decision.rationale || "No local-safe Decision Memo has been selected yet.",
  );

  const summary = memo.status === "not_found"
    ? memo.export_blocks?.short_summary || "Decision memo unavailable."
    : [
        safeValue(notice.title, "No title"),
        safeValue(notice.agency, "unknown agency"),
        safeValue(notice.deadline, "No deadline"),
      ].join(" / ");
  safeText("decision-memo-summary", summary);

  renderList(
    "decision-memo-fit-summary",
    [
      ...(Array.isArray(fitSummary.fit_reasons) ? fitSummary.fit_reasons : []),
      ...(Array.isArray(fitSummary.concern_reasons) ? fitSummary.concern_reasons : []),
    ],
    "No fit summary available yet.",
  );
  renderList(
    "decision-memo-risk-summary",
    [
      ...(Array.isArray(riskSummary.eligibility_risks) ? riskSummary.eligibility_risks : []),
      ...(Array.isArray(riskSummary.document_risks) ? riskSummary.document_risks : []),
      ...(Array.isArray(riskSummary.schedule_risks) ? riskSummary.schedule_risks : []),
      ...(Array.isArray(riskSummary.commercial_risks) ? riskSummary.commercial_risks : []),
    ],
    "No material risk was identified from the current local-safe metadata.",
  );
  renderList(
    "decision-memo-next-action",
    [
      `deadline: ${safeValue(nextAction.deadline, "No deadline")}`,
      `urgency: ${safeValue(nextAction.urgency, "unknown")}`,
      safeValue(nextAction.next_action, "Select a Review Board item or enter a known notice id."),
    ],
    "No next action available yet.",
  );
  renderList(
    "decision-memo-preparation-actions",
    (Array.isArray(memo.preparation_actions) ? memo.preparation_actions : []).map((item) =>
      [
        safeValue(item.action, "Review"),
        safeValue(item.owner, "unassigned"),
        safeValue(item.priority, "medium"),
      ].join(" / "),
    ),
    "No preparation actions available yet.",
  );
  renderList(
    "decision-memo-required-documents",
    (Array.isArray(memo.required_documents) ? memo.required_documents : []).map((item) =>
      [
        safeValue(item.name, "unknown document"),
        safeValue(item.status, "required"),
        safeValue(item.reason, "check readiness"),
      ].join(" / "),
    ),
    "No required documents listed yet.",
  );
  safeText(
    "decision-memo-copy-block",
    memo.export_blocks?.markdown || memo.export_blocks?.short_summary || "No decision memo selected.",
  );
  renderManualDecision(memo);
}

function loadDecisionMemoFromInput() {
  const input = document.getElementById("decision-memo-notice-id");
  const noticeId = input?.value || "";
  return loadDecisionMemo(noticeId);
}

function openSelectedDecisionMemo() {
  if (!state.currentOpportunityId) {
    renderDecisionMemo({
      ...emptyDecisionMemo(),
      export_blocks: {
        markdown: "",
        short_summary: "Select an opportunity from Opportunity Inbox first.",
      },
      recommended_decision: {
        value: "Hold",
        rationale: "Select an opportunity from Opportunity Inbox first.",
      },
    });
    return;
  }
  return loadDecisionMemo(state.currentOpportunityId);
}

function currentManualDecisionValue() {
  const selectedDecision = ["prepare", "review", "hold", "reject"].find((value) =>
    document.getElementById(`decision-memo-manual-${value}`)?.checked,
  );
  return selectedDecision || normalizeManualDecision(state.currentManualDecision);
}

async function saveManualDecision() {
  const noticeId = String(
    state.currentDecisionMemoId || document.getElementById("decision-memo-notice-id")?.value || "",
  ).trim();
  if (!noticeId) {
    safeText("decision-memo-manual-message", "Load a decision memo first.");
    return;
  }
  const payload = {
    decision: currentManualDecisionValue(),
    note: document.getElementById("decision-memo-manual-note")?.value || "",
  };
  const result = await apiJson(`/ops/manual-decision/${encodeURIComponent(noticeId)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  state.currentDecisionMemoId = result.notice_id || noticeId;
  renderManualDecision({
    recommended_decision: { value: payload.decision },
    manual_decision: result,
  });
  await loadDecisionMemo(noticeId);
  await loadDailyReviewPack();
}

function renderOpportunityReviewStatus(payload) {
  const status = document.getElementById("opportunity-review-status");
  const owner = document.getElementById("opportunity-review-owner");
  const nextAction = document.getElementById("opportunity-review-next-action");
  const note = document.getElementById("opportunity-review-note");
  if (status) status.value = payload.review_status || "new";
  if (owner) owner.value = payload.owner || "";
  if (nextAction) nextAction.value = payload.next_action || "";
  if (note) note.value = payload.note || "";
  safeText(
    "opportunity-review-message",
    payload.updated_at ? `Saved ${payload.updated_at}` : "Local only.",
  );
}

async function saveOpportunityReviewStatus() {
  if (!state.currentOpportunityId) {
    safeText("opportunity-review-message", "Select an opportunity first.");
    return;
  }
  const payload = {
    review_status: document.getElementById("opportunity-review-status")?.value || "new",
    owner: document.getElementById("opportunity-review-owner")?.value || "",
    next_action: document.getElementById("opportunity-review-next-action")?.value || "",
    note: document.getElementById("opportunity-review-note")?.value || "",
  };
  const result = await apiJson(`/ops/review-status/${encodeURIComponent(state.currentOpportunityId)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  renderOpportunityReviewStatus(result);
  await Promise.allSettled([loadOpportunityInbox(), loadReviewBoard(), loadDailyReviewPack()]);
}

async function clearOpportunityReviewStatus() {
  if (!state.currentOpportunityId) {
    safeText("opportunity-review-message", "Select an opportunity first.");
    return;
  }
  const result = await apiJson(`/ops/review-status/${encodeURIComponent(state.currentOpportunityId)}`, {
    method: "DELETE",
  });
  renderOpportunityReviewStatus(result);
  await Promise.allSettled([loadOpportunityInbox(), loadReviewBoard(), loadDailyReviewPack()]);
}

function renderFieldGroup(title, values) {
  const section = document.createElement("div");
  const heading = document.createElement("strong");
  heading.textContent = title;
  section.appendChild(heading);
  const list = document.createElement("ul");
  const safeValues = (Array.isArray(values) ? values : []).filter(Boolean);
  if (!safeValues.length) safeValues.push("확인 필요");
  for (const value of safeValues) {
    const item = document.createElement("li");
    item.textContent = value;
    list.appendChild(item);
  }
  section.appendChild(list);
  return section;
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

function downloadDailyReviewMarkdown() {
  const markdown = state.currentDailyReviewMarkdown || "# 오늘의 입찰 검토 패키지\n\nNo opportunity data.";
  const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "yonlab-daily-review-pack.md";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function downloadDailyReviewCsv() {
  const link = document.createElement("a");
  link.href = "/ops/daily-review-pack/csv";
  link.download = "yonlab-daily-review-pack.csv";
  document.body.appendChild(link);
  link.click();
  link.remove();
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
  return `${number.toLocaleString()}원`;
}

function formatDocumentGroups(groups) {
  const entries = Object.entries(groups || {}).filter(([, values]) => Array.isArray(values) && values.length);
  if (!entries.length) return "";
  return " / " + entries.map(([name, values]) => `${name}: ${values.join(", ")}`).join(" / ");
}

function requiredDocumentLines(payload) {
  const grouped = payload.required_documents_grouped || {};
  const groupedLines = Object.entries(grouped)
    .filter(([, values]) => Array.isArray(values) && values.length)
    .map(([group, values]) => `${group}: ${values.join(", ")}`);
  if (groupedLines.length) return groupedLines;
  return (payload.required_documents || []).map((doc) => `${doc.status || "check"}: ${doc.name || "확인 필요"}`);
}

async function loadRuns() {
  const payload = await apiJson("/ops/runs?limit=20");
  const body = document.getElementById("runs-body");
  if (!body) return;
  body.innerHTML = "";
  const runs = Array.isArray(payload.runs) ? payload.runs : [];
  for (const run of runs) {
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
      cell.textContent = safeValue(value, "");
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
  if (!body) return;
  body.innerHTML = "";
  const recommendations = Array.isArray(payload.recommendations) ? payload.recommendations : [];
  for (const rec of recommendations) {
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
      cell.textContent = safeValue(value, "");
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
  const minScore = document.getElementById("filter-min-score")?.value;
  const label = document.getElementById("filter-label")?.value;
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
  safeText("run-detail", `Run ${run.run_id || runId}: ${run.status || "unknown"} / ${run.source_count || 0} source notices`);
  await loadRecommendations({ run_id: runId, limit: "100" });
  const reportList = document.getElementById("report-list");
  if (!reportList) return;
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
  safeText("report-viewer", payload.markdown || "No report content");
}

function renderPackageInfo(packageInfo) {
  const storage = packageInfo.storage || {};
  safeText(
    "package-summary",
    `${packageInfo.package_name || "YOnLab G2B Agent"} ${packageInfo.package_version || "unknown"} / default ${packageInfo.default_run_mode || "fixture"} / reports ${storage.report_dir || "No data"}`,
  );
  renderList("package-capabilities", packageInfo.capabilities || []);
  renderList("package-scripts", packageInfo.scripts || []);
}

function renderList(elementId, values, fallback = "No data") {
  const list = document.getElementById(elementId);
  if (!list) return;
  list.innerHTML = "";
  const safeValues = Array.isArray(values) ? values : [];
  if (!safeValues.length) {
    const item = document.createElement("li");
    item.textContent = fallback;
    list.appendChild(item);
    return;
  }
  for (const value of safeValues) {
    const item = document.createElement("li");
    item.textContent = safeValue(value, "");
    list.appendChild(item);
  }
}

function updateRunModeDefaults() {
  const mode = document.querySelector('[name="mode"]')?.value;
  const rowsInput = document.querySelector('[name="num_rows"]');
  const submitButton = document.querySelector('#run-form button[type="submit"]');
  if (!rowsInput || !submitButton) return;
  if (mode === "real") {
    rowsInput.value = "3";
    submitButton.textContent = "Run controlled real job";
  } else {
    rowsInput.value = "5";
    submitButton.textContent = "Run fixture-safe job";
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  syncInboxDefaultFilters();
  document.getElementById("refresh-status")?.addEventListener("click", () =>
    loadSection("status", loadStatus, ["status-health", "status-package", "status-real-api", "status-service-key", "status-endpoint", "status-fixture", "status-readiness", "package-summary"]),
  );
  document.getElementById("refresh-quality")?.addEventListener("click", () =>
    loadSection("quality", loadQualitySummary, ["quality-summary-status", "opportunity-summary-status"]),
  );
  document.getElementById("refresh-daily-review")?.addEventListener("click", () =>
    loadSection("daily review pack", loadDailyReviewPack, ["daily-review-status", "daily-review-markdown"]),
  );
  document.getElementById("refresh-safe-daily")?.addEventListener("click", () =>
    loadSection("safe daily", loadSafeDailyStatus, ["safe-daily-current-status", "safe-daily-latest-result"]),
  );
  document.getElementById("refresh-review-board")?.addEventListener("click", () =>
    loadSection("review board", loadReviewBoard, ["review-board-empty", "review-board-total-count"]),
  );
  document.getElementById("refresh-runs")?.addEventListener("click", () =>
    loadSection("runs", loadRuns, ["run-detail"]),
  );
  document.getElementById("refresh-opportunities")?.addEventListener("click", () =>
    loadSection("opportunities", loadOpportunityInbox, ["opportunity-empty"]),
  );
  document.getElementById("apply-opportunity-filters")?.addEventListener("click", () =>
    loadSection("opportunities", loadOpportunityInbox, ["opportunity-empty"]),
  );
  document.getElementById("load-decision-memo")?.addEventListener("click", () =>
    loadSection("decision memo", loadDecisionMemoFromInput, ["decision-memo-status", "decision-memo-summary"]),
  );
  document.getElementById("open-selected-decision-memo")?.addEventListener("click", () =>
    loadSection("decision memo", openSelectedDecisionMemo, ["decision-memo-status", "decision-memo-summary"]),
  );
  for (const value of ["prepare", "review", "hold", "reject"]) {
    document.getElementById(`decision-memo-manual-${value}`)?.addEventListener("change", () =>
      selectManualDecision(value),
    );
  }
  document.getElementById("save-manual-decision")?.addEventListener("click", () =>
    loadSection("save manual decision", saveManualDecision, ["decision-memo-manual-message"]),
  );
  document.getElementById("download-opportunity-markdown")?.addEventListener("click", downloadOpportunityMarkdown);
  document.getElementById("save-opportunity-review-status")?.addEventListener("click", () =>
    loadSection("save review status", saveOpportunityReviewStatus, ["opportunity-review-message"]),
  );
  document.getElementById("clear-opportunity-review-status")?.addEventListener("click", () =>
    loadSection("clear review status", clearOpportunityReviewStatus, ["opportunity-review-message"]),
  );
  document.getElementById("download-daily-review-markdown")?.addEventListener("click", downloadDailyReviewMarkdown);
  document.getElementById("download-daily-review-csv")?.addEventListener("click", downloadDailyReviewCsv);
  document.getElementById("run-form")?.addEventListener("submit", (event) =>
    loadSection("run recommendation", () => runRecommendation(event), ["run-state", "run-result"]),
  );
  document.querySelector('[name="mode"]')?.addEventListener("change", updateRunModeDefaults);
  document.getElementById("apply-rec-filters")?.addEventListener("click", () =>
    loadSection("recommendation filters", applyRecommendationFilters, ["run-detail"]),
  );
  updateRunModeDefaults();
  renderDecisionMemo(emptyDecisionMemo());
  await Promise.allSettled([
    loadSection("status", loadStatus, ["status-health", "status-package", "status-real-api", "status-service-key", "status-endpoint", "status-fixture", "status-readiness", "package-summary"]),
    loadSection("quality", loadQualitySummary, ["quality-summary-status", "opportunity-summary-status"]),
    loadSection("daily review pack", loadDailyReviewPack, ["daily-review-status", "daily-review-markdown"]),
    loadSection("safe daily", loadSafeDailyStatus, ["safe-daily-current-status", "safe-daily-latest-result"]),
    loadSection("review board", loadReviewBoard, ["review-board-empty", "review-board-total-count"]),
    loadSection("opportunities", loadOpportunityInbox, ["opportunity-empty"]),
    loadSection("runs", loadRuns, ["run-detail"]),
    loadSection("recommendations", loadRecommendations, ["run-detail"]),
  ]);
});
