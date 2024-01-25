from typing import Union

import asyncpg
import discord


class ChatDB():
    def __init__(self, pool: asyncpg.Pool):
        self.db = pool
        
    async def is_chat_owner(self, thread_id: int, member_id: int) -> bool:
        async with self.db.acquire() as connection:
            result = await connection.fetch("""
                SELECT * FROM factorybot.threads
                WHERE thread_id = $1 AND user_id = $2 AND owner = True
            """, thread_id, member_id)
        
        return len(result) > 0
    
    async def chat_owner(self, thread: discord.Thread) -> int:
        async with self.db.acquire() as connection:
            result = await connection.fetchval("""
                SELECT user_id FROM factorybot.threads
                WHERE thread_id = $1 AND owner = True
            """, thread.id)
        
        return result
    
    async def chat_members(self, thread: discord.Thread) -> list[int]:
        async with self.db.acquire() as connection:
            result = await connection.fetch("""
                SELECT user_id FROM factorybot.threads
                WHERE thread_id = $1
            """, thread.id)
        
        return [row[0] for row in result]
    
    async def log_thread(self, thread: discord.Thread, member: Union[discord.Member, discord.User]) -> None:
        # Log the thread to the database.
        async with self.db.acquire() as connection:
            await connection.execute("""
                INSERT INTO factorybot.threads(user_id, thread_id, thread_name, guild_id, created_at, deleted, owner)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, member.id, thread.id, thread.name, thread.guild.id, thread.created_at, False, True)
    
    async def setup(self):
        async with self.db.acquire() as connection:
            # Check if the schema exists
            schema_exists = await connection.fetchval("""
                SELECT EXISTS (
                    SELECT 1
                    FROM pg_catalog.pg_namespace
                    WHERE nspname = 'factorybot'
                );
            """)

            # Create the schema if it does not exist
            if not schema_exists:
                await connection.execute("CREATE SCHEMA factorybot;")
                print("Schema 'factorybot' created.")
            else:
                print("Schema 'factorybot' already exists.")
        
        # Check if the thread tables exist in the schema. If not, create them.
        async with self.db.acquire() as connection:
            # Create the table
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS factorybot.threads (
                    user_id bigint NOT NULL,
                    thread_id bigint NOT NULL,
                    thread_name character(100),
                    guild_id bigint,
                    created_at date,
                    deleted boolean,
                    owner boolean NOT NULL,  -- Indicates if the user is the owner of the thread
                    PRIMARY KEY (user_id, thread_id)
                );

                ALTER TABLE factorybot.threads
                OWNER TO chilling;
            """)
            print("Table 'threads' checked/created in schema 'factorybot'.")
            
        # Check if the profile tables exist in the schema. If not, create them.
        async with self.db.acquire() as connection:
            # Create the table
            await connection.execute("""
                CREATE TABLE factorybot.profiles
                (
                    user_id bigint,
                    name character(20),
                    description character(100),
                    instruction character(5000),
                    model_id integer,
                    params json,
                    PRIMARY KEY (user_id)
                );

                ALTER TABLE IF EXISTS factorybot.profiles
                    OWNER to chilling;
            """)
            print("Table 'profiles' checked/created in schema 'factorybot'.")
            
        # Check if the server info tables exist in the schema. If not, create them.
        async with self.db.acquire() as connection:
            # Create the table
            await connection.execute("""
                CREATE TABLE factorybot.server
                (
                    guild_id bigint,
                    forum_id bigint,
                    PRIMARY KEY (guild_id)
                );

                ALTER TABLE IF EXISTS factorybot.server
                    OWNER to chilling;
            """)
            print("Table 'server_info' checked/created in schema 'factorybot'.")