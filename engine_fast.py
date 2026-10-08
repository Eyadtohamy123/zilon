"""
Web Scraper 4.0 — High-Scale Fast Engine
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Enterprise-grade async crawler using httpx + curl_cffi fallback.
Supports 100,000+ page crawls with semaphore concurrency, content-hash
deduplication, exponential backoff, and incremental data flushing.
"""
import asyncio
import httpx
import random
import json
import os
import re
import logging
import hashlib
import time
from selectolax.parser import HTMLParser
from urllib.parse import urljoin, urlparse, urldefrag
from datetime import datetime
from fake_useragent import UserAgent

try:
    import xxhash
    def content_hash(text: str) -> str:
        return xxhash.xxh64(text.encode("utf-8", errors="ignore")).hexdigest()
except ImportError:
    def content_hash(text: str) -> str:
        return hashlib.md5(text.encode("utf-8", errors="ignore")).hexdigest()

try:
    from curl_cffi.requests import AsyncSession as CurlAsyncSession
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False

from schemas import validate_batch
from ai_extractor import AIExtractor, AIExtractorDisabled
from extractor_ecommerce import EcommerceExtractor

logger = logging.getLogger("WebScraper3.0")

SKIP_EXTENSIONS = {
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp",
    ".mp3", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm",
    ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".exe", ".dmg", ".iso", ".bin",
    ".css", ".js", ".json", ".xml", ".rss", ".atom",
    ".woff", ".woff2", ".ttf", ".eot", ".ico",
}

EMAIL_REGEX = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
PHONE_REGEX = re.compile(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}')

# ── Retry-eligible status codes ──────────────────────────
RETRY_STATUS_CODES = {429, 500, 502, 503}

# ── Realistic browser headers ────────────────────────────
def build_headers(ua_string: str) -> dict:
    """Generate realistic browser headers for anti-bot evasion."""
    return {
        "User-Agent": ua_string,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
        "Connection": "keep-alive",
    }


def clean_text(text):
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip()


def get_domain(url):
    return urlparse(url).netloc


def is_valid_url(url):
    try:
        res = urlparse(url)
        return all([res.scheme in ("http", "https"), res.netloc])
    except Exception:
        return False


def should_skip(url):
    return any(urlparse(url.lower()).path.endswith(ext) for ext in SKIP_EXTENSIONS)


def make_safe_filename(text, max_length=50):
    safe = re.sub(r'[^\w\s-]', '', text)
    safe = re.sub(r'\s+', '_', safe).strip('_')
    return safe[:max_length] if safe else "unnamed"


def url_to_filename(url):
    """Convert a URL to a safe filename for HTML dumps."""
    parsed = urlparse(url)
    path = parsed.path.strip('/').replace('/', '_') or 'index'
    safe = re.sub(r'[^\w\s.-]', '_', path)
    return safe[:100] + '.html'


def strip_boilerplate(tree: HTMLParser) -> HTMLParser:
    """Remove nav, footer, sidebar, ad blocks, scripts, styles from parsed tree."""
    selectors_to_remove = [
        "script", "style", "noscript", "iframe",
        "nav", "footer", "header",
        ".sidebar", ".nav", ".menu", ".footer", ".header",
        ".ad", ".ads", ".advertisement", ".banner",
        "[role='navigation']", "[role='banner']", "[role='contentinfo']",
        ".cookie-banner", ".popup", ".modal",
    ]
    for selector in selectors_to_remove:
        try:
            for node in tree.css(selector):
                node.decompose()
        except Exception:
            pass
    return tree


# ═══════════════════════════════════════════════════════════════════════════
#  PAGE DATA EXTRACTOR — Selective & Targeted (v4.0)
# ═══════════════════════════════════════════════════════════════════════════

class PageDataExtractor:
    """Extracts data from a single HTML page based on selected options."""

    def __init__(self, url, html_content, config):
        self.url = url
        self.html_content = html_content
        self.tree = HTMLParser(html_content)
        self.domain = get_domain(url)
        self.extract_options = config.get('extract_options', ['metadata', 'text', 'images', 'links', 'tables', 'headings'])
        self.extract_patterns = config.get('extract_patterns', False)
        self.custom_selectors = config.get('custom_selectors', {})

    def extract_metadata(self):
        """Extract page metadata and SEO info."""
        metadata = {
            "url": self.url,
            "title": "",
            "description": "",
            "keywords": "",
            "author": "",
            "og_title": "",
            "og_description": "",
            "og_image": "",
            "canonical_url": "",
            "language": "",
            "scraped_at": datetime.now().isoformat(),
        }
        title_node = self.tree.css_first("title")
        if title_node:
            metadata["title"] = clean_text(title_node.text())

        for meta in self.tree.css("meta"):
            attrs = meta.attributes
            name = (attrs.get("name", "") or attrs.get("property", "")).lower()
            content = attrs.get("content", "")
            if name == "description":
                metadata["description"] = clean_text(content)
            elif name == "keywords":
                metadata["keywords"] = clean_text(content)
            elif name == "author":
                metadata["author"] = clean_text(content)
            elif name == "og:title":
                metadata["og_title"] = clean_text(content)
            elif name == "og:description":
                metadata["og_description"] = clean_text(content)
            elif name == "og:image":
                metadata["og_image"] = urljoin(self.url, content) if content else ""

        canonical = self.tree.css_first("link[rel='canonical']")
        if canonical and canonical.attributes.get("href"):
            metadata["canonical_url"] = urljoin(self.url, canonical.attributes.get("href"))

        html_node = self.tree.css_first("html")
        if html_node and html_node.attributes.get("lang"):
            metadata["language"] = html_node.attributes.get("lang")

        return metadata

    def extract_text(self):
        """Extract full page text with word/char counts and optional pattern extraction."""
        clean_tree = HTMLParser(self.html_content)
        clean_tree = strip_boilerplate(clean_tree)
        target_node = clean_tree.body or clean_tree
        text = clean_text(target_node.text(separator="\n", strip=True))

        result = {
            "url": self.url,
            "full_text": text,
            "character_count": len(text),
            "word_count": len(text.split()),
            "scraped_at": datetime.now().isoformat(),
        }
        if self.extract_patterns:
            result["emails_found"] = ", ".join(sorted(set(EMAIL_REGEX.findall(text))))
            result["phones_found"] = ", ".join(sorted(set(PHONE_REGEX.findall(text))))
        return result

    def extract_headings(self):
        """Extract all headings (h1-h6) with their hierarchy."""
        headings = []
        for level in range(1, 7):
            for h in self.tree.css(f"h{level}"):
                text = clean_text(h.text(strip=True))
                if text:
                    headings.append({
                        "url": self.url,
                        "level": f"h{level}",
                        "text": text,
                    })
        return headings

    def extract_images(self):
        """Extract all images with src, alt text, and dimensions."""
        images = []
        for img in self.tree.css("img"):
            attrs = img.attributes
            src = attrs.get("src", "") or attrs.get("data-src", "") or attrs.get("data-lazy-src", "")
            if not src:
                continue
            images.append({
                "url": self.url,
                "image_src": urljoin(self.url, src),
                "alt_text": clean_text(attrs.get("alt", "")),
                "width": attrs.get("width", ""),
                "height": attrs.get("height", ""),
                "loading": attrs.get("loading", ""),
            })
        return images

    def extract_links(self):
        """Extract all links with text, href, and classification."""
        links = []
        for a in self.tree.css("a[href]"):
            href = a.attributes.get("href", "").strip()
            if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue
            full_url = urljoin(self.url, href)
            is_internal = get_domain(full_url) == self.domain
            links.append({
                "source_url": self.url,
                "link_url": full_url,
                "link_text": clean_text(a.text(strip=True)) or "[No Text]",
                "type": "internal" if is_internal else "external",
                "rel": a.attributes.get("rel", ""),
            })
        return links

    def extract_tables(self):
        """Extract all HTML tables into structured row data."""
        tables = []
        for table_idx, table in enumerate(self.tree.css("table"), 1):
            headers = []
            for th in table.css("th"):
                headers.append(clean_text(th.text(strip=True)))

            for row_idx, tr in enumerate(table.css("tr"), 1):
                cells = []
                for td in tr.css("td"):
                    cells.append(clean_text(td.text(strip=True)))
                if cells:
                    row_data = {
                        "url": self.url,
                        "table_number": table_idx,
                        "row_number": row_idx,
                    }
                    # Map cells to headers if we have them
                    for i, cell in enumerate(cells):
                        col_name = headers[i] if i < len(headers) else f"column_{i+1}"
                        row_data[col_name] = cell
                    tables.append(row_data)
        return tables

    def extract_custom_selectors(self):
        """Extract data using user-defined CSS selectors."""
        results = []
        for label, selector in self.custom_selectors.items():
            try:
                elements = self.tree.css(selector)
                for idx, el in enumerate(elements, 1):
                    text = clean_text(el.text(strip=True))
                    href = el.attributes.get("href", "") if el.tag == "a" else ""
                    src = el.attributes.get("src", "") if el.tag == "img" else ""
                    results.append({
                        "url": self.url,
                        "selector_label": label,
                        "css_selector": selector,
                        "match_index": idx,
                        "text": text,
                        "href": href,
                        "src": src,
                    })
            except Exception as e:
                logger.warning(f"  Custom selector '{selector}' failed: {e}")
        return results

    def get_clean_text_for_ai(self) -> str:
        """Return cleaned page text suitable for sending to AI (boilerplate stripped)."""
        clean_tree = HTMLParser(self.html_content)
        clean_tree = strip_boilerplate(clean_tree)
        target_node = clean_tree.body or clean_tree
        return clean_text(target_node.text(separator="\n", strip=True))

    def extract_all(self):
        """Run all selected extractions and return organized data."""
        data = {}

        if 'metadata' in self.extract_options:
            data['metadata'] = self.extract_metadata()

        if 'text' in self.extract_options:
            data['text'] = self.extract_text()

        if 'headings' in self.extract_options:
            data['headings'] = self.extract_headings()

        if 'images' in self.extract_options:
            data['images'] = self.extract_images()

        if 'links' in self.extract_options:
            data['links'] = self.extract_links()

        if 'tables' in self.extract_options:
            data['tables'] = self.extract_tables()

        if 'ecommerce' in self.extract_options:
            ecommerce_extractor = EcommerceExtractor(self.url, self.html_content, self.tree)
            ecommerce_data = ecommerce_extractor.extract()
            if ecommerce_data:
                data['ecommerce'] = [ecommerce_data]

        if self.custom_selectors:
            data['custom'] = self.extract_custom_selectors()

        return data


# ═══════════════════════════════════════════════════════════════════════════
#  FAST ENGINE v4.0 — High-Scale Async with Semaphore, curl_cffi, Dedup
# ═══════════════════════════════════════════════════════════════════════════

class FastEngine:
    """
    Enterprise-grade async crawler.
    
    Features:
    - asyncio.Semaphore for precise concurrency control
    - curl_cffi fallback for Cloudflare/anti-bot bypass
    - Exponential backoff retries (5 attempts) for 429/5xx
    - Content-hash deduplication
    - AI extraction integration (optional)
    - Real-time stats for live dashboard
    """

    def __init__(self, config):
        self.start_url = config['url']
        self.domain = get_domain(self.start_url)
        self.max_pages = config['max_pages']
        self.max_depth = config['depth']
        self.proxy = config.get('proxy')
        self.config = config
        self.save_html = config.get('save_html', False)
        self.html_dir = config.get('html_dir', '')

        # High-scale settings
        self.max_concurrent = config.get('max_concurrent', 25)
        self.request_timeout = config.get('request_timeout', 30)
        self.batch_size = config.get('batch_size', 100)

        # State
        self.visited = set()
        self.content_hashes = set()  # Content-hash dedup
        self.pages_scraped = 0
        self.pages_failed = 0
        self.all_data = {}
        self.crawl_log = []
        self.ua = UserAgent()
        self.start_time = None

        # AI extractor
        if config.get('use_ai_extraction', False):
            self.ai = AIExtractor(
                model=config.get('ai_model', 'llama3.2'),
                prompt=config.get('ai_prompt', ''),
            )
        else:
            self.ai = AIExtractorDisabled()

        # Incremental exporter callback (set by menu.py)
        self.on_batch_ready = None  # Callable[[dict], None]

    @property
    def stats(self) -> dict:
        """Live stats for the dashboard."""
        elapsed = time.time() - self.start_time if self.start_time else 0
        rate = self.pages_scraped / elapsed if elapsed > 0 else 0
        return {
            "queued": self.queue.qsize() if hasattr(self, 'queue') else 0,
            "processed": self.pages_scraped,
            "failed": self.pages_failed,
            "rate": round(rate, 2),
            "elapsed": round(elapsed, 1),
            "dedup_skipped": len(self.content_hashes),
        }

    def normalize(self, url):
        return urldefrag(url)[0].rstrip("/")

    async def fetch_with_retry(self, client, url, max_retries=5):
        """
        Fetch a URL with exponential backoff retries.
        Falls back to curl_cffi if httpx gets a 403/Cloudflare challenge.
        """
        headers = build_headers(self.ua.random)
        last_error = None

        for attempt in range(max_retries):
            try:
                res = await client.get(
                    url, headers=headers, follow_redirects=True,
                    timeout=self.request_timeout
                )
                
                # Cloudflare / anti-bot detection → try curl_cffi
                if res.status_code == 403 and HAS_CURL_CFFI:
                    logger.info(f"  🛡️ 403 detected, trying curl_cffi for {url}")
                    return await self._fetch_curl_cffi(url, headers)
                
                # Retry-eligible status codes
                if res.status_code in RETRY_STATUS_CODES:
                    wait = min(2 ** attempt + random.uniform(0, 1), 30)
                    logger.warning(f"  ⏳ {res.status_code} on {url}, retry {attempt+1}/{max_retries} in {wait:.1f}s")
                    await asyncio.sleep(wait)
                    continue

                res.raise_for_status()
                return res

            except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError) as e:
                last_error = e
                wait = min(2 ** attempt + random.uniform(0, 1), 30)
                logger.warning(f"  ⏳ Network error on {url}: {e}, retry {attempt+1}/{max_retries} in {wait:.1f}s")
                await asyncio.sleep(wait)
            except httpx.HTTPStatusError as e:
                if e.response.status_code in RETRY_STATUS_CODES:
                    wait = min(2 ** attempt + random.uniform(0, 1), 30)
                    await asyncio.sleep(wait)
                    last_error = e
                    continue
                raise

        raise last_error or Exception(f"Failed after {max_retries} retries: {url}")

    async def _fetch_curl_cffi(self, url, headers):
        """Fallback fetch using curl_cffi with Chrome TLS impersonation."""
        if not HAS_CURL_CFFI:
            raise Exception("curl_cffi not installed")
        
        try:
            async with CurlAsyncSession(impersonate="chrome") as session:
                proxy_dict = {"https": self.proxy, "http": self.proxy} if self.proxy else None
                response = await session.get(
                    url, headers=headers, timeout=self.request_timeout,
                    proxies=proxy_dict, allow_redirects=True
                )
                # Wrap in a compatible object
                return CurlResponse(response)
        except Exception as e:
            logger.error(f"  ✗ curl_cffi also failed for {url}: {e}")
            raise

    def _merge_page_data(self, page_data):
        """Merge a single page's extracted data into the cumulative all_data dict."""
        for key, value in page_data.items():
            if key not in self.all_data:
                self.all_data[key] = []
            if isinstance(value, list):
                self.all_data[key].extend(value)
            elif isinstance(value, dict):
                self.all_data[key].append(value)

    def _validate_page_data(self, page_data: dict) -> dict:
        """Run Pydantic validation on all extracted datasets."""
        validated = {}
        for key, value in page_data.items():
            records = value if isinstance(value, list) else [value]
            valid_records = validate_batch(key, records)
            if valid_records:
                validated[key] = valid_records
        return validated

    def _save_state(self, output_dir):
        """Save crawl state for crash recovery."""
        state = {
            "visited": list(self.visited),
            "pages_scraped": self.pages_scraped,
            "start_url": self.start_url,
            "max_pages": self.max_pages,
            "max_depth": self.max_depth,
            "timestamp": datetime.now().isoformat(),
        }
        state_path = os.path.join(output_dir, ".scraper_state.json")
        try:
            with open(state_path, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception:
            pass

    def load_state(self, output_dir):
        """Load previous crawl state for resume."""
        state_path = os.path.join(output_dir, ".scraper_state.json")
        if os.path.exists(state_path):
            try:
                with open(state_path, 'r') as f:
                    state = json.load(f)
                if state.get("start_url") == self.start_url:
                    self.visited = set(state.get("visited", []))
                    self.pages_scraped = state.get("pages_scraped", 0)
                    return True
            except Exception:
                pass
        return False

    async def worker(self, worker_id, client, semaphore):
        """Worker coroutine — continuously processes URLs from the queue."""
        idle_cycles = 0
        while not self._shutdown:
            # Poll the queue — avoids asyncio.wait_for race condition
            if self.queue.empty():
                # Only exit if queue is TRULY empty AND no other worker is fetching
                # (a fetching worker may discover new URLs any moment)
                if self._active_workers == 0:
                    idle_cycles += 1
                    if idle_cycles >= 6:  # 6 × 0.5s = 3s of confirmed idleness
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

            async with semaphore:
                self.pages_scraped += 1
                logger.info(f"  [{self.pages_scraped}/{self.max_pages}] Depth={depth} | {url}")

                try:
                    res = await self.fetch_with_retry(client, url)
                    content_type = ""
                    if hasattr(res, 'headers'):
                        content_type = res.headers.get("Content-Type", "")
                    
                    if "text/html" not in content_type and content_type:
                        self._active_workers -= 1
                        self.queue.task_done()
                        continue

                    html = res.text if hasattr(res, 'text') else str(res.content, 'utf-8', errors='ignore')
                    status_code = res.status_code

                    # Content-hash dedup — skip if we've seen identical content
                    c_hash = content_hash(html)
                    if c_hash in self.content_hashes:
                        logger.info(f"  ♻️ Duplicate content skipped: {url}")
                        self._active_workers -= 1
                        self.queue.task_done()
                        continue
                    self.content_hashes.add(c_hash)

                    self.crawl_log.append({
                        "url": url,
                        "status_code": status_code,
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

                    # AI extraction (if enabled)
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
                                    img_res = await client.get(img_url, timeout=10)
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

                    # Incremental flush callback
                    if self.on_batch_ready and self.pages_scraped % self.batch_size == 0:
                        self.on_batch_ready(self.all_data, self.crawl_log)

                    # Discover new links for crawling
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
                    await asyncio.sleep(random.uniform(0.3, 1.5))

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

    async def run(self):
        self.start_time = time.time()
        self.queue = asyncio.Queue()
        self._shutdown = False
        self._active_workers = 0
        await self.queue.put((self.start_url, 0))
        semaphore = asyncio.Semaphore(self.max_concurrent)
        limits = httpx.Limits(max_connections=self.max_concurrent + 5, max_keepalive_connections=self.max_concurrent)
        mounts = None
        if self.proxy:
            mounts = {
                'http://': httpx.AsyncHTTPTransport(proxy=self.proxy),
                'https://': httpx.AsyncHTTPTransport(proxy=self.proxy),
            }

        num_workers = min(self.max_concurrent, 10)  # Don't spawn more than 10 actual coroutines

        async with httpx.AsyncClient(limits=limits, timeout=self.request_timeout, mounts=mounts) as client:
            workers = [
                asyncio.create_task(self.worker(i, client, semaphore))
                for i in range(num_workers)
            ]
            await asyncio.gather(*workers)

        return self.all_data, self.crawl_log


class CurlResponse:
    """Wrapper to make curl_cffi response look like httpx response."""
    def __init__(self, response):
        self._response = response
        self.status_code = response.status_code
        self.headers = dict(response.headers) if hasattr(response, 'headers') else {}
        self.text = response.text if hasattr(response, 'text') else ""
        self.content = response.content if hasattr(response, 'content') else b""
