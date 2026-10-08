import asyncio
from engine_browser import BrowserEngine

async def run_test():
    config = {
        "url": "https://www.amazon.com/Apple-iPhone-13-128GB-Midnight/dp/B09G9HD6PD/",
        "max_pages": 1,
        "depth": 0,
        "extract_options": ["ecommerce"],
        "save_html": True,
        "html_dir": "/home/eyad/Downloads/WEB_SCRAPER_3.0/test_html"
    }
    engine = BrowserEngine(config)
    data, log = await engine.run()
    
    print("\n--- RESULTS ---")
    if "ecommerce" in data:
        for item in data["ecommerce"]:
            print(item)
    else:
        print("No ecommerce data found")

if __name__ == "__main__":
    asyncio.run(run_test())
