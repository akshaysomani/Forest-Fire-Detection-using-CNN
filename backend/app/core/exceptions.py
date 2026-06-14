from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


class BaseAPIException(Exception):
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "INTERNAL_SERVER_ERROR"
    message: str = "An unexpected error occurred."

    def __init__(self, message: str = None, details: dict = None):
        if message:
            self.message = message
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationException(BaseAPIException):
    status_code: int = status.HTTP_401_UNAUTHORIZED
    error_code: str = "UNAUTHENTICATED"
    message: str = "Authentication credentials were not provided or are invalid."


class TokenExpiredException(AuthenticationException):
    error_code: str = "TOKEN_EXPIRED"
    message: str = "The authentication token has expired."


class InvalidCredentialsException(AuthenticationException):
    error_code: str = "INVALID_CREDENTIALS"
    message: str = "Incorrect email, username, or password."


class AccountLockedException(AuthenticationException):
    status_code: int = status.HTTP_403_FORBIDDEN
    error_code: str = "ACCOUNT_LOCKED"
    message: str = "This account has been temporarily locked due to excessive failed attempts."


class AuthorizationException(BaseAPIException):
    status_code: int = status.HTTP_403_FORBIDDEN
    error_code: str = "UNAUTHORIZED"
    message: str = "You do not have the required permissions to perform this action."


class ValidationException(BaseAPIException):
    status_code: int = status.HTTP_422_UNPROCESSABLE_CONTENT
    error_code: str = "VALIDATION_ERROR"
    message: str = "Request validation failed."


class EntityNotFoundException(BaseAPIException):
    status_code: int = status.HTTP_404_NOT_FOUND
    error_code: str = "NOT_FOUND"
    message: str = "The requested resource could not be found."


class DashboardException(BaseAPIException):
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "DASHBOARD_ERROR"
    message: str = "An error occurred while compiling the dashboard overview."


class AnalyticsException(BaseAPIException):
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "ANALYTICS_ERROR"
    message: str = "An error occurred during trend analytics processing."


class MonitoringException(BaseAPIException):
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "MONITORING_ERROR"
    message: str = "Failed to retrieve real-time system metrics."


class DataAggregationException(BaseAPIException):
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "DATA_AGGREGATION_ERROR"
    message: str = "Database query aggregation failed."


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BaseAPIException)
    async def base_api_exception_handler(request: Request, exc: BaseAPIException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "error": {"code": exc.error_code, "message": exc.message, "details": exc.details}},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        details = {}
        for error in exc.errors():
            loc = ".".join(str(x) for x in error["loc"][1:]) if len(error["loc"]) > 1 else str(error["loc"][0])
            details[loc] = error["msg"]

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "One or more validation errors occurred.",
                    "details": details,
                },
            },
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        # Prevent sensitive leakage
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {"code": "INTERNAL_SERVER_ERROR", "message": "An internal server error occurred."},
            },
        )
