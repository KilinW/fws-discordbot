from __future__ import annotations
import asyncio
from enum import Enum
from typing import Dict, List, TYPE_CHECKING, Optional, Union

import discord
from discord import app_commands
from discord.ext import commands

from .database import ChatDB

if TYPE_CHECKING:
    from .langchain import LangChainAgent


class FeedbackType(Enum):
    # Number is encoded by bitwise operation. Just like linux file permission.
    NEUTRAL = 0
    LIKE = 1
    HARMFUL = 2
    WRONG = 4
    HW = 6  # Harmful and Wrong
    USELESS = 8
    HU = 10  # Harmful and Useless
    WU = 12  # Wrong and Useless
    HUW = 14  # Harmful, Wrong and Useless


class MainPanel(discord.ui.View):
    # This is the main panel for the chat cog.
    def __init__(self, db: ChatDB, interaction: discord.Interaction):
        super().__init__()
        self.db = db
        self.user: Union[discord.Member, discord.User] = interaction.user
    
    @discord.ui.button(label="New Chat", style=discord.ButtonStyle.success, row=1)
    async def new_chat(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

    @discord.ui.button(label="Profile", style=discord.ButtonStyle.primary, row=1)
    async def profile(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass
    
    @discord.ui.button(label="My Chats", style=discord.ButtonStyle.secondary, row=1)
    async def my_chats(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass


class ProfilePanel(discord.ui.View):
    # Mange your profile.
    pass

class ChatPanel(discord.ui.View):
    pass


class FastQuestion(discord.ui.View):
    # This is the view for a fast question.
    # There should be some buttons for user who want to ask further questions.
    # Then we should open a thread for this question.
    pass


class Response(discord.ui.View):
    # This is the view for a response.
    # Button for regenerating the response.
    def __init__(
        self,
        agent: LangChainAgent,
        msg_history: List[discord.Message],
        response: str,
        db: ChatDB,
    ):
        super().__init__()
        self.timeout = 10
        self.db = db
        self.agent = agent
        self.msg_history = msg_history
        self.responses: List[str] = [response]
        self.cur_response = 0
        self.msg: Optional[discord.Message] = None
    
    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True   # type: ignore
        if self.msg is not None:
            await self.msg.edit(view=self)

    @discord.ui.button(label="↺", style=discord.ButtonStyle.primary, row=1)
    async def regenerate(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        response_dict = await self.agent.view_regenerate(
            self, self.msg_history, interaction.user
        )
        self.responses.append(response_dict["content"])
        self.cur_response = len(self.responses) - 1
        self.page.label = f"{len(self.responses)}/{len(self.responses)}"
        self.next.disabled = True
        self.previous.disabled = False
        await interaction.response.edit_message(**response_dict)

    @discord.ui.button(
        label="←", style=discord.ButtonStyle.secondary, row=1, disabled=True
    )
    async def previous(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.cur_response = max(self.cur_response - 1, 0)
        if self.cur_response == 0:
            self.previous.disabled = True
        self.next.disabled = False
        self.page.label = f"{self.cur_response + 1}/{len(self.responses)}"
        await interaction.response.edit_message(
            content=self.responses[self.cur_response], view=self
        )

    @discord.ui.button(
        label="1/1", style=discord.ButtonStyle.secondary, row=1, disabled=True
    )
    async def page(self, interaction: discord.Interaction, button: discord.ui.Button):
        return

    @discord.ui.button(
        label="→", style=discord.ButtonStyle.secondary, row=1, disabled=True
    )
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.cur_response = min(self.cur_response + 1, len(self.responses) - 1)
        if self.cur_response == len(self.responses) - 1:
            self.next.disabled = True
        self.previous.disabled = False
        self.page.label = f"{self.cur_response + 1}/{len(self.responses)}"
        await interaction.response.edit_message(
            content=self.responses[self.cur_response]
        )

    @discord.ui.button(label="Feedback", style=discord.ButtonStyle.success, row=1)
    async def feedback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            content="Thanks for your feedback! What do you think about this response?",
            view=Feedback(self.db, interaction.message),    # type: ignore
            ephemeral=True,
        )
        # await interaction.response.send_message("感謝您的回報，請問你對這則回覆的評價是？", view=Feedback(self.db), ephemeral=True)


class Feedback(discord.ui.View):
    # This is the view for a bad response.
    # Button for reporting the response.
    def __init__(self, db: ChatDB, message: discord.Message):
        super().__init__()
        self.db = db
        self.target_message = message
        self.feedback_type: FeedbackType = FeedbackType.NEUTRAL
        self.state = 0
        self.feedback_detail: str = ""
        self.bad_reason_select = BadReasonSelect(row=2)

    def update_items(self):
        self.clear_items()
        self.add_item(self.like)
        self.add_item(self.dislike)
        if self.state == 1:  # Like
            self.detail.row = 2
            self.submit.row = 2
            self.add_item(self.detail)
            self.add_item(self.submit)
        if self.state == 2:  # Dislike
            self.add_item(self.bad_reason_select)
            self.detail.row = 3
            self.submit.row = 3
            self.add_item(self.detail)
            self.add_item(self.submit)

    @discord.ui.button(label="👍", style=discord.ButtonStyle.success, row=1)
    async def like(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.state = 1
        self.update_items()
        self.feedback_type = FeedbackType.LIKE
        self.like.disabled = True
        self.dislike.disabled = False
        await interaction.response.edit_message(
            content="Thank you. We will keep improving our service. You can provide more details to help us improve, or click the button below to submit this feedback.",
            view=self,
        )
        # await interaction.response.edit_message(content="謝謝你，我們會繼續努力的！ 你可以提供詳細說明以幫助我們改進，或是點擊下方的按鈕來提交這則回饋。")

    @discord.ui.button(label="👎", style=discord.ButtonStyle.danger, row=1)
    async def dislike(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.state = 2
        self.update_items()
        self.feedback_type = FeedbackType.HARMFUL
        self.dislike.disabled = True
        self.like.disabled = False
        await interaction.response.edit_message(
            content="We are sorry for that. You can provide more details to help us improve, or click the button below to submit this feedback.",
            view=self,
        )
        return

    @discord.ui.button(
        label="Addition Feedback", style=discord.ButtonStyle.secondary, row=2
    )
    async def detail(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            FeedbackModal(self.feedback_type, self)
        )

        await interaction.edit_original_response(
            content="Thanks for your feedback! We will keep improving our service. You can click the button below to submit this feedback.",
            view=self,
        )

    @discord.ui.button(label="Submit", style=discord.ButtonStyle.primary, row=2)
    async def submit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.feedback_detail != "" or self.feedback_type != FeedbackType.NEUTRAL:
            await self.db.feedback(interaction.user, self.target_message, self.feedback_detail, self.feedback_type.value)
        await interaction.response.edit_message(
            content="# **Your feedback has been submitted. Thank you!**",
            embed=None,
            view=None,
        )
        await asyncio.sleep(10)
        await interaction.delete_original_response()


class BadReasonSelect(discord.ui.Select["Feedback"]):
    # This is the view for a bad response.
    # Button for reporting the response.
    def __init__(self, row):
        options = [
            discord.SelectOption(
                label="This is harmful / unsafe",
                value="2"
                # label="這則回覆有害/不安全",
            ),
            discord.SelectOption(
                label="This isn't true",
                value="4"
                # label="這則回覆有誤",
            ),
            discord.SelectOption(
                label="This isn't helpful",
                value="8"
                # label="這則回覆沒有幫助",
            ),
        ]

        super().__init__(
            placeholder="What's the issue with the response?",
            min_values=0,
            max_values=len(options),
            options=options,
            row=row,
        )

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: Feedback = self.view

        feedback_type = 0

        for option in self.options:
            if option.value in self.values:
                option.default = True
                feedback_type += int(option.value)
            else:
                option.default = False
        
        view.feedback_type = FeedbackType(feedback_type)
        
        await interaction.response.edit_message(
            content="Thanks for your feedback! You can provide more details to help us improve, or click the button below to submit this feedback.",
            view=view,
        )
            

class FeedbackModal(discord.ui.Modal):
    feedback = discord.ui.TextInput(
            label="Additional Feedback",
            style=discord.TextStyle.long,
            placeholder="",
            min_length=0,
            max_length=1000,
        )
    def __init__(self, feedback_type: FeedbackType, view: Feedback):
        if feedback_type == FeedbackType.LIKE:
            self.title = "👍 Provide additional feedback"
            placeholder = "What do you like about this response?"
        elif feedback_type == FeedbackType.NEUTRAL:
            self.title = "What do you think about this response?"
            placeholder = "What do you think about this response?"
        else:
            self.title = "👎 What do you dislike about this response?"
            placeholder = (
                "What was the issue with the response? How could it be improved?"
            )
        self.default = view.feedback_detail
        super().__init__(timeout=3600)
        self.feedback.placeholder = placeholder
        self.view = view
        
    async def on_submit(self, interaction: discord.Interaction):        
        await interaction.response.edit_message(
            content="We have received your feedback. Please check the embed below.",
            embed=discord.Embed(
                title="Additional Feedback",
                description=self.feedback.value,
            ),
            view=self.view
        )
        self.view.feedback_detail = self.feedback.value
        return
