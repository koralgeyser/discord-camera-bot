import typing
import discord
from reactionmenu import ViewMenu


class PageView(ViewMenu):
    def __init__(self, method, /, *, menu_type, **kwargs):
        super().__init__(method, menu_type=menu_type, **kwargs)
        
    async def _handle_send_to(self, send_to: typing.Union[str, int, discord.TextChannel, discord.VoiceChannel, discord.Thread, None], menu_payload: dict):
        menu_payload["ephemeral"] = True
        return await super()._handle_send_to(send_to, menu_payload)
