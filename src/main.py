import asyncio
import logging
import logging.handlers
import os
import sys
from typing import Optional

import asyncpg
import discord
from aiohttp import ClientSession
from discord.ext import commands

from utils.database import DB
from utils.config import Config

# Add parent directory to path
current_dir = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

intents = discord.Intents.default()
intents.message_content = True

class wangbot(commands.Bot):
    def __init__(
        self,
        *args,
        db_pool: asyncpg.Pool,
        web_client: ClientSession,
        testing_guild_id: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.wangsysDB = DB(db_pool)
        self.web_client = web_client
        self.testing_guild_id = testing_guild_id

    async def setup_hook(self):
        # Load cogs
        for filename in os.listdir(current_dir + "/cogs"):
            if filename.endswith(".py"):
                await self.load_extension(f"cogs.{filename[:-3]}")

    async def on_ready(self):
        print(f"We have logged in as {self.user}")


async def main():
    config = Config(parent_dir+"/config.ini")
    # Logging
    logger = logging.getLogger("discord")
    logger.setLevel(logging.INFO)

    handler = logging.handlers.RotatingFileHandler(
        filename="discord.log",
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
        user=config.postgresql_user(),
        password=config.postgresql_password(),
        host=config.postgresql_host(),
        port=config.postgresql_port(),
        database=config.postgresql_database(),
        min_size=3,
        command_timeout=30,
    ) as pool:
        async with wangbot(
            command_prefix=commands.when_mentioned_or("$"),
            intents=intents,
            db_pool=pool,
            web_client=web_client,
        ) as bot:
            await bot.start(config.bot_token())


asyncio.run(main())
