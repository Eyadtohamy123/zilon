"""
Web Scraper 4.0 — Data Exporter with Incremental Crash-Safe Writing
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Streams data to disk in batches. If the script crashes at page 99,000,
you still have all previously flushed rows safely on disk.
"""
import os
import json
import logging
import sqlite3
import threading
import pandas as pd
from datetime import datetime
import re

from data_cleaner import sanitize_dataframe

logger = logging.getLogger("WebScraper3.0")

DATA_LABELS = {
    "metadata": "📋 Page Metadata & SEO",
    "text": "📝 Full Page Text",
    "headings": "🔤 Headings (H1-H6)",
    "images": "🖼️  Images & Media",
    "links": "🔗 Links & Navigation",
    "tables": "📊 Tables",
    "ecommerce": "🛒 E-Commerce Products",
    "ai_insights": "🤖 AI Insights",
    "custom": "🎯 Custom Selectors",
    "crawl_log": "📜 Crawl Log",
}


# ═══════════════════════════════════════════════════════════════════════════
#  INCREMENTAL EXPORTER — Crash-Safe Streaming to Disk
# ═══════════════════════════════════════════════════════════════════════════

class IncrementalExporter:
    """
    Thread-safe incremental exporter that flushes data to .xlsx in batches.
    
    Usage:
        exporter = IncrementalExporter("output/site/run_xxx", "site_name", ["csv", "excel"])
        exporter.flush_batch(data_dict, crawl_log)  # Called every N pages
        exporter.finalize()                          # Called at end
    """

    def __init__(self, run_dir, site_name, formats):
        self.run_dir = run_dir
        self.site_name = site_name
        self.formats = formats
        self.lock = threading.RLock()  # RLock: reentrant so finalize() can call flush_batch()
        self.excel_row_counts = {}  # Track rows per sheet
        self.total_rows_flushed = 0
        self.flush_count = 0
        self._last_data_lengths = {}  # Track what we've already flushed

        os.makedirs(self.run_dir, exist_ok=True)
        self.dirs = {}
        for fmt in ["csv", "json", "jsonl", "excel", "sqlite"]:
            if fmt in self.formats:
                path = os.path.join(self.run_dir, fmt.upper())
                os.makedirs(path, exist_ok=True)
                self.dirs[fmt] = path

    @property
    def row_count(self) -> int:
        """Current total rows flushed to disk."""
        return self.total_rows_flushed

    def flush_batch(self, all_data: dict, crawl_log: list):
        """
        Incrementally append NEW data to files on disk.
        Only writes rows that haven't been flushed yet.
        Thread-safe via lock.
        """
        with self.lock:
            self.flush_count += 1
            new_data = self._get_new_data(all_data)
            
            if not new_data and not self._has_new_crawl_log(crawl_log):
                return
            
            logger.info(f"  💾 Flushing batch #{self.flush_count} to disk...")
            print(f"  💾 Flushing batch #{self.flush_count} to disk...")

            mapping = self._build_mapping(new_data, crawl_log)
            rows_this_batch = 0

            if "csv" in self.formats:
                for name, df in mapping.items():
                    csv_path = os.path.join(self.dirs["csv"], f"{name}.csv")
                    header = not os.path.exists(csv_path)
                    df.to_csv(csv_path, mode='a', index=False, encoding="utf-8-sig", header=header)
                    rows_this_batch += len(df)

            if "jsonl" in self.formats:
                for name, df in mapping.items():
                    jsonl_path = os.path.join(self.dirs["jsonl"], f"{name}.jsonl")
                    df.to_json(jsonl_path, orient="records", lines=True, force_ascii=False, mode='a')
                    
            self.total_rows_flushed += rows_this_batch
            
            # Track flushed positions
            for key, value in all_data.items():
                if isinstance(value, list):
                    self._last_data_lengths[key] = len(value)

    def _get_new_data(self, all_data: dict) -> dict:
        """Extract only the NEW records that haven't been flushed yet."""
        new_data = {}
        for key, value in all_data.items():
            if isinstance(value, list):
                last_len = self._last_data_lengths.get(key, 0)
                new_records = value[last_len:]
                if new_records:
                    new_data[key] = new_records
        return new_data

    def _has_new_crawl_log(self, crawl_log):
        last = self._last_data_lengths.get("_crawl_log", 0)
        return len(crawl_log) > last

    def finalize(self, all_data: dict, crawl_log: list):
        """
        Final export: write the complete dataset to Excel, JSON, SQLite.
        Also generates the report and data dictionary.
        """
        with self.lock:
            # First flush any remaining unflushed data to CSV/JSONL
            new_data = self._get_new_data(all_data)
            if new_data:
                self.flush_batch(all_data, crawl_log)

            mapping = self._build_full_mapping(all_data, crawl_log)
            files_saved = []
            total_datasets = len(mapping)
            print(f"  📊 Processing {total_datasets} datasets...")

            # Collect CSV/JSONL files already written
            for fmt in ["csv", "jsonl"]:
                if fmt in self.dirs and os.path.exists(self.dirs[fmt]):
                    for fname in os.listdir(self.dirs[fmt]):
                        files_saved.append(os.path.join(self.dirs[fmt], fname))

            if "json" in self.formats:
                print(f"  📋 Writing JSON files...")
                for name, df in mapping.items():
                    json_path = os.path.join(self.dirs["json"], f"{name}.json")
                    df.to_json(json_path, orient="records", force_ascii=False, indent=4)
                    files_saved.append(json_path)

            if "excel" in self.formats:
                print(f"  📊 Writing Excel workbook...")
                excel_path = os.path.join(self.dirs["excel"], f"{self.site_name}_COMPLETE.xlsx")
                try:
                    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
                        summary_data = []
                        for name, df in mapping.items():
                            label = DATA_LABELS.get(name, name.capitalize())
                            summary_data.append({
                                "Dataset": label,
                                "Sheet Name": name[:31].capitalize(),
                                "Records": len(df),
                                "Columns": len(df.columns),
                            })
                        pd.DataFrame(summary_data).to_excel(writer, sheet_name="Summary", index=False)
                        for name, df in mapping.items():
                            sheet_name = name[:31].capitalize()
                            self._sanitize_for_excel(df).to_excel(writer, sheet_name=sheet_name, index=False)
                            self.excel_row_counts[sheet_name] = len(df)
                    files_saved.append(excel_path)
                except Exception as e:
                    logger.error(f"  ✗ Failed to create Excel: {e}")

            if "sqlite" in self.formats:
                print(f"  🗄️  Writing SQLite database...")
                db_path = os.path.join(self.dirs["sqlite"], f"{self.site_name}.sqlite")
                try:
                    conn = sqlite3.connect(db_path)
                    for name, df in mapping.items():
                        df_sqlite = df.copy()
                        for col in df_sqlite.select_dtypes(include=['object']):
                            df_sqlite[col] = df_sqlite[col].apply(
                                lambda x: json.dumps(x) if isinstance(x, (dict, list)) else x
                            )
                        df_sqlite.to_sql(name, conn, if_exists="replace", index=False)
                    conn.close()
                    files_saved.append(db_path)
                except Exception as e:
                    logger.error(f"  ✗ Failed to create SQLite DB: {e}")

            print(f"  📝 Generating report and data dictionary...")
            report_path = self.create_report(mapping, crawl_log)
            files_saved.append(report_path)

            dict_path = self.create_dictionary(mapping)
            files_saved.append(dict_path)
            logger.info(f"  ✓ Report and Data Dictionary generated.")

            return files_saved

    def _build_mapping(self, data, crawl_log):
        mapping = {}
        for key, value in data.items():
            if value:
                records = value if isinstance(value, list) else [value]
                df = pd.DataFrame(records)
                if not df.empty:
                    df = sanitize_dataframe(df)
                    mapping[key] = df
        return mapping

    def _build_full_mapping(self, data, crawl_log):
        mapping = {}
        for key, value in data.items():
            if value:
                records = value if isinstance(value, list) else [value]
                df = pd.DataFrame(records)
                if not df.empty:
                    # Dedup
                    cols_to_check = [c for c in df.columns if c not in ('url', 'scraped_at')]
                    if cols_to_check:
                        before = len(df)
                        df = df.drop_duplicates(subset=cols_to_check, keep='first')
                        after = len(df)
                        if before - after > 0:
                            logger.info(f"  🧹 Removed {before - after} duplicate rows from {key}")
                    df = sanitize_dataframe(df)
                    mapping[key] = df

        if crawl_log:
            df_log = pd.DataFrame(crawl_log)
            if not df_log.empty:
                mapping["crawl_log"] = df_log
        return mapping

    def _sanitize_for_excel(self, df):
        _ILLEGAL_XML_RE = re.compile(
            r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\ud800-\udfff\ufdd0-\ufdef\ufffe\uffff]'
        )
        for col in df.select_dtypes(include=["object", "string"]).columns:
            df[col] = df[col].apply(
                lambda x: _ILLEGAL_XML_RE.sub("", str(x)) if pd.notnull(x) else x
            )
        return df

    def create_report(self, mapping, crawl_log):
        report_path = os.path.join(self.run_dir, "SCRAPING_REPORT.txt")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("═" * 60 + "\n")
            f.write("  WEB SCRAPER 4.0 — ENTERPRISE SCRAPING REPORT\n")
            f.write("═" * 60 + "\n\n")
            f.write(f"  Target:      {self.site_name}\n")
            f.write(f"  Run Date:    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"  Formats:     {', '.join(f.upper() for f in self.formats)}\n")
            f.write(f"  Total Rows:  {self.total_rows_flushed:,}\n\n")

            f.write("─" * 60 + "\n")
            f.write("  CRAWL STATISTICS\n")
            f.write("─" * 60 + "\n")
            if crawl_log:
                total = len(crawl_log)
                successes = sum(1 for log in crawl_log if str(log.get('status_code', '')).startswith('2'))
                errors = sum(1 for log in crawl_log if log.get('status_code') == 'ERROR')
                f.write(f"  Total Pages Attempted:  {total}\n")
                f.write(f"  Successful (2xx):       {successes}\n")
                f.write(f"  Failed:                 {errors}\n\n")
            else:
                f.write("  No crawl data recorded.\n\n")

            f.write("─" * 60 + "\n")
            f.write("  DATA EXTRACTED (Unique Rows)\n")
            f.write("─" * 60 + "\n")
            for name, df in mapping.items():
                label = DATA_LABELS.get(name, name.capitalize())
                f.write(f"  {label}: {len(df):,} records ({len(df.columns)} columns)\n")

            f.write("\n" + "─" * 60 + "\n")
            f.write("  OUTPUT FILES\n")
            f.write("─" * 60 + "\n")
            for fmt_dir_name, fmt_path in self.dirs.items():
                f.write(f"  📁 {fmt_dir_name.upper()}/\n")
                if os.path.exists(fmt_path):
                    for fname in sorted(os.listdir(fmt_path)):
                        fsize = os.path.getsize(os.path.join(fmt_path, fname))
                        f.write(f"     └── {fname} ({self._human_size(fsize)})\n")
        return report_path

    def create_dictionary(self, mapping):
        dict_path = os.path.join(self.run_dir, "DATA_DICTIONARY.md")
        with open(dict_path, "w", encoding="utf-8") as f:
            f.write(f"# Data Dictionary: {self.site_name}\n\n")
            f.write(f"> Generated by Web Scraper 4.0 on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("This document outlines the schema of the exported datasets.\n\n")

            for name, df in mapping.items():
                f.write(f"## Dataset: `{name}`\n")
                f.write(f"**Rows**: {len(df):,}\n\n")
                f.write("| Column Name | Data Type | Non-Null Count | Sample Value |\n")
                f.write("|-------------|-----------|----------------|--------------|\n")

                for col in df.columns:
                    dtype = str(df[col].dtype)
                    non_null = df[col].notna().sum()
                    sample = ""
                    if non_null > 0:
                        valid_vals = df[col].dropna()
                        if not valid_vals.empty:
                            sample = str(valid_vals.iloc[0])[:50].replace('\n', ' ')
                    f.write(f"| `{col}` | {dtype} | {non_null:,} | {sample} |\n")
                f.write("\n---\n\n")
        return dict_path

    @staticmethod
    def _human_size(size_bytes):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"


# ── Legacy Compatibility Wrapper ─────────────────────────────────────────
# Keep DataExporter name working for gui_server.py and other callers

class DataExporter(IncrementalExporter):
    """Legacy wrapper: calls finalize() in export_all() for backwards compat."""

    def __init__(self, base_output_dir, site_name, formats):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        run_dir = os.path.join(base_output_dir, f"run_{timestamp}")
        super().__init__(run_dir, site_name, formats)

    def export_all(self, data, crawl_log):
        return self.finalize(data, crawl_log)
