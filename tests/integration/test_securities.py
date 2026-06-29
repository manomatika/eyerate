import json
import os
import pytest
from eyerate.models import FinancialSecurity as Security, FinancialSecurityType as SecurityType, AssetClass
from matika.database import init_db

def test_securities_list_basic(client, test_admin, db):
    init_db(db)
    # Log in as admin
    client.post("/login", data={"email": test_admin.email, "password": "adminpassword"}, follow_redirects=False)
    
    # Manually add a security to ensure it's in the DB session used by the route
    new_sec = Security(
        symbol="TEST", 
        name="Test Security", 
        financial_security_type=SecurityType.STOCK,
        asset_class=AssetClass.LARGE_CAP_STOCK
    )
    db.add(new_sec)
    db.commit()

    # List
    resp = client.get("/eyerate/securities")
    assert resp.status_code == 200
    assert "TEST" in resp.text
    assert "Test Security" in resp.text
    assert AssetClass.LARGE_CAP_STOCK.value in resp.text

def test_maintenance_layout_elements(client, test_admin, db):
    init_db(db)
    client.post("/login", data={"email": test_admin.email, "password": "adminpassword"}, follow_redirects=False)
    
    resp = client.get("/eyerate/securities")
    assert resp.status_code == 200
    assert 'class="browse-panel"' in resp.text
    assert 'class="maintenance-panel"' in resp.text
    assert 'class="advanced-search-panel"' in resp.text
    assert 'class="button-bar-panel"' in resp.text
    assert 'class="maintenance-form"' in resp.text
    assert 'class="save-panel"' in resp.text

def test_securities_crud(client, test_admin, db):
    init_db(db)
    # Log in as admin
    client.post("/login", data={"email": test_admin.email, "password": "adminpassword"}, follow_redirects=False)
    
    # 1. Create
    resp = client.post("/eyerate/securities/create", data={
        "symbol": "VOO",
        "name": "Vanguard S&P 500 ETF",
        "financial_security_type": SecurityType.ETF.value,
        "asset_class": AssetClass.LARGE_CAP_STOCK.value,
        "current_price": "450.00"
    }, follow_redirects=False)
    assert resp.status_code == 303
    
    sec = db.query(Security).filter(Security.symbol == "VOO").first()
    assert sec is not None
    assert sec.asset_class == AssetClass.LARGE_CAP_STOCK

    # 2. Update
    resp = client.post(f"/eyerate/securities/update/{sec.id}", data={
        "symbol": "VOO",
        "name": "Vanguard S&P 500 ETF Updated",
        "financial_security_type": SecurityType.ETF.value,
        "asset_class": AssetClass.SMALL_CAP_STOCK.value,
        "current_price": "460.00"
    }, follow_redirects=False)
    assert resp.status_code == 303
    db.refresh(sec)
    assert sec.asset_class == AssetClass.SMALL_CAP_STOCK

    # 3. Delete
    resp = client.post(f"/eyerate/securities/delete/{sec.id}", follow_redirects=False)
    assert resp.status_code == 303
    deleted_sec = db.query(Security).filter(Security.id == sec.id).first()
    assert deleted_sec is None

def test_securities_toolbar_title_is_translated_not_raw_key(client, test_admin, db):
    """Regression (manomatika/eyerate#73): the Securities toolbar heading must
    render the SEEDED translated value for `item_securities`, never the raw i18n
    key. The route previously passed the raw key as `title`, which the maintenance
    base template renders verbatim into `<h2 id="activity-title">`."""
    init_db(db)
    client.post("/login", data={"email": test_admin.email, "password": "adminpassword"}, follow_redirects=False)

    # The expected display value is the seeded translation, read from eyerate's
    # own locale catalog (the source the i18n service merges into `t`).
    locale_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "src", "eyerate", "locales", "en.json",
    )
    with open(locale_path, encoding="utf-8") as f:
        expected_title = json.load(f)["item_securities"]
    assert expected_title and expected_title != "item_securities"

    resp = client.get("/eyerate/securities")
    assert resp.status_code == 200
    # Toolbar heading shows the translated value...
    assert f'<h2 id="activity-title">{expected_title}</h2>' in resp.text
    # ...and never the raw i18n key.
    assert '<h2 id="activity-title">item_securities</h2>' not in resp.text
    assert "item_securities" not in resp.text


def test_user_can_access_securities(client, test_user, db):
    init_db(db)
    client.post("/login", data={"email": test_user.email, "password": "testpassword"}, follow_redirects=False)

    # User role has FULL access to /eyerate/securities — this is a user-facing page
    resp = client.get("/eyerate/securities")
    assert resp.status_code == 200
