import asyncio
import datetime
import io
import json
import os
import shutil
import socket
import time
import discord
from discord import app_commands
import numpy as np
from discord.ext import tasks
import constants
from bot import CameraBot
import helpers
from views.confirm_view import ConfirmView
from config import CONFIG
from cogs import BaseCog

class CameraCog(BaseCog):
    is_timelapse_active = False
    camera_group = app_commands.Group(name="camera", description="Camera")
    timelapse_group = app_commands.Group(name="timelapse", description="Timelapse")

    camera_group.add_command(timelapse_group)

    @app_commands.describe(
        interval="Time interval in seconds.", count="Number of snaps.", name="Name of timelapse."
    )
    @timelapse_group.command(name="start")
    async def timelapse_start(
        self,
        interaction: discord.Interaction,
        interval: int,
        count: int,
        name: str,
    ):
        """Start a timelapse. Only one timelapse can be running at a time."""
        # Only allow one for now
        if self.is_timelapse_active:
            await interaction.response.send_message(
                "Failed to start. There is currently an active timelapse."
            )
        elif os.path.isdir(f"{constants.FINISHED_TIMELAPSES_DIR}/{name}"):
            await interaction.response.send_message(
                "Failed to start. This name already exists."
            )
        else:
            async def finished_timelapse_task():
                user = interaction.user
                channel = interaction.channel

                if task.failed():
                    await channel.send(
                        f"{user.mention} An error has occurred with the timelapse."
                    )
                else:
                    await asyncio.to_thread(helpers.upload_to_google_folder,
                        f"{name}.zip",
                        CONFIG.drive_folder_id,
                        helpers.get_timelapse_data(name)
                    )
                    await channel.send(
                        f"{user.mention} '{name}' timelapse has finished: https://drive.google.com/drive/folders/{CONFIG.drive_folder_id}?usp=sharing.",
                    )

            task = tasks.loop(count=1)(self.start_timelapse_task)
            task.error(self.on_task_error)
            task.after_loop(finished_timelapse_task)
            task.start(interval, count, name)

            await interaction.response.send_message(f"Timelapse '{name}' has started. ETA: {datetime.timedelta(seconds=interval * count)}")

    @timelapse_group.command(name="cancel")
    async def timelapse_cancel(self, interaction: discord.Interaction):
        """Cancels current running timelapse."""
        view = ConfirmView()

        await interaction.response.send_message(
            "Are you sure you want to cancel the timelapse?", view=view, ephemeral=True
        )
        await view.wait(interaction)
        if view.value:
            if self.is_timelapse_active:
                self.is_timelapse_active = False
                await interaction.channel.send(
                    f"Timelapse was canceled by {interaction.user.mention}."
                )
            else:
                await interaction.followup.send(
                    "There was no active timelapse to cancel.", ephemeral=True
                )

    @timelapse_group.command(name="progress")
    async def timelapse_progress(self, interaction: discord.Interaction):
        """Get progress of timelapse."""
        if self.is_timelapse_active:
            await interaction.response.send_message(
                f"{self.progress}/{self.total} completed. ETA: {datetime.timedelta(seconds=self.interval * (self.total - self.progress))}",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "There is no active timelapse.", ephemeral=True
            )


    @timelapse_group.command(name="list")
    async def timelapse_list(self, interaction: discord.Interaction):
        """Get link to timelapses."""
        await interaction.response.send_message(
            f"https://drive.google.com/drive/folders/{CONFIG.drive_folder_id}?usp=sharing.",
            ephemeral=True,
        )

    @camera_group.command(name="snap")
    async def snap(self, interaction: discord.Interaction):
        """Gets a snap from the camera."""
        import cameras
        from PIL import Image

        await interaction.response.defer()

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, cameras.camera_instance.snap)

        snap = cameras.camera_instance.snap()
        buffer = io.BytesIO()
        img = Image.fromarray(snap)

        # Hardcoding ext for now
        with io.BytesIO() as buffer:
            img.save(buffer, "PNG", optimize=True)
            buffer.seek(0)
            await interaction.followup.send(
                file=discord.File(fp=buffer, filename="snap.png")
            )

    @camera_group.command(name="feed")
    async def camera_feed(self, interaction: discord.Interaction):
        """Get link to camera feed. Can only view on local network."""
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)

        await interaction.response.send_message(
            f"View at http://{ip}:{constants.PORT} or http://{hostname}:{constants.PORT}",
            ephemeral=True,
        )

    async def start_timelapse_task(self, interval, count, name):
        import cameras
        dir = f"{constants.ACTIVE_TIMELAPSES_DIR}/{name}"
        self.is_timelapse_active = True

        SLEEP_TIME = 0.1
        try:
            if not os.path.isdir(dir):
                os.makedirs(dir)

            metadata = cameras.camera_instance.metadata
            t0 = time.time()
            data = list()
            metadata["start_time"] = str(datetime.datetime.fromtimestamp(t0))
            self.total = count
            self.interval = interval
            for i in range(count):
                self.progress = i
                time_up = i * interval
                while True:
                    # Sleep at most SLEEP_TIME
                    await asyncio.sleep(SLEEP_TIME)
                    dt = time.time() - t0
                    if dt >= time_up:
                        break
                    if not self.is_timelapse_active:
                        if os.path.isdir(dir):
                            shutil.rmtree(dir)
                        return

                metadata["snaps"] = i
                snap = await asyncio.to_thread(cameras.camera_instance.snap)
                data.append(snap)
                await asyncio.to_thread(np.save, f"{dir}/{name}.npy", data)
                with open(f"{dir}/{name}.json", "wt", encoding="utf-8") as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=4)
            shutil.move(dir, f"{constants.FINISHED_TIMELAPSES_DIR}/{name}")
            self.is_timelapse_active = False
        except Exception as e:
            self.is_timelapse_active = False
            if os.path.isdir(dir):
                shutil.rmtree(dir)
            raise e

async def setup(bot: CameraBot):
    await bot.add_cog(CameraCog(bot))