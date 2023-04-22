import asyncio
import datetime
import io
import json
import os
import shutil
import time
import discord
from discord import app_commands
import numpy as np
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
            
            async def timelapse_task():
                import cameras
                await self.bot.wait_until_ready()

                user = interaction.user
                channel = interaction.channel

                dir = f"{constants.ACTIVE_TIMELAPSES_DIR}/{name}"
                self.is_timelapse_active = True

                SLEEP_TIME = 0.5
                try:
                    if not os.path.isdir(dir):
                        os.makedirs(dir)

                    metadata = cameras.camera_instance.metadata
                    t0 = time.time()
                    metadata["start_time"] = str(datetime.datetime.fromtimestamp(t0))
                    data = []
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
                        data.append(await asyncio.to_thread(cameras.camera_instance.snap))

                    np.savez(f"{dir}/{name}", data)
                    with open(f"{dir}/{name}.json", "wt", encoding="utf-8") as f:
                        json.dump(metadata, f, ensure_ascii=False, indent=4)
                    shutil.move(dir, f"{constants.FINISHED_TIMELAPSES_DIR}/{name}")
                    self.is_timelapse_active = False
                except Exception as e:
                    self.is_timelapse_active = False
                    if os.path.isdir(dir):
                        shutil.rmtree(dir)
                    await channel.send(
                        f"{user.mention} An error has occurred with the timelapse."
                    )
                    raise e

                data = await asyncio.to_thread(helpers.get_timelapse_data, name)
                await asyncio.to_thread(helpers.upload_to_google_folder,
                    f"{name}.zip",
                    CONFIG.drive_folder_id,
                    data
                )
                await channel.send(
                    f"{user.mention} '{name}' timelapse has finished: https://drive.google.com/drive/folders/{CONFIG.drive_folder_id}?usp=sharing.",
                )
            
            self.bot.loop.create_task(timelapse_task())

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

        snap = await asyncio.to_thread(cameras.camera_instance.snap)
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
        # hostname = socket.gethostname()
        # ip = socket.gethostbyname(hostname)
        ip = "192.168.0.126"
        await interaction.response.send_message(
            f"View at http://{ip}:{constants.PORT}",
            ephemeral=True,
        )

async def setup(bot: CameraBot):
    await bot.add_cog(CameraCog(bot))