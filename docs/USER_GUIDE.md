# 📖 User Guide

Welcome to the Web Scraper 3.0 interactive CLI. This guide will walk you through setting up a scraping job from start to finish.

## Starting the Menu
To begin, ensure your virtual environment is activated, then run:
```bash
python menu.py
```
You will be greeted by the Main Menu. Select **"Start New Scraping Job"**.

---

## Step-by-Step Configuration

### 1. Target URL
Enter the exact URL you want to scrape (e.g., `https://books.toscrape.com`). The scraper will use this as the starting point to discover other pages on the same domain.

### 2. Engine Selection
* **Fast Engine (HTTPX)**: Select this 90% of the time. It is incredibly fast and uses minimal RAM.
* **Browser Engine (Playwright)**: Select this ONLY if the website is blank when you scrape it, or if it requires you to wait for a loading spinner. It opens a real headless Chrome browser to render JavaScript, but it is much slower.

### 3. Crawl Settings
* **Max Pages**: The hard limit on how many pages to scrape (e.g., 50).
* **Max Depth**: How many "clicks" away from the homepage the scraper is allowed to travel. A depth of 1 means it only scrapes the homepage and the links directly on the homepage.

### 4. What to Extract
Use the **Spacebar** to toggle checkboxes on and off.
* **Metadata & SEO**: Grabs page titles, meta descriptions, and OG (social media) tags.
* **Full Page Text**: Grabs all readable text on the page, stripping out code.
* **Headings**: Grabs H1 through H6 structural text.
* **Images**: Grabs image sources and alt-text.
* **Links**: Grabs all hyperlinks.
* **Tables**: Reconstructs HTML `<table>` elements into structured data rows.

### 5. Custom CSS Selectors
If a client asks for specific data (e.g., "I just want the prices of the products"), you can enter a Custom CSS Selector.
* **Label**: Give it a name (e.g., `price`).
* **Selector**: Enter the CSS selector (e.g., `.price_color`).
The tool will create a dedicated dataset just for this specific information.

### 6. Raw HTML & Images
* **Save Raw HTML**: If checked, saves a `.html` file containing the literal source code of every page visited.
* **Download Images**: If checked, physically downloads the `.jpg` / `.png` files found on the page into an `IMAGES/` folder on your hard drive.

### 7. Export Formats
Choose how you want to deliver data to your client:
* **CSV**: Best for developers and data scientists.
* **JSON**: Best for web developers.
* **JSONL**: Best for massive datasets (millions of rows).
* **Excel**: Best for business clients. It creates a beautiful multi-sheet workbook with a summary page.
* **SQLite**: Best for analysts. It creates a ready-to-query database file.

### 8. Proxies
If you are scraping a strict website, enter your proxy URL (e.g., `http://username:password@proxy.com:8080`). Otherwise, leave it blank.

---

## Viewing Your Output

Once the scraper finishes, it will generate a folder in `output/` named after the website you scraped. Inside, you will find a timestamped `run_` folder containing:

* `SCRAPING_REPORT.txt` (Your receipt of work)
* `DATA_DICTIONARY.md` (Schema definition for the client)
* Subfolders for `CSV/`, `JSON/`, `EXCEL/`, etc., containing your perfectly clean data.
