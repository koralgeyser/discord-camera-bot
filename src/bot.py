import asyncio
import base64
from datetime import datetime
import io
import json
import os
import pathlib
import shutil
import socket
import subprocess
from threading import Thread
import threading
import time
from typing import List, Optional, Union
import typing
import zipfile
import discord
from discord import app_commands
import numpy as np

# import dotenv
import pathvalidate
from reactionmenu import ViewButton, ViewMenu, ViewSelect

# This is my own server 
MY_GUILD = discord.Object(id)  # replace with your guild id

class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        # A CommandTree is a special type that holds all the application command
        # state required to make it work. This is a separate class because it
        # allows all the extra state to be opt-in.
        # Whenever you want to work with application commands, your tree is used
        # to store and work with them.
        # Note: When using commands.Bot instead of discord.Client, the bot will
        # maintain its own tree instead.
        self.tree = app_commands.CommandTree(self)
        # dotenv.load_dotenv()

    # In this basic example, we just synchronize the app commands to one guild.
    # Instead of specifying a guild to every command, we copy over our global commands instead.
    # By doing so, we don't have to wait up to an hour until they are shown to the end-user.
    async def setup_hook(self):
        # This copies the global commands over to your guild.

        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)
    
    async def on_ready(self):
        import cameras
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="the lab"))
        # fix this
        print(f"Camera Module: {cameras.camera_instance}")
        print('------')

intents = discord.Intents.default()
client = MyClient(intents=intents)
from commands.camera import Camera

client.tree.add_command(Camera())

# @client.tree.error
# async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
#     # Add logger here as well 
#     # if isinstance(error, discord.app_commands.CommandInvokeError):
#     #     if interaction.response.is_done():
#     #         await interaction.followup.send(str(error.original), ephemeral=True)
#     #     else:
#     #         await interaction.response.send_message(str(error.original), ephemeral=True)
#     #     # if isinstance(error.original, errors.ServerTimeoutError):
#     #     #     await interaction.followup.send(str(error.original), ephemeral=True)
#     #     # else:
#     #     #     pass

#     if interaction.response.is_done():
#         await interaction.followup.send(str(error.original), ephemeral=True)
#     else:
#         await interaction.response.send_message(str(error.original), ephemeral=True)

def initialize():
    import constants
    if not os.path.exists(constants.ACTIVE_TIMELAPSES_DIR):
        os.makedirs(constants.ACTIVE_TIMELAPSES_DIR)
    if not os.path.exists(constants.FINISHED_TIMELAPSES_DIR):
        os.makedirs(constants.FINISHED_TIMELAPSES_DIR)
    if not os.path.exists(constants.INCOMPLETE_TIMELAPSES_DIR):
        os.makedirs(constants.INCOMPLETE_TIMELAPSES_DIR)

    # Move any active timelapses that are now in limbo due to w/e reason to incomplete 
    for dir in os.listdir(constants.ACTIVE_TIMELAPSES_DIR):
        shutil.move(f"{constants.ACTIVE_TIMELAPSES_DIR}/{dir}", constants.INCOMPLETE_TIMELAPSES_DIR)

def run():
    client.run(os.environ["DISCORD_TOKEN"])


if __name__ == "__main__":
    run()
# client.run(os.environ["DISCORD_TOKEN"])
