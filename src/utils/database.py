import asyncpg


class FactoryDB:
    def __init__(self, pool: asyncpg.pool.Pool):
        self.pool = pool
        # Check if schema "factorybot" exists in database. If not, create it.
    
    async def _db_setup(self):
        async with self.pool.acquire() as connection:
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
        async with self.pool.acquire() as connection:
            # Create the table
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS factorybot.threads (
                    user_id bigint NOT NULL,
                    thread_id bigint,
                    guild_id bigint,
                    "time" date,
                    PRIMARY KEY (user_id)
                );

                ALTER TABLE factorybot.threads
                OWNER TO chilling;
            """)
            print("Table 'threads' checked/created in schema 'factorybot'.")
            
        # Check if the profile tables exist in the schema. If not, create them.
        async with self.pool.acquire() as connection:
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

