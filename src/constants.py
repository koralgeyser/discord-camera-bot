import os
import socket
from typing import Final

import discord


ACTIVE_TIMELAPSES_DIR: Final[str] = "data/timelapses/active"
FINISHED_TIMELAPSES_DIR: Final[str] = "data/timelapses/finished"
INCOMPLETE_TIMELAPSES_DIR: Final[str] = "data/timelapses/incomplete"
COGS_DIR: Final[str] = f"{os.path.realpath(os.path.dirname(__file__))}/cogs"
LOGS_DIR: Final[str] = "data/logs"

HOST_NAME: Final[str] = socket.gethostname()
PORT: Final[int] = 5000

DEV_GUILD_ID: Final[discord.Object] = 785334707277398026
DEV_CHANNEL_ID: Final[int] = 1091836580173451384
