from __future__ import annotations

import discord
from discord.ext import commands
errors = commands.errors

import traceback

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..main import Jovanes

IGNORED_EXCEPTIONS = (
    errors.CommandNotFound,
    errors.NotOwner,
)

class Events(commands.Cog):
    def __init__(self, bot: Jovanes) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, exception: errors.CommandError) -> Any:
        if isinstance(exception, IGNORED_EXCEPTIONS):
            return
        
        if isinstance(exception, errors.CommandOnCooldown):
            e = discord.Embed(description= "<:reactionFailure:983059904979959819>" f" You're on cooldown. Try again after {exception.retry_after:2f}.", color=discord.Color.red())        
            return await ctx.send(embed=e)
        if isinstance(exception, errors.ChannelNotFound):
            e = discord.Embed(description= "<:reactionFailure:983059904979959819>" f" Channel was not found.", color=discord.Color.red())        
            return await ctx.send(embed=e)
        if isinstance(exception, (errors.MemberNotFound, errors.UserNotFound)):
            e = discord.Embed(description= "<:reactionFailure:983059904979959819>" f" User/Member was not found.", color=discord.Color.red())        
            return await ctx.send(embed=e)
        if isinstance(exception, errors.RoleNotFound):
            e = discord.Embed(description= "<:reactionFailure:983059904979959819>" f" Role was not found.", color=discord.Color.red())        
            return await ctx.send(embed=e)
        if isinstance(exception, errors.MissingRequiredArgument) or isinstance(exception, errors.BadArgument):
            if not ctx.command:
                return
            
            e = discord.Embed(description="<:reactionFailure:983059904979959819>" f" Correct usage of the command: {ctx.command.name} {ctx.command.signature}", timestamp=ctx.message.created_at, color=discord.Color.red())
            e.set_footer(text="[] means the argument is optional and <> means the argument is required.")
            return await ctx.send(embed=e)
        
        raise exception

async def setup(bot: Jovanes) -> None:
    await bot.add_cog(Events(bot))