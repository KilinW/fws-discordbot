from __future__ import annotations

import time
import os
from typing import Dict, List, Optional, Union, TypedDict, TYPE_CHECKING

import discord
import aiohttp

from .views import Response
from .profile import ChatProfile
from .database import ChatDB

if TYPE_CHECKING:
    from .chatthread import ChatThread


class ResponseDict(TypedDict):
    content: str
    embed: discord.Embed
    view: Response


class LangChainAgent:
    def __init__(self, thread: ChatThread, db: ChatDB, session: aiohttp.ClientSession):
        self.db = db
        self.thread = thread
        self.session = session
        host = os.environ.get("LANGCHAIN_HOST")
        if host is None:
            raise Exception("LANGCHAIN_HOST is not set.")
        self.host = host

    async def generate(self, history: List[discord.Message]) -> ResponseDict:
        profile = await self.db.profile(history[-1].author)
        completion = await self._completion(history, profile)
        Embed = discord.Embed(title="Extra Info")
        Embed.add_field(name="Reference", value=completion["reference1"])
        Embed.add_field(name="Profile", value=profile.name)
        return {
            "content": completion["answer"],
            "embed": Embed,
            "view": Response(self, history, completion["answer"], self.db),
        }

    async def view_regenerate(
        self,
        view: Response,
        history: List[discord.Message],
        member: Union[discord.Member, discord.User],
    ) -> Dict:
        profile = await self.db.profile(member)
        completion = await self._completion(history, profile, len(view.responses))
        Embed = discord.Embed(title="Extra Info")
        Embed.add_field(name="Reference", value=completion["reference1"])
        Embed.add_field(name="Profile", value=profile.name)
        return {"content": completion["answer"], "embed": Embed, "view": view}

    async def _completion(
        self, history: List[discord.Message], profile: ChatProfile, regen_count: int = 0
    ) -> dict:
        # TODO: Make sure when something went wrong, we still return a string that says something went wrong.
        msg_payload: List[str] = []
        for msg in history:
            if msg.type != discord.MessageType.default:
                continue
            msg_payload.append(msg.content)
        history_payload = msg_payload[1:-1]
        input_payload = msg_payload[-1]

        selected_files = []
        for file in self.thread.files:
            if self.thread.files[file]:
                selected_files.append(file)

        payload = {
            "input": input_payload,
            "model": profile.model_name,
            "instruction": profile.instruction,
            "params": profile.params,
            "regen_count": regen_count,
            "chat_history": history_payload,
            "file_name": selected_files,
        }

        print(payload)

        response = await self.session.post(self.host + "agent", json=payload)

        # Decode content to dict
        res_dict = await response.json()

        print(res_dict)

        return res_dict

    async def title(self, question: discord.Message, answer: discord.Message) -> str:
        profile = ChatProfile()
        payload = {
            "input": f"Here are two conversations, please make a title for this conversation in 30 characters. Reply with and only with the title itself. \n\nQuestion: {question.content}\n\nAnswer: {answer.content}",
            "model": profile.model_name,
            "instruction": "You are a chatbot that can generate a title for a conversation. The title need to be short and meaningful. It shouldn't be to general. It's better to be very specific to the conversation.",
            "params": {
                "model_params": {
                    "temperature": 1,
                    "max_length": 20,
                },
                "langchain_params": {
                    "chunk_size": 300,
                    "chunk_overlap": 150,
                },
            },
            "regen_count": 0,
            "chat_history": [],
            "file_name": [],
        }

        print(payload)

        response = await self.session.post(self.host + "agent", json=payload)

        res_dict = await response.json()

        print(res_dict)

        return res_dict["answer"]
