"""
Web Scraper 3.0 — Enterprise Web GUI
Flask backend that bridges the scraping engines to the browser UI.
"""
import asyncio
import json
import logging
import os
import sys
import threading
from datetime import datetime

from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_socketio import SocketIO, emit

# Add the scraper directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine_fast import FastEngine, get_domain, make_safe_filename
from engine_browser import BrowserEngine
from exporter import IncrementalExporter

app = Flask(__name__, template_folder="gui/templates", static_folder="gui/static")
app.config["SECRET_KEY"] = "webscraper30_secret"
socketio = SocketIO(app, async_mode="threading", cors_allowed_origins="*")

# Global job state
active_job = {"running": False, "thread": None}

class SocketIOLogHandler(logging.Handler):
    """Streams log messages to the browser in real-time via WebSocket."""
    def emit(self, record):
        msg = self.format(record)
        level = record.levelname.lower()
        socketio.emit("log", {"message": msg, "level": level})

def setup_socket_logging():
    handler = SocketIOLogHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s  %(message)s", "%H:%M:%S"))
    logging.getLogger("WebScraper3.0").addHandler(handler)
    logging.getLogger("WebScraper3.0").setLevel(logging.INFO)

setup_socket_logging()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/runs")
def list_runs():
    """Returns all previous scraping run folders."""
    output_base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    runs = []
    if os.path.exists(output_base):
        for site in sorted(os.listdir(output_base)):
            site_dir = os.path.join(output_base, site)
            if not os.path.isdir(site_dir):
                continue
            for run in sorted(os.listdir(site_dir), reverse=True):
                run_dir = os.path.join(site_dir, run)
                if not os.path.isdir(run_dir) or not run.startswith("run_"):
                    continue
                # Read report if exists
                report_path = os.path.join(run_dir, "SCRAPING_REPORT.txt")
                report_snippet = ""
                if os.path.exists(report_path):
                    with open(report_path, "r") as f:
                        report_snippet = f.read()
                # Count files
                file_count = sum(
                    len(files) for _, _, files in os.walk(run_dir)
                )
                runs.append({
                    "site": site,
                    "run": run,
                    "path": run_dir,
                    "file_count": file_count,
                    "report": report_snippet,
                })
    return jsonify(runs)


@app.route("/api/run_files/<path:run_path>")
def list_run_files(run_path):
    """Returns files for a specific run directory."""
    output_base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    full_path = os.path.join(output_base, run_path)
    if not os.path.exists(full_path):
        return jsonify([])
    files = []
    for root, dirs, fnames in os.walk(full_path):
        for fname in fnames:
            fpath = os.path.join(root, fname)
            files.append({
                "name": fname,
                "rel_path": os.path.relpath(fpath, output_base),
                "size": os.path.getsize(fpath),
                "folder": os.path.basename(root),
            })
    return jsonify(files)


@app.route("/api/download/<path:rel_path>")
def download_file(rel_path):
    """Serves a file for download."""
    output_base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    directory = os.path.join(output_base, os.path.dirname(rel_path))
    filename = os.path.basename(rel_path)
    return send_from_directory(directory, filename, as_attachment=True)


@socketio.on("start_job")
def handle_start_job(config):
    """Receives job config from browser and starts scraping in a background thread."""
    global active_job
    if active_job["running"]:
        emit("log", {"message": "⚠ A job is already running!", "level": "warning"})
        return

    active_job["running"] = True
    emit("job_started", {})

    def run_job():
        try:
            url = config.get("url", "").strip()
            if not url.startswith(("http://", "https://")):
                url = "https://" + url

            domain_safe = make_safe_filename(get_domain(url))
            output_base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
            output_dir = os.path.join(output_base, domain_safe)

            html_dir = ""
            if config.get("save_html"):
                html_dir = os.path.join(output_dir, "HTML_DUMPS")
                os.makedirs(html_dir, exist_ok=True)

            img_dir = ""
            if config.get("download_images"):
                img_dir = os.path.join(output_dir, "IMAGES")
                os.makedirs(img_dir, exist_ok=True)

            os.makedirs(output_dir, exist_ok=True)

            engine_config = {
                "url": url,
                "max_pages": int(config.get("max_pages", 50)),
                "depth": int(config.get("depth", 3)),
                "extract_options": config.get("extract_options", ["metadata", "text", "links"]),
                "extract_patterns": config.get("extract_patterns", False),
                "custom_selectors": config.get("custom_selectors", {}),
                "save_html": config.get("save_html", False),
                "html_dir": html_dir,
                "download_images": config.get("download_images", False),
                "img_dir": img_dir,
                "proxy": config.get("proxy") or None,
            }

            # AI Configuration
            use_ai = "ai_insights" in config.get("extract_options", [])
            engine_config["use_ai_extraction"] = use_ai
            engine_config["ai_model"] = config.get("ai_model", "llama3.2")
            engine_config["ai_prompt"] = config.get("ai_prompt", "")
            engine_config["max_concurrent"] = int(config.get("max_concurrent", 25))
            engine_config["batch_size"] = int(config.get("batch_size", 100))
            engine_config["request_timeout"] = int(config.get("request_timeout", 30))

            # Export setup
            formats = config.get("formats", ["csv", "excel"])
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            run_dir = os.path.join(output_dir, f"run_{timestamp}")
            exporter = IncrementalExporter(run_dir, domain_safe, formats)

            # Run the engine
            engine_type = config.get("engine", "fast")
            if engine_type == "browser":
                engine = BrowserEngine(engine_config)
            else:
                engine = FastEngine(engine_config)

            # Wire up incremental exporter callback
            def on_batch_ready(data, crawl_log):
                exporter.flush_batch(data, crawl_log)
                socketio.emit("log", {"message": f"Flushed batch. Total rows: {exporter.row_count}", "level": "info"})
            engine.on_batch_ready = on_batch_ready

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            data, crawl_log = loop.run_until_complete(engine.run())
            loop.close()

            # Finalize Export
            socketio.emit("log", {"message": "Finalizing exports to disk...", "level": "info"})
            files = exporter.finalize(data, crawl_log)

            # Build file list for the UI
            file_list = []
            for f in files:
                if os.path.exists(f):
                    rel = os.path.relpath(f, output_base)
                    file_list.append({
                        "name": os.path.basename(f),
                        "rel_path": rel,
                        "size": os.path.getsize(f),
                        "folder": os.path.basename(os.path.dirname(f)),
                    })

            socketio.emit("job_complete", {
                "files": file_list,
                "run_dir": exporter.run_dir,
                "pages_scraped": len(crawl_log),
            })

        except Exception as e:
            socketio.emit("job_error", {"message": str(e)})
            logging.getLogger("WebScraper3.0").error(f"Job failed: {e}")
        finally:
            active_job["running"] = False

    t = threading.Thread(target=run_job, daemon=True)
    active_job["thread"] = t
    t.start()


@socketio.on("stop_job")
def handle_stop_job():
    global active_job
    active_job["running"] = False
    emit("log", {"message": "⛔ Stop requested. Job will finish current page and halt.", "level": "warning"})


if __name__ == "__main__":
    print("\n  🕸️  Web Scraper 3.0 — Enterprise GUI")
    print("  ─────────────────────────────────────")
    print("  Open your browser at: http://127.0.0.1:5000")
    print("  Press Ctrl+C to stop.\n")
    socketio.run(app, host="127.0.0.1", port=5000, debug=False, allow_unsafe_werkzeug=True)
