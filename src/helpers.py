import sys
from typing import List
import os
import constants


def get_autocomplete(query, choices: List):
    return list(filter(lambda x: query.lower() in x.lower(), choices))[:25]


def get_cogs():
    return [
        file[:-3]
        for file in os.listdir(constants.COGS_DIR)
        if file.endswith(".py") and not file.startswith("__init__")
    ]


def restart():
    os.execv(sys.executable, ["python"] + sys.argv)
