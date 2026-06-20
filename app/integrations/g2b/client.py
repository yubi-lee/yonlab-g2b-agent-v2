from typing import Any
from urllib.parse import urljoin

import httpx

from app.core.config import Settings
from app.domain.search import G2BSearchRequest
from app.integrations.g2b.capture import MASKED_VALUE, capture_real_response
from app.integrations.g2b.errors import G2BClientError
from app.integrations.g2b.presets import (
    ENDPOINT_PATH_SOURCE_MISSING,
    ENDPOINT_PATH_SOURCE_UNKNOWN_PRESET,
    resolve_endpoint_path,
)


class G2BClient:
    def __init__(self, settings: Settings, http_client: httpx.Client | None = None) -> None:
        self.settings = settings
        self.http_client = http_client

    def search(self, request: G2BSearchRequest) -> list[dict[str, Any]]:
        self._ensure_real_api_allowed(request.confirm_real_api_call)

        params = self._build_params(request)
        try:
            if self.http_client is not None:
                response = self.http_client.get(self._build_url(), params=params)
            else:
                with httpx.Client(timeout=self.settings.g2b_request_timeout_seconds) as client:
                    response = client.get(self._build_url(), params=params)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise G2BClientError("timeout", "G2B request timed out.") from exc
        except httpx.HTTPStatusError as exc:
            raise G2BClientError("http_error", "G2B request returned an HTTP error.") from exc
        except httpx.HTTPError as exc:
            raise G2BClientError("transport_error", "G2B request failed.") from exc

        payload = self._extract_payload(response)
        notices = _find_notice_items(payload)
        if notices is None:
            raise G2BClientError(
                "unexpected_response_shape",
                "G2B response did not contain recognizable notice items.",
            )

        if self.settings.g2b_capture_real_responses:
            capture_real_response(
                capture_dir=self.settings.g2b_capture_dir,
                request_metadata={
                    "url": self._build_url(),
                    "params": self._masked_params(params),
                },
                response_payload=payload,
            )

        return notices

    def _ensure_real_api_allowed(self, confirm_real_api_call: bool) -> None:
        if not self.settings.g2b_enable_real_api:
            raise G2BClientError("real_api_disabled", "Real G2B API access is disabled.")
        if not confirm_real_api_call:
            raise G2BClientError(
                "real_api_confirmation_required",
                "Real G2B API access requires confirm_real_api_call=true.",
            )
        if not self.settings.g2b_api_service_key:
            raise G2BClientError("service_key_missing", "G2B API service key is not configured.")
        _, endpoint_path_source = resolve_endpoint_path(self.settings)
        if endpoint_path_source == ENDPOINT_PATH_SOURCE_MISSING:
            raise G2BClientError(
                "endpoint_path_missing",
                "G2B list endpoint path is not configured.",
            )
        if endpoint_path_source == ENDPOINT_PATH_SOURCE_UNKNOWN_PRESET:
            raise G2BClientError(
                "endpoint_preset_unknown",
                "G2B endpoint preset is not recognized.",
            )

    def _build_url(self) -> str:
        base_url = self.settings.g2b_api_base_url.rstrip("/") + "/"
        endpoint_path, _ = resolve_endpoint_path(self.settings)
        endpoint_path = endpoint_path.lstrip("/")
        return urljoin(base_url, endpoint_path)

    def _build_params(self, request: G2BSearchRequest) -> dict[str, Any]:
        params: dict[str, Any] = {
            "serviceKey": self.settings.g2b_api_service_key,
            "pageNo": request.page_no or self.settings.g2b_default_page_no,
            "numOfRows": request.num_rows or self.settings.g2b_default_num_rows,
            "_type": "json",
        }
        optional_params = {
            "keyword": request.keyword,
            "startDate": request.start_date,
            "endDate": request.end_date,
            "businessType": request.business_type,
        }
        params.update({key: value for key, value in optional_params.items() if value})
        return params

    def _extract_payload(self, response: httpx.Response) -> Any:
        if not response.content:
            raise G2BClientError("empty_response", "G2B response was empty.")

        try:
            return response.json()
        except ValueError as exc:
            response_text = response.text.strip()
            if response_text.startswith("<"):
                raise G2BClientError(
                    "unsupported_response_format",
                    "G2B response format is not supported.",
                ) from exc
            raise G2BClientError("invalid_json", "G2B response was not valid JSON.") from exc

    def _masked_params(self, params: dict[str, Any]) -> dict[str, Any]:
        masked = dict(params)
        if "serviceKey" in masked:
            masked["serviceKey"] = MASKED_VALUE
        return masked


def _find_notice_items(payload: Any) -> list[dict[str, Any]] | None:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return None

    candidates = [
        payload.get("item"),
        payload.get("items"),
        payload.get("data"),
        payload.get("notices"),
        _nested_get(payload, ("response", "body", "items", "item")),
        _nested_get(payload, ("response", "body", "items")),
    ]
    for candidate in candidates:
        if isinstance(candidate, list):
            return [item for item in candidate if isinstance(item, dict)]
        if isinstance(candidate, dict):
            item = candidate.get("item")
            if isinstance(item, list):
                return [entry for entry in item if isinstance(entry, dict)]
            return [candidate]
    return None


def _nested_get(payload: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = payload
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current
