"""
app/core/logger.py — Centralized Structured Logger
────────────────────────────────────────────────────
Configures Python standard logging with formatted output for production monitoring.
"""

import sys
import logging

# Format: 2026-08-13 12:00:00 [INFO] [app.services.rag_service]: Message
LOG_FORMAT = "%(asctime)s [%(levelname)s] [%(name)s]: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=DATE_FORMAT,
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("campusmind")
