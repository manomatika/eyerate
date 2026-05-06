import logging
import os
from sqlalchemy.orm import Session
from fastapi.staticfiles import StaticFiles
from matika.core.applug import BaseAppLug
from matika.database import get_system_setting
from .routes import router as eyerate_router
from .models import Base as EyeRateBase

logger = logging.getLogger(f"[PLUGIN:eyerate]")

def get_financial_security_endpoint(db: Session):
    from .endpoints import YahooScraperEndpoint, FinnhubEndpoint, AlphaVantageEndpoint
    endpoint_type = get_system_setting(db, "financial_security_data_endpoint", "yahoo")
    api_key = get_system_setting(db, "financial_security_data_api_key", "")
    
    if endpoint_type == "finnhub":
        return FinnhubEndpoint(api_key=api_key)
    elif endpoint_type == "alphavantage":
        return AlphaVantageEndpoint(api_key=api_key)
    else:
        return YahooScraperEndpoint()

class EyeRatePlugin(BaseAppLug):
    """
    EyeRate Implementation as a Reference AppLug.
    """
    
    def on_load(self, db: Session):
        logger.info("EyeRate Plugin Loading...")
        
        # 1. Handle Schema Migration
        EyeRateBase.metadata.create_all(bind=db.get_bind())
        
        # 2. Register Routes with prefix
        self.router.include_router(eyerate_router, prefix="/eyerate")
        
        # 3. Handle Static Assets
        # Mounts at /eyerate/static (not /static/eyerate) to avoid Starlette route
        # ordering conflict: matika mounts a broad /static catch-all before plugins
        # load, so /static/eyerate/... requests never reach a plugin-added mount.
        # /eyerate/static sits outside matika's /static catch-all and resolves cleanly.
        static_dir = os.path.join(os.path.dirname(__file__), "static")
        if os.path.exists(static_dir) and self.app:
            self.app.mount("/eyerate/static", StaticFiles(directory=static_dir), name="eyerate_static")

        # 4. Integrate Templates
        if self.templates:
            from jinja2 import FileSystemLoader
            plugin_template_dir = os.path.join(os.path.dirname(__file__), "templates")
            if isinstance(self.templates.env.loader, FileSystemLoader):
                if plugin_template_dir not in self.templates.env.loader.searchpath:
                    self.templates.env.loader.searchpath.append(plugin_template_dir)

        logger.info("EyeRate Plugin Loaded Successfully.")

    def on_unload(self, db: Session):
        logger.info("EyeRate Plugin Unloading...")
