"""
Web Scraper 4.0 — CLI Interface & Dashboard
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Interactive terminal menu and rich live dashboard for monitoring crawls.
"""
import asyncio
import os
import sys
import logging
from datetime import datetime
from urllib.parse import urlparse
import questionary
from questionary import Choice

from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.layout import Layout
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn

from engine_fast import FastEngine
from engine_browser import BrowserEngine
from exporter import IncrementalExporter, DataExporter

# ════════════════ CONFIGURATION ════════════════
USE_AI_EXTRACTION   = False       # Set True to enable Ollama AI extraction
AI_MODEL            = "llama3.2"  # Ollama model name
AI_PROMPT           = ""          # Custom extraction prompt
MAX_CONCURRENT      = 25          # Max parallel requests
BATCH_SIZE          = 100         # Rows to flush to Excel per batch
REQUEST_TIMEOUT     = 30          # Seconds per request
OUTPUT_EXCEL_PATH   = ""          # Custom output path (auto-generated if empty)
# ═══════════════════════════════════════════════

logging.basicConfig(level=logging.ERROR) # Suppress standard logging in CLI to not break the dashboard
logger = logging.getLogger("WebScraper3.0")
logger.setLevel(logging.ERROR)


class Dashboard:
    """Rich Live Terminal Dashboard."""
    
    def __init__(self, target_url, max_pages):
        self.console = Console()
        self.target_url = target_url
        self.max_pages = max_pages
        self.stats = {}
        
    def generate_layout(self):
        """Generate the rich layout."""
        table = Table(show_header=True, header_style="bold magenta", expand=True)
        table.add_column("Metric", style="dim", width=20)
        table.add_column("Value")
        
        table.add_row("Target", self.target_url)
        table.add_row("Pages Processed", f"{self.stats.get('processed', 0)} / {self.max_pages}")
        table.add_row("Queued URLs", str(self.stats.get('queued', 0)))
        table.add_row("Failed Pages", str(self.stats.get('failed', 0)), style="red" if self.stats.get('failed', 0) > 0 else "")
        table.add_row("Speed (Pages/sec)", str(self.stats.get('rate', 0)))
        table.add_row("Elapsed Time (s)", str(self.stats.get('elapsed', 0)))
        
        dedup = self.stats.get('dedup_skipped', 0)
        if dedup > 0:
            table.add_row("Duplicates Skipped", str(dedup), style="yellow")
            
        rows_flushed = self.stats.get('rows_flushed', 0)
        table.add_row("Excel Rows Flushed", str(rows_flushed), style="green" if rows_flushed > 0 else "")
            
        return Panel(table, title="[bold blue]Web Scraper 4.0 Dashboard[/bold blue]", border_style="blue")


def print_header():
    """Print the ASCII art header."""
    header = """
    ██╗    ██╗███████╗██████╗     ███████╗ ██████╗██████╗  █████╗ ██████╗ ███████╗██████╗ 
    ██║    ██║██╔════╝██╔══██╗    ██╔════╝██╔════╝██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔══██╗
    ██║ █╗ ██║█████╗  ██████╔╝    ███████╗██║     ██████╔╝███████║██████╔╝█████╗  ██████╔╝
    ██║███╗██║██╔══╝  ██╔══██╗    ╚════██║██║     ██╔══██╗██╔══██║██╔═══╝ ██╔══╝  ██╔══██╗
    ╚███╔███╔╝███████╗██████╔╝    ███████║╚██████╗██║  ██║██║  ██║██║     ███████╗██║  ██║
     ╚══╝╚══╝ ╚══════╝╚═════╝     ╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚══════╝╚═╝  ╚═╝
                                              v4.0 Enterprise Edition
    """
    print(header)


def run_cli():
    print_header()
    
    url = questionary.text("1. Enter the Target URL (e.g., https://example.com):").ask()
    if not url: return
    if not url.startswith("http"): url = "https://" + url

    engine_choice = questionary.select(
        "2. Choose the Crawling Engine:",
        choices=[
            Choice("⚡ Fast Engine (httpx, selectolax, curl_cffi) - Best for most sites", "fast"),
            Choice("🌐 Browser Engine (Playwright) - Best for JS/React/Cloudflare/Amazon", "browser"),
        ]
    ).ask()
    if not engine_choice: return

    depth_pages = questionary.text("3. Enter max depth and max pages (e.g., 2,50):", default="2,50").ask()
    if not depth_pages: return
    try:
        depth, max_pages = map(int, depth_pages.split(","))
    except:
        print("Invalid format. Use 'depth,pages' (e.g. 2,50).")
        return

    extract_opts = questionary.checkbox(
        "4. Select Data to Extract:",
        choices=[
            Choice("📋 Metadata & SEO", "metadata", checked=True),
            Choice("📝 Full Page Text", "text", checked=True),
            Choice("🔤 Headings (H1-H6)", "headings", checked=True),
            Choice("🖼️  Images & Media", "images", checked=True),
            Choice("🔗 Links & Navigation", "links", checked=True),
            Choice("📊 Tables", "tables", checked=True),
            Choice("🛒 E-Commerce Products", "ecommerce"),
            Choice("🤖 AI Insights (Local Llama 3.2)", "ai_insights")
        ]
    ).ask()
    if not extract_opts: return
    
    # Check if AI was explicitly selected, or if the config var is True
    use_ai = "ai_insights" in extract_opts or USE_AI_EXTRACTION
    ai_prompt_val = AI_PROMPT
    if use_ai:
        if "ai_insights" not in extract_opts:
            extract_opts.append("ai_insights")
        print(f"\n[AI Enabled] Model: {AI_MODEL}")
        if not ai_prompt_val:
            ai_prompt_val = questionary.text(
                "Enter your AI extraction prompt (or leave blank for default):",
                default="Extract a 2 sentence summary, key entities, and sentiment as JSON."
            ).ask()

    formats = questionary.checkbox(
        "5. Select Export Formats:",
        choices=[
            Choice("📊 Excel (.xlsx)", "excel", checked=True),
            Choice("📄 CSV (.csv)", "csv", checked=True),
            Choice("🗄️ SQLite (.sqlite)", "sqlite"),
            Choice("📋 JSON (.json)", "json"),
            Choice("📝 JSONL (.jsonl)", "jsonl")
        ]
    ).ask()
    if not formats: return
    
    # Configure run
    site_name = urlparse(url).netloc.replace("www.", "")
    output_dir = os.path.join(os.getcwd(), "output")
    
    config = {
        "url": url,
        "depth": depth,
        "max_pages": max_pages,
        "extract_options": extract_opts,
        "max_concurrent": MAX_CONCURRENT,
        "batch_size": BATCH_SIZE,
        "request_timeout": REQUEST_TIMEOUT,
        "use_ai_extraction": use_ai,
        "ai_model": AI_MODEL,
        "ai_prompt": ai_prompt_val,
        "save_html": False
    }
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    run_dir = os.path.join(output_dir, f"run_{timestamp}")
    exporter = IncrementalExporter(run_dir, site_name, formats)
    
    # Initialize Engine
    if engine_choice == "fast":
        engine = FastEngine(config)
    else:
        engine = BrowserEngine(config)
        
    # Wire up the incremental exporter callback
    def on_batch_ready(data, crawl_log):
        exporter.flush_batch(data, crawl_log)
    engine.on_batch_ready = on_batch_ready
    
    # Dashboard Setup
    dashboard = Dashboard(url, max_pages)
    
    # Run the engine with live dashboard updates
    print(f"\n🚀 Starting scrape of {url} ...\n")
    
    async def run_live_engine():
        engine_task = asyncio.create_task(engine.run())
        
        with Live(dashboard.generate_layout(), refresh_per_second=4, console=dashboard.console) as live:
            while not engine_task.done():
                dashboard.stats = engine.stats
                dashboard.stats['rows_flushed'] = exporter.row_count
                live.update(dashboard.generate_layout())
                await asyncio.sleep(0.25)
                
            # Final update
            dashboard.stats = engine.stats
            dashboard.stats['rows_flushed'] = exporter.row_count
            live.update(dashboard.generate_layout())
            
        return await engine_task

    all_data, crawl_log = asyncio.run(run_live_engine())
    
    # Finalize export
    print("\n💾 Finalizing exports...")
    saved_files = exporter.finalize(all_data, crawl_log)
    
    print("\n✅ Scrape Complete!")
    print("Files saved to:")
    for f in saved_files:
        print(f"  - {f}")


if __name__ == "__main__":
    try:
        run_cli()
    except KeyboardInterrupt:
        print("\n\n🛑 Scrape interrupted by user.")
        sys.exit(0)
