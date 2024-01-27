from typing import List, Literal
import discord
from discord import app_commands
from discord.ext import commands
import os
import aiohttp

from .chatthread import ChatThreadStore
from .database import ChatDB
from .views import ChatPanel
from .modals import AddProfile, EditProfile
from .profile import ChatProfile
from .contents import chat_panel_message


@app_commands.guild_only()
class UserGroup(app_commands.Group):
    def __init__(self, db: ChatDB, chatstore: ChatThreadStore):
        super().__init__(name="chat", description="Chat user commands group")
        self.db = db
        self.chatstore = chatstore
        self.admin_group = AdminGroup(db, chatstore)
        self.add_command(self.admin_group)

    @app_commands.command(name="new")
    async def new_chat(self, interaction: discord.Interaction) -> None:
        # Create a thread for that interaction.
        await interaction.response.defer(ephemeral=True, thinking=True)

        # Get the channel of the interaction.
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            msg = await interaction.followup.send(
                "This command can only be used in a text channel.", ephemeral=True
            )
            return
        # Create a thread in that channel
        thread = await channel.create_thread(
            name="New Chat", auto_archive_duration=10080, slowmode_delay=5
        )
        await thread.add_user(interaction.user)
        await self.chatstore.add_chat(thread)

        await interaction.followup.send(
            f"Created a new chat thread: {thread.mention}", ephemeral=True
        )

    # @app_commands.command(name="panel")
    # async def main_panel(self, interaction: discord.Interaction) -> None:
    #    all_thread = await self.db.all_threads(interaction.user)
    #    await interaction.response.send_message(chat_panel_message, ephemeral=True, view=ChatPanel(self.db, self.chatstore))

    @app_commands.command(name="profile", description="Manage your profiles.")
    @app_commands.describe(
        action="The action to do with your profile.", profile="The profile name."
    )
    async def profile(
        self,
        interaction: discord.Interaction,
        action: Literal["Select", "Add", "Delete", "Edit"],
        profile: str,
    ) -> None:
        if action == "Select":
            success = await self.db.select_profile(interaction.user, profile)
            if success:
                await interaction.response.send_message(
                    f"# Selected profile: {profile}", ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"# Failed to select profile: {profile}", ephemeral=True
                )

        elif action == "Add":
            chat_profile = await self.db.find_profile(interaction.user, profile)
            if chat_profile is not None:
                await interaction.response.send_message(
                    f"# Profile already exists: {profile}", ephemeral=True
                )
                return
            else:
                profile_buffer: ChatProfile = ChatProfile()
                profile_buffer.name = profile
                await interaction.response.send_modal(
                    AddProfile(self.db, profile_buffer)
                )

        elif action == "Delete":
            status = await self.db.delete_profile(interaction.user, profile)
            if status:
                await interaction.response.send_message(
                    f"# Deleted profile: {profile}", ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"# Failed to delete profile: {profile}", ephemeral=True
                )

        elif action == "Edit":
            chat_profile = await self.db.find_profile(interaction.user, profile)
            if chat_profile is None:
                await interaction.response.send_message(
                    f"# Profile not found: {profile}", ephemeral=True
                )
                return
            await interaction.response.send_modal(EditProfile(self.db, chat_profile))

        else:
            await interaction.response.send_message(
                f"# Invalid action: {action}", ephemeral=True
            )

    @profile.autocomplete("profile")
    async def profile_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        profiles = [
            profile.name for profile in await self.db.all_profiles(interaction.user)
        ]
        profiles.append("Default Profile")
        return [
            app_commands.Choice(name=profile, value=profile)
            for profile in profiles
            if current.lower() in profile.lower()
        ]

    @app_commands.command(name="ask")
    async def ask(self, interaction: discord.Interaction) -> None:
        pass


@app_commands.guild_only()
class AdminGroup(app_commands.Group):
    def __init__(self, db: ChatDB, chatstore: ChatThreadStore):
        super().__init__(name="admin", description="Chat admin commands group")
        self.db = db
        self.chatstore = chatstore

    @app_commands.command(name="upload")
    @app_commands.describe(file="The file to upload.")
    async def upload(
        self, interaction: discord.Interaction, file: discord.Attachment
    ) -> None:
        await interaction.response.send_message(
            f"Uploaded file: {file.filename}", ephemeral=True
        )
        await self.db.add_file(file.filename, file.url)
        payload = {
            "url": file.url,
            "file_name": file.filename,
            "vectorize_params": {"chunk_size": 300, "chunk_overlap": 150},
        }
        print("hi")
        print(payload)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(os.environ.get("LANGCHAIN_HOST")+"upload_file", json=payload) as response:
                    print(response)
            print("finished")
        except Exception as e:
            import traceback
            print(e)
            traceback.print_exc()
