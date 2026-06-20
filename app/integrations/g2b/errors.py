class G2BClientError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int | None = None,
        safe_endpoint_path: str | None = None,
    ) -> None:
        self.code = code
        self.status_code = status_code
        self.safe_endpoint_path = safe_endpoint_path
        self.service_key_exposed = False
        super().__init__(message)
