import os
from fastapi import APIRouter, Depends, HTTPException, Request, Form, Header
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from matika.database import get_db, get_system_setting, PageType, PermissionLevel, User
from matika.models import SystemSetting
from matika.core.utils import load_metadata
from matika.security.service import check_page_permission
from matika.auth.dependencies import login_required, validate_csrf

from .models import FinancialSecurity, FinancialSecurityType, AssetClass

router = APIRouter()

@router.get("/securities", response_class=HTMLResponse, tags=[PageType.MAINTENANCE])
async def list_securities(request: Request, user: User = Depends(check_page_permission), db: Session = Depends(get_db)):
    # 't' and 'templates' are provided by framework context_processor for rendering.
    # The maintenance base template renders `title` verbatim as the toolbar heading,
    # so it must be an already-resolved display string. Resolve the i18n key here
    # (eyerate's locale catalogs supply "item_securities") rather than leaking the
    # raw key into the page.
    t = request.app.state.i18n.get_text(request.headers.get("accept-language"))
    return request.app.state.templates.TemplateResponse(request, "admin_securities.html", {
        "title": t.get("item_securities", "item_securities"), "user": user, "securities": db.query(FinancialSecurity).all(),
        "option_sources": {
            "financial_security_types": [e.value for e in FinancialSecurityType],
            "asset_classes": [e.value for e in AssetClass],
        },
        "metadata": load_metadata("securities", FinancialSecurity, metadata_dir=os.path.join(os.path.dirname(__file__), "metadata"))
    })

@router.post("/securities/create", tags=[PageType.MAINTENANCE])
async def create_security(symbol: str = Form(...), name: str = Form(...), financial_security_type: FinancialSecurityType = Form(...), asset_class: Optional[AssetClass] = Form(None), previous_close: Optional[str] = Form(None), open_price: Optional[str] = Form(None), current_price: Optional[str] = Form(None), nav: Optional[str] = Form(None), range_52_week: Optional[str] = Form(None), avg_volume: Optional[str] = Form(None), yield_30_day: Optional[str] = Form(None), yield_7_day: Optional[str] = Form(None), _auth: User = Depends(check_page_permission), _csrf=Depends(validate_csrf), db: Session = Depends(get_db)):
    if db.query(FinancialSecurity).filter(FinancialSecurity.symbol == symbol.upper()).first(): raise HTTPException(status_code=400, detail="already exists")
    db.add(FinancialSecurity(symbol=symbol.upper(), name=name, financial_security_type=financial_security_type, asset_class=asset_class, previous_close=previous_close, open_price=open_price, current_price=current_price, nav=nav, range_52_week=range_52_week, avg_volume=avg_volume, yield_30_day=yield_30_day, yield_7_day=yield_7_day))
    db.commit(); return RedirectResponse(url="/eyerate/securities", status_code=303)

@router.post("/securities/update/{sec_id}")
async def update_security(sec_id: int, symbol: str = Form(...), name: str = Form(...), financial_security_type: FinancialSecurityType = Form(...), asset_class: Optional[AssetClass] = Form(None), previous_close: Optional[str] = Form(None), open_price: Optional[str] = Form(None), current_price: Optional[str] = Form(None), nav: Optional[str] = Form(None), range_52_week: Optional[str] = Form(None), avg_volume: Optional[str] = Form(None), yield_30_day: Optional[str] = Form(None), yield_7_day: Optional[str] = Form(None), _auth: User = Depends(check_page_permission), _csrf=Depends(validate_csrf), db: Session = Depends(get_db)):
    sec = db.query(FinancialSecurity).filter(FinancialSecurity.id == sec_id).first()
    if sec:
        sec.symbol = symbol; sec.name = name; sec.financial_security_type = financial_security_type; sec.asset_class = asset_class
        sec.previous_close = previous_close; sec.open_price = open_price; sec.current_price = current_price
        sec.nav = nav; sec.range_52_week = range_52_week; sec.avg_volume = avg_volume
        sec.yield_30_day = yield_30_day; sec.yield_7_day = yield_7_day; db.commit()
    return RedirectResponse(url="/eyerate/securities", status_code=303)

@router.post("/securities/delete/{sec_id}")
async def delete_security(sec_id: int, _auth: User = Depends(check_page_permission), _csrf=Depends(validate_csrf), db: Session = Depends(get_db)):
    sec = db.query(FinancialSecurity).filter(FinancialSecurity.id == sec_id).first()
    if sec: db.delete(sec); db.commit()
    return RedirectResponse(url="/eyerate/securities", status_code=303)

@router.get("/securities/search")
async def search_securities(q: str, _auth: User = Depends(login_required), db: Session = Depends(get_db)):
    from .plugin import get_financial_security_endpoint
    from .endpoints import ProviderError
    try:
        return await get_financial_security_endpoint(db).search(q)
    except ProviderError as e:
        raise HTTPException(status_code=502, detail=f"lookup failed: {e}")

@router.get("/securities/lookup")
async def lookup_security(symbol: str, _auth: User = Depends(login_required), db: Session = Depends(get_db)):
    from .plugin import get_financial_security_endpoint
    from .endpoints import ProviderError
    try:
        data = await get_financial_security_endpoint(db).lookup(symbol)
    except ProviderError as e:
        raise HTTPException(status_code=502, detail=f"lookup failed: {e}")
    if data is None:
        raise HTTPException(status_code=404, detail="Not found")
    return data

class BulkCreateRequest(BaseModel): symbols: List[str]
@router.post("/securities/bulk_create")
async def bulk_create_securities(request: BulkCreateRequest, _auth: User = Depends(check_page_permission), db: Session = Depends(get_db)):
    from .plugin import get_financial_security_endpoint
    ep = get_financial_security_endpoint(db); added = []; errors = []
    for s in request.symbols:
        s = s.upper().strip()
        if not s: continue
        if db.query(FinancialSecurity).filter(FinancialSecurity.symbol == s).first():
            errors.append(f"{s} already exists")
            continue
        try:
            d = await ep.lookup(s)
            if d:
                db.add(FinancialSecurity(symbol=s, name=d.get("name", s), financial_security_type=d.get("financial_security_type", FinancialSecurityType.STOCK), asset_class=d.get("asset_class"), current_price=d.get("current_price"), previous_close=d.get("previous_close"), open_price=d.get("open_price"), nav=d.get("nav"), range_52_week=d.get("range_52_week"), avg_volume=d.get("avg_volume"), yield_30_day=d.get("yield_30_day"), yield_7_day=d.get("yield_7_day")))
                added.append(s)
            else: errors.append(f"{s} not found")
        except Exception as e: errors.append(f"Error {s}: {e}")
    db.commit(); return {"added": added, "errors": errors}

class BulkDeleteRequest(BaseModel): symbols: List[str]
@router.post("/securities/bulk_delete")
async def bulk_delete_securities(request: BulkDeleteRequest, _auth: User = Depends(check_page_permission), db: Session = Depends(get_db)):
    c = db.query(FinancialSecurity).filter(FinancialSecurity.symbol.in_([s.upper().strip() for s in request.symbols])).delete(synchronize_session=False)
    db.commit(); return {"deleted": c}

@router.get("/admin", response_class=HTMLResponse, tags=[PageType.MAINTENANCE])
async def eyerate_admin(request: Request, user: User = Depends(check_page_permission), db: Session = Depends(get_db)):
    current_endpoint = get_system_setting(db, "financial_security_data_endpoint", "yahoo")
    current_api_key = get_system_setting(db, "financial_security_data_api_key", "")
    return request.app.state.templates.TemplateResponse(request, "eyerate_admin.html", {
        "user": user,
        "current_endpoint": current_endpoint,
        "current_api_key": current_api_key,
    })

@router.post("/admin", tags=[PageType.MAINTENANCE])
async def eyerate_admin_save(
    request: Request,
    endpoint: str = Form(...),
    api_key: Optional[str] = Form(None),
    _auth: User = Depends(check_page_permission),
    _csrf=Depends(validate_csrf),
    db: Session = Depends(get_db),
):
    for name, value in [
        ("financial_security_data_endpoint", endpoint),
        ("financial_security_data_api_key", api_key or ""),
    ]:
        setting = db.query(SystemSetting).filter(SystemSetting.name == name).first()
        if setting:
            setting.value = value
        else:
            db.add(SystemSetting(name=name, value=value, is_system=True))
    db.commit()
    return RedirectResponse(url="/eyerate/admin", status_code=303)


@router.post("/securities/test_endpoint", tags=[PageType.SETTINGS])
async def test_security_endpoint(endpoint: str = Form(...), api_key: Optional[str] = Form(None), _auth: User = Depends(login_required)):
    from .endpoints import YahooScraperEndpoint, FinnhubEndpoint, AlphaVantageEndpoint
    try:
        if endpoint == "finnhub": ep = FinnhubEndpoint(api_key=api_key or "")
        elif endpoint == "alphavantage": ep = AlphaVantageEndpoint(api_key=api_key or "")
        else: ep = YahooScraperEndpoint()
        d = await ep.lookup("VOO")
        return {"success": True} if d and d.get("symbol") == "VOO" else {"success": False, "error": "No data"}
    except Exception as e: return {"success": False, "error": str(e)}
