import re
import logging
from typing import List, Dict, Any
import httpx

from src.models.listing import Listing, SourceEnum, TierEnum, CategoryEnum
from src.parsers.normalizer import (
    is_relevant_role,
    categorize_role,
    parse_conversion_potential,
    parse_locations,
    parse_batch_eligibility,
    parse_stipend_or_ctc,
    is_india_location
)

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/124.0.0.0 Safari/537.36"
}


async def scrape_github_markdown_repo(client: httpx.AsyncClient, name: str, url: str) -> List[Listing]:
    listings = []
    try:
        resp = await client.get(url, headers=HEADERS, timeout=15.0)
        if resp.status_code != 200:
            return []
            
        content = resp.text
        lines = content.splitlines()
        
        # Regex to parse markdown table rows: | Company | Role | Location | Application Link | Date |
        table_row_pattern = re.compile(r'\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|')
        
        for line in lines:
            if not line.startswith("|") or "---" in line or "Company" in line:
                continue
                
            match = table_row_pattern.search(line)
            if not match:
                continue
                
            raw_company, raw_role, raw_loc, raw_link, raw_date = match.groups()
            
            company_clean = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', raw_company).strip()
            role_clean = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', raw_role).strip()
            
            url_match = re.search(r'href=["\'](.*?)["\']|\[.*?\]\((.*?)\)', raw_link)
            apply_url = ""
            if url_match:
                apply_url = url_match.group(1) or url_match.group(2) or ""
                
            if not apply_url or not apply_url.startswith("http"):
                continue
                
            # Filter for relevance
            if not is_relevant_role(role_clean):
                continue
                
            # STRICT LOCATION FILTER: Must be explicitly an Indian location or India Remote
            if not is_india_location(raw_loc):
                continue
                
            listing_id = Listing.generate_id(company_clean or "Tech Company", role_clean, apply_url)
            
            listings.append(Listing(
                id=listing_id,
                company=company_clean or "Tech Company",
                title=role_clean,
                category=categorize_role(role_clean),
                tier=TierEnum.STARTUP_AI_LAB if "AI" in role_clean else TierEnum.ENTERPRISE_SAAS,
                conversion_potential=parse_conversion_potential(role_clean),
                location=parse_locations(raw_loc),
                batch_eligibility=parse_batch_eligibility(role_clean),
                stipend_or_ctc=parse_stipend_or_ctc(role_clean),
                apply_url=apply_url,
                source=SourceEnum.GITHUB_REPOS,
                date_posted="2026-08-01",
                is_active=True
            ))
            
    except Exception as e:
        logger.debug(f"GitHub Repos scraper error for {name}: {e}")
        
    return listings


async def scrape_all_github_repos(config: Dict[str, Any]) -> List[Listing]:
    all_listings = []
    repos = config.get("github_repos", [])
    
    async with httpx.AsyncClient(follow_redirects=True, timeout=20.0) as client:
        for repo in repos:
            name = repo.get("name", "GitHub Repo")
            url = repo.get("url", "")
            if url:
                res = await scrape_github_markdown_repo(client, name, url)
                all_listings.extend(res)
                
    return all_listings
