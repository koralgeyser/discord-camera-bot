import io
import logging
import os
import shutil
import subprocess
import sys
import traceback
import typing
import zipfile
import discord
import requests
import cameras
from discord.ext.commands import Bot
import constants
import logging.handlers
import cogs
import checks
import config
import helpers
from views.confirm_view import ConfirmView
from discord import app_commands


class CameraBot(Bot):
    def __init__(self) -> None:
        super().__init__(
            command_prefix=None,
            intents=discord.Intents.default(),
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
            maxBytes=5 * 1024 * 1024,  # 32 MiB
            backupCount=5,  # Rotate through 5 files
        )
        dt_fmt = "%Y-%m-%d %H:%M:%S"
        formatter = logging.Formatter(
            "[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{"
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    async def on_ready(self):
        self.logger.info(f"Logged in as {self.user.name} (ID: {self.user.id})")
        self.logger.info(f"Camera Module: {cameras.camera_instance}")
        self.logger.info("------")
        if not self.load_cogs_success:
            await self.get_channel(constants.DEV_CHANNEL_ID).send(
                "STARTUP: Failed to load all cogs."
            )

    async def load_cogs(self):
        for cog in helpers.get_cogs():
            try:
                await self.load_extension(f"{cogs.__name__}.{cog}")
                self.logger.info(f"Loaded '{cog}' cog")
            except:
                self.logger.info(f"Failed to load '{cog}' cog")
                self.logger.error(traceback.format_exc())
                self.load_cogs_success = False

    async def setup_hook(self):
        await self.load_cogs()
        guild = discord.Object(id=constants.DEV_GUILD_ID)
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
            constants.INCOMPLETE_TIMELAPSES_DIR,
        )


def run():
    initialize_dirs()

    bot = CameraBot()

    @checks.is_owner()
    @app_commands.describe(
        branch="Branch to update from. Defaults to 'main'.",
        auto_restart="Auto restart after updating? Defaults to False.",
    )
    @bot.tree.command()
    async def safemode_update(
        interaction: discord.Interaction,
        branch: typing.Optional[str] = "main",
        auto_restart: typing.Optional[bool] = False,
    ):
        """Update bot."""
        view = ConfirmView()
        TMP_DIR = "tmp/"
        if os.path.exists(TMP_DIR):
            shutil.rmtree(TMP_DIR)
        await interaction.response.send_message(
            "Are you sure you want me to update?", view=view, ephemeral=True
        )
        await view.wait(interaction)
        if view.value:
            await interaction.followup.send("Updating...", ephemeral=True)

            try:
                url = f"https://github.com/koralgeyser/discord-camera-bot/archive/refs/heads/{branch}.zip"
                r = requests.get(url, allow_redirects=True)
                buffer = io.BytesIO(r.content)

                with zipfile.ZipFile(buffer, "r") as zip:
                    zip.extractall(TMP_DIR)

                path = os.path.join(TMP_DIR, os.listdir(TMP_DIR)[0])
                requirements = os.path.join(path, "requirements.txt")
                subprocess.run(
                    f"{sys.executable} -m pip install -r {requirements}"
                ).check_returncode()
                shutil.copytree(path, os.getcwd(), dirs_exist_ok=True)

                if auto_restart:
                    await interaction.followup.send(
                        "Update complete. Restarting now...", ephemeral=True
                    )
                    helpers.restart()
                else:
                    await interaction.followup.send("Update complete.", ephemeral=True)
            except Exception as e:
                raise e
            finally:
                shutil.rmtree(TMP_DIR)

    bot.run(config.CONFIG.discord_token, reconnect=True)


if __name__ == "__main__":
    run()
