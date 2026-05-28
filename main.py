"""Application entry point for Cherry AI.

The entry point stays intentionally small: load configuration, initialize
cross-cutting systems, and hand control to the UI. This keeps the app ready for
future background workers, agents, and service orchestration without putting
business logic in the startup script.
"""

from __future__ import annotations

import argparse
import logging
import sys

from config.settings import AppSettings, load_settings
from database.init_db import initialize_database
from utils.logging import configure_logging


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cherry AI desktop assistant")
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="Run startup checks without opening the PyQt window.",
    )
    return parser.parse_args()


def bootstrap() -> AppSettings:
    """Initialize process-level systems required by both UI and workers."""
    settings = load_settings()
    configure_logging(settings)

    logger = logging.getLogger(__name__)
    logger.info("Starting Cherry AI")
    logger.info("Environment: %s", settings.app_env)
    logger.info("Project root: %s", settings.project_root)

    initialize_database(settings)
    logger.info("Database initialized: %s", settings.database_url)

    return settings


def main() -> int:
    args = parse_args()
    settings = bootstrap()

    if args.no_gui:
        logging.getLogger(__name__).info("Startup check completed without GUI")
        return 0

    # Import PyQt only after bootstrap so command-line health checks can run in
    # non-GUI environments such as future CI containers.
    from frontend.app import run_app

    return run_app(settings)


if __name__ == "__main__":
    sys.exit(main())
