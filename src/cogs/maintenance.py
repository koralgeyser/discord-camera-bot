import os
import typing
import checks
import cogs
import config
import constants
import discord
import helpers
from discord import app_commands
from discord.ext import commands
from views.confirm_view import ConfirmView
from bot import CameraBot
from cogs import BaseCog


class MaintenanceCog(BaseCog):
    maintenance_group = app_commands.Group(
        name="bot", description="Bot", guild_ids=[config.CONFIG.dev_guild_id]
    )

    cog_group = app_commands.Group(
        name="cog", description="Cog", guild_ids=[config.CONFIG.dev_guild_id]
    )

    config_group = app_commands.Group(
        name="config", description="Config", guild_ids=[config.CONFIG.dev_guild_id]
    )

    maintenance_group.add_command(cog_group)
    maintenance_group.add_command(config_group)

    @checks.is_owner()
    @app_commands.describe(file="Config JSON file.")
    @config_group.command(name="update")
    async def config_update(
        self, interaction: discord.Interaction, file: discord.Attachment
    ):
        """Update config"""
        if not file.filename.endswith(".json"):
            return await interaction.response.send_message(
                "Not a JSON file.", ephemeral=True
            )

        try:
            config.CONFIG: config.Config = config.Config.from_json(await file.read())
            config.CONFIG.update()
            await interaction.response.send_message("Updated config", ephemeral=True)
        except:
            await interaction.response.send_message(
                "Failed to update config", ephemeral=True
            )

    @checks.is_owner()
    @app_commands.describe(
        branch="Branch to update from. Defaults to 'main'.",
        auto_restart="Auto restart after updating? Defaults to False.",
    )
    @maintenance_group.command(name="update")
    async def bot_update(
        self,
        interaction: discord.Interaction,
        branch: typing.Optional[str] = "main",
        auto_restart: typing.Optional[bool] = False,
    ):
        """Update bot."""
        view = ConfirmView()
        await interaction.response.send_message(
            "Are you sure you want me to update?", view=view, ephemeral=True
        )
        await view.wait(interaction)
        if view.value:
            await interaction.followup.send("Updating...", ephemeral=True)
            await helpers.async_update(branch)

            if auto_restart:
                await interaction.followup.send(
                    "Update complete. Restarting now...", ephemeral=True
                )
                helpers.restart()
            else:
                await interaction.followup.send("Update complete.", ephemeral=True)


    @checks.is_owner()
    @maintenance_group.command(name="restart")
    async def bot_restart(self, interaction: discord.Interaction):
        """Restart bot."""
        view = ConfirmView()
        await interaction.response.send_message(
            "Are you sure you want me to restart?", view=view, ephemeral=True
        )
        await view.wait(interaction)
        if view.value:
            await interaction.followup.send("Restarting...", ephemeral=True)
            helpers.restart()

    @checks.is_owner()
    @maintenance_group.command(name="shutdown")
    async def bot_shutdown(self, interaction: discord.Interaction):
        """Shutdown bot."""
        view = ConfirmView()
        await interaction.response.send_message(
            "Are you sure you want me to shutdown?", view=view, ephemeral=True
        )
        await view.wait(interaction)
        if view.value:
            await interaction.followup.send("Shutting down...", ephemeral=True)
            await self.bot.close()

    @checks.is_owner()
    @app_commands.describe(id="Server ID to sync to. Defaults to current server.")
    @maintenance_group.command(name="sync")
    async def bot_sync(
        self, interaction: discord.Interaction, id: typing.Optional[str] = None
    ):
        """Sync slash commands."""

        view = ConfirmView()
        await interaction.response.send_message(
            "Are you sure you want to sync?",
            view=view,
            ephemeral=True,
        )
        await view.wait(interaction)
        if view.value:
            id = id if id else interaction.guild_id
            guild = discord.Object(id=id)
            self.bot.tree.copy_global_to(guild=guild)
            await self.bot.tree.sync(guild=guild)
            await interaction.followup.send("Synced!", ephemeral=True)

    async def logs_names_autocompletion(
        self, interaction: discord.Interaction, current: str
    ) -> typing.List[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=choice, value=choice)
            for choice in helpers.get_autocomplete(
                current, os.listdir(constants.LOGS_DIR)
            )
        ]

    @checks.is_owner()
    @app_commands.autocomplete(name=logs_names_autocompletion)
    @app_commands.describe(name="Name of log.")
    @maintenance_group.command(name="log")
    async def bot_log(self, interaction: discord.Interaction, name: str):
        """Get log."""
        await interaction.response.send_message(
            file=discord.File(f"{constants.LOGS_DIR}/{name}", name), ephemeral=True
        )

    async def cog_names_autocompletion(
        self, interaction: discord.Interaction, current: str
    ) -> typing.List[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=choice, value=choice)
            for choice in helpers.get_autocomplete(current, helpers.get_cogs())
        ]

    @checks.is_owner()
    @app_commands.autocomplete(name=cog_names_autocompletion)
    @app_commands.describe(name="Name of cog.")
    @cog_group.command(name="load")
    async def extension_load(self, interaction: discord.Interaction, name: str):
        """Loads a cog."""
        try:
            await self.bot.load_extension(f"{cogs.__name__}.{name}")
            await interaction.response.send_message(
                "Successfully loaded cog.", ephemeral=True
            )
        except commands.errors.ExtensionAlreadyLoaded:
            await interaction.response.send_message(
                "Cog already loaded.", ephemeral=True
            )
        except commands.errors.ExtensionNotFound:
            await interaction.response.send_message("Cog not found.", ephemeral=True)
        except Exception:
            await interaction.response.send_message(
                "Failed to load cog.", ephemeral=True
            )

    @checks.is_owner()
    @app_commands.autocomplete(name=cog_names_autocompletion)
    @app_commands.describe(name="Name of cog.")
    @cog_group.command(name="unload")
    async def extension_unload(self, interaction: discord.Interaction, name: str):
        """Unloads a cog."""
        cog = f"{cogs.__name__}.{name}"
        if cog == __name__:
            return await interaction.response.send_message(
                "SECURITY ERROR: Cannot unload this cog.", ephemeral=True
            )
        try:
            await self.bot.unload_extension(cog)
            await interaction.response.send_message(
                "Successfully unloaded cog.", ephemeral=True
            )
        except commands.errors.ExtensionNotLoaded:
            await interaction.response.send_message("Cog not loaded.", ephemeral=True)
        except commands.errors.ExtensionNotFound:
            await interaction.response.send_message("Cog not found.", ephemeral=True)
        except Exception:
            await interaction.response.send_message(
                "Failed to unload cog.", ephemeral=True
            )

    @checks.is_owner()
    @app_commands.autocomplete(name=cog_names_autocompletion)
    @app_commands.describe(all="Reload all? Defaults to false.", name="Name of cog.")
    @cog_group.command(name="reload")
    async def extension_reload(
        self,
        interaction: discord.Interaction,
        name: typing.Optional[str] = None,
        all: typing.Optional[bool] = False,
    ):
        """Reloads a cog."""
        if all:
            for cog in helpers.get_cogs():
                await self.bot.reload_extension(f"{cogs.__name__}.{cog}")
            return await interaction.response.send_message(
                "Successfully reloaded all cogs.", ephemeral=True
            )
        if name:
            try:
                await self.bot.reload_extension(f"{cogs.__name__}.{name}")
                await interaction.response.send_message(
                    "Successfully reloaded cog.", ephemeral=True
                )
            except commands.errors.ExtensionNotLoaded:
                await interaction.response.send_message(
                    "Cog not loaded.", ephemeral=True
                )
            except commands.errors.ExtensionNotFound:
                await interaction.response.send_message(
                    "Cog not found.", ephemeral=True
                )
            except Exception:
                await interaction.response.send_message(
                    "Failed to reload cog.", ephemeral=True
                )

    # @checks.is_owner()
    # @cog_group.command(name="list")
    # async def extension_list(self, interaction: discord.Interaction):
    #     """Lists cogs."""
    #     cogs: typing.List[str] = helpers.get_cogs()
    #     if cogs_count := len(cogs):
    #         menu = PageView(interaction, menu_type=ViewMenu.TypeEmbed)
    #         # 10 items per page
    #         ITEMS_PER_PAGE = 10
    #         count = cogs_count // ITEMS_PER_PAGE
    #         remainder = cogs_count % ITEMS_PER_PAGE
    #         for x in range(count):
    #             menu.add_page(
    #                 discord.Embed(
    #                     title="Timelapses",
    #                     description="\n".join(
    #                         cogs[x * ITEMS_PER_PAGE : (x + 1) * ITEMS_PER_PAGE]
    #                     ),
    #                 )
    #             )

    #         if remainder:
    #             cogs_slice = cogs[cogs_count - remainder :]
    #             menu.add_page(
    #                 discord.Embed(title="Timelapses", description="\n".join(cogs_slice))
    #             )

    #         menu.add_go_to_select(
    #             ViewSelect.GoTo(title="Go to page...", page_numbers=...)
    #         )
    #         menu.add_button(ViewButton.back())
    #         menu.add_button(ViewButton.next())
    #         await menu.start()
    #     else:
    #         await interaction.response.send_message(
    #             "There are no cogs.", ephemeral=True
    #         )

async def setup(bot: CameraBot):
    await bot.add_cog(MaintenanceCog(bot))
