import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler


def setup_logging(config):
    log_dir = Path(config.get("log_dir", "logs"))
    log_dir.mkdir(parents=True, exist_ok=True)

    level = getattr(logging, config.get("level", "INFO").upper(), logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        log_dir / "server.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    if config.get("journal_network_traffic", True):
        journal_handler = RotatingFileHandler(
            log_dir / "network_journal.jsonl",
            maxBytes=50 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8"
        )
        journal_handler.setLevel(logging.DEBUG)
        journal_handler.setFormatter(logging.Formatter("%(message)s"))
        for name in ("journal.network", "journal.http"):
            journal_logger = logging.getLogger(name)
            journal_logger.addHandler(journal_handler)
            journal_logger.setLevel(logging.DEBUG)
            journal_logger.propagate = False

    if config.get("journal_unknown_commands", True):
        unknown_handler = RotatingFileHandler(
            log_dir / "unknown_commands.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8"
        )
        unknown_handler.setLevel(logging.DEBUG)
        unknown_handler.setFormatter(
            logging.Formatter("%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        )
        unknown_logger = logging.getLogger("journal.unknown")
        unknown_logger.addHandler(unknown_handler)
        unknown_logger.setLevel(logging.DEBUG)
