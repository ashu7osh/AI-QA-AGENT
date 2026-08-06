"""
Central logging configuration.

Junior engineers print(). QA engineers with a year of experience configure
a logger once and import it everywhere, so every module's output is
timestamped, leveled, and goes to both the console AND a persistent log
file (useful for debugging a CI run after the fact, when you can't just
watch the terminal live).
"""

import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        # Already configured (avoids duplicate handlers on repeated imports)
        return logger

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "ai_qa_agent.log"),
        maxBytes=2_000_000,
        backupCount=3,
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
