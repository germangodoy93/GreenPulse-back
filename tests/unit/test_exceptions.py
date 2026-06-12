"""Unit tests for shared/exceptions/domain.py and handlers.py."""

import json

import pytest
from fastapi.exceptions import RequestValidationError
from starlette.requests import Request

from src.shared.exceptions.domain import (
    ConflictException,
    ForbiddenException,
    GreenPulseException,
    NotFoundException,
    UnauthorizedException,
    ValidationException,
)
from src.shared.exceptions.handlers import (
    domain_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)


def _mock_request() -> Request:
    """Create a minimal Starlette Request for handler tests."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/test",
        "headers": [],
        "query_string": b"",
    }
    return Request(scope=scope)  # type: ignore[arg-type]


# ── Domain exception hierarchy ────────────────────────────────────────────────

class TestGreenPulseException:
    def test_base_attributes(self) -> None:
        exc = GreenPulseException("msg", "CODE", 400)
        assert exc.message == "msg"
        assert exc.code == "CODE"
        assert exc.status_code == 400
        assert exc.details is None

    def test_details_stored(self) -> None:
        exc = GreenPulseException("msg", "CODE", details={"k": "v"})
        assert exc.details == {"k": "v"}


class TestNotFoundException:
    def test_status_code_is_404(self) -> None:
        assert NotFoundException("device", 1).status_code == 404

    def test_code_uppercased(self) -> None:
        assert NotFoundException("device", 1).code == "DEVICE_NOT_FOUND"

    def test_details_contain_id(self) -> None:
        assert NotFoundException("reading", 99).details == {"id": 99}

    def test_resource_name_in_message(self) -> None:
        exc = NotFoundException("alert", 7)
        assert "alert" in exc.message


class TestConflictException:
    def test_status_code_is_409(self) -> None:
        assert ConflictException("dup", "DUP").status_code == 409

    def test_details_passed_through(self) -> None:
        exc = ConflictException("dup", "DUP", details={"email": "x@y.com"})
        assert exc.details == {"email": "x@y.com"}


class TestUnauthorizedException:
    def test_status_code_is_401(self) -> None:
        assert UnauthorizedException().status_code == 401

    def test_code(self) -> None:
        assert UnauthorizedException().code == "UNAUTHORIZED"

    def test_custom_message(self) -> None:
        exc = UnauthorizedException("Token expirado")
        assert "Token expirado" in exc.message


class TestForbiddenException:
    def test_status_code_is_403(self) -> None:
        assert ForbiddenException().status_code == 403

    def test_code(self) -> None:
        assert ForbiddenException().code == "FORBIDDEN"


class TestValidationException:
    def test_status_code_is_422(self) -> None:
        assert ValidationException("campo requerido").status_code == 422

    def test_details(self) -> None:
        exc = ValidationException("err", details={"field": "email"})
        assert exc.details == {"field": "email"}


# ── Exception handlers ────────────────────────────────────────────────────────

class TestDomainExceptionHandler:
    @pytest.mark.asyncio
    async def test_correct_http_status(self) -> None:
        exc = NotFoundException("device", 42)
        response = await domain_exception_handler(_mock_request(), exc)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_response_envelope(self) -> None:
        exc = NotFoundException("device", 42)
        response = await domain_exception_handler(_mock_request(), exc)
        body = json.loads(response.body)
        assert body["success"] is False
        assert body["error"]["code"] == "DEVICE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_conflict_maps_to_409(self) -> None:
        exc = ConflictException("dup", "DUP_EMAIL")
        response = await domain_exception_handler(_mock_request(), exc)
        assert response.status_code == 409


class TestValidationExceptionHandler:
    @pytest.mark.asyncio
    async def test_returns_422(self) -> None:
        raw_errors = [{"loc": ("body", "email"), "msg": "invalid", "type": "value_error"}]
        exc = RequestValidationError(errors=raw_errors)
        response = await validation_exception_handler(_mock_request(), exc)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_error_code(self) -> None:
        raw_errors = [{"loc": ("body", "email"), "msg": "invalid", "type": "value_error"}]
        exc = RequestValidationError(errors=raw_errors)
        response = await validation_exception_handler(_mock_request(), exc)
        body = json.loads(response.body)
        assert body["error"]["code"] == "VALIDATION_ERROR"


class TestUnhandledExceptionHandler:
    @pytest.mark.asyncio
    async def test_returns_500(self) -> None:
        response = await unhandled_exception_handler(
            _mock_request(), RuntimeError("boom")
        )
        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_generic_error_code(self) -> None:
        response = await unhandled_exception_handler(
            _mock_request(), RuntimeError("boom")
        )
        body = json.loads(response.body)
        assert body["error"]["code"] == "INTERNAL_SERVER_ERROR"
