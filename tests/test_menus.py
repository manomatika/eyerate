"""
Tests for the consolidated eyerate_menus.json and /eyerate/admin route.

Exercises the full menu matrix:
  - Application menu: visible to all authenticated users
  - User role hub: contains /eyerate/securities
  - Admin role hub: contains /eyerate/admin (not /eyerate/securities)
  - /eyerate/admin: Admin=FULL, User=NONE
"""
import json
import pytest
from matika.database import init_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def login(client, email: str, password: str):
    client.post("/login", data={"email": email, "password": password}, follow_redirects=False)


def extract_menus_data(html: str) -> dict:
    import re
    m = re.search(
        r'<script type="application/json" id="matika-menus">(.*?)</script>',
        html, re.DOTALL,
    )
    return json.loads(m.group(1)) if m else {}


def selector_item_ids(data: dict) -> list:
    return [e["id"] for e in data.get("selector", []) if e.get("type") == "item"]


def all_hrefs(hub: list) -> list:
    """Recursively collect every href value from a hub's item tree."""
    hrefs = []
    for entry in hub:
        if entry.get("href"):
            hrefs.append(entry["href"])
        for item in entry.get("items", []):
            if item.get("href"):
                hrefs.append(item["href"])
            for sub in item.get("items", []):
                if sub.get("href"):
                    hrefs.append(sub["href"])
    return hrefs


# ---------------------------------------------------------------------------
# eyerate_menus.json schema
# ---------------------------------------------------------------------------

def test_eyerate_menus_json_is_valid():
    """eyerate_menus.json parses correctly and has the expected structure."""
    import os
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    with open(os.path.join(root, "eyerate_menus.json")) as f:
        data = json.load(f)
    assert data["schema_version"] == "1.0"
    menus = data["menus"]
    assert "application" in menus
    assert menus["application"]["id"] == "eyerate-main"
    roles = {r["role"]: r for r in menus.get("roles", [])}
    assert "User" in roles
    assert "Admin" in roles


def test_eyerate_menus_json_user_role_links_securities():
    """User role entry in eyerate_menus.json links to /eyerate/securities."""
    import os
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    with open(os.path.join(root, "eyerate_menus.json")) as f:
        data = json.load(f)
    user_role = next(r for r in data["menus"]["roles"] if r["role"] == "User")
    hrefs = all_hrefs(user_role["items"])
    assert "/eyerate/securities" in hrefs


def test_eyerate_menus_json_admin_role_links_admin():
    """Admin role entry in eyerate_menus.json links to /eyerate/admin."""
    import os
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    with open(os.path.join(root, "eyerate_menus.json")) as f:
        data = json.load(f)
    admin_role = next(r for r in data["menus"]["roles"] if r["role"] == "Admin")
    hrefs = all_hrefs(admin_role["items"])
    assert "/eyerate/admin" in hrefs


# ---------------------------------------------------------------------------
# Application menu — visible to all authenticated users
# ---------------------------------------------------------------------------

def test_eyerate_application_visible_to_admin(client, test_admin, db):
    """Admin users see 'eyerate' in the Applications section of the selector."""
    init_db(db)
    login(client, "admin@example.com", "adminpassword")
    data = extract_menus_data(client.get("/about").text)
    assert "eyerate" in selector_item_ids(data)


def test_eyerate_application_visible_to_user(client, test_user, db):
    """Regular users see 'eyerate' in the Applications section of the selector."""
    init_db(db)
    login(client, "test@example.com", "testpassword")
    data = extract_menus_data(client.get("/about").text)
    assert "eyerate" in selector_item_ids(data)


def test_eyerate_application_hub_contains_securities(client, test_admin, db):
    """The eyerate application hub contains a link to /eyerate/securities."""
    init_db(db)
    login(client, "admin@example.com", "adminpassword")
    data = extract_menus_data(client.get("/about").text)
    eyerate_hub = data["hubs"].get("eyerate", [])
    hrefs = all_hrefs(eyerate_hub)
    assert "/eyerate/securities" in hrefs


# ---------------------------------------------------------------------------
# User role hub
# ---------------------------------------------------------------------------

def test_user_role_hub_exists_for_user(client, test_user, db):
    """A user with User role sees __role_User__ in the selector."""
    init_db(db)
    login(client, "test@example.com", "testpassword")
    data = extract_menus_data(client.get("/about").text)
    assert "__role_User__" in selector_item_ids(data)


def test_user_role_hub_contains_securities(client, test_user, db):
    """__role_User__ hub contains a link to /eyerate/securities."""
    init_db(db)
    login(client, "test@example.com", "testpassword")
    data = extract_menus_data(client.get("/about").text)
    user_hub = data["hubs"].get("__role_User__", [])
    hrefs = all_hrefs(user_hub)
    assert "/eyerate/securities" in hrefs, f"Expected /eyerate/securities in User hub. Hrefs: {hrefs}"


def test_user_role_hub_does_not_contain_admin_page(client, test_user, db):
    """__role_User__ hub must not contain /eyerate/admin."""
    init_db(db)
    login(client, "test@example.com", "testpassword")
    data = extract_menus_data(client.get("/about").text)
    user_hub = data["hubs"].get("__role_User__", [])
    hrefs = all_hrefs(user_hub)
    assert "/eyerate/admin" not in hrefs, f"/eyerate/admin must not appear in User hub"


# ---------------------------------------------------------------------------
# Admin role hub
# ---------------------------------------------------------------------------

def test_admin_role_hub_exists_for_admin(client, test_admin, db):
    """A user with Admin role sees __role_Admin__ in the selector."""
    init_db(db)
    login(client, "admin@example.com", "adminpassword")
    data = extract_menus_data(client.get("/about").text)
    assert "__role_Admin__" in selector_item_ids(data)


def test_admin_role_hub_contains_eyerate_admin(client, test_admin, db):
    """__role_Admin__ hub contains /eyerate/admin from the plugin role menu."""
    init_db(db)
    login(client, "admin@example.com", "adminpassword")
    data = extract_menus_data(client.get("/about").text)
    admin_hub = data["hubs"].get("__role_Admin__", [])
    hrefs = all_hrefs(admin_hub)
    assert "/eyerate/admin" in hrefs, f"Expected /eyerate/admin in Admin hub. Hrefs: {hrefs}"


# ---------------------------------------------------------------------------
# /eyerate/admin route — permission matrix
# ---------------------------------------------------------------------------

def test_admin_can_access_eyerate_admin(client, test_admin, db):
    """Admin role has FULL permission on /eyerate/admin — page renders 200."""
    init_db(db)
    login(client, "admin@example.com", "adminpassword")
    resp = client.get("/eyerate/admin")
    assert resp.status_code == 200
    assert "EyeRate Administration" in resp.text


def test_user_denied_eyerate_admin(client, test_user, db):
    """User role has NONE permission on /eyerate/admin — access is denied."""
    init_db(db)
    login(client, "test@example.com", "testpassword")
    resp = client.get("/eyerate/admin", follow_redirects=True)
    assert resp.status_code == 403


def test_unauthenticated_denied_eyerate_admin(client):
    """Unauthenticated requests to /eyerate/admin are rejected."""
    resp = client.get("/eyerate/admin", follow_redirects=False)
    assert resp.status_code in (401, 403)


def test_eyerate_admin_page_uses_base_template(client, test_admin, db):
    """The /eyerate/admin page extends base.html and includes the menu bar."""
    init_db(db)
    login(client, "admin@example.com", "adminpassword")
    resp = client.get("/eyerate/admin")
    assert resp.status_code == 200
    assert 'id="menu-zone-hub"' in resp.text
