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
from datetime import datetime

from typing import Dict, Union, List, TYPE_CHECKING
from typing_extensions import Self
from dotenv import load_dotenv

logger = logging.getLogger("discord")
logger.setLevel(logging.INFO)
logger.propagate = False
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
handler.setFormatter(_logger.Logger()) 
logger.addHandler(handler)

DEFAULT_PREFIXES = ["fn "]

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
        
        print(res[0][0])
        
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

        super().__init__(
            command_prefix = self._get_prefix,
            intents = discord.Intents.all(),
            status = discord.Status.dnd, 
            activity = discord.Activity(name="joanus in the shower", type=discord.ActivityType.watching),
            owner_ids = [680416522245636183],
            case_insensitive = False
        )

    async def setup_hook(self) -> None:
        self._session = aiohttp.ClientSession()

        if not os.path.exists("./database"):
            os.mkdir("./database")
            
        self.pool = await asqlite.create_pool("database/database.db")
        self.logger.info("Created database connection pool.")

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
        if isinstance(entity, commands.Command):
            command = entity

            async with self.pool.acquire() as conn:
                res = await conn.fetchone("SELECT is_disabled FROM disabled WHERE guild_id = ? AND entity = ?", (guild_id, command.name))

            if not res or res[0] == 0:
                return False

            return True
        
        if isinstance(entity, commands.Cog):
            cog = entity
    
    async def close(self) -> None:
        await bot.pool.close()
        await bot._session.close()

        bot.logger.info("Shutting down the bot...")
        await super().close()
        
bot = Jovanes()

# Bot checks

@bot.check
async def disabled_check(ctx: commands.Context) -> bool:
    if not ctx.guild:
        return True
    
    assert isinstance(ctx.command, (commands.Cog, commands.Command))

    disabled = await bot.is_entity_disabled(ctx.command, ctx.guild.id)
    return not disabled

async def main() -> None:
    load_dotenv()

    token = os.getenv("TOKEN")
    if token:
        await bot.start(token)
    else:
        raise RuntimeError("No token was found in the envs.")

asyncio.run(main())