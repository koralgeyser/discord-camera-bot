import os
from typing import Final

ACTIVE_TIMELAPSES_DIR: Final[str] = "data/timelapses/active"
FINISHED_TIMELAPSES_DIR: Final[str] = "data/timelapses/finished"
INCOMPLETE_TIMELAPSES_DIR: Final[str] = "data/timelapses/incomplete"
COGS_DIR: Final[str] = f"{os.path.realpath(os.path.dirname(__file__))}/cogs"
LOGS_DIR: Final[str] = "data/logs"

PORT: Final[int] = 5000