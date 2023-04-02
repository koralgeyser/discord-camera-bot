
from typing import Callable, Optional, TypeVar, Union
from discord import Interaction
from discord import app_commands
from discord.ext import commands
import config

T = TypeVar('T')

class NotOwnerError(app_commands.errors.CheckFailure):
    def __init__(self, message: Optional[str] = None) -> None:
        super().__init__(message or "Only owners of this bot can use this command.")

def is_owner() -> Callable[[T], T]:
    def predicate(interaction: Interaction) -> bool:
        if interaction.user.id in config.CONFIG.owners:
            return True
        else:
            raise NotOwnerError()

    return app_commands.check(predicate)