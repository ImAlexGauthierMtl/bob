"""Bright Data enrichment service — LinkedIn scraping via API.

Calls Bright Data's Web Scraping API to extract:
- Company data: followers, employees, specialties, updates, logo
- Profile data: about, headline, experience, education, skills, connections, posts
"""

import os
import httpx
import structlog
from typing import Optional

logger = structlog.get_logger(__name__)

BRIGHT_DATA_API_TOKEN = os.getenv("BRIGHT_DATA_API_TOKEN", "")
BRIGHT_DATA_BASE_URL = os.getenv("BRIGHT_DATA_BASE_URL", "https://api.brightdata.com/datasets/v3")


class BrightDataService:
    """HTTP client for Bright Data LinkedIn scraping."""

    def __init__(self) -> None:
        self.token = BRIGHT_DATA_API_TOKEN
        self.base_url = BRIGHT_DATA_BASE_URL

    async def scrape_linkedin_company(self, linkedin_url: str) -> dict:
        """Scrape LinkedIn company page for org enrichment.

        Returns dict with: followers, employees_on_linkedin, specialties,
        company_updates, logo_url, founded_year, etc.
        """
        if not self.token:
            logger.warning("bright_data_no_token", action="scrape_linkedin_company")
            return {}

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/trigger",
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "dataset_id": "gd_l1viktl72bvl7bjuj0",  # LinkedIn Company dataset
                        "url": linkedin_url,
                        "format": "json",
                    },
                )
                response.raise_for_status()
                data = response.json()

                logger.info(
                    "bright_data_company_scraped",
                    linkedin_url=linkedin_url,
                    has_data=bool(data),
                )
                return self._normalize_company_data(data)

        except Exception as e:
            logger.error(
                "bright_data_company_error",
                linkedin_url=linkedin_url,
                error=str(e),
            )
            return {}

    async def scrape_linkedin_profile(self, linkedin_url: str) -> dict:
        """Scrape LinkedIn profile page for contact enrichment.

        Returns dict with: about, headline, work_experience, education,
        skills, connections, posts, certifications, profile_picture_url.
        """
        if not self.token:
            logger.warning("bright_data_no_token", action="scrape_linkedin_profile")
            return {}

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/trigger",
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "dataset_id": "gd_l1viktl72bvl7bjuj1",  # LinkedIn Profile dataset
                        "url": linkedin_url,
                        "format": "json",
                    },
                )
                response.raise_for_status()
                data = response.json()

                logger.info(
                    "bright_data_profile_scraped",
                    linkedin_url=linkedin_url,
                    has_data=bool(data),
                )
                return self._normalize_profile_data(data)

        except Exception as e:
            logger.error(
                "bright_data_profile_error",
                linkedin_url=linkedin_url,
                error=str(e),
            )
            return {}

    def _normalize_company_data(self, raw: dict) -> dict:
        """Normalize Bright Data company response to our schema."""
        if not raw:
            return {}

        # Handle both single result and array
        data = raw[0] if isinstance(raw, list) and raw else raw

        return {
            "followers": data.get("followers") or data.get("follower_count"),
            "employees_on_linkedin": data.get("employees_on_linkedin") or data.get("company_size"),
            "specialties": data.get("specialties", []),
            "logo_url": data.get("logo") or data.get("logo_url"),
            "founded_year": data.get("founded") or data.get("founded_year"),
            "company_type": data.get("type") or data.get("company_type"),
            "headquarters": data.get("headquarters"),
            "about": data.get("about") or data.get("description"),
            "company_updates": data.get("updates", [])[:5],  # Keep last 5
            "job_postings": data.get("jobs", [])[:10],  # Keep last 10
        }

    def _normalize_profile_data(self, raw: dict) -> dict:
        """Normalize Bright Data profile response to our schema."""
        if not raw:
            return {}

        # Handle both single result and array
        data = raw[0] if isinstance(raw, list) and raw else raw

        return {
            "headline": data.get("headline") or data.get("title"),
            "about": data.get("about") or data.get("summary"),
            "profile_picture_url": data.get("profile_picture") or data.get("photo_url"),
            "work_experience": data.get("experience", []),
            "education": data.get("education", []),
            "skills": data.get("skills", []),
            "connections": data.get("connections") or data.get("connection_count"),
            "certifications": data.get("certifications", []),
            "posts": data.get("posts", [])[:5],  # Keep last 5
            "followers": data.get("followers", []),
            "languages": data.get("languages", []),
            "location": data.get("location"),
        }
