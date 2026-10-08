# 🚨 Troubleshooting & FAQ

## 1. The scraper finishes instantly and exports empty files.
**Cause**: The website is blocking you, or it requires JavaScript to render the HTML.
**Solution**: 
1. Run the scraper again and select the **Browser Engine (Playwright)** instead of the Fast Engine.
2. If it still fails, the site is likely IP-banning you. You will need to use a Proxy.

## 2. Playwright throws a `Browser closed unexpectedly` error.
**Cause**: You might not have the Playwright browser binaries installed.
**Solution**:
Run this command in your terminal to download the necessary browser files:
```bash
playwright install chromium
```

## 3. "TimeoutException" during fast scraping.
**Cause**: You are hitting the server too hard and it is dropping your connections, or your internet is unstable.
**Solution**: 
The scraper already uses exponential backoff (retries 3 times automatically). If it still fails, the site's server is too weak. You can ignore these errors, as the scraper will skip the broken page and continue crawling the rest of the site safely.

## 4. How do I stop a long scrape?
Press `Ctrl+C` in your terminal.
Because this is the Enterprise Edition, the scraper will catch your interrupt and safely save a `.scraper_state.json` file in the output folder. 
The next time you scrape that identical URL, it will ask if you want to resume where you left off.

## 5. My Excel file won't open / is corrupted!
**Cause**: This happens when scraping sites with heavily corrupted characters (like null bytes) that break Excel's XML engine.
**Solution**:
Web Scraper 3.0 has a built-in `_sanitize_for_excel` function that strips illegal XML characters, so this should almost never happen. However, if it does, open the `.csv` versions of the data instead (they never corrupt), and resave it as an Excel file manually.

## 6. Playwright is using too much RAM!
**Cause**: Headless browsers use a lot of memory.
**Solution**:
The Browser Engine is hard-coded to limit concurrency to `3` tabs max to prevent RAM explosions. If your computer is extremely low on memory, try closing other applications or stick to the Fast Engine.
