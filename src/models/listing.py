from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
import hashlib


class CategoryEnum(str, Enum):
    AI_ML = "AI/ML & GenAI"
    SWE = "Software Engineering (Backend/Fullstack)"
    SYSTEMS = "Systems & Infrastructure/DevOps"
    DATA = "Data & Analytics"


class TierEnum(str, Enum):
    STARTUP_AI_LAB = "High-Paying Startup / AI Lab"
    ENTERPRISE_SAAS = "Enterprise SaaS & DevTools"
    GCC = "Global Capability Center (GCC)"
    GLOBAL_REMOTE = "Global Remote"


class ConversionPotentialEnum(str, Enum):
    HIGH_PPO = "High (PPO/FTE Path)"
    STANDARD_INTERNSHIP = "Standard Internship"
    DIRECT_FTE = "Direct FTE / New Grad"


class SourceEnum(str, Enum):
    GREENHOUSE = "Greenhouse"
    LEVER = "Lever"
    ASHBY = "Ashby"
    SMARTRECRUITERS = "SmartRecruiters"
    GITHUB_REPOS = "GitHub_Repos"


class Listing(BaseModel):
    id: str
    company: str
    title: str
    category: CategoryEnum
    tier: TierEnum
    conversion_potential: ConversionPotentialEnum
    location: List[str] = Field(default_factory=list)
    batch_eligibility: List[int] = Field(default_factory=list)
    stipend_or_ctc: str = "Disclosed"
    apply_url: str
    source: SourceEnum
    date_posted: str
    is_active: bool = True

    @staticmethod
    def generate_id(company: str, title: str, apply_url: str) -> str:
        raw_str = f"{company.strip().lower()}:{title.strip().lower()}:{apply_url.strip().lower()}"
        return hashlib.md5(raw_str.encode('utf-8')).hexdigest()
