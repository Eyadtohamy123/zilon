```
███████╗██╗██╗      ██████╗ ███╗   ██╗
╚══███╔╝██║██║     ██╔═══██╗████╗  ██║
  ███╔╝ ██║██║     ██║   ██║██╔██╗ ██║
 ███╔╝  ██║██║     ██║   ██║██║╚██╗██║
███████╗██║███████╗╚██████╔╝██║ ╚████║
╚══════╝╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═══╝

            v4.0  E N T E R P R I S E   E D I T I O N
   Fast crawling. Deep extraction. Local AI. Zero cloud bills.
```

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Local AI](https://img.shields.io/badge/AI-Local%20Llama%203.2-8A2BE2?style=for-the-badge)
![Interface](https://img.shields.io/badge/Interface-CLI%20%2B%20Web%20GUI-FF6B35?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Active-2ea44f?style=for-the-badge)

---

## 🌌 What is Zilon?

Most scrapers make you choose: fast OR powerful.
Static pages need speed. Modern sites need a real browser. Messy HTML needs a brain.

**Zilon refuses to choose.**

Zilon is a modular Python crawler and data extractor. Give it a URL, pick an engine,
set how deep to crawl, tick the data you want, and it returns clean, structured output.
Its AI insights run on a **local Llama 3.2 model**, so your data stays on your machine.

---

## 🖥️ See It in Action

```
$ python menu.py

  ? 1. Enter the Target URL (e.g., https://example.com): https://books.toscrape.com/
  ? 2. Choose the Crawling Engine: ⚡ Fast Engine (httpx, selectolax, curl_cffi) - Best for most sites
  ? 3. Enter max depth and max pages (e.g., 2,50): 2,50
  ? 4. Select Data to Extract: (Use arrow keys to move, <space> to select, <a> to toggle, <i> to invert)

   » ● 📋 Metadata & SEO
     ● 📝 Full Page Text
     ● 🔤 Headings (H1-H6)
     ● 🖼️ Images & Media
     ● 🔗 Links & Navigation
     ● 📊 Tables
     ○ 🛒 E-Commerce Products
     ○ 🤖 AI Insights (Local Llama 3.2)
```

---

## ✨ What Zilon Can Extract

| Option | What you get |
|---|---|
| 📋 Metadata & SEO | Titles, descriptions, and SEO-relevant tags |
| 📝 Full Page Text | Clean readable text from each page |
| 🔤 Headings (H1-H6) | The full heading structure of a page |
| 🖼️ Images & Media | Image and media sources |
| 🔗 Links & Navigation | Internal and external links |
| 📊 Tables | Table data turned into structured rows |
| 🛒 E-Commerce Products | Product names, prices, and details |
| 🤖 AI Insights | Summaries and insights from a local Llama 3.2 model |

---

## 🎭 Meet the Crew

| Member | Role | File |
|---|---|---|
| ⚡ The Sprinter | Fast HTTP crawling with httpx, selectolax, curl_cffi | `engine_fast.py` |
| 🧗 The Climber | Real browser engine for JavaScript-heavy sites | `engine_browser.py` |
| 🕵️ The Detective | AI-powered extraction with local Llama 3.2 | `ai_extractor.py` |
| 🛒 The Shopper | E-commerce product specialist | `extractor_ecommerce.py` |
| 🧹 The Janitor | Cleans and normalizes everything | `data_cleaner.py` |
| 📐 The Architect | Enforces consistent schemas | `schemas.py` |
| 📦 The Courier | Delivers results in the format you need | `exporter.py` |

---

## 🔄 How It Flows

```
                    +----------------+
                    |   Target URL   |
                    +-------+--------+
                            |
                  +---------v----------+
                  |  Choose Engine     |
                  +----+----------+----+
                       |          |
                  Fast |          | Browser
                       |          |
              +--------v---+  +---v------------+
              | Fast Engine|  | Browser Engine |
              +--------+---+  +---+------------+
                       |          |
                  +----v----------v----+
                  |  Crawl (max depth  |
                  |   and max pages)   |
                  +---------+----------+
                            |
                  +---------v----------+
                  |    Extractors      |
                  | (SEO, text, links, |
                  | tables, products,  |
                  |    AI insights)    |
                  +---------+----------+
                            |
                  +---------v----------+
                  |  Cleaner + Schema  |
                  +---------+----------+
                            |
                  +---------v----------+
                  |      Exporter      |
                  +---------+----------+
                            |
                  +---------v----------+
                  | Clean, ready data  |
                  +--------------------+
```

---

## ⚙️ Installation

```bash
# 1. Clone the repo
git clone https://github.com/Eyadtohamy123/zilon.git
cd zilon

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

### 🤖 Local AI setup (for AI Insights)

AI Insights uses a local **Llama 3.2** model, so no cloud API key is needed.
Install a local model runner and download Llama 3.2 before using that option.

---

## 🚀 Usage

**Terminal mode:**

```bash
python menu.py
```

**Web GUI mode:**

```bash
python gui_server.py
```

Then open the local address shown in your terminal.

---

## 🗂️ Project Structure

```
zilon/
├── engine_fast.py            # Fast HTTP crawling engine
├── engine_browser.py         # Browser engine for dynamic sites
├── ai_extractor.py           # Local Llama 3.2 extraction
├── extractor_ecommerce.py    # E-commerce product extractor
├── data_cleaner.py           # Cleaning and normalization
├── schemas.py                # Data models and schemas
├── exporter.py               # Export results to files
├── menu.py                   # Interactive command-line interface
├── gui_server.py             # Web GUI server
├── gui/                      # Web GUI assets
├── docs/                     # Documentation
├── output/                   # Scraped results
├── test_*.py                 # Test files
└── requirements.txt          # Dependencies
```

---

## 🧪 Testing

```bash
python -m pytest
```

---

## 🛣️ Roadmap

- [ ] Proxy rotation support
- [ ] Scheduled scraping jobs
- [ ] More site-specific extractors
- [ ] Additional export formats
- [ ] Docker image

---

## ⚠️ Scrape Responsibly

Zilon is built for educational and legitimate use. Always:

- ✅ Respect each website's Terms of Service
- ✅ Follow robots.txt
- ✅ Rate-limit your requests
- ❌ Do not scrape private, personal, or protected data

The author is not responsible for misuse of this tool.

---

## 👨‍💻 Author

**Eyad Tohamy Mohamed**
Python Automation Engineer | Aspiring AI Security Engineer

Need a custom scraper or automation tool? Let's talk.

- GitHub: [Eyadtohamy123](https://github.com/Eyadtohamy123)
- LinkedIn: [Eyad Tohamy](https://www.linkedin.com/in/eyad-tohamy-62764b376/)

---

## 📄 License

Released under the MIT License. See the `LICENSE` file for details.

---

```
   ⭐ If Zilon saved you time, drop a star. It fuels the next version.

   ───────────────  Z I L O N  ───────────────
```
