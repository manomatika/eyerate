"""eyerate's error-code package (Model A). See ``error-codes.yaml`` for the registry."""

from .error_codes import ALL_CODES, CODE_METADATA, COMPONENT, SUPPORTED_LOCALES
from .errors import resolve
from .manomatika_error import CODE_PATTERN, CODE_RE, ManoMatikaError, parse_code

__all__ = [
    "ALL_CODES",
    "CODE_METADATA",
    "COMPONENT",
    "SUPPORTED_LOCALES",
    "ManoMatikaError",
    "CODE_PATTERN",
    "CODE_RE",
    "parse_code",
    "resolve",
]
