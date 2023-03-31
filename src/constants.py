import socket
from typing import Final


ACTIVE_TIMELAPSES_DIR: Final[str] = "data/timelapses/active"
FINISHED_TIMELAPSES_DIR: Final[str] = "data/timelapses/finished"
INCOMPLETE_TIMELAPSES_DIR: Final[str] = "data/timelapses/incomplete"

HOST_NAME = socket.gethostname()
PORT = 5000