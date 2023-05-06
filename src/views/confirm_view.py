import discord


class ConfirmView(discord.ui.View):
    value: bool

    def __init__(self):
        super().__init__()

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer()
        self.value = True
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.value = False
        self.stop()

    async def wait(self, interaction: discord.Interaction) -> bool:
        for button in self.children:
            button.disabled = True
        result = await super().wait()
        if result:
            await interaction.edit_original_response(
                view=self
            )
            return result
        else:
            await interaction.edit_original_response(
                content="Confirmed. Please wait..." if self.value else "Canceled.",
                view=self,
            )
            return result
