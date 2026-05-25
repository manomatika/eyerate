"""
End-to-end field-name contract for the securities maintenance page.

These tests guard the cross-layer seam that drifted in manomatika/eyerate#21:
metadata field name ↔ rendered HTML name attr ↔ route Form param ↔ model attr.
When any one of those four diverges, the entire create flow breaks (empty
dropdown / 422 on save / silent un-set on lookup) — and unit tests covering
only one layer never see it. A round-trip test is the only way to catch it.
"""
import os

import pytest
from eyerate.models import (
    FinancialSecurity as Security,
    FinancialSecurityType,
    AssetClass,
)
from matika.database import init_db


METADATA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "src", "eyerate",
    "metadata", "securities_maint_activity_metadata.json",
)


def _login_admin(client, test_admin):
    client.post(
        "/login",
        data={"email": test_admin.email, "password": "adminpassword"},
        follow_redirects=False,
    )


def _securities_metadata():
    import json
    with open(METADATA_PATH) as f:
        return json.load(f)


def _select_field_meta(metadata, name):
    for f in metadata["maintenance_panel"]["fields"]:
        if f["name"] == name:
            return f
    raise AssertionError(f"field {name!r} not in metadata")


def test_dropdown_contains_every_enum_value(client, test_admin, db):
    """GET /eyerate/securities renders a <select id="field-financial_security_type">
    containing all five FinancialSecurityType enum values. If the metadata
    field-name and the option-source-keyed list ever drift, the rendered
    HTML loses options and this test fails immediately."""
    init_db(db)
    _login_admin(client, test_admin)

    resp = client.get("/eyerate/securities")
    assert resp.status_code == 200

    # The select must exist under the metadata-declared field name.
    assert 'id="field-financial_security_type"' in resp.text, (
        "<select id='field-financial_security_type'> not rendered — metadata "
        "field name does not match what the template emits."
    )

    # Every enum value must appear as an <option>.
    for member in FinancialSecurityType:
        needle = f'<option value="{member.value}">{member.value}</option>'
        assert needle in resp.text, (
            f"Expected option for {member.name} ({member.value!r}) not "
            f"rendered in dropdown — option_sources['financial_security_types'] "
            f"is missing or the template branch failed to match."
        )


def test_create_persists_with_metadata_declared_field_name(client, test_admin, db):
    """Posting the create form using the metadata-declared field name must
    succeed (2xx) and persist to the model attribute of the same name.

    This is the exact seam that broke in manomatika/eyerate#21: the metadata
    said financial_security_type but the route Form param said security_type,
    so even a fully-populated form 422'd. We POST using the metadata-declared
    name and verify the model attr afterwards — if any layer drifts, this
    fails."""
    init_db(db)
    _login_admin(client, test_admin)

    metadata = _securities_metadata()
    type_field = _select_field_meta(metadata, "financial_security_type")
    field_name = type_field["name"]
    assert field_name == "financial_security_type", (
        "Metadata field name changed; update this test and confirm route + "
        "model attr move with it."
    )

    payload = {
        "symbol": "VOO",
        "name": "Vanguard S&P 500 ETF",
        field_name: FinancialSecurityType.ETF.value,
        "asset_class": AssetClass.LARGE_CAP_STOCK.value,
        "current_price": "450.00",
    }
    resp = client.post(
        "/eyerate/securities/create", data=payload, follow_redirects=False
    )
    assert resp.status_code == 303, (
        f"Create returned {resp.status_code}; body: {resp.text!r}. The "
        f"metadata-declared field name {field_name!r} did not match the "
        f"route's Form parameter — the cross-layer contract drifted."
    )

    sec = db.query(Security).filter(Security.symbol == "VOO").first()
    assert sec is not None
    # The model attribute name must equal the metadata-declared field name.
    assert hasattr(sec, field_name), (
        f"Model is missing attribute {field_name!r}; metadata declares a "
        f"field name that doesn't exist on the model."
    )
    assert getattr(sec, field_name) == FinancialSecurityType.ETF


def test_manual_override_through_dropdown(client, test_admin, db):
    """The user must be able to override Yahoo's lookup-derived type by
    submitting a different value from the dropdown. Verifies the value
    submitted by the form is what actually persists."""
    init_db(db)
    _login_admin(client, test_admin)

    # Yahoo would classify VOO as ETF; user overrides to MUTUAL_FUND.
    resp = client.post(
        "/eyerate/securities/create",
        data={
            "symbol": "VOO",
            "name": "Vanguard S&P 500 ETF",
            "financial_security_type": FinancialSecurityType.MUTUAL_FUND.value,
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303

    sec = db.query(Security).filter(Security.symbol == "VOO").first()
    assert sec is not None
    assert sec.financial_security_type == FinancialSecurityType.MUTUAL_FUND


def test_metadata_field_name_matches_model_column(db):
    """Static contract: every metadata field whose name is a SQLAlchemy
    column must resolve via getattr — the row template uses
    getattr(s, field.name) to render data-* attributes."""
    metadata = _securities_metadata()
    sec = Security(
        symbol="X",
        name="X Co.",
        financial_security_type=FinancialSecurityType.STOCK,
    )
    for f in metadata["maintenance_panel"]["fields"]:
        # The row template depends on this resolving without AttributeError;
        # __dict__-only check would miss SQLAlchemy column descriptors.
        getattr(sec, f["name"])
