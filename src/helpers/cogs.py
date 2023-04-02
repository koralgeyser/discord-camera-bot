import os
import constants

def get_cogs():
    return [file[:-3] for file in os.listdir(constants.COGS_DIR) if file.endswith(".py") and not file.startswith("__init__")]

