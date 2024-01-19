import asyncpg


class PostgresqlDB:
    def __init__(self, pool: asyncpg.pool.Pool):
        self.pool = pool