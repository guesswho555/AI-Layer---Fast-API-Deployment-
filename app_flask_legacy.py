import os
from config import Config
from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS

app = Flask(__name__)
app.secret_key = Config.SECRET_KEY
CORS(app)

from scraper import WebScraper
from search_engine import SearchEngine
from comparison_engine import ComparisonEngine
from tools import (
    save_report_to_file,
    add_company_to_store,
    clean_url
)

scraper = WebScraper()
search_engine = SearchEngine()
comparison_engine = ComparisonEngine()


# =============================================================================
# PHASE TRACKING
# =============================================================================

def get_current_phase():
    """Get the current phase from session."""
    return session.get('current_phase', 1)


def set_phase(phase: int):
    """Set the current phase."""
    session['current_phase'] = phase


def get_session_data():
    """Get all session data."""
    return {
        'current_phase': session.get('current_phase', 1),
        'source_company': session.get('source_company'),
        'search_results': session.get('search_results'),
        'selected_url': session.get('selected_url'),
        'target_company': session.get('target_company'),
        'comparison_report': session.get('comparison_report')
    }


# =============================================================================
# ROUTES
# =============================================================================

@app.route('/')
def index():
    """Serve the main HTML page."""
    # Reset session for fresh start
    session.clear()
    set_phase(1)
    return render_template('index.html')


@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current application status and phase."""
    return jsonify({
        'status': 'success',
        'phase': get_current_phase(),
        'data': get_session_data()
    })


# =============================================================================
# PHASE 1: Source Company Scraping
# =============================================================================

@app.route('/api/phase1/scrape', methods=['POST'])
def phase1_scrape_source():
    """
    PHASE 1: Scrape source company URL
    
    Input: Company URL
    Output: Company profile (name, description, industry, size, specialties, services, etc.)
    """
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({
            'status': 'error',
            'message': 'URL is required'
        }), 400
    
    url = clean_url(url)
    
    try:
        print(f"\n{'='*50}")
        print(f"PHASE 1: Scraping Source Company")
        print(f"URL: {url}")
        print(f"{'='*50}")
        
        # Scrape company information
        company_data = scraper.scrape_company(url)
        
        if company_data.get('error'):
            return jsonify({
                'status': 'error',
                'message': company_data.get('message', 'Failed to scrape company')
            }), 400
        
        # Store in session and data store
        session['source_company'] = company_data
        add_company_to_store(company_data)
        
        # Move to Phase 2
        set_phase(2)
        
        return jsonify({
            'status': 'success',
            'phase': 2,
            'message': 'Source company scraped successfully',
            'data': company_data
        })
        
    except Exception as e:
        print(f"Phase 1 Error: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# =============================================================================
# PHASE 2: Keyword Search
# =============================================================================

@app.route('/api/phase2/search', methods=['POST'])
def phase2_search():
    """
    PHASE 2: Search for similar companies based on keywords
    
    Input: Keywords/text
    Output: Array of 5 URLs with previews
    """
    data = request.get_json()
    keywords = data.get('keywords')
    
    if not keywords:
        return jsonify({
            'status': 'error',
            'message': 'Keywords are required'
        }), 400
    
    # Check we're in correct phase
    if get_current_phase() < 2:
        return jsonify({
            'status': 'error',
            'message': 'Please complete Phase 1 first'
        }), 400
    
    try:
        print(f"\n{'='*50}")
        print(f"PHASE 2: Searching for Similar Companies")
        print(f"Keywords: {keywords}")
        print(f"{'='*50}")
        
        # Get source company for context
        source_company = session.get('source_company')
        
        # Search for similar companies
        search_results = search_engine.search_similar_companies(
            keywords=keywords,
            source_company=source_company,
            max_results=5
        )
        
        # Also search local data store
        local_results = search_engine.search_from_data_store(
            keywords=keywords,
            max_results=2
        )
        
        # Combine results (prioritize web results)
        all_results = search_results + [r for r in local_results if r not in search_results]
        all_results = all_results[:5]
        
        # Store in session
        session['search_results'] = all_results
        session['search_keywords'] = keywords
        
        # Move to Phase 3
        set_phase(3)
        
        return jsonify({
            'status': 'success',
            'phase': 3,
            'message': f'Found {len(all_results)} similar companies',
            'data': {
                'keywords': keywords,
                'results': all_results
            }
        })
        
    except Exception as e:
        print(f"Phase 2 Error: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# =============================================================================
# PHASE 3: URL Selection
# =============================================================================

@app.route('/api/phase3/select', methods=['POST'])
def phase3_select_url():
    """
    PHASE 3: User selects one URL from search results
    
    Input: Selected URL
    Output: Confirmation and move to Phase 4
    """
    data = request.get_json()
    selected_url = data.get('url')
    
    if not selected_url:
        return jsonify({
            'status': 'error',
            'message': 'URL selection is required'
        }), 400
    
    # Check we're in correct phase
    if get_current_phase() < 3:
        return jsonify({
            'status': 'error',
            'message': 'Please complete Phase 2 first'
        }), 400
    
    try:
        print(f"\n{'='*50}")
        print(f"PHASE 3: URL Selected")
        print(f"Selected: {selected_url}")
        print(f"{'='*50}")
        
        # Store selection
        session['selected_url'] = selected_url
        
        # Move to Phase 4
        set_phase(4)
        
        return jsonify({
            'status': 'success',
            'phase': 4,
            'message': 'URL selected. Ready for target company scraping.',
            'data': {
                'selected_url': selected_url
            }
        })
        
    except Exception as e:
        print(f"Phase 3 Error: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# =============================================================================
# PHASE 4: Target Company Scraping
# =============================================================================

@app.route('/api/phase4/scrape', methods=['POST'])
def phase4_scrape_target():
    """
    PHASE 4: Scrape selected target company URL
    
    Input: Selected URL (from Phase 3)
    Output: Target company profile
    """
    # Check we're in correct phase
    if get_current_phase() < 4:
        return jsonify({
            'status': 'error',
            'message': 'Please complete Phase 3 first'
        }), 400
    
    selected_url = session.get('selected_url')
    
    if not selected_url:
        return jsonify({
            'status': 'error',
            'message': 'No URL selected'
        }), 400
    
    try:
        print(f"\n{'='*50}")
        print(f"PHASE 4: Scraping Target Company")
        print(f"URL: {selected_url}")
        print(f"{'='*50}")
        
        # Scrape target company
        target_data = scraper.scrape_company(selected_url)
        
        if target_data.get('error'):
            return jsonify({
                'status': 'error',
                'message': target_data.get('message', 'Failed to scrape target company')
            }), 400
        
        # Store in session and data store
        session['target_company'] = target_data
        add_company_to_store(target_data)
        
        # Move to Phase 5 (ready for comparison)
        set_phase(5)
        
        return jsonify({
            'status': 'success',
            'phase': 5,
            'message': 'Target company scraped successfully. Ready for comparison.',
            'data': target_data
        })
        
    except Exception as e:
        print(f"Phase 4 Error: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# =============================================================================
# PHASE 5: Comparison & Summary
# =============================================================================

@app.route('/api/phase5/compare', methods=['POST'])
def phase5_compare():
    """
    PHASE 5: Compare source and target companies
    
    Input: Confirm action
    Output: Full comparison report with numeric summary
    """
    # Check we're in correct phase
    if get_current_phase() < 5:
        return jsonify({
            'status': 'error',
            'message': 'Please complete Phase 4 first'
        }), 400
    
    source_company = session.get('source_company')
    target_company = session.get('target_company')
    
    if not source_company or not target_company:
        return jsonify({
            'status': 'error',
            'message': 'Missing company data'
        }), 400
    
    try:
        print(f"\n{'='*50}")
        print(f"PHASE 5: Generating Comparison Report")
        print(f"Source: {source_company.get('name')}")
        print(f"Target: {target_company.get('name')}")
        print(f"{'='*50}")
        
        # Generate comparison
        report = comparison_engine.compare_companies(
            source_company=source_company,
            target_company=target_company
        )
        
        # Store in session
        session['comparison_report'] = report
        
        # Save report to file
        report_path = save_report_to_file(report)
        report['saved_to'] = report_path
        
        # Mark as complete
        set_phase(6)
        
        return jsonify({
            'status': 'success',
            'phase': 6,
            'message': 'Comparison complete!',
            'data': report
        })
        
    except Exception as e:
        print(f"Phase 5 Error: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# =============================================================================
# UTILITY ENDPOINTS
# =============================================================================

@app.route('/api/reset', methods=['POST'])
def reset_session():
    """Reset the session and start over."""
    session.clear()
    set_phase(1)
    return jsonify({
        'status': 'success',
        'message': 'Session reset. Ready to start fresh.',
        'phase': 1
    })


@app.route('/api/export', methods=['GET'])
def export_report():
    """Export the current comparison report."""
    report = session.get('comparison_report')
    
    if not report:
        return jsonify({
            'status': 'error',
            'message': 'No report available'
        }), 400
    
    filepath = save_report_to_file(report)
    
    return jsonify({
        'status': 'success',
        'message': 'Report exported',
        'filepath': filepath
    })


# =============================================================================
# COMBINED FLOW ENDPOINT (Alternative)
# =============================================================================

@app.route('/api/quick-match', methods=['POST'])
def quick_match():
    """
    Quick endpoint that takes two URLs and returns comparison.
    Bypasses the multi-phase flow for simple use cases.
    """
    data = request.get_json()
    source_url = data.get('source_url')
    target_url = data.get('target_url')
    
    if not source_url or not target_url:
        return jsonify({
            'status': 'error',
            'message': 'Both source_url and target_url are required'
        }), 400
    
    try:
        # Scrape both companies
        source_company = scraper.scrape_company(clean_url(source_url))
        target_company = scraper.scrape_company(clean_url(target_url))
        
        if source_company.get('error') or target_company.get('error'):
            return jsonify({
                'status': 'error',
                'message': 'Failed to scrape one or both companies'
            }), 400
        
        # Generate comparison
        report = comparison_engine.compare_companies(source_company, target_company)
        
        # Save report
        report_path = save_report_to_file(report)
        report['saved_to'] = report_path
        
        return jsonify({
            'status': 'success',
            'data': report
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    # Validate configuration
    try:
        Config.validate()
        print("✅ Configuration validated")
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        exit(1)
    
    # Create required directories
    os.makedirs('reports', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    print(f"""
    ╔══════════════════════════════════════════════════════════╗
    ║          BUSINESS MATCHING SYSTEM                        ║
    ╠══════════════════════════════════════════════════════════╣
    ║  Phase 1: Source Company Scraping                        ║
    ║  Phase 2: Keyword Search (5 URLs)                        ║
    ║  Phase 3: URL Selection                                  ║
    ║  Phase 4: Target Company Scraping                        ║
    ║  Phase 5: Comparison & Numeric Summary                   ║
    ╚══════════════════════════════════════════════════════════╝
    
    Server running at: http://localhost:{Config.PORT}
    """)
    
    app.run(debug=Config.DEBUG, port=Config.PORT)