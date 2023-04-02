from dataclasses import dataclass
import dataclasses
import json
from typing import Final, List

from dataclasses_json import dataclass_json

@dataclass_json
@dataclass
class Config:
    discord_token: str
    owners: List[int]

    def update(self):
        with open("config.json", mode="wt") as fs:
            json.dump(dataclasses.asdict(self), fs)

    # def __del__(self):
    #     with open("config.json", mode="wt") as fs:
    #         json.dump(dataclasses.asdict(self), fs)
    
with open("config.json") as fs:
    CONFIG: Final[Config] = Config.from_json(fs.read())