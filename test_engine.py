import asyncio
import logging
from engine_fast import FastEngine
from exporter import DataExporter

logging.basicConfig(level=logging.INFO)

async def main():
    config = {
        "url": "https://books.toscrape.com",
        "max_pages": 2,
        "depth": 1,
        "extract_patterns": False,
        "proxy": None
    }
    
    engine = FastEngine(config)
    data, log = await engine.run()
    
    print(f"Scraped {engine.pages_scraped} pages.")
    print(f"Data keys: {data.keys()}")
    print(f"Metadata rows: {len(data['metadata'])}")
    
    exporter = DataExporter("./test_output", "test_site", ["csv"])
    exporter.export_all(data, log)

if __name__ == "__main__":
    asyncio.run(main())
