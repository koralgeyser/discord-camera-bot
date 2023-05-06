import asyncio
import datetime
import io
import json
import os
import shutil
import time
import typing
import discord
from discord import app_commands
import constants
from bot import CameraBot
import helpers
from views.confirm_view import ConfirmView
from config import CONFIG
from cogs import BaseCog
import ffmpeg
import cameras

class CameraCog(BaseCog):
    progress: int
    total: int
    is_timelapse_active = False
    camera_group = app_commands.Group(name="camera", description="Camera")
    timelapse_group = app_commands.Group(name="timelapse", description="Timelapse")

    camera_group.add_command(timelapse_group)

    async def timelapses_names_autocompletion(
        self, interaction: discord.Interaction, current: str
    ) -> typing.List[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=choice, value=choice)
            for choice in helpers.get_autocomplete(current, helpers.list_timelapses())
        ]

    @app_commands.describe(
        name="Name of timelapse"
    )
    @app_commands.autocomplete(name=timelapses_names_autocompletion)
    @timelapse_group.command(name="delete")
    async def timelapse_delete(
        self,
        interaction: discord.Interaction,
        name: str,
    ):
        """Deletes timelapse on local drive."""
        view = ConfirmView()

        await interaction.response.send_message(
            f"Are you sure you want to delete timelapse '{name}'?", view=view, ephemeral=True
        )
        if not await view.wait(interaction):
            if view.value:
                path = os.path.join(constants.TIMELAPSES_DIR, name)
                if os.path.exists(path):
                    shutil.rmtree(path)
                    await interaction.followup.send(
                        f"Timelapse '{name}' was deleted by {interaction.user.mention}."
                    )
                else:
                    await interaction.followup.send(
                        f"Timelapse '{name}' does not exist.",
                        ephemeral=True
                    )


    @app_commands.describe(
        name="Name of timelapse"
    )
    @app_commands.autocomplete(name=timelapses_names_autocompletion)
    @timelapse_group.command(name="rename")
    async def timelapse_rename(
        self,
        interaction: discord.Interaction,
        name: str,
        rename: str
    ):
        """Renames timelapse on local drive."""
        view = ConfirmView()

        await interaction.response.send_message(
            f"Are you sure you want to rename timelapse '{name}' to '{rename}'?", view=view, ephemeral=True
        )
        if not await view.wait(interaction):
            if view.value:
                old = os.path.join(constants.TIMELAPSES_DIR, name)
                new = os.path.join(constants.TIMELAPSES_DIR, rename)
                if os.path.exists(old):
                    os.rename(old, new)
                    await interaction.followup.send(
                        f"Timelapse '{name}' was renamed to '{rename}'  by {interaction.user.mention}."
                    )
                else:
                    await interaction.followup.send(
                        f"Timelapse '{name}' does not exist.",
                        ephemeral=True
                    )

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
        elif os.path.isdir(f"{constants.TIMELAPSES_DIR}/{name}"):
            await interaction.response.send_message(
                "Failed to start. This name already exists."
            )
        else:
            total_time = interval * count
            self.eta = total_time 
            async def timelapse_task():
                try:
                    await self.bot.wait_until_ready()

                    user = interaction.user
                    channel = interaction.channel

                    dir = os.path.join(constants.TIMELAPSES_DIR, name)
                    frames_dir = os.path.join(dir, "frames")
                    self.is_timelapse_active = True

                    SLEEP_TIME = 0.1
                    try:
                        if not os.path.isdir(dir):
                            os.makedirs(dir)
                            os.makedirs(frames_dir)

                        metadata = cameras.camera_instance.metadata
                        t0 = time.time()
                        metadata["start_time"] = str(datetime.datetime.fromtimestamp(t0))
                        metadata["interval"] = interval
                        metadata["timestamps"] = []

                        for i in range(count):
                            self.progress = i
                            time_up = i * interval
                            while True:
                                # Relinquish control
                                await asyncio.sleep(SLEEP_TIME)
                                dt = time.time() - t0
                                self.eta -= dt
                                if dt >= time_up:
                                    break
                                if not self.is_timelapse_active:
                                    if os.path.isdir(dir):
                                        shutil.rmtree(dir)
                                    return
                            snap = await asyncio.to_thread(cameras.camera_instance.snap)
                            await asyncio.to_thread(snap.save, f"{frames_dir}/{i}.png")
                            metadata["snaps"] = i
                            metadata["timestamps"] += [dt]
                            with open(f"{dir}/metadata.json", "wt", encoding="utf-8") as f:
                                json.dump(metadata, f, ensure_ascii=False, indent=4)

                        self.is_timelapse_active = False
                    except Exception as e:
                        self.is_timelapse_active = False
                        if os.path.isdir(dir):
                            shutil.rmtree(dir)
                        raise e
                    
                    video_path = f"{dir}/timelapse.mp4"
                    try:
                        (
                            ffmpeg
                            .input(f"{frames_dir}/%d.png")
                            .output(
                                video_path,
                                framerate=30,
                                vcodec="libx264",
                                crf=17,
                                pix_fmt="yuv420p"
                            )
                            .overwrite_output()
                            .run(capture_stdout=True, capture_stderr=True)
                        )
                    except ffmpeg.Error:
                        await channel.send(
                            f"{user.mention} Failed to create timelapse video from frames."
                        )

                    path = await asyncio.to_thread(
                        shutil.make_archive,
                        name,
                        "zip",
                        constants.TIMELAPSES_DIR,
                        name
                    )
                    await asyncio.to_thread(helpers.upload_to_google_folder,
                        f"{name}.zip",
                        CONFIG.drive_folder_id,
                        path
                    )
                    os.remove(path)

                    # in MB
                    size = os.stat(video_path).st_size / (1024 * 1024)
                    msg = f"{user.mention} '{name}' timelapse has finished: https://drive.google.com/drive/folders/{CONFIG.drive_folder_id}?usp=sharing"
                    if size >= 25:
                        await channel.send(msg)
                    else:
                        await channel.send(msg, file=discord.File(video_path))
                except Exception as e:
                    await channel.send(
                        f"{user.mention} An error has occurred with the timelapse."
                    )
                    await self.bot.log_error(e)
            
            self.bot.loop.create_task(timelapse_task())

            await interaction.response.send_message(f"Timelapse '{name}' has started. ETA: {datetime.timedelta(seconds=total_time)}")

    @timelapse_group.command(name="cancel")
    async def timelapse_cancel(self, interaction: discord.Interaction):
        """Cancels current running timelapse."""
        view = ConfirmView()

        await interaction.response.send_message(
            "Are you sure you want to cancel the timelapse?", view=view, ephemeral=True
        )
        if not await view.wait(interaction):
            if view.value:
                if self.is_timelapse_active:
                    self.is_timelapse_active = False
                    await interaction.followup.send(
                        f"Timelapse was canceled by {interaction.user.mention}."
                    )
                else:
                    await interaction.followup.send(
                        "There was no active timelapse to cancel.",
                        ephemeral=True
                    )

    @timelapse_group.command(name="progress")
    async def timelapse_progress(self, interaction: discord.Interaction):
        """Get progress of timelapse."""
        if self.is_timelapse_active:
            await interaction.response.send_message(
                f"{self.progress}/{self.total} completed. ETA: {datetime.timedelta(seconds=self.eta)}",
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


    @app_commands.describe(
        private="Privately send? Defaults to true."
    )
    @camera_group.command(name="snap")
    async def snap(
        self,
        interaction: discord.Interaction,
        private: typing.Optional[bool] = True
    ):
        """Gets a snap from the camera."""
        import cameras

        await interaction.response.send_message("Please wait... This message will be updated with the snap.", ephemeral=private)

        snap = await asyncio.to_thread(cameras.camera_instance.snap)
        buffer = io.BytesIO()

        # Hardcoding ext for now
        with io.BytesIO() as buffer:
            await asyncio.to_thread(snap.save, buffer, "PNG", optimize=True)
            buffer.seek(0)
            await interaction.edit_original_response(
                content="",
                attachments=[discord.File(fp=buffer, filename="snap.png")]
            )

    @camera_group.command(name="feed")
    async def camera_feed(self, interaction: discord.Interaction):
        """Get link to camera feed. Can only view on local network."""
        # hostname = socket.gethostname()
        # ip = socket.gethostbyname(hostname)
        # Hardcoding for now
        ip = "192.168.0.126"
        await interaction.response.send_message(
            f"View at http://{ip}:{constants.PORT}",
            ephemeral=True,
        )

async def setup(bot: CameraBot):
    await bot.add_cog(CameraCog(bot))