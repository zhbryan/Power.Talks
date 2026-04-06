"""
scheduler.py — Power.Talks
Runs the downloader + study pipeline every night at midnight.
Keep this script running as a background process: python scheduler.py
"""

import logging
import os
import sys
from datetime import datetime

import schedule
import time

# ---------------------------------------------------------------------------
# Ensure imports resolve relative to the project root
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "Database Codes"))

import downloader
import study

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

RUN_TIME = "00:00"  # 24-hour format — change here to reschedule

LOG_FILE = os.path.join(BASE_DIR, "Database Codes", "scheduler.log")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Job
# ---------------------------------------------------------------------------

def nightly_job():
    start = datetime.now()
    log.info("━━━ Nightly job started: %s ━━━", start.strftime("%Y-%m-%d %H:%M:%S"))

    # Step 1: Download new documents
    try:
        log.info("--- Step 1: Downloader ---")
        downloaded = downloader.run()
        log.info("Downloader complete. New files: %d", downloaded)
    except Exception as e:
        log.error("Downloader failed: %s", e, exc_info=True)

    # Step 2: Summarize documents
    try:
        log.info("--- Step 2: Study ---")
        reports = study.run()
        log.info("Study complete. New reports: %d", reports)
    except Exception as e:
        log.error("Study failed: %s", e, exc_info=True)

    elapsed = (datetime.now() - start).total_seconds()
    log.info("━━━ Nightly job finished in %.1fs ━━━", elapsed)


# ---------------------------------------------------------------------------
# Schedule & Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    log.info("Scheduler started. Nightly job scheduled at %s.", RUN_TIME)
    schedule.every().day.at(RUN_TIME).do(nightly_job)

    log.info("Next run: %s", schedule.next_run())
    log.info("Press Ctrl+C to stop.")

    while True:
        schedule.run_pending()
        time.sleep(30)
