import json
import os
import asyncio
import logging
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
import httpx

from src.models.listing import Listing

logger = logging.getLogger(__name__)

DATA_FILE_PATH = os.path.join("data", "master_listings.json")
EXPIRED_FILE_PATH = os.path.join("data", "expired_listings.json")


def load_master_listings() -> List[Listing]:
    if not os.path.exists(DATA_FILE_PATH):
        return []
        
    try:
        with open(DATA_FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [Listing(**item) for item in data]
    except Exception as e:
        logger.error(f"Error loading master listings: {e}")
        return []


def load_expired_listings() -> List[Dict]:
    if not os.path.exists(EXPIRED_FILE_PATH):
        return []
        
    try:
        with open(EXPIRED_FILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading expired listings: {e}")
        return []


def save_master_listings(listings: List[Listing]) -> None:
    os.makedirs("data", exist_ok=True)
    
    # Filter only active listings for master database
    active_listings = [item for item in listings if item.is_active]
    
    def sort_key(item: Listing):
        prio = 0
        if item.conversion_potential == "High (PPO/FTE Path)":
            prio = 2
        elif item.conversion_potential == "Direct FTE / New Grad":
            prio = 1
        return (prio, item.date_posted)

    listings_sorted = sorted(active_listings, key=sort_key, reverse=True)
    dict_data = [item.model_dump() for item in listings_sorted]
    
    with open(DATA_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(dict_data, f, indent=2, ensure_ascii=False)
        
    logger.info(f"Saved {len(listings_sorted)} active listings to {DATA_FILE_PATH}")


def save_expired_listings(expired_items: List[Dict]) -> None:
    os.makedirs("data", exist_ok=True)
    with open(EXPIRED_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(expired_items, f, indent=2, ensure_ascii=False)
    logger.info(f"Updated expired listings archive ({len(expired_items)} total record(s)).")


def merge_and_deduplicate(existing: List[Listing], newly_scraped: List[Listing]) -> List[Listing]:
    listing_map: Dict[str, Listing] = {item.id: item for item in existing}
    
    new_count = 0
    updated_count = 0
    
    for item in newly_scraped:
        if item.id in listing_map:
            existing_item = listing_map[item.id]
            existing_item.is_active = True
            existing_item.apply_url = item.apply_url
            if item.stipend_or_ctc != "Disclosed":
                existing_item.stipend_or_ctc = item.stipend_or_ctc
            updated_count += 1
        else:
            listing_map[item.id] = item
            new_count += 1
            
    logger.info(f"Deduplication complete. New: {new_count}, Updated: {updated_count}, Active Master: {len(listing_map)}")
    return list(listing_map.values())


async def verify_link_health_smart(listings: List[Listing]) -> Tuple[List[Listing], List[Dict]]:
    """
    Adaptive Smart Checking Algorithm:
    - Skips newly scraped roles (< 48 hrs old) to save network calls.
    - Uses fast high-concurrency HEAD requests (25 workers, 3.0s timeout).
    - Automatically partitions expired roles into data/expired_listings.json.
    """
    today_str = datetime.now().strftime("%Y-%m-%d")
    now_date = datetime.now().date()
    
    expired_archive = load_expired_listings()
    expired_ids = {item["id"] for item in expired_archive}
    
    # Select listings eligible for checking (Active and > 2 days old)
    candidates_to_check = []
    active_retained = []
    
    for item in listings:
        if not item.is_active:
            continue
            
        try:
            posted_dt = datetime.strptime(item.date_posted, "%Y-%m-%d").date()
            age_days = (now_date - posted_dt).days
        except Exception:
            age_days = 5
            
        # Fresh roles (< 2 days old) are skipped from network checks (assumed active)
        if age_days < 2:
            active_retained.append(item)
        else:
            candidates_to_check.append(item)
            
    logger.info(f"Smart Check: Skipping {len(active_retained)} fresh listings (< 48h old). Verifying {len(candidates_to_check)} candidate links...")

    semaphore = asyncio.Semaphore(25)
    newly_expired = []
    
    async def check_url(client: httpx.AsyncClient, item: Listing):
        async with semaphore:
            is_valid = True
            try:
                resp = await client.head(item.apply_url, timeout=3.0, follow_redirects=True)
                if resp.status_code in (404, 410):
                    is_valid = False
            except Exception:
                try:
                    # Light GET retry
                    resp = await client.get(item.apply_url, timeout=3.0, follow_redirects=True)
                    if resp.status_code in (404, 410):
                        is_valid = False
                except Exception:
                    pass  # Retain active if intermittent network issue
                    
            if is_valid:
                active_retained.append(item)
            else:
                item.is_active = False
                if item.id not in expired_ids:
                    expired_record = item.model_dump()
                    expired_record["expired_at"] = today_str
                    expired_archive.append(expired_record)
                    expired_ids.add(item.id)
                    newly_expired.append(item)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    async with httpx.AsyncClient(headers=headers) as client:
        tasks = [check_url(client, item) for item in candidates_to_check]
        await asyncio.gather(*tasks, return_exceptions=True)

    if newly_expired:
        save_expired_listings(expired_archive)
        logger.info(f"Moved {len(newly_expired)} expired listings to archive.")

    return active_retained, expired_archive


# Alias for backwards compatibility
async def verify_link_health(listings: List[Listing], max_check: int = 50) -> List[Listing]:
    retained, _ = await verify_link_health_smart(listings)
    return retained
