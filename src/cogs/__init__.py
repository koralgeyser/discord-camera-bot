from discord.ext import commands
from bot import CameraBot


class BaseCog(commands.Cog):
    def __init__(self, bot: CameraBot):
        super().__init__()
        self.bot = bot

    async def on_task_error(self, e: Exception):
        await self.bot.log_error(e)
