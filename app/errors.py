"""Application errors that are safe to return to a client.

Messages name columns and counts. They do not include cell values or group labels.
"""


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 400,
        fields: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.fields = fields or {}


class ValidationFailure(AppError):
    def __init__(self, code: str, message: str, fields: dict[str, str] | None = None) -> None:
        super().__init__(code, message, status_code=422, fields=fields)


class NotFoundError(AppError):
    def __init__(self, message: str = "Not found.") -> None:
        super().__init__("not_found", message, status_code=404)
