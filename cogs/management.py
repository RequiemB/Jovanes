from __future__ import annotations

import discord
from discord.ext import commands

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..main import Jovanes

class Management(commands.Cog):
    def __init__(self, bot: Jovanes) -> None:
        self.bot = bot

    @commands.group(name="command", invoke_without_command=True)
    async def command_grp(self, ctx: commands.Context) -> None:
        return
    
    @command_grp.command(name="enable", description="Enables a command this is disabled in the guild.")
    async def command_enable(self, ctx: commands.Context, *, cmd: str) -> None:
        pass

    @command_grp.command(name="disable", description="Renders a command unusable in the guild.")
    async def command_disable(self, ctx: commands.Context, *, cmd: str) -> None:
        pass

async def setup(bot: Jovanes) -> None:
    await bot.add_cog(Management(bot))