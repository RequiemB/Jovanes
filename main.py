from __future__ import annotations

import discord
from discord.ext import commands

import aiohttp
import asqlite
import traceback
import logging
import os
import asyncio

from pkgutil import iter_modules
from helpers import (
    logger as _logger,
    utils as _utils
)
from helpers.errors import EntityDisabled
from datetime import datetime

from typing import Optional, Dict, Union, List
from typing_extensions import Self
from dotenv import load_dotenv

logger = logging.getLogger("discord")
logger.setLevel(logging.INFO)
logger.propagate = False
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
handler.setFormatter(_logger.Logger()) 
logger.addHandler(handler)

DEFAULT_PREFIXES = ["?"]

class Jovanes(commands.Bot):
     
    async def _get_prefix(self, bot: Self, message: discord.Message) -> List[str]:
        guild = message.guild
        if not guild:
            return DEFAULT_PREFIXES
        
        if not self.pool:
            return DEFAULT_PREFIXES
        
        async with self.pool.acquire() as conn:
            res = await conn.fetchall("SELECT prefix FROM prefixes WHERE guild_id = ?", guild.id)

        if not res:
            return DEFAULT_PREFIXES
        
        prefixes: List[str] = []
        for row in res:
            prefixes.append(row[0])

        if len(prefixes) == 0:
            return DEFAULT_PREFIXES

        return prefixes

    def __init__(self) -> None:
        self._extensions = [m.name for m in iter_modules(['cogs'], prefix='cogs.')]
        self._extensions.extend(["jishaku"])
        self.snipe_data: Dict[int, discord.Message] = {}
        self.logger = logger
        self.trivia_streaks: Dict[int, int] = {}
        self.logging_webhooks: Dict[int, discord.Webhook] = {}

        self._session: aiohttp.ClientSession
        self.pool: asqlite.Pool

        super().__init__(
            command_prefix = self._get_prefix,
            intents = discord.Intents.all(),
            status = discord.Status.dnd, 
            activity = discord.Activity(name="joanus in the shower", type=discord.ActivityType.watching),
            owner_ids = [680416522245636183, 744487004812869662],
            case_insensitive = False
        )

        self.say_authorized: List[int] = []
        if self.owner_ids:
            self.say_authorized.extend(self.owner_ids)

    async def setup_hook(self) -> None:
        if not os.path.exists("./database"):
            os.mkdir("./database")

        async with self.pool.acquire() as conn:
            await _utils.set_up_database(conn)

        for extension in self._extensions:
            try:
                await self.load_extension(extension)
            except Exception:
                self.logger.error(f"Unable to load extension {extension}.")
                traceback.print_exc()
            else:
                self.logger.info(f"Loaded extension {extension}.")

        self.launch_time = datetime.now()

    async def on_ready(self) -> None:
        print(f"Logged in as {self.user}.")

    async def is_entity_disabled(self, entity: Union[commands.Command, commands.Cog], guild_id: int) -> bool:
        if isinstance(entity, (commands.Command, commands.Cog)):
            name = entity.qualified_name
            
            async with self.pool.acquire() as conn:
                res = await conn.fetchone("SELECT entity FROM configuration WHERE guild_id = ? AND entity = ?", (guild_id, name))

            return res is not None
    
    async def close(self) -> None:
        await bot.pool.close()
        await bot._session.close()

        bot.logger.info("Shutting down the bot...")
        await super().close()

    async def create_logging_webhook(self, guild: discord.Guild) -> Optional[discord.Webhook]:
        async with self.pool.acquire() as conn:
            res = await conn.fetchone("SELECT log_channel FROM guild_data WHERE guild_id = ?", (guild.id))

            if not res[0]:
                return

            channel = self.get_channel(res[0])
            if not channel or not isinstance(channel, discord.TextChannel):
                return

            webhook = await channel.create_webhook(name=self.user.name) # type: ignore
            self.logging_webhooks[guild.id] = webhook
            
            await conn.execute("UPDATE guild_data SET log_webhook = ? WHERE guild_id = ?", (webhook.url, guild.id))
            return webhook
        
bot = Jovanes()

# Bot checks

@bot.check
async def disabled_check(ctx: commands.Context[Jovanes]) -> bool:
    if not ctx.guild or not ctx.command:
        return True
    
    # Cog check

    cog = ctx.command.cog
    if cog:
        assert isinstance(cog, commands.Cog)

        if cog.qualified_name == "Management": # Check if it's the management cog
            return True

        disabled = await bot.is_entity_disabled(cog, ctx.guild.id)
        if disabled:
            raise EntityDisabled(commands.Cog)
    
    # Command check

    disabled = await bot.is_entity_disabled(ctx.command, ctx.guild.id)
    if disabled:
        raise EntityDisabled(commands.Command)

    return True

async def main() -> None:
    load_dotenv()

    if not os.path.exists("./database"):
        os.mkdir("./database")

    token = os.getenv("TOKEN")
    if token:
        async with bot, asqlite.create_pool("./database/database.db") as bot.pool, aiohttp.ClientSession() as bot._session:
            await bot.start(token)
    else:
        raise RuntimeError("No token was found in the envs.")

asyncio.run(main())