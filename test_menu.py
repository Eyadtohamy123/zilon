import sys
import asyncio
from unittest.mock import patch

# Mock questionary
class MockQuestionary:
    def __init__(self, ret_val):
        self.ret_val = ret_val
    def ask(self):
        return self.ret_val

import questionary
questionary.text = lambda *args, **kwargs: MockQuestionary("https://books.toscrape.com") if "URL" in args[0] else MockQuestionary("3")
questionary.select = lambda *args, **kwargs: MockQuestionary("Fast Engine") if "Engine" in args[0] else MockQuestionary("1. Start New Scraping Job")
questionary.checkbox = lambda *args, **kwargs: MockQuestionary(["csv", "excel"])
questionary.confirm = lambda *args, **kwargs: MockQuestionary(False)

from menu import run_scraper

async def run():
    await asyncio.sleep(0) # just to allow async env
    from menu import run_scraper
    run_scraper()

if __name__ == "__main__":
    run_scraper()
