import json
import httpx
import asyncio
from typing import List, Optional
from config import Config
from tools import load_data_store
from ddgs import DDGS


class SearchEngine:
    """
    Search engine for finding a specific company's URL (Async).
    
    Phase 2: Lead Discovery
    """
    
    def __init__(self):
        # DDGS is synchronous, we will wrap calls in asyncio.to_thread
        self.ddgs = DDGS()
    
    async def find_company_url(
        self,
        company_name: str,
        max_results: int = 5
    ) -> List[dict]:
        """
        Search for the official website of a specific company.
        
        Args:
            company_name: Name of the lead company
            max_results: Maximum number of URLs to return
        
        Returns:
            List of dictionaries containing URL and preview info
        """
        print(f"🔎 Searching for URL of: {company_name}")
        
        # Build search query
        search_query = f"{company_name} official website"
        print(f"🔎 EXECUTING QUERY: '{search_query}'")
        
        try:
            # Perform DuckDuckGo search
            fetch_count = max_results * 3
            
            def run_search():
                return list(self.ddgs.text(search_query, max_results=fetch_count))
            
            results = await asyncio.to_thread(run_search)
            
            # Filter and format results
            formatted_results = self._format_search_results(results, max_results)
            
            # Rank results using AI to identify the most likely official URL
            if formatted_results:
                formatted_results = await self._rank_by_relevance(
                    formatted_results,
                    company_name
                )
            
            print(f"✅ Found {len(formatted_results)} potential URLs")
            return formatted_results[:max_results]
            
        except Exception as e:
            print(f"Search error: {e}")
            return []
    
    def _format_search_results(
        self,
        results: List[dict],
        max_results: int
    ) -> List[dict]:
        """Format and filter search results."""
        formatted = []
        seen_domains = set()
        
        for result in results:
            url = result.get('href', result.get('link', ''))
            title = result.get('title', '')
            snippet = result.get('body', result.get('snippet', ''))
            
            if not url:
                continue
            
            # Extract domain for deduplication
            domain = self._extract_domain(url)
            if domain in seen_domains:
                continue
            seen_domains.add(domain)
            
            # Filter out non-company pages
            if self._is_valid_company_page(url, title):
                formatted.append({
                    'url': url,
                    'title': title,
                    'snippet': snippet[:300] if snippet else '',
                    'domain': domain
                })
            
            if len(formatted) >= max_results:
                break
        
        return formatted
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        import re
        pattern = r'https?://(?:www\.)?([^/]+)'
        match = re.match(pattern, url)
        return match.group(1) if match else url
    
    def _is_valid_company_page(self, url: str, title: str) -> bool:
        """Check if URL is likely a company page."""
        # Filter out common non-company pages
        excluded_domains = [
            'wikipedia.org', 'facebook.com', 'twitter.com',
            'instagram.com', 'youtube.com', 'linkedin.com/posts',
            'reddit.com', 'quora.com', 'news.', 'blog.',
            'crunchbase.com', 'bloomberg.com', 'pitchbook.com'
        ]
        
        url_lower = url.lower()
        for excluded in excluded_domains:
            if excluded in url_lower:
                return False
        
        return True
    
    async def _rank_by_relevance(
        self,
        results: List[dict],
        company_name: str
    ) -> List[dict]:
        """Use AI to rank results by likelihood of being the official company website."""
        
        try:
            headers = {
                "Authorization": f"Bearer {Config.OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            }
            
            ranking_prompt = f"""
            Identify the official website for the company "{company_name}" from the search results below.
            
            Search Results:
            {json.dumps([{'url': r['url'], 'title': r['title'], 'snippet': r['snippet']} for r in results], indent=2)}
            
            Rank them in order of likelihood (Most likely official site first).
            Return a JSON array of URLs.
            Example: ["https://official-site.com", "https://other-site.com"]
            
            Return ONLY the valid JSON array.
            """
            
            payload = {
                "model": Config.OPENROUTER_MODEL,
                "messages": [
                    {"role": "user", "content": ranking_prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 500
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{Config.OPENROUTER_BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload
                )
            
            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content']
                content = content.strip()
                if content.startswith('```'):
                    content = content.split('\n', 1)[1].rsplit('```', 1)[0]
                
                try:
                    ranked_urls = json.loads(content)
                except json.JSONDecodeError:
                    return results
                
                # Reorder results based on ranking
                url_to_result = {r['url']: r for r in results}
                ranked_results = []
                for url in ranked_urls:
                    if url in url_to_result:
                        ranked_results.append(url_to_result[url])
                
                # Add any missing results at the end
                for result in results:
                    if result not in ranked_results:
                        ranked_results.append(result)
                
                return ranked_results
                
        except Exception as e:
            print(f"Ranking error: {e}")
        
        return results