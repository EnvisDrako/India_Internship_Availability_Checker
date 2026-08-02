import asyncio
import logging
from typing import List, Dict, Any
import httpx

from src.models.listing import Listing, SourceEnum, TierEnum
from src.parsers.normalizer import (
    is_relevant_role,
    categorize_role,
    parse_conversion_potential,
    parse_locations,
    parse_batch_eligibility,
    parse_stipend_or_ctc
)

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*"
}

SEMAPHORE = asyncio.Semaphore(10)


def is_india_location(loc_str: str) -> bool:
    if not loc_str:
        return False
    loc_lower = loc_str.lower()
    india_keywords = [
        "india", "bengaluru", "bangalore", "hyderabad", "gurgaon", "gurugram",
        "noida", "delhi", "pune", "mumbai", "chennai", "remote"
    ]
    return any(k in loc_lower for k in india_keywords)


async def scrape_greenhouse_company(client: httpx.AsyncClient, token: str, company_name: str, tier: str) -> List[Listing]:
    async with SEMAPHORE:
        url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
        listings = []
        try:
            resp = await client.get(url, headers=HEADERS, timeout=12.0)
            if resp.status_code != 200:
                return []
            data = resp.json()
            jobs = data.get("jobs", [])
            
            for j in jobs:
                title = j.get("title", "")
                loc_name = j.get("location", {}).get("name", "")
                apply_url = j.get("absolute_url", "")
                updated_at = j.get("updated_at", "")[:10] if j.get("updated_at") else "2026-08-01"
                
                if not is_relevant_role(title):
                    continue
                    
                if not is_india_location(loc_name):
                    continue
                    
                listing_id = Listing.generate_id(company_name, title, apply_url)
                
                listings.append(Listing(
                    id=listing_id,
                    company=company_name,
                    title=title,
                    category=categorize_role(title),
                    tier=TierEnum(tier),
                    conversion_potential=parse_conversion_potential(title),
                    location=parse_locations(loc_name),
                    batch_eligibility=parse_batch_eligibility(title),
                    stipend_or_ctc=parse_stipend_or_ctc(title),
                    apply_url=apply_url,
                    source=SourceEnum.GREENHOUSE,
                    date_posted=updated_at,
                    is_active=True
                ))
        except Exception as e:
            logger.debug(f"Greenhouse scrape error for {token}: {e}")
        return listings


async def scrape_lever_company(client: httpx.AsyncClient, token: str, company_name: str, tier: str) -> List[Listing]:
    async with SEMAPHORE:
        url = f"https://api.lever.co/v0/postings/{token}?mode=json"
        listings = []
        try:
            resp = await client.get(url, headers=HEADERS, timeout=12.0)
            if resp.status_code != 200:
                return []
            jobs = resp.json()
            if not isinstance(jobs, list):
                return []
                
            for j in jobs:
                title = j.get("text", "")
                categories = j.get("categories", {})
                loc_name = categories.get("location", "")
                apply_url = j.get("hostedUrl", "")
                created_at = j.get("createdAt")
                import datetime
                date_str = datetime.datetime.fromtimestamp(created_at / 1000.0).strftime("%Y-%m-%d") if created_at else "2026-08-01"
                
                if not is_relevant_role(title):
                    continue
                    
                if not is_india_location(loc_name):
                    continue
                    
                listing_id = Listing.generate_id(company_name, title, apply_url)
                
                listings.append(Listing(
                    id=listing_id,
                    company=company_name,
                    title=title,
                    category=categorize_role(title),
                    tier=TierEnum(tier),
                    conversion_potential=parse_conversion_potential(title),
                    location=parse_locations(loc_name),
                    batch_eligibility=parse_batch_eligibility(title),
                    stipend_or_ctc=parse_stipend_or_ctc(title),
                    apply_url=apply_url,
                    source=SourceEnum.LEVER,
                    date_posted=date_str,
                    is_active=True
                ))
        except Exception as e:
            logger.debug(f"Lever scrape error for {token}: {e}")
        return listings


async def scrape_ashby_company(client: httpx.AsyncClient, token: str, company_name: str, tier: str) -> List[Listing]:
    async with SEMAPHORE:
        url = f"https://api.ashbyhq.com/posting-api/job-board/{token}"
        listings = []
        try:
            resp = await client.get(url, headers=HEADERS, timeout=12.0)
            if resp.status_code != 200:
                return []
            data = resp.json()
            jobs = data.get("jobs", [])
            
            for j in jobs:
                title = j.get("title", "")
                loc_name = j.get("location", "")
                apply_url = j.get("jobUrl", "")
                
                if not is_relevant_role(title):
                    continue
                    
                if not is_india_location(loc_name):
                    continue
                    
                listing_id = Listing.generate_id(company_name, title, apply_url)
                
                listings.append(Listing(
                    id=listing_id,
                    company=company_name,
                    title=title,
                    category=categorize_role(title),
                    tier=TierEnum(tier),
                    conversion_potential=parse_conversion_potential(title),
                    location=parse_locations(loc_name),
                    batch_eligibility=parse_batch_eligibility(title),
                    stipend_or_ctc=parse_stipend_or_ctc(title),
                    apply_url=apply_url,
                    source=SourceEnum.ASHBY,
                    date_posted="2026-08-01",
                    is_active=True
                ))
        except Exception as e:
            logger.debug(f"Ashby scrape error for {token}: {e}")
        return listings


async def scrape_smartrecruiters_company(client: httpx.AsyncClient, token: str, company_name: str, tier: str) -> List[Listing]:
    async with SEMAPHORE:
        url = f"https://api.smartrecruiters.com/v1/companies/{token}/postings"
        listings = []
        try:
            resp = await client.get(url, headers=HEADERS, timeout=12.0)
            if resp.status_code != 200:
                return []
            data = resp.json()
            jobs = data.get("content", [])
            
            for j in jobs:
                title = j.get("name", "")
                loc_info = j.get("location", {})
                city = loc_info.get("city", "")
                country = loc_info.get("country", "")
                loc_name = f"{city}, {country}"
                job_id = j.get("id")
                apply_url = f"https://jobs.smartrecruiters.com/{token}/{job_id}"
                released_date = j.get("releasedDate", "")[:10] if j.get("releasedDate") else "2026-08-01"
                
                if not is_relevant_role(title):
                    continue
                    
                if not is_india_location(loc_name):
                    continue
                    
                listing_id = Listing.generate_id(company_name, title, apply_url)
                
                listings.append(Listing(
                    id=listing_id,
                    company=company_name,
                    title=title,
                    category=categorize_role(title),
                    tier=TierEnum(tier),
                    conversion_potential=parse_conversion_potential(title),
                    location=parse_locations(loc_name),
                    batch_eligibility=parse_batch_eligibility(title),
                    stipend_or_ctc=parse_stipend_or_ctc(title),
                    apply_url=apply_url,
                    source=SourceEnum.SMARTRECRUITERS,
                    date_posted=released_date,
                    is_active=True
                ))
        except Exception as e:
            logger.debug(f"SmartRecruiters scrape error for {token}: {e}")
        return listings


async def scrape_all_ats(config: Dict[str, Any]) -> List[Listing]:
    all_listings = []
    
    async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
        tasks = []
        
        # Greenhouse
        for comp in config.get("greenhouse", []):
            tasks.append(scrape_greenhouse_company(client, comp["token"], comp["name"], comp.get("tier", "Enterprise SaaS & DevTools")))
            
        # Lever
        for comp in config.get("lever", []):
            tasks.append(scrape_lever_company(client, comp["token"], comp["name"], comp.get("tier", "High-Paying Startup / AI Lab")))
            
        # Ashby
        for comp in config.get("ashby", []):
            tasks.append(scrape_ashby_company(client, comp["token"], comp["name"], comp.get("tier", "High-Paying Startup / AI Lab")))
            
        # SmartRecruiters
        for comp in config.get("smartrecruiters", []):
            tasks.append(scrape_smartrecruiters_company(client, comp["token"], comp["name"], comp.get("tier", "Global Capability Center (GCC)")))
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for res in results:
            if isinstance(res, list):
                all_listings.extend(res)
                
    return all_listings
