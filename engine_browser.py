"""
Web Scraper 4.0 — Browser Engine (Playwright)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Headless Chromium engine for JavaScript-rendered sites and anti-bot bypass.
Upgraded with Pydantic validation, AI extraction, and content-hash dedup.
"""
import asyncio
from playwright.async_api import async_playwright
from urllib.parse import urlparse, urljoin, urldefrag
import random
import os
import logging
import httpx
import time
from datetime import datetime
from engine_fast import (
    PageDataExtractor, should_skip, get_domain, url_to_filename,
    is_valid_url, make_safe_filename, content_hash, strip_boilerplate
)
from schemas import validate_batch
from ai_extractor import AIExtractor, AIExtractorDisabled
from extractor_ecommerce import EcommerceExtractor

logger = logging.getLogger("WebScraper3.0")


class BrowserEngine:
    """Headless browser engine using Playwright. Handles JS-rendered sites."""

    def __init__(self, config):
        self.start_url = config['url']
        self.domain = urlparse(self.start_url).netloc
        self.max_pages = config['max_pages']
        self.max_depth = config['depth']
        self.proxy = config.get('proxy')
        self.config = config
        self.save_html = config.get('save_html', False)
        self.html_dir = config.get('html_dir', '')

        self.visited = set()
        self.content_hashes = set()
        self.pages_scraped = 0
        self.pages_failed = 0
        self.all_data = {}
        self.crawl_log = []
        self.start_time = None

        # AI extractor
        if config.get('use_ai_extraction', False):
            self.ai = AIExtractor(
                model=config.get('ai_model', 'llama3.2'),
                prompt=config.get('ai_prompt', ''),
            )
        else:
            self.ai = AIExtractorDisabled()

        # Incremental exporter callback
        self.on_batch_ready = None
        self.batch_size = config.get('batch_size', 100)

    @property
    def stats(self) -> dict:
        elapsed = time.time() - self.start_time if self.start_time else 0
        rate = self.pages_scraped / elapsed if elapsed > 0 else 0
        return {
            "queued": self.queue.qsize() if hasattr(self, 'queue') else 0,
            "processed": self.pages_scraped,
            "failed": self.pages_failed,
            "rate": round(rate, 2),
            "elapsed": round(elapsed, 1),
        }

    def normalize(self, url):
        return urldefrag(url)[0].rstrip("/")

    def _merge_page_data(self, page_data):
        for key, value in page_data.items():
            if key not in self.all_data:
                self.all_data[key] = []
            if isinstance(value, list):
                self.all_data[key].extend(value)
            elif isinstance(value, dict):
                self.all_data[key].append(value)

    def _validate_page_data(self, page_data: dict) -> dict:
        validated = {}
        for key, value in page_data.items():
            records = value if isinstance(value, list) else [value]
            valid_records = validate_batch(key, records)
            if valid_records:
                validated[key] = valid_records
        return validated

    async def worker(self, context):
        page = await context.new_page()
        # Stealth: hide webdriver flag
        await page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        idle_cycles = 0
        while not self._shutdown:
            if self.queue.empty():
                if self._active_workers == 0:
                    idle_cycles += 1
                    if idle_cycles >= 6:
                        break
                else:
                    idle_cycles = 0
                await asyncio.sleep(0.5)
                continue

            idle_cycles = 0
            try:
                url, depth = self.queue.get_nowait()
            except asyncio.QueueEmpty:
                continue

            if self.pages_scraped >= self.max_pages:
                self._shutdown = True
                self.queue.task_done()
                break

            norm_url = self.normalize(url)
            if norm_url in self.visited or depth > self.max_depth:
                self.queue.task_done()
                continue

            self.visited.add(norm_url)
            self._active_workers += 1
            self.pages_scraped += 1
            logger.info(f"  [{self.pages_scraped}/{self.max_pages}] Depth={depth} | {url}")

            try:
                response = await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                # Wait for JS frameworks (React/Vue/Angular) to render
                await page.wait_for_timeout(2500)

                html = await page.content()
                status = response.status if response else 200

                # Content-hash dedup
                c_hash = content_hash(html)
                if c_hash in self.content_hashes:
                    logger.info(f"  ♻️ Duplicate content skipped: {url}")
                    self._active_workers -= 1
                    self.queue.task_done()
                    continue
                self.content_hashes.add(c_hash)

                self.crawl_log.append({
                    "url": url,
                    "status_code": status,
                    "content_length": len(html),
                    "depth": depth,
                    "timestamp": datetime.now().isoformat(),
                    "content_hash": c_hash,
                })

                # Save raw HTML if enabled
                if self.save_html and self.html_dir:
                    html_path = os.path.join(self.html_dir, url_to_filename(url))
                    try:
                        with open(html_path, 'w', encoding='utf-8') as f:
                            f.write(html)
                    except Exception as e:
                        logger.warning(f"  Could not save HTML for {url}: {e}")

                # Extract data
                extractor = PageDataExtractor(url, html, self.config)
                page_data = extractor.extract_all()

                # AI extraction
                if self.ai.is_available():
                    clean_page_text = extractor.get_clean_text_for_ai()
                    ai_result = self.ai.extract(url, clean_page_text)
                    if ai_result:
                        page_data['ai_insights'] = [ai_result]

                # Pydantic validation
                page_data = self._validate_page_data(page_data)

                # Image downloading
                if self.config.get("download_images") and self.config.get("img_dir") and "images" in page_data:
                    for img in page_data["images"]:
                        img_url = img.get("image_src", "")
                        if is_valid_url(img_url):
                            try:
                                async with httpx.AsyncClient(timeout=10) as client:
                                    img_res = await client.get(img_url)
                                    if img_res.status_code == 200:
                                        img_ext = os.path.splitext(urlparse(img_url).path)[-1]
                                        if not img_ext: img_ext = ".jpg"
                                        safe_name = make_safe_filename(img_url) + img_ext
                                        img_path = os.path.join(self.config["img_dir"], safe_name)
                                        with open(img_path, "wb") as f:
                                            f.write(img_res.content)
                                        img["local_path"] = img_path
                            except Exception:
                                img["local_path"] = "ERROR_DOWNLOADING"

                self._merge_page_data(page_data)

                # Incremental flush
                if self.on_batch_ready and self.pages_scraped % self.batch_size == 0:
                    self.on_batch_ready(self.all_data, self.crawl_log)

                # Discover new links
                if depth < self.max_depth:
                    links_added = 0
                    for a in extractor.tree.css("a[href]"):
                        href = a.attributes.get("href", "").strip()
                        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                            continue
                        link_url = urljoin(url, href)
                        if get_domain(link_url) == self.domain and not should_skip(link_url):
                            if self.normalize(link_url) not in self.visited:
                                await self.queue.put((link_url, depth + 1))
                                links_added += 1
                    if links_added:
                        logger.info(f"  ↳ Discovered {links_added} new URLs")

                # Anti-ban jitter
                await asyncio.sleep(random.uniform(0.5, 2.0))

            except Exception as e:
                self.pages_failed += 1
                logger.error(f"  ✗ Error on {url}: {e}")
                self.crawl_log.append({
                    "url": url,
                    "status_code": "ERROR",
                    "error": str(e),
                    "depth": depth,
                    "timestamp": datetime.now().isoformat(),
                })

            self._active_workers -= 1
            self.queue.task_done()

        await page.close()

    async def run(self):
        self.start_time = time.time()
        self.queue = asyncio.Queue()
        self._shutdown = False
        self._active_workers = 0
        await self.queue.put((self.start_url, 0))

        async with async_playwright() as p:
            launch_args = {"headless": True}
            if self.proxy:
                launch_args["proxy"] = {"server": self.proxy}

            browser = await p.chromium.launch(**launch_args)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

            concurrency = 3  # Browser tabs are heavy; keep low
            workers = [
                asyncio.create_task(self.worker(context))
                for _ in range(concurrency)
            ]
            await asyncio.gather(*workers)

            await browser.close()

        return self.all_data, self.crawl_log

