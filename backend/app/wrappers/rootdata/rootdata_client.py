"""Rootdata client for scraping project information.

This module uses Playwright to scrape project data from Rootdata.com,
which uses Nuxt.js with server-side rendering.
"""

import json
import logging
from typing import Optional
from urllib.parse import urljoin

from app.wrappers.rootdata.models import ProjectInfo, TokenInfo, Whitepaper

logger = logging.getLogger(__name__)

# Rootdata URLs
ROOTDATA_BASE = "https://www.rootdata.com"
ROOTDATA_PROJECTS = f"{ROOTDATA_BASE}/projects"
ROOTDATA_PROJECT_DETAIL = f"{ROOTDATA_BASE}/project_detail"


class RootdataClient:
    """Client for scraping Rootdata project information."""

    def __init__(self, headless: bool = True):
        """Initialize the client.

        Args:
            headless: Whether to run browser in headless mode
        """
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self.headless = headless

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def start(self):
        """Start the browser."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise ImportError(
                "Playwright is required. Install with: pip install playwright && playwright install chromium"
            )

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self.headless)
        self._context = await self._browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        self._page = await self._context.new_page()
        logger.info("Rootdata client started")

    async def close(self):
        """Close the browser."""
        if self._page:
            await self._page.close()
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Rootdata client closed")

    async def _get_nuxt_data(self) -> Optional[dict]:
        """Extract __NUXT__ data from the page.

        Rootdata uses Nuxt.js which exposes data in window.__NUXT__

        Returns:
            Nuxt data dict or None
        """
        try:
            nuxt_data = await self._page.evaluate("""() => {
                if (window.__NUXT__) {
                    return window.__NUXT__;
                }
                return null;
            }""")
            return nuxt_data
        except Exception as e:
            logger.debug(f"Error extracting Nuxt data: {e}")
            return None

    async def get_project_list(self, limit: int = 50) -> list[dict]:
        """Get list of projects from Rootdata.

        Args:
            limit: Maximum number of projects to fetch

        Returns:
            List of project summaries with id, name, url
        """
        logger.info(f"Fetching project list (limit: {limit})")

        await self._page.goto(ROOTDATA_PROJECTS, wait_until="networkidle", timeout=60000)
        await self._page.wait_for_timeout(5000)  # Wait for Nuxt hydration

        # Get Nuxt data
        nuxt_data = await self._get_nuxt_data()

        projects = []

        if nuxt_data and "data" in nuxt_data:
            # Navigate to the project list in Nuxt data structure
            # Structure: data[0].list
            data_list = nuxt_data.get("data", [])
            if data_list and len(data_list) > 0:
                project_list = data_list[0].get("list", [])
                logger.info(f"Found {len(project_list)} projects in Nuxt data")

                for item in project_list[:limit]:
                    try:
                        project_id = str(item.get("id", ""))
                        name_data = item.get("name", {})
                        name = name_data.get("en_value") or name_data.get("cn_value") or "Unknown"

                        projects.append({
                            "id": project_id,
                            "name": name,
                            "url": urljoin(ROOTDATA_BASE, f"/project_detail/{project_id}"),
                            "raw_data": item,  # Store raw data for later use
                        })
                    except Exception as e:
                        logger.debug(f"Error parsing project item: {e}")
                        continue

        logger.info(f"Extracted {len(projects)} projects from page")
        return projects

    async def get_project_detail(self, project_id: str, raw_data: Optional[dict] = None) -> Optional[ProjectInfo]:
        """Get detailed information for a project.

        Args:
            project_id: Rootdata project ID
            raw_data: Optional raw data from project list (saves an extra request)

        Returns:
            ProjectInfo or None if not found
        """
        # If we have raw data from the list, use it directly
        if raw_data:
            return self._parse_project_data(project_id, raw_data)

        # Otherwise, fetch from detail page
        url = f"{ROOTDATA_PROJECT_DETAIL}/{project_id}"
        logger.info(f"Fetching project detail: {url}")

        try:
            await self._page.goto(url, wait_until="networkidle")
            await self._page.wait_for_timeout(2000)

            nuxt_data = await self._get_nuxt_data()
            if nuxt_data and "data" in nuxt_data:
                data_list = nuxt_data.get("data", [])
                if data_list and len(data_list) > 0:
                    # Project detail is usually in data[0]
                    project_data = data_list[0]
                    if isinstance(project_data, dict):
                        return self._parse_project_data(project_id, project_data)

        except Exception as e:
            logger.error(f"Error fetching project {project_id}: {e}")

        return None

    def _parse_project_data(self, project_id: str, data: dict) -> Optional[ProjectInfo]:
        """Parse project data from Rootdata format.

        Args:
            project_id: Project ID
            data: Raw project data

        Returns:
            ProjectInfo object
        """
        try:
            # Extract name (multi-language)
            name_data = data.get("name", {})
            name = name_data.get("en_value") or name_data.get("cn_value") or "Unknown"
            name_cn = name_data.get("cn_value")

            # Extract description
            intd_data = data.get("intd", {})
            description = intd_data.get("en_value") or intd_data.get("cn_value") or ""

            # Extract brief intro
            brief_data = data.get("briefIntd", {})
            brief = brief_data.get("en_value") or brief_data.get("cn_value") or ""

            # Combine description and brief
            full_description = description
            if brief and brief != description:
                full_description = f"{brief}\n\n{description}" if description else brief

            # Extract tags
            tags = []
            categories = []
            tag_list = data.get("tagList", [])
            for tag_item in tag_list:
                try:
                    tag_name_str = tag_item.get("name", "{}")
                    if isinstance(tag_name_str, str):
                        tag_name_data = json.loads(tag_name_str)
                    else:
                        tag_name_data = tag_name_str
                    tag_name = tag_name_data.get("en_value") or tag_name_data.get("cn_value")
                    if tag_name:
                        tags.append(tag_name)
                        categories.append(tag_name)
                except Exception:
                    continue

            # Extract token info
            token = None
            lssuing_code = data.get("lssuingCode")
            if lssuing_code:
                token = TokenInfo(symbol=lssuing_code.upper(), name=lssuing_code)

            # Extract chains (public chains)
            chains = []
            pub_chains = data.get("pubChains", [])
            if isinstance(pub_chains, list):
                for chain in pub_chains:
                    if isinstance(chain, dict):
                        chain_name = chain.get("name") or chain.get("en_value") or chain.get("cn_value")
                        if chain_name:
                            chains.append(str(chain_name))

            return ProjectInfo(
                rootdata_id=project_id,
                name=name,
                name_en=name,
                description=full_description,
                introduction=full_description,  # Use full description as introduction
                categories=categories,
                chains=chains,
                tags=tags,
                token=token,
                logo_url=data.get("logoImg"),
                website_url=None,  # Can be fetched from detail page if needed
                source_url=urljoin(ROOTDATA_BASE, f"/project_detail/{project_id}"),
            )

        except Exception as e:
            logger.error(f"Error parsing project data: {e}")
            return None

    async def scrape_projects(self, limit: int = 20) -> list[ProjectInfo]:
        """Scrape multiple projects from Rootdata.

        Args:
            limit: Maximum number of projects to scrape

        Returns:
            List of ProjectInfo objects
        """
        logger.info(f"Starting to scrape {limit} projects from Rootdata")

        # Get project list with raw data
        projects_list = await self.get_project_list(limit=limit)
        results = []

        for i, project in enumerate(projects_list):
            logger.info(f"Parsing project {i + 1}/{limit}: {project['name']}")

            # Parse from raw data (no extra request needed)
            detail = self._parse_project_data(project["id"], project.get("raw_data", {}))
            if detail:
                results.append(detail)

        logger.info(f"Successfully scraped {len(results)} projects")
        return results


# Convenience function for quick usage
async def scrape_rootdata_projects(limit: int = 20) -> list[ProjectInfo]:
    """Convenience function to scrape projects from Rootdata.

    Args:
        limit: Maximum number of projects to scrape

    Returns:
        List of ProjectInfo objects
    """
    async with RootdataClient() as client:
        return await client.scrape_projects(limit=limit)
