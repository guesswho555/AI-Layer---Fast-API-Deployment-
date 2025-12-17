import datetime
import json
import os
import re
from typing import Optional
from config import Config


def save_report_to_file(
    report_data: dict,
    filename: Optional[str] = None
) -> str:
    """
    Saves the detailed business match report data to a text file.
    
    Args:
        report_data: Dictionary containing the full report
        filename: Optional custom filename
    
    Returns:
        Path to saved file or error message
    """
    try:
        # Ensure reports directory exists
        os.makedirs(Config.REPORTS_PATH, exist_ok=True)
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        file_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if filename is None:
            filename = f"business_match_report_{file_timestamp}.txt"
        
        filepath = os.path.join(Config.REPORTS_PATH, filename)
        
        # Format the report
        formatted_text = format_report(report_data, timestamp)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(formatted_text)
        
        return filepath
    except Exception as e:
        return f"Error saving file: {e}"


def format_report(report_data: dict, timestamp: str) -> str:
    """Format report data into readable text."""
    
    text = "=" * 60 + "\n"
    text += "    BUSINESS MATCH ANALYSIS REPORT\n"
    text += "=" * 60 + "\n\n"
    text += f"Generated On: {timestamp}\n\n"
    
    # Source Company Profile
    if "source_company" in report_data:
        text += "-" * 40 + "\n"
        text += "SOURCE COMPANY PROFILE\n"
        text += "-" * 40 + "\n"
        text += format_company_profile(report_data["source_company"])
        text += "\n"
    
    # Target Company Profile
    if "target_company" in report_data:
        text += "-" * 40 + "\n"
        text += "TARGET COMPANY PROFILE\n"
        text += "-" * 40 + "\n"
        text += format_company_profile(report_data["target_company"])
        text += "\n"
    
    # Comparison Analysis
    if "comparison" in report_data:
        text += "-" * 40 + "\n"
        text += "COMPARATIVE ANALYSIS\n"
        text += "-" * 40 + "\n"
        text += format_comparison(report_data["comparison"])
        text += "\n"
    
    # Numeric Summary
    if "numeric_summary" in report_data:
        text += "-" * 40 + "\n"
        text += "NUMERIC SUMMARY\n"
        text += "-" * 40 + "\n"
        text += format_numeric_summary(report_data["numeric_summary"])
        text += "\n"
    
    text += "=" * 60 + "\n"
    text += "END OF REPORT\n"
    text += "=" * 60 + "\n"
    
    return text


def format_company_profile(profile: dict) -> str:
    """Format a company profile into readable text."""
    text = ""
    text += f"• Company Name: {profile.get('name', 'N/A')}\n"
    text += f"• Description: {profile.get('description', 'N/A')}\n"
    text += f"• Industry: {profile.get('industry', 'N/A')}\n"
    text += f"• Size: {profile.get('size', 'N/A')}\n"
    text += f"• Location: {profile.get('location', 'N/A')}\n"
    
    specialties = profile.get('specialties', [])
    if specialties:
        text += f"• Specialties:\n"
        for spec in specialties:
            text += f"    - {spec}\n"
    
    services = profile.get('services', [])
    if services:
        text += f"• Services:\n"
        for svc in services:
            text += f"    - {svc}\n"
    
    return text


def format_comparison(comparison: dict) -> str:
    """Format comparison data into readable text."""
    text = ""
    
    text += f"\nMatch Score: {comparison.get('match_score', 'N/A')}\n"
    text += f"Match Level: {comparison.get('match_level', 'N/A')}\n\n"
    
    text += "Similarities:\n"
    for sim in comparison.get('similarities', []):
        text += f"  ✓ {sim}\n"
    
    text += "\nDifferences:\n"
    for diff in comparison.get('differences', []):
        text += f"  ✗ {diff}\n"
    
    text += f"\nRationale:\n{comparison.get('rationale', 'N/A')}\n"
    
    return text


def format_numeric_summary(summary: dict) -> str:
    """Format numeric summary into readable text."""
    text = ""
    
    scores = summary.get('scores', {})
    text += "\nCategory Scores (0-100):\n"
    text += f"  • Industry Alignment:    {scores.get('industry_alignment', 0):>3}%\n"
    text += f"  • Size Compatibility:    {scores.get('size_compatibility', 0):>3}%\n"
    text += f"  • Service Overlap:       {scores.get('service_overlap', 0):>3}%\n"
    text += f"  • Specialty Match:       {scores.get('specialty_match', 0):>3}%\n"
    text += f"  • Market Alignment:      {scores.get('market_alignment', 0):>3}%\n"
    text += f"  • Technology Synergy:    {scores.get('technology_synergy', 0):>3}%\n"
    
    text += f"\n  ══════════════════════════════\n"
    text += f"  OVERALL MATCH SCORE:     {summary.get('overall_score', 0):>3}%\n"
    text += f"  ══════════════════════════════\n"
    
    text += f"\nRecommendation: {summary.get('recommendation', 'N/A')}\n"
    
    return text


def clean_url(url: str) -> str:
    """Clean and validate URL format."""
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url


def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    pattern = r'https?://(?:www\.)?([^/]+)'
    match = re.match(pattern, url)
    return match.group(1) if match else url


def load_data_store() -> dict:
    """Load the data store from JSON file."""
    try:
        if os.path.exists(Config.DATA_STORE_PATH):
            with open(Config.DATA_STORE_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {"companies": [], "searches": []}


def save_data_store(data: dict) -> bool:
    """Save data to the data store."""
    try:
        with open(Config.DATA_STORE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def add_company_to_store(company_data: dict) -> bool:
    """Add a company profile to the data store."""
    data = load_data_store()
    
    # Check if company already exists (by URL)
    existing_urls = [c.get('url') for c in data['companies']]
    if company_data.get('url') not in existing_urls:
        company_data['added_at'] = datetime.datetime.now().isoformat()
        data['companies'].append(company_data)
        return save_data_store(data)
    return True