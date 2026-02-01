import re
from typing import Dict, List, Any, Optional

class ICPScoring:
    """
    Implements the ICP Scoring logic:
    1. Hard Filters (Pass/Fail)
    2. Signal Extraction (Positive/Negative)
    3. Weighted Scoring (0-100)
    """

    def __init__(self):
        # Default weights from summary
        self.weights = {
            "firmographic": 0.35,
            "technographic": 0.25,
            "behavioral": 0.20,
            "signal_boost": 0.20
        }
        
        # Signal Keywords
        self.positive_signals = {
            "FUNDED": ["funding", "series a", "series b", "series c", "venture capital", "investment"],
            "GROWING": ["growing", "expansion", "new office", "hiring aggressively"],
            "SCALING": ["scaling", "scale", "global expansion"],
            "HIRING": ["hiring", "jobs", "careers", "openings", "recruit"],
            "B2B_FIT": ["b2b", "enterprise", "saas", "platform"],
            "TECH_FIT": ["api", "integration", "cloud", "aws", "azure", "gcp"],
            "ACTIVE_NEED": ["looking for", "need", "problem", "solution"]
        }
        
        self.negative_signals = {
            "COMPETITOR": ["competitor", "rival"], # This usually needs a specific list
            "CONTRACTION": ["layoffs", "downsizing", "cutbacks", "restructuring"],
            "FINANCIAL_RISK": ["bankruptcy", "debt", "financial trouble"],
            "LEGAL_RISK": ["lawsuit", "legal dispute", "court"]
        }

    def evaluate_lead(self, lead: Dict[str, Any], icp_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Full evaluation pipeline. 
        Returns scoring result, pass/fail status, and explanation.
        """
        if not icp_profile:
            icp_profile = {}

        # Stage 1: Hard Filters
        filter_result = self._check_hard_filters(lead, icp_profile)
        if not filter_result["passed"]:
            return {
                "score": 0,
                "grade": "F",
                "status": "REJECTED",
                "passed_filters": False,
                "rejection_reason": filter_result["reason"],
                "signals": {},
                "breakdown": {}
            }

        # Stage 2: Signals
        signals = self._extract_signals(lead)

        # Stage 3: Scoring
        score_data = self._calculate_score(lead, icp_profile, signals)

        return {
            "score": score_data["total_score"],
            "grade": score_data["grade"],
            "status": score_data["status"],
            "passed_filters": True,
            "signals": signals,
            "breakdown": score_data["breakdown"]
        }

    def _check_hard_filters(self, lead: Dict[str, Any], icp: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check Pass/Fail criteria.
        Supported Filters:
        - restricted_industries (list)
        - restricted_regions (list)
        - min_employees (int)
        """
        # Industry Check
        if "restricted_industries" in icp:
            lead_industry = lead.get("industry", "").lower()
            for restricted in icp["restricted_industries"]:
                if restricted.lower() in lead_industry:
                    return {"passed": False, "reason": f"Industry '{lead_industry}' is restricted."}

        # Region Check
        if "restricted_regions" in icp:
            lead_loc = lead.get("location", "").lower() or lead.get("headquarters", "").lower()
            for restricted in icp["restricted_regions"]:
                if restricted.lower() in lead_loc:
                    return {"passed": False, "reason": f"Region '{lead_loc}' is restricted."}
        
        # Size Check
        if "min_employees" in icp:
            min_emp = icp["min_employees"]
            lead_emp = lead.get("employee_count", 0)
            # Handle string ranges like "51-200" if needed, simplified here
            if isinstance(lead_emp, int) and lead_emp < min_emp:
                 return {"passed": False, "reason": f"Employee count {lead_emp} below minimum {min_emp}."}

        return {"passed": True}

    def _extract_signals(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        """
        Scan lead data (description, about us, recent news) for signals.
        """
        found_signals = {
            "positive": [],
            "negative": [],
            "score_modifier": 0
        }
        
        # Aggregate text to search
        text_content = " ".join([
            str(lead.get("description", "")),
            str(lead.get("about", "")),
            str(lead.get("recent_news", ""))
        ]).lower()

        # Check Positive
        for signal_name, keywords in self.positive_signals.items():
            for kw in keywords:
                if kw in text_content:
                    found_signals["positive"].append(signal_name)
                    found_signals["score_modifier"] += 5 # +5 for each positive type found
                    break # Count each signal type once

        # Check Negative
        for signal_name, keywords in self.negative_signals.items():
            for kw in keywords:
                if kw in text_content:
                    found_signals["negative"].append(signal_name)
                    found_signals["score_modifier"] -= 10 # -10 for each negative type
                    break

        return found_signals

    def _calculate_score(self, lead: Dict[str, Any], icp: Dict[str, Any], signals: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate weighted score properties.
        """
        breakdown = {
            "firmographic": 0,
            "technographic": 0,
            "behavioral": 0,
            "signal_boost": 0
        }

        # 1. Firmographic (35%)
        # - Industry Match (if defined in ICP target_industries) -> 100
        # - Size Match -> 100
        f_score = 50 # Base
        target_inds = icp.get("target_industries", [])
        if target_inds:
            lead_ind = lead.get("industry", "").lower()
            if any(t.lower() in lead_ind for t in target_inds):
                f_score += 50
        
        breakdown["firmographic"] = min(100, f_score)

        # 2. Technographic (25%)
        # - Tech overlap (if defined in ICP required_tech)
        t_score = 50 # Base
        req_tech = icp.get("required_technologies", [])
        if req_tech:
            lead_tech = [t.lower() for t in lead.get("technologies", [])]
            matches = sum(1 for t in req_tech if t.lower() in lead_tech)
            if matches > 0:
                t_score += (matches / len(req_tech)) * 50
        
        breakdown["technographic"] = min(100, t_score)

        # 3. Behavioral (20%)
        # - Check for "Growing" or "Hiring" signals specifically as proxy
        b_score = 50
        if "GROWING" in signals["positive"] or "HIRING" in signals["positive"]:
            b_score += 40
        breakdown["behavioral"] = b_score

        # 4. Signal Boost (20%)
        # - Normalize modifier (-20 to +20 range roughly) into 0-100
        # Base 50, + signal_modifier
        s_base = 50
        s_score = s_base + signals["score_modifier"]
        breakdown["signal_boost"] = max(0, min(100, s_score))

        # Weighted Total
        total = (
            breakdown["firmographic"] * self.weights["firmographic"] +
            breakdown["technographic"] * self.weights["technographic"] +
            breakdown["behavioral"] * self.weights["behavioral"] +
            breakdown["signal_boost"] * self.weights["signal_boost"]
        )

        # Grade & Status
        grade = "F"
        status = "REJECTED"
        if total >= 80:
            grade = "A"
            status = "HIGH_PRIORITY"
        elif total >= 70:
            grade = "B"
            status = "AUTO_QUALIFIED"
        elif total >= 60:
            grade = "C"
            status = "REVIEW"
        elif total >= 50:
            grade = "D"
            status = "REVIEW"
        
        return {
            "total_score": round(total, 1),
            "grade": grade,
            "status": status,
            "breakdown": breakdown
        }
