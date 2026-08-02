import sys
import os
import yaml
import asyncio
import logging
from typing import Dict, Any

from src.scrapers.ats_engine import scrape_all_ats
from src.scrapers.github_repos import scrape_all_github_repos
from src.generator.db_manager import (
    load_master_listings,
    merge_and_deduplicate,
    verify_link_health_smart,
    save_master_listings
)
from src.generator.markdown_gen import generate_dashboards

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("main")


def load_config() -> Dict[str, Any]:
    config_path = os.path.join("config", "companies.yaml")
    if not os.path.exists(config_path):
        logger.error(f"Config file not found at {config_path}")
        return {}
        
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


async def run_scrape_all():
    logger.info("=== Starting Autonomous Scraping & Smart Expiration Pipeline ===")
    
    # 1. Load config
    config = load_config()
    logger.info("Loaded config registry with ATS and GitHub feeds.")
    
    # 2. Load existing master records
    existing_listings = load_master_listings()
    logger.info(f"Loaded {len(existing_listings)} existing active master listings.")
    
    # 3. Async Scraping
    logger.info("Scraping Greenhouse, Lever, Ashby, and SmartRecruiters ATS endpoints...")
    ats_listings = await scrape_all_ats(config)
    logger.info(f"Scraped {len(ats_listings)} roles from ATS endpoints.")
    
    logger.info("Scraping open-source GitHub repository feeds...")
    github_listings = await scrape_all_github_repos(config)
    logger.info(f"Scraped {len(github_listings)} roles from GitHub repositories.")
    
    all_newly_scraped = ats_listings + github_listings
    logger.info(f"Total newly scraped raw roles: {len(all_newly_scraped)}")
    
    # 4. Merge and Deduplicate
    merged_listings = merge_and_deduplicate(existing_listings, all_newly_scraped)
    
    # 5. Smart Adaptive Link Health Check (Fast & Resource-Efficient)
    logger.info("Running Smart Link Health Check & Partitioning expired items...")
    retained_active, expired_archive = await verify_link_health_smart(merged_listings)
    
    # 6. Save updated active master JSON
    save_master_listings(retained_active)
    
    # 7. Re-generate Markdown Dashboards
    generate_dashboards(retained_active)
    
    logger.info(f"=== Pipeline Finished Successfully! Total Active Listings: {len(retained_active)} | Total Expired Archived: {len(expired_archive)} ===")


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("scrape-all", "health-check", "build-docs"):
        print("Usage: python -m src.main [scrape-all | health-check | build-docs]")
        sys.exit(1)
        
    command = sys.argv[1]
    
    if command == "scrape-all":
        asyncio.run(run_scrape_all())
    elif command == "build-docs":
        listings = load_master_listings()
        generate_dashboards(listings)
        print("Rebuilt markdown dashboards.")
    elif command == "health-check":
        listings = load_master_listings()
        retained, expired = asyncio.run(verify_link_health_smart(listings))
        save_master_listings(retained)
        print(f"Completed smart health check. Active: {len(retained)} | Expired: {len(expired)}")


if __name__ == "__main__":
    main()
