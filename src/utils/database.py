import asyncpg

class DB():
    def __init__(self, pool: asyncpg.pool.Pool):
        self.pool = pool