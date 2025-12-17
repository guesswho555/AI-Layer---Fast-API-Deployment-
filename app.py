import os
import uvicorn
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from config import Config
from scraper import WebScraper
from search_engine import SearchEngine
from comparison_engine import ComparisonEngine
from tools import (
    save_report_to_file,
    add_company_to_store,
    clean_url
)

# Initialize engines
scraper = WebScraper()
search_engine = SearchEngine()
comparison_engine = ComparisonEngine()

# Initialize API
app = FastAPI(title="Lead Discovery & Matching System", version="3.0.0")

# Add Session Middleware (FastAPI doesn't have built-in session like Flask)
app.add_middleware(SessionMiddleware, secret_key=Config.SECRET_KEY)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Files
os.makedirs('static', exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
os.makedirs('templates', exist_ok=True)
templates = Jinja2Templates(directory="templates")


# =============================================================================
# MODELS
# =============================================================================

class SetLeadRequest(BaseModel):
    name: str = Field(description="Name of the lead/target company")

class SelectUrlRequest(BaseModel):
    url: str

class CompareRequest(BaseModel):
    user_company: Dict[str, Any] = Field(description="User's complete company data")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_session(request: Request) -> Dict[str, Any]:
    return request.session

def get_current_phase(request: Request) -> int:
    return request.session.get('current_phase', 1)

def set_phase(request: Request, phase: int):
    request.session['current_phase'] = phase

def get_session_data(request: Request) -> Dict[str, Any]:
    return {
        'current_phase': request.session.get('current_phase', 1),
        'lead_name': request.session.get('lead_name'),
        'search_results': request.session.get('search_results'),
        'selected_url': request.session.get('selected_url'),
        'lead_company': request.session.get('lead_company'),  # Was target_company
        'comparison_report': request.session.get('comparison_report')
    }


# =============================================================================
# ROUTES
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main HTML page."""
    # Reset session for fresh start
    request.session.clear()
    set_phase(request, 1)
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/status")
async def get_status(request: Request):
    """Get current application status and phase."""
    return {
        'status': 'success',
        'phase': get_current_phase(request),
        'data': get_session_data(request)
    }


# =============================================================================
# PHASE 1: Set Lead Name
# =============================================================================

@app.post("/api/phase1/set-lead")
async def phase1_set_lead(data: SetLeadRequest, request: Request):
    """
    PHASE 1: Receive Lead Company Name
    """
    try:
        print(f"\n{'='*50}")
        print(f"PHASE 1: Set Lead Name")
        print(f"Name: {data.name}")
        print(f"{'='*50}")
        
        request.session['lead_name'] = data.name
        
        # Move to Phase 2
        set_phase(request, 2)
        
        return {
            'status': 'success',
            'phase': 2,
            'message': f"Lead '{data.name}' set. Ready to find URL.",
            'data': {'lead_name': data.name}
        }
        
    except Exception as e:
        print(f"Phase 1 Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# PHASE 2: Find Lead URL
# =============================================================================

@app.post("/api/phase2/search")
async def phase2_search(request: Request):
    """
    PHASE 2: Search for Lead Company URL
    """
    if get_current_phase(request) < 2:
        raise HTTPException(status_code=400, detail="Please complete Phase 1 first")
    
    lead_name = request.session.get('lead_name')
    if not lead_name:
        raise HTTPException(status_code=400, detail="No lead name found in session")
    
    try:
        print(f"\n{'='*50}")
        print(f"PHASE 2: Finding URL for {lead_name}")
        print(f"{'='*50}")
        
        # Use updated search engine method
        search_results = await search_engine.find_company_url(
            company_name=lead_name,
            max_results=5
        )
        
        # Store in session
        request.session['search_results'] = search_results
        
        # Move to Phase 3
        set_phase(request, 3)
        
        return {
            'status': 'success',
            'phase': 3,
            'message': f'Found {len(search_results)} potential URLs for {lead_name}',
            'data': {
                'lead_name': lead_name,
                'results': search_results
            }
        }
        
    except Exception as e:
        print(f"Phase 2 Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# PHASE 3: Select Lead URL
# =============================================================================

@app.post("/api/phase3/select")
async def phase3_select_url(data: SelectUrlRequest, request: Request):
    """
    PHASE 3: User selects the correct URL for the Lead
    """
    if get_current_phase(request) < 3:
        raise HTTPException(status_code=400, detail="Please complete Phase 2 first")
    
    try:
        print(f"\n{'='*50}")
        print(f"PHASE 3: URL Selected")
        print(f"Selected: {data.url}")
        print(f"{'='*50}")
        
        # Store selection
        request.session['selected_url'] = data.url
        
        # Move to Phase 4
        set_phase(request, 4)
        
        return {
            'status': 'success',
            'phase': 4,
            'message': 'URL selected. Ready to analyze Lead Company.',
            'data': {
                'selected_url': data.url
            }
        }
        
    except Exception as e:
        print(f"Phase 3 Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# PHASE 4: Scrape Lead Company
# =============================================================================

@app.post("/api/phase4/scrape")
async def phase4_scrape_lead(request: Request):
    """
    PHASE 4: Scrape the selected Lead Company URL to understand them.
    (Description, Services, Roles, Goals, etc.)
    """
    if get_current_phase(request) < 4:
        raise HTTPException(status_code=400, detail="Please complete Phase 3 first")
    
    selected_url = request.session.get('selected_url')
    
    if not selected_url:
        raise HTTPException(status_code=400, detail="No URL selected")
    
    try:
        print(f"\n{'='*50}")
        print(f"PHASE 4: Analyzing Lead Company")
        print(f"URL: {selected_url}")
        print(f"{'='*50}")
        
        # Scrape lead company
        lead_data = await scraper.scrape_company(selected_url)
        
        if not lead_data or lead_data.get('error'):
             raise HTTPException(status_code=400, detail=lead_data.get('message', 'Failed to scrape lead company'))

        
        # Store in session
        request.session['lead_company'] = lead_data
        
        # Move to Phase 5 (ready for comparison)
        set_phase(request, 5)
        
        return {
            'status': 'success',
            'phase': 5,
            'message': 'Lead company analyzed successfully. Ready for comparison.',
            'data': lead_data
        }
        
    except Exception as e:
        print(f"Phase 4 Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# PHASE 5: User Data & Comparison
# =============================================================================

@app.post("/api/phase5/compare")
async def phase5_compare(data: CompareRequest, request: Request):
    """
    PHASE 5: Receive User Company Data and Compare with Lead Company
    """
    print(f"DEBUG: Current Phase: {get_current_phase(request)}")
    print(f"DEBUG: Lead Company in Session: {request.session.get('lead_company') is not None}")
    
    if get_current_phase(request) < 5:
        print(f"DEBUG: Phase check failed. Current: {get_current_phase(request)}")
        raise HTTPException(status_code=400, detail="Please complete Phase 4 first")
    
    lead_company = request.session.get('lead_company')
    user_company = data.user_company
    
    if not lead_company:
        print("DEBUG: Lead company missing in session")
        raise HTTPException(status_code=400, detail="Missing lead company data")
    
    try:
        print(f"\n{'='*50}")
        print(f"PHASE 5: Generating Business Match Report")
        print(f"User: {user_company.get('name')}")
        print(f"Lead: {lead_company.get('name')}")
        print(f"{'='*50}")
        
        # Generate comparison
        report = await comparison_engine.compare_companies(
            user_company=user_company,
            lead_company=lead_company
        )
        
        # Store in session
        request.session['comparison_report'] = report
        
        # Save report
        report_path = save_report_to_file(report)
        report['saved_to'] = report_path
        
        # Mark as complete (Phase 6 just means 'done')
        set_phase(request, 6)
        
        return {
            'status': 'success',
            'phase': 6,
            'message': 'Comparison complete!',
            'data': report
        }
        
    except Exception as e:
        print(f"Phase 5 Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# UTILITY ENDPOINTS
# =============================================================================

@app.post("/api/reset")
async def reset_session(request: Request):
    """Reset the session and start over."""
    request.session.clear()
    set_phase(request, 1)
    return {
        'status': 'success',
        'message': 'Session reset. Ready to start fresh.',
        'phase': 1
    }

@app.get("/api/export")
async def export_report(request: Request):
    """Export the current comparison report."""
    report = request.session.get('comparison_report')
    
    if not report:
        raise HTTPException(status_code=400, detail="No report available")
    
    filepath = save_report_to_file(report)
    
    return {
        'status': 'success',
        'message': 'Report exported',
        'filepath': filepath
    }


if __name__ == "__main__":
    try:
        Config.validate()
        print("✅ Configuration validated")
        print(f"🚀 Starting FastAPI Server on port {Config.PORT}")
        uvicorn.run("app:app", host="0.0.0.0", port=Config.PORT, reload=Config.DEBUG)
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        exit(1)
