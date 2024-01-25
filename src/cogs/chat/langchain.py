import time
from typing import Dict, List

import discord


class LangChainAgent():
    def __init__(self):
        pass

    async def completion(self, history: List[discord.Message]) -> Dict:
        return {
            "content": "Sorry I don't know"
        }

    async def title(self, question: discord.Message, answer: discord.Message) -> str:
        return f"Title changed at {time.asctime()}"