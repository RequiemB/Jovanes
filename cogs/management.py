from __future__ import annotations

import discord
from discord.ext import commands

from helpers import views
from config import reactionFailure, reactionSuccess
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..main import Jovanes

class PrefixFlag(commands.FlagConverter, prefix="--", delimiter=" "):
    whitespace: bool

class Management(commands.Cog):
    def __init__(self, bot: Jovanes) -> None:
        self.bot = bot
    
    @commands.command(name="enable", description="Enables a command/module this is disabled in the guild.")
    @commands.has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def enable(self, ctx: commands.Context[Jovanes], *, entity: str) -> Any:
        assert ctx.guild
        
        resolved_entity = self.bot.get_command(entity)

        if not resolved_entity: # If no command was found, check whether it's a cog
            resolved_entity = self.bot.get_cog(entity)
            
            if not resolved_entity:
                e = discord.Embed(description=f"{reactionFailure} No command/module named **{entity}** was found.", color=discord.Color.red())
                await ctx.reply(embed=e)
                return
            else:
                _type = "module"
        else:
            _type = "command"
        
        async with self.bot.pool.acquire() as conn:
            res = await conn.fetchone("SELECT entity FROM configuration WHERE entity = ? AND guild_id = ?", (entity, ctx.guild.id))

            if not res:
                e = discord.Embed(description=f"{reactionFailure} This **{_type}** is not disabled.", color=discord.Color.red())
                await ctx.reply(embed=e)
                return
            
            await conn.execute("DELETE FROM configuration WHERE entity = ? AND guild_id = ?", (entity, ctx.guild.id))

            e = discord.Embed(
                description = f"{reactionSuccess} {_type.capitalize()} **{resolved_entity.qualified_name}** has been enabled.",
                color = discord.Color.green()
            )
            await ctx.reply(embed=e)
            
    @commands.command(name="disable", description="Renders a command/module unusable in the guild.")
    @commands.has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def disable(self, ctx: commands.Context[Jovanes], *, entity: str) -> Any:
        assert ctx.guild

        resolved_entity = self.bot.get_command(entity)

        if not resolved_entity: # If no command was found, check whether it's a cog
            resolved_entity = self.bot.get_cog(entity)
            
            if not resolved_entity:
                e = discord.Embed(description=f"{reactionFailure} No command/module named **{entity}** was found.", color=discord.Color.red())
                await ctx.reply(embed=e)
                return
            else:
                _type = "module"
        else:
            _type =  "command"

        cog = resolved_entity.cog if isinstance(resolved_entity, commands.Command) else resolved_entity

        if isinstance(cog, Management): # This cog shouldn't be disabled
            e = discord.Embed(description=f"{reactionFailure} Commands in this module or the module itself can't be disabled.", color=discord.Color.red())
            await ctx.reply(embed=e)
            return

        async with self.bot.pool.acquire() as conn:
            res = await conn.fetchone("SELECT entity FROM configuration WHERE entity = ? AND guild_id = ?", (entity, ctx.guild.id))

            if res:
                e = discord.Embed(description=f"{reactionFailure} This **{_type}** is already disabled.", color=discord.Color.red())
                await ctx.reply(embed=e)
                return
            
            await conn.execute("INSERT INTO configuration (guild_id, entity, disabled) VALUES (?, ?, ?)", (ctx.guild.id, entity, 1))

            e = discord.Embed(
                description = f"{reactionSuccess} {_type.capitalize()} **{resolved_entity.qualified_name}** has been disabled.",
                color = discord.Color.green()
            )
            await ctx.reply(embed=e)

    @commands.group(name="prefix", description="The group for managing prefixes.", invoke_without_command=True)
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    async def prefix(self, ctx: commands.Context[Jovanes]) -> Any:
        await ctx.send_help(ctx.command)

    @prefix.command(name="add", description="Add a prefix to the guild.")
    @commands.has_guild_permissions(manage_guild=True)
    async def prefix_add(self, ctx: commands.Context[Jovanes], prefix: str) -> Any:
        assert ctx.guild

        if len(prefix) > 16:
            e = discord.Embed(description=f"{reactionFailure} Prefix cannot exceed 16 characters in length.", color=discord.Color.red())
            await ctx.reply(embed=e)
            return

        prefixes = await self.bot._get_prefix(self.bot, ctx.message)

        if len(prefixes) > 5:
            e = discord.Embed(description=f"{reactionFailure} Only five custom prefixes are allowed per guild.", color=discord.Color.red())
            await ctx.reply(embed=e)
            return
        
        for _prefix in prefixes:
            if _prefix.strip() == prefix.strip():
                e = discord.Embed(description=f"{reactionFailure} **{prefix}** is already a prefix in this guild.", color=discord.Color.red())
                await ctx.reply(embed=e)
                return
        
        async with self.bot.pool.acquire() as conn:
            await conn.execute("INSERT INTO prefixes (guild_id, prefix) VALUES (?, ?)", (ctx.guild.id, prefix))

        e = discord.Embed(
            description = f'{reactionSuccess} Added `{prefix}` to the list of prefixes.\n\nNote: If the prefix contains more than one word, it should be wrapped in quotes. E.g. `"two words"`. If you\'d like a whitespace after the end of the prefix, wrap it in quotes and leave a space at the end. E.g. `"two words "`.',
            color = discord.Color.green()
        )
        await ctx.reply(embed=e)

    @prefix.command(name="remove", description="Removes a prefix from the guild.")
    @commands.has_guild_permissions(manage_guild=True)
    async def prefix_remove(self, ctx: commands.Context[Jovanes]) -> Any:
        assert ctx.guild

        prefixes = await self.bot._get_prefix(self.bot, ctx.message)

        if len(prefixes) == 1:
            e = discord.Embed(description=f"{reactionFailure} There is only one prefix left in the server. You can't remove it unless more prefixes are added.", color=discord.Color.red())
            await ctx.reply(embed=e)
            return

        e = discord.Embed(
            title = "Prefix Remover",
            description = "Select a prefix to remove from the dropdown below.",
            color = discord.Color.blue(),
            timestamp = discord.utils.utcnow()
        )
        e.add_field(name="Prefixes", value="\n".join([f"`{prefix}`" for prefix in prefixes]))
        view = views.PrefixRemove(ctx, prefixes)
        view.message = await ctx.reply(embed=e, view=view)

    @commands.command(name="setlogging", description="Sets the logging channel for the guild.")
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    async def setlogging(self, ctx: commands.Context[Jovanes], channel: discord.TextChannel) -> Any:
        assert ctx.guild

        try:
            webhook = await channel.create_webhook(name=self.bot.user.name) # type: ignore
        except discord.Forbidden:
            await ctx.reply(embed=discord.Embed(description=f"{reactionFailure} The bot requires permissions to create webhooks in {channel.mention}.", color=discord.Color.red()))
            return
        
        self.bot.logging_webhooks[ctx.guild.id] = webhook
        async with self.bot.pool.acquire() as conn:
            await conn.execute("UPDATE guild_data SET log_channel = ?, log_webhook = ? WHERE guild_id = ?", (channel.id, webhook.url, ctx.guild.id))

        e = discord.Embed(
            description = f"{reactionSuccess} Successfully set the logging channel to {channel.mention}.",
            color = discord.Color.green()
        )
        await ctx.reply(embed=e)

async def setup(bot: Jovanes) -> None:
    await bot.add_cog(Management(bot))
