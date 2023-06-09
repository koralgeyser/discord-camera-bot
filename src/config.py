from dataclasses import dataclass
import dataclasses
import json
from typing import Final, List

from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class Config:
    discord_token: str
    bot_command_prefix: str
    dev_guild_id: int
    dev_channel_id: int
    drive_folder_id: str
    owners: List[int]

    def update(self):
        with open("config.json", mode="wt") as fs:
            json.dump(dataclasses.asdict(self), fs, indent=4)

    # def __del__(self):
    #     with open("config.json", mode="wt") as fs:
    #         json.dump(dataclasses.asdict(self), fs)


with open("config.json") as fs:
    CONFIG: Final[Config] = Config.from_json(fs.read())
