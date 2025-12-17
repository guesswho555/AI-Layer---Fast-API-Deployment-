import json
import httpx
from typing import Optional
from config import Config


class ComparisonEngine:
    """
    Engine for comparing User Company vs Lead Company (Async).
    
    Phase 5: Comparison & Match Report
    """
    
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {Config.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5001",
            "X-Title": "Business Matcher"
        }
    
    async def compare_companies(
        self,
        user_company: dict,
        lead_company: dict
    ) -> dict:
        """
        Compare User's company with Lead's company and generate a report.
        """
        print(f"📊 Comparing: {user_company.get('name')} (User) vs {lead_company.get('name')} (Lead)")
        
        # Step 1: Generate detailed comparison with explanations
        comparison = await self._generate_detailed_comparison(user_company, lead_company)
        
        # Step 2: Calculate numeric scores
        numeric_summary = await self._calculate_numeric_scores(
            user_company,
            lead_company,
            comparison
        )
        
        # Step 3: Compile full report
        report = {
            "user_company": user_company,
            "lead_company": lead_company,
            "comparison": comparison,
            "numeric_summary": numeric_summary
        }
        
        print(f"✅ Comparison complete. Match: {numeric_summary.get('overall_score', 0)}%")
        
        return report
    
    async def _generate_detailed_comparison(
        self,
        user: dict,
        lead: dict
    ) -> dict:
        """Generate AI-powered comparison analysis asynchronously."""
        
        comparison_prompt = f"""
        Perform a comprehensive B2B business matching analysis.
        
        USER COMPANY (My Company):
        - Name: {user.get('name')}
        - Description: {user.get('description')}
        - Industry: {user.get('industry')}
        - Size: {user.get('size')}
        - Products/Services: {', '.join(user.get('services', []))}
        - Specialties: {', '.join(user.get('specialties', []))}
        - Goals: {user.get('goals', 'N/A')}
        - Stage: {user.get('stage', 'N/A')}
        
        LEAD COMPANY (Target):
        - Name: {lead.get('name')}
        - Description: {lead.get('description')}
        - Industry: {lead.get('industry')}
        - Size: {lead.get('size')}
        - Products/Services: {', '.join(lead.get('services', []))}
        - Specialties: {', '.join(lead.get('specialties', []))}
        - Goals: {lead.get('goals', 'N/A')}
        - Stage: {lead.get('stage', 'N/A')}
        - Budget Estimate: {lead.get('budget_estimate', 'N/A')}
        
        Analyze the alignment and provide a JSON response with the following structure.
        Crucial: For every "explanation" field, you MUST explain HOW and WHY based on the data.
        
        {{
            "match_summary": "Brief executive summary of the business match opportunity",
            "business_match_percentage": <0-100 number>,
            "company_alignment": {{
                 "stage_comparison": "Compare stages (e.g. Startup vs Enterprise) and what it means",
                 "size_compatibility": "Analyze if the size difference is a pro or con",
                 "budget_fit": "Analyze if the lead likely has budget for user services"
            }},
            "key_interests_goals": "Analysis of shared or complementary goals",
            "similarities": ["Sim 1", "Sim 2", ...],
            "differences": ["Diff 1", "Diff 2", ...],
            "category_analysis": {{
                "size_compatibility": {{
                    "score": <0-100>,
                    "explanation": "HOW and WHY?"
                }},
                "service_overlap": {{
                    "score": <0-100>,
                    "explanation": "HOW and WHY?"
                }},
                "specialty_match": {{
                    "score": <0-100>,
                    "explanation": "HOW and WHY?"
                }},
                "market_alignment": {{
                    "score": <0-100>,
                    "explanation": "HOW and WHY?"
                }},
                "technology_synergy": {{
                    "score": <0-100>,
                    "explanation": "HOW and WHY?"
                }}
            }},
            "overall_opportunity": "Final verdict on the partnership/sales opportunity"
        }}
        
        Return ONLY valid JSON.
        """
        
        try:
            payload = {
                "model": Config.OPENROUTER_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a strategic business consultant expert in B2B matching."
                    },
                    {
                        "role": "user",
                        "content": comparison_prompt
                    }
                ],
                "temperature": 0.2,
                "max_tokens": 2500
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{Config.OPENROUTER_BASE_URL}/chat/completions",
                    headers=self.headers,
                    json=payload
                )
            response.raise_for_status()
            
            content = response.json()['choices'][0]['message']['content']
            
            # Parse JSON
            content = content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.startswith('```'):
                content = content[3:]
            if content.endswith('```'):
                content = content[:-3]
            
            return json.loads(content.strip())
            
        except Exception as e:
            print(f"Comparison error: {e}")
            return {
                "error": str(e)
            }
    
    async def _calculate_numeric_scores(
        self,
        user: dict,
        lead: dict,
        comparison: dict
    ) -> dict:
        """
        Extract validation scores. 
        In this version, most scoring is done in the main prompt, 
        so this just extracts/formats them for the summary.
        """
        try:
            category_analysis = comparison.get("category_analysis", {})
            
            scores = {
                "size_compatibility": category_analysis.get("size_compatibility", {}).get("score", 0),
                "service_overlap": category_analysis.get("service_overlap", {}).get("score", 0),
                "specialty_match": category_analysis.get("specialty_match", {}).get("score", 0),
                "market_alignment": category_analysis.get("market_alignment", {}).get("score", 0),
                "technology_synergy": category_analysis.get("technology_synergy", {}).get("score", 0)
            }
            
            return {
                "scores": scores,
                "overall_score": comparison.get("business_match_percentage", 0),
                "recommendation": comparison.get("overall_opportunity", "")
            }
            
        except Exception as e:
            print(f"Scoring extraction error: {e}")
            return {}