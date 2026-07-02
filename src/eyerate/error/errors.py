"""
errors.py — eyerate's error-code i18n resolver.

Resolves an eyerate error ``code`` (one of :mod:`eyerate.error.error_codes`
``ALL_CODES``) to its localized display string, per Model A (see
manomatika-v0.0.1-plan.md §2): the code is simultaneously the machine carrier and
the i18n catalog key. The catalog lives in the SAME locale files eyerate already
ships (``src/eyerate/locales/<lang>.json``), nested under a top-level ``errors``
object keyed by code (Q12 — nested catalog).

This is eyerate's OWN resolver — it reads eyerate's locale catalogs directly
rather than routing through matika's request-scoped ``I18nService``. That service
merges a plugin's catalog over matika-core's with a shallow, top-level
``dict.update`` (see ``matika/i18n.py`` ``load_language``), so a plugin's
top-level ``errors`` key would wholesale clobber matika-core's own ``errors`` key
rather than merge per-code. Error-code resolution is a data lookup, not
page-render i18n, so it deliberately does not go through that merge (rule 18: one
canonical *page-i18n* path — ``I18nService`` — is reused for page text; this is a
distinct concern with its own canonical, self-contained implementation, mirroring
how ``manomatika_error.py`` itself is self-contained per origin).

Fail-loud discipline (rule 18): resolving a code that is not in ``ALL_CODES``
raises immediately, naming the offending code. A locale missing from
``SUPPORTED_LOCALES`` falls back to English exactly like matika's own
``I18nService.get_text``.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Dict

from .error_codes import ALL_CODES, SUPPORTED_LOCALES

_LOCALES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "locales")
_FALLBACK_LOCALE = "en"


@lru_cache(maxsize=None)
def _load_errors_catalog(lang: str) -> Dict[str, str]:
    """Load the ``errors`` object from ``locales/<lang>.json``. Empty if absent."""
    path = os.path.join(_LOCALES_DIR, f"{lang}.json")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        return {}
    errors = data.get("errors", {})
    if not isinstance(errors, dict):
        raise ValueError(
            f"{path}: top-level 'errors' must be an object of code -> message, "
            f"got {type(errors).__name__}"
        )
    return errors


def _normalize_lang(lang: str) -> str:
    """Extract the primary language code from a raw ``Accept-Language`` value.

    Mirrors ``I18nService.get_text``'s normalization (``matika/i18n.py``) — e.g.
    ``"es-MX,es;q=0.9"`` -> ``"es"`` — so callers can pass the raw request header
    straight through, exactly as they do to the page-i18n service.
    """
    if not lang:
        return _FALLBACK_LOCALE
    return lang.split(",")[0].split("-")[0].strip().lower()


def resolve(code: str, lang: str = "en") -> str:
    """Resolve *code* to its localized display string for *lang*.

    *lang* may be a raw ``Accept-Language`` header value or a bare locale code;
    both are normalized identically to ``I18nService.get_text``. Raises
    ``ValueError`` — naming *code* — if it is not a declared eyerate error code
    (fail loud: an unregistered code is never silently stringified). Falls back to
    English when *lang* is unsupported or the catalog entry is missing for *lang*,
    matching ``I18nService.get_text`` fallback semantics. Raises ``ValueError`` if
    a declared code has no catalog entry in either *lang* or the English
    fallback — every declared code must resolve in every supported locale.
    """
    if code not in ALL_CODES:
        raise ValueError(
            f"unknown eyerate error code {code!r}; not declared in "
            f"src/eyerate/error/error-codes.yaml (see ALL_CODES)"
        )

    normalized = _normalize_lang(lang)
    resolved_lang = normalized if normalized in SUPPORTED_LOCALES else _FALLBACK_LOCALE
    catalog = _load_errors_catalog(resolved_lang)
    if code in catalog:
        return catalog[code]

    if resolved_lang != _FALLBACK_LOCALE:
        fallback_catalog = _load_errors_catalog(_FALLBACK_LOCALE)
        if code in fallback_catalog:
            return fallback_catalog[code]

    raise ValueError(
        f"eyerate error code {code!r} is declared in error-codes.yaml but has no "
        f"catalog entry in locales/{resolved_lang}.json or the "
        f"{_FALLBACK_LOCALE!r} fallback — every declared code must have an "
        "errors.<CODE> entry in every supported locale"
    )
