import os
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel, Field
from typing import Dict, Any

from config import Config
from scraper import WebScraper
from search_engine import SearchEngine
from comparison_engine import ComparisonEngine
from tools import save_report_to_file

# =============================================================
# 1. VALIDATION & INITIALIZATION
# =============================================================

# We run validation here so it executes on Render even if 
# the script is imported by a production server
try:
    Config.validate()
    print("✅ Configuration validated successfully")
except ValueError as e:
    print(f"❌ Configuration Error: {e}")
    # On Render, we don't want to exit(1) immediately during build, 
    # but we print the error clearly for the logs.

# Initialize engines
scraper = WebScraper()
search_engine = SearchEngine()
comparison_engine = ComparisonEngine()

# Initialize API
app = FastAPI(title="Lead Discovery & Matching System", version="3.0.0")

# =============================================================
# 2. MIDDLEWARE
# =============================================================

app.add_middleware(SessionMiddleware, secret_key=Config.SECRET_KEY)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allows your frontend to connect from anywhere
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static & Templates
os.makedirs('static', exist_ok=True)
os.makedirs('templates', exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# =============================================================
# 3. MODELS
# =============================================================

class SetLeadRequest(BaseModel):
    name: str = Field(description="Name of the lead company")

class SelectUrlRequest(BaseModel):
    url: str = Field(description="The URL to be scraped")

class CompareRequest(BaseModel):
    user_company: Dict[str, Any]
    lead_company: Dict[str, Any]

# =============================================================
# 4. ROUTES
# =============================-================================

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/health")
async def health_check():
    """Used by Render to verify the app is alive"""
    return {"status": "healthy", "config_valid": True}

# PHASE 2: Search
@app.post("/api/phase2/search")
async def phase2_search(request: SetLeadRequest):
    try:
        search_results = await search_engine.find_company_url(
            company_name=request.name,
            max_results=5
        )
        return {
            'status': 'success',
            'data': {'lead_name': request.name, 'results': search_results}
        }
    except Exception as e:
        print(f"❌ Phase 2 Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# PHASE 4: Scrape
@app.post("/api/phase4/scrape")
async def phase4_scrape_lead(request: SelectUrlRequest):
    try:
        print(f"🔍 PHASE 4: Analyzing {request.url}")
        lead_data = await scraper.scrape_company(request.url)
        
        if not lead_data or lead_data.get('error'):
             # If the scraper returns an error dict, we pass that message to frontend
             error_msg = lead_data.get('message', 'Failed to scrape')
             raise HTTPException(status_code=400, detail=error_msg)
        
        return {'status': 'success', 'data': lead_data}
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"❌ Phase 4 Error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

# PHASE 5: Compare
@app.post("/api/phase5/compare")
async def phase5_compare(data: CompareRequest):
    try:
        report = await comparison_engine.compare_companies(
            user_company=data.user_company,
            lead_company=data.lead_company
        )
        report_path = save_report_to_file(report)
        report['saved_to'] = report_path
        return {'status': 'success', 'data': report}
    except Exception as e:
        print(f"❌ Phase 5 Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================
# 5. STARTUP LOGIC
# =============================================================

if __name__ == "__main__":
    # RENDER DYNAMIC PORT HANDLING
    # Render provides the port in an environment variable named 'PORT'
    # We default to Config.PORT (5001) only if running locally
    port = int(os.environ.get("PORT", Config.PORT))
    
    print(f"🚀 Starting Server on port {port}")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=Config.DEBUG)
