from __future__ import annotations

import html

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..main import Jovanes
    from asqlite import ProxiedConnection

async def set_up_database(conn: ProxiedConnection) -> None:
    query = """
        CREATE TABLE IF NOT EXISTS guild_data (
            guild_id INT NOT NULL,
            log_channel INT,
            PRIMARY KEY (guild_id)
        )
    """

    await conn.execute(query)

    query = """
        CREATE TABLE IF NOT EXISTS prefixes (
            guild_id INT NOT NULL,
            PREFIX CHAR(16)
        )
    """

    await conn.execute(query)

    query = """
        CREATE TABLE IF NOT EXISTS trivia (
            user_id INT NOT NULL,
            correct INT,
            wrong INT,
            streak INT,
            PRIMARY KEY (user_id)
        )
    """

    await conn.execute(query)

    query = """
        CREATE TABLE IF NOT EXISTS disabled (
            guild_id INT NOT NULL,
            entity CHAR(40),
            is_disabled INT
        )
    """

    await conn.execute(query)

    query = """
        CREATE TABLE IF NOT EXISTS memory (
            user_id INT NOT NULL,
            minutes INT,
            seconds INT,
            total_seconds INT,
            PRIMARY KEY (user_id)
        )
    """

    await conn.execute(query)

    query = """
        CREATE TABLE IF NOT EXISTS tictactoe (
            winner INT NOT NULL,
            rival INT NOT NULL
        )
    """
    
    await conn.execute(query)

    query = """
        CREATE TABLE IF NOT EXISTS rps (
            winner INT NOT NULL,
            rival INT NOT NULL
        )
    """

    await conn.execute(query)

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

     