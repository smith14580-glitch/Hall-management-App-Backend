from fastapi import HTTPException, status


class AppError(HTTPException):
    def __init__(self, code: str, message: str, status_code: int = 400):
        super().__init__(status_code=status_code, detail={"code": code, "message": message})
        self.code = code


def unauthorized(message: str = "Not authenticated") -> AppError:
    return AppError("UNAUTHORIZED", message, status.HTTP_401_UNAUTHORIZED)


def forbidden(message: str = "Forbidden") -> AppError:
    return AppError("FORBIDDEN", message, status.HTTP_403_FORBIDDEN)


def not_found(message: str = "Not found") -> AppError:
    return AppError("NOT_FOUND", message, status.HTTP_404_NOT_FOUND)


def conflict(code: str, message: str) -> AppError:
    return AppError(code, message, status.HTTP_409_CONFLICT)


def validation_error(message: str = "Validation error") -> AppError:
    return AppError("VALIDATION_ERROR", message, status.HTTP_422_UNPROCESSABLE_ENTITY)
