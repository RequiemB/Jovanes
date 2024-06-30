from __future__ import annotations

import html
import discord
import re

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..main import Jovanes
    from asqlite import ProxiedConnection

async def set_up_database(conn: ProxiedConnection) -> None:
    sql_script = """
        CREATE TABLE IF NOT EXISTS guild_data (
            guild_id INT NOT NULL,
            log_channel INT,
            log_webhook VARCHAR(150),
            PRIMARY KEY (guild_id)
        );

        CREATE TABLE IF NOT EXISTS prefixes (
            guild_id INT NOT NULL,
            prefix CHAR(16)
        );

        CREATE TABLE IF NOT EXISTS trivia (
            user_id INT NOT NULL,
            correct INT,
            wrong INT,
            streak INT,
            PRIMARY KEY (user_id)
        );

        CREATE TABLE IF NOT EXISTS configuration (
            guild_id INT NOT NULL,
            entity CHAR(40),
            disabled INT
        );

        CREATE TABLE IF NOT EXISTS memory (
            user_id INT NOT NULL,
            minutes INT,
            seconds INT,
            total_seconds INT,
            PRIMARY KEY (user_id)
        );

        CREATE TABLE IF NOT EXISTS tictactoe (
            winner INT NOT NULL,
            rival INT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS rps (
            winner INT NOT NULL,
            rival INT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS guess (
            user_id INT NOT NULL,
            wins INT,
            PRIMARY KEY (user_id)
        );
    """

    await conn.executescript(sql_script)

def sanitize_response(string: str) -> str:
    return html.unescape(string)

async def update_trivia_score(bot: Jovanes, user_id: int, is_correct: bool) -> None:
    if user_id in bot.trivia_streaks:
        bot.trivia_streaks[user_id] += 1 if is_correct else 0
    else:
        bot.trivia_streaks[user_id] = 1 if is_correct else 0

    async with bot.pool.acquire() as conn:
        res = await conn.fetchone("SELECT correct, wrong, streak FROM trivia WHERE user_id = ?", (user_id,))

        if not res:
            if is_correct:
                correct, wrong = 1, 0
            else:
                correct, wrong = 0, 1
            await conn.execute("INSERT INTO trivia (user_id, correct, wrong, streak) VALUES (?, ?, ?, ?)", (user_id, correct, wrong, bot.trivia_streaks[user_id]))
        else:
            correct, wrong, streak = res
            if is_correct: correct += 1 
            else: wrong += 1

            if bot.trivia_streaks[user_id] > streak:
                query, params = "UPDATE trivia SET correct = ?, wrong = ?, streak = ? WHERE user_id = ?", (correct, wrong, bot.trivia_streaks[user_id], user_id)
            else:
                query, params = "UPDATE trivia SET correct = ?, wrong = ? WHERE user_id = ?", (correct, wrong, user_id)

            await conn.execute(query, params)
            
        await conn.commit()

def is_odd(num: int) -> bool:
    return (num % 2) != 0

def convert_to_mock(statement: str) -> str:
    res = ""
    for i in range(len(statement)):
        if i == 0:
            res = '"'
        if not i % 2:
            res = res + statement[i].lower()
        else:
            res = res + statement[i].upper()

    res += '" :nerd::point_up:'
    return res

URL_RE = r'^(http:\/\/www\.|https:\/\/www\.|http:\/\/|https:\/\/)?[a-z0-9]+([\-\.]{1}[a-z0-9]+)*\.[a-z]{2,5}(:[0-9]{1,5})?(\/.*)?$'

def is_url(string: str) -> re.Match[str] | None:
    return re.search(URL_RE, string)