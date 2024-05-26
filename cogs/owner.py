from __future__ import annotations

import discord
from discord.ext import commands
from discord import app_commands

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..main import Jovanes

class Owner(commands.Cog):
    def __init__(self, bot: Jovanes) -> None:
        self.bot = bot

    @commands.command(description="Shuts down the bot.")
    @commands.is_owner()
    async def shutdown(self, ctx: commands.Context) -> None:
        await ctx.send('Shutting down now...')
        await self.bot.close()

async def setup(bot: Jovanes) -> None:
    await bot.add_cog(Owner(bot))