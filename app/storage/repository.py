import json
from pathlib import Path
from typing import Any

from app.storage.database import connect_database, initialize_database
from app.storage.models import StoredRecommendation, StoredReport, StoredSearchRun


class OperationsRepository:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        initialize_database(self.db_path)

    def save_search_run(self, run: StoredSearchRun) -> None:
        with connect_database(self.db_path) as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO search_runs (
                    run_id, created_at, mode, keyword, start_date, end_date, num_rows,
                    source_count, status, message, error_code, service_key_exposed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.run_id,
                    run.created_at,
                    run.mode,
                    run.keyword,
                    run.start_date,
                    run.end_date,
                    run.num_rows,
                    run.source_count,
                    run.status,
                    run.message,
                    run.error_code,
                    int(run.service_key_exposed),
                ),
            )

    def save_recommendation(self, recommendation: StoredRecommendation) -> None:
        with connect_database(self.db_path) as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO recommendations (
                    run_id, rank, notice_id, title, agency, budget_amount, deadline,
                    total_score, recommendation_label, risk_count, top_reasons_json,
                    risk_summaries_json, detail_url, report_path, raw_json_path, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    recommendation.run_id,
                    recommendation.rank,
                    recommendation.notice_id,
                    recommendation.title,
                    recommendation.agency,
                    recommendation.budget_amount,
                    recommendation.deadline,
                    recommendation.total_score,
                    recommendation.recommendation_label,
                    recommendation.risk_count,
                    json.dumps(recommendation.top_reasons, ensure_ascii=False),
                    json.dumps(recommendation.risk_summaries, ensure_ascii=False),
                    recommendation.detail_url,
                    recommendation.report_path,
                    recommendation.raw_json_path,
                    recommendation.created_at,
                ),
            )

    def save_report(self, report: StoredReport) -> None:
        with connect_database(self.db_path) as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO reports (
                    run_id, notice_id, title, report_path, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    report.run_id,
                    report.notice_id,
                    report.title,
                    report.report_path,
                    report.created_at,
                ),
            )

    def list_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        with connect_database(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT * FROM search_runs
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [_row_to_dict(row) for row in rows]

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with connect_database(self.db_path) as connection:
            row = connection.execute(
                "SELECT * FROM search_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        return _row_to_dict(row) if row else None

    def list_recommendations(
        self,
        *,
        limit: int = 20,
        min_score: int | None = None,
        label: str | None = None,
        keyword: str | None = None,
        run_id: str | None = None,
    ) -> list[dict[str, Any]]:
        filters = []
        params: list[Any] = []
        if min_score is not None:
            filters.append("recommendations.total_score >= ?")
            params.append(min_score)
        if label:
            filters.append("recommendations.recommendation_label = ?")
            params.append(label)
        if keyword:
            filters.append("search_runs.keyword = ?")
            params.append(keyword)
        if run_id:
            filters.append("recommendations.run_id = ?")
            params.append(run_id)

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        params.append(limit)
        with connect_database(self.db_path) as connection:
            rows = connection.execute(
                f"""
                SELECT recommendations.*
                FROM recommendations
                LEFT JOIN search_runs ON recommendations.run_id = search_runs.run_id
                {where_clause}
                ORDER BY recommendations.created_at DESC, recommendations.rank ASC
                LIMIT ?
                """,
                params,
            ).fetchall()
        return [_recommendation_row_to_dict(row) for row in rows]

    def list_reports(self, run_id: str) -> list[dict[str, Any]]:
        with connect_database(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT * FROM reports
                WHERE run_id = ?
                ORDER BY created_at DESC, id ASC
                """,
                (run_id,),
            ).fetchall()
        return [_row_to_dict(row) for row in rows]

    def list_report_index(self, limit: int = 20) -> list[dict[str, Any]]:
        with connect_database(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT
                    reports.run_id,
                    reports.notice_id,
                    reports.title,
                    reports.report_path,
                    reports.created_at,
                    search_runs.mode,
                    search_runs.keyword,
                    search_runs.start_date,
                    search_runs.end_date,
                    search_runs.source_count AS total_items,
                    search_runs.status AS run_status,
                    search_runs.message AS run_message,
                    search_runs.error_code,
                    report_recommendation.total_score AS matching_score,
                    report_recommendation.recommendation_label AS recommendation_grade,
                    report_recommendation.risk_count AS report_warning_count,
                    COALESCE(run_quality.recommendation_count, 0) AS recommendation_count,
                    COALESCE(run_quality.recommended_count, 0) AS recommended_count,
                    COALESCE(run_quality.average_score, 0) AS average_score,
                    COALESCE(run_quality.score_min, 0) AS score_min,
                    COALESCE(run_quality.score_max, 0) AS score_max,
                    COALESCE(run_quality.warning_count, 0) AS run_warning_count
                FROM reports
                LEFT JOIN search_runs ON reports.run_id = search_runs.run_id
                LEFT JOIN recommendations AS report_recommendation
                    ON reports.run_id = report_recommendation.run_id
                    AND reports.notice_id = report_recommendation.notice_id
                LEFT JOIN (
                    SELECT
                        run_id,
                        COUNT(*) AS recommendation_count,
                        SUM(
                            CASE
                                WHEN recommendation_label IN ('적극 추천', '추천') THEN 1
                                ELSE 0
                            END
                        ) AS recommended_count,
                        AVG(total_score) AS average_score,
                        MIN(total_score) AS score_min,
                        MAX(total_score) AS score_max,
                        SUM(risk_count) AS warning_count
                    FROM recommendations
                    GROUP BY run_id
                ) AS run_quality ON reports.run_id = run_quality.run_id
                ORDER BY reports.created_at DESC, reports.id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [_report_index_row_to_dict(row) for row in rows]

    def build_quality_summary(self) -> dict[str, Any]:
        with connect_database(self.db_path) as connection:
            run_count = connection.execute("SELECT COUNT(*) FROM search_runs").fetchone()[0]
            report_count = connection.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
            real_report_count = connection.execute(
                """
                SELECT COUNT(*)
                FROM reports
                LEFT JOIN search_runs ON reports.run_id = search_runs.run_id
                WHERE search_runs.mode = 'real'
                """
            ).fetchone()[0]
            recommendation_row = connection.execute(
                """
                SELECT
                    COUNT(*) AS total_recommendations,
                    COALESCE(AVG(total_score), 0) AS average_score,
                    SUM(CASE WHEN recommendation_label = '적극 추천' THEN 1 ELSE 0 END)
                        AS strong_recommend_count,
                    SUM(CASE WHEN recommendation_label = '추천' THEN 1 ELSE 0 END)
                        AS recommend_count,
                    SUM(CASE WHEN recommendation_label = '조건부 검토' THEN 1 ELSE 0 END)
                        AS consider_count,
                    SUM(CASE WHEN recommendation_label = '비추천' THEN 1 ELSE 0 END)
                        AS not_recommended_count
                FROM recommendations
                """
            ).fetchone()
            label_rows = connection.execute(
                """
                SELECT recommendation_label, COUNT(*) AS count
                FROM recommendations
                GROUP BY recommendation_label
                ORDER BY count DESC, recommendation_label ASC
                """
            ).fetchall()
            run_status_row = connection.execute(
                """
                SELECT
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS success_count,
                    SUM(CASE WHEN status != 'success' THEN 1 ELSE 0 END) AS error_count,
                    SUM(CASE WHEN mode = 'real' THEN 1 ELSE 0 END) AS real_run_count,
                    SUM(CASE WHEN mode = 'fixture' THEN 1 ELSE 0 END) AS fixture_run_count
                FROM search_runs
                """
            ).fetchone()
            warning_count = connection.execute(
                "SELECT COALESCE(SUM(risk_count), 0) FROM recommendations"
            ).fetchone()[0]
            latest_run = connection.execute(
                """
                SELECT
                    run_id, created_at, mode, keyword, source_count, status, message,
                    error_code
                FROM search_runs
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """
            ).fetchone()

        total_recommendations = int(recommendation_row["total_recommendations"] or 0)
        error_count = int(run_status_row["error_count"] or 0)
        summary_status = _quality_summary_status(
            run_count=int(run_count or 0),
            total_recommendations=total_recommendations,
            error_count=error_count,
            latest_run_status=latest_run["status"] if latest_run else None,
        )
        quality_label_distribution = {
            row["recommendation_label"]: int(row["count"] or 0) for row in label_rows
        }
        return {
            "total_runs": int(run_count or 0),
            "total_reports": int(report_count or 0),
            "real_report_count": int(real_report_count or 0),
            "total_recommendations": total_recommendations,
            "strong_recommend_count": int(recommendation_row["strong_recommend_count"] or 0),
            "recommend_count": int(recommendation_row["recommend_count"] or 0),
            "consider_count": int(recommendation_row["consider_count"] or 0),
            "not_recommended_count": int(recommendation_row["not_recommended_count"] or 0),
            "average_score": round(float(recommendation_row["average_score"] or 0), 2),
            "summary_status": summary_status,
            "latest_run_id": latest_run["run_id"] if latest_run else None,
            "latest_run_created_at": latest_run["created_at"] if latest_run else None,
            "latest_run": _safe_latest_run(latest_run),
            "successful_run_count": int(run_status_row["success_count"] or 0),
            "failed_run_count": error_count,
            "warning_count": int(warning_count or 0),
            "error_count": error_count,
            "real_run_count": int(run_status_row["real_run_count"] or 0),
            "fixture_run_count": int(run_status_row["fixture_run_count"] or 0),
            "real_mode_executed": bool(run_status_row["real_run_count"] or 0),
            "real_mode_status": "executed"
            if run_status_row["real_run_count"]
            else "skipped",
            "quality_label_distribution": quality_label_distribution,
            "service_key_exposed": False,
        }

    def get_report(self, run_id: str, notice_id: str) -> dict[str, Any] | None:
        with connect_database(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT * FROM reports
                WHERE run_id = ? AND notice_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (run_id, notice_id),
            ).fetchone()
        return _row_to_dict(row) if row else None

    def get_run_detail(self, run_id: str) -> dict[str, Any]:
        return {
            "run": self.get_run(run_id),
            "recommendations": self.list_recommendations(limit=100, run_id=run_id),
            "reports": self.list_reports(run_id),
        }


def _row_to_dict(row: Any) -> dict[str, Any]:
    item = dict(row)
    if "service_key_exposed" in item:
        item["service_key_exposed"] = bool(item["service_key_exposed"])
    return item


def _recommendation_row_to_dict(row: Any) -> dict[str, Any]:
    item = _row_to_dict(row)
    item["top_reasons"] = json.loads(item.pop("top_reasons_json") or "[]")
    item["risk_summaries"] = json.loads(item.pop("risk_summaries_json") or "[]")
    return item


def _report_index_row_to_dict(row: Any) -> dict[str, Any]:
    item = _row_to_dict(row)
    item["total_items"] = int(item.get("total_items") or 0)
    item["recommendation_count"] = int(item.get("recommendation_count") or 0)
    item["recommended_count"] = int(item.get("recommended_count") or 0)
    item["average_score"] = round(float(item.get("average_score") or 0), 2)
    item["score_min"] = int(item.get("score_min") or 0)
    item["score_max"] = int(item.get("score_max") or 0)
    item["matching_score"] = int(item.get("matching_score") or 0)
    item["recommendation_grade"] = item.get("recommendation_grade") or "unknown"
    item["warning_count"] = int(item.get("report_warning_count") or 0)
    item["run_warning_count"] = int(item.get("run_warning_count") or 0)
    item["error_count"] = 1 if item.get("run_status") and item["run_status"] != "success" else 0
    item["source"] = item.get("mode") or "unknown"
    item["query_label"] = _query_label(item)
    item["quality_label"] = _report_quality_label(item)
    item["report_metadata_reference"] = f"{item['run_id']}:{item['notice_id']}"
    return item


def _query_label(item: dict[str, Any]) -> str:
    keyword = item.get("keyword") or "no keyword"
    start_date = item.get("start_date")
    end_date = item.get("end_date")
    if start_date or end_date:
        return f"{keyword} ({start_date or 'open'} to {end_date or 'open'})"
    return str(keyword)


def _report_quality_label(item: dict[str, Any]) -> str:
    if item.get("run_status") and item["run_status"] != "success":
        return "failure"
    if int(item.get("recommendation_count") or 0) == 0:
        return "empty"
    matching_score = int(item.get("matching_score") or 0)
    if matching_score >= 80:
        return "strong_fit"
    if matching_score >= 65:
        return "recommended"
    if matching_score >= 50:
        return "review"
    return "low_fit"


def _quality_summary_status(
    *,
    run_count: int,
    total_recommendations: int,
    error_count: int,
    latest_run_status: str | None,
) -> str:
    if run_count == 0:
        return "empty"
    if latest_run_status and latest_run_status != "success":
        return "failure"
    if total_recommendations == 0:
        return "empty"
    if error_count:
        return "success_with_warnings"
    return "success"


def _safe_latest_run(row: Any) -> dict[str, Any] | None:
    if row is None:
        return None
    item = _row_to_dict(row)
    return {
        "run_id": item["run_id"],
        "created_at": item["created_at"],
        "mode": item["mode"],
        "keyword": item["keyword"],
        "source_count": item["source_count"],
        "status": item["status"],
        "message": item["message"],
        "error_code": item["error_code"],
    }
