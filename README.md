# 🕸️ Web Scraper 3.0 — Enterprise Edition

Welcome to **Web Scraper 3.0**, a professional-grade, high-performance data extraction toolkit built specifically for freelancers, data engineers, and agencies. 

This tool is designed to handle everything from standard HTML sites to heavily JavaScript-rendered web applications, ensuring you can deliver pristine, structured, and deduplicated data to your clients in any format they request.

---

## 🚀 Quick Start Guide

### 1. Prerequisites
Ensure you have **Python 3.10+** installed on your machine.

### 2. Installation
Open your terminal and navigate to this folder. Then, create a virtual environment and install the required dependencies:

```bash
# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
# On Mac/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Running the Scraper
Start the interactive command-line menu:

```bash
python menu.py
```
Just follow the on-screen prompts! You will be able to input your target URL, select your extraction options, and choose your export formats.

---

## 📂 Documentation

Detailed documentation is available in the `docs/` folder:

1. [User Guide](docs/USER_GUIDE.md) — Step-by-step instructions on how to use every feature.
2. [Features & Capabilities](docs/FEATURES.md) — A breakdown of what makes this scraper enterprise-ready (perfect for showing to clients).
3. [Troubleshooting](docs/TROUBLESHOOTING.md) — How to fix common errors like timeouts or bot-blocks.

---

## 💎 Why Web Scraper 3.0?

* **Dual Engine Architecture**: Use the Lightning-fast HTTPX engine for standard sites, or the Headless Playwright browser for complex React/Vue/Angular sites.
* **Auto-Cleaning Data**: All data is automatically sanitized, formatted, and deduplicated before export.
* **Big Data Ready**: Supports JSON-Lines (JSONL) exporting for processing millions of records without crashing RAM.
* **Deliverable Ready**: Automatically generates a `DATA_DICTIONARY.md` and `SCRAPING_REPORT.txt` for your clients with every run.

---
*Built for Data Professionals. Happy Scraping!*
