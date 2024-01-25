from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Optional, List, Union

import discord
from discord import app_commands
from discord.ext import commands
import asyncpg

from .chatthread import ChatThreadStore
from .database import ChatDB

if TYPE_CHECKING:
    from main import FactoryBot

@app_commands.guild_only()
class Chat(commands.GroupCog, name="chat"):
    def __init__(self, bot: FactoryBot, db: Optional[asyncpg.Pool] = None):
        self.bot = bot
        self.description = '''A cog for chat commands.'''
        self.db = ChatDB(bot.db) if db is None else ChatDB(db)
        self.chatstore = ChatThreadStore(self.db)

    @app_commands.command(name="new")
    async def new_chat(self, interaction: discord.Interaction) -> None:
        # Create a thread for that interaction.
        await interaction.response.defer(ephemeral=True, thinking=True)

        # Get the channel of the interaction.
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            msg = await interaction.followup.send("This command can only be used in a text channel.", ephemeral=True)
            return
        # Create a thread in that channel
        thread = await channel.create_thread(name="New Chat", slowmode_delay=5)
        await thread.add_user(interaction.user)
        await self.chatstore.add_chat(thread)

        await interaction.followup.send(f"Created a new chat thread: {thread.mention}", ephemeral=True)

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


    