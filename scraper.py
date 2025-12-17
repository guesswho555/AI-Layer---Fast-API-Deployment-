import httpx
from bs4 import BeautifulSoup
import json
from typing import Optional
from pydantic import BaseModel, Field
from config import Config
from tools import clean_url, extract_domain


class CompanyProfile(BaseModel):
    """Structured data for a company profile."""
    name: str = Field(description="The official name of the company")
    description: str = Field(description="A detailed description of the company")
    industry: str = Field(description="The primary industry")
    size: str = Field(description="Company size (employees)")
    location: str = Field(description="Headquarters location")
    specialties: list[str] = Field(default_factory=list, description="Key specialties")
    services: list[str] = Field(default_factory=list, description="Services offered")
    website: str = Field(description="Company website URL")
    founded: Optional[str] = Field(default=None, description="Year founded")
    mission: Optional[str] = Field(default=None, description="Mission statement")
    
    # New fields
    key_people: list[str] = Field(default_factory=list, description="Important roles/people (CEO, Founders, etc)")
    goals: Optional[str] = Field(default=None, description="Company goals or strategic interests")
    stage: Optional[str] = Field(default=None, description="Company stage (Startup, SME, Enterprise, etc)")
    budget_estimate: Optional[str] = Field(default=None, description="Estimated budget or revenue range if available")


class WebScraper:
    """Web scraping functionality using BeautifulSoup and AI extraction (Async)."""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    async def fetch_page_content(self, url: str) -> Optional[str]:
        """Fetch and extract text content from a webpage asynchronously."""
        try:
            url = clean_url(url)
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                element.decompose()
            
            # Get text content
            text = soup.get_text(separator='\n', strip=True)
            
            # Clean up whitespace
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            text = '\n'.join(lines)
            
            # Limit content length for API
            return text[:20000] if len(text) > 20000 else text
            
        except Exception as e:
            print(f"Error fetching page: {e}")
            return None
    
    async def extract_company_info_with_ai(self, url: str, page_content: str) -> Optional[dict]:
        """Use OpenRouter (Gemini 2.5) to extract structured company information asynchronously."""
        
        try:
            headers = {
                "Authorization": f"Bearer {Config.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:5001",
                "X-Title": "Business Matcher"
            }
            
            extraction_prompt = f"""
            Analyze the following webpage content and extract company information.
            Return a JSON object with these exact fields:
            
            {{
                "name": "Company official name",
                "description": "Detailed company description (2-3 paragraphs)",
                "industry": "Primary industry",
                "size": "Company size (e.g., '1-10', '11-50', '50-200', 'Enterprise')",
                "location": "Headquarters location",
                "specialties": ["specialty1", "specialty2", ...],
                "services": ["service1", "service2", ...],
                "website": "{url}",
                "founded": "Year founded or null",
                "mission": "Mission statement or null",
                "key_people": ["Name (Role)", "Name (Role)", ...],
                "goals": "Key business goals or strategic interests mentioned",
                "stage": "Startup|SME|Enterprise|Corporation (Infer from size/history)",
                "budget_estimate": "Estimated revenue/budget range if mentioned (or 'Unknown')"
            }}
            
            Infere information if not explicitly stated, but be realistic.
            
            Website URL: {url}
            
            Page Content:
            {page_content}
            
            Return ONLY valid JSON, no markdown or explanation.
            """
            
            payload = {
                "model": Config.OPENROUTER_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert business analyst. Extract company information from webpage content and return structured JSON."
                    },
                    {
                        "role": "user",
                        "content": extraction_prompt
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 2000
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{Config.OPENROUTER_BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload
                )
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # Parse JSON from response
            content = content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.startswith('```'):
                content = content[3:]
            if content.endswith('```'):
                content = content[:-3]
            
            company_data = json.loads(content.strip())
            company_data['url'] = url
            
            return company_data
            
        except Exception as e:
            print(f"AI extraction error: {e}")
            return None
    
    async def scrape_company(self, url: str) -> Optional[dict]:
        """
        Main method to scrape and extract company information asynchronously.
        """
        print(f"🔍 Scraping: {url}")
        
        # Step 1: Fetch page content
        page_content = await self.fetch_page_content(url)
        if not page_content:
            return {
                "error": True,
                "message": f"Could not fetch content from {url}",
                "url": url
            }
        
        # Step 2: Extract company info using AI
        company_info = await self.extract_company_info_with_ai(url, page_content)
        if not company_info:
            return {
                "error": True,
                "message": f"Could not extract company information from {url}",
                "url": url
            }
        
        print(f"✅ Successfully scraped: {company_info.get('name', 'Unknown')}")
        return company_info