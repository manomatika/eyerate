"""
Tests for eyerate's error-code framework (manomatika/eyerate#77, R4):
  - src/eyerate/error/error-codes.yaml + generated error_codes.py constants
  - src/eyerate/error/errors.py resolver
  - en/es errors.<CODE> catalog parity (src/eyerate/locales/*.json)
  - applug.json 'supported_locales' required field

Self-contained: none of these imports need the matika sibling stack (the error
package is deliberately stdlib-only), so this file runs identically whether or
not ../matika is present.
"""
import json
from pathlib import Path

import pytest

from eyerate.error import ALL_CODES, CODE_METADATA, SUPPORTED_LOCALES, resolve
from eyerate.error.manomatika_error import CODE_RE

_REPO_ROOT = Path(__file__).parent.parent
_LOCALES_DIR = _REPO_ROOT / "src" / "eyerate" / "locales"

# The registry's English source text (manually kept in lockstep with
# src/eyerate/error/error-codes.yaml `message` fields and
# src/eyerate/locales/en.json `errors.<CODE>` entries — R3a's matika pattern
# generates the en catalog FROM the registry; eyerate mirrors that intent by
# asserting the three stay identical rather than re-deriving at runtime, since
# eyerate does not carry a yaml dependency at runtime).
_EXPECTED_EN_MESSAGES = {
    "EYERATE-PROV-001": "Provider requires an API key that is not configured",
    "EYERATE-PROV-002": "Provider request was rate limited",
    "EYERATE-PROV-003": "Provider returned an HTTP error",
    "EYERATE-PROV-004": "Provider call failed unexpectedly",
    "EYERATE-API-001": "Security search failed because the provider call did not complete",
    "EYERATE-API-002": "Security lookup failed because the provider call did not complete",
    "EYERATE-API-003": "Security was not found",
    "EYERATE-API-004": "Security already exists",
    "EYERATE-API-005": "Provider connectivity test failed",
}


def test_registry_declares_nine_codes():
    assert len(ALL_CODES) == 9
    assert ALL_CODES == set(_EXPECTED_EN_MESSAGES)


def test_every_code_is_well_formed_eyerate():
    for code in ALL_CODES:
        assert CODE_RE.match(code), f"{code!r} is not a well-formed error code"
        assert code.startswith("EYERATE-"), f"{code!r} does not carry the EYERATE component prefix"


def test_facilities_are_contiguous_from_one():
    by_facility = {}
    for code in ALL_CODES:
        _, facility, number = code.split("-")
        by_facility.setdefault(facility, []).append(int(number))
    for facility, numbers in by_facility.items():
        assert sorted(numbers) == list(range(1, len(numbers) + 1)), (
            f"facility {facility!r} is not contiguous from 001: {sorted(numbers)}"
        )


def test_code_metadata_covers_every_code():
    assert set(CODE_METADATA) == ALL_CODES
    for code, meta in CODE_METADATA.items():
        assert meta["severity"] in {"fatal", "error", "warning"}
        assert meta["log_route"] in {"startup", "aggregate", "n/a"}


def test_supported_locales_is_en_and_es():
    assert SUPPORTED_LOCALES == ["en", "es"]


# ---------------------------------------------------------------------------
# Resolver (src/eyerate/error/errors.py)
# ---------------------------------------------------------------------------

def test_resolve_unknown_code_fails_loud():
    with pytest.raises(ValueError, match="unknown eyerate error code"):
        resolve("EYERATE-BOGUS-999", "en")


def test_resolve_en_matches_registry_message_for_every_code():
    for code, expected in _EXPECTED_EN_MESSAGES.items():
        assert resolve(code, "en") == expected


def test_resolve_es_returns_non_empty_translation_for_every_code():
    for code in ALL_CODES:
        es_text = resolve(code, "es")
        assert es_text, f"{code!r} has no Spanish translation"
        # Spanish text must not just be the raw English fallback leaking through.
        assert es_text != _EXPECTED_EN_MESSAGES[code], (
            f"{code!r} resolves to the English string under 'es' — es.json is "
            "missing a real translation"
        )


def test_resolve_falls_back_to_english_for_unsupported_locale():
    code = next(iter(ALL_CODES))
    assert resolve(code, "fr") == resolve(code, "en")


def test_resolve_normalizes_raw_accept_language_header():
    code = next(iter(ALL_CODES))
    assert resolve(code, "es-MX,es;q=0.9,en;q=0.8") == resolve(code, "es")


# ---------------------------------------------------------------------------
# en/es catalog parity — R2 (Q12): every declared code resolves in BOTH
# shipped locales, and neither catalog carries stray/undeclared codes.
# ---------------------------------------------------------------------------

def _load_errors_catalog(lang: str) -> dict:
    with open(_LOCALES_DIR / f"{lang}.json", "r", encoding="utf-8") as fh:
        return json.load(fh)["errors"]


def test_en_and_es_errors_catalogs_cover_every_declared_code_exactly():
    en_errors = _load_errors_catalog("en")
    es_errors = _load_errors_catalog("es")
    assert set(en_errors) == ALL_CODES, (
        f"en.json errors keys != declared codes: "
        f"missing={ALL_CODES - set(en_errors)} extra={set(en_errors) - ALL_CODES}"
    )
    assert set(es_errors) == ALL_CODES, (
        f"es.json errors keys != declared codes: "
        f"missing={ALL_CODES - set(es_errors)} extra={set(es_errors) - ALL_CODES}"
    )


def test_en_catalog_text_equals_registry_message():
    en_errors = _load_errors_catalog("en")
    assert en_errors == _EXPECTED_EN_MESSAGES


# ---------------------------------------------------------------------------
# applug.json — 'supported_locales' is now a REQUIRED field.
# ---------------------------------------------------------------------------

def test_applug_json_declares_supported_locales():
    with open(_REPO_ROOT / "applug.json", "r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    assert "supported_locales" in manifest, (
        "applug.json is missing the required 'supported_locales' field"
    )
    assert manifest["supported_locales"] == ["en", "es"]


def test_applug_json_supported_locales_matches_shipped_catalogs():
    with open(_REPO_ROOT / "applug.json", "r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    shipped = sorted(p.stem for p in _LOCALES_DIR.glob("*.json"))
    assert sorted(manifest["supported_locales"]) == shipped
