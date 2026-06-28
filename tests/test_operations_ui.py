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
                json: async () => responses[url],
              }),
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
