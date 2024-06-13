from __future__ import annotations

import discord
from discord.ext import commands
from discord import app_commands

import random
import os
import aiohttp
import pathlib
import asyncio

from babel import Locale
from typing import Dict, Union, Optional, Any, TYPE_CHECKING
from helpers import utils as _utils
from langdetect import detect 
#from selenium.webdriver import Firefox, FirefoxOptions
#from functools import partial

if TYPE_CHECKING:
    from ..main import Jovanes

class Fun(commands.Cog):
    def __init__(self, bot: Jovanes) -> None:
        self.bot = bot
        self.responses = [
            'It is certain.',
            'It is decidedly so.',
            'Without a doubt.',
            'Yes - definitely.',
            'You may rely on it.',
            'As I see it, yes.',
            'Most likely.',
            'Outlook good.',
            'Yes.',
            'Signs point to yes.',
            'Reply hazy, try again.',
            'Ask again later.',
            'Better not tell you now.',
            'Cannot predict now.',
            'Concentrate and ask again.',
            'Do not count on it.',
            'My reply is no.',
            'My sources say no.',
            'Outlook not so good.',
            'Very doubtful.'
        ]
        self._session = self.bot._session
        self.context_menu = app_commands.ContextMenu(
            name = "Translate",
            callback = self._context_translate,
#            allowed_contexts=app_commands.AppCommandContext(guild=True, dm_channel=True, private_channel=True),
#            allowed_installs=app_commands.AppInstallationType(guild=True, user=True)
        )
        self.bot.tree.add_command(self.context_menu)
        self.snipe_data = self.bot.snipe_data
        self.snipe_tasks: Dict[int, asyncio.Task] = {}
        self.who_say: Dict[int, int] = {}
        self.sniped_image: Optional[discord.Message] = None
#        options = FirefoxOptions()
#        options.add_argument('--headless')
#        self.browser = Firefox(options=options)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> Any:
        if not message.attachments:
            return
        
        file = message.attachments[0]
        if not os.path.exists("./images"):
            os.mkdir("./images")

        _format = file.filename.split(".")[::-1][0]
        await file.save(pathlib.Path(f"./images/{message.id}.{_format}"))

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> Any:
        if not message.guild:
            return

        self.snipe_data[message.channel.id] = message

    async def _translate(self, to_lang: str, text: str) -> Dict[str, str]:
        api_key = os.getenv("RAPIDAPI_KEY")
        if not api_key:
            return {}
        
        url = "https://microsoft-translator-text.p.rapidapi.com/translate"

        query = {"api-version":"3.0","to[0]":to_lang,"textType":"plain","profanityAction":"NoAction"}

        payload = [{"Text": text}]
        headers = {
        	"content-type": "application/json",
        	"X-RapidAPI-Key": api_key,
        	"X-RapidAPI-Host": "microsoft-translator-text.p.rapidapi.com"
        }
        resp = await self._session.post(url, json=payload, headers=headers, params=query)
        data = await resp.json()
        return data

    async def _context_translate(self, interaction: discord.Interaction, message: discord.Message):
        await interaction.response.defer(thinking=True)

        source_lang = None
        try:
            detected = detect(message.content)
            source_lang = Locale(detected[:2])
        except:
            pass

        to_lang = Locale(interaction.locale.value[:2])

        if source_lang == to_lang:
            return await interaction.followup.send(f"The message you tried to translate is already in {to_lang.display_name}.")
        try:
            translation = await self._translate(to_lang.language, message.content)
        except aiohttp.ClientPayloadError:
            await interaction.followup.send(f"I can\'t translate this message. It's too long.")
            return
        
        if not translation:
            await interaction.followup.send(f"No API key was found.")
            return
        
        try:
            translation = translation[0]['translations'][0]['text'] # type: ignore
        except KeyError:
            await interaction.followup.send("No translations were received from the API.")
            return
        
        e = discord.Embed(
            title = "Translation",
            description = f"Translation of the message by {message.author.mention} was **successful**.",
            color = discord.Color.blue(),
            timestamp = discord.utils.utcnow()
        )
        if not source_lang:
            try:
                source_lang = Locale(translation[0]['detectedLanguage']['language']) # type: ignore
            except:
                e.add_field(name="Detected Language", value="Couldn't detect language.")
            else:
                e.add_field(name="Detected Language", value=f"{source_lang.display_name} ({source_lang.get_display_name('en')})")
        else:
            e.add_field(name="Detected Language", value=f"{source_lang.display_name} ({source_lang.get_display_name('en')})")
            
        e.add_field(name="Target Language", value=to_lang.display_name)
        e.add_field(name="From", value=message.content, inline=False)
        e.add_field(name="To", value=translation)
        e.set_footer(text=f"Requested by {interaction.user}", icon_url=interaction.user.avatar.url if interaction.user.avatar is not None else None)
        await interaction.followup.send(embed=e)

    def get_size(self) -> str:
        chance = random.randint(1, 100)
        if chance < 50:
            if chance < 10:
                number = random.randint(5, 20)
            if chance < 30:
                number = random.randint(5, 15)
            if chance < 50:
                number = random.randint(1, 15)
        else:
            number = random.randint(1, 10)
        size = "=" * number
        return size

    @commands.command(name="gay", description="Shows the gay rate of a user (very accurate).")
    async def gay(self, ctx: commands.Context, *, name: str) -> Any:
        rate = random.randint(0, 100)
        e = discord.Embed(description = f":rainbow_flag: **{name}** is {rate}% gay.", color=discord.Color.random())
        await ctx.send(embed=e)

    @commands.command(name="hot", description="Shows the hotness rate of a user (very accurate).")
    async def hot(self, ctx: commands.Context, *, name: str) -> Any:
        rate = random.randint(0, 100)
        e = discord.Embed(description = f":sunglasses: **{name}** is {rate}% hot.", color=discord.Color.random())
        await ctx.send(embed=e)

    @commands.command(description="Shows the IQ rate of a member (very accurate).")
    async def iq(self, ctx: commands.Context, *, name: str) -> Any:
        rate = random.randint(70, 250)
        if rate % 100 < 25 or rate % 100 < 45:
            if rate % 100 < 25:
                rate = random.randint(70, 180)
            else:
                rate = random.randint(70, 120)

        e = discord.Embed(description = f"{name} has an IQ of **{rate}**.", color=discord.Color.random())
        await ctx.send(embed=e)

    @commands.command(description="Tells you if the person is a nigger.")
    async def nigger(self, ctx: commands.Context, *, name: str) -> Any:
        chance = random.choice([0, 1])
        if chance == 1:
            e = discord.Embed(description = f":man_tone5: {name} is a nigger.", color=0x000000)
        else:
            e = discord.Embed(description = f":man_tone1: {name} is not a nigger.", color=discord.Color.lighter_gray())
        await ctx.send(embed=e)

    @commands.command(description="Shows the penis size of a user.")
    async def size(self, ctx: commands.Context, *, name: str) -> Any:
        size = self.get_size()
        e = discord.Embed(description = f"{name}'s cock size is 8{size}D.", color=discord.Color.random())
        await ctx.send(embed=e)

    @commands.command(description="Shows the Fred profile of a member.")
    async def profile(self, ctx: commands.Context, member: Union[discord.User, discord.Member]) -> Any:
        assert ctx.guild

        member = member or ctx.author
    
        e = discord.Embed(
            color = discord.Color.random(),
            timestamp = ctx.message.created_at
        )
        gay = random.randint(1, 100)
        nigger = True if random.randint(1, 100) > 50 else False
        gender = random.choice(["Male", "Female", "Non-Binary"])
        iq = random.randint(70, 250)

        members = [m for m in ctx.guild.members if not m.bot]
        chance = random.randint(1, 100)
        if chance < 10:
            partner = "Not worthy of love."
        else:
            partner = random.choice(members).mention 

        size = self.get_size()
        if len(size) <= 5:
            cock_emoji = ":flushed:"
        elif len(size) > 5 and len(size) <= 10:
            cock_emoji = ":smirk:"
        elif len(size) > 10 and len(size) <= 15:
            cock_emoji = ":sunglasses:"
        else:
            cock_emoji = ":fire:"

        e.add_field(name="Age", value=f":bar_chart: | {random.randint(7, 20)} years old.", inline=False)
        e.add_field(name="Gender", value=f":helicopter: | {gender}", inline=False)
        e.add_field(name="Nigger", value=f":man_tone5: | {member.name} is a nigger." if nigger else f":man_tone1: | {member.name} is not a nigger.", inline=False)
        e.add_field(name="Gayness", value=f":rainbow_flag: | {gay}%", inline=False)
        e.add_field(name="IQ", value=f":brain: | {member.name} has an IQ of {iq}.", inline=False)
        e.add_field(name="Sausage Size", value=f"{cock_emoji} | 8{size}D")
        e.add_field(name="Partner", value=f":kiss: | {partner}", inline=False)
        e.set_footer(text = f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        e.set_author(name=f"{member.name}'s Fred Profile", icon_url=member.display_avatar.url)
        await ctx.send(embed=e)

    @commands.command(description="Finds a random ship.")
    async def ship(self, ctx: commands.Context):
        assert ctx.guild

        members = [m for m in ctx.guild.members if not m.bot]
        e = discord.Embed(description=f"I ship {random.choice(members).mention} and {random.choice(members).mention}.", color = discord.Color.random())
        await ctx.send(embed=e)

    @commands.command(description="Shows the avatar of a user.", aliases=["av"])
    async def avatar(self, ctx: commands.Context, user: Optional[discord.User | discord.Member]):
        user = user or ctx.author
        e = discord.Embed(color = discord.Color.blue(), timestamp=ctx.message.created_at)
        e.set_author(name=user.display_name, icon_url=user.display_avatar.url)
        e.set_image(url=user.display_avatar.url)
        e.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=e)

    @commands.command(name="8ball", description="An 8Ball, but digital.")
    async def _8ball(self, ctx: commands.Context, *, question: str):
        response = random.choice(self.responses)
        e = discord.Embed(
            title = ":8ball: 8ball",
            description = "The digital 8ball has spoken.",
            color = discord.Color.random(),
            timestamp = ctx.message.created_at
        )
        e.add_field(name="Question", value=question)
        e.add_field(name="Answer", value=response, inline=False)
        await ctx.send(embed=e)

    @commands.command(description="Shows the last deleted message in a channel.")
    async def snipe(self, ctx: commands.Context) -> Any:
        if ctx.channel.id not in self.snipe_data:
            await ctx.reply("No message were deleted in this channel recently.")
            return

        message = self.snipe_data[ctx.channel.id]

        e = discord.Embed(color=discord.Color.blue())
        e.set_author(name=message.author.display_name, icon_url=message.author.display_avatar)
        e.timestamp = message.created_at
        e.description = message.content if message.content else ""

        if message.attachments:
            filename = message.attachments[0].filename
            _format = filename.split(".")[::-1][0]
            e.description = filename
            try:
                file = discord.File(f"./images/{message.id}.{_format}", filename=filename)
            except:
                await ctx.reply(embed=e)
            else:
                if _format in ("jpg", "jpeg", "png", "webp", "bmp"):
                    e.set_image(url=f"attachment://{filename}")
                    await ctx.reply(file=file, embed=e)

                else:
                    await ctx.reply(f"Video sent by: {message.author.mention}", allowed_mentions=discord.AllowedMentions.none(), file=file)
            return

        if message.embeds:
            if message.embeds[0].url:
                await ctx.reply(f"GIF sent by {message.author.mention}.\n{message.embeds[0].url}", allowed_mentions=discord.AllowedMentions.none())
                return
            
            e.description += f"\n{message.embeds[0].description}"

        await ctx.reply(embed=e)
        
    @commands.command(description="Mock a message by a user.")
    async def mock(self, ctx: commands.Context[Jovanes], *, statement: Optional[str]) -> Any:
        if not statement and not ctx.message.reference:
            await ctx.reply("You must either provide a statement to mock or reference a message.")
            return

        if statement and ctx.message.reference:
            await ctx.reply("You can't reference a message and give a statement together.")
            return 

        if ctx.message.reference:
            resolved = ctx.message.reference.resolved
            if not resolved or not isinstance(resolved, discord.Message):
                await ctx.reply("An error occured while referencing that message.")
                return
            
            content = resolved.content
            if len(content) > 250: 
                await ctx.send("Message content exceeds 250 characters in length.")
                return
            
            mock = _utils.convert_to_mock(content)
            await ctx.message.delete()
            await resolved.reply(mock)
        else:
            if not statement:
                return
            
            if len(statement) > 250:
                await ctx.send("Statement cannot exceed 250 characters in length.")
                return
            
            mock = _utils.convert_to_mock(statement)
            await ctx.send(mock)

    @commands.command(name="say", description="Say something as the bot.")
    async def say(self, ctx: commands.Context[Jovanes], channel: discord.TextChannel, *, message: str) -> Any:
        if ctx.author.id not in self.bot.say_authorized:
            await ctx.reply("You're not authorized to use this command.")
            return

        m = await channel.send(message)
        self.who_say[m.id] = ctx.author.id
        await ctx.message.add_reaction('✅')

    @commands.command(name="cat", description="Shows a cat.")
    async def cat(self, ctx: commands.Context) -> Any:
        URL = "https://api.thecatapi.com/v1/images/search"
        
        res = await self._session.get(URL)
        data = await res.json()

        e = discord.Embed(
            title = "Here's a cat! :cat:",
            color = discord.Color.random()
        )

        e.set_image(url=data[0]['url'])
        await ctx.reply(embed=e)

#    @commands.command(name="screenshot", description="Sends a screenshot of a webpage.", aliases=["sc", "ss"])
#    async def screenshot(self, ctx: commands.Context[Jovanes], url: str) -> Any:
#        if not _utils.is_url(url):
#            e = discord.Embed(description=f"**{url}** is not a valid URL.", color=discord.Color.red())
#            await ctx.reply(embed=e)
#            return
#        
#        if url.startswith("www"):
#            url = f"https://{url}"
#
#        def save_screenshot(url: str):
#            assert ctx.guild
#
#            self.browser.get(url)
#
#            if not os.path.exists("./screenshots"):
#                os.mkdir("./screenshots")
#
#            self.browser.save_screenshot(f'./images/{ctx.guild.id}.png')
#            return discord.File(f"./images/{ctx.guild.id}.png", filename="screenshot.png")
#
#        def done_callback(future: asyncio.Future[discord.File]):
#            screenshot = future.result()
#            asyncio.create_task(ctx.reply(file=screenshot))
#
#        func = partial(save_screenshot, url)
#        loop = asyncio.get_event_loop()
#        fut = loop.run_in_executor(None, func)
#        fut.add_done_callback(done_callback)

    @commands.command(name="joke", description="Sends a random joke.")
    async def joke(self, ctx: commands.Context[Jovanes]) -> Any:
        URL = "https://v2.jokeapi.dev/joke/Any"

        res = await self._session.get(URL)
        data = await res.json()

        if data["type"] == "twopart":
            _setup = data["setup"]
            delivery = data["delivery"]

            await ctx.reply(f"{_setup}\n\n{delivery}")
        else:
            joke = data["joke"]
            await ctx.reply(joke)

    @commands.command(description="Lets you know who used the say command.")
    async def whosay(self, ctx: commands.Context[Jovanes]) -> Any:
        if ctx.message.reference is None:
            await ctx.reply("You must reference a message by the bot.")
            return
        
        resolved = ctx.message.reference.resolved
        if not resolved or isinstance(resolved, discord.DeletedReferencedMessage):
            await ctx.reply("Referenced message wasn't found in the message cache.")
            return
        
        if resolved.author.id != self.bot.user.id or resolved.id not in self.who_say: # type: ignore
            await ctx.reply("This is not a message sent by the command say.")
            return
        
        await ctx.message.delete()
        await resolved.reply(f"This message was sent by <@{self.who_say[resolved.id]}>.")

async def setup(bot: Jovanes) -> None:
    await bot.add_cog(Fun(bot))