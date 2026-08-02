import re
from typing import List, Tuple, Optional
from src.models.listing import CategoryEnum, ConversionPotentialEnum


INDIAN_LOCATION_MAP = {
    "bengaluru": "Bengaluru",
    "bangalore": "Bengaluru",
    "blr": "Bengaluru",
    "gurgaon": "NCR (Delhi/Gurgaon/Noida)",
    "gurugram": "NCR (Delhi/Gurgaon/Noida)",
    "noida": "NCR (Delhi/Gurgaon/Noida)",
    "delhi": "NCR (Delhi/Gurgaon/Noida)",
    "ncr": "NCR (Delhi/Gurgaon/Noida)",
    "hyderabad": "Hyderabad",
    "hyd": "Hyderabad",
    "pune": "Pune",
    "mumbai": "Mumbai",
    "chennai": "Chennai",
    "remote": "Remote (India)",
    "india": "Remote (India)"
}

INCLUDE_KEYWORDS = [
    "software", "sde", "developer", "backend", "frontend", "fullstack",
    "ai", "ml", "machine learning", "data science", "deep learning", "llm",
    "systems", "cloud", "devops", "sre", "platform", "infrastructure",
    "data engineer", "analytics", "research scientist", "genai", "computer vision", "nlp"
]

EXCLUDE_KEYWORDS = [
    "sales", "marketing", "recruiter", "hr", "accounting", "finance",
    "legal", "executive assistant", "content writer", "customer support"
]


def is_india_location(loc_str: str) -> bool:
    if not loc_str:
        return False
    loc_lower = loc_str.lower()
    india_keywords = [
        "india", "bengaluru", "bangalore", "hyderabad", "gurgaon", "gurugram",
        "noida", "delhi", "pune", "mumbai", "chennai", "remote"
    ]
    return any(k in loc_lower for k in india_keywords)


def is_relevant_role(title: str, description: str = "") -> bool:
    title_lower = title.lower()
    
    # Check exclusion
    for exc in EXCLUDE_KEYWORDS:
        if exc in title_lower and not any(inc in title_lower for inc in ["software", "sde", "developer", "ai", "ml"]):
            return False
            
    # Check inclusion
    return any(keyword in title_lower for keyword in INCLUDE_KEYWORDS)


def categorize_role(title: str, description: str = "") -> CategoryEnum:
    text = (title + " " + description).lower()
    
    ai_keywords = ["ai", "ml", "machine learning", "deep learning", "llm", "genai", "nlp", "computer vision", "data science", "research scientist"]
    systems_keywords = ["systems", "cloud", "devops", "sre", "infrastructure", "platform", "site reliability", "security", "network"]
    data_keywords = ["data engineer", "data analyst", "data infrastructure", "analytics", "bi developer"]
    
    if any(k in text for k in ai_keywords):
        return CategoryEnum.AI_ML
    elif any(k in text for k in systems_keywords):
        return CategoryEnum.SYSTEMS
    elif any(k in text for k in data_keywords):
        return CategoryEnum.DATA
    else:
        return CategoryEnum.SWE


def parse_conversion_potential(title: str, description: str = "") -> ConversionPotentialEnum:
    text = (title + " " + description).lower()
    
    ppo_indicators = [
        "ppo", "pre-placement offer", "6 month", "6-month", "6 months",
        "graduate engineer trainee", "get", "intern to fte", "conversion",
        "return offer", "internship + fte", "ppo/fte"
    ]
    
    if any(ind in text for ind in ppo_indicators):
        return ConversionPotentialEnum.HIGH_PPO
    
    if "intern" in text or "internship" in text or "trainee" in text:
        return ConversionPotentialEnum.STANDARD_INTERNSHIP
        
    return ConversionPotentialEnum.DIRECT_FTE


def parse_locations(raw_location: str) -> List[str]:
    if not raw_location:
        return ["Remote (India)"]
        
    loc_lower = raw_location.lower()
    matched = set()
    
    for key, std_name in INDIAN_LOCATION_MAP.items():
        if key in loc_lower:
            matched.add(std_name)
            
    if not matched:
        if "remote" in loc_lower or "india" in loc_lower or "anywhere" in loc_lower:
            matched.add("Remote (India)")
        else:
            matched.add("Bengaluru")  # Default hub fallback if unspecified India location
            
    return sorted(list(matched))


def parse_batch_eligibility(title: str, description: str = "") -> List[int]:
    text = f"{title} {description}"
    batches = set()
    
    # Direct 4-digit years matching 2025, 2026, 2027, 2028, 2029
    year_matches = re.findall(r'\b(202[5-9])\b', text)
    for y in year_matches:
        batches.add(int(y))
        
    # Apostrophe / short years like '26, '27, '28
    short_matches = re.findall(r"['’](\d{2})\b", text)
    for s in short_matches:
        full_year = 2000 + int(s)
        if 2025 <= full_year <= 2029:
            batches.add(full_year)
            
    if not batches:
        # Default batch heuristics based on role type
        if "intern" in title.lower():
            batches = {2026, 2027, 2028}
        else:
            batches = {2025, 2026}
            
    return sorted(list(batches))


def parse_stipend_or_ctc(title: str, description: str = "") -> str:
    text = f"{title} {description}"
    
    # INR LPA patterns e.g. 15-25 LPA, 20LPA, Rs 12-18 Lakhs
    lpa_match = re.search(r'(\d+(?:\.\d+)?\s*(?:-|to)?\s*\d*(?:\.\d+)?)\s*(?:LPA|Lakhs|Lakh|L/yr)', text, re.IGNORECASE)
    if lpa_match:
        return f"{lpa_match.group(1).strip()} LPA"
        
    # Monthly stipend patterns e.g. ₹60,000/mo, 50k-1L/month, 75k per month
    stipend_match = re.search(r'(?:₹|Rs\.?|INR)\s*(\d+(?:,\d+)*(?:\s*k|\s*000)?\s*(?:-|to)?\s*\d*(?:,\d+)*(?:\s*k|\s*000)?)\s*(?:\/|\s*per\s*)?(?:month|mo|pm)', text, re.IGNORECASE)
    if stipend_match:
        return f"₹{stipend_match.group(1).strip()}/mo"
        
    # Simple k/mo pattern e.g., 50k/mo, 80k-1.2k/mo
    k_match = re.search(r'(\d+k\s*(?:-|to)?\s*\d*k?)\s*\/\s*mo', text, re.IGNORECASE)
    if k_match:
        return f"₹{k_match.group(1).strip()}/mo"
        
    return "Disclosed"
