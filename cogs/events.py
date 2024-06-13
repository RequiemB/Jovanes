from __future__ import annotations

import discord
from discord.ext import commands
errors = commands.errors

import traceback

from config import reactionSuccess, reactionFailure
from helpers.errors import EntityDisabled
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
    async def on_message(self, message: discord.Message) -> Any:
        if not message.guild or message.author.bot:
            return
        
        if self.bot.user and f"<@{self.bot.user.id}>" in message.content:
            prefixes = await self.bot._get_prefix(self.bot, message)

            e = discord.Embed(
                title = f"Prefixes for {message.guild.name}",
                description = "\n".join([f"`{prefix}`" for prefix in prefixes]),
                color = discord.Color.blue(),
                timestamp = discord.utils.utcnow()
            )
            
            await message.reply(embed=e)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context[Jovanes], exception: errors.CommandError) -> Any:
        if isinstance(exception, IGNORED_EXCEPTIONS):
            return
        
        # Custom errors

        if isinstance(exception, EntityDisabled):
            _type = "command" if exception.type is commands.Command else "module"
            e = discord.Embed(description=f"{reactionFailure} This {_type} is currently disabled.", color=discord.Color.red())
            return await ctx.send(embed=e)
    
        if isinstance(exception, errors.ExpectedClosingQuoteError):
            e = discord.Embed(description=f"{reactionFailure} No closing {exception.close_quote} was found.", color=discord.Color.red())
            return await ctx.send(embed=e)
        if isinstance(exception, errors.CommandOnCooldown):
            e = discord.Embed(description=f"{reactionFailure} You're on cooldown. Try again after {exception.retry_after:2f}.", color=discord.Color.red())        
            return await ctx.send(embed=e)
        if isinstance(exception, errors.ChannelNotFound):
            e = discord.Embed(description=f"{reactionFailure} Channel was not found.", color=discord.Color.red())        
            return await ctx.send(embed=e)
        if isinstance(exception, (errors.MemberNotFound, errors.UserNotFound)):
            e = discord.Embed(description=f"{reactionFailure} User/Member was not found.", color=discord.Color.red())        
            return await ctx.send(embed=e)
        if isinstance(exception, errors.RoleNotFound):
            e = discord.Embed(description=f"{reactionFailure} Role was not found.", color=discord.Color.red())        
            return await ctx.send(embed=e)
        if isinstance(exception, errors.MissingRequiredArgument) or isinstance(exception, errors.BadArgument):
            if not ctx.command:
                return
            
            e = discord.Embed(description=f"{reactionFailure} Correct usage of the command: {ctx.command.name} {ctx.command.signature}", timestamp=ctx.message.created_at, color=discord.Color.red())
            e.set_footer(text="[] means the argument is optional and <> means the argument is required.")
            return await ctx.send(embed=e)
        
        if isinstance(exception, errors.MissingPermissions):
            permissions = ", ".join([p.replace("_", " ").title() for p in exception.missing_permissions])
            e = discord.Embed(
                description = f"{reactionFailure} You require the `{permissions}` permission{'s' if len(permissions) > 1 else ''} to execute this command.",
                color = discord.Color.red()
            )
            return await ctx.send(embed=e)

        raise exception
    
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> Any:
        if message.author.bot or not message.guild:
            return
        
        if message.guild.id not in self.bot.logging_webhooks:
            async with self.bot.pool.acquire() as conn:
                res = await conn.fetchone("SELECT log_webhook, log_channel FROM guild_data WHERE guild_id = ?", (message.guild.id))

                if not res:
                    return
                
                self.bot.logging_webhooks[message.guild.id] = discord.Webhook.from_url(res[0], session=self.bot._session)

        webhook = self.bot.logging_webhooks[message.guild.id]
                
        e = discord.Embed(
            title = ":notepad_spiral: Message Deleted",
            description = f"Message sent by {message.author.mention} was **deleted** in {message.channel.mention}.", # type: ignore
            color = discord.Color.blue(),
            timestamp = discord.utils.utcnow()
        )

        e.set_footer(text=f"Message ID: {message.id}")

        if message.content:
            e.add_field(name="Content", value=message.content)
        
        if message.attachments:
            e.set_image(url=message.attachments[0].proxy_url)

        try:
            await webhook.send(embed=e, username=message.guild.me.display_name, avatar_url=message.guild.me.display_avatar.url)
        except discord.NotFound:
            webhook = await self.bot.create_logging_webhook(message.guild)
            if webhook:
                await webhook.send(embed=e, username=message.guild.me.display_name, avatar_url=message.guild.me.display_avatar.url)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> Any:
        if not after.guild or after.author.bot:
            return
    
        if after.guild.id not in self.bot.logging_webhooks:
            async with self.bot.pool.acquire() as conn:
                res = await conn.fetchone("SELECT log_webhook, log_channel FROM guild_data WHERE guild_id = ?", (after.guild.id))

                if not res:
                    return
                
                self.bot.logging_webhooks[after.guild.id] = discord.Webhook.from_url(res[0], session=self.bot._session)

        webhook = self.bot.logging_webhooks[after.guild.id]

        e = discord.Embed(
            title = ":notepad_spiral: Message Edited",
            description = f"Message sent by {after.author.mention} was **edited** in {after.channel.mention}.", # type: ignore
            color = discord.Color.blue(),
            timestamp = discord.utils.utcnow()
        )

        e.set_footer(text=f"Message ID: {after.id}")
        e.add_field(name="Before", value=before.content).add_field(name="After", value=after.content)

        try:
            await webhook.send(embed=e, username=after.guild.me.display_name, avatar_url=after.guild.me.display_avatar.url)
        except discord.NotFound:
            webhook = await self.bot.create_logging_webhook(after.guild)
            if webhook:
                await webhook.send(embed=e, username=after.guild.me.display_name, avatar_url=after.guild.me.display_avatar.url)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> Any:
        guild = member.guild

        if guild.id not in self.bot.logging_webhooks:
            async with self.bot.pool.acquire() as conn:
                res = await conn.fetchone("SELECT log_webhook, log_channel FROM guild_data WHERE guild_id = ?", (guild.id))

                if not res:
                    return
                
                self.bot.logging_webhooks[guild.id] = discord.Webhook.from_url(res[0], session=self.bot._session)

        webhook = self.bot.logging_webhooks[guild.id]

        e = discord.Embed(
            title = ":notepad_spiral: Member Left",
            description = f"**{member.name}** left the server.",
            color = discord.Color.blue(),
            timestamp = discord.utils.utcnow()
        )

        try:
            await webhook.send(embed=e, username=guild.me.display_name, avatar_url=guild.me.display_avatar.url)
        except discord.NotFound:
            webhook = await self.bot.create_logging_webhook(guild)
            if webhook:
                await webhook.send(embed=e, username=guild.me.display_name, avatar_url=guild.me.display_avatar.url)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> Any:
        async with self.bot.pool.acquire() as conn:
            await conn.execute("INSERT INTO guild_data (guild_id) VALUES (?)", (guild.id))

async def setup(bot: Jovanes) -> None:
    await bot.add_cog(Events(bot))