import asyncio
from datetime import datetime
import io
import json
import os
import pathlib
import shutil
import time
import typing
import zipfile
import discord
from discord import app_commands
import numpy as np
import pathvalidate
from discord.ext import tasks
from reactionmenu import ViewButton, ViewMenu, ViewSelect
import constants
from views.page_view import PageView

class Camera(app_commands.Group):
    is_timelapse_active = False
    timelapse_group = app_commands.Group(name="timelapse", description="Timelapse from camera")

    @app_commands.describe(
        timepoints_file="List of timepoints. Supports '.csv'",
        name="Name of timelapse."
    )
    @app_commands.rename(timepoints_file='timepoints')
    @timelapse_group.command(name="start")
    async def timelapse_start(self, interaction: discord.Interaction, timepoints_file: discord.Attachment, name: str):
        """Start a timelapse. Only one timelapse can be running at a time."""
        # TODO: Check if name is unused
        if not pathvalidate.is_valid_filename(name):
            return await interaction.response.send_message("Invalid name supplied.", ephemeral=True)
        # Unfort match cases only in 3.10+
        if pathlib.Path(timepoints_file.filename).suffix:
            # Use actual csv lib later
            timepoints = list(map(
                    lambda x: float(x),
                    (await timepoints_file.read())
                        .decode("utf-8")
                        .replace(" ", "")
                        .split(",")
                )
            )
        else:
            return await interaction.response.send_message("Invalid file format supplied.", ephemeral=True)

        # Only allow one for now
        if self.is_timelapse_active:
            await interaction.response.send_message("Failed to start. There is currently an active timelapse.")
        elif os.path.isdir(f"{constants.FINISHED_TIMELAPSES_DIR}/{name}"):
            await interaction.response.send_message("Failed to start. This name already exists.")
        else:
            async def finished_callback():
                user = interaction.user
                channel = interaction.channel

                data = self.timelapse_data(name)
                await channel.send(
                    f"{user.mention} Timelapse has finished.",
                    file=discord.File(
                        fp=data,
                        filename=f"<{name}.zip>")
                )
            task = tasks.loop(count=1)(self.start_timelapse_task)
            task.after_loop(finished_callback)
            task.start(timepoints, name)

            await interaction.response.send_message("The timelapse has started.")

    @timelapse_group.command(name="cancel")
    async def timelapse_cancel(self, interaction: discord.Interaction):
        """Cancels current running timelapse."""
        from views.confirm_view import ConfirmView
        view = ConfirmView()
            
        await interaction.response.send_message("Are you sure you want to cancel the timelapse?", view=view, ephemeral=True)
        await view.wait(interaction)
        if view.value:
            if self.is_timelapse_active: 
                self.is_timelapse_active = False
                await interaction.channel.send(f"Timelapse was canceled by {interaction.user.mention}.")
            else:
                await interaction.followup.send("There was no active timelapse to cancel.", ephemeral=True)


    async def timelapse_name_autocompletion(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> typing.List[app_commands.Choice[str]]:
        timelapses: typing.List[str] = os.listdir(constants.FINISHED_TIMELAPSES_DIR)
        filtered = list(filter(lambda timelapse: current.lower() in timelapse.lower(), timelapses))[:25]
        return [
            app_commands.Choice(name=choice, value=choice)
            for choice in filtered
        ]

    @app_commands.describe(
        name="Name of timelapse.",
        ephemeral="Send the message ephemerally? Defaults to false."
    )
    @app_commands.autocomplete(name=timelapse_name_autocompletion)
    @timelapse_group.command(name="data")
    async def timelapse_data(self, interaction: discord.Interaction, name: str, ephemeral: typing.Optional[bool] = False):
        """Get finished timelapse data."""
        data = self.timelapse_data(name)
        return await interaction.response.send_message(
            file=discord.File(
                fp=data,
                filename=f'<{name}.zip>'
            ),
            ephemeral=ephemeral
        )


    @timelapse_group.command(name="list")
    async def timelapse_list(self, interaction: discord.Interaction):
        """Lists finished timelapses."""
        timelapses: typing.List[str] = os.listdir(constants.FINISHED_TIMELAPSES_DIR)
        if timelapses_count := len(timelapses):
            menu = PageView(interaction, menu_type=ViewMenu.TypeEmbed)
            # 10 items per page
            ITEMS_PER_PAGE = 10
            count = timelapses_count//ITEMS_PER_PAGE
            remainder = timelapses_count % ITEMS_PER_PAGE
            for x in range(count):
                menu.add_page(discord.Embed(
                        title="Timelapses",
                        description="\n".join(timelapses[x*ITEMS_PER_PAGE:(x+1)*ITEMS_PER_PAGE])
                    )
                )

            if remainder:
                timelapses_slice = timelapses[timelapses_count - remainder:]
                menu.add_page(discord.Embed(
                        title="Timelapses",
                        description="\n".join(timelapses_slice)
                    )
                )

            menu.add_go_to_select(ViewSelect.GoTo(title="Go to page...", page_numbers=...))
            menu.add_button(ViewButton.back())
            menu.add_button(ViewButton.next())
            await menu.start()
        else:
            await interaction.response.send_message("There are no timelapse data.", ephemeral=True)

    @app_commands.command()
    async def snap(self, interaction: discord.Interaction):
        """Gets a snap from the camera."""
        import cameras
        from PIL import Image
        
        await interaction.response.defer()
        snap = cameras.camera_instance.snap()
        buffer = io.BytesIO()
        img = Image.fromarray(snap)
        # img = img.resize((int(img.width/1.5), int(img.height/1.5)))

        # Hardcoding ext for now
        with io.BytesIO() as buffer:
            img.save(buffer, 'PNG')
            buffer.seek(0)
            await interaction.followup.send(file=discord.File(fp=buffer, filename='snap.png'))

        @app_commands.command()
        async def camera_feed(interaction: discord.Interaction):
            """Get link to camera feed. Can only view on local network."""
            await interaction.response.send_message(f"http://{constants.HOST_NAME}:{constants.PORT}. Check my profile for the link as well.", ephemeral=True)




    @staticmethod
    def timelapse_data(name):
        # Only finished timelapses atm
        buffer = io.BytesIO()
        dir = pathlib.Path(f"{constants.FINISHED_TIMELAPSES_DIR}/{name}/")
        # TODO: QOL be fancy and send in chunks if using a pyobj
        with zipfile.ZipFile(buffer, "a", zipfile.ZIP_DEFLATED, False) as archive:
            for path in dir.iterdir():
                with open(path, mode="rb") as fs:
                    archive.writestr(path.name, fs.read())
        buffer.seek(0)
        return buffer

    # Only one task
    # Task Generator if want to have more in future
    async def start_timelapse_task(self, timepoints, name):
        import cameras
        SLEEP_TIME = 0.1
        dir = f"{constants.ACTIVE_TIMELAPSES_DIR}/{name}"
        self.is_timelapse_active = True

        try:
            # Send a result if there's an existing active or finished 
            if not os.path.isdir(dir):
                os.makedirs(dir)

            metadata = cameras.camera_instance.metadata
            times = np.array(timepoints) ## an np.ndarray of timepoints to take a picture after
            times.sort()
            npics = times.size
            data = np.zeros((npics, *metadata['shape']), dtype=metadata['dtype'])

            t0 = time.time()
            metadata['start_time'] = str(datetime.fromtimestamp(t0))
            metadata['timepoints'] = []
            for i in range(npics):
                while True:
                    # Sleep at most SLEEP_TIME
                    if SLEEP_TIME < times[i]:
                        await asyncio.sleep(SLEEP_TIME)
                    else:
                        await asyncio.sleep(times[i]/2)
                    dt = time.time() - t0
                    if dt >= times[i]:
                        break
                    if not self.is_timelapse_active:
                        if os.path.isdir(dir):
                            shutil.rmtree(dir)
                        return

                data[i] = cameras.camera_instance.snap()
                metadata['timepoints'].append(dt)
                np.save(f"{dir}/{name}.npy",data[:i+1])
                with open(f'{dir}/{name}.json', 'wt', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=4)
            shutil.move(dir, f"{constants.FINISHED_TIMELAPSES_DIR}/{name}")
            self.is_timelapse_active = False
        except:
            # Maybe add errors as well
            self.is_timelapse_active = False
            if os.path.isdir(dir):
                shutil.rmtree(dir)