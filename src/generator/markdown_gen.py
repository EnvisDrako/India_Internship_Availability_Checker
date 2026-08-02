import os
import logging
from typing import List
from datetime import datetime
from src.models.listing import Listing, CategoryEnum

logger = logging.getLogger(__name__)


def generate_markdown_tables(listings: List[Listing]) -> str:
    if not listings:
        return "| Company | Role | Category | Location | Batches | Compensation | Apply | Date |\n|---|---|---|---|---|---|---|---|\n| No active roles found | - | - | - | - | - | - | - |\n"
        
    lines = [
        "| Company | Role Title | Category | Location | Eligible Batches | Stipend / CTC | Conversion | Apply Link |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
    ]
    
    for item in listings:
        company_badge = f"**{item.company}**"
        title = item.title
        category = item.category.value
        locs = ", ".join(item.location) if item.location else "India"
        batches = ", ".join(str(b) for b in item.batch_eligibility) if item.batch_eligibility else "2026/2027"
        stipend = item.stipend_or_ctc
        conversion = "🔥 **High PPO**" if item.conversion_potential == "High (PPO/FTE Path)" else ("✨ Direct FTE" if item.conversion_potential == "Direct FTE / New Grad" else "🎓 Internship")
        apply_btn = f"[Apply Now 🚀]({item.apply_url})"
        
        lines.append(f"| {company_badge} | {title} | {category} | {locs} | `{batches}` | {stipend} | {conversion} | {apply_btn} |")
        
    return "\n".join(lines)


def generate_dashboards(listings: List[Listing]) -> None:
    active_listings = [item for item in listings if item.is_active]
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")
    
    high_ppo = [item for item in active_listings if item.conversion_potential == "High (PPO/FTE Path)"]
    ai_ml_roles = [item for item in active_listings if item.category == CategoryEnum.AI_ML]
    swe_roles = [item for item in active_listings if item.category in (CategoryEnum.SWE, CategoryEnum.SYSTEMS)]
    
    # Internship filter
    internship_roles = [
        item for item in active_listings 
        if "intern" in item.title.lower() or "trainee" in item.title.lower() or item.conversion_potential in ("Standard Internship", "High (PPO/FTE Path)")
    ]
    
    # 1. Main README.md
    readme_content = f"""# 🚀 Automated India AI & SWE Internship/Off-Campus Tracker

> **PPO & High-Conversion Focus** | Auto-scraped & normalized every 6 hours via GitHub Actions  
> **Live Web Dashboard:** [https://india-internship-availability-checker.vercel.app](index.html) *(Updated: {now_str})*

---

## 📊 Live Overview & Quick Metrics
- ⚡ **Total Active Roles (India):** `{len(active_listings)}`
- 🎓 **Indian Internships & Trainee Roles:** `{len(internship_roles)}`
- 🔥 **High PPO / FTE Conversion Roles:** `{len(high_ppo)}`
- 🤖 **AI / ML & GenAI Opportunities:** `{len(ai_ml_roles)}`
- 💻 **Software & Systems Engineering Roles:** `{len(swe_roles)}`

---

## 🎓 Featured Indian Internships & PPOs

{generate_markdown_tables(internship_roles[:25])}

---

## 📂 Quick Navigation Categories
- 🎓 **[View All Indian Internships](INTERNSHIPS_INDIA.md)** (`{len(internship_roles)}` open)
- 🤖 **[View All AI & ML Roles](AI_AND_ML_ROLES.md)** (`{len(ai_ml_roles)}` open)
- 💻 **[View All SDE & Systems Roles](SDE_AND_SYSTEMS.md)** (`{len(swe_roles)}` open)

---

## 🏛️ Top Employers & Tiers Tracked
- **GenAI Startups & AI Labs:** Sarvam AI, Krutrim, Cohesity, Rubrik, Databricks, Nvidia, AMD, Postman.
- **High-Paying Product Giants & Quant Labs:** Atlassian, Arcesium, Media.net, DE Shaw, Tower Research, Graviton, Razorpay, CRED, Swiggy, Zomato, Meesho, Sprinklr, BrowserStack, Hasura.
- **Global Tech GCCs:** Target India, Lowe's, Walmart Global Tech, Fidelity, BNY Mellon, Barclays, Wells Fargo, Mercedes-Benz, Bosch, Valeo.

---

## ⚙️ How It Works (Fully Autonomous Pipeline)
1. **Scrapes Public ATS APIs:** Queries Greenhouse, Lever, Ashby, and SmartRecruiters for 120+ Indian Tech Employers & Quant teams.
2. **Open-Source Secondary Feeds:** Ingests raw listings from specialized Indian off-campus and internship repos.
3. **Strict Location Filtering:** Enforces zero US/Global location leakage — only retains verified Indian tech hubs and Remote (India) roles.
4. **Auto-Deploy:** Rebuilds Markdown dashboards and deploys the Vercel & GitHub Pages web app.

---
*Disclaimer: All job listings redirect directly to the official employer career portals.*
"""

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)

    # 2. INTERNSHIPS_INDIA.md
    internship_content = f"""# 🎓 Indian Internships & PPO Off-Campus Roles

> Auto-generated tracker for Software Engineering and AI/ML Internships, Co-Ops, and Trainee roles in India.  
> **Updated:** `{now_str}`

{generate_markdown_tables(internship_roles)}
"""
    with open("INTERNSHIPS_INDIA.md", "w", encoding="utf-8") as f:
        f.write(internship_content)

    # 3. AI_AND_ML_ROLES.md
    ai_content = f"""# 🤖 AI & Machine Learning Off-Campus & Internship Roles (India)

> Auto-generated tracker for GenAI, DeepTech, Machine Learning, Data Science, and Computer Vision opportunities.  
> **Updated:** `{now_str}`

{generate_markdown_tables(ai_ml_roles)}
"""
    with open("AI_AND_ML_ROLES.md", "w", encoding="utf-8") as f:
        f.write(ai_content)

    # 4. SDE_AND_SYSTEMS.md
    swe_content = f"""# 💻 Software & Systems Engineering Off-Campus & Internship Roles (India)

> Auto-generated tracker for Core SDE (Backend/Fullstack), Infrastructure, DevOps, and Cloud roles.  
> **Updated:** `{now_str}`

{generate_markdown_tables(swe_roles)}
"""
    with open("SDE_AND_SYSTEMS.md", "w", encoding="utf-8") as f:
        f.write(swe_content)

    logger.info("Successfully generated README.md, INTERNSHIPS_INDIA.md, AI_AND_ML_ROLES.md, and SDE_AND_SYSTEMS.md")
