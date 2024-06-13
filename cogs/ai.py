from __future__ import annotations

import discord
from discord.ext import commands

import asyncio
import functools
import os

from collections import deque
from typing import Deque, Any, List, Dict, Tuple, TYPE_CHECKING
from helpers import views

if TYPE_CHECKING:
    from ..main import Jovanes

class AI(commands.Cog):
    def __init__(self, bot: Jovanes) -> None:
        self.bot = bot
        self.chat_model = "gpt-3.5-turbo"
        self.image_model = "openai"

        self.queue: asyncio.Queue[Tuple[commands.Context[Jovanes], str]] = asyncio.Queue(maxsize=5)
        self.chat_history: Deque[Dict[str, str]] = deque(maxlen=20)
        
        asyncio.create_task(self.handle_queue())

    async def get_ai_resp(self) -> str:
        api_key = os.getenv("RAPIDAPI_KEY")
        if not api_key:
            return ""
        
        URL = "https://chat-gpt26.p.rapidapi.com/"

        payload = {
            "model": self.chat_model,
            "messages": list(self.chat_history)
        }

        headers = {
	        "x-rapidapi-key": api_key,
	        "x-rapidapi-host": "chat-gpt26.p.rapidapi.com",
	        "Content-Type": "application/json"
        }

        resp = await self.bot._session.post(URL, json=payload, headers=headers)
        json = await resp.json()
        return json["choices"][0]["message"]["content"]

    async def handle_queue(self) -> None:
        while True:
            await asyncio.sleep(.5)
            if not self.queue.empty():
                ctx, text = await self.queue.get()
                await self.respond(ctx, text)
                self.queue.task_done()

    async def respond(self, ctx: commands.Context[Jovanes], text: str) -> None:
        if not ctx.guild or not ctx.channel or not ctx.channel.permissions_for(ctx.guild.me).send_messages:
            return
        
        async with ctx.channel.typing():
            data = {
                "role": "user",
                "content": text
            }

            self.chat_history.append(data)
            response = await self.get_ai_resp()

            if len(response) > 2000:
                paginator = views.TextPaginator(response)
                paginator.message = await ctx.reply(response[:2000], view=paginator)

            else:
                await ctx.reply(response[:2000])

    @commands.command(name="chat", description="Chat with the AI.")
    @commands.guild_only()
    async def chat(self, ctx: commands.Context[Jovanes], *, text: str) -> None:
        if self.queue.qsize() >= 5:
            await ctx.reply("The queue is currently full. Please retry again after a few seconds.")
            return
        
        await self.queue.put((ctx, text))
        await ctx.message.add_reaction('\U0000231b')

#    @commands.command(name="draw", description="Draw something using the AI.")
#    async def draw(self, ctx: commands.Context[Jovanes], *, prompt: str) -> None:
#        if self.queue.qsize() >= 5:
#            await ctx.reply("The queue is currently full. Please retry again after a few seconds.")
#            return
#        
#        await self.queue.put((ctx, prompt, True))
#        await ctx.message.add_reaction('\U0000231b')

async def setup(bot: Jovanes) -> None:
    await bot.add_cog(AI(bot))