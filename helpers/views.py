from __future__ import annotations

import discord
import random
import uuid
import asyncio
import json

from helpers import utils as _utils
from typing import Any, Optional, List, Dict, TYPE_CHECKING
from config import reactionFailure, reactionSuccess

if TYPE_CHECKING:
    from discord.ext.commands import Context
    from ..main import Jovanes

#MEMORY_EMOJIS = ['😀', '😁', '😂', '🤣', '😃', '😄', '😎', '🥲', '😙', '😗','🤗', '🙂', '🎈', '🧨', '✨', '🎉', '🎁', '🎀', '🎏','🎄', '🎃', '🎗️', '🎊', '🎠', '🌭', '🧈', '🍞', '🍕', '🧀' , '🌮', '🚒', '🚌', '💥', '💤']

MEMORY_EMOJIS: Dict[str, str] = {}

with open("./assets/emoji_map.json") as fp:
    MEMORY_EMOJIS = json.load(fp)

class TriviaMultiple(discord.ui.View):
    def __init__(self, bot: Jovanes, user: discord.Member, correct_answer: str, incorrect_answers: List[str], embed: discord.Embed, time: int) -> None:
        self.bot = bot
        self.user = user
        self.correct_answer = correct_answer
        self.answers = incorrect_answers
        self.answers.append(self.correct_answer)
        self.embed = embed
        self.buttons: Dict[str, discord.ui.Button] = {}
        self.message: Optional[discord.Message] = None
        super().__init__(timeout=time)

        for _ in range(4):
            answer = random.choice(self.answers)
            self.answers.remove(answer)

            unique_id = str(uuid.uuid4())[0:12]

            button = discord.ui.Button(label=answer, style=discord.ButtonStyle.grey, custom_id=f"trivia:{unique_id}")
            button.callback = self.process_answer
            self.add_item(button)
            self.buttons[f"trivia:{unique_id}"] = button

    async def on_timeout(self) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
                if item.label == self.correct_answer:
                    item.style = discord.ButtonStyle.green

        await _utils.update_trivia_score(self.bot, self.user.id, False)
        self.embed.color = discord.Color.red()
        self.embed.remove_field(3)
        self.embed.add_field(name="Status", value=f"{self.user.mention} ran out of time.")
        if self.message:
            await self.message.edit(embed=self.embed, view=self)

    async def process_answer(self, interaction: discord.Interaction[Jovanes]) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        custom_id = interaction.data["custom_id"] # type: ignore

        clicked_button = self.buttons[custom_id]
        if clicked_button.label == self.correct_answer:
            clicked_button.style = discord.ButtonStyle.green

            await _utils.update_trivia_score(interaction.client, interaction.user.id, True)        
            self.embed.color = discord.Color.green()    
            self.embed.remove_field(3)
            self.embed.add_field(name="Status", value=f"{interaction.user.mention} got the **correct** answer.", inline=False)
        else:
            clicked_button.style = discord.ButtonStyle.red
            for item in self.children:
                if isinstance(item, discord.ui.Button) and item.label == self.correct_answer:
                    item.style = discord.ButtonStyle.green

            await _utils.update_trivia_score(interaction.client, interaction.user.id, False)
            self.embed.color = discord.Color.red()
            self.embed.remove_field(3)
            self.embed.add_field(name="Status", value=f"{interaction.user.mention} got the **wrong** answer.", inline=False)

        self.stop()
        await interaction.response.edit_message(embed=self.embed, view=self)

class TriviaBool(discord.ui.View):
    def __init__(self, bot: Jovanes, user: discord.Member, correct_answer: str, incorrect_answer: str, embed: discord.Embed, time: int) -> None:
        self.bot = bot
        self.user = user
        self.correct_answer = correct_answer
        self.incorrect_answer = incorrect_answer
        self.embed = embed
        self.message: Optional[discord.Message] = None
        super().__init__(timeout=time)

    async def on_timeout(self) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
                if item.label == self.correct_answer:
                    item.style = discord.ButtonStyle.green

        await _utils.update_trivia_score(self.bot, self.user.id, False)
        self.embed.color = discord.Color.red()
        self.embed.remove_field(3)
        self.embed.add_field(name="Status", value=f"{self.user.mention} ran out of time.")
        if self.message:
            await self.message.edit(embed=self.embed, view=self)

    async def interaction_check(self, interaction: discord.Interaction[Jovanes]) -> bool:
        if interaction.user != self.user:
            await interaction.response.send_message("This is not your trivia.", ephemeral=True)
            return False
        
        return True

    async def process_answer(self, interaction: discord.Interaction[Jovanes], button: discord.ui.Button) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        if button.label == self.correct_answer:
            button.style = discord.ButtonStyle.green

            await _utils.update_trivia_score(interaction.client, interaction.user.id, True)        
            self.embed.color = discord.Color.green()    
            self.embed.remove_field(3)
            self.embed.add_field(name="Status", value=f"{interaction.user.mention} got the **correct** answer.", inline=False)
        else:
            button.style = discord.ButtonStyle.red
            correct_button = self.false if self.correct_answer == "False" else self.true
            correct_button.style = discord.ButtonStyle.green

            await _utils.update_trivia_score(interaction.client, interaction.user.id, False)
            self.embed.color = discord.Color.red()
            self.embed.remove_field(3)
            self.embed.add_field(name="Status", value=f"{interaction.user.mention} got the **wrong** answer.", inline=False)
            
        self.stop()
        await interaction.response.edit_message(embed=self.embed, view=self)

    @discord.ui.button(label="True", style=discord.ButtonStyle.grey)
    async def true(self, interaction: discord.Interaction[Jovanes], button: discord.ui.Button) -> None:
        await self.process_answer(interaction, button)

    @discord.ui.button(label="False", style=discord.ButtonStyle.grey)
    async def false(self, interaction: discord.Interaction[Jovanes], button: discord.ui.Button) -> None:
        await self.process_answer(interaction, button)

class Memory(discord.ui.View):
    def __init__(self, bot: Jovanes, user: discord.Member, guild: discord.Guild) -> None:
        self.bot = bot
        self.user = user
        self.guild = guild
        self.message: Optional[discord.Message] = None

        super().__init__(timeout=300.0)

        self.selected_button: Optional[str] = None # We store the custom_id here, this entire thing works on custom_ids

        self.selected_emojis = random.sample(list(MEMORY_EMOJIS.values()), k=12)
        self.added_emojis: List[str] = []
        self.buttons: Dict[str, discord.ui.Button] = {}
        self.emojis: Dict[str, str] = {}
        self.finished: List[str] = []
        self.started = False
        self.started_time = None

        self.get_buttons_ready()
        asyncio.create_task(self.start_game())

    def get_buttons_ready(self) -> None:
        i = 1
        while i <= 25:
            unique_id = str(uuid.uuid4())[0:16]

            if i == 13: # Ignore the middle part
                self.buttons[unique_id] = discord.ui.Button(label='\u2800', style=discord.ButtonStyle.blurple, custom_id=unique_id, disabled=True)
            else:
                if len(self.selected_emojis) == 0:
                    emoji = random.choice(self.added_emojis)
                    self.added_emojis.remove(emoji)
                else:
                    emoji = random.choice(self.selected_emojis)
                    if emoji in self.added_emojis:
                        self.selected_emojis.remove(emoji)
                    else:
                        self.added_emojis.append(emoji)

                self.buttons[unique_id] = discord.ui.Button(emoji=emoji, style=discord.ButtonStyle.grey, custom_id=unique_id)
                self.emojis[unique_id] = emoji
                
            self.buttons[unique_id].callback = self.button_callback
            self.add_item(self.buttons[unique_id])
            i += 1

    def hide_all_buttons(self) -> None:
        for index, item in enumerate(self.children, start=1):
            if isinstance(item, discord.ui.Button) and index != 13:
                item.emoji = '\U00002753'

    async def start_game(self) -> None:
        await asyncio.sleep(3)
        
        self.started = True
        self.started_time = discord.utils.utcnow()
        self.hide_all_buttons()
        if self.message:
            await self.message.edit(content=f"Game has started, {self.user.mention}.", view=self)

    async def check_status(self) -> None:
        if len(self.finished) == 12 and self.message:
            self.stop()
            time_elapsed = discord.utils.utcnow() - self.started_time # type: ignore
            minutes, seconds = divmod(time_elapsed.total_seconds(), 60)
            await self.message.edit(content=f"Congrats {self.user.mention}, you finished in {int(minutes)} minute(s) and {int(seconds)} seconds.")

            async with self.bot.pool.acquire() as conn:
                res = await conn.fetchone("SELECT minutes, seconds FROM memory WHERE user_id = ?", (self.user.id))

            if not res:
                current_time = int(minutes) * 60 + int(seconds)
                await conn.execute("INSERT INTO memory (user_id, minutes, seconds, total_seconds) VALUES (?, ?, ?, ?)", (self.user.id, int(minutes), int(seconds), current_time))
                await conn.commit()
            else:
                saved_time = res[0] * 60 + res[1]
                current_time = int(minutes) * 60 + int(seconds)
                if (current_time < saved_time):
                    await conn.execute("UPDATE memory SET minutes = ?, seconds = ?, total_seconds = ? WHERE user_id = ?", (int(minutes), int(seconds), current_time, self.user.id))
                    await conn.commit()

    async def on_timeout(self) -> None:
        for index, item in enumerate(self.children, start=1):
            if isinstance(item, discord.ui.Button) and index != 13 and item.custom_id is not None and item.emoji == '\U00002753':
                item.emoji = self.emojis[item.custom_id]
                item.style = discord.ButtonStyle.grey
                item.disabled = True

        if self.message:
            await self.message.edit(content=f"You ran out of time, {self.user.mention}.", view=self)

    async def interaction_check(self, interaction: discord.Interaction[Jovanes]) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This is not your memory game.", ephemeral=True)
            return False
        
        return True

    async def button_callback(self, interaction: discord.Interaction[Jovanes]) -> None:
        if not self.message:
            return
        
        if not self.started:
            await interaction.response.send_message(f"Calm down {interaction.user.mention}, game hasn't started yet.", ephemeral=True)
            return

        custom_id = interaction.data["custom_id"] # type: ignore
        current = self.buttons[custom_id]

        current.emoji = self.emojis[custom_id]
        current.disabled = True

        if self.selected_button:
            prev = self.buttons[self.selected_button]
            if self.emojis[self.selected_button] == self.emojis[custom_id]:
                self.selected_button = None
                prev.disabled, current.disabled = True, True
                prev.style, current.style = discord.ButtonStyle.green, discord.ButtonStyle.green
                self.finished.append(self.emojis[custom_id])

                await interaction.response.edit_message(view=self)
                await self.check_status()
            else:
                self.selected_button = None
                prev.style, current.style = discord.ButtonStyle.red, discord.ButtonStyle.red
                await interaction.response.edit_message(view=self)

                await asyncio.sleep(1)

                prev.style, current.style = discord.ButtonStyle.grey, discord.ButtonStyle.grey
                prev.emoji, current.emoji = '\U00002753', '\U00002753' 
                prev.disabled, current.disabled = False, False
                await self.message.edit(view=self)
        else:
            self.selected_button = custom_id
            current.emoji = self.emojis[custom_id]
            current.style = discord.ButtonStyle.blurple
            await interaction.response.edit_message(view=self)

class TicTacToe(discord.ui.View):
    def __init__(self, player_1: discord.Member, player_2: discord.Member, totem: Dict[int, str]) -> None:
        self.player_1 = player_1
        self.player_2 = player_2
        self.current_turn: Optional[discord.Member] = None
        self.totem = totem
        self.total_clicks = 0
        super().__init__(timeout=None)

        self.buttons: Dict[str, discord.ui.Button] = {}
        self.get_buttons_ready()
        self.timeout_task: Optional[asyncio.Task] = None

    async def interaction_check(self, interaction: discord.Interaction[Jovanes]) -> bool:
        if not self.current_turn:
            return False
        
        if interaction.user.id != self.current_turn.id:
            await interaction.response.send_message(f"This is {self.current_turn.mention}'s turn.", ephemeral=True)
            return False
        
        return True

    def get_buttons_ready(self) -> None:
        current_row = 0
        for i in range(9):
            if i != 0 and i % 3 == 0:
                current_row += 1

            unique_id = str(uuid.uuid4())[0:8]
            button = discord.ui.Button(label='\u2800', style=discord.ButtonStyle.grey, row=current_row, custom_id=unique_id)
            button.callback = self.callback
            self.buttons[unique_id] = button
            self.add_item(button)

    async def end_game_timeout(self, bot: Jovanes, message: discord.Message) -> None:
        winner = self.player_1 if self.current_turn.id == self.player_2.id else self.player_2 # type: ignore
        rival = self.player_1 if winner.id == self.player_2.id else self.player_2

        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        e = discord.Embed(
            title = "Tic-Tac-Toe",
            description = f"{winner.mention} has won the game because {rival.mention} didn't move in time.",
            color = discord.Color.green(),
            timestamp = discord.utils.utcnow()
        )

        async with bot.pool.acquire() as conn:
            await conn.execute("INSERT INTO tictactoe (winner, rival) VALUES (?, ?)", (winner.id, rival.id))

        await message.edit(embed=e, view=self)

    async def end_game(self, interaction: discord.Interaction[Jovanes], buttons: List[discord.ui.Button]) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

            if item in buttons:
                item.style = discord.ButtonStyle.green

        e = discord.Embed(
            title = "Tic-Tac-Toe",
            description = f"{interaction.user.mention} has won the game.",
            color = discord.Color.green(),
            timestamp = discord.utils.utcnow()
        )

        if self.timeout_task:
            self.timeout_task.cancel()

        self.stop()

        rival = self.player_1 if self.current_turn.id == self.player_2.id else self.player_2 # type: ignore
        async with interaction.client.pool.acquire() as conn:
            await conn.execute("INSERT INTO tictactoe (winner, rival) VALUES (?, ?)", (interaction.user.id, rival.id))
            
        await interaction.response.edit_message(view=self, embed=e)

    async def callback(self, interaction: discord.Interaction[Jovanes]) -> None:
        custom_id = interaction.data["custom_id"] # type: ignore

        clicked_button = self.buttons[custom_id]
        totem = self.totem[interaction.user.id]

        if clicked_button.label != '\u2800':
            await interaction.response.send_message("This slot has already been marked.", ephemeral=True)
            return

        clicked_button.label = totem

        for i, item in enumerate(self.children, start = 1):
            if not isinstance(item, discord.ui.Button): continue 
            
            if i in (1, 2, 3): # Vertical check
                middle = (i + 3) - 1 # Indexing starts at 0
                last = (i + 6) - 1

                if (item.label == totem and self.children[middle].label == totem and self.children[last].label == totem): # type: ignore
                    await self.end_game(interaction, [item, self.children[middle], self.children[last]]) # type: ignore
                    return

            if i in (1, 4, 7): # Horizontal check  
                middle = (i + 1) - 1
                last = (i + 2) - 1

                if (item.label == totem and self.children[middle].label == totem and self.children[last].label == totem): # type: ignore
                    await self.end_game(interaction, [item, self.children[middle], self.children[last]]) # type: ignore
                    return

            if i in (1, 3): # Diagonal check
                middle = 5 - 1
                last = (9 if i == 1 else 7) - 1

                if (item.label == totem and self.children[middle].label == totem and self.children[last].label == totem): # type: ignore
                    await self.end_game(interaction, [item, self.children[middle], self.children[last]]) # type: ignore
                    return
                
        self.total_clicks += 1
        if self.total_clicks == 9: # Draw
            for item in self.children:
                if isinstance(item, discord.ui.Button):
                    item.disabled = True

            e = discord.Embed(
                title = "Tic-Tac-Toe",
                description = f"Game ended in a draw.",
                color = discord.Color.greyple(),
                timestamp = discord.utils.utcnow()
            )
            self.stop()
            await interaction.response.edit_message(view=self, embed=e)
            return

        self.current_turn = self.player_1 if self.player_1.id != interaction.user.id else self.player_2
        e = interaction.message.embeds[0] # type: ignore
        e.description = f"{self.current_turn.mention}'s (**{self.totem[self.current_turn.id]}**) turn."

        if self.timeout_task:
            self.timeout_task.cancel()
        
        async def func():
            await asyncio.sleep(120)
            await self.end_game_timeout(interaction.client, interaction.message) # type: ignore

        self.timeout_task = asyncio.create_task(func())

        await interaction.response.edit_message(embed=e, view=self)

class TicTacToeChallenge(discord.ui.View):
    def __init__(self, player: discord.Member, challenged_player: discord.Member) -> None:
        self.player = player
        self.challenged_player = challenged_player
        self.message: Optional[discord.Message] = None
        self.totem: Dict[int, str] = {}
        super().__init__(timeout=60.0)

    async def interaction_check(self, interaction: discord.Interaction[Jovanes]) -> bool:
        if interaction.user.id != self.challenged_player.id:
            await interaction.response.send_message(f"This can only be used by {self.challenged_player.mention}.", ephemeral=True)
            return False
        
        return True
    
    async def on_timeout(self) -> None:
        e = discord.Embed(
            title = "Tic-Tac-Toe",
            description = "Invitation timed out.",
            color = discord.Color.blue(),
            timestamp = discord.utils.utcnow()
        )
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        if self.message:
            await self.message.edit(embed=e, view=self)
    
    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction[Jovanes], button: discord.ui.Button) -> None:
        self.stop()
        list_of_players = [self.player, self.challenged_player]
        chosen_player = random.choice([self.player, self.challenged_player])
        list_of_players.remove(chosen_player)
        
        self.totem[chosen_player.id] = "X"
        self.totem[list_of_players[0].id] = "O"
        game = TicTacToe(self.player, self.challenged_player, self.totem)
        game.current_turn = chosen_player
        e = discord.Embed(
            title = "Tic-Tac-Toe",
            description = f"{game.current_turn.mention}'s (**{self.totem[game.current_turn.id]}**) turn.",
            color = discord.Color.blue(),
            timestamp = discord.utils.utcnow()
        )
        await interaction.response.edit_message(content=f"{self.player.mention} V/S {self.challenged_player.mention}", embed=e, view=game)

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.red)
    async def decline(self, interaction: discord.Interaction[Jovanes], button: discord.ui.Button) -> None:
        e = discord.Embed(
            title = "Tic-Tac-Toe",
            description = f"{self.challenged_player.mention} declined {self.player.mention}'s challenge to a Tic-Tac-Toe match.",
            color = discord.Color.random(),
            timestamp = discord.utils.utcnow()
        )
        self.stop()
        await interaction.response.edit_message(embed=e, view=None)

class RPS(discord.ui.View):
    def __init__(self, player_1: discord.Member, player_2: discord.Member, embed: discord.Embed) -> None:
        self.player_1 = player_1
        self.player_2 = player_2
        self.players = [self.player_1.id, self.player_2.id]
        self.embed = embed
        self.message: Optional[discord.Message] = None
        self.moves: Dict[int, str] = {}
        super().__init__(timeout=300.0)

    async def on_timeout(self) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        if self.player_1.id in self.players:
            unmoved = self.player_2
        else:
            unmoved = self.player_1

        self.embed.description = f"{unmoved.mention} didn't move in time."
        self.embed.color = discord.Color.greyple()
        
        if self.message:
            await self.message.edit(view=self, embed=self.embed)

    async def interaction_check(self, interaction: discord.Interaction[Jovanes]) -> bool:
        if interaction.user.id not in self.players:
            await interaction.response.send_message(f"This is a match between {self.player_1.mention} and {self.player_2.mention}, you can't play in this.", ephemeral=True)
            return False
    
        return True
    
    def get_winner(self, moves: List[str]) -> str:
        if "paper" in moves and "scissors" in moves:
            return "scissors"
        if "paper" in moves and "rock" in moves:
            return "paper"
        if "scissors" in moves and "rock" in moves:
            return "rock"
        
        # It's a draw
        return ""
        
    def get_emoji(self, move: str) -> str:
        match move:
            case "paper":
                return ":page_facing_up:"
            case "rock":
                return ":rock:"
            case "scissors":
                return ":scissors:"
            case _:
                return ""
        
    async def check_win(self, interaction: discord.Interaction[Jovanes]) -> None:
        # Show the selected moves publicly
        self.embed.remove_field(0)
        self.embed.insert_field_at(0, name=self.player_1.display_name, value=f"{self.get_emoji(self.moves[self.player_1.id])} {self.moves[self.player_1.id].title()}")
        
        self.embed.remove_field(1)
        self.embed.insert_field_at(1, name=self.player_2.display_name, value=f"{self.get_emoji(self.moves[self.player_2.id])} {self.moves[self.player_2.id].title()}")
        winner = self.get_winner([m for m in self.moves.values()])
        if winner:     
            for k, v in self.moves.items():
                if v == winner: winner = k

            assert type(winner) is int

            winner = interaction.client.get_user(winner)
            assert winner

            self.embed.description = f"{winner.mention} has won the game."
            self.embed.color = discord.Color.green()
            
            rival = self.player_1 if winner.id == self.player_2.id else self.player_2
            async with interaction.client.pool.acquire() as conn:
                await conn.execute("INSERT INTO rps (winner, rival) VALUES (?, ?)", (winner.id, rival.id))
        else:
            self.embed.description = "Both the players made the same move. Game ended in a draw."
            self.embed.color = discord.Color.greyple()

        self.stop()

        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        await interaction.response.edit_message(view=self, embed=self.embed)

    @discord.ui.button(label="Rock", style=discord.ButtonStyle.grey, emoji='\U0001faa8')
    async def rock(self, interaction: discord.Interaction[Jovanes], button: discord.ui.Button) -> None:
        if interaction.user.id in self.moves:
            await interaction.response.send_message("You already made your move in this match.", ephemeral=True)
            return

        self.moves[interaction.user.id] = "rock"

        i = self.players.index(interaction.user.id)
        self.embed.remove_field(i)
        self.embed.insert_field_at(i, name=interaction.user.display_name, value="Moved.")
        if len(self.moves) == 2:
            await self.check_win(interaction)
        else:
            await interaction.response.edit_message(embed=self.embed, view=self)
            await interaction.followup.send("You selected :rock: Rock.", ephemeral=True)

    @discord.ui.button(label="Paper", style=discord.ButtonStyle.grey, emoji='\U0001f4c4')
    async def paper(self, interaction: discord.Interaction[Jovanes], button: discord.ui.Button) -> None:
        if interaction.user.id in self.moves:
            await interaction.response.send_message("You already made your move in this match.", ephemeral=True)
            return

        self.moves[interaction.user.id] = "paper"

        i = self.players.index(interaction.user.id)
        self.embed.remove_field(i)
        self.embed.insert_field_at(i, name=interaction.user.display_name, value="Moved.")
        if len(self.moves) == 2:
            await self.check_win(interaction)
        else:
            await interaction.response.edit_message(embed=self.embed, view=self)
            await interaction.followup.send("You selected :page_facing_up: Paper.", ephemeral=True)

    @discord.ui.button(label="Scissors", style=discord.ButtonStyle.grey, emoji="✂")
    async def scissors(self, interaction: discord.Interaction[Jovanes], button: discord.ui.Button) -> None:
        if interaction.user.id in self.moves:
            await interaction.response.send_message("You already made your move in this match.", ephemeral=True)
            return

        self.moves[interaction.user.id] = "scissors"

        i = self.players.index(interaction.user.id)
        self.embed.remove_field(i)
        self.embed.insert_field_at(i, name=interaction.user.display_name, value="Moved.")
        if len(self.moves) == 2:
            await self.check_win(interaction)
        else:
            await interaction.response.edit_message(embed=self.embed, view=self)
            await interaction.followup.send("You selected :scissors: Scissors.", ephemeral=True)

class GuessModal(discord.ui.Modal):
    def __init__(self, view: Guess) -> None:
        self.view = view
        super().__init__(title="Guess")
        self.guess = discord.ui.TextInput(label="Guess", placeholder=f"Type a number in the range {view.min_range} - {view.max_range}")
        self.add_item(self.guess)

    async def on_submit(self, interaction: discord.Interaction[Jovanes]) -> None:
        try:
            guess = int(self.guess.value)
        except ValueError:
            await interaction.response.send_message("Input must be an integer.", ephemeral=True)
            return
        
        if guess < self.view.min_range or guess > self.view.max_range:
            await interaction.response.send_message(f"The range is `{self.view.min_range} - {self.view.max_range}`. Your input was `{guess}`.", ephemeral=True)
            return
        
        self.view.guesses[interaction.user.id] += 1

        if guess == self.view.num:
            self.stop()
            self.view.end_game_task.cancel()
            await interaction.response.send_message(f"{interaction.user.mention} won the game. The number was {guess}.")
            log = self.view.embed.fields[2].value
            assert log is not None

            if log.startswith("No guesses"):
                log = f"{reactionSuccess} {interaction.user.mention}"
            else:
                log += f"\n{reactionSuccess} {interaction.user.mention}"

            self.view.embed.remove_field(2)
            self.view.embed.insert_field_at(2, name="Guesses", value=log, inline=False)
            self.view.guess.disabled = True
            self.view.guess.label = f"Winner: {interaction.user.display_name}"
            
            async with interaction.client.pool.acquire() as conn:
                res = await conn.fetchone("SELECT win FROM guess WHERE user_id = ?", (interaction.user.id))

                if not res:
                    await conn.execute("INSERT INTO guess (user_id, wins) VALUES (?, ?)", (interaction.user.id, 1))
                else:
                    wins = res[0]
                    wins += 1

                    await conn.execute("UPDATE guess SET wins = ? WHERE user_id = ?", (wins, interaction.user.id))
 
            if self.view.message:
                await self.view.message.edit(embed=self.view.embed, view=self)
        else:
            await interaction.response.send_message(f"Your guess was wrong.", ephemeral=True)
            log = self.view.embed.fields[2].value
            assert log is not None

            if log.startswith("No guesses"):
                log = f"{reactionFailure} {interaction.user.mention}"
            else:
                log += f"\n{reactionFailure} {interaction.user.mention}"

            self.view.embed.remove_field(2)
            self.view.embed.insert_field_at(2, name="Guesses", value=log, inline=False)

            if self.view.message:
                await self.view.message.edit(embed=self.view.embed)

class Guess(discord.ui.View):
    def __init__(self, *, num: int, guesses: int, min_range: int, max_range: int, embed: discord.Embed) -> None:
        self.num = num
        self.no_of_guesses = guesses
        self.min_range = min_range
        self.max_range = max_range
        self.embed = embed
        super().__init__()

        self.guesses: Dict[int, int] = {}
        self.message: Optional[discord.Message] = None
        self.end_game_task = asyncio.create_task(self.end_game())

    async def end_game(self) -> None:
        await asyncio.sleep(300)
        self.guess.disabled = True
        self.stop()

        if self.message:
            await self.message.edit(content=f"No one guessed the correct number. It was `{self.num}`.", view=self)

    @discord.ui.button(label="Guess", style=discord.ButtonStyle.grey)
    async def guess(self, interaction: discord.Interaction[Jovanes], button: discord.ui.Button) -> Any:
        if interaction.user.id not in self.guesses:
            self.guesses[interaction.user.id] = 0

        if self.guesses[interaction.user.id] == self.no_of_guesses:
            await interaction.response.send_message("You reached your maximum guesses.", ephemeral=True)
            return
        
        await interaction.response.send_modal(GuessModal(self))

class TextPaginator(discord.ui.View):
    def __init__(self, content: str) -> None:
        self.message: Optional[discord.Message] = None
        self.split_parts: List[str] = []

        while len(content) > 2000:
            split = content[:2000]
            self.split_parts.append(split)
            content = content[2000:]

        self.split_parts.append(content)

        self.current_page = 1
        self.total_pages = len(self.split_parts)
        super().__init__(timeout=300.0)

        self.configure_button_availability()
        self.page_button.label = f"{self.current_page}/{self.total_pages}"

    async def on_timeout(self) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        if self.message:
            await self.message.edit(view=self)

    def configure_button_availability(self) -> None:
        if self.current_page == 1:
            self.rewind.disabled = True
            self.previous.disabled = True
            self.next.disabled = False
            self.forward.disabled = False
        elif self.current_page == self.total_pages:
            self.rewind.disabled = False
            self.previous.disabled = False
            self.next.disabled = True
            self.forward.disabled = True
        else:
            for item in self.children:
                if isinstance(item, discord.ui.Button) and "/" not in item.label: # type: ignore
                    item.disabled = False

    @discord.ui.button(label="<<", style=discord.ButtonStyle.grey)
    async def rewind(self, interaction: discord.Interaction[Jovanes], button: discord.ui.Button) -> None:
        self.current_page = 1
        self.page_button.label = f"{self.current_page}/{self.total_pages}"
        self.configure_button_availability()

        await interaction.response.edit_message(content=self.split_parts[self.current_page-1], view=self)

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.blurple)
    async def previous(self, interaction: discord.Interaction[Jovanes], button: discord.ui.Button) -> None:
        self.current_page -= 1
        self.page_button.label = f"{self.current_page}/{self.total_pages}"
        self.configure_button_availability()

        await interaction.response.edit_message(content=self.split_parts[self.current_page-1], view=self)

    @discord.ui.button(label="0/0", style=discord.ButtonStyle.grey, disabled=True)
    async def page_button(self, interaction: discord.Interaction[Jovanes], button: discord.ui.Button) -> None:
        ...

    @discord.ui.button(label="Next", style=discord.ButtonStyle.blurple)
    async def next(self, interaction: discord.Interaction[Jovanes], button: discord.ui.Button) -> None:
        self.current_page += 1
        self.page_button.label = f"{self.current_page}/{self.total_pages}"
        self.configure_button_availability()

        await interaction.response.edit_message(content=self.split_parts[self.current_page-1], view=self)

    @discord.ui.button(label=">>", style=discord.ButtonStyle.grey)
    async def forward(self, interaction: discord.Interaction[Jovanes], button: discord.ui.Button) -> None:
        self.current_page = self.total_pages
        self.page_button.label = f"{self.current_page}/{self.total_pages}"
        self.configure_button_availability()

        await interaction.response.edit_message(content=self.split_parts[self.current_page-1], view=self)

class PrefixRemoveSelect(discord.ui.Select['PrefixRemove']):
    def __init__(self, prefixes: List[str]) -> None:
        self.prefixes = prefixes
        self.stripped_prefixes = [prefix.strip() for prefix in self.prefixes]

        options = [discord.SelectOption(label=prefix, value=prefix) for prefix in prefixes]
        super().__init__(
            placeholder = "Select a prefix to remove",
            options = options
        )

    async def callback(self, interaction: discord.Interaction[Jovanes]) -> Any:
        assert interaction.guild

        async with interaction.client.pool.acquire() as conn:
            actual_prefix = self.prefixes[self.stripped_prefixes.index(self.values[0])]
            await conn.execute("DELETE FROM prefixes WHERE guild_id = ? AND prefix = ?", (interaction.guild.id, actual_prefix))

        e = discord.Embed(
            title = "Prefix Remover",
            description = "Select a prefix to remove from the dropdown below.",
            color = discord.Color.blue(),
            timestamp = discord.utils.utcnow()
        )
        i = self.stripped_prefixes.index(self.values[0])
        self.options.pop(i)
        self.prefixes.pop(i)
        self.stripped_prefixes.remove(self.values[0])

        e.add_field(name="Prefixes", value="\n".join([f"`{prefix}`" for prefix in self.prefixes]))
        if len(self.prefixes) == 1:
            self.view.children[0].disabled = True # type: ignore

        await interaction.response.edit_message(embed=e, view=self.view)

class PrefixRemove(discord.ui.View):
    def __init__(self, ctx: Context[Jovanes], prefixes: List[str]) -> None:
        self.ctx = ctx
        self.prefixes = prefixes
        self.message: Optional[discord.Message] = None
        
        super().__init__(timeout=300.0)
        self.add_item(PrefixRemoveSelect(self.prefixes))

    async def on_timeout(self) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Select):
                item.disabled = True

        if self.message:
            await self.message.edit(view=self)