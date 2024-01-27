from typing import List, Optional, Union

import asyncpg
import discord
import json
import traceback


from .profile import ChatProfile


class ChatDB:
    def __init__(self, pool: asyncpg.Pool):
        self.db = pool

    async def is_chat_owner(self, thread_id: int, member_id: int) -> bool:
        async with self.db.acquire() as connection:
            result = await connection.fetch(
                """
                SELECT * FROM factorybot.threads
                WHERE thread_id = $1 AND user_id = $2 AND owner = True
            """,
                thread_id,
                member_id,
            )

        return len(result) > 0

    async def chat_owner(self, thread: discord.Thread) -> int:
        async with self.db.acquire() as connection:
            result = await connection.fetchval(
                """
                SELECT user_id FROM factorybot.threads
                WHERE thread_id = $1 AND owner = True
            """,
                thread.id,
            )

        return result

    async def chat_members(self, thread: discord.Thread) -> list[int]:
        async with self.db.acquire() as connection:
            result = await connection.fetch(
                """
                SELECT user_id FROM factorybot.threads
                WHERE thread_id = $1
            """,
                thread.id,
            )

        return [row[0] for row in result]
    
    async def all_thread(self, member: Union[discord.Member, discord.User]) -> List[discord.Thread]:
        async with self.db.acquire() as connection:
            result = await connection.fetch(
                """
                SELECT * FROM factorybot.threads
                WHERE user_id = $1
            """,
                member.id,
            )
        
        return [row[1] for row in result]

    async def log_thread(
        self, thread: discord.Thread, member: Union[discord.Member, discord.User]
    ) -> None:
        # Log the thread to the database.
        async with self.db.acquire() as connection:
            await connection.execute(
                """
                INSERT INTO factorybot.threads(user_id, thread_id, thread_name, guild_id, created_at, deleted, owner)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
                member.id,
                thread.id,
                thread.name,
                thread.guild.id,
                thread.created_at,
                False,
                True,
            )

    async def profile(self, user: Union[discord.Member, discord.User]) -> ChatProfile:
        async with self.db.acquire() as connection:
            result: asyncpg.Record = await connection.fetchrow(
                """
                SELECT * FROM factorybot.profiles
                WHERE user_id = $1 AND selected = True
            """,
                user.id,
            )

        if result is None:
            return ChatProfile()

        return ChatProfile(result)
    
    async def all_profiles(self, user: Union[discord.Member, discord.User]) -> List[ChatProfile]:
        async with self.db.acquire() as connection:
            result: asyncpg.Record = await connection.fetch(
                """
                SELECT * FROM factorybot.profiles
                WHERE user_id = $1
            """,
                user.id,
            )
        if len(result) == 0:
            return []
        
        return [ChatProfile(row) for row in result]
    
    async def find_profile(self, user: Union[discord.Member, discord.User], profile_name: str) -> Optional[ChatProfile]:
        async with self.db.acquire() as connection:
            result: asyncpg.Record = await connection.fetchrow(
                """
                SELECT * FROM factorybot.profiles
                WHERE user_id = $1 AND name = $2
            """,
                user.id,
                profile_name,
            )

        if result is None:
            return None
        
        return ChatProfile(result)
    
    async def edit_profile(self, user: Union[discord.Member, discord.User], profile_buffer: ChatProfile) -> bool:
        selected_profile = await self.find_profile(user, profile_buffer.name)
        if selected_profile is None:
            return False
        
        # Check if profile.params is valid JSON
        try:
            json.loads(profile_buffer.params)
        except json.JSONDecodeError:
            return False
        
        async with self.db.acquire() as connection:
            await connection.execute(
                """
                UPDATE factorybot.profiles
                SET description = $1, instruction = $2, model_name = $3, params = $4
                WHERE user_id = $5 AND name = $6
            """,
                profile_buffer.description,
                profile_buffer.instruction,
                profile_buffer.model_name,
                profile_buffer.params,
                user.id,
                profile_buffer.name,
            )
        
        return True
    
    async def add_profile(self, user: Union[discord.Member, discord.User], profile_buffer: ChatProfile) -> bool:
        selected_profile = await self.find_profile(user, profile_buffer.name)
        if selected_profile is not None:
            return False
        
        # Check if profile.params is valid JSON
        try:
            json.loads(profile_buffer.params)
        except json.JSONDecodeError:
            return False
        
        async with self.db.acquire() as connection:
            await connection.execute(
                """
                INSERT INTO factorybot.profiles (user_id, name, selected, description, instruction, model_name, params)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
                user.id,
                profile_buffer.name,
                False,
                profile_buffer.description,
                profile_buffer.instruction,
                profile_buffer.model_name,
                profile_buffer.params,
            )
        
        return True
    
    async def delete_profile(self, user: Union[discord.Member, discord.User], profile_name: str) -> bool:
        async with self.db.acquire() as connection:
            # Be aware of non-existing profile
            await connection.execute(
                """
                DELETE FROM factorybot.profiles
                WHERE user_id = $1 AND name = $2
            """,
                user.id,
                profile_name,
            )
        
        return True
    
    async def select_profile(self, user: Union[discord.Member, discord.User], profile_name: str) -> bool:
        if profile_name == "Default Profile":
            await self.deselect_profile(user)
            return True
        selected_profile = await self.find_profile(user, profile_name)
        if selected_profile is None:
            return False

        async with self.db.acquire() as connection:
            await connection.execute(
                """
                UPDATE factorybot.profiles
                SET selected = False
                WHERE user_id = $1
            """,
                user.id,
            )
            await connection.execute(
                """
                UPDATE factorybot.profiles
                SET selected = True
                WHERE user_id = $1 AND name = $2
            """,
                user.id,
                profile_name,
            )
            return True
        
    async def deselect_profile(self, user: Union[discord.Member, discord.User]) -> bool:
        async with self.db.acquire() as connection:
            await connection.execute(
                """
                UPDATE factorybot.profiles
                SET selected = False
                WHERE user_id = $1
            """,
                user.id,
            )
            return True
        
    async def all_files(self) -> List[str]:
        async with self.db.acquire() as connection:
            result = await connection.fetch(
                """
                SELECT * FROM factorybot.files
            """
            )
        
        return [row[0] for row in result]
    
    async def add_file(self, name: str, url: str) -> bool:
        async with self.db.acquire() as connection:
            await connection.execute(
                """
                INSERT INTO factorybot.files (name, url)
                VALUES ($1, $2)
                ON CONFLICT (name) DO NOTHING
            """,
                name,
                url,
            )
        
        return True
    
    async def feedback(self, user: Union[discord.Member, discord.User], message: discord.Message, opinion: str, type: int) -> None:
        async with self.db.acquire() as connection:
            await connection.execute(
                """
                INSERT INTO factorybot.feedback (user_id, message_id, opinion, type)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id, message_id) 
                DO UPDATE SET opinion = EXCLUDED.opinion, type = EXCLUDED.type;
            """,
                user.id,
                message.id,
                opinion,
                type,
            )

    async def setup(self):
        async with self.db.acquire() as connection:
            # Check if the schema exists
            schema_exists = await connection.fetchval(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM pg_catalog.pg_namespace
                    WHERE nspname = 'factorybot'
                );
            """
            )

            # Create the schema if it does not exist
            if not schema_exists:
                await connection.execute("CREATE SCHEMA factorybot;")
                print("Schema 'factorybot' created.")
            else:
                print("Schema 'factorybot' already exists.")

        # Check if the thread tables exist in the schema. If not, create them.
        async with self.db.acquire() as connection:
            # Create the table
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS factorybot.threads (
                    user_id bigint NOT NULL,
                    thread_id bigint NOT NULL,
                    thread_name character varying(100),
                    guild_id bigint,
                    created_at date,
                    deleted boolean,
                    owner boolean NOT NULL,  -- Indicates if the user is the owner of the thread
                    PRIMARY KEY (user_id, thread_id)
                );

                ALTER TABLE factorybot.threads
                OWNER TO chilling;
            """
            )
            print("Table 'threads' checked/created in schema 'factorybot'.")
        

        # Check if the profile tables exist in the schema. If not, create them.
        async with self.db.acquire() as connection:
            # Create the table
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS factorybot.profiles
                (
                    user_id bigint,
                    name character varying(20),
                    selected boolean,
                    description character varying(100),
                    instruction character varying(5000),
                    model_name character varying(100),
                    params json,
                    PRIMARY KEY (user_id, name)
                );

                ALTER TABLE IF EXISTS factorybot.profiles
                    OWNER to chilling;
            """
            )
            print("Table 'profiles' checked/created in schema 'factorybot'.")
        
        # Check if the server info tables exist in the schema. If not, create them.
        async with self.db.acquire() as connection:
            # Create the table
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS factorybot.server
                (
                    guild_id bigint,
                    forum_id bigint,
                    PRIMARY KEY (guild_id)
                );

                ALTER TABLE IF EXISTS factorybot.server
                    OWNER to chilling;
            """
            )
            print("Table 'server_info' checked/created in schema 'factorybot'.")

        # Check if the feedback tables exist in the schema. If not, create them.
        async with self.db.acquire() as connection:
            # Create the table
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS factorybot.feedback
                (
                    user_id bigint,
                    message_id bigint,
                    opinion character varying(1000),
                    type integer,
                    PRIMARY KEY (user_id, message_id)
                );

                ALTER TABLE IF EXISTS factorybot.feedback
                    OWNER to chilling;
            """
            )
            print("Table 'feedback' checked/created in schema 'factorybot'.")
            
        # Check if the admins tables exist in the schema. If not, create them.
        async with self.db.acquire() as connection:
            # Create the table
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS factorybot.admins
                (
                    user_id bigint,
                    feedback boolean,
                    PRIMARY KEY (user_id)
                );

                ALTER TABLE IF EXISTS factorybot.admins
                    OWNER to chilling;
            """
            )
            print("Table 'admin' checked/created in schema 'factorybot'.")
            
        async with self.db.acquire() as connection:
            # Create the table
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS factorybot.files
                (
                    name character varying(100),
                    url character varying(500),
                    PRIMARY KEY (name)
                );

                ALTER TABLE IF EXISTS factorybot.files
                    OWNER to chilling;
            """
            )
            print("Table 'files' checked/created in schema 'factorybot'.")