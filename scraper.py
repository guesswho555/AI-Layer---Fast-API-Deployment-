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
    key_people: list[str] = Field(default_factory=list, description="Important roles/people (CEO, Founders, etc)")
    goals: Optional[str] = Field(default=None, description="Company goals or strategic interests")
    stage: Optional[str] = Field(default=None, description="Company stage (Startup, SME, Enterprise, etc)")
    budget_estimate: Optional[str] = Field(default=None, description="Estimated budget or revenue range if available")


class WebScraper:
    """Web scraping functionality using BeautifulSoup and AI extraction (Async)."""
    
    def __init__(self):
        # Refactored headers to bypass bot detection (Cloudflare/520 errors)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        }
    
    async def fetch_page_content(self, url: str) -> Optional[str]:
        """Fetch and extract text content from a webpage asynchronously."""
        try:
            url = clean_url(url)
            # Use a fresh client for each request with a slightly longer timeout for cloud servers
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, verify=False) as client:
                response = await client.get(url, headers=self.headers)
            
            if response.status_code != 200:
                print(f"⚠️ Failed to fetch {url}. Status code: {response.status_code}")
                return None
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove noise
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                element.decompose()
            
            text = soup.get_text(separator='\n', strip=True)
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            text = '\n'.join(lines)
            
            # OpenRouter context window management
            return text[:15000] if len(text) > 15000 else text
            
        except httpx.HTTPStatusError as e:
            print(f"🛑 HTTP error occurred: {e.response.status_code} for {url}")
            return None
        except Exception as e:
            print(f"❌ Scraping error for {url}: {str(e)}")
            return None
    
    async def extract_company_info_with_ai(self, url: str, page_content: str) -> Optional[dict]:
        """Use OpenRouter to extract structured company information."""
        
        if not Config.OPENROUTER_API_KEY:
            print("❌ Error: OPENROUTER_API_KEY is missing in environment variables.")
            return None

        try:
            # Updated Referer for Render deployment
            headers = {
                "Authorization": f"Bearer {Config.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://lead-discovery-app.onrender.com", # Update to your real Render URL later
                "X-Title": "Lead Discovery System"
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
                "specialties": ["specialty1", "specialty2"],
                "services": ["service1", "service2"],
                "website": "{url}",
                "founded": "Year founded or null",
                "mission": "Mission statement or null",
                "key_people": ["Name (Role)"],
                "goals": "Strategic interests mentioned",
                "stage": "Startup|SME|Enterprise|Corporation",
                "budget_estimate": "Estimated revenue/budget range or 'Unknown'"
            }}
            
            Webpage Content:
            {page_content}
            
            Return ONLY valid JSON. No markdown blocks.
            """
            
            payload = {
                "model": Config.OPENROUTER_MODEL,
                "messages": [
                    {"role": "system", "content": "You are a professional business intelligence analyst."},
                    {"role": "user", "content": extraction_prompt}
                ],
                "temperature": 0.1
            }
            
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(
                    f"{Config.OPENROUTER_BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload
                )
            
            if response.status_code == 401:
                print("❌ OpenRouter API Key Rejected (401). Check credits or key accuracy.")
                return None

            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content'].strip()
            
            # Clean possible markdown formatting from AI
            if content.startswith('```'):
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]
            
            company_data = json.loads(content.strip())
            company_data['url'] = url
            return company_data
            
        except Exception as e:
            print(f"🤖 AI Extraction Error: {str(e)}")
            return None
    
    async def scrape_company(self, url: str) -> Optional[dict]:
        """Main method to scrape and extract company information."""
        print(f"🔍 Starting Scrape for: {url}")
        
        page_content = await self.fetch_page_content(url)
        if not page_content:
            return {"error": True, "message": f"Website blocked the request or URL is invalid.", "url": url}
        
        company_info = await self.extract_company_info_with_ai(url, page_content)
        if not company_info:
            return {"error": True, "message": f"AI could not parse the content (Check API Key/Credits).", "url": url}
        
        print(f"✅ Successful extract: {company_info.get('name')}")
        return company_info
