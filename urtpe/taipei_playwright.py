"""Playwright-based automation for Taipei platform case_id discovery.

Replaces fallback JSON with real-time automated search on gis.uro.taipei.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, Page, FrameLocator


@dataclass
class TaipeiSearchResult:
    """Result of Taipei platform case search."""
    case_ids: list[str]
    status: str  # "resolved", "unresolved", "error"
    error: str = ""
    view_id: str = ""  # National portal view_id for cross-reference


class TaipeiPlaywrightSearcher:
    """Playwright-based searcher for Taipei platform case_ids."""
    
    BASE_URL = "https://gis.uro.taipei/R_progress.aspx"
    DETAIL_URL_BASE = "https://gis.uro.taipei/r_progress_detail.aspx?case_id="
    
    def __init__(self, headless: bool = True, timeout: int = 30000):
        self.headless = headless
        self.timeout = timeout
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
    
    async def __aenter__(self):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self.headless)
        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        self._page = await self._browser.new_page()
        self._page.set_default_timeout(30000)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._browser:
            await self._browser.close()
        if hasattr(self, '_playwright'):
            await self._playwright.stop()
        return False
    
    async def search_case_ids(self, district: str, section: str, parcel: str, sub_parcel: str = "0") -> TaipeiSearchResult:
        """Search for case_ids using land core data.
        
        Uses the TOP form (enabled by default): section name + 母號 + 子號 text inputs.
        """
        try:
            await self._ensure_page()
            await self._page.goto("https://gis.uro.taipei/R_progress.aspx", wait_until="networkidle")
            await self._page.wait_for_timeout(3000)
            
            # Click the "依地段地號查詢" radio button (first radio button)
            radio_buttons = await self._page.query_selector_all('input[type="radio"]')
            if len(radio_buttons) < 1:
                return TaipeiSearchResult(
                    case_ids=[],
                    status="error",
                    error="Radio buttons not found"
                )
            
            # Click the first radio button (依地段地號查詢)
            await radio_buttons[0].click()
            
            # Wait for the land search form to load in #myframe div
            await self._page.wait_for_selector("#myframe #top_road_name", state="visible", timeout=15000)
            await self._page.wait_for_timeout(1000)
            
            # Fill the TOP form (enabled by default):
            # - top_road_name: 地段小段 (section, e.g. "河堤段四小段")
            # - top_lane: 母號 (parent parcel, e.g. "263")
            # - top_alley: 子號 (sub parcel, e.g. "19" or "0")
            await self._page.locator("#myframe #top_road_name").fill(section)
            await self._page.locator("#myframe #top_lane").fill(parcel)
            await self._page.locator("#myframe #top_alley").fill(sub_parcel)
            
            # Click the top search button
            await self._page.locator("#myframe #btn_search_top").click()
            
            # Wait for results (AJAX call to get_R_caseid)
            await self._page.wait_for_timeout(3000)
            await self._page.wait_for_load_state("networkidle")
            
            # Parse results
            case_ids = await self._extract_case_ids()
            
            if not case_ids:
                return TaipeiSearchResult(
                    case_ids=[],
                    status="unresolved",
                    error="No case_ids found in search results"
                )
            
            return TaipeiSearchResult(
                case_ids=case_ids,
                status="resolved"
            )
            
        except Exception as e:
            return TaipeiSearchResult(
                case_ids=[],
                status="error",
                error=str(e)
            )
    
    async def _ensure_page(self):
        if self._page is None:
            if self._context is None:
                self._context = await self._browser.new_context(
                    viewport={"width": 1280, "height": 720},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
            self._page = await self._context.new_page()
            self._page.set_default_timeout(30000)
    
    async def _extract_case_ids(self) -> list[str]:
        """Extract case_ids from search results table in #myframe div."""
        # Wait for results table in #myframe div
        await self._page.wait_for_selector("#myframe #cont .case-id, #myframe #cont .case-id a, #myframe .case-id", timeout=10000)
        
        # Extract case_ids from result links inside #myframe
        case_ids = await self._page.evaluate(r"""
            () => {
                const myframe = document.getElementById('myframe');
                if (!myframe) return [];
                const links = myframe.querySelectorAll('a[href*="case_id="]');
                return Array.from(links).map(a => {
                    const match = a.href.match(/case_id=(\d+)/);
                    return match ? match[1] : null;
                }).filter(Boolean);
            }
        """)
        
        return list(set(case_ids))  # Deduplicate
    
    async def get_case_detail(self, case_id: str) -> dict:
        """Fetch detailed milestone data for a case_id."""
        await self._ensure_page()
        await self._page.goto(f"https://gis.uro.taipei/r_progress_detail.aspx?case_id={case_id}", wait_until="networkidle")
        
        # Click "階段辦理過程" tab
        await self._page.click('button:has-text("階段辦理過程"), a:has-text("階段辦理過程")')
        await self._page.wait_for_timeout(1000)
        
        # Extract milestones from #data2
        milestones = await self._page.evaluate(r"""
            () => {
                const data2 = document.getElementById('data2');
                if (!data2) return {};
                const text = data2.innerText;
                const milestones = {};
                const lines = text.split('\n');
                for (const line of lines) {
                    const match = line.match(/^(.+?)\s+(\d{4}\/\d{2}\/\d{2}|\d{3}\.\d{2}\.\d{2})$/);
                    if (match) {
                        milestones[match[1].trim()] = match[2].trim();
                    }
                }
                return milestones;
            }
        """)
        
        return milestones
    
    async def search_by_land_core(self, land_core: str) -> TaipeiSearchResult:
        """Search by land_core string (e.g., '中正區河堤段四小段263-19地號等25筆')."""
        # Parse land_core to extract district, section, parcel, sub_parcel
        # Format: {district}{section}{parcel}地號等{count}筆
        match = re.match(r"(.+?區)(.+?段\d*小段)?(\d+(?:-\d+)?)地號等(\d+)筆", land_core)
        if not match:
            return TaipeiSearchResult(
                case_ids=[],
                status="unresolved",
                error=f"Could not parse land_core: {land_core}"
            )
        
        district = match.group(1)
        section = match.group(2) or ""
        parcel = match.group(3)
        count = match.group(4)
        
        # For sub-parcel, we'd need more parsing - use 0 for now
        return await self.search_case_ids(district, section, parcel, "0")


async def batch_search_all_projects(projects: list, cache_dir: Path) -> dict:
    """Search case_ids for all projects and save to cache."""
    results = {}
    
    async with TaipeiPlaywrightSearcher() as searcher:
        await searcher.start()
        
        # Load existing cache
        cache_file = cache_dir / "taipei_case_ids.json"
        if cache_file.exists():
            with open(cache_file, "r", encoding="utf-8") as f:
                cache = json.load(f)
        else:
            cache = {}
        
        for i, project in enumerate(projects):
            # Build land_core from anchor record
            anchor = next(r for r in project.members if r.recno == project.anchor_recno)
            land_core = build_land_core_key(anchor)
            
            # Check cache first
            if land_core in cache:
                results[project.project_id] = cache[land_core]
                continue
            
            print(f"[{i+1}/{len(projects)}] Searching: {project.project_id}")
            result = await searcher.search_by_land_core(land_core)
            
            # Cache result
            cache[land_core] = {
                "view_id": result.view_id,
                "case_ids": result.case_ids,
                "status": result.status,
                "error": result.error
            }
            
            # Save cache periodically
            if i % 10 == 0:
                with open(cache_dir / "taipei_case_ids.json", "w", encoding="utf-8") as f:
                    json.dump(cache, f, ensure_ascii=False, indent=2)
            
            # Be polite
            await asyncio.sleep(1)
        
        # Final save
        with open(cache_dir / "taipei_case_ids.json", "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        
        return cache


# Sync wrapper for CLI integration
def run_taipei_batch_search(projects: list, cache_dir: Path) -> dict:
    """Sync wrapper for CLI integration."""
    return asyncio.run(batch_search_all_projects(projects, Path(cache_dir)))