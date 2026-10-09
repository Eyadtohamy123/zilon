
```
███████╗██╗██╗      ██████╗ ███╗   ██╗
╚══███╔╝██║██║     ██╔═══██╗████╗  ██║
  ███╔╝ ██║██║     ██║   ██║██╔██╗ ██║
 ███╔╝  ██║██║     ██║   ██║██║╚██╗██║
███████╗██║███████╗╚██████╔╝██║ ╚████║
╚══════╝╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═══╝
```

**A Python web scraper with two engines: pick the right tool for every site.**

Zilon turns messy web pages into clean, structured data. Fast when it can be, browser-powered when it has to be, and ready to export wherever you need it.

---

## ✨ Why Zilon?

Most sites are simple HTML. Some are a maze of JavaScript, anti-bot shields, and lazy-loaded products. Zilon handles both:

- ⚡ **Fast Engine**: httpx, selectolax, and curl_cffi for quick, lightweight crawling
- 🌐 **Browser Engine**: Playwright for JavaScript-heavy sites, React apps, and tougher targets

Choose the engine per job, not per tool.

---

## 🧭 Features

- **Guided menu** that walks you from URL to dataset
- **Crawl control**: set max depth and max pages
- **Pick your data**:
  - 📋 Metadata & SEO
  - 📝 Full page text
  - 🔤 Headings (H1–H6)
  - 🖼️ Images & media
  - 🔗 Links & navigation
  - 📊 Tables
  - 🛒 E-commerce products
- **Export anywhere**: Excel (.xlsx), CSV, SQLite, JSON, JSONL
- 🤖 **Optional AI insights** using a local Llama 3.2 model, so your data stays on your machine
- 🖥️ **Two interfaces**: a CLI menu and a web GUI

---

## 🚀 Quick Start

```bash
# Clone the repo
git clone https://github.com/Eyadtohamy123/zilon.git
cd zilon

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the CLI menu
python menu.py

# Or launch the web GUI
python gui_server.py
```

Then follow the prompts: enter a URL, choose an engine, set depth and page limits, pick your data, and select export formats.

---

## 🗂️ Project Structure

```
zilon/
├── menu.py            # CLI entry point
├── gui_server.py      # Web GUI server
├── gui/               # Web interface files
├── ai_extractor.py    # Optional AI insights
├── engine_fast.py     # Fast crawling engine
├── engine_browser.py  # Playwright browser engine
├── extractor_ecommerce.py
├── exporter.py        # Excel, CSV, SQLite, JSON, JSONL export
├── data_cleaner.py
├── schemas.py
└── docs/
```

---

## 🧪 Tested On

Tested against [books.toscrape.com](https://books.toscrape.com), a site built for practicing scraping.

---

## 🛣️ Roadmap

- [ ] More export and analysis options
- [ ] Expanded e-commerce extraction
- [ ] Better anti-bot handling
- [ ] Documentation for each engine

Ideas and pull requests are welcome.

---

## 👤 Author

**Eyad Tohamy** · Python automation & web scraping
GitHub: [@Eyadtohamy123](https://github.com/Eyadtohamy123)
LinkedIn: [linkedin.com/in/eyad-tohamy-62764b376](https://www.linkedin.com/in/eyad-tohamy-62764b376/)

---

⭐ If Zilon helped you, consider starring the repo.
