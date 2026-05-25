import pytest
from eyerate.models import FinancialSecurity as Security, FinancialSecurityType as SecurityType
from matika.database import init_db

def test_duplicate_symbol_prevention(client, test_admin, db):
    init_db(db)
    # Log in as admin
    client.post("/login", data={"email": test_admin.email, "password": "adminpassword"}, follow_redirects=False)
    
    # Create a security
    data = {
        "symbol": "VOO",
        "name": "Vanguard S&P 500 ETF",
        "financial_security_type": SecurityType.ETF.value
    }
    resp = client.post("/eyerate/securities/create", data=data, follow_redirects=True)
    assert resp.status_code == 200
    
    # Try to create the same symbol again
    resp = client.post("/eyerate/securities/create", data=data, follow_redirects=False)
    assert resp.status_code == 400
    assert "already exists" in resp.text

def test_symbol_case_insensitivity(client, test_admin, db):
    init_db(db)
    client.post("/login", data={"email": test_admin.email, "password": "adminpassword"}, follow_redirects=False)
    
    # Create initial
    client.post("/eyerate/securities/create", data={
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "financial_security_type": SecurityType.STOCK.value
    })

    # Try lowercase version
    resp = client.post("/eyerate/securities/create", data={
        "symbol": "aapl",
        "name": "Apple Inc. Duplicate",
        "financial_security_type": SecurityType.STOCK.value
    })
    assert resp.status_code == 400
