import json
import shutil
import subprocess
import textwrap
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

import app.api.routes as routes
from app.core.config import Settings
from app.integrations.g2b.fixtures import load_sample_g2b_notices
from app.main import app
from app.storage.models import StoredReport
from app.storage.repository import OperationsRepository

client = TestClient(app)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DUPLICATED_KOREAN_FRAGMENTS = (
    "\uc11c\uc11c\uc6b8\uc6b8",
    "\ubd80\ubd80\uc0b0\uc0b0",
    "\uc9c0\uc9c0\uc5ed\uc5ed",
    "\uc2dc\uc2dc\uc2a4\uc2a4\ud15c\ud15c",
    "\ubd80\ubd80\ud569\ud569\ud569\ub2c8\ub2c8\ub2e4\ub2e4",
)


def test_ui_dashboard_returns_html_without_service_key(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(routes, "get_settings", lambda: Settings(g2b_api_service_key="SECRET"))

    response = client.get("/ui")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "YOnLab G2B Agent" in response.text
    assert "Run recommendation" in response.text
    assert "Recommendation Quality Summary" in response.text
    assert "Total Reports" in response.text
    assert "Real Reports" in response.text
    assert "Real Runs" in response.text
    assert "Latest Status" in response.text
    assert "Latest Error" in response.text
    assert "Source Mode" in response.text
    assert "Safe Daily Status" in response.text
    assert "Priority Legend" in response.text
    assert "오늘의 입찰 검토 패키지" in response.text
    assert "Real mode uses live G2B API quota. Use only when necessary." in response.text
    assert "SECRET" not in response.text


def test_root_redirects_to_ui() -> None:
    response = client.get("/", follow_redirects=False)

    assert response.status_code in {302, 307}
    assert response.headers["location"] == "/ui"


def test_ui_static_assets_are_available() -> None:
    css_response = client.get("/ui/static/dashboard.css")
    js_response = client.get("/ui/static/dashboard.js")

    assert css_response.status_code == 200
    assert ".topbar" in css_response.text
    assert js_response.status_code == 200
    assert "runRecommendation" in js_response.text


def test_dashboard_javascript_parses_cleanly() -> None:
    node = shutil.which("node")
    assert node is not None, "node is required for dashboard syntax validation"

    result = subprocess.run(
        [node, "--check", str(PROJECT_ROOT / "app" / "ui" / "static" / "dashboard.js")],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_dashboard_javascript_uses_section_safe_render_guards() -> None:
    js_text = (PROJECT_ROOT / "app" / "ui" / "static" / "dashboard.js").read_text(
        encoding="utf-8"
    )

    assert "safeText" in js_text
    assert "loadSection" in js_text
    assert "Promise.allSettled" in js_text
    assert "setSectionError" in js_text
    assert "No data" in js_text
    assert "toLocaleString()}원" in js_text
    assert "점 /" in js_text
    assert "\ufffd" not in js_text
    assert "??/" not in js_text
    assert "toLocaleString()}??" not in js_text


def test_dashboard_render_helpers_replace_loading_with_fallbacks(tmp_path: Path) -> None:
    node = shutil.which("node")
    assert node is not None, "node is required for dashboard render validation"

    check_script = tmp_path / "dashboard_render_check.js"
    check_script.write_text(
        textwrap.dedent(
            """
            const fs = require("fs");
            const vm = require("vm");
            const assert = require("assert");

            function makeElement(id) {
              const element = {
                id,
                tagName: id,
                textContent: "Loading",
                children: [],
                appendChild(child) {
                  this.children.push(child);
                },
                addEventListener() {},
                click() {},
                remove() {},
              };
              Object.defineProperty(element, "innerHTML", {
                get() {
                  return this._innerHTML || "";
                },
                set(value) {
                  this._innerHTML = value;
                  this.children = [];
                },
              });
              return element;
            }

            const elements = {
              "opportunity-body": makeElement("opportunity-body"),
              "opportunity-empty": makeElement("opportunity-empty"),
              "opportunity-detail": makeElement("opportunity-detail"),
              "opportunity-markdown": makeElement("opportunity-markdown"),
              "decision-memo-notice-id": makeElement("decision-memo-notice-id"),
              "decision-memo-status": makeElement("decision-memo-status"),
              "decision-memo-summary": makeElement("decision-memo-summary"),
              "decision-memo-decision": makeElement("decision-memo-decision"),
              "decision-memo-rationale": makeElement("decision-memo-rationale"),
              "decision-memo-fit-summary": makeElement("decision-memo-fit-summary"),
              "decision-memo-risk-summary": makeElement("decision-memo-risk-summary"),
              "decision-memo-next-action": makeElement("decision-memo-next-action"),
              "decision-memo-preparation-actions": makeElement("decision-memo-preparation-actions"),
              "decision-memo-required-documents": makeElement("decision-memo-required-documents"),
              "decision-memo-copy-block": makeElement("decision-memo-copy-block"),
              "decision-memo-manual-prepare": makeElement("decision-memo-manual-prepare"),
              "decision-memo-manual-review": makeElement("decision-memo-manual-review"),
              "decision-memo-manual-hold": makeElement("decision-memo-manual-hold"),
              "decision-memo-manual-reject": makeElement("decision-memo-manual-reject"),
              "decision-memo-manual-note": makeElement("decision-memo-manual-note"),
              "decision-memo-manual-message": makeElement("decision-memo-manual-message"),
            };
            const document = {
              body: makeElement("body"),
              createElement(tag) {
                return makeElement(tag);
              },
              getElementById(id) {
                return elements[id] || null;
              },
              addEventListener() {},
            };
            const responses = {
              "/ops/opportunity-inbox/N-1": {
                title: null,
                agency: null,
                source_type: null,
                score: null,
                risk_level: null,
              },
              "/ops/opportunity-report/N-1": {
                markdown:
                  "## YOnLab \\ub9de\\ucda4 \\ucd94\\ucc9c \\uacf5\\uace0: \\ud14c\\uc2a4\\ud2b8",
              },
              "/ops/decision-memo/N-1": {
                status: "success",
                notice_id: "N-1",
                notice: {
                  title: "Selected notice",
                  agency: "Agency",
                  deadline: "2099-01-01",
                },
                yonlab_fit_summary: { fit_reasons: ["Aligned"], concern_reasons: [] },
                risk_summary: {
                  eligibility_risks: [],
                  document_risks: [],
                  schedule_risks: [],
                  commercial_risks: [],
                },
                deadline_next_action: {
                  deadline: "2099-01-01",
                  urgency: "upcoming",
                  next_action: "Confirm scope",
                },
                recommended_decision: {
                  value: "Prepare",
                  rationale: "Selected opportunity is aligned.",
                },
                manual_decision: {
                  decision: "prepare",
                  note: "",
                  updated_at: "2026-06-30T12:00:00+09:00",
                },
                preparation_actions: [],
                required_documents: [],
                export_blocks: {
                  markdown: "# YOnLab Decision Memo",
                  short_summary: "Prepare - Selected notice",
                },
              },
            };
            const fetchCalls = [];
            const context = {
              Blob: function Blob() {},
              URL: { createObjectURL: () => "blob://local", revokeObjectURL() {} },
              URLSearchParams,
              console,
              document,
              elements,
              encodeURIComponent,
              fetch: async (url) => {
                fetchCalls.push(String(url));
                return {
                  ok: true,
                  status: 200,
                  statusText: "OK",
                  json: async () => responses[url],
                };
              },
            };

            (async () => {
              vm.createContext(context);
              vm.runInContext(fs.readFileSync(process.argv[2], "utf8"), context);
              vm.runInContext(`
                renderOpportunityInbox({
                  source_mode: "saved",
                  items: [{
                    notice_id: "N-1",
                    title: null,
                    agency: "Agency",
                    deadline: null,
                    budget: 1200000,
                    score: 88,
                    grade: "recommend",
                    risk_level: null,
                    source_badges: ["fixture"]
                  }]
                });
              `, context);
              assert.notStrictEqual(elements["opportunity-empty"].textContent, "Loading");
              assert.strictEqual(elements["opportunity-body"].children.length, 1);
              const populatedCells = elements["opportunity-body"].children[0].children;
              assert.strictEqual(populatedCells[0].textContent, "");
              assert.strictEqual(populatedCells[3].textContent, "1,200,000\\uc6d0");

              vm.runInContext(
                "renderOpportunityInbox({ items: null, empty_state_message: null });",
                context,
              );
              assert.strictEqual(elements["opportunity-body"].children.length, 1);
              const emptyMessage = elements["opportunity-body"].children[0].children[0];
              assert.match(emptyMessage.textContent, /No opportunity data/);

              await vm.runInContext('loadOpportunityDetail("N-1")', context);
              assert.match(elements["opportunity-detail"].textContent, /No title/);
              assert.match(elements["opportunity-detail"].textContent, /0\\uc810/);
              assert.match(elements["opportunity-markdown"].textContent, /YOnLab/);
              assert.strictEqual(elements["decision-memo-notice-id"].value, "N-1");

              await vm.runInContext("openSelectedDecisionMemo()", context);
              assert.ok(fetchCalls.includes("/ops/decision-memo/N-1"));
              assert.match(elements["decision-memo-summary"].textContent, /Selected notice/);
            })().catch((error) => {
              console.error(error);
              process.exit(1);
            });
            """
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [node, str(check_script), str(PROJECT_ROOT / "app" / "ui" / "static" / "dashboard.js")],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_report_content_endpoint_returns_saved_markdown(
    tmp_path: Path,
    monkeypatch,
) -> None:  # noqa: ANN001
    settings = _tmp_settings(tmp_path)
    monkeypatch.setattr(routes, "get_settings", lambda: settings)

    run_response = client.post(
        "/ops/run-recommendations",
        json={"mode": "fixture", "keyword": "AI", "num_rows": 2, "include_reports": True},
    )
    run_id = run_response.json()["run_id"]
    reports = client.get(f"/ops/reports/{run_id}").json()["reports"]

    assert reports
    report_response = client.get(f"/ops/report-content/{run_id}/{reports[0]['notice_id']}")

    assert report_response.status_code == 200
    payload = report_response.json()
    assert payload["run_id"] == run_id
    assert payload["notice_id"] == reports[0]["notice_id"]
    assert "와이온랩 맞춤 추천 공고" in payload["markdown"]
    assert "serviceKey" not in str(payload)


def test_report_content_endpoint_blocks_path_traversal(
    tmp_path: Path,
    monkeypatch,
) -> None:  # noqa: ANN001
    settings = _tmp_settings(tmp_path)
    monkeypatch.setattr(routes, "get_settings", lambda: settings)
    outside_file = tmp_path / "outside.md"
    outside_file.write_text("outside", encoding="utf-8")
    repository = OperationsRepository(settings.yonlab_storage_db_path)
    repository.save_report(
        StoredReport(
            run_id="run_unsafe",
            notice_id="NOTICE-UNSAFE",
            title="Unsafe",
            report_path=str(outside_file),
            created_at=datetime.now(UTC).isoformat(),
        )
    )

    response = client.get("/ops/report-content/run_unsafe/NOTICE-UNSAFE")

    assert response.status_code == 404


def test_ops_recommendations_can_filter_by_run_id(
    tmp_path: Path,
    monkeypatch,
) -> None:  # noqa: ANN001
    settings = _tmp_settings(tmp_path)
    monkeypatch.setattr(routes, "get_settings", lambda: settings)

    first = client.post(
        "/ops/run-recommendations",
        json={"mode": "fixture", "keyword": "AI", "num_rows": 1, "include_reports": True},
    ).json()
    second = client.post(
        "/ops/run-recommendations",
        json={"mode": "fixture", "keyword": "AI", "num_rows": 2, "include_reports": True},
    ).json()

    first_payload = client.get(
        "/ops/recommendations",
        params={"run_id": first["run_id"], "limit": 10},
    ).json()
    second_payload = client.get(
        "/ops/recommendations",
        params={"run_id": second["run_id"], "limit": 10},
    ).json()

    assert first_payload["recommendations"]
    assert second_payload["recommendations"]
    assert {item["run_id"] for item in first_payload["recommendations"]} == {first["run_id"]}
    assert {item["run_id"] for item in second_payload["recommendations"]} == {second["run_id"]}


def test_ui_smoke_scripts_exist_and_validate_local_references_them() -> None:
    assert (PROJECT_ROOT / "scripts" / "smoke_ui_health.ps1").is_file()
    assert (PROJECT_ROOT / "scripts" / "smoke_ops_ui_flow.ps1").is_file()
    assert (PROJECT_ROOT / "scripts" / "reset_local_ops_data.ps1").is_file()

    validate_local = (PROJECT_ROOT / "scripts" / "validate_local.ps1").read_text(
        encoding="utf-8"
    )
    assert "smoke_ui_health.ps1" in validate_local
    assert "smoke_ops_ui_flow.ps1" in validate_local
    assert "smoke_ops_quality_summary.ps1" in validate_local
    assert "smoke_ops_report_index.ps1" in validate_local


def test_ui_javascript_blocks_unconfirmed_real_mode_and_sets_row_defaults() -> None:
    js_text = (PROJECT_ROOT / "app" / "ui" / "static" / "dashboard.js").read_text(
        encoding="utf-8"
    )

    assert 'payload.mode === "real" && !payload.confirm_real_api_call' in js_text
    assert "Real mode uses live G2B API quota" in js_text
    assert 'rowsInput.value = "3"' in js_text
    assert 'rowsInput.value = "5"' in js_text
    assert 'apiJson("/ops/quality-summary")' in js_text
    assert "quality-summary-status" in js_text
    assert "quality-real-runs" in js_text
    assert "quality-real-reports" in js_text
    assert "quality-latest-status" in js_text
    assert "quality-latest-error" in js_text


def test_dashboard_contains_operator_clarity_hooks() -> None:
    html = (PROJECT_ROOT / "app" / "ui" / "templates" / "dashboard.html").read_text(
        encoding="utf-8"
    )
    js_text = (PROJECT_ROOT / "app" / "ui" / "static" / "dashboard.js").read_text(
        encoding="utf-8"
    )

    assert "source-mode-banner" in html
    assert "source-mode-message" in html
    assert "priority-legend" in html
    assert "safe-daily-status" in html
    assert "safe-daily-latest-result" in html
    assert "daily-review-executive-summary" in html
    assert "오늘의 우선 검토 공고" in html
    assert "오늘 할 일" in html
    assert "서류 준비" in html
    assert "리스크 요약" in html
    assert 'apiJson("/ops/safe-daily-status")' in js_text
    assert "renderSourceModeBanner" in js_text
    assert "renderPriorityLegend" in js_text
    assert "renderSafeDailyStatus" in js_text
    assert "controlled real run" in js_text


def test_dashboard_contains_review_board_section_before_opportunity_inbox() -> None:
    html = (PROJECT_ROOT / "app" / "ui" / "templates" / "dashboard.html").read_text(
        encoding="utf-8"
    )
    js_text = (PROJECT_ROOT / "app" / "ui" / "static" / "dashboard.js").read_text(
        encoding="utf-8"
    )

    assert "review-board-title" in html
    assert "refresh-review-board" in html
    assert "review-board-cards" in html
    assert "review-board-next-actions" in html
    assert html.index("review-board-title") < html.index("opportunity-title")
    assert 'apiJson("/ops/review-board")' in js_text
    assert "loadReviewBoard" in js_text
    assert "applyReviewBoardFilter" in js_text
    assert "syncInboxDefaultFilters" in js_text


def test_dashboard_contains_decision_memo_panel_and_loader_hooks() -> None:
    html = (PROJECT_ROOT / "app" / "ui" / "templates" / "dashboard.html").read_text(
        encoding="utf-8"
    )
    js_text = (PROJECT_ROOT / "app" / "ui" / "static" / "dashboard.js").read_text(
        encoding="utf-8"
    )

    assert "decision-memo-title" in html
    assert "decision-memo-notice-id" in html
    assert "load-decision-memo" in html
    assert "open-selected-decision-memo" in html
    assert "decision-memo-summary" in html
    assert "decision-memo-decision" in html
    assert "decision-memo-fit-summary" in html
    assert "decision-memo-risk-summary" in html
    assert "decision-memo-next-action" in html
    assert "decision-memo-preparation-actions" in html
    assert "decision-memo-required-documents" in html
    assert "decision-memo-copy-block" in html
    assert "decision-memo-manual-prepare" in html
    assert "decision-memo-manual-review" in html
    assert "decision-memo-manual-hold" in html
    assert "decision-memo-manual-reject" in html
    assert "decision-memo-manual-note" in html
    assert "save-manual-decision" in html
    assert "decision-memo-manual-message" in html
    assert "loadDecisionMemo" in js_text
    assert "renderDecisionMemo" in js_text
    assert "selectManualDecision" in js_text
    assert "saveManualDecision" in js_text
    assert "renderManualDecision" in js_text
    assert "/ops/manual-decision/" in js_text
    assert "/ops/decision-memo/" in js_text


def test_dashboard_manual_decision_helpers_render_and_save_refresh_context(
    tmp_path: Path,
) -> None:
    node = shutil.which("node")
    assert node is not None, "node is required for dashboard render validation"

    check_script = tmp_path / "dashboard_manual_decision_check.js"
    check_script.write_text(
        textwrap.dedent(
            """
            const fs = require("fs");
            const vm = require("vm");
            const assert = require("assert");

            function makeElement(id) {
              const element = {
                id,
                tagName: id,
                textContent: "Loading",
                children: [],
                dataset: {},
                value: "",
                checked: false,
                listeners: {},
                appendChild(child) {
                  this.children.push(child);
                },
                addEventListener(type, handler) {
                  this.listeners[type] = handler;
                },
                click() {
                  if (this.listeners.click) {
                    return this.listeners.click({ currentTarget: this, preventDefault() {} });
                  }
                  return undefined;
                },
                remove() {},
              };
              Object.defineProperty(element, "innerHTML", {
                get() {
                  return this._innerHTML || "";
                },
                set(value) {
                  this._innerHTML = value;
                  this.children = [];
                },
              });
              return element;
            }

            const elementIds = [
              "decision-memo-status",
              "decision-memo-notice-id",
              "decision-memo-summary",
              "decision-memo-decision",
              "decision-memo-rationale",
              "decision-memo-fit-summary",
              "decision-memo-risk-summary",
              "decision-memo-next-action",
              "decision-memo-preparation-actions",
              "decision-memo-required-documents",
              "decision-memo-copy-block",
              "decision-memo-manual-prepare",
              "decision-memo-manual-review",
              "decision-memo-manual-hold",
              "decision-memo-manual-reject",
              "decision-memo-manual-note",
              "save-manual-decision",
              "decision-memo-manual-message",
              "daily-review-status",
              "daily-review-generated-at",
              "daily-review-latest-run",
              "daily-review-total-items",
              "daily-review-p1",
              "daily-review-p2",
              "daily-review-p3",
              "daily-review-hold",
              "daily-review-no-go",
              "daily-review-executive-summary",
              "daily-review-top-items",
              "daily-review-today-actions",
              "daily-review-document-actions",
              "daily-review-risk-summary",
              "daily-review-markdown",
              "source-mode-current",
              "source-mode-message",
              "source-mode-latest-run",
              "source-mode-latest-at",
              "source-mode-real-reports",
              "source-mode-total-items",
              "source-mode-next-actions",
              "priority-legend",
            ];
            const elements = Object.fromEntries(elementIds.map((id) => [id, makeElement(id)]));
            const document = {
              body: makeElement("body"),
              createElement(tag) {
                return makeElement(tag);
              },
              getElementById(id) {
                return elements[id] || null;
              },
              querySelector() {
                return null;
              },
              addEventListener() {},
            };
            const fetchCalls = [];
            let manualDecision = {
              decision: "prepare",
              note: "Start the checklist.",
              updated_at: "2026-06-30T09:00:00+09:00",
            };
            const context = {
              Blob: function Blob() {},
              URL: { createObjectURL: () => "blob://local", revokeObjectURL() {} },
              URLSearchParams,
              console,
              document,
              elements,
              encodeURIComponent,
              fetch: async (url, options = {}) => {
                fetchCalls.push({ url: String(url), options });
                if (
                  String(url) === "/ops/decision-memo/G2B-SAMPLE-2026-001" &&
                  (!options.method || options.method === "GET")
                ) {
                  return {
                    ok: true,
                    status: 200,
                    statusText: "OK",
                    json: async () => ({
                      status: "success",
                      notice_id: "G2B-SAMPLE-2026-001",
                      notice: {
                        title: "Seoul AI workflow automation",
                        agency: "Seoul agency",
                        deadline: "2026-07-15",
                      },
                      yonlab_fit_summary: {
                        fit_reasons: ["AI/SW fit"],
                        concern_reasons: [],
                      },
                      risk_summary: {
                        eligibility_risks: [],
                        document_risks: [],
                        schedule_risks: [],
                        commercial_risks: [],
                      },
                      deadline_next_action: {
                        deadline: "2026-07-15",
                        urgency: "due_soon",
                        next_action: "Confirm proposal schedule",
                      },
                          recommended_decision: {
                            value: "Prepare",
                            rationale: "Fit is strong enough to begin preparation.",
                          },
                          manual_decision: manualDecision,
                          preparation_actions: [],
                          required_documents: [],
                          export_blocks: {
                            markdown: "# YOnLab Decision Memo\\n\\n- Decision: Prepare",
                            short_summary: "Prepare - Seoul AI workflow automation",
                      },
                    }),
                  };
                }
                if (String(url) === "/ops/manual-decision/G2B-SAMPLE-2026-001") {
                  const requestBody = JSON.parse(options.body || "{}");
                  manualDecision = {
                    decision: requestBody.decision || "hold",
                    note: requestBody.note || "",
                    updated_at: "2026-06-30T10:00:00+09:00",
                  };
                  return {
                    ok: true,
                    status: 200,
                    statusText: "OK",
                    json: async () => ({
                      notice_id: "G2B-SAMPLE-2026-001",
                      ...manualDecision,
                    }),
                  };
                }
                if (String(url) === "/ops/daily-review-pack") {
                  return {
                    ok: true,
                    status: 200,
                    statusText: "OK",
                    json: async () => ({
                      status: "ready",
                      generated_at: "2026-06-30T10:00:00+09:00",
                      latest_run_id: "run-1",
                      total_items: 1,
                      p1_count: 1,
                      p2_count: 0,
                      p3_count: 0,
                      hold_count: 0,
                      no_go_count: 0,
                      executive_summary: { lines: ["One item refreshed"] },
                      top_items: [],
                      today_actions: [],
                      document_actions: [],
                      risk_summary: {},
                      markdown_report: "# Daily review refreshed",
                      source_mode: "saved",
                      source_mode_message: "Saved data ready.",
                      real_report_count: 0,
                      empty_state_next_actions: [],
                      priority_legend: {},
                    }),
                  };
                }
                throw new Error("Unexpected fetch " + String(url));
              },
            };

            (async () => {
              vm.createContext(context);
              vm.runInContext(fs.readFileSync(process.argv[2], "utf8"), context);

              vm.runInContext("renderDecisionMemo(emptyDecisionMemo())", context);
              assert.match(elements["decision-memo-manual-message"].textContent, /Local only/i);
              await vm.runInContext("saveManualDecision()", context);
              assert.match(
                elements["decision-memo-manual-message"].textContent,
                /Load a decision memo first/i,
              );

              await vm.runInContext('loadDecisionMemo("G2B-SAMPLE-2026-001")', context);
              assert.strictEqual(elements["decision-memo-notice-id"].value, "G2B-SAMPLE-2026-001");
              assert.strictEqual(elements["decision-memo-manual-prepare"].checked, true);
              assert.strictEqual(elements["decision-memo-manual-review"].checked, false);
              assert.strictEqual(
                elements["decision-memo-manual-note"].value,
                "Start the checklist.",
              );
              assert.match(
                elements["decision-memo-manual-message"].textContent,
                /Saved 2026-06-30T09:00:00\\+09:00/,
              );

              vm.runInContext('selectManualDecision("review")', context);
              elements["decision-memo-manual-note"].value = "Need one more pricing check.";
              await vm.runInContext("saveManualDecision()", context);

              const postCall = fetchCalls.find(
                (entry) => entry.url === "/ops/manual-decision/G2B-SAMPLE-2026-001",
              );
              assert.ok(postCall, "manual decision POST should be called");
              assert.strictEqual(postCall.options.method, "POST");
              assert.strictEqual(postCall.options.headers["Content-Type"], "application/json");
              assert.deepStrictEqual(
                JSON.parse(postCall.options.body),
                { decision: "review", note: "Need one more pricing check." },
              );

              const memoFetches = fetchCalls.filter(
                (entry) =>
                  entry.url === "/ops/decision-memo/G2B-SAMPLE-2026-001" &&
                  (!entry.options.method || entry.options.method === "GET")
              );
              assert.ok(memoFetches.length >= 2, "decision memo should be refreshed after save");
              assert.ok(
                fetchCalls.some((entry) => entry.url === "/ops/daily-review-pack"),
                "daily review pack should refresh after save",
              );
              assert.strictEqual(elements["decision-memo-manual-review"].checked, true);
              assert.match(elements["daily-review-status"].textContent, /ready/);
            })().catch((error) => {
              console.error(error);
              process.exit(1);
            });
            """
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [node, str(check_script), str(PROJECT_ROOT / "app" / "ui" / "static" / "dashboard.js")],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_dashboard_review_board_helpers_render_and_drive_inbox_filters(tmp_path: Path) -> None:
    node = shutil.which("node")
    assert node is not None, "node is required for dashboard render validation"

    check_script = tmp_path / "dashboard_review_board_check.js"
    check_script.write_text(
        textwrap.dedent(
            """
            const fs = require("fs");
            const vm = require("vm");
            const assert = require("assert");

            function makeElement(id) {
              const element = {
                id,
                tagName: id,
                textContent: "Loading",
                children: [],
                dataset: {},
                value: "",
                checked: false,
                listeners: {},
                appendChild(child) {
                  this.children.push(child);
                },
                addEventListener(type, handler) {
                  this.listeners[type] = handler;
                },
                click() {
                  if (this.listeners.click) {
                    return this.listeners.click({ currentTarget: this, preventDefault() {} });
                  }
                  return undefined;
                },
                remove() {},
              };
              Object.defineProperty(element, "innerHTML", {
                get() {
                  return this._innerHTML || "";
                },
                set(value) {
                  this._innerHTML = value;
                  this.children = [];
                },
              });
              return element;
            }

            const elements = {
              "review-board-cards": makeElement("review-board-cards"),
              "review-board-next-actions": makeElement("review-board-next-actions"),
              "review-board-empty": makeElement("review-board-empty"),
              "review-board-generated-at": makeElement("review-board-generated-at"),
              "review-board-source": makeElement("review-board-source"),
              "review-board-total-count": makeElement("review-board-total-count"),
              "review-board-active-count": makeElement("review-board-active-count"),
              "review-board-go": makeElement("review-board-go"),
              "review-board-reviewing": makeElement("review-board-reviewing"),
              "review-board-shortlisted": makeElement("review-board-shortlisted"),
              "review-board-hold": makeElement("review-board-hold"),
              "opportunity-review-filter": makeElement("opportunity-review-filter"),
              "opportunity-hide-archived-no-go": makeElement("opportunity-hide-archived-no-go"),
              "opportunity-shortlisted-only": makeElement("opportunity-shortlisted-only"),
              "opportunity-sort": makeElement("opportunity-sort"),
              "opportunity-keyword": makeElement("opportunity-keyword"),
              "opportunity-grade": makeElement("opportunity-grade"),
              "opportunity-risk": makeElement("opportunity-risk"),
              "opportunity-source": makeElement("opportunity-source"),
              "opportunity-body": makeElement("opportunity-body"),
              "opportunity-empty": makeElement("opportunity-empty"),
              "source-mode-current": makeElement("source-mode-current"),
              "source-mode-message": makeElement("source-mode-message"),
              "source-mode-latest-run": makeElement("source-mode-latest-run"),
              "source-mode-latest-at": makeElement("source-mode-latest-at"),
              "source-mode-real-reports": makeElement("source-mode-real-reports"),
              "source-mode-total-items": makeElement("source-mode-total-items"),
              "source-mode-next-actions": makeElement("source-mode-next-actions"),
              "priority-legend": makeElement("priority-legend"),
            };
            const document = {
              body: makeElement("body"),
              createElement(tag) {
                return makeElement(tag);
              },
              getElementById(id) {
                return elements[id] || null;
              },
              querySelector() {
                return null;
              },
              addEventListener() {},
            };
            const fetchCalls = [];
            const context = {
              Blob: function Blob() {},
              URL: { createObjectURL: () => "blob://local", revokeObjectURL() {} },
              URLSearchParams,
              console,
              document,
              elements,
              encodeURIComponent,
              fetch: async (url) => {
                fetchCalls.push(url);
                if (String(url).startsWith("/ops/opportunity-inbox?")) {
                  return {
                    ok: true,
                    status: 200,
                    statusText: "OK",
                    json: async () => ({
                      items: [{
                        notice_id: "REVIEWING-1",
                        title: "Review notice",
                        agency: "Agency",
                        deadline: "2099-01-01",
                        budget: 1000,
                        score: 82,
                        grade: "recommend",
                        review_status: "reviewing",
                        review_status_ko: "reviewing",
                        source_badges: ["fixture"],
                      }],
                      source_mode: "saved",
                      empty_state_message: "",
                      empty_state_next_actions: [],
                      priority_legend: {},
                    }),
                  };
                }
                throw new Error("Unexpected fetch " + url);
              },
            };

            (async () => {
              vm.createContext(context);
              vm.runInContext(fs.readFileSync(process.argv[2], "utf8"), context);
              vm.runInContext(`
                renderReviewBoard({
                  generated_at: "2026-06-29T12:00:00+00:00",
                  source: "saved",
                  total_count: 3,
                  active_count: 2,
                  status_counts: { go: 1, reviewing: 1, shortlisted: 0, hold: 0 },
                  cards: [{
                    review_status: "reviewing",
                    review_status_ko: "reviewing",
                    count: 1,
                    items: [{
                      notice_id: "REVIEWING-1",
                      title: "Review notice",
                      agency: "Agency",
                      deadline: "2099-01-01",
                      deadline_status: "upcoming",
                      review_status: "reviewing",
                      score: 82,
                      risk_level: "medium",
                      next_action: "Confirm scope",
                      filter_payload: {
                        review_status: "reviewing",
                        shortlisted_only: false,
                        hide_archived_no_go: true,
                        sort: "deadline_asc"
                      }
                    }],
                    filter_payload: {
                      review_status: "reviewing",
                      shortlisted_only: false,
                      hide_archived_no_go: true,
                      sort: "deadline_asc"
                    }
                  }],
                  deadline_first_actions: [{
                    notice_id: "REVIEWING-1",
                    title: "Review notice",
                    agency: "Agency",
                    deadline: "2099-01-01",
                    deadline_status: "upcoming",
                    review_status: "reviewing",
                    score: 82,
                    risk_level: "medium",
                    next_action: "Confirm scope",
                    filter_payload: {
                      review_status: "reviewing",
                      shortlisted_only: false,
                      hide_archived_no_go: true,
                      sort: "deadline_asc"
                    }
                  }]
                });
              `, context);
              assert.strictEqual(elements["review-board-cards"].children.length, 1);
              assert.strictEqual(elements["review-board-next-actions"].children.length, 1);
              const boardButton = elements["review-board-cards"].children[0].children[0];
              assert.ok(boardButton);
              await boardButton.click();
              assert.strictEqual(elements["opportunity-review-filter"].value, "reviewing");
              assert.strictEqual(elements["opportunity-hide-archived-no-go"].checked, true);
              assert.strictEqual(elements["opportunity-sort"].value, "deadline_asc");
              assert.ok(
                fetchCalls.some((url) =>
                  String(url).includes("review_status=reviewing") &&
                  String(url).includes("hide_archived_no_go=true") &&
                  String(url).includes("sort=deadline_asc")
                ),
              );

              vm.runInContext(
                "renderReviewBoard({ cards: [], deadline_first_actions: [], status_counts: {} });",
                context,
              );
              assert.match(
                elements["review-board-empty"].textContent,
                /No active review board items/i,
              );
            })().catch((error) => {
              console.error(error);
              process.exit(1);
            });
            """
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [node, str(check_script), str(PROJECT_ROOT / "app" / "ui" / "static" / "dashboard.js")],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_dashboard_decision_memo_helpers_render_known_notice_and_safe_empty_state(
    tmp_path: Path,
) -> None:
    node = shutil.which("node")
    assert node is not None, "node is required for dashboard render validation"

    check_script = tmp_path / "dashboard_decision_memo_check.js"
    check_script.write_text(
        textwrap.dedent(
            """
            const fs = require("fs");
            const vm = require("vm");
            const assert = require("assert");

            function makeElement(id) {
              const element = {
                id,
                tagName: id,
                textContent: "Loading",
                children: [],
                dataset: {},
                value: "",
                checked: false,
                listeners: {},
                appendChild(child) {
                  this.children.push(child);
                },
                addEventListener(type, handler) {
                  this.listeners[type] = handler;
                },
                click() {
                  if (this.listeners.click) {
                    return this.listeners.click({ currentTarget: this, preventDefault() {} });
                  }
                  return undefined;
                },
                remove() {},
              };
              Object.defineProperty(element, "innerHTML", {
                get() {
                  return this._innerHTML || "";
                },
                set(value) {
                  this._innerHTML = value;
                  this.children = [];
                },
              });
              return element;
            }

            const elementIds = [
              "decision-memo-status",
              "decision-memo-notice-id",
              "decision-memo-summary",
              "decision-memo-decision",
              "decision-memo-rationale",
              "decision-memo-fit-summary",
              "decision-memo-risk-summary",
              "decision-memo-next-action",
              "decision-memo-preparation-actions",
              "decision-memo-required-documents",
              "decision-memo-copy-block",
              "open-selected-decision-memo",
              "load-decision-memo",
            ];
            const elements = Object.fromEntries(elementIds.map((id) => [id, makeElement(id)]));
            const document = {
              body: makeElement("body"),
              createElement(tag) {
                return makeElement(tag);
              },
              getElementById(id) {
                return elements[id] || null;
              },
              querySelector() {
                return null;
              },
              addEventListener() {},
            };
            const responses = {
              "/ops/decision-memo/G2B-SAMPLE-2026-001": {
                status: "success",
                notice_id: "G2B-SAMPLE-2026-001",
                notice: {
                  title: "Seoul AI workflow automation",
                  agency: "Seoul agency",
                  deadline: "2026-07-15",
                },
                yonlab_fit_summary: {
                  fit_reasons: ["AI/SW fit", "Seoul region fit"],
                  concern_reasons: ["Further review needed"],
                },
                risk_summary: {
                  eligibility_risks: ["Recent performance check required"],
                  document_risks: ["Document review required"],
                  schedule_risks: ["Deadline approaching"],
                  commercial_risks: [],
                },
                deadline_next_action: {
                  deadline: "2026-07-15",
                  urgency: "due_soon",
                  next_action: "Confirm proposal schedule",
                },
                recommended_decision: {
                  value: "Prepare",
                  rationale: "Fit is strong enough to begin preparation.",
                },
                preparation_actions: [
                  { action: "Draft proposal scope", owner: "ops", priority: "high" },
                ],
                required_documents: [
                  { name: "Software business certificate", status: "required", reason: "required" },
                ],
                export_blocks: {
                  markdown: "# YOnLab Decision Memo\\n\\n- Decision: Prepare",
                  short_summary: "Prepare - Seoul AI workflow automation",
                },
                safety: {
                  real_api_call_attempted: false,
                  source_data_mode: "fixture",
                },
              },
              "/ops/decision-memo/UNKNOWN-NOTICE-ID": {
                status: "not_found",
                notice_id: "UNKNOWN-NOTICE-ID",
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
                  next_action:
                    "Select a known local notice from Review Board or Opportunity Inbox.",
                },
                recommended_decision: {
                  value: "Hold",
                  rationale: "No local-safe notice data is available yet for this notice id.",
                },
                preparation_actions: [],
                required_documents: [],
                export_blocks: {
                  markdown: "# YOnLab Decision Memo\\n\\nDecision Memo Unavailable",
                  short_summary: "Decision memo unavailable for notice UNKNOWN-NOTICE-ID.",
                },
                safety: {
                  real_api_call_attempted: false,
                  source_data_mode: "empty",
                },
              },
            };
            const context = {
              Blob: function Blob() {},
              URL: { createObjectURL: () => "blob://local", revokeObjectURL() {} },
              URLSearchParams,
              console,
              document,
              elements,
              encodeURIComponent,
              fetch: async (url) => ({
                ok: true,
                status: 200,
                statusText: "OK",
                json: async () => {
                  if (!responses[url]) {
                    throw new Error("Unexpected fetch " + url);
                  }
                  return responses[url];
                },
              }),
            };

            (async () => {
              vm.createContext(context);
              vm.runInContext(fs.readFileSync(process.argv[2], "utf8"), context);

              await vm.runInContext('loadDecisionMemo("G2B-SAMPLE-2026-001")', context);
              assert.match(
                elements["decision-memo-summary"].textContent,
                /Seoul AI workflow automation/,
              );
              assert.match(elements["decision-memo-summary"].textContent, /Seoul agency/);
              assert.match(elements["decision-memo-summary"].textContent, /2026-07-15/);
              assert.match(elements["decision-memo-decision"].textContent, /Prepare/);
              assert.match(
                elements["decision-memo-fit-summary"].children[0].textContent,
                /AI\\/SW fit/,
              );
              assert.match(
                elements["decision-memo-risk-summary"].children[0].textContent,
                /Recent performance check required/,
              );
              assert.match(
                elements["decision-memo-next-action"].children[2].textContent,
                /Confirm proposal schedule/,
              );
              assert.match(
                elements["decision-memo-preparation-actions"].children[0].textContent,
                /Draft proposal scope/,
              );
              assert.match(
                elements["decision-memo-required-documents"].children[0].textContent,
                /Software business certificate/,
              );
              assert.match(elements["decision-memo-copy-block"].textContent, /Decision: Prepare/);

              await vm.runInContext('loadDecisionMemo("UNKNOWN-NOTICE-ID")', context);
              assert.match(elements["decision-memo-status"].textContent, /not_found/);
              assert.match(elements["decision-memo-decision"].textContent, /Hold/);
              assert.match(
                elements["decision-memo-summary"].textContent,
                /Decision memo unavailable/i,
              );
              assert.match(
                elements["decision-memo-next-action"].children[2].textContent,
                /Select a known local notice/i,
              );
            })().catch((error) => {
              console.error(error);
              process.exit(1);
            });
            """
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [node, str(check_script), str(PROJECT_ROOT / "app" / "ui" / "static" / "dashboard.js")],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_dashboard_review_board_items_can_open_decision_memo_without_real_api(
    tmp_path: Path,
) -> None:
    node = shutil.which("node")
    assert node is not None, "node is required for dashboard render validation"

    check_script = tmp_path / "dashboard_review_board_decision_memo_check.js"
    check_script.write_text(
        textwrap.dedent(
            """
            const fs = require("fs");
            const vm = require("vm");
            const assert = require("assert");

            function makeElement(id) {
              const element = {
                id,
                tagName: id,
                textContent: "Loading",
                children: [],
                dataset: {},
                value: "",
                checked: false,
                listeners: {},
                appendChild(child) {
                  this.children.push(child);
                },
                addEventListener(type, handler) {
                  this.listeners[type] = handler;
                },
                click() {
                  if (this.listeners.click) {
                    return this.listeners.click({ currentTarget: this, preventDefault() {} });
                  }
                  return undefined;
                },
                remove() {},
              };
              Object.defineProperty(element, "innerHTML", {
                get() {
                  return this._innerHTML || "";
                },
                set(value) {
                  this._innerHTML = value;
                  this.children = [];
                },
              });
              return element;
            }

            const elementIds = [
              "review-board-cards",
              "review-board-next-actions",
              "review-board-empty",
              "review-board-generated-at",
              "review-board-source",
              "review-board-total-count",
              "review-board-active-count",
              "review-board-go",
              "review-board-reviewing",
              "review-board-shortlisted",
              "review-board-hold",
              "opportunity-review-filter",
              "opportunity-hide-archived-no-go",
              "opportunity-shortlisted-only",
              "opportunity-sort",
              "opportunity-keyword",
              "opportunity-grade",
              "opportunity-risk",
              "opportunity-source",
              "opportunity-body",
              "opportunity-empty",
              "source-mode-current",
              "source-mode-message",
              "source-mode-latest-run",
              "source-mode-latest-at",
              "source-mode-real-reports",
              "source-mode-total-items",
              "source-mode-next-actions",
              "priority-legend",
              "decision-memo-status",
              "decision-memo-notice-id",
              "decision-memo-summary",
              "decision-memo-decision",
              "decision-memo-rationale",
              "decision-memo-fit-summary",
              "decision-memo-risk-summary",
              "decision-memo-next-action",
              "decision-memo-preparation-actions",
              "decision-memo-required-documents",
              "decision-memo-copy-block",
            ];
            const elements = Object.fromEntries(elementIds.map((id) => [id, makeElement(id)]));
            const document = {
              body: makeElement("body"),
              createElement(tag) {
                return makeElement(tag);
              },
              getElementById(id) {
                return elements[id] || null;
              },
              querySelector() {
                return null;
              },
              addEventListener() {},
            };
            const fetchCalls = [];
            const context = {
              Blob: function Blob() {},
              URL: { createObjectURL: () => "blob://local", revokeObjectURL() {} },
              URLSearchParams,
              console,
              document,
              elements,
              encodeURIComponent,
              fetch: async (url) => {
                fetchCalls.push(url);
                if (String(url).startsWith("/ops/opportunity-inbox?")) {
                  return {
                    ok: true,
                    status: 200,
                    statusText: "OK",
                    json: async () => ({
                      items: [],
                      source_mode: "saved",
                      empty_state_message: "",
                      empty_state_next_actions: [],
                      priority_legend: {},
                    }),
                  };
                }
                if (String(url) === "/ops/decision-memo/REVIEWING-1") {
                  return {
                    ok: true,
                    status: 200,
                    statusText: "OK",
                    json: async () => ({
                      status: "success",
                      notice_id: "REVIEWING-1",
                      notice: {
                        title: "Review notice",
                        agency: "Agency",
                        deadline: "2099-01-01",
                      },
                      yonlab_fit_summary: { fit_reasons: ["AI fit"], concern_reasons: [] },
                      risk_summary: {
                        eligibility_risks: [],
                        document_risks: [],
                        schedule_risks: [],
                        commercial_risks: ["Confirm scope"],
                      },
                      deadline_next_action: {
                        deadline: "2099-01-01",
                        urgency: "upcoming",
                        next_action: "Confirm scope",
                      },
                      recommended_decision: {
                        value: "Review",
                        rationale: "Further operator review needed.",
                      },
                      preparation_actions: [],
                      required_documents: [],
                      export_blocks: {
                        markdown: "# YOnLab Decision Memo",
                        short_summary: "Review - Review notice",
                      },
                      safety: {
                        real_api_call_attempted: false,
                        source_data_mode: "saved",
                      },
                    }),
                  };
                }
                throw new Error("Unexpected fetch " + url);
              },
            };

            (async () => {
              vm.createContext(context);
              vm.runInContext(fs.readFileSync(process.argv[2], "utf8"), context);
              vm.runInContext(`
                renderReviewBoard({
                  generated_at: "2026-06-29T12:00:00+00:00",
                  source: "saved",
                  total_count: 1,
                  active_count: 1,
                  status_counts: { go: 0, reviewing: 1, shortlisted: 0, hold: 0 },
                  cards: [{
                    review_status: "reviewing",
                    review_status_ko: "reviewing",
                    count: 1,
                    items: [{
                      notice_id: "REVIEWING-1",
                      title: "Review notice",
                      agency: "Agency",
                      deadline: "2099-01-01",
                      deadline_status: "upcoming",
                      review_status: "reviewing",
                      score: 82,
                      risk_level: "medium",
                      next_action: "Confirm scope",
                      filter_payload: {
                        review_status: "reviewing",
                        shortlisted_only: false,
                        hide_archived_no_go: true,
                        sort: "deadline_asc"
                      }
                    }],
                    filter_payload: {
                      review_status: "reviewing",
                      shortlisted_only: false,
                      hide_archived_no_go: true,
                      sort: "deadline_asc"
                    }
                  }],
                  deadline_first_actions: []
                });
              `, context);

              const reviewBoardCard = elements["review-board-cards"].children[0];
              const list = reviewBoardCard.children[2];
              const itemButton = list.children[0].children[0];
              await itemButton.click();

              assert.strictEqual(elements["opportunity-review-filter"].value, "reviewing");
              assert.strictEqual(elements["opportunity-sort"].value, "deadline_asc");
              assert.strictEqual(elements["decision-memo-notice-id"].value, "REVIEWING-1");
              assert.match(elements["decision-memo-summary"].textContent, /Review notice/);
              assert.match(elements["decision-memo-decision"].textContent, /Review/);
              assert.ok(fetchCalls.includes("/ops/decision-memo/REVIEWING-1"));
              assert.ok(
                fetchCalls.some((url) =>
                  String(url).includes("review_status=reviewing") &&
                  String(url).includes("sort=deadline_asc")
                ),
              );
            })().catch((error) => {
              console.error(error);
              process.exit(1);
            });
            """
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [node, str(check_script), str(PROJECT_ROOT / "app" / "ui" / "static" / "dashboard.js")],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_duplicated_korean_fragments_absent_from_fixture_and_fresh_ops_output(
    tmp_path: Path,
    monkeypatch,
) -> None:  # noqa: ANN001
    settings = _tmp_settings(tmp_path)
    monkeypatch.setattr(routes, "get_settings", lambda: settings)

    fixture_text = json.dumps(load_sample_g2b_notices(), ensure_ascii=False)
    run = client.post(
        "/ops/run-recommendations",
        json={"mode": "fixture", "keyword": "AI", "num_rows": 3, "include_reports": True},
    ).json()
    detail = client.get(f"/ops/runs/{run['run_id']}").json()
    recommendations = client.get(
        "/ops/recommendations",
        params={"run_id": run["run_id"], "limit": 10},
    ).json()
    output_text = json.dumps(
        {"fixture": fixture_text, "detail": detail, "recommendations": recommendations},
        ensure_ascii=False,
    )

    for fragment in DUPLICATED_KOREAN_FRAGMENTS:
        assert fragment not in output_text


def _tmp_settings(tmp_path: Path) -> Settings:
    return Settings(
        yonlab_storage_db_path=str(tmp_path / "ops" / "yonlab.sqlite3"),
        yonlab_report_dir=str(tmp_path / "reports"),
        yonlab_default_run_mode="fixture",
        yonlab_default_keyword="AI",
        yonlab_default_num_rows=3,
    )
