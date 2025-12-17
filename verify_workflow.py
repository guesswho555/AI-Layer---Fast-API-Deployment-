#!/usr/bin/env python3
import requests
import time
import json

BASE_URL = "http://127.0.0.1:5001"

def run_verification():
    print("🚀 Starting Workflow Verification...")
    
    # Session is handled by cookies in requests, so we need a session object
    session = requests.Session()
    
    # PHASE 1: Set Lead
    print("\n--- Phase 1: Set Lead ---")
    lead_name = "Nvidia"
    resp = session.post(f"{BASE_URL}/api/phase1/set-lead", json={"name": lead_name})
    if resp.status_code != 200:
        print(f"FAILED Phase 1: {resp.text}")
        return
    print(f"Phase 1 Success: {resp.json()['message']}")
    
    # PHASE 2: Search
    print("\n--- Phase 2: Search URL ---")
    resp = session.post(f"{BASE_URL}/api/phase2/search")
    if resp.status_code != 200:
        print(f"FAILED Phase 2: {resp.text}")
        return
    results = resp.json()['data']['results']
    print(f"Found {len(results)} URLs")
    if not results:
        print("FAILED: No results found")
        return
    
    # Pick first URL (should be nvidia.com)
    target_url = results[0]['url']
    print(f"Selected URL: {target_url}")
    
    # PHASE 3: Select
    print("\n--- Phase 3: Select URL ---")
    resp = session.post(f"{BASE_URL}/api/phase3/select", json={"url": target_url})
    if resp.status_code != 200:
        print(f"FAILED Phase 3: {resp.text}")
        return
    print(f"Phase 3 Success: {resp.json()['message']}")
    
    # PHASE 4: Scrape
    print("\n--- Phase 4: Scrape Lead ---")
    print("Scraping... (this make take a few seconds)")
    resp = session.post(f"{BASE_URL}/api/phase4/scrape")
    if resp.status_code != 200:
        print(f"FAILED Phase 4: {resp.text}")
        return
    lead_data = resp.json()['data']
    print(f"Scraped Lead: {lead_data.get('name')}")
    print(f"Stage: {lead_data.get('stage')}")
    print(f"Budget: {lead_data.get('budget_estimate')}")
    
    # PHASE 5: Compare
    print("\n--- Phase 5: Compare ---")
    user_company = {
        "name": "AI Startup Inc",
        "description": "We specialize in high-performance AI software optimization and custom CUDA kernels.",
        "industry": "Artificial Intelligence",
        "size": "11-50",
        "services": ["AI Optimization", "CUDA Development", "ML Infrastructure"],
        "specialties": ["GPU Computing", "Efficiency"],
        "goals": "Partner with hardware manufacturers to optimize our software stack.",
        "stage": "Startup"
    }
    
    print("Comparing with user data...")
    resp = session.post(f"{BASE_URL}/api/phase5/compare", json={"user_company": user_company})
    if resp.status_code != 200:
        print(f"FAILED Phase 5: {resp.text}")
        return
    
    report = resp.json()['data']
    print(f"\n✅ Comparison Complete!")
    print(f"Match Score: {report['numeric_summary'].get('overall_score')}%")
    print("\nChecking for Explanations:")
    cat_analysis = report['comparison'].get('category_analysis', {})
    for cat, details in cat_analysis.items():
        print(f"- {cat}: {details.get('explanation')[:50]}...")

if __name__ == "__main__":
    # Wait for server to start if running immediately
    time.sleep(2)
    try:
        run_verification()
    except Exception as e:
        print(f"Verification Failed: {e}")
        print("Is the server running?")
