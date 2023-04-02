import logging
import os
import shutil
import traceback
import discord
import cameras
from discord.ext.commands import Bot
import constants
import helpers.cogs
import logging.handlers
import cogs
import checks
import config

class CameraBot(Bot):
    def __init__(self) -> None:
        super().__init__(
            command_prefix=None,
            intents=discord.Intents.default(),
            help_command=None,
            activity=discord.Activity(type=discord.ActivityType.watching, name="the lab"),
            log_handler=None
        )

        self.logger = logging.getLogger('discord')
        self.logger.setLevel(logging.DEBUG)
        logging.getLogger('discord.http').setLevel(logging.INFO)

        handler = logging.handlers.RotatingFileHandler(
            filename=f"{constants.LOGS_DIR}/discord.log",
            encoding='utf-8',
            maxBytes=5 * 1024 * 1024,  # 32 MiB
            backupCount=5,  # Rotate through 5 files
        )
        dt_fmt = '%Y-%m-%d %H:%M:%S'
        formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        self.on_app_command_error = self.tree.error(self.on_app_command_error)

    async def on_ready(self):
        self.logger.info(f"Logged in as {self.user.name} (ID: {self.user.id})")
        self.logger.info(f"Camera Module: {cameras.camera_instance}")
        self.logger.info("------")

    async def load_cogs(self):
        for cog in helpers.cogs.get_cogs():
            try:
                await self.load_extension(f"{cogs.__name__}.{cog}")
                self.logger.info(f"Loaded '{cog}' cog")
            except Exception:
                self.logger.info(f"Failed to load '{cog}' cog")
                self.logger.error(traceback.format_exc())

    async def setup_hook(self):
        await self.load_cogs()
        guild = discord.Object(id=constants.DEV_GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        # await self.tree.sync(guild=guild)


    async def on_app_command_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        error_msg = "An error has occurred."
        if isinstance(error, checks.NotOwnerError):
            if interaction.response.is_done():
                return await interaction.followup.send(str(error), ephemeral=True)
            else:
                return await interaction.response.send_message(str(error), ephemeral=True)
        else:
            if interaction.response.is_done():
                await interaction.followup.send(error_msg, ephemeral=True)
            else:
                await interaction.response.send_message(error_msg, ephemeral=True)
            
            embed = discord.Embed(
                title=f"{type(error.__cause__).__name__}",
                description=traceback.format_exc()
            ).add_field(
                name="Data",
                value=str(interaction.data)
            )

            await self.get_channel(constants.DEV_CHANNEL_ID).send(embed=embed)
            self.logger.error(traceback.format_exc())


def initialize_dirs():
    import constants
    if not os.path.exists(constants.ACTIVE_TIMELAPSES_DIR):
        os.makedirs(constants.ACTIVE_TIMELAPSES_DIR)
    if not os.path.exists(constants.FINISHED_TIMELAPSES_DIR):
        os.makedirs(constants.FINISHED_TIMELAPSES_DIR)
    if not os.path.exists(constants.INCOMPLETE_TIMELAPSES_DIR):
        os.makedirs(constants.INCOMPLETE_TIMELAPSES_DIR)

    # Move any active timelapses that are now in limbo due to w/e reason to incomplete 
    for dir in os.listdir(constants.ACTIVE_TIMELAPSES_DIR):
        shutil.move(
            f"{constants.ACTIVE_TIMELAPSES_DIR}/{dir}",
            constants.INCOMPLETE_TIMELAPSES_DIR
        )

def run():
    initialize_dirs()
    bot = CameraBot()
    bot.run(config.CONFIG.discord_token)


if __name__ == "__main__":
    run()