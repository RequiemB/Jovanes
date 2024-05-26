from __future__ import annotations

import discord
from discord.ext import commands

from g4f.client import Client

import asyncio
import functools

from collections import deque
from typing import Deque, List, Dict, Tuple, TYPE_CHECKING
from helpers import views

if TYPE_CHECKING:
    from g4f.client import ChatCompletion, ImagesResponse
    from ..main import Jovanes

class AI(commands.Cog):
    def __init__(self, bot: Jovanes) -> None:
        self.bot = bot
        self.chat_model = "gpt-3.5-turbo"
        self.image_model = "openai"

        self.client = Client()
        self.queue: asyncio.Queue[Tuple[commands.Context[Jovanes], str, bool]] = asyncio.Queue(maxsize=5)
        self.chat_history: Deque[Dict[str, str]] = deque(maxlen=20)
        
        asyncio.create_task(self.handle_queue())

    async def handle_queue(self) -> None:
        while True:
            await asyncio.sleep(.5)
            if not self.queue.empty():
                ctx, text, is_img = await self.queue.get()
                if is_img:
                    await self.respond_img(ctx, text)
                else:
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

            func = functools.partial(self.client.chat.completions.create, model=self.chat_model, messages=list(self.chat_history)) # type: ignore
            loop = asyncio.get_event_loop()
            try:
                fut = loop.run_in_executor(None, func)
            except Exception as e:
                await ctx.reply("An error occured while processing your request. The error info has been sent to the developers.")
                return

            def callback(future: asyncio.Future[ChatCompletion]) -> None:
                response = future.result().choices[0].message.content

                if not response:
                    return

                data = {
                    "role": "assistant",
                    "content": response
                }
                self.chat_history.append(data) 

                if len(response) > 2000:
                    paginator = views.TextPaginator(response)
                    task = asyncio.create_task(ctx.reply(response[:2000], view=paginator))

                    def after(future: asyncio.Future[discord.Message]) -> None:
                        paginator.message = future.result()

                    task.add_done_callback(after)
                else:  
                    asyncio.create_task(ctx.reply(response[:2000]))

            fut.add_done_callback(callback) # type: ignore
        
    async def respond_img(self, ctx: commands.Context[Jovanes], prompt: str) -> None:
        if not ctx.guild or not ctx.channel or not ctx.channel.permissions_for(ctx.guild.me).embed_links:
            return
        
        async with ctx.channel.typing():
            func = functools.partial(self.client.images.generate, model=self.image_model, prompt=prompt)
            loop = asyncio.get_event_loop()

            try:
                fut = loop.run_in_executor(None, func)
            except Exception as e:
                await ctx.reply("An error occured while processing your request. The error info has been sent to the developers.")
                return
            
            def callback(future: asyncio.Future[ImagesResponse]) -> None:
                url = future.result().data[0].url

                if not url:
                    return
                
                e = discord.Embed(
                    title = f"{ctx.author.name}'s Request",
                    description = f"Prompt: **{prompt}**",
                    color = discord.Color.random(),
                    timestamp = discord.utils.utcnow()
                )
                e.set_image(url=url)
                asyncio.create_task(ctx.reply(embed=e))
                
            fut.add_done_callback(callback)

    @commands.command(name="chat", description="Chat with the AI.")
    async def chat(self, ctx: commands.Context[Jovanes], *, text: str) -> None:
        if self.queue.qsize() >= 5:
            await ctx.reply("The queue is currently full. Please retry again after a few seconds.")
            return
        
        await self.queue.put((ctx, text, False))
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