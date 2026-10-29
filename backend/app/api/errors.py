"""Single mapping from errors to HTTP responses, so routes contain no try/except.

Every error response has the same shape, `{"detail": "..."}`:
  * domain errors map to a specific status (404, 413, 422, 502, 503);
  * anything unexpected becomes a 500 with a short reference id. The full traceback is
    logged under that id; the client sees no internals (paths, SQL, stack frames).
"""

import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.domain.errors import (
    InvalidInputError,
    NotFoundError,
    OmniCareError,
    PayloadTooLargeError,
    ServiceUnavailableError,
    UpstreamServiceError,
)

logger = logging.getLogger(__name__)

# Most specific first: PayloadTooLargeError is also an InvalidInputError.
_STATUS_BY_ERROR: list[tuple[type[OmniCareError], int]] = [
    (PayloadTooLargeError, 413),
    (InvalidInputError, 422),
    (NotFoundError, 404),
    (ServiceUnavailableError, 503),
    (UpstreamServiceError, 502),
]


def status_for(error: OmniCareError) -> int:
    return next((code for cls, code in _STATUS_BY_ERROR if isinstance(error, cls)), 400)


async def _handle_domain_error(request: Request, exc: OmniCareError) -> JSONResponse:
    return JSONResponse(status_code=status_for(exc), content={"detail": str(exc)})


async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
    reference = uuid.uuid4().hex[:8]
    logger.exception(
        "Unhandled error (ref %s) on %s %s", reference, request.method, request.url.path
    )
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error (ref {reference}). Please try again."},
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(OmniCareError, _handle_domain_error)
    # Registered for Exception, Starlette runs this in its outermost error middleware, so it
    # also covers exceptions raised outside the routers.
    app.add_exception_handler(Exception, _handle_unexpected)
