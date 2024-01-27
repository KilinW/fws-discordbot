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
        self.description = ""
        self.instruction = "你是一個廠務知識的聊天機器人，你擅長並只能根據提供的文件回答答案，以下是我想問的問題以及對應的文件，還有過往的對話紀錄。請告訴我解決方案。"
        self.model_name = "gpt-3.5-turbo"
        self.params = {
            "langchain_params": {
                "chunk_size": 300,
                "chunk_overlap": 150
            },
            "model_params": {
                "temperature": 0.5,
                "max_length": 100
            }
        }
