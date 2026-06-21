from pathlib import Path
import json
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
