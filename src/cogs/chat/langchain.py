import time
from typing import Dict, List, Optional, Union, TypedDict

import discord

from .views import Response
from .profile import ChatProfile
from .database import ChatDB

class ResponseDict(TypedDict):
    content: str
    view: Response
    

class LangChainAgent:
    def __init__(self, db: ChatDB):
        self.db = db

    async def generate(self, history: List[discord.Message]) -> ResponseDict:
        completion = await self._completion(
            history, await self.db.profile(history[-1].author)
        )
        return {
            "content": completion,
            "view": Response(self, history, completion, self.db),
        }

    async def view_regenerate(
        self,
        view: discord.ui.View,
        history: List[discord.Message],
        member: Union[discord.Member, discord.User],
    ) -> Dict:
        profile = await self.db.profile(member)
        completion = await self._completion(history, profile)
        return {"content": completion, "view": view}

    async def _completion(
        self, history: List[discord.Message], profile: ChatProfile
    ) -> str:
        # TODO: Make sure when something went wrong, we still return a string that says something went wrong.
        return f"This is a mock reply for previous {len(history)} messages. Generated at {time.asctime()}    "

    async def title(self, question: discord.Message, answer: discord.Message) -> str:
        return f"Title changed at {time.asctime()}"
