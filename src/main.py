import asyncio
import logging
import logging.handlers
import os
import sys
from typing import Optional
import configparser

import asyncpg
import discord
from aiohttp import ClientSession
from discord.ext import commands

from cogs import EXTENSIONS

# Add parent directory to path
current_dir = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.dirname(current_dir)

intents = discord.Intents.default()
intents.message_content = True


class FactoryBot(commands.Bot):
    def __init__(
        self,
        *args,
        db_pool: asyncpg.Pool,
        web_client: ClientSession,
        testing_guild_id: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.db = db_pool
        self.web_client = web_client
        self.testing_guild_id = testing_guild_id

    async def setup_hook(self):
        # Load cogs
        for extension in EXTENSIONS:
            await self.load_extension(extension)

    async def on_ready(self):
        print(f"We have logged in as {self.user}")


async def main():
    config = configparser.ConfigParser()
    config.read(parent_dir + "/config.ini")
    # Logging
    logger = logging.getLogger("discord")
    logger.setLevel(logging.INFO)

    handler = logging.handlers.RotatingFileHandler(
        filename=parent_dir + "discord.log",
        encoding="utf-8",
        maxBytes=32 * 1024 * 1024,  # 32 MiB
        backupCount=5,  # Rotate through 5 files
    )
    dt_fmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(
        "[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Bot
    async with ClientSession() as web_client, asyncpg.create_pool(
        user=config["POSTGRESQL"]["user"],
        password=config["POSTGRESQL"]["password"],
        host=config["POSTGRESQL"]["host"],
        port=config["POSTGRESQL"]["port"],
        database=config["POSTGRESQL"]["database"],
        min_size=3,
        command_timeout=30,
    ) as pool:
        async with FactoryBot(
            command_prefix=commands.when_mentioned_or("$"),
            intents=intents,
            db_pool=pool,
            web_client=web_client,
        ) as bot:
            await bot.start(config["BOT"]["token"])


asyncio.run(main())
