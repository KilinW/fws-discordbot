from __future__ import annotations

from typing import Literal, Optional

import discord
from discord import ui


class NewProfile(ui.Modal, title="New Profile"):
    def __init__(self):
        super().__init__(timeout=60)
        self.name = ui.TextInput(label="Name", placeholder="Enter a name for the chat")
        
class Feecback(ui.Modal, title="Feedback"):
    def __init__(self):
        super().__init__(timeout=60)
        self.feedback = ui.TextInput(label="Feedback", placeholder="Enter a feedback for the chat")