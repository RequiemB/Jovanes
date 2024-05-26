from __future__ import annotations

import discord
from discord.ext import commands
from discord import app_commands

import random

from helpers import (
    utils as _utils,
    views
)

from typing import Dict, Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from ..main import Jovanes

TRIVIA_URL = "https://opentdb.com/api.php?amount=1"

class Games(commands.Cog):
    def __init__(self, bot: Jovanes) -> None:
        self.bot = bot
    
    def get_trivia_time(self, difficulty: str) -> int:
        match difficulty:
            case "easy":
                return 6
            case "medium":
                return 7
            case "hard":
                return 8
            case _:
                return 10
            
    def get_leaderboard_emoji(self, pos):
        match pos:
            case 1:
                return '\U0001f947'
            case 2:
                return '\U0001f948'
            case 3:
                return '\U0001f949'
            case _:
                return "*"

    @commands.command(name="trivia", description="Launches an interactive Trivia session with the bot.")
    @commands.guild_only()
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def trivia(self, ctx: commands.Context) -> None:
        assert isinstance(ctx.author, discord.Member)

        await ctx.defer()

        _type = random.choice(["boolean", "multiple"])

        url = TRIVIA_URL + f"&type={_type}"

        res = await self.bot._session.get(url)
        data = await res.json()

        category = _utils.sanitize_response(data["results"][0]["category"])
        difficulty = _utils.sanitize_response(data["results"][0]["difficulty"])
        question = _utils.sanitize_response(data["results"][0]["question"])
        time = self.get_trivia_time(difficulty)

        e = discord.Embed(
            description = f"**Question**: {question}\n**Time**: {time} seconds.",
            color = discord.Color.blue()
        )

        e.add_field(name="Category", value=category)
        e.add_field(name="Type", value=_type.title())
        e.add_field(name="Difficulty", value=difficulty.title())
        e.add_field(name="Status", value="Waiting for a button interaction.")
        e.set_author(name=f"{ctx.author.name}'s Trivia", icon_url=ctx.author.avatar)

        if _type == "boolean":
            correct_answer = _utils.sanitize_response(data["results"][0]["correct_answer"])
            incorrect_answer = _utils.sanitize_response(data["results"][0]["incorrect_answers"][0])
            view = views.TriviaBool(self.bot, ctx.author, correct_answer, incorrect_answer, e, time)
        else:
            correct_answer = _utils.sanitize_response(data["results"][0]["correct_answer"])
            incorrect_answers = []
            for i in range(3):
                incorrect_answers.append(_utils.sanitize_response(data["results"][0]["incorrect_answers"][i]))
            view = views.TriviaMultiple(self.bot, ctx.author, correct_answer, incorrect_answers, e, time)

        view.message = await ctx.send(embed=e, view=view)

    @commands.group(name="trivialb", description="The global leaderboard for the trivia.", invoke_without_command=True)
    @commands.guild_only()
    async def trivialb(self, ctx: commands.Context) -> None:
        async with self.bot.pool.acquire() as conn:
            res = await conn.fetchall("SELECT user_id, correct, wrong, streak FROM trivia ORDER BY correct DESC")

        e = discord.Embed(
            title = "Trivia Leaderboard",
            color = discord.Color.random(),
            timestamp = discord.utils.utcnow()
        )
        e.description = ""

        for i, user in enumerate(res, start=1):
            e.description += f"{self.get_leaderboard_emoji(i)} <@{user[0]}> (Correct: {user[1]}, Wrong: {user[2]}, Streak: {user[3]})\n" # type: ignore

        await ctx.send(embed=e)

    @trivialb.command(name="stats", aliases=["s"])
    async def trivialb_stats(self, ctx: commands.Context) -> None:        
        async with self.bot.pool.acquire() as conn:
            res = await conn.fetchall("SELECT user_id, correct, wrong, streak FROM trivia ORDER BY correct DESC")

        e = discord.Embed(
            title = "Trivia Leaderboard",
            color = discord.Color.random(),
            timestamp = discord.utils.utcnow()
        )
        e.description = ""

        ignored = {}
        percentages = {}
        for user in res:
            if (user[1] + user[2]) > 50:
                percentages[user[0]] = (user[1] / (user[1] + user[2])) * 100
            else:
                ignored[user[0]] = (user[1] / (user[1] + user[2])) * 100

        percentages = dict(sorted(percentages.items(), key=lambda x: float(x[1]), reverse=True))
        for i, (k, v) in enumerate(percentages.items(), start=1):
            e.description += f"{self.get_leaderboard_emoji(i)} <@{k}> (Percentage: **{v:.2f}%**)\n" # type: ignore

        if ignored:
            val = [f"{self.get_leaderboard_emoji(i)} <@{k}> (Percentage: **{v:.2f}%**)" for i, (k, v) in enumerate(ignored.items(), start=1)]
            e.add_field(name="Ignored (answered less than 50 questions)", value="\n".join(val))

        await ctx.send(embed=e)

    @commands.command(name="memory", description="Starts a memory game with the bot.")
    @commands.guild_only()
    async def memory(self, ctx: commands.Context) -> None:
        assert ctx.guild and isinstance(ctx.author, discord.Member)
        view = views.Memory(ctx.bot, ctx.author, ctx.guild)
        view.message = await ctx.send(f"The game will start soon, {ctx.author.mention}.", view=view)

    @commands.group(name="memorylb", description="The global leaderboard for the memory game.", invoke_without_command=True)
    @commands.guild_only()
    async def memorylb(self, ctx: commands.Context) -> None:
        async with self.bot.pool.acquire() as conn:
            res = await conn.fetchall("SELECT user_id, minutes, seconds, total_seconds FROM memory ORDER BY total_seconds ASC")

        e = discord.Embed(
            title = "Memory Leaderboard",
            color = discord.Color.random(),
            timestamp = discord.utils.utcnow()
        )
        e.description = ""

        for i, user in enumerate(res, start=1):
            e.description += f"{self.get_leaderboard_emoji(i)} <@{user[0]}> (Time: {user[1]} minute(s), {user[2]} second(s))\n" # type: ignore

        await ctx.send(embed=e)

    @commands.command(name="tictactoe", description="Plays a tic-tac-toe game with someone.", aliases=["ttt"])
    @commands.guild_only()
    async def tictactoe(self, ctx: commands.Context, player: discord.Member) -> None:
        assert isinstance(ctx.author, discord.Member)
        if player.id == ctx.author.id:
            await ctx.reply("You can't play with yourself.")
            return
        
        if player.bot:
            await ctx.reply("You can't play with a bot. Are you that lonely?")
            return

        e = discord.Embed(
            title = "Tic-Tac-Toe",
            description = f"{ctx.author.mention} has challenged you to a tic-tac-toe game. Do you accept?",
            color = discord.Color.random(),
            timestamp = discord.utils.utcnow()
        )
        view = views.TicTacToeChallenge(ctx.author, player)
        view.message = await ctx.send(player.mention, embed=e, view=view)

    @commands.group(name="tictactoelb", description="The global leaderboard for tic-tac-toe.", invoke_without_command=True)
    @commands.guild_only()
    async def tictactoelb(self, ctx: commands.Context) -> None:
        async with self.bot.pool.acquire() as conn:
            res = await conn.fetchall("SELECT winner FROM tictactoe")

        user_data: Dict[int, int] = {}

        e = discord.Embed(
            title = "Tic-Tac-Toe Leaderboard",
            color = discord.Color.random(),
            timestamp = discord.utils.utcnow()
        )
        e.description = ""

        if not res:
            e.description = "No one won any matches."
        else:
            for row in res:
                try:
                    user_data[row[0]] += 1
                except:
                    user_data[row[0]] = 1

            user_data = dict(sorted(user_data.items(), key=lambda x: x[1], reverse=True))

            for i, (k, v) in enumerate(user_data.items(), start=1):
                e.description += f"{self.get_leaderboard_emoji(i)} <@{k}> (Wins: {v})\n" # type: ignore

        await ctx.send(embed=e)

    @tictactoelb.command(name="info", description="Shows the individual match information of a user.")
    async def tictactoelb_info(self, ctx: commands.Context, member: Optional[discord.Member]) -> None:
        assert isinstance(ctx.author, discord.Member)
        member = member or ctx.author

        async with self.bot.pool.acquire() as conn:
            res = await conn.fetchall("SELECT winner, rival FROM tictactoe WHERE winner = ? OR rival = ?", (member.id, member.id))

        e = discord.Embed(
            title = "Tic-Tac-Toe Individual Match Info",
            color = discord.Color.random(),
            timestamp = discord.utils.utcnow()
        )
        e.description = ""
        
        if not res:
            e.description = f"{member.mention} didn't play any matches."
        else:
            for i, row in enumerate(res, start=1):
                if row[0] == member.id: # Won
                    e.description += f"* <@{member.id}> won against <@{row[1]}>.\n" # type: ignore
                else:
                    e.description += f"* <@{member.id}> lost against <@{row[0]}>.\n" # type: ignore

        await ctx.send(embed=e)

    @commands.hybrid_command(name="rps", description="Play a RPS match with another user.")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    @commands.guild_only()
    async def rps(self, ctx: commands.Context, player: discord.Member) -> None:
        assert isinstance(ctx.author, discord.Member)

        if player.id == ctx.author.id:
            await ctx.reply("You can't play with yourself.")
            return
        
        if player.bot:
            await ctx.reply("You can't play with a bot. Are you that lonely?")
            return


        e = discord.Embed(
            title = "RPS Match",
            description = "Waiting for both players to make their move.",
            color = discord.Color.blue(),
            timestamp = discord.utils.utcnow()
        )
        e.add_field(name=ctx.author.display_name, value="Waiting for response.")
        e.add_field(name=player.display_name, value="Waiting for response.")
        view = views.RPS(ctx.author, player, e)
        view.message = await ctx.send(f"{ctx.author.mention} V/S {player.mention}", embed=e, view=view)

    
    @commands.group(name="rpslb", description="The global leaderboard for rock-paper-scissors.", invoke_without_command=True)
    @commands.guild_only()
    async def rpslb(self, ctx: commands.Context) -> None:
        async with self.bot.pool.acquire() as conn:
            res = await conn.fetchall("SELECT winner FROM rps")

        user_data: Dict[int, int] = {}

        e = discord.Embed(
            title = "RPS Leaderboard",
            color = discord.Color.random(),
            timestamp = discord.utils.utcnow()
        )
        e.description = ""

        if not res:
            e.description = "No one won any matches."
        else:
            for row in res:
                try:
                    user_data[row[0]] += 1
                except:
                    user_data[row[0]] = 1

            user_data = dict(sorted(user_data.items(), key=lambda x: x[1], reverse=True))

            for i, (k, v) in enumerate(user_data.items(), start=1):
                e.description += f"{self.get_leaderboard_emoji(i)} <@{k}> (Wins: {v})\n" # type: ignore

        await ctx.send(embed=e)

    @rpslb.command(name="info", description="Shows the individual match information of a user.")
    async def rps_info(self, ctx: commands.Context, member: Optional[discord.Member]) -> None:
        assert isinstance(ctx.author, discord.Member)
        member = member or ctx.author

        async with self.bot.pool.acquire() as conn:
            res = await conn.fetchall("SELECT winner, rival FROM rps WHERE winner = ? OR rival = ?", (member.id, member.id))

        e = discord.Embed(
            title = "RPS Individual Match Info",
            color = discord.Color.random(),
            timestamp = discord.utils.utcnow()
        )
        e.description = ""
        
        if not res:
            e.description = f"{member.mention} didn't play any matches."
        else:
            for i, row in enumerate(res, start=1):
                if row[0] == member.id: # Won
                    e.description += f"* <@{member.id}> won against <@{row[1]}>.\n" # type: ignore
                else:
                    e.description += f"* <@{member.id}> lost against <@{row[0]}>.\n" # type: ignore

        await ctx.send(embed=e)

async def setup(bot: Jovanes) -> None:
    await bot.add_cog(Games(bot))