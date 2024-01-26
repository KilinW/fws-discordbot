from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Optional, List, Union

import discord
from discord import app_commands
from discord.ext import commands
import asyncpg

from .chatthread import ChatThreadStore
from .database import ChatDB
from .group import UserGroup

if TYPE_CHECKING:
    from main import FactoryBot

@app_commands.guild_only()
class Chat(commands.Cog):
    def __init__(self, bot: FactoryBot, db: Optional[asyncpg.Pool] = None):
        self.bot = bot
        self.description = '''A cog for chat commands.'''
        self.db = ChatDB(bot.db) if db is None else ChatDB(db)
        self.chatstore = ChatThreadStore(self.db)
        self.bot.tree.add_command(UserGroup(self.db, self.chatstore))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Check if the message is bot message
        if message.author.bot:
            return
        # Check if the message is in a thread owned by the bot
        if not isinstance(message.channel, discord.Thread):
            return
        if message.channel.owner != self.bot.user:
            return
        await self.chatstore.dispatch_chat(message.channel, message)

    @commands.Cog.listener()
    async def on_ready(self):
        # Build Database
        await self.db.setup()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payloads: discord.RawReactionActionEvent):
        if not await self.db.is_chat_owner(payloads.channel_id, payloads.user_id):
            return

        thread = self.bot.get_channel(payloads.channel_id)
        if not isinstance(thread, discord.Thread):  # This should never happen. But just in case.
            return
        
        msg = await thread.fetch_message(payloads.message_id)
        if msg.author != self.bot.user:
            return
        await msg.delete()
        
        await self.chatstore.add_chat(thread)

    async def log_thread(self, thread: discord.Thread, member: Union[discord.Member, discord.User]) -> None:
        # Log the thread to the database.
        async with self.bot.db.acquire() as connection:
            await connection.execute("""
                INSERT INTO factorybot.threads(user_id, thread_id, guild_id, created_at, deleted, owner)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, member.id, thread.id, thread.guild.id, thread.created_at, False, True)
            
    @commands.Cog.listener()
    async def on_raw_thread_update(self, payload: discord.RawThreadUpdateEvent):
        if payload.data["owner_id"] != self.bot.user.id:    # type: ignore
            return
        # TODO: This function should deal with the problm when the thread is locked and also auto archive.
        # We need to modifiy the last message of the thread to tell user to revive the thread using commands.
        # Since emoji can't be used in thread a locked and archived thread.