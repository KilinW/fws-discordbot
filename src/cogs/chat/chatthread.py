from __future__ import annotations
from functools import partial

from typing import TYPE_CHECKING, Callable, Literal, Optional, List, Dict
import time

import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import asyncio
import asyncpg

from .langchain import LangChainAgent
from .database import ChatDB
from .profile import ChatProfile
from .views import Response, ThreadWelcome
from .contents import thread_welcome_message

if TYPE_CHECKING:
    from main import FactoryBot


class ChatThread:
    def __init__(self, thread: discord.Thread, db: ChatDB):
        self.thread = thread
        self.db: ChatDB = db
        self.msg_history: List[discord.Message] = []
        self.files: Dict[str, bool] = {}
        self.session: aiohttp.ClientSession = aiohttp.ClientSession()
        self.agent: LangChainAgent = LangChainAgent(self, self.db, self.session)
        self._unload_callback: Optional[Callable[[ChatThread], None]] = None
        self._timeout = 3600
        self._timeout_expiry: Optional[float] = None
        self._timeout_task: Optional[asyncio.Task[None]] = None
        self._stopped: asyncio.Future[bool] = asyncio.get_running_loop().create_future()

    async def reload(self) -> None:
        # Reload the history of the thread.
        async for message in self.thread.history(after=self.thread.created_at):
            self.msg_history.append(message)

        await self.thread.edit(locked=False)
        files = await self.db.all_files()
        self.files = {file: False for file in files}
        try:
            if len(self.msg_history) == 1:  # No regular message
                welcome_msg = await self.thread.send(content=thread_welcome_message, view=ThreadWelcome(self, self.db))
                self.msg_history.append(welcome_msg)
        except Exception as e:
            import traceback
            print(e)
            traceback.print_exc()

    async def response(self, message: discord.Message) -> None:
        self._refresh_timeout()
        if self.msg_history[-1].id != message.id:
            self.msg_history.append(message)

        # Lock the thread to prevent user input before completion.
        msg = await self.thread.send("Generating...")
        await self.thread.edit(locked=True)

        # Get the response from the agent.
        response_dict = await self.agent.generate(self.msg_history.copy())

        # Send the response to the thread.
        response_msg = await self.thread.send(
            content=response_dict["content"], embed=response_dict["embed"], view=response_dict["view"]
        )
        await msg.delete()
        
        self.msg_history.append(response_msg)

        view = response_dict["view"]
        view.msg = response_msg

        await self.valid_thread_init(message, response_msg)
        await self.thread.edit(locked=False)

    async def valid_thread_init(
        self, message: discord.Message, response_msg: discord.Message
    ):
        # We only init the thread if user send the first question.
        if len(self.msg_history) > 4:  # Only invite, welcome, first question and first answer.
            return

        if self.thread.name == "New Chat":
            title = await self.agent.title(message, response_msg)
            self.thread = await self.thread.edit(name=title)

        await self.db.log_thread(self.thread, self.msg_history[0].mentions[0])

    async def on_timeout(self) -> None:
        # If the message is not in database owned by anyone.
        if len(await self.db.chat_members(self.thread)) == 0:
            await self.thread.delete()
            return

        # Lock the thread.
        lock_msg = await self.thread.send(
            "This thread is locked due to inactivity. Click the \U0001F513 emoji to unlock the thread.",
        )
        await lock_msg.add_reaction("\U0001F513")
        await self.thread.edit(locked=True)

    @property
    def timeout(self) -> Optional[float]:
        """Optional[:class:`float`]: The timeout in seconds from last interaction with the thread before locking the thread.
        If ``None`` then there is no timeout.
        """
        return self._timeout

    @timeout.setter
    def timeout(self, value: Optional[float]) -> None:
        # If the timeout task is already running this allows it to update
        # the expiry while it's running
        if self._timeout_task_impl is not None:
            if value is not None:
                self._timeout_expiry = time.monotonic() + value
            else:
                self._timeout_expiry = None

        self._timeout = value

    def _start_listening_from_store(self, store: ChatThreadStore) -> None:
        self._unload_callback = partial(store.remove_chat)
        if self.timeout:
            if self._timeout_task is not None:
                self._timeout_task.cancel()

            self._timeout_expiry = time.monotonic() + self.timeout
            self._timeout_task = asyncio.create_task(self._timeout_task_impl())

    def _dispatch_timeout(self) -> None:
        if self._stopped.done():
            return

        if self._unload_callback:
            self._unload_callback(self)
            self._unload_callback = None

        self._stopped.set_result(True)
        asyncio.create_task(
            self.on_timeout(), name=f"ChatThread-unload({self.thread.id})"
        )

    async def _timeout_task_impl(self) -> None:
        while True:
            # Guard just in case someone changes the value of the timeout at runtime
            if self.timeout is None:
                return

            if self._timeout_expiry is None:
                return self._dispatch_timeout()

            # Check if we've elapsed our currently set timeout
            now = time.monotonic()
            if now >= self._timeout_expiry:
                return self._dispatch_timeout()

            # Wait N seconds to see if timeout data has been refreshed
            await asyncio.sleep(self._timeout_expiry - now)

    def _refresh_timeout(self) -> None:
        if self._timeout:
            self._timeout_expiry = time.monotonic() + self._timeout


class ChatThreadStore:
    def __init__(self, db: ChatDB):
        self._chat_threads: Dict[int, ChatThread] = {}
        self.db: ChatDB = db

    async def add_chat(self, thread: discord.Thread) -> None:
        if thread.id in self._chat_threads:
            return
        new_chat = ChatThread(thread, self.db)
        new_chat._start_listening_from_store(self)
        self._chat_threads.update({thread.id: new_chat})
        await self._chat_threads[thread.id].reload()

    def remove_chat(self, chatthread: ChatThread) -> None:
        self._chat_threads.pop(chatthread.thread.id, None)

    def get_chat(self, thread: discord.Thread) -> Optional[ChatThread]:
        return self._chat_threads.get(thread.id)

    async def dispatch_chat(
        self, thread: discord.Thread, message: discord.Message
    ) -> None:
        chat_thread = self.get_chat(thread)

        if not chat_thread:
            await self.add_chat(thread)

        # Dispatch the message to the chat thread.
        await self._chat_threads[thread.id].response(message)
