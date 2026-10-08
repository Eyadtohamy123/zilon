# 🌟 Features & Capabilities (For Clients)

If you are a freelancer or agency selling scraping services, **Web Scraper 3.0** provides everything you need to deliver a premium, enterprise-tier result to your clients. You can use this document as a reference for your service proposals or Upwork listings.

## 🛠️ Core Extraction Capabilities

### 1. Dual-Engine Architecture
Most scrapers break when a website uses modern JavaScript (like React or Vue). Web Scraper 3.0 uses a dual-engine system:
* **Fast Engine (HTTPX)**: Incredibly fast engine for standard websites. Scrapes thousands of pages per minute.
* **Browser Engine (Playwright)**: A full headless Chromium browser that visually renders JavaScript, scrolls, and bypasses basic bot protections before extracting data.

### 2. Hyper-Targeted Extraction
Clients rarely want "everything". They want specific data. 
* **Custom CSS Selectors**: Target exact elements on a page (e.g., extracting only the `.product-price` and `.product-title`) to generate highly focused datasets.
* **Pattern Recognition**: Automatically scans massive text blocks to sniff out hidden Email Addresses and Phone Numbers using Regex.

### 3. Local Media Downloading
Instead of just handing a client a spreadsheet full of image URLs, this tool can physically download every image it finds into an organized `IMAGES/` folder, and link the local file path in the spreadsheet. Perfect for e-commerce scraping.

---

## 🧹 Data Engineering & Polish

### 4. Automated Data Sanitization
Before data is saved, it is routed through an aggressive cleaning pipeline:
* HTML encoded entities (like `&nbsp;` or `&amp;`) are decoded.
* Corrupted characters and weird spacing are squashed.
* Timestamps and dates are formatted.
Your client receives a database that is strictly "Ready-To-Use".

### 5. Automated Deduplication
It's common for scrapers to accidentally scrape the same footer link or sidebar text 1,000 times. Web Scraper 3.0 automatically drops exact duplicate rows across your dataset before exporting, saving your client hours of manual cleanup.

---

## 💾 Exporting & Deliverables

### 6. Big-Data Ready formats (JSONL)
Alongside standard CSV and Excel files, this tool exports in **JSON-Lines (JSONL)**. If your client requests a 2-million row dataset, a standard JSON or Excel file will crash their computer. JSONL allows them to process massive data row-by-row safely.

### 7. SQLite Database Generation
With a single checkbox, the tool generates a fully queryable `.sqlite` relational database file. You can hand your client a literal ready-to-query database instead of a messy spreadsheet.

### 8. Auto-Generated Data Dictionaries
The hallmark of a professional Data Engineer. The tool automatically generates a `DATA_DICTIONARY.md` file that acts as a schema manual. It tells the client exactly how many rows are in the dataset, what data type each column is, and provides sample data.

### 9. Scraping Reports
A highly professional `SCRAPING_REPORT.txt` is generated with every run, detailing exactly how many pages were attempted, how many succeeded, and what datasets were generated. This serves as a perfect "receipt of work" for freelance jobs.

---

## 🛡️ Resilience & Safety

### 10. Crash Recovery (Auto-Resume)
If you are scraping 50,000 pages and your internet dies at page 25,000, **you do not lose your progress**. The scraper constantly saves its state to a hidden `.scraper_state.json` file. When you restart it, it will pick up exactly where it left off.

### 11. Anti-Ban Mechanisms
* **Automated Request Jitter**: Randomizes the delay between requests to mimic human browsing patterns.
* **User-Agent Rotation**: Constantly switches browser profiles so the target server doesn't realize it's a bot.
* **Proxy Support**: Full support for residential and datacenter proxies to mask your IP address. 
