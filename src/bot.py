import logging
import os
import traceback
import discord
import cameras
from discord.ext import commands
import constants
import logging.handlers
import checks
import config
import helpers

class CameraBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        # intents.members = True
        # intents.message_content = True

        super().__init__(
            command_prefix=config.CONFIG.bot_command_prefix,
            intents=intents,
            help_command=None,
            activity=discord.Activity(
                type=discord.ActivityType.watching, name="the lab"
            ),
            log_handler=None,
        )
        self._setup_logger()
        self.tree.error(self.on_app_command_error)
        self.load_cogs_success = True

    def _setup_logger(self):
        self.logger = logging.getLogger("discord")
        self.logger.setLevel(logging.DEBUG)
        logging.getLogger("discord.http").setLevel(logging.INFO)

        handler = logging.handlers.RotatingFileHandler(
            filename=f"{constants.LOGS_DIR}/discord.log",
            encoding="utf-8",
            maxBytes=500 * 1000,  # 5 KB
            backupCount=5,  # Rotate through 5 files
        )
        dt_fmt = "%Y-%m-%d %H:%M:%S"
        formatter = logging.Formatter(
            "[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{"
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    async def on_ready(self):
        initialize_dirs()

        self.logger.info(f"Logged in as {self.user.name} (ID: {self.user.id})")
        self.logger.info(f"Camera Module: {cameras.camera_instance}")
        self.logger.info("------")
        if not self.load_cogs_success:
            await self.get_channel(config.CONFIG.dev_channel_id).send(
                "STARTUP: Failed to load all cogs."
            )

    async def load_cogs(self):
        import cogs

        for cog in helpers.list_cogs():
            try:
                await self.load_extension(f"{cogs.__name__}.{cog}")
                self.logger.info(f"Loaded '{cog}' cog")
            except:
                self.logger.info(f"Failed to load '{cog}' cog")
                self.logger.error(traceback.format_exc())
                self.load_cogs_success = False

    async def setup_hook(self):
        await self.load_cogs()
        guild = discord.Object(id=config.CONFIG.dev_guild_id)
        self.tree.copy_global_to(guild=guild)
        # await self.tree.sync(guild=guild)

    async def on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: discord.app_commands.AppCommandError,
    ):
        error_msg = "An error has occurred."
        if isinstance(error, checks.NotOwnerError):
            if interaction.response.is_done():
                return await interaction.followup.send(str(error), ephemeral=True)
            else:
                return await interaction.response.send_message(
                    str(error), ephemeral=True
                )
        else:
            if interaction.response.is_done():
                await interaction.followup.send(error_msg, ephemeral=True)
            else:
                await interaction.response.send_message(error_msg, ephemeral=True)
        await self.log_error(error.__cause__)

    async def log_error(self, e: Exception):
        embed = discord.Embed(
            title=f"{type(e).__name__}", description=traceback.format_exc()
        )

        await self.get_channel(config.CONFIG.dev_channel_id).send(embed=embed)
        self.logger.error(traceback.format_exc())


def initialize_dirs():
    import constants
    if not os.path.exists(constants.TIMELAPSES_DIR):
        os.makedirs(constants.TIMELAPSES_DIR)

# @commands.is_owner()
# @bot.command()
# async def safemode_update(
#     ctx: commands.Context,
#     branch: str,
# ):
#     """Update bot."""
#     bot: commands.Bot = ctx.bot
#     msg = await ctx.send("Are you sure you want me to update?")
#     yes_react = "✅"
#     no_react = "❎"
#     reactions = [yes_react, no_react]
#     for react in reactions:
#         msg.add_reaction(react)

#     def check(reaction: discord.Reaction, user: discord.User) -> bool:
#         return user == ctx.author and reaction.emoji == yes_react
    
#     try:
#         x = await bot.wait_for("reaction_add", check=check, timeout=5.0)
#         print(x)
#     except asyncio.TimeoutError:
#         return await msg.channel.send("Timed out.")

#     # helpers.update(branch)

def run():
    bot = CameraBot()
    bot.run(config.CONFIG.discord_token, reconnect=True)


if __name__ == "__main__":
    run()