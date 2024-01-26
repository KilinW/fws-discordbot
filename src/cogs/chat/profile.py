from typing import Optional

import asyncpg


class ChatProfile:
    def __init__(self, record: Optional[asyncpg.Record] = None):
        if record is not None:
            self.user_id = record["user_id"]
            self.name = record["name"]
            self.selected = record["selected"]
            self.description = record["description"]
            self.instruction = record["instruction"]
            self.model_name = record["model_name"]
            self.params = record["params"]
        else:
            self.default()
    def default(self) -> None:
        self.user_id = None
        self.name = "Default Profile"
        self.selected = True
        self.description = "Default Profile"
        self.instruction = "Default Profile"
        self.model_name = "default"
        self.params = '{}'
