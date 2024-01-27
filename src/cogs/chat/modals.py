from __future__ import annotations

from typing import Any, Coroutine, Literal, Optional

import discord
from discord import ui
from discord.interactions import Interaction

from .profile import ChatProfile
from .database import ChatDB


class NewProfile(ui.Modal, title="New Profile"):
    def __init__(self):
        super().__init__(timeout=60)
        self.name = ui.TextInput(label="Name", placeholder="Enter a name for the chat")


class Feecback(ui.Modal, title="Feedback"):
    def __init__(self):
        super().__init__(timeout=60)
        self.feedback = ui.TextInput(
            label="Feedback", placeholder="Enter a feedback for the chat"
        )


class AddProfile(ui.Modal, title="Add Profile"):
    def __init__(self, db: ChatDB, profile_buffer: ChatProfile):
        super().__init__(timeout=3600)
        self.db = db
        self.profile_buffer = profile_buffer
        self.name = ui.TextInput(
            label="Name",
            placeholder="Enter a name of this profile",
            style=discord.TextStyle.short,
            default=profile_buffer.name,
        )
        self.description = ui.TextInput(
            label="Description",
            placeholder="Enter a short description of this profile",
            style=discord.TextStyle.short,
        )
        self.model_name = ui.TextInput(
            label="Modal Name",
            placeholder="Enter the name of LLM model",
            style=discord.TextStyle.short,
        )
        self.params = ui.TextInput(
            label="Parameters",
            placeholder="Enter the params of LLM model in JSON format",
            style=discord.TextStyle.long,
        )
        self.instruction = ui.TextInput(
            label="Instruction",
            placeholder="Enter a short instruction of this profile",
            style=discord.TextStyle.long,
        )
        self.add_item(self.name)
        self.add_item(self.description)
        self.add_item(self.model_name)
        self.add_item(self.params)
        self.add_item(self.instruction)

    async def on_submit(self, interaction: Interaction) -> None:
        self.profile_buffer.user_id = interaction.user.id
        self.profile_buffer.name = self.name.value
        self.profile_buffer.description = self.description.value
        self.profile_buffer.model_name = self.model_name.value
        self.profile_buffer.params = self.params.value
        self.profile_buffer.instruction = self.instruction.value
        await interaction.response.send_message(
            content="# Profile adding.", ephemeral=True
        )
        status = await self.db.add_profile(interaction.user, self.profile_buffer)
        if status:
            await interaction.edit_original_response(
                content=f"# Profile added: {self.profile_buffer.name}"
            )
        else:
            await interaction.edit_original_response(
                content=f"# Failed to add profile: {self.profile_buffer.name}. Please check if params are valid JSON.",
                embeds=[
                    discord.Embed(
                        title="Name", description=self.profile_buffer.name
                    ),
                    discord.Embed(
                        title="Description",
                        description=self.profile_buffer.description,
                    ),
                    discord.Embed(
                        title="Model Name",
                        description=self.profile_buffer.model_name,
                    ),
                    discord.Embed(
                        title="Params", description=self.profile_buffer.params
                    ),
                    discord.Embed(
                        title="Instruction",
                        description=self.profile_buffer.instruction,
                    ),
                ],
            )
        return


class EditProfile(ui.Modal, title="Edit Profile"):
    def __init__(self, db: ChatDB, profile_buffer: ChatProfile):
        super().__init__(timeout=3600)
        self.db = db
        self.profile_buffer = profile_buffer
        self.name = ui.TextInput(
            label="Name",
            placeholder="Enter a name of this profile",
            style=discord.TextStyle.short,
            default=profile_buffer.name,
        )
        self.description = ui.TextInput(
            label="Description",
            placeholder="Enter a short description of this profile",
            style=discord.TextStyle.short,
            default=profile_buffer.description,
        )
        self.model_name = ui.TextInput(
            label="Modal Name",
            placeholder="Enter the name of LLM model",
            style=discord.TextStyle.short,
            default=profile_buffer.model_name,
        )
        self.params = ui.TextInput(
            label="Parameters",
            placeholder="Enter the params of LLM model in JSON format",
            style=discord.TextStyle.long,
            default=profile_buffer.params,
        )
        self.instruction = ui.TextInput(
            label="Instruction",
            placeholder="Enter a short instruction of this profile",
            style=discord.TextStyle.long,
            default=profile_buffer.instruction,
        )
        self.add_item(self.name)
        self.add_item(self.description)
        self.add_item(self.model_name)
        self.add_item(self.params)
        self.add_item(self.instruction)

    async def on_submit(self, interaction: Interaction) -> None:
        self.profile_buffer.user_id = interaction.user.id
        self.profile_buffer.name = self.name.value
        self.profile_buffer.description = self.description.value
        self.profile_buffer.model_name = self.model_name.value
        self.profile_buffer.params = self.params.value
        self.profile_buffer.instruction = self.instruction.value
        await interaction.response.send_message(
            content="# Profile editing.", ephemeral=True
        )
        status = await self.db.edit_profile(interaction.user, self.profile_buffer)
        if status:
            await interaction.edit_original_response(
                content=f"# Profile edited: {self.profile_buffer.name}"
            )
        else:
            await interaction.edit_original_response(
                content=f"# Failed to edit profile: {self.profile_buffer.name}. Please check if params are valid JSON.",
                embeds=[
                    discord.Embed(
                        title="Name", description=self.profile_buffer.name
                    ),
                    discord.Embed(
                        title="Description",
                        description=self.profile_buffer.description,
                    ),
                    discord.Embed(
                        title="Model Name",
                        description=self.profile_buffer.model_name,
                    ),
                    discord.Embed(
                        title="Params", description=self.profile_buffer.params
                    ),
                    discord.Embed(
                        title="Instruction",
                        description=self.profile_buffer.instruction,
                    ),
                ]
            )
        return
