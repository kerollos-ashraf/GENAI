"""Domain error hierarchy.

Services raise these; the API layer maps each family to one HTTP status in a single place
(`app/api/errors.py`). Business code therefore never imports FastAPI or knows about HTTP.
"""


class OmniCareError(Exception):
    """Base class for all expected, user-facing errors."""


class InvalidInputError(OmniCareError):
    """The request is well-formed but its content can't be accepted (-> 422)."""


class PayloadTooLargeError(InvalidInputError):
    """An uploaded file exceeds the configured limit (-> 413)."""


class NotFoundError(OmniCareError):
    """The requested resource doesn't exist (-> 404)."""


class ServiceUnavailableError(OmniCareError):
    """A dependency isn't configured, e.g. a missing API key (-> 503)."""


class UpstreamServiceError(OmniCareError):
    """A dependency (LLM, speech API) failed while serving the request (-> 502)."""
