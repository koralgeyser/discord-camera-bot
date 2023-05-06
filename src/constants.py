import os
from typing import Final

TIMELAPSES_DIR: Final[str] = "data/timelapses"
COGS_DIR: Final[str] = f"{os.path.realpath(os.path.dirname(__file__))}/cogs"
LOGS_DIR: Final[str] = "data/logs"

PORT: Final[int] = 5000