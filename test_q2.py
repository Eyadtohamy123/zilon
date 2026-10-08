import asyncio
import questionary
from unittest.mock import patch

class MockQuestionary:
    def __init__(self, ret_val):
        self.ret_val = ret_val
    def ask(self):
        return self.ret_val

questionary.text = lambda *args, **kwargs: MockQuestionary("https://books.toscrape.com")

# Simulate menu.py
url = questionary.text("URL:").ask()
# Wait, my mock doesn't trigger prompt_toolkit's loop. I need the REAL questionary.
