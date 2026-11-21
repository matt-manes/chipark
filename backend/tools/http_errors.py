from collections.abc import Mapping

from fastapi import Request
from fastapi.utils import is_body_allowed_for_status_code
from starlette.datastructures import Headers
from starlette.exceptions import HTTPException
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse, Response


class HttpErrorResponses:
    """Build consistent REST error responses."""

    @staticmethod
    def create(
        status_code: int,
        message: str,
        headers: Mapping[str, str] | None = None,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status_code,
            content={
                "detail": [
                    {"type": "http_error", "loc": [], "msg": message, "input": None}
                ]
            },
            headers=headers,
        )

    @staticmethod
    async def handle_http_exception(
        request: Request, exception: Exception
    ) -> Response:
        if not isinstance(exception, HTTPException):
            raise exception
        if not is_body_allowed_for_status_code(exception.status_code):
            return Response(status_code=exception.status_code, headers=exception.headers)
        return HttpErrorResponses.create(
            exception.status_code, str(exception.detail), exception.headers
        )

    @staticmethod
    async def handle_unexpected_exception(
        request: Request, exception: Exception
    ) -> Response:
        return HttpErrorResponses.create(500, "Internal Server Error")


class ApiCORSMiddleware(CORSMiddleware):
    """Return REST error envelopes for rejected CORS preflight requests."""

    def preflight_response(self, request_headers: Headers) -> Response:
        response: Response = super().preflight_response(request_headers)
        if response.status_code < 400:
            return response
        headers: dict[str, str] = {
            key: value
            for key, value in response.headers.items()
            if key.lower() not in ("content-length", "content-type")
        }
        return HttpErrorResponses.create(
            response.status_code, bytes(response.body).decode("utf-8"), headers
        )
